"""
Meeting Insights API — AI-powered analytics endpoints.
  POST /meeting/{meeting_id}/action-items  — Extract action items & decisions
  POST /meeting/{meeting_id}/auto-title    — Generate meeting title from transcript
"""
import logging
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-init (Groq client loading)
_insights_service = None


def _get_insights_service():
    global _insights_service
    if _insights_service is None:
        from app.services.insights_service import MeetingInsightsService
        _insights_service = MeetingInsightsService()
    return _insights_service


@router.post("/meeting/{meeting_id}/action-items")
async def extract_action_items(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """
    Extract action items, decisions, key takeaways, and follow-ups
    from a meeting transcript using AI.
    """
    logger.info("[%s] Action items requested (force=%s)", meeting_id, force)

    try:
        service = _get_insights_service()
        result = service.extract_action_items(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Action items extraction failed: %s", meeting_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Action items extraction failed: {str(e)}",
        )

    return result


@router.post("/meeting/{meeting_id}/auto-title")
async def generate_title(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """
    Auto-generate a concise, descriptive meeting title from the transcript.
    Saves to metadata.json as 'auto_title'.
    """
    logger.info("[%s] Auto-title requested (force=%s)", meeting_id, force)

    try:
        service = _get_insights_service()
        result = service.generate_title(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Title generation failed: %s", meeting_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Title generation failed: {str(e)}",
        )

    return result


@router.post("/meeting/{meeting_id}/followup-email")
async def generate_followup_email(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """
    Generate a professional follow-up email draft from the meeting.
    Combines title + summary + action items into a ready-to-send email.
    """
    logger.info("[%s] Follow-up email requested (force=%s)", meeting_id, force)

    try:
        service = _get_insights_service()
        result = service.generate_followup_email(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Follow-up email generation failed: %s", meeting_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Follow-up email generation failed: {str(e)}",
        )

    return result
