# VRIZE Video Analytics Hackathon: Team Submission

> **Instructions for Teams:** Please complete this template and upload it to your designated OneDrive folder along with all referenced output files. Ensure every stage of your pipeline is documented clearly so the evaluation committee can assess your work easily.

---

## Team Information

- **Team Name:** Squad404
- **Team Members:** Pawan Kumar Uikey, Ashish Jaiswal, Richa Pandey
- **Project Name/Brief Description:** ContextIQ — a fully-featured Meeting Intelligence Platform that takes raw MS Teams video recordings and produces speaker-diarized transcriptions, bilingual AI summaries (English + Hindi), sentiment analysis, action item extraction with Jira integration, and a RAG-powered chatbot — all orchestrated through a modern Svelte frontend and FastAPI backend.

---

## Part 1: Open-Source Tool Registry

| Tool / Library Name | Version | Primary Purpose | Stage Used |
|---|---|---|---|
| FFmpeg | v7.0+ | Audio extraction from MS Teams .mp4 video files (16 kHz mono WAV) | Stage 1 |
| AssemblyAI SDK | Latest | Primary cloud-based speech-to-text with integrated speaker diarization | Stage 2 |
| WhisperX | v3.1 | Local speech-to-text with word-level timestamps (CTranslate2 engine) | Stage 2 (fallback) |
| pyannote.audio | v3.1 | Speaker diarization — identifies and labels individual speakers | Stage 2 (local mode) |
| PyTorch | 2.x (CUDA 12.8) | GPU-accelerated ML inference for WhisperX and pyannote models | Stage 2 |
| Groq SDK (Llama 3.3 70B) | Latest | Ultra-fast LLM inference for summaries, action items, sentiment, email drafts | Stage 3 |
| LangChain | Latest | Orchestration framework for RAG pipeline (document loading, retrieval, chains) | Stage 3 |
| ChromaDB | Latest | Local vector database for storing transcript embeddings (RAG chatbot) | Stage 3 |
| HuggingFace Transformers | Latest | `all-MiniLM-L6-v2` embedding model for semantic search | Stage 3 |
| fpdf2 | Latest | PDF report generation with Unicode Hindi support (NotoSansDevanagari) | Stage 4 |
| FastAPI | 0.100+ | Backend REST API server with 32 endpoints | All Stages |
| Uvicorn | Latest | ASGI server to run FastAPI | All Stages |
| Svelte | v5 | Modern frontend SPA (single-page application) with reactive UI | All Stages |
| Vite | v5 | Frontend build tool and dev server | All Stages |
| TailwindCSS | v3 | Utility-first CSS framework for responsive, polished UI design | All Stages |
| Chart.js | Latest | Interactive charts for sentiment analysis and meeting statistics | Stage 3 |
| Lucide Svelte | Latest | Icon library for the Svelte frontend | All Stages |
| svelte-spa-router | Latest | Client-side hash-based routing for the SPA | All Stages |
| noisereduce | Latest | Audio noise reduction preprocessing before transcription | Stage 1 |
| soundfile | Latest | Audio file I/O for preprocessing pipeline | Stage 1 |
| smtplib (Python stdlib) | Built-in | Email publishing with PDF attachments via SMTP | Stage 4 |
| Atlassian REST API | v3 | Jira integration — push, sync, and update action items as tickets | Stage 4 |

---

## Part 2: Standard Operating Procedure (SOP) & Pipeline Stages

### Stage 1: Data Pre-Processing & Audio Extraction

- **Objective:** Extract clean, optimized audio from raw MS Teams .mp4 video recordings and prepare it for transcription.
- **Tool(s) Used:** FFmpeg, noisereduce, soundfile
- **Input Data:** Original MS Teams `.mp4` video file uploaded via the web UI.
- **Output File Link:** `data/audio/{meeting_id}.wav` — 16 kHz mono WAV file
- **Execution Details/Commands:**
  1. User uploads video via `POST /upload-video` endpoint.
  2. SHA-256 hash is computed to prevent duplicate processing.
  3. FFmpeg extracts audio: `ffmpeg -i input.mp4 -ar 16000 -ac 1 -f wav output.wav`
  4. Audio preprocessing applies noise reduction (`noisereduce` library, `prop_decrease=0.7`) and peak normalization to -1 dBFS.
  5. Clean audio saved as `{meeting_id}_clean.wav`.

