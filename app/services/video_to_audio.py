import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
logger = logging.getLogger(__name__)


class VideoAudioConverter:
    def __init__(self):
        self.ffmpeg_path = os.getenv("FFMPEG_PATH")

        if not self.ffmpeg_path or not Path(self.ffmpeg_path).exists():
            raise RuntimeError(
                "FFMPEG_PATH is not set or ffmpeg.exe not found. "
                "Check your .env configuration."
            )
        logger.info("VideoAudioConverter initialized: ffmpeg=%s", self.ffmpeg_path)

    def video_to_audio(self, video_path: Path, audio_path: Path):
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Extracting audio: %s -> %s", video_path, audio_path)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(video_path),
            "-map", "0:a:0",        # Only take the first audio stream
            "-vn",                   # No video
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(audio_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg failed: %s", result.stderr[-500:])
            raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")

        logger.info("Audio extraction complete: %s (%d bytes)", audio_path, audio_path.stat().st_size)
