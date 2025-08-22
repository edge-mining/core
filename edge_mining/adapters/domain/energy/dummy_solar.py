"""
Dummy adapter (Implementation of Port) that simulates
the energy provisioning of Edge Mining Application
"""

import random
from datetime import datetime
from typing import Optional

from edge_mining.domain.common import Percentage, WattHours, Watts, Timestamp
from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.domain.energy.entities import EnergySource
from edge_mining.domain.energy.ports import EnergyMonitorPort
from edge_mining.domain.energy.value_objects import (
    Battery,
    BatteryState,
    EnergyStateSnapshot,
    Grid,
    GridState,
    LoadState,
)
from edge_mining.shared.interfaces.config import Configuration
from edge_mining.shared.adapter_configs.energy import EnergyMonitorDummySolarConfig
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.factories import EnergyMonitorAdapterFactory
from edge_mining.shared.logging.port import LoggerPort


class DummySolarEnergyMonitor(EnergyMonitorPort):
    """Generates plausible fake energy data."""

    def __init__(
        self,
        nominal_max_power: Optional[Watts] = None,
        storage: Optional[Battery] = None,
        grid: Optional[Grid] = None,
        external_source: Optional[Watts] = None,
        max_consumption_power: Optional[Watts] = None,
        logger: Optional[LoggerPort] = None,
    ):
        super().__init__(energy_monitor_type=EnergyMonitorAdapter.DUMMY_SOLAR)
        self.logger = logger

        self.nominal_max_power = nominal_max_power if nominal_max_power else 5000
        self.storage = storage
        self.grid = grid
        self.external_source = external_source
        self.max_consumption_power = max_consumption_power if max_consumption_power else 3000

        # --- Storage ---
        self.current_soc = None
        self.remaining_capacity = WattHours(0.0)
        self.storage_max_charging_power = Watts(3000)
        self.storage_max_discharging_power = Watts(3000)

        if self.storage:
            self.current_soc = Percentage(random.uniform(40.0, 90.0))  # Start with random SOC
            self.remaining_capacity = WattHours(
                self.storage.nominal_capacity * (self.current_soc / 100.0)
            )  # Calculate remaining capacity

    def get_current_energy_state(self) -> Optional[EnergyStateSnapshot]:
        now = datetime.now()
        hour = now.hour

        # Simulate solar production (simple sinusoidal based on hour)
        if 6 < hour < 20:
            # Peak around 1 PM (hour 13)
            solar_factor = max(0, 1 - abs(hour - 13) / 7)
            production = Watts(random.uniform(500, self.nominal_max_power) * solar_factor)
        else:
            production = Watts(0.0)

        # Simulate base consumption
        consumption = LoadState(
            current_power=Watts(random.uniform(150, self.max_consumption_power)),
            timestamp=Timestamp(now),
        )

        battery_state = None
        grid_power = Watts(0.0)

        if self.storage:
            # Simple battery logic: charge if surplus, discharge if deficit
            net_power = production - consumption.current_power
            battery_power = Watts(0.0)

            if not self.current_soc:
                self.current_soc = Percentage(0.0)  # Default SOC if not set

            if net_power > 0 and self.current_soc < 100.0:  # Charging
                charge_power = min(net_power, self.storage_max_charging_power)  # Limit charge power
                current_soc = min(
                    100.0,
                    self.current_soc + (charge_power / self.storage.nominal_capacity * 100 / 60),
                )  # Wh adjustment per minute approx
                self.current_soc = Percentage(current_soc)
                self.remaining_capacity = WattHours(self.storage.nominal_capacity * (self.current_soc / 100.0))
                battery_power = Watts(charge_power)

                grid_power = Watts(net_power - charge_power)  # Export excess
            elif net_power < 0 and self.current_soc > 20.0:  # Discharging (with buffer)
                discharge_power = min(abs(net_power), self.storage_max_discharging_power)  # Limit discharge power
                current_soc = max(
                    0.0,
                    self.current_soc - (discharge_power / self.storage.nominal_capacity * 100 / 60),
                )
                self.current_soc = Percentage(current_soc)
                self.remaining_capacity = WattHours(self.storage.nominal_capacity * (self.current_soc / 100.0))
                battery_power = Watts(-discharge_power)

                grid_power = Watts(net_power - battery_power)  # Import remaining deficit
            else:  # Idle or full/empty
                grid_power = Watts(net_power)  # Import/export directly

            battery_state = BatteryState(
                state_of_charge=Percentage(self.current_soc),
                remaining_capacity=self.remaining_capacity,
                current_power=battery_power,  # Positive charging, negative discharging
                timestamp=Timestamp(now),
            )
        else:
            # No battery: grid takes all difference
            grid_power = Watts(production - consumption.current_power)

        # Default: the solar system is not connected to the grid (off-grid)
        grid_state: Optional[GridState] = None

        if self.grid:
            # The solar system is connected to the grid (on-grid)
            grid_state = GridState(current_power=grid_power, timestamp=Timestamp(now))

        snapshot = EnergyStateSnapshot(
            production=production,
            consumption=consumption,
            battery=battery_state,
            grid=grid_state,
            external_source=None,
            timestamp=Timestamp(now),
        )
        if self.logger:
            self.logger.debug(
                f"DummyMonitor: Generated state: Prod={production:.0f}W,"
                f"Cons={consumption.current_power:.0f}W,"
                f"Grid={grid_power:.0f}W, SOC={self.current_soc:.1f}%"
            )
        return snapshot


