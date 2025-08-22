"""
Configuration service for managing all domain entities of edge mining application.
"""

from typing import Any, Dict, List, Optional

from edge_mining.application.interfaces import ConfigurationServiceInterface
from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter, EnergySourceType
from edge_mining.domain.energy.entities import EnergyMonitor, EnergySource
from edge_mining.domain.energy.exceptions import (
    EnergyMonitorConfigurationError,
    EnergyMonitorNotFoundError,
    EnergySourceNotFoundError,
)
from edge_mining.domain.energy.ports import EnergyMonitorRepository, EnergySourceRepository
from edge_mining.domain.energy.value_objects import Battery, Grid
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.domain.forecast.entities import ForecastProvider
from edge_mining.domain.forecast.exceptions import ForecastProviderConfigurationError, ForecastProviderNotFoundError
from edge_mining.domain.forecast.ports import ForecastProviderRepository
from edge_mining.domain.home_load.entities import HomeForecastProvider
from edge_mining.domain.home_load.exceptions import HomeForecastProviderNotFoundError
from edge_mining.domain.home_load.ports import HomeForecastProviderRepository
from edge_mining.domain.miner.common import MinerControllerAdapter, MinerStatus
from edge_mining.domain.miner.entities import Miner, MinerController
from edge_mining.domain.miner.exceptions import (
    MinerControllerConfigurationError,
    MinerControllerNotFoundError,
    MinerNotFoundError,
)
from edge_mining.domain.miner.ports import MinerControllerRepository, MinerRepository
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.notification.common import NotificationAdapter
from edge_mining.domain.notification.entities import Notifier
from edge_mining.domain.notification.exceptions import NotifierConfigurationError, NotifierNotFoundError
from edge_mining.domain.notification.ports import NotifierRepository
from edge_mining.domain.optimization_unit.aggregate_roots import EnergyOptimizationUnit
from edge_mining.domain.optimization_unit.exceptions import (
    OptimizationUnitConfigurationError,
    OptimizationUnitNotFoundError,
)
from edge_mining.domain.optimization_unit.ports import EnergyOptimizationUnitRepository
from edge_mining.domain.performance.exceptions import MiningPerformanceTrackerNotFoundError
from edge_mining.domain.performance.ports import MiningPerformanceTrackerRepository
from edge_mining.domain.policy.aggregate_roots import OptimizationPolicy
from edge_mining.domain.policy.common import RuleType
from edge_mining.domain.policy.entities import AutomationRule
from edge_mining.domain.policy.exceptions import PolicyConfigurationError, PolicyError, PolicyNotFoundError
from edge_mining.domain.policy.ports import OptimizationPolicyRepository
from edge_mining.domain.user.common import UserId
from edge_mining.domain.user.entities import SystemSettings
from edge_mining.shared.adapter_maps.energy import (
    ENERGY_MONITOR_TYPE_EXTERNAL_SERVICE_MAP,
    ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_CONFIG_MAP,
    ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_TYPE_MAP,
)
from edge_mining.shared.adapter_maps.forecast import FORECAST_PROVIDER_TYPE_EXTERNAL_SERVICE_MAP
from edge_mining.shared.adapter_maps.miner import MINER_CONTROLLER_CONFIG_TYPE_MAP
from edge_mining.shared.adapter_maps.notification import NOTIFIER_TYPE_EXTERNAL_SERVICE_MAP
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.external_services.exceptions import (
    ExternalServiceConfigurationError,
    ExternalServiceNotFoundError,
)
from edge_mining.shared.external_services.ports import ExternalServiceRepository
from edge_mining.shared.external_services.value_objects import ExternalServiceLinkedEntities
from edge_mining.shared.infrastructure import PersistenceSettings
from edge_mining.shared.interfaces.config import (
    EnergyMonitorConfig,
    ExternalServiceConfig,
    ForecastProviderConfig,
    MinerControllerConfig,
    NotificationConfig,
)
from edge_mining.shared.logging.port import LoggerPort
from edge_mining.shared.settings.ports import SettingsRepository


