import sys
sys.path.append(r"C:\Users\JaiP\OneDrive\Documents\JaPari\src\IR")

import streamlit as st
import os
import json
from chatbot import RAGChatbot

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Document Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

import glob

# ─────────────────────────────────────────────
# Load all gdrive_links.json files from dataset folder
# ─────────────────────────────────────────────
@st.cache_data
def load_file_links(dataset_root: str):
    """
    Recursively find all gdrive_links.json files and merge them.
    Also extracts branch + semester from folder path.
    """
    mapping = {}
    
    if not os.path.exists(dataset_root):
        st.warning(f"Dataset folder not found: {dataset_root}")
        return mapping

    # Find all gdrive_links.json files recursively
    pattern = os.path.join(dataset_root, "**", "gdrive_links.json")
    json_files = glob.glob(pattern, recursive=True)

    if not json_files:
        st.warning(f"No gdrive_links.json files found in {dataset_root}")
        return mapping

    for json_path in json_files:
        # Extract branch and semester from path
        # e.g. .../study_material/CSE/3/gdrive_links.json
        parts = os.path.normpath(json_path).split(os.sep)
        try:
            # Find branch and semester (folder right after study_material)
            sm_idx  = parts.index("study_material")
            branch  = parts[sm_idx + 1] if sm_idx + 1 < len(parts) else ""
            sem     = parts[sm_idx + 2] if sm_idx + 2 < len(parts) else ""
        except ValueError:
            branch, sem = "", ""

        # Load this file
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                name = item.get("item_name", "").strip()
                url  = item.get("original_url", "")
                if name and url:
                    mapping[name] = {
                        "url":      url,
                        "subject":  item.get("subject", ""),
                        "category": item.get("category", ""),
                        "branch":   branch,
                        "semester": sem,
                    }
        except Exception as e:
            st.warning(f"Could not load {json_path}: {e}")

    return mapping


# ─────────────────────────────────────────────
# Load (change path to your dataset folder)
# ─────────────────────────────────────────────
DATASET_ROOT = r"dataset\study_material"
FILE_LINKS   = load_file_links(DATASET_ROOT)


# ─────────────────────────────────────────────
# Theme state
# ─────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True   # default to dark


