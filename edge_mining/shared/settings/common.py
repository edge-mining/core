"""Collection of Common Objects for the Settings shared domain of the Edge Mining application."""

from enum import Enum

class PersistenceAdapter(Enum):
    IN_MEMORY = "in_memory"
    SQLITE = "sqlite"

class EnergyMonitorAdapter(Enum):
    DUMMY = "dummy"
    HOME_ASSISTANT = "home_assistant"

class MinerControllerAdapter(Enum):
    DUMMY = "dummy"

class ForecastProviderAdapter(Enum):
    DUMMY = "dummy"
    HOME_ASSISTANT = "home_assistant"

class HomeForecastProviderAdapter(Enum):
    DUMMY = "dummy"

class NotificationAdapter(Enum):
    DUMMY = "dummy"
    TELEGRAM = "telegram"

class PerformaceTrackerAdapter(Enum):
    DUMMY = "dummy"

class ExternalServiceAdapter(Enum):
    HOME_ASSISTANT = "home_assistant"