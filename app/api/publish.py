"""
POST /publish/{meeting_id}
One-click publish: generate PDF + email + Teams delivery.
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.publish_service import MeetingPublishService

logger = logging.getLogger(__name__)
router = APIRouter()


class PublishRequest(BaseModel):
    """Optional config for the publish endpoint."""
    meeting_title: Optional[str] = None
    date: Optional[str] = None
    email_recipients: Optional[List[str]] = None
    teams_webhook_url: Optional[str] = None


@router.post("/publish/{meeting_id}")
async def publish_meeting(meeting_id: str, body: PublishRequest = None):
    """
    One-click publish: generates PDF, optionally emails and/or sends to Teams.

    - Always generates a PDF in storage/{meeting_id}/Meeting_Summary.pdf
    - If email_recipients provided, sends via SMTP
    - If teams_webhook_url provided (or TEAMS_WEBHOOK_URL in .env), sends card
    """
    if body is None:
        body = PublishRequest()

    logger.info("[%s] Publish requested", meeting_id)

    try:
        service = MeetingPublishService()
        result = service.publish(
            meeting_id=meeting_id,
            meeting_title=body.meeting_title,
            date=body.date,
            email_recipients=body.email_recipients,
            teams_webhook_url=body.teams_webhook_url,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Publish failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Publish failed: {str(e)}")

    return result


@router.get("/publish/{meeting_id}/pdf")
async def download_pdf(meeting_id: str):
    """Download the generated Meeting Summary PDF."""
    from pathlib import Path

    pdf_path = Path("storage") / meeting_id / "Meeting_Summary.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="PDF not found. Call POST /publish/{meeting_id} first.",
        )

    return FileResponse(
        path=str(pdf_path),
        filename="Meeting_Summary.pdf",
        media_type="application/pdf",
    )
