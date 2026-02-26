"""
Meeting Insights Service — AI-powered analytics.
  - Action Items & Decisions extraction
  - Auto Meeting Title generation

Uses Groq Llama 3.3 70B for all LLM calls.
"""
import os
import json
import logging
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

STORAGE_DIR = Path("storage")
MODEL = "llama-3.3-70b-versatile"


class MeetingInsightsService:
    """Extract structured insights from meeting transcripts using LLMs."""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
        self.client = Groq(api_key=api_key)
        logger.info("MeetingInsightsService initialized (model=%s)", MODEL)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq LLM and return the response text."""
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    def _load_transcript_text(self, meeting_id: str) -> tuple[str, list]:
        """Load transcript and return formatted text + segments list."""
        transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
        if not transcript_path.exists():
            raise FileNotFoundError(
                f"Transcript not found for meeting {meeting_id}. "
                "Run transcription first."
            )

        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        segments = data.get("segments", [])

        # Apply speaker map if available
        speaker_map = {}
        map_path = STORAGE_DIR / meeting_id / "speaker_map.json"
        if map_path.exists():
            with open(map_path, "r", encoding="utf-8") as f:
                speaker_map = json.load(f)

        lines = []
        for seg in segments:
            speaker = speaker_map.get(seg.get("speaker", ""), seg.get("speaker", "UNKNOWN"))
            lines.append(f"{speaker}: {seg.get('text', '')}")

        return "\n".join(lines), segments

    # ------------------------------------------------------------------
    # Feature 1: Action Items & Decisions
    # ------------------------------------------------------------------
    def extract_action_items(self, meeting_id: str, force: bool = False) -> dict:
        """
        Extract action items, decisions, and key takeaways from a meeting.
        Results cached in storage/{meeting_id}/action_items.json.
        """
        cache_path = STORAGE_DIR / meeting_id / "action_items.json"

        # Return cached if available
        if cache_path.exists() and not force:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            logger.info("[%s] Action items returned from cache", meeting_id)
            return cached

        transcript_text, _ = self._load_transcript_text(meeting_id)

        system_prompt = """You are a senior project manager with 15+ years of experience. Extract ALL action items, decisions, and insights from the meeting transcript with thorough detail.

Return a JSON object with EXACTLY this format (no markdown, no code fences, just raw JSON):
{
  "action_items": [
    {
      "task": "Detailed description of what needs to be done — be specific and elaborate. Include context about WHY this task matters.",
      "assigned_to": "Person name or 'Unassigned'",
      "deadline": "Mentioned deadline or 'Not specified'",
      "priority": "high/medium/low",
      "category": "development/design/research/communication/testing/documentation/infrastructure/other",
      "context": "Brief context of why this task was discussed and what problem it solves",
      "success_criteria": "How to know this task is complete",
      "dependencies": ["Other tasks or prerequisites this depends on"],
      "mentioned_by": "Who raised or proposed this task"
    }
  ],
  "decisions": [
    {
      "decision": "What was decided — be detailed and specific",
      "made_by": "Who made or proposed it",
      "context": "Brief context of why this decision was needed",
      "impact": "Expected impact or consequence of this decision",
      "alternatives_considered": "Any alternative options that were discussed before reaching this decision"
    }
  ],
  "key_takeaways": [
    {
      "takeaway": "Important insight or highlight from the meeting",
      "category": "technical/strategic/operational/risk",
      "importance": "high/medium/low"
    }
  ],
  "follow_ups": [
    {
      "item": "What needs follow-up",
      "owner": "Person responsible for following up",
      "urgency": "immediate/this-week/next-meeting",
      "context": "Why this needs follow-up"
    }
  ],
  "risks_identified": [
    {
      "risk": "Potential risk or blocker mentioned",
      "impact": "high/medium/low",
      "mitigation": "Any proposed mitigation discussed"
    }
  ]
}

