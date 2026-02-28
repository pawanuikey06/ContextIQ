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

# Singleton — avoid re-creating the service on every request
_publish_service = None


def _get_publish_service():
    global _publish_service
    if _publish_service is None:
        _publish_service = MeetingPublishService()
    return _publish_service


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
        service = _get_publish_service()
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


@router.get("/publish/{meeting_id}/full-report")
async def download_full_report(meeting_id: str):
    """Generate and download a comprehensive full meeting report PDF."""
    from pathlib import Path
    try:
        service = _get_publish_service()
        pdf_path = service.generate_full_report(meeting_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Full report generation failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    return FileResponse(
        path=pdf_path,
        filename="Full_Meeting_Report.pdf",
        media_type="application/pdf",
    )


# ------------------------------------------------------------------
# Full Report — Auto-generate missing sections + build PDF
# ------------------------------------------------------------------

class FullReportEmailRequest(BaseModel):
    """Request body for emailing the full report."""
    recipients: List[str]


@router.post("/publish/{meeting_id}/full-report")
async def generate_full_report_auto(meeting_id: str):
    """
    Auto-generate any missing meeting insights, then build a full report PDF.
    Generates: summary, action_items, requirements, documentation as needed.
    Returns status of each section + PDF path.
    """
    from pathlib import Path

    meeting_dir = Path("storage") / meeting_id
    if not meeting_dir.exists():
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found.")

    generated = []

    # 1. Summary (summary.json)
    if not (meeting_dir / "summary.json").exists():
        try:
            from app.services.summary_service import MeetingSummaryService
            svc = MeetingSummaryService()
            svc.summarize(meeting_id)
            generated.append("summary")
            logger.info("[%s] Auto-generated summary", meeting_id)
        except Exception as e:
            logger.error("[%s] Summary generation failed: %s", meeting_id, e)

    # 2. Action Items + Decisions (action_items.json)
    if not (meeting_dir / "action_items.json").exists():
        try:
            from app.services.insights_service import MeetingInsightsService
            svc = MeetingInsightsService()
            svc.extract_action_items(meeting_id)
            generated.append("action_items")
            logger.info("[%s] Auto-generated action items", meeting_id)
        except Exception as e:
            logger.error("[%s] Action items generation failed: %s", meeting_id, e)

    # 3. Requirements (requirements.json)
    if not (meeting_dir / "requirements.json").exists():
        try:
            from app.services.insights_service import MeetingInsightsService
            svc = MeetingInsightsService()
            svc.extract_requirements(meeting_id)
            generated.append("requirements")
            logger.info("[%s] Auto-generated requirements", meeting_id)
        except Exception as e:
            logger.error("[%s] Requirements generation failed: %s", meeting_id, e)

    # 4. Documentation / MoM (documentation.json)
    if not (meeting_dir / "documentation.json").exists():
        try:
            from app.services.insights_service import MeetingInsightsService
            svc = MeetingInsightsService()
            svc.generate_documentation(meeting_id)
            generated.append("documentation")
            logger.info("[%s] Auto-generated documentation", meeting_id)
        except Exception as e:
            logger.error("[%s] Documentation generation failed: %s", meeting_id, e)

    # 5. Build the full report PDF
    try:
        service = _get_publish_service()
        pdf_path = service.generate_full_report(meeting_id)
    except Exception as e:
        logger.error("[%s] Full report PDF generation failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    return {
        "success": True,
        "meeting_id": meeting_id,
        "generated_sections": generated,
        "pdf_path": pdf_path,
        "message": f"Full report ready. Auto-generated: {', '.join(generated) if generated else 'none (all cached)'}.",
    }


@router.post("/publish/{meeting_id}/full-report/email")
async def email_full_report(meeting_id: str, body: FullReportEmailRequest):
    """
    Email the full report PDF to specified recipients.
    Auto-generates the report if it doesn't exist yet.
    """
    from pathlib import Path

    if not body.recipients:
        raise HTTPException(status_code=400, detail="No recipients specified.")

    meeting_dir = Path("storage") / meeting_id
    pdf_path = meeting_dir / "Full_Report.pdf"

    # Generate if missing
    if not pdf_path.exists():
        # Trigger auto-generation first
        result = await generate_full_report_auto(meeting_id)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to generate report for email.")

    # Send via existing email method
    try:
        service = _get_publish_service()

        # Get meeting title for email subject
        meta_path = meeting_dir / "metadata.json"
        title = f"Meeting {meeting_id[:8]}"
        if meta_path.exists():
            import json
            with open(meta_path, "r", encoding="utf-8") as f:
                title = json.load(f).get("title", title)

        result = service.send_email(
            pdf_path=str(pdf_path),
            meeting_title=f"Full Report: {title}",
            recipients=body.recipients,
        )
    except Exception as e:
        logger.error("[%s] Full report email failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "Email failed"))

    return result
