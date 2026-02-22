# ContextIQ — Detailed Project Report

**Project Title:** ContextIQ — Meeting Intelligence Platform  
**Author:** Pawan Uikey  
**Date:** February 23, 2026  
**Version:** 3.0.0

---

## 1. Executive Summary

ContextIQ is an end-to-end **Meeting Intelligence Platform** that transforms raw meeting video recordings into structured, searchable, and shareable knowledge. The system performs:

- **Automatic speech-to-text transcription** with speaker diarization (local GPU)
- **Bilingual AI summaries** (English + Hindi) using Llama 3.3 70B via Groq
- **AI-powered action items, decisions, and follow-up email extraction**
- **RAG-powered chatbot** with real-time SSE streaming and source citations
- **Human-in-the-Loop (HITL)** review and approval workflow
- **One-click publishing** to PDF, Email, and Microsoft Teams

All of this is delivered through a premium Streamlit web interface with 5 interactive tabs.


## 2. Problem Statement

Organizations conduct numerous meetings daily, generating hours of unstructured audio/video content. Key decisions, action items, and critical discussions are often lost or poorly documented. Manual meeting notes are:

- **Time-consuming** — takes 30–60 minutes to summarize a 1-hour meeting
- **Incomplete** — note-takers miss details or introduce bias
- **Unsearchable** — information is locked in documents, not queryable
- **Inaccessible** — non-English speakers are excluded from meeting insights
- **Siloed** — sharing requires manual effort via email or messaging
- **Unaccountable** — action items and decisions are forgotten after the meeting

ContextIQ solves all of these problems with an automated, AI-powered pipeline that extracts every insight and makes it actionable.

---

## 3. System Architecture

### 3.1 Architecture Overview

The system follows a **5-layer architecture**:

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
│              speaker_map │ insights │ health                    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                      SERVICES LAYER                               │
│  stt_service │ rag_service │ summary_service │ publish_service  │
│  insights_service │ speaker_service │ storage_service           │
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
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Directory Structure

```
ContextIQ/
├── app/
│   ├── main.py                        # FastAPI entry, health check, v3.0.0
│   ├── api/                           # 8 API route files
│   │   ├── upload.py                  # Video upload (SHA-256 dedup)
│   │   ├── transcribe.py             # Transcription + auto-metadata
│   │   ├── diarization.py            # Transcript retrieval + editing
│   │   ├── summarize.py              # Bilingual AI summaries
│   │   ├── publish.py                # PDF + Email + Teams
│   │   ├── speaker_map.py            # HITL speaker name mapping
│   │   ├── chat.py                   # RAG chat + SSE streaming
│   │   └── insights.py              # Action items + auto title + email
│   ├── services/                      # 8 service modules
│   │   ├── stt_service.py            # WhisperX + pyannote (GPU offload)
│   │   ├── rag_service.py            # LangChain + ChromaDB + Groq
│   │   ├── summary_service.py        # Groq Llama 3.3 70B summaries
│   │   ├── insights_service.py      # Action items + title + email draft
│   │   ├── publish_service.py        # PDF (fpdf2) + SMTP + Teams
│   │   ├── speaker_service.py        # Speaker segment grouping
│   │   ├── storage_service.py        # JSON persistence
│   │   └── video_to_audio.py         # FFmpeg extraction
│   ├── schemas/schemas.py            # Pydantic v2 models
│   └── fonts/                        # NotoSans + Devanagari TTF
├── ui/streamlit_app.py               # Premium Streamlit frontend
├── docs/                              # Diagrams (.drawio + .png)
├── storage/                           # Runtime meeting data
│   ├── {meeting_id}/                 # Per-meeting folder
│   └── chroma_db/                    # ChromaDB vector store
├── data/audio/                        # Extracted WAV files
├── requirements.txt
└── .env
```

---

## 4. Technology Stack

### 4.1 AI/ML Models

