from typing import Optional

from edge_mining.domain.common import Watts
from edge_mining.shared.logging.port import LoggerPort
from edge_mining.domain.energy.ports import EnergyMonitorPort
from edge_mining.domain.policy.entities import MiningDecision
from edge_mining.domain.miner.common import MinerStatus, MinerId
from edge_mining.domain.exceptions import PolicyError, MinerError
from edge_mining.domain.forecast.ports import ForecastProviderPort
from edge_mining.domain.notification.ports import NotificationPort
from edge_mining.domain.forecast.value_objects import ForecastData
from edge_mining.domain.home_load.ports import HomeForecastProviderPort
from edge_mining.domain.energy.value_objects import EnergyStateSnapshot
from edge_mining.domain.policy.ports import OptimizationPolicyRepository
from edge_mining.domain.policy.aggregate_roots import OptimizationPolicy
from edge_mining.domain.miner.ports import MinerControlPort, MinerRepository

class MiningOrchestratorService:
    """Orchestrates the mining process based on energy, forecasts, and policies."""

    def __init__(
        self,
        energy_monitor: EnergyMonitorPort,
        miner_controller: MinerControlPort,
        forecast_provider: ForecastProviderPort,
        home_forecast_provider: HomeForecastProviderPort,
        policy_repo: OptimizationPolicyRepository,
        miner_repo: MinerRepository,
        notifier: Optional[NotificationPort] = None,
        logger: Optional[LoggerPort] = None,
    ):
        # Domains
        self.energy_monitor = energy_monitor
        self.miner_controller = miner_controller
        self.forecast_provider = forecast_provider
        self.home_forecast_provider = home_forecast_provider
        self.policy_repo = policy_repo
        self.miner_repo = miner_repo
        
        # Infrastructure
        self.notifier = notifier
        self.logger = logger

    def _notify(self, title: str, message: str):
        """Sends a notification using the configured notifier."""
        if self.notifier:
            try:
                self.notifier.send_notification(title, message)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to send notification: {e}")

    def evaluate_and_control_miners(self):
        """The main control loop evaluation triggered periodically."""
        if self.logger:
            self.logger.info("Starting evaluation cycle...")

        active_policy: Optional[OptimizationPolicy] = self.policy_repo.get_active_policy()
        if not active_policy:
            if self.logger:
                self.logger.warning("No active optimization policy found. Skipping evaluation.")
            return

        energy_state: Optional[EnergyStateSnapshot] = self.energy_monitor.get_current_energy_state()
        if not energy_state:
            if self.logger:
                self.logger.error("Could not retrieve current energy state. Skipping evaluation.")
            self._notify("Edge Mining Error", "Failed to retrieve energy state.")
            return

        solar_forecast: Optional[ForecastData] = self.forecast_provider.get_solar_forecast()
        if not solar_forecast:
            if self.logger:
                self.logger.warning("Could not retrieve solar forecast. Proceeding without it.")
            # Decide if this is critical or not - maybe policy needs forecast?

        home_load_forecast: Optional[Watts] = self.home_forecast_provider.get_home_consumption_forecast()
        if not home_load_forecast:
            if self.logger:
                self.logger.warning("Could not retrieve home load forecast. Proceeding without it.")


        # Apply policy to each targeted miner
        for miner_id in active_policy.target_miner_ids:
            try:
                miner = self.miner_repo.get_by_id(miner_id)
                if not miner:
                    if self.logger:
                        self.logger.error(f"Miner {miner_id} targeted by policy not found in repository.")
                    continue

                # Get current *actual* status from controller, not just repo's last known state
                current_status = self.miner_controller.get_miner_status(miner_id)

                # Maybe fetch power and hashrate too if needed by policy and they are provided by the miner
                current_power = self.miner_controller.get_miner_power(miner_id)
                hash_rate = self.miner_controller.get_miner_hashrate(miner_id)
                miner.update_status(
                    new_status=current_status,
                    hash_rate=hash_rate,
                    power=current_power
                )

                self.miner_repo.update(miner) # Persist the observed state

                # Here captures the intelligence 🚀​🚀​🚀​
                # ... wait, wait, wait ... it will do so in the future! 🤩​
                # At the moment, it's just a bunch of if elses. 😃
                decision = active_policy.decide_next_action(
                    energy_state=energy_state,
                    forecast=solar_forecast,
                    home_load_forecast=home_load_forecast,
                    current_miner_status=current_status,
                    current_miner_power=current_power,
                )

                self._execute_decision(miner_id, decision, current_status)

            except (PolicyError, MinerError, Exception) as e:
                if self.logger:
                    self.logger.error(f"Error processing miner {miner_id}: {e}")
                self._notify("Edge Miner Error", f"Error processing miner {miner_id}: {e}")


        if self.logger:
            self.logger.info("Evaluation cycle finished.")

    def _execute_decision(self, miner_id: MinerId, decision: MiningDecision, current_status: MinerStatus):
        """Executes the start/stop command based on the policy decision."""
        if self.logger:
            self.logger.info(f"Miner {miner_id}: Current Status={current_status}, Decision={decision.name}")

        if decision == MiningDecision.START_MINING and current_status != MinerStatus.ON:
            if self.logger:
                self.logger.info(f"Executing START command for miner {miner_id}")
            success = self.miner_controller.start_miner(miner_id)
            if success:
                # Optimistically update status, will be confirmed next cycle
                miner = self.miner_repo.get_by_id(miner_id)
                if miner:
                    miner.turn_on() # Update domain state
                    self.miner_repo.update(miner)
                self._notify("Edge Mining Info", f"Miner {miner_id} started.")
            else:
                if self.logger:
                    self.logger.error(f"Failed to send START command to miner {miner_id}")
                self._notify("Edge Mining Error", f"Failed START command for miner {miner_id}.")

        elif decision == MiningDecision.STOP_MINING and current_status == MinerStatus.ON:
            if self.logger:
                self.logger.info(f"Executing STOP command for miner {miner_id}")
            success = self.miner_controller.stop_miner(miner_id)
            if success:
                miner = self.miner_repo.get_by_id(miner_id)
                if miner:
                    miner.turn_off() # Update domain state
                    self.miner_repo.update(miner)
                self._notify("Edge Miner Info", f"Miner {miner_id} stopped.")
            else:
                if self.logger:
                    self.logger.error(f"Failed to send STOP command to miner {miner_id}")
                self._notify("Edge Miner Error", f"Failed STOP command for miner {miner_id}.")

        elif decision == MiningDecision.MAINTAIN_STATE:
            if self.logger:
                self.logger.debug(f"Miner {miner_id}: Maintaining current state ({current_status.name}).")

        else:
            if self.logger:
                self.logger.warning(f"Unhandled decision '{decision.name}' for miner {miner_id}")
