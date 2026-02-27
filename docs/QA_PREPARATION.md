# ContextIQ — Q&A Preparation Guide

## Part 1: Likely Questions & Answers
## Part 2: Technical Term Definitions & Explanations

---

# PART 1: QUESTIONS & ANSWERS

---

## 🔹 Section A: Project Overview Questions

### Q1: What is ContextIQ in one line?
**A:** ContextIQ is an AI platform that takes a meeting recording and automatically generates transcripts, summaries, action items, and lets you chat with an AI about your meetings.

### Q2: What problem does this solve?
**A:** After meetings, nobody writes proper notes. Decisions get forgotten, action items are lost, and people end up repeating the same discussions. ContextIQ automates all of that — you upload a recording, and in 90 seconds you get everything: transcript, summary in English and Hindi, action items with deadlines, requirements, meeting documents, and a follow-up email ready to send.

### Q3: Who is this for? Who is your target user?
**A:** Any team that has regular meetings — product teams, engineering teams, HR, management. Specifically:
- **Team leads** who need to track action items and decisions
- **Project managers** who need meeting documentation
- **Product managers** who need requirements extracted from discussions
- **Anyone** who wastes time writing meeting notes

### Q4: How is this different from just recording a meeting on Zoom?
**A:** Zoom gives you a video file. That's it. You still have to watch the entire recording to find information. ContextIQ converts that recording into structured data — searchable transcript with speaker names, organized action items, requirements, and an AI you can ask questions to. It's the difference between having a library of books vs having a search engine.

### Q5: Can this work for any language?
**A:** Currently, transcription works best for English. The AI model (Whisper) supports 99 languages, so it can transcribe other languages too. For summaries, we generate in English and Hindi. Adding more languages is just a prompt change — no code modification needed.

---

## 🔹 Section B: Technical Architecture Questions

### Q6: What is your tech stack?
**A:**
- **Frontend:** Svelte with Vite for fast development
- **Backend:** Python with FastAPI — it's async, fast, and auto-generates API docs
- **Transcription:** WhisperX — an open-source speech recognition model by OpenAI, with an extension for word-level timestamps
- **Speaker Detection:** pyannote.audio — a neural network that figures out who is speaking when
- **AI Model:** Llama 3.3 70B from Meta, served through Groq's API which gives very fast responses
- **Chat/RAG:** ChromaDB as vector database + LangChain for retrieval
- **Integrations:** Jira REST API, Microsoft Teams Webhooks, SMTP for email, fpdf2 for PDF

### Q7: Why did you choose FastAPI over Django or Flask?
**A:** Three reasons:
1. **Async support** — our API calls to Groq and Jira are I/O operations, async handles them efficiently
2. **Background tasks** — FastAPI has built-in BackgroundTasks, which we use for regeneration when speaker names are mapped
3. **Auto documentation** — FastAPI generates Swagger UI automatically, helpful for testing

### Q8: Why Svelte instead of React?
**A:** Svelte compiles to vanilla JavaScript at build time. There's no virtual DOM overhead. The bundle size is much smaller. For a project like this where we have 6 pages, Svelte keeps the code simple and fast. Each component is a single `.svelte` file with HTML, CSS, and JS together.

### Q9: Why file-based storage instead of a database?
**A:** For this demo and the current scale, JSON files are the simplest approach:
- Each meeting is a self-contained folder — easy to inspect, debug, copy
- No database server to install or configure
- Every file is human-readable — open any JSON in a text editor
- For production, we'd move to PostgreSQL. The service layer abstraction makes that migration straightforward.

### Q10: Why Groq instead of OpenAI?
**A:** Speed and cost. Groq uses custom hardware called LPU (Language Processing Unit) that runs Llama 3.3 70B with sub-second response times. OpenAI's GPT-4 takes 5-10 seconds for the same task. Groq also has a free tier, so there's no cost during development and demo.

### Q11: How many API endpoints does your backend have?
**A:** 30+ endpoints across 12 routers. They cover upload, transcription, summarization, 10 different AI analysis tasks, RAG chat with streaming, Jira bidirectional sync, publishing to PDF/email/Teams, speaker mapping, search, and dashboard statistics.

---

## 🔹 Section C: AI & ML Questions

