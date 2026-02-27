"""
Confluence Integration Service
================================
Pushes meeting data to Confluence as a wiki page using the
Confluence REST API with Storage Format (XHTML).
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


def _get_config():
    return {
        "url": os.getenv("CONFLUENCE_URL", ""),
        "email": os.getenv("CONFLUENCE_EMAIL", ""),
        "token": os.getenv("CONFLUENCE_API_TOKEN", ""),
        "space_key": os.getenv("CONFLUENCE_SPACE_KEY", ""),
    }


def _load_meeting_data(meeting_id: str) -> dict:
    base = STORAGE_DIR / meeting_id
    data = {}
    for name in ["metadata", "summary", "action_items", "speaker_map",
                  "sentiment", "topics"]:
        path = base / f"{name}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data[name] = json.load(f)
    return data


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _build_page_body(data: dict, meeting_id: str) -> str:
    """Build Confluence Storage Format (XHTML) body."""
    meta = data.get("metadata", {})
    summary = data.get("summary", {})
    actions = data.get("action_items", {})
    speaker_map = data.get("speaker_map", {})
    sentiment = data.get("sentiment", {})
    topics = data.get("topics", {})

    html = []

    # — Meeting Info —
    date_str = meta.get("processed_date", "Unknown")
    day_str = meta.get("processed_day", "")
    time_str = meta.get("processed_time", "")
    speakers = list(speaker_map.values()) if speaker_map else []

    html.append('<ac:structured-macro ac:name="info"><ac:rich-text-body>')
    html.append(f'<p><strong>Date:</strong> {_escape(date_str)}, {_escape(day_str)} {_escape(time_str)}</p>')
    if speakers:
        html.append(f'<p><strong>Speakers:</strong> {_escape(", ".join(speakers))}</p>')
    html.append('</ac:rich-text-body></ac:structured-macro>')

    # — Overall Summary —
    if summary.get("overall_summary_en"):
        html.append('<h2>Overall Summary (English)</h2>')
        html.append(f'<p>{_escape(summary["overall_summary_en"])}</p>')

    if summary.get("overall_summary_hi"):
        html.append('<h2>Overall Summary (Hindi)</h2>')
        html.append(f'<p>{_escape(summary["overall_summary_hi"])}</p>')

    # — Speaker Summaries —
    speaker_sums = summary.get("speaker_summaries_en", {})
    if speaker_sums:
        html.append('<h2>Speaker Summaries</h2>')
        for spk, text in speaker_sums.items():
            label = speaker_map.get(spk, spk)
            html.append(f'<h3>{_escape(label)}</h3>')
            html.append(f'<p>{_escape(text)}</p>')

    # — Action Items as Table —
    items = actions.get("action_items", actions) if isinstance(actions, dict) else actions
    if isinstance(items, list) and items:
        html.append('<h2>Action Items</h2>')
        html.append('<table><thead><tr>')
        html.append('<th>Task</th><th>Assignee</th><th>Deadline</th><th>Priority</th>')
        html.append('</tr></thead><tbody>')
        for item in items:
            if isinstance(item, dict):
                task = _escape(item.get("task", item.get("action", str(item))))
                assignee = _escape(item.get("assignee", "—"))
                deadline = _escape(item.get("deadline", "—"))
                priority = _escape(item.get("priority", "—"))
                html.append(f'<tr><td>{task}</td><td>{assignee}</td><td>{deadline}</td><td>{priority}</td></tr>')
        html.append('</tbody></table>')

    # — Topics —
    topic_list = topics.get("topics", []) if isinstance(topics, dict) else []
    if topic_list:
        html.append('<h2>Topics Discussed</h2>')
        html.append('<ul>')
        for t in topic_list:
            name = t.get("topic", t.get("name", str(t))) if isinstance(t, dict) else str(t)
            html.append(f'<li>{_escape(name)}</li>')
        html.append('</ul>')

    # — Sentiment —
    if sentiment:
        overall = sentiment.get("overall_sentiment", "")
        if overall:
            emoji = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(overall, "😐")
            html.append('<h2>Sentiment Analysis</h2>')
            html.append(f'<p>{emoji} Overall: <strong>{_escape(overall.title())}</strong></p>')
            summary_text = sentiment.get("summary", "")
            if summary_text:
                html.append(f'<p>{_escape(summary_text)}</p>')

    # — Jira Links —
    jira_path = STORAGE_DIR / meeting_id / "jira_tickets.json"
    if jira_path.exists():
        with open(jira_path, "r", encoding="utf-8") as f:
            jira_data = json.load(f)
        tickets = jira_data if isinstance(jira_data, list) else jira_data.get("tickets", [])
        if tickets:
            html.append('<h2>Linked Jira Tickets</h2>')
            html.append('<ul>')
            for t in tickets:
                if isinstance(t, dict):
                    key = t.get("key", "")
                    url = t.get("url", t.get("self", ""))
                    summary_t = _escape(t.get("summary", key))
                    if url:
                        html.append(f'<li><a href="{_escape(url)}">{_escape(key)}</a> — {summary_t}</li>')
                    else:
                        html.append(f'<li>{_escape(key)} — {summary_t}</li>')
            html.append('</ul>')

    return "\n".join(html)


# — Public API —

def check_status() -> dict:
    """Check Confluence API connectivity."""
    cfg = _get_config()
    if not cfg["url"] or not cfg["email"] or not cfg["token"]:
        return {"connected": False, "message": "Confluence credentials not set in .env (CONFLUENCE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN)"}
    try:
        r = requests.get(
            f"{cfg['url']}/rest/api/space/{cfg['space_key']}",
            auth=(cfg["email"], cfg["token"]),
            timeout=10,
        )
        if r.status_code == 200:
            space = r.json()
            return {"connected": True, "space_name": space.get("name", cfg["space_key"])}
        else:
            return {"connected": False, "message": f"API error: {r.status_code}"}
    except Exception as e:
        return {"connected": False, "message": str(e)}


def push_meeting(meeting_id: str) -> dict:
    """Push meeting data to Confluence as a new wiki page."""
    cfg = _get_config()
    if not cfg["url"] or not cfg["email"] or not cfg["token"] or not cfg["space_key"]:
        raise ValueError("Confluence credentials not fully configured in .env")

    data = _load_meeting_data(meeting_id)
    if not data:
        raise FileNotFoundError(f"No data found for meeting {meeting_id}")

    meta = data.get("metadata", {})
    title = meta.get("auto_title", meta.get("title", f"Meeting {meeting_id[:8]}"))
    date_str = meta.get("processed_date", "")
    page_title = f"{title} — {date_str}" if date_str else title

    body = _build_page_body(data, meeting_id)

    payload = {
        "type": "page",
        "title": page_title,
        "space": {"key": cfg["space_key"]},
        "body": {
            "storage": {
                "value": body,
                "representation": "storage",
            }
        },
    }

    r = requests.post(
        f"{cfg['url']}/rest/api/content",
        auth=(cfg["email"], cfg["token"]),
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if r.status_code in (200, 201):
        page = r.json()
        page_url = f"{cfg['url']}/wiki/spaces/{cfg['space_key']}/pages/{page.get('id', '')}"
        # Try to build the proper URL
        _links = page.get("_links", {})
        if _links.get("webui"):
            page_url = cfg["url"] + _links["webui"]

        logger.info("[%s] Pushed to Confluence: %s", meeting_id, page_url)
        return {
            "success": True,
            "page_url": page_url,
            "page_id": page.get("id", ""),
            "title": page_title,
        }
    else:
        error_msg = r.text[:300]
        logger.error("[%s] Confluence push failed: %s", meeting_id, error_msg)
        raise RuntimeError(f"Confluence API error ({r.status_code}): {error_msg}")
