"""
Meeting Summary Service.
Uses Hugging Face free Inference API (Zephyr 7B) to generate:
- Speaker-wise summaries (English)
- Overall meeting summary (English)
- Overall meeting summary (Hindi)
"""
import os
import json
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()
logger = logging.getLogger(__name__)

MODEL = "HuggingFaceH4/zephyr-7b-beta"
STORAGE_DIR = Path("storage")
MAX_RETRIES = 3


class MeetingSummaryService:
    """Generates meeting summaries using HuggingFace Inference API."""

    def __init__(self):
        token = os.getenv("HF_TOKEN")
        if not token:
            raise ValueError("HF_TOKEN not found in .env")

        self.client = InferenceClient(token=token)
        logger.info("MeetingSummaryService initialized (model=%s)", MODEL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def _load_speaker_map(self, meeting_id: str) -> dict:
        """Load speaker_map.json for a meeting, return {} if absent."""
        map_path = STORAGE_DIR / meeting_id / "speaker_map.json"
        if map_path.exists():
            with open(map_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _apply_speaker_map(self, text: str, speaker_map: dict) -> str:
        """Replace all SPEAKER_XX IDs with mapped real names in text."""
        for spk_id, real_name in speaker_map.items():
            text = text.replace(spk_id, real_name)
        return text

    def summarize(
        self,
        meeting_id: str,
        force: bool = False,
        extra_prompt: str = "",
    ) -> dict:
        summary_path = STORAGE_DIR / meeting_id / "summary.json"

        if not force and not extra_prompt and summary_path.exists():
            logger.info("[%s] Returning cached summary", meeting_id)
            with open(summary_path, "r", encoding="utf-8") as f:
                return json.load(f)

        transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
        if not transcript_path.exists():
            raise FileNotFoundError(
                f"Transcript not found for meeting {meeting_id}. "
                "Run transcription first."
            )

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        segments = transcript.get("segments", [])
        speakers = transcript.get("speakers", {})

        if not segments:
            raise ValueError(
                f"No segments in transcript for meeting {meeting_id}"
            )

        # Load speaker name mappings
        speaker_map = self._load_speaker_map(meeting_id)
        logger.info("[%s] Speaker map: %s", meeting_id, speaker_map)

        full_text = self._build_conversation_text(segments, speaker_map)

        logger.info("[%s] Generating speaker-wise summaries...", meeting_id)
        speaker_summaries = self._generate_speaker_summaries(
            speakers, speaker_map, extra_prompt
        )

        logger.info("[%s] Generating overall English summary...", meeting_id)
        overall_en = self._generate_overall_summary_en(full_text, extra_prompt)

        logger.info("[%s] Generating overall Hindi summary...", meeting_id)
        overall_hi = self._generate_overall_summary_hi(full_text, extra_prompt)

        result = {
            "meeting_id": meeting_id,
            "speaker_summaries_en": speaker_summaries,
            "overall_summary_en": overall_en,
            "overall_summary_hi": overall_hi,
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info("[%s] Summary saved to %s", meeting_id, summary_path)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _build_conversation_text(
        self, segments: list, speaker_map: dict = None
    ) -> str:
        lines = []
        smap = speaker_map or {}
        for seg in segments:
            speaker = seg.get("speaker", "UNKNOWN")
            speaker = smap.get(speaker, speaker)  # Use mapped name
            text = seg.get("text", "").strip()
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call HuggingFace Inference API with retry logic."""
        last_error = None
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info("HF call attempt %d/%d", attempt, MAX_RETRIES)
                response = self.client.chat_completion(
                    model=MODEL,
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.3,
                )
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                raise ValueError("Empty response from HF")
            except Exception as e:
                last_error = e
                logger.warning(
                    "HF attempt %d failed: %s", attempt, str(e)[:200]
                )
                if attempt < MAX_RETRIES:
                    time.sleep(3)

        raise RuntimeError(
            f"HF call failed after {MAX_RETRIES} attempts: {last_error}"
        )

    def _generate_speaker_summaries(
        self, speakers: dict, speaker_map: dict = None, extra_prompt: str = ""
    ) -> dict:
        summaries = {}
        smap = speaker_map or {}
        for speaker, segs in speakers.items():
            display = smap.get(speaker, speaker)  # Use mapped name
            combined = " ".join(
                s.get("text", "").strip()
                for s in segs
                if s.get("text", "").strip()
            )
            if not combined:
                summaries[display] = "No meaningful contributions."
                continue

            system_prompt = (
                "You are an expert meeting analyst. "
                "Summarize the following speaker's contributions. "
                "Capture: key decisions, action items, opinions, "
                "and responsibilities. "
                "Be concise (3-5 sentences). "
                "Output ONLY the summary text."
            )
            if extra_prompt:
                system_prompt += f" Additional instructions: {extra_prompt}"

            user_prompt = (
                f"Speaker: {display}\n\n"
                f"Their statements:\n{combined}"
            )
            summaries[display] = self._call_llm(system_prompt, user_prompt)
        return summaries

    def _generate_overall_summary_en(
        self, full_text: str, extra_prompt: str = ""
    ) -> str:
        system_prompt = (
            "You are an expert meeting analyst. "
            "Provide a concise overall meeting summary in English. "
            "Include:\n"
            "- High-level summary (2-3 sentences)\n"
            "- Key discussion points\n"
            "- Decisions made\n"
            "- Action items\n"
            "Output ONLY the summary text in plain text."
        )
        if extra_prompt:
            system_prompt += f" Additional instructions: {extra_prompt}"

        return self._call_llm(
            system_prompt, f"Meeting transcript:\n\n{full_text}"
        )

    def _generate_overall_summary_hi(
        self, full_text: str, extra_prompt: str = ""
    ) -> str:
        system_prompt = (
            "You are an expert meeting analyst. "
            "Provide a concise overall meeting summary in HINDI "
            "(हिंदी). Rules:\n"
            "- Write in natural, professional Hindi\n"
            "- Do NOT translate word-by-word from English\n"
            "- Keep it concise\n"
            "- Include: high-level summary, key points, decisions, "
            "action items\n"
            "- Output ONLY the Hindi summary text, no English, no JSON."
        )
        if extra_prompt:
            system_prompt += f" Additional instructions: {extra_prompt}"

        return self._call_llm(
            system_prompt, f"Meeting transcript:\n\n{full_text}"
        )