### Q12: How does the transcription work?
**A:** We use WhisperX. The audio goes through three stages:
1. **Whisper model** transcribes the speech to text
2. **Forced alignment** (using wav2vec2) aligns each word to its exact timestamp
3. **pyannote.audio** runs speaker diarization — it detects unique voices and assigns labels like SPEAKER_00, SPEAKER_01

The result is a transcript where every sentence has a speaker label and start/end timestamps.

### Q13: How does the AI generate summaries and action items?
**A:** We send the full transcript to Llama 3.3 70B (a large language model with 70 billion parameters) through Groq's API. For each task, we write a specific system prompt:
- For summaries: "Generate a concise meeting summary covering key discussions, decisions, and outcomes"
- For action items: "Extract action items with assigned person, priority, deadline, and context"

The model reads the entire transcript and returns structured JSON with the extracted information. We parse that JSON and save it.

### Q14: What is RAG? How does your chatbot work?
**A:** RAG stands for Retrieval-Augmented Generation. Instead of asking the AI to answer from memory (which can be wrong), we first **retrieve** relevant information from our database, then pass that information to the AI along with the question.

Step by step:
1. When a meeting is indexed, we break the transcript into segments and convert each segment into a number (a vector embedding) using a model called all-MiniLM-L6-v2
2. These vectors are stored in ChromaDB — a vector database
3. When a user asks a question, we convert the question into a vector too
4. We search ChromaDB for the most similar transcript segments
5. We pass those segments + the question to Llama 3.3
6. The AI generates an answer based **only** on the real transcript data
7. The answer streams back to the user in real-time

This way, the AI never makes things up — every answer is grounded in actual meeting content.

### Q15: What is "diverse retrieval"? You mentioned it.
**A:** Normal RAG retrieves the top 10 most similar chunks. But if you've indexed 5 meetings, all 10 chunks might come from the same meeting. That's a problem for cross-meeting questions.

Our diverse retrieval works differently:
1. We fetch 25 candidate chunks from the database
2. We group them by meeting
3. We round-robin: take 1 from Meeting A, 1 from Meeting B, 1 from Meeting C, repeat
4. We stop at 12 diverse chunks

This guarantees every relevant meeting is represented in the answer.

### Q16: What is the embedding model? Why all-MiniLM-L6-v2?
**A:** An embedding model converts text into a list of numbers (a vector) that captures the meaning. Similar sentences produce similar vectors. all-MiniLM-L6-v2 is a popular choice because:
- It's small (80 MB) — runs on CPU, no GPU needed
- It produces 384-dimensional vectors — compact but effective
- It's trained on billions of sentence pairs for semantic similarity
- It's fast — embeds thousands of sentences per second

### Q17: How does speaker diarization work?
**A:** pyannote.audio uses three steps:
1. **Voice Activity Detection (VAD)** — detect where speech exists (filter out silence)
2. **Speaker Embedding** — extract a voice "fingerprint" for each speech segment
3. **Clustering** — group segments with similar fingerprints into speakers

It doesn't know names — it just knows "these segments sound like the same person." That's why we need the Human-in-the-Loop mapping.

### Q18: What is the accuracy of the transcription?
**A:** WhisperX achieves about 92-95% word accuracy for clear English speech. Accuracy drops with:
- Heavy accents
- Background noise
- Multiple people talking at the same time
- Technical jargon not in the training data

For important terms that the AI gets wrong, the user can correct them through the speaker mapping and the summary editing features.

---

## 🔹 Section D: Feature-Specific Questions

### Q19: What happens when I map speaker names? You said "background regeneration."
**A:** When you save speaker names, the API does two things:
1. Returns "200 OK" immediately — you're not waiting
2. Queues 8 tasks to run in the background:
   - Re-index the RAG database with real names
   - Regenerate the summary
   - Re-extract action items
   - Re-extract requirements
   - Regenerate documentation
   - Regenerate follow-up email
   - Re-run sentiment analysis
   - Re-extract topics

Each task uses `force=True` to bypass the cached result and rebuild from scratch with the corrected names. If one task fails, the others still run.

### Q20: How does the Jira integration work? Is it real?
**A:** Yes, it's fully real and bidirectional:

