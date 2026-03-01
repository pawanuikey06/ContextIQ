"""
Speech-to-Text service — multi-engine transcription.

Modes (set via STT_MODE env var):
  - "assemblyai" : AssemblyAI API (transcription + diarization in one call) 
  - "groq"       : Groq Whisper API + local pyannote diarization
  - "local"      : WhisperX + local pyannote diarization
  - "auto"       : Try Groq first, fall back to local

Audio preprocessing: noise reduction + normalization for improved accuracy.
"""
import os
import gc
import logging
import numpy as np
import soundfile as sf
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Recommended by PyTorch for GPUs with limited VRAM
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

# Max file size for Groq API (25 MB)
GROQ_MAX_FILE_BYTES = 25 * 1024 * 1024



class AudioTranscriptionService:
    """
    Multi-engine transcription service:
      - AssemblyAI: transcription + diarization in one API call (best quality)
      - Groq Whisper API: fast cloud transcription + local diarization
      - WhisperX: local GPU/CPU fallback + local diarization
    """

    def __init__(self, device=None, compute_type=None):
        if device is None:
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                logger.warning("CUDA check failed — falling back to CPU")
                self.device = "cpu"
        else:
            self.device = device

        if compute_type is None:
            self.compute_type = "float16" if self.device == "cuda" else "int8"
        else:
            self.compute_type = compute_type

        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            logger.warning("HF_TOKEN not found — local diarization may not work.")

        self.stt_mode = os.getenv("STT_MODE", "assemblyai").lower()
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")

        logger.info(
            "AudioTranscriptionService initialized: device=%s, compute_type=%s, stt_mode=%s",
            self.device, self.compute_type, self.stt_mode,
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
    # Groq Whisper transcription (cloud)
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Audio preprocessing (noise reduction + normalization)
    # ------------------------------------------------------------------
    def _preprocess_audio(self, audio_path: str) -> str:
        """
        Apply noise reduction and normalization to improve transcription accuracy.
        Saves preprocessed audio alongside original with '_clean' suffix.
        Returns path to cleaned audio file.
        """
        try:
            import noisereduce as nr

            logger.info("[Preprocess] Loading audio for preprocessing: %s", audio_path)
            audio_data, sample_rate = sf.read(audio_path)

            # Ensure mono
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Step 1: Noise reduction
            logger.info("[Preprocess] Applying noise reduction...")
            cleaned = nr.reduce_noise(
                y=audio_data,
                sr=sample_rate,
                prop_decrease=0.7,   # Moderate noise reduction (preserve speech)
                n_std_thresh_stationary=1.5,
            )

            # Step 2: Normalize volume (peak normalization to -1 dBFS)
            logger.info("[Preprocess] Normalizing audio levels...")
            peak = np.max(np.abs(cleaned))
            if peak > 0:
                target_peak = 10 ** (-1.0 / 20)  # -1 dBFS
                cleaned = cleaned * (target_peak / peak)

            # Save cleaned audio
            clean_path = audio_path.replace(".wav", "_clean.wav")
            sf.write(clean_path, cleaned, sample_rate)

            clean_size = Path(clean_path).stat().st_size
            logger.info(
                "[Preprocess] Cleaned audio saved: %s (%d bytes)",
                clean_path, clean_size,
            )
            return clean_path

        except Exception as e:
            logger.warning("[Preprocess] Audio preprocessing failed (using original): %s", e)
            return audio_path

    # ------------------------------------------------------------------
    # AssemblyAI transcription + diarization (cloud, single API call)
    # ------------------------------------------------------------------
    def _transcribe_assemblyai(self, audio_path: str) -> dict:
        """
        Transcribe audio AND perform speaker diarization using AssemblyAI.
        Returns dict with "language" and "segments" (with speaker labels).
        """
        import assemblyai as aai

        aai.settings.api_key = self.assemblyai_api_key

        config_kwargs = {
            "speech_models": ["universal-2"],
            "language_detection": True,
            "speaker_labels": True,
        }

        # If SPEAKERS_EXPECTED is set in .env, tell AssemblyAI
        speakers_expected = os.getenv("SPEAKERS_EXPECTED")
        if speakers_expected:
            config_kwargs["speakers_expected"] = int(speakers_expected)
            logger.info("[AssemblyAI] speakers_expected=%s (from .env)", speakers_expected)

        config = aai.TranscriptionConfig(**config_kwargs)

        logger.info("[AssemblyAI] Uploading and transcribing: %s", audio_path)
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(audio_path, config=config)

        if transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(f"AssemblyAI transcription failed: {transcript.error}")

        # Parse utterances (each utterance = one speaker turn)
        segments = []
        if transcript.utterances:
            for utt in transcript.utterances:
                segments.append({
                    "start": round(utt.start / 1000, 2),  # ms → seconds
                    "end": round(utt.end / 1000, 2),
                    "text": utt.text.strip(),
                    "speaker": f"SPEAKER_{ord(utt.speaker) - ord('A'):02d}",  # A→00, B→01
                })
        else:
            # Fallback: use words if no utterances
            segments.append({
                "start": 0.0,
                "end": 0.0,
                "text": transcript.text or "",
                "speaker": "UNKNOWN",
            })

        detected_lang = transcript.language_code or "en"
        logger.info(
            "[AssemblyAI] Done: %d segments, %d speakers, lang=%s",
            len(segments),
            len(set(s["speaker"] for s in segments)),
            detected_lang,
        )
        return {
            "language": detected_lang,
            "segments": segments,
        }

    # ------------------------------------------------------------------
    # Groq Whisper transcription (cloud)
    # ------------------------------------------------------------------
    def _transcribe_groq(self, audio_path: str) -> dict:
        """
        Transcribe audio using Groq's Whisper API.
        Returns dict with "language" and "segments" (timestamped).
        """
        from groq import Groq

        file_size = Path(audio_path).stat().st_size
        if file_size > GROQ_MAX_FILE_BYTES:
            raise ValueError(
                f"Audio file too large for Groq API ({file_size / 1024 / 1024:.1f} MB > 25 MB limit). "
                "Falling back to local."
            )

        logger.info("[Groq] Sending audio to Whisper API (%d bytes)...", file_size)

        client = Groq(api_key=self.groq_api_key)

        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=(Path(audio_path).name, audio_file),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                language="en",
            )

        # Parse Groq response into our segment format
        segments = []
        if hasattr(response, "segments") and response.segments:
            for seg in response.segments:
                segments.append({
                    "start": round(seg.get("start", 0.0) if isinstance(seg, dict) else seg.start, 2),
                    "end": round(seg.get("end", 0.0) if isinstance(seg, dict) else seg.end, 2),
                    "text": (seg.get("text", "") if isinstance(seg, dict) else seg.text).strip(),
                    "speaker": "UNKNOWN",  # Groq doesn't do diarization
                })
        else:
            # Fallback: single segment with full text
            segments.append({
                "start": 0.0,
                "end": 0.0,
                "text": response.text.strip() if response.text else "",
                "speaker": "UNKNOWN",
            })

        language = getattr(response, "language", "en") or "en"

        logger.info(
            "[Groq] Transcription complete: %d segments, language=%s",
            len(segments), language,
        )

        return {
            "language": language,
            "segments": segments,
        }

    # ------------------------------------------------------------------
    # Local WhisperX transcription (GPU/CPU)
    # ------------------------------------------------------------------
    def _transcribe_local(self, audio_path: str) -> dict:
        """
        Transcribe audio using local WhisperX model.
        Returns dict with "language" and "segments".
        """
        import whisperx

        logger.info("[Local] Loading audio: %s", audio_path)
        audio = whisperx.load_audio(audio_path)

        logger.info("[Local] Loading WhisperX ASR model (medium)...")
        asr_model = whisperx.load_model(
            "medium",
            device=self.device,
            compute_type=self.compute_type,
        )

        logger.info("[Local] Running transcription...")
        result = asr_model.transcribe(audio)
        logger.info(
            "[Local] Transcription done: %d raw segments",
            len(result.get("segments", [])),
        )

        del asr_model
        self._free_gpu()

        return result

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
    # Speaker assignment for Groq transcripts
    # ------------------------------------------------------------------
    def _assign_speakers_from_diarization(self, segments: list, diarization) -> list:
        """
        Assign speaker labels to transcript segments using pyannote diarization output.
        Matches each segment to the speaker with the most overlap.

        diarization can be:
          - A pandas DataFrame with 'segment' (pyannote Segment) and 'speaker'/'label' columns
            (returned by WhisperX DiarizationPipeline)
          - A pyannote Annotation object with .itertracks()
        """
        # Convert diarization to a list of (start, end, speaker)
        diar_segments = []

        try:
            import pandas as pd
            if isinstance(diarization, pd.DataFrame):
                # WhisperX DiarizationPipeline returns a DataFrame
                for _, row in diarization.iterrows():
                    if hasattr(row.get("segment", None), "start"):
                        # segment is a pyannote Segment object
                        d_start = row["segment"].start
                        d_end = row["segment"].end
                    else:
                        d_start = row.get("start", 0.0)
                        d_end = row.get("end", 0.0)
                    speaker = row.get("speaker", row.get("label", "UNKNOWN"))
                    diar_segments.append((d_start, d_end, speaker))
            else:
                raise TypeError("Not a DataFrame, try itertracks")
        except (ImportError, TypeError):
            # Fallback: pyannote Annotation object
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                diar_segments.append((turn.start, turn.end, speaker))

        logger.info("Diarization segments: %d, mapping to %d transcript segments",
                     len(diar_segments), len(segments))

        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            best_speaker = "UNKNOWN"
            best_overlap = 0.0

            for d_start, d_end, d_speaker in diar_segments:
                # Calculate overlap
                overlap_start = max(seg_start, d_start)
                overlap_end = min(seg_end, d_end)
                overlap = max(0.0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = d_speaker

            seg["speaker"] = best_speaker

        return segments

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio and assign speaker labels.

        Modes:
          - assemblyai: Single API call for transcription + diarization
          - groq: Groq Whisper + local pyannote diarization
          - local: WhisperX + local pyannote diarization
          - auto: Try Groq, fall back to local

        Args:
            audio_path: Path to WAV audio file

        Returns:
            dict with keys: "language", "segments"
            Each segment: { "start", "end", "speaker", "text" }
        """
        # ── AssemblyAI mode: single API call handles everything ──────
        if self.stt_mode == "assemblyai" and self.assemblyai_api_key:
            logger.info("Using AssemblyAI for transcription + diarization")
            clean_audio_path = self._preprocess_audio(audio_path)
            result = self._transcribe_assemblyai(clean_audio_path)
            logger.info(
                "Final output: %d segments with speaker labels (mode=assemblyai)",
                len(result["segments"]),
            )
            return result

        # ── Groq / Local / Auto modes ────────────────────────────────
        import whisperx

        use_groq = False
        result = None

        # Step 0: Preprocess audio
        clean_audio_path = self._preprocess_audio(audio_path)

        # Step 1: Transcription
        if self.stt_mode in ("groq", "auto") and self.groq_api_key:
            try:
                result = self._transcribe_groq(clean_audio_path)
                use_groq = True
            except Exception as e:
                if self.stt_mode == "groq":
                    logger.error("Groq transcription failed: %s", e)
                    raise
                else:
                    logger.warning(
                        "Groq transcription failed, falling back to local: %s", e
                    )

        if result is None:
            result = self._transcribe_local(clean_audio_path)

        # Step 2: Diarization (local pyannote)
        logger.info("Loading diarization pipeline...")
        diarize_model = self._load_diarization_pipeline()

        logger.info("Running speaker diarization...")
        diarization = diarize_model(audio_path)

        del diarize_model
        self._free_gpu()

        # Step 3: Merge speakers into transcript
        if use_groq:
            segments = self._assign_speakers_from_diarization(
                result["segments"], diarization
            )
        else:
            audio = whisperx.load_audio(audio_path)
            result = whisperx.assign_word_speakers(diarization, result)
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "start": round(seg.get("start", 0.0), 2),
                    "end": round(seg.get("end", 0.0), 2),
                    "speaker": seg.get("speaker", "UNKNOWN"),
                    "text": seg.get("text", "").strip(),
                })

        logger.info(
            "Final output: %d segments with speaker labels (mode=%s)",
            len(segments), "groq" if use_groq else "local",
        )
        return {
            "language": result.get("language", "unknown"),
            "segments": segments,
        }