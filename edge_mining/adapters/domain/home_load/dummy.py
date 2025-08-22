"""
Dummy adapter (Implementation of Port) that simulates
the home loads forecast for Edge Mining Application
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Optional

from edge_mining.domain.common import Timestamp, Watts
from edge_mining.domain.home_load.common import HomeForecastProviderAdapter
from edge_mining.domain.home_load.ports import HomeForecastProviderPort
from edge_mining.domain.home_load.value_objects import ConsumptionForecast
from edge_mining.shared.logging.port import LoggerPort


class DummyHomeForecastProvider(HomeForecastProviderPort):
    """Generates a very basic fake home load forecast."""

    def __init__(self, load_power_max: float = 500.0, logger: Optional[LoggerPort] = None):
        """Initializes the DummyHomeForecastProvider."""
        super().__init__(home_forecast_provider_type=HomeForecastProviderAdapter.DUMMY)
        self.logger = logger

        self.load_power_max = load_power_max
        # You can set default values or use the ones from settings if needed

    def get_home_consumption_forecast(self, hours_ahead: int = 3) -> Optional[ConsumptionForecast]:
        """Get the home consumption forecast."""
        # Super simple: return a random average load expected soon for next hours_ahead hours.
        if self.logger:
            self.logger.debug(
                f"DummyHomeForecastProvider: "
                f"Generating home load forecast for {hours_ahead} hours ahead "
                f"with max load {self.load_power_max} kWp"
            )

        now = datetime.now()
        predictions: Dict[Timestamp, Watts] = {}

        # Average Watts expected for the next hours
        # For simplicity, we just generate a random load value
        # In a real scenario, this would be based on historical data, time of day, etc.
        # Here we assume a random load between 200W and max load
        avg_load = Watts(random.uniform(200, self.load_power_max))

        for i in range(hours_ahead):  # Forecast for next hours_ahead hours
            future_time = now + timedelta(hours=i)
            predicted_power = avg_load
            predictions[Timestamp(future_time)] = predicted_power

        home_forecast = ConsumptionForecast(predicted_watts=predictions, generated_at=Timestamp(now))

        if self.logger:
            self.logger.debug(
                f"DummyHomeForecastProvider: Estimated avg home load: {avg_load:.0f}W for next {hours_ahead} hours"
            )
        return home_forecast
