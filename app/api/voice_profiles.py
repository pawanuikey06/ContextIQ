"""
Voice Profiles API — speaker clip serving and profile management.

New router, fully self-contained. Registered in main.py.
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)
router = APIRouter()

STORAGE_DIR = Path("storage")

# Lazy-init the voice embedding service
_voice_service = None


def _get_voice_service():
    global _voice_service
    if _voice_service is None:
        from app.services.voice_embedding_service import VoiceEmbeddingService
        _voice_service = VoiceEmbeddingService()
    return _voice_service


# ------------------------------------------------------------------
# Speaker Clips
# ------------------------------------------------------------------

@router.get("/meeting/{meeting_id}/speaker-clips")
async def list_speaker_clips(meeting_id: str):
    """List available speaker audio clips for a meeting. Auto-extracts if missing."""
    clips_dir = STORAGE_DIR / meeting_id / "speaker_clips"

    # Auto-extract clips if they don't exist yet
    if not clips_dir.exists() or not list(clips_dir.glob("*.wav")):
        try:
            service = _get_voice_service()
            service.extract_speaker_clips(meeting_id)
            logger.info("[%s] Auto-extracted speaker clips on first request", meeting_id)
        except Exception as e:
            logger.warning("[%s] Auto clip extraction failed: %s", meeting_id, e)

    if not clips_dir.exists():
        return {"clips": [], "meeting_id": meeting_id}

    clips = []
    for clip_file in sorted(clips_dir.glob("*.wav")):
        clips.append({
            "speaker_id": clip_file.stem,
            "filename": clip_file.name,
            "size_bytes": clip_file.stat().st_size,
        })

    return {"clips": clips, "meeting_id": meeting_id}


@router.get("/meeting/{meeting_id}/speaker-clips/{speaker_id}")
@router.head("/meeting/{meeting_id}/speaker-clips/{speaker_id}")
async def get_speaker_clip(meeting_id: str, speaker_id: str):
    """Serve a speaker's audio clip for playback."""
    clip_path = STORAGE_DIR / meeting_id / "speaker_clips" / f"{speaker_id}.wav"

    # Auto-extract clips if needed
    if not clip_path.exists():
        try:
            service = _get_voice_service()
            service.extract_speaker_clips(meeting_id)
        except Exception:
            pass

    if not clip_path.exists():
        raise HTTPException(status_code=404, detail=f"No clip found for {speaker_id}")

    return FileResponse(
        path=str(clip_path),
        media_type="audio/wav",
        filename=f"{speaker_id}.wav",
    )


# ------------------------------------------------------------------
# Speaker Profiles
# ------------------------------------------------------------------

@router.get("/speaker-profiles")
async def list_speaker_profiles():
    """List all stored speaker profiles (name + embedding exists)."""
    service = _get_voice_service()
    profiles = service.load_profiles()
    return {
        "profiles": [
            {"name": name, "embedding_dim": len(emb)}
            for name, emb in profiles.items()
        ],
        "count": len(profiles),
    }


@router.post("/meeting/{meeting_id}/speaker-profiles")
async def save_profiles_from_map(meeting_id: str):
    """
    Generate embeddings from speaker clips and save profiles using the speaker_map names.
    Called after renaming speakers — links real names to voice embeddings.
    """
    service = _get_voice_service()

    # Load speaker map
    map_path = STORAGE_DIR / meeting_id / "speaker_map.json"
    if not map_path.exists():
        raise HTTPException(status_code=404, detail="No speaker map found. Rename speakers first.")

    with open(map_path, "r", encoding="utf-8") as f:
        speaker_map = json.load(f)

    if not speaker_map:
        return {"saved": 0, "message": "No speaker mappings to process"}

    clips_dir = STORAGE_DIR / meeting_id / "speaker_clips"
    if not clips_dir.exists():
        raise HTTPException(status_code=404, detail="No speaker clips found. Transcribe the meeting first.")

    saved = 0
    for spk_id, real_name in speaker_map.items():
        if not real_name.strip():
            continue

        clip_path = clips_dir / f"{spk_id}.wav"
        if not clip_path.exists():
            logger.warning("[%s] No clip for %s, skipping profile", meeting_id, spk_id)
            continue

        try:
            embedding = service.generate_embedding(str(clip_path))
            if embedding:
                service.save_speaker_profile(real_name.strip(), embedding)
                saved += 1
                logger.info("[%s] Profile saved: %s → %s", meeting_id, spk_id, real_name)
        except Exception as e:
            logger.warning("[%s] Profile generation failed for %s: %s", meeting_id, spk_id, e)

    return {
        "saved": saved,
        "total_speakers": len(speaker_map),
        "message": f"Saved {saved} speaker profile(s)",
    }
