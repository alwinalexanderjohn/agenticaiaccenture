"""
EcoHome Energy Advisor — Agent Tools
Provides weather, electricity pricing, energy DB queries, and RAG search.
"""

import json
import random
from datetime import datetime, timedelta
from typing import Optional
import os

from langchain.tools import tool
from sqlalchemy.orm import Session

from models.energy import EnergyUsage, SolarGeneration, ElectricityPrice, get_engine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session(db_path: str = "data/energy_data.db") -> Session:
    engine = get_engine(db_path)
    return Session(engine)


# ---------------------------------------------------------------------------
# Tool 1 — Weather Forecast
# ---------------------------------------------------------------------------

@tool
def get_weather_forecast(days: int = 3) -> str:
    """
    Retrieve a weather forecast for the next N days (1-7).
    Returns temperature, cloud cover, solar irradiance, and precipitation
    that affect solar panel output and HVAC energy demand.

    Args:
        days: Number of forecast days (1-7, default 3)
    """
    days = max(1, min(7, int(days)))
    forecast = []
    base_date = datetime.now()

    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Clear"]
    weights    = [0.35,    0.30,           0.15,    0.10,         0.10]

    for i in range(days):
        day = base_date + timedelta(days=i)
        condition = random.choices(conditions, weights=weights, k=1)[0]
        cloud_pct = {"Sunny": 5, "Partly Cloudy": 40, "Cloudy": 80,
                     "Light Rain": 90, "Clear": 2}[condition]
        temp_high = round(random.uniform(18, 38), 1)
        temp_low  = round(temp_high - random.uniform(8, 14), 1)
        irradiance = round(max(0, (100 - cloud_pct) / 100 * random.uniform(800, 1000)), 1)
        solar_est  = round(irradiance / 1000 * 10 * 6 * (1 - cloud_pct / 200), 2)  # kWh for 10kW system

        forecast.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_of_week": day.strftime("%A"),
            "condition": condition,
            "high_temp_c": temp_high,
            "low_temp_c": temp_low,
            "cloud_cover_pct": cloud_pct,
            "irradiance_wm2": irradiance,
            "estimated_solar_kwh": solar_est,
            "precipitation_mm": round(random.uniform(0, 20) if "Rain" in condition else 0, 1),
            "wind_speed_kmh": round(random.uniform(5, 35), 1),
        })

    return json.dumps({"forecast": forecast, "unit_notes": "temp in Celsius, energy in kWh"}, indent=2)


# ---------------------------------------------------------------------------
# Tool 2 — Electricity Pricing
# ---------------------------------------------------------------------------

@tool
def get_electricity_prices(date: Optional[str] = None) -> str:
    """
    Retrieve time-of-use electricity prices for a given date (YYYY-MM-DD).
    Returns hourly prices and tier classification (peak/off-peak/super-off-peak).
    If no date is provided, returns today's prices.

    Args:
        date: Target date in YYYY-MM-DD format (optional, defaults to today)
    """
    if date:
        try:
            target = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            target = datetime.now()
    else:
        target = datetime.now()

    is_weekend = target.weekday() >= 5
    prices = []

    for hour in range(24):
        if is_weekend:
            if 9 <= hour <= 21:
                tier, price = "off-peak", round(random.uniform(0.12, 0.16), 4)
            else:
                tier, price = "super-off-peak", round(random.uniform(0.07, 0.10), 4)
        else:
            if 7 <= hour <= 9 or 17 <= hour <= 21:
                tier, price = "peak", round(random.uniform(0.28, 0.38), 4)
            elif 10 <= hour <= 16:
                tier, price = "off-peak", round(random.uniform(0.14, 0.18), 4)
            else:
                tier, price = "super-off-peak", round(random.uniform(0.07, 0.11), 4)

        prices.append({
            "hour": hour,
            "time": f"{hour:02d}:00",
            "price_per_kwh_usd": price,
            "tier": tier,
        })

    cheapest = min(prices, key=lambda x: x["price_per_kwh_usd"])
    priciest = max(prices, key=lambda x: x["price_per_kwh_usd"])

    return json.dumps({
        "date": target.strftime("%Y-%m-%d"),
        "day_type": "weekend" if is_weekend else "weekday",
        "prices": prices,
        "cheapest_hour": cheapest,
        "most_expensive_hour": priciest,
        "avg_price_per_kwh": round(sum(p["price_per_kwh_usd"] for p in prices) / 24, 4),
    }, indent=2)


