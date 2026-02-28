# Multi-Engine Speech-to-Text (STT) Architecture

## 🎙️ Overview

ContextIQ implements a **Multi-Engine Speech-to-Text (STT)** pipeline that allows users to choose the transcription strategy that best fits their needs for privacy, accuracy, and speed. The system abstracts three entirely different transcription engines behind a single, unified interface (`AudioTranscriptionService`).

Regardless of the engine chosen, the final output is standardized: a transcript with highly accurate word-level timestamps and speaker labels (diarization), formatted as a unified JSON structure.

---

## ⚙️ The Three Engines

The active engine is determined by the frontend user selection or the `STT_MODE` environment variable.

### 1. Local WhisperX (High Privacy & Accuracy)
- **Engine**: `whisperx` (Open-source, runs locally on GPU)
- **Model**: Whisper `medium`
- **How it works**:
  1. Loads the audio into VRAM.
  2. Transcribes the audio using the Whisper model.
  3. Uses a secondary `wav2vec2` model to perform **forced alignment**, locking the timestamps to exact word boundaries.
  4. Passes the aligned audio through a local `pyannote.audio` diarization pipeline.
- **Pros**: 100% private (no data leaves the machine), highly accurate timestamps.
- **Cons**: Requires dedicated GPU hardware (VRAM), slower than cloud APIs.

### 2. Groq Whisper API (Ultra-Fast)
- **Engine**: `groq`
- **Model**: `whisper-large-v3-turbo` (via Groq LPU inference)
- **How it works**:
  1. Audio file size is checked (must be <25 MB for Groq).
  2. Audio is sent to Groq's API, which returns the transcription text and segments at lightning speed.
  3. **Note:** Groq *does not* support native speaker diarization. Therefore, the system falls back to downloading the audio and running the local `pyannote.audio` model to detect speakers.
- **Pros**: Blazing fast transcription, uses the largest Whisper model.
- **Cons**: Requires an internet connection and a Groq API key; audio size limits.

### 3. AssemblyAI (Cloud API & Native Diarization)
- **Engine**: `assemblyai`
- **Model**: `universal-2`
- **How it works**:
  1. The audio file is uploaded to AssemblyAI.
  2. AssemblyAI handles *both* the transcription and the speaker diarization in a single remote process.
  3. ContextIQ leverages the `speakers_expected` hint (if provided in `.env`) to improve speaker count accuracy.
  4. The returned `utterances` are parsed directly into the ContextIQ standard format.
- **Pros**: Best-in-class speaker diarization out of the box, zero local GPU usage required.
- **Cons**: Cloud dependency, requires AssemblyAI API key.

---

## 🔄 The Processing Pipeline

The pipeline is managed by `app/services/stt_service.py` and follows this flow:

### 1. Audio Preprocessing
Before any engine touches the audio, it is preprocessed to maximize accuracy:
- **Noise Reduction (`noisereduce`)**: Applies spectral gating to remove static background hums.
- **Audio Normalization (`pydub`)**: Balances the volume to ensure quiet speakers are heard by the neural networks.
*(Saves as `{meeting_id}_clean.wav`)*

### 2. Transcription Execution
The unified method `_transcribe(audio_path)` routes the audio to the selected engine (`_transcribe_local`, `_transcribe_groq`, or `_transcribe_assemblyai`).

### 3. Speaker Diarization (The "Who Spoke When")
If the engine does **not** provide native diarization (i.e., WhisperX and Groq):
- The system loads the `pyannote/speaker-diarization-3.1` pipeline from HuggingFace.
- The pipeline analyzes the audio to output a list of time segments (start, end) and the detected speaker (e.g., `SPEAKER_00`).

### 4. Segment Alignment (`_assign_speakers_from_diarization`)
When diarization is run independently of transcription (Groq/WhisperX), the two outputs must be merged:
- The system loops through every generated transcript segment (text + timestamps).
- It calculates the **time overlap** between the transcript segment and the diarization segments.
- It assigns the speaker label of the diarization segment that has the *highest overlap* with the transcript segment.

---

## 📤 Standardized Output Format

Regardless of which engine does the heavy lifting, the final shape returned to the rest of the application is always identical:

```json
{
  "language": "en",
  "segments": [
    {
      "start": 12.05,
      "end": 15.30,
      "text": "Let's review the Q3 roadmap.",
      "speaker": "SPEAKER_00"
    },
    {
      "start": 16.10,
      "end": 18.45,
      "text": "I think the database migration takes priority.",
      "speaker": "SPEAKER_01"
    }
  ]
}
```

This strict standardization guarantees that downstream services (Summarization, Speaker Grouping, Prompt Building) do not need to know which STT engine was used.

---
*Document Version: 1.0*
*Architecture Reference: `app/services/stt_service.py`*
