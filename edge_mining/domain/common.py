"""Collection of Common Objects for the Edge Mining application domain."""

from dataclasses import dataclass
from typing import NewType
from datetime import datetime
import uuid

# Example Value Objects using NewType for stronger typing
Watts = NewType("Watts", float)
WattHours = NewType("WattHours", float)
Percentage = NewType("Percentage", float) # 0.0 to 100.0
Timestamp = NewType("Timestamp", datetime)
EntityId = NewType("EntityId", uuid.UUID)

@dataclass(frozen=True)
class ValueObject:
    """Base class for value objects."""
    pass # Base class for value objects if needed
