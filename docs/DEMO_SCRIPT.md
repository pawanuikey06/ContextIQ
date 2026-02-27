# ContextIQ — 15-Minute Demo Script

## How to Use This Script
- Each section has a **time marker** and **what to show on screen**
- Speak naturally — this is a guide, not a script to read word-for-word
- Total: ~15 minutes (with buffer)

---

## 🎬 [0:00 – 1:30] Introduction — The Problem

**Show:** Title slide or just open the Landing Page

> "Every day, teams have meetings. After the meeting ends, what happens? Someone has to write notes, track who said what, list action items, and share updates. Most of the time, nobody does it — and important decisions get lost.
>
> We built **ContextIQ** — a platform that takes a meeting recording and automatically gives you everything: transcript with speaker names, summary in English and Hindi, action items, requirements, meeting documents, sentiment of each speaker, topic breakdown, and even a follow-up email draft.
>
> You can chat with an AI about your meetings — ask questions like 'What did Babu say about the laptop issue?' and get answers with exact timestamps. You can push action items directly to Jira and keep them in sync. You can publish a PDF report, send it over email, or post to Microsoft Teams — all in one click.
>
> Let me show you how it works, step by step."

---

## 📹 [1:30 – 2:30] Upload & Transcription

**Show:** Dashboard → Upload a video (or show pre-uploaded meeting)

> "It starts here. You upload a video recording of your meeting. The system extracts the audio using FFmpeg, then sends it for transcription.
>
> We support three transcription engines:
> - **WhisperX** — runs on your own GPU, gives word-level timestamps
> - **AssemblyAI** — a cloud service, very accurate on noisy audio
> - **Groq Whisper** — the fastest option, transcribes 5x faster than real-time
>
> Along with transcription, we also do **speaker detection** — the system figures out who spoke when. So every sentence in the transcript has a speaker label and a timestamp."

---

## 📜 [2:30 – 4:00] Transcript Views

**Show:** Click into a meeting → Show Chat View, Speaker View, Timeline View

> "Once transcription is done, you can see the transcript in three different views:
>
> **Chat View** — looks like a messaging app, each person's dialogue shown as a bubble. Easy to read.
>
> **Speaker View** — groups everything by speaker. So if you want to see everything Babu said, it's all in one place.
>
> **Timeline View** — shows exact timestamps, useful when you want to jump to a specific moment in the recording.
>
> Now, the system calls speakers SPEAKER_00, SPEAKER_01. That's not useful. So we built a name mapping feature..."

---

## 👤 [4:00 – 5:00] Speaker Name Mapping (Human-in-the-Loop)

**Show:** Speaker Map section → Map names → Save

> "Here's the speaker mapping panel. I just type the real names — SPEAKER_00 is Babu, SPEAKER_01 is Purnima, and so on. I hit Save.
>
> Now here's the important part — the moment I save these names, the system automatically regenerates **everything** in the background. The summary, action items, requirements, documents, sentiment analysis, topics, even the AI chat index — all of them get rebuilt using the real names.
>
> I don't have to click anything else. The API responds instantly, and 8 tasks run in the background with real names. This is what we call the Human-in-the-Loop design — let the AI do the work, let the human correct the names, and the AI re-does everything automatically."

---

## 📝 [5:00 – 6:30] AI-Generated Summary

**Show:** Summary section — English + Hindi

> "The system generates a meeting summary using Llama 3.3, a 70-billion parameter AI model. We get:
>
> **Per-speaker summaries** — what each person contributed. For example, 'Babu focused on the HRMS automation timeline and raised the need for HR approval.'
>
> **Overall summary in English** — 3 to 5 paragraphs covering the full meeting.
>
> **Overall summary in Hindi** — for teams that work in Hindi. This is not a Google Translate copy — the AI writes it naturally in Hindi.
>
> The user can **review and edit** both summaries before approving them. Only after approval can you publish or share them. This is another Human-in-the-Loop feature — the AI generates, the human verifies."

---

## ✅ [6:30 – 8:00] Action Items & Jira Integration