| Model | Purpose | Runs On |
|-------|---------|---------|
| **WhisperX** (CTranslate2 `base`) | Speech-to-text transcription | Local GPU/CPU |
| **pyannote.audio 3.1** | Speaker diarization | Local GPU/CPU |
| **Llama 3.3 70B Versatile** | Summarization, action items, email draft | Groq API (Cloud LPU) |
| **all-MiniLM-L6-v2** | Text embeddings for RAG | Local CPU |

### 4.2 Framework & Libraries

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend API | FastAPI + Uvicorn | REST API server |
| Frontend | Streamlit | Premium dark theme UI |
| LLM Orchestration | LangChain | RAG pipeline, conversation memory |
| Vector Database | ChromaDB | Persistent embedding store |
| LLM Provider | Groq | Ultra-fast inference (~500 tok/sec) |
| PDF Generation | fpdf2 | Unicode Hindi support |
| ML Framework | PyTorch + CUDA 12.8 | GPU acceleration |
| Streaming | Server-Sent Events | Real-time chat responses |
| Validation | Pydantic v2 | Request/response schemas |
| Audio | FFmpeg | Video → WAV extraction |

---

## 5. Feature Modules (26 Features)

### 5.1 Video Upload & Audio Extraction
- **API:** `POST /upload-video`
- **Service:** `video_to_audio.py`
- **Features:** SHA-256 deduplication, accepts `.mp4`/`.mkv`/`.mov`, FFmpeg 16 kHz mono WAV extraction
- **Output:** Unique `meeting_id` (UUID)

### 5.2 Transcription & Speaker Diarization
- **API:** `POST /transcribe/{meeting_id}`
- **Service:** `stt_service.py`
- **Process:**
  1. Load WhisperX model (CTranslate2, auto GPU/CPU detection)
  2. Transcribe → word-level timestamps
  3. Align with WhisperX alignment model
  4. Run pyannote.audio 3.1 speaker diarization
  5. Assign speaker labels to segments
  6. Auto-create `metadata.json` with processing stats
- **GPU Optimization:** Sequential VRAM offloading allows running on 4GB GPUs (GTX 1650)
- **Output:** `transcript.json` + `metadata.json`

### 5.3 AI Summarization
- **API:** `POST /summarize/{meeting_id}`
- **Service:** `summary_service.py`
- **LLM:** Llama 3.3 70B via Groq API
- **Generates:**
  - Speaker-wise summaries in English
  - Overall meeting summary in English
  - Overall meeting summary in Hindi (हिंदी)
- **Features:** Caching, force regeneration, custom prompt injection, speaker name mapping applied
- **Output:** `summary.json`

### 5.4 Action Items & Decisions Extraction (NEW)
- **API:** `POST /meeting/{meeting_id}/action-items`
- **Service:** `insights_service.py`
- **LLM:** Llama 3.3 70B via Groq API
- **Extracts:**
  - **Action Items** — task, assignee, deadline, priority (high/medium/low)
  - **Decisions** — what was decided, who proposed it, context
  - **Key Takeaways** — bullet-point highlights
  - **Follow-ups** — items needing follow-up
- **Output:** `action_items.json`

### 5.5 Auto Meeting Title (NEW)
- **API:** `POST /meeting/{meeting_id}/auto-title`
- **Service:** `insights_service.py`
- **Generates:** Concise, descriptive title (max 8 words) from first 3000 chars of transcript
- **Output:** Saved to `metadata.json` as `auto_title`

### 5.6 Follow-Up Email Draft (NEW)
- **API:** `POST /meeting/{meeting_id}/followup-email`
- **Service:** `insights_service.py`
- **Combines:** Title + summary + action items + decisions + participants
- **Generates:** Professional email with subject line, body, and suggested recipients
- **Output:** `followup_email.json`

### 5.7 RAG Chatbot
- **API:** `POST /chat/ask`, `POST /chat/ask/stream` (SSE)
- **Service:** `rag_service.py`
- **Architecture:**
  1. **Ingestion:** Transcript chunked by speaker segment → embedded → stored in ChromaDB
  2. **Query:** Semantic search → top-10 segments → context + question → Llama 3.3 70B → answer + citations
