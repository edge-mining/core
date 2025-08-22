"""MQTT message bus adapter for edge mining application."""

import threading
import time
from typing import List, Optional

import paho.mqtt.client as mqtt


class BaseMQTTBus:
    """Base class for MQTT message bus."""

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        username: Optional[str],
        password: Optional[str],
        client_id: str,
        topics: List[str],  # Map internal name to topic string
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client_id = f"{client_id}-{int(time.time())}"  # Add timestamp for more uniqueness
        self._connected = threading.Event()
        self._client: Optional[mqtt.Client] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
