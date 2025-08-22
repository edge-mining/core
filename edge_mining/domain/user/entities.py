"""Collection of Entities for the User Settings domain of the Edge Mining application."""

from dataclasses import dataclass, field
from typing import Any, Dict

from edge_mining.domain.common import Entity
from edge_mining.domain.user.common import UserId


@dataclass
class User(Entity):
    """Entity for a user."""

    username: str = ""
    # Add password hash, roles etc. if needed


@dataclass
class SystemSettings:
    """Entity for the system settings."""

    id: UserId  # Or a fixed ID like 'global_settings'
    settings: Dict[str, Any] = field(default_factory=dict)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting by its key."""
        return self.settings.get(key, default)

    def set_setting(self, key: str, value: Any):
        """Set a setting by its key."""
        self.settings[key] = value
