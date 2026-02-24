"""
Meeting search API.
Provides full-text keyword search across all meeting transcripts and metadata.
Falls back to keyword search if ChromaDB semantic search fails.
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Search"])
STORAGE_DIR = Path("storage")


def _load_meeting_meta(meeting_dir: Path) -> dict | None:
    """Load metadata for a meeting directory."""
    meta_path = meeting_dir / "metadata.json"
    transcript_path = meeting_dir / "transcript.json"
    if not transcript_path.exists():
        return None
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)
    segments = transcript.get("segments", [])
    return {
        "id": meeting_dir.name,
        "title": meta.get("title", f"Meeting {meeting_dir.name[:8]}"),
        "date": meta.get("uploaded_at", meta.get("created_at", ""))[:10],
        "speakers": list({s.get("speaker", "") for s in segments if s.get("speaker")}),
        "segments": segments,
        "full_text": " ".join(s.get("text", "") for s in segments),
    }


@router.get("/search")
async def search_meetings(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Max results"),
):
    """
    Search meetings by keyword across title, speaker names, and transcript text.
    Returns matching meetings with highlighted snippets.
    """
    if not q or len(q.strip()) < 2:
        return {"query": q, "results": [], "total": 0}

    query = q.strip().lower()
    results = []

    if not STORAGE_DIR.exists():
        return {"query": q, "results": [], "total": 0}

    for meeting_dir in STORAGE_DIR.iterdir():
        if not meeting_dir.is_dir() or meeting_dir.name in ("chroma_db", "."):
            continue
        try:
            meta = _load_meeting_meta(meeting_dir)
            if meta is None:
                continue

            score = 0
            snippets = []

            # Title match (high weight)
            if query in meta["title"].lower():
                score += 10

            # Speaker name match
            for spk in meta["speakers"]:
                if query in spk.lower():
                    score += 5

            # Transcript keyword match — collect matching snippets
            for seg in meta["segments"]:
                text = seg.get("text", "").lower()
                if query in text:
                    score += 1
                    if len(snippets) < 3:
                        # Highlight the match
                        original = seg.get("text", "")
                        start_idx = text.find(query)
                        snippet_start = max(0, start_idx - 30)
                        snippet_end = min(len(original), start_idx + len(query) + 60)
                        snippet = ("..." if snippet_start > 0 else "") + original[snippet_start:snippet_end] + ("..." if snippet_end < len(original) else "")
                        snippets.append({
                            "speaker": seg.get("speaker", "UNKNOWN"),
                            "start": seg.get("start", 0),
                            "snippet": snippet,
                        })

            if score > 0:
                results.append({
                    "id": meta["id"],
                    "title": meta["title"],
                    "date": meta["date"],
                    "speaker_count": len(meta["speakers"]),
                    "score": score,
                    "snippets": snippets,
                })
        except Exception as e:
            logger.warning("Search error for %s: %s", meeting_dir.name, e)
            continue

    # Sort by relevance score
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:limit]

    return {
        "query": q,
        "results": results,
        "total": len(results),
    }
