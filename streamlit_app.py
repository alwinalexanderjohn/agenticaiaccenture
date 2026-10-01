"""Streamlit front-end for the Document Assistant."""

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────
st.set_page_config(
    page_title="🏥 Document Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from src.assistant import DocumentAssistant
from src.retrieval import retriever


# ═══════════════════════════════════════════════════════════════════════
# CSS — light green theme
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    /* ── Global background ── */
    .stApp { background-color: #f0fdf4; }
    section[data-testid="stSidebar"] { background-color: #d1fae5; }

    /* ── Tab bar ── */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #d1fae5;
        border-radius: 12px;
        padding: 5px 6px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9px;
        font-weight: 600;
        font-size: 15px;
        color: #065f46;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #10b981 !important;
        color: white !important;
    }

    /* ── Header ── */
    .header-wrap {
        display: flex;
        align-items: center;
        gap: 18px;
        padding: 10px 0 4px 0;
    }
    .header-title {
        font-size: 2rem;
        font-weight: 800;
        color: #064e3b;
        margin: 0;
        line-height: 1.1;
    }
    .header-sub {
        color: #6b7280;
        font-size: 0.95rem;
        margin-top: 4px;
    }

    /* ── Document cards ── */
    .doc-card {
        background: white;
        border-left: 4px solid #10b981;
        padding: 10px 16px;
        border-radius: 8px;
        margin: 6px 0;
        font-size: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .doc-badge-builtin  { background:#d1fae5; color:#065f46; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:600; }
    .doc-badge-uploaded { background:#dbeafe; color:#1e40af; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:600; }

    /* ── Chat bubbles ── */
    .stChatMessage { border-radius: 12px; }

    /* ── Buttons ── */
    .stButton > button {
        background-color: #10b981;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton > button:hover { background-color: #059669; color: white; }

    /* ── Divider ── */
    hr { border-color: #d1fae5; }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {
        background: white;
        border: 2px dashed #10b981;
        border-radius: 12px;
        padding: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# Hospital doodle SVG
# ═══════════════════════════════════════════════════════════════════════
HOSPITAL_SVG = """
<svg width="130" height="130" viewBox="0 0 140 140" xmlns="http://www.w3.org/2000/svg">
  <!-- Soft background circle -->
  <circle cx="70" cy="72" r="64" fill="#bbf7d0" opacity="0.55"/>

  <!-- Main building -->
  <rect x="18" y="60" width="104" height="72" fill="#ecfdf5" stroke="#10b981" stroke-width="2.5" rx="4"/>

  <!-- Roof band -->
  <rect x="10" y="49" width="120" height="15" fill="#10b981" rx="3"/>

  <!-- Pillars above roof -->
  <rect x="26" y="38" width="13" height="14" fill="#059669" rx="2"/>
  <rect x="101" y="38" width="13" height="14" fill="#059669" rx="2"/>

  <!-- Red-cross circle -->
  <circle cx="70" cy="25" r="18" fill="white" stroke="#fca5a5" stroke-width="2"/>
  <rect x="66" y="13" width="8" height="24" fill="#ef4444" rx="2"/>
  <rect x="58" y="21" width="24" height="8" fill="#ef4444" rx="2"/>

  <!-- Windows — row 1 -->
  <rect x="26" y="72" width="24" height="19" fill="#a7f3d0" stroke="#059669" stroke-width="1.5" rx="2"/>
  <line x1="38" y1="72" x2="38" y2="91" stroke="#059669" stroke-width="1"/>
  <line x1="26" y1="81" x2="50" y2="81" stroke="#059669" stroke-width="1"/>

  <rect x="58" y="72" width="24" height="19" fill="#a7f3d0" stroke="#059669" stroke-width="1.5" rx="2"/>
  <line x1="70" y1="72" x2="70" y2="91" stroke="#059669" stroke-width="1"/>
  <line x1="58" y1="81" x2="82" y2="81" stroke="#059669" stroke-width="1"/>

  <rect x="90" y="72" width="24" height="19" fill="#a7f3d0" stroke="#059669" stroke-width="1.5" rx="2"/>
  <line x1="102" y1="72" x2="102" y2="91" stroke="#059669" stroke-width="1"/>
  <line x1="90" y1="81" x2="114" y2="81" stroke="#059669" stroke-width="1"/>

  <!-- Door -->
  <rect x="54" y="101" width="32" height="31" fill="#065f46" rx="3"/>
  <rect x="62" y="107" width="7" height="8" fill="#6ee7b7" rx="1"/>
  <rect x="71" y="107" width="7" height="8" fill="#6ee7b7" rx="1"/>
  <circle cx="83" cy="118" r="2" fill="#a7f3d0"/>

  <!-- Ground -->
  <rect x="0" y="129" width="140" height="11" fill="#a7f3d0" rx="3"/>

  <!-- Trees -->
  <ellipse cx="10" cy="124" rx="10" ry="9" fill="#34d399"/>
  <ellipse cx="130" cy="124" rx="10" ry="9" fill="#34d399"/>
  <rect x="7"   cy="126" width="6" height="6" fill="#065f46" rx="1"/>
  <rect x="127" cy="126" width="6" height="6" fill="#065f46" rx="1"/>

  <!-- Mini ambulance -->
  <rect x="92" y="119" width="32" height="13" fill="white" stroke="#ef4444" stroke-width="1.5" rx="2"/>
  <text x="108" y="129" text-anchor="middle" font-size="7" fill="#ef4444" font-weight="bold">+</text>
  <circle cx="98"  cy="132" r="3.5" fill="#4b5563"/>
  <circle cx="118" cy="132" r="3.5" fill="#4b5563"/>
  <rect x="116" y="121" width="8" height="7" fill="#bfdbfe" rx="1"/>
</svg>
"""


# ═══════════════════════════════════════════════════════════════════════
# Session-state initialisation
# ═══════════════════════════════════════════════════════════════════════
def _init():
    if "sum_assistant" not in st.session_state:
        a = DocumentAssistant(model_name="gpt-4o")
        a.start_session(user_id="sum_user")
        st.session_state.sum_assistant = a

    if "calc_assistant" not in st.session_state:
        a = DocumentAssistant(model_name="gpt-4o")
        a.start_session(user_id="calc_user")
        st.session_state.calc_assistant = a

    for key in ("sum_chat", "calc_chat", "uploaded_ids"):
        if key not in st.session_state:
            st.session_state[key] = []


_init()


# ═══════════════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════════════
c_logo, c_title = st.columns([1, 6])
with c_logo:
    st.markdown(HOSPITAL_SVG, unsafe_allow_html=True)
with c_title:
    st.markdown(
        '<p class="header-title">🏥 Document Assistant</p>'
        '<p class="header-sub">AI-powered analysis for medical &amp; financial documents &nbsp;·&nbsp; '
        'LangGraph &nbsp;+&nbsp; OpenAI GPT-4o</p>',
        unsafe_allow_html=True,
    )

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════
# Helper — show all loaded documents
# ═══════════════════════════════════════════════════════════════════════
def _render_doc_list():
    docs = retriever.list_documents()
    for d in docs:
        if d["type"] == "uploaded":
            badge = '<span class="doc-badge-uploaded">🆕 Uploaded</span>'
        else:
            badge = f'<span class="doc-badge-builtin">📄 {d["type"].title()}</span>'
        st.markdown(
            f'<div class="doc-card">'
            f'<strong>{d["id"]}</strong> &nbsp; {badge}<br>'
            f'<span style="color:#6b7280;font-size:13px;">{d["title"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════
# Tabs
# ═══════════════════════════════════════════════════════════════════════
tab_upload, tab_sum, tab_calc = st.tabs([
    "📁  Upload Documents",
    "📄  Summarization",
    "🧮  Calculator",
])


# ────────────────────────────────────────────────────────────────────────
# TAB 1 — Upload Documents
# ────────────────────────────────────────────────────────────────────────
with tab_upload:
    st.subheader("Upload Your Documents")
    st.caption("Supported formats: **.txt · .md · .csv** — files become available in all tabs instantly.")

    uploaded_files = st.file_uploader(
        "Drop files here or click Browse",
        type=["txt", "md", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        for uf in uploaded_files:
            ext = os.path.splitext(uf.name)[1] or ".txt"
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(uf.read())
                tmp_path = tmp.name

            result = retriever.load_document(tmp_path)
            os.unlink(tmp_path)

            if result.startswith("Error"):
                st.error(result)
            elif result not in st.session_state.uploaded_ids:
                st.session_state.uploaded_ids.append(result)
                st.success(f"✅ **{uf.name}** loaded successfully → document ID: `{result}`")
            else:
                st.info(f"ℹ️ **{uf.name}** is already loaded as `{result}`.")

    # Tip
    if st.session_state.uploaded_ids:
        last = st.session_state.uploaded_ids[-1]
        st.info(
            f"💡 **Tip:** Switch to the **Summarization** tab and type:  \n"
            f"*\"Summarize {last}\"*"
        )

    st.markdown("### 📚 Available Documents")
    _render_doc_list()


# ────────────────────────────────────────────────────────────────────────
# TAB 2 — Summarization
# ────────────────────────────────────────────────────────────────────────
with tab_sum:
    st.subheader("📄 Document Summarization")
    st.caption("Ask for a summary or key points from any loaded document.")

    # Document ID chips
    doc_ids = [d["id"] for d in retriever.list_documents()]
    st.markdown(
        "**Loaded documents:** " + "&nbsp; ".join(f"`{d}`" for d in doc_ids),
        unsafe_allow_html=True,
    )

    st.markdown("")  # spacer

    # Chat history display
    for msg in st.session_state.sum_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if prompt := st.chat_input(
        "e.g. Summarize the healthcare statistics report", key="sum_input"
    ):
        st.session_state.sum_chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Reading documents and summarizing …"):
                try:
                    # Prepend a light hint so intent classifier routes to summarization_agent
                    hint = prompt if prompt.lower().startswith(("summar", "give", "provide", "list", "extract")) \
                        else f"Please summarize: {prompt}"
                    response = st.session_state.sum_assistant.process_message(hint)
                    st.markdown(response)
                    st.session_state.sum_chat.append({"role": "assistant", "content": response})
                except Exception as exc:
                    st.error(f"Error: {exc}")

    col_clr, _ = st.columns([1, 5])
    with col_clr:
        if st.button("🗑️ Clear chat", key="clear_sum"):
            st.session_state.sum_chat = []
            st.rerun()


# ────────────────────────────────────────────────────────────────────────
# TAB 3 — Calculator
# ────────────────────────────────────────────────────────────────────────
with tab_calc:
    st.subheader("🧮 Document Calculator")
    st.caption(
        "Ask me to compute figures from loaded documents — the agent retrieves data "
        "then uses the calculator tool for every arithmetic step."
    )

    with st.expander("💡 Example questions"):
        st.markdown("""
- What is the total net profit across Q1 and Q2 2024?
- What is the revenue difference between Q1 and Q2?
- What is the operating margin (%) for Q2 2024?
- What is the cost per patient bed in the healthcare report?
- What percentage of the annual budget are operating costs?
        """)

    st.markdown("")  # spacer

    # Chat history display
    for msg in st.session_state.calc_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if prompt := st.chat_input(
        "e.g. Total revenue for Q1 and Q2 combined?", key="calc_input"
    ):
        st.session_state.calc_chat.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving document data and calculating …"):
                try:
                    # Prepend hint so intent classifier routes to calculation_agent
                    hint = prompt if prompt.lower().startswith("calculat") \
                        else f"Calculate: {prompt}"
                    response = st.session_state.calc_assistant.process_message(hint)
                    st.markdown(response)
                    st.session_state.calc_chat.append({"role": "assistant", "content": response})
                except Exception as exc:
                    st.error(f"Error: {exc}")

    col_clr, _ = st.columns([1, 5])
    with col_clr:
        if st.button("🗑️ Clear chat", key="clear_calc"):
            st.session_state.calc_chat = []
            st.rerun()
