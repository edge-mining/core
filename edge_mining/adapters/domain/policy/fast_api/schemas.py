"""Pydantic models for policy domain"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class OptimizationPolicyCreateSchema(BaseModel):
    """Schema for creating a new optimization policy"""

    name: str
    description: Optional[str] = None
    target_miner_ids: List[str]


class OptimizationPolicyResponseSchema(BaseModel):
    """Schema for returning an optimization policy"""

    id: str
    name: str
    description: Optional[str] = None
    target_miner_ids: List[str]
    is_active: bool


class RuleTypeSchema(str, Enum):
    """Schema for the type of rule"""

    START = "start"
    STOP = "stop"


class MiningDecisionSchema(str, Enum):
    """Schema for the mining decision"""

    START_MINING = "start_mining"
    STOP_MINING = "stop_mining"
    MAINTAIN_STATE = "maintain_state"


class AutomationRuleResponseSchema(BaseModel):
    """Schema for returning an automation rule"""

    id: str
    name: str
    conditions: dict  # Define the structure of conditions if needed
    action: Optional[MiningDecisionSchema] = None  # Optional, can be determined by policy


class AutomationRuleCreateSchema(BaseModel):
    """Schema for creating a new automation rule"""

    name: str
    conditions: dict
    action: Optional[MiningDecisionSchema] = None  # Optional, can be determined by policy