**Push:** When you click "Push to Jira," we call Jira's REST API v3 to create a ticket. The fields are mapped:
- task text → Jira summary
- priority → Jira priority (High/Medium/Low)
- category → Jira issue type (development → Story, testing → Bug, others → Task)
- deadline → Jira due date
- context + criteria → Jira description (in ADF format)
- We add labels: `contextiq` and `category-{type}`

**Sync:** When you click "Sync from Jira," we call `GET /rest/api/3/issue/{key}` for each linked ticket and check if status, priority, or assignee changed. If yes, we update the local data.

**Update:** When you edit an action item in ContextIQ, we push changes back to Jira — field changes via PUT, status changes via the Transitions API.

### Q21: How does the Teams notification work?
**A:** We use Microsoft Teams' Incoming Webhook feature. We send an Adaptive Card (version 1.4) — it's like a rich message with sections:
- Summary snippet
- Top 5 action items
- Top 4 decisions
- Key takeaways
- Speaker highlights

The webhook URL is configured in the `.env` file. No Teams app registration needed — just create an Incoming Webhook connector in any Teams channel.

### Q22: How do you generate the PDF?
**A:** We use fpdf2, a Python library. The challenge was Hindi text — most PDF libraries don't support Hindi characters. We solved this by embedding TrueType fonts:
- NotoSans — for English text
- NotoSansDevanagari — for Hindi text

The PDF includes the meeting title, date, speaker summaries, and the full bilingual summary.

### Q23: What is sentiment analysis? How accurate is it?
**A:** We send each transcript segment to Llama 3.3 and ask it to classify the emotional tone as positive, negative, or neutral, with a confidence score. It helps understand meeting dynamics — was someone frustrated? Was the team excited about a decision?

Accuracy is around 75-80%. It works well for clearly positive or negative statements but struggles with sarcasm, humor, or culturally specific expressions.

### Q24: Can the chatbot answer questions about multiple meetings at once?
**A:** Yes, that's a key feature. You can index multiple meetings, and the chatbot searches across all of them. For example: "What has been decided about the laptop issue across all meetings?" — it will pull relevant segments from every meeting where laptops were discussed and give a combined answer with citations showing which meeting each piece came from.

---

## 🔹 Section E: Design & Architecture Questions

### Q25: What is Human-in-the-Loop and why is it important?
**A:** Human-in-the-Loop means the AI does the heavy work, but a human verifies and corrects it. In ContextIQ:
1. **Speaker mapping** — AI detects speakers, human assigns real names
2. **Summary approval** — AI generates summary, human reviews and edits before publishing

This is important because AI isn't perfect. Speaker detection might merge two people, or the summary might miss a key point. By adding a human check, we get the speed of AI with the accuracy of human judgment.

### Q26: How do you handle errors? What if the Groq API is down?
**A:** Each LLM call has retry logic — 3 attempts with 2-second backoff. If all retries fail, we return a clear error message to the user. The background regeneration tasks are independent — if sentiment analysis fails, action items still regenerate. Every failure is logged with the meeting ID for debugging.

### Q27: Is the data stored securely?
**A:** This is a demo/prototype. Data is stored as plain JSON files on the local machine. For a production version, we would add encryption, access control, and database-level security. The architecture is designed so that swapping the storage layer doesn't require changing the service logic.

### Q28: Why Server-Sent Events (SSE) instead of WebSockets for chat?
**A:** SSE is simpler for our use case. The chat is one-directional streaming — the server sends answer tokens to the client. We don't need bidirectional communication (the user sends a question via a regular POST, not through the stream). SSE works over regular HTTP, needs no special server setup, and reconnects automatically.

### Q29: How does the system handle concurrent users?
**A:** FastAPI with Uvicorn handles async requests well. Multiple users can upload and process different meetings simultaneously because each meeting is in its own directory with its own files. The ChromaDB instance is shared but handles concurrent reads. For production scale, we'd add a task queue (like Celery) for heavy processing.

---

## 🔹 Section F: Business & Impact Questions

### Q30: What is the business value of this?
**A:** Time saved. A 30-minute meeting typically takes 1-2 hours of post-meeting work: writing notes, sending follow-ups, creating Jira tickets, filing requirements. ContextIQ reduces this to 2 minutes — upload and review. For a team that has 5 meetings a day, that's saving 5-10 hours daily across the team.