RULES:
1. Extract REAL action items — both explicitly stated AND clearly implied from the discussion
2. Be ELABORATE and DETAILED — minimum 2 sentences per task description
3. Infer reasonable deadlines from context clues (e.g., "by next sprint", "ASAP")
4. Assign priority based on urgency language ("ASAP"=high, "when you can"=low, "important"=medium)
5. Categorize each action item by type (development, design, testing, etc.)
6. If someone volunteers or is asked to do something, capture it as an action item
7. Look for implicit action items (e.g., "we should probably..." or "someone needs to...")
8. Return ONLY valid JSON, nothing else"""

        user_prompt = f"MEETING TRANSCRIPT:\n\n{transcript_text}"

        logger.info("[%s] Extracting action items via Groq...", meeting_id)
        raw_response = self._call_llm(system_prompt, user_prompt)

        # Parse JSON response
        try:
            # Handle potential markdown code fences
            cleaned = raw_response
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            result = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            logger.warning("[%s] LLM returned non-JSON, using fallback", meeting_id)
            result = {
                "action_items": [],
                "decisions": [],
                "key_takeaways": [],
                "follow_ups": [],
                "risks_identified": [],
            }

        result["meeting_id"] = meeting_id

        # Cache result
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(
            "[%s] Action items extracted: %d items, %d decisions",
            meeting_id,
            len(result.get("action_items", [])),
            len(result.get("decisions", [])),
        )
        return result

    # ------------------------------------------------------------------
    # Feature 2: Auto Meeting Title
    # ------------------------------------------------------------------
    def generate_title(self, meeting_id: str, force: bool = False) -> dict:
        """
        Auto-generate a concise meeting title from the transcript.
        Saves to metadata.json.
        """
        meta_path = STORAGE_DIR / meeting_id / "metadata.json"
        meta = {}
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

        # Return cached title if available and not forcing
        if meta.get("auto_title") and not force:
            logger.info("[%s] Title returned from cache", meeting_id)
            return {
                "meeting_id": meeting_id,
                "title": meta["auto_title"],
                "cached": True,
            }

        transcript_text, _ = self._load_transcript_text(meeting_id)

        # Use only first 3000 chars to save tokens
        excerpt = transcript_text[:3000]

        system_prompt = """You are a meeting title generator. Given a meeting transcript excerpt, generate a short, descriptive title.

RULES:
1. Maximum 8 words
2. Be specific — mention the actual topic, not generic like "Team Meeting"
3. Use title case
4. Return ONLY the title text, nothing else
5. Examples of good titles:
   - "Q4 Budget Review and Approval"
   - "Sprint 12 Planning and Task Assignment"
   - "Client Onboarding Process Discussion"
   - "API Performance Issues Debugging Session"
