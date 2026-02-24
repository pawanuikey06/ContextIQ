"""
Dashboard statistics API.
Scans storage directory for aggregate meeting stats.
"""
import json
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stats"])

STORAGE_DIR = Path("storage")


@router.get("/stats")
async def get_dashboard_stats():
    """Return aggregate stats across all meetings."""
    total_meetings = 0
    total_speakers = set()
    total_duration = 0.0
    meetings_per_day = defaultdict(int)

    if not STORAGE_DIR.exists():
        return {
            "total_meetings": 0,
            "total_speakers": 0,
            "total_duration_seconds": 0,
            "total_duration_formatted": "0:00",
            "meetings_per_day": [],
        }

    for meeting_dir in STORAGE_DIR.iterdir():
        if not meeting_dir.is_dir() or meeting_dir.name.startswith(".") or meeting_dir.name == "chroma_db":
            continue

        # Check for transcript to confirm it's a valid meeting
        transcript_path = meeting_dir / "transcript.json"
        if not transcript_path.exists():
            continue

        total_meetings += 1

        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = json.load(f)

            segments = transcript.get("segments", [])

            # Speakers
            for seg in segments:
                spk = seg.get("speaker", "UNKNOWN")
                if spk != "UNKNOWN":
                    total_speakers.add(spk)

            # Duration
            if segments:
                last_end = max(seg.get("end", 0) for seg in segments)
                total_duration += last_end

        except Exception as e:
            logger.warning("Failed to read transcript for %s: %s", meeting_dir.name, e)

        # Meeting date from metadata
        meta_path = meeting_dir / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                date_str = meta.get("uploaded_at", meta.get("created_at", ""))
                if date_str:
                    day = date_str[:10]  # YYYY-MM-DD
                    meetings_per_day[day] += 1
            except Exception:
                pass

    # Format duration
    hours = int(total_duration // 3600)
    minutes = int((total_duration % 3600) // 60)
    if hours > 0:
        formatted = f"{hours}:{minutes:02d}:{int(total_duration % 60):02d}"
    else:
        formatted = f"{minutes}:{int(total_duration % 60):02d}"

    # Sort meetings per day
    sorted_days = sorted(meetings_per_day.items())
    per_day_list = [{"date": d, "count": c} for d, c in sorted_days]

    return {
        "total_meetings": total_meetings,
        "total_speakers": len(total_speakers),
        "total_duration_seconds": round(total_duration, 1),
        "total_duration_formatted": formatted,
        "meetings_per_day": per_day_list,
    }
