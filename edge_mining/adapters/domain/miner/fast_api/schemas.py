"""Pydantic models for miner domain"""

from typing import Optional
from pydantic import BaseModel

from edge_mining.domain.miner.value_objects import HashRate

class MinerResponseSchema(BaseModel):
    """Schema for returning a miner"""
    id: str
    name: str
    status: str
    active: bool
    ip_address: Optional[str] = None
    hash_rate: Optional[HashRate] = None
    hash_rate_max: Optional[HashRate] = None
    power_consumption: Optional[float] = None
    power_consumption_max: Optional[float] = None

class MinerCreateSchema(BaseModel):
    """Schema for creating a miner"""
    name: str
    active: bool
    ip_address: Optional[str] = None
    hash_rate_max: Optional[HashRate] = None
    power_consumption_max: Optional[float] = None

class MinerUpdateSchema(BaseModel):
    """Schema for updating a miner"""
    name: str
    active: bool
    ip_address: Optional[str] = None
    hash_rate_max: Optional[HashRate] = None
    power_consumption_max: Optional[float] = None

class MinerStatusSchema(BaseModel):
    """Schema for miner status"""
    id: str
    status: str
    active: bool
    hash_rate: Optional[HashRate] = None
    power_consumption: Optional[float] = None
