"""Collection of Exceptions."""

from edge_mining.domain.exceptions import DomainError


class EnergyError(DomainError):
    """Base class for energy-related errors."""

    pass


class EnergyMonitorError(EnergyError):
    """Errors related to energy monitors."""

    pass


class EnergyMonitorNotFoundError(EnergyMonitorError):
    """Energy monitor not found."""

    pass


class EnergyMonitorAlreadyExistsError(EnergyMonitorError):
    """Energy monitor already exists."""

    pass


class EnergyMonitorConfigurationError(EnergyMonitorError):
    """Error with the configuration."""

    pass


class EnergySourceError(EnergyError):
    """Errors related to energy sources."""

    pass


class EnergySourceNotFoundError(EnergySourceError):
    """Energy source not found."""

    pass


class EnergySourceAlreadyExistsError(EnergySourceError):
    """Energy source already exists."""

    pass


class EnergySourceConfigurationError(EnergySourceError):
    """Errors related to energy source configuration."""

    pass
