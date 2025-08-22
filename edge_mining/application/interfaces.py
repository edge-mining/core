"""Edge Mining Application Interfaces Module"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter, EnergySourceType
from edge_mining.domain.energy.entities import EnergyMonitor, EnergySource
from edge_mining.domain.energy.ports import EnergyMonitorPort
from edge_mining.domain.energy.value_objects import Battery, Grid
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.domain.forecast.entities import ForecastProvider
from edge_mining.domain.forecast.ports import ForecastProviderPort
from edge_mining.domain.home_load.ports import HomeForecastProviderPort
from edge_mining.domain.miner.common import MinerControllerAdapter, MinerStatus
from edge_mining.domain.miner.entities import Miner, MinerController
from edge_mining.domain.miner.ports import MinerControlPort
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.notification.common import NotificationAdapter
from edge_mining.domain.notification.entities import Notifier
from edge_mining.domain.notification.ports import NotificationPort
from edge_mining.domain.optimization_unit.aggregate_roots import EnergyOptimizationUnit
from edge_mining.domain.performance.ports import MiningPerformanceTrackerPort
from edge_mining.domain.policy.aggregate_roots import AutomationRule, OptimizationPolicy
from edge_mining.domain.policy.common import RuleType
from edge_mining.domain.policy.services import RuleEngine
from edge_mining.domain.policy.value_objects import Sun
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.external_services.ports import ExternalServicePort
from edge_mining.shared.external_services.value_objects import ExternalServiceLinkedEntities
from edge_mining.shared.interfaces.config import (
    EnergyMonitorConfig,
    ExternalServiceConfig,
    ForecastProviderConfig,
    MinerControllerConfig,
    NotificationConfig,
)


class AdapterServiceInterface(ABC):
    """Base interface for all adapter services in the Edge Mining application."""

    @abstractmethod
    def get_energy_monitor(self, energy_source: EnergySource) -> Optional[EnergyMonitorPort]:
        """Get an energy monitor adapter instance."""

    @abstractmethod
    def get_miner_controller(self, miner: Miner) -> Optional[MinerControlPort]:
        """Get a miner controller adapter instance"""

    @abstractmethod
    def get_all_notifiers(self) -> List[NotificationPort]:
        """Get all notifier adapter instances"""

    @abstractmethod
    def get_notifier(self, notifier_id: EntityId) -> Optional[NotificationPort]:
        """Get a specific notifier adapter instance by ID."""

    @abstractmethod
    def get_notifiers(self, notifier_ids: List[EntityId]) -> List[NotificationPort]:
        """Get a list of specific notifiers adapter instance by IDs."""

    @abstractmethod
    def get_forecast_provider(self, energy_source: EnergySource) -> Optional[ForecastProviderPort]:
        """Get a forecast provider adapter instance."""

    @abstractmethod
    def get_home_load_forecast_provider(
        self, home_forecast_provider_id: EntityId
    ) -> Optional[HomeForecastProviderPort]:
        """Get an home load forecast provider adapter instance."""

    @abstractmethod
    def get_mining_performance_tracker(self, tracker_id: EntityId) -> Optional[MiningPerformanceTrackerPort]:
        """Get a mining performance tracker adapter instance."""

    @abstractmethod
    def get_external_service(self, external_service_id: EntityId) -> Optional[ExternalServicePort]:
        """Get a specific external service instance by ID."""

    @abstractmethod
    def get_rule_engine(self) -> Optional[RuleEngine]:
        """Get the rule engine instance."""

    @abstractmethod
    def clear_all_adapters(self):
        """Clear adapter chache"""

    @abstractmethod
    def remove_adapter(self, entity_id: EntityId):
        """Remove a specific adapter from the cache."""

    @abstractmethod
    def clear_all_services(self):
        """Clear external services chache"""

    @abstractmethod
    def remove_service(self, external_service_id: EntityId):
        """Remove a specific external seervice from the cache."""


class OptimizationServiceInterface(ABC):
    """Base interface for optimization services in the Edge Mining application."""

    @abstractmethod
    async def run_all_enabled_units(self):
        """Run the optimization process for all enabled units."""


class MinerActionServiceInterface(ABC):
    """Base interface for miner action services in the Edge Mining application."""

    @abstractmethod
    async def start_miner(self, miner_id: EntityId, notifiers: List[NotificationPort]) -> bool:
        """Start a specific miner."""

    @abstractmethod
    async def stop_miner(self, miner_id: EntityId, notifiers: List[NotificationPort]) -> bool:
        """Stop a specific miner."""

    @abstractmethod
    def get_miner_consumption(self, miner_id: EntityId) -> Optional[Watts]:
        """Gets the current power consumption of the specified miner."""

    @abstractmethod
    def get_miner_hashrate(self, miner_id: EntityId) -> Optional[HashRate]:
        """Gets the current hash rate of the specified miner."""


class ConfigurationServiceInterface(ABC):
    """Base interface for configuration services in the Edge Mining application."""

    # --- Miner Management ---
    @abstractmethod
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

    @abstractmethod
    def get_miner(self, miner_id: EntityId) -> Optional[Miner]:
        """Get a miner by its ID."""

    @abstractmethod
    def list_miners(self) -> List[Miner]:
        """List all miners in the system."""

    @abstractmethod
    def remove_miner(self, miner_id: EntityId) -> Miner:
        """Remove a miner from the system."""

    @abstractmethod
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

    @abstractmethod
    def activate_miner(self, miner_id: EntityId) -> Miner:
        """Activate a miner in the system."""

    @abstractmethod
    def deactivate_miner(self, miner_id: EntityId) -> Miner:
        """Deactivate a miner in the system."""

    @abstractmethod
    def list_miners_by_controller(self, controller_id: EntityId) -> List[Miner]:
        """List all miners associated with a specific controller."""

    @abstractmethod
    def check_miner(self, miner: Miner) -> bool:
        """Check if a miner is valid and can be used."""

    @abstractmethod
    def add_miner_controller(
        self,
        name: str,
        adapter: MinerControllerAdapter,
        config: MinerControllerConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> MinerController:
        """Add a miner controller to the system."""

    @abstractmethod
    def get_miner_controller(self, controller_id: EntityId) -> Optional[MinerController]:
        """Get a miner controller by its ID."""

    @abstractmethod
    def list_miner_controllers(self) -> List[MinerController]:
        """List all miner controllers in the system."""

    @abstractmethod
    def unlink_miner_controller(self, miner_controller_id: EntityId) -> None:
        """Unlink a miner controller from all miners."""

    @abstractmethod
    def remove_miner_controller(self, controller_id: EntityId) -> MinerController:
        """Remove a miner controller from the system."""

    @abstractmethod
    def update_miner_controller(
        self, controller_id: EntityId, name: str, config: MinerControllerConfig
    ) -> MinerController:
        """
        Update a miner controller in the system.
        This method updates the name and configuration only of an existing miner controller
        and avoid to change the adapter type.
        """

    @abstractmethod
    def set_miner_controller(self, controller_id: EntityId, miner_id: EntityId) -> None:
        """Set a miner controller to a miner."""

    @abstractmethod
    def check_miner_controller(self, controller: MinerController) -> bool:
        """Check if a miner controller is valid and can be used."""

    @abstractmethod
    def get_miner_controller_config_by_type(
        self, adapter_type: MinerControllerAdapter
    ) -> Optional[type[MinerControllerConfig]]:
        """Get the configuration class for a specific miner controller adapter type."""

    # --- Notifier Management ---
    @abstractmethod
    def add_notifier(
        self,
        name: str,
        adapter_type: NotificationAdapter,
        config: NotificationConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> Notifier:
        """Add a new notifier."""

    @abstractmethod
    def get_notifier(self, notifier_id: EntityId) -> Optional[Notifier]:
        """Get a notifier by its ID."""

    @abstractmethod
    def list_notifiers(self) -> List[Notifier]:
        """List all notifiers in the system."""

    @abstractmethod
    def remove_notifier(self, notifier_id: EntityId) -> Notifier:
        """Remove a notifier from the system."""

    @abstractmethod
    def update_notifier(
        self,
        notifier_id: EntityId,
        name: str,
        adapter_type: NotificationAdapter,
        config: NotificationConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> Notifier:
        """Update a notifier in the system."""

    @abstractmethod
    def check_notifier(self, notifier: Notifier) -> bool:
        """Check if a notifier is valid and can be used."""

    # --- Policy Management ---
    @abstractmethod
    def create_policy(self, name: str, description: str = "") -> OptimizationPolicy:
        """Create a new policy."""

    @abstractmethod
    def get_policy(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        """Get a policy by its ID."""

    @abstractmethod
    def list_policies(self) -> List[OptimizationPolicy]:
        """List all policies in the system."""

    @abstractmethod
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

    @abstractmethod
    def get_policy_rules(self, policy_id: EntityId, rule_type: RuleType) -> List[AutomationRule]:
        """Get all rules of a policy."""

    @abstractmethod
    def get_policy_rule(self, policy_id: EntityId, rule_id: EntityId) -> Optional[AutomationRule]:
        """Get a rule by its ID."""

    @abstractmethod
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

    @abstractmethod
    def delete_policy_rule(self, policy_id: EntityId, rule_id: EntityId) -> AutomationRule:
        """Delete a rule from a policy."""

    @abstractmethod
    def delete_policy(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        """Delete a policy from the system."""

    @abstractmethod
    def check_policy(self, policy_id: EntityId) -> bool:
        """Check if a policy is valid and can be used."""

    @abstractmethod
    def update_policy(
        self,
        policy_id: EntityId,
        name: str,
        description: str = "",
    ) -> OptimizationPolicy:
        """Update a policy in the system."""

    @abstractmethod
    def sort_policy_rules(self, policy_id: EntityId) -> None:
        """Sort the rules of a policy by priority."""

    # --- Optimization Unit Management ---
    @abstractmethod
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

    @abstractmethod
    def get_optimization_unit(self, unit_id: EntityId) -> Optional[EnergyOptimizationUnit]:
        """Get an optimization unit by its ID."""

    @abstractmethod
    def list_optimization_units(self) -> List[EnergyOptimizationUnit]:
        """List all optimization units in the system."""

    @abstractmethod
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

    @abstractmethod
    def remove_optimization_unit(self, unit_id: EntityId) -> EnergyOptimizationUnit:
        """Remove an optimization unit from the system."""

    @abstractmethod
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

    @abstractmethod
    def activate_optimization_unit(self, unit_id: EntityId) -> EnergyOptimizationUnit:
        """Activate an optimization unit in the system."""

    @abstractmethod
    def deactivate_optimization_unit(self, unit_id: EntityId) -> EnergyOptimizationUnit:
        """Deactivate an optimization unit in the system."""

    @abstractmethod
    def add_miner_to_optimization_unit(self, unit_id: EntityId, miner_id: EntityId) -> EnergyOptimizationUnit:
        """Add a miner to an optimization unit."""

    @abstractmethod
    def remove_miner_from_optimization_unit(self, unit_id: EntityId, miner_id: EntityId) -> EnergyOptimizationUnit:
        """Remove a miner from an optimization unit."""

    @abstractmethod
    def assign_policy_to_optimization_unit(self, unit_id: EntityId, policy_id: EntityId) -> EnergyOptimizationUnit:
        """Assign a policy to an optimization unit."""

    @abstractmethod
    def assign_energy_source_to_optimization_unit(
        self, unit_id: EntityId, energy_source_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Assign an energy source to an optimization unit."""

    @abstractmethod
    def assign_home_forecast_provider_to_optimization_unit(
        self, unit_id: EntityId, home_forecast_provider_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Assign a home forecast provider to an optimization unit."""

    @abstractmethod
    def assign_performance_tracker_to_optimization_unit(
        self, unit_id: EntityId, performance_tracker_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Assign a performance tracker to an optimization unit."""

    @abstractmethod
    def add_notifier_to_optimization_unit(self, unit_id: EntityId, notifier_id: EntityId) -> EnergyOptimizationUnit:
        """Add a notifier to an optimization unit."""

    @abstractmethod
    def remove_notifier_from_optimization_unit(
        self, unit_id: EntityId, notifier_id: EntityId
    ) -> EnergyOptimizationUnit:
        """Remove a notifier from an optimization unit."""

    @abstractmethod
    def check_optimization_unit(self, optimization_unit: EnergyOptimizationUnit) -> bool:
        """Check if an optimization unit is valid and can be used."""

    # --- External Service Management ---
    @abstractmethod
    def create_external_service(
        self,
        name: str,
        adapter_type: ExternalServiceAdapter,
        config: ExternalServiceConfig,
    ) -> ExternalService:
        """Create a new external service."""

    @abstractmethod
    def get_external_service(self, service_id: EntityId) -> Optional[ExternalService]:
        """Get an external service by its ID."""

    @abstractmethod
    def list_external_services(self) -> List[ExternalService]:
        """List all external services in the system."""

    @abstractmethod
    def get_entities_by_external_service(self, service_id: EntityId) -> ExternalServiceLinkedEntities:
        """Get entities associated with this external service"""

    @abstractmethod
    def unlink_external_service(self, service_id: EntityId) -> None:
        """Remove the association of an external service from all entities."""

    @abstractmethod
    def remove_external_service(self, service_id: EntityId) -> ExternalService:
        """Remove an external service from the system."""

    @abstractmethod
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

    @abstractmethod
    def check_external_service(self, external_service: ExternalService) -> bool:
        """Check if an external service is valid and can be used."""

    # --- Energy Source Management ---
    @abstractmethod
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

    @abstractmethod
    def get_energy_source(self, source_id: EntityId) -> Optional[EnergySource]:
        """Get an energy source by its ID."""

    @abstractmethod
    def list_energy_sources(self) -> List[EnergySource]:
        """List all energy sources in the system."""

    @abstractmethod
    def remove_energy_source(self, source_id: EntityId) -> EnergySource:
        """Remove an energy source from the system."""

    @abstractmethod
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

    @abstractmethod
    def check_energy_source(self, energy_source: EnergySource) -> bool:
        """Check if an energy source is valid and can be used."""

    @abstractmethod
    def create_energy_monitor(
        self,
        name: str,
        adapter_type: EnergyMonitorAdapter,
        config: EnergyMonitorConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> EnergyMonitor:
        """Create a new energy monitor."""

    @abstractmethod
    def get_energy_monitor(self, monitor_id: EntityId) -> Optional[EnergyMonitor]:
        """Get an energy monitor by its ID."""

    @abstractmethod
    def list_energy_monitors(self) -> List[EnergyMonitor]:
        """List all energy monitors in the system."""

    @abstractmethod
    def unlink_energy_monitor(self, monitor_id: EntityId) -> None:
        """Unlink an energy monitor from all associated energy sources."""

    @abstractmethod
    def remove_energy_monitor(self, monitor_id: EntityId) -> EnergyMonitor:
        """Remove an energy monitor from the system."""

    @abstractmethod
    def update_energy_monitor(
        self,
        monitor_id: EntityId,
        name: str,
        adapter_type: EnergyMonitorAdapter,
        config: EnergyMonitorConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> EnergyMonitor:
        """Update an energy monitor in the system."""

    @abstractmethod
    def set_energy_monitor_to_energy_source(
        self, energy_source_id: EntityId, energy_monitor_id: EntityId
    ) -> EnergySource:
        """Set an energy monitor to an energy source."""

    @abstractmethod
    def set_forecast_provider_to_energy_source(
        self, energy_source_id: EntityId, forecast_provider_id: EntityId
    ) -> EnergySource:
        """Set a forecast provider to an energy source."""

    @abstractmethod
    def list_energy_sources_by_monitor(self, monitor_id: EntityId) -> List[EnergySource]:
        """List all energy sources that use a specific energy monitor."""

    @abstractmethod
    def list_energy_sources_by_forecast_provider(self, forecast_provider_id: EntityId) -> List[EnergySource]:
        """List all energy sources that use a specific forecast provider."""

    @abstractmethod
    def check_energy_monitor(self, energy_monitor: EnergyMonitor) -> bool:
        """Check if an energy monitor is valid and can be used."""

    # --- Forecast Provider Management ---
    @abstractmethod
    def create_forecast_provider(
        self,
        name: str,
        adapter_type: ForecastProviderAdapter,
        config: ForecastProviderConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> ForecastProvider:
        """Create a new forecast provider."""

    @abstractmethod
    def get_forecast_provider(self, provider_id: EntityId) -> Optional[ForecastProvider]:
        """Get a forecast provider by its ID."""

    @abstractmethod
    def list_forecast_providers(self) -> List[ForecastProvider]:
        """List all forecast providers in the system."""

    @abstractmethod
    def remove_forecast_provider(self, provider_id: EntityId) -> ForecastProvider:
        """Remove a forecast provider from the system."""

    @abstractmethod
    def update_forecast_provider(
        self,
        provider_id: EntityId,
        name: str,
        adapter_type: ForecastProviderAdapter,
        config: ForecastProviderConfig,
        external_service_id: Optional[EntityId] = None,
    ) -> ForecastProvider:
        """Update a forecast provider in the system."""

    @abstractmethod
    def check_forecast_provider(self, provider: ForecastProvider) -> bool:
        """Check if a forecast provider is valid and can be used."""

    # --- Settings Management ---
    @abstractmethod
    def get_all_settings(self) -> dict:
        """Get all settings."""

    @abstractmethod
    def update_setting(self, key: str, value: Any) -> None:
        """Update a setting."""


class SunFactoryInterface(ABC):
    """Base interface for Sun factories in the Edge Mining application."""

    @abstractmethod
    def create_sun_for_date(self, for_date: datetime = datetime.now()) -> Sun:
        """Create a Sun object for a specific date."""
