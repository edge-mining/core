"""API Router for policy domain"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Annotated

from edge_mining.application.services.configuration_service import ConfigurationService

from edge_mining.domain.common import EntityId
from edge_mining.domain.policy.common import RuleType
from edge_mining.domain.policy.entities import AutomationRule
from edge_mining.domain.policy.aggregate_roots import OptimizationPolicy
from edge_mining.domain.exceptions import PolicyNotFoundError

from edge_mining.adapters.domain.policy.fast_api.schemas import (
    OptimizationPolicyResponseSchema, OptimizationPolicyCreateSchema,
    AutomationRuleResponseSchema, AutomationRuleCreateSchema, RuleTypeSchema
)

# Import the dependency injection function defined in main_api.py
from edge_mining.adapters.infrastructure.api.main_api import get_config_service

router = APIRouter()

@router.get("/policies", response_model=List[OptimizationPolicyResponseSchema])
async def get_policies_list(
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get a list of all configured policies."""
    try:
        policies = config_service.list_policies()

        response: List[OptimizationPolicyResponseSchema] = []
        for policy in policies:
            response.append(
                OptimizationPolicyResponseSchema(
                    id=policy.id,
                    name=policy.name,
                    description=policy.description,
                    target_miner_ids=policy.target_miner_ids,
                    is_active=policy.is_active
                )
            )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/policies/active", response_model=OptimizationPolicyResponseSchema)
async def get_active_policy(
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get the currently active optimization policy."""
    try:
        active_policy = config_service.get_active_policy()
        if active_policy is None:
            raise HTTPException(status_code=404, detail="No active policy found")

        response = OptimizationPolicyResponseSchema(
            id=str(active_policy.id),
            name=active_policy.name,
            description=active_policy.description,
            is_active=active_policy.is_active,
            target_miner_ids=active_policy.target_miner_ids
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/policies/{policy_id}", response_model=OptimizationPolicyResponseSchema)
async def get_policy_details(
    policy_id: EntityId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get details for a specific optimization policy."""
    try:
        policy = config_service.get_policy(policy_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Optimization policy not found")

        response = OptimizationPolicyResponseSchema(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            target_miner_ids=policy.target_miner_ids,
            is_active=policy.is_active
        )

        return response
    except PolicyNotFoundError as e: # Catch specific domain errors if needed
        raise HTTPException(status_code=404, detail="Policy not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/policies", response_model=OptimizationPolicyResponseSchema)
async def add_policy(
    policy: OptimizationPolicyCreateSchema,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Add a new optimization policy."""
    try:
        new_policy = config_service.create_policy(
            name=policy.name,
            description=policy.description,
            target_miner_ids=policy.target_miner_ids
        )

        response = OptimizationPolicyResponseSchema(
            id=new_policy.id,
            name=new_policy.name,
            description=new_policy.description,
            target_miner_ids=policy.target_miner_ids,
            is_active=new_policy.is_active
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/policies/{policy_id}/rules", response_model=AutomationRuleCreateSchema)
async def add_rule_to_policy(
    policy_id: EntityId,
    rule: AutomationRuleCreateSchema,
    rule_type: RuleTypeSchema,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Add a new rule to an existing optimization policy."""
    try:
        if rule_type == RuleTypeSchema.start:
            rule_type = RuleType.START
        elif rule_type == RuleTypeSchema.stop:
            rule_type = RuleType.STOP

        new_rule: AutomationRule = config_service.add_rule_to_policy(
            policy_id=policy_id,
            rule_type=rule_type,
            name=rule.name,
            conditions=rule.conditions,
            action=rule.action
        )

        response = AutomationRuleResponseSchema(
            id=str(new_rule.id),
            name=new_rule.name,
            conditions=new_rule.conditions,
            action=new_rule.action
        )

        return response
    except PolicyNotFoundError as e:
        raise HTTPException(status_code=404, detail="Policy not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/policies/{policy_id}/rules/type/{rule_type}", response_model=List[AutomationRuleResponseSchema])
async def get_policy_rules(
    policy_id: EntityId,
    rule_type: RuleTypeSchema,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get all rules type for a specific optimization policy."""
    try:
        if rule_type == RuleTypeSchema.start:
            rule_type = RuleType.START
        elif rule_type == RuleTypeSchema.stop:
            rule_type = RuleType.STOP

        rules: List[AutomationRule] = config_service.get_policy_rules(policy_id, rule_type)

        response: List[AutomationRuleResponseSchema] = []
        for rule in rules:
            response.append(
                AutomationRuleResponseSchema(
                    id=str(rule.id),
                    name=rule.name,
                    conditions=rule.conditions,
                    action=rule.action.value
                )
            )

        return response
    except PolicyNotFoundError as e:
        raise HTTPException(status_code=404, detail="Policy not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/policies/{policy_id}/rules/{rule_id}", response_model=AutomationRuleResponseSchema)
async def get_policy_rule(
    policy_id: EntityId,
    rule_id: EntityId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get a specific rule for a specific optimization policy."""
    try:
        rule: AutomationRule = config_service.get_policy_rule(policy_id, rule_id)

        if rule is None:
            raise HTTPException(status_code=404, detail="Rule not found")

        response = AutomationRuleResponseSchema(
            id=str(rule.id),
            name=rule.name,
            conditions=rule.conditions,
            action=rule.action
        )

        return response
    except PolicyNotFoundError as e:
        raise HTTPException(status_code=404, detail="Policy not found") from e

@router.put("/policies/{policy_id}/rules/{rule_id}", response_model=AutomationRuleResponseSchema)
async def update_policy_rule(
    policy_id: EntityId,
    rule_id: str,
    rule: AutomationRuleResponseSchema,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Update a specific rule for a specific optimization policy."""
    try:
        updated_rule: AutomationRule = config_service.update_policy_rule(
            policy_id=policy_id,
            rule_id=rule_id,
            name=rule.name,
            conditions=rule.conditions,
            action=rule.action
        )

        response = AutomationRuleResponseSchema(
            id=str(updated_rule.id),
            name=updated_rule.name,
            conditions=updated_rule.conditions,
            action=updated_rule.action
        )

        return response
    except PolicyNotFoundError as e:
        raise HTTPException(status_code=404, detail="Policy not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.delete("/policies/{policy_id}/rules/{rule_id}")
async def delete_policy_rule(
    policy_id: EntityId,
    rule_id: str,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Delete a specific rule for a specific optimization policy."""
    try:
        config_service.delete_policy_rule(policy_id, rule_id)
        return {"detail": "Rule deleted successfully"}
    except PolicyNotFoundError as e:
        raise HTTPException(status_code=404, detail="Policy not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.put("/policies/{policy_id}/activate")
async def set_active_policy(
    policy_id: EntityId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Set a specific optimization policy as active."""
    try:
        config_service.set_active_policy(policy_id)
        return {"detail": "Policy activated successfully"}
    except PolicyNotFoundError as e:
        raise HTTPException(status_code=404, detail="Policy not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: EntityId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Delete a specific optimization policy."""
    try:
        deleted_policy = config_service.delete_policy(policy_id)

        return {"detail": f"Policy '{deleted_policy.name}' deleted successfully"}
    except PolicyNotFoundError as e:
        raise HTTPException(status_code=404, detail="Policy not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

