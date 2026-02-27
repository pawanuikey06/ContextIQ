# 🏆 ContextIQ — 48-Hour Hackathon Battle Plan

**Goal:** Win the hackathon. Ship maximum impact features in 48 hours.
**Strategy:** Focus on features that are VISIBLE in demo, fill market gaps, and use "wow" words (AI Agent, n8n, RAG, Automation).

---

## ⏱️ Timeline

### Day 1 (Hours 1–24)

#### Hour 1–3: 🔧 Quick Fixes & Polish (Immediate Impact)

| # | Task | Time | Impact |
|---|---|---|---|
| 1 | **Demo Mode / Sample Meeting** — preload a fully processed meeting so the app looks alive on first open | 45 min | 🔥🔥🔥 |
| 2 | **Toast Notifications** — success/error toasts for every action (already have toasts, verify all actions use them) | 30 min | 🔥🔥 |
| 3 | **Loading Skeletons** — replace spinners with skeleton loaders on main sections for premium feel | 30 min | 🔥🔥 |
| 4 | **Landing/Hero Page** — a single stunning landing page before dashboard explaining what ContextIQ does | 45 min | 🔥🔥🔥 |
| 5 | **Dark Mode Toggle** — add a light/dark theme toggle | 30 min | 🔥🔥 |

---

#### Hour 3–8: 🤖 AI Agent #1 — Follow-Up Agent (Biggest Market Gap)

**What:** An autonomous agent that scans all meetings, finds overdue action items, and sends personalized reminder emails.

**Files to create:**
```
app/agents/__init__.py
app/agents/followup_agent.py
app/api/agents.py
```

**Implementation:**
1. Create `followup_agent.py`:
   - Scan all `storage/*/action_items.json`
   - Find items past deadline or items assigned but not marked done
   - For each overdue item, use Groq LLM to generate a personalized, professional reminder email
   - Send via existing SMTP service
   - Log results

2. Create `app/api/agents.py`:
   - `POST /agents/followup/run` — trigger manually
   - `GET /agents/followup/status` — last run results
   - `POST /agents/followup/configure` — set schedule, recipients

3. Add scheduler (APScheduler):
   - `pip install apscheduler`
   - Setup in `main.py` — run follow-up agent daily at 9 AM
   - Also allow manual trigger from UI

4. Frontend — Agent Dashboard:
   - New page: "AI Agents" in sidebar
   - Show follow-up agent status: last run, items found, emails sent
   - Toggle on/off, configure schedule
   - Run manually button

**Why judges care:** "Our AI agent autonomously follows up on action items. Nobody else does this."

---

#### Hour 8–12: 🤖 AI Agent #2 — Meeting Prep Agent

**What:** Before a meeting, generates a prep brief by searching past meetings with same attendees.

**Implementation:**
1. Create `app/agents/prep_agent.py`:
   - Accept a list of attendee names
   - Query RAG for all past meetings involving those people
   - Use LLM to generate a 1-page prep brief:
     - Pending action items from previous meetings
     - Key decisions made
     - Unresolved issues
     - Relationship context ("last met 2 weeks ago")
   - Return as JSON + optional email delivery

2. API endpoint:
   - `POST /agents/prep/generate` — body: `{attendees: ["Varun", "Poornima"]}`
   - Returns prep brief

3. Frontend:
   - Button on dashboard: "Prep for Meeting"
   - Modal: enter attendee names
   - Shows generated prep brief with option to email it

---

#### Hour 12–16: 🔗 n8n Integration

**What:** Ship a pre-built n8n workflow that connects ContextIQ to external tools.

**Implementation:**
1. Create `docker-compose.yml` that runs both ContextIQ + n8n
2. Create 3 pre-built n8n workflow JSON files:
   - `workflows/n8n_daily_followup.json` — daily follow-up via email
   - `workflows/n8n_slack_post.json` — post summary to Slack after processing
   - `workflows/n8n_notion_sync.json` — push MoM to Notion
3. Add import instructions in README
4. Screenshot the n8n canvas for the demo

**Why judges care:** "ContextIQ is extensible. Connect it to ANY tool via n8n — no code, drag and drop."

