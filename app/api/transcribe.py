"""
POST /transcribe/{meeting_id}
Uses the already-extracted audio to run transcription + speaker diarization.
Saves merged output to storage/{meeting_id}/transcript.json.
Auto-creates metadata.json with processing timestamps.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pathlib import Path

from app.services.stt_service import AudioTranscriptionService
from app.services.speaker_service import SpeakerTranscriptBuilder
from app.services.storage_service import MeetingStorageService
from app.schemas.schemas import TranscriptResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Services initialized lazily to avoid import-time model loading
_stt_service = None
_speaker_builder = None
_storage_service = None

STORAGE_DIR = Path("storage")
MEETING_COUNTER_FILE = STORAGE_DIR / "_meeting_counter.json"


def _get_meeting_number(meeting_id: str) -> int:
    """
    Get or assign a sequential meeting number (1, 2, 3, ...) for the given meeting_id.
    Persisted in storage/_meeting_counter.json.
    """
    counter_data = {}
    if MEETING_COUNTER_FILE.exists():
        try:
            with open(MEETING_COUNTER_FILE, "r", encoding="utf-8") as f:
                counter_data = json.load(f)
        except Exception:
            counter_data = {}

    if meeting_id in counter_data:
        return counter_data[meeting_id]

    existing_numbers = list(counter_data.values()) if counter_data else []
    next_number = max(existing_numbers) + 1 if existing_numbers else 1
    counter_data[meeting_id] = next_number

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with open(MEETING_COUNTER_FILE, "w", encoding="utf-8") as f:
        json.dump(counter_data, f, indent=2)

    logger.info("[%s] Assigned meeting number: m%d", meeting_id, next_number)
    return next_number


def _add_meeting_suffix_to_speakers(segments: list, meeting_number: int) -> list:
    """
    Post-process segments to append _m{N} suffix to all speaker labels.
    e.g. SPEAKER_00 → SPEAKER_00_m1
    """
    suffix = f"_m{meeting_number}"
    for seg in segments:
        speaker = seg.get("speaker", "UNKNOWN")
        if speaker and speaker != "UNKNOWN" and not speaker.endswith(suffix):
            seg["speaker"] = f"{speaker}{suffix}"
    return segments


def _get_services():
    """Lazy-init services on first request."""
    global _stt_service, _speaker_builder, _storage_service
    if _stt_service is None:
        _stt_service = AudioTranscriptionService()
    if _speaker_builder is None:
        _speaker_builder = SpeakerTranscriptBuilder()
    if _storage_service is None:
        _storage_service = MeetingStorageService()
    return _stt_service, _speaker_builder, _storage_service

AUDIO_DIR = Path("data/audio")


@router.post("/transcribe/{meeting_id}", response_model=TranscriptResponse)
async def transcribe_meeting(meeting_id: str):
    """
    Transcribe + diarize the audio for a given meeting_id.
    Audio must already exist at data/audio/{meeting_id}.wav (from /upload-video).
    """
    audio_path = AUDIO_DIR / f"{meeting_id}.wav"

    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Audio not found for meeting {meeting_id}. Upload video first."
        )

    logger.info(f"[{meeting_id}] Starting transcription: {audio_path}")

    try:
        stt_service, speaker_builder, storage_service = _get_services()

        # Step 1: Transcribe + diarize
        result = stt_service.transcribe(str(audio_path))
        segments = result["segments"]
        logger.info(f"[{meeting_id}] Transcription complete: {len(segments)} segments")

        # Step 1b: Add meeting number suffix to speaker labels
        meeting_number = _get_meeting_number(meeting_id)
        segments = _add_meeting_suffix_to_speakers(segments, meeting_number)
        logger.info(f"[{meeting_id}] Speaker labels updated with suffix _m{meeting_number}")

        # Step 2: Build speaker-wise grouping
        speakers = speaker_builder.build(segments)
        logger.info(f"[{meeting_id}] Speaker grouping complete: {len(speakers)} speakers")

        # Step 3: Save to storage/{meeting_id}/transcript.json
        transcript_data = {
            "meeting_id": meeting_id,
            "audio_path": str(audio_path),
            "segments": segments,
            "speakers": speakers,
        }
        storage_path = storage_service.save(meeting_id, transcript_data)
        logger.info(f"[{meeting_id}] Transcript saved: {storage_path}")

        # Step 3a: Extract speaker clips + auto-match known speakers (non-fatal)
        # NOTE: Must run AFTER transcript is saved — extract_speaker_clips reads transcript.json from disk
        try:
            from app.services.voice_embedding_service import VoiceEmbeddingService
            _voice_svc = VoiceEmbeddingService()
            _voice_svc.extract_speaker_clips(meeting_id)
            auto_matches = _voice_svc.match_speakers(meeting_id)
            if auto_matches:
                # Update segments with matched names and re-save
                for seg in segments:
                    spk = seg.get("speaker", "")
                    if spk in auto_matches:
                        seg["speaker"] = auto_matches[spk]
                # Re-build speaker grouping with matched names
                speakers = speaker_builder.build(segments)
                transcript_data["segments"] = segments
                transcript_data["speakers"] = speakers
                storage_service.save(meeting_id, transcript_data)
                logger.info(f"[{meeting_id}] Auto-matched speakers: {auto_matches} — transcript re-saved")
        except Exception as e:
            logger.warning(f"[{meeting_id}] Voice embedding step skipped: {e}")

        # Step 3b: Auto-create metadata.json with processing info
        try:
            now = datetime.now()
            meta_path = Path("storage") / meeting_id / "metadata.json"
            existing_meta = {}
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    existing_meta = json.load(f)

            existing_meta.update({
                "meeting_id": meeting_id,
                "status": "transcribed",
                "processed_at": now.isoformat(),
                "processed_date": now.strftime("%B %d, %Y"),
                "processed_day": now.strftime("%A"),
                "processed_time": now.strftime("%I:%M %p"),
                "segment_count": len(segments),
                "speaker_count": len(speakers),
            })

            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(existing_meta, f, indent=2, ensure_ascii=False)
            logger.info(f"[{meeting_id}] Metadata saved: {len(segments)} segments, {len(speakers)} speakers")
        except Exception as e:
            logger.warning(f"[{meeting_id}] Metadata creation failed (non-fatal): {e}")
        try:
            from app.api.chat import _get_rag_service
            rag = _get_rag_service()
            chunk_count = rag.ingest_meeting(meeting_id)
            logger.info(f"[{meeting_id}] Auto-indexed: {chunk_count} chunks")
        except Exception as e:
            logger.warning(f"[{meeting_id}] Auto-index failed (non-fatal): {e}")

        # Step 4b: Auto-generate meeting title from transcript
        try:
            from app.services.insights_service import MeetingInsightsService
            insights = MeetingInsightsService()
            title_result = insights.generate_title(meeting_id, force=False)
            logger.info(f"[{meeting_id}] Auto-title generated: {title_result.get('auto_title', 'N/A')}")
        except Exception as e:
            logger.warning(f"[{meeting_id}] Auto-title failed (non-fatal): {e}")

    except Exception as e:
        logger.error(f"[{meeting_id}] Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    return TranscriptResponse(**transcript_data)
