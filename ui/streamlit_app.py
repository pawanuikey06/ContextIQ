import streamlit as st
import requests
 
st.set_page_config(page_title="Meeting Intelligence", layout="centered")
 
st.title("🎥 Meeting Intelligence System")
st.write("Upload a video to get speaker-wise transcription.")
 
VIDEO_TO_AUDIO_URL = "http://localhost:8000/media/video-to-audio"
TRANSCRIBE_AUDIO_URL = "http://localhost:8000/media/transcribe-audio"
 
# --------------------
# Upload Video
# --------------------
uploaded_video = st.file_uploader(
    "Upload video file",
    type=["mp4", "mkv", "mov"]
)
 
if uploaded_video:
    st.success(f"Uploaded: {uploaded_video.name}")
 
    if st.button("🚀 Process Video"):
        with st.spinner("Processing video..."):
            try:
                # Step 1: Video → Audio
                video_files = {
                    "file": (uploaded_video.name, uploaded_video.getvalue())
                }
 
                video_res = requests.post(
                    VIDEO_TO_AUDIO_URL,
                    files=video_files
                )
 
                if video_res.status_code != 200:
                    st.error("❌ Video to audio failed")
                    st.text(video_res.text)
                    st.stop()
 
                audio_path = video_res.json()["audio_path"]
                st.success("✅ Video converted to audio")
 
                # Step 2: Send audio for transcription
                with open(audio_path, "rb") as f:
                    audio_files = {
                        "file": ("audio.wav", f.read())
                    }
 
                transcribe_res = requests.post(
                    TRANSCRIBE_AUDIO_URL,
                    files=audio_files
                )
 
                if transcribe_res.status_code != 200:
                    st.error("❌ Transcription failed")
                    st.text(transcribe_res.text)
                    st.stop()
 
                data = transcribe_res.json()
                segments = data["segments"]
                speaker_transcript = data["speaker_transcript"]
 
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()
 
        # --------------------
        # VIEW 1: WHO SPOKE WHEN
        # --------------------
        st.divider()
        st.subheader("🕒 Who spoke when")
 
        for seg in segments:
            st.markdown(
                f"**{seg['speaker']}** "
                f"[{seg['start']}s → {seg['end']}s]\n\n"
                f"{seg['text']}"
            )
 
        # --------------------
        # VIEW 2: SPEAKER-WISE TRANSCRIPT
        # --------------------
        st.divider()
        st.subheader("🗣 Speaker-wise Transcript")
 
        for speaker, text in speaker_transcript.items():
            st.markdown(f"### {speaker}")
            st.write(text)
 
 