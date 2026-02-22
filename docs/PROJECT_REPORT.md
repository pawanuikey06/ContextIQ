# ContextIQ — Detailed Project Report

**Project Title:** ContextIQ — Meeting Intelligence Platform  
**Author:** Pawan Uikey  
**Date:** February 22, 2026  
**Version:** 2.0.0

---

## 1. Executive Summary

ContextIQ is an end-to-end **Meeting Intelligence Platform** that transforms raw meeting video recordings into structured, searchable, and shareable knowledge. The system performs automatic speech-to-text transcription with speaker diarization, generates bilingual summaries (English + Hindi) using large language models, enables intelligent Q&A over meeting content using Retrieval-Augmented Generation (RAG), and delivers polished outputs via PDF, Email, and Microsoft Teams — all through a premium Streamlit web interface.

### Key Highlights

- **Fully automated pipeline:** Upload a video → get transcribed, summarized, and published
- **Multi-speaker recognition:** Identifies and labels individual speakers using pyannote.audio
- **GPU-accelerated:** 3–5× faster transcription on NVIDIA GPUs via CUDA
- **Bilingual AI summaries:** English + Hindi generation using Llama 3.3 70B via Groq
- **RAG-powered chatbot:** Semantic search + contextual Q&A across all meetings
- **Human-in-the-Loop (HITL):** Speaker name mapping + summary approval before publishing
- **One-click publishing:** PDF + Email (SMTP) + Microsoft Teams (Webhook)

---

## 2. Problem Statement

Organizations conduct numerous meetings daily, generating hours of unstructured audio/video content. Key decisions, action items, and critical discussions are often lost or poorly documented. Manual meeting notes are:

- **Time-consuming** — takes 30–60 minutes to summarize a 1-hour meeting
- **Incomplete** — note-takers miss details or introduce bias
- **Unsearchable** — information is locked in documents, not queryable
- **Inaccessible** — non-English speakers are excluded from meeting insights
- **Siloed** — sharing requires manual effort via email or messaging

ContextIQ solves all of these problems with an automated, AI-powered pipeline.

---

## 3. System Architecture

### 3.1 Architecture Overview

