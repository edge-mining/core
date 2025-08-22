"""
Collection of Entities for the External Sources
of the Edge Mining application.
"""

from dataclasses import dataclass
from typing import Optional

from edge_mining.domain.common import Entity
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.interfaces.config import ExternalServiceConfig


@dataclass
class ExternalService(Entity):
    """Entity for an external source"""

    name: str = ""
    adapter_type: ExternalServiceAdapter = ExternalServiceAdapter.UNKNOWN
    config: Optional[ExternalServiceConfig] = None
