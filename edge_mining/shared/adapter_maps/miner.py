"""
Collection of adapters maps for the miner domain
of the Edge Mining application.
"""

from typing import Dict, Optional

from edge_mining.domain.miner.common import MinerControllerAdapter
from edge_mining.shared.adapter_configs.miner import MinerControllerDummyConfig
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.interfaces.config import MinerControllerConfig

MINER_CONTROLLER_CONFIG_TYPE_MAP: Dict[MinerControllerAdapter, Optional[type[MinerControllerConfig]]] = {
    MinerControllerAdapter.DUMMY: MinerControllerDummyConfig
}

MINER_CONTROLLER_TYPE_EXTERNAL_SERVICE_MAP: Dict[MinerControllerAdapter, Optional[ExternalServiceAdapter]] = {
    MinerControllerAdapter.DUMMY: None  # Dummy does not use an external service
}
