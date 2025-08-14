"""Dummy adapter (Implementation of Port) that simulates the home loads forecast for Edge Mining Application"""

from typing import Optional
import random

from edge_mining.domain.common import Watts
from edge_mining.domain.home_load.ports import HomeForecastProviderPort

class DummyHomeForecastProvider(HomeForecastProviderPort):
    """Generates a very basic fake home load forecast."""

    def get_home_consumption_forecast(self, hours_ahead: int = 24) -> Optional[Watts]:
        """Get the home consumption forecast."""
        # Super simple: return a random average load expected soon
        # A real implementation would look at time of day, historical data, etc.
        avg_load = Watts(random.uniform(200, 800)) # Average Watts expected
        print(f"DummyHomeForecastProvider: Estimated avg home load: {avg_load:.0f}W")
        return avg_load
