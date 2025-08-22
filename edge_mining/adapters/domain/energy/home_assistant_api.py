"""
Home Assistant API adapter (Implementation of Port)
for the energy provisioning of Edge Mining Application using the Home Assistant API
"""

from datetime import datetime
from typing import Optional, cast

from edge_mining.adapters.infrastructure.homeassistant.homeassistant_api import (
    ServiceHomeAssistantAPI,
)
from edge_mining.domain.common import Timestamp, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.domain.energy.entities import EnergySource
from edge_mining.domain.energy.exceptions import (
    EnergyMonitorConfigurationError,
    EnergyMonitorError,
)
from edge_mining.domain.energy.ports import EnergyMonitorPort
from edge_mining.domain.energy.value_objects import (
    BatteryState,
    EnergyStateSnapshot,
    GridState,
    LoadState,
)
from edge_mining.shared.adapter_configs.energy import EnergyMonitorHomeAssistantConfig
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.config import Configuration
from edge_mining.shared.interfaces.factories import EnergyMonitorAdapterFactory
from edge_mining.shared.logging.port import LoggerPort


class HomeAssistantAPIEnergyMonitorFactory(EnergyMonitorAdapterFactory):
    """
    Creates a factory for HomeAssistantAPI energy monitor adapter.

    This factory aims to simplifying the building of HomeAssistantAPI.
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
    ) -> EnergyMonitorPort:
        """Create an energy monitor adapter"""

        # Needs to have the Home Assistant API service as external_service
        if not external_service:
            raise EnergyMonitorError("HomeAssistantAPI Service is required for HomeAssistantAPI energy monitor.")

        if not external_service.external_service_type == ExternalServiceAdapter.HOME_ASSISTANT_API:
            raise EnergyMonitorError("External service must be of type HomeAssistantAPI")

        if not isinstance(config, EnergyMonitorHomeAssistantConfig):
            raise EnergyMonitorConfigurationError(
                "Invalid configuration type for HomeAssistantAPI energy monitor. "
                "Expected EnergyMonitorHomeAssistantConfig."
            )

        # Get the config from the energy monitor config
        energy_monitor_config: EnergyMonitorHomeAssistantConfig = config

        service_home_assistant_api = cast(ServiceHomeAssistantAPI, external_service)

        # Use builder pattern to create the adapter, in this way
        # we can easily add more configuration options in the future
        # based on the config provided by the user.
        builder = HomeAssistantAPIEnergyMonitorBuilder(home_assistant=service_home_assistant_api, logger=logger)

        # --- Production ---
        if energy_monitor_config.entity_production:
            if energy_monitor_config.unit_production:
                builder.set_production_entity(
                    entity_id=energy_monitor_config.entity_production,
                    unit=energy_monitor_config.unit_production,
                )
            else:
                builder.set_production_entity(entity_id=energy_monitor_config.entity_production)

        # --- Consumption ---
        if energy_monitor_config.entity_consumption:
            if energy_monitor_config.unit_consumption:
                builder.set_consumption_entity(
                    entity_id=energy_monitor_config.entity_consumption,
                    unit=energy_monitor_config.unit_consumption,
                )
            else:
                builder.set_consumption_entity(entity_id=energy_monitor_config.entity_consumption)

        # --- Grid ---
        if energy_monitor_config.entity_grid:
            if energy_monitor_config.unit_grid:
                builder.set_grid_entity(
                    entity_id=energy_monitor_config.entity_grid,
                    unit=energy_monitor_config.unit_grid,
                    positive_export=energy_monitor_config.grid_positive_export,
                )
            else:
                builder.set_grid_entity(entity_id=energy_monitor_config.entity_grid)

        # --- Battery ---
        if energy_monitor_config.entity_battery_soc and energy_monitor_config.entity_battery_power:
            if energy_monitor_config.unit_battery_power:
                builder.set_battery_entities(
                    soc_entity_id=energy_monitor_config.entity_battery_soc,
                    power_entity_id=energy_monitor_config.entity_battery_power,
                    power_unit=energy_monitor_config.unit_battery_power,
                )
            else:
                builder.set_battery_entities(
                    soc_entity_id=energy_monitor_config.entity_battery_soc,
                    power_entity_id=energy_monitor_config.entity_battery_power,
                )
        # --- Battery Remaining Capacity ---
        if energy_monitor_config.entity_battery_remaining_capacity:
            if energy_monitor_config.unit_battery_remaining_capacity:
                builder.set_battery_remaining_capacity_entity(
                    entity_id=energy_monitor_config.entity_battery_remaining_capacity,
                    unit=energy_monitor_config.unit_battery_remaining_capacity,
                )
            else:
                builder.set_battery_remaining_capacity_entity(
                    entity_id=energy_monitor_config.entity_battery_remaining_capacity
                )

        # --- Build the adapter ---
        return builder.build()


class HomeAssistantAPIEnergyMonitorBuilder:
    """Builder class for constructing HomeAssistantAPIEnergyMonitor instances."""

    def __init__(self, home_assistant: ServiceHomeAssistantAPI, logger: Optional[LoggerPort]):
        self.home_assistant: ServiceHomeAssistantAPI = home_assistant
        self.logger: Optional[LoggerPort] = logger
        self.entity_production: Optional[str] = None
        self.entity_consumption: Optional[str] = None
        self.entity_grid: Optional[str] = None
        self.entity_battery_soc: Optional[str] = None
        self.entity_battery_power: Optional[str] = None
        self.entity_battery_remaining_capacity: Optional[str] = None
        self.unit_production: str = "W"
        self.unit_consumption: str = "W"
        self.unit_grid: str = "W"
        self.unit_battery_power: str = "W"
        self.unit_battery_remaining_capacity: str = "Wh"
        self.grid_positive_export: bool = False
        self.battery_positive_charge: bool = True

    def set_production_entity(self, entity_id: str, unit: str = "W") -> "HomeAssistantAPIEnergyMonitorBuilder":
        """Set entity for monitoring the production"""
        self.entity_production = entity_id
        self.unit_production = unit.lower()
        return self

    def set_consumption_entity(self, entity_id: str, unit: str = "W") -> "HomeAssistantAPIEnergyMonitorBuilder":
        """Set entity for monitoring the consumption"""
        self.entity_consumption = entity_id
        self.unit_consumption = unit.lower()
        return self

    def set_grid_entity(
        self, entity_id: str, unit: str = "W", positive_export: bool = False
    ) -> "HomeAssistantAPIEnergyMonitorBuilder":
        """Set entity for monitoring the grid"""
        self.entity_grid = entity_id
        self.unit_grid = unit.lower()
        self.grid_positive_export = positive_export
        return self

    def set_battery_entities(
        self,
        soc_entity_id: str,
        power_entity_id: str,
        power_unit: str = "W",
        positive_charge: bool = True,
    ) -> "HomeAssistantAPIEnergyMonitorBuilder":
        """Set entities for monitoring the battery"""
        self.entity_battery_soc = soc_entity_id
        self.entity_battery_power = power_entity_id

        self.unit_battery_power = power_unit.lower()
        self.battery_positive_charge = positive_charge

        return self

    def set_battery_remaining_capacity_entity(
        self, entity_id: str, unit: str = "Wh"
    ) -> "HomeAssistantAPIEnergyMonitorBuilder":
        """Set entity for monitoring the battery remaining capacity"""
        self.entity_battery_remaining_capacity = entity_id
        self.unit_battery_remaining_capacity = unit.lower()
        return self

    def build(self) -> "HomeAssistantAPIEnergyMonitor":
        """Build and validate the HomeAssistantAPIEnergyMonitor instance."""

        if not self.entity_consumption:
            raise EnergyMonitorError("Consumption entity is required")

        if self.entity_battery_soc and not self.entity_battery_power:
            raise EnergyMonitorError("Battery power entity is required when battery SOC is configured")

        monitor = HomeAssistantAPIEnergyMonitor(
            home_assistant=self.home_assistant,
            logger=self.logger,
            entity_production=self.entity_production,
            entity_consumption=self.entity_consumption,
            entity_grid=self.entity_grid,
            entity_battery_soc=self.entity_battery_soc,
            entity_battery_power=self.entity_battery_power,
            entity_battery_remaining_capacity=self.entity_battery_remaining_capacity,
            unit_production=self.unit_production,
            unit_consumption=self.unit_consumption,
            unit_grid=self.unit_grid,
            unit_battery_power=self.unit_battery_power,
            unit_battery_remaining_capacity=self.unit_battery_remaining_capacity,
            grid_positive_export=self.grid_positive_export,
            battery_positive_charge=self.battery_positive_charge,
        )

        return monitor


class HomeAssistantAPIEnergyMonitor(EnergyMonitorPort):
    """
    Fetches energy data from a Home Assistant instance via its REST API.

    Requires careful configuration of entity IDs.
    Make sure the House Consumption entity EXCLUDES the consumption of miners,
    possibly using a template sensor in Home Assistant.
    """

    def __init__(
        self,
        home_assistant: ServiceHomeAssistantAPI,
        logger: Optional[LoggerPort],
        entity_production: Optional[str],
        entity_consumption: Optional[str],
        entity_grid: Optional[str],
        entity_battery_soc: Optional[str],
        entity_battery_power: Optional[str],
        entity_battery_remaining_capacity: Optional[str],
        unit_production: str = "W",
        unit_consumption: str = "W",
        unit_grid: str = "W",
        unit_battery_power: str = "W",
        unit_battery_remaining_capacity: str = "Wh",
        grid_positive_export: bool = False,
        battery_positive_charge: bool = True,
    ):
        super().__init__(energy_monitor_type=EnergyMonitorAdapter.HOME_ASSISTANT_API)

        # Initialize the HomeAssistant API Service
        self.home_assistant = home_assistant
        self.logger = logger

        self.entity_production = entity_production
        self.entity_consumption = entity_consumption
        self.entity_grid = entity_grid
        self.entity_battery_soc = entity_battery_soc
        self.entity_battery_power = entity_battery_power
        self.entity_battery_remaining_capacity = entity_battery_remaining_capacity
        self.unit_production = unit_production.lower()
        self.unit_consumption = unit_consumption.lower()
        self.unit_grid = unit_grid.lower()
        self.unit_battery_power = unit_battery_power.lower()
        self.unit_battery_remaining_capacity = unit_battery_remaining_capacity.lower()
        self.grid_positive_export = grid_positive_export
        self.battery_positive_charge = battery_positive_charge

        self._log_configuration()

    def _log_configuration(self):
        """Log the current configuration of the monitor."""
        if self.logger:
            self.logger.debug(
                f"Entities Configured: "
                f"Production='{self.entity_production}', "
                f"Consumption='{self.entity_consumption}', "
                f"Grid='{self.entity_grid}', "
                f"BatterySOC='{self.entity_battery_soc}', "
                f"BatteryPower='{self.entity_battery_power}', "
                f"BatteryRemaining='{self.entity_battery_remaining_capacity}'"
            )
            self.logger.debug(
                f"Units: "
                f"Production='{self.unit_production}', "
                f"Consumption='{self.unit_consumption}', "
                f"Grid='{self.unit_grid}', "
                f"BatteryPower='{self.unit_battery_power}', "
                f"BatteryRemaining='{self.unit_battery_remaining_capacity}'"
            )
            self.logger.debug(
                f"Conventions: "
                f"Grid Positive Export='{self.grid_positive_export}', "
                f"Battery Positive Charge='{self.battery_positive_charge}'"
            )

    def get_current_energy_state(self) -> Optional[EnergyStateSnapshot]:
        if self.logger:
            self.logger.debug("Fetching current energy state from Home Assistant...")
        now = Timestamp(datetime.now())
        has_critical_error = False

        # --- Production ---
        if self.entity_production:
            state_production, _ = self.home_assistant.get_entity_state(self.entity_production)
            production_watts = self.home_assistant.parse_power(
                state_production,
                self.unit_production,
                self.entity_production or "N/A",
            )
        else:
            production_watts = None

        # --- Consumption ---
        if self.entity_consumption:
            state_consumption, _ = self.home_assistant.get_entity_state(self.entity_consumption)
            consumption_watts = self.home_assistant.parse_power(
                state_consumption,
                self.unit_consumption,
                self.entity_consumption or "N/A",
            )
        else:
            consumption_watts = None

        # --- Grid ---
        if self.entity_grid:
            state_grid, _ = self.home_assistant.get_entity_state(self.entity_grid)
            grid_watts_raw = self.home_assistant.parse_power(state_grid, self.unit_grid, self.entity_grid or "N/A")
        else:
            grid_watts_raw = None

        # --- Battery ---
        if self.entity_battery_soc and self.entity_battery_power:
            state_battery_soc, _ = self.home_assistant.get_entity_state(self.entity_battery_soc)
            state_battery_power, _ = self.home_assistant.get_entity_state(self.entity_battery_power)
            battery_soc = self.home_assistant.parse_percentage(state_battery_soc, self.entity_battery_soc or "N/A")
            battery_power_raw = self.home_assistant.parse_power(
                state_battery_power,
                self.unit_battery_power,
                self.entity_battery_power or "N/A",
            )
        else:
            battery_soc = None
            battery_power_raw = None

        if self.entity_battery_remaining_capacity:
            state_battery_remaining_capacity, _ = self.home_assistant.get_entity_state(
                self.entity_battery_remaining_capacity
            )
            battery_remaining_capacity = self.home_assistant.parse_energy(
                state_battery_remaining_capacity,
                self.unit_battery_remaining_capacity,
                self.entity_battery_remaining_capacity or "N/A",
            )
        else:
            battery_remaining_capacity = None

        # --- Apply Conventions ---
        # Grid: We want positive for IMPORTING, negative for EXPORTING
        if grid_watts_raw is not None:
            grid_watts = -grid_watts_raw if self.grid_positive_export else grid_watts_raw
        else:
            grid_watts = None
            if self.entity_grid:
                has_critical_error = True  # Grid is usually important

        # Battery: We want positive for CHARGING, negative for DISCHARGING
        if battery_power_raw is not None:
            battery_power = battery_power_raw if self.battery_positive_charge else -battery_power_raw
        else:
            battery_power = None
            # Only critical if battery SOC is also configured
            if self.entity_battery_soc and self.entity_battery_power:
                has_critical_error = True

        # Check if essential values are missing
        if production_watts is None and self.entity_production:
            if self.logger:
                self.logger.error(f"Missing critical value: Production (Entity: {self.entity_production})")
            has_critical_error = True
        if consumption_watts is None and self.entity_consumption:
            if self.logger:
                self.logger.error(f"Missing critical value: House Consumption (Entity: {self.entity_consumption})")
            has_critical_error = True

        if has_critical_error:
            if self.logger:
                self.logger.error(
                    "Failed to retrieve one or more critical energy values from Home Assistant. Cannot create snapshot."
                )
            return None

        reading_timestamp = now

        # Fill defaults if entities weren't configured
        production_watts = production_watts if production_watts is not None else Watts(0.0)
        consumption_watts = consumption_watts if consumption_watts is not None else Watts(0.0)

        consumption_state = LoadState(current_power=consumption_watts, timestamp=reading_timestamp)

        # Create GridState if relevant entities are available
        grid_state: Optional[GridState] = None
        if grid_watts is not None:
            grid_state = GridState(current_power=Watts(grid_watts), timestamp=reading_timestamp)

        # Construct BatteryState if relevant entities are available
        battery_state: Optional[BatteryState] = None
        if battery_soc is not None and battery_power is not None:
            battery_state = BatteryState(
                state_of_charge=battery_soc,
                remaining_capacity=battery_remaining_capacity,
                current_power=Watts(battery_power),
                timestamp=reading_timestamp,
            )
        elif self.entity_battery_soc:  # Log if configured but data missing
            if self.logger:
                self.logger.warning(
                    "Battery SOC entity configured, but could not create full BatteryState (missing power or SOC?)."
                )

        snapshot = EnergyStateSnapshot(
            production=production_watts,
            consumption=consumption_state,
            battery=battery_state,
            grid=grid_state,
            external_source=None,  # TODO: Add external source
            timestamp=reading_timestamp,
        )

        if self.logger:
            self.logger.info(
                f"HA Monitor: Energy State fetched: Prod={snapshot.production:.0f}W, "
                f"Cons={snapshot.consumption.current_power:.0f}W, "
                f"Grid={snapshot.grid.current_power if snapshot.grid else 'N/A'}W, "
                f"SOC={snapshot.battery.state_of_charge if snapshot.battery else 'N/A'}%, "
                f"BattPwr={snapshot.battery.current_power if snapshot.battery else 'N/A'}W"
            )

        return snapshot