class DummySolarEnergyMonitorBuilder:
    """Builder class for constructing DummySolarEnergyMonitor instances."""

    def __init__(self, logger: Optional[LoggerPort]):
        self.logger: Optional[LoggerPort] = logger
        self.nominal_max_power: Optional[Watts] = None
        self.storage: Optional[Battery] = None
        self.grid: Optional[Grid] = None
        self.external_source: Optional[Watts] = None
        self.max_consumption_power: Optional[Watts] = None

    def set_nominal_max_power(self, nominal_max_power: Watts) -> "DummySolarEnergyMonitorBuilder":
        """Set nominal max inverter power."""
        self.nominal_max_power = nominal_max_power
        return self

    def set_max_consumption_power(self, max_consumption_power: Watts) -> "DummySolarEnergyMonitorBuilder":
        """Set max load consumption power."""
        self.max_consumption_power = max_consumption_power
        return self

    def has_external_source(self, external_source: Watts) -> "DummySolarEnergyMonitorBuilder":
        """Add an external source."""
        self.external_source = external_source
        return self

    def has_storage(self, storage: Battery) -> "DummySolarEnergyMonitorBuilder":
        """Add a battery."""
        self.storage = storage
        return self

    def on_grid(self, grid: Grid) -> "DummySolarEnergyMonitorBuilder":
        """Is an on-grid solar system."""
        self.grid = grid
        return self

    def build(self) -> DummySolarEnergyMonitor:
        """Build and validate the DummySolarEnergyMonitor instance."""

        monitor = DummySolarEnergyMonitor(
            nominal_max_power=self.nominal_max_power,
            storage=self.storage,
            grid=self.grid,
            external_source=self.external_source,
            max_consumption_power=self.max_consumption_power,
        )

        return monitor


class DummySolarEnergyMonitorFactory(EnergyMonitorAdapterFactory):
    """
    Creates a factory for Dummy Solar energy monitor adapter.

    This factory aims to simplifying the building of Dummy Solar.
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
        """Create an energy source adapter"""

        # Use builder pattern to create the adapter
        builder = DummySolarEnergyMonitorBuilder(logger=logger)

        if not isinstance(config, EnergyMonitorDummySolarConfig):
            raise ValueError(
                "Invalid configuration type for Dummy Solar energy monitor. Expected EnergyMonitorDummySolarConfig."
            )

        # Get the config from the energy monitor config
        energy_monitor_config: EnergyMonitorDummySolarConfig = config

        if energy_monitor_config.max_consumption_power:
            builder.set_max_consumption_power(energy_monitor_config.max_consumption_power)

        # if energy source has been set, we use it
        if self._energy_source:
            # If energy source has a nominal max power, we use it
            if self._energy_source.nominal_power_max:
                builder.set_nominal_max_power(self._energy_source.nominal_power_max)

            # If energy source has a battery connected, we expect to produce data for it
            if self._energy_source.storage:
                builder.has_storage(self._energy_source.storage)

            # If energy source is on grid, we expect to use it
            if self._energy_source.grid:
                builder.on_grid(self._energy_source.grid)

            # If energy source has an external source, we take it
            if self._energy_source.external_source:
                builder.has_external_source(self._energy_source.external_source)

        # --- Build the adapter ---
        return builder.build()
