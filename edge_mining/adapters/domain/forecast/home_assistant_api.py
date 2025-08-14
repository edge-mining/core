"""Home Assistant API adapter (Implementation of Port) for the energy forecast of Edge Mining Application"""

from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

from edge_mining.domain.forecast.ports import ForecastProviderPort
from edge_mining.shared.logging.port import LoggerPort
from edge_mining.domain.common import Watts, WattHours, Timestamp
from edge_mining.domain.forecast.value_objects import ForecastData

from edge_mining.adapters.infrastructure.homeassistant.homeassistant_api import ServiceHomeAssistantAPI

class HomeAssistantForecastProvider(ForecastProviderPort):
    """
    Fetches energy forecast from a Home Assistant instance via its REST API.

    Requires careful configuration of entity IDs in the .env file.
    """
    def __init__(
        self,
        home_assistant: ServiceHomeAssistantAPI,
        entity_solar_forecast_power_actual_h: Optional[str],
        entity_solar_forecast_power_next_1h: Optional[str],
        entity_solar_forecast_power_next_12h: Optional[str],
        entity_solar_forecast_power_next_24h: Optional[str],
        entity_solar_forecast_energy_actual_h: Optional[str],
        entity_solar_forecast_energy_next_1h: Optional[str],
        entity_solar_forecast_energy_next_24h: Optional[str],
        entity_solar_forecast_energy_remaining_today: Optional[str],
        unit_solar_forecast_power_actual_h: str = "W",
        unit_solar_forecast_power_next_1h: str = "W",
        unit_solar_forecast_power_next_12h: str = "W",
        unit_solar_forecast_power_next_24h: str = "W",
        unit_solar_forecast_energy_actual_h: str = "kWh",
        unit_solar_forecast_energy_next_1h: str = "kWh",
        unit_solar_forecast_energy_next_24h: str = "kWh",
        unit_solar_forecast_energy_remaining_today: str = "kWh",
        logger: LoggerPort = None
    ):
        # Initialize the HomeAssistant API Service
        self.home_assistant = home_assistant
        self.logger = logger

        self.entity_solar_forecast_power_actual_h = entity_solar_forecast_power_actual_h
        self.entity_solar_forecast_power_next_1h = entity_solar_forecast_power_next_1h
        self.entity_solar_forecast_power_next_12h = entity_solar_forecast_power_next_12h
        self.entity_solar_forecast_power_next_24h = entity_solar_forecast_power_next_24h
        self.entity_solar_forecast_energy_actual_h = entity_solar_forecast_energy_actual_h
        self.entity_solar_forecast_energy_next_1h = entity_solar_forecast_energy_next_1h
        self.entity_solar_forecast_energy_next_24h = entity_solar_forecast_energy_next_24h
        self.entity_solar_forecast_energy_remaining_today = entity_solar_forecast_energy_remaining_today
        self.unit_solar_forecast_power_actual_h = unit_solar_forecast_power_actual_h.lower()
        self.unit_solar_forecast_power_next_1h = unit_solar_forecast_power_next_1h.lower()
        self.unit_solar_forecast_power_next_12h = unit_solar_forecast_power_next_12h.lower()
        self.unit_solar_forecast_power_next_24h = unit_solar_forecast_power_next_24h.lower()
        self.unit_solar_forecast_energy_actual_h = unit_solar_forecast_energy_actual_h.lower()
        self.unit_solar_forecast_energy_next_1h = unit_solar_forecast_energy_next_1h.lower()
        self.unit_solar_forecast_energy_next_24h = unit_solar_forecast_energy_next_24h.lower()
        self.unit_solar_forecast_energy_remaining_today = unit_solar_forecast_energy_remaining_today.lower()

        self.logger.debug(f"Entities Configured for Power:"
                    f"Actual='{entity_solar_forecast_power_actual_h}', Next 1h='{entity_solar_forecast_power_next_1h}', "
                    f"Next 12h='{entity_solar_forecast_power_next_12h}', Next 24h='{entity_solar_forecast_power_next_24h}'")
        self.logger.debug(f"Entities Configured for Energy:"
                    f"Actual='{entity_solar_forecast_energy_actual_h}', Next 1h='{entity_solar_forecast_energy_next_1h}', "
                    f"Next 24h='{entity_solar_forecast_energy_next_24h}', Remaining='{entity_solar_forecast_energy_remaining_today}'")
        
        self.logger.debug(f"Units for Power:"
                    f"Actual='{unit_solar_forecast_power_actual_h}', Next 1h='{unit_solar_forecast_power_next_1h}', "
                    f"Next 12h='{unit_solar_forecast_power_next_12h}', Next 24h='{unit_solar_forecast_power_next_24h}'")
        self.logger.debug(f"Units Configured for Energy:"
                    f"Actual='{unit_solar_forecast_energy_actual_h}', Next 1h='{unit_solar_forecast_energy_next_1h}', "
                    f"Next 24h='{unit_solar_forecast_energy_next_24h}', Remaining='{unit_solar_forecast_energy_remaining_today}'")

    def get_solar_forecast(self) -> Optional[ForecastData]:
        """Fetches the solar energy production forecast."""
        self.logger.debug("Fetching solar forecast energy state from Home Assistant...")
        now = Timestamp(datetime.now())
        has_critical_error = False

        # Fetch states from Home Assistant
        state_solar_forecast_power_actual_h, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_power_actual_h)
        state_solar_forecast_power_next_1h, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_power_next_1h)
        state_solar_forecast_power_next_12h, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_power_next_12h)
        state_solar_forecast_power_next_24h, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_power_next_24h)
        state_solar_forecast_energy_actual_h, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_energy_actual_h)
        state_solar_forecast_energy_next_1h, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_energy_next_1h)
        state_solar_forecast_energy_next_24h, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_energy_next_24h)
        state_solar_forecast_energy_remaining_today, _ = self.home_assistant.get_entity_state(self.entity_solar_forecast_energy_remaining_today)

        # Parse values, converting units and handling errors
        power_actual_h = self.home_assistant.parse_power(state_solar_forecast_power_actual_h, self.unit_solar_forecast_power_actual_h, self.entity_solar_forecast_power_actual_h or "N/A")
        power_next_1h = self.home_assistant.parse_power(state_solar_forecast_power_next_1h, self.unit_solar_forecast_power_next_1h, self.entity_solar_forecast_power_next_1h or "N/A")
        power_next_12h = self.home_assistant.parse_power(state_solar_forecast_power_next_12h, self.unit_solar_forecast_power_next_12h, self.entity_solar_forecast_power_next_12h or "N/A")
        power_next_24h = self.home_assistant.parse_power(state_solar_forecast_power_next_24h, self.unit_solar_forecast_power_next_24h, self.entity_solar_forecast_power_next_24h or "N/A")
        energy_actual_h = self.home_assistant.parse_energy(state_solar_forecast_energy_actual_h, self.unit_solar_forecast_energy_actual_h, self.entity_solar_forecast_energy_actual_h or "N/A")
        energy_next_1h = self.home_assistant.parse_energy(state_solar_forecast_energy_next_1h, self.unit_solar_forecast_energy_next_1h, self.entity_solar_forecast_energy_next_1h or "N/A")
        energy_next_24h = self.home_assistant.parse_energy(state_solar_forecast_energy_next_24h, self.unit_solar_forecast_energy_next_24h, self.entity_solar_forecast_energy_next_24h or "N/A")
        energy_remaining_today = self.home_assistant.parse_energy(state_solar_forecast_energy_remaining_today, self.unit_solar_forecast_energy_remaining_today, self.entity_solar_forecast_energy_remaining_today or "N/A")

        # Check if essential values are missing
        if energy_next_24h is None and self.entity_solar_forecast_energy_next_24h:
            self.logger.error(f"Missing critical value: Solar Production (Entity: {self.entity_solar_forecast_energy_next_24h})")
            has_critical_error = True

        # Add here other checks for critical values as needed

        if has_critical_error:
            self.logger.error("Failed to retrieve one or more critical energy values from Home Assistant. Cannot create forecast data.")
            return None

        now = datetime.now()

        # Add power data
        power_predictions: Dict[Timestamp, Watts] = {}

        if power_actual_h is not None:
            power_predictions[(now, now + timedelta(hours=0))] = power_actual_h
        if power_next_1h is not None:
            power_predictions[(now, now + timedelta(hours=1))] = power_next_1h
        if power_next_12h is not None:    
            power_predictions[(now, now + timedelta(hours=12))] = power_next_12h
        if power_next_24h is not None:
            power_predictions[(now, now + timedelta(hours=24))] = power_next_24h

        # Add energy data
        energy_predictions: Dict[Tuple[Timestamp, Timestamp], WattHours] = {}

        if energy_actual_h is not None:
            energy_predictions[(now, now + timedelta(hours=0))] = energy_actual_h
        if energy_next_1h is not None:
            energy_predictions[(now, now + timedelta(hours=1))] = energy_next_1h
        if energy_remaining_today is not None:
            energy_predictions[(now, now + timedelta(hours=24))] = energy_remaining_today

        energy_predictions[(now, now + timedelta(hours=24))] = energy_next_24h

        forecast = ForecastData(
            predicted_energy=energy_predictions,
            predicted_power=power_predictions,
            generated_at=now
        )

        self.logger.info(f"HA Monitor: Forecast Power State fetched: {forecast.predicted_power}")
        self.logger.info(f"HA Monitor: Forecast Energy State fetched: {forecast.predicted_energy}")

        return forecast
