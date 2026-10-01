"""
EcoHome Energy Advisor — Database Seeding Script
Run this directly: python seed_data.py
Creates energy_data.db with 30 days of realistic sample data.
"""

import os, sys, random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from models.energy import (
    Base, EnergyUsage, SolarGeneration, DeviceUsage, ElectricityPrice,
    init_db, get_engine,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "energy_data.db")
os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

random.seed(42)

# ─── Devices ────────────────────────────────────────────────────────────────

DEVICES = [
    dict(device_name="Central AC",           device_category="HVAC",      rated_power_kw=3.5,  preferred_start_hour=10, preferred_end_hour=15, is_schedulable=1, notes="Pre-cool during solar peak"),
    dict(device_name="Heat Pump",             device_category="HVAC",      rated_power_kw=2.8,  preferred_start_hour=10, preferred_end_hour=14, is_schedulable=1, notes="Avoid peak hours"),
    dict(device_name="EV Charger (Level 2)",  device_category="EV",        rated_power_kw=7.2,  preferred_start_hour=22, preferred_end_hour=6,  is_schedulable=1, notes="Off-peak or solar charging"),
    dict(device_name="Pool Pump",             device_category="Appliance", rated_power_kw=1.5,  preferred_start_hour=10, preferred_end_hour=16, is_schedulable=1, notes="Run during solar hours"),
    dict(device_name="Dishwasher",            device_category="Appliance", rated_power_kw=1.2,  preferred_start_hour=21, preferred_end_hour=23, is_schedulable=1, notes="Delay-start off-peak"),
    dict(device_name="Washing Machine",       device_category="Appliance", rated_power_kw=0.5,  preferred_start_hour=10, preferred_end_hour=14, is_schedulable=1, notes="Cold water midday"),
    dict(device_name="Dryer",                 device_category="Appliance", rated_power_kw=5.0,  preferred_start_hour=21, preferred_end_hour=23, is_schedulable=1, notes="High load — off-peak"),
    dict(device_name="Water Heater (HP)",     device_category="Appliance", rated_power_kw=0.5,  preferred_start_hour=10, preferred_end_hour=15, is_schedulable=1, notes="Solar peak"),
    dict(device_name="Refrigerator",          device_category="Appliance", rated_power_kw=0.15, preferred_start_hour=None, preferred_end_hour=None, is_schedulable=0, notes="Always on"),
    dict(device_name="Lighting (LED)",        device_category="Lighting",  rated_power_kw=0.3,  preferred_start_hour=None, preferred_end_hour=None, is_schedulable=0, notes="Smart dimming"),
]

# ─── TOU Pricing helper ──────────────────────────────────────────────────────

def tou_price(hour, is_weekend):
    if is_weekend:
        if 9 <= hour <= 21:
            return "off-peak", round(random.uniform(0.12, 0.16), 4)
        return "super-off-peak", round(random.uniform(0.07, 0.10), 4)
    if 7 <= hour <= 9 or 17 <= hour <= 21:
        return "peak", round(random.uniform(0.28, 0.38), 4)
    if 10 <= hour <= 16:
        return "off-peak", round(random.uniform(0.14, 0.18), 4)
    return "super-off-peak", round(random.uniform(0.07, 0.11), 4)

# ─── Solar helper ────────────────────────────────────────────────────────────

CONDITIONS = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Clear"]
WEIGHTS    = [0.35, 0.30, 0.15, 0.10, 0.10]
CLOUD = {"Sunny": 5, "Partly Cloudy": 40, "Cloudy": 80, "Light Rain": 90, "Clear": 2}
PANEL_KW = 10.0

# ─── Usage patterns ──────────────────────────────────────────────────────────

