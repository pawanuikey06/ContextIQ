"""
Meeting Insights API — AI-powered analytics endpoints.
  POST /meeting/{meeting_id}/action-items  — Extract action items & decisions
  PUT  /meeting/{meeting_id}/action-items  — Save edited action items (HITL)
  POST /meeting/{meeting_id}/auto-title    — Generate meeting title from transcript
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Body

logger = logging.getLogger(__name__)
STORAGE_DIR = Path("storage")

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


@router.put("/meeting/{meeting_id}/action-items")
async def save_action_items(
    meeting_id: str,
    payload: dict = Body(...),
):
    """
    Save human-edited action items back to disk (HITL workflow).
    Accepts the full action_items.json structure.
    """
    meeting_dir = STORAGE_DIR / meeting_id
    if not meeting_dir.exists():
        raise HTTPException(status_code=404, detail="Meeting not found")

    out_path = meeting_dir / "action_items.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info("[%s] Action items saved (HITL edit)", meeting_id)
    except Exception as e:
        logger.error("[%s] Failed to save action items: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "saved", "meeting_id": meeting_id}


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


@router.post("/meeting/{meeting_id}/requirements")
async def extract_requirements(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """Extract requirements, user stories, and constraints from a meeting."""
    logger.info("[%s] Requirements extraction requested (force=%s)", meeting_id, force)
    try:
        service = _get_insights_service()
        result = service.extract_requirements(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Requirements extraction failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Requirements extraction failed: {str(e)}")
    return result


@router.post("/meeting/{meeting_id}/documentation")
async def generate_documentation(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """Generate structured meeting documentation (MoM)."""
    logger.info("[%s] Documentation requested (force=%s)", meeting_id, force)
    try:
        service = _get_insights_service()
        result = service.generate_documentation(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Documentation generation failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Documentation generation failed: {str(e)}")
    return result


@router.post("/meeting/{meeting_id}/sentiment")
async def analyze_sentiment(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """Analyze sentiment of each segment in a meeting transcript."""
    logger.info("[%s] Sentiment analysis requested (force=%s)", meeting_id, force)
    try:
        service = _get_insights_service()
        result = service.analyze_sentiment(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Sentiment analysis failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")
    return result
