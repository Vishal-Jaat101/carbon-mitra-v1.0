# 🌿 CarbonMitra — Personal Carbon Footprint Awareness Platform

> **BharatAgent Challenge 3** | Built with Streamlit + Google ADK 2.0 + Gemini 2.5 Flash

---

## 📋 Overview

**CarbonMitra** is an AI-powered, India-centric carbon footprint awareness platform that helps individuals **Understand**, **Track**, and **Reduce** their CO₂ impact through visual analytics, gamified challenges, multimodal image auditing, and guardrailed chat.

### 🌟 Key Features

1. **Baseline Calculator (UNDERSTAND)**: Interactive sidebar with 3 simple sliders (Monthly Electricity in kWh, Weekly Driving in KM, Diet Type selector) providing an instant baseline footprint score upon loading.
2. **Visual Analytics Chart (TRACK)**: Renders a beautiful breakdown of emissions by category (Energy, Transport, Food) using Streamlit's native `st.bar_chart` so tracking is immediately visible.
3. **Gamified Daily Challenges (REDUCE)**: Dynamic checklist of 3 simple actions (e.g. turning off idle appliances, transit switches, plant-based meals). Checking these off dynamically subtracts from the daily score.
4. **Multimodal Bill/Receipt Scanner**: File uploader for utility bills or receipts. Gemini analyzes the image, extracts consumption figures, and calculates the carbon impact.
5. **ADK AI Eco-Coach Chatbot**: A chat panel connected to an ADK graph router that helps users with custom lifestyle queries, protected by strict guardrails that block off-topic discussions.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                    │
│   Sidebar Sliders | Dashboard | Scanner | Eco-Coach Chat │
└──────────────────────────┬───────────────────────────────┘
                           │ user_message / image_bytes
                           ▼
┌──────────────────────────────────────────────────────────┐
│            CarbonMitra ADK Graph Workflow                │
│                                                          │
│  ┌──────────────┐     ┌──────────────┐                   │
│  │  Guard Node  │────▶│  Intent Node │                   │
│  │ (Guardrail)  │     │ (Classifier) │                   │
│  └──────────────┘     └──────┬───────┘                   │
│                              │                           │
│        ┌─────────────────────┼─────────────────────┐     │
│        ▼                     ▼                     ▼     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ Vision Audit │   │  Eco-Coach   │   │  Block Node  │  │
│  │    Node      │   │    Node      │   │ (Off-Topic)  │  │
│  └──────────────┘   └──────────────┘   └──────────────┘  │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   MCP Tools Layer                        │
│    Local Emission Factors | Baseline Calc | Equivalents  │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
            Gemini 2.5 Flash (google-genai)
```

---

## 📁 File Structure

```
Carbon-Tracer/
├── app.py              # Streamlit dashboard layout & tabs
├── agent_graph.py      # ADK 2.0 Graph Workflow & Gemini model integration
├── mcp_tools.py        # Emission variables, average coefficients & calculator logic
├── requirements.txt    # Project dependencies
├── .env                # API key (gitignored)
└── README.md           # Project documentation
```

---

## 🚀 Setup & Launch Instructions

### 1. Prerequisites
- Python **3.11+**
- A **Google Gemini API key** ([Get one here](https://aistudio.google.com/apikey))

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Key
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 5. Run the Application
```bash
streamlit run app.py
```
The application will launch on your default browser at `http://localhost:8501`.

---

## 🌍 Indian Context Emission Coefficients

| Category | Factor | Source / Details |
|----------|--------|------------------|
| Electricity | 0.82 kg CO2 / kWh | India average (CEA 2023) |
| Driving | 0.20 kg CO2 / km | Average petrol passenger car |
| Vegan Diet | 0.60 kg CO2 / meal | Sustainable food LCA |
| Vegetarian Diet | 1.10 kg CO2 / meal | Standard vegetarian meal |
| Non-Vegetarian Diet | 3.20 kg CO2 / meal | High footprint (poultry/mutton/beef average) |

---

## 🔐 Security Guardrails

- **Key Security**: API keys are strictly read from the environment using `os.environ.get("GEMINI_API_KEY")` and never hardcoded in scripts.
- **Topic Filtering**: A `GuardNode` verifies the semantic relevance of queries. Off-topic questions (e.g., about movies, coding help, political questions) are blocked gracefully.
- **Bilingual Support**: Guardrails detect Hindi characters and deliver customized blocking alerts in Hindi as well.
- **No PII storage**: History remains memory-bound to the user's Streamlit session scope.

---

*Built with 🌿 for a cleaner, greener India*
