# VRIZE Video Analytics Hackathon: Team Submission

> **Instructions for Teams:** Please complete this template and upload it to your designated OneDrive folder along with all referenced output files. Ensure every stage of your pipeline is documented clearly so the evaluation committee can assess your work easily.

---

## Team Information

- **Team Name:** Squad404
- **Team Members:** Pawan Kumar Uikey, Ashish Jaiswal, Richa Pandey
- **Project Name/Brief Description:** ContextIQ — a fully-featured Meeting Intelligence Platform that takes raw MS Teams video recordings and produces speaker-diarized transcriptions, voice-identified speakers, bilingual AI summaries (English + Hindi), sentiment analysis, topic segmentation, action item extraction with Jira integration, per-speaker report cards, keyword extraction, and a RAG-powered chatbot with video navigation — all orchestrated through a modern Svelte frontend and FastAPI backend with 50+ REST API endpoints.

---

## Part 1: Open-Source Tool Registry

| Tool / Library Name | Version | Primary Purpose | Stage Used |
|---|---|---|---|
| FFmpeg | v7.0+ | Audio extraction from MS Teams .mp4 video files (16 kHz mono WAV) | Stage 1 |
| noisereduce | Latest | Spectral gating noise reduction preprocessing | Stage 1 |
| soundfile | Latest | Audio file I/O for preprocessing and voice embedding pipelines | Stage 1, 2 |
| AssemblyAI SDK | Latest | Primary cloud-based speech-to-text with integrated speaker diarization | Stage 2 |
| Groq Whisper API | Latest | Ultra-fast cloud STT (whisper-large-v3-turbo) | Stage 2 |
| WhisperX | v3.1 | Local speech-to-text with word-level forced alignment (wav2vec2) | Stage 2 |
| pyannote.audio | v3.1 | Neural speaker diarization — identifies and labels individual speakers | Stage 2 |
| SpeechBrain (ECAPA-TDNN) | Latest | 192-dim voice embeddings for cross-meeting speaker identification | Stage 2 |
| PyTorch | 2.x (CUDA 12.8) | GPU-accelerated ML inference for WhisperX, pyannote, and SpeechBrain | Stage 2 |
| NumPy | Latest | Audio preprocessing: bandpass filtering, silence removal, normalization | Stage 2 |
| Groq SDK (Llama 3.3 70B) | Latest | Ultra-fast LLM inference for all 8 AI analytics features | Stage 3 |
| LangChain | Latest | Orchestration framework for RAG pipeline (retrieval, chains, memory) | Stage 3 |
| ChromaDB | Latest | Local persistent vector database for transcript embeddings (RAG chatbot) | Stage 3 |
| HuggingFace (all-MiniLM-L6-v2) | Latest | 384-dim sentence embedding model for semantic search | Stage 3 |
| Chart.js | Latest | Interactive charts for sentiment timeline, speaker analytics, culture score | Stage 3 |
| fpdf2 | Latest | PDF report generation with Unicode Hindi support (NotoSansDevanagari) | Stage 4 |
| smtplib (Python stdlib) | Built-in | Email publishing with PDF attachments via SMTP | Stage 4 |
| Atlassian REST API | v3 | Jira integration — push, sync, and update action items as tickets | Stage 4 |
| Notion API | v1 | Push meeting notes and summaries to Notion pages | Stage 4 |
| Confluence REST API | v2 | Push meeting documentation to Confluence spaces | Stage 4 |
| FastAPI | 0.100+ | Backend REST API server with 50+ endpoints across 14 router modules | All Stages |
| Uvicorn | Latest | ASGI server to run FastAPI with hot-reload | All Stages |
| Svelte | v5 | Modern frontend SPA with 6 pages and 6 reusable components | All Stages |
| Vite | v5 | Frontend build tool and HMR dev server | All Stages |
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
  - `storage/{meeting_id}/transcript.json` — full diarized transcript with speaker-tagged segments
  - `storage/{meeting_id}/speaker_clips/` — 10-second preprocessed WAV clips per speaker
  - `storage/speaker_profiles/profiles.json` — 192-dim voice embeddings for known speakers
  - `storage/{meeting_id}/speaker_map.json` — SPEAKER_ID → real name mapping
