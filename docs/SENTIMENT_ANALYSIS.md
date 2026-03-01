# Sentiment Analysis

## Overview

The Sentiment Analysis feature provides **per-segment emotional intelligence** for meeting transcripts. It analyzes every spoken segment in a meeting to classify the sentiment (positive / negative / neutral), assign an emotion label (e.g., *enthusiastic*, *frustrated*, *skeptical*), and compute a numeric score from -1.0 to +1.0.

**Core Idea**: Understand not just *what* was said, but *how* it was said — enabling teams to identify moments of tension, enthusiasm, or disagreement in their meetings.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Sentiment Analysis Pipeline                │
│                                                             │
│  transcript.json                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────┐     ┌──────────────────────────┐  │
│  │  Build Segments     │────▶│  Groq LLM (Llama 3.3)    │  │
│  │  [idx] SPEAKER (Xs):│     │  Sentiment Classification │  │
│  │  "text..."          │     │  per segment              │  │
│  └─────────────────────┘     └──────────┬───────────────┘  │
│                                         │                   │
│                                         ▼                   │
│                              ┌──────────────────────┐      │
│                              │  Enrich with metadata │      │
│                              │  speaker, timestamps  │      │
│                              │  Cache to JSON        │      │
│                              └──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Role |
|-----------|------|------|
| Insights Service | `app/services/insights_service.py` | `analyze_sentiment()` method — LLM-based sentiment classification |
| Insights API | `app/api/insights.py` | REST endpoint `/meeting/{id}/sentiment` |
| Meeting Detail UI | `frontend/src/pages/MeetingDetail.svelte` | Sentiment tab — timeline, charts, per-segment breakdown |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| LLM | Groq `llama-3.3-70b-versatile` | Sentiment classification + emotion labeling |
| Framework | Groq Python SDK | LLM API calls |
| Cache | JSON file | Persistent caching in `storage/{id}/sentiment.json` |
| Frontend | Svelte + Chart.js | Sentiment timeline visualization |

---

## Data Flow

### 1. Input Preparation

The meeting transcript is formatted into a numbered segment list:

```
[0] SPEAKER_00 (0.0s): Good morning everyone, let's get started
[1] SPEAKER_01 (4.2s): Hi, thanks for setting this up
[2] SPEAKER_00 (8.1s): So we have a problem with the laptop deliveries
[3] SPEAKER_02 (12.5s): Yes, this is frustrating, it's been weeks
```

The speaker map is applied during transcript loading, so the LLM sees real names (e.g., `Varun Kumar` instead of `SPEAKER_00`) if available.

### 2. LLM Analysis

The system sends all segments to Groq Llama 3.3 70B with a structured prompt:

**System Prompt Instructions:**

```
For each segment, determine:
- sentiment: "positive", "negative", or "neutral"
- score: -1.0 (most negative) to 1.0 (most positive), 0 is neutral
- emotion: primary emotion (enthusiastic, concerned, frustrated,
           agreeable, neutral, excited, skeptical, etc.)
```

**Expected JSON Output:**

```json
{
  "segments": [
    { "index": 0, "sentiment": "neutral", "score": 0.1, "emotion": "neutral" },
    { "index": 1, "sentiment": "positive", "score": 0.5, "emotion": "agreeable" },
    { "index": 2, "sentiment": "negative", "score": -0.3, "emotion": "concerned" },
    { "index": 3, "sentiment": "negative", "score": -0.7, "emotion": "frustrated" }
  ],
  "overall_sentiment": "negative",
  "overall_score": -0.1,
  "mood_summary": "The meeting started neutral but became tense as delivery delays were discussed.",
  "highlights": {
    "most_positive": "\"Thanks for setting this up\" — appreciative opening",
    "most_negative": "\"This is frustrating, it's been weeks\" — clear frustration",
    "turning_points": ["Segment 2-3: mood shifted negative when delays were raised"]
  }
}
```

### 3. Enrichment

After receiving the LLM response, the system enriches each segment with original metadata:

```python
for idx, segment in enumerate(transcript_segments):
    sentiment_data = llm_result.get(idx, default_neutral)
    enriched_segment = {
        "index": idx,
        "speaker": segment["speaker"],       # Original speaker label
        "start": segment["start"],            # Timestamp (seconds)
        "end": segment["end"],
        "text": segment["text"],              # Full transcript text
        "sentiment": sentiment_data["sentiment"],  # positive/negative/neutral
        "score": sentiment_data["score"],          # -1.0 to 1.0
        "emotion": sentiment_data["emotion"],      # Emotion label
    }
```

### 4. Caching

Results are cached in `storage/{meeting_id}/sentiment.json` and returned immediately on subsequent requests unless `force=true`.

---

## API Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/meeting/{id}/sentiment` | Analyze sentiment for a meeting (cached) |

### Response Schema

