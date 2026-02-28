# VRIZE Video Analytics Hackathon: Team Submission

> **Instructions for Teams:** Please complete this template and upload it to your designated OneDrive folder along with all referenced output files. Ensure every stage of your pipeline is documented clearly so the evaluation committee can assess your work easily.

---

## Team Information

- **Team Name:** Squad404
- **Team Members:** Pawan Kumar Uikey, Ashish Jaiswal, Richa Pandey
- **Project Name/Brief Description:** ContextIQ — a fully-featured Meeting Intelligence Platform that takes raw MS Teams video recordings and produces speaker-diarized transcriptions, voice-identified speakers, bilingual AI summaries (English + Hindi), sentiment analysis, topic segmentation, action item extraction with Jira integration, SOW drafts, per-speaker report cards, and a RAG-powered chatbot — all orchestrated through a modern Svelte frontend and FastAPI backend.

---

## Part 1: Open-Source Tool Registry

| Tool / Library Name | Version | Primary Purpose | Stage Used |
|---|---|---|---|
| FFmpeg | v7.0+ | Audio extraction from MS Teams .mp4 video files (16 kHz mono WAV) | Stage 1 |
| noisereduce | Latest | Spectral gating noise reduction preprocessing | Stage 1 |
| soundfile | Latest | Audio file I/O for preprocessing pipeline | Stage 1 |
| AssemblyAI SDK | Latest | Primary cloud-based speech-to-text with integrated speaker diarization | Stage 2 |
| Groq Whisper API | Latest | Ultra-fast cloud STT (whisper-large-v3-turbo) | Stage 2 |
| WhisperX | v3.1 | Local speech-to-text with word-level forced alignment (wav2vec2) | Stage 2 |
| pyannote.audio | v3.1 | Neural speaker diarization — identifies and labels individual speakers | Stage 2 |
| SpeechBrain (ECAPA-TDNN) | Latest | 192-dim voice embeddings for speaker identification | Stage 2 |
| PyTorch | 2.x (CUDA 12.8) | GPU-accelerated ML inference for WhisperX, pyannote, and SpeechBrain | Stage 2 |
| Groq SDK (Llama 3.3 70B) | Latest | Ultra-fast LLM inference for summaries, action items, sentiment, topics | Stage 3 |
| LangChain | Latest | Orchestration framework for RAG pipeline (retrieval, chains, memory) | Stage 3 |
| ChromaDB | Latest | Local vector database for storing transcript embeddings (RAG chatbot) | Stage 3 |
| HuggingFace (all-MiniLM-L6-v2) | Latest | 384-dim embedding model for semantic search | Stage 3 |
| Chart.js | Latest | Interactive charts for sentiment, analytics, and culture score | Stage 3 |
| fpdf2 | Latest | PDF report generation with Unicode Hindi support (NotoSansDevanagari) | Stage 4 |
| smtplib (Python stdlib) | Built-in | Email publishing with PDF attachments via SMTP | Stage 4 |
| Atlassian REST API | v3 | Jira integration — push, sync, and update action items as tickets | Stage 4 |
| FastAPI | 0.100+ | Backend REST API server with 35+ endpoints | All Stages |
| Uvicorn | Latest | ASGI server to run FastAPI | All Stages |
| Svelte | v5 | Modern frontend SPA (single-page application) with reactive UI | All Stages |
| Vite | v5 | Frontend build tool and dev server | All Stages |
| TailwindCSS | v3 | Utility-first CSS framework for responsive, polished UI design | All Stages |
| Lucide Svelte | Latest | Icon library for the Svelte frontend | All Stages |
| svelte-spa-router | Latest | Client-side hash-based routing for the SPA | All Stages |

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
  4. Audio preprocessing applies spectral gating noise reduction (`noisereduce`) and peak normalization.
  5. Clean audio saved as `{meeting_id}_clean.wav`.

### Stage 2: Transcription, Diarization & Voice Identification

- **Objective:** Convert the extracted audio to text with word-level timestamps, identify individual speakers (diarization), and automatically recognize known speakers using voice embeddings.
- **Tool(s) Used:** AssemblyAI (primary), Groq Whisper (ultra-fast), WhisperX + pyannote.audio (local), SpeechBrain ECAPA-TDNN (voice identification)
- **Input Data:** `data/audio/{meeting_id}_clean.wav` (preprocessed audio)
- **Output File Links:**
  - `storage/{meeting_id}/transcript.json` — full diarized transcript with segments
  - `storage/{meeting_id}/speaker_clips/` — 10-second WAV clips per speaker
  - `storage/speaker_profiles/profiles.json` — 192-dim voice embeddings for known speakers
