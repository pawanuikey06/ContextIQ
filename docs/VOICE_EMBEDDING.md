# Voice Embedding & Speaker Identification

## Overview

The Voice Embedding feature enables **automatic speaker identification** across meetings using neural voice fingerprints. When a speaker is manually named in one meeting, the system creates a **voice profile** (embedding vector) from their audio. In subsequent meetings, the system automatically recognizes that same person's voice and assigns their name — no manual labeling needed.

**Core Idea**: Record a speaker once, name them once, recognize them forever.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Voice Embedding Pipeline                │
│                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐ │
│  │  Audio   │───▶│  Clip        │───▶│  Preprocess   │ │
│  │  File    │    │  Extraction  │    │  Pipeline     │ │
│  └──────────┘    └──────────────┘    └───────┬───────┘ │
│                                              │         │
│  ┌──────────────────────────────┐            ▼         │
│  │  Speaker Profiles            │    ┌───────────────┐ │
│  │  (profiles.json)             │◀──▶│  ECAPA-TDNN   │ │
│  │  name → 192-dim embedding    │    │  (SpeechBrain)│ │
│  └──────────────────────────────┘    └───────────────┘ │
│                     │                        │         │
│                     ▼                        ▼         │
│            ┌───────────────────────────────────┐       │
│            │  Cosine Similarity Matching        │       │
│            │  threshold ≥ 0.55 → match          │       │
│            └───────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Role |
|-----------|------|------|
| Voice Embedding Service | `app/services/voice_embedding_service.py` | Clip extraction, preprocessing, embedding generation, matching |
| Voice Profiles API | `app/api/voice_profiles.py` | REST endpoints for clips, profiles, and voice matching |
| Speaker Audio Player | `frontend/src/components/SpeakerAudioPlayer.svelte` | UI for playing speaker voice clips |
| Speaker Map API | `app/api/speaker_map.py` | Manages SPEAKER_ID → name mappings |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Embedding Model | SpeechBrain ECAPA-TDNN | 192-dim speaker verification embeddings |
| Pre-trained Weights | `spkrec-ecapa-voxceleb` | Trained on VoxCeleb dataset |
| Audio I/O | soundfile (libsndfile) | Read/write WAV files without FFmpeg dependency |
| Numeric | NumPy | Audio preprocessing, cosine similarity |
| Deep Learning | PyTorch (CPU) | Inference for ECAPA-TDNN model |

---

## Data Flow

### 1. Speaker Clip Extraction

When a meeting is transcribed, the system extracts a ~10-second voice sample per speaker:

```
Meeting Audio (WAV, full length)
         │
         ▼
┌──────────────────────────────────┐
│  Load transcript.json            │
│  Group segments by speaker_id    │
│  For each speaker:               │
│    1. Score segments by energy    │
│       (RMS × min(duration, 5s))  │
│    2. Pick highest-quality first  │
│    3. Concatenate until ~10s     │
│    4. Preprocess audio clip      │
│    5. Save as {SPEAKER_ID}.wav   │
└──────────────────────────────────┘
         │
         ▼
storage/{meeting_id}/speaker_clips/
├── SPEAKER_00.wav  (10s, 16kHz, mono)
├── SPEAKER_01.wav
└── SPEAKER_02.wav
```

**Segment Selection Strategy**: Instead of using the first N seconds, the system ranks all segments by **signal-to-noise quality** (RMS energy × bounded duration). This ensures the clip contains the clearest speech, not filler or crosstalk.

### 2. Audio Preprocessing Pipeline

Every clip goes through a 5-stage preprocessing pipeline before embedding:

```
Raw Audio Clip
      │
      ▼ Step 1: Resample to 16kHz (model requirement)
      │         Uses linear interpolation for CPU-friendly resampling
      │
      ▼ Step 2: Peak Normalize to [-1, 1]
      │         Ensures consistent amplitude across speakers
      │
      ▼ Step 3: Bandpass Filter (80Hz – 7600Hz)
      │         FFT-based filter isolating speech frequencies
      │         Removes low-frequency rumble + high-frequency noise
      │
      ▼ Step 4: Remove Silence
      │         30ms frame analysis, drops frames with RMS < 0.01
      │         Keeps only voiced (active speech) frames
      │
      ▼ Step 5: Re-normalize
      │         Normalize again after filtering
      │
      ▼
  Preprocessed Clip (16kHz, mono, clean speech)
```

**Fallback**: If preprocessing reduces the clip below 3 seconds (`MIN_CLIP_DURATION`), the system falls back to a simpler resample + normalize pipeline to preserve enough audio.

### 3. Embedding Generation

```python
# ECAPA-TDNN model (loaded lazily, runs on CPU)
model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="storage/models/spkrec-ecapa",
    run_opts={"device": "cpu"},
)

# Generate 192-dimensional embedding vector
signal = torch.tensor(audio_data).unsqueeze(0)  # [1, num_samples]
signal = signal / (signal.abs().max() + 1e-8)   # Normalize
embedding = model.encode_batch(signal)            # → [1, 1, 192]
embedding_vector = embedding.squeeze().tolist()   # → [192 floats]
```

**Output**: A 192-dimensional float vector that uniquely represents the speaker's voice characteristics.

### 4. Profile Storage

Speaker profiles are stored in a central JSON file:

```json
// storage/speaker_profiles/profiles.json
{
  "Varun Kumar": [0.0234, -0.1567, 0.4821, ...],    // 192 floats
  "Poornima Kumaran": [0.1122, 0.0398, -0.2156, ...],
  "Babuji Abraham": [-0.0567, 0.2341, 0.1789, ...]
}
```