- **Execution Details/Commands:**
  1. Triggered via `POST /transcribe/{meeting_id}` with configurable STT engine parameter.
  2. **AssemblyAI mode (primary):** Audio uploaded with `speaker_labels=True`, returns speaker-tagged segments.
  3. **Groq mode (ultra-fast):** Whisper large-v3-turbo transcription + local pyannote diarization.
  4. **Local mode:** WhisperX with wav2vec2 forced alignment + pyannote.audio 3.1 diarization on GPU.
  5. **Voice Identification Pipeline:**
     - Extracts ~10s speaker clips ranked by audio quality (RMS energy × bounded duration).
     - 5-stage audio preprocessing: resample to 16 kHz → peak normalize → bandpass filter (80–7600 Hz) → silence removal (30ms frames, RMS < 0.01) → re-normalize.
     - Generates 192-dim ECAPA-TDNN embeddings via SpeechBrain (`spkrec-ecapa-voxceleb`).
     - Cosine similarity matching against stored profiles (threshold ≥ 0.55).
     - Exclusive assignment ensures no duplicate name matches.
  6. Matched speakers are auto-renamed in the transcript (e.g., `SPEAKER_00` → `"Babuji Abraham"`).
  7. GPU memory explicitly cleared after processing.

### Stage 3: Analytics & Feature Generation

- **Objective:** Generate comprehensive AI-powered analytics: bilingual summaries, action items, sentiment analysis, topic segmentation, requirements, documentation, speaker report cards, keyword extraction, meeting culture score, and enable a cross-meeting RAG chatbot with video navigation.
- **Tool(s) Used:** Groq API (Llama 3.3 70B Versatile), LangChain, ChromaDB, HuggingFace Embeddings, Chart.js
- **Input Data:** `storage/{meeting_id}/transcript.json`, `storage/{meeting_id}/speaker_map.json`
- **Output File Links:**
  - `storage/{meeting_id}/summary.json` — Bilingual summaries (English + Hindi)
  - `storage/{meeting_id}/action_items.json` — Action items, decisions, key takeaways, follow-ups, risks
  - `storage/{meeting_id}/sentiment.json` — Per-segment sentiment scores, emotion labels, mood summary
  - `storage/{meeting_id}/topics.json` — Topic segmentation with time ranges and speaker participation
  - `storage/{meeting_id}/requirements.json` — Functional/non-functional requirements, user stories, constraints
  - `storage/{meeting_id}/documentation.json` — Auto-generated meeting minutes (MoM)
  - `storage/{meeting_id}/followup_email.json` — AI-drafted professional follow-up email
  - `storage/chroma_db/` — Vector embeddings indexed in ChromaDB for RAG chatbot
