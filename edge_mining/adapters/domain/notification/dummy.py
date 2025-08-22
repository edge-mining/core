"""
Dummy adapter (Implementation of Port) that simulates a notification sender
for Edge Mining Application
"""

import logging

from edge_mining.domain.notification.ports import NotificationPort

logger = logging.getLogger(__name__)


class DummyNotifier(NotificationPort):
    """Prints notifications to the console/log."""

    async def send_notification(self, title: str, message: str) -> bool:
        full_message = f"--- NOTIFICATION ---\nTitle: {title}\nMessage: {message}\n--------------------"
        print(full_message)
        logger.info("Notification Sent: Title='%s'", title)
        return True
