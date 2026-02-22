# ContextIQ — Meeting Intelligence Platform

> Upload a meeting video → get **speaker-diarized transcription**, **AI summaries** (English + Hindi), **action items & decisions**, **follow-up email draft**, **RAG-powered chatbot with streaming**, and **one-click PDF/Email/Teams publishing** — all privacy-first, running locally on your GPU.

---

## ✨ Features

### 🎬 Ingestion & Processing
| # | Feature | Details |
|---|---------|---------|
| 1 | **Video Upload** | Accepts `.mp4`, `.mkv`, `.mov` — extracts 16 kHz mono WAV via FFmpeg |
| 2 | **Upload Deduplication** | SHA-256 hashing prevents reprocessing duplicate files |
| 3 | **Auto Audio Extraction** | FFmpeg-based, supports all major codecs |

### 🗣️ Transcription & Diarization
| # | Feature | Details |
|---|---------|---------|
| 4 | **WhisperX STT** | Fast CTranslate2 engine with word-level timestamps |
| 5 | **Speaker Diarization** | pyannote.audio 3.1 identifies individual speakers |
| 6 | **GPU Acceleration** | Auto-detects NVIDIA CUDA GPUs (3–5× faster), sequential VRAM offloading for 4GB GPUs |
| 7 | **Auto Metadata** | Processing timestamps, segment/speaker counts auto-saved after transcription |

### 🤖 AI Intelligence (Groq Llama 3.3 70B)
| # | Feature | Details |
|---|---------|---------|
| 8 | **Bilingual Summaries** | Speaker-wise + overall summaries in English & Hindi |
| 9 | **Action Items Extraction** | Structured tasks with assignee, deadline, priority (🔴🟡🟢) |
| 10 | **Decisions Tracker** | Who decided what and why — extracted automatically |
| 11 | **Key Takeaways & Follow-ups** | Bullet-point highlights from every meeting |
| 12 | **Auto Meeting Title** | AI-generated descriptive title saved to metadata |
| 13 | **Follow-Up Email Draft** | Professional email combining summary + action items + decisions |

### 💬 RAG Chatbot
| # | Feature | Details |
|---|---------|---------|
| 14 | **Multi-Meeting Q&A** | Ask questions across ALL meetings via LangChain + ChromaDB |
| 15 | **SSE Streaming** | Real-time token-by-token responses with blinking cursor (▌) |
| 16 | **Source Citations** | Every answer cites speaker, timestamp, and meeting ID |
| 17 | **Session Memory** | Conversation history maintained per session |

### 👤 Human-in-the-Loop (HITL)
| # | Feature | Details |
|---|---------|---------|
| 18 | **Speaker Name Mapping** | Map `SPEAKER_00` → real names; persists across all views |
| 19 | **Summary Approval** | Review, edit, and approve AI summaries before publishing |
| 20 | **Custom Rewrite** | Provide instructions to regenerate summaries with different style |

### 📄 Publishing & Export
| # | Feature | Details |
|---|---------|---------|
| 21 | **PDF Generation** | Professional layout with Unicode Hindi support (NotoSansDevanagari) |
| 22 | **Email Publishing** | SMTP delivery with PDF attachment |
| 23 | **Teams Webhook** | Microsoft Teams Adaptive Card with summary + speaker breakdowns |
| 24 | **Transcript Editing** | Edit individual segments (text/speaker) via API |

### 🖥️ Platform
| # | Feature | Details |
|---|---------|---------|
| 25 | **Premium Streamlit UI** | Dark-themed, gradient-accented, 5-tab dashboard (1300+ lines) |
| 26 | **Health Check** | `GET /health` — GPU status, VRAM, storage stats, meeting breakdown |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                           │
│                 Streamlit UI (streamlit_app.py)                   │
│  Upload │ Chat View │ Speaker │ Timeline │ Summaries │ Actions  │
│                   + Meeting Chat (SSE Streaming)                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │ REST API (HTTP + SSE)
┌─────────────────────────────▼───────────────────────────────────┐
│                       API LAYER (FastAPI)                         │
│  upload │ transcribe │ diarization │ summarize │ publish │ chat │
│              speaker_map │ insights (new) │ health              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      SERVICES LAYER                               │
│  stt_service │ rag_service │ summary_service │ publish_service  │
│  insights_service (new) │ speaker_service │ storage_service     │
│                        video_to_audio                            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                   EXTERNAL AI SERVICES                            │
│  Groq API (Llama 3.3 70B) │ WhisperX (local) │ pyannote (local)│
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    DATA & STORAGE LAYER                            │
│  storage/ (JSON) │ ChromaDB (vectors) │ data/audio/ (WAV)       │
│                    _file_hashes.json (dedup)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
ContextIQ/
├── app/
│   ├── main.py                        # FastAPI entry point, router registration, health check
│   ├── api/
│   │   ├── upload.py                  # POST /upload-video (SHA-256 dedup)
│   │   ├── transcribe.py             # POST /transcribe/{meeting_id} (auto-metadata)
│   │   ├── diarization.py            # GET /meeting/{meeting_id}, PUT segments, metadata
│   │   ├── summarize.py              # POST /summarize/{meeting_id}
│   │   ├── publish.py                # POST /publish, GET /publish/{id}/pdf
│   │   ├── speaker_map.py            # POST/GET speaker-map
│   │   ├── chat.py                   # POST /chat/ask, /chat/ask/stream (SSE)
│   │   └── insights.py              # POST action-items, auto-title, followup-email ← NEW
│   ├── services/
│   │   ├── stt_service.py            # WhisperX + pyannote (GPU offloading)
│   │   ├── rag_service.py            # LangChain + ChromaDB + Groq RAG
│   │   ├── summary_service.py        # Groq Llama 3.3 70B summarization
│   │   ├── insights_service.py      # Action items + auto title + email draft ← NEW
│   │   ├── publish_service.py        # PDF (fpdf2) + SMTP + Teams webhook
│   │   ├── speaker_service.py        # Speaker segment grouping
│   │   ├── storage_service.py        # JSON persistence
│   │   └── video_to_audio.py         # FFmpeg extraction
│   ├── schemas/schemas.py            # Pydantic v2 models
│   └── fonts/                        # NotoSans + NotoSansDevanagari TTF
├── ui/
│   └── streamlit_app.py              # Premium Streamlit frontend (1300+ lines)
├── docs/                              # Architecture, workflow, class diagrams (.drawio)
├── storage/                           # Runtime: transcripts, summaries, action items, emails
│   ├── {meeting_id}/                 # Per-meeting data folder
│   └── chroma_db/                    # ChromaDB vector store
├── data/audio/                        # Extracted WAV files
├── requirements.txt
└── .env                               # Environment configuration
```

---

## 🔄 Processing Pipeline

```mermaid
flowchart LR
    A["📹 Upload Video"] --> B["🎵 Extract Audio<br/>(FFmpeg)"]
    B --> C["🗣️ Transcribe + Diarize<br/>(WhisperX + pyannote)"]
    C --> D["💾 Save Transcript<br/>(JSON + metadata)"]
    D --> E["🤖 AI Summary<br/>(Groq Llama 3.3 70B)"]
    D --> F["💬 RAG Chat<br/>(ChromaDB + Groq SSE)"]
    D --> G["🎯 Action Items<br/>(Groq extraction)"]
    D --> H["🖥️ Interactive Views<br/>(Streamlit 5-tab UI)"]
    E --> I["✅ Human Review<br/>(HITL approval)"]
    G --> J["✉️ Follow-Up Email<br/>(AI draft)"]
    I --> K["📄 Publish<br/>(PDF + Email + Teams)"]
