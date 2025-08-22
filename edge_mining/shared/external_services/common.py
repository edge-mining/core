"""Collection of Common Objects for the External Services shared domain of the Edge Mining application."""

from enum import Enum


class ExternalServiceAdapter(Enum):
    """Types of external service adapter."""

    HOME_ASSISTANT_API = "home_assistant_api"
    UNKNOWN = "unknown"
