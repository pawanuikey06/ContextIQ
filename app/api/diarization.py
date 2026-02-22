"""
Upload deduplication + meeting metadata + transcript editing.

Adds to existing diarization.py:
- PUT /meeting/{meeting_id}/segments/{index} — edit a transcript segment
- GET /meeting/{meeting_id}/metadata — retrieve metadata
- PATCH /meeting/{meeting_id}/metadata — update metadata
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.schemas.schemas import (
    MeetingResponse,
    SegmentEditRequest,
    MeetingMetadataRequest,
    MeetingMetadataResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_DIR = Path("storage")


# ── Existing: GET /meeting/{meeting_id} ──


@router.get("/meeting/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: str):
    """
    Retrieve the stored transcript for a meeting.
    Reads from storage/{meeting_id}/transcript.json.
    """
    transcript_path = STORAGE_DIR / meeting_id / "transcript.json"

    if not transcript_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Transcript not found for meeting {meeting_id}. Run transcription first."
        )

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"[{meeting_id}] Transcript retrieved")
    except Exception as e:
        logger.error(f"[{meeting_id}] Failed to read transcript: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read transcript: {str(e)}")

    return MeetingResponse(**data)


# ── NEW: Transcript Segment Editing ──


@router.put("/meeting/{meeting_id}/segments/{index}")
async def edit_segment(meeting_id: str, index: int, body: SegmentEditRequest):
    """
    Edit a single transcript segment's text and/or speaker.
    Updates both the flat segments list and the speaker-grouped dict.
    """
    transcript_path = STORAGE_DIR / meeting_id / "transcript.json"

    if not transcript_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Transcript not found for meeting {meeting_id}"
        )

    with open(transcript_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = data.get("segments", [])
    if index < 0 or index >= len(segments):
        raise HTTPException(
            status_code=400,
            detail=f"Segment index {index} out of range (0-{len(segments) - 1})"
        )

    old_segment = segments[index]
    old_speaker = old_segment.get("speaker", "UNKNOWN")

    # Apply edits
    if body.text is not None:
        segments[index]["text"] = body.text
    if body.speaker is not None:
        segments[index]["speaker"] = body.speaker

    new_speaker = segments[index].get("speaker", "UNKNOWN")

    # Rebuild speakers dict from updated segments
    speakers = {}
    for seg in segments:
        spk = seg.get("speaker", "UNKNOWN")
        if spk not in speakers:
            speakers[spk] = []
        speakers[spk].append({
            "start": seg.get("start", 0.0),
            "end": seg.get("end", 0.0),
            "text": seg.get("text", ""),
        })

    data["segments"] = segments
    data["speakers"] = speakers

    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(
        "[%s] Segment %d edited: speaker=%s→%s, text=%s",
        meeting_id, index, old_speaker, new_speaker,
        "updated" if body.text is not None else "unchanged"
    )

    return {
        "meeting_id": meeting_id,
        "segment_index": index,
        "updated_segment": segments[index],
        "message": "Segment updated successfully",
    }


# ── NEW: Meeting Metadata ──


@router.get("/meeting/{meeting_id}/metadata", response_model=MeetingMetadataResponse)
async def get_metadata(meeting_id: str):
    """Retrieve meeting metadata (title, date, participants, etc.)."""
    meeting_dir = STORAGE_DIR / meeting_id
    if not meeting_dir.exists():
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

    meta_path = meeting_dir / "metadata.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    # Filter to only fields in the response model, exclude meeting_id (passed separately)
    valid_fields = MeetingMetadataResponse.model_fields.keys()
    filtered = {k: v for k, v in meta.items() if k in valid_fields and k != "meeting_id"}

    return MeetingMetadataResponse(meeting_id=meeting_id, **filtered)


@router.patch("/meeting/{meeting_id}/metadata", response_model=MeetingMetadataResponse)
async def update_metadata(meeting_id: str, body: MeetingMetadataRequest):
    """
    Update meeting metadata. Only provided fields are changed (PATCH merge).
    Stores in storage/{meeting_id}/metadata.json.
    """
    meeting_dir = STORAGE_DIR / meeting_id
    if not meeting_dir.exists():
        meeting_dir.mkdir(parents=True, exist_ok=True)

    meta_path = meeting_dir / "metadata.json"

    # Load existing metadata (if any)
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    # Merge only fields that were explicitly provided
    update_data = body.model_dump(exclude_none=True)
    meta.update(update_data)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    logger.info("[%s] Metadata updated: %s", meeting_id, list(update_data.keys()))

    return MeetingMetadataResponse(meeting_id=meeting_id, **meta)