```json
{
  "meeting_id": "5c276f9d-...",
  "segments": [
    {
      "index": 0,
      "speaker": "SPEAKER_00",
      "start": 0.0,
      "end": 4.2,
      "text": "Good morning everyone, let's get started",
      "sentiment": "neutral",
      "score": 0.1,
      "emotion": "neutral"
    },
    {
      "index": 3,
      "speaker": "SPEAKER_02",
      "start": 12.5,
      "end": 18.3,
      "text": "This is frustrating, it's been weeks",
      "sentiment": "negative",
      "score": -0.7,
      "emotion": "frustrated"
    }
  ],
  "overall_sentiment": "negative",
  "overall_score": -0.1,
  "mood_summary": "The meeting started neutral but became tense...",
  "highlights": {
    "most_positive": "...",
    "most_negative": "...",
    "turning_points": ["..."]
  }
}
```

---

## Frontend Visualization

The sentiment data is displayed in the **Sentiment Analysis** tab of the Meeting Detail page with several visualizations:

### 1. Overall Metrics

Three stat cards at the top:
- **Overall Sentiment** — Dominant sentiment with emoji indicator (😊 / 😐 / 😟)
- **Sentiment Score** — Numeric score from -1.0 to +1.0 with color coding
- **Mood Summary** — One-sentence LLM-generated description of the meeting mood

### 2. Sentiment Timeline

A horizontal timeline showing sentiment flow across the meeting:

```
Positive ─ ─ ─ ● ─ ─ ● ─ ─ ─ ─ ─ ─ ─ ─ ● ─ ─ ─ ─ ─ ─
Neutral  ─ ● ─ ─ ─ ─ ─ ─ ● ─ ─ ─ ● ─ ─ ─ ─ ─ ─ ● ─ ─
Negative ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ● ─ ─ ─ ● ─ ─ ─ ─ ─ ─ ─
         0:00         1:00         2:00         3:00
```

Each point is color-coded:
- 🟢 **Positive** (score > 0.15) — Green (#22c55e)
- 🟡 **Neutral** (-0.15 to 0.15) — Gray (#94a3b8)
- 🔴 **Negative** (score < -0.15) — Red (#ef4444)

### 3. Highlights Section

Displays the LLM-identified highlights:
- **Most Positive Moment** — Quote and context
- **Most Negative Moment** — Quote and context
- **Turning Points** — Key moments where the meeting mood shifted

### 4. Per-Segment Breakdown

A scrollable list of every segment with:
- Speaker name + timestamp
- Transcript text
- Sentiment badge (Positive / Neutral / Negative)
- Emotion label (e.g., *enthusiastic*, *frustrated*)
- Numeric score
- Color-coded left border for quick scanning

---

## LLM Prompt Design

Key aspects of the sentiment analysis prompt:

| Rule | Purpose |
|------|---------|
| Analyze ALL segments | Ensures no gaps in the timeline |
| Don't default to neutral | Forces the LLM to detect subtle cues |
| Pick up on subtle cues | Agreement, pushback, excitement, frustration |
| Return only valid JSON | Ensures parseable response |

**Fallback Handling**: If the LLM returns invalid JSON, the system provides a default neutral response for all segments:

```python
fallback = {
    "segments": [],
    "overall_sentiment": "neutral",
    "overall_score": 0.0,
    "mood_summary": "Could not analyze sentiment.",
    "highlights": {
        "most_positive": "N/A",
        "most_negative": "N/A",
        "turning_points": []
    }
}
```

---

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| LLM model | `llama-3.3-70b-versatile` | `insights_service.py` |
| LLM temperature | `0.2` | `_call_llm()` |
| Max tokens | `4096` | `_call_llm()` |
| Cache path | `storage/{id}/sentiment.json` | `analyze_sentiment()` |
| GROQ_API_KEY | Required in `.env` | Environment |

---

## Storage Structure

```
storage/
└── {meeting_id}/
    ├── transcript.json     # Source segments with speaker labels
    ├── speaker_map.json    # SPEAKER_ID → real name
    └── sentiment.json      # Cached analysis result
```

---

## Key Design Decisions

1. **LLM-based over rule-based**: Using Llama 3.3 70B for sentiment enables understanding of context, sarcasm, and nuanced language that keyword-based approaches miss.

2. **Per-segment granularity**: Analyzing each transcript segment individually (rather than the whole meeting) enables the timeline visualization and pinpointing specific moments of tension or agreement.

3. **Emotion labeling**: Beyond just positive/negative/neutral, the system provides specific emotion labels (*frustrated*, *enthusiastic*, *skeptical*) for richer insight.

4. **Score scale (-1 to +1)**: Continuous scoring enables the timeline visualization and overall aggregation, whereas categorical labels alone would not support this.

5. **Caching**: Sentiment analysis is compute-intensive (requires LLM call). Results are cached and reused, with force-regeneration available when needed.