- **Execution Details/Commands:**
  1. **Summarization** (`POST /summarize/{id}`): Groq Llama 3.3 70B generates speaker-wise + overall summaries in both English and Hindi (Devanagari script).
  2. **Action Items** (`POST /meeting/{id}/action-items`): Structured extraction with task description, assignee, deadline, priority, category, success criteria, dependencies, and mentioned_by. Supports HITL editing via `PUT`.
  3. **Decisions & Risks**: Captured alongside action items — who decided what, impact, alternatives considered, and risks with mitigation strategies.
  4. **Sentiment Analysis** (`POST /meeting/{id}/sentiment`): Per-segment mood scoring (-1.0 to +1.0), emotion labels (enthusiastic, frustrated, skeptical, etc.), overall mood summary, and turning point detection.
  5. **Topic Segmentation** (`POST /meeting/{id}/topics`): Identifies distinct discussion chapters with time ranges, titles, summaries, and participating speakers.
  6. **Requirements Mining** (`POST /meeting/{id}/requirements`): Extracts functional requirements (FR-001, FR-002...), non-functional requirements (NFR-001...), user stories (As a... I want... So that...), constraints, assumptions, risks, and open questions with MoSCoW prioritization.
  7. **Documentation Generation** (`POST /meeting/{id}/documentation`): Auto-generated meeting minutes with objective, attendees, agenda, and next steps.
  8. **Follow-Up Email** (`POST /meeting/{id}/followup-email`): Professional email draft combining summary + action items + decisions. Sendable via `POST .../send` with SMTP.
  9. **Auto Meeting Title** (`POST /meeting/{id}/auto-title`): AI-generated descriptive meeting title from transcript content.
  10. **Speaker Analytics** (`GET /meeting/{id}/speaker-analytics`): Per-speaker talk-time, word count, words-per-minute, interruption count. Pure computation — no LLM needed.
  11. **Speaker Report Cards** (`GET /meeting/{id}/speaker-report`): Comprehensive per-speaker scorecards aggregating transcript stats, sentiment breakdown, action items, and topic participation. Auto-classifies speaker role (Decision Maker, Presenter, Challenger, Doer, Observer, Contributor).
  12. **Keyword Cloud** (`GET /meeting/{id}/keywords`): Top 30 keywords extracted via word frequency analysis with stop-word filtering. Weighted for visual sizing.
  13. **Meeting Culture Score** (`GET /stats/culture-score`): Composite health metric (0–100) across all meetings with 4 weighted signals: Speaker Balance (30%, Gini-like), Sentiment Health (25%), Action Item Completion (30%), Meeting Efficiency (15%, decisions per 10 min). Grading: Excellent/Good/Needs Work/Poor.
  14. **RAG Indexing** (`POST /chat/index/{id}`): Transcript segments chunked into LangChain Documents with speaker/timestamp/meeting metadata. all-MiniLM-L6-v2 embeddings stored in ChromaDB. Meeting summary chunks injected for cross-meeting accuracy.
  15. **RAG Chat with Video Navigation** (`POST /chat/ask/stream`): Diverse retrieval algorithm (fetch 40 → round-robin across meetings → select 18 chunks) prevents single-meeting bias. SSE streaming for real-time token delivery. Source citations with meeting_id, speaker, timestamp, and excerpt. Clickable ▶ Play buttons open a VideoSidePanel (400px) that auto-seeks to the exact moment in the meeting video.
  16. **HITL Regeneration**: When speakers are renamed via speaker map, all AI insights regenerate in background with mapped names (force=True), ensuring all analytics use real names.

### Stage 4: Report Generation & Publishing

- **Objective:** Generate professional PDF reports, distribute summaries via email and Microsoft Teams, push action items to Jira for project management, export subtitles, and publish meeting notes to enterprise wikis.
- **Tool(s) Used:** fpdf2, smtplib, Microsoft Teams Webhook, Atlassian Jira REST API, Notion API, Confluence REST API
- **Input Data:** `summary.json`, `action_items.json`, `requirements.json`, `documentation.json`
- **Output File Links:**
  - Downloaded PDF summary report (NotoSans + NotoSansDevanagari fonts for Hindi support)
  - Downloaded full comprehensive report PDF (summary + actions + requirements + docs)
