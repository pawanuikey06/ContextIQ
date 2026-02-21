"""
Streamlit UI for Meeting Intelligence System.
Calls FastAPI backend: upload → transcribe → display results.
"""
import streamlit as st
import requests

st.set_page_config(page_title="Meeting Intelligence", layout="wide")

# --------------------
# API URLs
# --------------------
API_BASE = "http://localhost:8000"
UPLOAD_URL = f"{API_BASE}/upload-video"
TRANSCRIBE_URL = f"{API_BASE}/transcribe"
MEETING_URL = f"{API_BASE}/meeting"

# --------------------
# Header
# --------------------
st.title("🎥 Meeting Intelligence System")
st.markdown("Upload a video to get **speaker-wise**, **timestamped** transcription with diarization.")
st.divider()

# --------------------
# Upload Video
# --------------------
uploaded_video = st.file_uploader(
    "Upload video file",
    type=["mp4", "mkv", "mov"],
    help="Supported formats: MP4, MKV, MOV"
)

if uploaded_video:
    st.success(f"📁 Selected: **{uploaded_video.name}** ({uploaded_video.size / (1024*1024):.1f} MB)")

    if st.button("🚀 Process Video", type="primary"):
        data = None

        with st.status("Processing video...", expanded=True) as status:

            # ─── Step 1: Upload & Extract Audio ───
            st.write("📤 Uploading video and extracting audio...")
            try:
                files = {"file": (uploaded_video.name, uploaded_video.getvalue())}
                upload_res = requests.post(UPLOAD_URL, files=files, timeout=120)

                if upload_res.status_code != 200:
                    st.error(f"❌ Upload failed: {upload_res.text}")
                    status.update(label="Failed", state="error")
                    st.stop()

                upload_data = upload_res.json()
                meeting_id = upload_data["meeting_id"]
                audio_path = upload_data["audio_path"]
                st.write(f"✅ Audio extracted → `{audio_path}`")
                st.write(f"📋 Meeting ID: `{meeting_id}`")

            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot connect to backend. Is FastAPI running on port 8000?")
                status.update(label="Connection Error", state="error")
                st.stop()
            except Exception as e:
                st.error(f"❌ Upload error: {e}")
                status.update(label="Failed", state="error")
                st.stop()

            # ─── Step 2: Transcribe + Diarize ───
            st.write("🎙️ Transcribing audio and identifying speakers...")
            try:
                transcribe_res = requests.post(
                    f"{TRANSCRIBE_URL}/{meeting_id}",
                    timeout=600  # Transcription can take a while on CPU
                )

                if transcribe_res.status_code != 200:
                    st.error(f"❌ Transcription failed: {transcribe_res.text}")
                    status.update(label="Transcription Failed", state="error")
                    st.stop()

                data = transcribe_res.json()
                segments = data["segments"]
                speakers = data["speakers"]
                st.write(f"✅ Transcription complete: **{len(segments)} segments**, **{len(speakers)} speakers**")

            except Exception as e:
                st.error(f"❌ Transcription error: {e}")
                status.update(label="Failed", state="error")
                st.stop()

            status.update(label="✅ Processing complete!", state="complete")

        # ─── Display Results ───
        if data:
            st.session_state["transcript_data"] = data

# --------------------
# Display Results (persists across reruns)
# --------------------
if "transcript_data" in st.session_state:
    data = st.session_state["transcript_data"]
    segments = data["segments"]
    speakers = data["speakers"]
    meeting_id = data["meeting_id"]

    st.divider()
    st.markdown(f"### 📋 Meeting: `{meeting_id}`")

    tab1, tab2, tab3 = st.tabs(["💬 Chat View", "🗣️ Speaker View", "🕒 Timestamp View"])

    # ─── TAB 1: Chat-style transcript ───
    with tab1:
        # Assign colors to speakers
        speaker_colors = {}
        color_palette = ["🔵", "🟢", "🟠", "🟣", "🔴", "🟡"]
        for i, spk in enumerate(speakers.keys()):
            speaker_colors[spk] = color_palette[i % len(color_palette)]

        for seg in segments:
            icon = speaker_colors.get(seg["speaker"], "⚪")
            st.markdown(
                f"{icon} **{seg['speaker']}** "
                f"<small style='color:gray'>({seg['start']:.1f}s – {seg['end']:.1f}s)</small>",
                unsafe_allow_html=True
            )
            st.markdown(f"> {seg['text']}")
            st.write("")

    # ─── TAB 2: Speaker-wise expandable view ───
    with tab2:
        for speaker, segs in speakers.items():
            with st.expander(f"🗣️ {speaker} ({len(segs)} segments)", expanded=False):
                for s in segs:
                    st.markdown(
                        f"**[{s['start']:.1f}s – {s['end']:.1f}s]** {s['text']}"
                    )

    # ─── TAB 3: Timestamp table ───
    with tab3:
        import pandas as pd
        df = pd.DataFrame(segments)
        df.columns = ["Start (s)", "End (s)", "Speaker", "Text"]
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ─── Download button ───
    st.divider()
    import json
    st.download_button(
        label="📥 Download Transcript JSON",
        data=json.dumps(data, indent=2, ensure_ascii=False),
        file_name=f"transcript_{meeting_id}.json",
        mime="application/json"
    )