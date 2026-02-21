import os
import whisperx
from dotenv import load_dotenv
from whisperx.diarize import DiarizationPipeline
 
load_dotenv()
 
 
class AudioTranscriptionService:
    """
    FAST WhisperX transcription with speaker diarization.
    - No alignment
    - CPU optimized
    - Old logic preserved
    """
 
    def __init__(self, device="cpu", compute_type="int8"):
        self.device = device
        self.compute_type = compute_type
 
        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            raise ValueError("HF_TOKEN not found in environment")
 
        # Load models ONCE (important for speed)
        self.asr_model = whisperx.load_model(
            "base",
            device=self.device,
            compute_type=self.compute_type
        )
 
        self.diarize_model = DiarizationPipeline(
            model_name="pyannote/speaker-diarization",
            device=self.device
        )
 
    def transcribe(self, audio_path: str) -> dict:
        # 1️⃣ Load audio
        audio = whisperx.load_audio(audio_path)
 
        # 2️⃣ Transcribe (FAST)
        result = self.asr_model.transcribe(audio)
 
        # 3️⃣ Diarization (FAST)
        diarization = self.diarize_model(audio)
 
        # 4️⃣ Assign speakers (NO ALIGNMENT)
        result = whisperx.assign_word_speakers(
            diarization,
            result
        )
 
        # 5️⃣ Normalize output
        segments = []
        for seg in result["segments"]:
            segments.append({
                "start": round(seg.get("start", 0.0), 2),
                "end": round(seg.get("end", 0.0), 2),
                "speaker": seg.get("speaker", "UNKNOWN"),
                "text": seg.get("text", "").strip()
            })
 
        return {
            "language": result.get("language", "unknown"),
            "segments": segments
        }
 