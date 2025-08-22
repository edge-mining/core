"""Collection of Value Objects for the Mining Device Management domain of the Edge Mining application."""

from dataclasses import dataclass

from edge_mining.domain.common import ValueObject


@dataclass(frozen=True)
class HashRate(ValueObject):
    """Value Object for a hash rate."""

    value: float  # e.g., TH/s
    unit: str = "TH/s"
