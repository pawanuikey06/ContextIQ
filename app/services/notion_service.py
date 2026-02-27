"""
Notion Integration Service
===========================
Pushes meeting data (summary, action items, speakers, topics, sentiment)
to a Notion database page via the Notion API.
"""
import os
import json
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

STORAGE_DIR = Path("storage")

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_config():
    api_key = os.getenv("NOTION_API_KEY", "")
    database_id = os.getenv("NOTION_DATABASE_ID", "")
    return api_key, database_id


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _load_meeting_data(meeting_id: str) -> dict:
    """Load all available meeting JSON files."""
    base = STORAGE_DIR / meeting_id
    data = {}

    for name in ["metadata", "summary", "action_items", "speaker_map",
                  "sentiment", "topics"]:
        path = base / f"{name}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data[name] = json.load(f)
    return data


def _build_blocks(data: dict, meeting_id: str) -> list:
    """Build Notion block children from meeting data."""
    blocks = []
    meta = data.get("metadata", {})
    summary = data.get("summary", {})
    actions = data.get("action_items", {})
    speaker_map = data.get("speaker_map", {})
    sentiment = data.get("sentiment", {})
    topics = data.get("topics", {})

    # — Meeting Info —
    date_str = meta.get("processed_date", "Unknown")
    day_str = meta.get("processed_day", "")
    time_str = meta.get("processed_time", "")
    blocks.append(_heading2("Meeting Information"))
    blocks.append(_paragraph(f"📅 Date: {date_str}, {day_str} {time_str}"))

    speakers = list(speaker_map.values()) if speaker_map else []
    if speakers:
        blocks.append(_paragraph(f"👥 Speakers: {', '.join(speakers)}"))

    # — Overall Summary —
    if summary.get("overall_summary_en"):
        blocks.append(_divider())
        blocks.append(_heading2("Overall Summary (English)"))
        blocks.append(_paragraph(summary["overall_summary_en"]))

    if summary.get("overall_summary_hi"):
        blocks.append(_heading2("Overall Summary (Hindi)"))
        blocks.append(_paragraph(summary["overall_summary_hi"]))

    # — Speaker Summaries —
    speaker_sums = summary.get("speaker_summaries_en", {})
    if speaker_sums:
        blocks.append(_divider())
        blocks.append(_heading2("Speaker Summaries"))
        for spk, text in speaker_sums.items():
            label = speaker_map.get(spk, spk)
            blocks.append(_heading3(label))
            blocks.append(_paragraph(text))

    # — Action Items —
    items = actions.get("action_items", actions) if isinstance(actions, dict) else actions
    if isinstance(items, list) and items:
        blocks.append(_divider())
        blocks.append(_heading2("Action Items"))
        for item in items:
            if isinstance(item, dict):
                text = item.get("task", item.get("action", str(item)))
                assignee = item.get("assignee", "")
                deadline = item.get("deadline", "")
                priority = item.get("priority", "")
                line = f"{text}"
                if assignee:
                    line += f" — 👤 {assignee}"
                if deadline:
                    line += f" | 📅 {deadline}"
                if priority:
                    line += f" | ⚡ {priority}"
                blocks.append(_todo(line))
            else:
                blocks.append(_todo(str(item)))

    # — Topics —
    topic_list = topics.get("topics", []) if isinstance(topics, dict) else []
    if topic_list:
        blocks.append(_divider())
        blocks.append(_heading2("Topics Discussed"))
        for t in topic_list:
            if isinstance(t, dict):
                blocks.append(_bulleted(t.get("topic", t.get("name", str(t)))))
            else:
                blocks.append(_bulleted(str(t)))

    # — Sentiment —
    if sentiment:
        overall = sentiment.get("overall_sentiment", "")
        if overall:
            blocks.append(_divider())
            blocks.append(_heading2("Sentiment Analysis"))
            emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(overall, "😐")
            blocks.append(_paragraph(f"Overall Sentiment: {emoji} {overall.title()}"))
            summary_text = sentiment.get("summary", "")
            if summary_text:
                blocks.append(_paragraph(summary_text))

    return blocks


# — Notion Block Builders —

def _heading2(text: str) -> dict:
    return {"object": "block", "type": "heading_2", "heading_2": {
        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
    }}


def _heading3(text: str) -> dict:
    return {"object": "block", "type": "heading_3", "heading_3": {
        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
    }}


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {
        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
    }}


def _todo(text: str, checked=False) -> dict:
    return {"object": "block", "type": "to_do", "to_do": {
        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        "checked": checked,
    }}


def _bulleted(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {
        "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
    }}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


# — Public API —

def check_status() -> dict:
    """Check Notion API connectivity."""
    api_key, db_id = _get_config()
    if not api_key or not db_id:
        return {"connected": False, "message": "NOTION_API_KEY or NOTION_DATABASE_ID not set in .env"}
    try:
        r = requests.get(
            f"{NOTION_API_BASE}/databases/{db_id}",
            headers=_headers(api_key),
            timeout=10,
        )
        if r.status_code == 200:
            db = r.json()
            return {"connected": True, "database_title": db.get("title", [{}])[0].get("plain_text", "Unknown")}
        else:
            return {"connected": False, "message": f"API error: {r.status_code} — {r.text[:200]}"}
    except Exception as e:
        return {"connected": False, "message": str(e)}


def push_meeting(meeting_id: str) -> dict:
    """Push a meeting's full data to Notion as a new page."""
    api_key, db_id = _get_config()
    if not api_key or not db_id:
        raise ValueError("NOTION_API_KEY or NOTION_DATABASE_ID not configured in .env")

    data = _load_meeting_data(meeting_id)
    if not data:
        raise FileNotFoundError(f"No data found for meeting {meeting_id}")

    meta = data.get("metadata", {})
    title = meta.get("auto_title", meta.get("title", f"Meeting {meeting_id[:8]}"))
    date_str = meta.get("processed_date", "")

    # Build page
    blocks = _build_blocks(data, meeting_id)

    # Notion limits 100 blocks per request
    blocks = blocks[:100]

    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "title": {
                "title": [{"text": {"content": title}}]
            },
        },
        "children": blocks,
    }

    r = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=_headers(api_key),
        json=payload,
        timeout=30,
    )

    if r.status_code in (200, 201):
        page = r.json()
        page_url = page.get("url", "")
        logger.info("[%s] Pushed to Notion: %s", meeting_id, page_url)
        return {
            "success": True,
            "page_url": page_url,
            "page_id": page.get("id", ""),
            "title": title,
        }
    else:
        error_msg = r.text[:300]
        logger.error("[%s] Notion push failed: %s", meeting_id, error_msg)
        raise RuntimeError(f"Notion API error ({r.status_code}): {error_msg}")
