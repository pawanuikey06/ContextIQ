"""
Confluence API Router
"""
import logging
from fastapi import APIRouter, HTTPException

from app.services import confluence_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/confluence/status")
async def confluence_status():
    """Check Confluence API connectivity."""
    return confluence_service.check_status()


@router.post("/meeting/{meeting_id}/confluence/push")
async def push_to_confluence(meeting_id: str):
    """Push meeting data to Confluence."""
    try:
        result = confluence_service.push_meeting(meeting_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Confluence push failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
