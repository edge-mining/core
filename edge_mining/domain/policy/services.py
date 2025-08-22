"""Domain services for the Energy Optimization domain."""

from abc import ABC, abstractmethod
from typing import List

from edge_mining.domain.policy.entities import AutomationRule
from edge_mining.domain.policy.value_objects import DecisionalContext


class RuleEngine(ABC):
    """Domain service for rule evaluation."""

    @abstractmethod
    def load_rules(self, rules: List[AutomationRule]) -> None:
        """
        Loads rules. This method should be called before evaluating any rules.
        """
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, context: DecisionalContext) -> bool:
        """
        Evaluates rules based on the given context and returns True if any rule matches.
        If no rules match, returns False.
        This is the core decision-making logic of the rule engine.
        """
        raise NotImplementedError
