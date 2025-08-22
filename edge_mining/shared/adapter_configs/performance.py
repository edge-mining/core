"""
Collection of adapters configuration for the performace tracker domain
of the Edge Mining application.
"""

from dataclasses import asdict, dataclass

from edge_mining.domain.performance.common import MiningPerformanceTrackerAdapter
from edge_mining.shared.interfaces.config import MiningPerformanceTrackerConfig


@dataclass(frozen=True)
class MiningPerformanceTrackerDummyConfig(MiningPerformanceTrackerConfig):
    """
    Dummy mining performance tracker configuration. It encapsulates the configuration parameters
    to track performance via a dummy adapter.
    """

    message: str = "This is a dummy performance tracker"

    def is_valid(self, adapter_type: MiningPerformanceTrackerAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Dummy Performance Tracker, it is always valid.
        """
        return adapter_type == MiningPerformanceTrackerAdapter.DUMMY

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)
