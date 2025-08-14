"""Dummy adapter (Implementation of Port) that simulates the energy provisioning of Edge Mining Application"""

from datetime import datetime
from typing import Optional
import random

from edge_mining.domain.energy.ports import EnergyMonitorPort
from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.domain.common import Watts, Percentage, WattHours
from edge_mining.domain.energy.value_objects import EnergyStateSnapshot, BatteryState

class DummyEnergyMonitor(EnergyMonitorPort):
    """Generates plausible fake energy data."""
    def __init__(self, has_battery: bool = True, battery_capacity_wh: float = 10000):
        super().__init__(energy_monitor_type=EnergyMonitorAdapter.DUMMY)
        self.has_battery = has_battery
        self.battery_capacity = WattHours(battery_capacity_wh)
        self.current_soc = Percentage(random.uniform(40.0, 90.0)) # Start with random SOC

    def get_current_energy_state(self) -> Optional[EnergyStateSnapshot]:
        now = datetime.now()
        hour = now.hour

        # Simulate solar production (simple sinusoidal based on hour)
        if 6 < hour < 20:
            # Peak around 1 PM (hour 13)
            solar_factor = max(0, 1 - abs(hour - 13) / 7)
            production = Watts(random.uniform(500, 4000) * solar_factor)
        else:
            production = Watts(0.0)

        # Simulate base consumption
        consumption = Watts(random.uniform(150, 600))

        battery_state = None
        grid_power = Watts(0.0)

        if self.has_battery:
            # Simple battery logic: charge if surplus, discharge if deficit
            net_power = production - consumption
            battery_power = Watts(0.0)

            if net_power > 0 and self.current_soc < 100.0: # Charging
                charge_power = min(net_power, Watts(3000)) # Limit charge power
                self.current_soc = min(100.0, self.current_soc + (charge_power / self.battery_capacity * 100 / 60)) # Wh adjustment per minute approx
                battery_power = charge_power
                grid_power = net_power - charge_power # Export excess
            elif net_power < 0 and self.current_soc > 20.0: # Discharging (with buffer)
                discharge_power = min(abs(net_power), Watts(3000)) # Limit discharge power
                self.current_soc = max(0.0, self.current_soc - (discharge_power / self.battery_capacity * 100 / 60))
                battery_power = -discharge_power
                grid_power = net_power - battery_power # Import remaining deficit
            else: # Idle or full/empty
                grid_power = net_power # Import/export directly

            battery_state = BatteryState(
                state_of_charge=Percentage(self.current_soc),
                nominal_capacity=self.battery_capacity,
                current_power=battery_power, # Positive charging, negative discharging
                timestamp=now
            )
        else:
            # No battery: grid takes all difference
            grid_power = production - consumption

        snapshot = EnergyStateSnapshot(
            production=production,
            consumption=consumption,
            battery=battery_state,
            grid=grid_power,
            timestamp=now
        )
        print(f"DummyMonitor: Generated state: Prod={production:.0f}W, Cons={consumption:.0f}W, Grid={grid_power:.0f}W, SOC={self.current_soc:.1f}%")
        return snapshot
