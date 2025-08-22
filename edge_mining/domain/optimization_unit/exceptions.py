"""Collection of Exceptions."""

from edge_mining.domain.exceptions import DomainError


class OptimizationUnitError(DomainError):
    """Errors related to optimization units."""

    pass


class OptimizationUnitNotFoundError(OptimizationUnitError):
    """Optimization unit not found."""

    pass


class OptimizationUnitAlreadyExistsError(OptimizationUnitError):
    """Optimization unit already exists."""

    pass


class OptimizationUnitConfigurationError(OptimizationUnitError):
    """Error in optimization unit configuration."""

    pass