"""

        user_prompt = f"TRANSCRIPT EXCERPT:\n\n{excerpt}"

        logger.info("[%s] Generating title via Groq...", meeting_id)
        title = self._call_llm(system_prompt, user_prompt)

        # Clean up — remove quotes, newlines
        title = title.strip().strip('"').strip("'").strip()

        # Save to metadata
        meta["auto_title"] = title
        if not meta.get("title"):
            meta["title"] = title  # Set as main title if none exists

        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        logger.info("[%s] Auto title: '%s'", meeting_id, title)
        return {
            "meeting_id": meeting_id,
            "title": title,
            "cached": False,
        }

    # ------------------------------------------------------------------
    # Feature 3: Follow-Up Email Draft
    # ------------------------------------------------------------------
    def generate_followup_email(self, meeting_id: str, force: bool = False) -> dict:
        """
        Generate a professional follow-up email from the meeting.
        Combines: title + summary + action items + decisions.
        Cached in storage/{meeting_id}/followup_email.json.
        """
        cache_path = STORAGE_DIR / meeting_id / "followup_email.json"

        if cache_path.exists() and not force:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            logger.info("[%s] Follow-up email returned from cache", meeting_id)
            return cached

        # Gather all available data
        transcript_text, _ = self._load_transcript_text(meeting_id)

        # Load summary if available
        summary_text = ""
        summary_path = STORAGE_DIR / meeting_id / "summary.json"
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
            summary_text = summary_data.get("overall_summary_en", "")

        # Load action items if available
        action_items_text = ""
        ai_path = STORAGE_DIR / meeting_id / "action_items.json"
        if ai_path.exists():
            with open(ai_path, "r", encoding="utf-8") as f:
                ai_data = json.load(f)
            items = ai_data.get("action_items", [])
            decisions = ai_data.get("decisions", [])
            if items:
                action_items_text += "ACTION ITEMS:\n"
                for item in items:
                    action_items_text += f"- {item['task']} (Assigned: {item.get('assigned_to', 'TBD')}, Deadline: {item.get('deadline', 'TBD')})\n"
            if decisions:
                action_items_text += "\nDECISIONS:\n"
                for d in decisions:
                    action_items_text += f"- {d['decision']}\n"

        # Load meeting title
        title = f"Meeting {meeting_id[:8]}"
        meta_path = STORAGE_DIR / meeting_id / "metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            title = meta.get("auto_title", meta.get("title", title))

        # Load participants (speakers)
        participants = []
        transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
        if transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                t_data = json.load(f)
            participants = list(t_data.get("speakers", {}).keys())

        # Apply speaker map to participants
        map_path = STORAGE_DIR / meeting_id / "speaker_map.json"
        if map_path.exists():
            with open(map_path, "r", encoding="utf-8") as f:
                smap = json.load(f)
            participants = [smap.get(p, p) for p in participants]

        system_prompt = """You are a professional executive assistant drafting a follow-up email after a meeting.

Write a concise, professional follow-up email that includes:
1. A warm greeting
2. Brief meeting recap (2-3 sentences max)
3. Key decisions made (bullet points)
4. Action items with owners and deadlines (table or bullets)
5. Any follow-ups needed
6. A professional closing

RULES:
1. Be concise — busy professionals won't read long emails
2. Use bullet points, not paragraphs
3. Sound human and warm, not robotic
4. Include specific names, dates, and details from the meeting
5. Return the email in this exact JSON format:
{
  "subject": "Follow-Up: Meeting Title — Key Action Items",
  "body": "The full email body text with line breaks",
  "recipients_suggested": ["list of participant names"]
}
6. Return ONLY valid JSON, nothing else"""

        context_parts = [f"MEETING TITLE: {title}"]
        if participants:
            context_parts.append(f"PARTICIPANTS: {', '.join(participants)}")
        if summary_text:
            context_parts.append(f"MEETING SUMMARY:\n{summary_text}")
        if action_items_text:
            context_parts.append(f"\n{action_items_text}")
        context_parts.append(f"\nTRANSCRIPT (for details):\n{transcript_text[:3000]}")

        user_prompt = "\n\n".join(context_parts)

        logger.info("[%s] Generating follow-up email via Groq...", meeting_id)
        raw_response = self._call_llm(system_prompt, user_prompt)

        # Parse
        try:
            cleaned = raw_response
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            result = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            result = {
                "subject": f"Follow-Up: {title}",
                "body": raw_response,
                "recipients_suggested": participants,
            }

        result["meeting_id"] = meeting_id

        # Cache
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info("[%s] Follow-up email drafted (subject: %s)", meeting_id, result.get("subject", ""))
        return result

    # ------------------------------------------------------------------
    # Feature 4: Requirement Extraction (Optional per meeting)
    # ------------------------------------------------------------------
    def extract_requirements(self, meeting_id: str, force: bool = False) -> dict:
        """
        Extract requirements, user stories, and constraints from a meeting.
        Cached in storage/{meeting_id}/requirements.json.
        """
        cache_path = STORAGE_DIR / meeting_id / "requirements.json"

        if cache_path.exists() and not force:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            logger.info("[%s] Requirements returned from cache", meeting_id)
            return cached

        transcript_text, _ = self._load_transcript_text(meeting_id)

        system_prompt = """You are a senior business analyst with 15+ years of experience in requirements engineering. Extract ALL requirements discussed in this meeting transcript with thorough detail.

