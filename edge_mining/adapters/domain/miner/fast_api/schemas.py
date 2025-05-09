"""Pydantic models for miner domain"""

from pydantic import BaseModel
from typing import List, Optional, Annotated

class MinerSchema(BaseModel):
    id: str
    name: str
    ip_address: Optional[str] = None
    power_consumption: Optional[str] = None