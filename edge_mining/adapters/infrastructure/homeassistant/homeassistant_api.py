"""
The Home Assistant API Infrastructure External Service Adapter

The REST API for Home Assistant has been superseded by the websocket API.
I use it only for simplicity, in the future I plan to switch to websocket API

https://github.com/home-assistant/architecture/discussions/1074#discussioncomment-9196867

and

https://github.com/home-assistant/developers.home-assistant/pull/2150
"""

import math  # For isnan
from typing import Optional, Tuple

from homeassistant_api import Client

from edge_mining.domain.common import Percentage, WattHours, Watts
from edge_mining.shared.adapter_configs.external_services import (
    ExternalServiceHomeAssistantConfig,
)
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.exceptions import (
    ExternalServiceConfigurationError,
    ExternalServiceError,
)
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.config import ExternalServiceConfig
from edge_mining.shared.interfaces.factories import ExternalServiceFactory
from edge_mining.shared.logging.port import LoggerPort


class ServiceHomeAssistantAPI(ExternalServicePort):
    """
    Use Home Assistant instance via its REST API as external service.

    Requires careful configuration of HA parameters in the .env file.
    """

    def __init__(self, api_url: str, token: str, logger: Optional[LoggerPort]):
        super().__init__(external_service_type=ExternalServiceAdapter.HOME_ASSISTANT_API)
        self.logger = logger

        if not api_url or not token:
            raise ValueError("Home Assistant URL and Token are required.")

        self.api_url = f"{api_url}/api"
        self.token = token

        self.client: Optional[Client] = None

        self.connect()  # Connect to the API during initialization

    def connect(self) -> None:
        """Connect to the Home Assistant API."""
        if self.logger:
            self.logger.info(f"Initializing HomeAssistantAPI for {self.api_url}")

        # Initialize Home Assistant client
        try:
            self.client = Client(self.api_url, self.token)

            # Test connection during initialization (optional but recommended)
            self.client.get_config()
            if self.logger:
                self.logger.info("Successfully connected to Home Assistant API.")
        except Exception as e:
            if self.logger:
                self.logger.error(f"An unexpected error occurred connecting to Home Assistant: {e}")
            raise ConnectionError(f"Unexpected error connecting to Home Assistant: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from the Home Assistant API."""
        if self.logger:
            self.logger.info("Disconnecting from Home Assistant API.")

        # The Client does not have a disconnect method, but we can clear the client
        self.client = None

    def get_entity_state(self, entity_id: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Safely retrieves the state and unit of an entity."""
        if not entity_id:
            return None, None
        if not self.client:
            if self.logger:
                self.logger.error("Home Assistant client is not initialized.")
            return None, None
        try:
            entity = self.client.get_entity(entity_id=entity_id)
            if not entity:
                if self.logger:
                    self.logger.warning(f"Home Assistant entity '{entity_id}' not found.")
                return None, None
            # Check if state is unavailable or unknown
            state = entity.state.state  # The actual value as a string
            if state is None or state.lower() in ["unavailable", "unknown"]:
                if self.logger:
                    self.logger.warning(f"Home Assistant entity '{entity_id}' is unavailable or unknown.")
                return None, None

            unit = entity.state.attributes.get("unit_of_measurement")
            if self.logger:
                self.logger.debug(f"Fetched HA entity '{entity_id}': State='{state}', Unit='{unit}'")
            return state, unit
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error getting Home Assistant entity '{entity_id}': {e}")
            return None, None

    def parse_power(
        self,
        state: Optional[str],
        configured_unit: str,
        entity_id_for_log: str,
    ) -> Optional[Watts]:
        """Parses state string to Watts, handling units (W/kW) and errors."""
        if state is None:
            return None
        try:
            value = float(state)
            if math.isnan(value):
                if self.logger:
                    self.logger.warning(
                        f"Parsed NaN value for entity '{entity_id_for_log}', state='{state}'. Treating as missing."
                    )
                return None
            if configured_unit.lower() == "kw":
                value *= 1000  # Convert kW to W
            elif configured_unit.lower() != "w":
                if self.logger:
                    self.logger.warning(
                        f"Unsupported unit '{configured_unit}' "
                        f"configured for entity '{entity_id_for_log}'. "
                        f"Assuming Watts."
                    )

            return Watts(value)
        except (ValueError, TypeError) as e:
            if self.logger:
                self.logger.error(
                    f"Could not parse power value for entity '{entity_id_for_log}' from state='{state}': {e}"
                )
            return None

    def parse_energy(
        self,
        state: Optional[str],
        configured_unit: str,
        entity_id_for_log: str,
    ) -> Optional[WattHours]:
        """Parses state string to Watt Hours, handling units (Wh/kWh) and errors."""
        if state is None:
            return None
        try:
            value = float(state)
            if math.isnan(value):
                if self.logger:
                    self.logger.warning(
                        f"Parsed NaN value for entity '{entity_id_for_log}', state='{state}'. Treating as missing."
                    )
                return None
            if configured_unit.lower() == "kwh":
                value *= 1000  # Convert kWh to Wh
            elif configured_unit.lower() != "wh":
                if self.logger:
                    self.logger.warning(
                        f"Unsupported unit '{configured_unit}' "
                        f"configured for entity '{entity_id_for_log}'. "
                        f"Assuming WattHours."
                    )

            return WattHours(value)
        except (ValueError, TypeError) as e:
            if self.logger:
                self.logger.error(
                    f"Could not parse energy value for entity '{entity_id_for_log}' from state='{state}': {e}"
                )
            return None

    def parse_percentage(self, state: Optional[str], entity_id_for_log: str) -> Optional[Percentage]:
        """Parses state string to Percentage, handling errors."""
        if state is None:
            return None
        try:
            value = float(state)
            if math.isnan(value):
                if self.logger:
                    self.logger.warning(
                        f"Parsed NaN value for entity '{entity_id_for_log}', state='{state}'. Treating as missing."
                    )
                return None
            return Percentage(max(0.0, min(100.0, value)))  # Clamp between 0 and 100
        except (ValueError, TypeError) as e:
            if self.logger:
                self.logger.error(
                    f"Could not parse percentage value for entity '{entity_id_for_log}' from state='{state}': {e}"
                )
            return None


class ServiceHomeAssistantAPIFactory(ExternalServiceFactory):
    """
    Creates a factory for Home Assistant API External Service.

    This factory aims to simplifying the building of Home Assistant API.
    """

    def create(self, config: Optional[ExternalServiceConfig], logger: Optional[LoggerPort]) -> ExternalServicePort:
        """Create an Home Assistant API Service"""

        if not config:
            raise ExternalServiceConfigurationError("Configuration is required for Home Assistant API service.")

        if not isinstance(config, ExternalServiceHomeAssistantConfig):
            raise ExternalServiceError("Invalid configuration type for Home Assistant API service.")

        # Get the config from the external service config
        external_service_ha_config: ExternalServiceHomeAssistantConfig = config

        if external_service_ha_config.url is None:
            raise ExternalServiceConfigurationError("URL is required for Home Assistant API service.")

        if external_service_ha_config.token is None:
            raise ExternalServiceConfigurationError("Token is required for Home Assistant API service.")

        return ServiceHomeAssistantAPI(
            api_url=external_service_ha_config.url,
            token=external_service_ha_config.token,
            logger=logger,
        )
