"""Collection of Value Objects for the Energy Forecast domain of the Edge Mining application."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Tuple
from datetime import datetime

from edge_mining.domain.common import Watts, WattHours, Timestamp, ValueObject

@dataclass(frozen=True)
class ForecastData(ValueObject):
    """Value Object for a forecast data."""
    predicted_power: Optional[Dict[Timestamp, Watts]] = field(default_factory=dict) # Predicted power generation at specific future times
    predicted_energy: Optional[Dict[Tuple[Timestamp, Timestamp], WattHours]] = field(default_factory=dict) # Predicted energy generation at specific future time range
    generated_at: Timestamp = field(default_factory=datetime.now)