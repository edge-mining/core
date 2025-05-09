"""Dummy adapter (Implementation of Port) that simulates the energy forecast for Edge Mining Application"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import random

from edge_mining.domain.common import Watts, Timestamp
from edge_mining.domain.forecast.ports import ForecastProviderPort
from edge_mining.domain.forecast.value_objects import ForecastData

class DummyForecastProvider(ForecastProviderPort):
    def __init__(self, latitude: float = None, longitude: float = None, capacity_kwp: float = 0.0):
        """Initializes the DummyForecastProvider."""
        self.latitude = latitude
        self.longitude = longitude
        self.capacity_kwp = capacity_kwp
        # You can set default values or use the ones from settings if needed
    
    """Generates a plausible fake solar forecast."""
    def get_solar_forecast(self) -> Optional[ForecastData]:
        print(f"DummyForecastProvider: Generating forecast for {self.latitude},{self.longitude} ({self.capacity_kwp} kWp)")
        now = datetime.now()
        predictions: Dict[Timestamp, Watts] = {}
        base_max_watts = self.capacity_kwp * 1000 * 0.8 # Assume 80% peak efficiency

        for i in range(24): # Forecast for next 24 hours
            future_time = now + timedelta(hours=i)
            hour = future_time.hour

            if 6 < hour < 20:
                # Simple sinusoidal based on hour
                solar_factor = max(0, 1 - abs(hour - 13) / 7)
                # Add some randomness
                noise = random.uniform(0.7, 1.0)
                predicted_power = Watts(base_max_watts * solar_factor * noise)
            else:
                predicted_power = Watts(0.0)

            predictions[Timestamp(future_time)] = predicted_power

        forecast = ForecastData(
            predicted_power=predictions,
            generated_at=Timestamp(now)
        )
        print(f"DummyForecastProvider: Generated {len(predictions)} predictions.")
        return forecast
