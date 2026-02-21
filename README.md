# ContextIQ — Meeting Intelligence System

> Upload a meeting video → get **speaker-diarized**, **timestamped** transcription — powered by WhisperX + pyannote.

---

## ✨ Features

- **Video Upload** — Accepts `.mp4`, `.mkv`, `.mov` files and extracts 16 kHz mono WAV audio via FFmpeg
- **WhisperX Transcription** — Fast speech-to-text using the WhisperX `base` model
- **Speaker Diarization** — Identifies and labels individual speakers using pyannote.audio 3.1
- **GPU Accelerated** — Auto-detects NVIDIA CUDA GPUs (3–5× faster than CPU)
- **Streamlit UI** — Interactive frontend with Chat View, Speaker View, and Timestamp Table
- **JSON Export** — Download full transcript with speaker labels and timestamps
- **Persistent Storage** — Transcripts saved to `storage/{meeting_id}/transcript.json`

---

## 🏗️ Architecture

```
ContextIQ/
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── api/
│   │   ├── upload.py              # POST /upload-video
│   │   ├── transcribe.py          # POST /transcribe/{meeting_id}
│   │   └── diarization.py         # GET  /meeting/{meeting_id}
│   ├── services/
│   │   ├── stt_service.py         # WhisperX transcription + diarization
│   │   ├── speaker_service.py     # Speaker-wise segment grouping
│   │   ├── storage_service.py     # JSON persistence to disk
│   │   └── video_to_audio.py      # FFmpeg video → WAV extraction
│   └── schemas/
│       └── schemas.py             # Pydantic request/response models
├── ui/
│   └── streamlit_app.py           # Streamlit frontend
├── data/audio/                    # Extracted WAV files (auto-created)
├── storage/                       # Saved transcript JSONs (auto-created)
├── requirements.txt
└── .env                           # Environment variables (see below)
```

---

## 🚀 Quick Start

### 1. Prerequisites

| Tool | Why |
|------|-----|
| **Python 3.10+** | Runtime |
| **FFmpeg** | Video → audio extraction |
| **NVIDIA GPU + CUDA** *(optional)* | 3–5× faster transcription |
| **HuggingFace account** | Access pyannote diarization models |

> **Diarization model access:** Accept the licenses at:
> - https://huggingface.co/pyannote/speaker-diarization-3.1
> - https://huggingface.co/pyannote/segmentation-3.0

### 2. Clone & Setup

```bash
git clone <repo-url>
cd ContextIQ
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
```

### 3. Install Dependencies

**With NVIDIA GPU (recommended):**
```bash
pip install -r requirements.txt
pip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

**CPU only:**
```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `.env` file in the project root:

```env
FFMPEG_PATH=C:/path/to/ffmpeg.exe
HF_TOKEN=hf_your_huggingface_token
OPENAI_API_KEY=sk-your-openai-key
```

| Variable | Description |
|----------|-------------|
| `FFMPEG_PATH` | Absolute path to `ffmpeg.exe` binary |
| `HF_TOKEN` | HuggingFace access token ([create here](https://huggingface.co/settings/tokens)) |
| `OPENAI_API_KEY` | OpenAI API key (for future features) |

### 5. Run

**Start the backend:**
```bash
python -m uvicorn app.main:app --reload --port 8000
```

**Start the frontend (separate terminal):**
```bash
streamlit run ui/streamlit_app.py
```

- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Frontend:** http://localhost:8501

---

## 📡 API Endpoints

### `POST /upload-video`
Upload a video file and extract audio.

```bash
curl -X POST http://localhost:8000/upload-video \
  -F "file=@meeting.mp4"
```

**Response:**
```json
{
  "meeting_id": "a1b2c3d4-...",
  "audio_path": "data/audio/a1b2c3d4-....wav",
  "message": "Video uploaded and audio extracted successfully"
}
```

### `POST /transcribe/{meeting_id}`
Run transcription + speaker diarization on extracted audio.

```bash
curl -X POST http://localhost:8000/transcribe/a1b2c3d4-...
```

**Response:**
```json
{
  "meeting_id": "a1b2c3d4-...",
  "audio_path": "data/audio/a1b2c3d4-....wav",
  "segments": [
    { "start": 0.0, "end": 4.2, "speaker": "SPEAKER_00", "text": "Hello everyone" }
  ],
  "speakers": {
    "SPEAKER_00": [
      { "start": 0.0, "end": 4.2, "text": "Hello everyone" }
    ]
  }
}
```

### `GET /meeting/{meeting_id}`
Retrieve a previously saved transcript.

```bash
curl http://localhost:8000/meeting/a1b2c3d4-...
```

---

## 🖥️ Streamlit UI

The frontend provides three views for the transcript:

| Tab | Description |
|-----|-------------|
| 💬 **Chat View** | Color-coded conversation with speaker labels and timestamps |
| 🗣️ **Speaker View** | Expandable per-speaker grouping of all segments |
| 🕒 **Timestamp View** | Sortable table with Start, End, Speaker, and Text columns |

Plus a **Download Transcript JSON** button.

---

## ⚡ GPU Acceleration

The system auto-detects your GPU. To verify:

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

| Mode | Compute Type | Speed |
|------|-------------|-------|
| **CUDA GPU** | `float16` | ⚡ 3–5× faster |
| **CPU** | `int8` | 🐢 Baseline |

If CUDA shows `False`, reinstall PyTorch with CUDA:
```bash
pip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

---

## 📂 Output Format

Transcripts are saved to `storage/{meeting_id}/transcript.json`:

```json
{
  "created_at": "2026-02-21T16:00:00+00:00",
  "meeting_id": "a1b2c3d4-...",
  "audio_path": "data/audio/a1b2c3d4-....wav",
  "segments": [
    { "start": 0.0, "end": 4.2, "speaker": "SPEAKER_00", "text": "Hello everyone" },
    { "start": 4.5, "end": 8.1, "speaker": "SPEAKER_01", "text": "Hi, thanks for joining" }
  ],
  "speakers": {
    "SPEAKER_00": [
      { "start": 0.0, "end": 4.2, "text": "Hello everyone" }
    ],
    "SPEAKER_01": [
      { "start": 4.5, "end": 8.1, "text": "Hi, thanks for joining" }
    ]
  }
}
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Transcription | WhisperX (CTranslate2) |
| Diarization | pyannote.audio 3.1 |
| Audio Extraction | FFmpeg |
| Validation | Pydantic v2 |
| ML Framework | PyTorch (CUDA 12.8) |

---

## 📝 License

MIT
