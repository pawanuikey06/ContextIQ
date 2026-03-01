# AI RAG Chatbot with Video Navigation

## Overview

The AI RAG (Retrieval-Augmented Generation) Chatbot is ContextIQ's conversational intelligence layer. It enables users to ask natural-language questions across **all** indexed meeting transcripts and receive accurate, contextual answers — backed by source citations that link directly to the exact video timestamp where the information was discussed.

**Core Idea**: Instead of re-watching hours of meeting recordings to find a specific decision, action item, or discussion point, users simply ask: *"What did Varun say about the laptop delivery delay?"* — and the system retrieves the relevant transcript chunks, generates a grounded answer, and provides clickable citations that open a video side panel seeked to that exact moment.

---

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Chat.svelte │────▶│  chat.py     │────▶│  rag_service.py  │
│  (Frontend)  │ SSE │  (FastAPI)   │     │  (RAG Engine)    │
└──────┬───────┘     └──────────────┘     └───────┬──────────┘
       │                                          │
       │  Video Navigation                        │
       ▼                                          ▼
┌──────────────────┐              ┌───────────────────────────┐
│ VideoSidePanel   │              │  LangChain + ChromaDB +   │
│ (Video Player)   │              │  Groq (Llama 3.3 70B)     │
└──────────────────┘              │  + HuggingFace Embeddings │
                                  └───────────────────────────┘
```

### Component Breakdown

| Component | File | Role |
|-----------|------|------|
| RAG Service | `app/services/rag_service.py` | Core engine — ingestion, retrieval, LLM query, streaming |
| Chat API | `app/api/chat.py` | FastAPI endpoints for ask, stream, index, clear |
| Chat UI | `frontend/src/pages/Chat.svelte` | Conversational interface with sidebar + streaming |
| Video Panel | `frontend/src/components/VideoSidePanel.svelte` | Side panel for video playback at citation timestamps |
| API Config | `frontend/src/lib/api.js` | Endpoint definitions |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Embedding Model | `all-MiniLM-L6-v2` (HuggingFace) | 384-dim sentence embeddings, runs on CPU |
| Vector Store | ChromaDB (persistent) | Stores and retrieves meeting transcript chunks |
| LLM | Groq `llama-3.3-70b-versatile` | Generates answers from retrieved context |
| Framework | LangChain | Orchestrates retrieval + LLM chain |
| API | FastAPI + SSE | Streaming responses via Server-Sent Events |
| Frontend | Svelte | Chat UI with real-time token streaming |

---

## Data Flow

### 1. Ingestion Pipeline

When a meeting is indexed into the knowledge base:

```
Audio File → Transcription → Transcript JSON
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  Segment Chunking      │
                        │  (1 doc per segment)   │
                        │  + Meeting Summary doc │
                        └───────────┬───────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  ChromaDB (Chroma)     │
                        │  collection: "meetings"│
                        │  persist: storage/     │
                        │          chroma_db/    │
                        └───────────────────────┘
```

**Each segment becomes a LangChain `Document` with:**

```python
page_content = "[2026-02-28, Friday] Varun Kumar: We need to check the delivery status"
metadata = {
    "meeting_id": "5c276f9d-...",
    "meeting_title": "Laptop Delivery Delay Resolution Meeting",
    "speaker": "Varun Kumar",      # Resolved via speaker_map.json
    "speaker_id": "SPEAKER_02",     # Raw diarization label
    "start": 45.2,                  # Timestamp in seconds
    "end": 52.8,
    "chunk_index": 12,
    "meeting_date": "2026-02-28",
    "meeting_day": "Friday",
}
```

**Additionally, a Meeting Summary chunk is injected** to enable cross-meeting queries:

```
MEETING SUMMARY — Laptop Delivery Delay Resolution Meeting
Date: 2026-02-28, Friday
Duration: 5.7 minutes
Total segments: 20
Number of speakers: 3
Speakers in this meeting: Babuji Abraham, Poornima Kumaran, Varun Kumar
IMPORTANT: ONLY the speakers listed above participated in this meeting.
```

This ensures queries like *"Who spoke in both meetings?"* are answered accurately.

### 2. Retrieval — Diverse Round-Robin Strategy

The system uses a **diverse retrieval** algorithm to ensure answers consider context from ALL indexed meetings, not just the most similar one:

1. **Fetch** top-40 candidates via cosine similarity from ChromaDB.
2. **Group** candidates by `meeting_id`.
3. **Round-robin** across meetings, picking one chunk per meeting per round.
4. **Stop** when 18 chunks are selected (guaranteeing coverage of every meeting).

```python
# Pseudo-code of round-robin selection
diverse = []
while len(diverse) < 18:
    for each meeting in meetings:
        if meeting has chunks left:
            diverse.append(meeting.pop_best())
```

**Auto-recovery**: If ChromaDB becomes corrupted (e.g., dimension mismatch after a model change), the system automatically **nukes and rebuilds** the entire index from stored transcripts.

### 3. Query Processing

```
User Question
      │
      ▼
