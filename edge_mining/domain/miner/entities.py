"""Collection of Entities for the Mining Device Management domain of the Edge Mining application."""

from dataclasses import dataclass
from typing import Optional

from edge_mining.domain.common import Watts
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.miner.common import MinerId, MinerStatus
from edge_mining.domain.exceptions import MinerNotActiveError

@dataclass
class Miner:
    """Entity for a mining device."""
    id: MinerId
    name: str
    status: MinerStatus = MinerStatus.UNKNOWN
    hash_rate: Optional[HashRate] = None # Hash rate in MH/s or GH/s
    hash_rate_max: Optional[HashRate] = None # Max hash rate for the miner
    power_consumption: Optional[Watts] = None # Can be dynamic or fixed
    power_consumption_max: Optional[Watts] = None # Max power consumption for the miner
    ip_address: Optional[str] = None # 🤷​ Will need it for some control methods ?
    active: bool = True # Is the miner active in the system?

    def turn_on(self):
        """Turn on the miner."""
        # Domain logic: update status if applicable
        if self.active:
            if self.status in [MinerStatus.OFF, MinerStatus.ERROR, MinerStatus.UNKNOWN]:
                self.status = MinerStatus.STARTING
                print(f"Domain: Miner {self.id} requested to turn ON") # Placeholder
        else:
            raise MinerNotActiveError(f"Miner {self.id} is not active and cannot be turned ON.")

    def turn_off(self):
        """Turn off the miner."""
        # Domain logic: update status if applicable
        if self.active:
            if self.status in [MinerStatus.ON, MinerStatus.ERROR]:
                self.status = MinerStatus.STOPPING
                print(f"Domain: Miner {self.id} requested to turn OFF") # Placeholder
            # Else: Already off or transitioning
        else:
            raise MinerNotActiveError(f"Miner {self.id} is not active and cannot be turned OFF.")

    def update_status(self, new_status: MinerStatus, hash_rate: Optional[HashRate] = None, power: Optional[Watts] = None):
        """Update the status of the miner."""
        if self.active:
            self.status = new_status
            if hash_rate is not None:
                self.hash_rate = hash_rate
            if power is not None:
                self.power_consumption = power

            # TODO: Add logic to handle max hash rate and power consumption

            print(f"Domain: Miner {self.id} status updated to {new_status}, hashrate: {hash_rate}, power: {power}") # Placeholder
        else:
            raise MinerNotActiveError(f"Miner {self.id} is not active and cannot update status.")

    def activate(self):
        """Activate the miner."""
        self.active = True
        print(f"Domain: Miner {self.id} activated")

    def deactivate(self):
        """Deactivate the miner."""
        self.active = False
        print(f"Domain: Miner {self.id} deactivated")