- **Execution Details/Commands:**
  1. **PDF Generation** (`GET /publish/{id}/pdf`): fpdf2 renders a professional layout with Unicode Hindi support using NotoSansDevanagari font.
  2. **Full Report PDF** (`GET /publish/{id}/full-report`): All analytics combined into one comprehensive PDF. Auto-generates any missing sections before building.
  3. **Full Report Email** (`POST /publish/{id}/full-report/email`): Generates and emails the full report PDF to specified recipients. Auto-populated recipient list from meeting speaker names.
  4. **Email Publishing** (`POST /publish/{id}`): Attaches PDF and sends via SMTP (Gmail App Passwords).
  5. **Teams Webhook** (`POST /publish/{id}`): Sends an Adaptive Card v1.4 with summary, decisions, and action items.
  6. **Jira Integration** (`POST /meeting/{id}/jira/push`): Pushes action items as Jira tickets with ADF (Atlassian Document Format) descriptions, priority mapping, and assignee resolution. Supports bi-directional sync via transitions API (`POST .../jira/sync`, `PUT .../jira/update`).
  7. **Notion Integration** (`POST /meeting/{id}/notion/push`): Pushes meeting notes, summary, and action items to Notion pages via the Notion API.
  8. **Confluence Integration** (`POST /meeting/{id}/confluence/push`): Publishes meeting documentation to Confluence spaces via the Confluence REST API.


---

## Part 3: Features & Innovation Summary

### List of Features Built

1. **Multi-Engine Speech-to-Text** — AssemblyAI (primary), Groq Whisper (ultra-fast), local WhisperX; configurable per meeting
2. **Speaker Diarization** — pyannote.audio 3.1 with neural VAD + clustering on GPU
3. **Voice Identification** — ECAPA-TDNN 192-dim embeddings, SNR-ranked clip selection, 5-stage audio preprocessing, cosine similarity matching (threshold ≥ 0.55), profile averaging for multi-session stability
4. **Bilingual AI Summaries** — Speaker-wise + overall summaries in both English and Hindi (Devanagari script)
5. **Action Item Extraction** — Structured tasks with assignee, deadline, priority, category, dependencies, success criteria, and context
6. **Decisions & Risk Tracker** — Captures who decided what, why, impact, alternatives considered, and identified risks with mitigation strategies
7. **Key Takeaways & Follow-Ups** — Bullet-point highlights and trackable follow-up items with urgency and ownership
8. **Auto Meeting Title** — AI-generated descriptive meeting title from transcript content
9. **Follow-Up Email Draft** — Professional email combining summary + action items, auto-populated recipients from speaker names, sendable via SMTP
10. **Per-Segment Sentiment Analysis** — Mood scoring (-1.0 to +1.0), emotion labels, overall mood summary, turning point detection, and sentiment timeline visualization
11. **Topic Segmentation** — Auto-detected discussion chapters with time ranges, titles, summaries, and participating speakers
12. **Requirements Mining** — Functional (FR-001...) and non-functional (NFR-001...) requirements, user stories, constraints, assumptions, risks, and open questions with MoSCoW prioritization
13. **Documentation Generation** — Auto-generated meeting minutes (MoM) with objective, attendees, agenda, and next steps
14. **Per-Speaker Report Cards** — Role classification (Decision Maker, Presenter, Challenger, Doer, Observer, Contributor), talk-time stats, sentiment summary, action items, topic participation
15. **Speaker Analytics** — Per-speaker talk-time %, word count, WPM, interruption detection (gap < 0.5s), segment count
16. **Keyword Cloud** — Top 30 keywords by frequency with stop-word filtering and weighted sizing
17. **Meeting Culture Score** — Composite health metric (0–100) with 4 weighted signals: Speaker Balance (30%), Sentiment Health (25%), Action Item Completion (30%), Meeting Efficiency (15%). Grading: Excellent/Good/Needs Work/Poor
18. **RAG Chatbot with SSE Streaming** — Cross-meeting Q&A with diverse round-robin retrieval (prevents single-meeting bias), source citations, session-based conversation memory (last 10 messages), meeting calendar context injection
19. **Video Navigation from Chat** — Clickable ▶ Play buttons on RAG chat citations open a VideoSidePanel (400px) auto-seeked to the exact timestamp in the meeting video. Supports smooth cross-meeting navigation
20. **Human-in-the-Loop (HITL)** — Speaker name mapping triggers async regeneration of all AI insights. Action items editable via PUT endpoint with status tracking (Done/In Progress/Pending)
21. **Professional PDF Reports** — Summary PDF and comprehensive full-report PDF with Unicode Hindi support. Auto-generates missing sections before building
22. **Full Report Email** — One-click email of comprehensive PDF with auto-populated recipient list from meeting speakers
23. **One-Click Email & Teams Publishing** — SMTP email with PDF attachment + Teams Adaptive Card v1.4
24. **Bidirectional Jira Integration** — Push action items as tickets with ADF descriptions, priority mapping, assignee resolution, status sync via transitions API
25. **Notion Integration** — Push meeting notes and summaries to Notion pages via Notion API
26. **Confluence Integration** — Publish meeting documentation to Confluence spaces via Confluence REST API
27. **Upload Deduplication** — SHA-256 hashing prevents reprocessing of duplicate video files
28. **Meeting Dashboard** — Aggregate stats (total meetings, unique speakers resolved via speaker maps, total duration), meetings-per-day chart, real-time statistics
29. **Global Keyword Search** — Weighted relevance scoring across transcripts, titles, and speakers
30. **In-Browser Video Playback** — Video player with HTTP Range request support for seeking, integrated into meeting detail and RAG chat
31. **System Health Check** — `GET /health` endpoint reporting GPU status, VRAM, storage usage, meeting pipeline status, and ChromaDB state
32. **Skeleton Loading & Toast Notifications** — Polished, premium UX with shimmer loading states and system-wide success/error feedback

