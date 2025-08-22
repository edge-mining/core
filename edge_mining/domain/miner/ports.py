"""Collection of Ports for the Mining Device Management domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import List, Optional

from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.miner.common import MinerStatus
from edge_mining.domain.miner.entities import Miner, MinerController
from edge_mining.domain.miner.value_objects import HashRate


class MinerControlPort(ABC):
    """Port for the Miner Control."""

    @abstractmethod
    def start_miner(self) -> bool:
        """Attempts to start the miner. Returns True on success request."""
        raise NotImplementedError

    @abstractmethod
    def stop_miner(self) -> bool:
        """Attempts to stop the specified miner. Returns True on success request."""
        raise NotImplementedError

    @abstractmethod
    def get_miner_status(self) -> MinerStatus:
        """Gets the current operational status of the miner."""
        raise NotImplementedError

    @abstractmethod
    def get_miner_power(self) -> Optional[Watts]:
        """Gets the current power consumption, if available."""
        raise NotImplementedError

    @abstractmethod
    def get_miner_hashrate(self) -> Optional[HashRate]:
        """Gets the current hash rate, if available."""
        raise NotImplementedError


class MinerRepository(ABC):
    """Port for the Miner Repository."""

    @abstractmethod
    def add(self, miner: Miner) -> None:
        """Adds a new miner to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, miner_id: EntityId) -> Optional[Miner]:
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
    def remove(self, miner_id: EntityId) -> None:
        """Removes a miner from the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_controller_id(self, controller_id: EntityId) -> List[Miner]:
        """Retrieves a list of miners by their associated controller ID."""
        raise NotImplementedError


class MinerControllerRepository(ABC):
    """Port for the Miner Controller Repository."""

    @abstractmethod
    def add(self, miner_controller: MinerController) -> None:
        """Adds a new miner controller to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, miner_controller_id: EntityId) -> Optional[MinerController]:
        """Retrieves a miner controller by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[MinerController]:
        """Retrieves all miner controllers in the repository."""
        raise NotImplementedError

    @abstractmethod
    def update(self, miner_controller: MinerController) -> None:
        """Updates the state of an existing miner controller in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, miner_controller_id: EntityId) -> None:
        """Removes a miner controller from the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_external_service_id(self, external_service_id: EntityId) -> List[MinerController]:
        """Retrieves a list of miner controllers by its associated external service ID."""
        raise NotImplementedError
