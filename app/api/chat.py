"""
Chat API — Q&A over meeting transcripts.
Endpoints for asking questions (with streaming), indexing meetings, and managing chat.
"""
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy-init the RAG service (heavy model loading)
_rag_service = None


def _get_rag_service():
    global _rag_service
    if _rag_service is None:
        from app.services.rag_service import MeetingRAGService
        _rag_service = MeetingRAGService()
    return _rag_service


# ── Request/Response Schemas ──


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"
    meeting_ids: Optional[List[str]] = None


class Citation(BaseModel):
    meeting_id: str
    speaker: str
    start: float
    end: float
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]


class IndexResponse(BaseModel):
    meeting_id: str
    chunks_indexed: int
    message: str


# ── Endpoints ──


@router.post("/chat/ask", response_model=ChatResponse)
async def chat_ask(body: ChatRequest):
    """
    Ask a question about your meetings.
    Optionally filter by meeting_ids to scope the answer.
    """
    logger.info(
        "Chat query: %s (session=%s, meetings=%s)",
        body.question[:100],
        body.session_id,
        body.meeting_ids,
    )

    try:
        service = _get_rag_service()
        result = service.query(
            question=body.question,
            session_id=body.session_id,
            meeting_ids=body.meeting_ids,
        )
    except Exception as e:
        logger.error("Chat query failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Chat query failed: {str(e)}",
        )

    return ChatResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
    )


@router.post("/chat/ask/stream")
async def chat_ask_stream(body: ChatRequest):
    """
    Stream a chat answer using Server-Sent Events (SSE).
    Yields:
      data: {"type": "token", "content": "word..."}
      data: {"type": "citations", "content": [...]}
      data: {"type": "done", "content": ""}
    """
    logger.info(
        "Chat stream: %s (session=%s)",
        body.question[:100],
        body.session_id,
    )

    def event_generator():
        try:
            service = _get_rag_service()
            for event_type, data in service.query_stream(
                question=body.question,
                session_id=body.session_id,
                meeting_ids=body.meeting_ids,
            ):
                payload = json.dumps({"type": event_type, "content": data})
                yield f"data: {payload}\n\n"
        except Exception as e:
            logger.error("Chat stream failed: %s", e)
            error_payload = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/index/{meeting_id}", response_model=IndexResponse)
async def index_meeting(meeting_id: str):
    """Index (or re-index) a meeting transcript into the knowledge base."""
    logger.info("Indexing meeting: %s", meeting_id)

    try:
        service = _get_rag_service()
        count = service.ingest_meeting(meeting_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Indexing failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Indexing failed: {str(e)}",
        )

    return IndexResponse(
        meeting_id=meeting_id,
        chunks_indexed=count,
        message=f"Successfully indexed {count} segments",
    )


@router.get("/chat/meetings")
async def list_indexed_meetings():
    """List all meetings currently in the knowledge base."""
    try:
        service = _get_rag_service()
        meetings = service.list_indexed_meetings()
        return {"indexed_meetings": meetings, "count": len(meetings)}
    except Exception as e:
        logger.error("List meetings failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/clear/{session_id}")
async def clear_chat(session_id: str):
    """Clear conversation history for a session."""
    service = _get_rag_service()
    service.clear_chat_history(session_id)
    return {"success": True, "message": f"Chat history cleared for session {session_id}"}
