"""Collection of Common Objects for the Edge Mining application domain."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import NewType, Tuple

# Example Value Objects using NewType for stronger typing
Watts = NewType("Watts", float)
WattHours = NewType("WattHours", float)
Percentage = NewType("Percentage", float)  # 0.0 to 100.0
Timestamp = NewType("Timestamp", datetime)
EntityId = NewType("EntityId", uuid.UUID)

TimePeriod = Tuple[datetime, datetime]


@dataclass(frozen=True)
class ValueObject:
    """Base class for value objects."""

    pass  # Base class for value objects if needed


@dataclass
class Entity:
    """Base class for entities."""

    id: EntityId = field(default_factory=lambda: EntityId(uuid.uuid4()))


@dataclass
class AggregateRoot:
    """Base class for aggregate roots."""

    id: EntityId = field(default_factory=EntityId(uuid.uuid4()))


class AdapterType(Enum):
    """Base class for adapter types."""

    pass  # Base class for adapter types if needed
