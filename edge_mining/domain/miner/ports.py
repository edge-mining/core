"""Collection of Ports for the Mining Device Management domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import Optional, List

from edge_mining.domain.common import Watts
from edge_mining.domain.miner.entities import Miner
from edge_mining.domain.miner.common import MinerId, MinerStatus
from edge_mining.domain.miner.value_objects import HashRate

class MinerControlPort(ABC):
    """Port for the Miner Control."""
    @abstractmethod
    def start_miner(self, miner_id: MinerId) -> bool:
        """Attempts to start the specified miner. Returns True on success request."""
        raise NotImplementedError

    @abstractmethod
    def stop_miner(self, miner_id: MinerId) -> bool:
        """Attempts to stop the specified miner. Returns True on success request."""
        raise NotImplementedError

    @abstractmethod
    def get_miner_status(self, miner_id: MinerId) -> MinerStatus:
        """Gets the current operational status of the miner."""
        raise NotImplementedError

    @abstractmethod
    def get_miner_power(self, miner_id: MinerId) -> Optional[Watts]:
        """Gets the current power consumption, if available."""
        raise NotImplementedError
    
    @abstractmethod
    def get_miner_hashrate(self, miner_id: MinerId) -> Optional[HashRate]:
        """Gets the current hash rate, if available."""
        raise NotImplementedError

class MinerRepository(ABC):
    """Port for the Miner Repository."""
    @abstractmethod
    def generate_id(self) -> MinerId:
        """Generates a new unique ID for a miner."""
        raise NotImplementedError
    
    @abstractmethod
    def add(self, miner: Miner) -> None:
        """Adds a new miner to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, miner_id: MinerId) -> Optional[Miner]:
        """Retrieves a miner by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[Miner]:
        """Retrieves all miners in the repository."""
        raise NotImplementedError

    @abstractmethod
    def update(self, miner: Miner) -> None:
        """Updates the state of an existing miner in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, miner_id: MinerId) -> None:
        """Removes a miner from the repository."""
        raise NotImplementedError
