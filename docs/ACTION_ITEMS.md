# Action Items & Decisions Extraction

## Overview

The Action Items feature uses AI to automatically extract **action items, decisions, key takeaways, follow-ups, and risks** from meeting transcripts. It supports a **Human-in-the-Loop (HITL)** workflow where AI generates the initial extraction and users can edit, add, or remove items before finalizing.

**Core Idea**: Turn unstructured meeting conversations into a structured, trackable project backlog — automatically.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Action Items Pipeline                      │
│                                                             │
│  transcript.json                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐     ┌──────────────────────────┐  │
│  │  Format transcript  │────▶│  Groq LLM (Llama 3.3)    │  │
│  │  Speaker: text      │     │  "Senior PM" persona      │  │
│  └─────────────────────┘     └──────────┬───────────────┘  │
│                                         │                   │
│                              ┌──────────▼──────────┐       │
│                              │  Structured JSON     │       │
│                              │  action_items[]      │       │
│                              │  decisions[]         │       │
│                              │  key_takeaways[]     │       │
│                              │  follow_ups[]        │       │
│                              │  risks_identified[]  │       │
│                              └──────────┬──────────┘       │
│                                         │                   │
│                              ┌──────────▼──────────┐       │
│                              │  Cache + HITL Edit   │       │
│                              │  (PUT endpoint)      │       │
│                              └─────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Role |
|-----------|------|------|
| Insights Service | `app/services/insights_service.py` | `extract_action_items()` — LLM extraction logic |
| Insights API | `app/api/insights.py` | POST/PUT endpoints for extraction + HITL editing |
| Action Items UI | `frontend/src/pages/ActionItems.svelte` | Full-page UI with filtering, editing, email |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | Groq `llama-3.3-70b-versatile` | Extraction with "Senior PM" persona |
| Cache | JSON file | `storage/{id}/action_items.json` |
| Email | SMTP (Gmail) | Follow-up email sending |
| Frontend | Svelte | Interactive action items dashboard |

---

## Extraction Schema

The LLM is prompted to return a comprehensive structured JSON with five sections:

### 1. Action Items

```json
{
  "task": "Detailed description (2+ sentences) — what, why, context",
  "assigned_to": "Person name or 'Unassigned'",
  "deadline": "Mentioned deadline or 'Not specified'",
  "priority": "high | medium | low",
  "category": "development | design | research | communication | testing | documentation | infrastructure | other",
  "context": "Why this task was discussed, what problem it solves",
  "success_criteria": "How to know this task is complete",
  "dependencies": ["Other tasks this depends on"],
  "mentioned_by": "Who raised or proposed this task"
}
```

### 2. Decisions

```json
{
  "decision": "What was decided — detailed and specific",
  "made_by": "Who made or proposed it",
  "context": "Why this decision was needed",
  "impact": "Expected consequence",
  "alternatives_considered": "Other options discussed"
}
```

### 3. Key Takeaways

```json
{
  "takeaway": "Important insight or highlight",
  "category": "technical | strategic | operational | risk",
  "importance": "high | medium | low"
}
```

### 4. Follow-Ups

```json
{
  "item": "What needs follow-up",
  "owner": "Person responsible",
  "urgency": "immediate | this-week | next-meeting",
  "context": "Why this needs follow-up"
}
```

### 5. Risks Identified

```json
{
  "risk": "Potential risk or blocker",
  "impact": "high | medium | low",
  "mitigation": "Proposed mitigation if discussed"
}
```

---

## LLM Prompt Design

The system prompt uses a **"Senior Project Manager with 15+ years experience"** persona. Key rules:

| Rule | Purpose |
|------|---------|
| Extract both explicit AND implied action items | Catches "we should probably..." statements |
| Be elaborate (2+ sentences per task) | Prevents vague, unhelpful extractions |
| Infer deadlines from context clues | "by next sprint" → concrete deadline |
| Assign priority by urgency language | "ASAP" = high, "when you can" = low |
| Categorize every item | Enables filtering by type |
| Capture who volunteered or was asked | Accurate assignment tracking |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/meeting/{id}/action-items` | Extract action items (AI-generated, cached) |
| `PUT` | `/meeting/{id}/action-items` | Save human-edited items back (HITL) |
| `POST` | `/meeting/{id}/followup-email` | Generate follow-up email from action items |
| `POST` | `/meeting/{id}/followup-email/send` | Send follow-up via SMTP |

### Query Parameters

- `force=true` — Force regeneration even if cached results exist

### HITL Workflow

```
1. POST /meeting/{id}/action-items     → AI extracts items
2. User reviews in frontend            → Edits, adds, removes items
3. PUT /meeting/{id}/action-items      → Saves edited version to disk
4. POST /meeting/{id}/followup-email   → Generates email from final items
5. POST /meeting/{id}/followup-email/send → Sends via SMTP
```

---

## Follow-Up Email

The system generates a professional follow-up email combining:
- Meeting title + summary
- Action items with assignees
- Decisions made
- Key follow-ups

**Email Delivery**: Uses SMTP (configured via environment variables):

| Env Variable | Default | Purpose |
|-------------|---------|---------|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port (TLS) |
| `SMTP_USER` | Required | Sender email |
| `SMTP_PASSWORD` | Required | App password |

Recipients are auto-populated from meeting speaker names and can be edited before sending.

---

## Frontend Features (`ActionItems.svelte`)

- **Meeting Selector** — Dropdown to choose which meeting to analyze
- **Priority Badges** — Color-coded: 🔴 High, 🟡 Medium, 🟢 Low
- **Category Tags** — Development, Design, Research, etc.
- **Inline Editing** — Edit task descriptions, assignees, priorities directly
- **Status Tracking** — Mark items as Done/In Progress/Pending
- **Follow-Up Email Modal** — Auto-populated recipients, editable subject/body, send via SMTP
- **Recipient Chips** — Add/remove recipients with (+) and trash buttons

---

## Caching & Storage

```
storage/{meeting_id}/
└── action_items.json    # Cached (and HITL-edited) results
```

Results are cached after first extraction. The HITL `PUT` endpoint overwrites the cache with human-edited data. Force regeneration with `?force=true` replaces HITL edits.
