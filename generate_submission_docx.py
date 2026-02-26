"""
Generate VRIZE Hackathon Submission as a .docx file
matching the submission_template.docx format.
"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# ── Styles ──
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)

# ── Title ──
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("VRIZE Video Analytics Hackathon: Team Submission")
run.bold = True
run.font.size = Pt(16)
run.font.color.rgb = RGBColor(0, 51, 102)

doc.add_paragraph(
    "Instructions for Teams: Please complete this template and upload it to your "
    "designated OneDrive folder along with all referenced output files. Ensure every "
    "stage of your pipeline is documented clearly so the evaluation committee can "
    "assess your work easily."
).italic = True

# ── Team Information ──
h = doc.add_heading("Team Information", level=1)
doc.add_paragraph().add_run("Team Name: ").bold = True
doc.paragraphs[-1].add_run("Squad404")

doc.add_paragraph().add_run("Team Members: ").bold = True
doc.paragraphs[-1].add_run("Pawan Kumar Uikey, Ashish Jaiswal, Richa Pandey")

doc.add_paragraph().add_run("Project Name: ").bold = True
doc.paragraphs[-1].add_run(
    "ContextIQ — a fully-featured Meeting Intelligence Platform that takes raw MS Teams "
    "video recordings and produces speaker-diarized transcriptions, bilingual AI summaries "
    "(English + Hindi), sentiment analysis, action item extraction with Jira integration, "
    "and a RAG-powered chatbot — all orchestrated through a modern Svelte frontend and "
    "FastAPI backend."
)

# ══════════════════════════════════════════════════════════════
# PART 1: Open-Source Tool Registry
# ══════════════════════════════════════════════════════════════
doc.add_heading("Part 1: Open-Source Tool Registry", level=1)
doc.add_paragraph(
    "List of all open-source tools, libraries, and models used during the hackathon."
)

tools = [
    ("FFmpeg", "v7.0+", "Audio extraction from MS Teams .mp4 video (16 kHz mono WAV)", "Stage 1"),
    ("noisereduce", "Latest", "Audio noise reduction preprocessing", "Stage 1"),
    ("soundfile", "Latest", "Audio file I/O for preprocessing pipeline", "Stage 1"),
    ("AssemblyAI SDK", "Latest", "Primary cloud-based STT with speaker diarization", "Stage 2"),
    ("WhisperX", "v3.1", "Local STT with word-level timestamps (CTranslate2)", "Stage 2"),
    ("pyannote.audio", "v3.1", "Speaker diarization — identifies individual speakers", "Stage 2"),
    ("PyTorch", "2.x (CUDA 12.8)", "GPU-accelerated ML inference for local models", "Stage 2"),
    ("Groq SDK (Llama 3.3 70B)", "Latest", "Ultra-fast LLM inference for summaries, action items, sentiment", "Stage 3"),
    ("LangChain", "Latest", "RAG pipeline orchestration (document loading, retrieval, chains)", "Stage 3"),
    ("ChromaDB", "Latest", "Local vector database for transcript embeddings", "Stage 3"),
    ("HuggingFace (all-MiniLM-L6-v2)", "Latest", "384-dim embedding model for semantic search", "Stage 3"),
    ("Chart.js", "Latest", "Interactive charts for sentiment and statistics", "Stage 3"),
    ("fpdf2", "Latest", "PDF report generation with Unicode Hindi support", "Stage 4"),
    ("smtplib (stdlib)", "Built-in", "Email publishing with PDF attachments via SMTP", "Stage 4"),
    ("Atlassian REST API", "v3", "Jira integration — push, sync, update action items", "Stage 4"),
    ("FastAPI", "0.100+", "Backend REST API server with 32 endpoints", "All"),
    ("Uvicorn", "Latest", "ASGI server to run FastAPI", "All"),
    ("Svelte", "v5", "Modern frontend SPA with reactive UI", "All"),
    ("Vite", "v5", "Frontend build tool and dev server", "All"),
    ("TailwindCSS", "v3", "Utility-first CSS framework for responsive UI", "All"),
    ("Lucide Svelte", "Latest", "Icon library for the frontend", "All"),
    ("svelte-spa-router", "Latest", "Client-side hash-based routing for SPA", "All"),
]

table = doc.add_table(rows=1, cols=4)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
hdr = table.rows[0].cells
for i, text in enumerate(["Tool / Library Name", "Version", "Primary Purpose", "Stage Used"]):
    hdr[i].text = text
    for p in hdr[i].paragraphs:
        for r in p.runs:
            r.bold = True

for tool in tools:
    row = table.add_row().cells
    for i, val in enumerate(tool):
        row[i].text = val

# ══════════════════════════════════════════════════════════════
# PART 2: SOP & Pipeline Stages
# ══════════════════════════════════════════════════════════════
doc.add_heading("Part 2: Standard Operating Procedure (SOP) & Pipeline Stages", level=1)
doc.add_paragraph(
    "Breakdown of the video analytics pipeline into sequential stages."
)

# --- Stage 1 ---
doc.add_heading("Stage 1: Data Pre-Processing & Audio Extraction", level=2)

doc.add_paragraph().add_run("Objective: ").bold = True
doc.paragraphs[-1].add_run(
    "Extract clean, optimized audio from raw MS Teams .mp4 video recordings "
    "and prepare it for transcription."
)

doc.add_paragraph().add_run("Tool(s) Used: ").bold = True
doc.paragraphs[-1].add_run("FFmpeg, noisereduce, soundfile")

doc.add_paragraph().add_run("Input Data: ").bold = True
doc.paragraphs[-1].add_run("Original MS Teams .mp4 video file uploaded via the web UI.")

doc.add_paragraph().add_run("Output File Link: ").bold = True
doc.paragraphs[-1].add_run("data/audio/{meeting_id}.wav — 16 kHz mono WAV file")

doc.add_paragraph().add_run("Execution Details: ").bold = True
doc.add_paragraph(
    "1. User uploads video via POST /upload-video endpoint.\n"
    "2. SHA-256 hash is computed to prevent duplicate processing.\n"
    "3. FFmpeg extracts audio: ffmpeg -i input.mp4 -ar 16000 -ac 1 -f wav output.wav\n"
    "4. Audio preprocessing applies noise reduction (prop_decrease=0.7) and peak normalization to -1 dBFS.\n"
    "5. Clean audio saved as {meeting_id}_clean.wav.",
    style='List Bullet'
)

# --- Stage 2 ---
doc.add_heading("Stage 2: Transcription & Speaker Diarization", level=2)

doc.add_paragraph().add_run("Objective: ").bold = True
doc.paragraphs[-1].add_run(
    "Convert the extracted audio to text with word-level timestamps and identify "
    "individual speakers throughout the recording."
)

doc.add_paragraph().add_run("Tool(s) Used: ").bold = True
doc.paragraphs[-1].add_run("AssemblyAI (primary), WhisperX + pyannote.audio (local fallback)")

doc.add_paragraph().add_run("Input Data: ").bold = True
doc.paragraphs[-1].add_run("data/audio/{meeting_id}_clean.wav (preprocessed audio)")

doc.add_paragraph().add_run("Output File Link: ").bold = True
doc.paragraphs[-1].add_run("storage/{meeting_id}/transcript.json — full diarized transcript")

doc.add_paragraph().add_run("Execution Details: ").bold = True
doc.add_paragraph(
    "1. Triggered via POST /transcribe/{meeting_id}.\n"
    "2. AssemblyAI mode (primary): Audio uploaded to AssemblyAI API with speaker_labels=True.\n"
    "3. Local mode (fallback): WhisperX large-v2 model on GPU + pyannote.audio 3.1 diarization.\n"
    "4. Metadata auto-saved: processing timestamp, segment count, speaker count, total duration.\n"
    "5. GPU memory explicitly cleared after processing (torch.cuda.empty_cache()).",
    style='List Bullet'
)

# --- Stage 3 ---
doc.add_heading("Stage 3: Analytics & Feature Generation", level=2)

doc.add_paragraph().add_run("Objective: ").bold = True
doc.paragraphs[-1].add_run(
    "Generate comprehensive AI-powered analytics: bilingual summaries, action items, "
    "sentiment analysis, requirements, documentation, and RAG chatbot."
)

doc.add_paragraph().add_run("Tool(s) Used: ").bold = True
doc.paragraphs[-1].add_run("Groq API (Llama 3.3 70B), LangChain, ChromaDB, HuggingFace Embeddings")

doc.add_paragraph().add_run("Input Data: ").bold = True
doc.paragraphs[-1].add_run("storage/{meeting_id}/transcript.json")

doc.add_paragraph().add_run("Output File Links: ").bold = True
outputs = [
    "storage/{meeting_id}/summary.json — Bilingual summaries (English + Hindi)",
    "storage/{meeting_id}/action_items.json — Action items, decisions, takeaways, risks",
    "storage/{meeting_id}/sentiment.json — Per-segment sentiment scores and emotion labels",
    "storage/{meeting_id}/requirements.json — Extracted functional requirements",
    "storage/{meeting_id}/documentation.json — Auto-generated meeting minutes (MoM)",
    "storage/{meeting_id}/followup_email.json — AI-drafted follow-up email",
    "storage/chroma_db/ — Vector embeddings indexed in ChromaDB",
]
for o in outputs:
    doc.add_paragraph(o, style='List Bullet')

doc.add_paragraph().add_run("Execution Details: ").bold = True
doc.add_paragraph(
    "1. Summarization (POST /summarize/{id}): Groq Llama 3.3 70B generates speaker-wise + overall summaries in English and Hindi.\n"
    "2. Action Items (POST /meeting/{id}/action-items): Structured JSON extraction.\n"
    "3. Sentiment (POST /meeting/{id}/sentiment): Per-segment mood scoring.\n"
    "4. RAG Indexing (POST /chat/index/{id}): all-MiniLM-L6-v2 embeddings stored in ChromaDB.\n"
    "5. RAG Chat (POST /chat/ask/stream): SSE streaming with source citations (~500 tok/sec).",
    style='List Bullet'
)

# --- Stage 4 ---
doc.add_heading("Stage 4: Report Generation & Publishing", level=2)

doc.add_paragraph().add_run("Objective: ").bold = True
doc.paragraphs[-1].add_run(
    "Generate professional PDF reports, distribute via email and Teams, "
    "push action items to Jira, and export subtitles."
)

doc.add_paragraph().add_run("Tool(s) Used: ").bold = True
doc.paragraphs[-1].add_run("fpdf2, smtplib, Microsoft Teams Webhook, Atlassian Jira REST API")

doc.add_paragraph().add_run("Input Data: ").bold = True
doc.paragraphs[-1].add_run("summary.json, action_items.json, requirements.json, documentation.json")

doc.add_paragraph().add_run("Output File Links: ").bold = True
doc.add_paragraph("PDF summary report (NotoSans + NotoSansDevanagari fonts)", style='List Bullet')
doc.add_paragraph("Full comprehensive report PDF (summary + actions + requirements + docs)", style='List Bullet')
doc.add_paragraph("SRT and VTT subtitle files with speaker labels", style='List Bullet')

doc.add_paragraph().add_run("Execution Details: ").bold = True
doc.add_paragraph(
    "1. PDF Generation (GET /publish/{id}/pdf): fpdf2 with Unicode Hindi support.\n"
    "2. Full Report (GET /publish/{id}/full-report): All analytics combined.\n"
    "3. Email (POST /publish/{id}): SMTP with PDF attachment.\n"
    "4. Teams (POST /publish/{id}): Adaptive Card to configured webhook.\n"
    "5. Jira Push (POST /meeting/{id}/jira/push): Action items as Jira tickets with bi-directional sync.\n"
    "6. Subtitles (GET /meeting/{id}/subtitles/srt and /vtt).",
    style='List Bullet'
)

# ══════════════════════════════════════════════════════════════
# PART 3: Features & Innovation Summary
# ══════════════════════════════════════════════════════════════
doc.add_heading("Part 3: Features & Innovation Summary", level=1)
doc.add_paragraph("Highlight the capabilities of the final analytics report.")

doc.add_heading("List of Features Built:", level=2)
features = [
    "Multi-Engine Speech-to-Text (AssemblyAI, Groq Whisper, local WhisperX)",
    "Speaker Diarization with GPU acceleration (pyannote.audio 3.1)",
    "Bilingual AI Summaries — English + Hindi (Devanagari)",
    "Action Item Extraction with assignee, deadline, priority, and success criteria",
    "Decisions Tracker — who decided what, why, and alternatives considered",
    "Key Takeaways — bullet-point highlights",
    "Auto Meeting Title generation",
    "Follow-Up Email Draft — professional email with summary + action items",
    "Per-Segment Sentiment Analysis with emotion labels and trends",
    "Requirements Extraction with priority levels",
    "Documentation Generation — auto-generated meeting minutes (MoM)",
    "RAG Chatbot with SSE Streaming — cross-meeting Q&A with source citations",
    "Human-in-the-Loop (HITL) — speaker mapping, summary editing & approval",
    "Professional PDF Reports with Unicode Hindi support",
    "SRT/VTT Subtitle Export with speaker labels",
    "One-Click Email & Teams Publishing",
    "Jira Integration — push, sync, and update action items bidirectionally",
    "Upload Deduplication via SHA-256 hashing",
    "Meeting Dashboard with real-time statistics and search",
    "Live Keyword Search across all meetings",
    "Skeleton Loading & Toast Notifications for polished UX",
]
for f in features:
    doc.add_paragraph(f, style='List Bullet')

doc.add_heading("Innovation Highlight:", level=2)
doc.add_paragraph(
    "ContextIQ's most innovative aspect is its end-to-end, privacy-first architecture "
    "that combines local GPU-accelerated processing for speech-to-text with cloud LLM APIs "
    "for intelligence. Unlike competitors that require all data to be uploaded to external "
    "servers, ContextIQ keeps raw audio and transcripts local while only sending text to "
    "Groq for analysis. The system uniquely provides bilingual Hindi summaries (a feature "
    "absent from all major competitors), a bi-directional Jira integration for action item "
    "management, and a Human-in-the-Loop approval workflow that ensures AI-generated content "
    "is reviewed before publishing. The multi-engine STT architecture (AssemblyAI → Groq → "
    "WhisperX) provides configurable fallback chains, allowing teams to optimize for accuracy, "
    "speed, or privacy based on their specific needs."
)

# ══════════════════════════════════════════════════════════════
# PART 4: Final Deliverables
# ══════════════════════════════════════════════════════════════
doc.add_heading("Part 4: Final Deliverables", level=1)

doc.add_paragraph().add_run("Link to Final Analytics Report: ").bold = True
doc.paragraphs[-1].add_run("[Insert OneDrive link to the final PDF report]")

doc.add_paragraph().add_run("Link to Source Code Repository: ").bold = True
doc.paragraphs[-1].add_run("https://github.com/pawanuikey06/ContextIQ")

doc.add_paragraph().add_run("Self-Reported Transcript Accuracy (Optional): ").bold = True
doc.paragraphs[-1].add_run("[Insert percentage match and metric used, e.g., Word Error Rate]")

# ── Save ──
output_path = r"d:\ContextIQ\VRIZE_Submission_Squad404.docx"
doc.save(output_path)
print(f"✅ Submission saved to: {output_path}")
