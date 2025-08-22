"""
Collection of adapters configuration for the home load forecast domain
of the Edge Mining application.
"""

from dataclasses import asdict, dataclass, field

from edge_mining.domain.home_load.common import HomeForecastProviderAdapter
from edge_mining.shared.interfaces.config import HomeForecastProviderConfig


@dataclass(frozen=True)
class HomeForecastProviderDummyConfig(HomeForecastProviderConfig):
    """
    Home Forecast provider configuration. It encapsulate the configuration parameters
    to retrieve home forecast data from a dummy provider.
    """

    load_power_max: float = field(default=500.0)

    def is_valid(self, adapter_type: HomeForecastProviderAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Dummy Home Forecast, it is always valid.
        """
        return adapter_type == HomeForecastProviderAdapter.DUMMY

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)
