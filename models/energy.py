"""SQLAlchemy ORM models for EcoHome energy data."""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class EnergyUsage(Base):
    """Records household energy consumption per device."""
    __tablename__ = "energy_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    device_name = Column(String(100), nullable=False)
    device_category = Column(String(50), nullable=False)  # HVAC, EV, Appliance, Lighting
    consumption_kwh = Column(Float, nullable=False)
    duration_hours = Column(Float, nullable=False)
    cost_usd = Column(Float, nullable=True)

    def __repr__(self):
        return (
            f"<EnergyUsage(device={self.device_name}, "
            f"kwh={self.consumption_kwh:.2f}, ts={self.timestamp})>"
        )


class SolarGeneration(Base):
    """Records solar panel energy generation."""
    __tablename__ = "solar_generation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    generation_kwh = Column(Float, nullable=False)
    panel_capacity_kw = Column(Float, nullable=False, default=10.0)
    efficiency_pct = Column(Float, nullable=True)    # actual / rated
    temperature_c = Column(Float, nullable=True)
    cloud_cover_pct = Column(Float, nullable=True)   # 0-100
    irradiance_wm2 = Column(Float, nullable=True)    # W/m²

    def __repr__(self):
        return (
            f"<SolarGeneration(kwh={self.generation_kwh:.2f}, "
            f"cloud={self.cloud_cover_pct}%, ts={self.timestamp})>"
        )


class DeviceUsage(Base):
    """Configuration and schedule for smart home devices."""
    __tablename__ = "device_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_name = Column(String(100), nullable=False, unique=True)
    device_category = Column(String(50), nullable=False)
    rated_power_kw = Column(Float, nullable=False)
    preferred_start_hour = Column(Integer, nullable=True)   # 0-23
    preferred_end_hour = Column(Integer, nullable=True)     # 0-23
    is_schedulable = Column(Integer, nullable=False, default=1)  # 1=yes, 0=no
    notes = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<DeviceUsage(name={self.device_name}, power={self.rated_power_kw}kW)>"


class ElectricityPrice(Base):
    """Time-of-use electricity pricing records."""
    __tablename__ = "electricity_price"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    hour_of_day = Column(Integer, nullable=False)   # 0-23
    price_per_kwh = Column(Float, nullable=False)
    tier = Column(String(30), nullable=False)       # peak / off-peak / super-off-peak
    day_type = Column(String(15), nullable=False, default="weekday")  # weekday / weekend

    def __repr__(self):
        return (
            f"<ElectricityPrice(hour={self.hour_of_day}, "
            f"${self.price_per_kwh:.3f}/kWh, tier={self.tier})>"
        )


def get_engine(db_path: str = "data/energy_data.db"):
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_db(db_path: str = "data/energy_data.db"):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
