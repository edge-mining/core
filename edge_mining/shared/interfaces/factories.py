"""Interfaces for the factories."""

from abc import ABC, abstractmethod
from typing import Any, Optional

from edge_mining.domain.energy.entities import EnergySource
from edge_mining.domain.miner.entities import Miner
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.interfaces.config import Configuration, ExternalServiceConfig
from edge_mining.shared.logging.port import LoggerPort


class ExternalServiceFactory(ABC):
    """Abstract factory for external services"""

    @abstractmethod
    def create(self, config: Optional[ExternalServiceConfig], logger: LoggerPort) -> Any:
        """Create an external service"""
        pass


class AdapterFactory(ABC):
    """Abstract factory for adapters"""

    @abstractmethod
    def create(
        self,
        config: Optional[Configuration],
        logger: Optional[LoggerPort],
        external_service: Optional[ExternalServicePort],
    ) -> Any:
        """Create an adapter"""
        pass


class EnergyMonitorAdapterFactory(AdapterFactory):
    """Abstract factory for energy monitor adapters"""

    @abstractmethod
    def from_energy_source(self, energy_source: EnergySource) -> None:
        """Set the reference energy source"""
        pass


class MinerControllerAdapterFactory(AdapterFactory):
    """Abstract factory for miner control adapters"""

    @abstractmethod
    def from_miner(self, miner: Miner) -> None:
        """Set the reference miner"""
        pass


class NotificationAdapterFactory(AdapterFactory):
    """Abstract factory for notification adapters"""


class ForecastAdapterFactory(AdapterFactory):
    """Abstract factory for forecast adapters"""

    @abstractmethod
    def from_energy_source(self, energy_source: EnergySource) -> None:
        """Set the reference energy source"""
        pass
