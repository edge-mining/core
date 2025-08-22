"""Validation schemas for miner domain."""

import uuid
from typing import Dict, Optional, Union, cast

from pydantic import BaseModel, Field, field_serializer, field_validator

from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.miner.common import MinerControllerAdapter, MinerStatus
from edge_mining.domain.miner.entities import Miner, MinerController
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.shared.adapter_configs.miner import MinerControllerDummyConfig
from edge_mining.shared.interfaces.config import MinerControllerConfig


class HashRateSchema(BaseModel):
    """Schema for HashRate value object."""

    value: float = Field(..., ge=0, description="Hash rate value, must be zero or positive")
    unit: str = Field(default="TH/s", description="Hash rate unit")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        """Validate hash rate unit."""
        allowed_units = ["GH/s", "TH/s", "PH/s", "EH/s"]
        if v not in allowed_units:
            raise ValueError(f"Unit must be one of {allowed_units}")
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Validate hash rate value."""
        if v < 0:
            raise ValueError("Hash rate value must be zero or positive")
        return v

    def to_model(self) -> HashRate:
        """Convert HashRateSchema to HashRate domain value object."""
        return HashRate(value=self.value, unit=self.unit)


class MinerSchema(BaseModel):
    """Schema for Miner entity with complete validation."""

    id: str = Field(..., description="Unique identifier for the miner")
    name: str = Field(default="", description="Miner name")
    status: MinerStatus = Field(default=MinerStatus.UNKNOWN, description="Current miner status")
    hash_rate: Optional[HashRateSchema] = Field(default=None, description="Current hash rate")
    hash_rate_max: Optional[HashRateSchema] = Field(default=None, description="Maximum hash rate")
    power_consumption: Optional[float] = Field(default=None, description="Current power consumption in Watts")
    power_consumption_max: Optional[float] = Field(default=None, ge=0, description="Maximum power consumption in Watts")
    active: bool = Field(default=True, description="Whether the miner is active in the system")
    controller_id: Optional[str] = Field(default=None, description="ID of the associated Miner controller")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate that id is a valid UUID string."""
        try:
            uuid.UUID(v)
        except ValueError as exc:
            raise ValueError("id must be a valid UUID string") from exc
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate miner name."""
        v = v.strip()
        if not v:
            v = ""
        return v

    @field_validator("controller_id")
    @classmethod
    def validate_controller_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate that controller_id is a valid UUID string if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError as exc:
                raise ValueError("controller_id must be a valid UUID string") from exc
        return v

    @field_validator("power_consumption_max")
    @classmethod
    def validate_power_max(cls, v: Optional[float]) -> Optional[float]:
        """Validate power consumption max values."""
        if v is not None and v < 0:
            raise ValueError("Power consumption max cannot be negative")
        return v

    @classmethod
    def from_model(cls, miner: Miner) -> "MinerSchema":
        """Create MinerSchema from a Miner domain model instance."""
        return cls(
            id=str(miner.id),
            name=miner.name,
            status=miner.status,
            hash_rate=HashRateSchema(value=miner.hash_rate.value, unit=miner.hash_rate.unit)
            if miner.hash_rate
            else None,
            hash_rate_max=HashRateSchema(value=miner.hash_rate_max.value, unit=miner.hash_rate_max.unit)
            if miner.hash_rate_max
            else None,
            power_consumption=miner.power_consumption,
            power_consumption_max=miner.power_consumption_max,
            active=miner.active,
            controller_id=str(miner.controller_id) if miner.controller_id else None,
        )

    @field_serializer("id")
    def serialize_id(self, value: str) -> str:
        """Serialize id field."""
        return str(value)

    @field_serializer("controller_id")
    def serialize_controller_id(self, value: Optional[str]) -> Optional[str]:
        """Serialize controller_id field."""
        return str(value) if value is not None else None

    def to_model(self) -> Miner:
        """Convert MinerSchema back to Miner domain model instance."""
        return Miner(
            id=EntityId(uuid.UUID(self.id)),
            name=self.name,
            status=self.status,
            hash_rate=(HashRate(value=self.hash_rate.value, unit=self.hash_rate.unit) if self.hash_rate else None),
            hash_rate_max=(
                HashRate(value=self.hash_rate_max.value, unit=self.hash_rate_max.unit) if self.hash_rate_max else None
            ),
            power_consumption=Watts(self.power_consumption) if self.power_consumption is not None else None,
            power_consumption_max=Watts(self.power_consumption_max) if self.power_consumption_max is not None else None,
            active=self.active,
            controller_id=EntityId(uuid.UUID(self.controller_id)) if self.controller_id else None,
        )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        json_encoders = {
            uuid.UUID: str,
            MinerStatus: lambda v: v.value,
            MinerControllerAdapter: lambda v: v.value,
        }


class MinerCreateSchema(BaseModel):
    """Schema for creating a new miner."""

    name: str = Field(..., min_length=1, max_length=255, description="Miner name")
    hash_rate_max: Optional[HashRateSchema] = Field(default=None, description="Maximum hash rate")
    power_consumption_max: Optional[float] = Field(default=None, ge=0, description="Maximum power consumption in Watts")
    controller_id: Optional[str] = Field(default=None, description="ID of the associated controller")

    @field_validator("controller_id")
    @classmethod
    def validate_controller_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate that controller_id is a valid UUID string if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError as exc:
                raise ValueError("controller_id must be a valid UUID string") from exc
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate miner name."""
        v = v.strip()
        if not v:
            v = ""
        return v

    def to_model(self) -> Miner:
        """Convert MinerCreateSchema to a Miner domain model instance."""
        return Miner(
            id=EntityId(uuid.uuid4()),
            name=self.name,
            status=MinerStatus.UNKNOWN,
            hash_rate=None,
            hash_rate_max=(
                HashRate(value=self.hash_rate_max.value, unit=self.hash_rate_max.unit) if self.hash_rate_max else None
            ),
            power_consumption=None,
            power_consumption_max=Watts(self.power_consumption_max) if self.power_consumption_max is not None else None,
            active=True,
            controller_id=EntityId(uuid.UUID(self.controller_id)) if self.controller_id else None,
        )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            uuid.UUID: str,
        }


