"""
Dummy adapter (Implementation of Port) that simulates
the energy forecast for Edge Mining Application
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from edge_mining.domain.common import Timestamp, WattHours, Watts
from edge_mining.domain.energy.entities import EnergySource
from edge_mining.domain.forecast.aggregate_root import Forecast
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.domain.forecast.exceptions import ForecastError
from edge_mining.domain.forecast.ports import ForecastProviderPort
from edge_mining.domain.forecast.value_objects import (
    ForecastInterval,
    ForecastPowerPoint,
)
from edge_mining.shared.adapter_configs.forecast import ForecastProviderDummySolarConfig
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.config import Configuration
from edge_mining.shared.interfaces.factories import ForecastAdapterFactory
from edge_mining.shared.logging.port import LoggerPort


class DummyForecastProviderFactory(ForecastAdapterFactory):
    """
    Factory for creating a DummySolarForecastProvider instance.
    """

    def __init__(self):
        self._energy_source: Optional[EnergySource] = None

    def from_energy_source(self, energy_source: EnergySource) -> None:
        """Set the reference energy source"""
        self._energy_source = energy_source

    def create(
        self,
        config: Optional[Configuration],
        logger: Optional[LoggerPort],
        external_service: Optional[ExternalServicePort],
    ) -> ForecastProviderPort:
        """
        Creates a DummySolarForecastProvider instance.
        """
        if not isinstance(config, ForecastProviderDummySolarConfig):
            raise ForecastError(
                "Invalid configuration type for HomeAssistantAPI forecast provider. "
                "Expected ForecastProviderDummySolarConfig."
            )

        # Get the config from the forecast provider config
        forecast_provider_config: ForecastProviderDummySolarConfig = config

        capacity_kwp = forecast_provider_config.capacity_kwp
        if not capacity_kwp:
            if self._energy_source and self._energy_source.nominal_power_max:
                capacity_kwp = self._energy_source.nominal_power_max

        return DummySolarForecastProvider(
            latitude=forecast_provider_config.latitude,
            longitude=forecast_provider_config.longitude,
            capacity_kwp=capacity_kwp,
            efficiency_percent=forecast_provider_config.efficiency_percent,
            production_start_hour=forecast_provider_config.production_start_hour,
            production_end_hour=forecast_provider_config.production_end_hour,
            logger=logger,
        )


class DummySolarForecastProvider(ForecastProviderPort):
    """Dummy implementation of the ForecastProviderPort."""

    def __init__(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        capacity_kwp: float = 5.0,
        efficiency_percent: float = 80.0,
        production_start_hour: int = 6,
        production_end_hour: int = 20,
        logger: Optional[LoggerPort] = None,
    ):
        """Initializes the DummySolarForecastProvider."""
        super().__init__(forecast_provider_type=ForecastProviderAdapter.DUMMY_SOLAR)
        self.logger = logger

        self.latitude = latitude
        self.longitude = longitude
        self.capacity_kwp = capacity_kwp
        self.efficiency_percent = efficiency_percent
        self.production_start_hour = production_start_hour
        self.production_end_hour = production_end_hour
        # You can set default values or use the ones from settings if needed

    def get_forecast(self) -> Optional[Forecast]:
        # Generates a plausible fake solar forecast.
        if self.logger:
            self.logger.debug(
                f"DummySolarForecastProvider: "
                f"Generating forecast for {self.latitude},{self.longitude} "
                f"({self.capacity_kwp} kWp)"
            )
        now = datetime.now()
        forecast: Forecast = Forecast(timestamp=Timestamp(now))
        base_max_watts = self.capacity_kwp * 1000 * (self.efficiency_percent / 100)

        peak_hour = 13
        total_production_hours = self.production_end_hour - self.production_start_hour

        for i in range(24):  # Forecast for next 24 hours
            future_time = now + timedelta(hours=i)
            hour = future_time.hour

            if self.production_start_hour < hour < self.production_end_hour:
                # Simple sinusoidal based on hour
                solar_factor = max(0, 1 - abs(hour - peak_hour) / (total_production_hours / 2))
                # Add some randomness
                noise = random.uniform(0.7, 1.0)
                predicted_power = Watts(base_max_watts * solar_factor * noise)
            else:
                predicted_power = Watts(0.0)

            # Generate forecast for energy based on peak power
            predicted_energy = WattHours(predicted_power)

            # Create a forecast power point for this hour
            forecast_point = ForecastPowerPoint(timestamp=Timestamp(future_time), power=predicted_power)

            start_time = Timestamp(now) if i == 0 else Timestamp(now + timedelta(hours=i - 1))
            end_time = Timestamp(future_time)

            # Create a forecast interval for this hour
            interval = ForecastInterval(
                start=start_time,
                end=end_time,
                energy=predicted_energy,  # Energy in Wh for the hour
                energy_remaining=None,  # Remaining energy in Wh for the hour
                power_points=[forecast_point],
            )

            # Add the forecast interval to the forecast
            forecast.intervals.append(interval)

        if self.logger:
            self.logger.debug(f"DummyForecastProvider: Generated {len(forecast.intervals)} predictions.")
        return forecast