# ─────────────────────────────────────────────
# Theme CSS
# ─────────────────────────────────────────────
def get_theme_css(dark_mode: bool) -> str:
    if dark_mode:
        # Dark theme colors
        bg            = "#0e1117"
        bg_secondary  = "#1a1d29"
        bg_tertiary   = "#262936"
        text          = "#fafafa"
        text_muted    = "#a0a0a0"
        border        = "#2d3142"
        accent        = "#7c8aff"
        accent_hover  = "#5a6fff"
        user_bg       = "#1e3a5f"
        bot_bg        = "#2a1e3f"
        source_bg     = "#1a1d29"
        source_border = "#7c8aff"
        gradient      = "linear-gradient(135deg, #4a3a8a 0%, #2a1e5e 100%)"
        shadow        = "0 4px 12px rgba(0, 0, 0, 0.4)"
    else:
        # Light theme colors
        bg            = "#ffffff"
        bg_secondary  = "#f0f2f6"
        bg_tertiary   = "#e6e9ef"
        text          = "#262730"
        text_muted    = "#5a5a5a"
        border        = "#d0d4dc"
        accent        = "#667eea"
        accent_hover  = "#5568d3"
        user_bg       = "#e3f2fd"
        bot_bg        = "#f3e5f5"
        source_bg     = "#f0f2f6"
        source_border = "#667eea"
        gradient      = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        shadow        = "0 4px 12px rgba(0, 0, 0, 0.1)"

    return f"""
    <style>
        /* ── App background ────────────────── */
        .stApp {{
            background-color: {bg};
            color: {text};
        }}

        /* ── Sidebar ───────────────────────── */
        section[data-testid="stSidebar"] {{
            background-color: {bg_secondary};
        }}
        section[data-testid="stSidebar"] * {{
            color: {text} !important;
        }}

        /* ── Header banner ─────────────────── */
        .main-header {{
            text-align: center;
            padding: 1.5rem 1rem;
            background: {gradient};
            color: white !important;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: {shadow};
        }}
        .main-header h1 {{
            color: white !important;
            margin: 0;
            font-size: 2.2rem;
        }}
        .main-header p {{
            color: rgba(255, 255, 255, 0.9) !important;
            margin: 0.5rem 0 0 0;
        }}

        /* ── Source box ────────────────────── */
        .source-box {{
            background-color: {source_bg};
            color: {text};
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 4px solid {source_border};
            box-shadow: {shadow};
        }}
        .source-box strong {{
            color: {accent};
        }}
        .source-box em {{
            color: {text_muted};
        }}
        .source-box small {{
            color: {text_muted};
        }}
        .source-box hr {{
            border-color: {border};
        }}

        /* ── Chat messages ─────────────────── */
        div[data-testid="stChatMessage"] {{
            background-color: {bg_secondary};
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 0.8rem;
            border: 1px solid {border};
        }}

        /* User and assistant message tinting */
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {{
            background-color: {user_bg};
        }}
        div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {{
            background-color: {bot_bg};
        }}

        /* ── Chat input box ────────────────── */
        div[data-testid="stChatInput"] {{
            background-color: {bg_secondary};
            border-radius: 12px;
            border: 1px solid {border};
        }}
        div[data-testid="stChatInput"] textarea {{
            background-color: {bg_secondary} !important;
            color: {text} !important;
        }}

        /* ── Buttons ───────────────────────── */
        .stButton > button {{
            background-color: {accent};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .stButton > button:hover {{
            background-color: {accent_hover};
            transform: translateY(-1px);
            box-shadow: {shadow};
        }}

        /* ── Metrics ───────────────────────── */
        div[data-testid="stMetric"] {{
            background-color: {bg_tertiary};
            padding: 12px;
            border-radius: 8px;
            border: 1px solid {border};
        }}
        div[data-testid="stMetricValue"] {{
            color: {accent} !important;
        }}

        /* ── Expander ──────────────────────── */
        div[data-testid="stExpander"] {{
            background-color: {bg_secondary};
            border: 1px solid {border};
            border-radius: 8px;
        }}

        /* ── Text inputs ───────────────────── */
        .stTextInput input, .stTextArea textarea {{
            background-color: {bg_secondary} !important;
            color: {text} !important;
            border: 1px solid {border} !important;
        }}

        /* ── Success / Error / Info boxes ──── */
        div[data-testid="stAlert"] {{
            border-radius: 8px;
        }}

        /* ── Footer text ───────────────────── */
        .footer-text {{
            text-align: center;
            color: {text_muted};
            padding: 1rem;
            font-size: 0.9rem;
        }}

        /* ── Hide Streamlit branding ───────── */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        # header {{visibility: hidden;}}

        /* ── Scrollbar styling ─────────────── */
        ::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}
        ::-webkit-scrollbar-track {{
            background: {bg_secondary};
        }}
        ::-webkit-scrollbar-thumb {{
            background: {border};
            border-radius: 5px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: {accent};
        }}
    </style>
    """


