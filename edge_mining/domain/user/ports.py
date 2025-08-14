"""Collection of Ports for the User Settings domain of the Edge Mining application."""

from abc import ABC, abstractmethod
from typing import Optional

from edge_mining.domain.user.common import UserId
from edge_mining.domain.user.entities import User

class UserRepository(ABC):
    """Port for the User Repository."""

    @abstractmethod
    def get_by_id(self, user_id: UserId) -> Optional[User]:
        """Gets a user by its ID."""
        raise NotImplementedError
    # ... other methods as needed

