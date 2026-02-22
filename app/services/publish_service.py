"""
Meeting Publish Service.
Generates a professional PDF from stored summary JSON,
sends via Email (SMTP) and/or Microsoft Teams (Webhook).

Zero AI cost — uses only deterministic templates.
"""
import os
import json
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime

import requests as http_requests
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# Paths
STORAGE_DIR = Path("storage")
FONTS_DIR = Path(__file__).parent.parent / "fonts"


# ─────────────────────────────────────────────────────────────
# PDF Generator — Hindi + English with clean professional layout
# ─────────────────────────────────────────────────────────────
class SummaryPDF(FPDF):
    """Custom PDF with registered Unicode fonts."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

        # Register fonts for Unicode (Hindi) support
        noto = str(FONTS_DIR / "NotoSans.ttf")
        noto_hi = str(FONTS_DIR / "NotoSansDevanagari.ttf")

        if Path(noto).exists():
            self.add_font("NotoSans", "", noto, uni=True)
        if Path(noto_hi).exists():
            self.add_font("NotoHindi", "", noto_hi, uni=True)

    def header(self):
        """Page header — thin accent line."""
        self.set_draw_color(100, 100, 220)
        self.set_line_width(0.8)
        self.line(10, 10, self.w - 10, 10)
        self.ln(5)

    def footer(self):
        """Page footer — page number and branding."""
        self.set_y(-15)
        self.set_font("NotoSans", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(
            0, 10,
            f"ContextIQ - Meeting Intelligence  |  Page {self.page_no()}/{{nb}}",
            align="C",
        )

    def add_title(self, title: str):
        """Centered meeting title."""
        self.set_font("NotoSans", "", 22)
        self.set_text_color(30, 30, 80)
        self.cell(0, 15, title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def add_date(self, date_str: str):
        """Date line below title."""
        self.set_font("NotoSans", "", 11)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Date: {date_str}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)

    def add_section_heading(self, heading: str):
        """Section heading with an underline accent."""
        self.set_font("NotoSans", "", 14)
        self.set_text_color(50, 50, 140)
        self.cell(0, 10, heading, new_x="LMARGIN", new_y="NEXT")
        # Subtle underline
        self.set_draw_color(180, 180, 220)
        self.set_line_width(0.4)
        y = self.get_y()
        self.line(10, y, self.w - 10, y)
        self.ln(4)

    def add_english_text(self, text: str):
        """Body text in English (NotoSans)."""
        self.set_font("NotoSans", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def add_hindi_text(self, text: str):
        """Body text in Hindi (NotoSansDevanagari)."""
        self.set_font("NotoHindi", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 7, text)
        self.ln(4)

    def add_speaker_block(self, speaker: str, summary: str):
        """Individual speaker summary block."""
        self.set_font("NotoSans", "", 11)
        self.set_text_color(60, 60, 150)
        self.cell(0, 8, speaker, new_x="LMARGIN", new_y="NEXT")
        self.set_font("NotoSans", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 6, summary)
        self.ln(3)


# ─────────────────────────────────────────────────────────────
# Main Publish Service
# ─────────────────────────────────────────────────────────────
class MeetingPublishService:
    """
    One-click publishing: PDF + Email + Teams.
    All template-based, zero AI cost.
    """

    # ── PDF Generation ──────────────────────────────────────
    def generate_pdf(
        self,
        summary_data: dict,
        output_path: str,
        meeting_title: str = "Meeting Summary",
        date: str = None,
    ) -> str:
        """
        Generate a professional PDF from summary JSON.

        Args:
            summary_data: dict with speaker_summaries_en, overall_summary_en,
                          overall_summary_hi
            output_path: where to save the PDF
            meeting_title: title for the PDF header
            date: date string; defaults to today

        Returns:
            absolute path to the generated PDF
        """
        if date is None:
            date = datetime.now().strftime("%B %d, %Y")

        pdf = SummaryPDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        # ── Title & Date ──
        pdf.add_title(meeting_title)
        pdf.add_date(date)

        # ── Overall Summary (English) ──
        overall_en = summary_data.get("overall_summary_en", "")
        if overall_en:
            pdf.add_section_heading("Meeting Summary (English)")
            pdf.add_english_text(overall_en)

        # ── Overall Summary (Hindi) ──
        overall_hi = summary_data.get("overall_summary_hi", "")
        if overall_hi:
            pdf.add_section_heading("Meeting Summary (Hindi)")
            pdf.add_hindi_text(overall_hi)

        # Save PDF
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pdf.output(output_path)
        logger.info("PDF generated: %s", output_path)
        return str(Path(output_path).resolve())

    # ── Email Sending ───────────────────────────────────────
    def send_email(
        self,
        pdf_path: str,
        meeting_title: str,
        recipients: list[str],
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
    ) -> dict:
        """
        Send the PDF as an email attachment via SMTP.

        Args:
            pdf_path: path to the PDF file
            meeting_title: used in subject line
            recipients: list of email addresses
            smtp_*: SMTP config; falls back to env vars

        Returns:
            dict with success status and message
        """
        # Resolve SMTP config from env vars if not provided
        smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        smtp_user = smtp_user or os.getenv("SMTP_USER", "")
        smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_password:
            return {
                "success": False,
                "message": "SMTP credentials not configured. "
                           "Set SMTP_USER and SMTP_PASSWORD in .env",
            }

        if not recipients:
            return {"success": False, "message": "No recipients specified"}

        try:
            # Build the email
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = f"Meeting Summary: {meeting_title}"

            # Professional email body
            body = (
                f"Dear Team,\n\n"
                f"Please find attached the summary for: {meeting_title}.\n\n"
                f"This summary includes speaker-wise contributions and "
                f"an overall meeting overview in English and Hindi.\n\n"
                f"Best regards,\n"
                f"ContextIQ - Meeting Intelligence"
            )
            msg.attach(MIMEText(body, "plain"))

            # Attach PDF
            with open(pdf_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="Meeting_Summary.pdf"',
            )
            msg.attach(part)

            # Send via SMTP
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info("Email sent to %s", recipients)
            return {
                "success": True,
                "message": f"Email sent to {', '.join(recipients)}",
            }

        except Exception as e:
            logger.error("Email sending failed: %s", e)
            return {"success": False, "message": f"Email failed: {str(e)}"}

    # ── Teams Webhook ───────────────────────────────────────
    def send_to_teams(
        self,
        summary_data: dict,
        meeting_title: str,
        date: str = None,
        webhook_url: str = None,
    ) -> dict:
        """
        Send a summary card to a Microsoft Teams channel
        via Incoming Webhook.

        Args:
            summary_data: the meeting summary dict
            meeting_title: display title
            date: date string
            webhook_url: Teams Incoming Webhook URL

        Returns:
            dict with success status and message
        """
        webhook_url = webhook_url or os.getenv("TEAMS_WEBHOOK_URL", "")
        if not webhook_url:
            return {
                "success": False,
                "message": "Teams webhook URL not configured. "
                           "Set TEAMS_WEBHOOK_URL in .env",
            }

        if date is None:
            date = datetime.now().strftime("%B %d, %Y")

        # Build a clean overall summary snippet (first 300 chars)
        overall = summary_data.get("overall_summary_en", "No summary available.")
        snippet = overall[:300] + ("..." if len(overall) > 300 else "")

        # Teams Adaptive Card payload
        card_payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": meeting_title,
                                "weight": "Bolder",
                                "size": "Large",
                                "wrap": True,
                            },
                            {
                                "type": "TextBlock",
                                "text": f"Date: {date}",
                                "isSubtle": True,
                                "spacing": "None",
                            },
                            {
                                "type": "TextBlock",
                                "text": "Meeting Summary",
                                "weight": "Bolder",
                                "spacing": "Medium",
                            },
                            {
                                "type": "TextBlock",
                                "text": snippet,
                                "wrap": True,
                                "spacing": "Small",
                            },
                        ],
                    },
                }
            ],
        }

        try:
            resp = http_requests.post(
                webhook_url,
                json=card_payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code in (200, 202):
                logger.info("Teams message sent successfully")
                return {"success": True, "message": "Sent to Teams channel"}
            else:
                return {
                    "success": False,
                    "message": f"Teams returned {resp.status_code}: {resp.text[:200]}",
                }
        except Exception as e:
            logger.error("Teams delivery failed: %s", e)
            return {"success": False, "message": f"Teams failed: {str(e)}"}

    # ── One-Click Publish ───────────────────────────────────
    def publish(
        self,
        meeting_id: str,
        meeting_title: str = None,
        date: str = None,
        email_recipients: list[str] = None,
        teams_webhook_url: str = None,
    ) -> dict:
        """
        One-click: generate PDF + optionally email + optionally Teams.

        Args:
            meeting_id: UUID of the meeting
            meeting_title: optional title override
            date: optional date override
            email_recipients: if provided, sends email
            teams_webhook_url: if provided, sends to Teams

        Returns:
            dict with status for each channel
        """
        # ── Step 1: Load summary JSON ──
        # Re-read .env to pick up any new credentials
        load_dotenv(override=True)

        summary_path = STORAGE_DIR / meeting_id / "summary.json"
        if not summary_path.exists():
            raise FileNotFoundError(
                f"Summary not found for meeting {meeting_id}. "
                "Generate a summary first."
            )

        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)

        if meeting_title is None:
            meeting_title = f"Meeting {meeting_id[:8]}"
        if date is None:
            date = datetime.now().strftime("%B %d, %Y")

        result = {"meeting_id": meeting_id}

        # ── Step 2: Generate PDF ──
        pdf_path = str(STORAGE_DIR / meeting_id / "Meeting_Summary.pdf")
        try:
            self.generate_pdf(
                summary_data, pdf_path,
                meeting_title=meeting_title, date=date,
            )
            result["pdf"] = {
                "success": True,
                "path": pdf_path,
                "message": "PDF generated successfully",
            }
        except Exception as e:
            logger.error("PDF generation failed: %s", e)
            result["pdf"] = {"success": False, "message": str(e)}
            return result  # Can't proceed without PDF

        # ── Step 3: Send Email (optional) ──
        if email_recipients:
            result["email"] = self.send_email(
                pdf_path, meeting_title, email_recipients
            )
        else:
            result["email"] = {
                "success": False,
                "message": "No recipients provided (skipped)",
            }

        # ── Step 4: Send to Teams (optional) ──
        if teams_webhook_url or os.getenv("TEAMS_WEBHOOK_URL"):
            result["teams"] = self.send_to_teams(
                summary_data, meeting_title, date,
                webhook_url=teams_webhook_url,
            )
        else:
            result["teams"] = {
                "success": False,
                "message": "No webhook URL configured (skipped)",
            }

        return result