### Q31: How much does it cost to run?
**A:** Very low:
- Groq API has a free tier (14,000 tokens/minute) — enough for demos and small teams
- Hosting is just a Python server + a Node.js dev server
- No database server costs
- The only paid service we used is AssemblyAI for cloud transcription, and even that has a free tier
- Total cost for a small team: effectively $0

### Q32: Can this scale to an enterprise?
**A:** The current demo uses file storage and single-server architecture. For enterprise:
- Replace JSON files with PostgreSQL
- Add authentication (OAuth2/JWT)
- Use a task queue (Celery/Redis) for processing
- Deploy on Kubernetes for horizontal scaling
- The service-layer architecture makes these changes straightforward without rewriting business logic

### Q33: What if the meeting is 2 hours long?
**A:** The system handles any length. A 2-hour meeting takes longer to transcribe (~4 minutes with Groq, ~8 minutes with WhisperX on GPU) and generates more data, but all the AI analysis tasks work the same way. The LLM prompt includes the full transcript — Llama 3.3 has a 128K token context window, which can hold transcripts for meetings up to 4-5 hours.

---

## 🔹 Section G: Edge Case Questions

### Q34: What if two people are talking at the same time?
**A:** The diarization model (pyannote) handles some overlap but accuracy drops. In overlapping speech, it typically assigns the segment to the louder or clearer speaker. WhisperX might also miss words during heavy overlap. This is a known limitation of current diarization technology.

### Q35: What if the audio quality is bad?
**A:** Whisper is trained on noisy audio and handles moderate background noise well. For very poor quality, AssemblyAI's cloud engine tends to perform better because it was specifically trained on business meeting audio (phone calls, conference rooms). Users can switch engines based on audio quality.

### Q36: What if the AI extracts wrong action items?
**A:** The user reviews action items before pushing to Jira. They can edit any field — task, assignee, priority, deadline. The AI gives you a starting point; the human makes the final call. That's the Human-in-the-Loop approach.

### Q37: What if someone joins the meeting late?
**A:** The diarization will detect them as a new speaker. Their segments will appear from the time they start speaking. Topic segmentation will correctly show which topics they participated in and which they missed.

---

# PART 2: TECHNICAL TERM DEFINITIONS

---

## 🧠 AI & Machine Learning Terms

### 1. LLM (Large Language Model)
**What it is:** A neural network trained on massive amounts of text (books, websites, code) that can understand and generate human language.

**How it works:** The model learns patterns in text — grammar, facts, reasoning — by predicting the next word billions of times during training. After training, it can answer questions, write summaries, translate languages, and extract information.

**In ContextIQ:** We use Llama 3.3 70B (70 billion parameters) for all text analysis: summaries, action items, requirements, sentiment, and the chatbot.

**Simple analogy:** Imagine someone who has read every book, article, and conversation ever written. You can ask them to summarize a meeting, and they'll do it based on patterns they learned.

---

### 2. Transformer Architecture
**What it is:** The fundamental architecture behind all modern LLMs (GPT, Llama, Claude, Gemini).

**How it works:** The key innovation is the **attention mechanism** — when processing a sentence, the model looks at ALL words simultaneously and figures out which words relate to which. Traditional models read left-to-right; transformers see everything at once.

A transformer has:
- **Encoder** — reads and understands input text
- **Decoder** — generates output text
- **Self-attention layers** — each word "attends" to every other word to understand context
- **Feed-forward layers** — process the attention output to make decisions

**Why it matters:** Before transformers (pre-2017), language models were slow and couldn't handle long text. Transformers can process entire documents in parallel, making them fast and accurate.

**In ContextIQ:** WhisperX uses a transformer encoder-decoder for speech recognition. Llama 3.3 uses a decoder-only transformer for text generation.

---

### 3. Parameters (70B means 70 Billion Parameters)
**What it is:** Parameters are the numbers inside a neural network that get adjusted during training. They represent learned knowledge.

**Simple analogy:** Think of parameters as the "brain cells" of the model. More parameters = more capacity to store knowledge and handle complex tasks. A 70B model has 70 billion adjustable numbers.

**Scale comparison:**
- GPT-2 (2019): 1.5 billion
- Llama 3.3 (2024): 70 billion
- GPT-4 (2023): estimated 1.7 trillion

---

### 4. Token
**What it is:** The basic unit of text that an LLM processes. Not exactly a word — more like a word piece.

