# Meeting Health & Culture Score

## Overview

The Meeting Health feature computes a **Meeting Culture Score (0–100)** that measures team collaboration quality across all meetings. It aggregates four health signals — speaker balance, sentiment, action item completion, and meeting efficiency — into a single weighted score with a letter grade.

**Core Idea**: Give teams a data-driven "health check" on their meeting culture. Are meetings balanced? Are decisions being made? Are action items being completed?

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Meeting Health Pipeline                     │
│                                                             │
│  For each meeting in storage/:                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │transcript │  │sentiment │  │action_   │  │ metadata   │ │
│  │.json      │  │.json     │  │items.json│  │ .json      │ │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬──────┘ │
│        │             │             │              │         │
│        ▼             ▼             ▼              ▼         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  4 Sub-Score Computations (Pure Math, No LLM)        │  │
│  │                                                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │  │
│  │  │Speaker      │ │ Sentiment   │ │ Completion    │  │  │
│  │  │Balance (30%)│ │ Score (25%) │ │ Score (30%)   │  │  │
│  │  └─────────────┘ └─────────────┘ └───────────────┘  │  │
│  │  ┌─────────────┐                                    │  │
│  │  │ Efficiency  │                                    │  │
│  │  │ Score (15%) │                                    │  │
│  │  └─────────────┘                                    │  │
│  └──────────────────────────┬───────────────────────────┘  │
│                             │                               │
│                             ▼                               │
│                  ┌─────────────────────┐                   │
│                  │ Weighted Average     │                   │
│                  │ → Score (0–100)      │                   │
│                  │ → Grade (A–F)        │                   │
│                  └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Role |
|-----------|------|------|
| Stats API | `app/api/stats.py` | Dashboard stats + Culture Score endpoint |
| Dashboard UI | `frontend/src/pages/Home.svelte` | Culture score heatmap display |

---

## The Four Health Signals

### 1. Speaker Balance (Weight: 30%)

**Measures**: How evenly talk-time is distributed among participants.

**Algorithm**: Gini-like imbalance measure:

```
ideal_share = 1 / num_speakers
max_share = max_speaker_time / total_time
score = (1 - max_share) / (1 - ideal_share) × 100
```

