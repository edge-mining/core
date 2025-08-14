"""Collection of Common Objects for the Settings shared domain of the Edge Mining application."""

from enum import Enum

class PersistenceAdapter(Enum):
    """Types of persistence adapter."""
    IN_MEMORY = "in_memory"
    SQLITE = "sqlite"

class MinerControllerAdapter(Enum):
    """Types of miner controller adapter."""
    DUMMY = "dummy"

class ForecastProviderAdapter(Enum):
    """Types of forecast provider adapter."""
    DUMMY = "dummy"
    HOME_ASSISTANT = "home_assistant"

class HomeForecastProviderAdapter(Enum):
    """Types of home forecast provider adapter."""
    DUMMY = "dummy"

class NotificationAdapter(Enum):
    """Types of notification adapter."""
    DUMMY = "dummy"
    TELEGRAM = "telegram"

class PerformaceTrackerAdapter(Enum):
    """Types of performace tracker adapter."""
    DUMMY = "dummy"

class ExternalServiceAdapter(Enum):
    """Types of external service adapter."""
