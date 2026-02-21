"""
POST /upload-video
Accepts a video file, extracts audio (16kHz mono WAV), returns meeting_id.
Audio is extracted ONCE and stored in data/audio/ for reuse.
"""
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

from app.services.video_to_audio import VideoAudioConverter
from app.schemas.schemas import UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()
video_converter = VideoAudioConverter()

# Directories for video temp files and extracted audio
AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload-video", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file → extract audio → return meeting_id.
    Audio saved to data/audio/{meeting_id}.wav
    """
    if not file.filename.endswith((".mp4", ".mkv", ".mov")):
        raise HTTPException(status_code=400, detail="Unsupported video format. Use .mp4, .mkv, or .mov")

    meeting_id = str(uuid.uuid4())
    logger.info(f"[{meeting_id}] Upload started: {file.filename}")

    # Save uploaded video to a temp location
    temp_video_path = AUDIO_DIR / f"{meeting_id}_temp.mp4"
    audio_path = AUDIO_DIR / f"{meeting_id}.wav"

    try:
        # Write video to disk
        video_bytes = await file.read()
        with open(temp_video_path, "wb") as f:
            f.write(video_bytes)
        logger.info(f"[{meeting_id}] Video saved ({len(video_bytes)} bytes)")

        # Extract audio (16kHz, mono, WAV)
        video_converter.video_to_audio(temp_video_path, audio_path)
        logger.info(f"[{meeting_id}] Audio extracted: {audio_path}")

    except Exception as e:
        logger.error(f"[{meeting_id}] Audio extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio extraction failed: {str(e)}")

    finally:
        # Clean up temp video file
        if temp_video_path.exists():
            temp_video_path.unlink()
            logger.info(f"[{meeting_id}] Temp video deleted")

    return UploadResponse(
        meeting_id=meeting_id,
        audio_path=str(audio_path),
        message="Video uploaded and audio extracted successfully"
    )