**Show:** Action Items page → Show fields → Push to Jira → Show Jira ticket

> "Next, the system extracts action items from the meeting discussion. Each one has:
> - **Who is responsible** — assigned person
> - **Priority** — high, medium, or low
> - **Deadline** — if mentioned in the meeting
> - **Category** — like development, testing, communication
> - **Context** — why this task was discussed
> - **Success criteria** — how do we know it's done
>
> Along with action items, we also extract **decisions** — what was decided and by whom. And **key takeaways** — the big-picture points.
>
> Now the interesting part — I can push any action item directly to **Jira**. I click this button, and it creates a Jira ticket with all the fields mapped — title, priority, description, due date, labels. Let me show you the actual ticket in Jira... here it is, SCRUM-12, with all the details.
>
> The sync is **bidirectional**. If someone changes the status in Jira, I click Sync and it updates here. If I change priority here, I can push it back to Jira. They stay in sync."

---

## 📋 [8:00 – 9:00] Requirements & Documentation

**Show:** Requirements tab → Documentation tab

> "For product and engineering meetings, we extract **requirements** — functional requirements, non-functional requirements, constraints, and even user stories.
>
> We also generate a complete **Meeting Document** — like official Minutes of Meeting. It has the agenda, attendees, discussion points organized by topic, action items, decisions, and next steps. This is ready to share — no formatting needed.
>
> We also have **topic segmentation** — the system identifies when the discussion shifted from one topic to another, with time ranges. And **sentiment analysis** — for each part of the conversation, it tells you if the tone was positive, negative, or neutral."

---

## 💬 [9:00 – 10:30] AI Chatbot (RAG)

**Show:** AI Chat page → Ask a question → Show streaming answer with citations

> "This is one of the most powerful features. You can **talk to an AI about your meetings**.
>
> I've indexed multiple meetings into the system. Now I can ask: 'What decisions were made about the laptop delivery process?'
>
> Watch — the answer streams in real-time, and it tells me exactly which meeting this came from, which speaker said it, and the timestamp. I can ask follow-up questions too, because the chat remembers context.
>
> Under the hood, this uses a technique called RAG — we store meeting transcripts in a vector database called ChromaDB. When you ask a question, the system finds relevant segments from ALL your meetings, combines them, and asks the AI to generate an answer grounded in the actual meeting content. It doesn't make things up — every answer is backed by real transcript data."

---

## 📤 [10:30 – 11:30] Publishing — PDF, Email, Teams

**Show:** Publish section → Show PDF → Show Teams card (if available)

> "Once everything is reviewed and approved, you can publish the meeting intelligence in three ways:
>
> **PDF Report** — downloads a nicely formatted PDF with both English and Hindi content. We use special Unicode fonts so Hindi renders correctly.
>
> **Email** — attaches the PDF and sends it to your team via email.
>
> **Microsoft Teams** — sends a rich notification card to your Teams channel. It shows the summary, top action items, decisions, key takeaways, and speaker highlights — all in a nicely formatted card.
>
> We also generate a **follow-up email** — a professional email draft that combines the meeting title, summary, action items assigned to each person, and key decisions. You can preview it, edit it, and send it directly from the app."

---

## 📊 [11:30 – 12:30] Speaker Analytics & Report Cards

**Show:** Speaker Analytics section → Report Cards → Culture Score

> "The system also generates **speaker analytics** — talk time distribution, how active each person was, and what topics they participated in.
>
> We have **Speaker Report Cards** — each person gets a scorecard showing their talk time percentage, number of action items assigned, topics they contributed to, their sentiment pattern, and an AI-classified role like 'Decision Maker' or 'Presenter'.
>
> There's also a **Meeting Culture Score** — an overall rating of how balanced, productive, and collaborative the meeting was. It tells you things like 'One speaker dominated 70% of the time' or 'All action items were assigned to the same person.'"

---

## 🏗️ [12:30 – 13:30] Architecture & Tech Stack

**Show:** Architecture diagram from docs/architecture.md

