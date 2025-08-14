"""Collection of Aggregate Roots for the Energy Optimization domain of the Edge Mining application."""

from dataclasses import dataclass, field
from typing import List, Optional
import uuid

from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.policy.common import MiningDecision
from edge_mining.domain.policy.entities import AutomationRule
from edge_mining.domain.miner.common import MinerStatus, MinerId
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.forecast.value_objects import ForecastData
from edge_mining.domain.energy.value_objects import EnergyStateSnapshot

@dataclass
class OptimizationPolicy:
    """Aggregate Root for the Optimization Policy."""
    id: EntityId = field(default_factory=uuid.uuid4)
    name: str = ""
    description: Optional[str] = None
    is_active: bool = False
    # Could have different types of rules or grouped rules, but for now I have to make it simple! 🙃​
    start_rules: List[AutomationRule] = field(default_factory=list)
    stop_rules: List[AutomationRule] = field(default_factory=list)
    target_miner_ids: List[MinerId] = field(default_factory=list) # Which miners this policy applies to, needed if we have multiple miners.

    def decide_next_action(
        self,
        energy_state: EnergyStateSnapshot,
        forecast: Optional[ForecastData],
        home_load_forecast: Optional[Watts], # Added home load forecast
        current_miner_status: MinerStatus,
        hash_rate: Optional[HashRate],
        current_miner_power: Optional[Watts],
    ) -> MiningDecision:
        """
        Applies the policy rules to determine the next action.
        This is the core decision-making logic.
        """
        print(f"Policy '{self.name}': Evaluating state for miner status {current_miner_status.name}")

        # Logic:
        # 1. If miner is OFF, check START rules. If any match -> START_MINING
        # 2. If miner is ON, check STOP rules. If any match -> STOP_MINING
        # 3. Otherwise -> MAINTAIN_STATE

        # This is the location where the magic happens! 🪄​🎩

        if current_miner_status in [MinerStatus.OFF, MinerStatus.ERROR, MinerStatus.UNKNOWN]:
            for rule in self.start_rules:
                if rule.evaluate(energy_state, forecast, home_load_forecast, current_miner_status):
                    print(f"Policy '{self.name}': Start condition met by rule '{rule.name}'.")
                    return MiningDecision.START_MINING
            return MiningDecision.MAINTAIN_STATE # Stay off if no start rule matches

        elif current_miner_status == MinerStatus.ON:
            for rule in self.stop_rules:
                if rule.evaluate(energy_state, forecast, home_load_forecast, current_miner_status):
                    print(f"Policy '{self.name}': Stop condition met by rule '{rule.name}'.")
                    return MiningDecision.STOP_MINING
            return MiningDecision.MAINTAIN_STATE # Stay on if no stop rule matches

        # For STARTING/STOPPING states, usually maintain state until confirmed ON/OFF
        return MiningDecision.MAINTAIN_STATE