┌─────────────────────────────────┐
│  1. Diverse Retrieval (18 docs) │
│  2. Build Meeting Calendar      │
│  3. Load Chat History (last 10) │
│  4. Construct System Prompt     │
│  5. Call Groq LLM               │
│  6. Extract Citations           │
│  7. Update Memory               │
└─────────────────────────────────┘
      │
      ▼
  Answer + Citations[]
```

**System Prompt Highlights:**
- Answers ONLY from provided context (no hallucination)
- Maintains speaker accuracy — checks MEETING SUMMARY chunks before confirming speaker presence
- Supports date-based queries by injecting an indexed meetings calendar
- Clean answers without inline citations (UI handles source display separately)

### 4. Streaming (SSE)

The chatbot uses **Server-Sent Events** for real-time token streaming:

```
Client ──POST /chat/ask/stream──▶ Server
         ◀── data: {"type":"token","content":"The"}
         ◀── data: {"type":"token","content":" meeting"}
         ◀── data: {"type":"token","content":" discussed"}
         ...
         ◀── data: {"type":"citations","content":[...]}
         ◀── data: {"type":"done","content":""}
```

---

## Video Navigation

The standout feature is **citation-to-video linking**. Every answer comes with source citations that include:

- `meeting_id` — which meeting
- `speaker` — who said it
- `start` / `end` — exact timestamp in the video
- `excerpt` — transcript excerpt

### How It Works

1. **Citation UI**: Each citation shows a ▶ Play button with the formatted timestamp (e.g., `2:15`).
2. **On Click**: `openVideo(meeting_id, start)` is called.
3. **VideoSidePanel** opens as a 400px right-side panel:
   - Loads the meeting video from `GET /meeting/{id}/video`
   - Auto-seeks to the exact `startTime` via `video.currentTime = startTime`
   - Supports **smooth navigation** between citations (if panel is already open, it uses `seekTo()` instead of remounting)
4. The user can watch the exact 10-15 second clip where the cited information was spoken.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/ask` | Ask a question (non-streaming) → `{ answer, citations[] }` |
| `POST` | `/chat/ask/stream` | Ask a question (SSE streaming) → token-by-token + citations |
| `POST` | `/chat/index/{meeting_id}` | Index/re-index a meeting into ChromaDB |
| `GET`  | `/chat/meetings` | List all indexed meetings |
| `POST` | `/chat/clear/{session_id}` | Clear conversation history for a session |

### Request Schema

```json
{
  "question": "What were the key decisions?",
  "session_id": "unique-session-uuid",
  "meeting_ids": ["5c276f9d-..."]  // Optional: scope to specific meetings
}
```

### Response Schema (non-streaming)

```json
{
  "answer": "The key decisions were...",
  "citations": [
    {
      "meeting_id": "5c276f9d-...",
      "speaker": "Varun Kumar",
      "start": 45.2,
      "end": 52.8,
      "excerpt": "[2026-02-28, Friday] Varun Kumar: We decided to..."
    }
  ]
}
```

---

## Frontend Features

### Chat Interface (`Chat.svelte`)

- **Sidebar** — Lists all indexed meetings as checkboxes; users can filter which meetings to query.
- **Index All** — One-click button to index all un-indexed meetings into the knowledge base.
- **Quick Prompts** — Pre-built starter questions: "Summarize all my meetings", "What action items were discussed?", "What did each speaker talk about?", "What were the key decisions made?"
- **Streaming Display** — Answers appear token-by-token in real-time.
- **Citations** — Expandable "Sources (N)" section with play buttons for each citation.
- **New Chat** — Clears conversation memory for fresh context.
- **Session Management** — Each chat session gets a unique `session_id` (UUID) to maintain conversation context.

### Video Side Panel (`VideoSidePanel.svelte`)

- Opens as a 400px right-side panel alongside the chat.
- Plays the meeting video served from `GET /meeting/{id}/video`.
- Auto-seeks to the citation timestamp on open.
- Supports cross-meeting navigation — clicking citations from different meetings seamlessly switches video source.
- Shows `"Seeked to X:XX"` indicator.

---

## Conversation Memory

The chatbot maintains **session-based conversation memory**:

- Stores last 10 messages (5 Q&A exchanges) per session.
- Injects history into the LLM prompt as context for follow-up questions.
- Memory is in-process (resets on server restart).
- Can be manually cleared via `POST /chat/clear/{session_id}`.

---

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Embedding model | `all-MiniLM-L6-v2` | `rag_service.py` |
| LLM model | `llama-3.3-70b-versatile` | `rag_service.py` |
| LLM temperature | `0.1` | `rag_service.py` |
| Retrieval target_k | `18` chunks | `_diverse_retrieve()` |
| Retrieval fetch_k | `40` candidates | `_diverse_retrieve()` |
| Chat history limit | `10` messages | `query()` |
| ChromaDB persist path | `storage/chroma_db/` | `rag_service.py` |
| GROQ_API_KEY | Required in `.env` | Environment |

---

## Storage Structure

```
storage/
├── chroma_db/                  # ChromaDB persistent vector store
│   └── meetings/               # Collection with all meeting chunks
├── {meeting_id}/
│   ├── transcript.json         # Source transcript (segments[])
│   ├── speaker_map.json        # SPEAKER_00 → "Real Name"
│   └── metadata.json           # Title, date, processing info
```
