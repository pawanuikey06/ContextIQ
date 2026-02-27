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
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.responses import StreamingResponse

from app.schemas.schemas import (
    MeetingResponse,
    SegmentEditRequest,
    MeetingMetadataRequest,
    MeetingMetadataResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

STORAGE_DIR = Path("storage")


# ── List all meetings ──


@router.get("/meetings")
async def list_meetings():
    """
    List all meetings in storage with metadata summary.
    Returns a list of meetings for the Dashboard.
    """
    meetings = []
    if not STORAGE_DIR.exists():
        return {"meetings": []}

    for d in sorted(STORAGE_DIR.iterdir(), reverse=True):
        if not d.is_dir() or d.name == "chroma_db":
            continue

        meeting_id = d.name
        meta = {}
        title = f"Meeting {meeting_id[:8]}..."
        date = ""
        day = ""
        speakers_count = 0
        segments_count = 0
        duration = 0
        status = "uploaded"

        # Load metadata
        meta_path = d / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                title = meta.get("auto_title", meta.get("title", title))
                date = meta.get("processed_date", "")
                day = meta.get("processed_day", "")
            except Exception:
                pass

        # Load transcript info
        transcript_path = d / "transcript.json"
        if transcript_path.exists():
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    tdata = json.load(f)
                segs = tdata.get("segments", [])
                segments_count = len(segs)
                speakers_count = len(tdata.get("speakers", {}))
                if segs:
                    duration = max(s.get("end", 0) for s in segs)
                status = "transcribed"
            except Exception:
                pass

        # Check summary status
        if (d / "summary.json").exists():
            status = "summarized"
        if (d / "Meeting_Summary.pdf").exists():
            status = "published"

        meetings.append({
            "id": meeting_id,
            "title": title,
            "date": date,
            "day": day,
            "speakers": speakers_count,
            "segments": segments_count,
            "duration": duration,
            "status": status,
        })

    return {"meetings": meetings}


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


# ------------------------------------------------------------------
# Video Playback (with Range request support for seeking)
# ------------------------------------------------------------------
@router.head("/meeting/{meeting_id}/video")
@router.get("/meeting/{meeting_id}/video")
async def get_meeting_video(meeting_id: str, request: Request):
    """
    Stream the original video file for in-browser playback.
    Supports HTTP Range requests so the browser can seek to arbitrary positions.
    Video is stored at storage/{meeting_id}/video.mp4
    """
    import os

    video_path = STORAGE_DIR / meeting_id / "video.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found for this meeting")

    file_size = os.path.getsize(video_path)

    range_header = request.headers.get("range")

    if range_header:
        # Parse Range: bytes=start-end
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1

        def iter_file():
            with open(video_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iter_file(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Type": "video/mp4",
            },
        )
    else:
        # No Range header — return full file with Accept-Ranges
        return FileResponse(
            path=str(video_path),
            media_type="video/mp4",
            filename=f"{meeting_id}.mp4",
            headers={"Accept-Ranges": "bytes"},
        )


# ------------------------------------------------------------------
# Delete Meeting
# ------------------------------------------------------------------
@router.delete("/meeting/{meeting_id}")
async def delete_meeting(meeting_id: str):
    """
    Permanently delete a meeting: storage dir, audio, video, and ChromaDB index.
    """
    import shutil

    meeting_dir = STORAGE_DIR / meeting_id
    audio_path = Path("data/audio") / f"{meeting_id}.wav"
    video_path = meeting_dir / "video.mp4"

    deleted = []

    # 1. Remove from ChromaDB (RAG)
    try:
        from app.api.chat import _get_rag_service
        rag = _get_rag_service()
        rag._delete_meeting_docs(meeting_id)
        deleted.append("chromadb")
        logger.info("[%s] Removed from ChromaDB", meeting_id)
    except Exception as e:
        logger.warning("[%s] ChromaDB cleanup failed: %s", meeting_id, e)

    # 2. Remove storage directory
    if meeting_dir.exists():
        shutil.rmtree(str(meeting_dir))
        deleted.append("storage")
        logger.info("[%s] Storage directory removed", meeting_id)

    # 3. Remove audio file
    if audio_path.exists():
        audio_path.unlink()
        deleted.append("audio")
        logger.info("[%s] Audio file removed", meeting_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")

    logger.info("[%s] Meeting deleted: %s", meeting_id, deleted)
    return {
        "success": True,
        "meeting_id": meeting_id,
        "deleted": deleted,
        "message": f"Meeting {meeting_id} permanently deleted",
    }