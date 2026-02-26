"""
Meeting Insights API — AI-powered analytics endpoints.
  POST /meeting/{meeting_id}/action-items  — Extract action items & decisions
  PUT  /meeting/{meeting_id}/action-items  — Save edited action items (HITL)
  POST /meeting/{meeting_id}/auto-title    — Generate meeting title from transcript
"""
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Body

logger = logging.getLogger(__name__)
STORAGE_DIR = Path("storage")

router = APIRouter()

# Lazy-init (Groq client loading)
_insights_service = None


def _get_insights_service():
    global _insights_service
    if _insights_service is None:
        from app.services.insights_service import MeetingInsightsService
        _insights_service = MeetingInsightsService()
    return _insights_service


@router.post("/meeting/{meeting_id}/action-items")
async def extract_action_items(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """
    Extract action items, decisions, key takeaways, and follow-ups
    from a meeting transcript using AI.
    """
    logger.info("[%s] Action items requested (force=%s)", meeting_id, force)

    try:
        service = _get_insights_service()
        result = service.extract_action_items(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Action items extraction failed: %s", meeting_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Action items extraction failed: {str(e)}",
        )

    return result


@router.put("/meeting/{meeting_id}/action-items")
async def save_action_items(
    meeting_id: str,
    payload: dict = Body(...),
):
    """
    Save human-edited action items back to disk (HITL workflow).
    Accepts the full action_items.json structure.
    """
    meeting_dir = STORAGE_DIR / meeting_id
    if not meeting_dir.exists():
        raise HTTPException(status_code=404, detail="Meeting not found")

    out_path = meeting_dir / "action_items.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info("[%s] Action items saved (HITL edit)", meeting_id)
    except Exception as e:
        logger.error("[%s] Failed to save action items: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "saved", "meeting_id": meeting_id}


@router.post("/meeting/{meeting_id}/auto-title")
async def generate_title(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """
    Auto-generate a concise, descriptive meeting title from the transcript.
    Saves to metadata.json as 'auto_title'.
    """
    logger.info("[%s] Auto-title requested (force=%s)", meeting_id, force)

    try:
        service = _get_insights_service()
        result = service.generate_title(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Title generation failed: %s", meeting_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Title generation failed: {str(e)}",
        )

    return result


@router.post("/meeting/{meeting_id}/followup-email")
async def generate_followup_email(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """
    Generate a professional follow-up email draft from the meeting.
    Combines title + summary + action items into a ready-to-send email.
    """
    logger.info("[%s] Follow-up email requested (force=%s)", meeting_id, force)

    try:
        service = _get_insights_service()
        result = service.generate_followup_email(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Follow-up email generation failed: %s", meeting_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Follow-up email generation failed: {str(e)}",
        )

    return result


@router.post("/meeting/{meeting_id}/followup-email/send")
async def send_followup_email(
    meeting_id: str,
    payload: dict = Body(...),
):
    """
    Send the follow-up email via SMTP.
    Accepts: { "recipients": ["email@example.com"], "subject": "...", "body": "..." }
    If subject/body not provided, generates them via AI first.
    """
    recipients = payload.get("recipients", [])
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients specified. Provide a 'recipients' list.")

    subject = payload.get("subject", "")
    body = payload.get("body", "")

    # If no subject/body provided, generate the email first
    if not subject or not body:
        try:
            service = _get_insights_service()
            email_data = service.generate_followup_email(meeting_id)
            subject = subject or email_data.get("subject", f"Follow-Up: Meeting {meeting_id[:8]}")
            body = body or email_data.get("body", "")
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error("[%s] Follow-up email generation failed: %s", meeting_id, e)
            raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")

    # Send via SMTP
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_password:
        raise HTTPException(
            status_code=500,
            detail="SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in .env",
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info("[%s] Follow-up email sent to %s", meeting_id, recipients)
        return {
            "success": True,
            "message": f"Follow-up email sent to {', '.join(recipients)}",
            "recipients": recipients,
        }

    except Exception as e:
        logger.error("[%s] Follow-up email send failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")


@router.post("/meeting/{meeting_id}/requirements")
async def extract_requirements(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """Extract requirements, user stories, and constraints from a meeting."""
    logger.info("[%s] Requirements extraction requested (force=%s)", meeting_id, force)
    try:
        service = _get_insights_service()
        result = service.extract_requirements(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Requirements extraction failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Requirements extraction failed: {str(e)}")
    return result


@router.post("/meeting/{meeting_id}/documentation")
async def generate_documentation(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """Generate structured meeting documentation (MoM)."""
    logger.info("[%s] Documentation requested (force=%s)", meeting_id, force)
    try:
        service = _get_insights_service()
        result = service.generate_documentation(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Documentation generation failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Documentation generation failed: {str(e)}")
    return result


@router.post("/meeting/{meeting_id}/sentiment")
async def analyze_sentiment(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """Analyze sentiment of each segment in a meeting transcript."""
    logger.info("[%s] Sentiment analysis requested (force=%s)", meeting_id, force)
    try:
        service = _get_insights_service()
        result = service.analyze_sentiment(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Sentiment analysis failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")
    return result


@router.post("/meeting/{meeting_id}/topics")
async def extract_topics(
    meeting_id: str,
    force: bool = Query(False, description="Force regeneration even if cached"),
):
    """Extract topic segments — what was discussed when."""
    logger.info("[%s] Topic segmentation requested (force=%s)", meeting_id, force)
    try:
        service = _get_insights_service()
        result = service.extract_topics(meeting_id, force=force)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("[%s] Topic extraction failed: %s", meeting_id, e)
        raise HTTPException(status_code=500, detail=f"Topic extraction failed: {str(e)}")
    return result


# ──────────────────────────────────────────────────────────────
# Pure-computation analytics (no LLM needed)
# ──────────────────────────────────────────────────────────────

@router.get("/meeting/{meeting_id}/speaker-analytics")
async def speaker_analytics(meeting_id: str):
    """
    Compute per-speaker analytics from the transcript:
    talk-time, word count, words-per-minute, interruption count.
    Pure math — no LLM call required.
    """
    transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found. Run transcription first.")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    segments = transcript.get("segments", [])
    if not segments:
        return {"meeting_id": meeting_id, "speakers": [], "total_duration": 0}

    # Load speaker map for display names
    smap = {}
    smap_path = STORAGE_DIR / meeting_id / "speaker_map.json"
    if smap_path.exists():
        with open(smap_path, "r", encoding="utf-8") as f:
            smap = json.load(f)

    # Compute per-speaker stats
    stats = {}
    for seg in segments:
        spk = seg.get("speaker", "UNKNOWN")
        text = seg.get("text", "").strip()
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        duration = max(0, end - start)
        words = len(text.split()) if text else 0

        if spk not in stats:
            stats[spk] = {
                "talk_time": 0,
                "word_count": 0,
                "segment_count": 0,
                "interruptions": 0,
            }
        stats[spk]["talk_time"] += duration
        stats[spk]["word_count"] += words
        stats[spk]["segment_count"] += 1

    # Detect interruptions (speaker changes where the gap is < 0.5s)
    for i in range(1, len(segments)):
        prev = segments[i - 1]
        curr = segments[i]
        if prev.get("speaker") != curr.get("speaker"):
            gap = curr.get("start", 0) - prev.get("end", 0)
            if gap < 0.5:
                spk = curr.get("speaker", "UNKNOWN")
                if spk in stats:
                    stats[spk]["interruptions"] += 1

    total_talk = sum(s["talk_time"] for s in stats.values()) or 1
    total_dur = max(seg.get("end", 0) for seg in segments) if segments else 0

    result = []
    for spk, s in sorted(stats.items(), key=lambda x: x[1]["talk_time"], reverse=True):
        wpm = round(s["word_count"] / (s["talk_time"] / 60)) if s["talk_time"] > 0 else 0
        result.append({
            "speaker_id": spk,
            "display_name": smap.get(spk, spk),
            "talk_time_seconds": round(s["talk_time"], 1),
            "talk_time_percent": round((s["talk_time"] / total_talk) * 100, 1),
            "word_count": s["word_count"],
            "words_per_minute": wpm,
            "segment_count": s["segment_count"],
            "interruptions": s["interruptions"],
        })

    return {
        "meeting_id": meeting_id,
        "total_duration": round(total_dur, 1),
        "total_speakers": len(result),
        "speakers": result,
    }


@router.get("/meeting/{meeting_id}/speaker-report")
async def speaker_report(meeting_id: str):
    """
    Per-speaker report cards — aggregates transcript, sentiment,
    action items, and topics into a comprehensive scorecard per speaker.
    Auto-classifies speaker role. Pure math — no LLM call.
    """
    meeting_dir = STORAGE_DIR / meeting_id
    transcript_path = meeting_dir / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found.")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)
    segments = transcript.get("segments", [])
    if not segments:
        return {"meeting_id": meeting_id, "speakers": []}

    # Speaker map
    smap = {}
    smap_path = meeting_dir / "speaker_map.json"
    if smap_path.exists():
        with open(smap_path, "r", encoding="utf-8") as f:
            smap = json.load(f)

    # Optional: sentiment
    sentiment_data = {}
    sentiment_path = meeting_dir / "sentiment.json"
    if sentiment_path.exists():
        try:
            with open(sentiment_path, "r", encoding="utf-8") as f:
                sentiment_data = json.load(f)
        except Exception:
            pass

    # Optional: action items
    action_data = {}
    action_path = meeting_dir / "action_items.json"
    if action_path.exists():
        try:
            with open(action_path, "r", encoding="utf-8") as f:
                action_data = json.load(f)
        except Exception:
            pass

    # Optional: topics
    topics_data = {}
    topics_path = meeting_dir / "topics.json"
    if topics_path.exists():
        try:
            with open(topics_path, "r", encoding="utf-8") as f:
                topics_data = json.load(f)
        except Exception:
            pass

    # ── Step 1: Basic transcript stats per speaker ──
    speaker_stats = {}
    for seg in segments:
        spk = seg.get("speaker", "UNKNOWN")
        text = seg.get("text", "").strip()
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        duration = max(0, end - start)
        words = len(text.split()) if text else 0
        questions = text.count("?")

        if spk not in speaker_stats:
            speaker_stats[spk] = {
                "talk_time": 0, "word_count": 0, "segment_count": 0,
                "questions_asked": 0, "interruptions": 0,
                "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
                "topics": set(),
            }
        s = speaker_stats[spk]
        s["talk_time"] += duration
        s["word_count"] += words
        s["segment_count"] += 1
        s["questions_asked"] += questions

    # Interruptions
    for i in range(1, len(segments)):
        prev = segments[i - 1]
        curr = segments[i]
        if prev.get("speaker") != curr.get("speaker"):
            gap = curr.get("start", 0) - prev.get("end", 0)
            if gap < 0.5:
                spk = curr.get("speaker", "UNKNOWN")
                if spk in speaker_stats:
                    speaker_stats[spk]["interruptions"] += 1

    # ── Step 2: Sentiment per speaker ──
    sentiment_segments = sentiment_data.get("segments", [])
    for ss in sentiment_segments:
        spk = ss.get("speaker", "UNKNOWN")
        sent = ss.get("sentiment", "neutral").lower()
        if spk in speaker_stats and sent in speaker_stats[spk]["sentiment"]:
            speaker_stats[spk]["sentiment"][sent] += 1

    # ── Step 3: Action items per speaker ──
    action_items_list = action_data.get("action_items", [])
    decisions_list = action_data.get("decisions", [])
    speaker_actions = {}
    speaker_decisions = {}

    for item in action_items_list:
        assignee = item.get("assignee", "").strip()
        # Match assignee to speaker via speaker_map
        for spk_id, name in smap.items():
            if name.lower() == assignee.lower():
                speaker_actions[spk_id] = speaker_actions.get(spk_id, 0) + 1
                break
        else:
            # Try matching directly to speaker IDs
            for spk_id in speaker_stats:
                if spk_id.lower() == assignee.lower():
                    speaker_actions[spk_id] = speaker_actions.get(spk_id, 0) + 1
                    break

    # Attribute decisions to the speaker who spoke just before the decision context
    for spk in speaker_stats:
        speaker_decisions[spk] = 0
    if decisions_list:
        # Simple heuristic: distribute decisions proportional to talk time
        total_talk = sum(s["talk_time"] for s in speaker_stats.values()) or 1
        for spk, s in speaker_stats.items():
            share = s["talk_time"] / total_talk
            speaker_decisions[spk] = round(len(decisions_list) * share)

    # ── Step 4: Topics per speaker ──
    topic_segments = topics_data.get("topics", [])
    for topic in topic_segments:
        topic_label = topic.get("topic", "")
        topic_segs = topic.get("segments", [])
        for ts in topic_segs:
            spk = ts.get("speaker", "UNKNOWN")
            if spk in speaker_stats:
                speaker_stats[spk]["topics"].add(topic_label)

    # ── Step 5: Build cards + classify roles ──
    total_talk = sum(s["talk_time"] for s in speaker_stats.values()) or 1
    total_dur = max((seg.get("end", 0) for seg in segments), default=0)

    cards = []
    for spk, s in sorted(speaker_stats.items(), key=lambda x: x[1]["talk_time"], reverse=True):
        talk_pct = round((s["talk_time"] / total_talk) * 100, 1)
        total_sent = s["sentiment"]["positive"] + s["sentiment"]["negative"] + s["sentiment"]["neutral"]
        dominant_sentiment = "neutral"
        if total_sent > 0:
            if s["sentiment"]["positive"] >= s["sentiment"]["negative"] and s["sentiment"]["positive"] >= s["sentiment"]["neutral"]:
                dominant_sentiment = "positive"
            elif s["sentiment"]["negative"] > s["sentiment"]["positive"] and s["sentiment"]["negative"] > s["sentiment"]["neutral"]:
                dominant_sentiment = "negative"

        wpm = round(s["word_count"] / (s["talk_time"] / 60)) if s["talk_time"] > 0 else 0

        cards.append({
            "speaker_id": spk,
            "display_name": smap.get(spk, spk),
            "talk_time_seconds": round(s["talk_time"], 1),
            "talk_time_percent": talk_pct,
            "word_count": s["word_count"],
            "words_per_minute": wpm,
            "segment_count": s["segment_count"],
            "questions_asked": s["questions_asked"],
            "interruptions": s["interruptions"],
            "action_items_assigned": speaker_actions.get(spk, 0),
            "decisions_attributed": speaker_decisions.get(spk, 0),
            "sentiment": {
                "positive": s["sentiment"]["positive"],
                "negative": s["sentiment"]["negative"],
                "neutral": s["sentiment"]["neutral"],
                "dominant": dominant_sentiment,
            },
            "topics": sorted(s["topics"]),
            "role": "",  # filled below
        })

    # ── Role classification ──
    if cards:
        max_talk = max(c["talk_time_percent"] for c in cards)
        max_questions = max(c["questions_asked"] for c in cards)
        max_actions = max(c["action_items_assigned"] for c in cards)
        max_decisions = max(c["decisions_attributed"] for c in cards)

        for c in cards:
            if max_decisions > 0 and c["decisions_attributed"] == max_decisions:
                c["role"] = "Decision Maker"
            elif c["talk_time_percent"] == max_talk and c["talk_time_percent"] > 40:
                c["role"] = "Presenter"
            elif max_questions > 0 and c["questions_asked"] == max_questions and c["questions_asked"] >= 2:
                c["role"] = "Challenger"
            elif max_actions > 0 and c["action_items_assigned"] == max_actions:
                c["role"] = "Doer"
            elif c["talk_time_percent"] < 15:
                c["role"] = "Observer"
            else:
                c["role"] = "Contributor"

    return {
        "meeting_id": meeting_id,
        "total_duration": round(total_dur, 1),
        "total_speakers": len(cards),
        "speakers": cards,
    }

@router.get("/meeting/{meeting_id}/keywords")
async def keyword_cloud(meeting_id: str):
    """
    Extract top keywords from transcript.
    Pure computation — word frequency with stop-word filtering.
    """
    transcript_path = STORAGE_DIR / meeting_id / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript not found. Run transcription first.")

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    segments = transcript.get("segments", [])
    full_text = " ".join(seg.get("text", "") for seg in segments).lower()

    # Common English stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "it", "that", "this", "was", "are",
        "be", "has", "have", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall", "not", "no", "so",
        "if", "then", "than", "too", "very", "just", "about", "up", "out",
        "all", "also", "as", "into", "its", "my", "we", "our", "you", "your",
        "they", "their", "them", "he", "she", "his", "her", "him", "me", "i",
        "what", "which", "who", "when", "where", "how", "why", "been", "being",
        "there", "here", "some", "any", "each", "every", "both", "few", "more",
        "most", "other", "such", "only", "own", "same", "over", "after",
        "before", "between", "through", "during", "above", "below", "again",
        "further", "once", "like", "well", "back", "even", "still", "way",
        "much", "many", "these", "those", "get", "got", "going", "go", "went",
        "come", "came", "make", "made", "take", "took", "know", "knew",
        "think", "thought", "say", "said", "see", "saw", "want", "need",
        "use", "used", "one", "two", "first", "new", "now", "look", "people",
        "time", "thing", "right", "yeah", "yes", "okay", "ok", "um", "uh",
        "oh", "ah", "hmm", "actually", "really", "basically", "something",
        "kind", "let", "good", "don't", "didn't", "won't", "can't", "it's",
        "that's", "i'm", "we're", "you're", "they're", "there's", "what's",
    }

    # Tokenize and count
    import re
    words = re.findall(r"[a-z']{3,}", full_text)
    freq = {}
    for w in words:
        if w not in stop_words and len(w) >= 3:
            freq[w] = freq.get(w, 0) + 1

    # Sort by frequency, top 30
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:30]

    max_count = sorted_words[0][1] if sorted_words else 1
    keywords = []
    for word, count in sorted_words:
        keywords.append({
            "word": word,
            "count": count,
            "weight": round(count / max_count, 2),  # 0.0-1.0 for sizing
        })

    return {
        "meeting_id": meeting_id,
        "total_unique_words": len(freq),
        "keywords": keywords,
    }

