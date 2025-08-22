"""
Collection of adapters maps for the energy forecast domain
of the Edge Mining application.
"""

from typing import Dict, Optional

from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.shared.adapter_configs.forecast import (
    ForecastProviderDummySolarConfig,
    ForecastProviderHomeAssistantConfig,
)
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.interfaces.config import ForecastProviderConfig

FORECAST_PROVIDER_CONFIG_TYPE_MAP: Dict[ForecastProviderAdapter, Optional[type[ForecastProviderConfig]]] = {
    ForecastProviderAdapter.DUMMY_SOLAR: ForecastProviderDummySolarConfig,
    ForecastProviderAdapter.HOME_ASSISTANT_API: ForecastProviderHomeAssistantConfig,
}

FORECAST_PROVIDER_TYPE_EXTERNAL_SERVICE_MAP: Dict[ForecastProviderAdapter, Optional[ExternalServiceAdapter]] = {
    ForecastProviderAdapter.DUMMY_SOLAR: None,  # Dummy does not use an external service
    ForecastProviderAdapter.HOME_ASSISTANT_API: ExternalServiceAdapter.HOME_ASSISTANT_API,
}
