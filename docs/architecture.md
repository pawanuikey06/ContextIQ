# ContextIQ — System Architecture

## 1. High-Level Architecture

```mermaid
graph TB
    subgraph Frontend["🖥️ Frontend — Svelte 5 + Vite :5173"]
        Home["Home.svelte<br/>Landing Page"]
        Dash["Dashboard.svelte<br/>Stats + Upload + Culture Score"]
        MD["MeetingDetail.svelte<br/>Transcript + All Analytics"]
        AI["ActionItems.svelte<br/>Tasks + Follow-up Email"]
        Chat["Chat.svelte<br/>RAG Q&A"]
        Search["Search.svelte<br/>Keyword Search"]
    end

    subgraph Backend["⚙️ Backend — FastAPI + Uvicorn :8000"]
        direction TB
        subgraph APIs["API Layer (14 Routers, 35+ Endpoints)"]
            upload["POST /upload-video"]
            transcribe["POST /transcribe/{id}"]
            summarize["POST /summarize/{id}"]
            insights["POST /meeting/{id}/action-items<br/>POST /meeting/{id}/requirements<br/>POST /meeting/{id}/documentation<br/>POST /meeting/{id}/sentiment<br/>POST /meeting/{id}/topics<br/>POST /meeting/{id}/followup-email<br/>POST /meeting/{id}/auto-title"]
            publish["POST /publish/{id}<br/>GET /publish/{id}/pdf<br/>GET /publish/{id}/full-report"]
            chat_api["POST /chat/ask/stream<br/>POST /chat/index/{id}"]
            jira_api["POST /meeting/{id}/jira/push<br/>POST /meeting/{id}/jira/sync"]
            voice_api["GET /meeting/{id}/speaker-clips<br/>POST /meeting/{id}/speaker-profiles<br/>POST /meeting/{id}/voice-match"]
            speaker["POST /meeting/{id}/speaker-map"]
            stats_api["GET /stats<br/>GET /stats/culture-score<br/>GET /meetings"]
            search_api["GET /search"]
            diarize["GET /meeting/{id}<br/>GET /meeting/{id}/video"]
            notion_api["POST /meeting/{id}/notion/push"]
            confluence_api["POST /meeting/{id}/confluence/push"]
        end

        subgraph Services["Service Layer"]
            stt["stt_service.py<br/>WhisperX + AssemblyAI + Groq"]
            v2a["video_to_audio.py<br/>FFmpeg Converter"]
            voice_svc["voice_embedding_service.py<br/>ECAPA-TDNN Speaker ID"]
            summary_svc["summary_service.py<br/>Groq LLM Summaries"]
            insights_svc["insights_service.py<br/>Action Items, Decisions,<br/>Requirements, Docs, Sentiment,<br/>Topics, Title, Follow-up Email"]
            pub["publish_service.py<br/>PDF + Email + Teams"]
            rag["rag_service.py<br/>ChromaDB + LangChain"]
            jira_svc["jira_service.py<br/>REST API v3"]
        end
    end

    subgraph External["☁️ External Services"]
        Groq["Groq API<br/>Llama 3.3 70B + Whisper"]
        ADB["AssemblyAI API"]
        Jira["Jira Cloud<br/>REST API v3"]
        SMTP["SMTP Server<br/>Gmail"]
        Teams["Teams Webhook"]
        Notion["Notion API"]
        Confluence["Confluence API"]
    end

    subgraph Storage["💾 Storage Layer"]
        FS["File System<br/>storage/{meeting_id}/*.json"]
        Chroma["ChromaDB<br/>storage/chroma_db/"]
        Audio["data/audio/{id}.wav"]
        Video["storage/{id}/video.mp4"]
        Profiles["storage/speaker_profiles/<br/>profiles.json"]
        Models["storage/models/<br/>ECAPA-TDNN cache"]
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
    B --> C["🗣️ Transcribe + Diarize<br/>AssemblyAI / Groq / WhisperX"]
    C --> D["💾 Save transcript.json"]
    D --> E["🏷️ Auto-Generate Title<br/>Groq LLM"]

    D --> F["🔍 Auto-Index RAG<br/>ChromaDB"]

    D --> V["🎤 Voice Match<br/>ECAPA-TDNN Embeddings"]
    V --> V2["Auto-rename speakers<br/>from stored profiles"]

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
    I --> S["📘 Confluence / Notion"]

    style G fill:#ffd700,stroke:#333
    style H fill:#ff6b6b,stroke:#333
    style P fill:#0052CC,stroke:#333
    style R fill:#10b981,stroke:#333
    style V fill:#9b59b6,stroke:#333
```

