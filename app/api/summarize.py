"""
POST /summarize/{meeting_id}
Generates meeting summaries from existing transcript.
"""
import logging
from fastapi import APIRouter, HTTPException, Query

from app.services.summary_service import MeetingSummaryService
from app.schemas.schemas import SummaryResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/summarize/{meeting_id}", response_model=SummaryResponse)
async def summarize_meeting(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """
    Generate speaker-wise and overall summaries for a meeting.
    Returns cached result if available (pass force=true to regenerate).
    """
    logger.info("[%s] Summary requested (force=%s)", meeting_id, force)

    try:
        service = MeetingSummaryService()
        result = service.summarize(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("[%s] Summary generation failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

    return SummaryResponse(**result)

