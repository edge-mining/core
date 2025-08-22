"""
Collection of adapters maps for the home load forecast domain
of the Edge Mining application.
"""

from typing import Dict, Optional

from edge_mining.domain.home_load.common import HomeForecastProviderAdapter
from edge_mining.shared.adapter_configs.home_load import HomeForecastProviderDummyConfig
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.interfaces.config import HomeForecastProviderConfig

HOME_FORECAST_PROVIDER_CONFIG_TYPE_MAP: Dict[
    HomeForecastProviderAdapter, Optional[type[HomeForecastProviderConfig]]
] = {HomeForecastProviderAdapter.DUMMY: HomeForecastProviderDummyConfig}

HOME_FORECAST_PROVIDER_EXTERNAL_SERVICE_MAP: Dict[HomeForecastProviderAdapter, Optional[ExternalServiceAdapter]] = {
    HomeForecastProviderAdapter.DUMMY: None  # Dummy does not use an external service
}
