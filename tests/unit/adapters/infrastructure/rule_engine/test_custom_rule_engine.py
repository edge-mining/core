"""Unit tests for CustomRuleEngine class."""

import unittest
from unittest.mock import Mock, patch

try:
    from edge_mining.adapters.infrastructure.rule_engine.engine import CustomRuleEngine
    from edge_mining.domain.policy.entities import AutomationRule
    from edge_mining.domain.policy.value_objects import DecisionalContext
    from edge_mining.shared.logging.port import LoggerPort
except ImportError as e:
    print(f"Import error: {e}")
    raise


class TestCustomRuleEngine(unittest.TestCase):
    """Test cases for CustomRuleEngine class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_logger = Mock(spec=LoggerPort)
        self.engine = CustomRuleEngine(self.mock_logger)

        # Create mock automation rules
        self.mock_rule_high_priority = Mock(spec=AutomationRule)
        self.mock_rule_high_priority.name = "High Priority Rule"
        self.mock_rule_high_priority.priority = 10
        self.mock_rule_high_priority.enabled = True
        self.mock_rule_high_priority.conditions = ["condition1"]

        self.mock_rule_low_priority = Mock(spec=AutomationRule)
        self.mock_rule_low_priority.name = "Low Priority Rule"
        self.mock_rule_low_priority.priority = 5
        self.mock_rule_low_priority.enabled = True
        self.mock_rule_low_priority.conditions = ["condition2"]

        self.mock_rule_disabled = Mock(spec=AutomationRule)
        self.mock_rule_disabled.name = "Disabled Rule"
        self.mock_rule_disabled.priority = 15
        self.mock_rule_disabled.enabled = False
        self.mock_rule_disabled.conditions = ["condition3"]

        # Create mock decisional context
        self.mock_context = Mock(spec=DecisionalContext)

    def test_init(self):
        """Test CustomRuleEngine initialization."""
        engine = CustomRuleEngine(self.mock_logger)

        self.assertEqual(engine.rules, [])
        self.assertEqual(engine.logger, self.mock_logger)

    def test_load_rules_empty_list(self):
        """Test loading an empty list of rules."""
        rules = []

        self.engine.load_rules(rules)

        self.assertEqual(self.engine.rules, [])
        self.mock_logger.debug.assert_called_once_with("Successfully loaded 0 rules into CustomRuleEngine")

    def test_load_rules_single_rule(self):
        """Test loading a single rule."""
        rules = [self.mock_rule_high_priority]

        self.engine.load_rules(rules)

        self.assertEqual(self.engine.rules, rules)
        self.mock_logger.debug.assert_called_once_with("Successfully loaded 1 rules into CustomRuleEngine")

    def test_load_rules_multiple_rules(self):
        """Test loading multiple rules."""
        rules = [self.mock_rule_high_priority, self.mock_rule_low_priority]

        self.engine.load_rules(rules)

        self.assertEqual(self.engine.rules, rules)
        self.mock_logger.debug.assert_called_once_with("Successfully loaded 2 rules into CustomRuleEngine")

    def test_load_rules_overwrites_existing(self):
        """Test that loading rules overwrites existing rules."""
        # Load initial rules
        initial_rules = [self.mock_rule_high_priority]
        self.engine.load_rules(initial_rules)

        # Load new rules
        new_rules = [self.mock_rule_low_priority]
        self.engine.load_rules(new_rules)

        self.assertEqual(self.engine.rules, new_rules)
        self.assertEqual(len(self.engine.rules), 1)

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_no_rules(self, mock_rule_evaluator):
        """Test evaluation when no rules are loaded."""
        result = self.engine.evaluate(self.mock_context)

        self.assertFalse(result)
        mock_rule_evaluator.evaluate_rule_conditions.assert_not_called()

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_single_rule_matches(self, mock_rule_evaluator):
        """Test evaluation when single rule matches."""
        mock_rule_evaluator.evaluate_rule_conditions.return_value = True

        self.engine.load_rules([self.mock_rule_high_priority])
        result = self.engine.evaluate(self.mock_context)

        self.assertTrue(result)
        mock_rule_evaluator.evaluate_rule_conditions.assert_called_once_with(
            self.mock_context, self.mock_rule_high_priority.conditions
        )
        self.mock_logger.debug.assert_any_call("Rule 'High Priority Rule' matched!")

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_single_rule_no_match(self, mock_rule_evaluator):
        """Test evaluation when single rule doesn't match."""
        mock_rule_evaluator.evaluate_rule_conditions.return_value = False

        self.engine.load_rules([self.mock_rule_high_priority])
        result = self.engine.evaluate(self.mock_context)

        self.assertFalse(result)
        mock_rule_evaluator.evaluate_rule_conditions.assert_called_once_with(
            self.mock_context, self.mock_rule_high_priority.conditions
        )

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_multiple_rules_first_matches(self, mock_rule_evaluator):
        """Test evaluation when first rule (by priority) matches."""
        mock_rule_evaluator.evaluate_rule_conditions.return_value = True

        rules = [self.mock_rule_low_priority, self.mock_rule_high_priority]
        self.engine.load_rules(rules)
        result = self.engine.evaluate(self.mock_context)

        self.assertTrue(result)
        # Should only evaluate the high priority rule (first in sorted order)
        mock_rule_evaluator.evaluate_rule_conditions.assert_called_once_with(
            self.mock_context, self.mock_rule_high_priority.conditions
        )
        self.mock_logger.debug.assert_any_call("Rule 'High Priority Rule' matched!")

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_multiple_rules_second_matches(self, mock_rule_evaluator):
        """Test evaluation when second rule (by priority) matches."""
        # First call returns False, second returns True
        mock_rule_evaluator.evaluate_rule_conditions.side_effect = [
            False,
            True,
        ]

        rules = [self.mock_rule_low_priority, self.mock_rule_high_priority]
        self.engine.load_rules(rules)
        result = self.engine.evaluate(self.mock_context)

        self.assertTrue(result)
        # Should evaluate both rules in priority order
        self.assertEqual(mock_rule_evaluator.evaluate_rule_conditions.call_count, 2)
        self.mock_logger.debug.assert_any_call("Rule 'Low Priority Rule' matched!")

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_priority_sorting(self, mock_rule_evaluator):
        """Test that rules are evaluated in priority order (highest first)."""
        mock_rule_evaluator.evaluate_rule_conditions.side_effect = [
            False,
            False,
        ]

        # Add rules in random order
        rules = [self.mock_rule_low_priority, self.mock_rule_high_priority]
        self.engine.load_rules(rules)
        result = self.engine.evaluate(self.mock_context)

        self.assertFalse(result)
        # Verify rules were called in priority order (high priority first)
        calls = mock_rule_evaluator.evaluate_rule_conditions.call_args_list
        self.assertEqual(len(calls), 2)
        # First call should be for high priority rule
        self.assertEqual(calls[0][0][1], self.mock_rule_high_priority.conditions)
        # Second call should be for low priority rule
        self.assertEqual(calls[1][0][1], self.mock_rule_low_priority.conditions)

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_skips_disabled_rules(self, mock_rule_evaluator):
        """Test that disabled rules are skipped during evaluation."""
        mock_rule_evaluator.evaluate_rule_conditions.return_value = False

        rules = [self.mock_rule_disabled, self.mock_rule_high_priority]
        self.engine.load_rules(rules)
        result = self.engine.evaluate(self.mock_context)

        self.assertFalse(result)
        # Should only evaluate the enabled rule
        mock_rule_evaluator.evaluate_rule_conditions.assert_called_once_with(
            self.mock_context, self.mock_rule_high_priority.conditions
        )

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_handles_value_error(self, mock_rule_evaluator):
        """Test evaluation handles ValueError exceptions gracefully."""
        mock_rule_evaluator.evaluate_rule_conditions.side_effect = ValueError("Test error")

        self.engine.load_rules([self.mock_rule_high_priority])
        result = self.engine.evaluate(self.mock_context)

        self.assertFalse(result)
        self.mock_logger.error.assert_called_once_with("Error evaluating rule 'High Priority Rule': Test error")

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_handles_attribute_error(self, mock_rule_evaluator):
        """Test evaluation handles AttributeError exceptions gracefully."""
        mock_rule_evaluator.evaluate_rule_conditions.side_effect = AttributeError("Test error")

        self.engine.load_rules([self.mock_rule_high_priority])
        result = self.engine.evaluate(self.mock_context)

        self.assertFalse(result)
        self.mock_logger.error.assert_called_once_with("Error evaluating rule 'High Priority Rule': Test error")

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_continues_after_error(self, mock_rule_evaluator):
        """Test that evaluation continues with other rules after an error."""
        # First rule throws exception, second rule matches
        mock_rule_evaluator.evaluate_rule_conditions.side_effect = [
            ValueError("Test error"),
            True,
        ]

        rules = [self.mock_rule_high_priority, self.mock_rule_low_priority]
        self.engine.load_rules(rules)
        result = self.engine.evaluate(self.mock_context)

        self.assertTrue(result)
        self.assertEqual(mock_rule_evaluator.evaluate_rule_conditions.call_count, 2)
        self.mock_logger.error.assert_called_once_with("Error evaluating rule 'High Priority Rule': Test error")
        self.mock_logger.debug.assert_any_call("Rule 'Low Priority Rule' matched!")

    @patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator")
    def test_evaluate_all_rules_fail(self, mock_rule_evaluator):
        """Test evaluation when all rules fail to match."""
        mock_rule_evaluator.evaluate_rule_conditions.return_value = False

        rules = [self.mock_rule_high_priority, self.mock_rule_low_priority]
        self.engine.load_rules(rules)
        result = self.engine.evaluate(self.mock_context)

        self.assertFalse(result)
        self.assertEqual(mock_rule_evaluator.evaluate_rule_conditions.call_count, 2)

    def test_evaluate_with_mixed_enabled_disabled_rules(self):
        """Test evaluation with a mix of enabled and disabled rules."""
        # Create a rule that should match
        enabled_rule = Mock(spec=AutomationRule)
        enabled_rule.name = "Enabled Rule"
        enabled_rule.priority = 8
        enabled_rule.enabled = True
        enabled_rule.conditions = ["condition"]

        with patch("edge_mining.adapters.infrastructure.rule_engine.engine.RuleEvaluator") as mock_evaluator:
            mock_evaluator.evaluate_rule_conditions.return_value = True

            rules = [
                self.mock_rule_disabled,
                enabled_rule,
                self.mock_rule_low_priority,
            ]
            self.engine.load_rules(rules)
            result = self.engine.evaluate(self.mock_context)

            self.assertTrue(result)
            # Should only evaluate enabled rules
            self.assertEqual(mock_evaluator.evaluate_rule_conditions.call_count, 1)
            mock_evaluator.evaluate_rule_conditions.assert_called_with(self.mock_context, enabled_rule.conditions)


if __name__ == "__main__":
    unittest.main()
