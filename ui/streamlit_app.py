"""
ContextIQ — Meeting Intelligence Platform
Premium Streamlit UI with branded design, separated workflows, and polished aesthetics.
"""
import streamlit as st
import requests
import json
import pandas as pd

# ─────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="ContextIQ — Meeting Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────
# API URLs
# ─────────────────────────────────────────
API_BASE = "http://localhost:8000"
UPLOAD_URL = f"{API_BASE}/upload-video"
TRANSCRIBE_URL = f"{API_BASE}/transcribe"
MEETING_URL = f"{API_BASE}/meeting"
SUMMARIZE_URL = f"{API_BASE}/summarize"

# ─────────────────────────────────────────
# Custom CSS — Premium Dark Theme
# ─────────────────────────────────────────
st.markdown("""
<style>
    /* ── Import Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Global ── */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ── Hero Banner ── */
    .hero-container {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-container::after {
        content: '';
        position: absolute;
        bottom: -30%;
        left: 10%;
        width: 300px;
        height: 300px;
        background: radial-gradient(circle, rgba(168,85,247,0.1) 0%, transparent 70%);
        border-radius: 50%;
    }
    .brand-name {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -1px;
        position: relative;
        z-index: 1;
    }
    .brand-tagline {
        color: rgba(255,255,255,0.6);
        font-size: 1.1rem;
        font-weight: 300;
        margin-top: 0.3rem;
        letter-spacing: 0.5px;
        position: relative;
        z-index: 1;
    }
    .brand-badge {
        display: inline-block;
        background: rgba(99,102,241,0.15);
        border: 1px solid rgba(99,102,241,0.3);
        color: #a5b4fc;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 20px;
        margin-left: 12px;
        letter-spacing: 1px;
        text-transform: uppercase;
        vertical-align: middle;
        position: relative;
        z-index: 1;
    }

    /* ── Metric Cards ── */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin: 1.5rem 0;
    }
    .metric-card {
        flex: 1;
        background: linear-gradient(135deg, rgba(30,27,75,0.6), rgba(55,48,107,0.4));
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        backdrop-filter: blur(12px);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label {
        color: rgba(255,255,255,0.5);
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.2rem;
    }

    /* ── Section Headers ── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 1.5rem 0 0.8rem 0;
    }
    .section-icon {
        font-size: 1.4rem;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: #e2e8f0;
        margin: 0;
    }
    .section-line {
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, rgba(99,102,241,0.3), transparent);
        margin-left: 0.5rem;
    }

    /* ── Chat Bubble ── */
    .chat-bubble {
        background: rgba(30, 27, 75, 0.35);
        border: 1px solid rgba(99,102,241,0.12);
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.6rem;
        transition: border-color 0.2s;
    }
    .chat-bubble:hover {
        border-color: rgba(129,140,248,0.3);
    }
    .chat-speaker {
        font-weight: 600;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
    }
    .chat-time {
        color: rgba(255,255,255,0.35);
        font-size: 0.7rem;
        font-weight: 400;
        margin-left: 0.5rem;
    }
    .chat-text {
        color: rgba(255,255,255,0.8);
        font-size: 0.9rem;
        line-height: 1.5;
    }

    /* ── Speaker Color Badges ── */
    .spk-0 { color: #818cf8; }
    .spk-1 { color: #34d399; }
    .spk-2 { color: #fb923c; }
    .spk-3 { color: #c084fc; }
    .spk-4 { color: #f87171; }
    .spk-5 { color: #fbbf24; }

    /* ── Summary Cards ── */
    .summary-card {
        background: linear-gradient(135deg, rgba(30,27,75,0.5), rgba(55,48,107,0.3));
        border: 1px solid rgba(99,102,241,0.15);
        border-radius: 14px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 1rem;
    }
    .summary-card-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #a5b4fc;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.6rem;
    }
    .summary-card-content {
        color: rgba(255,255,255,0.8);
        font-size: 0.92rem;
        line-height: 1.65;
    }

    /* ── Hindi Card Special ── */
    .hindi-card {
        border-color: rgba(251,146,60,0.25);
        background: linear-gradient(135deg, rgba(55,30,15,0.4), rgba(80,45,20,0.2));
    }
    .hindi-card .summary-card-title {
        color: #fb923c;
    }

    /* ── Upload Zone ── */
    .upload-zone {
        background: linear-gradient(135deg, rgba(30,27,75,0.3), rgba(55,48,107,0.15));
        border: 2px dashed rgba(99,102,241,0.25);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1rem;
    }

    /* ── Meeting ID Pill ── */
    .meeting-pill {
        display: inline-block;
        background: rgba(99,102,241,0.12);
        border: 1px solid rgba(99,102,241,0.25);
        color: #a5b4fc;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        padding: 4px 14px;
        border-radius: 20px;
        letter-spacing: 0.3px;
    }

    /* ── Footer ── */
    .footer {
        text-align: center;
        color: rgba(255,255,255,0.25);
        font-size: 0.75rem;
        margin-top: 3rem;
        padding: 1rem 0;
        border-top: 1px solid rgba(255,255,255,0.05);
    }

    /* ── Button Styling ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 4px 20px rgba(99,102,241,0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Tab styling ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: 0.5rem 1.2rem !important;
        font-weight: 500 !important;
    }

    /* ── Dataframe scrollable fix ── */
    .stDataFrame > div {
        overflow-x: auto !important;
    }
    .stDataFrame [data-testid="stDataFrameResizable"] {
        overflow-x: auto !important;
        max-width: 100% !important;
    }

    /* ── Hide Streamlit branding ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Hero Banner
# ─────────────────────────────────────────
st.markdown("""
<div class="hero-container">
    <p class="brand-name">ContextIQ <span class="brand-badge">AI-Powered</span></p>
    <p class="brand-tagline">Transform meetings into actionable intelligence — transcribe, diarize, and summarize with AI</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Step 1: Upload Video
# ─────────────────────────────────────────
st.markdown("""
<div class="section-header">
    <span class="section-icon">📤</span>
    <p class="section-title">Upload & Process</p>
    <div class="section-line"></div>
</div>
""", unsafe_allow_html=True)

col_upload, col_action = st.columns([3, 1])

with col_upload:
    uploaded_video = st.file_uploader(
        "Drop your meeting video here",
        type=["mp4", "mkv", "mov"],
        help="Supported: MP4, MKV, MOV • Max recommended: 500 MB",
        label_visibility="collapsed",
    )

with col_action:
    st.write("")  # spacing
    process_btn = st.button("🚀 Process Video", type="primary", use_container_width=True, disabled=not uploaded_video)

if uploaded_video:
    size_mb = uploaded_video.size / (1024 * 1024)
    st.markdown(f"📁 **{uploaded_video.name}** — {size_mb:.1f} MB ready to process")

if uploaded_video and process_btn:
    data = None

    with st.status("🔄 Processing your meeting video...", expanded=True) as status:

        # Step 1: Upload & Extract Audio
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
            st.write(f"✅ Audio extracted • Meeting ID: `{meeting_id}`")

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend. Is FastAPI running on port 8000?")
            status.update(label="Connection Error", state="error")
            st.stop()
        except Exception as e:
            st.error(f"❌ Upload error: {e}")
            status.update(label="Failed", state="error")
            st.stop()

        # Step 2: Transcribe + Diarize
        st.write("🎙️ Transcribing audio and identifying speakers...")
        try:
            transcribe_res = requests.post(
                f"{TRANSCRIBE_URL}/{meeting_id}",
                timeout=600,
            )

            if transcribe_res.status_code != 200:
                st.error(f"❌ Transcription failed: {transcribe_res.text}")
                status.update(label="Transcription Failed", state="error")
                st.stop()

            data = transcribe_res.json()
            segments = data["segments"]
            speakers = data["speakers"]
            st.write(f"✅ Done — **{len(segments)} segments** from **{len(speakers)} speakers**")

        except Exception as e:
            st.error(f"❌ Transcription error: {e}")
            status.update(label="Failed", state="error")
            st.stop()

        status.update(label="✅ Processing complete!", state="complete")

    if data:
        st.session_state["transcript_data"] = data
        st.session_state.pop("summary_data", None)  # clear old summary

# ═════════════════════════════════════════
# Results Section
# ═════════════════════════════════════════
if "transcript_data" in st.session_state:
    data = st.session_state["transcript_data"]
    segments = data["segments"]
    speakers = data["speakers"]
    meeting_id = data["meeting_id"]

    # ── Meeting Info Bar ──
    st.markdown(f"""
    <div class="section-header">
        <span class="section-icon">📋</span>
        <p class="section-title">Meeting Results</p>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<span class="meeting-pill">🆔 {meeting_id}</span>', unsafe_allow_html=True)

    # ── Metric Cards ──
    num_speakers = len(speakers)
    num_segments = len(segments)
    total_dur = max((s["end"] for s in segments), default=0)
    dur_min = int(total_dur // 60)
    dur_sec = int(total_dur % 60)

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-value">{num_speakers}</div>
            <div class="metric-label">Speakers</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{num_segments}</div>
            <div class="metric-label">Segments</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{dur_min}:{dur_sec:02d}</div>
            <div class="metric-label">Duration</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Chat View", "🗣️ Speaker View", "📊 Timeline", "🧠 AI Summaries"
    ])

    # ─── TAB 1: Chat View ───
    with tab1:
        speaker_list = list(speakers.keys())
        for seg in segments:
            spk = seg["speaker"]
            idx = speaker_list.index(spk) if spk in speaker_list else 0
            color_class = f"spk-{idx % 6}"

            st.markdown(f"""
            <div class="chat-bubble">
                <div class="chat-speaker {color_class}">
                    {spk} <span class="chat-time">{seg['start']:.1f}s – {seg['end']:.1f}s</span>
                </div>
                <div class="chat-text">{seg['text']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ─── TAB 2: Speaker View ───
    with tab2:
        for speaker, segs in speakers.items():
            with st.expander(f"🗣️ {speaker} — {len(segs)} segments", expanded=False):
                for s in segs:
                    st.markdown(
                        f"**`{s['start']:.1f}s – {s['end']:.1f}s`** &nbsp; {s['text']}",
                        unsafe_allow_html=True,
                    )

    # ─── TAB 3: Timeline Table ───
    with tab3:
        df = pd.DataFrame(segments)
        df.columns = ["Start (s)", "End (s)", "Speaker", "Text"]
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=500,
            column_config={
                "Start (s)": st.column_config.NumberColumn(format="%.1f", width="small"),
                "End (s)": st.column_config.NumberColumn(format="%.1f", width="small"),
                "Speaker": st.column_config.TextColumn(width="small"),
                "Text": st.column_config.TextColumn(width="large"),
            },
        )

    # ─── TAB 4: AI Summaries ───
    with tab4:
        st.markdown("""
        <div class="section-header">
            <span class="section-icon">🧠</span>
            <p class="section-title">AI-Powered Meeting Summaries</p>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)
        st.caption("Generate intelligent summaries in English and Hindi using AI.")

        col_gen, col_regen, col_spacer = st.columns([1, 1, 3])
        with col_gen:
            generate_btn = st.button("✨ Generate Summary", type="primary", use_container_width=True)
        with col_regen:
            force_regen = st.checkbox("♻️ Force regenerate", value=False)

        # Generate on click
        if generate_btn:
            with st.spinner("🧠 AI is analyzing your meeting... This may take up to a minute."):
                try:
                    params = {"force": "true"} if force_regen else {}
                    res = requests.post(
                        f"{SUMMARIZE_URL}/{meeting_id}",
                        params=params,
                        timeout=300,
                    )
                    if res.status_code != 200:
                        st.error(f"❌ Summary generation failed: {res.text}")
                    else:
                        st.session_state["summary_data"] = res.json()
                        st.rerun()
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend. Make sure FastAPI is running.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        # Display summaries
        if "summary_data" in st.session_state:
            summary = st.session_state["summary_data"]

            # Speaker-wise summaries
            st.markdown("""
            <div class="section-header">
                <span class="section-icon">🗣️</span>
                <p class="section-title">Speaker-wise Summaries</p>
                <div class="section-line"></div>
            </div>
            """, unsafe_allow_html=True)

            speaker_sums = summary.get("speaker_summaries_en", {})
            cols = st.columns(min(len(speaker_sums), 2))
            for i, (speaker, text) in enumerate(speaker_sums.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div class="summary-card">
                        <div class="summary-card-title">🗣️ {speaker}</div>
                        <div class="summary-card-content">{text}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Overall English summary
            st.markdown("""
            <div class="section-header">
                <span class="section-icon">🌐</span>
                <p class="section-title">Overall Summary — English</p>
                <div class="section-line"></div>
            </div>
            """, unsafe_allow_html=True)

            en_text = summary.get("overall_summary_en", "N/A").replace('\n', '<br>')
            st.markdown(f"""
            <div class="summary-card">
                <div class="summary-card-content">{en_text}</div>
            </div>
            """, unsafe_allow_html=True)

            # Overall Hindi summary
            st.markdown("""
            <div class="section-header">
                <span class="section-icon">🇮🇳</span>
                <p class="section-title">Overall Summary — हिंदी</p>
                <div class="section-line"></div>
            </div>
            """, unsafe_allow_html=True)

            hi_text = summary.get("overall_summary_hi", "N/A").replace('\n', '<br>')
            st.markdown(f"""
            <div class="summary-card hindi-card">
                <div class="summary-card-content">{hi_text}</div>
            </div>
            """, unsafe_allow_html=True)

            # Download buttons
            dl1, dl2, dl3 = st.columns(3)
            with dl1:
                st.download_button(
                    "📥 Download Summary JSON",
                    data=json.dumps(summary, indent=2, ensure_ascii=False),
                    file_name=f"summary_{meeting_id}.json",
                    mime="application/json",
                    use_container_width=True,
                )

    # ── Global Download ──
    st.markdown("<br>", unsafe_allow_html=True)
    dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 3])
    with dl_col1:
        st.download_button(
            "📥 Download Transcript",
            data=json.dumps(data, indent=2, ensure_ascii=False),
            file_name=f"transcript_{meeting_id}.json",
            mime="application/json",
            use_container_width=True,
        )

# ─────────────────────────────────────────
# Footer
# ─────────────────────────────────────────
st.markdown("""
<div class="footer">
    Built with ❤️ by <strong>ContextIQ</strong> • AI-Powered Meeting Intelligence Platform
</div>
""", unsafe_allow_html=True)