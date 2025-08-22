"""
Common classes for the Home Load domain of the Edge Mining application.
"""

from edge_mining.domain.common import AdapterType


class HomeForecastProviderAdapter(AdapterType):
    """Types of home forecast provider adapter."""

    DUMMY = "dummy"