**Running Average**: When a speaker is profiled from multiple meetings, their embedding is averaged with the existing one:

```python
averaged = (existing_embedding + new_embedding) / 2.0
```

This improves cross-meeting accuracy by reducing variance from recording conditions.

### 5. Speaker Matching

When a new meeting is processed, each speaker is compared against all stored profiles:

```
New Meeting Speaker Clips
         │
         ▼
┌─────────────────────────────────────┐
│  For each speaker in new meeting:   │
│    1. Generate embedding from clip  │
│    2. Compute cosine similarity     │
│       against ALL stored profiles   │
│    3. Find best match ≥ threshold   │
│    4. Exclusive assignment          │
│       (each name used at most once) │
└─────────────────────────────────────┘
         │
         ▼
  Matches: { "SPEAKER_00": "Varun Kumar", "SPEAKER_02": "Poornima Kumaran" }
```

**Cosine Similarity**:

```python
similarity = dot(a, b) / (||a|| × ||b||)
# Range: -1.0 to 1.0
# Threshold: 0.55 (tuned for meeting audio quality)
```

**Exclusive Assignment**: The system prevents assigning the same real name to multiple speakers in a meeting. Once a profile is matched, it's removed from the candidate pool.

---

## API Endpoints

### Speaker Clips

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/meeting/{id}/speaker-clips` | List available clips (auto-extracts if missing) |
| `GET` | `/meeting/{id}/speaker-clips/{speaker_id}` | Serve a speaker's WAV clip for playback |

### Speaker Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/speaker-profiles` | List all stored profiles (name + dimension) |
| `POST` | `/meeting/{id}/speaker-profiles` | Generate embeddings + save profiles from speaker map |
| `POST` | `/meeting/{id}/voice-match` | Run voice matching on a meeting → update transcript + speaker map |

### Profile Save Flow (triggered by `POST /meeting/{id}/speaker-profiles`)

```
1. Load speaker_map.json (SPEAKER_00 → "Varun Kumar")
2. For each mapped speaker:
   a. Find clip at speaker_clips/SPEAKER_00.wav
   b. Generate 192-dim embedding
   c. Save/average into profiles.json under the real name
3. Return: { "saved": 3, "total_speakers": 3 }
```

### Voice Match Flow (triggered by `POST /meeting/{id}/voice-match`)

```
1. Ensure speaker clips exist (extract if missing)
2. Run match_speakers(meeting_id, threshold=0.55)
3. For each match found:
   a. Update transcript.json segments with real names
   b. Rebuild speaker groupings
   c. Update speaker_map.json
4. Return: { "matched": 2, "matches": {"SPEAKER_00": "Varun Kumar", ...} }
```

---

## Platform Compatibility

### Windows-Specific Patches

The service includes two critical patches for Windows:

1. **torchaudio compatibility**: torchaudio 2.10+ removed `list_audio_backends()` which SpeechBrain 1.0.x needs. The service patches it: `torchaudio.list_audio_backends = lambda: ["soundfile"]`.

2. **Symlink workaround**: SpeechBrain uses symlinks for model caching, which require admin privileges on Windows. The service monkey-patches `speechbrain.utils.fetching.fetch()` to use `COPY` strategy instead of `SYMLINK`.

---

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| Embedding model | `spkrec-ecapa-voxceleb` | ECAPA-TDNN (SpeechBrain) |
| Embedding dimensions | 192 | Model output |
| Target clip duration | 10 seconds | `TARGET_CLIP_DURATION` |
| Minimum clip duration | 3 seconds | `MIN_CLIP_DURATION` |
| Target sample rate | 16,000 Hz | `TARGET_SAMPLE_RATE` |
| Match threshold | 0.55 | `match_speakers()` default |
| Bandpass filter | 80Hz – 7600Hz | `_bandpass_filter()` |
| Silence detection | 30ms frames, RMS < 0.01 | `_remove_silence()` |
| Model cache | `storage/models/spkrec-ecapa/` | `_get_model()` |
| Profiles path | `storage/speaker_profiles/profiles.json` | Global store |

---

## Storage Structure

```
storage/
├── speaker_profiles/
│   └── profiles.json              # Global name → embedding map
├── models/
│   └── spkrec-ecapa/              # Cached ECAPA-TDNN model weights
├── {meeting_id}/
│   ├── speaker_clips/
│   │   ├── SPEAKER_00.wav         # 10s preprocessed clip (16kHz, mono)
│   │   ├── SPEAKER_01.wav
│   │   └── SPEAKER_02.wav
│   ├── speaker_map.json           # SPEAKER_ID → real name
│   └── transcript.json            # Contains segments with speaker labels
data/
└── audio/
    └── {meeting_id}.wav           # Original full meeting audio
```

---

## Logging & Debugging

The service provides detailed logging at every stage:

```
[meeting_id] ✅ Preprocessed clip saved: SPEAKER_00 (9.8s, 16kHz)
[meeting_id] 🔍 Starting speaker matching against 3 stored profiles: ['Varun Kumar', ...]
[meeting_id] 📊 SPEAKER_00 similarity scores → Varun Kumar: 0.7823 | Poornima: 0.3421 | Babuji: 0.2198
[meeting_id] ✅ MATCH: SPEAKER_00 → 'Varun Kumar' (score=0.7823, threshold=0.55)
[meeting_id] ❌ NO MATCH for SPEAKER_03 (best: 'Babuji' at 0.4102, threshold=0.55)
[meeting_id] 🏁 Matching complete: 2/3 speakers matched → {'SPEAKER_00': 'Varun Kumar', ...}
```