---

## 3. Voice Identification Pipeline

```mermaid
flowchart TD
    A["🎤 Meeting Transcribed"] --> B["Extract ~10s clip per speaker<br/>SNR-ranked segment selection"]
    B --> C["5-Step Audio Preprocessing<br/>Resample → Normalize →<br/>Bandpass 80-7600Hz →<br/>Silence Removal → Re-normalize"]
    C --> D["ECAPA-TDNN Embedding<br/>SpeechBrain → 192-dim vector"]
    D --> E{"Stored Profiles Exist?"}

    E -->|Yes| F["Cosine Similarity<br/>Match against all profiles"]
    F --> G{"Similarity > 0.55?"}
    G -->|Yes| H["Auto-rename speaker<br/>SPEAKER_00 → Babuji Abraham"]
    G -->|No| I["Keep generic label"]

    E -->|No| I

    J["👤 User names speakers<br/>via HITL Speaker Map"] --> K["Enroll Profile<br/>POST /meeting/{id}/speaker-profiles"]
    K --> L["Save to profiles.json<br/>Running average if exists"]
    L --> M["Future meetings<br/>auto-match against profiles"]

    style D fill:#9b59b6,stroke:#333
    style H fill:#27ae60,stroke:#333
    style L fill:#e67e22,stroke:#333
```

---

## 4. File Storage Structure

```
storage/
├── {meeting_id}/
│   ├── transcript.json        ← segments + speakers
│   ├── metadata.json          ← title, dates, counts
│   ├── video.mp4              ← original video for playback
│   ├── speaker_map.json       ← HITL name mapping
│   ├── speaker_clips/         ← 10s WAV clips per speaker
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
├── speaker_profiles/
│   └── profiles.json          ← global voice embeddings {name: [192 floats]}
├── models/
│   └── spkrec-ecapa-voxceleb/ ← cached SpeechBrain model
├── chroma_db/                 ← ChromaDB vector store
└── _file_hashes.json          ← SHA-256 upload deduplication registry

data/
├── audio/{meeting_id}.wav     ← extracted audio (16kHz mono)
└── audio/{meeting_id}_clean.wav ← noise-reduced audio
```

---

## 5. API Endpoint Map

```mermaid
graph LR
    subgraph Upload["📹 Upload & Transcribe"]
        A1["POST /upload-video"]
        A2["POST /transcribe/{id}"]
    end

    subgraph Voice["🎤 Voice ID"]
        V1["GET /meeting/{id}/speaker-clips"]
        V2["POST /meeting/{id}/speaker-profiles"]
        V3["POST /meeting/{id}/voice-match"]
        V4["GET /speaker-profiles"]
    end

    subgraph Insights["🧠 AI Insights"]
        B1["POST /summarize/{id}"]
        B2["POST /meeting/{id}/action-items"]
        B3["POST /meeting/{id}/requirements"]
        B4["POST /meeting/{id}/documentation"]
        B5["POST /meeting/{id}/sentiment"]
        B6["POST /meeting/{id}/topics"]
        B7["POST /meeting/{id}/followup-email"]
        B8["POST /meeting/{id}/auto-title"]
    end

    subgraph Publish["📤 Publish"]
        C1["POST /publish/{id}"]
        C2["POST /meeting/{id}/followup-email/send"]
        C3["GET /publish/{id}/pdf"]
        C4["GET /publish/{id}/full-report"]
    end

    subgraph Chat["💬 RAG Chat"]
        D1["POST /chat/ask/stream"]
        D2["POST /chat/index/{id}"]
        D3["GET /chat/meetings"]
        D4["POST /chat/clear/{session_id}"]
    end

    subgraph Jira["🎫 Jira"]
        E1["POST /meeting/{id}/jira/push"]
        E2["POST /meeting/{id}/jira/sync"]
        E3["PUT /meeting/{id}/jira/update"]
        E4["GET /jira/status"]
    end

    subgraph Wiki["📘 Wiki"]
        W1["POST /meeting/{id}/notion/push"]
        W2["POST /meeting/{id}/confluence/push"]
        W3["GET /notion/status"]
        W4["GET /confluence/status"]
    end

    subgraph Data["📊 Data"]
        F1["GET /meetings"]
        F2["GET /meeting/{id}"]
        F3["GET /meeting/{id}/metadata"]
        F4["GET /meeting/{id}/video"]
        F5["GET /stats"]
        F6["GET /stats/culture-score"]
        F7["GET /search"]
        F8["POST /meeting/{id}/speaker-map"]
        F9["GET /meeting/{id}/speaker-analytics"]
    end
```

