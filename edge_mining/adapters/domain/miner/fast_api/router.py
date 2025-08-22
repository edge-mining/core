"""API Router for miner domain"""

import uuid
from typing import Annotated, List, Optional, Union, cast

from fastapi import APIRouter, Depends, HTTPException

from edge_mining.adapters.domain.miner.schemas import (
    MINER_CONTROLLER_CONFIG_SCHEMA_MAP,
    MinerControllerCreateSchema,
    MinerControllerDummyConfigSchema,
    MinerControllerSchema,
    MinerControllerUpdateSchema,
    MinerCreateSchema,
    MinerSchema,
    MinerUpdateSchema,
)

# Import dependency injection setup functions
from edge_mining.adapters.infrastructure.api.setup import (
    get_adapter_service,
    get_config_service,
    get_miner_action_service,
)
from edge_mining.application.interfaces import (
    AdapterServiceInterface,
    ConfigurationServiceInterface,
    MinerActionServiceInterface,
)
from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.miner.common import MinerControllerAdapter
from edge_mining.domain.miner.entities import Miner
from edge_mining.domain.miner.exceptions import (
    MinerControllerConfigurationError,
    MinerControllerNotFoundError,
    MinerNotFoundError,
)
from edge_mining.domain.notification.exceptions import NotifierNotFoundError
from edge_mining.domain.notification.ports import NotificationPort
from edge_mining.domain.optimization_unit.aggregate_roots import EnergyOptimizationUnit
from edge_mining.shared.interfaces.config import Configuration, MinerControllerConfig

router = APIRouter()


