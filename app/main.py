"""
FastAPI application entry point.
Registers routers for upload, transcription, and meeting retrieval.
"""
import logging
from fastapi import FastAPI

from app.api.upload import router as upload_router
from app.api.transcribe import router as transcribe_router
from app.api.diarization import router as diarization_router

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


@app.get("/")
async def root():
    return {
        "service": "Meeting Intelligence System",
        "endpoints": [
            "POST /upload-video",
            "POST /transcribe/{meeting_id}",
            "GET /meeting/{meeting_id}"
        ]
    }