---

## 6. Speaker Map → Background Regeneration Workflow

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

## 7. RAG Diverse Retrieval Algorithm

```mermaid
flowchart TD
    Q["User Question"] --> A["Embed question<br/>all-MiniLM-L6-v2"]
    A --> B["ChromaDB similarity search<br/>Fetch top 40 candidates"]
    B --> C["Group by meeting_id"]
    C --> D["Round-robin selection<br/>1 from Meeting A<br/>1 from Meeting B<br/>1 from Meeting A<br/>..."]
    D --> E["Final 18 diverse chunks<br/>All meetings represented"]
    E --> F["Build context + calendar"]
    F --> G["Groq Llama 3.3 70B<br/>SSE Streaming"]
    G --> H["Token-by-token response<br/>+ Source citations"]

    style D fill:#10b981,stroke:#333
    style G fill:#3b82f6,stroke:#333
```

---

## 8. Jira Bidirectional Sync Workflow

```mermaid
sequenceDiagram
    actor User
    participant CIQ as ContextIQ
    participant Jira as Jira Cloud

    Note over User,Jira: Push: ContextIQ → Jira
    User->>CIQ: Click "Push to Jira" on action item
    CIQ->>Jira: POST /rest/api/3/issue (create)
    Note over CIQ: Maps: task→summary, priority,<br/>category→issuetype, context→ADF body
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
    CIQ->>Jira: GET /rest/api/3/issue/{key}/transitions
    CIQ->>Jira: POST /rest/api/3/issue/{key}/transitions (status change)
```

---

## 9. Publish Pipeline

```mermaid
flowchart TD
    A["POST /publish/{id}"] --> B["Load summary.json +<br/>action_items.json"]
    B --> C["Generate PDF<br/>fpdf2 + NotoSans +<br/>NotoSansDevanagari"]
    C --> D{Email recipients?}
    D -->|Yes| E["Send via SMTP<br/>PDF attached"]
    D -->|No| F["Skip email"]
    C --> G{Teams webhook?}
    G -->|Yes| H["Send Rich Adaptive Card v1.4<br/>Summary + Action Items +<br/>Decisions + Speakers"]
    G -->|No| I["Skip Teams"]
    E --> J["Return result"]
    F --> J
    H --> J
    I --> J

    K["POST /meeting/{id}/notion/push"] --> L["Convert to Notion blocks"]
    M["POST /meeting/{id}/confluence/push"] --> N["Convert to XHTML storage format"]
```

---

## 10. Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Svelte 5 + Vite 5 + TailwindCSS 3 + Lucide Svelte |
| **Backend** | FastAPI + Uvicorn (Python 3.10+) |
| **STT Engines** | AssemblyAI (primary) + Groq Whisper + WhisperX (local) |
| **Diarization** | pyannote.audio 3.1 (neural VAD + clustering) |
| **Voice ID** | SpeechBrain ECAPA-TDNN (192-dim embeddings, VoxCeleb) |
| **LLM** | Groq API → Llama 3.3 70B Versatile |
| **RAG** | LangChain + ChromaDB + all-MiniLM-L6-v2 (384-dim) |
| **PDF** | fpdf2 with NotoSans + NotoSansDevanagari |
| **Email** | smtplib (SMTP/TLS) |
| **Teams** | Incoming Webhook (Adaptive Cards v1.4) |
| **Jira** | REST API v3 (Basic Auth, ADF descriptions) |
| **Confluence** | REST API v2 (API Token) |
| **Notion** | Notion API (API Token) |
| **Audio** | FFmpeg (video → WAV 16kHz mono) |
| **Storage** | File-system JSON + ChromaDB (SQLite-backed) |

---

## 11. Frontend Routing

| Route | Page | Purpose |
|---|---|---|
| `/` | Home.svelte | Landing page |
| `/dashboard` | Dashboard.svelte | Upload + stats + meeting list + culture score |
| `/meeting/:id` | MeetingDetail.svelte | Transcript + all analytics tabs |
| `/meeting/:id/actions` | ActionItems.svelte | Tasks + Jira + follow-up email |
| `/chat` | Chat.svelte | RAG chatbot with SSE streaming |
| `/search` | Search.svelte | Keyword search across meetings |

---

