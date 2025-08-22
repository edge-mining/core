"""
Collection of Aggregate Roots for the Energy Optimization domain
of the Edge Mining application.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from edge_mining.domain.common import AggregateRoot
from edge_mining.domain.miner.common import MinerStatus
from edge_mining.domain.policy.common import MiningDecision
from edge_mining.domain.policy.entities import AutomationRule
from edge_mining.domain.policy.services import RuleEngine
from edge_mining.domain.policy.value_objects import DecisionalContext


@dataclass
class OptimizationPolicy(AggregateRoot):
    """Aggregate Root for the Optimization Policy."""

    name: str = ""
    description: Optional[str] = None

    start_rules: List[AutomationRule] = field(default_factory=list)
    stop_rules: List[AutomationRule] = field(default_factory=list)

    def sort_rules(self) -> None:
        """Sort rules by priority."""
        self.start_rules.sort(key=lambda r: r.priority, reverse=True)
        self.stop_rules.sort(key=lambda r: r.priority, reverse=True)

    def decide_next_action(self, decisional_context: DecisionalContext, rule_engine: RuleEngine) -> MiningDecision:
        """
        Applies the policy rules to determine the next action.
        This is the core decision-making logic.
        """

        if not decisional_context.miner:
            raise ValueError("Error while evaluating policy: Miner is not set in the context.")

        print(f"Policy '{self.name}': Evaluating state for miner status {decisional_context.miner.status.name}")

        # Logic:
        # 1. If miner is OFF, check START rules. If any match -> START_MINING
        # 2. If miner is ON, check STOP rules. If any match -> STOP_MINING
        # 3. Otherwise -> MAINTAIN_STATE

        # This is the location where the magic happens!

        # Sort the rules by priority before evaluation
        self.sort_rules()

        # Load rules into the rule engine based on miner status
        if decisional_context.miner.status in [
            MinerStatus.OFF,
            MinerStatus.ERROR,
            MinerStatus.UNKNOWN,
        ]:
            rule_engine.load_rules(self.start_rules)

            # Evaluate the rules in the rule engine
            if rule_engine.evaluate(decisional_context):
                # If any START rule matches, return START_MINING decision
                return MiningDecision.START_MINING
        elif decisional_context.miner.status in [MinerStatus.ON]:
            rule_engine.load_rules(self.stop_rules)

            # Evaluate the rules in the rule engine
            if rule_engine.evaluate(decisional_context):
                # If any STOP rule matches, return STOP_MINING decision
                return MiningDecision.STOP_MINING
        else:
            # For STARTING/STOPPING states, usually maintain state until confirmed
            # ON/OFF
            return MiningDecision.MAINTAIN_STATE

        # If no rules matched, maintain the current state
        return MiningDecision.MAINTAIN_STATE
