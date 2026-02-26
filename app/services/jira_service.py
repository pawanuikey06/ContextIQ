"""
Jira Integration Service — creates Jira tickets from ContextIQ action items.
Uses Jira REST API v3 with Basic Auth (email + API token).
"""
import os
import logging
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")        # e.g. https://yourorg.atlassian.net
JIRA_EMAIL    = os.getenv("JIRA_EMAIL", "")            # e.g. you@company.com
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")       # Atlassian API Token
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "")   # e.g. PROJ


# Map ContextIQ priority to Jira priority names
PRIORITY_MAP = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

# Map ContextIQ category to Jira issue type
ISSUE_TYPE_MAP = {
    "development": "Story",
    "design": "Task",
    "research": "Task",
    "communication": "Task",
    "testing": "Bug",
    "documentation": "Task",
    "infrastructure": "Task",
    "other": "Task",
}


def is_configured() -> bool:
    """Return True if Jira credentials are fully configured."""
    return bool(JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN and JIRA_PROJECT_KEY)


def get_config_status() -> dict:
    """Return current Jira configuration status (without exposing secrets)."""
    return {
        "configured": is_configured(),
        "base_url": JIRA_BASE_URL or None,
        "email": JIRA_EMAIL or None,
        "project_key": JIRA_PROJECT_KEY or None,
    }


def _auth() -> HTTPBasicAuth:
    return HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)


def _headers() -> dict:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def create_ticket(action_item: dict, meeting_title: str = "") -> dict:
    """
    Create a single Jira ticket from a ContextIQ action item.

    Returns dict with 'success', 'key', 'url', or 'error'.
    """
    if not is_configured():
        return {"success": False, "error": "Jira is not configured. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY in .env"}

    task_desc = action_item.get("task", "Untitled")
    assigned_to = action_item.get("assigned_to", "Unassigned")
    priority = action_item.get("priority", "medium")
    category = action_item.get("category", "other")
    context = action_item.get("context", "")
    success_criteria = action_item.get("success_criteria", "")
    dependencies = action_item.get("dependencies", [])
    deadline = action_item.get("deadline", "")
    mentioned_by = action_item.get("mentioned_by", "")

    # Build rich description
    desc_parts = []
    if meeting_title:
        desc_parts.append(f"*Source Meeting:* {meeting_title}")
    if context:
        desc_parts.append(f"*Context:* {context}")
    if success_criteria:
        desc_parts.append(f"*Acceptance Criteria:* {success_criteria}")
    if dependencies:
        desc_parts.append(f"*Dependencies:* {', '.join(dependencies)}")
    if deadline and deadline != "Not specified":
        desc_parts.append(f"*Deadline:* {deadline}")
    if mentioned_by:
        desc_parts.append(f"*Raised by:* {mentioned_by}")
    if assigned_to and assigned_to != "Unassigned":
        desc_parts.append(f"*Assigned to:* {assigned_to}")

    desc_parts.append("\n_Created automatically by ContextIQ Meeting Intelligence_")

    description_text = "\n\n".join(desc_parts)

    # Build Jira payload (v3 ADF format)
    fields = {
        "project": {"key": JIRA_PROJECT_KEY},
        "summary": task_desc[:255],  # Jira limits summary to 255 chars
        "issuetype": {"name": ISSUE_TYPE_MAP.get(category, "Task")},
        "priority": {"name": PRIORITY_MAP.get(priority.lower(), "Medium")},
        "description": {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": line}]
                }
                for line in description_text.split("\n") if line.strip()
            ]
        },
        "labels": ["contextiq", f"category-{category}"],
    }

    # Add due date if deadline is available
    if deadline and deadline.lower() not in ("not specified", ""):
        import re
        from datetime import datetime
        if re.match(r"^\d{4}-\d{2}-\d{2}$", deadline):
            fields["duedate"] = deadline
        else:
            try:
                dt = datetime.strptime(deadline, "%b %d, %Y")
                fields["duedate"] = dt.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    dt = datetime.fromisoformat(deadline.split("T")[0])
                    fields["duedate"] = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass

    payload = {"fields": fields}

    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"

    try:
        resp = requests.post(url, json=payload, auth=_auth(), headers=_headers(), timeout=15)

        if resp.status_code in (200, 201):
            data = resp.json()
            ticket_key = data.get("key", "")
            ticket_url = f"{JIRA_BASE_URL.rstrip('/')}/browse/{ticket_key}"
            logger.info("Created Jira ticket: %s", ticket_key)
            return {
                "success": True,
                "key": ticket_key,
                "url": ticket_url,
                "id": data.get("id", ""),
            }
        else:
            error_msg = resp.text[:300]
            logger.error("Jira API error %d: %s", resp.status_code, error_msg)
            return {"success": False, "error": f"Jira API returned {resp.status_code}: {error_msg}"}

    except requests.RequestException as e:
        logger.error("Jira request failed: %s", str(e))
        return {"success": False, "error": f"Connection error: {str(e)}"}