USAGE_PATTERNS = [
    # (device_name,            category,    kw,   hrs, start_h, rate)
    ("Central AC",             "HVAC",      3.5,  6,   13,  0.16),
    ("Heat Pump",              "HVAC",      2.8,  4,   7,   0.14),
    ("EV Charger (Level 2)",   "EV",        7.2,  4,   22,  0.09),
    ("Pool Pump",              "Appliance", 1.5,  7,   10,  0.14),
    ("Dishwasher",             "Appliance", 1.2,  1.5, 20,  0.10),
    ("Washing Machine",        "Appliance", 0.5,  1,   11,  0.14),
    ("Dryer",                  "Appliance", 5.0,  1,   21,  0.10),
    ("Water Heater (HP)",      "Appliance", 0.5,  2,   11,  0.14),
    ("Refrigerator",           "Appliance", 0.15, 24,  0,   0.14),
    ("Lighting (LED)",         "Lighting",  0.3,  5,   18,  0.20),
]


def seed(db_path: str = DB_PATH):
    engine = init_db(db_path)
    base_date = datetime.now() - timedelta(days=30)

    with Session(engine) as session:
        # Devices
        for d in DEVICES:
            if not session.query(DeviceUsage).filter_by(device_name=d["device_name"]).first():
                session.add(DeviceUsage(**d))
        session.commit()
        print(f"  ✅ {len(DEVICES)} devices configured")

        # Electricity prices
        price_rows = []
        for day_off in range(30):
            day = base_date + timedelta(days=day_off)
            is_wknd = day.weekday() >= 5
            for h in range(24):
                tier, price = tou_price(h, is_wknd)
                price_rows.append(ElectricityPrice(
                    timestamp=day.replace(hour=h, minute=0, second=0),
                    hour_of_day=h, price_per_kwh=price, tier=tier,
                    day_type="weekend" if is_wknd else "weekday",
                ))
        session.add_all(price_rows)
        session.commit()
        print(f"  ✅ {len(price_rows)} electricity price records (30d × 24h)")

        # Solar generation
        solar_rows = []
        for day_off in range(30):
            day = base_date + timedelta(days=day_off)
            cond = random.choices(CONDITIONS, weights=WEIGHTS)[0]
            cp   = CLOUD[cond]
            temp = round(random.uniform(15, 38), 1)
            for h in range(6, 20):
                factor   = max(0, 1 - abs(h - 13) / 7)
                irr      = round(factor * (100 - cp) / 100 * random.uniform(800, 1000), 1)
                gen      = max(0.0, round(irr / 1000 * PANEL_KW * (1 - (temp - 25) * 0.004), 3))
                eff      = round(gen / (PANEL_KW * factor + 1e-6) * 100, 1) if factor > 0.05 else 0.0
                solar_rows.append(SolarGeneration(
                    timestamp=day.replace(hour=h, minute=0, second=0),
                    generation_kwh=gen, panel_capacity_kw=PANEL_KW,
                    efficiency_pct=min(eff, 100.0), temperature_c=temp,
                    cloud_cover_pct=float(cp), irradiance_wm2=irr,
                ))
        session.add_all(solar_rows)
        session.commit()
        print(f"  ✅ {len(solar_rows)} solar generation records")

        # Energy usage
        usage_rows = []
        for day_off in range(30):
            day = base_date + timedelta(days=day_off)
            for dev, cat, kw, hrs, start_h, rate in USAGE_PATTERNS:
                if dev == "EV Charger (Level 2)" and random.random() < 0.2:
                    continue
                if dev == "Pool Pump" and random.random() < 0.1:
                    continue
                h = kw * hrs * random.uniform(0.85, 1.15)
                usage_rows.append(EnergyUsage(
                    timestamp=day.replace(hour=start_h, minute=random.randint(0, 30), second=0),
                    device_name=dev, device_category=cat,
                    consumption_kwh=round(kw * h / kw, 3),
                    duration_hours=round(h / kw, 2),
                    cost_usd=round(kw * hrs * rate, 4),
                ))
        session.add_all(usage_rows)
        session.commit()
        print(f"  ✅ {len(usage_rows)} energy usage records")

    print(f"\n🎉 Database ready at: {db_path}")


if __name__ == "__main__":
    print("EcoHome — Seeding database...")
    seed()
