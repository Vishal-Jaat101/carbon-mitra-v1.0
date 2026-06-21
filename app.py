"""
app.py — CarbonMitra Streamlit Dashboard
========================================
A comprehensive single-page interactive dashboard for Challenge 3:
Carbon Footprint Awareness Platform.

Incorporates:
- Baseline Calculator (Sliders in Sidebar)
- Visual Analytics (st.bar_chart)
- Gamified Daily Challenges (Checklist that dynamically updates score)
- Multimodal Bill/Receipt Scanner (Image uploader + Gemini 2.5 Flash)
- ADK AI Eco-Coach Chatbot (Chat panel + Guardrails)
"""

from __future__ import annotations

import os
import io
import datetime
import pandas as pd
import streamlit as st
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check API Key before importing other components
api_key = os.environ.get("GEMINI_API_KEY")

import mcp_tools as mcp
from agent_graph import get_graph

# ---------------------------------------------------------------------------
# Page Styling & Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CarbonMitra — Track & Mitigate Your Carbon Footprint",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Vanilla CSS styling for premium look
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    :root {
        --bg-primary: #0a0f1e;
        --bg-card: #111827;
        --bg-card-hover: #1a2332;
        --accent-green: #22c55e;
        --accent-teal: #14b8a6;
        --accent-amber: #f59e0b;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --border: #1e293b;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
        color: var(--text-primary);
    }

    /* Hero Banner */
    .hero-container {
        background: linear-gradient(135deg, #064e3b 0%, #0a1f10 50%, #0c2e1b 100%);
        border: 1px solid rgba(34, 197, 94, 0.2);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }

    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #22c55e, #10b981, #06b6d4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }

    .hero-sub {
        font-size: 1.1rem;
        color: #a7f3d0;
        margin-top: 0.5rem;
    }

    /* Cards */
    .metric-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }

    .metric-card:hover {
        transform: translateY(-3px);
        border-color: rgba(34, 197, 94, 0.4);
        background: #162032;
    }

    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 0.2rem 0;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Score badges */
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }

    /* Sidebar Styles */
    .sidebar-section {
        background: #0f172a;
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #1e293b;
        margin-bottom: 1rem;
    }

    /* Section Headers */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        border-left: 4px solid #22c55e;
        padding-left: 10px;
        margin: 1.5rem 0 1rem;
        color: #e2e8f0;
    }

    /* File Uploader styling */
    [data-testid="stFileUploadDropzone"] {
        background: #091a10 !important;
        border: 2px dashed #22c55e !important;
        border-radius: 12px !important;
    }

    /* Chat Styling */
    .chat-bubble-user {
        background: linear-gradient(135deg, #1e3a5f, #1e293b);
        border: 1px solid rgba(59, 130, 246, 0.4);
        border-radius: 16px 16px 4px 16px;
        padding: 12px 16px;
        margin: 8px 0;
        max-width: 80%;
        float: right;
        clear: both;
        color: #e2e8f0;
    }

    .chat-bubble-coach {
        background: linear-gradient(135deg, #092e20, #111827);
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 16px 16px 16px 4px;
        padding: 12px 16px;
        margin: 8px 0;
        max-width: 80%;
        float: left;
        clear: both;
        color: #f0fdf4;
    }

    .chat-clear {
        clear: both;
    }

    /* Progress bar override */
    .stProgress > div > div > div > div {
        background-color: #22c55e !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------------
# Session State Init
# ---------------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "scan_result" not in st.session_state:
    st.session_state.scan_result = None
if "last_chat_input" not in st.session_state:
    st.session_state.last_chat_input = ""

# ---------------------------------------------------------------------------
# Sidebar: Baseline Calculator (UNDERSTAND)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div style='text-align: center; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    st.markdown("## 🌿 CarbonMitra")
    st.markdown("<span style='color: #94a3b8; font-size: 0.95rem;'>India's Carbon Awareness Platform</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<h4 style='color: #10b981;'>📊 Baseline Footprint</h4>", unsafe_allow_html=True)
    st.markdown("Adjust the sliders below to calculate your instant baseline score based on standard Indian emissions coefficients.")

    # Slider 1: Monthly Electricity Units
    elec_kwh = st.slider(
        "Monthly Electricity (kWh)",
        min_value=0,
        max_value=1000,
        value=250,
        step=10,
        help="Average Indian household electricity usage ranges from 90 to 300 units per month."
    )

    # Slider 2: Weekly Driving Distance
    driving_km = st.slider(
        "Weekly Driving (KM)",
        min_value=0,
        max_value=500,
        value=80,
        step=5,
        help="Total driving distance using a personal petrol vehicle."
    )

    # Selector 3: Diet Type
    diet_type = st.selectbox(
        "Diet Type",
        options=["Vegan", "Vegetarian", "Non-Vegetarian"],
        index=1,
        help="Different food habits carry varying greenhouse gas intensities."
    )

    # Instant calculation from mcp_tools
    baseline = mcp.calculate_baseline(elec_kwh, driving_km, diet_type)
    
    st.markdown("---")
    st.markdown("<h5 style='color: #94a3b8;'>Your Daily Baseline Emissions</h5>", unsafe_allow_html=True)
    st.markdown(f"**{baseline['total_daily']:.2f} kg CO2e / day**")
    
    st.markdown("<h5 style='color: #94a3b8;'>Your Monthly Baseline Emissions</h5>", unsafe_allow_html=True)
    st.markdown(f"**{baseline['total_monthly']:.2f} kg CO2e / month**")

# ---------------------------------------------------------------------------
# Main Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-container">
        <h1 class="hero-title">🌿 CarbonMitra</h1>
        <p class="hero-sub">Empowering individuals in India to Understand, Track, and Reduce their Carbon Footprint</p>
    </div>
    """,
    unsafe_allow_html=True
)

if not api_key:
    st.error(
        "⚠️ **Missing GEMINI_API_KEY**: The API Key was not detected in the environment. "
        "Please create a `.env` file in the project directory and assign your key: "
        "`GEMINI_API_KEY=your_key_here`. Restart the application to load it."
    )
    st.stop()

# Load agent graph singleton
try:
    graph = get_graph()
except Exception as e:
    st.error(f"Failed to initialize the Gemini ADK Workflow Agent: {str(e)}")
    st.stop()

# ---------------------------------------------------------------------------
# Tabs Configuration
# ---------------------------------------------------------------------------
tab_dashboard, tab_scanner, tab_coach = st.tabs([
    "🏠 Dashboard & Challenges",
    "📷 Multimodal Scanner",
    "💬 AI Eco-Coach Chat"
])

# ===========================================================================
# TAB 1: DASHBOARD & DALY CHALLENGES
# ===========================================================================
with tab_dashboard:
    # 1. Gamified Daily Challenges (REDUCE)
    st.markdown("<div class='section-header'>🏆 Gamified Daily Challenges</div>", unsafe_allow_html=True)
    st.markdown("Complete these daily eco-friendly habits to instantly see your carbon score decrease!")

    col_ch1, col_ch2, col_ch3 = st.columns(3)
    
    challenges_checked = []
    
    with col_ch1:
        ch1 = st.checkbox(
            f"💡 Switch off idle appliances (Saves {mcp.DAILY_CHALLENGES[0]['savings_kg']} kg CO2e)",
            value=False,
            key="ch_appliances"
        )
        if ch1:
            challenges_checked.append("idle_appliances")
            
    with col_ch2:
        ch2 = st.checkbox(
            f"🚌 Use public transit / walk (Saves {mcp.DAILY_CHALLENGES[1]['savings_kg']} kg CO2e)",
            value=False,
            key="ch_transit"
        )
        if ch2:
            challenges_checked.append("public_transit")
            
    with col_ch3:
        ch3 = st.checkbox(
            f"🍱 Had a plant-based meal (Saves {mcp.DAILY_CHALLENGES[2]['savings_kg']} kg CO2e)",
            value=False,
            key="ch_diet"
        )
        if ch3:
            challenges_checked.append("plant_based")

    # Calculate Challenge Savings
    total_savings = 0.0
    for ch_id in challenges_checked:
        for ch in mcp.DAILY_CHALLENGES:
            if ch["id"] == ch_id:
                total_savings += ch["savings_kg"]

    # Compute final daily footprint after challenge deductions
    adjusted_daily_total = max(0.0, baseline["total_daily"] - total_savings)
    score_data = mcp.score_carbon_footprint(adjusted_daily_total)

    # 2. Main Analytics Breakdown Cards
    st.markdown("<div class='section-header'>📊 Your Live Carbon Snapshot</div>", unsafe_allow_html=True)
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Daily Net Footprint</div>
                <div class="metric-value">{adjusted_daily_total:.2f} kg</div>
                <div style="font-size: 0.9rem; color: #94a3b8;">CO2e emissions today</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m_col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Daily Savings</div>
                <div class="metric-value" style="color: #22c55e;">-{total_savings:.1f} kg</div>
                <div style="font-size: 0.9rem; color: #94a3b8;">from challenges</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m_col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Green Score</div>
                <div class="metric-value" style="color: {score_data['color']};">{score_data['value']}</div>
                <span class="score-badge" style="background-color: {score_data['color']}22; color: {score_data['color']};">{score_data['label']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m_col4:
        # Comparison with Indian urban average (5.1 kg)
        india_avg = mcp.INDIA_LIFESTYLE_AVERAGES["urban_india_daily_kg_co2"]
        diff = adjusted_daily_total - india_avg
        pct = (diff / india_avg) * 100
        
        if diff < 0:
            diff_text = f"{abs(pct):.1f}% Below Average"
            diff_color = "#22c55e"
        else:
            diff_text = f"{pct:.1f}% Above Average"
            diff_color = "#ef4444"

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">vs Indian Urban Avg</div>
                <div class="metric-value" style="color: {diff_color};">{diff_text}</div>
                <div style="font-size: 0.9rem; color: #94a3b8;">Average: {india_avg} kg/day</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    if total_savings > 0.0:
        st.balloons()
        st.success(f"🎉 Awesome! You saved **{total_savings:.1f} kg of CO2e** today by completing daily challenges.")

    # 3. Streamlit Native Bar Chart (TRACK)
    st.markdown("---")
    c_col1, c_col2 = st.columns([2, 1])

    with c_col1:
        st.markdown("<h4 style='color: #10b981;'>📈 Baseline Emission Breakdown (Category-wise)</h4>", unsafe_allow_html=True)
        # Category breakdown
        chart_info = mcp.format_chart_data(baseline, total_savings)
        
        # Create pandas DataFrame for native bar_chart
        df_chart = pd.DataFrame({
            "Category": chart_info["categories"],
            "Daily Emissions (kg CO2e)": chart_info["emissions"]
        })
        
        # Native Streamlit st.bar_chart
        st.bar_chart(
            data=df_chart,
            x="Category",
            y="Daily Emissions (kg CO2e)",
            color="#22c55e"
        )

    with c_col2:
        st.markdown("<h4 style='color: #10b981;'>💡 Quick Eco-Actions</h4>", unsafe_allow_html=True)
        st.markdown(
            """
            * **Switch to LED bulbs**: Reduces energy emissions by 75% compared to traditional bulbs.
            * **Reduce single-use plastic**: Carrying a cloth bag avoids plastic bag emissions.
            * **Eat local**: Reduces logistics emissions. Buy fresh foods from local *mandis*.
            * **Optimize AC usage**: Setting ACs to 24°C instead of 18°C saves ~30% in power bills.
            """
        )
        
        # Sequestration equivalency
        equivalency = mcp.calculate_equivalents(adjusted_daily_total)
        st.markdown(
            f"""
            <div style="background-color: #111827; border: 1px dashed #22c55e; border-radius: 12px; padding: 1rem; margin-top: 1rem;">
                <h5 style="margin-top: 0; color: #22c55e;">🌳 Environmental Impact</h5>
                <p style="font-size: 0.95rem; margin-bottom: 0;">{equivalency}</p>
            </div>
            """,
            unsafe_allow_html=True
        )


# ===========================================================================
# TAB 2: MULTIMODAL BILL / RECEIPT SCANNER
# ===========================================================================
with tab_scanner:
    st.markdown("<div class='section-header'>📷 Multimodal Utility Bill & Receipt Auditor</div>", unsafe_allow_html=True)
    st.markdown(
        "Upload an image of your electricity bill, shopping receipt, or item label to "
        "automatically audit carbon footprint and usage data using Gemini 2.5 Flash Vision."
    )

    col_up, col_res = st.columns([1, 1])

    with col_up:
        uploaded_image = st.file_uploader(
            "Choose a receipt or bill image (JPG, PNG, WEBP)",
            type=["jpg", "jpeg", "png", "webp"],
            key="scanner_file"
        )
        
        scan_prompt = st.text_area(
            "Extra context (optional)",
            placeholder="e.g. 'This is my monthly power bill from BESCOM' or 'grocery store receipt'",
            key="scanner_prompt"
        )

        trigger_scan = st.button("🔍 Scan & Calculate Carbon Impact", use_container_width=True)

    with col_res:
        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, caption="Uploaded Document Preview", use_container_width=True)
            
            if trigger_scan:
                # Read image bytes
                uploaded_image.seek(0)
                img_bytes = uploaded_image.read()
                mime_type = uploaded_image.type

                with st.spinner("🌿 Analyzing bill/receipt details using Gemini Vision..."):
                    result = graph.execute(
                        user_message=scan_prompt or "Analyze this image and estimate the carbon footprint.",
                        image_bytes=img_bytes,
                        image_mime_type=mime_type
                    )
                    st.session_state.scan_result = result.get("response", "No response returned.")

        elif trigger_scan:
            st.warning("⚠️ Please upload a valid image file first.")

    if st.session_state.scan_result:
        st.markdown("---")
        st.markdown("### 📊 Carbon Audit Result")
        st.markdown(
            f"""
            <div style="background-color: #0b1511; border: 1px solid rgba(34,197,94,0.3); border-radius: 12px; padding: 1.5rem;">
                {st.session_state.scan_result}
            </div>
            """,
            unsafe_allow_html=True
        )


# ===========================================================================
# TAB 3: ADK AI ECO-COACH CHATBOT
# ===========================================================================
with tab_coach:
    st.markdown("<div class='section-header'>💬 ADK AI Eco-Coach Chatbot</div>", unsafe_allow_html=True)
    st.markdown(
        "Chat with our sustainability assistant. Ask questions about carbon offsets, "
        "energy saving, sustainable lifestyle choices, or Indian climate initiatives. "
        "*(Note: Off-topic questions will be gracefully blocked by our guardrails).* "
    )

    # Pre-filled query buttons
    st.markdown("**💡 Try Asking:**")
    chat_col1, chat_col2, chat_col3 = st.columns(3)
    with chat_col1:
        if st.button("How to reduce my home energy bill in India?", use_container_width=True):
            st.session_state.last_chat_input = "How to reduce my home energy bill in India?"
    with chat_col2:
        if st.button("What is the carbon footprint of a vegetarian diet?", use_container_width=True):
            st.session_state.last_chat_input = "What is the carbon footprint of a vegetarian diet?"
    with chat_col3:
        if st.button("Is public transport much greener than electric vehicles?", use_container_width=True):
            st.session_state.last_chat_input = "Is public transport much greener than electric vehicles?"

    st.markdown("---")

    # Chat Display container
    chat_box = st.container()
    
    with chat_box:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(
                    f"""
                    <div class="chat-bubble-user">
                        <b>You:</b><br>{message['content']}
                    </div>
                    <div class="chat-clear"></div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="chat-bubble-coach">
                        <b>CarbonMitra Coach:</b><br>{message['content']}
                    </div>
                    <div class="chat-clear"></div>
                    """,
                    unsafe_allow_html=True
                )

    # Chat input field
    chat_input_val = st.text_input(
        "Ask CarbonMitra Coach:",
        value=st.session_state.last_chat_input,
        placeholder="Type your lifestyle or sustainability query here...",
        key="chat_query_field"
    )
    
    send_message = st.button("Send Message ➤")

    if send_message and chat_input_val.strip():
        # Add query to history
        st.session_state.chat_history.append({"role": "user", "content": chat_input_val})
        
        # Rerun to show user message instantly while waiting
        st.session_state.last_chat_input = ""
        
        with st.spinner("🌿 Consulting CarbonMitra Coach..."):
            # Call ADK Graph Router
            result = graph.execute(
                user_message=chat_input_val,
                chat_history=st.session_state.chat_history[:-1]
            )
            coach_reply = result.get("response", "I could not generate a response.")
            st.session_state.chat_history.append({"role": "assistant", "content": coach_reply})
            st.rerun()

    # Clear chat utility
    st.markdown(" ")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
