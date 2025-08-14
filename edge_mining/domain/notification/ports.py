"""Collection of Ports for the Notification domain of the Edge Mining application."""

# Is it really necessary to have a domain dedicated to the notification service? ❓​❓​❓​ 🤔​

from abc import ABC, abstractmethod

class NotificationPort(ABC):
    """Port for the Notification."""
    @abstractmethod
    async def send_notification(self, title: str, message: str) -> bool:
        """Sends a notification to the configured channel(s)."""
        raise NotImplementedError