The system follows a **4-layer architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                 PRESENTATION LAYER                       │
│            Streamlit UI (streamlit_app.py)               │
│   Upload │ Chat View │ Speaker View │ Timeline │ Chat   │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (HTTP)
┌───────────────────────▼─────────────────────────────────┐
│                    API LAYER                              │
│                FastAPI (main.py)                          │
│   /upload │ /transcribe │ /summarize │ /publish │ /chat │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                  SERVICES LAYER                           │
│  STT │ RAG │ Summary │ Publish │ Speaker │ Storage │ FFmpeg│
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                 DATA & STORAGE LAYER                      │
│  storage/ (JSON) │ ChromaDB (vectors) │ data/audio/ (WAV)│
└─────────────────────────────────────────────────────────┘
```

> Full architecture diagram: `docs/architecture_diagram.drawio` / `docs/architecture_diagram.png`

### 3.2 Directory Structure

```
ContextIQ/
├── app/
│   ├── main.py                        # FastAPI entry point
│   ├── api/                           # 7 API route files
│   │   ├── upload.py                  # Video upload + audio extraction
│   │   ├── transcribe.py             # Transcription + diarization
│   │   ├── diarization.py            # Meeting transcript retrieval
│   │   ├── summarize.py              # AI summary generation
│   │   ├── publish.py                # PDF + Email + Teams
│   │   ├── speaker_map.py            # HITL speaker name mapping
│   │   └── chat.py                   # RAG chatbot endpoints
│   ├── services/                      # 7 service modules
│   │   ├── stt_service.py            # WhisperX + pyannote
│   │   ├── rag_service.py            # LangChain + ChromaDB + Groq
│   │   ├── summary_service.py        # Groq Llama 3.3 70B
│   │   ├── publish_service.py        # PDF (fpdf2) + SMTP + Teams
│   │   ├── speaker_service.py        # Speaker segment grouping
│   │   ├── storage_service.py        # JSON persistence
│   │   └── video_to_audio.py         # FFmpeg extraction
│   ├── schemas/schemas.py            # Pydantic v2 models
│   └── fonts/                        # NotoSans + Devanagari TTF
├── ui/streamlit_app.py               # Streamlit frontend (1100+ lines)
├── docs/                              # Diagrams (.drawio + .png)
├── storage/                           # Runtime meeting data
├── data/audio/                        # Extracted WAV files
├── requirements.txt                   # Python dependencies
└── .env                               # Environment configuration
```

---

## 4. Technology Stack

### 4.1 AI/ML Models

| Model | Purpose | Provider | Runs On |
|-------|---------|----------|---------|
| **WhisperX** (CTranslate2 `base`) | Speech-to-text transcription | Local | GPU (CUDA) / CPU |
| **pyannote.audio 3.1** | Speaker diarization | Local (HuggingFace) | GPU (CUDA) / CPU |
| **Llama 3.3 70B Versatile** | Meeting summarization (EN + HI) | Groq API | Cloud (Groq LPU) |
| **Llama 3.3 70B Versatile** | RAG chatbot Q&A | Groq API | Cloud (Groq LPU) |
| **all-MiniLM-L6-v2** | Text embeddings for ChromaDB | Local (HuggingFace) | CPU |

### 4.2 Framework & Libraries

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend API | FastAPI + Uvicorn | 0.109.2 |
| Frontend | Streamlit | 1.54.0 |
| LLM Orchestration | LangChain | 1.2.10 |
| Vector Database | ChromaDB | 1.5.1 |
| LLM Provider | Groq (OpenAI-compatible) | 1.0.0 |
| PDF Generation | fpdf2 | 2.8.6 |
| ML Framework | PyTorch + CUDA 12.8 | 2.10.0 |
| Data Validation | Pydantic v2 | 2.12.5 |
| Audio Processing | FFmpeg | External |

---

## 5. Module Descriptions

### 5.1 Video Upload & Audio Extraction

- **API:** `POST /upload-video` (`upload.py`)
- **Service:** `video_to_audio.py`
- **Process:** Accepts `.mp4`/`.mkv`/`.mov` files → FFmpeg extracts 16 kHz mono WAV → stored in `data/audio/`
- **Output:** Unique `meeting_id` (UUID) returned to client

### 5.2 Transcription & Speaker Diarization

- **API:** `POST /transcribe/{meeting_id}` (`transcribe.py`)
- **Service:** `stt_service.py`
- **Process:**
  1. Load WhisperX model (CTranslate2 backend, auto-detects GPU/CPU)
  2. Transcribe audio → word-level timestamps
  3. Align transcription with audio using WhisperX alignment model
  4. Run pyannote.audio speaker diarization pipeline
  5. Assign speaker labels to each segment
- **Output:** `transcript.json` with segments (speaker, start, end, text) + speaker-wise grouping

### 5.3 AI Summarization

- **API:** `POST /summarize/{meeting_id}` (`summarize.py`)
- **Service:** `summary_service.py`
- **LLM:** Llama 3.3 70B Versatile via Groq API
- **Generates:**
  - Speaker-wise summaries in English (one per speaker)
  - Overall meeting summary in English
  - Overall meeting summary in Hindi (हिंदी)
- **Features:** Caching (skip if already generated), force regeneration, custom prompt injection, speaker name mapping applied
- **Output:** `summary.json`

### 5.4 RAG Chatbot

- **API:** `POST /chat/ask`, `POST /chat/index/{meeting_id}`, `GET /chat/meetings` (`chat.py`)
- **Service:** `rag_service.py`
- **Architecture:**
  1. **Ingestion:** Meeting transcript chunked by speaker segment → embedded using `all-MiniLM-L6-v2` → stored in ChromaDB
  2. **Query:** User question → semantic search in ChromaDB → top-10 relevant segments retrieved → context + question sent to Llama 3.3 70B via Groq → answer with source citations returned
- **Features:** Session-based conversation memory, meeting-filtered queries, meeting calendar awareness (date/day-based queries), source citations with speaker + timestamp

### 5.5 Publishing

- **API:** `POST /publish/{meeting_id}`, `GET /publish/{meeting_id}/pdf` (`publish.py`)
- **Service:** `publish_service.py`
- **PDF:** Professional layout with fpdf2, Unicode Hindi support (NotoSansDevanagari font), header/footer branding, speaker summary blocks
- **Email:** SMTP delivery with PDF attachment (Gmail app password support)
- **Teams:** Microsoft Incoming Webhook with Adaptive Card (title, summary, speaker breakdowns)
- **Output:** `Meeting_Summary.pdf` in `storage/{meeting_id}/`

### 5.6 Speaker Name Mapping (HITL)

- **API:** `POST/GET /meeting/{meeting_id}/speaker-map` (`speaker_map.py`)
- **Process:** Users manually assign real names to detected speaker IDs (e.g., `SPEAKER_00` → `Pawan`)
- **Persistence:** Saved to `speaker_map.json`, applied across all views (Chat, Speaker, Timeline, Summaries)

### 5.7 Frontend (Streamlit UI)

- **File:** `ui/streamlit_app.py` (1100+ lines)
- **Design:** Premium dark theme with gradient accents, glassmorphism effects, Inter font
- **Pages:**
  - **Meeting Processing:** Upload → Transcribe → View (Chat/Speaker/Timeline) → Summarize → Publish
  - **Meeting Chat:** RAG-powered Q&A with indexed meetings, source citations, session management

---

## 6. API Reference

### 6.1 Complete Endpoint Listing

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | `POST` | `/upload-video` | Upload video, extract audio |
| 2 | `POST` | `/transcribe/{meeting_id}` | Transcribe + diarize |
| 3 | `GET` | `/meeting/{meeting_id}` | Get saved transcript |
| 4 | `POST` | `/summarize/{meeting_id}` | Generate AI summaries |
| 5 | `POST` | `/publish/{meeting_id}` | Publish (PDF + Email + Teams) |
| 6 | `GET` | `/publish/{meeting_id}/pdf` | Download PDF |
| 7 | `POST` | `/chat/ask` | Ask question (RAG) |
| 8 | `POST` | `/chat/index/{meeting_id}` | Index meeting for RAG |
| 9 | `GET` | `/chat/meetings` | List indexed meetings |
| 10 | `POST` | `/chat/clear/{session_id}` | Clear chat history |
| 11 | `POST` | `/meeting/{meeting_id}/speaker-map` | Save speaker map |
| 12 | `GET` | `/meeting/{meeting_id}/speaker-map` | Get speaker map |

### 6.2 Data Schemas

| Schema | Fields | Used In |
|--------|--------|---------|
| `SegmentOut` | start, end, speaker, text | Transcription responses |
| `SpeakerSegment` | start, end, text | Speaker-grouped segments |
| `UploadResponse` | meeting_id, audio_path, message | Upload endpoint |
| `TranscriptResponse` | meeting_id, audio_path, segments, speakers | Transcription endpoint |
| `SummaryResponse` | meeting_id, speaker_summaries_en, overall_summary_en, overall_summary_hi | Summary endpoint |
| `ChatRequest` | question, session_id, meeting_ids | Chat endpoint |
| `ChatResponse` | answer, citations | Chat endpoint |
| `PublishRequest` | meeting_title, date, email_recipients, teams_webhook_url | Publish endpoint |

---

## 7. Data Flow & Storage

### 7.1 File Storage Structure

```
storage/
└── {meeting_id}/
    ├── transcript.json        # Diarized transcript (segments + speakers)
    ├── summary.json           # AI-generated summaries (EN + HI)
    ├── speaker_map.json       # HITL speaker name mappings
    ├── metadata.json          # Processing metadata (date, time)
    └── Meeting_Summary.pdf    # Generated PDF report

