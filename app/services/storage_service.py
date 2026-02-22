"""
Meeting storage service.
Saves transcript JSON to storage/{meeting_id}/transcript.json.
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict

logger = logging.getLogger(__name__)


class MeetingStorageService:
    """Saves and retrieves meeting transcripts from disk."""

    def __init__(self, base_dir: str = "storage"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, meeting_id: str, data: Dict) -> str:
        """
        Save transcript data to storage/{meeting_id}/transcript.json.

        Args:
            meeting_id: UUID of the meeting
            data: full transcript dict (meeting_id, audio_path, segments, speakers)

        Returns:
            Path to the saved JSON file
        """
        meeting_dir = self.base_dir / meeting_id
        meeting_dir.mkdir(parents=True, exist_ok=True)

        file_path = meeting_dir / "transcript.json"

        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            **data
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        # Save meeting metadata with human-readable date/day
        now_local = datetime.now()
        metadata = {
            "meeting_id": meeting_id,
            "processed_at": now_local.isoformat(),
            "processed_date": now_local.strftime("%B %d, %Y"),
            "processed_day": now_local.strftime("%A"),
            "processed_time": now_local.strftime("%I:%M %p"),
        }
        meta_path = meeting_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"[{meeting_id}] Transcript saved to {file_path}")
        return str(file_path)