Return a JSON object with EXACTLY this format (no markdown, no code fences, just raw JSON):
{
  "summary": "2-3 sentence overview of what this meeting requires",
  "functional_requirements": [
    {
      "id": "FR-001",
      "title": "Short descriptive title",
      "description": "Detailed description of the requirement — be specific and elaborate. Include context about WHY this is needed, WHAT problem it solves, and HOW it should work.",
      "acceptance_criteria": ["Testable condition 1 that proves this requirement is met", "Testable condition 2"],
      "priority": "must-have/should-have/nice-to-have",
      "priority_rationale": "Why this priority level was assigned",
      "raised_by": "Person name who raised or proposed this",
      "agreed_by": ["Names of people who agreed"],
      "status": "proposed/agreed/needs-discussion",
      "dependencies": ["FR-002"],
      "implementation_notes": "Any technical implementation hints discussed",
      "risk": "What could go wrong if this isn't implemented or is implemented incorrectly"
    }
  ],
  "non_functional_requirements": [
    {
      "id": "NFR-001",
      "title": "Short title",
      "description": "Detailed description of the non-functional requirement",
      "category": "performance/security/scalability/usability/reliability/compliance",
      "measurable_criteria": "How to measure if this NFR is met (e.g. response time < 2s)",
      "impact": "What happens if this NFR is not met"
    }
  ],
  "user_stories": [
    {
      "story": "As a [specific role], I want [specific feature/capability], so that [specific business benefit]",
      "acceptance_criteria": ["Given X, When Y, Then Z"]
    }
  ],
  "constraints": [
    {
      "constraint": "Description of the constraint",
      "type": "budget/timeline/technical/resource/regulatory",
      "impact": "How this constraint affects the project"
    }
  ],
  "assumptions": [
    "Assumption made during the discussion that needs validation"
  ],
  "risks": [
    {
      "risk": "Description of the risk",
      "likelihood": "high/medium/low",
      "impact": "high/medium/low",
      "mitigation": "Proposed mitigation if discussed"
    }
  ],
  "open_questions": [
    {
      "question": "Unresolved question",
      "raised_by": "Person who raised it",
      "needs_answer_from": "Who should answer this"
    }
  ]
}

