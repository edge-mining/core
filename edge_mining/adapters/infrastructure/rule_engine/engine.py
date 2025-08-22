"""Rule engine infrastructure adapter for automation rules."""

from typing import List

from edge_mining.adapters.infrastructure.rule_engine.custom.helpers import RuleEvaluator
from edge_mining.domain.policy.entities import AutomationRule
from edge_mining.domain.policy.services import RuleEngine
from edge_mining.domain.policy.value_objects import DecisionalContext
from edge_mining.shared.logging.port import LoggerPort


class CustomRuleEngine(RuleEngine):
    """Custom rule engine for automation rules."""

    def __init__(self, logger: LoggerPort):
        self.rules: List[AutomationRule] = []
        self.logger = logger

    def load_rules(self, rules: List[AutomationRule]) -> None:
        """Load rules"""

        # Store the rules
        self.rules = rules

        self.logger.debug(f"Successfully loaded {len(rules)} rules into CustomRuleEngine")

    def evaluate(self, context: DecisionalContext) -> bool:
        """
        Evaluate all rules against the decisional context.
        Returns True if any rule matches, False if no rules match
        """

        # Sort rules by priority (higher first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            try:
                if RuleEvaluator.evaluate_rule_conditions(context, rule.conditions):
                    self.logger.debug(f"Rule '{rule.name}' matched!")
                    return True  # Rule matched, return True
            except (ValueError, AttributeError) as e:
                self.logger.error(f"Error evaluating rule '{rule.name}': {e}")
                continue

        return False  # No rules matched, return False
