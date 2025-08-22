"""
Aggregate Roots for the Optimization Unit.

Holds a reference to the policy to be used for the optimization, the target miners,
the energy source and so on.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from edge_mining.domain.common import AggregateRoot, EntityId


@dataclass
class EnergyOptimizationUnit(AggregateRoot):
    """Aggregate Root for the Energy Optimization Unit."""

    name: str = ""
    description: Optional[str] = None
    is_enabled: bool = False

    # References to entities
    policy_id: Optional[EntityId] = None  # Policy to be used for the optimization
    target_miner_ids: List[EntityId] = field(default_factory=list)  # Miners to be controlled
    energy_source_id: Optional[EntityId] = None  # Energy source to be used

    # References to adapters
    home_forecast_provider_id: Optional[EntityId] = None  # Home load forecast provider to be used
    performance_tracker_id: Optional[EntityId] = None  # Performance tracker to be used
    notifier_ids: List[EntityId] = field(default_factory=list)  # Notifiers to be used

    # We could add specific state attributes,
    # like the last energy snapshot or the last decision taken.
    # last_energy_snapshot: Optional[EnergyStateSnapshot] = None
    # last_decision: Optional[MiningDecision] = None

    def add_target_miner(self, miner_id: EntityId):
        """Add a target miner to the energy optimization unit."""
        if miner_id not in self.target_miner_ids:
            self.target_miner_ids.append(miner_id)

    def remove_target_miner(self, miner_id: EntityId):
        """Remove a target miner from the energy optimization unit."""
        if miner_id in self.target_miner_ids:
            self.target_miner_ids.remove(miner_id)

    def assign_policy(self, policy_id: EntityId):
        """Assign a policy to the energy optimization unit."""
        self.policy_id = policy_id

    def assign_energy_source(self, energy_source_id: EntityId):
        """Assign an energy source to the energy optimization unit."""
        self.energy_source_id = energy_source_id

    def assign_home_forecast_provider(self, home_forecast_provider_id: EntityId):
        """Assign a home load forecast provider to the energy optimization unit."""
        self.home_forecast_provider_id = home_forecast_provider_id

    def assign_performance_tracker(self, performance_tracker_id: EntityId):
        """Assign a performance tracker to the energy optimization unit."""
        self.performance_tracker_id = performance_tracker_id

    def add_notifier(self, notifier_id: EntityId):
        """Add a notifier to the energy optimization unit."""
        if notifier_id not in self.notifier_ids:
            self.notifier_ids.append(notifier_id)

    def remove_notifier(self, notifier_id: EntityId):
        """Remove a notifier from the energy optimization unit."""
        if notifier_id in self.notifier_ids:
            self.notifier_ids.remove(notifier_id)

    def enable(self):
        """Enable the energy optimization unit."""
        self.is_enabled = True

    def disable(self):
        """Disable the energy optimization unit."""
        self.is_enabled = False
