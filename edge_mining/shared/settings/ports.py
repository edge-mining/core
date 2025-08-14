"""Repository settings Port"""
from typing import Optional
from abc import ABC, abstractmethod

from edge_mining.domain.user.common import UserId
from edge_mining.domain.user.entities import SystemSettings

class SettingsRepository(ABC):
    """Port for the Settings Repository."""
    @abstractmethod
    def get_settings(self, user_id: Optional[UserId]) -> Optional[SystemSettings]: # Assuming single settings object
        """Gets the settings."""
        raise NotImplementedError

    @abstractmethod
    def save_settings(self, settings: SystemSettings, user_id: Optional[UserId]) -> None:
        """Saves the settings."""
        raise NotImplementedError
