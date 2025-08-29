"""Collection of Common Objects for the Mining Device Management domain of the Edge Mining application."""

from enum import Enum

from edge_mining.domain.common import AdapterType


class MinerStatus(Enum):
    """Enum for the different miner statuses."""

    UNKNOWN = "unknown"
    OFF = "off"
    ON = "on"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


class MinerControllerAdapter(AdapterType):
    """Types of miner controller adapter."""

    DUMMY = "dummy"
    GENERIC_SOCKET_HOME_ASSISTANT_API = "generic_socket_home_assistant_api"
    PYASIC = "pyasic"
