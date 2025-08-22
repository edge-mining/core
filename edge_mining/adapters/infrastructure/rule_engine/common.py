"""Common objects for rule engine."""

from enum import Enum
from typing import Dict


class OperatorType(Enum):
    """Supported operators for rule conditions."""

    EQ = "eq"  # equal
    NE = "ne"  # not equal
    GT = "gt"  # greater than
    GTE = "gte"  # greater than or equal
    LT = "lt"  # less than
    LTE = "lte"  # less than or equal
    IN = "in"  # in list/array
    NOT_IN = "not_in"  # not in list/array
    CONTAINS = "contains"  # string contains
    STARTS_WITH = "starts_with"  # string starts with
    ENDS_WITH = "ends_with"  # string ends with
    REGEX = "regex"  # regex match


# Mapping of operators to their symbolic representation
OPERATOR_SYMBOLS: Dict[OperatorType, str] = {
    OperatorType.EQ: "==",
    OperatorType.NE: "!=",
    OperatorType.GT: ">",
    OperatorType.GTE: ">=",
    OperatorType.LT: "<",
    OperatorType.LTE: "<=",
    OperatorType.IN: "∈",
    OperatorType.NOT_IN: "∉",
    OperatorType.CONTAINS: "⊃",
    OperatorType.STARTS_WITH: "^",
    OperatorType.ENDS_WITH: "$",
    OperatorType.REGEX: "~",
}


class RuleEngineType(Enum):
    """Types of rule engines."""

    CUSTOM = "custom"  # Custom rule engine
