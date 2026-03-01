"""
FastAPI application entry point.
Registers routers for upload, transcription, and meeting retrieval.
"""
import logging
from pathlib import Path
from fastapi import FastAPI

from app.api.upload import router as upload_router
from app.api.transcribe import router as transcribe_router
from app.api.diarization import router as diarization_router
from app.api.summarize import router as summarize_router
from app.api.publish import router as publish_router
from app.api.speaker_map import router as speaker_map_router
from app.api.chat import router as chat_router
from app.api.insights import router as insights_router
from app.api.stats import router as stats_router
from app.api.search import router as search_router
from app.api.jira import router as jira_router
from app.api.notion import router as notion_router
from app.api.confluence import router as confluence_router
from app.api.voice_profiles import router as voice_profiles_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)

app = FastAPI(title="Meeting Intelligence System", version="2.0.0")

# Ensure required directories exist at startup
for d in ["data/audio", "storage"]:
    Path(d).mkdir(parents=True, exist_ok=True)

# CORS — allow Svelte frontend to call the API
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",  # Vite preview
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(upload_router, tags=["Upload"])
app.include_router(transcribe_router, tags=["Transcription"])
app.include_router(diarization_router, tags=["Meeting"])
app.include_router(summarize_router, tags=["Summary"])
app.include_router(publish_router, tags=["Publish"])
app.include_router(speaker_map_router, tags=["Speaker Map"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(insights_router, tags=["Insights"])
app.include_router(stats_router, tags=["Stats"])
app.include_router(search_router, tags=["Search"])
app.include_router(jira_router, tags=["Jira"])
app.include_router(notion_router, tags=["Notion"])
app.include_router(confluence_router, tags=["Confluence"])
app.include_router(voice_profiles_router, tags=["Voice Profiles"])


@app.get("/")
async def root():
    return {
        "service": "Meeting Intelligence System",
        "version": "2.0.0",
        "endpoints": [
            # Stage 1: Upload & Audio
            "POST /upload-video",
            # Stage 2: Transcription & Diarization
            "POST /transcribe/{meeting_id}",
            "GET  /meetings",
            "GET  /meeting/{meeting_id}",
            "PUT  /meeting/{meeting_id}/segments/{index}",
            "GET  /meeting/{meeting_id}/metadata",
            "PATCH /meeting/{meeting_id}/metadata",
            "GET  /meeting/{meeting_id}/video",
            # Speaker Map
            "POST /meeting/{meeting_id}/speaker-map",
            "GET  /meeting/{meeting_id}/speaker-map",
            # Voice Identification
            "GET  /meeting/{meeting_id}/speaker-clips",
            "GET  /meeting/{meeting_id}/speaker-clips/{speaker_id}",
            "GET  /speaker-profiles",
            "POST /meeting/{meeting_id}/speaker-profiles",
            "POST /meeting/{meeting_id}/voice-match",
            # Stage 3: AI Analytics
            "POST /summarize/{meeting_id}",
            "POST /meeting/{meeting_id}/action-items",
            "PUT  /meeting/{meeting_id}/action-items",
            "POST /meeting/{meeting_id}/auto-title",
            "POST /meeting/{meeting_id}/followup-email",
            "POST /meeting/{meeting_id}/followup-email/send",
            "POST /meeting/{meeting_id}/requirements",
            "POST /meeting/{meeting_id}/documentation",
            "POST /meeting/{meeting_id}/sentiment",
            "POST /meeting/{meeting_id}/topics",
            "GET  /meeting/{meeting_id}/speaker-analytics",
            "GET  /meeting/{meeting_id}/speaker-report",
            "GET  /meeting/{meeting_id}/keywords",
            # RAG Chatbot
            "POST /chat/ask",
            "POST /chat/ask/stream",
            "POST /chat/index/{meeting_id}",
            "GET  /chat/meetings",
            "POST /chat/clear/{session_id}",
            # Dashboard & Search
            "GET  /stats",
            "GET  /stats/culture-score",
            "GET  /search?q=keyword",
            "GET  /health",
            # Stage 4: Publishing & Integrations
            "POST /publish/{meeting_id}",
            "GET  /publish/{meeting_id}/pdf",
            "GET  /publish/{meeting_id}/full-report",
            "POST /publish/{meeting_id}/full-report",
            "POST /publish/{meeting_id}/full-report/email",
            "GET  /jira/status",
            "POST /meeting/{meeting_id}/jira/push",
            "POST /meeting/{meeting_id}/jira/sync",
            "PUT  /meeting/{meeting_id}/jira/update",
            "GET  /notion/status",
            "POST /meeting/{meeting_id}/notion/push",
            "GET  /confluence/status",
            "POST /meeting/{meeting_id}/confluence/push",
        ]
    }


@app.get("/health", tags=["System"])
async def health_check():
    """
    System health check — GPU, storage, and ChromaDB status.
    Useful for monitoring and hackathon demos.
    """
    try:
        import torch

        # GPU info
        gpu_available = torch.cuda.is_available()
        gpu_info = {}
        if gpu_available:
            gpu_info = {
                "device": torch.cuda.get_device_name(0),
                "vram_total_mb": round(torch.cuda.get_device_properties(0).total_memory / 1024**2),
                "vram_free_mb": round(torch.cuda.mem_get_info()[0] / 1024**2),
            }

        # Storage stats
        storage_dir = Path("storage")
        meeting_dirs = [d for d in storage_dir.iterdir() if d.is_dir() and d.name != "chroma_db"] if storage_dir.exists() else []
        total_size = sum(f.stat().st_size for d in meeting_dirs for f in d.rglob("*") if f.is_file())

        # Meeting status breakdown
        status_counts = {"uploaded": 0, "transcribed": 0, "summarized": 0, "published": 0}
        for d in meeting_dirs:
            if (d / "Meeting_Summary.pdf").exists():
                status_counts["published"] += 1
            elif (d / "summary.json").exists():
                status_counts["summarized"] += 1
            elif (d / "transcript.json").exists():
                status_counts["transcribed"] += 1
            else:
                status_counts["uploaded"] += 1

        # ChromaDB status
        chroma_path = storage_dir / "chroma_db"
        chroma_exists = chroma_path.exists()

        return {
            "status": "healthy",
            "gpu": {
                "available": gpu_available,
                "compute_type": "float16" if gpu_available else "int8",
                **gpu_info,
            },
            "storage": {
                "total_meetings": len(meeting_dirs),
                "disk_usage_mb": round(total_size / 1024**2, 1),
                "meetings_by_status": status_counts,
            },
            "chromadb": {
                "initialized": chroma_exists,
            },
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}