- **Execution Details/Commands:**
  1. Triggered via `POST /transcribe/{meeting_id}` with configurable STT engine.
  2. **AssemblyAI mode (primary):** Audio uploaded with `speaker_labels=True`, returns speaker-tagged segments.
  3. **Groq mode (ultra-fast):** Whisper large-v3-turbo transcription + local pyannote diarization.
  4. **Local mode:** WhisperX with wav2vec2 forced alignment + pyannote.audio 3.1 diarization on GPU.
  5. **Voice Identification:** Extracts ~10s speaker clips (SNR-ranked), generates 192-dim ECAPA-TDNN embeddings, matches against stored profiles using cosine similarity (threshold 0.55).
  6. Matched speakers are auto-renamed in the transcript (e.g., `SPEAKER_00` → `"Babuji Abraham"`).
  7. GPU memory explicitly cleared after processing.

### Stage 3: Analytics & Feature Generation

- **Objective:** Generate comprehensive AI-powered analytics: bilingual summaries, action items, sentiment analysis, topic segmentation, requirements, documentation, speaker report cards, and enable a RAG chatbot.
- **Tool(s) Used:** Groq API (Llama 3.3 70B Versatile), LangChain, ChromaDB, HuggingFace Embeddings
- **Input Data:** `storage/{meeting_id}/transcript.json`
- **Output File Links:**
  - `storage/{meeting_id}/summary.json` — Bilingual summaries (English + Hindi)
  - `storage/{meeting_id}/action_items.json` — Action items, decisions, key takeaways, risks
  - `storage/{meeting_id}/sentiment.json` — Per-segment sentiment scores and emotion labels
  - `storage/{meeting_id}/topics.json` — Topic segmentation with time ranges and speakers
  - `storage/{meeting_id}/requirements.json` — Functional/non-functional requirements, user stories
  - `storage/{meeting_id}/documentation.json` — Auto-generated meeting minutes (MoM)
  - `storage/{meeting_id}/followup_email.json` — AI-drafted professional follow-up email
  - `storage/chroma_db/` — Vector embeddings indexed in ChromaDB for RAG
- **Execution Details/Commands:**
  1. **Summarization** (`POST /summarize/{id}`): Groq Llama 3.3 70B generates speaker-wise + overall summaries in English and Hindi.
  2. **Action Items** (`POST /meeting/{id}/action-items`): Structured JSON extraction with task, assignee, deadline, priority, category, success criteria, and dependencies.
  3. **Sentiment Analysis** (`POST /meeting/{id}/sentiment`): Per-segment mood scoring with confidence.
  4. **Topic Segmentation** (`POST /meeting/{id}/topics`): Identifies distinct discussion topics with time ranges, titles, summaries, and speakers.
  5. **Requirements Mining** (`POST /meeting/{id}/requirements`): Extracts functional/non-functional requirements, technical constraints, and user stories with MoSCoW prioritization.
  6. **Speaker Report Cards** (`GET /meeting/{id}/speaker-analytics`): Per-speaker scorecards with role classification (Decision Maker, Presenter, etc.), talk-time, sentiment trends.
  7. **Meeting Culture Score** (`GET /stats/culture-score`): Composite health metric (0-100) combining speaker balance (Gini-like), sentiment health, action completion, and meeting efficiency.
  8. **RAG Indexing** (`POST /chat/index/{id}`): all-MiniLM-L6-v2 embeddings stored in ChromaDB with speaker/timestamp metadata.
  9. **RAG Chat** (`POST /chat/ask/stream`): Diverse retrieval algorithm (round-robin across meetings) + SSE streaming with source citations.
  10. **HITL Regeneration**: When speakers are renamed, all 8 AI insights regenerate in background with mapped names (force=True).

### Stage 4: Report Generation & Publishing

- **Objective:** Generate professional PDF reports, distribute summaries via email and Microsoft Teams, push action items to Jira for project management, and export subtitles.
- **Tool(s) Used:** fpdf2, smtplib, Microsoft Teams Webhook, Atlassian Jira REST API
- **Input Data:** `summary.json`, `action_items.json`, `requirements.json`, `documentation.json`
- **Output File Links:**
  - Downloaded PDF summary report (NotoSans + NotoSansDevanagari fonts)
  - Downloaded full comprehensive report PDF (summary + actions + requirements + docs)
  - SRT/VTT subtitle files with speaker labels
- **Execution Details/Commands:**
  1. **PDF Generation** (`GET /publish/{id}/pdf`): fpdf2 renders a professional layout with Unicode Hindi support.
  2. **Full Report PDF** (`GET /publish/{id}/full-report`): All analytics combined into one comprehensive PDF.
  3. **Email Publishing** (`POST /publish/{id}`): Attaches PDF and sends via SMTP (Gmail App Passwords).
  4. **Teams Webhook** (`POST /publish/{id}`): Sends an Adaptive Card v1.4 with summary, decisions, action items.
  5. **Jira Push** (`POST /meeting/{id}/jira/push`): Action items as Jira tickets with ADF description, priority mapping, and bi-directional sync via transitions API.
  6. **Subtitle Export** (`GET /meeting/{id}/subtitles/srt` and `/vtt`): Standard SRT and WebVTT subtitle files.

