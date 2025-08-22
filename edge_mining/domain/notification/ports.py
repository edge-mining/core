"""Collection of Ports for the Notification domain of the Edge Mining application."""

# Is it really necessary to have a domain dedicated to the notification service?

from abc import ABC, abstractmethod
from typing import List, Optional

from edge_mining.domain.common import EntityId
from edge_mining.domain.notification.entities import Notifier


class NotificationPort(ABC):
    """Port for the Notification."""

    @abstractmethod
    async def send_notification(self, title: str, message: str) -> bool:
        """Sends a notification to the configured channel(s)."""
        raise NotImplementedError


class NotifierRepository(ABC):
    """Port for the Notifier Repository."""

    @abstractmethod
    def add(self, notifier: Notifier) -> None:
        """Adds a new notifier to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, notifier_id: EntityId) -> Optional[Notifier]:
        """Retrieves an notifier by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[Notifier]:
        """Retrieves all notifiers from the repository."""
        raise NotImplementedError

    @abstractmethod
    def update(self, notifier: Notifier) -> None:
        """Updates an notifier in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, notifier_id: EntityId) -> None:
        """Removes an notifier from the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_external_service_id(self, external_service_id: EntityId) -> List[Notifier]:
        """Retrieves a list of notifiers by its associated external service ID."""
        raise NotImplementedError
