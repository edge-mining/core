"""
Home Assistant API adapter (Implementation of Port)
for the energy forecast of Edge Mining Application
"""

from datetime import datetime, time, timedelta
from typing import List, Optional, cast

from edge_mining.adapters.infrastructure.homeassistant.homeassistant_api import (
    ServiceHomeAssistantAPI,
)
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
from edge_mining.shared.interfaces.config import Configuration
from edge_mining.shared.adapter_configs.forecast import (
    ForecastProviderHomeAssistantConfig,
)
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.factories import ForecastAdapterFactory
from edge_mining.shared.logging.port import LoggerPort


class HomeAssistantForecastProviderFactory(ForecastAdapterFactory):
    """
    Factory for creating HomeAssistantForecastProvider instances.
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
    ) -> "HomeAssistantForecastProvider":
        """Creates a HomeAssistantForecastProvider instance."""

        # Needs to have the Home Assistant API service as external_service
        if not external_service:
            raise ForecastError("External service is required for HomeAssistantForecastProvider.")

        if not external_service.external_service_type == ExternalServiceAdapter.HOME_ASSISTANT_API:
            raise ForecastError("External service must be of type Home Assistant API")

        if not isinstance(config, ForecastProviderHomeAssistantConfig):
            raise ForecastError(
                "Invalid configuration type for HomeAssistantAPI forecast provider. "
                "Expected ForecastProviderHomeAssistantConfig."
            )

        # Get the config from the forecast provider config
        forecast_provider_config: ForecastProviderHomeAssistantConfig = config
        service_home_assistant_api = cast(ServiceHomeAssistantAPI, external_service)

        # Use the builder to configure the provider, in this way we can
        # ensure that all required entities are set.
        builder = HomeAssistantForecastProviderBuilder(home_assistant=service_home_assistant_api, logger=logger)

        # Configure the builder with the entities and units
        if forecast_provider_config.entity_forecast_power_actual_h:
            builder.set_actual_power_entity(
                forecast_provider_config.entity_forecast_power_actual_h,
                forecast_provider_config.unit_forecast_power_actual_h,
            )
        if forecast_provider_config.entity_forecast_power_next_1h:
            builder.set_next_1h_power_entity(
                forecast_provider_config.entity_forecast_power_next_1h,
                forecast_provider_config.unit_forecast_power_next_1h,
            )
        if forecast_provider_config.entity_forecast_power_next_12h:
            builder.set_next_12h_power_entity(
                forecast_provider_config.entity_forecast_power_next_12h,
                forecast_provider_config.unit_forecast_power_next_12h,
            )
        if forecast_provider_config.entity_forecast_power_next_24h:
            builder.set_next_24h_power_entity(
                forecast_provider_config.entity_forecast_power_next_24h,
                forecast_provider_config.unit_forecast_power_next_24h,
            )
        if forecast_provider_config.entity_forecast_energy_actual_h:
            builder.set_actual_energy_entity(
                forecast_provider_config.entity_forecast_energy_actual_h,
                forecast_provider_config.unit_forecast_energy_actual_h,
            )
        if forecast_provider_config.entity_forecast_energy_next_1h:
            builder.set_next_1h_energy_entity(
                forecast_provider_config.entity_forecast_energy_next_1h,
                forecast_provider_config.unit_forecast_energy_next_1h,
            )
        if forecast_provider_config.entity_forecast_energy_today:
            builder.set_today_energy_entity(
                forecast_provider_config.entity_forecast_energy_today,
                forecast_provider_config.unit_forecast_energy_today,
            )
        if forecast_provider_config.entity_forecast_energy_tomorrow:
            builder.set_tomorrow_energy_entity(
                forecast_provider_config.entity_forecast_energy_tomorrow,
                forecast_provider_config.unit_forecast_energy_tomorrow,
            )
        if forecast_provider_config.entity_forecast_energy_remaining_today:
            builder.set_remaining_today_energy_entity(
                forecast_provider_config.entity_forecast_energy_remaining_today,
                forecast_provider_config.unit_forecast_energy_remaining_today,
            )

        # --- Build the adapter ---
        return builder.build()


class HomeAssistantForecastProviderBuilder:
    """Builder for HomeAssistantForecastProvider instances."""

    def __init__(self, home_assistant: ServiceHomeAssistantAPI, logger: Optional[LoggerPort]):
        """Initializes the HomeAssistantForecastProviderBuilder."""
        self.home_assistant: ServiceHomeAssistantAPI = home_assistant
        self.logger: Optional[LoggerPort] = logger
        self.entity_forecast_power_actual_h: Optional[str] = None
        self.entity_forecast_power_next_1h: Optional[str] = None
        self.entity_forecast_power_next_12h: Optional[str] = None
        self.entity_forecast_power_next_24h: Optional[str] = None
        self.entity_forecast_energy_actual_h: Optional[str] = None
        self.entity_forecast_energy_next_1h: Optional[str] = None
        self.entity_forecast_energy_today: Optional[str] = None
        self.entity_forecast_energy_tomorrow: Optional[str] = None
        self.entity_forecast_energy_remaining_today: Optional[str] = None
        self.unit_forecast_power_actual_h: str = "W"
        self.unit_forecast_power_next_1h: str = "W"
        self.unit_forecast_power_next_12h: str = "W"
        self.unit_forecast_power_next_24h: str = "W"
        self.unit_forecast_energy_actual_h: str = "kWh"
        self.unit_forecast_energy_next_1h: str = "kWh"
        self.unit_forecast_energy_today: str = "kWh"
        self.unit_forecast_energy_tomorrow: str = "kWh"
        self.unit_forecast_energy_remaining_today: str = "kWh"

    def set_actual_power_entity(self, entity_id: str, unit: str = "W") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the actual solar power forecast."""
        self.entity_forecast_power_actual_h = entity_id
        self.unit_forecast_power_actual_h = unit.lower()
        return self

    def set_next_1h_power_entity(self, entity_id: str, unit: str = "W") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the next 1 hour solar power forecast."""
        self.entity_forecast_power_next_1h = entity_id
        self.unit_forecast_power_next_1h = unit.lower()
        return self

    def set_next_12h_power_entity(self, entity_id: str, unit: str = "W") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the next 12 hours solar power forecast."""
        self.entity_forecast_power_next_12h = entity_id
        self.unit_forecast_power_next_12h = unit.lower()
        return self

    def set_next_24h_power_entity(self, entity_id: str, unit: str = "W") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the next 24 hours solar power forecast."""
        self.entity_forecast_power_next_24h = entity_id
        self.unit_forecast_power_next_24h = unit.lower()
        return self

    def set_actual_energy_entity(self, entity_id: str, unit: str = "kWh") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the actual solar energy forecast."""
        self.entity_forecast_energy_actual_h = entity_id
        self.unit_forecast_energy_actual_h = unit.lower()
        return self

    def set_next_1h_energy_entity(self, entity_id: str, unit: str = "kWh") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the next 1 hour solar energy forecast."""
        self.entity_forecast_energy_next_1h = entity_id
        self.unit_forecast_energy_next_1h = unit.lower()
        return self

    def set_today_energy_entity(self, entity_id: str, unit: str = "kWh") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the today solar energy forecast."""
        self.entity_forecast_energy_today = entity_id
        self.unit_forecast_energy_today = unit.lower()
        return self

    def set_tomorrow_energy_entity(self, entity_id: str, unit: str = "kWh") -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the tomorrow solar energy forecast."""
        self.entity_forecast_energy_tomorrow = entity_id
        self.unit_forecast_energy_tomorrow = unit.lower()
        return self

    def set_remaining_today_energy_entity(
        self, entity_id: str, unit: str = "kWh"
    ) -> "HomeAssistantForecastProviderBuilder":
        """Sets the entity ID for the remaining energy forecast for today."""
        self.entity_forecast_energy_remaining_today = entity_id
        self.unit_forecast_energy_remaining_today = unit.lower()
        return self

    def build(self) -> "HomeAssistantForecastProvider":
        """Builds the HomeAssistantForecastProvider instance."""
        if not self.entity_forecast_power_actual_h:
            raise ValueError("Entity ID for actual solar power forecast is required.")
        if not self.entity_forecast_energy_actual_h:
            raise ValueError("Entity ID for actual solar energy forecast is required.")

        forecast_provider = HomeAssistantForecastProvider(
            home_assistant=self.home_assistant,
            entity_forecast_power_actual_h=self.entity_forecast_power_actual_h,
            entity_forecast_power_next_1h=self.entity_forecast_power_next_1h,
            entity_forecast_power_next_12h=self.entity_forecast_power_next_12h,
            entity_forecast_power_next_24h=self.entity_forecast_power_next_24h,
            entity_forecast_energy_actual_h=self.entity_forecast_energy_actual_h,
            entity_forecast_energy_next_1h=self.entity_forecast_energy_next_1h,
            entity_forecast_energy_today=self.entity_forecast_energy_today,
            entity_forecast_energy_tomorrow=self.entity_forecast_energy_tomorrow,
            entity_forecast_energy_remaining_today=self.entity_forecast_energy_remaining_today,
            unit_forecast_power_actual_h=self.unit_forecast_power_actual_h,
            unit_forecast_power_next_1h=self.unit_forecast_power_next_1h,
            unit_forecast_power_next_12h=self.unit_forecast_power_next_12h,
            unit_forecast_power_next_24h=self.unit_forecast_power_next_24h,
            unit_forecast_energy_actual_h=self.unit_forecast_energy_actual_h,
            unit_forecast_energy_next_1h=self.unit_forecast_energy_next_1h,
            unit_forecast_energy_today=self.unit_forecast_energy_today,
            unit_forecast_energy_tomorrow=self.unit_forecast_energy_tomorrow,
            unit_forecast_energy_remaining_today=self.unit_forecast_energy_remaining_today,
            logger=self.logger,
        )

        return forecast_provider


class HomeAssistantForecastProvider(ForecastProviderPort):
    """
    Fetches energy forecast from a Home Assistant instance via its REST API.

    Requires careful configuration of entity IDs in the .env file.
    """

    def __init__(
        self,
        home_assistant: ServiceHomeAssistantAPI,
        entity_forecast_power_actual_h: Optional[str],
        entity_forecast_power_next_1h: Optional[str],
        entity_forecast_power_next_12h: Optional[str],
        entity_forecast_power_next_24h: Optional[str],
        entity_forecast_energy_actual_h: Optional[str],
        entity_forecast_energy_next_1h: Optional[str],
        entity_forecast_energy_today: Optional[str],
        entity_forecast_energy_tomorrow: Optional[str],
        entity_forecast_energy_remaining_today: Optional[str],
        unit_forecast_power_actual_h: str = "W",
        unit_forecast_power_next_1h: str = "W",
        unit_forecast_power_next_12h: str = "W",
        unit_forecast_power_next_24h: str = "W",
        unit_forecast_energy_actual_h: str = "kWh",
        unit_forecast_energy_next_1h: str = "kWh",
        unit_forecast_energy_today: str = "kWh",
        unit_forecast_energy_tomorrow: str = "kWh",
        unit_forecast_energy_remaining_today: str = "kWh",
        logger: Optional[LoggerPort] = None,
    ):
        # Initialize the HomeAssistant API Service
        super().__init__(forecast_provider_type=ForecastProviderAdapter.HOME_ASSISTANT_API)
        self.home_assistant = home_assistant
        self.logger = logger

        self.entity_forecast_power_actual_h = entity_forecast_power_actual_h
        self.entity_forecast_power_next_1h = entity_forecast_power_next_1h
        self.entity_forecast_power_next_12h = entity_forecast_power_next_12h
        self.entity_forecast_power_next_24h = entity_forecast_power_next_24h
        self.entity_forecast_energy_actual_h = entity_forecast_energy_actual_h
        self.entity_forecast_energy_next_1h = entity_forecast_energy_next_1h
        self.entity_forecast_energy_today = entity_forecast_energy_today
        self.entity_forecast_energy_tomorrow = entity_forecast_energy_tomorrow
        self.entity_forecast_energy_remaining_today = entity_forecast_energy_remaining_today
        self.unit_forecast_power_actual_h = unit_forecast_power_actual_h.lower()
        self.unit_forecast_power_next_1h = unit_forecast_power_next_1h.lower()
        self.unit_forecast_power_next_12h = unit_forecast_power_next_12h.lower()
        self.unit_forecast_power_next_24h = unit_forecast_power_next_24h.lower()
        self.unit_forecast_energy_actual_h = unit_forecast_energy_actual_h.lower()
        self.unit_forecast_energy_next_1h = unit_forecast_energy_next_1h.lower()
        self.unit_forecast_energy_today = unit_forecast_energy_today.lower()
        self.unit_forecast_energy_tomorrow = unit_forecast_energy_tomorrow.lower()
        self.unit_forecast_energy_remaining_today = unit_forecast_energy_remaining_today.lower()

        if self.logger:
            self.logger.debug(
                f"Entities Configured for Power:"
                f"Actual='{entity_forecast_power_actual_h}', "
                f"Next 1h='{entity_forecast_power_next_1h}', "
                f"Next 12h='{entity_forecast_power_next_12h}', "
                f"Next 24h='{entity_forecast_power_next_24h}'"
            )
            self.logger.debug(
                f"Entities Configured for Energy:"
                f"Actual='{entity_forecast_energy_actual_h}', "
                f"Today='{entity_forecast_energy_next_1h}', "
                f"Tomorow='{entity_forecast_energy_tomorrow}', "
                f"Remaining='{entity_forecast_energy_remaining_today}'"
            )

            self.logger.debug(
                f"Units for Power:"
                f"Actual='{unit_forecast_power_actual_h}', "
                f"Next 1h='{unit_forecast_power_next_1h}', "
                f"Next 12h='{unit_forecast_power_next_12h}', "
                f"Next 24h='{unit_forecast_power_next_24h}'"
            )
            self.logger.debug(
                f"Units Configured for Energy:"
                f"Actual='{unit_forecast_energy_actual_h}', "
                f"Next 1h='{unit_forecast_energy_next_1h}', "
                f"Today='{unit_forecast_energy_today}', "
                f"Tomorrow='{unit_forecast_energy_tomorrow}', "
                f"Remaining='{unit_forecast_energy_remaining_today}'"
            )

    def get_forecast(self) -> Optional[Forecast]:
        """Fetches the energy production forecast."""
        if self.logger:
            self.logger.debug("Fetching forecast energy state from Home Assistant...")
        has_critical_error = False

        # --- Actual Power h ---
        if self.entity_forecast_power_actual_h:
            state_forecast_power_actual_h, _ = self.home_assistant.get_entity_state(self.entity_forecast_power_actual_h)
            power_actual_h = self.home_assistant.parse_power(
                state_forecast_power_actual_h,
                self.unit_forecast_power_actual_h,
                self.entity_forecast_power_actual_h or "N/A",
            )
        else:
            power_actual_h = None

        # --- Next Power 1h ---
        if self.entity_forecast_power_next_1h:
            state_forecast_power_next_1h, _ = self.home_assistant.get_entity_state(self.entity_forecast_power_next_1h)
            power_next_1h = self.home_assistant.parse_power(
                state_forecast_power_next_1h,
                self.unit_forecast_power_next_1h,
                self.entity_forecast_power_next_1h or "N/A",
            )
        else:
            power_next_1h = None

        # --- Next Power 12h ---
        if self.entity_forecast_power_next_12h:
            state_forecast_power_next_12h, _ = self.home_assistant.get_entity_state(self.entity_forecast_power_next_12h)
            power_next_12h = self.home_assistant.parse_power(
                state_forecast_power_next_12h,
                self.unit_forecast_power_next_12h,
                self.entity_forecast_power_next_12h or "N/A",
            )
        else:
            power_next_12h = None

        # --- Next Power 24h ---
        if self.entity_forecast_power_next_24h:
            state_forecast_power_next_24h, _ = self.home_assistant.get_entity_state(self.entity_forecast_power_next_24h)
            power_next_24h = self.home_assistant.parse_power(
                state_forecast_power_next_24h,
                self.unit_forecast_power_next_24h,
                self.entity_forecast_power_next_24h or "N/A",
            )
        else:
            power_next_24h = None

        # --- Actual Energy h ---
        if self.entity_forecast_energy_actual_h:
            state_forecast_energy_actual_h, _ = self.home_assistant.get_entity_state(
                self.entity_forecast_energy_actual_h
            )
            energy_actual_h = self.home_assistant.parse_energy(
                state_forecast_energy_actual_h,
                self.unit_forecast_energy_actual_h,
                self.entity_forecast_energy_actual_h or "N/A",
            )
        else:
            energy_actual_h = None

        # --- Next Energy 1h ---
        if self.entity_forecast_energy_next_1h:
            state_forecast_energy_next_1h, _ = self.home_assistant.get_entity_state(self.entity_forecast_energy_next_1h)
            energy_next_1h = self.home_assistant.parse_energy(
                state_forecast_energy_next_1h,
                self.unit_forecast_energy_next_1h,
                self.entity_forecast_energy_next_1h or "N/A",
            )
        else:
            energy_next_1h = None

        # --- Today Energy ---
        if self.entity_forecast_energy_today:
            state_forecast_energy_today, _ = self.home_assistant.get_entity_state(self.entity_forecast_energy_today)
            energy_today = self.home_assistant.parse_energy(
                state_forecast_energy_today,
                self.unit_forecast_energy_today,
                self.entity_forecast_energy_today or "N/A",
            )
        else:
            energy_today = None

        # --- Tomorrow Energy ---
        if self.entity_forecast_energy_tomorrow:
            state_forecast_energy_tomorrow, _ = self.home_assistant.get_entity_state(
                self.entity_forecast_energy_tomorrow
            )
            energy_tomorrow = self.home_assistant.parse_energy(
                state_forecast_energy_tomorrow,
                self.unit_forecast_energy_tomorrow,
                self.entity_forecast_energy_tomorrow or "N/A",
            )
        else:
            energy_tomorrow = None

        # --- Remaining Energy Today ---
        if self.entity_forecast_energy_remaining_today:
            state_forecast_energy_remaining_today, _ = self.home_assistant.get_entity_state(
                self.entity_forecast_energy_remaining_today
            )
            energy_remaining_today = self.home_assistant.parse_energy(
                state_forecast_energy_remaining_today,
                self.unit_forecast_energy_remaining_today,
                self.entity_forecast_energy_remaining_today or "N/A",
            )
        else:
            energy_remaining_today = None

        # Check if essential values are missing
        if energy_today is None and self.entity_forecast_energy_today:
            if self.logger:
                self.logger.error(
                    f"Missing critical value: Solar Production (Entity: {self.entity_forecast_energy_today})"
                )
            has_critical_error = True
        if energy_tomorrow is None and self.entity_forecast_energy_tomorrow:
            if self.logger:
                self.logger.error(
                    f"Missing critical value: Solar Production (Entity: {self.entity_forecast_energy_tomorrow})"
                )
            has_critical_error = True

        # Add here other checks for critical values as needed

        if has_critical_error:
            if self.logger:
                self.logger.error(
                    "Failed to retrieve one or more critical energy values "
                    "from Home Assistant. Cannot create forecast data."
                )
            return None

        now = Timestamp(datetime.now())
        actual_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        end_of_today = datetime.combine(now, time.max)

        forecast: Forecast = Forecast(timestamp=Timestamp(now))

        # Create forecast intervals
        forecast_interval_actual_h = ForecastInterval(
            start=Timestamp(actual_hour),
            end=Timestamp(actual_hour),
            energy=WattHours(energy_actual_h) if energy_actual_h else None,
            energy_remaining=None,
            power_points=[],
        )
        forecast_interval_1h = ForecastInterval(
            start=Timestamp(actual_hour),
            end=Timestamp(actual_hour + timedelta(hours=1)),
            energy=WattHours(energy_next_1h) if energy_next_1h else None,
            energy_remaining=None,
            power_points=[],
        )
        forecast_interval_12h = ForecastInterval(
            start=Timestamp(actual_hour),
            end=Timestamp(actual_hour + timedelta(hours=12)),
            energy=None,
            energy_remaining=None,
            power_points=[],
        )
        forecast_interval_24h = ForecastInterval(
            start=Timestamp(actual_hour),
            end=Timestamp(actual_hour + timedelta(hours=24)),
            energy=None,
            energy_remaining=None,
            power_points=[],
        )
        forecast_interval_today = ForecastInterval(
            start=Timestamp(actual_hour),
            end=Timestamp(end_of_today),
            energy=WattHours(energy_today) if energy_today else None,
            energy_remaining=WattHours(energy_remaining_today) if energy_remaining_today else None,
            power_points=[],
        )
        forecast_interval_tomorrow = ForecastInterval(
            start=Timestamp(end_of_today + timedelta(seconds=1)),
            end=Timestamp(end_of_today + timedelta(days=1)),
            energy=WattHours(energy_tomorrow) if energy_tomorrow else None,
            energy_remaining=None,
            power_points=[],
        )

        # Add power data
        if power_actual_h is not None:
            forecast_interval_actual_h.power_points.append(
                ForecastPowerPoint(
                    timestamp=Timestamp(actual_hour),
                    power=Watts(power_actual_h),
                )
            )
        if power_next_1h is not None:
            forecast_interval_1h.power_points.append(
                ForecastPowerPoint(
                    timestamp=Timestamp(actual_hour + timedelta(hours=1)),
                    power=Watts(power_next_1h),
                )
            )
        if power_next_12h is not None:
            forecast_interval_12h.power_points.append(
                ForecastPowerPoint(
                    timestamp=Timestamp(actual_hour + timedelta(hours=12)),
                    power=Watts(power_next_12h),
                )
            )
        if power_next_24h is not None:
            forecast_interval_24h.power_points.append(
                ForecastPowerPoint(
                    timestamp=Timestamp(actual_hour + timedelta(hours=24)),
                    power=Watts(power_next_24h),
                )
            )

        forecast_intervals: List[ForecastInterval] = [
            forecast_interval_actual_h,
            forecast_interval_1h,
            forecast_interval_12h,
            forecast_interval_24h,
            forecast_interval_today,
            forecast_interval_tomorrow,
        ]

        # Add intervals to forecast if they contain data
        for interval in forecast_intervals:
            if interval.power_points or interval.energy is not None or interval.energy_remaining is not None:
                forecast.intervals.append(interval)

        if self.logger:
            self.logger.debug(f"HA Monitor: Forecast Intervals fetched: {forecast.intervals}")

        return forecast