> "Let me quickly walk through the architecture.
>
> The **frontend** is built with Svelte — a lightweight JavaScript framework. Clean, fast, minimal code.
>
> The **backend** is Python with FastAPI — 12 API routers, 30+ endpoints, all REST-based.
>
> We have **9 service classes** that handle the business logic — one for transcription, one for summaries, one for insights, one for RAG, one for Jira, one for publishing, and so on.
>
> For **AI**, we use:
> - WhisperX for transcription
> - pyannote for speaker detection
> - Groq API serving Llama 3.3 70B for all text analysis
> - ChromaDB with LangChain for the RAG chatbot
>
> **Storage** is simple — one folder per meeting, each insight saved as a JSON file. Easy to inspect, debug, and portable.
>
> **Integrations** — Jira REST API for ticket management, Teams Webhooks for notifications, SMTP for email, and fpdf2 for PDF generation."

---

## 🔄 [13:30 – 14:30] Key Design Highlights

**Show:** Workflow diagram or just speak

> "A few things that make ContextIQ unique:
>
> **One — Automatic background regeneration.** When you fix speaker names, you don't have to redo anything. Eight AI tasks run automatically in the background with the correct names. The user doesn't wait — the API responds instantly.
>
> **Two — Cross-meeting intelligence.** The AI chatbot doesn't just answer about one meeting. It searches across ALL your meetings and gives you combined answers with sources.
>
> **Three — Bidirectional Jira sync.** Action items aren't just exported and forgotten. Changes in Jira flow back to ContextIQ and vice versa.
>
> **Four — Bilingual support.** English and Hindi summaries generated natively — not machine translated, but properly written by the AI in each language.
>
> **Five — Everything is connected.** Upload once, and the system gives you transcript, summary, action items, requirements, documentation, sentiment, topics, follow-up email, Jira tickets, PDF report, Teams notification — all from one recording."

---

## 🚀 [14:30 – 15:00] Future Enhancements

**Show:** Speak directly, wrap up

> "This is a working platform today. For future versions, we're planning:
>
> **Multi-role access** — different views for managers, team leads, and team members. A manager sees cross-team analytics and decision tracking. A team lead sees their team's action items and follow-ups. A team member sees only their assignments and meeting transcripts.
>
> **Live recording** — record directly from the browser microphone, no file upload needed.
>
> **Decision tracking dashboard** — track all decisions made across meetings, flag ones that keep coming back without resolution.
>
> **More languages** — beyond English and Hindi, support for regional and international languages.
>
> **Calendar integration** — auto-import recordings from Google Calendar or Outlook.
>
> That's ContextIQ — from a raw meeting recording to complete, actionable meeting intelligence, fully automated. Thank you."

---

## ⏱️ Timing Summary

| Section | Duration | Cumulative |
|---|---|---|
| Introduction | 1:30 | 1:30 |
| Upload & Transcription | 1:00 | 2:30 |
| Transcript Views | 1:30 | 4:00 |
| Speaker Mapping (HITL) | 1:00 | 5:00 |
| AI Summary | 1:30 | 6:30 |
| Action Items & Jira | 1:30 | 8:00 |
| Requirements & Docs | 1:00 | 9:00 |
| AI Chatbot (RAG) | 1:30 | 10:30 |
| Publishing | 1:00 | 11:30 |
| Speaker Analytics | 1:00 | 12:30 |
| Architecture | 1:00 | 13:30 |
| Design Highlights | 1:00 | 14:30 |
| Future Enhancements | 0:30 | **15:00** |

---

## 💡 Tips for the Demo

1. **Pre-load everything** — have a meeting already transcribed with all insights generated
2. **Keep the Jira ticket open** in another browser tab to switch to quickly
3. **Have the AI Chat pre-indexed** with at least 1-2 meetings
4. **Don't read from screen** — glance at bullet points, speak naturally
5. **If something fails live**, say "Let me show you the one I prepared earlier" and switch to pre-generated data
6. **End with a strong line:** "One recording. Complete intelligence. Fully automated."