RULES:
1. Only extract REAL requirements explicitly discussed — do not invent
2. Be ELABORATE and DETAILED in descriptions — write 2-3 sentences minimum per requirement
3. If this meeting has no requirements, return empty arrays
4. Use auto-incrementing IDs (FR-001, FR-002, NFR-001, etc.)
5. Extract implicit requirements too (e.g. if someone says 'we need it to be fast', that's a performance NFR)
6. Map dependencies between requirements where they exist
7. Include ALL acceptance criteria you can derive from the discussion
8. Return ONLY valid JSON, nothing else"""

        user_prompt = f"MEETING TRANSCRIPT:\n\n{transcript_text}"

        logger.info("[%s] Extracting requirements via Groq...", meeting_id)
        raw_response = self._call_llm(system_prompt, user_prompt)

        try:
            cleaned = raw_response
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            result = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            logger.warning("[%s] LLM returned non-JSON for requirements", meeting_id)
            result = {
                "summary": "",
                "functional_requirements": [],
                "non_functional_requirements": [],
                "user_stories": [],
                "constraints": [],
                "assumptions": [],
                "risks": [],
                "open_questions": [{"question": raw_response[:500], "raised_by": "", "needs_answer_from": ""}],
            }

        result["meeting_id"] = meeting_id

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(
            "[%s] Requirements extracted: %d functional, %d non-functional",
            meeting_id,
            len(result.get("functional_requirements", [])),
            len(result.get("non_functional_requirements", [])),
        )
        return result

    # ------------------------------------------------------------------
    # Feature 5: Documentation Generation (Optional per meeting)
    # ------------------------------------------------------------------
    def generate_documentation(self, meeting_id: str, force: bool = False) -> dict:
        """
        Generate structured meeting documentation / MoM.
        Cached in storage/{meeting_id}/documentation.json.
        """
        cache_path = STORAGE_DIR / meeting_id / "documentation.json"

        if cache_path.exists() and not force:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            logger.info("[%s] Documentation returned from cache", meeting_id)
            return cached

        transcript_text, _ = self._load_transcript_text(meeting_id)

        # Load title
        title = f"Meeting {meeting_id[:8]}"
        meta_path = STORAGE_DIR / meeting_id / "metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            title = meta.get("auto_title", meta.get("title", title))

        system_prompt = """You are a senior technical writer creating comprehensive, formal meeting documentation (Minutes of Meeting). Your documentation should be THOROUGH and ELABORATE — not just bullet points but detailed narrative descriptions.

Return a JSON object with EXACTLY this format (no markdown, no code fences, just raw JSON):
{
  "title": "Meeting title",
  "executive_summary": "A comprehensive 3-5 sentence executive summary covering the purpose of the meeting, key discussion points, major decisions made, and the overall outcome. This should be detailed enough that someone who missed the meeting can understand what happened.",
  "attendees": [
    {
      "name": "Person name",
      "role": "Their role/title as inferred from discussion (e.g. IT Head, Revenue Manager, Project Lead)"
    }
  ],
  "objective": "Detailed description of the meeting's purpose — what problem was being addressed and why a meeting was needed",
  "topics_discussed": [
    {
      "topic": "Topic name",
      "summary": "Detailed 3-5 sentence summary of what was discussed under this topic. Include specific numbers, data points, examples mentioned. Don't just list facts — explain the flow of discussion.",
      "key_points": ["Specific point 1 with details", "Specific point 2 with details"],
      "speakers_involved": ["Person 1", "Person 2"],
      "outcome": "What was the conclusion or result of this discussion topic"
    }
  ],
  "technical_details": [
    {
      "area": "Technical area discussed",
      "details": "Detailed technical description — include system names, integration points, architecture decisions, implementation approaches. Be specific.",
      "tools_mentioned": ["Tool 1", "Tool 2"],
      "implementation_approach": "How the team plans to implement this technically"
    }
  ],
  "decisions_and_rationale": [
    {
      "decision": "Clear statement of what was decided",
      "rationale": "Detailed explanation of WHY this decision was made — what factors were considered",
      "alternatives_discussed": "Other options that were considered and why they were rejected",
      "decided_by": "Who made or proposed the final decision",
      "impact": "What impact this decision will have"
    }
  ],
  "agreements": [
    "Specific agreement reached between participants"
  ],
  "disagreements": [
    {
      "topic": "What was the disagreement about",
      "parties": ["Person 1", "Person 2"],
      "resolution": "How it was resolved or if it's still open"
    }
  ],
  "next_steps": [
    {
      "action": "Clear description of what needs to be done",
      "owner": "Person responsible",
      "deadline": "When it should be done if mentioned"
    }
  ],
  "stakeholder_impact": [
    {
      "stakeholder": "Who is affected (team, department, client, etc.)",
      "impact": "How they are affected by the decisions made"
    }
  ],
  "parking_lot": [
    "Items deferred for future discussion with context on why they were deferred"
  ],
  "glossary": [
    {
      "term": "Technical term or acronym used",
      "definition": "What it means in context"
    }
  ]
}

RULES:
1. Be THOROUGH and ELABORATE — write detailed descriptions, not one-liners
2. Group by topics logically and chronologically
3. Include ALL technical details discussed with specific system/tool names
4. Capture the FLOW of conversation — who said what and how the discussion evolved
5. Include specific numbers, dates, and data points mentioned
6. Extract ALL attendees and infer their roles from the conversation
7. If a section has no content, return an empty array
8. The executive_summary should be comprehensive enough to stand alone
9. Return ONLY valid JSON, nothing else"""

        user_prompt = f"MEETING TITLE: {title}\n\nMEETING TRANSCRIPT:\n\n{transcript_text}"

        logger.info("[%s] Generating documentation via Groq...", meeting_id)
        raw_response = self._call_llm(system_prompt, user_prompt)

        try:
            cleaned = raw_response
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            result = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            logger.warning("[%s] LLM returned non-JSON for docs", meeting_id)
            result = {
                "title": title,
                "executive_summary": "",
                "attendees": [],
                "objective": "",
                "topics_discussed": [],
                "technical_details": [],
                "decisions_and_rationale": [],
                "agreements": [],
                "disagreements": [],
                "next_steps": [],
                "stakeholder_impact": [],
                "parking_lot": [],
                "glossary": [],
            }

        result["meeting_id"] = meeting_id

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info("[%s] Documentation generated: %d topics", meeting_id, len(result.get("topics_discussed", [])))
        return result

    # ------------------------------------------------------------------
    # Feature 6: Sentiment Analysis (Optional per meeting)
    # ------------------------------------------------------------------
    def analyze_sentiment(self, meeting_id: str, force: bool = False) -> dict:
        """
        Analyze sentiment of each speaker segment in the meeting.
        Cached in storage/{meeting_id}/sentiment.json.
        """
        cache_path = STORAGE_DIR / meeting_id / "sentiment.json"

        if cache_path.exists() and not force:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            logger.info("[%s] Sentiment returned from cache", meeting_id)
            return cached

        transcript_text, segments = self._load_transcript_text(meeting_id)

        # Build a condensed version for sentiment analysis
        segment_lines = []
        for idx, seg in enumerate(segments):
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "").strip()
            start = seg.get("start", 0)
            if text:
                segment_lines.append(f"[{idx}] {speaker} ({start}s): {text}")

        segments_block = "\n".join(segment_lines)

        system_prompt = """You are a sentiment analysis expert. Analyze the sentiment of each segment in the meeting transcript.

For each segment, determine:
- sentiment: "positive", "negative", or "neutral"
- score: a number from -1.0 (most negative) to 1.0 (most positive), 0 is neutral
- emotion: the primary emotion (e.g. "enthusiastic", "concerned", "frustrated", "agreeable", "neutral", "excited", "skeptical")

Return a JSON object with EXACTLY this format (no markdown, no code fences, just raw JSON):
{
  "segments": [
    {
      "index": 0,
      "sentiment": "positive",
      "score": 0.7,
      "emotion": "enthusiastic"
    }
  ],
  "overall_sentiment": "positive",
  "overall_score": 0.5,
  "mood_summary": "One sentence describing the overall mood of the meeting",
  "highlights": {
    "most_positive": "Brief quote or moment that was most positive",
    "most_negative": "Brief quote or moment that was most negative or N/A",
    "turning_points": ["Any moment where mood shifted significantly"]
  }
}

RULES:
1. Analyze ALL segments — one entry per segment index
2. Be accurate — don't default everything to neutral
3. Pick up on subtle cues: agreement, pushback, excitement, frustration
4. Return ONLY valid JSON, nothing else"""

        user_prompt = f"MEETING SEGMENTS:\n\n{segments_block}"

        logger.info("[%s] Analyzing sentiment via Groq...", meeting_id)
        raw_response = self._call_llm(system_prompt, user_prompt)

        try:
            cleaned = raw_response
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]
            result = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            logger.warning("[%s] LLM returned non-JSON for sentiment", meeting_id)
            result = {
                "segments": [],
                "overall_sentiment": "neutral",
                "overall_score": 0.0,
                "mood_summary": "Could not analyze sentiment.",
                "highlights": {"most_positive": "N/A", "most_negative": "N/A", "turning_points": []},
            }

        # Enrich segments with original data
        enriched_segments = []
        sentiment_map = {s["index"]: s for s in result.get("segments", []) if "index" in s}
        for idx, seg in enumerate(segments):
            s_data = sentiment_map.get(idx, {"sentiment": "neutral", "score": 0.0, "emotion": "neutral"})
            enriched_segments.append({
                "index": idx,
                "speaker": seg.get("speaker", "UNKNOWN"),
                "start": seg.get("start", 0),
                "end": seg.get("end", 0),
                "text": seg.get("text", ""),
                "sentiment": s_data.get("sentiment", "neutral"),
                "score": s_data.get("score", 0.0),
                "emotion": s_data.get("emotion", "neutral"),
            })

        result["segments"] = enriched_segments
        result["meeting_id"] = meeting_id

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        pos = sum(1 for s in enriched_segments if s["sentiment"] == "positive")
        neg = sum(1 for s in enriched_segments if s["sentiment"] == "negative")
        logger.info("[%s] Sentiment analyzed: %d segments (%d pos, %d neg)", meeting_id, len(enriched_segments), pos, neg)
        return result

    # ──────────────────────────────────────────────────────────────
    #  Topic Segmentation — what was discussed when
    # ──────────────────────────────────────────────────────────────
    def extract_topics(self, meeting_id: str, force: bool = False) -> dict:
        """
        Identify distinct topic segments in the meeting.
        Returns a list of topics with time ranges, titles, summaries, and speakers.
        Cached in storage/{meeting_id}/topics.json.
        """
        cache_path = STORAGE_DIR / meeting_id / "topics.json"
        if not force and cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        full_text, segments = self._load_transcript_text(meeting_id)

        # Build timestamped transcript for the LLM
        timestamped_lines = []
        for seg in segments:
            start = seg.get("start", 0)
            end = seg.get("end", 0)
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "")
            timestamped_lines.append(
                f"[{round(start,1)}s-{round(end,1)}s] {speaker}: {text}"
            )
        timestamped_text = "\n".join(timestamped_lines)

        system_prompt = """You are a meeting analyst. Given a timestamped meeting transcript, identify the distinct TOPICS discussed during the meeting.

For each topic, provide:
1. "title" — A short, descriptive title (3-8 words)
2. "summary" — A 1-2 sentence summary of what was discussed
3. "start_time" — Start time as a NUMBER IN SECONDS (e.g. 0, 19.5, 61, 180)
4. "end_time" — End time as a NUMBER IN SECONDS (e.g. 19.5, 61, 180, 343)
5. "speakers" — List of speaker IDs who participated in this topic

IMPORTANT: start_time and end_time MUST be numbers in SECONDS, NOT minutes. The transcript timestamps are in seconds (e.g. [19.5s-61.2s]).

Rules:
- Identify 3-8 distinct topics based on the conversation flow
- Topics should cover the FULL meeting duration without gaps
- Each topic should represent a meaningful shift in discussion
- Order topics chronologically
- Return ONLY a valid JSON array, no markdown fences"""

        user_prompt = f"Identify the distinct topics discussed in this meeting:\n\n{timestamped_text}"

        logger.info("[%s] Extracting topics via LLM...", meeting_id)
        raw = self._call_llm(system_prompt, user_prompt)

        # Parse JSON response
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]

        try:
            topics = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[%s] Failed to parse topics JSON, using fallback", meeting_id)
            total_dur = max((s.get("end", 0) for s in segments), default=0)
            topics = [{
                "title": "Full Meeting Discussion",
                "summary": "Complete meeting transcript.",
                "start_time": 0,
                "end_time": total_dur,
                "speakers": list(set(s.get("speaker", "UNKNOWN") for s in segments)),
            }]

        result = {
            "meeting_id": meeting_id,
            "topic_count": len(topics),
            "topics": topics,
        }

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info("[%s] Topics extracted: %d topics", meeting_id, len(topics))
        return result
