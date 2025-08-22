"""Settings module for Edge Mining application."""

from pydantic_settings import BaseSettings, SettingsConfigDict

# Using pydantic-settings for easy environment variable loading


class AppSettings(BaseSettings):
    """Settings for the Edge Mining application."""

    # Application settings
    log_level: str = "INFO"
    timezone: str = "Europe/Rome"  # Default timezone
    latitude: float = 41.9028  # Default latitude for Rome
    longitude: float = 12.4964  # Default longitude for Rome

    # Adapters Configuration (select which ones to use)
    persistence_adapter: str = "sqlite"  # Options: "in_memory", "sqlite", "yaml"
    policies_persistence_adapter: str = "yaml"  # Options: "in_memory", "sqlite", "yaml"

    sqlite_db_file: str = "edgemining.db"  # SQLite file path
    yaml_policies_dir: str = "optimization_policies"  # Directory for YAML policies

    # API Settings
    api_port: int = 8001

    # Scheduler settings
    scheduler_interval_seconds: int = 5  # Evaluate every 5 seconds

    model_config = SettingsConfigDict(
        env_file=".env",  # Load .env file if exists
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from env
    )
