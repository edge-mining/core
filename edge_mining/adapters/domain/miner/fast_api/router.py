"""API Router for miner domain"""

from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException

from edge_mining.application.services.configuration_service import ConfigurationService
from edge_mining.application.services.action_service import ActionService

from edge_mining.domain.miner.common import MinerId
from edge_mining.domain.exceptions import MinerNotFoundError

from edge_mining.adapters.domain.miner.fast_api.schemas import (
    MinerResponseSchema, MinerCreateSchema, MinerUpdateSchema,
    MinerStatusSchema
)

# Import the dependency injection function defined in main_api.py
from edge_mining.adapters.infrastructure.api.main_api import get_config_service
from edge_mining.adapters.infrastructure.api.main_api import get_action_service

router = APIRouter()

@router.get("/miners", response_model=List[MinerResponseSchema]) # Use DTOs directly or a Pydantic schema
async def get_miners_list(
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get a list of all configured miners."""
    try:
        miners = config_service.list_miners()

        # Convert to response schema
        response_miners: List[MinerResponseSchema] = []

        for miner in miners:
            response_miners.append(
                MinerResponseSchema(
                    id=miner.id,
                    name=miner.name,
                    status=miner.status,
                    active=miner.active,
                    hash_rate=miner.hash_rate,
                    hash_rate_max=miner.hash_rate_max,
                    power_consumption=miner.power_consumption,
                    power_consumption_max=miner.power_consumption_max,
                    ip_address=miner.ip_address
                )
            )

        return response_miners
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/miners/{miner_id}", response_model=MinerResponseSchema)
async def get_miner_details(
    miner_id: MinerId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get details for a specific miner."""
    try:
        miner = config_service.get_miner(miner_id)

        response = MinerResponseSchema(
            id=miner.id,
            name=miner.name,
            status=miner.status,
            active=miner.active,
            hash_rate=miner.hash_rate,
            hash_rate_max=miner.hash_rate_max,
            power_consumption=miner.power_consumption,
            power_consumption_max=miner.power_consumption_max,
            ip_address=miner.ip_address
        )

        return response
    except MinerNotFoundError as e: # Catch specific domain errors if needed
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/miners", response_model=MinerResponseSchema)
async def add_miner(
    miner: MinerCreateSchema,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Add a new miner."""
    try:
        new_miner = config_service.add_miner(
            name=miner.name,
            ip_address=miner.ip_address,
            hash_rate_max=miner.hash_rate_max,
            power_consumption_max=miner.power_consumption_max,
            active=miner.active
        )

        response = MinerResponseSchema(
            id=new_miner.id,
            name=new_miner.name,
            active=new_miner.active,
            status=new_miner.status,
            ip_address=new_miner.ip_address,
            hash_rate=new_miner.hash_rate,
            hash_rate_max=new_miner.hash_rate_max,
            power_consumption=new_miner.power_consumption,
            power_consumption_max=new_miner.power_consumption_max
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.delete("/miners/{miner_id}", response_model=MinerResponseSchema)
async def remove_miner(
    miner_id: MinerId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Remove a miner."""
    try:
        deleted_miner = config_service.remove_miner(miner_id)

        response = MinerResponseSchema(
            id=deleted_miner.id,
            name=deleted_miner.name,
            active=deleted_miner.active,
            status=deleted_miner.status,
            ip_address=deleted_miner.ip_address,
            hash_rate=deleted_miner.hash_rate,
            hash_rate_max=deleted_miner.hash_rate_max,
            power_consumption=deleted_miner.power_consumption,
            power_consumption_max=deleted_miner.power_consumption_max
        )

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.put("/miners/{miner_id}", response_model=MinerResponseSchema)
async def update_miner(
    miner_id: MinerId,
    miner_update: MinerUpdateSchema,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Update a miner's details."""
    try:
        miner = config_service.get_miner(miner_id)

        miner_updated = config_service.update_miner(
            miner_id=miner.id,
            name=miner_update.name,
            ip_address=miner_update.ip_address,
            hash_rate_max=miner_update.hash_rate_max,
            power_consumption_max=miner_update.power_consumption_max,
            active=miner.active
        )

        response = MinerResponseSchema(
            id=miner_updated.id,
            name=miner_updated.name,
            active=miner_updated.active,
            status=miner_updated.status,
            ip_address=miner_updated.ip_address,
            hash_rate=miner_updated.hash_rate,
            hash_rate_max=miner_updated.hash_rate_max,
            power_consumption=miner_updated.power_consumption,
            power_consumption_max=miner_updated.power_consumption_max
        )

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/miners/{miner_id}/start", response_model=MinerStatusSchema)
async def start_miner(
    miner_id: MinerId,
    action_service: Annotated[ActionService, Depends(get_action_service)],
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Start a miner."""
    try:
        success = action_service.start_miner(miner_id)

        if success:
            miner = config_service.get_miner(miner_id)

            response = MinerStatusSchema(
                id=miner.id,
                status=miner.status,
                active=miner.active,
                hash_rate=miner.hash_rate,
                power_consumption=miner.power_consumption
            )

            return response
        else:
            raise HTTPException(status_code=500, detail="Failed to start miner")
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/miners/{miner_id}/stop", response_model=MinerStatusSchema)
async def stop_miner(
    miner_id: MinerId,
    action_service: Annotated[ActionService, Depends(get_action_service)],
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Stop a miner."""
    try:
        success = action_service.stop_miner(miner_id)

        if success:
            miner = config_service.get_miner(miner_id)

            response = MinerStatusSchema(
                id=miner.id,
                status=miner.status,
                active=miner.active,
                hash_rate=miner.hash_rate,
                power_consumption=miner.power_consumption
            )

            return response
        else:
            raise HTTPException(status_code=500, detail="Failed to stop miner")
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/miners/{miner_id}/status", response_model=MinerStatusSchema)
async def get_miner_status(
    miner_id: MinerId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get the current status of a miner."""
    try:
        miner = config_service.get_miner(miner_id)

        response = MinerStatusSchema(
            id=miner.id,
            status=miner.status,
            active=miner.active,
            hash_rate=miner.hash_rate,
            power_consumption=miner.power_consumption
        )

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/miners/{miner_id}/activate", response_model=MinerStatusSchema)
async def activate_miner(
    miner_id: MinerId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Activate a miner."""
    try:
        miner = config_service.activate_miner(miner_id)

        response = MinerStatusSchema(
            id=miner.id,
            status=miner.status,
            active=miner.active,
            hash_rate=miner.hash_rate,
            power_consumption=miner.power_consumption
        )

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post("/miners/{miner_id}/deactivate", response_model=MinerStatusSchema)
async def deactivate_miner(
    miner_id: MinerId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Deactivate a miner."""
    try:
        miner = config_service.deactivate_miner(miner_id)

        response = MinerStatusSchema(
            id=miner.id,
            status=miner.status,
            active=miner.active,
            hash_rate=miner.hash_rate,
            power_consumption=miner.power_consumption
        )

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