### Stage 2: Transcription & Speaker Diarization

- **Objective:** Convert the extracted audio to text with word-level timestamps and identify individual speakers throughout the recording.
- **Tool(s) Used:** AssemblyAI (primary), WhisperX + pyannote.audio (local fallback)
- **Input Data:** `data/audio/{meeting_id}_clean.wav` (preprocessed audio)
- **Output File Link:** `storage/{meeting_id}/transcript.json` — full diarized transcript with segments
- **Execution Details/Commands:**
  1. Triggered via `POST /transcribe/{meeting_id}`.
  2. **AssemblyAI mode (primary):** Audio file is uploaded to AssemblyAI API with `speaker_labels=True`. Returns speaker-tagged segments with timestamps.
  3. **Local mode (fallback):** WhisperX loads `large-v2` model via CTranslate2 on GPU. Performs word-level transcription, then pyannote.audio 3.1 performs speaker diarization. Results are merged using WhisperX's `assign_word_speakers()`.
  4. Metadata is auto-saved: processing timestamp, segment count, speaker count, total duration.
  5. GPU memory is explicitly cleared after local processing (`torch.cuda.empty_cache()`).

### Stage 3: Analytics & Feature Generation

- **Objective:** Generate comprehensive AI-powered analytics: bilingual summaries, action items, sentiment analysis, requirements extraction, meeting documentation, and enable a RAG chatbot.
- **Tool(s) Used:** Groq API (Llama 3.3 70B Versatile), LangChain, ChromaDB, HuggingFace Embeddings
- **Input Data:** `storage/{meeting_id}/transcript.json`
- **Output File Links:**
  - `storage/{meeting_id}/summary.json` — Bilingual summaries (English + Hindi)
  - `storage/{meeting_id}/action_items.json` — Action items, decisions, key takeaways, follow-ups, risks
  - `storage/{meeting_id}/sentiment.json` — Per-segment sentiment scores and emotion labels
  - `storage/{meeting_id}/requirements.json` — Extracted functional requirements
  - `storage/{meeting_id}/documentation.json` — Auto-generated meeting minutes (MoM)
  - `storage/{meeting_id}/followup_email.json` — AI-drafted professional follow-up email
  - `storage/chroma_db/` — Vector embeddings indexed in ChromaDB
- **Execution Details/Commands:**
  1. **Summarization** (`POST /summarize/{id}`): Transcript is sent to Groq Llama 3.3 70B with a structured system prompt. Generates speaker-wise + overall summaries in both English and Hindi. Hindi is generated in a separate LLM call to ensure quality Devanagari output.
  2. **Action Items** (`POST /meeting/{id}/action-items`): Groq extracts structured JSON with tasks, assignees, deadlines, priorities, categories, and success criteria.
  3. **Sentiment Analysis** (`POST /meeting/{id}/sentiment`): Each transcript segment is scored for mood (positive/negative/neutral), emotion labels, and confidence scores.
  4. **RAG Indexing** (`POST /chat/index/{id}`): Transcript segments are embedded using `all-MiniLM-L6-v2` (384-dim vectors) and stored in ChromaDB with speaker/timestamp metadata.
  5. **RAG Chat** (`POST /chat/ask/stream`): User queries are embedded, top-k relevant segments are retrieved from ChromaDB, and Groq generates answers via SSE streaming (~500 tokens/sec) with source citations.

### Stage 4: Report Generation & Publishing

- **Objective:** Generate professional PDF reports, distribute summaries via email and Microsoft Teams, and push action items to Jira for project management.
- **Tool(s) Used:** fpdf2, smtplib, Microsoft Teams Webhook, Atlassian Jira REST API
- **Input Data:** `summary.json`, `action_items.json`, `requirements.json`, `documentation.json`
- **Output File Links:**
  - Downloaded PDF summary report
  - Downloaded full comprehensive report (summary + action items + requirements + docs)
  - SRT/VTT subtitle files for the recording
