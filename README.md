# EcoHome Energy Advisor

An intelligent AI-powered energy optimization agent built with **LangGraph** and **OpenAI GPT-4o**.
It analyzes solar generation, electricity prices, weather forecasts, and historical energy usage to
deliver personalized, data-driven energy-saving recommendations.

## Project Structure

```
ecohome_solution/
├── models/
│   ├── __init__.py
│   └── energy.py              # SQLAlchemy ORM models
├── data/
│   ├── documents/             # Energy-saving knowledge base (7 .txt files)
│   ├── energy_data.db         # SQLite database (created by 01_db_setup.ipynb)
│   └── vectorstore/           # ChromaDB embeddings (created by 02_rag_setup.ipynb)
├── agent.py                   # LangGraph Energy Advisor agent
├── tools.py                   # Six agent tools
├── requirements.txt           # Python dependencies
├── 01_db_setup.ipynb          # Database initialisation and seeding
├── 02_rag_setup.ipynb         # RAG pipeline setup (ChromaDB + OpenAI embeddings)
├── 03_run_and_evaluate.ipynb  # Agent testing across 5 key scenarios
├── .env.example               # API key template
└── README.md                  # This file
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up API Key
```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

### 3. Run Notebooks in Order
1. **`01_db_setup.ipynb`** — Creates SQLite DB with 30 days of sample data
2. **`02_rag_setup.ipynb`** — Embeds knowledge base into ChromaDB
3. **`03_run_and_evaluate.ipynb`** — Tests and evaluates the agent

### 4. Run the Agent from Python
```python
from agent import build_agent, chat

advisor = build_agent()
chat("When should I charge my EV tomorrow?", agent=advisor)
```

## Agent Tools

| Tool | Description |
|------|-------------|
| `get_weather_forecast` | 7-day weather forecast with solar irradiance estimates |
| `get_electricity_prices` | Hourly TOU pricing (peak / off-peak / super off-peak) |
| `query_energy_usage` | Historical device energy consumption from SQLite |
| `query_solar_generation` | Historical solar panel generation data |
| `search_energy_tips` | Semantic RAG search over the knowledge base |
| `calculate_savings` | Dollar savings from shifting device schedules |

## Knowledge Base Documents

- `tip_energy_savings.txt` — General energy-saving tips
- `tip_device_best_practices.txt` — Per-device optimization guides
- `tip_hvac_optimization.txt` — HVAC strategies and heat pump guidance
- `tip_smart_home_automation.txt` — Automation rules for solar, pricing, occupancy
- `tip_renewable_energy_integration.txt` — Solar sizing, battery storage, incentives
- `tip_seasonal_energy_management.txt` — Season-specific strategies
- `tip_energy_storage_optimization.txt` — Battery dispatch, arbitrage, sizing

## Example Questions

- *"When should I charge my electric car tomorrow to minimize cost and maximize solar power?"*
- *"What temperature should I set my thermostat on Wednesday afternoon if electricity prices spike?"*
- *"Suggest three ways I can reduce energy use based on my usage history."*
- *"How much can I save by running my dishwasher during off-peak hours?"*
- *"What's the best time to run my pool pump this week based on the weather forecast?"*

## Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────┐
│         LangGraph Agent             │
│  ┌─────────────────────────────┐   │
│  │  GPT-4o + System Prompt     │   │
│  └────────────┬────────────────┘   │
│               │ tool calls          │
│  ┌────────────▼────────────────┐   │
│  │        Tool Node            │   │
│  │  • Weather Forecast         │   │
│  │  • Electricity Prices       │   │
│  │  • Energy Usage DB          │   │
│  │  • Solar Generation DB      │   │
│  │  • RAG Search (ChromaDB)    │   │
│  │  • Savings Calculator       │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
     │
     ▼
Personalized Energy Recommendation
```