class MinerUpdateSchema(BaseModel):
    """Schema for updating an existing miner."""

    name: Optional[str] = Field(default=None, max_length=255, description="Miner name")
    hash_rate_max: Optional[HashRateSchema] = Field(default=None, description="Maximum hash rate")
    power_consumption_max: Optional[float] = Field(default=None, ge=0, description="Maximum power consumption in Watts")
    active: Optional[bool] = Field(default=None, description="Whether the miner is active")
    controller_id: Optional[str] = Field(default=None, description="ID of the associated Miner controller")

    @field_validator("controller_id")
    @classmethod
    def validate_controller_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate that controller_id is a valid UUID string if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError as exc:
                raise ValueError("controller_id must be a valid UUID string") from exc
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate miner name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            uuid.UUID: str,
        }


class MinerControllerSchema(BaseModel):
    """Schema for MinerController entity with complete validation."""

    id: str = Field(..., description="Unique identifier for the miner controller")
    name: str = Field(default="", description="Controller name")
    adapter_type: MinerControllerAdapter = Field(
        default=MinerControllerAdapter.DUMMY, description="Type of controller adapter"
    )
    config: dict = Field(default={}, description="Controller configuration")
    external_service_id: Optional[str] = Field(default=None, description="ID of external service")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate that id is a valid UUID string."""
        try:
            uuid.UUID(v)
        except ValueError as exc:
            raise ValueError("id must be a valid UUID string") from exc
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate controller name."""
        v = v.strip()
        if not v:
            v = ""
        return v

    @field_validator("external_service_id")
    @classmethod
    def validate_external_service_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate that external_service_id is a valid UUID string if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError as exc:
                raise ValueError("external_service_id must be a valid UUID string") from exc
        return v

    @classmethod
    def from_model(cls, controller: "MinerController") -> "MinerControllerSchema":
        """Create MinerControllerSchema from a MinerController domain model instance."""
        return cls(
            id=str(controller.id),
            name=controller.name,
            adapter_type=controller.adapter_type,
            config=controller.config.to_dict() if controller.config else {},
            external_service_id=str(controller.external_service_id) if controller.external_service_id else None,
        )

    @field_serializer("id")
    def serialize_id(self, value: str) -> str:
        """Serialize id field."""
        return str(value)

    @field_serializer("external_service_id")
    def serialize_external_service_id(self, value: Optional[str]) -> Optional[str]:
        """Serialize external_service_id field."""
        return str(value) if value is not None else None

    def to_model(self) -> "MinerController":
        """Convert MinerControllerSchema to MinerController domain model instance."""
        configuration: Optional[MinerControllerConfig] = cast(
            MinerControllerConfig, MinerControllerConfig.from_dict(self.config) if self.config else {}
        )

        return MinerController(
            id=EntityId(uuid.UUID(self.id)),
            name=self.name,
            adapter_type=self.adapter_type,
            config=configuration,
            external_service_id=EntityId(uuid.UUID(self.external_service_id)) if self.external_service_id else None,
        )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
        json_encoders = {
            uuid.UUID: str,
            MinerControllerAdapter: lambda v: v.value,
        }


