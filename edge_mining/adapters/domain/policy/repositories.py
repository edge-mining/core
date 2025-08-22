"""
This module contains the adapter classes implementing the OptimizationPolicyRepository interface.
"""

import copy
import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import yaml
from pydantic import ValidationError

from edge_mining.adapters.domain.policy.schemas import (
    AutomationRuleSchema,
    LogicalGroupSchema,
    MetadataSchema,
    OptimizationPolicySchema,
    RuleConditionSchema,
)
from edge_mining.adapters.domain.policy.yaml.utils import CustomDumper
from edge_mining.adapters.infrastructure.persistence.sqlite import BaseSqliteRepository
from edge_mining.domain.common import EntityId
from edge_mining.domain.policy.aggregate_roots import AutomationRule, OptimizationPolicy
from edge_mining.domain.policy.exceptions import (
    PolicyConfigurationError,
    PolicyError,
    PolicyNotFoundError,
)
from edge_mining.domain.policy.ports import OptimizationPolicyRepository
from edge_mining.shared.logging.port import LoggerPort

# Simple In-Memory implementation for testing and basic use


class InMemoryOptimizationPolicyRepository(OptimizationPolicyRepository):
    """In-Memory implementation of the OptimizationPolicyRepository."""

    def __init__(
        self,
        initial_policies: Optional[Dict[EntityId, OptimizationPolicy]] = None,
    ):
        self._policies: Dict[EntityId, OptimizationPolicy] = copy.deepcopy(initial_policies) if initial_policies else {}

    def add(self, policy: OptimizationPolicy) -> None:
        if policy.id in self._policies:
            print(f"Warning: Policy {policy.id} already exists, overwriting.")
        self._policies[policy.id] = copy.deepcopy(policy)

    def get_by_id(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        return copy.deepcopy(self._policies.get(policy_id))

    def get_all(self) -> List[OptimizationPolicy]:
        return [copy.deepcopy(p) for p in self._policies.values()]

    def update(self, policy: OptimizationPolicy) -> None:
        if policy.id not in self._policies:
            raise ValueError(f"Policy {policy.id} not found for update.")
        self._policies[policy.id] = copy.deepcopy(policy)

    def remove(self, policy_id: EntityId) -> None:
        if policy_id not in self._policies:
            raise ValueError(f"Policy {policy_id} not found for removal.")
        del self._policies[policy_id]


class SqliteOptimizationPolicyRepository(OptimizationPolicyRepository):
    """SQLite implementation of the OptimizationPolicyRepository."""

    def __init__(self, db: BaseSqliteRepository):
        self._db = db
        self.logger = db.logger

        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables for the Optimization Policy domain if they do not exist."""
        self.logger.debug(f"Ensuring SQLite tables exist for Optimization Policy Repository in {self._db.db_path}...")
        sql_statements = [
            """
            CREATE TABLE IF NOT EXISTS policies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                start_rules TEXT, -- JSON list of AutomationRule dicts
                stop_rules TEXT  -- JSON list of AutomationRule dicts
            );
            """
        ]

        conn = self._db.get_connection()

        try:
            with conn:
                cursor = conn.cursor()
                for statement in sql_statements:
                    cursor.execute(statement)

                self.logger.debug("Optimization Policies tables checked/created successfully.")
        except sqlite3.Error as e:
            self.logger.error(f"Error creating SQLite tables: {e}")
            raise PolicyConfigurationError(f"DB error creating tables: {e}") from e
        finally:
            if conn:
                conn.close()

    def _dict_to_rule(self, data: Dict[str, Any]) -> AutomationRule:
        # Deserialize a dictionary (from JSON) into an AutomationRule object
        return AutomationRule(
            id=EntityId(uuid.UUID(data["id"])),  # Convert UUID string
            priority=data["priority"],
            name=data["name"],
            description=data["description"],
            enabled=data["enabled"],
            conditions=data["conditions"],
        )

    def _rule_to_dict(self, rule: AutomationRule) -> Dict[str, Any]:
        # Serializes an AutomationRule object into a dictionary for JSON
        return {
            "id": str(rule.id),
            "name": rule.name,
            "description": rule.description,
            "priority": rule.priority,
            "enabled": rule.enabled,
            "conditions": rule.conditions,
        }

    def _row_to_policy(self, row: sqlite3.Row) -> Optional[OptimizationPolicy]:
        if not row:
            return None
        try:
            # Deserialize JSON lists of rules and target IDs
            start_rules_data = json.loads(row["start_rules"] or "[]")
            stop_rules_data = json.loads(row["stop_rules"] or "[]")

            start_rules = [self._dict_to_rule(r) for r in start_rules_data]
            stop_rules = [self._dict_to_rule(r) for r in stop_rules_data]

            return OptimizationPolicy(
                id=row["id"],  # UUID is already converted by detect_types
                name=row["name"],
                description=row["description"],
                start_rules=start_rules,
                stop_rules=stop_rules,
            )
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error deserializing Policy from DB line: {dict(row)}. Error: {e}")
            return None

    def add(self, policy: OptimizationPolicy) -> None:
        self.logger.debug(f"Adding policy '{policy.name}' ({policy.id}) to SQLite.")
        sql = """
            INSERT INTO policies (id, name, description, start_rules, stop_rules)
            VALUES (?, ?, ?, ?, ?)
        """
        conn = self._db.get_connection()
        try:
            # Serialize rules and target IDs to JSON
            start_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.start_rules])
            stop_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.stop_rules])

            with conn:
                conn.execute(
                    sql,
                    (
                        policy.id,  # UUID
                        policy.name,
                        policy.description,
                        start_rules_json,
                        stop_rules_json,
                    ),
                )
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
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (policy_id,))  # Pass UUID directly
            row = cursor.fetchone()
            return self._row_to_policy(row)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting policy {policy_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_all(self) -> List[OptimizationPolicy]:
        self.logger.debug("Getting all policies from SQLite.")
        sql = "SELECT * FROM policies ORDER BY name"
        conn = self._db.get_connection()
        policies = []
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row in rows:
                policy = self._row_to_policy(row)
                if policy:
                    policies.append(policy)
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error getting all policies: {e}")
            return []
        finally:
            if conn:
                conn.close()
        return policies

    def update(self, policy: OptimizationPolicy) -> None:
        self.logger.debug(f"Updating policy '{policy.name}' ({policy.id}) in SQLite.")
        # Activation Management: If this policy becomes active, deactivates the others
        conn = self._db.get_connection()
        try:
            with conn:  # Transaction
                cursor = conn.cursor()

                # Update the current policy
                sql_update = """
                    UPDATE policies
                    SET name = ?, description = ?, start_rules = ?, stop_rules = ?
                    WHERE id = ?
                """
                start_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.start_rules])
                stop_rules_json = json.dumps([self._rule_to_dict(r) for r in policy.stop_rules])

                cursor.execute(
                    sql_update,
                    (
                        policy.name,
                        policy.description,
                        start_rules_json,
                        stop_rules_json,
                        policy.id,  # UUID
                    ),
                )

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
        conn = self._db.get_connection()
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


class YamlOptimizationPolicyRepository(OptimizationPolicyRepository):
    """YAML file-based implementation of OptimizationPolicyRepository."""

    def __init__(self, policies_directory: str, logger: Optional[LoggerPort] = None):
        """
        Initialize the YAML policy repository.

        Args:
            policies_directory: Path to the directory containing policy YAML files
            logger: Optional logger for debugging
        """
        self.policies_directory = Path(policies_directory)
        self.logger = logger

        # Create directory if it doesn't exist
        self.policies_directory.mkdir(parents=True, exist_ok=True)

        if self.logger:
            self.logger.debug(f"Initialized YamlOptimizationPolicyRepository with directory: {self.policies_directory}")

    def _get_policy_file_path(self, policy_id: EntityId) -> Path:
        """Get the file path for a policy based on its ID."""
        return Path(os.path.join(self.policies_directory.resolve(), f"{policy_id}.yaml"))

    def _get_policy_file_path_by_name(self, name: str) -> Path:
        """Get a potential file path for a policy based on its name (for searching)."""
        # Sanitize name for filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_name = safe_name.replace(" ", "_").lower()
        return Path(os.path.join(self.policies_directory, f"{safe_name}.yaml"))

    def _load_policy_from_file(self, file_path: Path) -> Tuple[Optional[OptimizationPolicy], Optional[MetadataSchema]]:
        """Load a policy from a YAML file."""
        try:
            # Check if the file exists
            if not os.path.isfile(file_path):
                return None, None

            with open(file_path, "r", encoding="utf-8") as f:
                yaml_content = yaml.safe_load(f)

            if yaml_content is None:
                if self.logger:
                    self.logger.warning(f"Empty YAML file: {file_path}")
                return None, None

            # Parse and validate the YAML content
            policy_schema = OptimizationPolicySchema(**yaml_content)

            # Removing extension from file name to use as policy ID
            file_name = os.path.split(file_path)[-1]
            file_name_id = file_name.replace(".yaml", "").strip()

            # Check if file name and ID match
            if not (file_name_id == policy_schema.id):
                if self.logger:
                    self.logger.warning(
                        f"Policy file name '{file_name_id}' does not match policy ID '{policy_schema.id}'. "
                        f"Using file name as ID: {file_name_id}"
                    )
                # Use the file name as the ID if they don't match
                policy_schema.id = file_name_id

            # Convert to domain objects
            policy_id = EntityId(cast(uuid.UUID, file_name_id))  # Use filename as ID

            # Convert AutomationRuleSchema to AutomationRule entities
            start_rules = self._load_and_sort_rules(policy_schema.start_rules)

            if len(start_rules) > 0:
                if self.logger:
                    self.logger.debug(f"Successfully loaded {len(start_rules)} start rules from {file_path}")
            else:
                if self.logger:
                    self.logger.warning(f"No start rules found in {file_path}")

            stop_rules = self._load_and_sort_rules(policy_schema.stop_rules)

            if len(stop_rules) > 0:
                if self.logger:
                    self.logger.debug(f"Successfully loaded {len(start_rules)} stop rules from {file_path}")
            else:
                if self.logger:
                    self.logger.warning(f"No stop rules found in {file_path}")

            # Create the OptimizationPolicy domain object
            policy = OptimizationPolicy(
                id=policy_id,
                name=policy_schema.name,
                description=policy_schema.description,
                start_rules=start_rules,
                stop_rules=stop_rules,
            )

            return policy, policy_schema.metadata

        except yaml.YAMLError as e:
            if self.logger:
                self.logger.error(f"YAML parsing error in {file_path}: {e}")
            raise PolicyError(f"Invalid YAML in policy file {file_path}: {e}") from e
        except ValueError as e:
            if self.logger:
                self.logger.error(f"Validation error in {file_path}: {e}")
            raise PolicyConfigurationError(f"Policy validation error in {file_path}: {e}") from e
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error loading policy from {file_path}: {e}")
            raise PolicyError(f"Failed to load policy from {file_path}: {e}") from e

    def _load_and_sort_rules(self, rule_schemas: List[AutomationRuleSchema]) -> List[AutomationRule]:
        """Load rule schemas and sort rules by priority."""
        rules: List[AutomationRule] = []

        if not rule_schemas:
            return []

        # Load the rules
        for rule_schema in rule_schemas:
            try:
                # rule_schema.model_validate()  # Validate the rule schema
                rule = self._schema_to_automation_rule(rule_schema)
                rules.append(rule)
            except ValidationError as e:
                if self.logger:
                    self.logger.error(
                        f"Validation error in rule schema {rule_schema.id} | {rule_schema.name}: {e}. Skipping rule..."
                    )

        # Sort by priority (highest first)
        return sorted(rules, key=lambda r: r.priority, reverse=True)

    def _schema_to_automation_rule(self, rule_schema: AutomationRuleSchema) -> AutomationRule:
        """Convert a rule schema to an AutomationRule entity."""

        # Create AutomationRule with YAML rule support
        return AutomationRule(
            id=EntityId(cast(uuid.UUID, rule_schema.id)),
            name=rule_schema.name,
            description=rule_schema.description or "",
            priority=rule_schema.priority,
            enabled=rule_schema.enabled,
            conditions=rule_schema.conditions.model_dump(),
        )

    def _save_policy_to_file(
        self,
        policy: OptimizationPolicy,
        metadata: Optional[MetadataSchema] = None,
    ) -> None:
        """Save a policy to a YAML file."""
        file_path = self._get_policy_file_path(policy.id)

        # Sort rules by priority before saving
        policy.sort_rules()

        try:
            # Convert OptimizationPolicy to OptimizationPolicySchema
            policy_schema = self._policy_to_schema(policy)

            if metadata:
                # Add metadata if provided
                policy_schema.metadata = metadata

            # Convert schema to dict for YAML serialization
            yaml_content = policy_schema.model_dump(exclude_none=True, exclude_unset=True)

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    yaml_content,
                    f,
                    Dumper=CustomDumper,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                    width=1000,
                    default_style=None,
                )

            if self.logger:
                self.logger.debug(f"Saved policy '{policy.name}' to {file_path}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save policy '{policy.name}' to {file_path}: {e}")
            raise PolicyError(f"Failed to save policy to file: {e}") from e

    def _policy_to_schema(self, policy: OptimizationPolicy) -> OptimizationPolicySchema:
        """Convert an OptimizationPolicy to OptimizationPolicySchema for YAML serialization."""
        try:
            # Convert start rules to schema format
            start_rules_schema = []
            for rule in policy.start_rules:
                rule_schema = self._automation_rule_to_schema(rule)
                start_rules_schema.append(rule_schema)

            # Convert stop rules to schema format
            stop_rules_schema = []
            for rule in policy.stop_rules:
                rule_schema = self._automation_rule_to_schema(rule)
                stop_rules_schema.append(rule_schema)

            # Create OptimizationPolicySchema instance
            return OptimizationPolicySchema(
                id=str(policy.id),  # Convert EntityId to string
                name=policy.name,
                description=policy.description,
                start_rules=start_rules_schema,
                stop_rules=stop_rules_schema,
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error converting policy '{policy.name}' to schema: {e}")
            raise PolicyError(f"Failed to convert policy to schema: {e}") from e

    def _automation_rule_to_schema(self, rule: AutomationRule) -> AutomationRuleSchema:
        """Convert an AutomationRule to a AutomationRuleSchema for YAML serialization."""
        try:
            return AutomationRuleSchema(
                id=str(rule.id),  # Convert UUID to string for YAML
                name=rule.name,
                description=rule.description,
                priority=rule.priority,
                enabled=rule.enabled,
                conditions=self._convert_conditions_to_schema(rule.conditions),  # Convert conditions to schema
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error converting rule '{rule.name}' to schema: {e}")
            raise PolicyError(f"Failed to convert rule to schema: {e}") from e

    def _convert_conditions_to_schema(self, conditions: dict) -> Union[LogicalGroupSchema, RuleConditionSchema]:
        try:
            if isinstance(conditions, dict):
                # Check if conditions are a logical group or a single rule condition
                conditions_dict_keys = set(conditions.keys())

                if conditions_dict_keys == LogicalGroupSchema.model_fields.keys():
                    # It's a logical group
                    return LogicalGroupSchema(**conditions)
                elif conditions_dict_keys == RuleConditionSchema.model_fields.keys():
                    # It's a single rule condition
                    return RuleConditionSchema(**conditions)
                else:
                    # It's an unknown format, raise an error
                    raise PolicyError(f"Invalid conditions format: {conditions}")
            else:
                # If conditions is not a dict, raise an error
                raise PolicyError(f"Expected conditions to be a dict, got {type(conditions)}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error converting conditions to schema: {e}")
            raise PolicyError(f"Failed to convert conditions to schema: {e}") from e

    # Repository interface implementation

    def add(self, policy: OptimizationPolicy) -> None:
        """Add a policy to the YAML repository."""
        if self.logger:
            self.logger.debug(f"Adding policy '{policy.name}' ({policy.id})")

        file_path = self._get_policy_file_path(policy.id)

        if file_path.exists():
            raise PolicyError(f"Policy with ID {policy.id} already exists")

        self._save_policy_to_file(policy)

    def get_by_id(self, policy_id: EntityId) -> Optional[OptimizationPolicy]:
        """Get a policy by its ID."""
        if self.logger:
            self.logger.debug(f"Getting policy {policy_id}")

        file_path = self._get_policy_file_path(policy_id)
        policy, metadata = self._load_policy_from_file(file_path)
        return policy

    def get_all(self) -> List[OptimizationPolicy]:
        """Get all policies from the YAML repository."""
        if self.logger:
            self.logger.debug("Getting all policies")

        policies: List[OptimizationPolicy] = []

        if not self.policies_directory.exists():
            if self.logger:
                self.logger.warning(f"Policies directory {self.policies_directory} does not exist")
            return policies

        if self.logger:
            self.logger.debug(f"Scanning policies directory: {self.policies_directory.resolve()}")

        try:
            # Scan the policies directory for YAML files
            for yaml_file in self.policies_directory.glob("*.yaml"):
                if yaml_file.is_file():
                    policy, metadata = self._load_policy_from_file(yaml_file)
                    if policy:
                        policies.append(policy)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error scanning policy directory: {e}")
            raise PolicyError(f"Failed to scan policies directory: {e}") from e

        return policies

    def update(self, policy: OptimizationPolicy) -> None:
        """Update a policy in the YAML repository."""
        if self.logger:
            self.logger.debug(f"Updating policy '{policy.name}' ({policy.id})")

        file_path = self._get_policy_file_path(policy.id)

        if not os.path.isfile(file_path):
            raise PolicyNotFoundError(f"Policy with ID {policy.id} not found")

        # Get existing policy metadata and update last modified date and version
        existing_policy, metadata = self._load_policy_from_file(file_path)
        if metadata:
            metadata = MetadataSchema(
                author=metadata.author,
                version=metadata.version,
                created=metadata.created,
                last_modified=metadata.last_modified,
            )
            metadata.last_modified = datetime.now().strftime("%Y-%m-%d")
            # Increment version
            metadata.version = metadata.version + 1 if metadata.version else 1

        self._save_policy_to_file(policy, metadata)

    def remove(self, policy_id: EntityId) -> None:
        """Remove a policy from the YAML repository."""
        if self.logger:
            self.logger.debug(f"Removing policy {policy_id}")

        file_path = self._get_policy_file_path(policy_id)

        if not file_path.exists():
            raise PolicyNotFoundError(f"Policy with ID {policy_id} not found")

        try:
            file_path.unlink()
            if self.logger:
                self.logger.debug(f"Removed policy file: {file_path}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to remove policy file {file_path}: {e}")
            raise PolicyError(f"Failed to remove policy file: {e}") from e
