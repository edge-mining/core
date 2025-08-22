"""Collection of Exceptions."""

from edge_mining.domain.exceptions import DomainError


class MiningPerformanceTrackerError(DomainError):
    """Base class for performance tracker-specific errors."""

    pass


class MiningPerformanceTrackerNotFoundError(MiningPerformanceTrackerError):
    """Performance Tracker not found."""

    pass


class MiningPerformanceTrackerAlreadyExistsError(MiningPerformanceTrackerError):
    """Performance Tracker already exists."""

    pass


class MiningPerformanceTrackerConfigurationError(MiningPerformanceTrackerError):
    """Error with the configuration."""

    pass
