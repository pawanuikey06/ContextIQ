"""
POST/GET /meeting/{meeting_id}/speaker-map
Save and retrieve speaker name mappings (HITL feature).
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

logger = logging.getLogger(__name__)
router = APIRouter()

STORAGE_DIR = Path("storage")


class SpeakerMapRequest(BaseModel):
    """Maps detected speaker IDs to real names."""
    speaker_map: Dict[str, str]  # e.g. {"SPEAKER_00": "Pawan", "SPEAKER_01": "Ravi"}


@router.post("/meeting/{meeting_id}/speaker-map")
async def save_speaker_map(meeting_id: str, body: SpeakerMapRequest):
    """Save speaker name mappings to disk."""
    meeting_dir = STORAGE_DIR / meeting_id
    if not meeting_dir.exists():
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

    map_path = meeting_dir / "speaker_map.json"
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(body.speaker_map, f, indent=2, ensure_ascii=False)

    logger.info("[%s] Speaker map saved: %s", meeting_id, body.speaker_map)

    # Auto-reindex in RAG so chat uses mapped names
    try:
        from app.api.chat import _get_rag_service
        rag = _get_rag_service()
        transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
        if transcript_path.exists():
            count = rag.ingest_meeting(meeting_id)
            logger.info("[%s] Auto-reindexed with speaker names: %d chunks", meeting_id, count)
    except Exception as e:
        logger.warning("[%s] Auto-reindex after speaker map failed: %s", meeting_id, e)

    return {"success": True, "speaker_map": body.speaker_map}


@router.get("/meeting/{meeting_id}/speaker-map")
async def get_speaker_map(meeting_id: str):
    """Load saved speaker name mappings."""
    map_path = STORAGE_DIR / meeting_id / "speaker_map.json"
    if not map_path.exists():
        return {"speaker_map": {}}

    with open(map_path, "r", encoding="utf-8") as f:
        return {"speaker_map": json.load(f)}
