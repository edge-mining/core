"""Collection of Entities for the Energy Optimization domain of the Edge Mining application."""

from dataclasses import dataclass, field

from edge_mining.domain.common import Entity


@dataclass
class AutomationRule(Entity):
    """Entity for an automation rule."""

    name: str = ""
    description: str = ""
    priority: int = 0  # Priority for rule evaluation (higher numbers = higher priority)
    enabled: bool = True
    conditions: dict = field(default_factory=dict)
