"""Collection of Common Objects for the Settings shared domain of the Edge Mining application."""

from enum import Enum


class PersistenceAdapter(Enum):
    """Types of persistence adapter."""

    IN_MEMORY = "in_memory"
    SQLITE = "sqlite"
    YAML = "yaml"
