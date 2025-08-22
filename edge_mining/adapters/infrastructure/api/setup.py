"""Setup for FastAPI application with Dependency Injection."""

from typing import Optional

from fastapi import Depends, HTTPException

from edge_mining.application.interfaces import (
    AdapterServiceInterface,
    ConfigurationServiceInterface,
    MinerActionServiceInterface,
    OptimizationServiceInterface,
)
from edge_mining.shared.infrastructure import Services
from edge_mining.shared.logging.port import LoggerPort


class ServiceContainer:
    """Container for application services - thread-safe singleton pattern."""

    _instance: Optional["ServiceContainer"] = None
    _services: Optional[Services] = None
    _logger: Optional[LoggerPort] = None
    _initialized: bool = False

    def __new__(cls) -> "ServiceContainer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, services: Services, logger: LoggerPort) -> None:
        """Initialize the container with services."""
        if self._initialized:
            return  # Already initialized

        self._services = services
        self._logger = logger
        self._initialized = True

    def is_initialized(self) -> bool:
        """Check if container is initialized."""
        return self._initialized

    @property
    def services(self) -> Services:
        """Get services instance."""
        if not self._initialized or self._services is None:
            raise HTTPException(
                status_code=500,
                detail="Services not initialized. Application startup failed.",
            )
        return self._services

    @property
    def logger(self) -> LoggerPort:
        """Get logger instance."""
        if not self._initialized or self._logger is None:
            raise HTTPException(
                status_code=500,
                detail="Logger not initialized. Application startup failed.",
            )
        return self._logger


# Global container instance
_container = ServiceContainer()


# FastAPI dependency functions - these are what we inject in endpoints
async def get_service_container() -> ServiceContainer:
    """Get the service container."""
    return _container


async def get_adapter_service(
    container: ServiceContainer = Depends(get_service_container),
) -> AdapterServiceInterface:
    """Get AdapterService via dependency injection."""
    return container.services.adapter_service


async def get_config_service(
    container: ServiceContainer = Depends(get_service_container),
) -> ConfigurationServiceInterface:
    """Get ConfigurationService via dependency injection."""
    return container.services.configuration_service


async def get_miner_action_service(
    container: ServiceContainer = Depends(get_service_container),
) -> MinerActionServiceInterface:
    """Get MinerActionService via dependency injection."""
    return container.services.miner_action_service


async def get_optimization_service(
    container: ServiceContainer = Depends(get_service_container),
) -> OptimizationServiceInterface:
    """Get OptimizationService via dependency injection."""
    return container.services.optimization_service


async def get_logger(
    container: ServiceContainer = Depends(get_service_container),
) -> LoggerPort:
    """Get LoggerPort via dependency injection."""
    return container.logger


# Initialization function to replace set_api_services
def init_api_dependencies(services: Services, logger: LoggerPort) -> None:
    """Initialize API dependencies - call this during app startup."""
    _container.initialize(services, logger)
