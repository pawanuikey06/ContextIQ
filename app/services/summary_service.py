"""
Meeting Summary Service.
Uses OpenAI GPT-4o-mini to generate:
- Speaker-wise summaries (English)
- Overall meeting summary (English)
- Overall meeting summary (Hindi)
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)

# GPT-4o-mini: fast, cheap (~$0.15/1M input tokens), great multilingual
MODEL = "gpt-4o-mini"
STORAGE_DIR = Path("storage")


class MeetingSummaryService:
    """Generates meeting summaries from transcript JSON using OpenAI."""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env")

        self.client = OpenAI(api_key=api_key)
        logger.info("MeetingSummaryService initialized (model=%s)", MODEL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def summarize(self, meeting_id: str, force: bool = False) -> dict:
        """
        Generate (or return cached) summaries for a meeting.

        Args:
            meeting_id: UUID of the meeting
            force: regenerate even if summary.json exists

        Returns:
            dict with meeting_id, speaker_summaries_en,
            overall_summary_en, overall_summary_hi
        """
        summary_path = STORAGE_DIR / meeting_id / "summary.json"

        # Return cached summary unless forced
        if not force and summary_path.exists():
            logger.info("[%s] Returning cached summary", meeting_id)
            with open(summary_path, "r", encoding="utf-8") as f:
                return json.load(f)

        # Load transcript
        transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
        if not transcript_path.exists():
            raise FileNotFoundError(
                f"Transcript not found for meeting {meeting_id}. Run transcription first."
            )

        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript = json.load(f)

        segments = transcript.get("segments", [])
        speakers = transcript.get("speakers", {})

        if not segments:
            raise ValueError(f"No segments found in transcript for meeting {meeting_id}")

        # Build the full conversation text for context
        full_text = self._build_conversation_text(segments)

        # Generate summaries
        logger.info("[%s] Generating speaker-wise summaries...", meeting_id)
        speaker_summaries = self._generate_speaker_summaries(speakers)

        logger.info("[%s] Generating overall English summary...", meeting_id)
        overall_en = self._generate_overall_summary_en(full_text)

        logger.info("[%s] Generating overall Hindi summary...", meeting_id)
        overall_hi = self._generate_overall_summary_hi(full_text)

        result = {
            "meeting_id": meeting_id,
            "speaker_summaries_en": speaker_summaries,
            "overall_summary_en": overall_en,
            "overall_summary_hi": overall_hi,
        }

        # Save to disk
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info("[%s] Summary saved to %s", meeting_id, summary_path)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _build_conversation_text(self, segments: list) -> str:
        """Build a readable conversation string from segments."""
        lines = []
        for seg in segments:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "").strip()
            if text:
                lines.append(f"{speaker}: {text}")
        return "\n".join(lines)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Make a chat completion call to OpenRouter with retries."""
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info("LLM call attempt %d/%d", attempt, MAX_RETRIES)
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=2048,
                )
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                raise ValueError("Empty response from LLM")
            except Exception as e:
                last_error = e
                logger.warning("LLM attempt %d failed: %s", attempt, str(e)[:200])
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt  # 2s, 4s, 8s
                    logger.info("Retrying in %ds...", wait)
                    time.sleep(wait)

        raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {last_error}")

    def _generate_speaker_summaries(self, speakers: dict) -> dict:
        """Generate a summary for each speaker's contributions."""
        summaries = {}

        for speaker, segments in speakers.items():
            combined_text = " ".join(
                seg.get("text", "").strip() for seg in segments if seg.get("text", "").strip()
            )
            if not combined_text:
                summaries[speaker] = "No meaningful contributions."
                continue

            system_prompt = (
                "You are an expert meeting analyst. "
                "Summarize the following speaker's contributions in a meeting. "
                "Capture: key decisions, action items, opinions, and responsibilities. "
                "Be concise (3-5 sentences). Output ONLY the summary text, nothing else."
            )
            user_prompt = f"Speaker: {speaker}\n\nTheir statements:\n{combined_text}"

            summaries[speaker] = self._call_llm(system_prompt, user_prompt)

        return summaries

    def _generate_overall_summary_en(self, full_text: str) -> str:
        """Generate an overall meeting summary in English."""
        system_prompt = (
            "You are an expert meeting analyst. "
            "Provide a concise overall meeting summary in English. Include:\n"
            "- High-level summary (2-3 sentences)\n"
            "- Key discussion points\n"
            "- Decisions made\n"
            "- Action items\n"
            "Output ONLY the summary text in plain text, no JSON."
        )
        user_prompt = f"Meeting transcript:\n\n{full_text}"
        return self._call_llm(system_prompt, user_prompt)

    def _generate_overall_summary_hi(self, full_text: str) -> str:
        """Generate an overall meeting summary in Hindi."""
        system_prompt = (
            "You are an expert meeting analyst. "
            "Provide a concise overall meeting summary in HINDI (हिंदी). Rules:\n"
            "- Write in natural, professional Hindi\n"
            "- Do NOT translate word-by-word from English\n"
            "- Keep it concise (same level of detail as an English summary)\n"
            "- Include: high-level summary, key points, decisions, action items\n"
            "- Output ONLY the Hindi summary text, no English, no JSON."
        )
        user_prompt = f"Meeting transcript:\n\n{full_text}"
        return self._call_llm(system_prompt, user_prompt)