## 12. Entity Relationship — Data Model

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
    MEETING ||--o{ SPEAKER_CLIP : "has many"
    ACTION_ITEMS ||--o{ JIRA_TICKET : "links to"
    SPEAKER_PROFILE ||--o{ MEETING : "matches across"

    MEETING {
        string meeting_id PK
        string audio_path
        string video_path
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
        string processed_date
        string processed_day
        int segment_count
        int speaker_count
    }
    SPEAKER_MAP {
        string SPEAKER_00 "Real Name"
        string SPEAKER_01 "Real Name"
    }
    SPEAKER_PROFILE {
        string name PK
        array embedding "192 floats"
        int enrollment_count
    }
    SPEAKER_CLIP {
        string speaker_id
        string clip_path
        float duration
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
    TOPICS {
        array topics "title, summary, start, end, speakers"
    }
```

---

## 13. Meeting Lifecycle — State Diagram

```mermaid
stateDiagram-v2
    [*] --> Uploaded: POST /upload-video
    Uploaded --> Transcribing: POST /transcribe/{id}
    Transcribing --> Transcribed: STT engine complete

    Transcribed --> VoiceMatched: Auto voice-match
    Transcribed --> TitleGenerated: Auto-title (background)
    TitleGenerated --> RAGIndexed: Auto-index (background)

    VoiceMatched --> SpeakersMapped: User maps remaining names (HITL)
    RAGIndexed --> SpeakersMapped: User maps names (HITL)
    SpeakersMapped --> Regenerating: Background regeneration

    Regenerating --> InsightsReady: All 8 tasks complete

    InsightsReady --> Published: PDF + Email + Teams
    InsightsReady --> JiraSynced: Push to Jira
    InsightsReady --> WikiPublished: Confluence / Notion

    state InsightsReady {
        [*] --> Summary
        [*] --> ActionItems
        [*] --> Requirements
        [*] --> Documentation
        [*] --> Sentiment
        [*] --> Topics
        [*] --> FollowupEmail
        [*] --> SpeakerReportCard
    }

    Published --> [*]
    JiraSynced --> BidirectionalSync: Sync from Jira
    BidirectionalSync --> JiraSynced
```

---

## 14. User Journey — Complete Workflow

```mermaid
flowchart TD
    A["🎬 User uploads video"] --> B["⏳ Processing<br/>Audio extraction + Transcription"]
    B --> B2["🎤 Auto Voice Match<br/>ECAPA-TDNN vs stored profiles"]
    B2 --> C["📜 View Transcript<br/>Chat / Speaker / Timeline views"]
    C --> D["👤 Map Speaker Names<br/>HITL: SPEAKER_00 → Babuji Abraham"]
    D --> D2["💾 Enroll Profiles<br/>Save voice embeddings for future"]
    D2 --> E["🔄 Auto-Regeneration<br/>8 tasks in background"]
    E --> F{"Choose Action"}

    F --> G["📝 View Summary<br/>English + Hindi"]
    F --> H["✅ View Action Items<br/>Review tasks + decisions"]
    F --> I["💬 Chat with AI<br/>Ask questions about meetings"]
    F --> J["📊 View Analytics<br/>Speaker stats + sentiment +<br/>topics + report cards"]

    H --> K{"Push to Jira?"}
    K -->|Yes| L["🎫 Create Jira Tickets<br/>Auto-mapped fields + ADF body"]
    K -->|No| M["Continue"]

    L --> N["🔄 Bidirectional Sync<br/>Status stays in sync"]

    G --> O{"Publish?"}
    O -->|PDF| P["📄 Download PDF"]
    O -->|Email| Q["📧 Send via SMTP"]
    O -->|Teams| R["💬 Rich Adaptive Card"]
    O -->|Follow-up| S["💌 Follow-up Email"]
    O -->|Wiki| S2["📘 Confluence / Notion"]

    I --> T["📚 Cross-meeting Q&A<br/>RAG with diverse retrieval + citations"]

    style B2 fill:#9b59b6,stroke:#333
    style D fill:#ffd700,stroke:#333
    style E fill:#ff6b6b,stroke:#333
    style L fill:#0052CC,stroke:#333
    style T fill:#10b981,stroke:#333
```

---

## 15. Service Class Diagram

```mermaid
classDiagram
    class VideoAudioConverter {
        -ffmpeg_path: str
        +video_to_audio(video_path, audio_path)
    }

    class AudioTranscriptionService {
        -device: str
        -compute_type: str
        -stt_mode: str
        +transcribe(audio_path) dict
        -_transcribe_assemblyai(path) dict
        -_transcribe_groq(path) dict
        -_transcribe_local(path) dict
        -_preprocess_audio(path) str
        -_load_diarization_pipeline()
        -_assign_speakers_from_diarization()
        -_free_gpu()
    }

    class VoiceEmbeddingService {
        -_model: EncoderClassifier
        -profiles_dir: Path
        +extract_speaker_clips(meeting_id) dict
        +generate_embedding(clip_path) list
        +save_speaker_profile(name, embedding)
        +load_profiles() dict
        +match_speakers(meeting_id) dict
        -_build_clip(audio, sr, segments) ndarray
        -_preprocess_audio(audio, sr) ndarray
        -_bandpass_filter(audio, sr) ndarray
        -_remove_silence(audio, sr) ndarray
        -_get_model() EncoderClassifier
        +cosine_similarity(a, b) float
    }

    class MeetingSummaryService {
        -client: Groq
        +summarize(meeting_id, force, extra_prompt) dict
        -_build_conversation_text(segments) str
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
    }

    class MeetingRAGService {
        -_embeddings: HuggingFaceEmbeddings
        -_vectorstore: Chroma
        -_memories: dict
        +ingest_meeting(meeting_id) int
        +query_stream(question, session_id) generator
        +list_indexed_meetings() list
        -_diverse_retrieve(question) list
        -_rebuild_index()
        -_delete_meeting_docs(meeting_id)
    }

    class MeetingPublishService {
        +generate_pdf(summary_data, output_path) str
        +generate_full_report(meeting_id) str
        +send_email(pdf_path, title, recipients) dict
        +send_to_teams(summary_data, title, meeting_id) dict
        +publish(meeting_id) dict
    }

    class JiraService {
        +is_configured() bool
        +create_ticket(action_item, title) dict
        +create_tickets_batch(items, title) dict
        +update_ticket(ticket_key, item) dict
        +fetch_ticket_status(ticket_key) dict
        +sync_tickets(items) dict
    }

    AudioTranscriptionService --> VideoAudioConverter : uses
    AudioTranscriptionService --> VoiceEmbeddingService : triggers voice match
    MeetingSummaryService --> MeetingInsightsService : same Groq client
    MeetingPublishService --> MeetingSummaryService : reads summary
    MeetingRAGService --> MeetingInsightsService : indexes insights
```

---

## 16. Meeting Culture Score Algorithm

```mermaid
flowchart LR
    A["Speaker Balance<br/>Weight: 30%<br/>Gini-like measure"] --> E["Weighted<br/>Average"]
    B["Sentiment Health<br/>Weight: 25%<br/>% positive+neutral"] --> E
    C["Action Completion<br/>Weight: 30%<br/>% items Done"] --> E
    D["Meeting Efficiency<br/>Weight: 15%<br/>Decisions per 10min"] --> E
    E --> F["Culture Score<br/>0-100"]
    F --> G{"Grade"}
    G -->|"80-100"| H["Excellent ✅"]
    G -->|"60-79"| I["Good 👍"]
    G -->|"40-59"| J["Needs Work ⚠️"]
    G -->|"0-39"| K["Poor ❌"]
```

---

## 17. Feature Mind Map

```mermaid
mindmap
  root((ContextIQ))
    🎙️ Ingestion
      Video Upload + Dedup
      Audio Extraction FFmpeg
      Multi-Engine STT
        AssemblyAI Cloud
        Groq Whisper Ultra-Fast
        WhisperX Local GPU
      Speaker Diarization pyannote
      Voice Identification ECAPA-TDNN
    🧠 AI Analytics
      Bilingual Summary EN+HI
      Action Items + Decisions
      Requirements Mining MoSCoW
      Meeting Documentation
      Sentiment Analysis
      Topic Segmentation
      Auto Title Generation
      Follow-up Email Draft
      Speaker Report Cards
      Meeting Culture Score
    👤 Human-in-the-Loop
      Speaker Name Mapping
      Voice Profile Enrollment
      Summary Review + Approval
      Auto Background Regeneration
    📤 Publishing
      PDF Report NotoSans+Devanagari
      Email with Attachment
      Teams Rich Adaptive Card
      Follow-up Email SMTP
    🎫 Integrations
      Jira Bidirectional Sync
        Push Action Items
        Sync Status Back
        Update via Transitions API
      Confluence Wiki Pages
      Notion Pages
    💬 AI Chat
      RAG over Transcripts
      SSE Streaming
      Diverse Retrieval Round-Robin
      Cross-Meeting Q and A
      Citations with Timestamps
      Conversation Memory
      Meeting Calendar Context
    📊 Dashboard
      Unique Speaker Count
      Culture Score Heatmap
      Meeting Statistics
    🔍 Search
      Weighted Keyword Search
      Snippet Highlighting
    🎬 Media
      Video Playback Range Requests
      Speaker Clip Audio Playback
```

---

*Updated: February 28, 2026 — reflects all 27 features across 14 API modules and 8 services*