- **SSE Streaming:** Server-Sent Events deliver tokens word-by-word to the UI with a blinking cursor
- **Features:** Session memory, meeting-filtered queries, date-aware queries, source citations

### 5.8 Publishing & Distribution
- **API:** `POST /publish/{meeting_id}`, `GET /publish/{meeting_id}/pdf`
- **Service:** `publish_service.py`
- **Channels:**
  - **PDF** — Professional layout, Unicode Hindi (NotoSansDevanagari), speaker summary blocks
  - **Email** — SMTP delivery with PDF attachment
  - **Teams** — Microsoft Webhook with Adaptive Card

### 5.9 Human-in-the-Loop (HITL)
- **Speaker Name Mapping** — Map speaker IDs to real names, persists across all views
- **Summary Approval** — Users review, edit, and approve summaries before publishing
- **Custom Rewrite** — Regenerate summaries with custom instructions

### 5.10 Health Check & Monitoring
- **API:** `GET /health`
- **Reports:** GPU status (device name, VRAM total/free), storage usage (total/per-meeting), ChromaDB initialization status, meeting count

---

## 6. API Reference (21 Endpoints)

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | `POST` | `/upload-video` | Upload video, extract audio |
| 2 | `POST` | `/transcribe/{meeting_id}` | Transcribe + diarize + auto-metadata |
| 3 | `GET` | `/meeting/{meeting_id}` | Get saved transcript |
| 4 | `PUT` | `/meeting/{meeting_id}/segments/{index}` | Edit transcript segment |
| 5 | `GET` | `/meeting/{meeting_id}/metadata` | Get meeting metadata |
| 6 | `PATCH` | `/meeting/{meeting_id}/metadata` | Update meeting metadata |
| 7 | `POST` | `/summarize/{meeting_id}` | Generate AI summaries |
| 8 | `POST` | `/meeting/{meeting_id}/action-items` | Extract action items & decisions |
| 9 | `POST` | `/meeting/{meeting_id}/auto-title` | Generate AI meeting title |
| 10 | `POST` | `/meeting/{meeting_id}/followup-email` | Draft follow-up email |
| 11 | `POST` | `/publish/{meeting_id}` | Publish (PDF + Email + Teams) |
| 12 | `GET` | `/publish/{meeting_id}/pdf` | Download PDF |
| 13 | `POST` | `/chat/ask` | Ask question (standard) |
| 14 | `POST` | `/chat/ask/stream` | Ask question (SSE streaming) |
| 15 | `POST` | `/chat/index/{meeting_id}` | Index meeting for RAG |
| 16 | `GET` | `/chat/meetings` | List indexed meetings |
| 17 | `POST` | `/chat/clear/{session_id}` | Clear chat session |
| 18 | `POST` | `/meeting/{meeting_id}/speaker-map` | Save speaker names |
| 19 | `GET` | `/meeting/{meeting_id}/speaker-map` | Get speaker names |
| 20 | `GET` | `/` | Service info + all endpoints |
| 21 | `GET` | `/health` | System health (GPU + storage) |

---

## 7. Data Flow & Storage

### 7.1 File Storage Structure

```
storage/
└── {meeting_id}/
    ├── transcript.json        # Diarized transcript (segments + speakers)
    ├── summary.json           # AI summaries (EN + HI + speaker-wise)
    ├── action_items.json      # Action items, decisions, takeaways
    ├── followup_email.json    # AI-drafted follow-up email
    ├── speaker_map.json       # HITL speaker name mappings
    ├── metadata.json          # Processing metadata + auto title
    └── Meeting_Summary.pdf    # Generated PDF report

storage/chroma_db/             # ChromaDB vector store (RAG embeddings)
data/audio/{meeting_id}.wav    # Extracted 16 kHz mono audio
```

### 7.2 Processing Pipeline

