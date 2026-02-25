"""
Test improved accuracy with:
1. whisper-large-v3 (full model, not turbo)
2. Better prompt hints with Indian names and company terms
"""
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()

audio_path = "data/audio/77297bbe-b307-4c10-add0-39edf55350f8.wav"
# Use clean audio if exists
clean_path = audio_path.replace(".wav", "_clean.wav")
if os.path.exists(clean_path):
    audio_path = clean_path
    print("Using preprocessed audio:", clean_path)

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Better prompt hints with names and domain terms
prompt_hints = (
    "Meeting transcription between Purnima, Varun, and Babuji. "
    "Company: Vrize. Topics: laptop delivery, new hires, onboarding, "
    "HRMS, IT ticketing, SLA, billable hours, asset request, "
    "background check, offer letter, tier-2 cities, lateral hires."
)

models_to_test = [
    ("whisper-large-v3-turbo", prompt_hints),
    ("whisper-large-v3", prompt_hints),
    ("whisper-large-v3-turbo", ""),      # without hints
    ("whisper-large-v3", ""),             # without hints
]

for model_name, prompt in models_to_test:
    label = model_name + (" + hints" if prompt else " (no hints)")
    print("=" * 60)
    print("MODEL: " + label)
    print("=" * 60)

    start = time.time()
    with open(audio_path, "rb") as f:
        kwargs = dict(
            file=("audio.wav", f),
            model=model_name,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            language="en",
        )
        if prompt:
            kwargs["prompt"] = prompt

        resp = client.audio.transcriptions.create(**kwargs)

    elapsed = time.time() - start

    # Extract segments
    segments = []
    if resp.segments:
        for s in resp.segments:
            d = s.__dict__ if hasattr(s, "__dict__") else s
            segments.append(d)

    print("Time: {:.2f}s | Segments: {}".format(elapsed, len(segments)))

    # Print first 5 segments to compare
    for seg in segments[:5]:
        st = seg.get("start", 0)
        en = seg.get("end", 0)
        tx = seg.get("text", "").strip()
        print("  [{:.0f}-{:.0f}s] {}".format(st, en, tx))

    # Check for known problem words
    full_text = " ".join(seg.get("text", "") for seg in segments)
    checks = {
        "Purnima": "Purnima" in full_text or "purnima" in full_text.lower(),
        "Varun": "Varun" in full_text or "varun" in full_text.lower(),
        "Vrize/V-Rice": "Vrize" in full_text or "V-Rice" in full_text or "VRize" in full_text.lower(),
        "HRMS": "HRMS" in full_text or "hrms" in full_text.lower(),
        "Babuji": "Babuji" in full_text or "babuji" in full_text.lower(),
    }
    print("  Name checks: ", end="")
    for name, found in checks.items():
        status = "OK" if found else "MISS"
        print("{}: {} | ".format(name, status), end="")
    print()
    print()