---

## Part 3: Features & Innovation Summary

### List of Features Built

1. **Multi-Engine Speech-to-Text** — AssemblyAI (primary), Groq Whisper (ultra-fast), local WhisperX; configurable per meeting
2. **Speaker Diarization** — pyannote.audio 3.1 with neural VAD + clustering on GPU
3. **Voice Identification** — ECAPA-TDNN 192-dim embeddings, SNR-ranked clip selection, cosine similarity matching, profile averaging for multi-session stability
4. **Bilingual AI Summaries** — Speaker-wise + overall summaries in both English and Hindi (Devanagari script)
5. **Action Item Extraction** — Structured tasks with assignee, deadline, priority, category, dependencies, and success criteria
6. **Decisions Tracker** — Captures who decided what, why, alternatives considered, and impact
7. **Key Takeaways** — Bullet-point highlights from every meeting
8. **Auto Meeting Title** — AI-generated descriptive meeting title from transcript content
9. **Follow-Up Email Draft** — Professional email combining summary + action items, ready to send via SMTP
10. **Per-Segment Sentiment Analysis** — Mood scoring, emotion labels, confidence scores, and speaker sentiment trends
11. **Topic Segmentation** — Auto-detected discussion chapters with time ranges, titles, summaries, and participating speakers
12. **Requirements Mining** — Functional, non-functional, technical constraints, user stories with MoSCoW prioritization
13. **Documentation Generation** — Auto-generated meeting minutes with objective, attendees, and next steps
14. **Per-Speaker Report Cards** — Role classification (Decision Maker, Presenter, etc.), talk-time stats, sentiment summary
15. **Meeting Culture Score** — Composite health metric: speaker balance (Gini-like), sentiment, action completion, efficiency
16. **RAG Chatbot with SSE Streaming** — Cross-meeting Q&A with diverse retrieval (round-robin), source citations, session memory, meeting calendar context
17. **Human-in-the-Loop (HITL)** — Speaker name mapping triggers async regeneration of all 8 AI insights, summary editing & approval before publishing
18. **Professional PDF Reports** — Summary PDF and comprehensive full report with Unicode Hindi support
19. **SRT/VTT Subtitle Export** — Standard subtitle files with speaker labels
20. **One-Click Email & Teams Publishing** — SMTP email with PDF attachment + Teams Adaptive Card v1.4
21. **Bidirectional Jira Integration** — Push tickets, sync statuses, transitions API, ADF descriptions
22. **Confluence & Notion Integration** — Push meeting notes to enterprise wikis via API
23. **Upload Deduplication** — SHA-256 hashing prevents reprocessing of duplicate video files
24. **Meeting Dashboard** — Unique speaker counting (resolves mapped names), real-time statistics, and search
25. **Global Keyword Search** — Weighted relevance scoring across transcripts, titles, and speakers
26. **Video Playback** — In-browser video player with HTTP Range request support for seeking
27. **Skeleton Loading & Toast Notifications** — Polished, premium UX with shimmer states and system-wide feedback

### Innovation Highlight

ContextIQ's most innovative aspect is its **end-to-end, privacy-first architecture** that combines **local GPU-accelerated processing** for speech-to-text with **cloud LLM APIs for intelligence**. Unlike competitors that require all data to be uploaded to external servers, ContextIQ keeps raw audio and transcripts local while only sending text to Groq for analysis.

Key innovations include: (1) **Voice Identification** using ECAPA-TDNN neural embeddings — speakers enrolled from one meeting are automatically recognized in all future meetings; (2) **Bilingual Hindi summaries** in native Devanagari (absent from all major competitors); (3) **Bi-directional Jira integration** using the transitions API for proper status changes; (4) **Diverse retrieval algorithm** for the RAG chatbot that round-robins chunks across meetings to prevent single-meeting bias; (5) **Human-in-the-Loop workflow** where renaming speakers triggers async regeneration of all 8 AI insights; (6) **Meeting Culture Score** — a composite health metric combining Gini-like speaker balance, sentiment health, action completion rate, and decisions-per-minute.

---

## Part 4: Final Deliverables

- **Link to Final Analytics Report:** [Insert OneDrive link to the final PDF report generated by ContextIQ]
- **Link to Source Code Repository:** [https://github.com/pawanuikey06/ContextIQ](https://github.com/pawanuikey06/ContextIQ)
- **Self-Reported Transcript Accuracy (Optional):** [If your team ran an automated comparison against the provided PDF ground truth, state your percentage match here and the metric used]
