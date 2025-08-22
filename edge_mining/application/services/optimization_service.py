"""
The Optimization Runner Service is responsible for running the optimization process.
It is responsible for:
- Evaluating the policy
- Getting the current energy state
- Getting the forecast
- Executing the decision
"""

import asyncio
from typing import List, Optional

from edge_mining.application.interfaces import (
    AdapterServiceInterface,
    SunFactoryInterface,
)
from edge_mining.domain.common import EntityId
from edge_mining.domain.energy.entities import EnergySource
from edge_mining.domain.energy.ports import EnergyMonitorPort, EnergySourceRepository
from edge_mining.domain.energy.value_objects import EnergyStateSnapshot
from edge_mining.domain.forecast.aggregate_root import Forecast
from edge_mining.domain.forecast.ports import ForecastProviderPort
from edge_mining.domain.home_load.ports import HomeForecastProviderPort
from edge_mining.domain.home_load.value_objects import ConsumptionForecast
from edge_mining.domain.miner.common import MinerStatus
from edge_mining.domain.miner.entities import Miner
from edge_mining.domain.miner.exceptions import MinerError
from edge_mining.domain.miner.ports import MinerControlPort, MinerRepository
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.notification.ports import NotificationPort
from edge_mining.domain.optimization_unit.aggregate_roots import EnergyOptimizationUnit
from edge_mining.domain.optimization_unit.ports import EnergyOptimizationUnitRepository
from edge_mining.domain.performance.ports import MiningPerformanceTrackerPort
from edge_mining.domain.policy.aggregate_roots import OptimizationPolicy
from edge_mining.domain.policy.common import MiningDecision
from edge_mining.domain.policy.exceptions import PolicyError
from edge_mining.domain.policy.ports import OptimizationPolicyRepository
from edge_mining.domain.policy.value_objects import DecisionalContext, Sun
from edge_mining.shared.logging.port import LoggerPort

from edge_mining.application.interfaces import OptimizationServiceInterface