# Apply theme
st.markdown(get_theme_css(st.session_state.dark_mode), unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Initialize chatbot (cached)
# ─────────────────────────────────────────────
@st.cache_resource
def load_chatbot():
    return RAGChatbot()


# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "sources_history" not in st.session_state:
    st.session_state.sources_history = []


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📚 Document Chatbot</h1>
    <p>Ask questions about your PDF and PPTX files</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    # ── Theme toggle at top ──────────────────
    st.subheader("🎨 Appearance")
    theme_label = "🌙 Dark Mode" if st.session_state.dark_mode else "☀️ Light Mode"
    if st.toggle(theme_label, value=st.session_state.dark_mode, key="theme_toggle"):
        if not st.session_state.dark_mode:
            st.session_state.dark_mode = True
            st.rerun()
    else:
        if st.session_state.dark_mode:
            st.session_state.dark_mode = False
            st.rerun()

    st.divider()

    # ── Settings ─────────────────────────────
    st.header("⚙️ Settings")

    # Check if index exists
    if not os.path.exists("index_store/faiss.index"):
        st.error("❌ No index found!")
        st.info("Run `python main.py` first to build the index.")
        st.stop()
    else:
        st.success("✅ Index loaded")

    st.divider()

    # ── Stats ────────────────────────────────
    try:
        with open("index_store/chunks.json", encoding="utf-8") as f:
            chunks = json.load(f)
        files = set(c["source_file"] for c in chunks)

        # Count unique branches and subjects
        branches_set = set(FILE_LINKS.get(f, {}).get("branch", "") for f in files) - {""}
        subjects_set = set(FILE_LINKS.get(f, {}).get("subject", "") for f in files) - {""}

        col1, col2 = st.columns(2)
        col1.metric("📄 Files", len(files))
        col2.metric("🧩 Chunks", len(chunks))

        col3, col4 = st.columns(2)
        col3.metric("🎓 Branches", len(branches_set))
        col4.metric("📚 Subjects", len(subjects_set))

    except Exception as e:
        st.warning(f"Could not load stats: {e}")
        files = set()

    st.divider()

    # ── Filters ──────────────────────────────
    st.subheader("🔍 Filters")

    # Branch filter
    all_branches = sorted(set(info.get("branch", "") for info in FILE_LINKS.values()) - {""})
    selected_branch = st.selectbox(
        "🎓 Branch",
        ["All"] + all_branches,
        key="branch_filter",
    )

    # Semester filter (depends on branch)
    if selected_branch == "All":
        all_sems = sorted(
            set(info.get("semester", "") for info in FILE_LINKS.values()) - {""}
        )
    else:
        all_sems = sorted(
            set(
                info.get("semester", "")
                for info in FILE_LINKS.values()
                if info.get("branch") == selected_branch
            ) - {""}
        )

    selected_sem = st.selectbox(
        "📅 Semester",
        ["All"] + all_sems,
        key="sem_filter",
    )

    # Helper: check if a file matches branch/sem filters
    def matches_filters(info):
        if selected_branch != "All" and info.get("branch") != selected_branch:
            return False
        if selected_sem != "All" and info.get("semester") != selected_sem:
            return False
        return True

    # Subject filter (depends on branch + sem)
    all_subjects = sorted(
        set(
            info.get("subject", "")
            for info in FILE_LINKS.values()
            if matches_filters(info)
        ) - {""}
    )
    selected_subject = st.selectbox(
        "📚 Subject",
        ["All"] + all_subjects,
        key="subject_filter",
    )

    # Count matching files
    matching_files = [
        name
        for name, info in FILE_LINKS.items()
        if matches_filters(info)
        and (selected_subject == "All" or info.get("subject") == selected_subject)
    ]
    st.caption(f"📊 **{len(matching_files)}** files match current filters")

    # Store filter selections in session state (for use by chatbot)
    st.session_state.filter_branch  = selected_branch
    st.session_state.filter_sem     = selected_sem
    st.session_state.filter_subject = selected_subject
    st.session_state.matching_files = set(matching_files)

    st.divider()

    # ── Indexed Files (grouped) ──────────────
    with st.expander("📁 Indexed Files"):
        # Build hierarchy: branch → semester → subject → [files]
        hierarchy = {}
        for f in sorted(files):
            info    = FILE_LINKS.get(f, {})
            branch  = info.get("branch",   "Unknown")
            sem     = info.get("semester", "?")
            subject = info.get("subject",  "Other")
            url     = info.get("url",      "")

            # Apply filters
            if selected_branch != "All"  and branch  != selected_branch:  continue
            if selected_sem    != "All"  and sem     != selected_sem:     continue
            if selected_subject != "All" and subject != selected_subject: continue

            hierarchy.setdefault(branch, {}).setdefault(sem, {}).setdefault(subject, []).append((f, url))

        if not hierarchy:
            st.info("No files match current filters.")
        else:
            for branch in sorted(hierarchy.keys()):
                st.markdown(f"**🎓 {branch}**")
                for sem in sorted(hierarchy[branch].keys()):
                    st.markdown(f"&nbsp;&nbsp;📅 *Semester {sem}*", unsafe_allow_html=True)
                    for subject in sorted(hierarchy[branch][sem].keys()):
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📚 **{subject}**", unsafe_allow_html=True)
                        for fname, url in hierarchy[branch][sem][subject]:
                            if url:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• [{fname}]({url})", unsafe_allow_html=True)
                            else:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• {fname}", unsafe_allow_html=True)

    st.divider()

    # ── Conversation Controls ────────────────
    st.subheader("💬 Conversation")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sources_history = []
        bot = load_chatbot()
        bot.reset_history()
        st.rerun()

    # Download chat history
    if st.session_state.messages:
        chat_export = json.dumps(st.session_state.messages, indent=2, ensure_ascii=False)
        st.download_button(
            "💾 Download Chat",
            chat_export,
            "chat_history.json",
            "application/json",
            use_container_width=True,
        )

    st.divider()

    # ── About ────────────────────────────────
    st.subheader("ℹ️ About")
    st.markdown("""
    This chatbot uses:
    - **Hybrid Search** (BM25 + Semantic)
    - **RAG** (Retrieval-Augmented Generation)
    - **LLM** for natural answers

    Use the filters above to narrow down searches by branch, semester, or subject.
    """)
    

# ─────────────────────────────────────────────
# Load chatbot
# ─────────────────────────────────────────────
with st.spinner("Loading chatbot..."):
    bot = load_chatbot()


# ─────────────────────────────────────────────
# Render sources helper
# ─────────────────────────────────────────────
def render_sources(sources):
    if not sources:
        return
    with st.expander(f"📚 View {len(sources)} sources"):
        for j, src in enumerate(sources, start=1):
            file_name = src['source_file']
            link_info = FILE_LINKS.get(file_name, {})
            drive_url = link_info.get("url", "")
            subject   = link_info.get("subject", "")
            category  = link_info.get("category", "")
            branch    = link_info.get("branch", "")
            semester  = link_info.get("semester", "")

            # File link
            if drive_url:
                file_link = f'<a href="{drive_url}" target="_blank" style="color:#7c8aff; text-decoration:none; font-weight:600;">📄 {file_name} 🔗</a>'
            else:
                file_link = f"📄 {file_name}"

            # Metadata line
            meta_parts = []
            if branch:   meta_parts.append(f"🎓 {branch}")
            if semester: meta_parts.append(f"📅 Sem {semester}")
            if subject:  meta_parts.append(f"📚 {subject}")
            if category: meta_parts.append(f"🏷️ {category}")
            meta_line = " | ".join(meta_parts)

            st.markdown(f"""
            <div class="source-box">
                <strong>Source {j}</strong> | {file_link}
                <br>📍 {src['location']} | 🎯 Score: {src['score']:.3f} | BM25: {src['bm25_score']:.2f} | Semantic: {src['semantic_score']:.2f}
                {f'<br><small>{meta_line}</small>' if meta_line else ''}
                <hr style="margin: 8px 0;">
                <em>{src['text'][:300]}...</em>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Chat history
# ─────────────────────────────────────────────
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and i // 2 < len(st.session_state.sources_history):
            render_sources(st.session_state.sources_history[i // 2])


# ─────────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────────
if prompt := st.chat_input("Ask a question about your documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🔍 Searching documents and thinking..."):
            answer, sources = bot.chat(prompt)
        st.markdown(answer)
        render_sources(sources)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.sources_history.append(sources)


# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown(
    "<div class='footer-text'>Powered by Hybrid Search + RAG</div>",
    unsafe_allow_html=True
)