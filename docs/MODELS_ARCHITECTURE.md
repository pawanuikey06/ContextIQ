# AI/ML Models Architecture — ContextIQ

Complete reference of every AI/ML model used in the ContextIQ codebase, with architecture details, data flow, and where each model is invoked.

---

## Model Overview

| # | Model | Type | Provider | Runs On | Code Location |
|---|-------|------|----------|---------|---------------|
| 1 | **Llama 3.3 70B** | Large Language Model (LLM) | Groq API | Cloud (Groq LPU) | `summary_service.py`, `insights_service.py`, `rag_service.py` |
| 2 | **Whisper Large V3 Turbo** | Speech-to-Text (ASR) | Groq API | Cloud (Groq LPU) | `stt_service.py` |
| 3 | **AssemblyAI Universal-2** | Speech-to-Text + Diarization | AssemblyAI API | Cloud | `stt_service.py` |
| 4 | **WhisperX (medium)** | Speech-to-Text (ASR) | Open-source | Local GPU/CPU | `stt_service.py` |
| 5 | **pyannote/speaker-diarization-3.1** | Speaker Diarization | Open-source | Local GPU/CPU | `stt_service.py` |
| 6 | **ECAPA-TDNN (SpeechBrain)** | Speaker Verification / Voice Embedding | Open-source | Local CPU | `voice_embedding_service.py` |
| 7 | **all-MiniLM-L6-v2** | Text Embedding (Sentence Transformer) | HuggingFace | Local CPU | `rag_service.py` |

---

## 1. Llama 3.3 70B Versatile (via Groq)

### What It Is
A 70-billion parameter open-source LLM by Meta AI, served through Groq's ultra-fast LPU inference chips (~800 tokens/sec).

### Architecture
- **Type**: Transformer (decoder-only, autoregressive)
- **Parameters**: 70 billion learned weights
- **Context Window**: 128K tokens
- **Training Data**: ~15 trillion tokens of publicly available text
- **Quantization**: Served optimized on Groq's custom LPU silicon

### How It's Called in Code
```python
# summary_service.py & insights_service.py
MODEL = "llama-3.3-70b-versatile"
client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.3,
    max_tokens=4096,
)
```

### What It Does in ContextIQ (7 Tasks)

| Task | Service Method | System Prompt Summary |
|------|---------------|----------------------|
| **Bilingual Summary** | `summary_service.generate_summary()` | Generate speaker-wise + overall summary in English and Hindi |
| **Action Items** | `insights_service.extract_action_items()` | Extract tasks, assignees, deadlines, priorities, dependencies |
| **Decisions & Risks** | `insights_service.extract_action_items()` | Capture decisions (who, why, impact) and risks (mitigation) |
| **Requirements** | `insights_service.extract_requirements()` | Mine FR/NFR, user stories, constraints with MoSCoW priority |
| **Sentiment Analysis** | `insights_service.analyze_sentiment()` | Score each segment -1.0 to +1.0, classify emotion |
| **Documentation (MoM)** | `insights_service.generate_documentation()` | Generate formal meeting minutes with attendees & next steps |
| **Topic Segmentation** | `insights_service.extract_topics()` | Auto-detect discussion chapters with time ranges |
| **RAG Q&A** | `rag_service.ask()` | Answer questions using retrieved transcript context |
| **Speaker Report Cards** | `insights.py speaker_report()` | Classify speaker roles (Decision Maker, Presenter, etc.) |
| **Auto Title** | `summary_service.generate_summary()` | Generate descriptive meeting title from content |

### Data Flow
```
Transcript JSON → Build system prompt + user prompt
                → Groq API (Llama 3.3 70B)
                → Parse JSON response
                → Cache to storage/{meeting_id}/<feature>.json
                → Serve to frontend via API
```

### Why Llama 3.3 70B?
- **Speed**: Groq LPU delivers ~800 tok/sec (10× faster than GPT-4)
- **Cost**: Significantly cheaper than OpenAI
- **Quality**: 70B competes with GPT-4 on structured JSON extraction
- **Open-Source**: No vendor lock-in, model weights are publicly available

---

## 2. Whisper Large V3 Turbo (via Groq)

