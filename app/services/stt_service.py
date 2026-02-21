"""
Speech-to-Text service using WhisperX.
Handles transcription + speaker diarization in one pass.
Models are loaded lazily on first use to avoid startup failures.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class AudioTranscriptionService:
    """
    WhisperX transcription with speaker diarization.
    - Auto-detects CUDA GPU (uses float16) or falls back to CPU (int8)
    - Models loaded lazily on first transcribe() call
    """

    def __init__(self, device=None, compute_type=None):
        import torch

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        if compute_type is None:
            self.compute_type = "float16" if self.device == "cuda" else "int8"
        else:
            self.compute_type = compute_type

        self._asr_model = None
        self._diarize_model = None

        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            raise ValueError("HF_TOKEN not found in environment. Set it in .env")

        logger.info(f"AudioTranscriptionService initialized: device={self.device}, compute_type={self.compute_type}")

    def _load_models(self):
        """Lazy-load WhisperX and diarization models on first use."""
        import whisperx
        from whisperx.diarize import DiarizationPipeline

        if self._asr_model is None:
            logger.info("Loading WhisperX ASR model (base)...")
            self._asr_model = whisperx.load_model(
                "base",
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("ASR model loaded")

        if self._diarize_model is None:
            logger.info("Loading diarization pipeline...")
            # Try models in order of preference
            models_to_try = [
                "pyannote/speaker-diarization-3.1",
                "pyannote/speaker-diarization",
                "pyannote/speaker-diarization-community-1",
            ]
            last_error = None
            for model_name in models_to_try:
                try:
                    logger.info(f"Trying diarization model: {model_name}")
                    self._diarize_model = DiarizationPipeline(
                        model_name=model_name,
                        token=self.hf_token,
                        device=self.device
                    )
                    logger.info(f"Diarization pipeline loaded: {model_name}")
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(f"Failed to load {model_name}: {e}")
                    continue

            if self._diarize_model is None:
                raise RuntimeError(
                    f"Could not load any diarization model. Last error: {last_error}\n"
                    "Please accept model licenses at:\n"
                    "  https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                    "  https://huggingface.co/pyannote/segmentation-3.0\n"
                    "  https://huggingface.co/pyannote/speaker-diarization-community-1"
                )

    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio and assign speaker labels.

        Args:
            audio_path: Path to WAV audio file

        Returns:
            dict with keys: "language", "segments"
            Each segment: { "start", "end", "speaker", "text" }
        """
        import whisperx

        # Ensure models are loaded
        self._load_models()

        logger.info(f"Loading audio: {audio_path}")
        audio = whisperx.load_audio(audio_path)

        # 1. Transcribe
        logger.info("Running transcription...")
        result = self._asr_model.transcribe(audio)
        logger.info(f"Transcription done: {len(result.get('segments', []))} raw segments")

        # 2. Diarization — pass the audio FILE PATH
        logger.info("Running speaker diarization...")
        diarization = self._diarize_model(audio_path)

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