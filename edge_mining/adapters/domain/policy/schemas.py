"""Validation schemas for optimization policies."""

import uuid
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from edge_mining.adapters.infrastructure.rule_engine.common import OperatorType


class RuleConditionSchema(BaseModel):
    """Single condition within a rule."""

    field: str = Field(..., description="Field path in DecisionalContext (dot notation)")
    operator: OperatorType = Field(..., description="Comparison operator")
    value: Union[int, float, str, bool, List[Union[int, float, str]]] = Field(
        ..., description="Value to compare against"
    )

    @field_validator("field")
    @classmethod
    def validate_field_path(cls, v):
        """Validate that field path is not empty and contains valid characters."""
        if not v or not isinstance(v, str):
            raise ValueError("Field path must be a non-empty string")

        # Basic validation - could be enhanced with actual field path checking
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._")
        if not all(c in allowed_chars for c in v):
            raise ValueError("Field path contains invalid characters")

        return v

    @field_validator("operator", mode="before")
    @classmethod
    def validate_operator(cls, v: Union[str, OperatorType]) -> OperatorType:
        """Validate operator type."""
        if isinstance(v, str):
            try:
                return OperatorType(v.lower())
            except KeyError as e:
                raise ValueError(f"Invalid operator: {v}. Must be one of {list(OperatorType)}") from e
        elif isinstance(v, OperatorType):
            return v
        else:
            raise ValueError("Operator must be a string or an OperatorType enum value")

    @field_serializer("operator")
    def serialize_operator(self, operator: OperatorType) -> str:
        """Serialize operator as string value."""
        return operator.value


class LogicalGroupSchema(BaseModel):
    """Logical grouping of conditions (AND/OR)."""

    all_of: Optional[List[Union[RuleConditionSchema, "LogicalGroupSchema"]]] = Field(
        None, description="All conditions must be true (AND logic)"
    )
    any_of: Optional[List[Union[RuleConditionSchema, "LogicalGroupSchema"]]] = Field(
        None, description="At least one condition must be true (OR logic)"
    )
    not_: Optional[Union[RuleConditionSchema, "LogicalGroupSchema"]] = Field(
        None, description="Negation of the condition/group"
    )

    @field_validator("all_of", "any_of")
    @classmethod
    def validate_logical_groups(cls, v: Optional[List]):
        """Ensure at least one logical operator is specified."""
        if v is None:
            return v
        if not isinstance(v, List) or len(v) == 0:
            raise ValueError("Logical group must be a non-empty list")
        return v

    @model_validator(mode="after")
    def validate_single_operator(self) -> "LogicalGroupSchema":
        """Ensure exactly one logical operator is specified."""
        operators = [self.all_of, self.any_of, self.not_]
        non_none_count = sum(1 for op in operators if op is not None)
        if non_none_count != 1:
            raise ValueError("Exactly one logical operator (all_of, any_of, not_) must be specified")
        return self


class AutomationRuleSchema(BaseModel):
    """Schema for a single automation rule."""

    id: Optional[str] = Field(
        None,
        description="Unique identifier for the rule (optional, can be auto-generated)",
    )
    name: str = Field(..., description="Unique name for the rule")
    description: Optional[str] = Field(None, description="Human-readable description")
    conditions: Union[LogicalGroupSchema, RuleConditionSchema] = Field(
        ..., description="Conditions that must be met for the rule to trigger"
    )
    priority: int = Field(
        default=0,
        description="Rule priority (higher numbers = higher priority)",
    )
    enabled: bool = Field(default=True, description="Whether the rule is active")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate rule ID and auto-generate if not provided."""
        if v is None or (isinstance(v, str) and len(v.strip()) == 0):
            # Auto-generate ID using UUID4
            return str(uuid.uuid4())

        if not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError("Rule ID must be a non-empty string")

        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate rule name."""
        if not v or not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError("Rule name must be a non-empty string")
        return v.strip()


class MetadataSchema(BaseModel):
    """Schema for optional metadata."""

    author: Optional[str] = Field(None, description="Author of the policy")
    version: Optional[int] = Field(None, description="Version of the policy schema")
    created: Optional[str] = Field(None, description="Creation date")
    last_modified: Optional[str] = Field(None, description="Last modified date")


class OptimizationPolicySchema(BaseModel):
    """Schema for an optimization policy."""

    id: Optional[str] = Field(
        None,
        description="Unique identifier for the policy (optional, can be auto-generated)",
    )
    name: str = Field(..., description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")

    # Rules embedded directly in the policy file
    start_rules: List[AutomationRuleSchema] = Field(default_factory=list, description="Rules for starting mining")
    stop_rules: List[AutomationRuleSchema] = Field(default_factory=list, description="Rules for stopping mining")

    # Metadata
    metadata: Optional[MetadataSchema] = Field(
        default_factory=lambda: MetadataSchema(
            author="Edge Mining User",
            version=1,
            created=datetime.now().strftime("%Y-%m-%d"),
            last_modified=datetime.now().strftime("%Y-%m-%d"),
        )
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate policy name."""
        if not v or not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError("Policy name must be a non-empty string")
        return v.strip()

    @field_validator("start_rules", "stop_rules")
    @classmethod
    def validate_rule_ids_unique(cls, v: List["OptimizationPolicySchema"]) -> List["OptimizationPolicySchema"]:
        """Ensure rule ids are unique within each rule type."""
        if not v:
            return v
        ids = [rule.id for rule in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate rule id found: {duplicates}")
        return v

    @model_validator(mode="after")
    def validate_overall_rule_ids(self) -> "OptimizationPolicySchema":
        """Ensure rule ids are unique across all rules in the policy."""
        all_rule_ids = []
        all_rule_ids.extend([rule.id for rule in self.start_rules])
        all_rule_ids.extend([rule.id for rule in self.stop_rules])

        if len(all_rule_ids) != len(set(all_rule_ids)):
            duplicates = [id for id in all_rule_ids if all_rule_ids.count(id) > 1]
            raise ValueError(f"Duplicate rule ids found across start and stop rules: {duplicates}")

        return self


# Update forward references
LogicalGroupSchema.model_rebuild()
