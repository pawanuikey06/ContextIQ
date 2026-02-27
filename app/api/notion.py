"""
Notion API Router
"""
import logging
from fastapi import APIRouter, HTTPException

from app.services import notion_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/notion/status")
async def notion_status():
    """Check Notion API connectivity."""
    return notion_service.check_status()


@router.post("/meeting/{meeting_id}/notion/push")
async def push_to_notion(meeting_id: str):
    """Push meeting data to Notion."""
    try:
        result = notion_service.push_meeting(meeting_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Notion push failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
