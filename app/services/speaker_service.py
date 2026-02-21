"""
Speaker transcript builder.
Groups transcription segments by speaker, preserving timestamps.
"""
from collections import defaultdict
from typing import List, Dict


class SpeakerTranscriptBuilder:
    """
    Builds speaker-wise transcript from diarized segments.
    Output format matches the mandatory JSON structure:
    {
        "Speaker 1": [
            { "start": 0.0, "end": 4.2, "text": "Hello everyone" }
        ]
    }
    """

    def build(self, segments: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group segments by speaker with timestamps preserved.

        Args:
            segments: list of dicts with keys: start, end, speaker, text

        Returns:
            dict mapping speaker name → list of { start, end, text }
        """
        if not isinstance(segments, list):
            raise TypeError("segments must be a list of dictionaries")

        speaker_map = defaultdict(list)

        for seg in segments:
            if not isinstance(seg, dict):
                continue

            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "").strip()

            if text:
                speaker_map[speaker].append({
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", 0.0),
                    "text": text
                })

        return dict(speaker_map)