def create_tickets_batch(action_items: list, meeting_title: str = "") -> dict:
    """
    Create Jira tickets for multiple action items.
    Returns summary with created tickets and any failures.
    """
    results = []
    created = 0
    failed = 0

    for item in action_items:
        result = create_ticket(item, meeting_title)
        result["task"] = item.get("task", "")[:80]
        results.append(result)
        if result["success"]:
            created += 1
        else:
            failed += 1

    return {
        "total": len(action_items),
        "created": created,
        "failed": failed,
        "tickets": results,
    }


def update_ticket(ticket_key: str, action_item: dict) -> dict:
    """
    Update a Jira ticket from ContextIQ changes (status, priority, summary).
    Status changes use Jira transitions API, others use PUT.
    """
    if not is_configured():
        return {"success": False, "error": "Jira not configured"}

    base = JIRA_BASE_URL.rstrip("/")
    updated_fields = []

    # --- Update priority, summary, and deadline via PUT ---
    fields_payload = {}
    priority = action_item.get("priority", "")
    if priority:
        jira_priority = PRIORITY_MAP.get(priority.lower(), "Medium")
        fields_payload["priority"] = {"name": jira_priority}

    task = action_item.get("task", "")
    if task:
        fields_payload["summary"] = task[:255]

    deadline = action_item.get("deadline", "")
    if deadline and deadline.lower() not in ("not specified", ""):
        # Try to parse to YYYY-MM-DD for Jira duedate
        import re
        from datetime import datetime
        if re.match(r"^\d{4}-\d{2}-\d{2}$", deadline):
            fields_payload["duedate"] = deadline
        else:
            try:
                dt = datetime.strptime(deadline, "%b %d, %Y")
                fields_payload["duedate"] = dt.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    dt = datetime.fromisoformat(deadline.split("T")[0])
                    fields_payload["duedate"] = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass  # Can't parse, skip

    if fields_payload:
        try:
            resp = requests.put(
                f"{base}/rest/api/3/issue/{ticket_key}",
                json={"fields": fields_payload},
                auth=_auth(), headers=_headers(), timeout=10,
            )
            if resp.ok or resp.status_code == 204:
                updated_fields.extend(list(fields_payload.keys()))
            else:
                logger.warning("Jira field update failed for %s: %s", ticket_key, resp.text[:200])
        except requests.RequestException as e:
            logger.error("Jira update request failed: %s", str(e))

    # --- Update status via transitions API ---
    status = action_item.get("status", "")
    if status:
        # Map ContextIQ status to target Jira status names
        target_statuses = {
            "To Do": ["to do", "backlog", "open"],
            "In Progress": ["in progress", "in development"],
            "In Review": ["in review", "review"],
            "Done": ["done", "closed", "resolved"],
        }
        targets = target_statuses.get(status, [status.lower()])

        try:
            # Get available transitions
            tr_resp = requests.get(
                f"{base}/rest/api/3/issue/{ticket_key}/transitions",
                auth=_auth(), headers=_headers(), timeout=10,
            )
            if tr_resp.ok:
                transitions = tr_resp.json().get("transitions", [])
                # Find matching transition
                target_transition = None
                for t in transitions:
                    if t.get("name", "").lower() in targets or t.get("to", {}).get("name", "").lower() in targets:
                        target_transition = t
                        break

                if target_transition:
                    exec_resp = requests.post(
                        f"{base}/rest/api/3/issue/{ticket_key}/transitions",
                        json={"transition": {"id": target_transition["id"]}},
                        auth=_auth(), headers=_headers(), timeout=10,
                    )
                    if exec_resp.ok or exec_resp.status_code == 204:
                        updated_fields.append("status")
                        logger.info("Transitioned %s to %s", ticket_key, target_transition["name"])
                    else:
                        logger.warning("Transition failed for %s: %s", ticket_key, exec_resp.text[:200])
                else:
                    logger.info("No matching transition for %s → %s (available: %s)",
                               ticket_key, status, [t["name"] for t in transitions])
        except requests.RequestException as e:
            logger.error("Jira transition request failed: %s", str(e))

    return {
        "success": len(updated_fields) > 0 or bool(status),
        "key": ticket_key,
        "updated_fields": updated_fields,
        "message": f"Updated: {', '.join(updated_fields)}" if updated_fields else "No changes needed or no matching transition found",
    }


