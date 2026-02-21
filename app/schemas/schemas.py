"""
Pydantic v2 schemas for the Meeting Intelligence pipeline.
Defines request/response models for upload, transcription, and meeting retrieval.
"""
from typing import Dict, List
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