**Examples:**
- "meeting" = 1 token
- "unbelievable" = 2 tokens ("un" + "believable")
- "123456" = multiple tokens

**Rule of thumb:** 1 token ≈ 4 characters, or about 0.75 words. So 1000 tokens ≈ 750 words.

**Why it matters:** LLMs have a **context window** — the maximum number of tokens they can process at once. Llama 3.3 has 128K tokens (~96,000 words), which is enough for a 4-5 hour meeting transcript.

---

### 5. Prompt Engineering
**What it is:** Writing specific instructions for the LLM to get the output you want.

**In ContextIQ:** Each AI task has a carefully written system prompt. For example, the action item extraction prompt says:
> "From the transcript, extract all action items. For each, include: task description, assigned person, priority (high/medium/low), category, deadline, context, success criteria, and dependencies. Return as JSON."

The quality of the output depends heavily on how well the prompt is written. We spent significant time refining prompts for each task.

---

### 6. Inference
**What it is:** Running a trained model to get predictions/outputs. The "using" phase (as opposed to training phase).

**In ContextIQ:** Every time we call Groq's API to generate a summary, that's inference. The model is already trained — we're just using it.

**Groq's LPU:** Groq built custom hardware (Language Processing Unit) that runs inference extremely fast — sub-second for 70B models, compared to 5-10 seconds on GPU.

---

### 7. Fine-Tuning vs Prompt Engineering
**What it is:**
- **Fine-tuning** = retraining the model on your specific data (expensive, needs GPU, takes hours)
- **Prompt engineering** = writing better instructions for the model (free, instant, no training)

**In ContextIQ:** We use prompt engineering, not fine-tuning. We don't retrain Llama — we just write detailed prompts that tell it exactly what format and content we want. This is faster, cheaper, and easier to modify.

---

## 🗣️ Speech & Audio Terms

### 8. ASR (Automatic Speech Recognition) / STT (Speech-to-Text)
**What it is:** Technology that converts spoken audio into written text.

**How Whisper does it:**
1. Audio is converted to a **spectrogram** (visual representation of sound frequencies)
2. The spectrogram is processed by a transformer encoder
3. The decoder generates text token by token

**In ContextIQ:** WhisperX is our primary STT engine. It's OpenAI's open-source model extended with forced alignment for precise timestamps.

---

### 9. Speaker Diarization
**What it is:** Figuring out "who spoke when" in an audio recording.

**How pyannote.audio does it:**
1. **Voice Activity Detection (VAD)** — find where speech exists (ignore silence, music, noise)
2. **Speaker Embedding Extraction** — create a voice "fingerprint" for each speech segment using a neural network
3. **Clustering** — group segments with similar fingerprints. All segments in one cluster = one speaker

**Output:** Timestamps with speaker labels — "SPEAKER_00 spoke from 12.5s to 18.3s"

**Limitation:** It doesn't know names. It only knows "same voice / different voice."

---

### 10. Forced Alignment
**What it is:** Matching each word in the transcript to its exact position in the audio.

**Why it matters:** Basic Whisper gives you segment-level timestamps (e.g., "this sentence is from 10s to 15s"). Forced alignment (using wav2vec2 model) gives you word-level timestamps (e.g., "meeting" is at 12.4s, "tomorrow" is at 12.8s).

**In ContextIQ:** WhisperX uses this for precise timestamps in the transcript.

---

### 11. Spectrogram
**What it is:** A visual representation of audio showing frequency content over time. The x-axis is time, y-axis is frequency, and color/brightness represents intensity.

**Why it matters:** Neural networks can't directly process audio waves. They convert audio to a spectrogram (specifically a mel-spectrogram) and process it like an image. Whisper's encoder processes mel-spectrograms.

---

## 🔍 RAG & Vector Database Terms

### 12. RAG (Retrieval-Augmented Generation)
**What it is:** A technique that combines search (retrieval) with AI generation. Instead of asking the AI to answer from memory, you first search for relevant information and pass it to the AI.

**Why it exists:** LLMs can "hallucinate" — make up facts. RAG prevents this by grounding the AI's answers in real data.

**Step by step in ContextIQ:**
1. User asks: "What did Babu say about laptops?"
2. We search ChromaDB for transcript segments about "laptops" and "Babu"
3. We find relevant segments from the actual meetings
4. We give those segments + the question to Llama 3.3
5. The AI generates an answer using ONLY the provided segments
6. The answer includes citations with speaker names and timestamps