# Map Jira status categories back to ContextIQ status
JIRA_STATUS_MAP = {
    # Jira status name → ContextIQ status
    "to do": "To Do",
    "backlog": "To Do",
    "selected for development": "To Do",
    "in progress": "In Progress",
    "in development": "In Progress",
    "in review": "In Review",
    "review": "In Review",
    "done": "Done",
    "closed": "Done",
    "resolved": "Done",
}

# Reverse priority map
JIRA_PRIORITY_REVERSE = {
    "highest": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "lowest": "low",
}


def fetch_ticket_status(ticket_key: str) -> dict:
    """
    Fetch current status, priority, and assignee of a Jira ticket.
    Returns dict with 'status', 'priority', 'assignee', 'jira_url'.
    """
    if not is_configured():
        return {"success": False, "error": "Jira not configured"}

    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue/{ticket_key}?fields=status,priority,assignee,summary"

    try:
        resp = requests.get(url, auth=_auth(), headers=_headers(), timeout=10)
        if resp.ok:
            data = resp.json()
            fields = data.get("fields", {})

            jira_status = fields.get("status", {}).get("name", "To Do")
            jira_priority = fields.get("priority", {}).get("name", "Medium")
            assignee_data = fields.get("assignee")
            jira_assignee = assignee_data.get("displayName", "") if assignee_data else ""

            return {
                "success": True,
                "key": ticket_key,
                "status": JIRA_STATUS_MAP.get(jira_status.lower(), jira_status),
                "priority": JIRA_PRIORITY_REVERSE.get(jira_priority.lower(), "medium"),
                "assignee": jira_assignee,
                "jira_status_raw": jira_status,
                "jira_url": f"{JIRA_BASE_URL.rstrip('/')}/browse/{ticket_key}",
            }
        else:
            return {"success": False, "key": ticket_key, "error": f"HTTP {resp.status_code}"}
    except requests.RequestException as e:
        return {"success": False, "key": ticket_key, "error": str(e)}


def sync_tickets(action_items: list) -> dict:
    """
    Sync status of all action items that have Jira IDs.
    Updates each item in-place and returns sync summary.
    """
    synced = 0
    failed = 0
    changes = []

    for item in action_items:
        jira_id = item.get("jira_id", "")
        if not jira_id:
            continue

        result = fetch_ticket_status(jira_id)
        if result.get("success"):
            old_status = item.get("status", "To Do")
            new_status = result["status"]
            new_priority = result["priority"]
            new_assignee = result.get("assignee", "")

            changed_fields = []
            if old_status != new_status:
                changed_fields.append(f"status: {old_status} → {new_status}")
                item["status"] = new_status
            if new_priority and item.get("priority", "").lower() != new_priority:
                changed_fields.append(f"priority: {item.get('priority')} → {new_priority}")
                item["priority"] = new_priority
            if new_assignee and item.get("assigned_to") != new_assignee:
                changed_fields.append(f"assignee: {item.get('assigned_to')} → {new_assignee}")
                item["assigned_to"] = new_assignee

            synced += 1
            if changed_fields:
                changes.append({"key": jira_id, "changes": changed_fields})
        else:
            failed += 1

    return {
        "synced": synced,
        "failed": failed,
        "changes": changes,
        "total_with_jira": synced + failed,
    }