| Scenario | Score |
|----------|-------|
| All speakers talk equally | **100** |
| One speaker talks 60%, two share 40% (3 speakers) | ~60 |
| One speaker dominates 90% | ~15 |
| Single speaker (monologue) | **50** (neutral — can't judge) |

**Data Source**: `transcript.json` segments (speaker + start/end times)

---

### 2. Sentiment Score (Weight: 25%)

**Measures**: Percentage of segments with positive or neutral sentiment.

**Algorithm**:

```
good_count = count(segments where sentiment ∈ {"positive", "neutral"})
score = (good_count / total_segments) × 100
```

| Scenario | Score |
|----------|-------|
| All segments positive/neutral | **100** |
| 80% positive/neutral, 20% negative | **80** |
| Half negative | **50** |

**Data Source**: `sentiment.json` (requires sentiment analysis to have been run)

**Returns `None`** if no sentiment data exists → excluded from weighted average.

---

### 3. Action Item Completion (Weight: 30%)

**Measures**: Percentage of action items marked as "Done".

**Algorithm**:

```
done_count = count(action_items where status == "Done")
score = (done_count / total_items) × 100
```

| Scenario | Score |
|----------|-------|
| All items completed | **100** |
| Half completed | **50** |
| None completed | **0** |

**Data Source**: `action_items.json` (requires action items extraction + HITL status updates)

**Returns `None`** if no action items exist → excluded from weighted average.

---

### 4. Meeting Efficiency (Weight: 15%)

**Measures**: Decisions made per 10 minutes of meeting time.

**Algorithm**:

```
expected_decisions = meeting_duration_minutes / 10
ratio = actual_decisions / expected_decisions
score = min(100, ratio × 100)
```

| Scenario | Score |
|----------|-------|
| 30-min meeting with 3+ decisions | **100** |
| 30-min meeting with 1 decision | ~33 |
| 30-min meeting with 0 decisions | **0** |

**Data Source**: `action_items.json` decisions list + `transcript.json` duration

**Returns `None`** if no action items data or meeting < 1 minute.

---

## Weighted Score Calculation

```python
WEIGHTS = {
    "speaker_balance": 0.30,
    "sentiment":       0.25,
    "completion":      0.30,
    "efficiency":      0.15,
}

# Only signals with data contribute (None signals are excluded)
# Weight is redistributed proportionally among available signals
for key, val in signals.items():
    if val is not None:
        weighted_sum += val * WEIGHTS[key]
        total_weight += WEIGHTS[key]

meeting_score = weighted_sum / total_weight
```

**Example**: Meeting with only speaker_balance (70) and sentiment (85):
```
weighted_sum = 70 × 0.30 + 85 × 0.25 = 21 + 21.25 = 42.25
total_weight = 0.30 + 0.25 = 0.55
score = 42.25 / 0.55 = 76.8
```

---

## Grading System

| Score Range | Grade |
|-------------|-------|
| 80–100 | **Excellent** |
| 60–79 | **Good** |
| 40–59 | **Needs Work** |
| 0–39 | **Poor** |
| No data | **No Data** |

---

## API Endpoints

### Dashboard Stats

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stats` | Aggregate stats across all meetings |
| `GET` | `/stats/culture-score` | Full culture score with per-meeting breakdown |

### `/stats` Response

```json
{
  "total_meetings": 5,
  "total_speakers": 8,
  "total_duration_seconds": 1842.5,
  "total_duration_formatted": "30:42",
  "meetings_per_day": [
    { "date": "2026-02-25", "count": 2 },
    { "date": "2026-02-28", "count": 3 }
  ]
}
```

### `/stats/culture-score` Response

```json
{
  "overall_score": 72.4,
  "grade": "Good",
  "signal_scores": {
    "speaker_balance": 68.5,
    "sentiment": 82.0,
    "completion": 50.0,
    "efficiency": 100.0
  },
  "per_meeting": [
    {
      "meeting_id": "5c276f9d-...",
      "title": "Laptop Delivery Delay Resolution Meeting",
      "date": "2026-02-28",
      "score": 72.4,
      "signals": {
        "speaker_balance": 68.5,
        "sentiment": 82.0,
        "completion": 50.0,
        "efficiency": 100.0
      }
    }
  ],
  "total_scored": 2
}
```

---

## Dashboard Stats Computation

The `/stats` endpoint scans ALL meeting directories and computes:

1. **Total Meetings** — Count of directories with `transcript.json`
2. **Unique Speakers** — Resolved via `speaker_map.json` across all meetings (deduplicates by real name)
3. **Total Duration** — Sum of last segment end-times, formatted as `H:MM:SS` or `M:SS`
4. **Meetings Per Day** — From `metadata.json` upload dates

---

## Key Design Decisions

1. **Pure computation** — No LLM calls needed. All scores are computed from existing data files using math. This makes the endpoint fast and free.

2. **Graceful degradation** — If sentiment or action items haven't been generated yet, those signals return `None` and the available signals' weights are redistributed. The score is still meaningful.

3. **Cross-meeting aggregation** — The overall score averages across all meetings, giving a longitudinal view of meeting culture trends.

4. **Speaker deduplication** — The stats endpoint resolves SPEAKER_00/01/02 labels to real names via `speaker_map.json` before counting unique speakers, so the same person isn't counted multiple times.

---

## Storage Dependencies

```
storage/
├── {meeting_id}/
│   ├── transcript.json      # Required (speaker balance + duration)
│   ├── metadata.json        # Required (dates, title)
│   ├── sentiment.json       # Optional (sentiment signal)
│   └── action_items.json    # Optional (completion + efficiency signals)
```

All four JSON files must exist for a meeting to receive all four sub-scores. Meetings with only `transcript.json` will receive only the speaker balance score.