### What It Is
OpenAI's Whisper speech recognition model, optimized and served through Groq's API for ultra-fast cloud transcription.

### Architecture
- **Type**: Encoder-Decoder Transformer
- **Base Model**: OpenAI Whisper Large V3
- **Input**: Raw audio (WAV/MP3, ≤25MB)
- **Output**: Timestamped text segments with language detection
- **Languages**: 99+ languages supported

### How It's Called in Code
```python
# stt_service.py → _transcribe_groq()
client = Groq(api_key=self.groq_api_key)

response = client.audio.transcriptions.create(
    file=(Path(audio_path).name, audio_file),
    model="whisper-large-v3-turbo",
    response_format="verbose_json",
    timestamp_granularities=["segment"],
    language="en",
)
```

### Data Flow
```
Video Upload → FFmpeg extract WAV audio
             → Noise reduction (noisereduce library)
             → Volume normalization (-1 dBFS peak)
             → Groq Whisper API
             → Timestamped segments (no speaker labels)
             → pyannote diarization assigns speakers
```

### Limitations
- Max file size: 25 MB
- **No diarization** — returns text segments without speaker labels
- Requires separate pyannote diarization step for speaker assignment

---

## 3. AssemblyAI Universal-2

### What It Is
AssemblyAI's latest production speech model that handles both transcription AND speaker diarization in a single API call.