class OptimizationService(OptimizationServiceInterface):
    """Service for the optimization process."""

    def __init__(
        self,
        optimization_unit_repo: EnergyOptimizationUnitRepository,
        energy_source_repo: EnergySourceRepository,
        policy_repo: OptimizationPolicyRepository,
        miner_repo: MinerRepository,
        adapter_service: AdapterServiceInterface,
        sun_factory: SunFactoryInterface,
        logger: Optional[LoggerPort] = None,
    ):
        # Domains

        # Repositories
        self.optimization_unit_repo = optimization_unit_repo
        self.energy_source_repo = energy_source_repo
        self.policy_repo = policy_repo
        self.miner_repo = miner_repo

        # Infrastructure
        self.sun_factory = sun_factory
        self.adapter_service = adapter_service
        self.logger = logger

    async def _notify_unit(self, notifiers: List[NotificationPort], title: str, message: str):
        """Notify the unit."""
        if not notifiers:
            return

        for notifier in notifiers:
            try:
                success = await notifier.send_notification(title, message)
                if not success:
                    if self.logger:
                        self.logger.warning(f"Notifier {type(notifier).__name__} reported failure for: {title}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to send notification via {type(notifier).__name__}: {e}")

    async def run_all_enabled_units(self):
        """Run the optimization process for all enabled units."""
        if self.logger:
            self.logger.info("Starting optimization run for all enabled units...")

        enabled_units = self.optimization_unit_repo.get_all_enabled()

        if not enabled_units:
            if self.logger:
                self.logger.info("No enabled energy optimization units found.")
            return

        unit_tasks = [self._process_unit(unit) for unit in enabled_units]
        # Don't stop for an error in a unit
        await asyncio.gather(*unit_tasks, return_exceptions=False)

        if self.logger:
            self.logger.info(f"Optimization run for all units finished. {len(enabled_units)} units processed.")

    async def _process_unit(self, optimization_unit: EnergyOptimizationUnit):
        if self.logger:
            self.logger.info(f"Processing Optimization Unit: '{optimization_unit.name}' (ID: {optimization_unit.id})")

        # --- Notifiers ---
        unit_notifiers: List[NotificationPort] = []
        unit_notifiers = self.adapter_service.get_notifiers(optimization_unit.notifier_ids)

        # --- Policy ---
        if not optimization_unit.policy_id:
            if self.logger:
                self.logger.warning(f"Optimization unit '{optimization_unit.name}' has no policy assigned. Skipping.")
            return
        policy: Optional[OptimizationPolicy] = None
        policy = self.policy_repo.get_by_id(optimization_unit.policy_id)
        if not policy:
            if self.logger:
                self.logger.error(
                    f"Policy ID {optimization_unit.policy_id} for optimization unit "
                    f"'{optimization_unit.name}' not found. Skipping."
                )
            return
        else:
            if self.logger:
                self.logger.info(f"Optimization unit '{optimization_unit.name}' > Using policy '{policy.name}'.")

        # --- Energy Source  ---
        energy_source: Optional[EnergySource] = None
        if optimization_unit.energy_source_id:
            energy_source = self.energy_source_repo.get_by_id(optimization_unit.energy_source_id)
        if not energy_source:
            if self.logger:
                self.logger.error(
                    f"Energy source for optimization unit '{optimization_unit.name}' "
                    f"(Config ID: {optimization_unit.energy_source_id}) not found "
                    f"or failed to initialize. Skipping optimization unit."
                )
            await self._notify_unit(
                unit_notifiers,
                f"Optimizer Error ({optimization_unit.name})",
                "Energy source unavailable.",
            )
            return
        else:
            if self.logger:
                self.logger.info(
                    f"Optimization unit '{optimization_unit.name}' > Using energy source '{energy_source.name}'."
                )

        # --- Energy Monitor ---
        energy_monitor: Optional[EnergyMonitorPort] = None
        if energy_source.energy_monitor_id:
            energy_monitor = self.adapter_service.get_energy_monitor(energy_source)
        if not energy_monitor:
            if self.logger:
                self.logger.error(
                    f"Energy monitor for energy source '{energy_source.name}' "
                    f"(Config ID: {energy_source.energy_monitor_id}) not found. "
                    f"Skipping optimization unit."
                )
            await self._notify_unit(
                unit_notifiers,
                f"Optimizer Error ({optimization_unit.name})",
                "Energy monitor unavailable.",
            )
            return

        # --- Forecast Provider ---
        forecast_provider: Optional[ForecastProviderPort] = None
        if energy_source.forecast_provider_id:
            forecast_provider = self.adapter_service.get_forecast_provider(energy_source)
        # Forecast is optional, so log a warning if it's missing but continue
        if not forecast_provider:
            if self.logger:
                self.logger.warning(
                    f"Forecast provider for energy source '{energy_source.name}' "
                    f"(Config ID: {energy_source.forecast_provider_id}) not found. "
                    f"Skipping optimization unit."
                )

        # --- Home Forecast Provider ---
        home_forecast_provider: Optional[HomeForecastProviderPort] = None
        if optimization_unit.home_forecast_provider_id:
            home_forecast_provider = self.adapter_service.get_home_load_forecast_provider(
                optimization_unit.home_forecast_provider_id
            )
        # Home forecast provider is optional, so log a warning if it's missing but
        # continue
        if not home_forecast_provider:
            if self.logger:
                self.logger.warning(
                    f"Home forecast provider for "
                    f"optimization unit '{optimization_unit.name}' "
                    f"(Config ID: {optimization_unit.home_forecast_provider_id}) "
                    "not found. Skipping forecast provider."
                )

        # --- Mining Performance Tracker ---
        mining_performance_tracker: Optional[MiningPerformanceTrackerPort] = None
        if optimization_unit.performance_tracker_id:
            mining_performance_tracker = self.adapter_service.get_mining_performance_tracker(
                optimization_unit.performance_tracker_id
            )
        # Mining performance tracker is optional, so log a warning if it's missing
        # but continue
        if not mining_performance_tracker:
            if self.logger:
                self.logger.warning(
                    f"Mining performance tracker for optimization unit "
                    f"'{optimization_unit.name}' "
                    f"(Config ID: {optimization_unit.performance_tracker_id}) not found. "
                    f"Skipping mining performance tracker."
                )

        # --- Energy State ---
        try:
            energy_state: Optional[EnergyStateSnapshot] = None
            energy_state = energy_monitor.get_current_energy_state()
            if not energy_state:
                if self.logger:
                    self.logger.error(
                        f"Could not retrieve energy state for optimization unit '{optimization_unit.name}'. Skipping."
                    )
                await self._notify_unit(
                    unit_notifiers,
                    f"Optimizer Error ({optimization_unit.name})",
                    "Failed to retrieve energy state.",
                )
                return
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting energy state for optimization unit '{optimization_unit.name}': {e}")
            await self._notify_unit(
                unit_notifiers,
                f"Optimizer Error ({optimization_unit.name})",
                f"Energy state error: {e}",
            )
            return

        # --- Solar Forecast ---
        forecast_data: Optional[Forecast] = None
        if forecast_provider:
            try:
                # Assuming the forecast provider needs parameters from its config,
                # or that the resolver has already injected them. If specific parameters
                # are needed for the optimization unit (e.g. lat/lon), they should be
                # part of the adapter's config or passed here if the resolver doesn't handle them.
                # For now, assuming the resolver provides a ready-to-use adapter.
                # (the configuration has already done outside of the edge mining application)

                forecast_data = forecast_provider.get_forecast()
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Error getting solar forecast for optimization unit '{optimization_unit.name}': {e}"
                    )
        else:
            if self.logger:
                self.logger.info(
                    f"No solar forecast provider configured for optimization unit '{optimization_unit.name}'."
                )

        # --- Home Load Forecast ---
        home_load_forecast: Optional[ConsumptionForecast] = None
        if home_forecast_provider:
            try:
                # TODO: Provide parameters if needed
                home_load_forecast = home_forecast_provider.get_home_consumption_forecast()
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Error getting home load forecast for optimization unit '{optimization_unit.name}': {e}"
                    )
        else:
            if self.logger:
                self.logger.info(
                    f"No home load forecast provider configured for optimization unit '{optimization_unit.name}'."
                )

        # --- Target Miners ---
        # Process each target miner in this optimization unit
        if not optimization_unit.target_miner_ids:
            if self.logger:
                self.logger.info(f"No target miners configured for optimization unit '{optimization_unit.name}'.")
            return

        # --- Mining Performance Tracker ---
        tracker_current_hashrate: Optional[HashRate] = None
        if mining_performance_tracker:
            try:
                # TODO: Provide parameters if needed
                miner_ids = optimization_unit.target_miner_ids
                tracker_current_hashrate = mining_performance_tracker.get_current_hashrate(miner_ids=miner_ids)
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Error getting mining performance tracker "
                        f"for optimization unit '{optimization_unit.name}': {e}"
                    )
                tracker_current_hashrate = None

        # Creates the Sun object for the current date.
        sun: Sun = self.sun_factory.create_sun_for_date()

        # Create the decisional context without the miner yet,
        # as we will add it later after fetching the miner status.
        # This allows us to have a single context for the unit.
        # The context will be updated for each miner in the unit.
        context = DecisionalContext(
            energy_source=energy_source,
            energy_state=energy_state,
            forecast=forecast_data,
            home_load_forecast=home_load_forecast,
            tracker_current_hashrate=tracker_current_hashrate,
            sun=sun,
        )

        # TODO: should we manage miners singularly or together?
        # TODO: should we serialize the miner process or run them in parallel?
        # For now, we will run them in parallel, but I imagine that is not the best approach
        # for tracking the energy used for each miner.
        miner_processing_tasks = []
        for miner_id in optimization_unit.target_miner_ids:
            miner_processing_tasks.append(
                self._process_single_miner_in_unit(
                    optimization_unit=optimization_unit,
                    policy=policy,
                    context=context,
                    miner_id=miner_id,
                    notifiers=unit_notifiers,
                )
            )
        await asyncio.gather(*miner_processing_tasks, return_exceptions=False)

        if self.logger:
            self.logger.info(
                f"Finished processing for optimization unit '{optimization_unit.name}'. "
                f"{len(miner_processing_tasks)} miners controlled."
            )

    async def _process_single_miner_in_unit(
        self,
        optimization_unit: EnergyOptimizationUnit,
        policy: OptimizationPolicy,
        context: DecisionalContext,
        miner_id: EntityId,
        notifiers: List[NotificationPort],
    ):
        # --- Miner ---
        miner: Optional[Miner] = None
        miner = self.miner_repo.get_by_id(miner_id)
        if not miner:
            if self.logger:
                self.logger.error(
                    f"Miner {miner_id} in optimization unit '{optimization_unit.name}' not found in repository."
                )
            message = f"Miner {miner_id} not found in optimization unit '{optimization_unit.name}'."
            await self._notify_unit(
                notifiers,
                f"Optimizer Error ({optimization_unit.name})",
                message,
            )
            return

        # --- Miner Controller ---
        miner_controller: Optional[MinerControlPort] = None
        if miner.controller_id:
            miner_controller = self.adapter_service.get_miner_controller(miner)
            if not miner_controller:
                if self.logger:
                    self.logger.error(
                        f"Controller for miner {miner_id} "
                        f"(Config ID: {miner.controller_id}) not found/initialized. "
                        f"Using default."
                    )
                message = f"Controller for miner {miner_id} not found in optimization unit '{optimization_unit.name}'."
                await self._notify_unit(
                    notifiers,
                    f"Optimizer Error ({optimization_unit.name})",
                    message,
                )

        if not miner_controller:
            if self.logger:
                self.logger.error(
                    f"No miner controller (specific or default) available "
                    f"for miner {miner_id} in optimization unit "
                    f"'{optimization_unit.name}'. Cannot control miner."
                )
            await self._notify_unit(
                notifiers,
                f"Optimizer Error ({optimization_unit.name} / {miner_id})",
                "Miner controller unavailable.",
            )
            return

        # Get current status and make decision
        try:
            # Update miner status using controller
            current_status = miner_controller.get_miner_status()
            current_hashrate = miner_controller.get_miner_hashrate()
            current_power = miner_controller.get_miner_power()

            # Update the domain model
            miner.update_status(
                new_status=current_status,
                hash_rate=current_hashrate,
                power=current_power,
            )

            # Persist the observed state
            self.miner_repo.update(miner)

            # Creates a copy of the context with the miner included, so that the policy
            # can access miner-specific data, without modifying the original context.
            # This is important to keep the context consistent across all miners in
            # the unit.
            decisional_context = DecisionalContext(
                energy_source=context.energy_source,
                energy_state=context.energy_state,
                forecast=context.forecast,
                home_load_forecast=context.home_load_forecast,
                tracker_current_hashrate=context.tracker_current_hashrate,
                sun=context.sun,
                miner=miner,  # Add the miner to the context
            )

            # Create the rule engine instance
            rule_engine = self.adapter_service.get_rule_engine()
            if not rule_engine:
                if self.logger:
                    self.logger.error(
                        f"Rule engine not available for optimization unit "
                        f"'{optimization_unit.name}'. Cannot process policy."
                    )
                await self._notify_unit(
                    notifiers,
                    f"Optimizer Error ({optimization_unit.name} / {miner_id})",
                    "Rule engine unavailable.",
                )
                return

            decision = policy.decide_next_action(decisional_context=decisional_context, rule_engine=rule_engine)
            if self.logger:
                self.logger.info(
                    f"Optimization unit '{optimization_unit.name}', "
                    f"Miner {miner_id}: Status={current_status.name}, "
                    f"Policy='{policy.name}', Decision={decision.name}"
                )

            await self._execute_miner_decision(
                miner_controller,
                miner_id,
                decision,
                current_status,
                notifiers,
                optimization_unit.name,
            )

        except (MinerError, PolicyError) as e:
            if self.logger:
                self.logger.error(
                    f"Domain error processing miner {miner_id} in optimization unit '{optimization_unit.name}': {e}"
                )
            await self._notify_unit(
                notifiers,
                f"Optimizer Error ({optimization_unit.name} / {miner_id})",
                f"Domain error: {e}",
            )
        except Exception as e:  # Other exceptions (e.g. IO from the controller)
            if self.logger:
                if self.logger:
                    self.logger.error(
                        f"Unexpected error processing miner {miner_id} "
                        f"in optimization unit '{optimization_unit.name}': {e}"
                    )
            await self._notify_unit(
                notifiers,
                f"Optimizer Error ({optimization_unit.name} / {miner_id})",
                f"Runtime error: {e}",
            )

    async def _execute_miner_decision(
        self,
        controller: MinerControlPort,
        miner_id: EntityId,
        decision: MiningDecision,
        current_status: MinerStatus,
        notifiers: List[NotificationPort],
        unit_name: str,
    ):
        action_taken = False
        success = False
        message_suffix = f" (Optimization Unit: {unit_name})"

        if decision == MiningDecision.START_MINING and current_status != MinerStatus.ON:
            if self.logger:
                self.logger.info(f"Executing START for miner {miner_id} via {type(controller).__name__}")
            success = controller.start_miner()
            action_taken = True
            if success:
                await self._notify_unit(
                    notifiers,
                    f"Miner Started: {miner_id}",
                    f"Miner {miner_id} was started." + message_suffix,
                )
            else:
                await self._notify_unit(
                    notifiers,
                    f"Miner Start Failed: {miner_id}",
                    f"Attempt to start miner {miner_id} failed." + message_suffix,
                )

        elif decision == MiningDecision.STOP_MINING and current_status == MinerStatus.ON:
            if self.logger:
                self.logger.info(f"Executing STOP for miner {miner_id} via {type(controller).__name__}")
            success = controller.stop_miner()
            action_taken = True
            if success:
                await self._notify_unit(
                    notifiers,
                    f"Miner Stopped: {miner_id}",
                    f"Miner {miner_id} was stopped." + message_suffix,
                )
            else:
                await self._notify_unit(
                    notifiers,
                    f"Miner Stop Failed: {miner_id}",
                    f"Attempt to stop miner {miner_id} failed." + message_suffix,
                )

        if action_taken and not success:
            if self.logger:
                self.logger.error(
                    f"Command {decision.name} for miner {miner_id} failed using controller {type(controller).__name__}."
                )
        elif action_taken and success:
            # We might want to update the expected state in the miner entity here,
            # and then the next iteration will confirm with get_miner_status.
            miner = self.miner_repo.get_by_id(miner_id)
            if miner:
                if decision == MiningDecision.START_MINING:
                    miner.turn_on()
                elif decision == MiningDecision.STOP_MINING:
                    miner.turn_off()
                self.miner_repo.update(miner)  # If the repo needs to track the state
