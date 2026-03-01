# Requirements Extraction

## Overview

The Requirements Extraction feature uses AI to automatically extract **functional requirements, non-functional requirements, user stories, constraints, assumptions, risks, and open questions** from meeting transcripts. It transforms unstructured meeting discussions into a structured requirements document suitable for engineering handoff.

**Core Idea**: Convert meeting conversations into a traceable requirements specification — no manual note-taking needed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Requirements Pipeline                      │
│                                                             │
│  transcript.json                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐     ┌──────────────────────────┐  │
│  │  Format transcript  │────▶│  Groq LLM (Llama 3.3)    │  │
│  │  Speaker: text      │     │  "Sr. Business Analyst"   │  │
│  └─────────────────────┘     │  persona                  │  │
│                              └──────────┬───────────────┘  │
│                                         │                   │
│                              ┌──────────▼────────────────┐ │
│                              │  Structured JSON           │ │
│                              │  functional_requirements[] │ │
│                              │  non_functional_req[]      │ │
│                              │  user_stories[]            │ │
│                              │  constraints[]             │ │
│                              │  assumptions[]             │ │
│                              │  risks[]                   │ │
│                              │  open_questions[]          │ │
│                              └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Role |
|-----------|------|------|
| Insights Service | `app/services/insights_service.py` | `extract_requirements()` — LLM extraction |
| Insights API | `app/api/insights.py` | `POST /meeting/{id}/requirements` |
| Meeting Detail UI | `frontend/src/pages/MeetingDetail.svelte` | Requirements tab display |

---

## Extraction Schema

### 1. Summary

A 2-3 sentence overview of what the meeting requires.

### 2. Functional Requirements

```json
{
  "id": "FR-001",
  "title": "Short descriptive title",
  "description": "Detailed description (2-3 sentences) — WHY needed, WHAT problem, HOW it works",
  "acceptance_criteria": ["Testable condition 1", "Testable condition 2"],
  "priority": "must-have | should-have | nice-to-have",
  "priority_rationale": "Why this priority level",
  "raised_by": "Person who raised this",
  "agreed_by": ["Names of people who agreed"],
  "status": "proposed | agreed | needs-discussion",
  "dependencies": ["FR-002"],
  "implementation_notes": "Technical implementation hints discussed",
  "risk": "What could go wrong if not implemented correctly"
}
```

### 3. Non-Functional Requirements

```json
{
  "id": "NFR-001",
  "title": "Short title",
  "description": "Detailed description",
  "category": "performance | security | scalability | usability | reliability | compliance",
  "measurable_criteria": "How to measure (e.g., response time < 2s)",
  "impact": "What happens if this NFR is not met"
}
```

### 4. User Stories

```json
{
  "story": "As a [role], I want [feature], so that [benefit]",
  "acceptance_criteria": ["Given X, When Y, Then Z"]
}
```

### 5. Constraints

```json
{
  "constraint": "Description",
  "type": "budget | timeline | technical | resource | regulatory",
  "impact": "How this affects the project"
}
```

### 6. Risks

```json
{
  "risk": "Description",
  "likelihood": "high | medium | low",
  "impact": "high | medium | low",
  "mitigation": "Proposed mitigation"
}
```

### 7. Open Questions

```json
{
  "question": "Unresolved question",
  "raised_by": "Person who raised it",
  "needs_answer_from": "Who should answer"
}
```

### 8. Assumptions

Simple string array: `["Assumption that needs validation"]`

---

## LLM Prompt Design

Uses a **"Senior Business Analyst with 15+ years of requirements engineering"** persona. Key rules:

| Rule | Purpose |
|------|---------|
| Extract only REAL requirements | No invention — only from transcript |
| Be elaborate (2-3 sentences minimum) | Detailed, actionable descriptions |
| Auto-increment IDs (FR-001, NFR-001) | Traceable requirement numbering |
| Extract implicit requirements | "we need it to be fast" → performance NFR |
| Map dependencies between requirements | Shows requirement relationships |
| Include ALL derivable acceptance criteria | Testable conditions from discussion |
| Return empty arrays if no requirements | Handles non-requirement meetings gracefully |

---

## API Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/meeting/{id}/requirements` | Extract requirements (cached) |

### Query Parameters

- `force=true` — Force regeneration even if cached

### Response Example

```json
{
  "meeting_id": "5c276f9d-...",
  "summary": "The meeting discussed requirements for a laptop delivery tracking system...",
  "functional_requirements": [
    {
      "id": "FR-001",
      "title": "Delivery Status Tracking",
      "description": "The system must provide real-time tracking...",
      "acceptance_criteria": ["Status updates within 30 minutes", "..."],
      "priority": "must-have",
      "status": "agreed"
    }
  ],
  "non_functional_requirements": [...],
  "user_stories": [...],
  "constraints": [...],
  "assumptions": [...],
  "risks": [...],
  "open_questions": [...]
}
```

---

## Fallback Handling

If the LLM returns invalid JSON, the system creates a fallback response with empty arrays and saves the raw LLM output as the first open question for manual review.

---

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| LLM model | `llama-3.3-70b-versatile` | `insights_service.py` |
| LLM temperature | `0.2` | `_call_llm()` |
| Max tokens | `4096` | `_call_llm()` |
| Cache path | `storage/{id}/requirements.json` | `extract_requirements()` |

---

## Storage

```
storage/{meeting_id}/
└── requirements.json    # Cached extraction result
```
