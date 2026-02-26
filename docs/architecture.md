# ContextIQ — System Architecture

## 1. High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["🖥️ Frontend — Svelte + Vite :5173"]
        Home["Home.svelte<br/>Landing Page"]
        Dash["Dashboard.svelte<br/>Stats + Upload"]
        MD["MeetingDetail.svelte<br/>Transcript + Analytics"]
        AI["ActionItems.svelte<br/>Tasks + Follow-up Email"]
        Chat["Chat.svelte<br/>RAG Q&A"]
        Search["Search.svelte<br/>Keyword Search"]
    end

    subgraph Backend["⚙️ Backend — FastAPI + Uvicorn :8000"]
        direction TB
        subgraph APIs["API Layer (12 Routers)"]
            upload["POST /upload-video"]
            transcribe["POST /transcribe/{id}"]
            summarize["POST /summarize/{id}"]
            insights["POST /meeting/{id}/action-items<br/>POST /meeting/{id}/requirements<br/>POST /meeting/{id}/documentation<br/>POST /meeting/{id}/sentiment<br/>POST /meeting/{id}/topics<br/>POST /meeting/{id}/followup-email"]
            publish["POST /publish/{id}"]
            chat_api["POST /chat/ask/stream<br/>POST /chat/index/{id}"]
            jira_api["POST /meeting/{id}/jira/push<br/>POST /meeting/{id}/jira/sync"]
            speaker["POST /meeting/{id}/speaker-map"]
            stats_api["GET /stats<br/>GET /meetings"]
            search_api["GET /search"]
            diarize["GET /meeting/{id}"]
        end

        subgraph Services["Service Layer"]
            stt["stt_service.py<br/>WhisperX + AssemblyAI + Groq"]
            v2a["video_to_audio.py<br/>FFmpeg Converter"]
            spk["speaker_service.py<br/>Speaker Grouping"]
            store["storage_service.py<br/>File I/O"]
            summary_svc["summary_service.py<br/>Groq LLM Summaries"]
            insights_svc["insights_service.py<br/>Action Items, Decisions,<br/>Requirements, Docs, Sentiment,<br/>Topics, Title, Follow-up Email"]
            pub["publish_service.py<br/>PDF + Email + Teams"]
            rag["rag_service.py<br/>ChromaDB + LangChain"]
            jira_svc["jira_service.py<br/>REST API v3"]
        end
    end

    subgraph External["☁️ External Services"]
        Groq["Groq API<br/>Llama 3.3 70B"]
        ADB["AssemblyAI API"]
        Jira["Jira Cloud<br/>REST API v3"]
        SMTP["SMTP Server<br/>Gmail"]
        Teams["Teams Webhook"]
    end

    subgraph Storage["💾 Storage Layer"]
        FS["File System<br/>storage/{meeting_id}/*.json"]
        Chroma["ChromaDB<br/>storage/chroma_db/"]
        Audio["data/audio/{id}.wav"]
        Video["data/videos/{id}.*"]
    end

    Frontend -->|HTTP REST| APIs
    APIs --> Services
    Services --> External
    Services --> Storage
```

---

## 2. Data Flow — End-to-End Meeting Pipeline

```mermaid
flowchart LR
    A["📹 Upload Video"] --> B["🔊 Extract Audio<br/>FFmpeg → WAV 16kHz"]
    B --> C["🗣️ Transcribe + Diarize<br/>WhisperX / AssemblyAI"]
    C --> D["💾 Save transcript.json"]
    D --> E["🏷️ Auto-Generate Title<br/>Groq LLM"]

    D --> F["🔍 Auto-Index RAG<br/>ChromaDB"]

    D --> G["👤 Speaker Map<br/>HITL Name Mapping"]
    G -->|"Background Tasks"| H["🔄 Regenerate ALL<br/>with real names"]

    H --> I["📝 Summary EN+HI"]
    H --> J["✅ Action Items"]
    H --> K["📋 Requirements"]
    H --> L["📄 Documentation"]
    H --> M["💌 Follow-up Email"]
    H --> N["😊 Sentiment"]
    H --> O["📌 Topics"]
    H --> F

    J --> P["🎫 Jira Sync<br/>Bidirectional"]
    I --> Q["📤 Publish<br/>PDF + Email + Teams"]
    F --> R["💬 AI Chat<br/>RAG Q&A"]

    style G fill:#ffd700,stroke:#333
    style H fill:#ff6b6b,stroke:#333
    style P fill:#0052CC,stroke:#333
    style R fill:#10b981,stroke:#333
