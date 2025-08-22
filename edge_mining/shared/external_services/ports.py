"""The External Services port."""

from abc import ABC, abstractmethod
from typing import List, Optional

from edge_mining.domain.common import EntityId
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.entities import ExternalService


class ExternalServicePort(ABC):
    """Interface for external service."""

    def __init__(self, external_service_type: ExternalServiceAdapter):
        """Initialize the External Service."""
        self.external_service_type = external_service_type

    @abstractmethod
    def connect(self) -> None:
        """Connect to the external service."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the external service."""
        pass


class ExternalServiceRepository(ABC):
    """Port for the External Service Repository."""

    @abstractmethod
    def add(self, external_service: ExternalService) -> None:
        """Adds a new external service to the repository."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, external_service_id: EntityId) -> Optional[ExternalService]:
        """Retrieves an external service by its ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[ExternalService]:
        """Retrieves all external services from the repository."""
        raise NotImplementedError

    @abstractmethod
    def update(self, external_service: ExternalService) -> None:
        """Updates an external service in the repository."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, external_service_id: EntityId) -> None:
        """Removes an external service from the repository."""
        raise NotImplementedError
