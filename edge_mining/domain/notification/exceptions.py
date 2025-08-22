"""Collection of Exceptions."""

from edge_mining.domain.exceptions import DomainError


class NotificationError(DomainError):
    """Errors related to notifications."""

    pass


class NotifierError(NotificationError):
    """Errors related to notifier."""

    pass


class NotifierNotFoundError(NotifierError):
    """Notifier not found."""

    pass


class NotifierAlreadyExistsError(NotifierError):
    """Notifier already exists."""

    pass


class NotifierConfigurationError(NotifierError):
    """Error with the configuration."""

    pass
