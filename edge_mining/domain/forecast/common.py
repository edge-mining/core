"""
Common classes for the Energy Forecast domain of the Edge Mining application.
"""

from edge_mining.domain.common import AdapterType


class ForecastProviderAdapter(AdapterType):
    """Types of forecast provider adapter."""

    DUMMY_SOLAR = "dummy_solar"
    HOME_ASSISTANT_API = "home_assistant_api"
