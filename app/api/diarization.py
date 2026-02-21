"""
GET /meeting/{meeting_id}
Retrieves the stored transcript JSON for a given meeting.
"""
import json
import logging
from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.schemas.schemas import MeetingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_DIR = Path("storage")


@router.get("/meeting/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: str):
    """
    Retrieve the stored transcript for a meeting.
    Reads from storage/{meeting_id}/transcript.json.
    """
    transcript_path = STORAGE_DIR / meeting_id / "transcript.json"

    if not transcript_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Transcript not found for meeting {meeting_id}. Run transcription first."
        )

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"[{meeting_id}] Transcript retrieved")
    except Exception as e:
        logger.error(f"[{meeting_id}] Failed to read transcript: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read transcript: {str(e)}")

    return MeetingResponse(**data)