---

#### Hour 16–20: 📊 Manager Dashboard

**What:** A dashboard view for managers showing metrics across ALL meetings.

**Implementation:**
1. Backend: `GET /dashboard/manager`
   - Total meetings this week/month
   - Total action items: created / completed / overdue
   - Top assignees by workload
   - Decisions made this week
   - Risks flagged
   - Meeting time breakdown by topic

2. Frontend: New page accessible from sidebar
   - Stats cards at top (meetings, items, completion rate)
   - Chart: action items over time (simple bar chart using Chart.js)
   - Table: overdue items across all meetings
   - Table: top 5 pending commitments

---

#### Hour 20–24: ✨ UI Polish & Screenshots

| Task | Time |
|---|---|
| Responsive design check — ensure mobile-friendly | 1 hr |
| Add micro-animations (card hover, button press, page transitions) | 1 hr |
| Take 10-15 screenshots for the project report | 30 min |
| Record a 2-minute demo video (browser recording) | 30 min |
| Fix any remaining UI bugs from the day | 1 hr |

---

### Day 2 (Hours 25–48)

#### Hour 25–29: 🤖 AI Agent #3 — Commitment Tracker

**What:** Extracts verbal promises from meetings and tracks their fulfillment.

**Implementation:**
1. Create `app/agents/commitment_agent.py`:
   - After each meeting, extract commitments: "Who said they'd do What by When"
   - Store in `storage/{meeting_id}/commitments.json`
   - Daily scan: check if commitment deadline passed
   - Generate accountability report

2. New insight type in insights_service:
   - `extract_commitments(meeting_id)` — new method
   - Prompt: "Extract all verbal commitments, promises, and volunteered tasks with owner and deadline"

3. Frontend:
   - New section in meeting detail: "Commitments Tracker"
   - Status badges: ✅ Fulfilled | ⏳ Pending | ❌ Overdue
   - Commitment timeline across meetings

---

#### Hour 29–33: 🔗 Notion Integration

**What:** Push meeting summary + action items as a Notion page.

**Implementation:**
1. Create `app/services/notion_service.py`:
   - Notion API — create page in a database
   - Map: meeting title → page title, summary → content, action items → to-do blocks
   - Tags: date, attendees, status

2. API endpoint: `POST /meeting/{id}/publish/notion`

3. Frontend: Add "Push to Notion" button next to existing PDF/Email/Teams buttons

4. Config: Notion API key + database ID in `.env`

**Why judges care:** "Export to the tools your team uses — Jira, Notion, Teams, Email, PDF. One click."

---

#### Hour 33–37: 📝 Auto SOW Generator

**What:** From requirements extraction, auto-generate a Statement of Work document.

**Implementation:**
1. Create `app/services/sow_service.py`:
   - Read `requirements.json`
   - LLM prompt: "Generate a professional Statement of Work including scope, deliverables, timeline, assumptions, and pricing template"
   - Return as structured JSON + rendered PDF

2. API: `POST /meeting/{id}/generate-sow`

3. Frontend: Button in Requirements section: "Generate SOW"
   - Preview the SOW
   - Download as PDF

**Why judges care:** "Client meeting to SOW draft in 60 seconds. Consulting firms save hours per proposal."

---

#### Hour 37–41: 🧪 Testing & Bug Fixes

| Task | Time |
|---|---|
| Test all 3 agents end-to-end | 1.5 hr |
| Test Jira integration (push, sync, update) | 30 min |
| Test all publishing (PDF, email, Teams, Notion) | 30 min |
| Fix any breaking bugs | 1.5 hr |

---

#### Hour 41–45: 📑 Documentation & Report

| Task | Time |
|---|---|
| Update PROJECT_REPORT.md with new features + screenshots | 1.5 hr |
| Update README.md with agent docs + n8n setup | 1 hr |
| Update DEMO_SCRIPT.md with agent demo flow | 30 min |
| Finalize architecture diagrams with agents layer | 1 hr |

---

#### Hour 45–48: 🎤 Demo Prep

| Task | Time |
|---|---|
| Rehearse the demo 2-3 times | 1 hr |
| Ensure demo data looks realistic and impressive | 30 min |
| Prepare backup plan (screenshots) in case of live issues | 30 min |
| Final git push + backup | 30 min |

