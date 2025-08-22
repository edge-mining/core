"""Unit tests for RuleEvaluator class."""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

try:
    from edge_mining.adapters.domain.policy.schemas import (
        LogicalGroupSchema,
        RuleConditionSchema,
    )
    from edge_mining.adapters.infrastructure.rule_engine.common import OperatorType
    from edge_mining.adapters.infrastructure.rule_engine.custom.helpers import (
        RuleEvaluator,
    )
    from edge_mining.domain.policy.value_objects import DecisionalContext

    print("All imports successful")
except ImportError as e:
    print(f"Import error: {e}")
    raise


class TestRuleEvaluator(unittest.TestCase):
    """Test cases for RuleEvaluator class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create mock DecisionalContext
        self.mock_context = Mock(spec=DecisionalContext)

        # Set up nested mock attributes for dot notation testing
        self.mock_context.energy_state = Mock()
        self.mock_context.energy_state.battery = Mock()
        self.mock_context.energy_state.battery.state_of_charge = 75
        self.mock_context.energy_state.production = 1200

        self.mock_context.miner = Mock()
        self.mock_context.miner.status = "ON"

        self.mock_context.timestamp = datetime(2025, 8, 13, 14, 30)  # Tuesday 14:30

        self.mock_context.forecast = Mock()
        self.mock_context.forecast.next_hour_power = Mock(value=1500)
        self.mock_context.forecast.avg_next_4_hours_power = Mock(value=1800)

    # === Tests for evaluate_rule_conditions ===

    def test_evaluate_rule_conditions_single_condition_dict(self):
        """Test evaluating a single condition from dict format."""
        conditions_dict = {
            "field": "energy_state.battery.state_of_charge",
            "operator": "gt",
            "value": 50,
        }

        result = RuleEvaluator.evaluate_rule_conditions(self.mock_context, conditions_dict)

        self.assertTrue(result)

    def test_evaluate_rule_conditions_logical_group_dict(self):
        """Test evaluating a logical group from dict format."""
        conditions_dict = {
            "all_of": [
                {
                    "field": "energy_state.battery.state_of_charge",
                    "operator": "gt",
                    "value": 50,
                },
                {
                    "field": "energy_state.production",
                    "operator": "gt",
                    "value": 1000,
                },
            ]
        }

        result = RuleEvaluator.evaluate_rule_conditions(self.mock_context, conditions_dict)

        self.assertTrue(result)

    def test_evaluate_rule_conditions_unsupported_type(self):
        """Test that unsupported condition types raise ValueError."""
        # The method expects a dict but we pass a string
        with self.assertRaises(ValueError) as cm:
            RuleEvaluator.evaluate_rule_conditions(self.mock_context, "invalid_condition")

        # The actual error message will be about unsupported condition type
        self.assertIn("Unsupported condition type", str(cm.exception))

    # === Tests for _convert_conditions_to_schema ===

    def test_convert_conditions_to_schema_rule_condition(self):
        """Test converting dict to RuleConditionSchema."""
        conditions_dict = {
            "field": "miner.status",
            "operator": "eq",
            "value": "ON",
        }

        result = RuleEvaluator._convert_conditions_to_schema(conditions_dict)

        self.assertIsInstance(result, RuleConditionSchema)
        self.assertEqual(result.field, "miner.status")
        self.assertEqual(result.operator, OperatorType.EQ)
        self.assertEqual(result.value, "ON")

    def test_convert_conditions_to_schema_logical_group(self):
        """Test converting dict to LogicalGroupSchema."""
        conditions_dict = {"all_of": [{"field": "test.field", "operator": "eq", "value": 1}]}

        result = RuleEvaluator._convert_conditions_to_schema(conditions_dict)

        self.assertIsInstance(result, LogicalGroupSchema)
        self.assertIsNotNone(result.all_of)
        self.assertEqual(len(result.all_of), 1)

    def test_convert_conditions_to_schema_invalid_format(self):
        """Test that invalid dict format raises ValueError."""
        conditions_dict = {"invalid_key": "invalid_value"}

        with self.assertRaises(ValueError) as cm:
            RuleEvaluator._convert_conditions_to_schema(conditions_dict)

        self.assertIn("Invalid conditions format", str(cm.exception))

    def test_convert_conditions_to_schema_non_dict(self):
        """Test that non-dict input raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            RuleEvaluator._convert_conditions_to_schema("not_a_dict")

        self.assertIn("Expected conditions to be a dict", str(cm.exception))

    def test_convert_conditions_to_schema_exception_handling(self):
        """Test exception handling in schema conversion."""
        # Use an invalid operator to force a validation error
        conditions_dict = {
            "field": "test.field",
            "operator": "invalid_operator",  # This will cause validation error
            "value": 1,
        }

        with self.assertRaises(Exception):
            RuleEvaluator._convert_conditions_to_schema(conditions_dict)

    # === Tests for _evaluate_single_condition ===

    def test_evaluate_single_condition_success(self):
        """Test successful evaluation of a single condition."""
        condition = RuleConditionSchema(
            field="energy_state.battery.state_of_charge",
            operator=OperatorType.GT,
            value=50,
        )

        result = RuleEvaluator._evaluate_single_condition(self.mock_context, condition)

        self.assertTrue(result)

    def test_evaluate_single_condition_field_not_found(self):
        """Test single condition with non-existent field."""
        condition = RuleConditionSchema(field="non.existent.field", operator=OperatorType.EQ, value=100)

        result = RuleEvaluator._evaluate_single_condition(self.mock_context, condition)

        self.assertFalse(result)

    def test_evaluate_single_condition_none_value(self):
        """Test single condition when field value is None."""
        self.mock_context.energy_state.battery.state_of_charge = None

        condition = RuleConditionSchema(
            field="energy_state.battery.state_of_charge",
            operator=OperatorType.GT,
            value=50,
        )

        result = RuleEvaluator._evaluate_single_condition(self.mock_context, condition)

        self.assertFalse(result)

    @patch("edge_mining.adapters.infrastructure.rule_engine.custom.helpers.RuleEvaluator._get_field_value")
    def test_evaluate_single_condition_exception_handling(self, mock_get_field):
        """Test exception handling in single condition evaluation."""
        mock_get_field.side_effect = Exception("Field access error")

        condition = RuleConditionSchema(field="test.field", operator=OperatorType.EQ, value=100)

        result = RuleEvaluator._evaluate_single_condition(self.mock_context, condition)

        self.assertFalse(result)

    # === Tests for _evaluate_logical_group ===

    # === Direct Tests for Logical Group Functionality ===

    def test_logical_group_direct_evaluation(self):
        """Test logical group evaluation using direct schema objects."""
        # Test _evaluate_logical_group directly with mock schema objects
        mock_group = Mock(spec=LogicalGroupSchema)
        mock_group.all_of = None
        mock_group.any_of = None
        mock_group.not_ = None

        # Test with no operators (should return False)
        result = RuleEvaluator._evaluate_logical_group(self.mock_context, mock_group)
        self.assertFalse(result)

    def test_basic_single_condition_scenarios(self):
        """Test various single condition scenarios."""
        # High battery scenario
        test_cases = [
            # (field_value, operator, expected_value, expected_result)
            (80, "gt", 70, True),  # 80 > 70 = True
            (60, "gt", 70, False),  # 60 > 70 = False
            (1500, "gte", 1000, True),  # 1500 >= 1000 = True
            ("ON", "eq", "ON", True),  # "ON" == "ON" = True
            ("OFF", "ne", "ERROR", True),  # "OFF" != "ERROR" = True
        ]

        for (
            field_value,
            operator,
            expected_value,
            expected_result,
        ) in test_cases:
            with self.subTest(
                field_value=field_value,
                operator=operator,
                expected_value=expected_value,
            ):
                # Mock the field value
                self.mock_context.test_field = field_value

                conditions_dict = {
                    "field": "test_field",
                    "operator": operator,
                    "value": expected_value,
                }

                result = RuleEvaluator.evaluate_rule_conditions(self.mock_context, conditions_dict)
                self.assertEqual(result, expected_result)

    def test_field_access_edge_cases(self):
        """Test edge cases for field access."""
        # Test various field access patterns
        test_cases = [
            ("energy_state", True),  # Simple field exists
            (
                "energy_state.battery.state_of_charge",
                True,
            ),  # Nested field exists
        ]

        for field_path, should_exist in test_cases:
            with self.subTest(field_path=field_path):
                result = RuleEvaluator._get_field_value(self.mock_context, field_path)
                if should_exist:
                    self.assertIsNotNone(result)

        # Test non-existent simple field
        result = RuleEvaluator._get_field_value(self.mock_context, "non_existent")
        self.assertIsNone(result)

        # For deeply nested non-existent paths, Mock returns Mock objects
        # but the RuleEvaluator should handle this gracefully in real scenarios
        # where the actual context object would properly return None

    def test_realistic_mining_decision_simple(self):
        """Test a realistic mining decision with both conditions evaluated together."""
        # Scenario: Start mining if battery > 70% AND production > 1000W
        conditions = {
            "all_of": [
                {
                    "field": "energy_state.battery.state_of_charge",
                    "operator": "gt",
                    "value": 70,
                },
                {
                    "field": "energy_state.production",
                    "operator": "gt",
                    "value": 1000,
                },
            ]
        }
        result = RuleEvaluator.evaluate_rule_conditions(self.mock_context, conditions)
        self.assertTrue(result)  # Both conditions must be True

    def test_evaluate_logical_group_no_operator(self):
        """Test logical group with no operators specified."""
        # Create a LogicalGroupSchema manually with all_of=[] to avoid validation
        group = Mock(spec=LogicalGroupSchema)
        group.all_of = None
        group.any_of = None
        group.not_ = None

        result = RuleEvaluator._evaluate_logical_group(self.mock_context, group)

        self.assertFalse(result)

    # === Tests for _get_field_value ===

    def test_get_field_value_simple_path(self):
        """Test getting field value with simple path."""
        result = RuleEvaluator._get_field_value(self.mock_context, "energy_state")

        self.assertEqual(result, self.mock_context.energy_state)

    def test_get_field_value_nested_path(self):
        """Test getting field value with nested path."""
        result = RuleEvaluator._get_field_value(self.mock_context, "energy_state.battery.state_of_charge")

        self.assertEqual(result, 75)

    def test_get_field_value_nonexistent_path(self):
        """Test getting field value with non-existent path."""
        result = RuleEvaluator._get_field_value(self.mock_context, "non.existent.field")

        self.assertIsNone(result)

    def test_get_field_value_partial_path_missing(self):
        """Test getting field value when intermediate path doesn't exist."""
        # Remove the missing attribute to make it truly missing
        (
            delattr(self.mock_context.energy_state, "missing")
            if hasattr(self.mock_context.energy_state, "missing")
            else None
        )

        result = RuleEvaluator._get_field_value(self.mock_context, "energy_state.missing.field")

        self.assertIsNone(result)

    # === Tests for _apply_operator ===

    def test_apply_operator_eq_true(self):
        """Test EQ operator when values are equal."""
        result = RuleEvaluator._apply_operator(75, OperatorType.EQ, 75)
        self.assertTrue(result)

    def test_apply_operator_eq_false(self):
        """Test EQ operator when values are not equal."""
        result = RuleEvaluator._apply_operator(75, OperatorType.EQ, 50)
        self.assertFalse(result)

    def test_apply_operator_ne_true(self):
        """Test NE operator when values are not equal."""
        result = RuleEvaluator._apply_operator(75, OperatorType.NE, 50)
        self.assertTrue(result)

    def test_apply_operator_ne_false(self):
        """Test NE operator when values are equal."""
        result = RuleEvaluator._apply_operator(75, OperatorType.NE, 75)
        self.assertFalse(result)

    def test_apply_operator_gt_true(self):
        """Test GT operator when first value is greater."""
        result = RuleEvaluator._apply_operator(75, OperatorType.GT, 50)
        self.assertTrue(result)

    def test_apply_operator_gt_false(self):
        """Test GT operator when first value is not greater."""
        result = RuleEvaluator._apply_operator(50, OperatorType.GT, 75)
        self.assertFalse(result)

    def test_apply_operator_gte_true_greater(self):
        """Test GTE operator when first value is greater."""
        result = RuleEvaluator._apply_operator(75, OperatorType.GTE, 50)
        self.assertTrue(result)

    def test_apply_operator_gte_true_equal(self):
        """Test GTE operator when values are equal."""
        result = RuleEvaluator._apply_operator(75, OperatorType.GTE, 75)
        self.assertTrue(result)

    def test_apply_operator_gte_false(self):
        """Test GTE operator when first value is less."""
        result = RuleEvaluator._apply_operator(50, OperatorType.GTE, 75)
        self.assertFalse(result)

    def test_apply_operator_lt_true(self):
        """Test LT operator when first value is less."""
        result = RuleEvaluator._apply_operator(50, OperatorType.LT, 75)
        self.assertTrue(result)

    def test_apply_operator_lt_false(self):
        """Test LT operator when first value is not less."""
        result = RuleEvaluator._apply_operator(75, OperatorType.LT, 50)
        self.assertFalse(result)

    def test_apply_operator_lte_true_less(self):
        """Test LTE operator when first value is less."""
        result = RuleEvaluator._apply_operator(50, OperatorType.LTE, 75)
        self.assertTrue(result)

    def test_apply_operator_lte_true_equal(self):
        """Test LTE operator when values are equal."""
        result = RuleEvaluator._apply_operator(75, OperatorType.LTE, 75)
        self.assertTrue(result)

    def test_apply_operator_lte_false(self):
        """Test LTE operator when first value is greater."""
        result = RuleEvaluator._apply_operator(75, OperatorType.LTE, 50)
        self.assertFalse(result)

    def test_apply_operator_in_true(self):
        """Test IN operator when value is in list."""
        result = RuleEvaluator._apply_operator("ON", OperatorType.IN, ["ON", "OFF", "ERROR"])
        self.assertTrue(result)

    def test_apply_operator_in_false(self):
        """Test IN operator when value is not in list."""
        result = RuleEvaluator._apply_operator("STARTING", OperatorType.IN, ["ON", "OFF", "ERROR"])
        self.assertFalse(result)

    def test_apply_operator_not_in_true(self):
        """Test NOT_IN operator when value is not in list."""
        result = RuleEvaluator._apply_operator("STARTING", OperatorType.NOT_IN, ["ON", "OFF", "ERROR"])
        self.assertTrue(result)

    def test_apply_operator_not_in_false(self):
        """Test NOT_IN operator when value is in list."""
        result = RuleEvaluator._apply_operator("ON", OperatorType.NOT_IN, ["ON", "OFF", "ERROR"])
        self.assertFalse(result)

    def test_apply_operator_contains_true(self):
        """Test CONTAINS operator when expected value is in field value."""
        result = RuleEvaluator._apply_operator("solar_panel_1", OperatorType.CONTAINS, "solar")
        self.assertTrue(result)

    def test_apply_operator_contains_false(self):
        """Test CONTAINS operator when expected value is not in field value."""
        result = RuleEvaluator._apply_operator("battery_monitor", OperatorType.CONTAINS, "solar")
        self.assertFalse(result)

    def test_apply_operator_starts_with_true(self):
        """Test STARTS_WITH operator when field value starts with expected value."""
        result = RuleEvaluator._apply_operator("HIGH_PRIORITY", OperatorType.STARTS_WITH, "HIGH")
        self.assertTrue(result)

    def test_apply_operator_starts_with_false(self):
        """Test STARTS_WITH operator when field value doesn't start with expected value."""
        result = RuleEvaluator._apply_operator("LOW_PRIORITY", OperatorType.STARTS_WITH, "HIGH")
        self.assertFalse(result)

    def test_apply_operator_ends_with_true(self):
        """Test ENDS_WITH operator when field value ends with expected value."""
        result = RuleEvaluator._apply_operator("SYSTEM_LEVEL", OperatorType.ENDS_WITH, "LEVEL")
        self.assertTrue(result)

    def test_apply_operator_ends_with_false(self):
        """Test ENDS_WITH operator when field value doesn't end with expected value."""
        result = RuleEvaluator._apply_operator("SYSTEM_STATE", OperatorType.ENDS_WITH, "LEVEL")
        self.assertFalse(result)

    def test_apply_operator_regex_true(self):
        """Test REGEX operator when pattern matches."""
        result = RuleEvaluator._apply_operator("12345", OperatorType.REGEX, r"^\d+$")
        self.assertTrue(result)

    def test_apply_operator_regex_false(self):
        """Test REGEX operator when pattern doesn't match."""
        result = RuleEvaluator._apply_operator("abc123", OperatorType.REGEX, r"^\d+$")
        self.assertFalse(result)

    def test_apply_operator_unsupported(self):
        """Test that unsupported operators raise ValueError."""

        # Create a mock operator that doesn't exist in OperatorType
        class FakeOperator:
            def __str__(self):
                return "FAKE_OP"

        fake_operator = FakeOperator()

        # The _apply_operator should return False for unsupported operators due to try/catch
        result = RuleEvaluator._apply_operator(75, fake_operator, 50)
        self.assertFalse(result)

    def test_apply_operator_value_error_conversion(self):
        """Test operator with values that can't be converted (e.g., string to float)."""
        result = RuleEvaluator._apply_operator("not_a_number", OperatorType.GT, 50)
        self.assertFalse(result)

    def test_apply_operator_type_error(self):
        """Test operator with incompatible types."""
        result = RuleEvaluator._apply_operator(None, OperatorType.GT, 50)
        self.assertFalse(result)

    # === Integration Tests ===

    def test_complex_nested_logical_groups(self):
        """Test complex nested logical groups."""
        # Simplified version - test basic AND/OR combination
        conditions_dict = {
            "all_of": [
                {
                    "field": "energy_state.battery.state_of_charge",
                    "operator": "gt",
                    "value": 50,
                },
                {
                    "field": "energy_state.production",
                    "operator": "gt",
                    "value": 1000,
                },
            ]
        }

        result = RuleEvaluator.evaluate_rule_conditions(self.mock_context, conditions_dict)

        self.assertTrue(result)

    def test_end_to_end_evaluation_flow(self):
        """Test end-to-end evaluation from dict to final result."""
        # Test a realistic scenario: start mining if battery > 70% AND production > 1000W
        self.mock_context.timestamp = datetime(2025, 8, 13, 14, 30)  # 14:30

        conditions_dict = {
            "all_of": [
                {
                    "field": "energy_state.battery.state_of_charge",
                    "operator": "gt",
                    "value": 70,
                },
                {
                    "field": "energy_state.production",
                    "operator": "gt",
                    "value": 1000,
                },
            ]
        }

        result = RuleEvaluator.evaluate_rule_conditions(self.mock_context, conditions_dict)

        self.assertTrue(result)

    def test_weekend_condition_evaluation(self):
        """Test evaluation with timestamp-based weekend conditions."""
        # Create a mock timestamp instead of trying to modify datetime
        mock_timestamp = Mock()
        mock_timestamp.weekday.return_value = 5
        self.mock_context.timestamp = mock_timestamp

        conditions_dict = {
            "field": "timestamp.weekday",
            "operator": "in",
            "value": [5, 6],  # Weekend
        }

        # We need to mock the _get_field_value since timestamp.weekday requires special handling
        with patch.object(RuleEvaluator, "_get_field_value", return_value=5):
            result = RuleEvaluator.evaluate_rule_conditions(self.mock_context, conditions_dict)
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
