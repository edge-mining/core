"""Collection of Value Objects for the Home Consumption Analytics domain of the Edge Mining application."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

from edge_mining.domain.common import Timestamp, ValueObject, Watts


@dataclass(frozen=True)
class ConsumptionForecast(ValueObject):
    """Value Object for a consumption forecast."""

    # Predicted consumption for a future period
    predicted_watts: Dict[Timestamp, Watts] = field(default_factory=dict)
    generated_at: Timestamp = field(default_factory=Timestamp(datetime.now()))
