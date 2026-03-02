# ContextIQ — Backend Documentation (Code-Level)

> **End-to-end, code-level documentation for the ContextIQ Meeting Intelligence System backend. Every file, class, function, and data flow explained in detail.**

---

## Table of Contents

| # | Section | Key Files |
|---|---------|-----------|
| 1 | [System Overview](#1-system-overview) | `.env`, `requirements.txt` |
| 2 | [Entry Point](#2-entry-point--mainpy) | `app/main.py` |
| 3 | [Data Models](#3-data-models--schemaspy) | `app/schemas/schemas.py` |
| 4 | [Video Upload Pipeline](#4-video-upload-pipeline) | `app/api/upload.py`, `app/services/video_to_audio.py` |
| 5 | [Transcription & Diarization](#5-transcription--diarization-engine) | `app/api/transcribe.py`, `app/services/stt_service.py` |
| 6 | [Meeting Management](#6-meeting-management-crud) | `app/api/diarization.py`, `app/services/storage_service.py`, `app/services/speaker_service.py` |
| 7 | [AI Summaries](#7-ai-powered-summaries) | `app/api/summarize.py`, `app/services/summary_service.py` |
| 8 | [AI Insights & Analytics](#8-ai-insights--analytics) | `app/api/insights.py`, `app/services/insights_service.py` |
| 9 | [RAG Chatbot](#9-rag-chatbot) | `app/api/chat.py`, `app/services/rag_service.py` |
| 10 | [Publishing & Delivery](#10-publishing--delivery) | `app/api/publish.py`, `app/services/publish_service.py` |
| 11 | [Speaker Map & Voice ID](#11-speaker-map--voice-identification) | `app/api/speaker_map.py`, `app/api/voice_profiles.py`, `app/services/voice_embedding_service.py` |
| 12 | [Third-Party Integrations](#12-third-party-integrations) | `app/api/jira.py`, `app/services/jira_service.py`, etc. |
| 13 | [Dashboard & Search](#13-dashboard--search) | `app/api/stats.py`, `app/api/search.py` |
| 14 | [Storage Layout](#14-storage-layout) | File system structure |

---

## 1. System Overview

ContextIQ is a **FastAPI-based Meeting Intelligence System** (v2.0.0) that transforms raw meeting videos into structured, searchable, AI-analyzed knowledge. It processes meetings through a multi-stage pipeline:

```
Video Upload → Audio Extraction → Transcription + Diarization → AI Analytics → Publishing
```

### 1.1 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Framework** | FastAPI 0.109 + Uvicorn 0.27 | Async REST API server |
| **Data Validation** | Pydantic v2 | Request/response schemas |
| **Transcription** | WhisperX 3.8 / Groq Whisper / AssemblyAI | Speech-to-text (3 engines) |
| **Diarization** | pyannote-audio 4.0 | Speaker identification |
| **LLM** | Groq API → Llama 3.3 70B Versatile | Summaries, insights, analysis |
| **RAG** | LangChain + ChromaDB + HuggingFace `all-MiniLM-L6-v2` | Q&A over transcripts |
| **Voice ID** | SpeechBrain ECAPA-TDNN | Speaker verification embeddings |
| **PDF** | fpdf2 with NotoSans + NotoSansDevanagari fonts | Bilingual PDF reports |
| **GPU** | PyTorch 2.10 + CUDA 12.8 | GPU-accelerated ML inference |
| **Audio** | FFmpeg | Video → WAV 16kHz mono extraction |

### 1.2 Configuration (`.env`)

The system reads these environment variables at runtime:

```bash
# Audio extraction
FFMPEG_PATH=C:/ffmpeg/.../ffmpeg.exe       # Path to FFmpeg binary

# ML Models (pyannote requires HuggingFace token)
HF_TOKEN="hf_..."                          # HuggingFace access token

# LLM + Transcription (Groq provides both)
GROQ_API_KEY="gsk_..."                     # Groq API key for Llama 3.3 + Whisper

# Email delivery
SMTP_HOST=smtp.gmail.com                   # SMTP server
SMTP_PORT=587                              # TLS port
SMTP_USER=your@gmail.com                   # Sender email
SMTP_PASSWORD=xxxx xxxx xxxx xxxx          # App-specific password

# Microsoft Teams
TEAMS_WEBHOOK_URL=https://...              # Incoming webhook URL
```

---

## 2. Entry Point — `main.py`

**File:** `app/main.py` (192 lines)

This is where the FastAPI application is created and configured. It is the single entry point for the entire backend.

### 2.1 Application Creation

```python
app = FastAPI(title="Meeting Intelligence System", version="2.0.0")
```

This creates the FastAPI application object with a descriptive title and version number. When you run `uvicorn app.main:app`, this is the object that Uvicorn serves.

### 2.2 Directory Setup

```python
for d in ["data/audio", "storage"]:
    Path(d).mkdir(parents=True, exist_ok=True)
```

At startup, the app ensures two critical directories exist:
- **`data/audio/`** — Where extracted WAV audio files are stored
- **`storage/`** — Where all per-meeting JSON artifacts (transcripts, summaries, etc.) are stored

### 2.3 CORS Middleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:4173",    # Vite preview
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Why:** The Svelte frontend runs on port `5173` (Vite dev server). Without CORS middleware, the browser would block all API calls from the frontend due to the Same-Origin Policy. This configuration allows the frontend to make any HTTP method (GET, POST, PUT, DELETE, PATCH) to the backend.

### 2.4 Router Registration

The app registers **14 separate routers**, each handling a specific domain of functionality:

```python
app.include_router(upload_router, tags=["Upload"])           # Video upload
app.include_router(transcribe_router, tags=["Transcription"]) # STT + diarization
app.include_router(diarization_router, tags=["Meeting"])       # Meeting CRUD
app.include_router(summarize_router, tags=["Summary"])         # AI summaries
app.include_router(publish_router, tags=["Publish"])           # PDF + email
app.include_router(speaker_map_router, tags=["Speaker Map"])   # HITL naming
app.include_router(chat_router, tags=["Chat"])                 # RAG chatbot
app.include_router(insights_router, tags=["Insights"])         # AI analytics
app.include_router(stats_router, tags=["Stats"])               # Dashboard
app.include_router(search_router, tags=["Search"])             # Keyword search
app.include_router(jira_router, tags=["Jira"])                 # Jira integration
app.include_router(notion_router, tags=["Notion"])             # Notion integration
app.include_router(confluence_router, tags=["Confluence"])     # Confluence integration
app.include_router(voice_profiles_router, tags=["Voice Profiles"]) # Voice ID
```

**Design Pattern:** Each router is an `APIRouter()` instance defined in its own file under `app/api/`. This keeps the codebase modular — each file handles one feature area. The `tags` parameter groups endpoints in the auto-generated Swagger docs (`/docs`).

### 2.5 Root Endpoint (`GET /`)

Returns a JSON index of all 50+ API endpoints, organized by stage. This serves as a self-documenting API reference.

### 2.6 Health Check (`GET /health`)

Reports system status:
- **GPU:** Whether CUDA is available, device name, total/free VRAM
- **Storage:** Total meetings, disk usage in MB, meetings broken down by status (uploaded/transcribed/summarized/published)
- **ChromaDB:** Whether the RAG vector store is initialized

---

## 3. Data Models — `schemas.py`

**File:** `app/schemas/schemas.py` (97 lines)

All request/response models use **Pydantic v2 `BaseModel`**. Pydantic provides automatic data validation, serialization, and documentation generation.

### 3.1 Core Transcript Models

```python
class SegmentOut(BaseModel):
    """A single transcription segment with speaker and timestamps."""
    start: float    # Start time in seconds (e.g., 0.0)
    end: float      # End time in seconds (e.g., 4.2)
    speaker: str    # Speaker label (e.g., "SPEAKER_00" or "Pawan")
    text: str       # Transcribed text
```

This is the fundamental building block of every transcript. Every transcribed utterance becomes a `SegmentOut`.

```python
class SpeakerSegment(BaseModel):
    """Speaker-grouped segment — no speaker field needed since it's the dict key."""
    start: float
    end: float
    text: str
```

Used inside the `speakers` dictionary where the key is already the speaker name, so the `speaker` field is omitted to avoid redundancy.

### 3.2 Response Models

```python
class TranscriptResponse(BaseModel):
    meeting_id: str                              # UUID
    audio_path: str                              # Path to WAV file
    segments: List[SegmentOut]                   # Flat chronological list
    speakers: Dict[str, List[SpeakerSegment]]    # Grouped by speaker
```

**Why two formats?** The `segments` list preserves chronological order (for timeline view), while the `speakers` dict groups by speaker (for speaker-centric views). Both are generated from the same data.

### 3.3 Metadata Models

```python
class MeetingMetadataResponse(BaseModel):
    meeting_id: str
    title: Optional[str] = None
    auto_title: Optional[str] = None      # AI-generated title
    date: Optional[str] = None
    participants: Optional[List[str]] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None           # uploaded/transcribed/summarized/published
    segment_count: Optional[int] = None
    speaker_count: Optional[int] = None
    processed_at: Optional[str] = None     # ISO timestamp
    processed_date: Optional[str] = None   # "February 28, 2026"
    processed_day: Optional[str] = None    # "Friday"
    processed_time: Optional[str] = None   # "03:45 PM"
```

All fields are `Optional` because metadata is built up progressively — at upload time only `meeting_id` exists; after transcription, `segment_count` and `speaker_count` are added; after AI analysis, `auto_title` is added.

---

## 4. Video Upload Pipeline

### 4.1 API Route: `POST /upload-video`

**File:** `app/api/upload.py` (142 lines)

This endpoint accepts a video file and returns a `meeting_id` that's used as the identifier for all subsequent operations.

#### Complete Flow:

```
1. Validate file format (.mp4, .mkv, .mov only)
2. Read file bytes into memory
3. Validate file size (≤ 500 MB)
4. Compute SHA-256 hash of the file
5. Check deduplication registry
   → If duplicate: return existing meeting_id immediately
   → If new: continue processing
6. Generate UUID for the meeting
7. Write video to temp file
8. Extract audio via FFmpeg (16kHz, mono, WAV)
9. Register hash → meeting_id mapping
10. Move video to storage/{meeting_id}/video.mp4
11. Return { meeting_id, audio_path, message }
```

#### SHA-256 Deduplication (Key Feature):

```python
# Compute hash of entire video file
file_hash = hashlib.sha256(video_bytes).hexdigest()
hash_registry = _load_hashes()  # Loads storage/_file_hashes.json

if file_hash in hash_registry:
    existing_id = hash_registry[file_hash]
    # Return the existing meeting_id without re-processing
    return UploadResponse(
        meeting_id=existing_id,
        audio_path=str(audio_path),
        message=f"Duplicate file detected. Returning existing meeting: {existing_id}"
    )
```

**Why this matters:** If a user accidentally uploads the same video twice, the system detects it instantly (SHA-256 hash comparison) and returns the existing meeting data. This avoids wasting time on redundant transcription and saves storage space.

The hash registry is a simple JSON file (`storage/_file_hashes.json`):
```json
{
  "a1b2c3d4...": "550e8400-e29b-41d4-a716-446655440000",
  "e5f6g7h8...": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
}
```

### 4.2 Service: `VideoAudioConverter`

**File:** `app/services/video_to_audio.py` (44 lines)

This service wraps FFmpeg to extract audio from video files.

```python
class VideoAudioConverter:
    def __init__(self):
        self.ffmpeg_path = os.getenv("FFMPEG_PATH")
        # Validates that FFmpeg binary exists on disk

    def video_to_audio(self, video_path, audio_path):
        cmd = [
            self.ffmpeg_path,
            "-y",                    # Overwrite output
            "-i", str(video_path),   # Input video
            "-map", "0:a:0",         # Take ONLY the first audio stream
            "-vn",                   # Strip video (audio only)
            "-acodec", "pcm_s16le",  # 16-bit PCM encoding
            "-ar", "16000",          # 16kHz sample rate (required by Whisper)
            "-ac", "1",              # Mono channel
            str(audio_path)          # Output WAV file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
```

**Why 16kHz mono?** All speech recognition models (Whisper, AssemblyAI, pyannote) expect 16kHz mono audio. Converting at extraction time means we only do it once, and every downstream service gets the format it expects.

---

## 5. Transcription & Diarization Engine

### 5.1 API Route: `POST /transcribe/{meeting_id}`

**File:** `app/api/transcribe.py` (198 lines)

This is the **most complex endpoint** in the system. It orchestrates multiple services and triggers several background tasks.

#### Complete Orchestration Flow:

```
Step 1:   Verify audio file exists at data/audio/{meeting_id}.wav
Step 2:   Transcribe + diarize audio (stt_service)
Step 3:   Add meeting-number suffix to speaker labels (SPEAKER_00 → SPEAKER_00_m1)
Step 4:   Build speaker-wise grouping (speaker_service)
Step 5:   Save to storage/{meeting_id}/transcript.json (storage_service)
Step 6:   [Non-fatal] Extract speaker voice clips + auto-match against profiles
Step 7:   [Non-fatal] Create metadata.json with processing timestamps
Step 8:   [Non-fatal] Auto-index transcript into RAG (ChromaDB)
Step 9:   [Non-fatal] Auto-generate meeting title via LLM
```

**Why "non-fatal"?** Steps 6-9 are wrapped in `try/except` blocks so that a failure in any one (e.g., ChromaDB not available) doesn't prevent the core transcript from being saved. The transcript is the critical output.

#### Meeting Number Suffix:

```python
def _add_meeting_suffix_to_speakers(segments, meeting_number):
    suffix = f"_m{meeting_number}"
    for seg in segments:
        speaker = seg.get("speaker", "UNKNOWN")
        if speaker and speaker != "UNKNOWN" and not speaker.endswith(suffix):
            seg["speaker"] = f"{speaker}{suffix}"
    return segments
```

**Why?** Pyannote always labels speakers as `SPEAKER_00`, `SPEAKER_01`, etc. within each meeting. But across meetings, the same person might get different labels. Adding `_m1`, `_m2` suffixes prevents name collisions when comparing across meetings and makes the RAG chatbot's citations unambiguous.

#### Lazy Service Initialization:

```python
_stt_service = None  # Global singleton

def _get_services():
    global _stt_service, _speaker_builder, _storage_service
    if _stt_service is None:
        _stt_service = AudioTranscriptionService()  # Loads ML models
    ...
```

**Why lazy?** Loading WhisperX models and pyannote pipelines takes 5-15 seconds and uses significant GPU memory. By initializing lazily (on first request, not at server startup), we keep server boot time fast and only load models when actually needed.

### 5.2 Service: `AudioTranscriptionService`

**File:** `app/services/stt_service.py` (479 lines)

This is the core ML service. It supports **3 transcription engines** configurable via the `STT_MODE` environment variable:

| Mode | Transcription Engine | Diarization Engine | Speed | Quality |
|------|--------------------|--------------------|-------|---------|
| `assemblyai` | AssemblyAI Cloud API | AssemblyAI (built-in) | Medium | Highest |
| `groq` | Groq Whisper API | Local pyannote | Fastest | High |
| `local` | Local WhisperX (GPU) | WhisperX diarization | Slow | High |

#### Constructor — Device Detection:

```python
def __init__(self, device=None, compute_type=None):
    import torch
    if device is None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    if compute_type is None:
        self.compute_type = "float16" if self.device == "cuda" else "int8"
```

**What this does:** Automatically detects whether a GPU is available. Uses `float16` precision on GPU (faster, lower memory) and `int8` on CPU (enables quantized inference for slower but functional CPU-only mode).

#### Audio Preprocessing:

```python
def _preprocess_audio(self, audio_path):
    # Applies noise reduction using noisereduce library
    # Normalizes audio volume
    # Saves cleaned version as {id}_clean.wav
    # Returns path to cleaned audio
```

**Why preprocess?** Real meeting recordings often have background noise (AC, keyboard clicks, echo). Preprocessing improves transcription accuracy, especially for lower-quality microphones.

#### Groq Whisper Transcription (Primary Engine):

```python
def _transcribe_groq(self, audio_path):
    # Handles files > 25MB by chunking
    # Calls Groq's Whisper API for each chunk
    # Returns timestamped segments
    # Then runs LOCAL pyannote diarization to assign speakers
```

**Key detail:** Groq's Whisper API does transcription only — it doesn't identify speakers. So we pair it with local pyannote diarization. Groq gives us the text + timestamps, pyannote gives us who said what.

#### Speaker Assignment Algorithm:

```python
def _assign_speakers_from_diarization(self, segments, diarization):
    for seg in segments:
        seg_start, seg_end = seg["start"], seg["end"]
        best_speaker = "UNKNOWN"
        best_overlap = 0
        for turn in diarization.itertracks(yield_label=True):
            # Calculate temporal overlap between transcript segment
            # and diarization turn
            overlap = min(seg_end, turn_end) - max(seg_start, turn_start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn_label
        seg["speaker"] = best_speaker
```

**How it works:** For each transcribed segment, we check all diarization turns (time ranges labeled with speaker IDs). The speaker with the most temporal overlap with the segment gets assigned as the speaker. This "maximum overlap" strategy handles cases where a segment spans multiple speaker turns.

### 5.3 Service: `SpeakerTranscriptBuilder`

**File:** `app/services/speaker_service.py` (49 lines)

Converts the flat segments list into a speaker-grouped dictionary:

```python
# Input (flat chronological list):
segments = [
    {"speaker": "SPEAKER_00_m1", "start": 0.0, "end": 4.2, "text": "Hello everyone"},
    {"speaker": "SPEAKER_01_m1", "start": 4.5, "end": 8.1, "text": "Hi, let's begin"},
    {"speaker": "SPEAKER_00_m1", "start": 8.3, "end": 12.0, "text": "Sure, first item..."},
]

# Output (grouped by speaker):
speakers = {
    "SPEAKER_00_m1": [
        {"start": 0.0, "end": 4.2, "text": "Hello everyone"},
        {"start": 8.3, "end": 12.0, "text": "Sure, first item..."},
    ],
    "SPEAKER_01_m1": [
        {"start": 4.5, "end": 8.1, "text": "Hi, let's begin"},
    ],
}
```

### 5.4 Service: `MeetingStorageService`

**File:** `app/services/storage_service.py` (59 lines)

Persists transcript data to disk:

```python
def save(self, meeting_id, data):
    meeting_dir = self.base_dir / meeting_id
    meeting_dir.mkdir(parents=True, exist_ok=True)

    # Save transcript with UTC timestamp
    payload = {"created_at": datetime.now(timezone.utc).isoformat(), **data}
    with open(meeting_dir / "transcript.json", "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Also save metadata with human-readable date/time
    metadata = {
        "meeting_id": meeting_id,
        "processed_at": now.isoformat(),
        "processed_date": now.strftime("%B %d, %Y"),     # "February 28, 2026"
        "processed_day": now.strftime("%A"),               # "Friday"
        "processed_time": now.strftime("%I:%M %p"),        # "03:45 PM"
    }
```

**Why human-readable dates?** The frontend dashboard displays "February 28, 2026 (Friday)" — storing these formatted strings avoids client-side date formatting and ensures consistency.

---

## 6. Meeting Management (CRUD)

**File:** `app/api/diarization.py` (447 lines)

This file handles all meeting data operations: listing, retrieving, editing, metadata management, video streaming, and deletion.

### 6.1 List Meetings — `GET /meetings`

Returns all meetings for the dashboard, with metadata and status.

```python
@router.get("/meetings")
async def list_meetings():
    for d in STORAGE_DIR.iterdir():
        # Skip system directories
        SKIP_DIRS = {"chroma_db", "speaker_profiles", "models", "__pycache__"}
        if not d.is_dir() or d.name in SKIP_DIRS or d.name.startswith("_"):
            continue

        # Determine status by checking which files exist
        if (d / "Meeting_Summary.pdf").exists():
            status = "published"
        elif (d / "summary.json").exists():
            status = "summarized"
        elif (d / "transcript.json").exists():
            status = "transcribed"
        else:
            status = "uploaded"

        # Calculate duration from last segment end time
        if segs:
            duration = max(s.get("end", 0) for s in segs)
```

**How status is determined:** The system checks for the existence of specific files in reverse order of the pipeline. If a PDF exists, the meeting is "published". This is a simple, filesystem-based state machine.

#### Display IDs (`m1`, `m2`, `m3`...):

```python
def _get_display_id(meeting_id, counter):
    if meeting_id not in counter:
        existing_numbers = list(counter.values())
        next_number = max(existing_numbers) + 1 if existing_numbers else 1
        counter[meeting_id] = next_number
        _save_meeting_counter(counter)
    return f"m{counter[meeting_id]}"
```

**Why?** UUIDs like `550e8400-e29b-41d4-a716-446655440000` are not user-friendly. Display IDs like `m1`, `m2` give meetings short, memorable names. The mapping is persisted in `storage/_meeting_counter.json` and never reuses numbers even after deletion.

### 6.2 Get Meeting — `GET /meeting/{meeting_id}`

Reads `storage/{meeting_id}/transcript.json` and returns it as a `MeetingResponse` object.

### 6.3 Edit Segment — `PUT /meeting/{meeting_id}/segments/{index}`

Allows editing a specific transcript segment's text or speaker label:

```python
@router.put("/meeting/{meeting_id}/segments/{index}")
async def edit_segment(meeting_id, index, body: SegmentEditRequest):
    # Apply edits to the specific segment
    if body.text is not None:
        segments[index]["text"] = body.text
    if body.speaker is not None:
        segments[index]["speaker"] = body.speaker

    # IMPORTANT: Rebuild the entire speakers dict from segments
    speakers = {}
    for seg in segments:
        spk = seg.get("speaker", "UNKNOWN")
        if spk not in speakers:
            speakers[spk] = []
        speakers[spk].append({...})

    # Save back to disk
    data["segments"] = segments
    data["speakers"] = speakers
```

**Why rebuild speakers dict?** When a segment's speaker is changed (e.g., `SPEAKER_00` → `SPEAKER_01`), the speaker grouping becomes stale. Rebuilding from scratch ensures consistency between the flat `segments` list and the grouped `speakers` dict.

### 6.4 Metadata — `GET/PATCH /meeting/{meeting_id}/metadata`

- **GET:** Returns current metadata from `metadata.json`
- **PATCH:** Merge-style update — only provided fields are changed, existing fields are preserved

```python
# PATCH uses Pydantic's exclude_none to only update provided fields
update_data = body.model_dump(exclude_none=True)
meta.update(update_data)  # Merge into existing metadata
```

### 6.5 Video Streaming — `GET /meeting/{meeting_id}/video`

Supports **HTTP Range requests** for in-browser video seeking:

```python
range_header = request.headers.get("range")
if range_header:
    # Parse "bytes=0-1024"
    start = int(parts[0])
    end = int(parts[1]) if parts[1] else file_size - 1

    def iter_file():
        with open(video_path, "rb") as f:
            f.seek(start)  # Jump to requested position
            remaining = content_length
            while remaining > 0:
                chunk = f.read(min(8192, remaining))
                yield chunk

    return StreamingResponse(iter_file(), status_code=206,
        headers={"Content-Range": f"bytes {start}-{end}/{file_size}"})
```

**Why Range requests?** Without Range support, the browser would have to download the entire video before playback starts, and seeking would be impossible. With Range support (HTTP 206 Partial Content), the browser can request specific byte ranges, enabling instant seeking to any position.

### 6.6 Delete Meeting — `DELETE /meeting/{meeting_id}`

Cleans up **4 separate locations**:

1. **ChromaDB** — Removes RAG vectors for this meeting
2. **Storage directory** — Deletes `storage/{meeting_id}/` and all files inside
3. **Audio file** — Removes `data/audio/{meeting_id}.wav`
4. **Hash registry** — Removes the SHA-256 → meeting_id entry so re-uploading the same video gets a new meeting ID

---

## 7. AI-Powered Summaries

### 7.1 API Route: `POST /summarize/{meeting_id}`

**File:** `app/api/summarize.py` (57 lines)

Accepts two optional query parameters:
- `force=true` — Regenerate even if a cached summary exists
- `extra_prompt="..."` — Custom instructions for summary style

### 7.2 Service: `MeetingSummaryService`

**File:** `app/services/summary_service.py` (236 lines)

Uses **Groq API with Llama 3.3 70B** for all summary generation.

#### Three-Part Summary Generation:

```python
def summarize(self, meeting_id, force=False, extra_prompt=""):
    # 1. Check cache
    cache_path = STORAGE_DIR / meeting_id / "summary.json"
    if cache_path.exists() and not force:
        return json.load(open(cache_path))  # Return cached

    # 2. Load transcript + speaker map
    transcript = json.load(open(STORAGE_DIR / meeting_id / "transcript.json"))
    speaker_map = self._load_speaker_map(meeting_id)

    # 3. Build conversation text with real names
    full_text = self._build_conversation_text(segments, speaker_map)

    # 4. Generate three outputs:
    speaker_summaries = self._generate_speaker_summaries(speakers, speaker_map)
    overall_en = self._generate_overall_summary_en(full_text, extra_prompt)
    overall_hi = self._generate_overall_summary_hi(full_text, extra_prompt)

    # 5. Cache result
    result = {
        "meeting_id": meeting_id,
        "speaker_summaries_en": speaker_summaries,
        "overall_summary_en": overall_en,
        "overall_summary_hi": overall_hi,
    }
    json.dump(result, open(cache_path, "w"))
```

#### Speaker Map Integration:

```python
def _apply_speaker_map(self, text, speaker_map):
    """Replace SPEAKER_00_m1 with real names in the text."""
    for speaker_id, real_name in speaker_map.items():
        text = text.replace(speaker_id, real_name)
    return text
```

**Why?** When speaker names are mapped (e.g., `SPEAKER_00_m1 → Pawan`), the LLM prompt includes real names, so the generated summary says "Pawan discussed..." instead of "SPEAKER_00_m1 discussed...".

#### LLM Call with Retry Logic:

```python
def _call_llm(self, system_prompt, user_prompt):
    for attempt in range(MAX_RETRIES):
        try:
            response = self.client.chat.completions.create(
                model=MODEL,  # "llama-3.3-70b-versatile"
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception:
            time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
```

**Retry strategy:** Groq's API can occasionally rate-limit or timeout. The exponential backoff (1s → 2s → 4s) handles transient failures gracefully.

---

## 8. AI Insights & Analytics

### 8.1 API Route: Multiple Endpoints

**File:** `app/api/insights.py` (632 lines)

This file contains **12 endpoints** — 9 using LLM calls and 3 using pure computation.

#### LLM-Powered Endpoints:

| Endpoint | Cache File | What It Extracts |
|----------|-----------|-----------------|
| `POST /meeting/{id}/action-items` | `action_items.json` | Tasks, decisions, key takeaways, follow-ups |
| `PUT /meeting/{id}/action-items` | `action_items.json` | Save human-edited items (HITL) |
| `POST /meeting/{id}/auto-title` | `metadata.json` | 5-8 word descriptive meeting title |
| `POST /meeting/{id}/followup-email` | `followup_email.json` | Professional email draft |
| `POST /meeting/{id}/followup-email/send` | — | Send email via SMTP |
| `POST /meeting/{id}/requirements` | `requirements.json` | User stories, MoSCoW priorities |
| `POST /meeting/{id}/documentation` | `documentation.json` | Minutes of Meeting (MoM) |
| `POST /meeting/{id}/sentiment` | `sentiment.json` | Positive/negative/neutral per segment |
| `POST /meeting/{id}/topics` | `topics.json` | Topic segments with time ranges |

#### Pure Computation Endpoints (No LLM):

| Endpoint | What It Computes |
|----------|-----------------|
| `GET /meeting/{id}/speaker-analytics` | Talk-time, word count, WPM, interruptions |
| `GET /meeting/{id}/speaker-report` | Full speaker scorecards with role classification |
| `GET /meeting/{id}/keywords` | Top 30 keywords by frequency |

### 8.2 Service: `MeetingInsightsService`

**File:** `app/services/insights_service.py` (870 lines)

All LLM methods follow the **same caching pattern**:

```
1. Check for cached JSON → return if exists (unless force=True)
2. Load transcript text with speaker names
3. Send structured prompt to Groq LLM
4. Parse JSON from LLM response
5. Save to storage/{meeting_id}/{feature}.json
6. Return parsed result
```

#### Interruption Detection Algorithm:

```python
# A speaker change with < 0.5 seconds gap = interruption
for i in range(1, len(segments)):
    prev = segments[i - 1]
    curr = segments[i]
    if prev.get("speaker") != curr.get("speaker"):
        gap = curr.get("start", 0) - prev.get("end", 0)
        if gap < 0.5:  # Less than half a second
            stats[curr.get("speaker")]["interruptions"] += 1
```

#### Speaker Role Classification (Heuristic):

```python
# Roles are assigned based on quantitative metrics:
if max_decisions > 0 and c["decisions_attributed"] == max_decisions:
    role = "Decision Maker"     # Most decisions
elif talk_percent == max_talk and talk_percent > 40:
    role = "Presenter"          # Dominated the conversation
elif max_questions > 0 and c["questions_asked"] == max_questions >= 2:
    role = "Challenger"         # Asked the most questions
elif max_actions > 0 and c["action_items_assigned"] == max_actions:
    role = "Doer"               # Most action items assigned
elif talk_percent < 15:
    role = "Observer"           # Barely spoke
else:
    role = "Contributor"        # Everyone else
```

---

## 9. RAG Chatbot

### 9.1 API Route: Chat Endpoints

**File:** `app/api/chat.py` (175 lines)

| Endpoint | Description |
|----------|-------------|
| `POST /chat/ask` | Synchronous Q&A — full answer + citations |
| `POST /chat/ask/stream` | SSE streaming — token-by-token answer |
| `POST /chat/index/{id}` | Index a meeting into ChromaDB |
| `GET /chat/meetings` | List all indexed meetings |
| `POST /chat/clear/{session_id}` | Clear conversation memory |

#### SSE Streaming:

```python
@router.post("/chat/ask/stream")
async def chat_ask_stream(body: ChatRequest):
    def event_generator():
        for event_type, data in service.query_stream(...):
            payload = json.dumps({"type": event_type, "content": data})
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**How SSE works:** The server sends events line by line as the LLM generates tokens. The frontend receives them in real-time, showing the answer being "typed out" character by character. Event types:
- `{"type": "token", "content": "The"}` — Individual word
- `{"type": "citations", "content": [...]}` — Source references
- `{"type": "done", "content": ""}` — Stream complete

### 9.2 Service: `MeetingRAGService`

**File:** `app/services/rag_service.py` (557 lines)

**Architecture:** LangChain + ChromaDB + Groq (Llama 3.3 70B)

#### Initialization:

```python
def __init__(self):
    # Embedding model: converts text → 384-dim vectors
    self._embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    # Vector store: persisted on disk at storage/chroma_db/
    self._vectorstore = Chroma(
        collection_name="meeting_transcripts",
        embedding_function=self._embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    # LLM: Groq's Llama 3.3 70B for answer generation
    self._llm = ChatOpenAI(
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )
```

#### Meeting Ingestion:

```python
def ingest_meeting(self, meeting_id):
    # 1. Load transcript.json
    # 2. Load speaker_map.json (for real names)
    # 3. Chunk by speaker segment:
    #    "Pawan [0:30-1:15]: We should use React for the frontend"
    # 4. Attach metadata: {meeting_id, speaker, start, end}
    # 5. Delete any existing chunks for this meeting
    # 6. Upsert new chunks into ChromaDB
    # Returns: number of chunks indexed
```

#### Diverse Retrieval Algorithm (Key Innovation):

```python
def _diverse_retrieve(self, question, meeting_ids=None, target_k=18, fetch_k=40):
    # 1. Fetch top 40 candidates from ChromaDB
    candidates = self._vectorstore.similarity_search(question, k=fetch_k)

    # 2. Group candidates by meeting_id
    by_meeting = defaultdict(list)
    for doc in candidates:
        mid = doc.metadata["meeting_id"]
        by_meeting[mid].append(doc)

    # 3. Round-robin selection: take 1 from each meeting in turn
    result = []
    while len(result) < target_k:
        for mid in meeting_ids_in_order:
            if by_meeting[mid]:
                result.append(by_meeting[mid].pop(0))
```

**Why diverse retrieval?** Standard similarity search might return all 18 results from a single meeting that closely matches the question. But the user might want cross-meeting comparisons like "What did we decide about React across all meetings?" The round-robin approach ensures every indexed meeting gets represented in the context.

#### Auto-Recovery:

If ChromaDB becomes corrupted (missing embeddings, dimension mismatch), the service automatically detects the error and rebuilds the entire index:

```python
except Exception as e:
    if "dimensionality" in str(e) or "NotFound" in str(e):
        self._rebuild_index()  # Nukes and re-indexes everything
        return self._diverse_retrieve(question, ...)  # Retry
```

---

## 10. Publishing & Delivery

### 10.1 API Route: Publish Endpoints

**File:** `app/api/publish.py` (237 lines)

| Endpoint | Description |
|----------|-------------|
| `POST /publish/{id}` | One-click: generate PDF + optional email + Teams |
| `GET /publish/{id}/pdf` | Download generated PDF |
| `POST /publish/{id}/full-report` | Auto-generate missing sections + build comprehensive report |
| `GET /publish/{id}/full-report` | Download comprehensive report PDF |
| `POST /publish/{id}/full-report/email` | Email the full report to recipients |

#### Auto-Generation for Full Report:

```python
@router.post("/publish/{meeting_id}/full-report")
async def generate_full_report_auto(meeting_id):
    # Auto-generates any MISSING sections before building the PDF:
    if not (meeting_dir / "summary.json").exists():
        MeetingSummaryService().summarize(meeting_id)

    if not (meeting_dir / "action_items.json").exists():
        MeetingInsightsService().extract_action_items(meeting_id)

    if not (meeting_dir / "requirements.json").exists():
        MeetingInsightsService().extract_requirements(meeting_id)

    if not (meeting_dir / "documentation.json").exists():
        MeetingInsightsService().generate_documentation(meeting_id)

    # Then build the comprehensive PDF
    pdf_path = service.generate_full_report(meeting_id)
```

**Why auto-generate?** Users can click "Full Report" at any time — even before running individual analyses. The system checks which sections are missing and generates them on-demand before building the PDF.

### 10.2 Service: `MeetingPublishService`

**File:** `app/services/publish_service.py` (639 lines)

**Zero AI cost** — all publishing uses pre-computed cached JSON files. No LLM calls during publishing.

#### PDF Generation (SummaryPDF class):

```python
class SummaryPDF(FPDF):
    def __init__(self):
        super().__init__()
        # Register Unicode fonts for Hindi support
        self.add_font("NotoSans", "", str(FONT_DIR / "NotoSans-Regular.ttf"), uni=True)
        self.add_font("NotoSansDevanagari", "", str(FONT_DIR / "NotoSansDevanagari-Regular.ttf"), uni=True)
```

**Why custom fonts?** The system generates bilingual summaries (English + Hindi). Standard PDF fonts don't support Devanagari script. By bundling NotoSans fonts, the PDF renders both languages correctly.

#### Email Delivery:

```python
def send_email(self, pdf_path, meeting_title, recipients):
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"Meeting Summary: {meeting_title}"

    # Attach PDF
    with open(pdf_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
        attachment.add_header("Content-Disposition", "attachment", filename="Meeting_Summary.pdf")
        msg.attach(attachment)

    # Send via TLS
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
```

#### Microsoft Teams Adaptive Card:

The service sends a rich card to Teams channels via webhook, including:
- Meeting title and date
- Full summary text
- Action items list
- Decisions list
- Speaker names
All formatted as an Adaptive Card v1.4 JSON payload.

---

## 11. Speaker Map & Voice Identification

### 11.1 Speaker Map — HITL Naming

**File:** `app/api/speaker_map.py` (236 lines)

When users save speaker names (e.g., `SPEAKER_00_m1 → "Pawan"`), the system:

1. **Saves the mapping** to `storage/{meeting_id}/speaker_map.json`
2. **Saves voice profiles** — generates ECAPA-TDNN embeddings from speaker clips and stores them for future auto-matching
3. **Triggers background regeneration** of ALL AI insights with real names:

```python
background_tasks.add_task(_regenerate_all_insights, meeting_id)
```

#### Background Regeneration Task:

```python
def _regenerate_all_insights(meeting_id):
    # 1. Re-index RAG with real names
    # 2. Regenerate Summary (force=True)
    # 3. Re-extract Action Items (preserves Jira links!)
    # 4. Re-extract Requirements
    # 5. Regenerate Documentation
    # 6. Regenerate Follow-up Email
    # 7. Re-run Sentiment Analysis
    # 8. Re-extract Topics
```

**Jira Link Preservation:** When regenerating action items, the system:
1. Saves existing `jira_id` values from the old action items
2. Regenerates with real speaker names
3. Fuzzy-matches old items to new items (word overlap ≥ 40%)
4. Restores Jira links to the matching new items

```python
# Fuzzy matching: compare word overlap between old and new tasks
old_words = set(old["task"].lower().split())
new_words = set(new_item["task"].lower().split())
overlap = len(old_words & new_words) / max(len(old_words), len(new_words))
if overlap >= 0.4:  # 40% word overlap
    new_item["jira_id"] = old["jira_id"]
```

### 11.2 Voice Identification

**File:** `app/api/voice_profiles.py` (229 lines)
**File:** `app/services/voice_embedding_service.py` (477 lines)

Uses **SpeechBrain ECAPA-TDNN** for speaker verification.

#### Pipeline:

```
1. Extract ~10s audio clip per speaker (best SNR segments)
2. Preprocess: Resample 16kHz → Normalize → Bandpass 80-7600Hz → Remove silence
3. Generate 192-dim embedding via ECAPA-TDNN
4. Compare against stored profiles using cosine similarity
5. Threshold: 0.55 → auto-match speaker to known name
```

#### Speaker Clip Extraction:

```python
def extract_speaker_clips(self, meeting_id):
    # For each speaker:
    # 1. Collect all their segments from the transcript
    # 2. Score segments by SNR (signal-to-noise ratio)
    # 3. Pick highest-quality segments totaling ~10 seconds
    # 4. Concatenate into a single clip
    # 5. Apply preprocessing pipeline
    # 6. Save as storage/{meeting_id}/speaker_clips/{SPEAKER_ID}.wav
```

#### Profile Enrollment (Cross-Meeting Learning):

```python
def save_speaker_profile(self, name, embedding):
    profiles = self.load_profiles()
    if name in profiles:
        # Average with existing embedding for better accuracy
        old = profiles[name]["embedding"]
        new_avg = [(a + b) / 2 for a, b in zip(old, embedding)]
        profiles[name]["embedding"] = new_avg
        profiles[name]["enrollment_count"] += 1
    else:
        profiles[name] = {"embedding": embedding, "enrollment_count": 1}
```

**Why averaging?** A speaker's voice varies across recordings (different microphones, background noise, speaking style). By averaging embeddings from multiple meetings, the profile becomes more robust and accurate over time.

---

## 12. Third-Party Integrations

### 12.1 Jira Integration

**Files:** `app/api/jira.py` (189 lines), `app/services/jira_service.py` (400+ lines)

Provides **bidirectional sync** between ContextIQ action items and Jira tickets:

| Direction | Endpoint | Description |
|-----------|----------|-------------|
| Status Check | `GET /jira/status` | Check if Jira credentials are configured |
| Push → Jira | `POST /meeting/{id}/jira/push` | Create Jira tickets from action items |
| Sync ← Jira | `POST /meeting/{id}/jira/sync` | Fetch latest status from Jira |
| Update → Jira | `PUT /meeting/{id}/jira/update` | Push local edits (status, priority) to Jira |

**Push flow:** Maps ContextIQ fields → Jira fields:
- `task` → Jira `summary`
- `priority` → Jira `priority` (High/Medium/Low → Jira priority IDs)
- `category` → Jira `issuetype` (Task/Bug/Story)
- `context` → Jira `description` (formatted as ADF — Atlassian Document Format)

### 12.2 Notion & Confluence

**Files:** `app/api/notion.py`, `app/api/confluence.py` (32 lines each)
**Services:** `app/services/notion_service.py`, `app/services/confluence_service.py`

Both follow the same pattern:
- **Status endpoint** — Check API connectivity
- **Push endpoint** — Convert meeting data to platform-specific format and create a page

---

## 13. Dashboard & Search

### 13.1 Dashboard Statistics

**File:** `app/api/stats.py` (349 lines)

#### `GET /stats`
Scans all meeting directories and aggregates:
- Total meetings (only those with transcripts)
- Unique speakers (resolved through speaker maps across ALL meetings)
- Total duration (sum of all meeting lengths)
- Meetings per day

#### `GET /stats/culture-score` — Meeting Health Metric

A **composite score (0-100)** measuring team meeting quality:

| Signal | Weight | How It's Calculated |
|--------|--------|-------------------|
| Speaker Balance | 30% | `(1 - max_speaker_share) / (1 - ideal_share) × 100` — Penalizes meetings dominated by one person |
| Sentiment | 25% | `% of positive + neutral segments` — Penalizes meetings with negative sentiment |
| Action Completion | 30% | `% of action items marked Done` — Rewards follow-through |
| Meeting Efficiency | 15% | `(decisions ÷ (duration_min / 10)) × 100` — Rewards productive meetings |

**Grading:** Excellent (≥80), Good (≥60), Needs Work (≥40), Poor (<40)

### 13.2 Full-Text Search

**File:** `app/api/search.py` (117 lines)

#### `GET /search?q=keyword&limit=10`

Weighted keyword search across all meetings:

```python
# Scoring weights:
# Title match:      +10 points (highest — title is most descriptive)
# Speaker name:      +5 points (searching for a person)
# Transcript text:   +1 point per matching segment

# Results include highlighted snippets with ±30 chars context:
# "...and we decided to use **React** for the frontend because..."
```

---

## 14. Storage Layout

### Per-Meeting Files (`storage/{meeting_id}/`)

| File | Created By | Stage | Description |
|------|-----------|-------|-------------|
| `video.mp4` | Upload | 1 | Original video for playback |
| `transcript.json` | Transcription | 2 | Segments + speakers + timestamps |
| `metadata.json` | Transcription | 2 | Title, status, dates, counts |
| `speaker_clips/*.wav` | Voice ID | 2 | ~10s audio clip per speaker |
| `speaker_map.json` | Speaker Map | 3 | `{SPEAKER_ID: "Real Name"}` |
| `summary.json` | Summary | 4 | EN + HI summaries |
| `action_items.json` | Insights | 4 | Tasks, decisions, takeaways |
| `requirements.json` | Insights | 4 | User stories, MoSCoW priorities |
| `documentation.json` | Insights | 4 | Minutes of Meeting |
| `sentiment.json` | Insights | 4 | Per-segment sentiment labels |
| `topics.json` | Insights | 4 | Topic segments with time ranges |
| `followup_email.json` | Insights | 4 | Draft email subject + body |
| `Meeting_Summary.pdf` | Publish | 5 | Summary PDF report |
| `Full_Report.pdf` | Publish | 5 | Comprehensive report PDF |

### Global Files

| Path | Description |
|------|-------------|
| `storage/_file_hashes.json` | SHA-256 → meeting_id dedup registry |
| `storage/_meeting_counter.json` | meeting_id → sequential number (m1, m2...) |
| `storage/chroma_db/` | ChromaDB persistent vector store (RAG) |
| `storage/speaker_profiles/profiles.json` | Global voice embeddings `{name: [192 floats]}` |
| `data/audio/{meeting_id}.wav` | Extracted 16kHz mono WAV audio |

---

## Appendix: Key Design Patterns

### 1. Lazy Initialization
All heavy services (ML models, API clients) are initialized on first use with a global singleton pattern:
```python
_service = None
def _get_service():
    global _service
    if _service is None:
        _service = HeavyService()  # Loads models
    return _service
```

### 2. Cache-on-Disk
Every AI-generated result is cached as a JSON file. Subsequent requests return the cache instantly. Pass `force=True` to regenerate.

### 3. Non-Fatal Background Tasks
Secondary operations (voice matching, RAG indexing, title generation) run in `try/except` blocks so failures don't break the primary pipeline.

### 4. Background Regeneration
When speaker names change, ALL insights are regenerated in a FastAPI `BackgroundTask` so the API responds immediately while the work happens asynchronously.

### 5. File-System as Database
No SQL database is used. All state is stored as JSON files on disk, organized by meeting_id directories. This simplifies deployment and makes the system inspectable (you can read any meeting's data by opening its JSON files).

---

*Last updated: March 2, 2026*
