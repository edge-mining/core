"""Interfaces for the configurations."""

from abc import ABC, abstractmethod

from edge_mining.domain.energy.common import EnergyMonitorAdapter
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.domain.home_load.common import HomeForecastProviderAdapter
from edge_mining.domain.miner.common import MinerControllerAdapter
from edge_mining.domain.notification.common import NotificationAdapter
from edge_mining.domain.performance.common import MiningPerformanceTrackerAdapter
from edge_mining.shared.external_services.common import ExternalServiceAdapter


class Configuration(ABC):
    """Base interface for all configurations"""

    @abstractmethod
    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> "Configuration":
        """Create a configuration object from a dictionary"""


class EnergyMonitorConfig(Configuration):
    """Base interface for Energy Monitor configurations."""

    @abstractmethod
    def is_valid(self, adapter_type: EnergyMonitorAdapter) -> bool:
        """Check if the configuration is valid for the given adapter type."""
        pass


class NotificationConfig(Configuration):
    """Base interface for Notification configurations."""

    @abstractmethod
    def is_valid(self, adapter_type: NotificationAdapter) -> bool:
        """Check if the configuration is valid for the given adapter type."""
        pass


class ForecastProviderConfig(Configuration):
    """Base interface for Forecast Provider configurations."""

    @abstractmethod
    def is_valid(self, adapter_type: ForecastProviderAdapter) -> bool:
        """Check if the configuration is valid for the given adapter type."""
        pass


class HomeForecastProviderConfig(Configuration):
    """Base interface for Home Loads Forecast Provider configurations."""

    @abstractmethod
    def is_valid(self, adapter_type: HomeForecastProviderAdapter) -> bool:
        """Check if the configuration is valid for the given adapter type."""
        pass


class MinerControllerConfig(Configuration):
    """Base interface for Miner Controller configurations."""

    @abstractmethod
    def is_valid(self, adapter_type: MinerControllerAdapter) -> bool:
        """Check if the configuration is valid for the given adapter type."""
        pass


class MiningPerformanceTrackerConfig(Configuration):
    """Base interface for Mining Performance Tracker configurations."""

    @abstractmethod
    def is_valid(self, adapter_type: MiningPerformanceTrackerAdapter) -> bool:
        """Check if the configuration is valid for the given adapter type."""
        pass


class ExternalServiceConfig(Configuration):
    """Base interface for External Service configurations."""

    @abstractmethod
    def is_valid(self, adapter_type: ExternalServiceAdapter) -> bool:
        """Check if the configuration is valid for the given adapter type."""
        pass
