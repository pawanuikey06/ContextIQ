"""
Jira integration API — push action items to Jira as tickets.
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.jira_service import (
    is_configured,
    get_config_status,
    create_ticket,
    create_tickets_batch,
    sync_tickets,
    update_ticket,
)

logger = logging.getLogger(__name__)
router = APIRouter()
STORAGE_DIR = Path("storage")


class JiraPushRequest(BaseModel):
    """Request to push specific action items (by index) to Jira."""
    indices: Optional[List[int]] = None   # None = push all


@router.get("/jira/status")
async def jira_status():
    """Check if Jira integration is configured."""
    return get_config_status()


@router.post("/meeting/{meeting_id}/jira/push")
async def push_to_jira(meeting_id: str, body: JiraPushRequest = JiraPushRequest()):
    """
    Push action items from a meeting to Jira as tickets.
    If indices are provided, only those action items are pushed.
    Otherwise, all action items are pushed.
    """
    if not is_configured():
        raise HTTPException(
            status_code=400,
            detail="Jira is not configured. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY in .env"
        )

    # Load action items from cache
    ai_path = STORAGE_DIR / meeting_id / "action_items.json"
    if not ai_path.exists():
        raise HTTPException(status_code=404, detail="No action items found. Extract action items first.")

    with open(ai_path, "r", encoding="utf-8") as f:
        action_data = json.load(f)

    items = action_data.get("action_items", [])
    if not items:
        raise HTTPException(status_code=404, detail="No action items to push.")

    # Load meeting title — prefer auto_title (AI-generated) over generic title
    meeting_title = f"Meeting {meeting_id[:8]}"
    meta_path = STORAGE_DIR / meeting_id / "metadata.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            meeting_title = meta.get("auto_title", meta.get("title", meeting_title))

    # Filter by indices if specified
    if body.indices is not None:
        selected = []
        for idx in body.indices:
            if 0 <= idx < len(items):
                selected.append(items[idx])
        if not selected:
            raise HTTPException(status_code=400, detail="No valid action item indices provided.")
        items_to_push = selected
    else:
        items_to_push = items

    # Push to Jira
    result = create_tickets_batch(items_to_push, meeting_title)

    # Save Jira IDs back into action_items using index matching (not text matching)
    if result["created"] > 0:
        # Build a map: original item index → ticket result
        selected_indices = body.indices if body.indices is not None else list(range(len(items)))
        valid_indices = [i for i in selected_indices if 0 <= i < len(items)]
        ticket_list = result.get("tickets", [])
        for orig_idx, ticket_info in zip(valid_indices, ticket_list):
            if ticket_info.get("success") and ticket_info.get("key"):
                action_data["action_items"][orig_idx]["jira_id"] = ticket_info["key"]
                action_data["action_items"][orig_idx]["jira_url"] = ticket_info.get("url", "")

        # Save updated action items back
        with open(ai_path, "w", encoding="utf-8") as f:
            json.dump(action_data, f, indent=2, ensure_ascii=False)

    logger.info(
        "[%s] Jira push: %d created, %d failed",
        meeting_id, result["created"], result["failed"]
    )

    return result


@router.post("/meeting/{meeting_id}/jira/sync")
async def sync_from_jira(meeting_id: str):
    """
    Sync action item statuses from Jira back to ContextIQ.
    Fetches current status, priority, and assignee for all items with Jira IDs.
    """
    if not is_configured():
        raise HTTPException(status_code=400, detail="Jira is not configured.")

    ai_path = STORAGE_DIR / meeting_id / "action_items.json"
    if not ai_path.exists():
        raise HTTPException(status_code=404, detail="No action items found.")

    with open(ai_path, "r", encoding="utf-8") as f:
        action_data = json.load(f)

    items = action_data.get("action_items", [])
    jira_items = [i for i in items if i.get("jira_id")]

    if not jira_items:
        return {"synced": 0, "message": "No items linked to Jira."}

    # Pass only items that have Jira IDs — avoids wasted API calls
    result = sync_tickets(jira_items)

    # Merge synced data back into full action_data list
    jira_map = {item["jira_id"]: item for item in jira_items if item.get("jira_id")}
    for item in action_data.get("action_items", []):
        jid = item.get("jira_id")
        if jid and jid in jira_map:
            item.update(jira_map[jid])

    # Save updated data back
    with open(ai_path, "w", encoding="utf-8") as f:
        json.dump(action_data, f, indent=2, ensure_ascii=False)

    logger.info(
        "[%s] Jira sync: %d synced, %d changes",
        meeting_id, result["synced"], len(result["changes"])
    )

    return result


class JiraUpdateRequest(BaseModel):
    """Request to update a Jira ticket from ContextIQ."""
    index: int


@router.put("/meeting/{meeting_id}/jira/update")
async def update_jira_ticket(meeting_id: str, body: JiraUpdateRequest):
    """
    Update a Jira ticket when an action item is edited in ContextIQ.
    Pushes status, priority, and task summary changes to Jira.
    """
    if not is_configured():
        raise HTTPException(status_code=400, detail="Jira is not configured.")

    ai_path = STORAGE_DIR / meeting_id / "action_items.json"
    if not ai_path.exists():
        raise HTTPException(status_code=404, detail="No action items found.")

    with open(ai_path, "r", encoding="utf-8") as f:
        action_data = json.load(f)

    items = action_data.get("action_items", [])
    if body.index < 0 or body.index >= len(items):
        raise HTTPException(status_code=400, detail="Invalid action item index.")

    item = items[body.index]
    jira_id = item.get("jira_id", "")
    if not jira_id:
        raise HTTPException(status_code=400, detail="This action item has no linked Jira ticket.")

    result = update_ticket(jira_id, item)

    logger.info(
        "[%s] Jira update %s: %s",
        meeting_id, jira_id, result.get("updated_fields", [])
    )

    return result
