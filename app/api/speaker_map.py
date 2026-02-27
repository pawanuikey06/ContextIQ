"""
POST/GET /meeting/{meeting_id}/speaker-map
Save and retrieve speaker name mappings (HITL feature).
After saving, automatically regenerates ALL AI insights in the background
using the real speaker names (summary, action items, requirements, docs, email, RAG).
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict

logger = logging.getLogger(__name__)
router = APIRouter()

STORAGE_DIR = Path("storage")


class SpeakerMapRequest(BaseModel):
    """Maps detected speaker IDs to real names."""
    speaker_map: Dict[str, str]  # e.g. {"SPEAKER_00": "Pawan", "SPEAKER_01": "Ravi"}


def _regenerate_all_insights(meeting_id: str):
    """
    Background task: re-run ALL AI insights + RAG index with mapped speaker names.
    Runs force=True so cached results are discarded and rebuilt with real names.
    """
    logger.info("[%s] 🔄 Background regeneration started with mapped speaker names", meeting_id)

    transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
    if not transcript_path.exists():
        logger.warning("[%s] Transcript not found, skipping regeneration", meeting_id)
        return

    # ── 1. Re-index RAG (uses speaker_map for chunk content) ──
    try:
        from app.api.chat import _get_rag_service
        rag = _get_rag_service()
        count = rag.ingest_meeting(meeting_id)
        logger.info("[%s] ✅ RAG re-indexed: %d chunks with mapped names", meeting_id, count)
    except Exception as e:
        logger.warning("[%s] RAG re-index failed: %s", meeting_id, e)

    # ── 2. Re-generate Summary (force=True → rebuilds with mapped names) ──
    try:
        from app.services.summary_service import MeetingSummaryService
        svc = MeetingSummaryService()
        svc.summarize(meeting_id, force=True)
        logger.info("[%s] ✅ Summary regenerated with mapped names", meeting_id)
    except Exception as e:
        logger.warning("[%s] Summary regeneration failed: %s", meeting_id, e)

    # ── 3. Re-extract Action Items + Decisions (preserve Jira links!) ──
    try:
        from app.services.insights_service import MeetingInsightsService
        insights = MeetingInsightsService()

        # Save existing Jira links BEFORE regeneration
        ai_path = STORAGE_DIR / meeting_id / "action_items.json"
        old_jira_data = []
        if ai_path.exists():
            import json as _json
            with open(ai_path, "r", encoding="utf-8") as f:
                old_data = _json.load(f)
            for item in old_data.get("action_items", []):
                if item.get("jira_id"):
                    old_jira_data.append({
                        "task": item.get("task", ""),
                        "jira_id": item["jira_id"],
                        "jira_url": item.get("jira_url", ""),
                        "status": item.get("status", "To Do"),
                    })

        # Regenerate with real names
        insights.extract_action_items(meeting_id, force=True)

        # Merge Jira links back into regenerated items
        if old_jira_data and ai_path.exists():
            import json as _json
            with open(ai_path, "r", encoding="utf-8") as f:
                new_data = _json.load(f)
            new_items = new_data.get("action_items", [])

            for old in old_jira_data:
                best_match = None
                best_score = 0
                old_words = set(old["task"].lower().split())
                for new_item in new_items:
                    if new_item.get("jira_id"):
                        continue  # already has a link
                    new_words = set(new_item.get("task", "").lower().split())
                    if not old_words or not new_words:
                        continue
                    overlap = len(old_words & new_words) / max(len(old_words), len(new_words))
                    if overlap > best_score and overlap >= 0.4:
                        best_score = overlap
                        best_match = new_item

                if best_match:
                    best_match["jira_id"] = old["jira_id"]
                    best_match["jira_url"] = old["jira_url"]
                    if old.get("status"):
                        best_match["status"] = old["status"]

            with open(ai_path, "w", encoding="utf-8") as f:
                _json.dump(new_data, f, indent=2, ensure_ascii=False)

        logger.info("[%s] ✅ Action items regenerated with mapped names (Jira links preserved)", meeting_id)
    except Exception as e:
        logger.warning("[%s] Action items regeneration failed: %s", meeting_id, e)

    # ── 4. Re-extract Requirements ──
    try:
        from app.services.insights_service import MeetingInsightsService
        insights = MeetingInsightsService()
        insights.extract_requirements(meeting_id, force=True)
        logger.info("[%s] ✅ Requirements regenerated with mapped names", meeting_id)
    except Exception as e:
        logger.warning("[%s] Requirements regeneration failed: %s", meeting_id, e)

    # ── 5. Re-generate Documentation ──
    try:
        from app.services.insights_service import MeetingInsightsService
        insights = MeetingInsightsService()
        insights.generate_documentation(meeting_id, force=True)
        logger.info("[%s] ✅ Documentation regenerated with mapped names", meeting_id)
    except Exception as e:
        logger.warning("[%s] Documentation regeneration failed: %s", meeting_id, e)

    # ── 6. Re-generate Follow-up Email ──
    try:
        from app.services.insights_service import MeetingInsightsService
        insights = MeetingInsightsService()
        insights.generate_followup_email(meeting_id, force=True)
        logger.info("[%s] ✅ Follow-up email regenerated with mapped names", meeting_id)
    except Exception as e:
        logger.warning("[%s] Follow-up email regeneration failed: %s", meeting_id, e)

    # ── 7. Re-run Sentiment Analysis ──
    try:
        from app.services.insights_service import MeetingInsightsService
        insights = MeetingInsightsService()
        insights.analyze_sentiment(meeting_id, force=True)
        logger.info("[%s] ✅ Sentiment analysis regenerated with mapped names", meeting_id)
    except Exception as e:
        logger.warning("[%s] Sentiment regeneration failed: %s", meeting_id, e)

    # ── 8. Re-extract Topic Segments ──
    try:
        from app.services.insights_service import MeetingInsightsService
        insights = MeetingInsightsService()
        insights.extract_topics(meeting_id, force=True)
        logger.info("[%s] ✅ Topics regenerated with mapped names", meeting_id)
    except Exception as e:
        logger.warning("[%s] Topics regeneration failed: %s", meeting_id, e)

    logger.info("[%s] 🎉 Background regeneration complete — all insights updated with real speaker names", meeting_id)


@router.post("/meeting/{meeting_id}/speaker-map")
async def save_speaker_map(
    meeting_id: str,
    body: SpeakerMapRequest,
    background_tasks: BackgroundTasks,
):
    """
    Save speaker name mappings to disk.
    Automatically triggers background regeneration of ALL AI insights
    (summary, action items, requirements, docs, email, sentiment, RAG index)
    using the mapped names. Returns immediately — regeneration runs in background.
    """
    meeting_dir = STORAGE_DIR / meeting_id
    if not meeting_dir.exists():
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

    map_path = meeting_dir / "speaker_map.json"
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(body.speaker_map, f, indent=2, ensure_ascii=False)

    logger.info("[%s] Speaker map saved: %s", meeting_id, body.speaker_map)

    # Queue background regeneration of all insights
    background_tasks.add_task(_regenerate_all_insights, meeting_id)

    return {
        "success": True,
        "speaker_map": body.speaker_map,
        "regenerating": True,
        "message": "Speaker names saved. All insights are being regenerated in the background with the mapped names.",
    }


@router.get("/meeting/{meeting_id}/speaker-map")
async def get_speaker_map(meeting_id: str):
    """Load saved speaker name mappings."""
    map_path = STORAGE_DIR / meeting_id / "speaker_map.json"
    if not map_path.exists():
        return {"speaker_map": {}}

    with open(map_path, "r", encoding="utf-8") as f:
        return {"speaker_map": json.load(f)}
