"""The External Service port."""

from abc import ABC, abstractmethod

class ExternalServicePort(ABC):
    """Interface for external service."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the external service."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the external service."""
        pass
