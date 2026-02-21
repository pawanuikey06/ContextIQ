import json
from pathlib import Path
from datetime import datetime
from typing import Dict
 
 
class MeetingStorageService:
    def __init__(self, base_dir="app/data/meetings"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
 
    def save(self, meeting_id: str, data: Dict) -> str:
        payload = {
            "meeting_id": meeting_id,
            "created_at": datetime.utcnow().isoformat(),
            **data
        }
 
        file_path = self.base_dir / f"{meeting_id}.json"
 
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
 
        return str(file_path)
 
 