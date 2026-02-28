# ContextIQ — Comprehensive Technical Reference

> A topic-by-topic breakdown of every feature in ContextIQ, covering the architecture, algorithms, implementation details, data flow, and key code references.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Audio Ingestion & Preprocessing](#2-audio-ingestion--preprocessing)
3. [Multi-Engine Speech-to-Text](#3-multi-engine-speech-to-text)
4. [Speaker Diarization](#4-speaker-diarization)
5. [Voice Identification & Speaker Profiling](#5-voice-identification--speaker-profiling)
6. [Human-in-the-Loop Speaker Mapping](#6-human-in-the-loop-speaker-mapping)
7. [Bilingual Summarization](#7-bilingual-summarization)
8. [Action Item Extraction](#8-action-item-extraction)
9. [Sentiment Analysis](#9-sentiment-analysis)
10. [Topic Segmentation](#10-topic-segmentation)
11. [Requirements Mining](#11-requirements-mining)
12. [Documentation Generation (MoM)](#12-documentation-generation-mom)
13. [Follow-Up Email Drafting](#13-follow-up-email-drafting)
14. [Auto Meeting Title Generation](#14-auto-meeting-title-generation)
15. [RAG AI Chatbot](#15-rag-ai-chatbot)
16. [Speaker Analytics & Report Cards](#16-speaker-analytics--report-cards)
17. [Meeting Culture Score](#17-meeting-culture-score)
18. [Global Keyword Search](#18-global-keyword-search)
19. [PDF Report Generation](#19-pdf-report-generation)
20. [Email & Teams Publishing](#20-email--teams-publishing)
21. [Bidirectional Jira Integration](#21-bidirectional-jira-integration)
22. [Confluence & Notion Integration](#22-confluence--notion-integration)
23. [Meeting Dashboard & Statistics](#23-meeting-dashboard--statistics)
24. [Video Playback](#24-video-playback)
25. [Upload Deduplication](#25-upload-deduplication)
26. [Frontend Architecture](#26-frontend-architecture)

---

## 1. System Architecture Overview

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Svelte 5 + Vite 5 + TailwindCSS 3 | SPA with reactive UI, routing, charts |
| **Backend** | FastAPI + Uvicorn (ASGI) | REST API with 35+ endpoints |
| **LLM** | Groq (Llama 3.3 70B Versatile) | All AI insight generation |
| **Vector DB** | ChromaDB (SQLite-backed) | RAG embeddings for semantic search |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` | 384-dim vectors for ChromaDB |
| **Voice Model** | SpeechBrain ECAPA-TDNN | 192-dim speaker verification embeddings |
| **Storage** | File-based JSON + WAV/MP4 | No traditional database — full transparency |

### Data Flow

```
Video Upload → FFmpeg → Audio WAV → Noise Reduction → STT Engine → Transcript JSON
                                                                        ↓
Voice Clips ← Speaker Clips Extraction ← Diarized Transcript → Storage
    ↓                                                              ↓
Speaker Profiles ← Embedding Generation      LLM Insights (Summary, Actions, Sentiment, Topics...)
    ↓                                                              ↓
Auto-Match Future Meetings                   PDF / Email / Teams / Jira Publishing
```

### Storage Layout

```
storage/
├── {meeting_id}/
│   ├── transcript.json       # Diarized transcript with segments
│   ├── metadata.json         # Processing info, title, dates
│   ├── video.mp4             # Original video for playback
│   ├── speaker_clips/        # 10-second WAV clips per speaker
│   ├── speaker_map.json      # Manual name mappings (HITL)
│   ├── summary.json          # Bilingual summaries
│   ├── action_items.json     # Actions, decisions, takeaways
│   ├── sentiment.json        # Per-segment sentiment scores
│   ├── topics.json           # Topic segmentation
│   ├── requirements.json     # Requirements extraction
│   ├── documentation.json    # Auto-generated MoM
│   ├── followup_email.json   # Email draft
│   └── Meeting_Summary.pdf   # Generated PDF report
├── speaker_profiles/
│   └── profiles.json         # Global voice embeddings {name: [192 floats]}
├── chroma_db/                # ChromaDB vector store
└── models/                   # Cached SpeechBrain models
```

**Key files:** `app/main.py` (FastAPI app entry), `app/api/` (14 API modules), `app/services/` (business logic)

---

## 2. Audio Ingestion & Preprocessing

### API Endpoint
`POST /upload-video`

### Implementation: `app/api/upload.py`

### Process
1. **Upload**: Video file received via multipart form upload (max 500 MB)
2. **Deduplication**: SHA-256 hash computed over raw bytes; checked against `storage/_file_hashes.json` registry
3. **Audio Extraction**: FFmpeg converts video to 16 kHz mono WAV
   ```
   ffmpeg -i input.mp4 -ar 16000 -ac 1 -f wav output.wav
   ```
4. **Video Preservation**: Original `.mp4` moved to `storage/{meeting_id}/video.mp4` for in-browser playback

### Preprocessing Pipeline: `stt_service.py → _preprocess_audio()`

Before any STT engine processes the audio, two preprocessing steps are applied:

| Step | Library | Detail |
|---|---|---|
| **Noise Reduction** | `noisereduce` | Spectral gating with `prop_decrease=0.7` and `n_std_thresh_stationary=1.5`. Removes static hums while preserving speech. |
| **Volume Normalization** | numpy | Peak normalization to -1 dBFS: `audio *= (10^(-1/20)) / peak` |

Output: `{meeting_id}_clean.wav`

---

## 3. Multi-Engine Speech-to-Text

### Implementation: `app/services/stt_service.py` → `AudioTranscriptionService`

### Engine Selection

Configured via `STT_MODE` environment variable:

| Mode | Engine | Diarization | Pros | Cons |
|---|---|---|---|---|
| `assemblyai` | AssemblyAI `universal-2` | Native (single API call) | Best accuracy, zero GPU | Cloud dependency |
| `groq` | Groq `whisper-large-v3-turbo` | Local pyannote (separate) | Blazing fast transcription | 25 MB file limit |
| `local` | WhisperX `medium` | Local pyannote (separate) | 100% private, no internet | Requires GPU & VRAM |
| `auto` | Groq → Local fallback | Local pyannote | Best of both worlds | Groq file limit |

### AssemblyAI Engine: `_transcribe_assemblyai()`

- Uploads audio to AssemblyAI with `speaker_labels=True`
- Uses `language_detection=True` for auto language detection
- Supports `SPEAKERS_EXPECTED` hint from `.env` for improved accuracy
- Converts AssemblyAI's A/B/C labels to `SPEAKER_00/01/02` format:
  ```python
  f"SPEAKER_{ord(utt.speaker) - ord('A'):02d}"  # A→00, B→01
  ```

### Groq Whisper Engine: `_transcribe_groq()`

- Checks 25 MB file size limit before upload
- Uses `whisper-large-v3-turbo` model with `verbose_json` response format
- Returns segments with timestamps but **no speaker labels** (marked as `UNKNOWN`)
- Requires separate diarization step (pyannote)

### Local WhisperX Engine: `_transcribe_local()`

- Loads WhisperX `medium` model onto GPU/CPU
- Performs word-level transcription with CTranslate2 acceleration
- After transcription, model is explicitly deleted and `torch.cuda.empty_cache()` is called
- Uses forced alignment via `wav2vec2` for precise word boundaries

### Standardized Output Format

All engines produce the same output shape:
```json
{
  "language": "en",
  "segments": [
    {"start": 12.05, "end": 15.30, "text": "Let's discuss the roadmap.", "speaker": "SPEAKER_00"}
  ]
}
```

---

## 4. Speaker Diarization

### Implementation: `stt_service.py` → `_load_diarization_pipeline()`, `_assign_speakers_from_diarization()`

### When Used
- **AssemblyAI mode**: Diarization is native — handled by AssemblyAI's API in a single call
- **Groq & Local modes**: Separate diarization step using local `pyannote.audio`

### Pipeline Loading

The system tries multiple pyannote models with a fallback chain:
1. `pyannote/speaker-diarization-3.1` (preferred)
2. `pyannote/speaker-diarization`
3. `pyannote/speaker-diarization-community-1`

Requires `HF_TOKEN` from `.env` for HuggingFace model access.

### Segment-to-Speaker Assignment Algorithm

When diarization runs separately from transcription (Groq/WhisperX), the system must merge two independent outputs:

**Input**: Transcript segments (text + timestamps) + Diarization output (speaker + time ranges)

**Algorithm** (`_assign_speakers_from_diarization`):
```
For each transcript segment [seg_start, seg_end]:
    best_speaker = UNKNOWN
    best_overlap = 0.0
    
    For each diarization segment [d_start, d_end, d_speaker]:
        overlap = max(0, min(seg_end, d_end) - max(seg_start, d_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = d_speaker
    
    segment.speaker = best_speaker
```

This maximum-overlap assignment ensures each transcript segment gets the speaker who talked the most during that time window.

---

## 5. Voice Identification & Speaker Profiling

### Implementation: `app/services/voice_embedding_service.py` → `VoiceEmbeddingService`

### Neural Architecture
- **Model**: ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation in Time-Delay Neural Networks)
- **Source**: SpeechBrain `spkrec-ecapa-voxceleb` (trained on VoxCeleb dataset)
- **Output**: 192-dimensional embedding vector per speaker
- **Storage**: Cached in `storage/models/` to avoid re-downloading

### End-to-End Pipeline

```
Audio → Extract ~10s clip per speaker → Preprocess clip → ECAPA-TDNN → 192-dim embedding → Cosine match against profiles
```

### Step 1: Speaker Clip Extraction — `extract_speaker_clips()`

For each speaker in the transcript:
- Loads the full meeting audio
- Groups all segments belonging to that speaker
- Calls `_build_clip()` to select the best segments

### Step 2: SNR-Based Clip Selection — `_build_clip()`

**Not just the longest segments** — the system ranks segments by speech quality:

```python
for each segment:
    chunk = audio[start:end]
    rms = sqrt(mean(chunk²))          # Root-Mean-Square energy
    duration = min(len(chunk)/sr, 5.0) # Cap at 5 seconds
    score = rms × duration             # Quality score
```

Segments are sorted by quality score (descending), and the clearest ones are concatenated until ~10 seconds of audio is collected.

### Step 3: Audio Preprocessing — `_preprocess_audio()`

A 5-step preprocessing pipeline optimized for neural voice embeddings:

| Step | Method | Detail |
|---|---|---|
| 1. Resample | `_resample()` | Linear interpolation to 16 kHz (SpeechBrain requirement) |
| 2. Normalize | `_normalize()` | Peak normalization to [-1, 1] range |
| 3. Bandpass Filter | `_bandpass_filter()` | FFT-based: zeros out frequencies below 80 Hz and above 7600 Hz. Removes rumble and high-frequency noise while preserving the full speech band. |
| 4. Silence Removal | `_remove_silence()` | Frame-level RMS energy thresholding (30ms frames, 0.01 threshold). Drops silent frames. |
| 5. Re-normalize | `_normalize()` | Re-normalize after filtering to maximize dynamic range |

### Step 4: Embedding Generation — `generate_embedding()`

- Loads audio via `soundfile` (avoids torchaudio/FFmpeg dependency issues)
- Converts to mono, resamples to 16 kHz if needed
- Converts numpy array to PyTorch tensor `[1, num_samples]`
- Normalizes: `signal = signal / (signal.abs().max() + 1e-8)`
- Calls `model.encode_batch(signal)` → returns 192-dim embedding vector

### Step 5: Profile Storage — `save_speaker_profile()`

- Stored in `storage/speaker_profiles/profiles.json`
- Format: `{"Speaker Name": [192 floats], ...}`
- **Running Average**: If re-enrolling the same speaker, the new embedding is averaged with the existing one:
  ```python
  averaged = (existing + new) / 2.0
  ```
  This improves cross-meeting accuracy as the profile captures more vocal variety.

### Step 6: Speaker Matching — `match_speakers()`

- Loads all stored profiles
- Generates embeddings for each speaker clip in the new meeting
- Computes **cosine similarity** between every clip and every profile:
  ```python
  similarity = dot(a, b) / (norm(a) × norm(b))
  ```
- **Threshold**: 0.55 (configurable). Matches above this threshold are accepted.
- **Greedy assignment**: Once a profile is matched, it's marked as "used" to prevent double-assignment
- All similarity scores are logged for debugging

### API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /meeting/{id}/speaker-clips` | List/auto-extract speaker clips |
| `GET /meeting/{id}/speaker-clips/{speaker}` | Stream a speaker's audio clip |
| `GET /speaker-profiles` | List all enrolled voice profiles |
| `POST /meeting/{id}/speaker-profiles` | Enroll profiles from speaker map |
| `POST /meeting/{id}/voice-match` | Re-run matching on existing meeting |

---

## 6. Human-in-the-Loop Speaker Mapping

### Implementation: `app/api/speaker_map.py`

### How It Works
1. User renames speakers in the UI (e.g., `SPEAKER_00` → `"Babuji Abraham"`)
2. Frontend calls `POST /meeting/{id}/speaker-map` with the mapping
3. Speaker map is saved to `storage/{meeting_id}/speaker_map.json`
4. Transcript segments are updated in-place with mapped names
5. **Background regeneration** of ALL AI insights is triggered

### Background Regeneration — `_regenerate_all_insights()`

Uses FastAPI's `BackgroundTasks` to asynchronously regenerate **8 AI tasks** with `force=True`:

| Order | Task | Service Method |
|---|---|---|
| 1 | RAG Re-indexing | `rag.ingest_meeting()` |
| 2 | Bilingual Summary | `summary.summarize_meeting()` |
| 3 | Action Items | `insights.extract_action_items()` |
| 4 | Requirements | `insights.extract_requirements()` |
| 5 | Documentation | `insights.generate_documentation()` |
| 6 | Follow-up Email | `insights.generate_followup_email()` |
| 7 | Sentiment Analysis | `insights.analyze_sentiment()` |
| 8 | Topic Segmentation | `insights.extract_topics()` |

The API returns `200 OK` immediately — all regeneration runs in the background. The `force=True` flag ensures cached results are discarded and rebuilt with the corrected speaker names.

---

## 7. Bilingual Summarization

### API Endpoint
`POST /summarize/{meeting_id}`

### Implementation: `app/services/summary_service.py` → `MeetingSummaryService`

### Process
1. **Conversation Builder**: Reconstructs readable dialogue from raw segments:
   ```
   [Babuji Abraham]: Let's discuss the delivery timeline.
   [Poornima Kumaran]: I think we need two more weeks.
   ```
2. **English Summary**: Overall meeting summary via Groq Llama 3.3 70B
3. **Hindi Summary**: Separate LLM call with specific prompt engineering for natural Hindi (not machine translation)
4. **Per-Speaker Summaries**: Individual LLM calls per speaker with contribution-focused prompts

### Output: `storage/{meeting_id}/summary.json`
```json
{
  "overall_summary_en": "...",
  "overall_summary_hi": "...",
  "speaker_summaries_en": {"Babuji Abraham": "...", "Poornima Kumaran": "..."}
}
```

---

## 8. Action Item Extraction

### API Endpoint
`POST /meeting/{meeting_id}/action-items`

### Implementation: `app/services/insights_service.py` → `extract_action_items()`

### Structured Output

Each action item extracted by the LLM contains:

| Field | Example |
|---|---|
| `task` | Prepare the deployment checklist |
| `assigned_to` | Varun Kumar |
| `raised_by` | Babuji Abraham |
| `priority` | high |
| `category` | development |
| `deadline` | March 5, 2026 |
| `context` | Discussed during infrastructure review |
| `success_criteria` | All items verified and signed off |
| `dependencies` | Requires staging environment setup |

Also extracts alongside:
- **Decisions** — who decided, what, why, alternatives, impact
- **Key Takeaways** — bullet-point highlights
- **Follow-ups** — items needing future discussion
- **Risk Flags** — potential risks identified in the meeting

### Error Handling
- LLM returns structured JSON; the service uses regex fallback for malformed outputs
- Results cached in `storage/{meeting_id}/action_items.json`
- `force=True` discards cache and re-generates

---

## 9. Sentiment Analysis

### API Endpoint
`POST /meeting/{meeting_id}/sentiment`

### Implementation: `app/services/insights_service.py` → `analyze_sentiment()`

### Process
- Every transcript segment is sent to the LLM in a single batch call
- Each segment receives:
  - **Sentiment label**: `positive`, `negative`, or `neutral`
  - **Confidence score**: 0.0 to 1.0
  - **Emotion label**: e.g., `enthusiastic`, `frustrated`, `curious`

### Frontend Visualization
- Per-speaker sentiment trends (line chart over time)
- Overall meeting mood distribution (pie chart)
- Key sentiment highlights with timestamps

---

## 10. Topic Segmentation

### API Endpoint
`POST /meeting/{meeting_id}/topics`

### Implementation: `app/services/insights_service.py` → `extract_topics()`

### Output
Each topic contains:
- `title` — concise topic name
- `summary` — what was discussed
- `start_time` / `end_time` — time range in the meeting
- `speakers[]` — who participated in this topic

### Use Case
Enables "jump to topic" in the frontend — click on a topic chapter to jump to that point in the video/transcript.

---

## 11. Requirements Mining

### API Endpoint
`POST /meeting/{meeting_id}/requirements`

### Implementation: `app/services/insights_service.py` → `extract_requirements()`

### Extracted Categories
- **Functional Requirements** — what the system should do
- **Non-Functional Requirements** — performance, security, scalability
- **Technical Constraints** — technology stack limitations
- **Assumptions** — underlying assumptions discussed
- **User Stories** — enforces "As a [role], I want [feature] so that [benefit]" format

### Prioritization
Each requirement is tagged with MoSCoW priority: Must / Should / Could / Won't

---

## 12. Documentation Generation (MoM)

### API Endpoint
`POST /meeting/{meeting_id}/documentation`

### Implementation: `app/services/insights_service.py` → `generate_documentation()`

### Output Structure
- **Meeting Objective** — auto-detected from transcript
- **Attendees** — list of speakers with roles
- **Agenda Items** — topics discussed
- **Discussion Points** — step-by-step breakdown
- **Decisions Made** — with rationale
- **Action Items** — with assignees and deadlines
- **Next Steps** — future meeting items

---

## 13. Follow-Up Email Drafting

### API Endpoint
`POST /meeting/{meeting_id}/followup-email`

### Implementation: `app/services/insights_service.py` → `generate_followup_email()`

### Process
Combines: meeting title + summary + action items + decisions into a professional email draft.

### Send Capability
`POST /meeting/{meeting_id}/followup-email/send` — sends the drafted email via SMTP.

---

## 14. Auto Meeting Title Generation

### API Endpoint
`POST /meeting/{meeting_id}/auto-title`

### Implementation: `app/services/insights_service.py` → `generate_title()`

### Process
1. Loads the first ~5000 characters of transcript
2. Sends to Groq LLM with a prompt requesting a concise, descriptive title
3. Saves the title to `metadata.json` under the `auto_title` key
4. **Auto-triggered** after transcription completes (in `transcribe.py`)

---

## 15. RAG AI Chatbot

### API Endpoints
- `POST /chat/ask` — single response
- `POST /chat/ask/stream` — SSE streaming (preferred)
- `POST /chat/index/{meeting_id}` — index a meeting
- `GET /chat/meetings` — list indexed meetings
- `POST /chat/clear/{session_id}` — clear conversation memory

### Implementation: `app/services/rag_service.py` → `MeetingRAGService`

### Ingestion — `ingest_meeting()`

1. Loads transcript + speaker map + metadata
2. Creates one LangChain `Document` per segment with rich metadata:
   ```python
   page_content = f"[{meeting_date}, {meeting_day}] {speaker}: {text}"
   metadata = {meeting_id, meeting_title, speaker, start, end, chunk_index, ...}
   ```
3. Creates a **Meeting Summary Chunk** — a synthetic document listing all speakers, duration, and date. This enables cross-meeting comparison queries.
4. Upserts into ChromaDB with unique IDs: `{meeting_id}_seg_{i}`

### Diverse Retrieval Algorithm — `_diverse_retrieve()`

**Problem**: Standard top-k retrieval is biased toward the meeting most similar to the query. If you have 5 meetings indexed but only 1 is about "deployment," all 18 chunks might come from that single meeting.

**Solution**: Round-robin retrieval across meetings:

```
1. Fetch 40 candidate chunks from ChromaDB (similarity search)
2. Group by meeting_id → {"meeting_A": [chunks...], "meeting_B": [chunks...]}
3. Round-robin: take 1 from A, 1 from B, 1 from A, 1 from B... until 18 selected
4. Every meeting is guaranteed representation in the context
```

### Meeting Calendar Context

The system prompt includes a date-indexed list of all meetings:
```
- Laptop Delivery Delay Resolution Meeting: February 28, 2026, Friday, 1:30 PM
- Jeff Thompson Visit Postmortem Review: February 28, 2026, Friday, 2:15 PM
```

This enables time-based queries like "What did we discuss on Friday?"

### SSE Streaming — `query_stream()`

- Uses `langchain_openai.ChatOpenAI` with Groq's OpenAI-compatible endpoint
- Streams tokens via Server-Sent Events (SSE)
- Yields `(type, data)` tuples: `("token", "word...")`, `("citations", [...])`, `("done", "")`
- Frontend shows a blinking cursor effect during streaming

### Conversation Memory

- Stores last 10 messages per session ID in a dictionary
- Provides context for follow-up questions ("What about the deadlines?" after asking about action items)
- Cleared via `POST /chat/clear/{session_id}`

### Auto-Recovery

If ChromaDB is corrupted (e.g., dimension mismatch), `_diverse_retrieve()` catches the error and triggers `_rebuild_index()` — which nukes the collection and re-indexes all meetings from scratch.

---

## 16. Speaker Analytics & Report Cards

### API Endpoint
`GET /meeting/{meeting_id}/speaker-analytics`

### Implementation: `app/api/insights.py`

### Metrics Per Speaker
- **Talk-time** — total seconds and percentage of meeting
- **Speaking pace** — words per minute
- **Segment count** — number of turns
- **Sentiment distribution** — positive/negative/neutral percentages
- **Role classification** — auto-classified as Decision Maker, Presenter, Facilitator, Observer, etc.
- **Key contributions** — summarized from their individual segments

---

## 17. Meeting Culture Score

### API Endpoint
`GET /stats/culture-score`

### Implementation: `app/api/stats.py` → `get_culture_score()`

### Composite Score (0–100)

A weighted combination of 4 signals:

| Signal | Weight | Formula |
|---|---|---|
| **Speaker Balance** | 30% | Gini-like: `(1 - max_speaker_share) / (1 - 1/N) × 100`. Perfect balance = 100, one person dominates = 0. |
| **Sentiment Health** | 25% | `(positive_segments + neutral_segments) / total_segments × 100` |
| **Action Completion** | 30% | `done_items / total_items × 100` |
| **Meeting Efficiency** | 15% | `decisions_count / (duration_minutes / 10) × 100`. Target: 1 decision per 10 minutes. |

### Grading
| Score | Grade |
|---|---|
| 80-100 | Excellent |
| 60-79 | Good |
| 40-59 | Needs Work |
| 0-39 | Poor |

### Aggregation
- Computed per meeting first, then averaged across all meetings
- Includes per-meeting breakdown with individual signal scores

---

## 18. Global Keyword Search

### API Endpoint
`GET /search?q=keyword&limit=10`

### Implementation: `app/api/search.py` → `search_meetings()`

### Weighted Relevance Scoring

| Match Type | Points |
|---|---|
| Title match | 10 |
| Speaker name match | 5 |
| Transcript keyword (per hit) | 1 |

### Snippet Highlighting
Extracts ±30 character context window around each keyword match, with ellipsis for truncation. Up to 3 snippets per meeting.

### Multi-Field Search
Searches simultaneously across: title, all speaker names, and full transcript text.

---

## 19. PDF Report Generation

### Implementation: `app/services/publish_service.py` → `MeetingPublishService`

### Unicode Support
Custom `fpdf2` subclass (`SummaryPDF`) with registered TrueType fonts:
- **NotoSans** — for English text
- **NotoSansDevanagari** — for Hindi (Devanagari script) text

### Report Types
1. **Summary PDF** (`GET /publish/{id}/pdf`) — bilingual summary with per-speaker contributions
2. **Full Report PDF** (`GET /publish/{id}/full-report`) — combines summary + action items + decisions + requirements + documentation into one comprehensive document

### Layout
- Page header with accent line
- Centered meeting title and date
- Section headings with underline accents
- Footer with page numbers and ContextIQ branding

---

## 20. Email & Teams Publishing

### Email: `send_email()`
- Uses Python's `smtplib` with `MIME/Multipart`
- Attaches PDF as email attachment
- Supports Gmail App Passwords via configurable SMTP settings
- Meeting title used as email subject

### Microsoft Teams: `send_to_teams()`
- Sends **Adaptive Card v1.4** to a configured webhook URL
- Card includes: summary snippet, top 5 action items, top 4 decisions, top 4 takeaways, top 3 speaker highlights
- Rich formatting with ColumnSets, TextBlocks, and FactSets
- Zero AI cost — reads from cached JSON only

---

## 21. Bidirectional Jira Integration

### Implementation: `app/services/jira_service.py`

### API Endpoints
- `GET /jira/status` — check Jira configuration status
- `POST /meeting/{id}/jira/push` — push action items as Jira tickets
- `POST /meeting/{id}/jira/sync` — sync Jira status back to ContextIQ
- `PUT /meeting/{id}/jira/update` — update Jira ticket from ContextIQ changes

### Field Mapping (ContextIQ → Jira)

| ContextIQ Field | Jira Field |
|---|---|
| `task` | Summary |
| `priority` | Priority (Highest/High/Medium/Low/Lowest) |
| `category` | Issue Type (development→Story, testing→Bug, others→Task) |
| `deadline` | Due Date |
| `context` + `success_criteria` + `dependencies` | ADF Description (rich text) |
| `category` | Labels |

### ADF (Atlassian Document Format)
The system builds structured Atlassian Document Format bodies for rich ticket descriptions, including panels, bullet lists, and formatted text.

### Status Transitions
Jira doesn't allow directly setting status — you must use transitions:
```python
# 1. Get available transitions for the ticket
GET /issue/{key}/transitions

# 2. Find the transition that leads to the target status
transition_id = find_transition(target_status)

# 3. Execute the transition
POST /issue/{key}/transitions  {transition: {id: transition_id}}
```

### Bidirectional Sync — `sync_tickets()`
- Fetches current Jira status, priority, and assignee for all linked tickets
- Compares with local action items
- Updates local items in-place with fresh Jira data
- Maps Jira statuses back to ContextIQ statuses using `JIRA_STATUS_MAP`

---

## 22. Confluence & Notion Integration

### Confluence: `app/api/confluence.py`
- Converts meeting data to XHTML storage format
- Pushes to Confluence pages via REST API v2
- API token authentication from `.env`

### Notion: `app/api/notion.py`
- Maps meeting sections to Notion block types (headings, lists, callouts)
- Pushes via Notion API
- API token authentication from `.env`

---

## 23. Meeting Dashboard & Statistics

### API Endpoints
- `GET /meetings` — list all meetings with metadata
- `GET /stats` — aggregate statistics

### Implementation: `app/api/diarization.py`, `app/api/stats.py`

### Directory Filtering
The `list_meetings` endpoint skips non-meeting directories:
```python
SKIP_DIRS = {"chroma_db", "speaker_profiles", "models", "__pycache__"}
```

### Unique Speaker Counting
The stats endpoint resolves speaker labels through `speaker_map.json` before counting:
```python
resolved = speaker_map.get(spk, spk)  # SPEAKER_00 → "Babuji Abraham"
all_speakers.add(resolved)
```
This ensures the same person appearing in multiple meetings with different raw labels is counted once.

---

## 24. Video Playback

### API Endpoint
`GET /meeting/{meeting_id}/video`

### Implementation: `app/api/diarization.py` → `get_meeting_video()`

### HTTP Range Request Support
Supports the `Range` header for in-browser seeking:
- Parses `Range: bytes=start-end`
- Returns `206 Partial Content` with `Content-Range` header
- Chunks data in 8192-byte blocks
- Full file response with `Accept-Ranges: bytes` when no Range header

---

## 25. Upload Deduplication

### Implementation: `app/api/upload.py`

### Process
1. Compute SHA-256 hash of uploaded file bytes
2. Check `storage/_file_hashes.json` registry
3. If hash exists → return existing `meeting_id` (skip reprocessing)
4. If hash is new → generate UUID, extract audio, register hash
5. Edge case: if hash exists but audio file is missing → re-extract with same meeting_id

---

## 26. Frontend Architecture

### Tech Stack
- **Framework**: Svelte 5 (compiled, reactive)
- **Build Tool**: Vite 5 (HMR, fast builds)
- **Styling**: TailwindCSS 3 (utility-first)
- **Routing**: `svelte-spa-router` (hash-based client-side routing)
- **Icons**: Lucide Svelte
- **Charts**: Chart.js (sentiment, analytics, culture score)

### Key Pages
| Route | Component | Purpose |
|---|---|---|
| `/` | `Dashboard.svelte` | Meeting list, stats, culture score, search |
| `/meeting/:id` | `MeetingDetail.svelte` | Full meeting view with all features |

### UX Features
- **Skeleton loading** — shimmer placeholders during data fetch
- **Toast notifications** — system-wide feedback for all operations
- **Tab navigation** — organized sections (Transcript, Summary, Actions, Sentiment, Topics, etc.)
- **Audio playback** — listen to speaker clips directly in the UI
- **Video player** — embedded video with seeking support

---

*Document Version: 1.0 — February 28, 2026*
*Source: Full codebase scan of all 14 API modules and 6 service classes*