### Architecture
- **Type**: Proprietary cloud ASR + diarization pipeline
- **Model**: `universal-2` (AssemblyAI's most accurate model)
- **Features**: Automatic language detection, speaker labels, utterance-level output
- **Input**: Any audio format (uploaded to AssemblyAI servers)

### How It's Called in Code
```python
# stt_service.py → _transcribe_assemblyai()
import assemblyai as aai
aai.settings.api_key = self.assemblyai_api_key

config = aai.TranscriptionConfig(
    speech_models=["universal-2"],
    language_detection=True,
    speaker_labels=True,
)

transcriber = aai.Transcriber()
transcript = transcriber.transcribe(audio_path, config=config)
# Returns utterances with speaker labels directly
```

### Why It's the Default (`STT_MODE=assemblyai`)
- **Single API call** — no need for separate diarization
- **Best quality** — state-of-the-art accuracy
- **Speaker labels included** — each utterance has `speaker: "A"`, `"B"`, etc.
- **Configurable** — supports `SPEAKERS_EXPECTED` env var for hints

---

## 4. WhisperX (Local, medium)

### What It Is
An optimized version of OpenAI's Whisper with word-level timestamps and faster inference. Runs entirely on local GPU/CPU.

### Architecture
- **Type**: CTC-Whisper hybrid with forced alignment
- **Model Size**: `medium` (769M parameters)
- **Compute**: CUDA float16 (GPU) or int8 (CPU)
- **Extra**: Word-level timestamps via wav2vec2 alignment

### How It's Called in Code
```python
# stt_service.py → _transcribe_local()
import whisperx

audio = whisperx.load_audio(audio_path)
asr_model = whisperx.load_model(
    "medium",
    device=self.device,           # "cuda" or "cpu"
    compute_type=self.compute_type # "float16" or "int8"
)
result = asr_model.transcribe(audio)

# Model deleted immediately after use to free VRAM
del asr_model
torch.cuda.empty_cache()
```

### When It's Used
- `STT_MODE=local`: Always used
- `STT_MODE=auto`: Fallback when Groq fails (file too large, API error)
- Requires local GPU for acceptable speed

---

## 5. pyannote/speaker-diarization-3.1

### What It Is
A state-of-the-art neural speaker diarization pipeline that answers "who spoke when" in an audio file.

### Architecture
- **Type**: Neural segmentation + clustering pipeline
- **Segmentation Model**: pyannote/segmentation-3.0 (PyanNet-based)
- **Embedding Model**: Wespeaker embeddings for speaker clustering
- **Algorithm**: Agglomerative clustering on speaker embeddings
- **Output**: Timeline of `(start, end, speaker_label)` intervals

### How It's Called in Code
```python
# stt_service.py → _load_diarization_pipeline()
from whisperx.diarize import DiarizationPipeline

# Tries models in order of preference:
models_to_try = [
    "pyannote/speaker-diarization-3.1",      # Best quality
    "pyannote/speaker-diarization",           # Fallback
    "pyannote/speaker-diarization-community-1" # Last resort
]

pipeline = DiarizationPipeline(
    model_name=model_name,
    token=self.hf_token,  # HuggingFace access token required
    device=self.device,
)
diarization = pipeline(audio_path)
```

### Speaker Assignment Logic
```python
# For each transcript segment, find the diarization interval
# with the maximum temporal overlap:
for seg in segments:
    for d_start, d_end, d_speaker in diar_segments:
        overlap = max(0, min(seg_end, d_end) - max(seg_start, d_start))
        if overlap > best_overlap:
            best_speaker = d_speaker
    seg["speaker"] = best_speaker
```

### When It's Used
- Combined with Groq Whisper (which has no diarization)
- Combined with local WhisperX
- **NOT used** with AssemblyAI (which has built-in diarization)

---

## 6. ECAPA-TDNN (SpeechBrain)

### What It Is
A neural speaker embedding model that generates a fixed-size **192-dimensional vector** from a voice clip. Used for speaker identification across meetings.

### Architecture
- **Type**: Time Delay Neural Network with ECAPA (channel-attention, squeeze-excitation)
- **Model ID**: `speechbrain/spkrec-ecapa-voxceleb`
- **Training Data**: VoxCeleb1 + VoxCeleb2 (7000+ speaker identities)
- **Output**: 192-dim embedding vector (speaker "fingerprint")
- **Similarity**: Cosine similarity for matching (threshold: 0.25)

### How It's Called in Code
```python
# voice_embedding_service.py → _load_model()
from speechbrain.inference.speaker import SpeakerRecognition
# or fallback:
from speechbrain.pretrained import EncoderClassifier

model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="storage/models/spkrec-ecapa",
)
```

### Voice Identification Pipeline
```
1. CLIP EXTRACTION
   transcript.json segments → FFmpeg cuts speaker audio clips
   → One WAV per speaker per meeting

2. AUDIO PREPROCESSING (5-stage)
   → Mono conversion
   → Resample to 16kHz (SpeechBrain requirement)
   → Silence trimming (30dB threshold)
   → Peak normalization
   → Length validation (0.5s - 30s)

3. EMBEDDING GENERATION
   signal, fs = torchaudio.load(clip_path)
   embedding = model.encode_batch(signal)  # → 192-dim vector

4. PROFILE MATCHING
   For each speaker embedding:
   → Compare against all stored profiles via cosine similarity
   → Match if score ≥ 0.25 (threshold)
   → If matched: merge embedding (running average)
   → If no match: flag as new/unidentified

5. STORAGE
   → Profiles saved to storage/speaker_profiles/profiles.json
   → Format: { "Speaker Name": [192 floats] }
```

### Cosine Similarity Formula
```python
def cosine_similarity(self, emb1, emb2):
    a, b = np.array(emb1), np.array(emb2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
# Returns: -1.0 (opposite) to 1.0 (identical)
# Threshold: ≥ 0.25 = same speaker
```

---

## 7. all-MiniLM-L6-v2 (Sentence Transformer)

### What It Is
A lightweight sentence embedding model that converts text chunks into 384-dimensional vectors for semantic search in the RAG chatbot.

### Architecture
- **Type**: Transformer encoder (BERT-based, distilled)
- **Parameters**: 22.7 million (very small, runs on CPU)
- **Output**: 384-dim embedding vector per text chunk
- **Training**: Trained on 1B+ sentence pairs for semantic similarity
- **Speed**: ~14,000 sentences/sec on GPU, ~500/sec on CPU

### How It's Called in Code
```python
# rag_service.py → __init__()
from langchain_huggingface import HuggingFaceEmbeddings

self._embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
)

# Used by ChromaDB for indexing and querying:
self._vectorstore = Chroma(
    collection_name="meetings",
    embedding_function=self._embeddings,
    persist_directory=str(CHROMA_DIR),
)
```

### RAG Pipeline Data Flow
```
INDEXING (one-time per meeting):
  Transcript → Sliding window chunks (500 chars, 100 overlap)
             → all-MiniLM-L6-v2 embeds each chunk → 384-dim vectors
             → Stored in ChromaDB (persistent on disk)

QUERYING (per question):
  User Question → all-MiniLM-L6-v2 embeds question → 384-dim vector
                → ChromaDB cosine similarity search (top-k chunks)
                → Diverse round-robin retrieval (prevents single-meeting bias)
                → Retrieved chunks + question → Llama 3.3 70B generates answer
                → SSE streaming response to frontend
```

### Why all-MiniLM-L6-v2?
- **Tiny** (22M params) — runs on CPU without GPU
- **Fast** — embeds ~500 sentences/sec on CPU
- **Good quality** — top-10 on sentence similarity benchmarks
- **Free** — no API costs, runs locally

---

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     VIDEO UPLOAD (.mp4)                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │ FFmpeg
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AUDIO EXTRACTION (.wav)                       │
│              + Noise Reduction + Normalization                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┼───────────────┐
          ▼           ▼               ▼
   ┌─────────────┐ ┌────────────┐ ┌───────────┐
   │ AssemblyAI  │ │   Groq     │ │ WhisperX  │
   │ Universal-2 │ │  Whisper   │ │  (local)  │
   │ (STT+Diar)  │ │ V3 Turbo   │ │  medium   │
   └──────┬──────┘ └─────┬──────┘ └─────┬─────┘
          │               │              │
          │         ┌─────┴──────┐       │
          │         │  pyannote  │       │
          │         │ diarize-3.1│◄──────┘
          │         └─────┬──────┘
          │               │
          ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│              TRANSCRIPT (speaker-labeled segments)              │
│              storage/{meeting_id}/transcript.json               │
└──────────┬──────────────┬────────────────┬──────────────────────┘
           │              │                │
     ┌─────▼─────┐  ┌────▼─────┐   ┌──────▼──────┐
     │  Llama    │  │ ECAPA-  │   │ MiniLM-L6  │
     │ 3.3 70B  │  │  TDNN   │   │    -v2     │
     │ (Groq)   │  │(Speaker │   │(Embedding) │
     │          │  │  ID)    │   │            │
     └────┬─────┘  └────┬────┘   └──────┬─────┘
          │              │               │
          ▼              ▼               ▼
   ┌────────────┐ ┌───────────┐  ┌───────────┐
   │ Summary    │ │  Voice    │  │  ChromaDB  │
   │ Actions    │ │ Profiles  │  │  Vector    │
   │ Sentiment  │ │ Matching  │  │   Store    │
   │ Requiremnts│ │           │  │  (RAG)     │
   │ Topics     │ │           │  │            │
   │ MoM/Docs   │ │           │  │            │
   └────────────┘ └───────────┘  └───────────┘
```

---

## Environment Variables for Models

| Variable | Required By | Purpose |
|----------|------------|---------|
| `GROQ_API_KEY` | Llama 3.3, Whisper V3 | API authentication for Groq cloud |
| `ASSEMBLYAI_API_KEY` | AssemblyAI Universal-2 | API authentication for AssemblyAI |
| `HF_TOKEN` | pyannote diarization | HuggingFace token (model license) |
| `STT_MODE` | STT service | `assemblyai` / `groq` / `local` / `auto` |
| `SPEAKERS_EXPECTED` | AssemblyAI | Optional hint for expected speaker count |

---

## Model Size & Resource Comparison

| Model | Parameters | Size on Disk | Runs On | Speed |
|-------|-----------|-------------|---------|-------|
| Llama 3.3 70B | 70B | Cloud (Groq) | Groq LPU | ~800 tok/sec |
| Whisper V3 Turbo | ~1.5B | Cloud (Groq) | Groq LPU | ~10× realtime |
| AssemblyAI U-2 | Proprietary | Cloud | AssemblyAI | ~3× realtime |
| WhisperX medium | 769M | ~1.5 GB | Local GPU/CPU | ~5× realtime (GPU) |
| pyannote 3.1 | ~5M | ~20 MB | Local GPU/CPU | ~50× realtime |
| ECAPA-TDNN | ~15M | ~60 MB | Local CPU | <1 sec/clip |
| all-MiniLM-L6-v2 | 22.7M | ~80 MB | Local CPU | ~500 sent/sec |
