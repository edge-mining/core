"""Collection of Common Objects for the Energy System Monitoring domain of the Edge Mining application."""

from enum import Enum

from edge_mining.domain.common import AdapterType


class EnergySourceType(Enum):
    """Enum for the different energy sources."""

    SOLAR = "solar"
    WIND = "wind"
    GRID = "grid"
    HYDROELECTRIC = "hydroelectric"
    OTHER = "other"


class EnergyMonitorAdapter(AdapterType):
    """Enum for the different energy monitor adapters."""

    DUMMY_SOLAR = "dummy_solar"
    HOME_ASSISTANT_API = "home_assistant_api"
    HOME_ASSISTANT_MQTT = "home_assistant_mqtt"