---

### 13. Vector Embedding
**What it is:** Converting text into a list of numbers (a vector) that captures the meaning.

**Example:**
- "The meeting went well" → [0.23, -0.45, 0.87, ..., 0.12] (384 numbers)
- "The discussion was productive" → [0.25, -0.41, 0.85, ..., 0.14] (similar numbers because similar meaning)
- "I like pizza" → [0.91, 0.32, -0.56, ..., -0.78] (very different numbers)

**Why it works:** Similar meanings create similar vectors. We can then find related text by comparing vectors mathematically (cosine similarity).

---

### 14. Vector Database (ChromaDB)
**What it is:** A database optimized for storing and searching vector embeddings. Regular databases search by exact text match. Vector databases search by meaning similarity.

**How ChromaDB works:**
1. Store documents with their vector embeddings
2. When querying, convert the question to a vector
3. Find stored vectors closest to the question vector
4. Return the original documents

**In ContextIQ:** Each transcript segment is stored as a document in ChromaDB with its embedding + metadata (meeting_id, speaker, timestamp).

---

### 15. Cosine Similarity
**What it is:** A mathematical way to measure how similar two vectors are. Returns a value between -1 (opposite) and 1 (identical).

**How it works:** Calculates the cosine of the angle between two vectors. If they point in the same direction → similar meaning (close to 1). If perpendicular → unrelated (0). If opposite → opposite meaning (-1).

**In ContextIQ:** ChromaDB uses cosine similarity to find transcript segments most relevant to the user's question.

---

### 16. Chunking
**What it is:** Breaking a large document into smaller pieces for embedding and retrieval.

**In ContextIQ:** We chunk by **speaker segment** — each time a different person speaks, that's one chunk. This is better than fixed-size chunking because:
- Each chunk has a clear speaker attribution
- The boundaries are natural conversation breaks
- Metadata (speaker, timestamp) is accurate per chunk

---

### 17. SSE (Server-Sent Events)
**What it is:** A protocol where the server sends a continuous stream of data to the browser over a single HTTP connection.

**In ContextIQ:** The chatbot answer streams word-by-word via SSE. The user sees the answer being typed out in real-time, instead of waiting for the entire response.

**How it differs from WebSocket:** SSE is one-directional (server → client). WebSocket is bidirectional. SSE is simpler and sufficient for our use case.

---

## 🔧 Backend & API Terms

### 18. REST API
**What it is:** A way for the frontend to communicate with the backend using standard HTTP methods:
- **GET** = read data
- **POST** = create/process data
- **PUT** = update data
- **DELETE** = remove data

**In ContextIQ:** `POST /meeting/{id}/action-items` tells the backend to extract action items for a specific meeting. The response is JSON with the extracted data.

---

### 19. ASGI (Asynchronous Server Gateway Interface)
**What it is:** A protocol for Python web servers that supports async operations. Uvicorn is an ASGI server.

**Why it matters:** When ContextIQ calls Groq's API, it's waiting for a network response. With async, the server doesn't block — it can handle other requests while waiting. This makes the server more efficient.

---

### 20. Background Tasks (FastAPI)
**What it is:** Tasks that run after the API has already sent a response to the user.

**In ContextIQ:** When speaker names are saved, the API returns "200 OK" immediately. Then 8 regeneration tasks run in the background. The user isn't waiting — they can continue using the app while the background tasks process.

---

### 21. Pydantic Validation
**What it is:** Automatic checking that API request data matches the expected format.

**Example:** If an endpoint expects `{"indices": [0, 1, 2]}` and someone sends `{"indices": "hello"}`, Pydantic automatically rejects it with a clear error message. No manual validation code needed.

---

## 🎫 Integration Terms

### 22. Jira REST API v3
**What it is:** Jira's official API for creating, reading, updating tickets programmatically.

**Key operations in ContextIQ:**
- `POST /rest/api/3/issue` — create a ticket
- `PUT /rest/api/3/issue/{key}` — update fields (summary, priority, due date)
- `GET /rest/api/3/issue/{key}/transitions` — get available status changes
- `POST /rest/api/3/issue/{key}/transitions` — change ticket status

