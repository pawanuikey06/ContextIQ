"""
FastAPI application entry point.
Registers routers for upload, transcription, and meeting retrieval.
"""
import logging
from fastapi import FastAPI

from app.api.upload import router as upload_router
from app.api.transcribe import router as transcribe_router
from app.api.diarization import router as diarization_router
from app.api.summarize import router as summarize_router
from app.api.publish import router as publish_router
from app.api.speaker_map import router as speaker_map_router
from app.api.chat import router as chat_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)

app = FastAPI(title="Meeting Intelligence System", version="1.0.0")

# Register all routers
app.include_router(upload_router, tags=["Upload"])
app.include_router(transcribe_router, tags=["Transcription"])
app.include_router(diarization_router, tags=["Meeting"])
app.include_router(summarize_router, tags=["Summary"])
app.include_router(publish_router, tags=["Publish"])
app.include_router(speaker_map_router, tags=["Speaker Map"])
app.include_router(chat_router, tags=["Chat"])


@app.get("/")
async def root():
    return {
        "service": "Meeting Intelligence System",
        "version": "2.0.0",
        "endpoints": [
            "POST /upload-video",
            "POST /transcribe/{meeting_id}",
            "GET  /meeting/{meeting_id}",
            "PUT  /meeting/{meeting_id}/segments/{index}",
            "GET  /meeting/{meeting_id}/metadata",
            "PATCH /meeting/{meeting_id}/metadata",
            "POST /summarize/{meeting_id}",
            "POST /publish/{meeting_id}",
            "GET  /publish/{meeting_id}/pdf",
            "POST /chat/ask",
            "POST /chat/ask/stream",
            "POST /chat/index/{meeting_id}",
            "GET  /chat/meetings",
            "POST /chat/clear/{session_id}",
            "POST /meeting/{meeting_id}/speaker-map",
            "GET  /meeting/{meeting_id}/speaker-map",
        ]
    }