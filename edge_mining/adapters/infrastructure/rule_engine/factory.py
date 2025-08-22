"""Factory for creating RuleEngine instances."""

from typing import Optional

from edge_mining.adapters.infrastructure.rule_engine.common import RuleEngineType
from edge_mining.adapters.infrastructure.rule_engine.engine import CustomRuleEngine
from edge_mining.domain.policy.services import RuleEngine
from edge_mining.shared.logging.port import LoggerPort


class RuleEngineFactory:
    """Factory for creating RuleEngine instances."""

    def create(
        self,
        engine_type: RuleEngineType = RuleEngineType.CUSTOM,
        logger: Optional[LoggerPort] = None,
    ) -> RuleEngine:
        """
        Creates a rule engine instance based on the specified type.
        """
        if not logger:
            raise ValueError("Logger is required to create a RuleEngine instance.")

        if engine_type == RuleEngineType.CUSTOM:
            # CustomRuleEngine is suitable for simple rule evaluations
            # where rules are loaded and evaluated in a straightforward manner.
            return CustomRuleEngine(logger=logger)
        else:
            raise ValueError(f"Unsupported rule engine type: {engine_type}")
        # Future extensions can include more complex rule engines