class MinerControllerCreateSchema(BaseModel):
    """Schema for creating a new miner controller."""

    name: str = Field(..., description="Controller name")
    adapter_type: MinerControllerAdapter = Field(
        default=MinerControllerAdapter.DUMMY, description="Type of controller adapter"
    )
    config: Optional[dict] = Field(default=None, description="Controller configuration")
    external_service_id: Optional[str] = Field(default=None, description="ID of external service")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate controller name."""
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("external_service_id")
    @classmethod
    def validate_external_service_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate that external_service_id is a valid UUID string if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError as exc:
                raise ValueError("external_service_id must be a valid UUID string") from exc
        return v

    def to_model(self) -> "MinerController":
        """Convert MinerControllerCreateSchema to a MinerController domain model instance."""
        configuration: Optional[MinerControllerConfig] = cast(
            MinerControllerConfig, MinerControllerConfig.from_dict(self.config) if self.config else None
        )

        return MinerController(
            id=EntityId(uuid.uuid4()),
            name=self.name,
            adapter_type=self.adapter_type,
            config=configuration,
            external_service_id=EntityId(uuid.UUID(self.external_service_id)) if self.external_service_id else None,
        )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            uuid.UUID: str,
            MinerControllerAdapter: lambda v: v.value,
        }


class MinerControllerUpdateSchema(BaseModel):
    """Schema for updating an existing miner controller."""

    name: Optional[str] = Field(default=None, description="Controller name")
    config: Optional[dict] = Field(default=None, description="Controller configuration")
    external_service_id: Optional[str] = Field(default=None, description="ID of external service")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate controller name."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Name cannot be empty")
        return v

    @field_validator("external_service_id")
    @classmethod
    def validate_external_service_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate that external_service_id is a valid UUID string if provided."""
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError as exc:
                raise ValueError("external_service_id must be a valid UUID string") from exc
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            uuid.UUID: str,
        }


class MinerControllerDummyConfigSchema(BaseModel):
    """Schema for Dummy MinerControllerConfig."""

    initial_status: MinerStatus = Field(default=MinerStatus.UNKNOWN, description="Initial status of the miner")
    power_max: float = Field(default=3200.0, description="Maximum power consumption in Watts")
    hashrate_max: HashRateSchema = Field(default=HashRateSchema(value=90, unit="TH/s"), description="Maximum hash rate")

    @field_validator("initial_status")
    @classmethod
    def validate_initial_status(cls, v: str) -> str:
        """Validate initial status."""
        allowed_statuses = [status.value for status in MinerStatus]
        if v not in allowed_statuses:
            raise ValueError(f"Initial status must be one of {allowed_statuses}")
        return v

    @field_validator("power_max")
    @classmethod
    def validate_power_max(cls, v: float) -> float:
        """Validate power max."""
        if v < 0:
            raise ValueError("Power max cannot be negative")
        return v

    def to_model(self) -> MinerControllerDummyConfig:
        """
        Convert MinerControllerDummyConfigSchema to MinerControllerDummyConfig adapter configuration model instance.
        """
        return MinerControllerDummyConfig(
            initial_status=self.initial_status.value,
            power_max=self.power_max,
            hashrate_max=HashRate(value=self.hashrate_max.value, unit=self.hashrate_max.unit),
        )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            uuid.UUID: str,
        }


MINER_CONTROLLER_CONFIG_SCHEMA_MAP: Dict[type[MinerControllerConfig], Union[type[MinerControllerDummyConfigSchema]]] = {
    MinerControllerDummyConfig: MinerControllerDummyConfigSchema,
}