```

---

## 3. File Storage Structure

```
storage/
├── {meeting_id}/
│   ├── transcript.json        ← segments + speakers
│   ├── metadata.json          ← title, dates, counts
│   ├── speaker_map.json       ← HITL name mapping
│   ├── summary.json           ← EN + HI summaries
│   ├── action_items.json      ← tasks, decisions, takeaways
│   ├── requirements.json      ← functional/non-functional reqs
│   ├── documentation.json     ← MoM, agenda, next steps
│   ├── sentiment.json         ← per-segment sentiment scores
│   ├── topics.json            ← topic segments with time ranges
│   ├── followup_email.json    ← generated email draft
│   ├── speaker_report.json    ← per-speaker scorecards
│   ├── Meeting_Summary.pdf    ← generated PDF
│   └── Full_Report.pdf        ← comprehensive report
├── chroma_db/                 ← ChromaDB vector store
│
data/
├── audio/{meeting_id}.wav     ← extracted audio (16kHz mono)
└── videos/{meeting_id}.*      ← uploaded video files
```

---

## 4. API Endpoint Map

```mermaid
graph LR
    subgraph Upload["📹 Upload & Transcribe"]
        A1["POST /upload-video"]
        A2["POST /transcribe/{id}"]
    end

    subgraph Insights["🧠 AI Insights (Groq LLM)"]
        B1["POST /summarize/{id}"]
        B2["POST /meeting/{id}/action-items"]
        B3["POST /meeting/{id}/requirements"]
        B4["POST /meeting/{id}/documentation"]
        B5["POST /meeting/{id}/sentiment"]
        B6["POST /meeting/{id}/topics"]
        B7["POST /meeting/{id}/followup-email"]
        B8["POST /meeting/{id}/title"]
        B9["POST /meeting/{id}/speaker-report"]
        B10["POST /meeting/{id}/culture-score"]
    end

    subgraph Publish["📤 Publish"]
        C1["POST /publish/{id}"]
        C2["POST /meeting/{id}/followup-email/send"]
        C3["GET /meeting/{id}/report"]
    end

    subgraph Chat["💬 RAG Chat"]
        D1["POST /chat/ask/stream"]
        D2["POST /chat/index/{id}"]
        D3["GET /chat/meetings"]
    end

    subgraph Jira["🎫 Jira"]
        E1["POST /meeting/{id}/jira/push"]
        E2["POST /meeting/{id}/jira/sync"]
        E3["PUT /meeting/{id}/jira/update"]
        E4["GET /jira/status"]
    end

    subgraph Data["📊 Data"]
        F1["GET /meetings"]
        F2["GET /meeting/{id}"]
        F3["GET /meeting/{id}/metadata"]
        F4["GET /stats"]
        F5["GET /search"]
        F6["POST /meeting/{id}/speaker-map"]
    end
```

---

## 5. Speaker Map → Background Regeneration Workflow

```mermaid
sequenceDiagram
    actor User
    participant UI as Frontend
    participant API as speaker_map.py
    participant BG as Background Tasks
    participant LLM as Groq LLM
    participant DB as ChromaDB

    User->>UI: Save speaker names
    UI->>API: POST /meeting/{id}/speaker-map
    API->>API: Save speaker_map.json
    API-->>UI: 200 OK (instant)
    API->>BG: Queue regeneration

    Note over BG: Runs sequentially in background

    BG->>DB: 1. Re-index RAG with real names
    BG->>LLM: 2. Regenerate Summary (force=true)
    BG->>LLM: 3. Re-extract Action Items
    BG->>LLM: 4. Re-extract Requirements
    BG->>LLM: 5. Regenerate Documentation
    BG->>LLM: 6. Regenerate Follow-up Email
    BG->>LLM: 7. Re-run Sentiment Analysis
    BG->>LLM: 8. Re-extract Topics

    Note over BG: All cached JSONs now have real speaker names
