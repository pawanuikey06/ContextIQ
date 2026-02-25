"""
POST /upload-video
Accepts a video file, extracts audio (16kHz mono WAV), returns meeting_id.
Audio is extracted ONCE and stored in data/audio/ for reuse.
Includes SHA-256 deduplication — re-uploading same file returns existing meeting_id.
"""
import uuid
import hashlib
import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

from app.services.video_to_audio import VideoAudioConverter
from app.schemas.schemas import UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()
video_converter = VideoAudioConverter()

# Directories
AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Hash registry for deduplication
HASH_REGISTRY = STORAGE_DIR / "_file_hashes.json"


def _load_hashes() -> dict:
    """Load file hash → meeting_id registry."""
    if HASH_REGISTRY.exists():
        with open(HASH_REGISTRY, "r") as f:
            return json.load(f)
    return {}


def _save_hashes(hashes: dict):
    """Persist file hash → meeting_id registry."""
    with open(HASH_REGISTRY, "w") as f:
        json.dump(hashes, f, indent=2)


@router.post("/upload-video", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file → extract audio → return meeting_id.
    If the same file was uploaded before (SHA-256 match), returns
    the existing meeting_id without re-processing.
    """
    if not file.filename.endswith((".mp4", ".mkv", ".mov")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format. Use .mp4, .mkv, or .mov"
        )

    # Read file bytes
    video_bytes = await file.read()
    logger.info("Upload received: %s (%d bytes)", file.filename, len(video_bytes))

    # ── Deduplication: compute SHA-256 hash ──
    file_hash = hashlib.sha256(video_bytes).hexdigest()
    hash_registry = _load_hashes()

    if file_hash in hash_registry:
        existing_id = hash_registry[file_hash]
        audio_path = AUDIO_DIR / f"{existing_id}.wav"
        if audio_path.exists():
            logger.info(
                "Duplicate detected! hash=%s → existing meeting_id=%s",
                file_hash[:16], existing_id
            )
            return UploadResponse(
                meeting_id=existing_id,
                audio_path=str(audio_path),
                message=f"Duplicate file detected. Returning existing meeting: {existing_id}"
            )
        else:
            logger.warning(
                "Duplicate hash found but audio missing for %s. Re-extracting.",
                existing_id
            )

    # ── New file (or re-extract for missing audio) ──
    # Reuse existing meeting_id if hash was seen before (audio was deleted)
    meeting_id = hash_registry.get(file_hash) or str(uuid.uuid4())
    logger.info("[%s] %s: %s (hash=%s)", meeting_id,
                "Re-extracting audio" if file_hash in hash_registry else "New upload",
                file.filename, file_hash[:16])

    temp_video_path = AUDIO_DIR / f"{meeting_id}_temp.mp4"
    audio_path = AUDIO_DIR / f"{meeting_id}.wav"

    try:
        # Write video to disk
        with open(temp_video_path, "wb") as f:
            f.write(video_bytes)

        # Extract audio (16kHz, mono, WAV)
        video_converter.video_to_audio(temp_video_path, audio_path)
        logger.info("[%s] Audio extracted: %s", meeting_id, audio_path)

        # Register hash → meeting_id
        hash_registry[file_hash] = meeting_id
        _save_hashes(hash_registry)
        logger.info("[%s] Hash registered: %s", meeting_id, file_hash[:16])

    except Exception as e:
        logger.error("[%s] Audio extraction failed: %s", meeting_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Audio extraction failed: {str(e)}"
        )
    finally:
        # Keep video for playback — move to storage dir
        if temp_video_path.exists():
            meeting_dir = STORAGE_DIR / meeting_id
            meeting_dir.mkdir(parents=True, exist_ok=True)
            saved_video = meeting_dir / "video.mp4"
            try:
                import shutil
                shutil.move(str(temp_video_path), str(saved_video))
                logger.info("[%s] Video saved: %s", meeting_id, saved_video)
            except Exception:
                temp_video_path.unlink(missing_ok=True)

    return UploadResponse(
        meeting_id=meeting_id,
        audio_path=str(audio_path),
        message="Video uploaded and audio extracted successfully"
    )