```

---

## 📡 API Reference (21 Endpoints)

### Upload & Transcription
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload-video` | Upload video, extract audio (SHA-256 dedup) |
| `POST` | `/transcribe/{meeting_id}` | Transcribe + diarize + auto-metadata |
| `GET` | `/meeting/{meeting_id}` | Retrieve saved transcript |
| `PUT` | `/meeting/{meeting_id}/segments/{index}` | Edit a transcript segment |
| `GET` | `/meeting/{meeting_id}/metadata` | Get meeting metadata |
| `PATCH` | `/meeting/{meeting_id}/metadata` | Update meeting metadata |

### AI Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/summarize/{meeting_id}` | Generate bilingual summaries |
| `POST` | `/meeting/{meeting_id}/action-items` | Extract action items & decisions |
| `POST` | `/meeting/{meeting_id}/auto-title` | Generate AI meeting title |
| `POST` | `/meeting/{meeting_id}/followup-email` | Draft follow-up email |

### RAG Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/ask` | Ask question (standard response) |
| `POST` | `/chat/ask/stream` | Ask question (SSE streaming) |
| `POST` | `/chat/index/{meeting_id}` | Index meeting for RAG |
| `GET` | `/chat/meetings` | List indexed meetings |
| `POST` | `/chat/clear/{session_id}` | Clear chat session |

### Publishing & HITL
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/publish/{meeting_id}` | Generate PDF + send Email/Teams |
| `GET` | `/publish/{meeting_id}/pdf` | Download PDF |
| `POST` | `/meeting/{meeting_id}/speaker-map` | Save speaker names |
| `GET` | `/meeting/{meeting_id}/speaker-map` | Get speaker names |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info + all endpoints |
| `GET` | `/health` | GPU, storage, ChromaDB status |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------:|
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | Streamlit (premium dark theme) |
| **Transcription** | WhisperX (CTranslate2) |
| **Diarization** | pyannote.audio 3.1 |
| **LLM** | Llama 3.3 70B via Groq (⚡ ~500 tok/sec) |
| **RAG** | LangChain + ChromaDB |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` (local) |
| **PDF** | fpdf2 (Unicode Hindi) |
| **Email** | SMTP (smtplib) |
| **Teams** | Microsoft Incoming Webhook |
| **Audio** | FFmpeg |
| **Validation** | Pydantic v2 |
| **ML** | PyTorch (CUDA 12.8) |
| **Streaming** | Server-Sent Events (SSE) |

---

## 🚀 Quick Start

### Prerequisites

| Tool | Why |
|------|-----|
| **Python 3.10+** | Runtime |
| **FFmpeg** | Video → audio extraction |
| **NVIDIA GPU + CUDA** *(optional)* | 3–5× faster transcription |
| **HuggingFace account** | Access pyannote diarization models |
| **Groq API key** | LLM inference ([get free key](https://console.groq.com/keys)) |

### Setup

```bash
git clone https://github.com/pawanuikey06/ContextIQ.git
cd ContextIQ
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
pip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### Configure `.env`

```env
FFMPEG_PATH=C:/path/to/ffmpeg.exe
HF_TOKEN=hf_your_huggingface_token
GROQ_API_KEY=gsk_your_groq_api_key

# Optional
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your-app-password
TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/...
```

### Run

```bash
python -m uvicorn app.main:app --reload --port 8000   # Backend
streamlit run ui/streamlit_app.py                       # Frontend
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |

---



---

## 📝 License

MIT