**ADF (Atlassian Document Format):** Jira v3 doesn't accept plain text for descriptions. It requires JSON in ADF format — a structured document with paragraphs, text nodes, and formatting.

---

### 23. Adaptive Cards (MS Teams)
**What it is:** A JSON-based card format used by Microsoft Teams for rich notifications. Like a mini web page in a chat message.

**In ContextIQ:** Our Teams notification is an Adaptive Card v1.4 with columns, sections, facts, and formatted text — showing summary, action items, decisions, and speaker highlights in a professional layout.

---

### 24. Webhook
**What it is:** A URL that receives HTTP POST requests. Instead of polling "Is there new data?", you push data TO the webhook when something happens.

**In ContextIQ:** Teams Incoming Webhook — we POST our Adaptive Card JSON to the webhook URL, and Teams displays it in the channel.

---

### 25. SMTP (Simple Mail Transfer Protocol)
**What it is:** The protocol for sending emails. We use Python's built-in `smtplib` to connect to Gmail's SMTP server and send emails with PDF attachments.

**Gmail App Password:** Gmail doesn't allow regular password login for SMTP. You generate a special "App Password" in your Google account settings.

---

## 📦 Frontend Terms

### 26. SPA (Single Page Application)
**What it is:** A web application that loads once and then updates content dynamically without full page reloads. Only one HTML page is ever loaded — JavaScript handles all the routing.

**In ContextIQ:** Svelte compiles everything into a single bundle. Navigation between Dashboard, Meeting Detail, Chat, etc. happens without page reloads.

---

### 27. Reactive Declarations (Svelte)
**What it is:** A Svelte feature where variables automatically update the UI when their value changes. No `setState()` or `useEffect()` like React.

**Example:** `$: totalItems = actionItems.length` — whenever `actionItems` changes, `totalItems` is recalculated and the UI updates automatically.

---

### 28. Hash-based Routing
**What it is:** Using the URL hash (`#`) for navigation. Example: `http://localhost:5173/#/meeting/abc123`

**Why:** The `#` part is never sent to the server. This means any URL works without server-side routing configuration. It's the simplest way to deploy an SPA.

---

## 🔑 Quick Reference Table

| Term | One-Line Definition |
|---|---|
| LLM | AI model trained on text that can understand and generate language |
| Transformer | Neural network architecture that processes all words simultaneously using attention |
| RAG | Search for relevant data first, then ask AI to generate an answer from it |
| Embedding | Converting text into numbers that capture meaning |
| Vector Database | Database that searches by meaning similarity, not exact text match |
| Diarization | Detecting "who spoke when" in audio |
| ASR/STT | Converting speech to text |
| Forced Alignment | Matching each word to its exact position in audio |
| Token | The basic text unit an LLM processes (~0.75 words) |
| Inference | Running a trained model to get predictions |
| Fine-tuning | Retraining a model on specific data |
| Prompt Engineering | Writing instructions to get better AI output |
| ASGI | Async Python server protocol |
| SSE | Server streams data to browser continuously |
| REST API | Standard HTTP-based communication (GET/POST/PUT/DELETE) |
| Webhook | URL that receives push notifications |
| SMTP | Email sending protocol |
| ADF | Jira's structured document format for descriptions |
| Adaptive Card | Rich notification format for MS Teams |
| Cosine Similarity | Mathematical measure of how similar two vectors are |
| SPA | Web app that loads once, updates without page reloads |
| HITL | Human-in-the-Loop — AI does work, human verifies and corrects |
| LPU | Groq's custom chip for fast AI inference |

---

## 💡 Pro Tips for Q&A

1. **If you don't know an answer:** "That's an interesting question. In the current version we haven't addressed that, but for production we would..."
2. **If they ask about security:** "This is a demo prototype focused on functionality. For production, we would add OAuth2 authentication, encrypted storage, and role-based access control."
3. **If they ask about competitors:** "We focused on building a complete end-to-end solution rather than comparing with existing tools. Our strength is the full pipeline — from recording to Jira tickets — in one platform."
4. **Keep answers to 30-60 seconds each.** Don't ramble. State the answer, give one example, stop.
5. **Use simple analogies.** RAG = "giving the AI a cheat sheet before the exam." Embeddings = "converting text into coordinates on a map."
