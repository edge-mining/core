"""Collection of Entities for the Notification domain of the Edge Mining application."""

from dataclasses import dataclass
from typing import Optional

from edge_mining.domain.common import Entity, EntityId
from edge_mining.domain.notification.common import NotificationAdapter
from edge_mining.shared.interfaces.config import NotificationConfig


@dataclass
class Notifier(Entity):
    """Entity for an energy monitor."""

    name: str = ""
    adapter_type: NotificationAdapter = NotificationAdapter.DUMMY  # Default to dummy notifier
    config: Optional[NotificationConfig] = None
    external_service_id: Optional[EntityId] = None
