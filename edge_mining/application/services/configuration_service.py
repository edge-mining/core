"""Configuration service for managing miners, policies, and system settings."""
from typing import List, Optional, Dict, Any

from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.miner.entities import Miner
from edge_mining.domain.miner.common import MinerId
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.domain.policy.common import RuleType
from edge_mining.shared.logging.port import LoggerPort
from edge_mining.domain.miner.ports import MinerRepository
from edge_mining.domain.user.entities import SystemSettings
from edge_mining.domain.user.ports import SettingsRepository
from edge_mining.domain.exceptions import PolicyError, MinerError, MinerNotFoundError
from edge_mining.domain.policy.ports import OptimizationPolicyRepository
from edge_mining.domain.policy.aggregate_roots import OptimizationPolicy, AutomationRule, MiningDecision

class ConfigurationService:
    """Handles configuration of miners, policies, and system settings."""

    def __init__(
        self,
        miner_repo: MinerRepository,
        policy_repo: OptimizationPolicyRepository,
        settings_repo: SettingsRepository,
        logger: LoggerPort
    ):
        # Domains
        self.miner_repo = miner_repo
        self.policy_repo = policy_repo
        self.settings_repo = settings_repo
        
        # Infrastructure
        self.logger = logger

    # --- Miner Management ---
    def add_miner(self,
            name: str,
            ip_address: Optional[str] = None,
            hash_rate_max: Optional[HashRate] = None,
            power_consumption_max: Optional[Watts] = None,
            active: Optional[bool] = True
        ) -> Miner:
        """Add a miner to the system."""
        miner_id: MinerId = self.miner_repo.generate_id()

        self.logger.info(f"Adding miner {miner_id} ({name}), IP: {ip_address}, Max Hashrate: {hash_rate_max}, Max Power: {power_consumption_max}, Active: {active}")

        miner = Miner(id=miner_id, name=name, ip_address=ip_address, hash_rate_max=hash_rate_max, power_consumption_max=power_consumption_max, active=active)

        self.miner_repo.add(miner)

        return miner

    def get_miner(self, miner_id: MinerId) -> Optional[Miner]:
        """Get a miner by its ID."""
        miner: Miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        return miner

    def list_miners(self) -> List[Miner]:
        """List all miners in the system."""
        return self.miner_repo.get_all()

    def remove_miner(self, miner_id: MinerId) -> Miner:
        """Remove a miner from the system."""
        self.logger.info(f"Removing miner {miner_id}")

        miner: Miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        self.miner_repo.remove(miner_id)

        return miner

    def update_miner(self,
            miner_id: MinerId,
            name: str,
            ip_address: Optional[str] = None,
            hash_rate_max: Optional[HashRate] = None,
            power_consumption_max: Optional[Watts] = None,
            active: Optional[bool] = True
        ) -> Miner:
        """Update a miner in the system."""
        self.logger.info(f"Updating miner {miner_id} ({name})")

        miner: Miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        miner.name = name
        miner.ip_address = ip_address
        miner.hash_rate_max = hash_rate_max
        miner.power_consumption_max = power_consumption_max
        miner.active = active

        self.miner_repo.update(miner)

        return miner

    def activate_miner(self, miner_id: MinerId) -> Miner:
        """Activate a miner in the system."""
        self.logger.info(f"Activating miner {miner_id}")

        miner: Miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        miner.activate()

        self.miner_repo.update(miner)

        return miner

    def deactivate_miner(self, miner_id: MinerId) -> Miner:
        """Deactivate a miner in the system."""
        self.logger.info(f"Deactivating miner {miner_id}")

        miner: Miner = self.miner_repo.get_by_id(miner_id)

        if not miner:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found.")

        miner.deactivate()

        self.miner_repo.update(miner)

        return miner

    # --- Policy Management ---
    def create_policy(self, name: str, description: str = "", target_miner_ids: List[MinerId] = None) -> OptimizationPolicy:
        """Create a new policy."""
        self.logger.info(f"Creating policy '{name}'")

        if target_miner_ids is None:
            target_miner_ids = []

        # Validate miner IDs exist?
        policy = OptimizationPolicy(name=name, description=description, target_miner_ids=target_miner_ids)

        self.policy_repo.add(policy)

        return policy

    def get_policy(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        """Get a policy by its ID."""
        return self.policy_repo.get_by_id(policy_id)

    def list_policies(self) -> List[OptimizationPolicy]:
        """List all policies in the system."""
        return self.policy_repo.get_all()

    def add_rule_to_policy(self, policy_id: EntityId, rule_type: RuleType, name: str, conditions: Dict[str, Any], action: MiningDecision) -> AutomationRule:
        """Add a rule to a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        rule = AutomationRule(name=name, conditions=conditions, action=action)
        if rule_type == RuleType.START:
            policy.start_rules.append(rule)
        elif rule_type == RuleType.STOP:
            policy.stop_rules.append(rule)
        else:
            raise ValueError(f"Invalid rule_type. Must be {RuleType.START} or {RuleType.STOP}.")

        self.policy_repo.update(policy)
        self.logger.info(f"Added {rule_type} rule '{name}' to policy '{policy.name}'")

        return rule

    def get_policy_rules(self, policy_id: EntityId, rule_type: RuleType) -> List[AutomationRule]:
        """Get all rules of a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        if rule_type == RuleType.START:
            return policy.start_rules
        elif rule_type == RuleType.STOP:
            return policy.stop_rules
        else:
            raise ValueError(f"Invalid rule_type. Must be {RuleType.START} or {RuleType.STOP}.")

    def get_policy_rule(self, policy_id: EntityId, rule_id: EntityId) -> Optional[AutomationRule]:
        """Get a rule by its ID."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        for rule in policy.start_rules + policy.stop_rules:
            if rule.id == rule_id:
                return rule

        raise PolicyError(f"Rule with ID {rule_id} not found in policy {policy_id}.")

    def update_policy_rule(self, policy_id: EntityId, rule_id: EntityId, name: str, conditions: Dict[str, Any], action: MiningDecision) -> AutomationRule:
        """Update a rule in a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        for rule in policy.start_rules + policy.stop_rules:
            if rule.id == rule_id:
                rule.name = name
                rule.conditions = conditions
                rule.action = action
                self.policy_repo.update(policy)
                self.logger.info(f"Updated rule '{name}' in policy '{policy.name}'")

                return rule

        raise PolicyError(f"Rule with ID {rule_id} not found in policy {policy_id}.")

    def delete_policy_rule(self, policy_id: EntityId, rule_id: EntityId) -> AutomationRule:
        """Delete a rule from a policy."""
        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        for rule in policy.start_rules + policy.stop_rules:
            if rule.id == rule_id:
                if rule in policy.start_rules:
                    policy.start_rules.remove(rule)
                else:
                    policy.stop_rules.remove(rule)

                self.policy_repo.update(policy)

                self.logger.info(f"Deleted rule '{rule.name}' from policy '{policy.name}'")

                return rule
        raise PolicyError(f"Rule with ID {rule_id} not found in policy {policy_id}.")

    def set_active_policy(self, policy_id: EntityId) -> None:
        """Set a policy as active."""
        self.logger.info(f"Setting policy {policy_id} as active.")

        policies = self.policy_repo.get_all()

        found = False
        for p in policies:
            if p.id == str(policy_id):
                # Add checks for the presence and validation of rules before activating
                p.is_active = True
                found = True
            else:
                p.is_active = False
            self.policy_repo.update(p) # Persist change for each policy

        if not found:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

    def get_active_policy(self) -> Optional[OptimizationPolicy]:
        """Get the active policy."""
        return self.policy_repo.get_active_policy()

    def delete_policy(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        """Delete a policy from the system."""
        self.logger.info(f"Deleting policy {policy_id}")

        policy = self.policy_repo.get_by_id(policy_id)

        if not policy:
            raise PolicyError(f"Policy with ID {policy_id} not found.")

        self.policy_repo.remove(policy_id)

        self.logger.info(f"Policy {policy_id} | {policy.name} deleted successfully.")

        return policy
        
    # --- Settings Management ---
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        settings = self.settings_repo.get_settings()
        return settings.settings if settings else {}

    def update_setting(self, key: str, value: Any) -> None:
        """Update a setting."""
        settings = self.settings_repo.get_settings()

        if not settings:
            settings = SystemSettings() # Create if doesn't exist

        self.logger.info(f"Updating setting '{key}' to '{value}'")

        settings.set_setting(key, value)

        self.settings_repo.save_settings(settings)
