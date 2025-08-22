"""
Collection of adapters configuration for the notification domain
of the Edge Mining application.
"""

from dataclasses import asdict, dataclass

from edge_mining.domain.notification.common import NotificationAdapter
from edge_mining.shared.interfaces.config import NotificationConfig


@dataclass(frozen=True)
class DummyNotificationConfig(NotificationConfig):
    """
    Dummy notification configuration. It encapsulate the configuration parameters
    to send notifications via a dummy adapter.
    """

    message: str = "This is a dummy notification"

    def is_valid(self, adapter_type: NotificationAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Dummy Notification, it is always valid.
        """
        return adapter_type == NotificationAdapter.DUMMY

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)


@dataclass(frozen=True)
class TelegramNotificationConfig(NotificationConfig):
    """
    Telegram notification configuration. It encapsulate the configuration parameters
    to send notifications via Telegram.
    """

    bot_token: str
    chat_id: str

    def is_valid(self, adapter_type: NotificationAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Telegram Notification, it is always valid.
        """
        return adapter_type == NotificationAdapter.TELEGRAM

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)
