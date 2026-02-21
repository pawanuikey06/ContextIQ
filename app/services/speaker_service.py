from collections import defaultdict
from typing import List, Dict
 
 
class SpeakerTranscriptBuilder:
    """
    Builds speaker-wise transcript from WhisperX diarized segments
    Expected segment format:
    {
        "start": float,
        "end": float,
        "speaker": str,
        "text": str
    }
    """
 
    def build(self, segments: List[Dict]) -> Dict[str, str]:
        if not isinstance(segments, list):
            raise TypeError("segments must be a list of dictionaries")
 
        speaker_map = defaultdict(list)
 
        for seg in segments:
            if not isinstance(seg, dict):
                continue
 
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "").strip()
 
            if text:
                speaker_map[speaker].append(text)
 
        return {
            speaker: " ".join(texts)
            for speaker, texts in speaker_map.items()
        }
 