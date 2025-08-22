"""Rule condition evaluator for YAML-based rules."""

import re
from typing import Any, Union

from edge_mining.adapters.domain.policy.schemas import (
    LogicalGroupSchema,
    RuleConditionSchema,
)
from edge_mining.adapters.infrastructure.rule_engine.common import OperatorType
from edge_mining.domain.policy.value_objects import DecisionalContext


class RuleEvaluator:
    """Evaluates rule conditions against decisional context."""

    @staticmethod
    def evaluate_rule_conditions(
        context: DecisionalContext,
        conditions: Union[dict, RuleConditionSchema, LogicalGroupSchema],
    ) -> bool:
        """Evaluate rule conditions against the decisional context."""

        # Convert conditions to schema if they are in dict format
        if isinstance(conditions, dict):
            conditions = RuleEvaluator._convert_conditions_to_schema(conditions)

        if isinstance(conditions, RuleConditionSchema):
            return RuleEvaluator._evaluate_single_condition(context, conditions)
        elif isinstance(conditions, LogicalGroupSchema):
            return RuleEvaluator._evaluate_logical_group(context, conditions)
        else:
            raise ValueError(f"Unsupported condition type: {type(conditions)}")

    @staticmethod
    def _convert_conditions_to_schema(
        conditions: dict,
    ) -> Union[LogicalGroupSchema, RuleConditionSchema]:
        try:
            if isinstance(conditions, dict):
                # Check if conditions are a logical group or a single rule condition
                conditions_dict_keys = set(conditions.keys())

                if any(key in conditions_dict_keys for key in LogicalGroupSchema.model_fields.keys()):
                    # It's a logical group
                    return LogicalGroupSchema(**conditions)
                elif conditions_dict_keys == RuleConditionSchema.model_fields.keys():
                    # It's a single rule condition
                    return RuleConditionSchema(**conditions)
                else:
                    # It's an unknown format, raise an error
                    raise ValueError(f"Invalid conditions format in RuleEvaluator: {conditions}")
            else:
                # If conditions is not a dict, raise an error
                raise ValueError(f"Expected conditions to be a dict, got {type(conditions)}")
        except Exception as e:
            print(f"Error converting conditions to schema: {e}")
            raise

    @staticmethod
    def _evaluate_single_condition(context: DecisionalContext, condition: RuleConditionSchema) -> bool:
        """Evaluate a single condition."""
        try:
            # Get field value from context using dot notation
            field_value = RuleEvaluator._get_field_value(context, condition.field)

            if field_value is None:
                print(f"Field '{condition.field}' not found in context.")
                return False

            # Apply operator
            return RuleEvaluator._apply_operator(field_value, condition.operator, condition.value)

        except Exception as e:
            print(f"Error evaluating condition '{condition.field}': {e}")
            return False

    @staticmethod
    def _evaluate_logical_group(context: DecisionalContext, group: LogicalGroupSchema) -> bool:
        """Evaluate a logical group (AND/OR/NOT)."""
        if group.all_of:
            # ALL conditions must be true (AND)
            return all(RuleEvaluator.evaluate_rule_conditions(context, cond) for cond in group.all_of)

        elif group.any_of:
            # ANY condition must be true (OR)
            return any(RuleEvaluator.evaluate_rule_conditions(context, cond) for cond in group.any_of)

        elif group.not_:
            # NOT condition
            return not RuleEvaluator.evaluate_rule_conditions(context, group.not_)

        return False

    @staticmethod
    def _get_field_value(context: DecisionalContext, field_path: str) -> Any:
        """Get value from DecisionalContext using dot notation."""
        parts = field_path.split(".")
        current = context

        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    @staticmethod
    def _apply_operator(field_value: Any, operator: OperatorType, expected_value: Any) -> bool:
        """Apply comparison operator."""
        try:
            if operator == OperatorType.EQ:
                return bool(field_value == expected_value)
            elif operator == OperatorType.NE:
                return bool(field_value != expected_value)
            elif operator == OperatorType.GT:
                return float(field_value) > float(expected_value)
            elif operator == OperatorType.GTE:
                return float(field_value) >= float(expected_value)
            elif operator == OperatorType.LT:
                return float(field_value) < float(expected_value)
            elif operator == OperatorType.LTE:
                return float(field_value) <= float(expected_value)
            elif operator == OperatorType.IN:
                return field_value in expected_value
            elif operator == OperatorType.NOT_IN:
                return field_value not in expected_value
            elif operator == OperatorType.CONTAINS:
                return str(expected_value) in str(field_value)
            elif operator == OperatorType.STARTS_WITH:
                return str(field_value).startswith(str(expected_value))
            elif operator == OperatorType.ENDS_WITH:
                return str(field_value).endswith(str(expected_value))
            elif operator == OperatorType.REGEX:
                return bool(re.match(str(expected_value), str(field_value)))
            else:
                raise ValueError(f"Unsupported operator: {operator}")

        except (ValueError, TypeError) as e:
            print(f"Error applying operator {operator}: {e}")
            return False
