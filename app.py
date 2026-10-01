"""
EcoHome Energy Advisor — Streamlit UI
Run: streamlit run ecohome_solution/app.py
"""

import os, sys, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ─── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="EcoHome Energy Advisor",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Beige base ── */
html, body, [data-testid="stApp"] {
    background-color: #F7F0E0 !important;
    font-family: 'Segoe UI', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #EDE3C8 !important;
    border-right: 2px dashed #C9A96E;
}

/* ── Top bar ── */
header[data-testid="stHeader"] {
    background-color: #F7F0E0 !important;
}

/* ── Inputs ── */
textarea, input, .stTextInput input {
    background-color: #FFFDF5 !important;
    border: 2px solid #C9A96E !important;
    border-radius: 12px !important;
}

/* ── Chat bubbles ── */
.user-bubble {
    background: #4A7C59;
    color: #fff;
    padding: 12px 18px;
    border-radius: 20px 20px 4px 20px;
    margin: 8px 0 8px 60px;
    font-size: 0.95rem;
    line-height: 1.5;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.12);
}
.bot-bubble {
    background: #FFFDF5;
    color: #2D2D2D;
    padding: 14px 18px;
    border-radius: 20px 20px 20px 4px;
    margin: 8px 60px 8px 0;
    font-size: 0.95rem;
    line-height: 1.6;
    border: 1.5px solid #C9A96E;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.08);
}
.bubble-label {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
    opacity: 0.7;
}

