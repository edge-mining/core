"""Collection of adapters configuration for the external services of the Edge Mining application."""

from dataclasses import asdict, dataclass

from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.interfaces.config import ExternalServiceConfig


@dataclass(frozen=True)
class ExternalServiceHomeAssistantConfig(ExternalServiceConfig):
    """
    Home Assistant external service configuration. It encapsulates the configuration parameters
    to connect to a Home Assistant instance.
    """

    url: str
    token: str

    def is_valid(self, adapter_type: ExternalServiceAdapter) -> bool:
        """
        Check if the configuration is valid for the given adapter type.
        For Home Assistant, it is always valid.
        """
        return adapter_type == ExternalServiceAdapter.HOME_ASSISTANT_API

    def to_dict(self) -> dict:
        """Converts the configuration object into a serializable dictionary"""
        return {**asdict(self)}

    @classmethod
    def from_dict(cls, data: dict):
        """Create a configuration object from a dictionary"""
        return cls(**data)
