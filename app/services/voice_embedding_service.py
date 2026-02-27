"""
Voice Embedding Service — speaker clip extraction, embedding, and matching.

Extracts ~10-second audio clips per speaker, preprocesses for quality,
generates voice embeddings using speechbrain ECAPA-TDNN, and matches
against stored speaker profiles.

Audio preprocessing pipeline:
  1. Resample to 16kHz (model requirement)
  2. Convert to mono
  3. Remove silence / low-energy frames
  4. Peak normalization
  5. Bandpass filter (80Hz–7600Hz) to isolate speech band

Fully self-contained — does not modify any existing service.
"""
import json
import logging
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

STORAGE_DIR = Path("storage")
AUDIO_DIR = Path("data/audio")
PROFILES_DIR = STORAGE_DIR / "speaker_profiles"
TARGET_CLIP_DURATION = 10.0  # seconds
TARGET_SAMPLE_RATE = 16000  # speechbrain requirement
MIN_CLIP_DURATION = 3.0  # minimum useful clip length in seconds


class VoiceEmbeddingService:
    """
    Handles speaker clip extraction, embedding generation, and profile matching.
    Uses speechbrain's ECAPA-TDNN model for speaker verification embeddings.
    """

    def __init__(self):
        self._embedding_model = None

    # ------------------------------------------------------------------
    # Lazy model loading
    # ------------------------------------------------------------------
    @staticmethod
    def _patch_torchaudio():
        """Patch torchaudio for speechbrain compatibility (torchaudio 2.10+)."""
        try:
            import torchaudio
            if not hasattr(torchaudio, 'list_audio_backends'):
                # torchaudio 2.10+ removed list_audio_backends; speechbrain 1.0.x needs it
                torchaudio.list_audio_backends = lambda: ["soundfile"]
                logger.info("Patched torchaudio.list_audio_backends for compatibility")
        except Exception:
            pass

    def _get_model(self):
        """Lazy-load the speechbrain speaker embedding model."""
        if self._embedding_model is None:
            try:
                import platform
                self._patch_torchaudio()

                # Windows: monkey-patch speechbrain's fetch to use COPY instead of SYMLINK
                # (symlinks require admin privileges on Windows)
                if platform.system() == "Windows":
                    try:
                        import speechbrain.utils.fetching as sb_fetch
                        _original_fetch = sb_fetch.fetch

                        def _patched_fetch(*args, **kwargs):
                            if kwargs.get("local_strategy") == sb_fetch.LocalStrategy.SYMLINK:
                                kwargs["local_strategy"] = sb_fetch.LocalStrategy.COPY
                            elif len(args) > 7:  # local_strategy is 8th positional arg
                                args = list(args)
                                if args[7] == sb_fetch.LocalStrategy.SYMLINK:
                                    args[7] = sb_fetch.LocalStrategy.COPY
                                args = tuple(args)
                            else:
                                kwargs.setdefault("local_strategy", sb_fetch.LocalStrategy.COPY)
                            return _original_fetch(*args, **kwargs)

                        sb_fetch.fetch = _patched_fetch
                        logger.info("Patched speechbrain fetch to use COPY strategy (Windows)")
                    except Exception as patch_err:
                        logger.warning("Could not patch speechbrain fetch: %s", patch_err)

                # speechbrain 1.0+ moved pretrained → speechbrain.inference
                try:
                    from speechbrain.inference.speaker import SpeakerRecognition
                    self._embedding_model = SpeakerRecognition.from_hparams(
                        source="speechbrain/spkrec-ecapa-voxceleb",
                        savedir="storage/models/spkrec-ecapa",
                        run_opts={"device": "cpu"},
                    )
                except ImportError:
                    from speechbrain.pretrained import EncoderClassifier
                    self._embedding_model = EncoderClassifier.from_hparams(
                        source="speechbrain/spkrec-ecapa-voxceleb",
                        savedir="storage/models/spkrec-ecapa",
                        run_opts={"device": "cpu"},
                    )
                logger.info("SpeechBrain ECAPA-TDNN model loaded (CPU)")
            except Exception as e:
                logger.error("Failed to load speaker embedding model: %s", e, exc_info=True)
                raise
        return self._embedding_model

    # ------------------------------------------------------------------
    # Audio Preprocessing
    # ------------------------------------------------------------------
    @staticmethod
    def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio to target sample rate using linear interpolation."""
        if orig_sr == target_sr:
            return audio
        duration = len(audio) / orig_sr
        target_len = int(duration * target_sr)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    @staticmethod
    def _normalize(audio: np.ndarray) -> np.ndarray:
        """Peak-normalize audio to [-1, 1] range."""
        peak = np.max(np.abs(audio))
        if peak > 0:
            return (audio / peak).astype(np.float32)
        return audio

    @staticmethod
    def _remove_silence(audio: np.ndarray, sr: int,
                        frame_ms: int = 30, energy_threshold: float = 0.01) -> np.ndarray:
        """
        Remove low-energy (silent) frames from audio.
        Keeps only frames where RMS energy exceeds threshold.
        """
        frame_len = int(sr * frame_ms / 1000)
        voiced_frames = []

        for i in range(0, len(audio) - frame_len, frame_len):
            frame = audio[i:i + frame_len]
            rms = np.sqrt(np.mean(frame ** 2))
            if rms > energy_threshold:
                voiced_frames.append(frame)

        if not voiced_frames:
            return audio  # fallback: return original if all frames are "silent"
        return np.concatenate(voiced_frames).astype(np.float32)

    @staticmethod
    def _bandpass_filter(audio: np.ndarray, sr: int,
                         low_hz: int = 80, high_hz: int = 7600) -> np.ndarray:
        """
        Apply a simple FFT-based bandpass filter to keep only the speech band.
        Removes low-frequency rumble and high-frequency noise.
        """
        try:
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), d=1.0 / sr)
            fft[(freqs < low_hz) | (freqs > high_hz)] = 0
            return np.fft.irfft(fft, n=len(audio)).astype(np.float32)
        except Exception:
            return audio  # fallback on error

    def _preprocess_audio(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Full preprocessing pipeline:
          1. Resample to 16kHz
          2. Peak normalize
          3. Bandpass filter (80Hz-7600Hz)
          4. Remove silent frames
          5. Re-normalize after filtering
        """
        # Step 1: Resample
        audio = self._resample(audio, sr, TARGET_SAMPLE_RATE)

        # Step 2: Normalize
        audio = self._normalize(audio)

        # Step 3: Bandpass filter to speech frequencies
        audio = self._bandpass_filter(audio, TARGET_SAMPLE_RATE)

        # Step 4: Remove silence
        audio = self._remove_silence(audio, TARGET_SAMPLE_RATE)

        # Step 5: Re-normalize after filtering
        audio = self._normalize(audio)

        return audio

    # ------------------------------------------------------------------
    # Clip extraction
    # ------------------------------------------------------------------
    def extract_speaker_clips(self, meeting_id: str) -> Dict[str, str]:
        """
        Extract a ~10-second audio clip for each speaker in a meeting.
        Preprocesses each clip for optimal embedding quality.

        Returns: dict mapping speaker_id → clip file path
        """
        audio_path = AUDIO_DIR / f"{meeting_id}.wav"
        transcript_path = STORAGE_DIR / meeting_id / "transcript.json"

        if not audio_path.exists() or not transcript_path.exists():
            logger.warning("[%s] Audio or transcript missing, skipping clip extraction", meeting_id)
            return {}

        # Load audio
        audio_data, sample_rate = sf.read(str(audio_path))
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Load transcript segments
        with open(transcript_path, "r", encoding="utf-8") as f:
            tdata = json.load(f)
        segments = tdata.get("segments", [])

        if not segments:
            return {}

        # Group segments by speaker
        speaker_segments: Dict[str, List[dict]] = {}
        for seg in segments:
            spk = seg.get("speaker", "UNKNOWN")
            if spk == "UNKNOWN":
                continue
            if spk not in speaker_segments:
                speaker_segments[spk] = []
            speaker_segments[spk].append(seg)

        # Create clips directory
        clips_dir = STORAGE_DIR / meeting_id / "speaker_clips"
        clips_dir.mkdir(parents=True, exist_ok=True)

        result = {}
        for spk_id, segs in speaker_segments.items():
            try:
                clip_path = clips_dir / f"{spk_id}.wav"
                clip_audio = self._build_clip(audio_data, sample_rate, segs)

                if clip_audio is not None and len(clip_audio) > 0:
                    # Preprocess the clip for better embedding quality
                    processed = self._preprocess_audio(clip_audio, sample_rate)
                    duration = len(processed) / TARGET_SAMPLE_RATE

                    if duration < MIN_CLIP_DURATION:
                        logger.warning("[%s] Clip for %s too short (%.1fs), using raw",
                                       meeting_id, spk_id, duration)
                        # Fallback: save raw resampled audio
                        processed = self._resample(clip_audio, sample_rate, TARGET_SAMPLE_RATE)
                        processed = self._normalize(processed)

                    # Save at 16kHz (model-ready)
                    sf.write(str(clip_path), processed, TARGET_SAMPLE_RATE)
                    result[spk_id] = str(clip_path)
                    duration = len(processed) / TARGET_SAMPLE_RATE
                    logger.info("[%s] ✅ Preprocessed clip saved: %s (%.1fs, 16kHz)",
                                meeting_id, spk_id, duration)
            except Exception as e:
                logger.warning("[%s] Clip extraction failed for %s: %s", meeting_id, spk_id, e)

        return result

    def _build_clip(self, audio_data: np.ndarray, sample_rate: int,
                    segments: list) -> Optional[np.ndarray]:
        """
        Build a ~10-second clip from a speaker's segments.
        Strategy: pick segments with highest energy (clearest speech), sorted by
        signal-to-noise quality, not just duration.
        """
        target_samples = int(TARGET_CLIP_DURATION * sample_rate)

        # Score each segment by energy (prefer louder, clearer speech)
        scored_segs = []
        for seg in segments:
            start_sample = max(0, int(seg.get("start", 0) * sample_rate))
            end_sample = min(len(audio_data), int(seg.get("end", 0) * sample_rate))
            if end_sample <= start_sample:
                continue
            chunk = audio_data[start_sample:end_sample]
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            duration = len(chunk) / sample_rate
            # Score: prefer longer + louder segments (quality indicator)
            score = rms * min(duration, 5.0)  # cap at 5s to avoid boosting very long segments
            scored_segs.append((seg, score, chunk))

        # Sort by quality score (best first)
        scored_segs.sort(key=lambda x: x[1], reverse=True)

        collected = []
        total_samples = 0

        for seg, score, chunk in scored_segs:
            collected.append(chunk)
            total_samples += len(chunk)
            if total_samples >= target_samples:
                break

        if not collected:
            return None

        clip = np.concatenate(collected)

        # Trim to exactly target duration
        if len(clip) > target_samples:
            clip = clip[:target_samples]

        return clip

    # ------------------------------------------------------------------
    # Embedding generation
    # ------------------------------------------------------------------
    def generate_embedding(self, clip_path: str) -> Optional[List[float]]:
        """
        Generate a speaker embedding vector from a preprocessed WAV clip.
        Returns a list of floats (embedding vector) or None on failure.
        """
        try:
            import torch

            model = self._get_model()

            # Use soundfile instead of torchaudio to avoid torchcodec/FFmpeg dependency
            audio_data, fs = sf.read(clip_path)

            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            # Resample to 16kHz if needed
            if fs != 16000:
                audio_data = self._resample(audio_data, fs, 16000)

            # Convert numpy array to torch tensor [1, num_samples]
            signal = torch.tensor(audio_data, dtype=torch.float32).unsqueeze(0)

            # Normalize signal for model
            signal = signal / (signal.abs().max() + 1e-8)

            embedding = model.encode_batch(signal)
            emb_list = embedding.squeeze().tolist()

            logger.info("Embedding generated for %s (%d dims, signal_len=%d)",
                        clip_path, len(emb_list), signal.shape[1])
            return emb_list

        except Exception as e:
            logger.error("Embedding generation failed for %s: %s", clip_path, e, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Profile storage
    # ------------------------------------------------------------------
    def save_speaker_profile(self, name: str, embedding: List[float]):
        """
        Save a speaker name → embedding mapping to global profiles.
        If a profile already exists for this name, averages the new embedding
        with the stored one for better cross-meeting accuracy.
        """
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        profiles_path = PROFILES_DIR / "profiles.json"

        profiles = {}
        if profiles_path.exists():
            try:
                with open(profiles_path, "r", encoding="utf-8") as f:
                    profiles = json.load(f)
            except Exception:
                profiles = {}

        # Average with existing embedding if present (running average)
        if name in profiles:
            existing = np.array(profiles[name], dtype=np.float64)
            new = np.array(embedding, dtype=np.float64)
            averaged = ((existing + new) / 2.0).tolist()
            profiles[name] = averaged
            logger.info("✅ Speaker profile updated (averaged): '%s' (%d-dim)", name, len(averaged))
        else:
            profiles[name] = embedding
            logger.info("✅ Speaker profile created: '%s' (%d-dim embedding)", name, len(embedding))

        with open(profiles_path, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2)

    def load_profiles(self) -> Dict[str, List[float]]:
        """Load all stored speaker profiles."""
        profiles_path = PROFILES_DIR / "profiles.json"
        if not profiles_path.exists():
            return {}
        try:
            with open(profiles_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Speaker matching
    # ------------------------------------------------------------------
    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_arr = np.array(a, dtype=np.float64)
        b_arr = np.array(b, dtype=np.float64)
        dot = np.dot(a_arr, b_arr)
        norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm == 0:
            return 0.0
        return float(dot / norm)

    def match_speakers(self, meeting_id: str, threshold: float = 0.55) -> Dict[str, str]:
        """
        Match speakers in a meeting against stored profiles.
        Uses cosine similarity with a threshold (default 0.55).

        Logs ALL similarity scores for verification/debugging.

        Returns: dict mapping speaker_id → matched_name (only for matches above threshold)
        """
        profiles = self.load_profiles()
        if not profiles:
            logger.info("[%s] No stored profiles, skipping auto-match", meeting_id)
            return {}

        clips_dir = STORAGE_DIR / meeting_id / "speaker_clips"
        if not clips_dir.exists():
            return {}

        logger.info("[%s] 🔍 Starting speaker matching against %d stored profiles: %s",
                    meeting_id, len(profiles), list(profiles.keys()))

        matches = {}
        used_names = set()  # prevent assigning same name to multiple speakers

        # Generate all embeddings first
        speaker_embeddings = {}
        for clip_file in sorted(clips_dir.glob("*.wav")):
            spk_id = clip_file.stem
            embedding = self.generate_embedding(str(clip_file))
            if embedding is not None:
                speaker_embeddings[spk_id] = embedding

        # Match each speaker, log ALL scores
        for spk_id, embedding in speaker_embeddings.items():
            scores = {}
            for name, stored_emb in profiles.items():
                score = self.cosine_similarity(embedding, stored_emb)
                scores[name] = round(score, 4)

            # Sort by score descending for clear logging
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            score_str = " | ".join([f"{n}: {s:.4f}" for n, s in sorted_scores])
            logger.info("[%s] 📊 %s similarity scores → %s", meeting_id, spk_id, score_str)

            # Find best match above threshold, not already used
            best_name = None
            best_score = 0.0
            for name, score in sorted_scores:
                if score >= threshold and name not in used_names:
                    best_name = name
                    best_score = score
                    break

            if best_name:
                matches[spk_id] = best_name
                used_names.add(best_name)
                logger.info("[%s] ✅ MATCH: %s → '%s' (score=%.4f, threshold=%.2f)",
                            meeting_id, spk_id, best_name, best_score, threshold)
            else:
                top_name, top_score = sorted_scores[0] if sorted_scores else ("none", 0)
                logger.info("[%s] ❌ NO MATCH for %s (best: '%s' at %.4f, threshold=%.2f)",
                            meeting_id, spk_id, top_name, top_score, threshold)

        logger.info("[%s] 🏁 Matching complete: %d/%d speakers matched → %s",
                    meeting_id, len(matches), len(speaker_embeddings), matches)
        return matches