---

## 🎯 What You'll Have After 48 Hours

### Features (for demo)

| Feature | Status |
|---|---|
| Multi-engine transcription (WhisperX, AssemblyAI, Groq) | ✅ Already done |
| Speaker diarization + HITL name mapping | ✅ Already done |
| Background regeneration (8 AI tasks auto-refresh) | ✅ Already done |
| Bilingual summary (EN + HI) | ✅ Already done |
| Action items + decisions + risks + follow-ups | ✅ Already done |
| Requirements extraction | ✅ Already done |
| MoM documentation generation | ✅ Already done |
| Topic segmentation | ✅ Already done |
| Sentiment analysis | ✅ Already done |
| Speaker report cards + culture score | ✅ Already done |
| RAG chatbot (cross-meeting, streaming) | ✅ Already done |
| Jira bidirectional sync | ✅ Already done |
| PDF + Email + Teams publishing | ✅ Already done |
| Follow-up email generator | ✅ Already done |
| **🆕 AI Follow-Up Agent** | Build in 48h |
| **🆕 AI Meeting Prep Agent** | Build in 48h |
| **🆕 AI Commitment Tracker** | Build in 48h |
| **🆕 n8n Workflow Integration** | Build in 48h |
| **🆕 Manager Dashboard** | Build in 48h |
| **🆕 Notion Integration** | Build in 48h |
| **🆕 Auto SOW Generator** | Build in 48h |
| **🆕 Landing Page** | Build in 48h |
| **🆕 Dark Mode** | Build in 48h |
| **🆕 Demo Mode** | Build in 48h |

### Architecture Diagram (after 48h)

```
┌─────────────────────────────────────────────────────┐
│                    CONTEXTIQ                         │
├─────────────────────────────────────────────────────┤
│  PRESENTATION LAYER                                  │
│  Svelte SPA + Landing Page + Manager Dashboard       │
├─────────────────────────────────────────────────────┤
│  API LAYER (FastAPI, 35+ endpoints)                  │
│  Upload │ Transcribe │ Insights │ Chat │ Agents      │
├─────────────────────────────────────────────────────┤
│  AI AGENTS LAYER (NEW)                               │
│  Follow-Up │ Meeting Prep │ Commitment Tracker       │
├─────────────────────────────────────────────────────┤
│  SERVICE LAYER                                       │
│  STT │ Summary │ Insights │ RAG │ Jira │ Notion      │
├─────────────────────────────────────────────────────┤
│  INTEGRATION LAYER                                   │
│  n8n │ Jira │ Teams │ Email │ Notion │ PDF           │
├─────────────────────────────────────────────────────┤
│  DATA LAYER                                          │
│  JSON Storage │ ChromaDB │ Audio Files               │
└─────────────────────────────────────────────────────┘
```

---

## 🗣️ Demo Wow Moments (plan these carefully)

1. **"Upload a recording → fully processed in 90 seconds"** — show the speed
2. **"Map speaker names → all 8 insights regenerate in background"** — live HITL
3. **"Ask the AI about past meetings"** — cross-meeting RAG with streaming
4. **"Push to Jira with one click"** — real ticket appears in Jira
5. **"Our AI agent found 3 overdue items and already sent reminders"** — show agent email
6. **"Prep brief for your next meeting — generated automatically"** — show prep agent
7. **"Connect to any tool via n8n — no code"** — show n8n canvas
8. **"Client meeting → SOW draft in 60 seconds"** — live SOW generation

---

## 🔑 Winning Keywords for Judges

Use these in your demo and report:
- **AI Agents** (autonomous, scheduled, proactive)
- **RAG** (Retrieval-Augmented Generation, no hallucination)
- **HITL** (Human-in-the-Loop, AI + human verification)
- **Bidirectional Sync** (Jira ↔ ContextIQ)
- **Multi-modal** (speech → text → intelligence → action)
- **Zero-code extensibility** (n8n integration)
- **Bilingual** (English + Hindi support)
- **Platform-agnostic** (works with any meeting tool)
