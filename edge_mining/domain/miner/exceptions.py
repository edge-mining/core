"""Collection of Exceptions."""

from edge_mining.domain.exceptions import DomainError


class MinerError(DomainError):
    """Errors related to miners."""

    pass


class MinerNotFoundError(MinerError):
    """Miner not found."""

    pass


class MinerNotActiveError(MinerError):
    """Miner not active."""

    pass


class MinerControllerError(DomainError):
    """Errors related to miner controllers."""

    pass


class MinerControllerNotFoundError(MinerControllerError):
    """Miner controller not found."""

    pass


class MinerControllerAlreadyExistsError(MinerControllerError):
    """Miner controller already exists."""

    pass


class MinerControllerConfigurationError(MinerControllerError):
    """Error with the configuration."""

    pass