class ConfigurationService(ConfigurationServiceInterface):
    """Handles configuration of miners, policies, and system settings."""

    def __init__(self, persistence_settings: PersistenceSettings, logger: LoggerPort):
        # Domains
        self.external_service_repo: ExternalServiceRepository = persistence_settings.external_service_repo
        self.energy_source_repo: EnergySourceRepository = persistence_settings.energy_source_repo
        self.energy_monitor_repo: EnergyMonitorRepository = persistence_settings.energy_monitor_repo
        self.miner_repo: MinerRepository = persistence_settings.miner_repo
        self.miner_controller_repo: MinerControllerRepository = persistence_settings.miner_controller_repo
        self.policy_repo: OptimizationPolicyRepository = persistence_settings.policy_repo
        self.optimization_unit_repo: EnergyOptimizationUnitRepository = persistence_settings.optimization_unit_repo
        self.forecast_provider_repo: ForecastProviderRepository = persistence_settings.forecast_provider_repo
        self.home_forecast_provider_repo: HomeForecastProviderRepository = (
            persistence_settings.home_forecast_provider_repo
        )
        self.mining_performance_tracker_repo: MiningPerformanceTrackerRepository = (
            persistence_settings.mining_performance_tracker_repo
        )
        self.notifier_repo: NotifierRepository = persistence_settings.notifier_repo
        self.settings_repo: SettingsRepository = persistence_settings.settings_repo

        # Infrastructure
        self.logger = logger

    # --- External Service Management ---
    def create_external_service(
        self,
        name: str,
        adapter_type: ExternalServiceAdapter,
        config: ExternalServiceConfig,
    ) -> ExternalService:
        """Create a new external service."""
        self.logger.debug(f"Creating external service '{name}' with adapter {adapter_type}")

        external_service = ExternalService(name=name, adapter_type=adapter_type, config=config)

        self.check_external_service(external_service)

        self.external_service_repo.add(external_service)

        return external_service

    def get_external_service(self, service_id: EntityId) -> Optional[ExternalService]:
        """Get an external service by its ID."""
        external_service = self.external_service_repo.get_by_id(service_id)

        if not external_service:
            return None

        return external_service

    def list_external_services(self) -> List[ExternalService]:
        """List all external services in the system."""
        return self.external_service_repo.get_all()

    def get_entities_by_external_service(self, service_id: EntityId) -> ExternalServiceLinkedEntities:
        """Get entities associated with this external service"""
        miner_controllers: List[MinerController] = self.miner_controller_repo.get_by_external_service_id(service_id)
        energy_monitors: List[EnergyMonitor] = self.energy_monitor_repo.get_by_external_service_id(service_id)
        forecast_providers: List[ForecastProvider] = self.forecast_provider_repo.get_by_external_service_id(service_id)
        home_forecast_providers: List[HomeForecastProvider] = (
            self.home_forecast_provider_repo.get_by_external_service_id(service_id)
        )
        notifiers: List[Notifier] = self.notifier_repo.get_by_external_service_id(service_id)

        external_service_linked_entities = ExternalServiceLinkedEntities(
            miner_controllers=miner_controllers,
            energy_monitors=energy_monitors,
            forecast_providers=forecast_providers,
            home_forecast_providers=home_forecast_providers,
            notifiers=notifiers,
        )
        return external_service_linked_entities

    def unlink_external_service(self, service_id: EntityId) -> None:
        """Remove the association of an external service from all entities."""
        self.logger.debug(f"Unlinking external service {service_id}")

        # Get entities associated with this external service
        external_service_linked_entities = self.get_entities_by_external_service(service_id)

        # Unlink from miner controllers
        for controller in external_service_linked_entities.miner_controllers:
            self.logger.debug(
                f"Unlinking controller {controller.name} ({controller.id}) from external service {service_id}"
            )
            controller.external_service_id = None
            self.miner_controller_repo.update(controller)

        # Unlink from energy monitors
        for monitor in external_service_linked_entities.energy_monitors:
            self.logger.debug(
                f"Unlinking energy monitor {monitor.name} ({monitor.id}) from external service {service_id}"
            )
            monitor.external_service_id = None
            self.energy_monitor_repo.update(monitor)

        # Unlink from forecast providers
        for forecast_provider in external_service_linked_entities.forecast_providers:
            self.logger.debug(
                f"Unlinking forecast provider {forecast_provider.name} "
                f"({forecast_provider.id}) from external service {service_id}"
            )
            forecast_provider.external_service_id = None
            self.forecast_provider_repo.update(forecast_provider)

        # Unlink from home forecast providers
        for home_forecast_provider in external_service_linked_entities.home_forecast_providers:
            self.logger.debug(
                f"Unlinking home forecast provider {home_forecast_provider.name} "
                f"({home_forecast_provider.id}) from external service {service_id}"
            )
            home_forecast_provider.external_service_id = None
            self.home_forecast_provider_repo.update(home_forecast_provider)

        # Unlink from notifiers
        for notifier in external_service_linked_entities.notifiers:
            self.logger.debug(f"Unlinking notifier {notifier.name} ({notifier.id}) from external service {service_id}")
            notifier.external_service_id = None
            self.notifier_repo.update(notifier)

    def remove_external_service(self, service_id: EntityId) -> ExternalService:
        """Remove an external service from the system."""
        self.logger.debug(f"Removing external service {service_id}")

        external_service = self.external_service_repo.get_by_id(service_id)

        if not external_service:
            raise ExternalServiceNotFoundError(f"External Service with ID {service_id} not found.")

        # Unlink the external service from all associated entities before removal
        self.unlink_external_service(service_id)

        self.external_service_repo.remove(service_id)

        return external_service

    def update_external_service(
        self,
        service_id: EntityId,
        name: str,
        config: ExternalServiceConfig,
    ) -> ExternalService:
        """
        Update an external service in the system.
        This method updates the name and configuration only of an existing external service.
        """

        external_service = self.external_service_repo.get_by_id(service_id)

        if not external_service:
            raise ExternalServiceNotFoundError(f"External Service with ID {name} not found.")

        self.logger.debug(f"Updating external service {service_id} ({name})")

        external_service.name = name
        external_service.config = config

        self.check_external_service(external_service)

        self.external_service_repo.update(external_service)

        return external_service

    def check_external_service(self, external_service: ExternalService) -> bool:
        """Check if an external service is valid and can be used."""
        self.logger.debug(f"Checking external service {external_service.id} ({external_service.name})")

        if not external_service:
            raise ExternalServiceNotFoundError("External Service not found.")

        # Checks if the configuration is valid for the given adapter type
        if external_service.config is None or not external_service.config.is_valid(external_service.adapter_type):
            raise ExternalServiceConfigurationError(
                f"Invalid configuration for External Service {external_service.name} "
                f"with adapter {external_service.adapter_type}."
            )

        self.logger.debug(f"External Service {external_service.id} ({external_service.name}) is valid.")
        return True

    # --- Energy Source Management ---
    def create_energy_source(
        self,
        name: str,
        source_type: EnergySourceType,
        nominal_power_max: Optional[Watts] = None,
        storage: Optional[Battery] = None,
        grid: Optional[Grid] = None,
        external_source: Optional[Watts] = None,
        energy_monitor_id: Optional[EntityId] = None,
        forecast_provider_id: Optional[EntityId] = None,
    ) -> EnergySource:
        """Create a new energy source."""
        self.logger.debug(f"Creating energy source '{name}' with type {source_type}")

        energy_source = EnergySource(
            name=name,
            type=source_type,
            nominal_power_max=nominal_power_max,
            storage=storage,
            grid=grid,
            external_source=external_source,
            energy_monitor_id=energy_monitor_id,
            forecast_provider_id=forecast_provider_id,
        )

        self.check_energy_source(energy_source)

        self.energy_source_repo.add(energy_source)

        return energy_source

    def get_energy_source(self, source_id: EntityId) -> Optional[EnergySource]:
        """Get an energy source by its ID."""
        energy_source = self.energy_source_repo.get_by_id(source_id)

        if not energy_source:
            raise EnergySourceNotFoundError(f"Energy Source with ID {source_id} not found.")

        return energy_source

    def list_energy_sources(self) -> List[EnergySource]:
        """List all energy sources in the system."""
        return self.energy_source_repo.get_all()

    def remove_energy_source(self, source_id: EntityId) -> EnergySource:
        """Remove an energy source from the system."""
        self.logger.debug(f"Removing energy source {source_id}")

        energy_source = self.energy_source_repo.get_by_id(source_id)

        if not energy_source:
            raise EnergySourceNotFoundError(f"Energy Source with ID {source_id} not found.")

        self.energy_source_repo.remove(source_id)

        return energy_source

    def update_energy_source(
        self,
        source_id: EntityId,
        name: str,
        source_type: EnergySourceType,
        nominal_power_max: Optional[Watts] = None,
        storage: Optional[Battery] = None,
        grid: Optional[Grid] = None,
        external_source: Optional[Watts] = None,
        energy_monitor_id: Optional[EntityId] = None,
        forecast_provider_id: Optional[EntityId] = None,
    ) -> EnergySource:
        """Update an energy source in the system."""
        self.logger.debug(f"Updating energy source {source_id} ({name})")

        energy_source = self.energy_source_repo.get_by_id(source_id)

        if not energy_source:
            raise EnergySourceNotFoundError(f"Energy Source with ID {source_id} not found.")

        energy_source.name = name
        energy_source.type = source_type
        energy_source.nominal_power_max = nominal_power_max
        energy_source.storage = storage
        energy_source.grid = grid
        energy_source.external_source = external_source
        energy_source.energy_monitor_id = energy_monitor_id
        energy_source.forecast_provider_id = forecast_provider_id

        self.check_energy_source(energy_source)

        self.energy_source_repo.update(energy_source)

        return energy_source

    def check_energy_source(self, energy_source: EnergySource) -> bool:
        """Check if an energy source is valid and can be used."""
        self.logger.debug(f"Checking energy source {energy_source.id} ({energy_source.name})")

        if energy_source.forecast_provider_id:
            # Checks if the forecast provider exists
            provider = self.forecast_provider_repo.get_by_id(energy_source.forecast_provider_id)
            if not provider:
                raise ForecastProviderNotFoundError(
                    f"Forecast Provider with ID {energy_source.forecast_provider_id} not found."
                )

            # Checks if the forecast provider type is compatible with the source type
            required_types = ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_TYPE_MAP.get(energy_source.type, None)
            if required_types:
                is_allowed_type = any([(provider.adapter_type == required_type) for required_type in required_types])
                if not is_allowed_type:
                    raise ForecastProviderConfigurationError(
                        f"Forecast Provider {provider.id} Type {provider.adapter_type} "
                        "is not compatible with Energy Source {energy_source.name} "
                        f"of type {energy_source.type}."
                    )

            # Check if forecast provider is valid for the actual forecast provider type
            if provider.config is None:
                raise ForecastProviderConfigurationError(
                    f"Missing configuration for Forecast Provider {provider.id} "
                    f"into Energy Source {energy_source.name}."
                )

            if not provider.config.is_valid(provider.adapter_type):
                raise ForecastProviderConfigurationError(
                    f"Mismatch between Forecast Provider {provider.id} configuration "
                    f"and adapter type {provider.adapter_type} for "
                    f"Energy Source {energy_source.name}."
                )

            # Checks if the forecast provider configuration is compatible with the
            # source type
            required_classes = ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_CONFIG_MAP.get(energy_source.type, None)
            if required_classes:
                is_allowed_class = any(
                    [isinstance(provider.config, required_class) for required_class in required_classes]
                )
                if not is_allowed_class:
                    raise ForecastProviderConfigurationError(
                        f"Forecast Provider Configuration {provider.id} is not compatible "
                        f"with Energy Source {energy_source.name} of type {energy_source.type}."
                    )

        self.logger.debug(f"Energy Source {energy_source.id} ({energy_source.name}) is valid.")
        return True

    def create_energy_monitor(
        self,
        name: str,
        adapter_type: EnergyMonitorAdapter,
        config: EnergyMonitorConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> EnergyMonitor:
        """Create a new energy monitor."""
        self.logger.debug(f"Creating energy monitor '{name}' with adapter {adapter_type}")

        energy_monitor = EnergyMonitor(
            name=name,
            adapter_type=adapter_type,
            config=config,
            external_service_id=external_service_id,
        )

        self.check_energy_monitor(energy_monitor)

        self.energy_monitor_repo.add(energy_monitor)

        return energy_monitor

    def get_energy_monitor(self, monitor_id: EntityId) -> Optional[EnergyMonitor]:
        """Get an energy monitor by its ID."""
        energy_monitor = self.energy_monitor_repo.get_by_id(monitor_id)

        if not energy_monitor:
            raise EnergyMonitorNotFoundError(f"Energy Monitor with ID {monitor_id} not found.")

        return energy_monitor

    def list_energy_monitors(self) -> List[EnergyMonitor]:
        """List all energy monitors in the system."""
        return self.energy_monitor_repo.get_all()

    def unlink_energy_monitor(self, monitor_id: EntityId) -> None:
        """Unlink an energy monitor from all associated energy sources."""
        self.logger.debug(f"Unlinking energy monitor {monitor_id}")

        # Get all energy sources that use this monitor
        energy_sources: List[EnergySource] = self.energy_source_repo.get_all()

        for source in energy_sources:
            if source.energy_monitor_id == monitor_id:
                self.logger.debug(f"Unlinking energy monitor {monitor_id} from energy source {source.id}")
                source.energy_monitor_id = None
                self.energy_source_repo.update(source)

    def remove_energy_monitor(self, monitor_id: EntityId) -> EnergyMonitor:
        """Remove an energy monitor from the system."""

        energy_monitor = self.energy_monitor_repo.get_by_id(monitor_id)

        if not energy_monitor:
            raise EnergyMonitorNotFoundError(f"Energy Monitor with ID {monitor_id} not found.")

        # Unlink the energy monitor from all associated energy sources before delete
        self.unlink_energy_monitor(monitor_id)

        self.energy_monitor_repo.remove(monitor_id)

        return energy_monitor

    def update_energy_monitor(
        self,
        monitor_id: EntityId,
        name: str,
        adapter_type: EnergyMonitorAdapter,
        config: EnergyMonitorConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> EnergyMonitor:
        """Update an energy monitor in the system."""

        energy_monitor = self.energy_monitor_repo.get_by_id(monitor_id)

        if not energy_monitor:
            raise EnergyMonitorNotFoundError(f"Energy Monitor with ID {monitor_id} not found.")

        energy_monitor.name = name
        energy_monitor.adapter_type = adapter_type
        energy_monitor.config = config
        energy_monitor.external_service_id = external_service_id

        self.check_energy_monitor(energy_monitor)

        self.energy_monitor_repo.update(energy_monitor)

        return energy_monitor

    def set_energy_monitor_to_energy_source(
        self, energy_source_id: EntityId, energy_monitor_id: EntityId
    ) -> EnergySource:
        """Set an energy monitor to an energy source."""
        self.logger.debug(f"Setting energy monitor {energy_monitor_id} to energy source {energy_source_id}")

        energy_source = self.energy_source_repo.get_by_id(energy_source_id)

        if not energy_source:
            raise EnergySourceNotFoundError(f"Energy Source with ID {energy_source_id} not found.")

        energy_monitor = self.energy_monitor_repo.get_by_id(energy_monitor_id)

        if not energy_monitor:
            raise EnergyMonitorNotFoundError(f"Energy Monitor with ID {energy_monitor_id} not found.")

        energy_source.energy_monitor_id = energy_monitor_id

        self.energy_source_repo.update(energy_source)

        return energy_source

    def set_forecast_provider_to_energy_source(
        self, energy_source_id: EntityId, forecast_provider_id: EntityId
    ) -> EnergySource:
        """Set a forecast provider to an energy source."""
        self.logger.debug(f"Setting forecast provider {forecast_provider_id} to energy source {energy_source_id}")

        energy_source = self.energy_source_repo.get_by_id(energy_source_id)

        if not energy_source:
            raise EnergySourceNotFoundError(f"Energy Source with ID {energy_source_id} not found.")

        forecast_provider = self.forecast_provider_repo.get_by_id(forecast_provider_id)

        if not forecast_provider:
            raise ForecastProviderNotFoundError(f"Forecast Provider with ID {forecast_provider_id} not found.")

        energy_source.forecast_provider_id = forecast_provider_id

        self.energy_source_repo.update(energy_source)

        return energy_source

    def list_energy_sources_by_monitor(self, monitor_id: EntityId) -> List[EnergySource]:
        """List all energy sources that use a specific energy monitor."""
        self.logger.debug(f"Listing energy sources using energy monitor {monitor_id}")

        energy_sources: List[EnergySource] = self.energy_source_repo.get_all()

        filtered_sources = [source for source in energy_sources if source.energy_monitor_id == monitor_id]

        return filtered_sources

    def list_energy_sources_by_forecast_provider(self, forecast_provider_id: EntityId) -> List[EnergySource]:
        """List all energy sources that use a specific forecast provider."""
        self.logger.debug(f"Listing energy sources using forecast provider {forecast_provider_id}")
        energy_sources: List[EnergySource] = self.energy_source_repo.get_all()
        filtered_sources = [source for source in energy_sources if source.forecast_provider_id == forecast_provider_id]
        return filtered_sources

    def check_energy_monitor(self, energy_monitor: EnergyMonitor) -> bool:
        """Check if an energy monitor is valid and can be used."""
        self.logger.debug(f"Checking energy monitor {energy_monitor.id} ({energy_monitor.name})")

        if energy_monitor.external_service_id:
            external_service = self.external_service_repo.get_by_id(energy_monitor.external_service_id)
            if not external_service:
                raise ExternalServiceNotFoundError(
                    f"External Service with ID {energy_monitor.external_service_id} not found."
                )

            # Checks if the external service is compatible with the adapter type
            required_external_service_type = ENERGY_MONITOR_TYPE_EXTERNAL_SERVICE_MAP.get(
                energy_monitor.adapter_type, None
            )
            if required_external_service_type and external_service.adapter_type != required_external_service_type:
                raise EnergyMonitorConfigurationError(
                    f"External Service {energy_monitor.external_service_id} is not compatible "
                    f"with Energy Monitor {energy_monitor.name} using adapter {energy_monitor.adapter_type}."
                )

        # Checks if the configuration is valid for the given adapter type
        if energy_monitor.config is None or not energy_monitor.config.is_valid(energy_monitor.adapter_type):
            raise EnergyMonitorConfigurationError(
                f"Invalid configuration for Energy Monitor {energy_monitor.name} "
                f"with adapter {energy_monitor.adapter_type}."
            )

        self.logger.debug(f"Energy monitor {energy_monitor.id} ({energy_monitor.name}) is valid.")
        return True

    # --- Forecast Provider Management ---
    def create_forecast_provider(
        self,
        name: str,
        adapter_type: ForecastProviderAdapter,
        config: ForecastProviderConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> ForecastProvider:
        """Create a new forecast provider."""
        self.logger.debug(f"Creating forecast provider '{name}' with adapter {adapter_type}")

        forecast_provider = ForecastProvider(
            name=name,
            adapter_type=adapter_type,
            config=config,
            external_service_id=external_service_id,
        )

        self.check_forecast_provider(forecast_provider)

        self.forecast_provider_repo.add(forecast_provider)

        return forecast_provider

    def get_forecast_provider(self, provider_id: EntityId) -> Optional[ForecastProvider]:
        """Get a forecast provider by its ID."""
        forecast_provider = self.forecast_provider_repo.get_by_id(provider_id)

        if not forecast_provider:
            raise ForecastProviderNotFoundError(f"Forecast Provider with ID {provider_id} not found.")

        return forecast_provider

    def list_forecast_providers(self) -> List[ForecastProvider]:
        """List all forecast providers in the system."""
        return self.forecast_provider_repo.get_all()

    def remove_forecast_provider(self, provider_id: EntityId) -> ForecastProvider:
        """Remove a forecast provider from the system."""
        self.logger.debug(f"Removing forecast provider {provider_id}")

        forecast_provider = self.forecast_provider_repo.get_by_id(provider_id)

        if not forecast_provider:
            raise ForecastProviderNotFoundError(f"Forecast Provider with ID {provider_id} not found.")

        self.forecast_provider_repo.remove(provider_id)

        return forecast_provider

    def update_forecast_provider(
        self,
        provider_id: EntityId,
        name: str,
        adapter_type: ForecastProviderAdapter,
        config: ForecastProviderConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> ForecastProvider:
        """Update a forecast provider in the system."""
        self.logger.debug(f"Updating forecast provider {provider_id} ({name})")

        forecast_provider = self.forecast_provider_repo.get_by_id(provider_id)

        if not forecast_provider:
            raise ForecastProviderNotFoundError(f"Forecast Provider with ID {provider_id} not found.")

        forecast_provider.name = name
        forecast_provider.adapter_type = adapter_type
        forecast_provider.config = config
        forecast_provider.external_service_id = external_service_id

        self.check_forecast_provider(forecast_provider)

        self.forecast_provider_repo.update(forecast_provider)

        return forecast_provider

    def check_forecast_provider(self, provider: ForecastProvider) -> bool:
        """Check if a forecast provider is valid and can be used."""
        self.logger.debug(f"Checking forecast provider {provider.id} ({provider.name})")

        if provider.external_service_id:
            external_service = self.external_service_repo.get_by_id(provider.external_service_id)
            if not external_service:
                raise ExternalServiceNotFoundError(
                    f"External Service with ID {provider.external_service_id} not found."
                )

            # Checks if the external service is compatible with the adapter type
            required_external_service_type = FORECAST_PROVIDER_TYPE_EXTERNAL_SERVICE_MAP.get(
                provider.adapter_type, None
            )
            if required_external_service_type and external_service.adapter_type != required_external_service_type:
                raise ForecastProviderConfigurationError(
                    f"External Service {provider.external_service_id} is not compatible "
                    f"with Forecast Provider {provider.name} using adapter {provider.adapter_type}."
                )

        # Checks if the configuration is valid for the given adapter type
        if provider.config is None or not provider.config.is_valid(provider.adapter_type):
            raise ForecastProviderConfigurationError(
                f"Invalid configuration for Forecast Provider {provider.name} with adapter {provider.adapter_type}."
            )

        self.logger.debug(f"Forecast provider {provider.id} ({provider.name}) is valid.")
        return True

    # --- Optimization Unit Management ---
    def create_optimization_unit(
        self,
        name: str,
        description: Optional[str] = None,
        is_enabled: bool = False,
        policy_id: Optional[EntityId] = None,
        target_miner_ids: Optional[List[EntityId]] = None,
        energy_source_id: Optional[EntityId] = None,
        home_forecast_provider_id: Optional[EntityId] = None,
        performance_tracker_id: Optional[EntityId] = None,
        notifier_ids: Optional[List[EntityId]] = None,
    ) -> Optional[EnergyOptimizationUnit]:
        """Create an optimization unit into the system."""
        self.logger.info(f"Adding optimization unit {name} ({description}), Active: {is_enabled}")

        optimization_unit = EnergyOptimizationUnit(
            name=name,
            description=description,
            is_enabled=is_enabled,
            policy_id=policy_id,
            target_miner_ids=target_miner_ids or [],
            energy_source_id=energy_source_id,
            home_forecast_provider_id=home_forecast_provider_id,
            performance_tracker_id=performance_tracker_id,
            notifier_ids=notifier_ids or [],
        )

        self.check_optimization_unit(optimization_unit)

        self.optimization_unit_repo.add(optimization_unit)

        return optimization_unit

    def get_optimization_unit(self, unit_id: EntityId) -> Optional[EnergyOptimizationUnit]:
        """Get an optimization unit by its ID."""
        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        return optimization_unit

    def list_optimization_units(self) -> List[EnergyOptimizationUnit]:
        """List all optimization units in the system."""
        return self.optimization_unit_repo.get_all()

    def filter_optimization_units(
        self,
        filter_by_miners: Optional[List[EntityId]] = None,
        filter_by_energy_source: Optional[EntityId] = None,
        filter_by_policy: Optional[EntityId] = None,
        filter_by_home_forecast_provider: Optional[EntityId] = None,
        filter_by_performance_tracker: Optional[EntityId] = None,
        filter_by_notifiers: Optional[List[EntityId]] = None,
    ) -> List[EnergyOptimizationUnit]:
        """Filter optimization units based on various criteria."""
        # eous -> Energy optimization units
        eous = self.list_optimization_units()

        if filter_by_miners is not None:
            eous = [eou for eou in eous if set(eou.target_miner_ids).intersection(filter_by_miners)]
        if filter_by_energy_source is not None:
            eous = [eou for eou in eous if eou.energy_source_id == filter_by_energy_source]
        if filter_by_policy is not None:
            eous = [eou for eou in eous if eou.policy_id == filter_by_policy]
        if filter_by_home_forecast_provider is not None:
            eous = [eou for eou in eous if eou.home_forecast_provider_id == filter_by_home_forecast_provider]
        if filter_by_performance_tracker is not None:
            eous = [eou for eou in eous if eou.performance_tracker_id == filter_by_performance_tracker]
        if filter_by_notifiers is not None:
            eous = [eou for eou in eous if set(eou.notifier_ids).intersection(filter_by_notifiers)]
        return eous

    def remove_optimization_unit(self, unit_id: EntityId) -> EnergyOptimizationUnit:
        """Remove an optimization unit from the system."""
        self.logger.info(f"Removing optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        self.optimization_unit_repo.remove(unit_id)

        return optimization_unit

    def update_optimization_unit(
        self,
        unit_id: EntityId,
        name: str,
        description: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        policy_id: Optional[EntityId] = None,
        target_miner_ids: Optional[List[EntityId]] = None,
        energy_source_id: Optional[EntityId] = None,
        home_forecast_provider_id: Optional[EntityId] = None,
        performance_tracker_id: Optional[EntityId] = None,
        notifier_ids: Optional[List[EntityId]] = None,
    ) -> EnergyOptimizationUnit:
        """Update an optimization unit in the system."""
        self.logger.info(f"Updating optimization unit {unit_id} ({name})")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        optimization_unit.name = name
        optimization_unit.description = description

        if is_enabled is not None:
            optimization_unit.is_enabled = is_enabled
        if policy_id is not None:
            optimization_unit.policy_id = policy_id
        if target_miner_ids is not None:
            optimization_unit.target_miner_ids = target_miner_ids
        if energy_source_id is not None:
            optimization_unit.energy_source_id = energy_source_id
        if home_forecast_provider_id is not None:
            optimization_unit.home_forecast_provider_id = home_forecast_provider_id
        if performance_tracker_id is not None:
            optimization_unit.performance_tracker_id = performance_tracker_id
        if notifier_ids is not None:
            optimization_unit.notifier_ids = notifier_ids

        self.check_optimization_unit(optimization_unit)

        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def activate_optimization_unit(self, unit_id: EntityId) -> EnergyOptimizationUnit:
        """Activate an optimization unit in the system."""
        self.logger.info(f"Activating optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        self.check_optimization_unit(optimization_unit)

        if optimization_unit.policy_id is None:
            raise OptimizationUnitConfigurationError(
                f"Optimization Unit {unit_id} must have a policy assigned before activation."
            )
        self.check_policy(optimization_unit.policy_id)

        optimization_unit.enable()

        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def deactivate_optimization_unit(self, unit_id: EntityId) -> EnergyOptimizationUnit:
        """Deactivate an optimization unit in the system."""
        self.logger.info(f"Deactivating optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        optimization_unit.disable()

        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def add_miner_to_optimization_unit(self, unit_id: EntityId, miner_id: EntityId) -> EnergyOptimizationUnit:
        """Add a miner to an optimization unit."""
        self.logger.info(f"Adding miner {miner_id} to optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        if miner_id not in optimization_unit.target_miner_ids:
            optimization_unit.target_miner_ids.append(miner_id)
        else:
            self.logger.warning(f"Miner {miner_id} is already part of the optimization unit {unit_id}.")

        self.check_optimization_unit(optimization_unit)

        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def remove_miner_from_optimization_unit(self, unit_id: EntityId, miner_id: EntityId) -> EnergyOptimizationUnit:
        """Remove a miner from an optimization unit."""
        self.logger.info(f"Removing miner {miner_id} from optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        if miner_id in optimization_unit.target_miner_ids:
            optimization_unit.target_miner_ids.remove(miner_id)
        else:
            self.logger.warning(f"Miner {miner_id} is not part of the optimization unit {unit_id}.")

        self.check_optimization_unit(optimization_unit)
        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def assign_policy_to_optimization_unit(self, unit_id: EntityId, policy_id: EntityId) -> EnergyOptimizationUnit:
        """Assign a policy to an optimization unit."""
        self.logger.info(f"Assigning policy {policy_id} to optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        optimization_unit.policy_id = policy_id
        self.check_optimization_unit(optimization_unit)
        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def assign_energy_source_to_optimization_unit(
        self, unit_id: EntityId, energy_source_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Assign an energy source to an optimization unit."""
        self.logger.info(f"Assigning energy source {energy_source_id} to optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        optimization_unit.energy_source_id = energy_source_id
        self.check_optimization_unit(optimization_unit)
        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def assign_home_forecast_provider_to_optimization_unit(
        self, unit_id: EntityId, home_forecast_provider_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Assign a home forecast provider to an optimization unit."""
        self.logger.info(f"Assigning home forecast provider {home_forecast_provider_id} to optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        optimization_unit.home_forecast_provider_id = home_forecast_provider_id
        self.check_optimization_unit(optimization_unit)
        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def assign_performance_tracker_to_optimization_unit(
        self, unit_id: EntityId, performance_tracker_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Assign a performance tracker to an optimization unit."""
        self.logger.info(f"Assigning performance tracker {performance_tracker_id} to optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        optimization_unit.performance_tracker_id = performance_tracker_id
        self.check_optimization_unit(optimization_unit)
        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def add_notifier_to_optimization_unit(self, unit_id: EntityId, notifier_id: EntityId) -> EnergyOptimizationUnit:
        """Add a notifier to an optimization unit."""
        self.logger.info(f"Adding notifier {notifier_id} to optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        if notifier_id not in optimization_unit.notifier_ids:
            optimization_unit.notifier_ids.append(notifier_id)
        else:
            self.logger.warning(f"Notifier {notifier_id} is already part of the optimization unit {unit_id}.")

        self.check_optimization_unit(optimization_unit)
        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def remove_notifier_from_optimization_unit(
        self, unit_id: EntityId, notifier_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Remove a notifier from an optimization unit."""
        self.logger.info(f"Removing notifier {notifier_id} from optimization unit {unit_id}")

        optimization_unit = self.optimization_unit_repo.get_by_id(unit_id)

        if not optimization_unit:
            raise OptimizationUnitNotFoundError(f"Optimization Unit with ID {unit_id} not found.")

        if notifier_id in optimization_unit.notifier_ids:
            optimization_unit.notifier_ids.remove(notifier_id)
        else:
            self.logger.warning(f"Notifier {notifier_id} is not part of the optimization unit {unit_id}.")

        self.check_optimization_unit(optimization_unit)
        self.optimization_unit_repo.update(optimization_unit)

        return optimization_unit

    def check_optimization_unit(self, optimization_unit: EnergyOptimizationUnit) -> bool:
        """Check if an optimization unit is valid and can be used."""
        self.logger.debug(f"Checking optimization unit {optimization_unit.id} ({optimization_unit.name})")

        if not optimization_unit:
            raise OptimizationUnitNotFoundError("Optimization Unit not found.")

        # Check id the policy is valid
        if optimization_unit.policy_id:
            policy = self.policy_repo.get_by_id(optimization_unit.policy_id)
            if not policy:
                raise PolicyNotFoundError(f"Optimization Policy with ID {optimization_unit.policy_id} not found.")

        # Check if the miners are valid
        if optimization_unit.target_miner_ids:
            for miner_id in optimization_unit.target_miner_ids:
                miner = self.miner_repo.get_by_id(miner_id)
                if not miner:
                    raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        # Check if the energy source is valid
        if optimization_unit.energy_source_id:
            energy_source = self.energy_source_repo.get_by_id(optimization_unit.energy_source_id)
            if not energy_source:
                raise EnergySourceNotFoundError(
                    f"Energy Source with ID {optimization_unit.energy_source_id} not found."
                )

        # Check if the home forecast provider is valid
        if optimization_unit.home_forecast_provider_id:
            home_forecast_provider = self.home_forecast_provider_repo.get_by_id(
                optimization_unit.home_forecast_provider_id
            )
            if not home_forecast_provider:
                raise HomeForecastProviderNotFoundError(
                    f"Home Forecast Provider with ID {optimization_unit.home_forecast_provider_id} not found."
                )

        # Check if the performance tracker is valid
        if optimization_unit.performance_tracker_id:
            performance_tracker = self.mining_performance_tracker_repo.get_by_id(
                optimization_unit.performance_tracker_id
            )
            if not performance_tracker:
                raise MiningPerformanceTrackerNotFoundError(
                    f"Mining Performance Tracker with ID {optimization_unit.performance_tracker_id} not found."
                )

        # Check if notifiers are valid
        if optimization_unit.notifier_ids:
            for notifier_id in optimization_unit.notifier_ids:
                notifier = self.notifier_repo.get_by_id(notifier_id)
                if not notifier:
                    raise NotifierNotFoundError(f"Notifier with ID {notifier_id} not found.")

        self.logger.debug(f"Optimization unit {optimization_unit.id} ({optimization_unit.name}) is valid.")
        return True

    # --- Miner Management ---
    def add_miner(
        self,
        name: str,
        status: MinerStatus = MinerStatus.UNKNOWN,
        hash_rate_max: Optional[HashRate] = None,
        power_consumption_max: Optional[Watts] = None,
        controller_id: Optional[EntityId] = None,
        active: bool = True,
    ) -> Miner:
        """Add a miner to the system."""

        hash_rate_str = f"{hash_rate_max.value}{hash_rate_max.unit}" if hash_rate_max else "Unknown"

        self.logger.info(
            f"Adding miner '{name}', "
            f"Max Hashrate: {hash_rate_str}, "
            f"Max Power: {power_consumption_max}W, Active: {active}"
        )

        miner = Miner(
            name=name,
            status=status,
            hash_rate_max=hash_rate_max,
            power_consumption_max=power_consumption_max,
            controller_id=controller_id,
            active=active,
        )

        self.check_miner(miner)
        self.miner_repo.add(miner)

        return miner

    def get_miner(self, miner_id: EntityId) -> Optional[Miner]:
        """Get a miner by its ID."""
        miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        return miner

    def list_miners(self) -> List[Miner]:
        """List all miners in the system."""
        return self.miner_repo.get_all()

    def remove_miner(self, miner_id: EntityId) -> Miner:
        """Remove a miner from the system."""
        self.logger.info(f"Removing miner {miner_id}")

        miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        self.miner_repo.remove(miner_id)

        return miner

    def update_miner(
        self,
        miner_id: EntityId,
        name: str,
        hash_rate_max: Optional[HashRate] = None,
        power_consumption_max: Optional[Watts] = None,
        controller_id: Optional[EntityId] = None,
        active: bool = True,
    ) -> Miner:
        """Update a miner in the system."""
        self.logger.info(f"Updating miner {miner_id} ({name})")

        miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        miner.name = name
        miner.hash_rate_max = hash_rate_max
        miner.power_consumption_max = power_consumption_max
        miner.controller_id = controller_id
        miner.active = active

        self.check_miner(miner)
        self.miner_repo.update(miner)

        return miner

    def activate_miner(self, miner_id: EntityId) -> Miner:
        """Activate a miner in the system."""
        self.logger.info(f"Activating miner {miner_id}")

        miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        miner.activate()

        self.miner_repo.update(miner)

        return miner

    def deactivate_miner(self, miner_id: EntityId) -> Miner:
        """Deactivate a miner in the system."""
        self.logger.info(f"Deactivating miner {miner_id}")

        miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        miner.deactivate()

        self.miner_repo.update(miner)

        return miner

    def list_miners_by_controller(self, controller_id: EntityId) -> List[Miner]:
        """List all miners associated with a specific controller."""
        miners: List[Miner] = self.miner_repo.get_by_controller_id(controller_id)

        if not miners:
            self.logger.warning(f"No miners found for controller {controller_id}")

        return miners

    def check_miner(self, miner: Miner) -> bool:
        """Check if a miner is valid and can be used."""
        self.logger.debug(f"Checking miner {miner.id} ({miner.name})")

        if not miner:
            raise MinerNotFoundError("Miner not found.")

        # Check if the controller exists
        if miner.controller_id:
            controller = self.miner_controller_repo.get_by_id(miner.controller_id)
            if not controller:
                raise MinerControllerNotFoundError(f"Miner Controller with ID {miner.controller_id} not found.")

        self.logger.debug(f"Miner {miner.id} ({miner.name}) is valid.")
        return True

    def add_miner_controller(
        self,
        name: str,
        adapter: MinerControllerAdapter,
        config: Optional[MinerControllerConfig],
        external_service_id: Optional[EntityId] = None,
    ) -> MinerController:
        """Add a miner controller to the system."""
        self.logger.info(f"Adding miner controller '{name}' with adapter {adapter}")

        controller = MinerController(
            name=name,
            adapter_type=adapter,
            config=config,
            external_service_id=external_service_id,
        )

        self.miner_controller_repo.add(controller)
        self.check_miner_controller(controller)

        return controller

    def get_miner_controller(self, controller_id: EntityId) -> Optional[MinerController]:
        """Get a miner controller by its ID."""
        controller = self.miner_controller_repo.get_by_id(controller_id)

        if not controller:
            raise MinerControllerNotFoundError(f"Controller with ID {controller_id} not found.")

        return controller

    def list_miner_controllers(self) -> List[MinerController]:
        """List all miner controllers in the system."""
        return self.miner_controller_repo.get_all()

    def unlink_miner_controller(self, miner_controller_id: EntityId) -> None:
        """Unlink a miner controller from all miners."""
        self.logger.info(f"Unlinking controller {miner_controller_id} from all miners")

        miners: List[Miner] = self.miner_repo.get_by_controller_id(miner_controller_id)

        for miner in miners:
            self.logger.info(f"Unlinking miner {miner.name} ({miner.id}) from controller {miner_controller_id}")
            miner.controller_id = None
            self.miner_repo.update(miner)

    def remove_miner_controller(self, controller_id: EntityId) -> MinerController:
        """Remove a miner controller from the system."""
        self.logger.info(f"Removing miner controller {controller_id}")

        controller = self.miner_controller_repo.get_by_id(controller_id)

        if not controller:
            raise MinerControllerNotFoundError(f"Controller with ID {controller_id} not found.")

        # Unlink the controller from all miners before removal
        self.unlink_miner_controller(controller_id)

        self.miner_controller_repo.remove(controller_id)

        return controller

    def update_miner_controller(
        self, controller_id: EntityId, name: str, config: MinerControllerConfig
    ) -> MinerController:
        """
        Update a miner controller in the system.
        This method updates the name and configuration only of an existing miner controller
        and avoid to change the adapter type.
        """
        self.logger.info(f"Updating miner controller {controller_id} ({name})")

        controller = self.miner_controller_repo.get_by_id(controller_id)

        if not controller:
            raise MinerControllerNotFoundError(f"Controller with ID {controller_id} not found.")

        # Check if the config is valid for the current adapter type
        config_type = MINER_CONTROLLER_CONFIG_TYPE_MAP[controller.adapter_type]
        if config_type and not isinstance(config, config_type):
            raise MinerControllerConfigurationError(
                f"Invalid configuration type for controller {controller_id}. "
                f"Expected {config_type}, "
                f"got {type(config).__name__}."
            )

        controller.name = name
        controller.config = config

        self.check_miner_controller(controller)

        self.miner_controller_repo.update(controller)

        return controller

    def set_miner_controller(self, controller_id: EntityId, miner_id: EntityId) -> None:
        """Set a miner controller to a miner."""
        self.logger.info(f"Adding controller {controller_id} to miner {miner_id}")

        miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        if not self.miner_controller_repo.get_by_id(controller_id):
            raise MinerControllerNotFoundError(f"Controller with ID {controller_id} does not exist.")

        miner.controller_id = controller_id
        self.miner_repo.update(miner)

    def check_miner_controller(self, controller: MinerController) -> bool:
        """Check if a miner controller is valid and can be used."""
        self.logger.debug(f"Checking miner controller {controller.id} ({controller.name})")

        # Checks if the configuration is valid for the given adapter type
        if controller.config is None or not controller.config.is_valid(controller.adapter_type):
            raise MinerControllerConfigurationError(
                f"Invalid configuration for Miner Controller {controller.name} with adapter {controller.adapter_type}."
            )

        self.logger.debug(f"Miner controller {controller.id} ({controller.name}) is valid.")
        return True

    def get_miner_controller_config_by_type(
        self, adapter_type: MinerControllerAdapter
    ) -> Optional[type[MinerControllerConfig]]:
        """Get the configuration class for a specific miner controller adapter type."""
        self.logger.debug(f"Getting configuration for miner controller adapter {adapter_type}")
        if adapter_type not in MINER_CONTROLLER_CONFIG_TYPE_MAP:
            raise MinerControllerConfigurationError(
                f"Adapter type {adapter_type} is not supported for miner controller configuration."
            )

        return MINER_CONTROLLER_CONFIG_TYPE_MAP.get(adapter_type, None)

    # --- Notifier Management ---
    def add_notifier(
        self,
        name: str,
        adapter_type: NotificationAdapter,
        config: NotificationConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> Notifier:
        """Add a new notifier."""
        self.logger.debug(f"Adding notifier '{name}' with adapter {adapter_type}")

        notifier = Notifier(
            name=name,
            adapter_type=adapter_type,
            config=config,
            external_service_id=external_service_id,
        )

        self.check_notifier(notifier)

        self.notifier_repo.add(notifier)

        return notifier

    def get_notifier(self, notifier_id: EntityId) -> Optional[Notifier]:
        """Get a notifier by its ID."""
        notifier = self.notifier_repo.get_by_id(notifier_id)
        if not notifier:
            raise NotifierNotFoundError(f"Notifier with ID {notifier_id} not found.")
        return notifier

    def list_notifiers(self) -> List[Notifier]:
        """List all notifiers in the system."""
        return self.notifier_repo.get_all()

    def remove_notifier(self, notifier_id: EntityId) -> Notifier:
        """Remove a notifier from the system."""
        self.logger.debug(f"Removing notifier {notifier_id}")

        notifier = self.notifier_repo.get_by_id(notifier_id)
        if not notifier:
            raise NotifierNotFoundError(f"Notifier with ID {notifier_id} not found.")

        self.notifier_repo.remove(notifier_id)
        return notifier

    def update_notifier(
        self,
        notifier_id: EntityId,
        name: str,
        adapter_type: NotificationAdapter,
        config: NotificationConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> Notifier:
        """Update a notifier in the system."""
        self.logger.debug(f"Updating notifier {notifier_id} ({name})")

        notifier = self.notifier_repo.get_by_id(notifier_id)
        if not notifier:
            raise NotifierNotFoundError(f"Notifier with ID {notifier_id} not found.")

        notifier.name = name
        notifier.adapter_type = adapter_type
        notifier.config = config
        notifier.external_service_id = external_service_id

        self.check_notifier(notifier)
        self.notifier_repo.update(notifier)

        return notifier

    def check_notifier(self, notifier: Notifier) -> bool:
        """Check if a notifier is valid and can be used."""
        self.logger.debug(f"Checking notifier {notifier.id} ({notifier.name})")

        if notifier.external_service_id:
            external_service = self.external_service_repo.get_by_id(notifier.external_service_id)
            if not external_service:
                raise ExternalServiceNotFoundError(
                    f"External Service with ID {notifier.external_service_id} not found."
                )

            # Checks if the external service is compatible with the notifier's adapter
            # type
            required_external_service_type = NOTIFIER_TYPE_EXTERNAL_SERVICE_MAP.get(notifier.adapter_type, None)
            if required_external_service_type and external_service.adapter_type != required_external_service_type:
                raise NotifierConfigurationError(
                    f"External Service {external_service.id} is not compatible "
                    f"with Notifier {notifier.name} using adapter "
                    f"{notifier.adapter_type}. "
                    f"Expected type {required_external_service_type}."
                )

        # Checks if the configuration is valid for the given adapter type
        if notifier.config is None or not notifier.config.is_valid(notifier.adapter_type):
            raise NotifierNotFoundError(
                f"Invalid configuration for Notifier {notifier.name} with adapter {notifier.adapter_type}."
            )

        self.logger.debug(f"Notifier {notifier.id} ({notifier.name}) is valid.")
        return True

    # --- Policy Management ---
    def create_policy(self, name: str, description: str = "") -> OptimizationPolicy:
        """Create a new policy."""
        self.logger.info(f"Creating policy '{name}'")

        policy = OptimizationPolicy(name=name, description=description)

        self.policy_repo.add(policy)

        return policy

    def get_policy(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        """Get a policy by its ID."""
        return self.policy_repo.get_by_id(policy_id)

    def list_policies(self) -> List[OptimizationPolicy]:
        """List all policies in the system."""
        return self.policy_repo.get_all()

    def add_rule_to_policy(
        self,
        policy_id: EntityId,
        rule_type: RuleType,
        name: str,
        priority: int,
        conditions: Dict,
        description: str = "",
    ) -> AutomationRule:
        """Add a rule to a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyNotFoundError(f"Policy with ID {policy_id} not found.")

        rule = AutomationRule(
            name=name,
            description=description,
            priority=priority,
            conditions=conditions,
        )
        if rule_type == RuleType.START:
            policy.start_rules.append(rule)
        elif rule_type == RuleType.STOP:
            policy.stop_rules.append(rule)
        else:
            raise PolicyConfigurationError(f"Invalid Rule Type. Must be {RuleType.START} or {RuleType.STOP}.")

        self.policy_repo.update(policy)
        self.logger.debug(f"Added {rule_type.value} rule '{name}' to policy '{policy.name}'")

        return rule

    def get_policy_rules(self, policy_id: EntityId, rule_type: RuleType) -> List[AutomationRule]:
        """Get all rules of a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        if rule_type == RuleType.START:
            return policy.start_rules
        elif rule_type == RuleType.STOP:
            return policy.stop_rules
        else:
            raise ValueError(f"Invalid rule_type. Must be {RuleType.START} or {RuleType.STOP}.")

    def get_policy_rule(self, policy_id: EntityId, rule_id: EntityId) -> Optional[AutomationRule]:
        """Get a rule by its ID."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        for rule in policy.start_rules + policy.stop_rules:
            if rule.id == rule_id:
                return rule

        raise PolicyError(f"Rule with ID {rule_id} not found in policy {policy_id}.")

    def update_policy_rule(
        self,
        policy_id: EntityId,
        rule_id: EntityId,
        name: str,
        priority: int,
        enabled: bool,
        conditions: Dict,
        description: str = "",
    ) -> AutomationRule:
        """Update a rule in a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyNotFoundError(f"Policy with ID {policy_id} not found.")

        for rule in policy.start_rules + policy.stop_rules:
            if rule.id == rule_id:
                rule.name = name
                rule.conditions = conditions
                rule.priority = priority
                rule.enabled = enabled

                if description:
                    rule.description = description

                self.policy_repo.update(policy)

                self.logger.info(f"Updated rule '{name}' in policy '{policy.name}'")

                return rule

        raise PolicyError(f"Rule with ID {rule_id} not found in policy {policy_id}.")

    def delete_policy_rule(self, policy_id: EntityId, rule_id: EntityId) -> AutomationRule:
        """Delete a rule from a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        for rule in policy.start_rules + policy.stop_rules:
            if rule.id == rule_id:
                if rule in policy.start_rules:
                    policy.start_rules.remove(rule)
                else:
                    policy.stop_rules.remove(rule)

                self.policy_repo.update(policy)

                self.logger.info(f"Deleted rule '{rule.name}' from policy '{policy.name}'")

                return rule
        raise PolicyError(f"Rule with ID {rule_id} not found in policy {policy_id}.")

    def enable_policy_rule(self, policy_id: EntityId, rule_id: EntityId) -> None:
        """Set a rule as enabled."""
        self.logger.info(f"Setting rule {rule_id} of policy {policy_id} as active.")

        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        # Find the rule in the policy's start or stop rules
        rule = None
        for r in policy.start_rules + policy.stop_rules:
            if r.id == rule_id:
                rule = r
                break

        if not rule:
            raise PolicyError(f"Rule with ID {rule_id} not found in policy {policy_id}.")

        # Set the rule as enabled
        rule.enabled = True
        self.policy_repo.update(policy)  # Persist change for each policy

    def delete_policy(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        """Delete a policy from the system."""
        self.logger.info(f"Deleting policy {policy_id}")

        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        self.policy_repo.remove(policy_id)

        self.logger.info(f"Policy {policy_id} | {policy.name} deleted successfully.")

        return policy

    def check_policy(self, policy_id: EntityId) -> bool:
        """Check if a policy is valid and can be used."""
        self.logger.debug(f"Checking policy {policy_id}")

        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        # Check if start rules contain at least one rule to stop the miner
        if not policy.start_rules or len(policy.start_rules) == 0:
            raise PolicyError("Policy must have at least one start rule with a STOP MINING action.")

        # Check if stop rules contain at least one rule to start the miner
        if not policy.stop_rules or len(policy.stop_rules) == 0:
            raise PolicyError("Policy must have at least one stop rule with a START MINING action.")

        self.logger.debug(f"Policy {policy.id} ({policy.name}) is valid.")
        return True

    def update_policy(
        self,
        policy_id: EntityId,
        name: str,
        description: str = "",
    ) -> OptimizationPolicy:
        """Update a policy in the system."""
        self.logger.info(f"Updating policy {policy_id} ({name})")

        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyNotFoundError(f"Policy with ID {policy_id} not found")

        policy.name = name
        policy.description = description

        self.logger.debug(f"Updated policy {name} ({policy_id})")
        self.policy_repo.update(policy)

        return policy

    def sort_policy_rules(self, policy_id: EntityId) -> None:
        """Sort the rules of a policy by priority."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyNotFoundError(f"Policy with ID {policy_id} not found")

        # Sort start rules by priority
        policy.start_rules.sort(key=lambda r: r.priority)
        # Sort stop rules by priority
        policy.stop_rules.sort(key=lambda r: r.priority)

        self.logger.info(f"Sorted rules for policy {policy.name} by priority")
        self.policy_repo.update(policy)

    # --- Settings Management ---
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        user_id: UserId = UserId("global_settings")
        settings: Optional[SystemSettings] = self.settings_repo.get_settings(user_id)
        return settings.settings if settings else {}

    def update_setting(self, key: str, value: Any) -> None:
        """Update a setting."""
        user_id: UserId = UserId("global_settings")
        settings = self.settings_repo.get_settings(user_id)

        if not settings:
            settings = SystemSettings(id=user_id)  # Create if doesn't exist

        self.logger.info(f"Updating setting '{key}' to '{value}'")

        settings.set_setting(key, value)

        self.settings_repo.save_settings(user_id, settings)
