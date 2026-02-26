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
    total_speakers = 0
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

            # Speakers — count unique per meeting, then sum
            meeting_speakers = set()
            for seg in segments:
                spk = seg.get("speaker", "UNKNOWN")
                if spk != "UNKNOWN":
                    meeting_speakers.add(spk)
            total_speakers += len(meeting_speakers)

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
        "total_speakers": total_speakers,
        "total_duration_seconds": round(total_duration, 1),
        "total_duration_formatted": formatted,
        "meetings_per_day": per_day_list,
    }


# ──────────────────────────────────────────────────────────────
# Meeting Culture Score — Team Health Heatmap
# ──────────────────────────────────────────────────────────────

def _compute_speaker_balance(segments: list) -> float:
    """
    Score 0–100: how evenly talk-time is distributed.
    100 = perfectly balanced, 0 = one speaker dominates completely.
    Uses Gini-like measure: 1 - (max_speaker_time / total_time).
    """
    if not segments:
        return 50.0  # neutral fallback

    speaker_time = defaultdict(float)
    for seg in segments:
        spk = seg.get("speaker", "UNKNOWN")
        duration = seg.get("end", 0) - seg.get("start", 0)
        if duration > 0:
            speaker_time[spk] += duration

    if not speaker_time:
        return 50.0

    total = sum(speaker_time.values())
    if total == 0:
        return 50.0

    num_speakers = len(speaker_time)
    if num_speakers <= 1:
        return 50.0  # single speaker — neutral, can't judge balance

    max_share = max(speaker_time.values()) / total
    # Perfect balance for N speakers = 1/N share each
    # Score: how far from "one person talks 100%" we are
    # Normalized so perfect balance = 100, one person = 0
    ideal_share = 1.0 / num_speakers
    # max_share ranges from ideal_share (best) to 1.0 (worst)
    score = (1.0 - max_share) / (1.0 - ideal_share) * 100
    return max(0, min(100, score))


def _compute_sentiment_score(sentiment_data: dict) -> float | None:
    """
    Score 0–100: % of segments with positive or neutral sentiment.
    Returns None if no sentiment data available.
    """
    segments = sentiment_data.get("segments", [])
    if not segments:
        return None

    good_count = sum(
        1 for s in segments
        if s.get("sentiment", "").lower() in ("positive", "neutral")
    )
    return (good_count / len(segments)) * 100


def _compute_completion_score(action_data: dict) -> float | None:
    """
    Score 0–100: % of action items marked 'Done'.
    Returns None if no action items exist.
    """
    items = action_data.get("action_items", [])
    if not items:
        return None

    done = sum(1 for i in items if i.get("status", "").lower() == "done")
    return (done / len(items)) * 100


def _compute_efficiency_score(segments: list, action_data: dict) -> float | None:
    """
    Score 0–100: decisions per 10 minutes of meeting.
    At least 1 decision/10min = 100. Zero decisions = 0.
    Returns None if no action items data exists.
    """
    decisions = action_data.get("decisions", [])
    if decisions is None:
        return None

    if not segments:
        return None

    duration_sec = max((seg.get("end", 0) for seg in segments), default=0)
    duration_min = duration_sec / 60
    if duration_min < 1:
        return None

    num_decisions = len(decisions)
    # Target: 1 decision per 10 minutes
    expected = duration_min / 10
    if expected == 0:
        return 50.0

    ratio = num_decisions / expected
    return max(0, min(100, ratio * 100))


@router.get("/stats/culture-score")
async def get_culture_score():
    """
    Compute Meeting Culture Score (0–100) across all meetings.
    Signals: Speaker Balance (30%), Sentiment (25%),
    Action Item Completion (25%), Meeting Efficiency (20%).
    """
    WEIGHTS = {
        "speaker_balance": 0.30,
        "sentiment": 0.25,
        "completion": 0.30,
        "efficiency": 0.15,
    }

    per_meeting = []

    if not STORAGE_DIR.exists():
        return {
            "overall_score": 0,
            "grade": "No Data",
            "signal_scores": {},
            "per_meeting": [],
            "total_scored": 0,
        }

    for meeting_dir in STORAGE_DIR.iterdir():
        if not meeting_dir.is_dir() or meeting_dir.name.startswith(".") or meeting_dir.name == "chroma_db":
            continue

        transcript_path = meeting_dir / "transcript.json"
        if not transcript_path.exists():
            continue

        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = json.load(f)
            segments = transcript.get("segments", [])
        except Exception:
            continue

        # Load optional data files
        sentiment_data = {}
        sentiment_path = meeting_dir / "sentiment.json"
        if sentiment_path.exists():
            try:
                with open(sentiment_path, "r", encoding="utf-8") as f:
                    sentiment_data = json.load(f)
            except Exception:
                pass

        action_data = {}
        action_path = meeting_dir / "action_items.json"
        if action_path.exists():
            try:
                with open(action_path, "r", encoding="utf-8") as f:
                    action_data = json.load(f)
            except Exception:
                pass

        # Compute sub-scores
        balance = _compute_speaker_balance(segments)
        sentiment = _compute_sentiment_score(sentiment_data)
        completion = _compute_completion_score(action_data)
        efficiency = _compute_efficiency_score(segments, action_data)

        # Weighted average (skip None signals)
        signals = {
            "speaker_balance": balance,
            "sentiment": sentiment,
            "completion": completion,
            "efficiency": efficiency,
        }
        total_weight = 0
        weighted_sum = 0
        for key, val in signals.items():
            if val is not None:
                weighted_sum += val * WEIGHTS[key]
                total_weight += WEIGHTS[key]

        meeting_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else None

        # Meeting metadata
        meta = {}
        meta_path = meeting_dir / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                pass

        title = meta.get("title", meta.get("auto_title", f"Meeting {meeting_dir.name[:8]}"))
        date = meta.get("uploaded_at", meta.get("created_at", ""))[:10]

        per_meeting.append({
            "meeting_id": meeting_dir.name,
            "title": title,
            "date": date,
            "score": meeting_score,
            "signals": {k: round(v, 1) if v is not None else None for k, v in signals.items()},
        })

    # Sort by date
    per_meeting.sort(key=lambda m: m["date"] or "")

    # Overall averages
    scored = [m for m in per_meeting if m["score"] is not None]
    if scored:
        overall = round(sum(m["score"] for m in scored) / len(scored), 1)
        # Per-signal averages
        signal_avgs = {}
        for sig in ["speaker_balance", "sentiment", "completion", "efficiency"]:
            vals = [m["signals"][sig] for m in scored if m["signals"][sig] is not None]
            signal_avgs[sig] = round(sum(vals) / len(vals), 1) if vals else None
    else:
        overall = 0
        signal_avgs = {}

    # Grade
    if not scored:
        grade = "No Data"
    elif overall >= 80:
        grade = "Excellent"
    elif overall >= 60:
        grade = "Good"
    elif overall >= 40:
        grade = "Needs Work"
    else:
        grade = "Poor"

    return {
        "overall_score": overall,
        "grade": grade,
        "signal_scores": signal_avgs,
        "per_meeting": per_meeting,
        "total_scored": len(scored),
    }
