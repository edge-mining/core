"""API Router for miner domain"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Annotated

from edge_mining.application.services.configuration_service import ConfigurationService

from edge_mining.domain.miner.common import MinerId
from edge_mining.domain.exceptions import MinerNotFoundError

from edge_mining.adapters.domain.miner.fast_api.schemas import MinerSchema

# Import the dependency injection function defined in main_api.py
from edge_mining.adapters.infrastructure.api.main_api import get_config_service

router = APIRouter()


@router.get("/miners", response_model=List[MinerSchema]) # Use DTOs directly or a Pydantic schema
async def get_miners_list(
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get a list of all configured miners."""
    try:
        miners = config_service.list_miners()

        # Convert to response schema
        response_miners = []
        for miner in miners:
            response_miners.append(
                MinerSchema(
                    id=miner.id,
                    name=miner.name,
                    status=miner.status,
                    power_consumption=miner.power_consumption,
                    ip_address=miner.ip_address
                )
            )

        return response_miners
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/miners/{miner_id}", response_model=MinerSchema)
async def get_miner_details(
    miner_id: MinerId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Get details for a specific miner."""
    try:
        miner = config_service.get_miner(miner_id)
        if miner is None:
            raise HTTPException(status_code=404, detail="Miner not found")

        response = MinerSchema(
            id=miner.id,
            name=miner.name,
            ip_address=miner.ip_address
        )

        return response
    except MinerNotFoundError: # Catch specific domain errors if needed
         raise HTTPException(status_code=404, detail="Miner not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/miners", response_model=MinerSchema)
async def add_miner(
    miner: MinerSchema,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Add a new miner."""
    try:
        new_miner = config_service.add_miner(
            miner_id=miner.id,
            name=miner.name,
            ip_address=miner.ip_address
        )

        response = MinerSchema(
            id=new_miner.id,
            name=new_miner.name,
            status=new_miner.status,
            ip_address=new_miner.ip_address
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/miners/{miner_id}")
async def remove_miner(
    miner_id: MinerId,
    config_service: Annotated[ConfigurationService, Depends(get_config_service)]
):
    """Remove a miner."""
    try:
        config_service.remove_miner(miner_id)
        return {"detail": "Miner removed successfully"}
    except MinerNotFoundError:
        raise HTTPException(status_code=404, detail="Miner not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))