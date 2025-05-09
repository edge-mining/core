from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

# Using pydantic-settings for easy environment variable loading

# Helper to define a default path in the project directory
DEFAULT_SQLITE_DB_PATH = os.path.join(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
), 'edgemining.db')

class AppSettings(BaseSettings):
    # Application settings
    log_level: str = "INFO"
    
    timezome: str = "Europe/Rome" # Default timezone

    # Adapters Configuration (select which ones to use)
    energy_monitor_adapter: str = "home_assistant" # Options: "dummy", "home_assistant"
    miner_controller_adapter: str = "dummy" # Options: "dummy", "vnish"
    forecast_provider_adapter: str = "home_assistant" # Options: "dummy", "home_assistant"
    home_forecast_adapter: str = "dummy" # Options: "dummy", "ml_model"
    persistence_adapter: str = "sqlite" # Options: "in_memory", "sqlite"
    notification_adapter: str = "dummy" # Options: "dummy", "telegram"
    performance_tracker_adapter: str = "dummy" # Options: "dummy", "braiins"

    sqlite_db_file: str = DEFAULT_SQLITE_DB_PATH # SQLite file path

    api_port: int = 8001

    # Dummy Adapter Settings (if used)
    dummy_miner_power_w: float = 1500.0
    dummy_battery_present: bool = True
    dummy_battery_capacity_wh: float = 10000.0

    # Real Adapter Settings (examples, loaded from .env)
    telegram_bot_token: Optional[str] = None # Token del tuo bot Telegram
    telegram_chat_id: Optional[str] = None # Chat ID (utente, gruppo o canale) a cui inviare

    # Location for Forecasts
    latitude: float = 41.90 # Default Rome
    longitude: float = 12.49
    pv_capacity_kwp: float = 5.0 # Default PV capacity

    # Scheduler settings
    scheduler_interval_seconds: int = 5 # Evaluate every 5 seconds

    # Home Assistant Adapter Settings (if energy_monitor_adapter=home_assistant)
    home_assistant_url: Optional[str] = None # e.g., http://homeassistant.local:8123
    home_assistant_token: Optional[str] = None # Long-Lived Access Token
    
    # Energy Monitor Adapter (if energy_monitor_adapter=home_assistant)
    # --- Entity IDs ---
    ha_entity_solar_production: Optional[str] = None # e.g., sensor.solar_power (W or kW)
    ha_entity_house_consumption: Optional[str] = None # e.g., sensor.house_load_power (W or kW) - MUST exclude miner load!
    ha_entity_grid_power: Optional[str] = None # e.g., sensor.grid_power (W or kW, +/- convention matters)
    ha_entity_battery_soc: Optional[str] = None # e.g., sensor.battery_soc (%)
    ha_entity_battery_power: Optional[str] = None # e.g., sensor.battery_power (W or kW, +/- convention matters)
    # --- Optional: Units (if entities report in kW instead of W) ---
    ha_unit_solar_production: str = "W" # "W" or "kW"
    ha_unit_house_consumption: str = "W" # "W" or "kW"
    ha_unit_grid_power: str = "W" # "W" or "kW"
    ha_unit_battery_power: str = "W" # "W" or "kW"
    # --- Optional: Battery Capacity (if not available via an entity) ---
    ha_battery_nominal_capacity_wh: Optional[float] = None # e.g., 10000.0
    
    # Forecast Provider Adapter (if forecast_provider_adapter=home_assistant)
    # --- Entity IDs ---
    ha_entity_solar_forecast_power_actual_h: Optional[str] = None # e.g., sensor.solar_forecast_power_actual_h (W or kW)
    ha_entity_solar_forecast_power_next_1h: Optional[str] = None # e.g., sensor.solar_forecast_power_next_1h (W or kW)
    ha_entity_solar_forecast_power_next_12h: Optional[str] = None # e.g., sensor.solar_forecast_power_next_12h (W or kW)
    ha_entity_solar_forecast_power_next_24h: Optional[str] = None # e.g., sensor.solar_forecast_power_next_24h (W or kW)
    ha_entity_solar_forecast_energy_actual_h: Optional[str] = None # e.g., sensor.solar_forecast_energy_actual_h (Wh or kWh)
    ha_entity_solar_forecast_energy_next_1h: Optional[str] = None # e.g., sensor.solar_forecast_energy_next_1h (Wh or kWh)
    ha_entity_solar_forecast_energy_next_24h: Optional[str] = None # e.g., sensor.solar_forecast_energy_next_24h (Wh or kWh)
    ha_entity_solar_forecast_energy_remaining_today: Optional[str] = None # e.g., sensor.solar_forecast_energy_remaining_today (Wh or kWh)
    # --- Optional: Units (if entities report in kW instead of W) ---
    ha_unit_solar_forecast_power_actual_h: str = "W" # "W" or "kW"
    ha_unit_solar_forecast_power_next_1h: str = "W" # "W" or "kW"
    ha_unit_solar_forecast_power_next_12h: str = "W" # "W" or "kW"
    ha_unit_solar_forecast_power_next_24h: str = "W" # "W" or "kW"
    ha_unit_solar_forecast_energy_actual_h: str = "Wh" # "Wh" or "kWh"
    ha_unit_solar_forecast_energy_next_1h: str = "Wh" # "Wh" or "kWh"
    ha_unit_solar_forecast_energy_next_24h: str = "Wh" # "Wh" or "kWh"
    ha_unit_solar_forecast_energy_remaining_today: str = "Wh" # "Wh" or "kWh"

    # --- Grid/Battery Power Convention ---
    # Set to True if your grid sensor reports positive for EXPORTING energy
    ha_grid_positive_export: bool = False
    # Set to True if your battery sensor reports positive for CHARGING
    ha_battery_positive_charge: bool = True

    model_config = SettingsConfigDict(
        env_file='.env',          # Load .env file if exists
        env_file_encoding='utf-8',
        extra='ignore'            # Ignore extra fields from env
    )