### Innovation Highlight

ContextIQ's most innovative aspect is its **end-to-end, privacy-first architecture** that combines **local GPU-accelerated processing** for speech-to-text with **cloud LLM APIs for intelligence**. Unlike competitors that require all data to be uploaded to external servers, ContextIQ keeps raw audio and transcripts local while only sending text to Groq for analysis.

Key innovations include:

1. **Voice Identification** using ECAPA-TDNN neural embeddings with a 5-stage audio preprocessing pipeline (resample → normalize → bandpass filter → silence removal → re-normalize). Speakers enrolled once are automatically recognized in all future meetings via cosine similarity matching with exclusive assignment.

2. **Bilingual Hindi Summaries** in native Devanagari script — absent from all major competitors — with full Unicode PDF rendering support.

3. **Diverse Retrieval Algorithm** for the RAG chatbot that round-robins chunks across meetings (fetch 40 → select 18 via round-robin) to prevent single-meeting bias in cross-meeting queries.

4. **Citation-to-Video Navigation** — RAG chat answers include clickable ▶ Play buttons that open a side panel auto-seeked to the exact moment in the meeting video where the cited information was spoken.

5. **Human-in-the-Loop Workflow** where renaming speakers triggers async regeneration of all AI insights with mapped names, ensuring all analytics use real speaker identities.

6. **Meeting Culture Score** — a composite health metric combining Gini-like speaker balance (30%), sentiment health (25%), action item completion rate (30%), and decisions-per-10-minutes efficiency (15%) across all meetings.

7. **Bi-directional Jira Integration** using the transitions API for proper status changes between ContextIQ and Jira, with ADF (Atlassian Document Format) for rich ticket descriptions.

8. **Multi-Platform Publishing** — one-click distribution to Email, Teams (Adaptive Cards), Jira, Notion, and Confluence from a single meeting analysis.

---

## Part 4: Final Deliverables

- **Link to Final Analytics Report:** [Insert OneDrive link to the final PDF report generated by ContextIQ]
- **Link to Source Code Repository:** [https://github.com/pawanuikey06/ContextIQ](https://github.com/pawanuikey06/ContextIQ)
- **Self-Reported Transcript Accuracy (Optional):** [If your team ran an automated comparison against the provided PDF ground truth, state your percentage match here and the metric used]
