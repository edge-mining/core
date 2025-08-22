"""
Collection of adapters configuration for the miner domain
of the Edge Mining application.
"""

from dataclasses import asdict, dataclass, field

from edge_mining.domain.miner.common import MinerControllerAdapter
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.shared.interfaces.config import MinerControllerConfig


@dataclass(frozen=True)
class MinerControllerDummyConfig(MinerControllerConfig):
    """
    Miner controller configuration. It encapsulate the configuration parameters
    to control a miner with dummy controller.
    """

    initial_status: str = field(default="UNKNOWN")
    power_max: float = field(default=3200.0)
    hashrate_max: HashRate = field(default=HashRate(90, "TH/s"))

    def is_valid(self, adapter_type: MinerControllerAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Dummy Miner Controller, it is always valid.
        """
        return adapter_type == MinerControllerAdapter.DUMMY

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)