/* ── Stat cards ── */
.stat-card {
    background: #FFFDF5;
    border: 1.5px solid #C9A96E;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
    box-shadow: 1px 2px 5px rgba(0,0,0,0.07);
}
.stat-value { font-size: 1.5rem; font-weight: 800; color: #4A7C59; }
.stat-label { font-size: 0.78rem; color: #7A6A4A; font-weight: 600; letter-spacing: 0.05em; }

/* ── Section headers ── */
.section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #4A7C59;
    border-bottom: 2px dashed #C9A96E;
    padding-bottom: 6px;
    margin: 16px 0 10px 0;
}

/* ── Quick question pills ── */
.pill-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.pill {
    background: #4A7C59;
    color: #fff;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.8rem;
    cursor: pointer;
    border: none;
    font-weight: 600;
}

/* ── Thinking spinner text ── */
.stSpinner > div { color: #4A7C59 !important; }

/* ── Hide Streamlit branding ── */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─── SVG Doodles ─────────────────────────────────────────────────────────────

HEADER_SVG = """
<svg viewBox="0 0 900 120" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:120px;">
  <!-- Background squiggle -->
  <path d="M0 80 Q 100 40 200 75 Q 300 110 400 70 Q 500 30 600 75 Q 700 110 800 70 Q 860 48 900 65 L900 120 L0 120Z"
        fill="#EDE3C8" opacity="0.6"/>

  <!-- EV Car body doodle -->
  <g transform="translate(30,30)" stroke="#4A7C59" stroke-width="2.5" fill="none" stroke-linecap="round">
    <rect x="10" y="20" width="100" height="32" rx="8" fill="#FFFDF5" stroke="#4A7C59"/>
    <path d="M20 20 Q 35 5 55 5 Q 80 5 95 20" fill="#D4EDD9" stroke="#4A7C59"/>
    <circle cx="27" cy="54" r="9" fill="#4A7C59"/>
    <circle cx="27" cy="54" r="4" fill="#FFFDF5"/>
    <circle cx="93" cy="54" r="9" fill="#4A7C59"/>
    <circle cx="93" cy="54" r="4" fill="#FFFDF5"/>
    <!-- Lightning bolt on car -->
    <path d="M57 12 L52 22 L57 22 L52 33" stroke="#F0A500" stroke-width="2.5" fill="none"/>
  </g>

  <!-- Charging plug doodle -->
  <g transform="translate(170,25)" stroke="#4A7C59" stroke-width="2.2" fill="none" stroke-linecap="round">
    <rect x="0" y="10" width="22" height="32" rx="4" fill="#D4EDD9" stroke="#4A7C59"/>
    <line x1="6" y1="10" x2="6" y2="2"/>
    <line x1="16" y1="10" x2="16" y2="2"/>
    <path d="M22 26 Q 36 26 36 38 L 36 52" stroke="#C9A96E" stroke-width="2.2"/>
    <circle cx="36" cy="56" r="5" fill="#F0A500" stroke="#C9A96E"/>
  </g>

  <!-- Solar panel doodle -->
  <g transform="translate(240,20)" stroke="#4A7C59" stroke-width="2" fill="none">
    <rect x="0" y="0" width="60" height="42" rx="4" fill="#D4EDD9" stroke="#4A7C59"/>
    <line x1="20" y1="0" x2="20" y2="42" stroke="#4A7C59" stroke-width="1.5"/>
    <line x1="40" y1="0" x2="40" y2="42" stroke="#4A7C59" stroke-width="1.5"/>
    <line x1="0" y1="14" x2="60" y2="14" stroke="#4A7C59" stroke-width="1.5"/>
    <line x1="0" y1="28" x2="60" y2="28" stroke="#4A7C59" stroke-width="1.5"/>
    <!-- Sun rays -->
    <circle cx="30" cy="-14" r="7" fill="#F0A500" stroke="#F0A500"/>
    <line x1="30" y1="-24" x2="30" y2="-28"/>
    <line x1="40" y1="-20" x2="43" y2="-23"/>
    <line x1="44" y1="-10" x2="48" y2="-10"/>
    <line x1="16" y1="-20" x2="13" y2="-23"/>
    <line x1="12" y1="-10" x2="8"  y2="-10"/>
  </g>

  <!-- Battery doodle -->
  <g transform="translate(330,28)" stroke="#4A7C59" stroke-width="2.2" fill="none">
    <rect x="0" y="0" width="48" height="26" rx="5" fill="#FFFDF5" stroke="#4A7C59"/>
    <rect x="48" y="8" width="6" height="10" rx="2" fill="#4A7C59"/>
    <rect x="4" y="5" width="16" height="16" rx="3" fill="#4A7C59" opacity="0.8"/>
    <rect x="24" y="5" width="8" height="16"  rx="3" fill="#4A7C59" opacity="0.4"/>
  </g>

  <!-- Leaf doodle -->
  <g transform="translate(412,22)" stroke="#4A7C59" stroke-width="2" fill="none">
    <path d="M 20 45 Q -5 30 5 5 Q 20 -5 40 10 Q 50 30 20 45 Z" fill="#D4EDD9" stroke="#4A7C59"/>
    <path d="M 20 45 Q 18 30 22 10" stroke="#4A7C59" stroke-width="1.5"/>
    <path d="M 22 25 Q 30 20 38 15" stroke="#4A7C59" stroke-width="1.2"/>
    <path d="M 20 35 Q 12 30 8 22"  stroke="#4A7C59" stroke-width="1.2"/>
  </g>

  <!-- Wind turbine doodle -->
  <g transform="translate(490,10)" stroke="#4A7C59" stroke-width="2" fill="none">
    <line x1="20" y1="70" x2="20" y2="20"/>
    <ellipse cx="20" cy="20" rx="4" ry="4" fill="#4A7C59"/>
    <path d="M20 16 Q 5 10 8 0 Q 14 8 20 16" fill="#D4EDD9" stroke="#4A7C59"/>
    <path d="M24 22 Q 36 10 44 18 Q 34 20 24 22" fill="#D4EDD9" stroke="#4A7C59"/>
    <path d="M16 24 Q 4 36 -4 30 Q 6 24 16 24" fill="#D4EDD9" stroke="#4A7C59"/>
  </g>

  <!-- Home with solar doodle -->
  <g transform="translate(570,20)" stroke="#4A7C59" stroke-width="2" fill="none">
    <polygon points="30,0 60,25 0,25" fill="#D4EDD9" stroke="#4A7C59"/>
    <rect x="10" y="25" width="40" height="35" fill="#FFFDF5" stroke="#4A7C59"/>
    <rect x="22" y="35" width="12" height="16" rx="2" fill="#D4EDD9" stroke="#4A7C59"/>
    <!-- mini solar on roof -->
    <rect x="12" y="10" width="16" height="10" rx="2" fill="#4A7C59" opacity="0.5" stroke="#4A7C59"/>
  </g>

  <!-- Lightning bolts scattered -->
  <g fill="#F0A500" opacity="0.8">
    <path d="M700 15 L695 28 L701 28 L696 42" stroke="#F0A500" stroke-width="2" fill="none"/>
    <path d="M750 8  L745 20 L751 20 L746 33" stroke="#F0A500" stroke-width="2" fill="none"/>
    <path d="M800 18 L795 30 L801 30 L796 44" stroke="#F0A500" stroke-width="2" fill="none"/>
    <path d="M850 10 L845 22 L851 22 L846 35" stroke="#F0A500" stroke-width="2" fill="none"/>
  </g>

  <!-- Wavy doodle underline -->
  <path d="M0 95 Q 50 90 100 95 Q 150 100 200 95 Q 250 90 300 95 Q 350 100 400 95 Q 450 90 500 95 Q 550 100 600 95 Q 650 90 700 95 Q 750 100 800 95 Q 850 90 900 95"
        stroke="#C9A96E" stroke-width="2" fill="none" stroke-dasharray="6,4"/>
</svg>
"""

SIDEBAR_EV_SVG = """
<svg viewBox="0 0 180 90" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:180px;">
  <g transform="translate(10,15)" stroke="#4A7C59" stroke-width="2" fill="none" stroke-linecap="round">
    <rect x="5" y="22" width="120" height="36" rx="10" fill="#D4EDD9" stroke="#4A7C59"/>
    <path d="M15 22 Q 32 5 58 5 Q 90 5 105 22" fill="#B8DFC0" stroke="#4A7C59"/>
    <circle cx="28" cy="60" r="11" fill="#4A7C59"/>
    <circle cx="28" cy="60" r="5"  fill="#FFFDF5"/>
    <circle cx="102" cy="60" r="11" fill="#4A7C59"/>
    <circle cx="102" cy="60" r="5"  fill="#FFFDF5"/>
    <!-- windows -->
    <rect x="30" y="12" width="25" height="16" rx="3" fill="#FFFDF5" stroke="#4A7C59"/>
    <rect x="62" y="12" width="25" height="16" rx="3" fill="#FFFDF5" stroke="#4A7C59"/>
    <!-- lightning -->
    <path d="M140 18 L134 34 L141 34 L135 52" stroke="#F0A500" stroke-width="3" fill="none"/>
  </g>
</svg>
"""


# ─── DB stats helper ──────────────────────────────────────────────────────────

@st.cache_data(ttl=10)
def get_db_stats():
    try:
        from sqlalchemy.orm import Session
        from models.energy import EnergyUsage, SolarGeneration, get_engine

        db_path = os.path.join(os.path.dirname(__file__), "data", "energy_data.db")
        if not os.path.exists(db_path):
            return None
        engine  = get_engine(db_path)
        since   = datetime.now() - timedelta(days=7)

        with Session(engine) as s:
            total_kwh  = s.query(EnergyUsage).filter(EnergyUsage.timestamp >= since).all()
            solar_rows = s.query(SolarGeneration).filter(SolarGeneration.timestamp >= since).all()
            total_cost = sum(r.cost_usd or 0 for r in total_kwh)
            total_use  = sum(r.consumption_kwh for r in total_kwh)
            total_sol  = sum(r.generation_kwh for r in solar_rows)
            co2_saved  = round(total_sol * 0.233, 1)
        return {
            "total_kwh":  round(total_use, 1),
            "total_cost": round(total_cost, 2),
            "solar_kwh":  round(total_sol, 1),
            "co2_saved":  co2_saved,
        }
    except Exception:
        return None


@st.cache_data(ttl=10)
def get_daily_solar():
    try:
        import pandas as pd
        from models.energy import get_engine

        db_path = os.path.join(os.path.dirname(__file__), "data", "energy_data.db")
        if not os.path.exists(db_path):
            return None
        engine = get_engine(db_path)
        df = pd.read_sql(
            "SELECT DATE(timestamp) as day, SUM(generation_kwh) as kwh "
            "FROM solar_generation GROUP BY DATE(timestamp) ORDER BY day DESC LIMIT 10",
            engine,
        )
        return df[::-1].reset_index(drop=True)
    except Exception:
        return None


# ─── Agent singleton ──────────────────────────────────────────────────────────

@st.cache_resource
def get_agent():
    from agent import build_agent
    return build_agent(model_name="gpt-4o", temperature=0.0)


# ─── LAYOUT ──────────────────────────────────────────────────────────────────

# Header doodle banner
st.markdown(HEADER_SVG, unsafe_allow_html=True)

st.markdown("""
<div style='text-align:center; margin:-10px 0 20px 0;'>
  <span style='font-size:2.2rem; font-weight:900; color:#4A7C59; letter-spacing:1px;'>
    ⚡ EcoHome Energy Advisor
  </span><br>
  <span style='font-size:0.95rem; color:#7A6A4A; font-weight:500;'>
    AI-powered smart home energy optimization &nbsp;·&nbsp; Solar · EV · HVAC · Savings
  </span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(SIDEBAR_EV_SVG, unsafe_allow_html=True)
    st.markdown("<div class='section-header'>📊 Last 7-Day Stats</div>", unsafe_allow_html=True)

    stats = get_db_stats()
    if stats:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class='stat-card'>
              <div class='stat-label'>⚡ CONSUMED</div>
              <div class='stat-value'>{stats['total_kwh']}</div>
              <div class='stat-label'>kWh</div>
            </div>""", unsafe_allow_html=True)
            st.markdown(f"""
            <div class='stat-card'>
              <div class='stat-label'>💸 COST</div>
              <div class='stat-value'>${stats['total_cost']}</div>
              <div class='stat-label'>USD</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class='stat-card'>
              <div class='stat-label'>☀️ SOLAR</div>
              <div class='stat-value'>{stats['solar_kwh']}</div>
              <div class='stat-label'>kWh</div>
            </div>""", unsafe_allow_html=True)
            st.markdown(f"""
            <div class='stat-card'>
              <div class='stat-label'>🌿 CO₂ SAVED</div>
              <div class='stat-value'>{stats['co2_saved']}</div>
              <div class='stat-label'>kg</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Run `seed_data.py` first to populate the database.")

    # Solar bar chart
    st.markdown("<div class='section-header'>☀️ Daily Solar Generation (kWh)</div>", unsafe_allow_html=True)
    solar_df = get_daily_solar()
    if solar_df is not None and len(solar_df):
        import pandas as pd
        solar_df["day"] = pd.to_datetime(solar_df["day"]).dt.strftime("%m/%d")
        st.bar_chart(solar_df.set_index("day")["kwh"], color="#4A7C59", height=160)
    else:
        st.info("No solar data yet.")

    st.markdown("<div class='section-header'>⚡ TOU Pricing Guide</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size:0.82rem; line-height:1.8; color:#2D2D2D;'>
    🔴 <b>Peak</b>: 7–9 AM, 5–9 PM &nbsp; ~$0.33/kWh<br>
    🟡 <b>Off-peak</b>: 10 AM–4 PM &nbsp; ~$0.16/kWh<br>
    🟢 <b>Super off-peak</b>: 9 PM–7 AM &nbsp; ~$0.09/kWh
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    col_r, col_c = st.columns(2)
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_c:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# ── Main chat area ────────────────────────────────────────────────────────────

# Quick-question pills (rendered as buttons)
QUICK_Qs = [
    "⚡ When to charge my EV tomorrow?",
    "🌡️ Best thermostat setting during peak hours?",
    "💧 Optimal pool pump schedule this week?",
    "💸 How much can I save with off-peak dishwasher?",
    "☀️ 3 energy tips based on my usage history",
    "🔋 Should I run dryer tonight or morning?",
]

st.markdown("<div class='section-header'>💬 Ask the Energy Advisor</div>", unsafe_allow_html=True)

cols = st.columns(3)
for i, q in enumerate(QUICK_Qs):
    if cols[i % 3].button(q, key=f"pill_{i}", use_container_width=True):
        # Strip emoji prefix for the actual question
        clean_q = q.split(" ", 1)[1] if q[0] in "⚡🌡️💧💸☀️🔋" else q
        st.session_state.setdefault("messages", [])
        st.session_state.messages.append({"role": "user", "content": clean_q})
        st.session_state["pending_response"] = True
        st.rerun()

st.markdown("---")

# ── Message history ───────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown("""
        <div style='text-align:center; color:#9A8A6A; font-size:0.95rem; margin-top:30px;'>
          👆 Click a quick question above or type your own below.<br>
          Ask about EV charging, solar, HVAC, savings estimates, and more!
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class='bubble-label' style='text-align:right; color:#4A7C59;'>YOU</div>
            <div class='user-bubble'>{msg['content']}</div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='bubble-label' style='color:#7A6A4A;'>⚡ ECOHOME ADVISOR</div>
            <div class='bot-bubble'>{msg['content']}</div>
            """, unsafe_allow_html=True)

# ── Handle pending response from quick-pill click ────────────────────────────

if st.session_state.get("pending_response"):
    st.session_state["pending_response"] = False
    user_q = st.session_state.messages[-1]["content"]
    with st.spinner("🔍 Analysing your energy data..."):
        try:
            agent = get_agent()
            from langchain_core.messages import HumanMessage, SystemMessage
            from agent import SYSTEM_PROMPT
            result = agent.invoke({
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_q),
                ]
            })
            answer = result["messages"][-1].content
        except Exception as e:
            answer = f"⚠️ Error: {e}\n\nMake sure your OPENAI_API_KEY is set in `.env` and the database is seeded."
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()

# ── Chat input ────────────────────────────────────────────────────────────────

user_input = st.chat_input("Ask anything about your home energy — EV, solar, HVAC, savings...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.spinner("🔍 Analysing your energy data..."):
        try:
            agent = get_agent()
            from langchain_core.messages import HumanMessage, SystemMessage
            from agent import SYSTEM_PROMPT
            result = agent.invoke({
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_input),
                ]
            })
            answer = result["messages"][-1].content
        except Exception as e:
            answer = f"⚠️ Error: {e}\n\nMake sure your OPENAI_API_KEY is set in `.env` and the database is seeded."
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()

# ── Footer doodle ─────────────────────────────────────────────────────────────

st.markdown("""
<div style='text-align:center; color:#9A8A6A; font-size:0.78rem; margin-top:40px; padding-top:10px;
            border-top: 1px dashed #C9A96E;'>
  ⚡ Powered by GPT-4o + LangGraph + ChromaDB &nbsp;·&nbsp; 🌿 EcoHome Energy Advisor
</div>
""", unsafe_allow_html=True)