- **Execution Details/Commands:**
  1. **PDF Generation** (`GET /publish/{id}/pdf`): fpdf2 renders a professional layout with NotoSans (English) and NotoSansDevanagari (Hindi) fonts for full Unicode support.
  2. **Full Report PDF** (`GET /publish/{id}/full-report`): Combines all analytics (summary, action items, requirements, documentation) into a single comprehensive PDF.
  3. **Email Publishing** (`POST /publish/{id}`): Attaches the PDF and sends it via SMTP (Gmail).
  4. **Teams Webhook** (`POST /publish/{id}`): Sends an Adaptive Card with the meeting summary to a configured Microsoft Teams channel.
  5. **Jira Push** (`POST /meeting/{id}/jira/push`): Individual or batch action items are created as Jira tickets with task description, priority, and assignee mapping. Bi-directional sync (`/jira/sync`) fetches updates back from Jira.
  6. **Subtitle Export** (`GET /meeting/{id}/subtitles/srt` and `/vtt`): Generates standard SRT and WebVTT subtitle files with speaker labels.

---

## Part 3: Features & Innovation Summary

### List of Features Built

1. **Multi-Engine Speech-to-Text** — AssemblyAI (primary), Groq Whisper, local WhisperX; configurable via `STT_MODE` env variable
2. **Speaker Diarization** — pyannote.audio 3.1 with GPU acceleration on NVIDIA CUDA GPUs
3. **Bilingual AI Summaries** — Speaker-wise + overall summaries in both English and Hindi (Devanagari script)
4. **Action Item Extraction** — Structured tasks with assignee, deadline, priority (🔴🟡🟢), category, and success criteria
5. **Decisions Tracker** — Captures who decided what, why, alternatives considered, and impact
6. **Key Takeaways** — Bullet-point highlights from every meeting
7. **Auto Meeting Title** — AI-generated descriptive meeting title from transcript content
8. **Follow-Up Email Draft** — Professional email combining summary + action items, ready to send
9. **Per-Segment Sentiment Analysis** — Mood scoring, emotion labels, speaker sentiment trends, and key sentiment highlights
10. **Requirements Extraction** — Functional requirements with priority levels
11. **Documentation Generation** — Auto-generated meeting minutes with objective, attendees, and next steps
12. **RAG Chatbot with SSE Streaming** — Cross-meeting Q&A with real-time token streaming (blinking cursor effect), source citations (speaker + timestamp), and session memory
13. **Human-in-the-Loop (HITL)** — Speaker name mapping, summary editing & approval before publishing, custom rewrite instructions
14. **Professional PDF Reports** — Summary PDF and comprehensive full report with Unicode Hindi support
15. **SRT/VTT Subtitle Export** — Standard subtitle files with speaker labels
16. **One-Click Email & Teams Publishing** — SMTP email with PDF attachment + Teams Adaptive Card delivery
17. **Jira Integration** — Push action items to Jira, sync statuses bidirectionally, update linked tickets from ContextIQ
18. **Upload Deduplication** — SHA-256 hashing prevents reprocessing of duplicate video files
19. **Meeting Dashboard** — Real-time statistics (total meetings, speakers, duration), meeting search, sortable table
20. **Meeting Search** — Live keyword search across transcripts, titles, and speakers
21. **Skeleton Loading & Toast Notifications** — Polished UX with shimmer states and system-wide feedback

### Innovation Highlight

ContextIQ's most innovative aspect is its **end-to-end, privacy-first architecture** that combines **local GPU-accelerated processing** for speech-to-text with **cloud LLM APIs for intelligence**. Unlike competitors that require all data to be uploaded to external servers, ContextIQ keeps raw audio and transcripts local while only sending text to Groq for analysis. The system also uniquely provides **bilingual Hindi summaries** (a feature absent from all major competitors), a **bi-directional Jira integration** for action item management, and a **Human-in-the-Loop approval workflow** that ensures AI-generated content is reviewed before publishing. The multi-engine STT architecture (AssemblyAI → Groq → WhisperX) provides configurable fallback chains, allowing teams to optimize for accuracy, speed, or privacy based on their specific needs.

---

## Part 4: Final Deliverables

- **Link to Final Analytics Report:** [Insert OneDrive link to the final PDF report generated by ContextIQ]
- **Link to Source Code Repository:** [https://github.com/pawanuikey06/ContextIQ](https://github.com/pawanuikey06/ContextIQ)
- **Self-Reported Transcript Accuracy (Optional):** [If your team ran an automated comparison against the provided PDF ground truth, state your percentage match here and the metric used]
