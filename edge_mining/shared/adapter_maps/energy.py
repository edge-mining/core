"""Collection of adapters maps for the energy domain of the Edge Mining application."""

from typing import Dict, List, Optional, Union

from edge_mining.adapters.domain.energy.dummy_solar import DummySolarEnergyMonitor
from edge_mining.adapters.domain.energy.home_assistant_api import (
    HomeAssistantAPIEnergyMonitor,
)
from edge_mining.adapters.domain.forecast.dummy_solar import DummySolarForecastProvider
from edge_mining.adapters.domain.forecast.home_assistant_api import (
    HomeAssistantForecastProvider,
)
from edge_mining.domain.energy.common import EnergyMonitorAdapter, EnergySourceType
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.shared.adapter_configs.energy import (
    EnergyMonitorDummySolarConfig,
    EnergyMonitorHomeAssistantConfig,
)
from edge_mining.shared.adapter_configs.forecast import (
    ForecastProviderDummySolarConfig,
    ForecastProviderHomeAssistantConfig,
)
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.interfaces.config import EnergyMonitorConfig

# Mapping of energy source types to forecast providers types.
ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_TYPE_MAP: Dict[EnergySourceType, Optional[List[ForecastProviderAdapter]]] = {
    EnergySourceType.SOLAR: [
        ForecastProviderAdapter.DUMMY_SOLAR,
        ForecastProviderAdapter.HOME_ASSISTANT_API,
    ],
    EnergySourceType.WIND: [ForecastProviderAdapter.HOME_ASSISTANT_API],
    EnergySourceType.GRID: [ForecastProviderAdapter.HOME_ASSISTANT_API],
    EnergySourceType.HYDROELECTRIC: [ForecastProviderAdapter.HOME_ASSISTANT_API],
    EnergySourceType.OTHER: [ForecastProviderAdapter.HOME_ASSISTANT_API],
}

# Mapping of energy source types to forecast providers configuration classes.
ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_CONFIG_MAP: Dict[
    EnergySourceType,
    Optional[
        List[
            Union[
                type[ForecastProviderDummySolarConfig],
                type[ForecastProviderHomeAssistantConfig],
            ]
        ]
    ],
] = {
    EnergySourceType.SOLAR: [
        ForecastProviderDummySolarConfig,
        ForecastProviderHomeAssistantConfig,
    ],
    EnergySourceType.WIND: None,
    EnergySourceType.GRID: None,
    EnergySourceType.HYDROELECTRIC: None,
    EnergySourceType.OTHER: None,
}

# Mapping of energy source types to forecast providers instance classes.
ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_CLASS_MAP: Dict[
    EnergySourceType,
    Optional[List[Union[type[DummySolarForecastProvider], type[HomeAssistantForecastProvider]]]],
] = {
    EnergySourceType.SOLAR: [
        DummySolarForecastProvider,
        HomeAssistantForecastProvider,
    ],
    EnergySourceType.WIND: None,
    EnergySourceType.GRID: None,
    EnergySourceType.HYDROELECTRIC: None,
    EnergySourceType.OTHER: None,
}

ENERGY_SOURCE_TYPE_ENERGY_MONITOR_MAP: Dict[EnergySourceType, Optional[List[EnergyMonitorAdapter]]] = {
    EnergySourceType.SOLAR: [
        EnergyMonitorAdapter.DUMMY_SOLAR,
        EnergyMonitorAdapter.HOME_ASSISTANT_API,
    ],
    EnergySourceType.WIND: [EnergyMonitorAdapter.HOME_ASSISTANT_API],
    EnergySourceType.GRID: [EnergyMonitorAdapter.HOME_ASSISTANT_API],
    EnergySourceType.HYDROELECTRIC: [EnergyMonitorAdapter.HOME_ASSISTANT_API],
    EnergySourceType.OTHER: [EnergyMonitorAdapter.HOME_ASSISTANT_API],
}

ENERGY_SOURCE_TYPE_ENERGY_MONITOR_CLASS_MAP: Dict[
    EnergySourceType,
    Optional[List[Union[type[DummySolarEnergyMonitor], type[HomeAssistantAPIEnergyMonitor]]]],
] = {
    EnergySourceType.SOLAR: [
        DummySolarEnergyMonitor,
        HomeAssistantAPIEnergyMonitor,
    ],
    EnergySourceType.WIND: [HomeAssistantAPIEnergyMonitor],
    EnergySourceType.GRID: [HomeAssistantAPIEnergyMonitor],
    EnergySourceType.HYDROELECTRIC: [HomeAssistantAPIEnergyMonitor],
    EnergySourceType.OTHER: [HomeAssistantAPIEnergyMonitor],
}

ENERGY_MONITOR_CONFIG_TYPE_MAP: Dict[EnergyMonitorAdapter, Optional[type[EnergyMonitorConfig]]] = {
    EnergyMonitorAdapter.DUMMY_SOLAR: EnergyMonitorDummySolarConfig,
    EnergyMonitorAdapter.HOME_ASSISTANT_API: EnergyMonitorHomeAssistantConfig,
}

ENERGY_MONITOR_TYPE_EXTERNAL_SERVICE_MAP: Dict[EnergyMonitorAdapter, Optional[ExternalServiceAdapter]] = {
    EnergyMonitorAdapter.DUMMY_SOLAR: None,  # Dummy does not use an external service
    EnergyMonitorAdapter.HOME_ASSISTANT_API: ExternalServiceAdapter.HOME_ASSISTANT_API,
}
