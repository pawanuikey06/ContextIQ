# ContextIQ — Future Roadmap & Feature Ideas

---

## 🤖 AI Agents

### Agent 1: Action Item Follow-Up Agent
- Scans all meetings daily, finds overdue action items
- Sends personalized reminder emails to assignees
- Escalates to manager if 3+ days overdue
- **How:** APScheduler cron → read action_items.json → LLM generates reminder → send via email
- **Time:** 3 hrs | **Impact:** #1 market gap

### Agent 2: Meeting Prep Agent
- 1 hour before a meeting, queries RAG for past meetings with same attendees
- Generates a 1-page prep brief: pending items, past decisions, unresolved issues
- Sends via email to the organizer
- **How:** Calendar webhook → identify attendees → RAG search → LLM generates brief → email
- **Time:** 4 hrs | **Impact:** Unique differentiator, nobody does this well

### Agent 3: Commitment Tracker Agent
- Extracts verbal promises from transcripts: "Varun said he'd finish by Friday"
- Tracks fulfillment: fulfilled / overdue / cancelled
- Weekly accountability report to meeting organizer
- **How:** Post-meeting LLM extraction → commitments DB → daily check → email report
- **Time:** 5 hrs | **Impact:** Turns talk into accountability

### Agent 4: Risk Escalation / Recurring Issue Detector
- Scans all meetings, flags topics discussed 3+ times without resolution
- Alerts leadership: "Laptop issue discussed 4 times in 3 weeks. No resolution."
- **How:** After each meeting → extract topics → compare with last 30 days → alert if repeated
- **Time:** 4 hrs | **Impact:** Identifies stuck problems

### Agent 5: Auto-Stakeholder Update Agent
- Weekly aggregation of all meetings into an executive summary
- "This week: 5 decisions made, 8/12 items completed, 3 risks identified"
- Sends formatted email to configured stakeholder list
- **How:** Weekly cron → gather all meetings → LLM aggregate → email
- **Time:** 3 hrs

---

## 🔌 Integrations

### Project Management
| Tool | What | Time |
|---|---|---|
| Jira | ✅ Already built — bidirectional sync | Done |
| Asana | Push action items as Asana tasks | 3 hrs |
| Trello | Push action items as Trello cards | 2 hrs |
| Linear | Push action items as Linear issues | 2 hrs |
| Monday.com | Push action items as Monday items | 3 hrs |

### Documentation
| Tool | What | Time |
|---|---|---|
| Notion | Auto-create meeting page with summary, action items, decisions | 2 hrs |
| Confluence | Push MoM as wiki page under project space | 3 hrs |
| Google Docs | Export meeting documentation as Google Doc | 2 hrs |

### Communication
| Tool | What | Time |
|---|---|---|
| Teams | ✅ Already built — Adaptive Card notifications | Done |
| Slack | Post summary to channels + `/ask` slash command for RAG | 3 hrs |
| Email | ✅ Already built — follow-up emails with PDF | Done |

### CRM
| Tool | What | Time |
|---|---|---|
| HubSpot | Auto-log meeting summary in contact record | 3 hrs |
| Salesforce | Auto-create activity with summary + action items | 4 hrs |

### Calendar
| Tool | What | Time |
|---|---|---|
| Google Calendar | Auto-import recording after meeting ends | 3 hrs |
| Outlook/Teams Calendar | Auto-fetch Teams recording via Graph API | 4 hrs |

### Publishing
| Tool | What | Time |
|---|---|---|
| PDF | ✅ Already built | Done |
| Word (.docx) | Export MoM as Word document | 2 hrs |
| Google Slides | Auto-generate meeting recap slide deck | 4 hrs |

---

## 📧 Automation Features

### Auto Email Digest (Daily/Weekly)
- Cron job sends digest: "3 meetings this week. 7 items pending. 2 decisions need follow-up."
- Manager-level visibility without opening any tool
- **Time:** 2 hrs

### Auto SOW/Proposal Drafter
- From requirement extraction, generate a draft Statement of Work
- Consulting firms: client meeting → SOW draft in minutes
- **Time:** 3 hrs

### Auto Board/Sprint Report Generator
- Select date range → pull all meetings → aggregate decisions, items, risks
- Generate formatted report (PDF/Notion)
- **Time:** 4 hrs

---

## 🧩 Agent Architecture (How It Fits)

```
Existing Code (NO changes needed)
├── storage/           → Agents READ existing JSON files
├── insights_service   → Agents USE its output
├── jira_service       → Agents CALL existing functions
├── rag_service        → Agents QUERY existing RAG
├── email service      → Agents SEND via existing SMTP
└── FastAPI            → Agents ADD new endpoints

New Code (ADD only)
├── app/agents/
│   ├── followup_agent.py
│   ├── prep_agent.py
│   ├── commitment_agent.py
│   └── escalation_agent.py
├── app/api/agents.py      → API endpoints to trigger agents
└── scheduler setup        → APScheduler for cron triggers
```

### What You Need
| Component | Status |
|---|---|
| Data source (JSON files) | ✅ Already have |
| Brain (Groq + Llama 3.3) | ✅ Already have |
| Action tools (email, Jira, Teams) | ✅ Already have |
| Scheduler (APScheduler) | 🆕 1 pip install |

---

## 🏆 Build Priority

| Phase | Feature | Time | Why |
|---|---|---|---|
| **Phase 1** ✅ | Core pipeline (transcribe → insights → chat → Jira → publish) | Done | Foundation |
| **Phase 2** | Follow-Up Agent (email-based) | 3 hrs | #1 market gap |
| **Phase 3** | Notion + Asana connectors | 4 hrs | Expand beyond Jira |
| **Phase 4** | Meeting Prep Agent | 4 hrs | Unique differentiator |
| **Phase 5** | Slack Bot | 3 hrs | Meet users where they are |
| **Phase 6** | CRM integration (HubSpot) | 3 hrs | Enterprise sales use case |
| **Phase 7** | Commitment Tracker | 5 hrs | Accountability engine |
| **Phase 8** | Multi-role dashboard (manager/lead/member views) | 8 hrs | Enterprise readiness |

---

## 💡 Product Positioning

**Market gap:** Other tools transcribe meetings. ContextIQ makes sure meetings actually lead to action.

| Gap | ContextIQ Solution |
|---|---|
| Nobody follows up on action items | Follow-Up Agent + Jira sync |
| Decisions forgotten across meetings | Commitment Tracker |
| Same problems discussed repeatedly | Recurring Issue Detector |
| People walk in unprepared | Meeting Prep Agent |
| Notes never reach the right tool | Multi-platform push |
| No institutional memory | RAG chatbot across meetings |

**One line pitch:** *"One recording. Complete intelligence. Fully automated."*
