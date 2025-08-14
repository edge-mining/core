import copy
import uuid
import json
import sqlite3
from typing import List, Optional, Dict, Any

from edge_mining.domain.common import EntityId
from edge_mining.domain.exceptions import PolicyError
from edge_mining.domain.miner.common import MinerId
from edge_mining.domain.policy.aggregate_roots import OptimizationPolicy, AutomationRule
from edge_mining.domain.policy.common import MiningDecision
from edge_mining.domain.policy.ports import OptimizationPolicyRepository

from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository

# Simple In-Memory implementation for testing and basic use

class InMemoryOptimizationPolicyRepository(OptimizationPolicyRepository):
    """In-Memory implementation of the OptimizationPolicyRepository."""
    def __init__(self, initial_policies: Optional[Dict[EntityId, OptimizationPolicy]] = None):
        self._policies: Dict[EntityId, OptimizationPolicy] = copy.deepcopy(initial_policies) if initial_policies else {}

    def add(self, policy: OptimizationPolicy) -> None:
        if policy.id in self._policies:
            print(f"Warning: Policy {policy.id} already exists, overwriting.")
        self._policies[policy.id] = copy.deepcopy(policy)

    def get_by_id(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        return copy.deepcopy(self._policies.get(policy_id))

    def get_active_policy(self) -> Optional[OptimizationPolicy]:
        for policy in self._policies.values():
            if policy.is_active:
                return copy.deepcopy(policy)
        return None

    def get_all(self) -> List[OptimizationPolicy]:
        return [copy.deepcopy(p) for p in self._policies.values()]

    def update(self, policy: OptimizationPolicy) -> None:
        if policy.id not in self._policies:
            raise ValueError(f"Policy {policy.id} not found for update.")
        # Ensure only one policy is active if is_active is being set to True
        if policy.is_active:
            for p_id, p in self._policies.items():
                if p_id != policy.id and p.is_active:
                    p.is_active = False # Deactivate others
        self._policies[policy.id] = copy.deepcopy(policy)

    def remove(self, policy_id: EntityId) -> None:
        if policy_id not in self._policies:
            raise ValueError(f"Policy {policy_id} not found for removal.")
        del self._policies[policy_id]

class SqliteOptimizationPolicyRepository(BaseSqliteRepository, OptimizationPolicyRepository):
    """SQLite implementation of the OptimizationPolicyRepository."""

    def _dict_to_rule(self, data: Dict[str, Any]) -> AutomationRule:
        # Deserialize a dictionary (from JSON) into an AutomationRule object
        return AutomationRule(
            id=uuid.UUID(data['id']), # Convert UUID string
            name=data['name'],
            conditions=data['conditions'],
            action=MiningDecision(data['action']) # Convert Enum value
        )

    def _rule_to_dict(self, rule: AutomationRule) -> Dict[str, Any]:
        # Serializes an AutomationRule object into a dictionary for JSON
        return {
            'id': str(rule.id),
            'name': rule.name,
            'conditions': rule.conditions,
            'action': rule.action.value
        }

    def _row_to_policy(self, row: sqlite3.Row) -> Optional[OptimizationPolicy]:
        if not row:
            return None
        try:
            # Deserialize JSON lists of rules and target IDs
            start_rules_data = json.loads(row["start_rules"] or '[]')
            stop_rules_data = json.loads(row["stop_rules"] or '[]')
            target_ids_data = json.loads(row["target_miner_ids"] or '[]')

            start_rules = [self._dict_to_rule(r) for r in start_rules_data]
            stop_rules = [self._dict_to_rule(r) for r in stop_rules_data]
            target_ids = [MinerId(tid) for tid in target_ids_data]

            return OptimizationPolicy(
                id=row["id"], # UUID is already converted by detect_types
                name=row["name"],
                description=row["description"],
                is_active=bool(row["is_active"]),
                start_rules=start_rules,
                stop_rules=stop_rules,
                target_miner_ids=target_ids
            )
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error deserializing Policy from DB line: {dict(row)}. Error: {e}")
            return None

    def add(self, policy: OptimizationPolicy) -> None:
        self.logger.debug(f"Adding policy '{policy.name}' ({policy.id}) to SQLite.")
        sql = """
            INSERT INTO policies (id, name, description, is_active, start_rules, stop_rules, target_miner_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        conn = self._get_connection()
        try:
            # Serialize rules and target IDs to JSON
            start_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.start_rules])
            stop_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.stop_rules])
            target_ids_json = json.dumps([str(tid) for tid in policy.target_miner_ids])

            with conn:
                conn.execute(sql, (
                    policy.id, # UUID
                    policy.name,
                    policy.description,
                    1 if policy.is_active else 0,
                    start_rules_json,
                    stop_rules_json,
                    target_ids_json
                ))
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error adding policy '{policy.name}': {e}")
            raise PolicyError(f"Policy with ID {policy.id} or name '{policy.name}' already exists: {e}") from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error adding policy '{policy.name}': {e}")
            raise PolicyError(f"DB error adding policy: {e}") from e
        finally:
            if conn:
                conn.close()

    def get_by_id(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        self.logger.debug(f"Getting policy {policy_id} from SQLite.")
        sql = "SELECT * FROM policies WHERE id = ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (policy_id,)) # Pass UUID directly
            row = cursor.fetchone()
            return self._row_to_policy(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting policy {policy_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_active_policy(self) -> Optional[OptimizationPolicy]:
        self.logger.debug("Getting active policy from SQLite.")
        sql = "SELECT * FROM policies WHERE is_active = 1 LIMIT 1"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            return self._row_to_policy(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting active policy: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[OptimizationPolicy]:
        self.logger.debug("Getting all policies from SQLite.")
        sql = "SELECT * FROM policies ORDER BY name"
        conn = self._get_connection()
        policies = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                policy = self._row_to_policy(row)
                if policy:
                     policies.append(policy)
            return policies
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all policies: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update(self, policy: OptimizationPolicy) -> None:
        self.logger.debug(f"Updating policy '{policy.name}' ({policy.id}) in SQLite.")
        # Activation Management: If this policy becomes active, deactivates the others
        conn = self._get_connection()
        try:
            with conn: # Transaction
                cursor = conn.cursor()
                if policy.is_active:
                    self.logger.debug(f"Deactivating other policies as '{policy.name}' becomes active.")
                    cursor.execute("UPDATE policies SET is_active = 0 WHERE id != ?", (policy.id,))

                # Now update the current policy
                sql_update = """
                    UPDATE policies
                    SET name = ?, description = ?, is_active = ?, start_rules = ?, stop_rules = ?, target_miner_ids = ?
                    WHERE id = ?
                """
                start_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.start_rules])
                stop_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.stop_rules])
                target_ids_json = json.dumps([str(tid) for tid in policy.target_miner_ids])

                cursor.execute(sql_update, (
                    policy.name,
                    policy.description,
                    1 if policy.is_active else 0,
                    start_rules_json,
                    stop_rules_json,
                    target_ids_json,
                    policy.id # UUID
                ))

                if cursor.rowcount == 0:
                    raise PolicyError(f"No policies found with ID {policy.id}.")

        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error updating policy '{policy.name}': {e}")
            # There might be a conflict over the name UNIQUE
            raise PolicyError(f"Constraint error updating policy (duplicate name?): {e}") from e
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating policy '{policy.name}': {e}")
            raise PolicyError(f"EDB error updating policy: {e}") from e
        finally:
            if conn:
                conn.close()

    def remove(self, policy_id: EntityId) -> None:
        self.logger.debug(f"Removing policy {policy_id} from SQLite.")
        sql = "DELETE FROM policies WHERE id = ?"
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(sql, (policy_id,))
                if cursor.rowcount == 0:
                    raise PolicyError(f"No policies found with ID {policy_id}.")
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error removing policy {policy_id}: {e}")
            raise PolicyError(f"DB error removing policy: {e}") from e
        finally:
            if conn:
                conn.close()