@router.get("/miners", response_model=List[MinerSchema])
async def get_miners_list(
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> List[MinerSchema]:
    """Get a list of all configured miners."""
    try:
        miners = config_service.list_miners()

        # Convert to miner schema
        miner_schemas: List[MinerSchema] = []

        for miner in miners:
            miner_schemas.append(MinerSchema.from_model(miner))

        return miner_schemas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/miners/{miner_id}", response_model=MinerSchema)
async def get_miner_details(
    miner_id: EntityId,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Get details for a specific miner."""
    try:
        miner: Optional[Miner] = config_service.get_miner(miner_id)

        if miner is None:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found")

        response = MinerSchema.from_model(miner)

        return response
    except MinerNotFoundError as e:  # Catch specific domain errors if needed
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/miners", response_model=MinerSchema)
async def add_miner(
    miner_schema: MinerCreateSchema,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Add a new miner."""
    try:
        miner_to_add: Miner = miner_schema.to_model()

        new_miner = config_service.add_miner(
            name=miner_to_add.name,
            hash_rate_max=miner_to_add.hash_rate_max,
            power_consumption_max=miner_to_add.power_consumption_max,
            controller_id=miner_to_add.controller_id,
        )

        response = MinerSchema.from_model(new_miner)

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/miners/{miner_id}", response_model=MinerSchema)
async def update_miner(
    miner_id: EntityId,
    miner_update: MinerUpdateSchema,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Update a miner's details."""
    try:
        miner = config_service.get_miner(miner_id)

        if miner is None:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found")

        hash_rate_max = miner_update.hash_rate_max.to_model() if miner_update.hash_rate_max else None
        power_consumption_max = (
            Watts(miner_update.power_consumption_max) if miner_update.power_consumption_max is not None else None
        )

        miner_updated = config_service.update_miner(
            miner_id=miner.id,
            name=miner_update.name or "",
            hash_rate_max=hash_rate_max,
            power_consumption_max=power_consumption_max,
            controller_id=EntityId(uuid.UUID(miner_update.controller_id)),
            active=miner.active,
        )

        response = MinerSchema.from_model(miner_updated)

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/miners/{miner_id}", response_model=MinerSchema)
async def remove_miner(
    miner_id: EntityId,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Remove a miner."""
    try:
        deleted_miner = config_service.remove_miner(miner_id)

        response = MinerSchema.from_model(deleted_miner)

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/miners/{miner_id}/start", response_model=MinerSchema)
async def start_miner(
    miner_id: EntityId,
    action_service: Annotated[MinerActionServiceInterface, Depends(get_miner_action_service)],
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
    adapter_service: Annotated[AdapterServiceInterface, Depends(get_adapter_service)],
) -> MinerSchema:
    """Start a miner."""
    try:
        # If the miner has been inserted into an optimization unit, we can get the notifiers of the unit (if any)
        # and use them to notify the miner action
        optimization_units: List[EnergyOptimizationUnit] = config_service.filter_optimization_units(
            filter_by_miners=[miner_id]
        )
        notifiers: List[NotificationPort] = []
        if optimization_units is not None and len(optimization_units) > 0:
            notifier_ids: List[EntityId] = []
            # Extract notifier IDs from optimization units
            for unit in optimization_units:
                if unit.notifier_ids:
                    notifier_ids.extend(unit.notifier_ids)

            # Remove duplicates
            notifier_ids = list(set(notifier_ids))

            if notifier_ids:
                # Get the notifiers from the configuration service
                for notifier_id in notifier_ids:
                    try:
                        notifier = adapter_service.get_notifier(notifier_id)
                        if notifier is not None:
                            notifiers.append(notifier)
                    except NotifierNotFoundError:
                        continue

        success = await action_service.start_miner(miner_id, notifiers)

        if success:
            miner = config_service.get_miner(miner_id)

            if miner is None:
                raise MinerNotFoundError(f"Miner with ID {miner_id} can not be started")

            response = MinerSchema.from_model(miner)

            return response
        else:
            raise HTTPException(status_code=500, detail="Failed to start miner")
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/miners/{miner_id}/stop", response_model=MinerSchema)
async def stop_miner(
    miner_id: EntityId,
    action_service: Annotated[MinerActionServiceInterface, Depends(get_miner_action_service)],
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
    adapter_service: Annotated[AdapterServiceInterface, Depends(get_adapter_service)],
) -> MinerSchema:
    """Stop a miner."""
    try:
        # If the miner has been inserted into an optimization unit, we can get the notifiers of the unit (if any)
        # and use them to notify the miner action
        optimization_units: List[EnergyOptimizationUnit] = config_service.filter_optimization_units(
            filter_by_miners=[miner_id]
        )
        notifiers: List[NotificationPort] = []
        if optimization_units is not None and len(optimization_units) > 0:
            notifier_ids: List[EntityId] = []
            # Extract notifier IDs from optimization units
            for unit in optimization_units:
                if unit.notifier_ids:
                    notifier_ids.extend(unit.notifier_ids)

            # Remove duplicates
            notifier_ids = list(set(notifier_ids))

            if notifier_ids:
                # Get the notifiers from the configuration service
                for notifier_id in notifier_ids:
                    try:
                        notifier = adapter_service.get_notifier(notifier_id)
                        if notifier is not None:
                            notifiers.append(notifier)
                    except NotifierNotFoundError:
                        continue

        success = await action_service.stop_miner(miner_id, notifiers)

        if success:
            miner = config_service.get_miner(miner_id)

            if miner is None:
                raise MinerNotFoundError(f"Miner with ID {miner_id} can not be stopped")

            response = MinerSchema.from_model(miner)

            return response
        else:
            raise HTTPException(status_code=500, detail="Failed to stop miner")
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/miners/{miner_id}/status", response_model=MinerSchema)
async def get_miner_status(
    miner_id: EntityId,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Get the current status of a miner."""
    try:
        miner = config_service.get_miner(miner_id)

        if miner is None:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found")

        response = MinerSchema.from_model(miner)

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/miners/{miner_id}/activate", response_model=MinerSchema)
async def activate_miner(
    miner_id: EntityId,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Activate a miner."""
    try:
        miner = config_service.activate_miner(miner_id)

        response = MinerSchema.from_model(miner)

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/miners/{miner_id}/deactivate", response_model=MinerSchema)
async def deactivate_miner(
    miner_id: EntityId,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Deactivate a miner."""
    try:
        miner = config_service.deactivate_miner(miner_id)

        response = MinerSchema.from_model(miner)

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/miners/{miner_id}/set-controller", response_model=MinerSchema)
async def set_miner_controller(
    miner_id: EntityId,
    controller_id: EntityId,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerSchema:
    """Set the controller for a miner."""
    try:
        miner = config_service.get_miner(miner_id)

        if miner is None:
            raise MinerNotFoundError(f"Miner with ID {miner_id} not found")

        config_service.set_miner_controller(miner_id, controller_id)

        response = MinerSchema.from_model(miner)

        return response
    except MinerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner not found") from e
    except MinerControllerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner controller not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/miner-controllers", response_model=List[MinerControllerSchema])
async def get_miner_controllers(
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> List[MinerControllerSchema]:
    """Get a list of all miner controllers."""
    try:
        controllers = config_service.list_miner_controllers()

        # Convert to controller schema
        controller_schemas: List[MinerControllerSchema] = []

        for controller in controllers:
            controller_schemas.append(MinerControllerSchema.from_model(controller))

        return controller_schemas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/miner-controllers", response_model=MinerControllerSchema)
async def add_miner_controller(
    controller_schema: MinerControllerCreateSchema,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerControllerSchema:
    """Add a new miner controller."""
    try:
        controller_to_add = controller_schema.to_model()

        if controller_to_add.config is None:
            raise MinerControllerConfigurationError("Miner controller configuration must be set")

        new_controller = config_service.add_miner_controller(
            name=controller_to_add.name,
            adapter=controller_to_add.adapter_type,
            config=controller_to_add.config,
            external_service_id=controller_to_add.external_service_id,
        )

        response = MinerControllerSchema.from_model(new_controller)

        return response
    except MinerControllerConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/miner-controllers/types", response_model=List[MinerControllerAdapter])
async def get_miner_controller_types() -> List[MinerControllerAdapter]:
    """Get a list of available miner controller types."""
    try:
        return [MinerControllerAdapter(adapter.value) for adapter in MinerControllerAdapter]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/miner-controllers/types/{adapter_type}/config-schema", response_model=Union[MinerControllerDummyConfigSchema]
)
async def get_miner_controller_config_schema(
    adapter_type: MinerControllerAdapter,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> Union[MinerControllerDummyConfigSchema]:
    """Get the configuration schema for a specific miner controller type."""
    try:
        try:
            miner_controller_adapter = MinerControllerAdapter(adapter_type)
        except ValueError as e:
            raise ValueError(f"Invalid miner controller adapter type: {adapter_type}") from e

        # Get the corresponding configuration class for the adapter type
        miner_controller_config_type: Optional[type[MinerControllerConfig]] = (
            config_service.get_miner_controller_config_by_type(miner_controller_adapter)
        )

        if miner_controller_config_type is None:
            raise ValueError(f"No configuration class found for adapter type: {adapter_type}")

        # Map the configuration class to its corresponding schema
        miner_controller_config_schema = MINER_CONTROLLER_CONFIG_SCHEMA_MAP.get(miner_controller_config_type, None)

        if miner_controller_config_schema is None:
            raise ValueError(f"No schema found for miner controller config class: {miner_controller_config_type}")

        return miner_controller_config_schema()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/miner-controllers/{controller_id}", response_model=MinerControllerSchema)
async def get_miner_controller(
    controller_id: EntityId,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerControllerSchema:
    """Get details for a specific miner controller."""
    try:
        controller = config_service.get_miner_controller(controller_id)

        if controller is None:
            raise MinerControllerNotFoundError(f"Miner controller with ID {controller_id} not found")

        response = MinerControllerSchema.from_model(controller)

        return response
    except MinerControllerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner controller not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/miner-controllers/{controller_id}", response_model=MinerControllerSchema)
async def update_miner_controller(
    controller_id: EntityId,
    controller_update: MinerControllerUpdateSchema,
    config_service: Annotated[ConfigurationServiceInterface, Depends(get_config_service)],
) -> MinerControllerSchema:
    """Update a miner controller's details."""
    try:
        controller = config_service.get_miner_controller(controller_id)

        if controller is None:
            raise MinerControllerNotFoundError(f"Miner controller with ID {controller_id} not found")

        configuration: Optional[Configuration] = None
        if controller_update.config:
            configuration = MinerControllerConfig.from_dict(controller_update.config)

        updated_controller = config_service.update_miner_controller(
            controller_id=controller.id,
            name=controller_update.name or "",
            config=cast(MinerControllerConfig, configuration),
        )

        response = MinerControllerSchema.from_model(updated_controller)

        return response
    except MinerControllerNotFoundError as e:
        raise HTTPException(status_code=404, detail="Miner controller not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
        raise HTTPException(status_code=500, detail=str(e)) from e
