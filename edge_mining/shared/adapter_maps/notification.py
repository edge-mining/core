"""
Collection of adapters maps for the notification domain
of the Edge Mining application.
"""

from typing import Dict, Optional

from edge_mining.domain.notification.common import NotificationAdapter
from edge_mining.shared.adapter_configs.notification import (
    DummyNotificationConfig,
    TelegramNotificationConfig,
)
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.interfaces.config import NotificationConfig

NOTIFIER_CONFIG_TYPE_MAP: Dict[NotificationAdapter, Optional[type[NotificationConfig]]] = {
    NotificationAdapter.DUMMY: DummyNotificationConfig,
    NotificationAdapter.TELEGRAM: TelegramNotificationConfig,
}

NOTIFIER_TYPE_EXTERNAL_SERVICE_MAP: Dict[NotificationAdapter, Optional[ExternalServiceAdapter]] = {
    NotificationAdapter.DUMMY: None,  # Dummy does not use an external service
    NotificationAdapter.TELEGRAM: None,  # Telegram does not use an external service
}
