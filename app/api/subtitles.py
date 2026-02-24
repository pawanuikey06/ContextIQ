"""
Subtitle export API.
Generates SRT and VTT subtitles from meeting transcripts.
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Subtitles"])
STORAGE_DIR = Path("storage")


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    """Convert seconds to VTT timestamp HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _load_segments(meeting_id: str) -> list:
    transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found for meeting {meeting_id}")
    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Apply speaker map if it exists
    speaker_map = {}
    smap_path = STORAGE_DIR / meeting_id / "speaker_map.json"
    if smap_path.exists():
        with open(smap_path, "r", encoding="utf-8") as f:
            speaker_map = json.load(f).get("mapping", {})

    segments = data.get("segments", [])
    for seg in segments:
        raw = seg.get("speaker", "UNKNOWN")
        seg["speaker_display"] = speaker_map.get(raw, raw)
    return segments


@router.get("/meeting/{meeting_id}/subtitles/srt")
async def export_srt(meeting_id: str):
    """Export meeting transcript as SRT subtitle file."""
    try:
        segments = _load_segments(meeting_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    lines = []
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_srt_time(seg.get("start", 0))
        end = _seconds_to_srt_time(seg.get("end", 0))
        speaker = seg.get("speaker_display", seg.get("speaker", "UNKNOWN"))
        text = seg.get("text", "").strip()
        lines.append(f"{i}\n{start} --> {end}\n[{speaker}]: {text}\n")

    content = "\n".join(lines)
    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="meeting_{meeting_id[:8]}.srt"'},
    )


@router.get("/meeting/{meeting_id}/subtitles/vtt")
async def export_vtt(meeting_id: str):
    """Export meeting transcript as WebVTT subtitle file."""
    try:
        segments = _load_segments(meeting_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, 1):
        start = _seconds_to_vtt_time(seg.get("start", 0))
        end = _seconds_to_vtt_time(seg.get("end", 0))
        speaker = seg.get("speaker_display", seg.get("speaker", "UNKNOWN"))
        text = seg.get("text", "").strip()
        lines.append(f"{i}\n{start} --> {end}\n<v {speaker}>{text}</v>\n")

    content = "\n".join(lines)
    return PlainTextResponse(
        content=content,
        media_type="text/vtt",
        headers={"Content-Disposition": f'attachment; filename="meeting_{meeting_id[:8]}.vtt"'},
    )
