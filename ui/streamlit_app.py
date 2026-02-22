"""
ContextIQ — Meeting Intelligence Platform
Premium Streamlit UI with branded design, separated workflows, and polished aesthetics.
Multipage: Meeting Processing + Meeting Chat
"""
import streamlit as st
import requests
import json
import uuid
import pandas as pd

# ─────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="ContextIQ — Meeting Intelligence",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# API URLs
# ─────────────────────────────────────────
API_BASE = "http://localhost:8000"
UPLOAD_URL = f"{API_BASE}/upload-video"
TRANSCRIBE_URL = f"{API_BASE}/transcribe"
MEETING_URL = f"{API_BASE}/meeting"
SUMMARIZE_URL = f"{API_BASE}/summarize"
CHAT_URL = f"{API_BASE}/chat"

# ─────────────────────────────────────────
# Sidebar Navigation
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("""<p style='font-size:1.5rem;font-weight:700;
        background:linear-gradient(135deg,#818cf8,#c084fc);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
        margin-bottom:0.5rem;'>🧠 ContextIQ</p>""", unsafe_allow_html=True)
    page = st.radio(
        "Module",
        ["📋 Meeting Processing", "💬 Meeting Chat"],
        label_visibility="collapsed",
    )

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
# ═══════════════════════════════════════════════════
# PAGE 2: Meeting Chat (if selected, run and stop)
# ═══════════════════════════════════════════════════
if page == "💬 Meeting Chat":

    st.markdown("""
    <div class="hero-container">
        <p class="brand-name">💬 Meeting Chat</p>
        <p class="brand-tagline">Ask questions about your meetings — powered by LangChain + ChromaDB + Gemini</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Initialize chat session ──
    if "chat_session_id" not in st.session_state:
        st.session_state["chat_session_id"] = str(uuid.uuid4())
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    # ── Sidebar: Indexed Meetings ──
    with st.sidebar:
        st.markdown("---")
        st.markdown("**📂 Knowledge Base**")

        # Fetch indexed meetings
        try:
            idx_res = requests.get(f"{CHAT_URL}/meetings", timeout=5)
            if idx_res.status_code == 200:
                indexed = idx_res.json().get("indexed_meetings", [])
            else:
                indexed = []
        except Exception:
            indexed = []

        if indexed:
            st.caption(f"{len(indexed)} meeting(s) indexed")
            selected_meetings = []
            for mid in indexed:
                if st.checkbox(f"📄 {mid[:8]}...", value=True, key=f"chat_m_{mid}"):
                    selected_meetings.append(mid)
        else:
            st.caption("No meetings indexed yet.")
            st.info("Process a meeting first, or index existing ones below.")
            selected_meetings = None

        # Index All button
        st.markdown("---")
        if st.button("� Index All Meetings", use_container_width=True):
            from pathlib import Path
            storage = Path("storage")
            count = 0
            for meeting_dir in storage.iterdir():
                if meeting_dir.is_dir() and (meeting_dir / "transcript.json").exists():
                    mid_name = meeting_dir.name
                    try:
                        requests.post(f"{CHAT_URL}/index/{mid_name}", timeout=30)
                        count += 1
                    except Exception:
                        pass
            st.success(f"✅ Indexed {count} meetings")
            st.rerun()

        # New Chat button
        if st.button("🗑️ New Chat", use_container_width=True):
            st.session_state["chat_messages"] = []
            st.session_state["chat_session_id"] = str(uuid.uuid4())
            try:
                requests.post(
                    f"{CHAT_URL}/clear/{st.session_state['chat_session_id']}",
                    timeout=5,
                )
            except Exception:
                pass
            st.rerun()

    # ── Quick Prompts ──
    if not st.session_state["chat_messages"]:
        st.markdown("""
        <div class="section-header">
            <span class="section-icon">💡</span>
            <p class="section-title">Quick Prompts — Click to get started</p>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        prompts = [
            "📋 Summarize the last meeting",
            "📌 What action items were discussed?",
            "👤 What did each speaker talk about?",
            "🔍 What were the main disagreements?",
        ]
        prompt_cols = st.columns(len(prompts))
        for i, p in enumerate(prompts):
            with prompt_cols[i]:
                if st.button(p, use_container_width=True, key=f"qp_{i}"):
                    st.session_state["chat_messages"].append(
                        {"role": "user", "content": p}
                    )
                    st.rerun()

    # ── Chat History ──
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                with st.expander(f"📎 Sources ({len(msg['citations'])})", expanded=False):
                    for c in msg["citations"]:
                        mins = int(c['start'] // 60)
                        secs = int(c['start'] % 60)
                        st.markdown(
                            f"**{c['speaker']}** • `{mins}:{secs:02d}` • "
                            f"Meeting `{c['meeting_id'][:8]}...`\n\n"
                            f"> {c['excerpt']}"
                        )

    # ── Chat Input ──
    user_input = st.chat_input("Ask about your meetings...")

    if user_input:
        st.session_state["chat_messages"].append(
            {"role": "user", "content": user_input}
        )
        st.rerun()

    # If last message is from user, get AI response
    if (
        st.session_state["chat_messages"]
        and st.session_state["chat_messages"][-1]["role"] == "user"
    ):
        question = st.session_state["chat_messages"][-1]["content"]

        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching meetings..."):
                try:
                    payload = {
                        "question": question,
                        "session_id": st.session_state["chat_session_id"],
                    }
                    if selected_meetings:
                        payload["meeting_ids"] = selected_meetings

                    res = requests.post(
                        f"{CHAT_URL}/ask",
                        json=payload,
                        timeout=60,
                    )

                    if res.status_code == 200:
                        chat_data = res.json()
                        answer = chat_data.get("answer", "Sorry, I couldn't find an answer.")
                        citations = chat_data.get("citations", [])

                        st.markdown(answer)
                        if citations:
                            with st.expander(f"📎 Sources ({len(citations)})", expanded=False):
                                for c in citations:
                                    mins = int(c['start'] // 60)
                                    secs = int(c['start'] % 60)
                                    st.markdown(
                                        f"**{c['speaker']}** • `{mins}:{secs:02d}` • "
                                        f"Meeting `{c['meeting_id'][:8]}...`\n\n"
                                        f"> {c['excerpt']}"
                                    )

                        st.session_state["chat_messages"].append({
                            "role": "assistant",
                            "content": answer,
                            "citations": citations,
                        })
                    else:
                        error_msg = f"❌ Error: {res.text}"
                        st.error(error_msg)
                        st.session_state["chat_messages"].append({
                            "role": "assistant",
                            "content": error_msg,
                        })
                except requests.exceptions.ConnectionError:
                    err_msg = "❌ Cannot connect to backend. Make sure FastAPI is running."
                    st.error(err_msg)
                    st.session_state["chat_messages"].append(
                        {"role": "assistant", "content": err_msg}
                    )
                except Exception as e:
                    err_msg = f"❌ Error: {e}"
                    st.error(err_msg)
                    st.session_state["chat_messages"].append(
                        {"role": "assistant", "content": err_msg}
                    )

    # Footer for chat page
    st.markdown("""
    <div class="footer">
        Built with ❤️ by <strong>ContextIQ</strong> • AI-Powered Meeting Intelligence Platform
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════
# PAGE 1: Meeting Processing (default, falls through)
# ═══════════════════════════════════════════════════

# ─────────────────────────────────────────
# Hero Banner
# ─────────────────────────────────────────

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

    # ── Speaker Name Mapping (HITL) ──
    # Initialize speaker map in session state
    if "speaker_map" not in st.session_state:
        # Try to load saved mapping from backend
        try:
            map_res = requests.get(f"{API_BASE}/meeting/{meeting_id}/speaker-map", timeout=5)
            if map_res.status_code == 200:
                st.session_state["speaker_map"] = map_res.json().get("speaker_map", {})
            else:
                st.session_state["speaker_map"] = {}
        except Exception:
            st.session_state["speaker_map"] = {}

    smap = st.session_state["speaker_map"]

    # Helper: resolve display name
    def display_name(spk_id):
        return smap.get(spk_id, spk_id)

    with st.expander("✏️ Speaker Name Mapping — click to rename speakers", expanded=False):
        st.caption("Replace auto-detected speaker IDs with real names. Click 'Apply Names' to save.")
        speaker_ids = list(speakers.keys())
        rename_cols = st.columns(min(len(speaker_ids), 3))

        new_map = {}
        for i, spk_id in enumerate(speaker_ids):
            with rename_cols[i % min(len(speaker_ids), 3)]:
                new_name = st.text_input(
                    spk_id,
                    value=smap.get(spk_id, ""),
                    placeholder=f"e.g. Pawan",
                    key=f"rename_{spk_id}",
                )
                if new_name.strip():
                    new_map[spk_id] = new_name.strip()

        apply_col, clear_col, _ = st.columns([1, 1, 3])
        with apply_col:
            if st.button("✅ Apply Names", type="primary", use_container_width=True):
                st.session_state["speaker_map"] = new_map
                # Save to backend
                try:
                    requests.post(
                        f"{API_BASE}/meeting/{meeting_id}/speaker-map",
                        json={"speaker_map": new_map},
                        timeout=5,
                    )
                except Exception:
                    pass
                st.rerun()
        with clear_col:
            if st.button("🔄 Reset Names", use_container_width=True):
                st.session_state["speaker_map"] = {}
                try:
                    requests.post(
                        f"{API_BASE}/meeting/{meeting_id}/speaker-map",
                        json={"speaker_map": {}},
                        timeout=5,
                    )
                except Exception:
                    pass
                st.rerun()

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
            name = display_name(spk)

            st.markdown(f"""
            <div class="chat-bubble">
                <div class="chat-speaker {color_class}">
                    {name} <span class="chat-time">{seg['start']:.1f}s – {seg['end']:.1f}s</span>
                </div>
                <div class="chat-text">{seg['text']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ─── TAB 2: Speaker View ───
    with tab2:
        for speaker, segs in speakers.items():
            name = display_name(speaker)
            with st.expander(f"🗣️ {name} — {len(segs)} segments", expanded=False):
                for s in segs:
                    st.markdown(
                        f"**`{s['start']:.1f}s – {s['end']:.1f}s`** &nbsp; {s['text']}",
                        unsafe_allow_html=True,
                    )

    # ─── TAB 3: Timeline Table ───
    with tab3:
        df = pd.DataFrame(segments)
        df.columns = ["Start (s)", "End (s)", "Speaker", "Text"]
        # Apply mapped speaker names
        df["Speaker"] = df["Speaker"].map(lambda s: display_name(s))
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
                    # Sync speaker map to backend before generating
                    if smap:
                        requests.post(
                            f"{API_BASE}/meeting/{meeting_id}/speaker-map",
                            json={"speaker_map": smap},
                            timeout=5,
                        )
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
                        st.session_state.pop("summary_approved", None)
                        st.rerun()
                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to backend. Make sure FastAPI is running.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        # Display summaries
        if "summary_data" in st.session_state:
            summary = st.session_state["summary_data"]

            # Speaker-wise summaries (use mapped names)
            st.markdown("""
            <div class="section-header">
                <span class="section-icon">🗣️</span>
                <p class="section-title">Speaker-wise Summaries</p>
                <div class="section-line"></div>
            </div>
            """, unsafe_allow_html=True)

            speaker_sums = summary.get("speaker_summaries_en", {})
            cols = st.columns(min(len(speaker_sums), 2)) if speaker_sums else [st]
            for i, (speaker, text) in enumerate(speaker_sums.items()):
                name = display_name(speaker)
                with cols[i % min(len(speaker_sums), 2)]:
                    st.markdown(f"""
                    <div class="summary-card">
                        <div class="summary-card-title">🗣️ {name}</div>
                        <div class="summary-card-content">{text}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # ── Summary Approval (HITL) ──
            st.markdown("""
            <div class="section-header">
                <span class="section-icon">✏️</span>
                <p class="section-title">Review & Approve Summary</p>
                <div class="section-line"></div>
            </div>
            """, unsafe_allow_html=True)
            st.caption("Review the AI-generated summaries below. Edit if needed, then approve before publishing.")

            # Editable English summary
            st.markdown("**Overall Summary — English**")
            edited_en = st.text_area(
                "English Summary",
                value=summary.get("overall_summary_en", ""),
                height=150,
                key="edit_summary_en",
                label_visibility="collapsed",
            )

            # Editable Hindi summary
            st.markdown("**Overall Summary — हिंदी**")
            edited_hi = st.text_area(
                "Hindi Summary",
                value=summary.get("overall_summary_hi", ""),
                height=150,
                key="edit_summary_hi",
                label_visibility="collapsed",
            )

            # Approve / Rewrite buttons side by side
            approve_col, rewrite_col, spacer_col = st.columns([1, 1, 2])
            with approve_col:
                approve_btn = st.button("✅ Approve Summary", type="primary", use_container_width=True)
            with rewrite_col:
                show_rewrite = st.button("🔄 Rewrite Summary", use_container_width=True)

            # Rewrite section (expandable)
            if show_rewrite:
                st.session_state["show_rewrite_ui"] = True

            if st.session_state.get("show_rewrite_ui", False):
                st.markdown("**🔄 Rewrite with Custom Instructions**")
                st.caption("Add your instructions below and click Rewrite to regenerate the summary.")
                rewrite_prompt = st.text_area(
                    "Custom instructions",
                    placeholder="e.g. Focus more on action items, keep it shorter, use bullet points...",
                    height=80,
                    key="rewrite_prompt_input",
                    label_visibility="collapsed",
                )
                rewrite_go = st.button("🚀 Rewrite Now", type="primary")
                if rewrite_go:
                    if not rewrite_prompt.strip():
                        st.warning("⚠️ Please enter custom instructions.")
                    else:
                        with st.spinner("🔄 Rewriting summary with your instructions..."):
                            try:
                                # Sync speaker map to backend before rewriting
                                if smap:
                                    requests.post(
                                        f"{API_BASE}/meeting/{meeting_id}/speaker-map",
                                        json={"speaker_map": smap},
                                        timeout=5,
                                    )
                                params = {
                                    "force": "true",
                                    "extra_prompt": rewrite_prompt.strip(),
                                }
                                res = requests.post(
                                    f"{SUMMARIZE_URL}/{meeting_id}",
                                    params=params,
                                    timeout=300,
                                )
                                if res.status_code != 200:
                                    st.error(f"❌ Rewrite failed: {res.text}")
                                else:
                                    st.session_state["summary_data"] = res.json()
                                    st.session_state.pop("summary_approved", None)
                                    st.session_state.pop("show_rewrite_ui", None)
                                    st.rerun()
                            except requests.exceptions.ConnectionError:
                                st.error("❌ Cannot connect to backend.")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")

            if approve_btn:
                # Save edited summaries back
                summary["overall_summary_en"] = edited_en
                summary["overall_summary_hi"] = edited_hi
                st.session_state["summary_data"] = summary
                st.session_state["summary_approved"] = True

                # Persist to disk via summary.json
                import pathlib
                summary_path = pathlib.Path(f"storage/{meeting_id}/summary.json")
                if summary_path.exists():
                    try:
                        with open(summary_path, "w", encoding="utf-8") as f:
                            json.dump(summary, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                st.success("✅ Summary approved and saved! You can now publish.")

            # ── Publish (only after approval) ──
            if st.session_state.get("summary_approved", False):
                st.markdown("""
                <div class="section-header">
                    <span class="section-icon">📤</span>
                    <p class="section-title">Publish & Share</p>
                    <div class="section-line"></div>
                </div>
                """, unsafe_allow_html=True)
                st.caption("Summary approved. Generate PDF, send via Email, or post to Teams.")

                pub_col1, pub_col2, pub_col3, pub_col4 = st.columns(4)

                with pub_col1:
                    pdf_btn = st.button("📄 Download PDF", type="primary", use_container_width=True)
                with pub_col2:
                    email_btn = st.button("📧 Send Email", use_container_width=True)
                with pub_col3:
                    teams_btn = st.button("💬 Send to Teams", use_container_width=True)
                with pub_col4:
                    all_btn = st.button("🚀 Publish All", type="primary", use_container_width=True)

                # ── PDF Download ──
                if pdf_btn:
                    with st.spinner("Generating PDF..."):
                        try:
                            pub_res = requests.post(
                                f"{API_BASE}/publish/{meeting_id}",
                                json={"meeting_title": f"Meeting {meeting_id[:8]}"},
                                timeout=30,
                            )
                            if pub_res.status_code == 200:
                                pdf_dl = requests.get(f"{API_BASE}/publish/{meeting_id}/pdf", timeout=10)
                                if pdf_dl.status_code == 200:
                                    st.download_button(
                                        "⬇️ Click to download PDF",
                                        data=pdf_dl.content,
                                        file_name="Meeting_Summary.pdf",
                                        mime="application/pdf",
                                        use_container_width=True,
                                    )
                                else:
                                    st.error("PDF download failed.")
                            else:
                                st.error(f"PDF generation failed: {pub_res.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")

                # ── Email ──
                if email_btn:
                    with st.spinner("Generating PDF & sending email..."):
                        try:
                            pub_res = requests.post(
                                f"{API_BASE}/publish/{meeting_id}",
                                json={
                                    "meeting_title": f"Meeting {meeting_id[:8]}",
                                    "email_recipients": ["pawanuikey690@gmail.com"],
                                },
                                timeout=60,
                            )
                            if pub_res.status_code == 200:
                                result = pub_res.json()
                                email_ok = result.get("email", {}).get("success")
                                if email_ok:
                                    st.success(f"✅ {result['email']['message']}")
                                else:
                                    st.warning(f"⚠️ {result['email'].get('message', 'Unknown')}")
                            else:
                                st.error(f"Failed: {pub_res.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")

                # ── Teams ──
                if teams_btn:
                    with st.spinner("Sending to Teams..."):
                        try:
                            pub_res = requests.post(
                                f"{API_BASE}/publish/{meeting_id}",
                                json={"meeting_title": f"Meeting {meeting_id[:8]}"},
                                timeout=30,
                            )
                            if pub_res.status_code == 200:
                                result = pub_res.json()
                                teams_ok = result.get("teams", {}).get("success")
                                if teams_ok:
                                    st.success(f"✅ {result['teams']['message']}")
                                else:
                                    st.warning(f"⚠️ {result['teams'].get('message', 'Unknown')}")
                            else:
                                st.error(f"Failed: {pub_res.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")

                # ── Publish All ──
                if all_btn:
                    with st.spinner("Publishing everywhere..."):
                        try:
                            pub_res = requests.post(
                                f"{API_BASE}/publish/{meeting_id}",
                                json={
                                    "meeting_title": f"Meeting {meeting_id[:8]}",
                                    "email_recipients": ["pawanuikey690@gmail.com"],
                                },
                                timeout=60,
                            )
                            if pub_res.status_code == 200:
                                result = pub_res.json()
                                _cols = st.columns(3)
                                with _cols[0]:
                                    if result.get("pdf", {}).get("success"):
                                        st.success("📄 PDF ✅")
                                    else:
                                        st.error("📄 PDF ❌")
                                with _cols[1]:
                                    if result.get("email", {}).get("success"):
                                        st.success("📧 Email ✅")
                                    else:
                                        st.error("📧 Email ❌")
                                with _cols[2]:
                                    if result.get("teams", {}).get("success"):
                                        st.success("💬 Teams ✅")
                                    else:
                                        st.error("💬 Teams ❌")

                                if result.get("pdf", {}).get("success"):
                                    pdf_dl = requests.get(f"{API_BASE}/publish/{meeting_id}/pdf", timeout=10)
                                    if pdf_dl.status_code == 200:
                                        st.download_button(
                                            "⬇️ Download PDF",
                                            data=pdf_dl.content,
                                            file_name="Meeting_Summary.pdf",
                                            mime="application/pdf",
                                            use_container_width=True,
                                        )
                            else:
                                st.error(f"Publish failed: {pub_res.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")
            else:
                st.info("👆 Review the summaries above and click **Approve Summary** to unlock publishing.")

            st.markdown("<br>", unsafe_allow_html=True)

            # Download JSON
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