```
Video Upload → Audio Extraction → Transcription → Diarization → Save JSON
                                                                    │
                ┌───────────────┬──────────────┬───────────────────┤
                │               │              │                   │
         AI Summarization  RAG Indexing  Action Items        Interactive Views
         (Groq API)        (ChromaDB)   + Auto Title        (Streamlit 5-tab)
                │               │        + Email Draft
         Human Review      SSE Chat         │
         (Edit/Approve)    (Groq API)   Follow-Up Email
                │
         Publish (PDF + Email + Teams)
```

---

## 8. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Groq over OpenAI/Gemini** | 10× faster inference (~500 tok/sec), free tier, Llama 3.3 70B handles Hindi well |
| **Local STT over cloud** | Privacy-first — audio never leaves the machine. Critical for healthcare, legal, HR meetings |
| **ChromaDB over Pinecone** | Runs locally, no cloud dependency, persistent on disk |
| **WhisperX over Whisper** | Word-level alignment, CTranslate2 (faster), integrated diarization support |
| **JSON over SQL** | Simpler deployment, no database setup, sufficient for single-user |
| **SSE over WebSocket** | Simpler, HTTP-compatible, works with Streamlit's request-based architecture |
| **Sequential GPU offloading** | Enables running on 4GB GPUs by loading/unloading models one at a time |
| **Lazy model loading** | Services loaded only when first used — avoids slowing startup |
| **HITL before publish** | Responsible AI — human reviews and approves before distribution |
| **Action items caching** | Avoid redundant LLM calls — cache results, force-regenerate when needed |

---

## 9. Streamlit UI (1300+ lines)

### Pages
1. **Meeting Processing** — Upload → Transcribe → View → Summarize → Publish
2. **Meeting Chat** — SSE streaming RAG Q&A with source citations

### Dashboard Tabs (5)
| Tab | Content |
|-----|---------|
| 💬 **Chat View** | Color-coded conversation with speaker labels and timestamps |
| 🗣️ **Speaker View** | Expandable per-speaker grouping of all segments |
| 📊 **Timeline** | Sortable table with Start, End, Speaker, Text |
| 🧠 **AI Summaries** | Bilingual summaries + HITL approval + publish (PDF/Email/Teams) |
| 🎯 **Action Items** | Tasks, decisions, takeaways, follow-ups + email draft |

### UI Features
- Premium dark theme with gradient accents
- Auto Title display next to meeting ID
- Metric cards (segments, speakers, duration)
- Speaker name mapping with live updates
- Real-time SSE streaming chat with blinking cursor

---

## 10. Environment Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `FFMPEG_PATH` | ✅ | Path to FFmpeg binary |
| `HF_TOKEN` | ✅ | HuggingFace token (pyannote access) |
| `GROQ_API_KEY` | ✅ | Groq API key (LLM inference) |
| `SMTP_HOST` | ⬜ | Email server hostname |
| `SMTP_PORT` | ⬜ | Email server port |
| `SMTP_USER` | ⬜ | Email sender address |
| `SMTP_PASSWORD` | ⬜ | Email app password |
| `TEAMS_WEBHOOK_URL` | ⬜ | Microsoft Teams webhook URL |

---

## 11. How to Run

```bash
# Clone & setup
git clone https://github.com/pawanuikey06/ContextIQ.git
cd ContextIQ
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install --force-reinstall torch torchaudio --index-url https://download.pytorch.org/whl/cu128

# Configure .env (see Section 10)

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

ContextIQ demonstrates a **production-quality meeting intelligence pipeline** combining:

- **State-of-the-art speech recognition** (WhisperX + pyannote) running locally on GPU
- **Large language model intelligence** (Llama 3.3 70B via Groq) for summaries, action items, and email drafts
- **Retrieval-Augmented Generation** (LangChain + ChromaDB) for intelligent multi-meeting Q&A
- **Human-in-the-Loop governance** ensuring AI outputs meet quality standards before distribution
- **Privacy-first architecture** — audio transcription happens entirely on-device

With **26 features across 21 API endpoints**, ContextIQ replaces $100+/month commercial tools (Otter.ai, Fireflies, Gong) with a free, open-source, self-hosted alternative that keeps data where it belongs — on the user's machine.
