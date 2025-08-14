"""Collection of Ports for the Home Consumption Analytics domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import Optional

from edge_mining.domain.common import Watts
from edge_mining.domain.home_load.aggregate_roots import HomeLoadsProfile

class HomeForecastProviderPort(ABC):
    """Port for the Home Forecast Provider."""
    @abstractmethod
    def get_home_consumption_forecast(self, hours_ahead: int = 24) -> Optional[Watts]:
        """
        Provides an aggregated forecast of home energy consumption
        for the specified period. Returns average Watts or a profile?
        For now, let's return an estimated *average* Watts needed soon.
        Refine later based on how OptimizationPolicy uses it.
        """
        raise NotImplementedError

class HomeLoadsProfileRepository(ABC):
    """Port for the Home Loads Profile Repository."""
    @abstractmethod
    def get_profile(self) -> Optional[HomeLoadsProfile]: # Assuming single profile for now
        """Get the home loads profile."""
        raise NotImplementedError

    @abstractmethod
    def save_profile(self, profile: HomeLoadsProfile) -> None:
        """Save the home loads profile."""
        raise NotImplementedError