storage/
└── chroma_db/                 # ChromaDB vector store
    └── meetings/              # Collection: embedded transcript segments

data/
└── audio/
    └── {meeting_id}.wav       # Extracted 16 kHz mono audio
```

### 7.2 Processing Pipeline

```
Video Upload → Audio Extraction → Transcription → Diarization → Save JSON
                                                                    │
                ┌───────────────────────────────────────────────────┤
                │                    │                              │
         AI Summarization     RAG Indexing              Interactive Views
         (Groq API)           (ChromaDB)               (Streamlit)
                │                    │
         Human Review          Q&A Chat
         (Edit/Approve)        (Groq API)
                │
         Publish (PDF + Email + Teams)
```

---

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Groq over OpenAI/Gemini** | 10× faster inference (~500 tok/sec), free tier available, Llama 3.3 70B handles Hindi well |
| **ChromaDB over Pinecone/Weaviate** | Runs locally, no cloud dependency, persistent on disk, simple setup |
| **WhisperX over Whisper** | Word-level alignment, CTranslate2 backend (faster), integrated diarization support |
| **JSON file storage over DB** | Simpler deployment, no database setup, sufficient for single-user use cases |
| **fpdf2 over ReportLab** | Lightweight, native Unicode/Hindi font support, no license concerns |
| **Streamlit over React** | Rapid prototyping, built-in widgets, native Python integration, dark theme support |
| **Lazy model loading** | RAG service loaded only when first used — avoids slowing down server startup for non-chat requests |
| **Speaker map as separate JSON** | Decoupled from transcript — allows re-mapping without re-transcribing |

---

## 9. Environment Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `FFMPEG_PATH` | ✅ | Path to FFmpeg binary |
| `HF_TOKEN` | ✅ | HuggingFace token (pyannote model access) |
| `GROQ_API_KEY` | ✅ | Groq API key (summaries + RAG chat) |
| `SMTP_HOST` | ⬜ | Email server hostname |
| `SMTP_PORT` | ⬜ | Email server port (587 for TLS) |
| `SMTP_USER` | ⬜ | Email sender address |
| `SMTP_PASSWORD` | ⬜ | Email app password |
| `TEAMS_WEBHOOK_URL` | ⬜ | Microsoft Teams webhook URL |

---

## 10. Future Enhancements

| Priority | Feature | Description |
|----------|---------|-------------|
| 🔴 High | Action Items & Decision Extraction | Auto-detect tasks, assignees, deadlines from transcript |
| 🔴 High | Smart Search Across Meetings | Semantic + full-text search across all meeting history |
| 🟡 Medium | Topic Segmentation | Auto-split meetings into topic chapters with timestamps |
| 🟡 Medium | Meeting Diff / Comparison | Compare recurring meetings to track progress |
| 🟢 Low | RBAC Authentication | User login, roles, per-meeting permissions |
| 🟢 Low | PostgreSQL Backend | Replace JSON files for multi-user scalability |
| 🟢 Low | Zoom/Teams Bot Integration | Auto-join meetings, record, and process |

---

## 11. How to Run

### Prerequisites

- Python 3.10+
- FFmpeg installed
- NVIDIA GPU + CUDA (optional, 3–5× speedup)
- HuggingFace account (pyannote model access)
- Groq API key (free at https://console.groq.com)

### Quick Start

```bash
# Clone & setup
git clone <repo-url>
cd ContextIQ
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu128

# Configure .env (see Section 9)

# Start backend
python -m uvicorn app.main:app --reload --port 8000

# Start frontend (new terminal)
streamlit run ui/streamlit_app.py
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |

---

## 12. Conclusion

ContextIQ demonstrates a production-quality meeting intelligence pipeline that combines state-of-the-art speech recognition, large language models, and retrieval-augmented generation into a cohesive, user-friendly platform. The system's modular architecture allows for easy extension, while the Human-in-the-Loop features ensure AI outputs meet human quality standards before distribution.
