import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
from app.services.video_to_audio import VideoAudioConverter
from app.services.stt_service import AudioTranscriptionService
from app.services.speaker_service import SpeakerTranscriptBuilder
 
from app.services.storage_service import MeetingStorageService
 
router = APIRouter()
 
video_converter = VideoAudioConverter()
stt_service = AudioTranscriptionService()
speaker_builder = SpeakerTranscriptBuilder()
storage_service = MeetingStorageService()
 
 
 
@router.post("/video-to-audio")
async def convert_video(file: UploadFile = File(...)):
    if not file.filename.endswith((".mp4", ".mkv", ".mov")):
        raise HTTPException(status_code=400, detail="Unsupported video format")
 
    uid = str(uuid.uuid4())
 
    video_path = Path(f"app/data/{uid}.mp4")
    audio_path = Path(f"app/data/{uid}.wav")
    video_path.parent.mkdir(parents=True, exist_ok=True)
 
    # save uploaded video
    with open(video_path, "wb") as f:
        f.write(await file.read())
 
    # convert
    video_converter.video_to_audio(video_path, audio_path)
 
    return {
        "message": "Video converted to audio successfully",
        "audio_path": str(audio_path)
    }
 
@router.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...)):
    if not file.filename.endswith((".wav", ".mp3", ".m4a")):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
 
    uid = str(uuid.uuid4())
    audio_path = Path(f"app/data/{uid}.wav")
    audio_path.parent.mkdir(parents=True, exist_ok=True)
 
    with open(audio_path, "wb") as f:
        f.write(await file.read())
 
    segments = stt_service.transcribe(str(audio_path))
 
    speaker_transcript = speaker_builder.build(segments)
   
    meeting_id = str(uuid.uuid4())
   
    storage_path = storage_service.save(
    meeting_id,
    {
        "segments": segments,
        "speaker_transcript": speaker_transcript
    }
    )
    return {
    "meeting_id": meeting_id,
    "segments": segments,
    "speaker_transcript": speaker_transcript,
    "stored_at": storage_path
    }
 