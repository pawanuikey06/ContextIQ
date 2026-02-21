"""
Speech-to-Text service using WhisperX.
Handles transcription + speaker diarization in one pass.
Models are loaded ONCE at init for speed.
"""
import os
import logging
import whisperx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class AudioTranscriptionService:
    """
    WhisperX transcription with speaker diarization.
    - CPU optimized (int8)
    - Models loaded once at startup
    """

    def __init__(self, device="cpu", compute_type="int8"):
        self.device = device
        self.compute_type = compute_type

        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            raise ValueError("HF_TOKEN not found in environment. Set it in .env")

        logger.info("Loading WhisperX ASR model (base)...")
        self.asr_model = whisperx.load_model(
            "base",
            device=self.device,
            compute_type=self.compute_type
        )

        logger.info("Loading diarization pipeline...")
        self.diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=self.hf_token,
            device=self.device
        )
        logger.info("Models loaded successfully")

    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio and assign speaker labels.

        Args:
            audio_path: Path to WAV audio file

        Returns:
            dict with keys: "language", "segments"
            Each segment: { "start", "end", "speaker", "text" }
        """
        logger.info(f"Loading audio: {audio_path}")
        audio = whisperx.load_audio(audio_path)

        # 1. Transcribe
        logger.info("Running transcription...")
        result = self.asr_model.transcribe(audio)
        logger.info(f"Transcription done: {len(result.get('segments', []))} raw segments")

        # 2. Diarization — needs the audio FILE PATH, not numpy array
        logger.info("Running speaker diarization...")
        diarization = self.diarize_model(audio_path)

        # 3. Assign speaker labels to segments
        result = whisperx.assign_word_speakers(diarization, result)

        # 4. Normalize output
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "speaker": seg.get("speaker", "UNKNOWN"),
                "text": seg.get("text", "").strip()
            })

        logger.info(f"Final output: {len(segments)} segments with speaker labels")
        return {
            "language": result.get("language", "unknown"),
            "segments": segments
        }