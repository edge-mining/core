"""
Common classes for the Notification domain of the Edge Mining application.
"""

from edge_mining.domain.common import AdapterType


class NotificationAdapter(AdapterType):
    """Types of notification adapter."""

    DUMMY = "dummy"
    TELEGRAM = "telegram"