```

---

## 6. Jira Bidirectional Sync Workflow

```mermaid
sequenceDiagram
    actor User
    participant CIQ as ContextIQ
    participant Jira as Jira Cloud

    Note over User,Jira: Push: ContextIQ → Jira
    User->>CIQ: Click "Push to Jira" on action item
    CIQ->>Jira: POST /rest/api/3/issue (create)
    Jira-->>CIQ: Returns ticket key (SCRUM-12)
    CIQ->>CIQ: Save jira_id + jira_url in action_items.json

    Note over User,Jira: Sync: Jira → ContextIQ
    User->>CIQ: Click "Sync from Jira"
    CIQ->>Jira: GET /rest/api/3/issue/{key} (for each linked item)
    Jira-->>CIQ: Returns status, priority, assignee
    CIQ->>CIQ: Update action_items.json with Jira values

    Note over User,Jira: Update: ContextIQ → Jira
    User->>CIQ: Edit action item (status/priority)
    CIQ->>Jira: PUT /rest/api/3/issue/{key} (fields)
    CIQ->>Jira: POST /rest/api/3/issue/{key}/transitions (status)
```

---

## 7. Publish Pipeline

```mermaid
flowchart TD
    A["POST /publish/{id}"] --> B["Load summary.json"]
    B --> C["Generate PDF<br/>fpdf2 + Unicode fonts"]
    C --> D{Email recipients?}
    D -->|Yes| E["Send via SMTP<br/>PDF attached"]
    D -->|No| F["Skip email"]
    C --> G{Teams webhook?}
    G -->|Yes| H["Send Rich Adaptive Card<br/>Summary + Action Items +<br/>Decisions + Speakers"]
    G -->|No| I["Skip Teams"]
    E --> J["Return result"]
    F --> J
    H --> J
    I --> J
