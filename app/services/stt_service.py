"""
Speech-to-Text service using WhisperX.
Handles transcription + speaker diarization in one pass.

Uses sequential GPU offloading to fit within limited VRAM (e.g. 4 GB):
    Load ASR → transcribe → free ASR →
    Load diarization → diarize → free diarization
"""
import os
import gc
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Recommended by PyTorch for GPUs with limited VRAM
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")


class AudioTranscriptionService:
    """
    WhisperX transcription with speaker diarization.
    - Auto-detects CUDA GPU (uses float16) or falls back to CPU (int8)
    - Uses sequential GPU offloading: only one model in VRAM at a time
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

        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            raise ValueError("HF_TOKEN not found in environment. Set it in .env")

        logger.info(
            "AudioTranscriptionService initialized: device=%s, compute_type=%s",
            self.device, self.compute_type,
        )

    # ------------------------------------------------------------------
    # GPU memory helpers
    # ------------------------------------------------------------------
    def _free_gpu(self):
        """Force-release all unused CUDA memory."""
        gc.collect()
        if self.device == "cuda":
            import torch
            torch.cuda.empty_cache()
            logger.info(
                "CUDA cache cleared – free VRAM: %.1f MiB",
                torch.cuda.mem_get_info()[0] / 1024 ** 2,
            )

    # ------------------------------------------------------------------
    # Model loaders (create-use-delete, never cached)
    # ------------------------------------------------------------------
    def _load_diarization_pipeline(self):
        """Load the first available pyannote diarization model."""
        from whisperx.diarize import DiarizationPipeline

        models_to_try = [
            "pyannote/speaker-diarization-3.1",
            "pyannote/speaker-diarization",
            "pyannote/speaker-diarization-community-1",
        ]
        last_error = None
        for model_name in models_to_try:
            try:
                logger.info("Trying diarization model: %s", model_name)
                pipeline = DiarizationPipeline(
                    model_name=model_name,
                    token=self.hf_token,
                    device=self.device,
                )
                logger.info("Diarization pipeline loaded: %s", model_name)
                return pipeline
            except Exception as e:
                last_error = e
                logger.warning("Failed to load %s: %s", model_name, e)
                continue

        raise RuntimeError(
            f"Could not load any diarization model. Last error: {last_error}\n"
            "Please accept model licenses at:\n"
            "  https://huggingface.co/pyannote/speaker-diarization-3.1\n"
            "  https://huggingface.co/pyannote/segmentation-3.0\n"
            "  https://huggingface.co/pyannote/speaker-diarization-community-1"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio and assign speaker labels.

        Uses sequential GPU offloading so only one model sits in VRAM
        at a time, allowing operation on GPUs with as little as 4 GB.

        Args:
            audio_path: Path to WAV audio file

        Returns:
            dict with keys: "language", "segments"
            Each segment: { "start", "end", "speaker", "text" }
        """
        import whisperx

        logger.info("Loading audio: %s", audio_path)
        audio = whisperx.load_audio(audio_path)

        # ── Step 1: ASR (load → transcribe → free) ──────────────────
        logger.info("Loading WhisperX ASR model (base)...")
        asr_model = whisperx.load_model(
            "base",
            device=self.device,
            compute_type=self.compute_type,
        )

        logger.info("Running transcription...")
        result = asr_model.transcribe(audio)
        logger.info(
            "Transcription done: %d raw segments",
            len(result.get("segments", [])),
        )

        del asr_model  # release ASR model from VRAM
        self._free_gpu()

        # ── Step 2: Diarization (load → diarize → free) ─────────────
        logger.info("Loading diarization pipeline...")
        diarize_model = self._load_diarization_pipeline()

        logger.info("Running speaker diarization...")
        diarization = diarize_model(audio_path)

        del diarize_model  # release diarization model from VRAM
        self._free_gpu()

        # ── Step 3: Merge speakers into transcript (CPU only) ───────
        result = whisperx.assign_word_speakers(diarization, result)

        # ── Step 4: Normalize output ────────────────────────────────
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "speaker": seg.get("speaker", "UNKNOWN"),
                "text": seg.get("text", "").strip(),
            })

        logger.info("Final output: %d segments with speaker labels", len(segments))
        return {
            "language": result.get("language", "unknown"),
            "segments": segments,
        }