# ---------------------------------------------------------------------------
# Tool 3 — Query Energy Usage
# ---------------------------------------------------------------------------

@tool
def query_energy_usage(
    device_name: Optional[str] = None,
    device_category: Optional[str] = None,
    days_back: int = 7,
    db_path: str = "data/energy_data.db",
) -> str:
    """
    Query historical household energy consumption from the database.
    Filter by device name or category (HVAC, EV, Appliance, Lighting).
    Returns usage records, totals, and averages for the requested period.

    Args:
        device_name:     Specific device to filter (optional)
        device_category: Device category to filter — HVAC, EV, Appliance, Lighting (optional)
        days_back:       Number of past days to include (default 7)
        db_path:         Path to the SQLite database
    """
    since = datetime.now() - timedelta(days=days_back)

    try:
        session = _get_session(db_path)
        query = session.query(EnergyUsage).filter(EnergyUsage.timestamp >= since)
        if device_name:
            query = query.filter(EnergyUsage.device_name.ilike(f"%{device_name}%"))
        if device_category:
            query = query.filter(EnergyUsage.device_category.ilike(f"%{device_category}%"))

        records = query.order_by(EnergyUsage.timestamp.desc()).all()

        if not records:
            return json.dumps({"message": "No energy usage records found for the given filters.", "records": []})

        data = [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "device_name": r.device_name,
                "device_category": r.device_category,
                "consumption_kwh": r.consumption_kwh,
                "duration_hours": r.duration_hours,
                "cost_usd": r.cost_usd,
            }
            for r in records
        ]

        total_kwh  = sum(r.consumption_kwh for r in records)
        total_cost = sum(r.cost_usd or 0.0 for r in records)
        avg_daily  = total_kwh / max(days_back, 1)

        session.close()
        return json.dumps({
            "period_days": days_back,
            "total_records": len(data),
            "total_consumption_kwh": round(total_kwh, 2),
            "total_cost_usd": round(total_cost, 2),
            "avg_daily_kwh": round(avg_daily, 2),
            "records": data[:50],  # cap at 50 rows for context
        }, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool 4 — Query Solar Generation
# ---------------------------------------------------------------------------

@tool
def query_solar_generation(
    days_back: int = 7,
    db_path: str = "data/energy_data.db",
) -> str:
    """
    Query historical solar panel generation data from the database.
    Returns generation totals, peak output times, and efficiency metrics.

    Args:
        days_back: Number of past days to include (default 7)
        db_path:   Path to the SQLite database
    """
    since = datetime.now() - timedelta(days=days_back)

    try:
        session = _get_session(db_path)
        records = (
            session.query(SolarGeneration)
            .filter(SolarGeneration.timestamp >= since)
            .order_by(SolarGeneration.timestamp.desc())
            .all()
        )

        if not records:
            return json.dumps({"message": "No solar generation records found.", "records": []})

        data = [
            {
                "timestamp": r.timestamp.isoformat(),
                "generation_kwh": r.generation_kwh,
                "panel_capacity_kw": r.panel_capacity_kw,
                "efficiency_pct": r.efficiency_pct,
                "temperature_c": r.temperature_c,
                "cloud_cover_pct": r.cloud_cover_pct,
                "irradiance_wm2": r.irradiance_wm2,
            }
            for r in records
        ]

        total_gen = sum(r.generation_kwh for r in records)
        avg_daily = total_gen / max(days_back, 1)
        avg_eff   = (
            sum(r.efficiency_pct for r in records if r.efficiency_pct) /
            max(1, sum(1 for r in records if r.efficiency_pct))
        )

        session.close()
        return json.dumps({
            "period_days": days_back,
            "total_records": len(data),
            "total_generation_kwh": round(total_gen, 2),
            "avg_daily_generation_kwh": round(avg_daily, 2),
            "avg_efficiency_pct": round(avg_eff, 1),
            "records": data[:50],
        }, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool 5 — RAG: Search Energy Tips
# ---------------------------------------------------------------------------

@tool
def search_energy_tips(query: str, n_results: int = 4) -> str:
    """
    Search the EcoHome knowledge base for energy-saving tips and best practices
    relevant to the user's query using semantic similarity.

    Args:
        query:     Natural-language question or topic to search for
        n_results: Number of tip documents to return (default 4)
    """
    try:
        import chromadb
        from langchain_openai import OpenAIEmbeddings

        client = chromadb.PersistentClient(path="data/vectorstore")
        collection = client.get_collection("energy_tips")

        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
        query_embedding = embeddings_model.embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        tips = []
        for i, (doc, meta, dist) in enumerate(
            zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
        ):
            tips.append({
                "rank": i + 1,
                "relevance_score": round(1 - dist, 3),
                "source": meta.get("source", "unknown"),
                "topic": meta.get("topic", "general"),
                "content": doc,
            })

        return json.dumps({"query": query, "tips": tips}, indent=2)

    except Exception as exc:
        return json.dumps({"error": f"RAG search failed: {exc}. Ensure 02_rag_setup.ipynb was run."})


# ---------------------------------------------------------------------------
# Tool 6 — Savings Calculator
# ---------------------------------------------------------------------------

@tool
def calculate_savings(
    device_name: str,
    rated_power_kw: float,
    usage_hours_per_day: float,
    current_hour: int,
    optimal_hour: int,
    days: int = 30,
    db_path: str = "data/energy_data.db",
) -> str:
    """
    Calculate potential cost savings by shifting a device's runtime
    from the current schedule to an optimal (cheaper) time slot.

    Args:
        device_name:         Name of the device (e.g., "EV Charger")
        rated_power_kw:      Device power consumption in kW
        usage_hours_per_day: Daily usage hours
        current_hour:        Current start hour (0-23)
        optimal_hour:        Proposed optimal start hour (0-23)
        days:                Projection period in days (default 30)
        db_path:             Path to the SQLite database
    """
    try:
        # Pull pricing for today to get representative rates
        session = _get_session(db_path)
        today = datetime.now().date()

        current_prices = (
            session.query(ElectricityPrice)
            .filter(ElectricityPrice.hour_of_day == current_hour)
            .order_by(ElectricityPrice.timestamp.desc())
            .first()
        )
        optimal_prices = (
            session.query(ElectricityPrice)
            .filter(ElectricityPrice.hour_of_day == optimal_hour)
            .order_by(ElectricityPrice.timestamp.desc())
            .first()
        )
        session.close()

        # Fall back to heuristic if no DB data yet
        def heuristic_price(hour):
            if 7 <= hour <= 9 or 17 <= hour <= 21:
                return 0.32
            elif 10 <= hour <= 16:
                return 0.16
            return 0.09

        current_rate  = current_prices.price_per_kwh  if current_prices  else heuristic_price(current_hour)
        optimal_rate  = optimal_prices.price_per_kwh  if optimal_prices  else heuristic_price(optimal_hour)

        energy_per_day   = rated_power_kw * usage_hours_per_day
        current_daily    = energy_per_day * current_rate
        optimal_daily    = energy_per_day * optimal_rate
        daily_savings    = current_daily - optimal_daily
        total_savings    = daily_savings * days
        co2_saved_kg     = energy_per_day * days * 0.233  # kg CO₂/kWh (US avg grid)

        def tier(rate):
            if rate >= 0.25: return "peak"
            elif rate >= 0.14: return "off-peak"
            return "super-off-peak"

        return json.dumps({
            "device": device_name,
            "rated_power_kw": rated_power_kw,
            "usage_hours_per_day": usage_hours_per_day,
            "current_schedule": {
                "start_hour": current_hour,
                "rate_per_kwh": round(current_rate, 4),
                "tier": tier(current_rate),
                "daily_cost_usd": round(current_daily, 2),
            },
            "optimal_schedule": {
                "start_hour": optimal_hour,
                "rate_per_kwh": round(optimal_rate, 4),
                "tier": tier(optimal_rate),
                "daily_cost_usd": round(optimal_daily, 2),
            },
            "savings": {
                "daily_savings_usd": round(daily_savings, 2),
                f"savings_over_{days}_days_usd": round(total_savings, 2),
                "annual_savings_usd": round(daily_savings * 365, 2),
                "co2_reduction_kg": round(co2_saved_kg, 1),
            },
            "recommendation": (
                f"Shifting {device_name} from {current_hour:02d}:00 to {optimal_hour:02d}:00 "
                f"saves ${daily_savings:.2f}/day (${total_savings:.2f} over {days} days)."
            ),
        }, indent=2)

    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    get_weather_forecast,
    get_electricity_prices,
    query_energy_usage,
    query_solar_generation,
    search_energy_tips,
    calculate_savings,
]
