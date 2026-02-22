"""
Pydantic v2 schemas for the Meeting Intelligence pipeline.
Defines request/response models for upload, transcription, meeting retrieval,
segment editing, meeting metadata, and chat.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel


class SegmentOut(BaseModel):
    """A single transcription segment with speaker and timestamps."""
    start: float
    end: float
    speaker: str
    text: str


class SpeakerSegment(BaseModel):
    """A segment belonging to a specific speaker (no speaker field needed)."""
    start: float
    end: float
    text: str


class UploadResponse(BaseModel):
    """Response from POST /upload-video."""
    meeting_id: str
    audio_path: str
    message: str


class TranscriptResponse(BaseModel):
    """
    Full transcript output with segments and speaker-wise grouping.
    Matches the mandatory JSON output format.
    """
    meeting_id: str
    audio_path: str
    segments: List[SegmentOut]
    speakers: Dict[str, List[SpeakerSegment]]


class MeetingResponse(BaseModel):
    """Response from GET /meeting/{meeting_id} — wraps stored transcript."""
    meeting_id: str
    audio_path: str
    segments: List[SegmentOut]
    speakers: Dict[str, List[SpeakerSegment]]


class SummaryResponse(BaseModel):
    """Response from POST /summarize/{meeting_id}."""
    meeting_id: str
    speaker_summaries_en: Dict[str, str]
    overall_summary_en: str
    overall_summary_hi: str


# ── Segment Editing ──

class SegmentEditRequest(BaseModel):
    """Request to edit a transcript segment."""
    text: Optional[str] = None
    speaker: Optional[str] = None


# ── Meeting Metadata ──

class MeetingMetadataRequest(BaseModel):
    """Request to update meeting metadata."""
    title: Optional[str] = None
    date: Optional[str] = None
    participants: Optional[List[str]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class MeetingMetadataResponse(BaseModel):
    """Response from GET /meeting/{id}/metadata."""
    meeting_id: str
    title: Optional[str] = None
    date: Optional[str] = None
    participants: Optional[List[str]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    processed_date: Optional[str] = None
    processed_day: Optional[str] = None
    processed_time: Optional[str] = None