```

---

## 8. Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Svelte 4 + Vite + lucide-svelte |
| **Backend** | FastAPI + Uvicorn (Python 3.10) |
| **STT Engine** | WhisperX (local) + AssemblyAI + Groq Whisper |
| **Diarization** | pyannote.audio 3.x |
| **LLM** | Groq API → Llama 3.3 70B Versatile |
| **RAG** | LangChain + ChromaDB + all-MiniLM-L6-v2 |
| **PDF** | fpdf2 with NotoSans + NotoSansDevanagari |
| **Email** | smtplib (SMTP/TLS) |
| **Teams** | Incoming Webhook (Adaptive Cards v1.4) |
| **Jira** | REST API v3 (Basic Auth) |
| **Audio** | FFmpeg (video → WAV 16kHz mono) |
| **Storage** | File-system JSON + ChromaDB (SQLite) |

---

## 9. Frontend Routing

| Route | Page | Purpose |
|---|---|---|
| `/` | Home.svelte | Landing page |
| `/dashboard` | Dashboard.svelte | Upload + stats + meeting list |
| `/meeting/:id` | MeetingDetail.svelte | Transcript + all analytics |
| `/meeting/:id/actions` | ActionItems.svelte | Tasks + Jira + follow-up email |
| `/chat` | Chat.svelte | RAG chatbot |
| `/search` | Search.svelte | Keyword search |

---

## 10. Entity Relationship — Data Model

```mermaid
erDiagram
    MEETING ||--o{ SEGMENT : "has many"
    MEETING ||--o| METADATA : "has one"
    MEETING ||--o| SPEAKER_MAP : "has one"
    MEETING ||--o| SUMMARY : "has one"
    MEETING ||--o| ACTION_ITEMS : "has one"
    MEETING ||--o| REQUIREMENTS : "has one"
    MEETING ||--o| DOCUMENTATION : "has one"
    MEETING ||--o| SENTIMENT : "has one"
    MEETING ||--o| TOPICS : "has one"
    MEETING ||--o| FOLLOWUP_EMAIL : "has one"
    MEETING ||--o| SPEAKER_REPORT : "has one"
    ACTION_ITEMS ||--o{ JIRA_TICKET : "links to"

    MEETING {
        string meeting_id PK
        string audio_path
    }
    SEGMENT {
        string speaker
        string text
        float start
        float end
    }
    METADATA {
        string auto_title
        string status
        string processed_at
        int segment_count
        int speaker_count
    }
    SPEAKER_MAP {
        string SPEAKER_00 "Real Name"
        string SPEAKER_01 "Real Name"
    }
    SUMMARY {
        string overall_summary_en
        string overall_summary_hi
        object speaker_summaries_en
    }
    ACTION_ITEMS {
        array action_items
        array decisions
        array key_takeaways
        array follow_ups
    }
    JIRA_TICKET {
        string jira_id
        string jira_url
        string status
        string priority
    }
```

---

## 11. Meeting Lifecycle — State Diagram

```mermaid
stateDiagram-v2
    [*] --> Uploaded: POST /upload-video
    Uploaded --> Transcribing: POST /transcribe/{id}
    Transcribing --> Transcribed: WhisperX complete
    Transcribed --> TitleGenerated: Auto-title (background)
    TitleGenerated --> RAGIndexed: Auto-index (background)

    RAGIndexed --> SpeakersMapped: User maps names (HITL)
    SpeakersMapped --> Regenerating: Background regeneration

    Regenerating --> SummaryReady: Summary generated
    SummaryReady --> InsightsReady: Action items + requirements + docs

    InsightsReady --> Published: PDF + Email + Teams
    InsightsReady --> JiraSynced: Push to Jira

    state InsightsReady {
        [*] --> ActionItems
        [*] --> Requirements
        [*] --> Documentation
        [*] --> Sentiment
        [*] --> Topics
        [*] --> FollowupEmail
    }

    Published --> [*]
    JiraSynced --> BidirectionalSync: Sync from Jira
    BidirectionalSync --> JiraSynced
```

---

## 12. User Journey — Complete Workflow

```mermaid
flowchart TD
    A["🎬 User uploads video"] --> B["⏳ Processing<br/>Audio extraction + Transcription"]
    B --> C["📜 View Transcript<br/>Chat / Speaker / Timeline views"]
    C --> D["👤 Map Speaker Names<br/>HITL: SPEAKER_00 → Babu JI"]
    D --> E["🔄 Auto-Regeneration<br/>8 tasks in background"]
    E --> F{"Choose Action"}

    F --> G["📝 View Summary<br/>English + Hindi"]
    F --> H["✅ View Action Items<br/>Review tasks + decisions"]
    F --> I["💬 Chat with AI<br/>Ask questions about meetings"]
    F --> J["📊 View Analytics<br/>Speaker stats + sentiment"]

    H --> K{"Push to Jira?"}
    K -->|Yes| L["🎫 Create Jira Tickets<br/>Auto-mapped fields"]
    K -->|No| M["Continue"]

    L --> N["🔄 Bidirectional Sync<br/>Status stays in sync"]

    G --> O{"Publish?"}
    O -->|PDF| P["📄 Download PDF"]
    O -->|Email| Q["📧 Send via SMTP"]
    O -->|Teams| R["💬 Rich Adaptive Card"]
    O -->|Follow-up| S["💌 Follow-up Email"]

    I --> T["📚 Cross-meeting Q&A<br/>RAG with citations"]

    style D fill:#ffd700,stroke:#333
    style E fill:#ff6b6b,stroke:#333
    style L fill:#0052CC,stroke:#333
    style T fill:#10b981,stroke:#333
```

---

## 13. Service Class Diagram

```mermaid
classDiagram
    class VideoAudioConverter {
        -ffmpeg_path: str
        +video_to_audio(video_path, audio_path)
    }

    class AudioTranscriptionService {
        -engine: str
        -groq_client: Groq
        -assembly_client: AssemblyAI
        +transcribe(audio_path) dict
        -_whisperx_transcribe()
        -_assemblyai_transcribe()
        -_groq_transcribe()
    }

    class SpeakerTranscriptBuilder {
        +build(segments) dict
    }

    class MeetingSummaryService {
        -client: Groq
        +summarize(meeting_id, force, extra_prompt) dict
        -_load_speaker_map(meeting_id) dict
        -_build_conversation_text(segments) str
        -_call_llm(system, user) str
        -_generate_speaker_summaries() dict
        -_generate_overall_summary_en() str
        -_generate_overall_summary_hi() str
    }

    class MeetingInsightsService {
        -client: Groq
        +extract_action_items(meeting_id, force) dict
        +generate_title(meeting_id, force) dict
        +generate_followup_email(meeting_id, force) dict
        +extract_requirements(meeting_id, force) dict
        +generate_documentation(meeting_id, force) dict
        +analyze_sentiment(meeting_id, force) dict
        +extract_topics(meeting_id, force) dict
        -_call_llm(system, user) str
        -_load_transcript_text(meeting_id) tuple
    }

    class MeetingRAGService {
        -_embeddings: HuggingFaceEmbeddings
        -_vectorstore: Chroma
        -_memories: dict
        +ingest_meeting(meeting_id) int
        +query(question, session_id, meeting_ids) dict
        +query_stream(question, session_id) generator
        +list_indexed_meetings() list
        -_diverse_retrieve(question) list
        -_rebuild_index()
    }

    class MeetingPublishService {
        +generate_pdf(summary_data, output_path) str
        +send_email(pdf_path, title, recipients) dict
        +send_to_teams(summary_data, title, meeting_id) dict
        +publish(meeting_id) dict
        +generate_full_report(meeting_id) str
    }

    class JiraService {
        +create_ticket(action_item, title) dict
        +create_tickets_batch(items, title) dict
        +update_ticket(ticket_key, item) dict
        +fetch_ticket_status(ticket_key) dict
        +sync_tickets(items) dict
    }

    AudioTranscriptionService --> VideoAudioConverter : uses
    AudioTranscriptionService --> SpeakerTranscriptBuilder : uses
    MeetingSummaryService --> MeetingInsightsService : same Groq client
    MeetingPublishService --> MeetingSummaryService : reads summary
    MeetingRAGService --> MeetingInsightsService : indexes insights
```

---

## 14. Feature Mind Map

```mermaid
mindmap
  root((ContextIQ))
    🎙️ Ingestion
      Video Upload
      Audio Extraction FFmpeg
      Multi-Engine STT
        WhisperX Local
        AssemblyAI Cloud
        Groq Whisper
      Speaker Diarization pyannote
    🧠 AI Analytics
      Bilingual Summary EN+HI
      Action Items + Decisions
      Requirements Extraction
      Meeting Documentation
      Sentiment Analysis
      Topic Segmentation
      Auto Title Generation
      Follow-up Email Draft
      Speaker Report Cards
      Culture Score
    👤 Human-in-the-Loop
      Speaker Name Mapping
      Summary Review + Approval
      Auto Background Regeneration
    📤 Publishing
      PDF Report Generation
      Email with Attachment
      Teams Rich Adaptive Card
      Follow-up Email SMTP
    🎫 Integrations
      Jira Bidirectional Sync
        Push Action Items
        Sync Status Back
        Update Tickets
    💬 AI Chat
      RAG over Transcripts
      SSE Streaming
      Cross-Meeting Q and A
      Citations with Timestamps
      Conversation Memory
    🔍 Search
      Keyword Search
      Full-Text Transcript Search
```

