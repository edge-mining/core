"""Initializes the FastAPI application for the Edge Mining system."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import routers after DI setup functions are defined
from edge_mining.adapters.domain.miner.fast_api.router import router as miner_router
from edge_mining.adapters.domain.policy.fast_api.router import router as policy_router

# Import dependency injection setup functions
from edge_mining.adapters.infrastructure.api.setup import get_logger, get_optimization_service, get_service_container
from edge_mining.application.services.optimization_service import OptimizationService
from edge_mining.shared.logging.port import LoggerPort


@asynccontextmanager
async def app_lifespan(api_app: FastAPI):
    """Application lifespan - startup and shutdown logic."""
    # Startup
    try:
        container = await get_service_container()
        if not container.is_initialized():
            # This should not happen if properly initialized in main
            raise RuntimeError("Services not initialized before FastAPI startup!")

        container.logger.info("FastAPI application started successfully")

        # We can add other startup logic here
        # e.g., database connections, external service checks, etc.

    except Exception as e:
        print(f"Failed to start FastAPI application: {e}")
        raise

    yield  # Application is running

    # Shutdown
    try:
        container.logger.info("FastAPI application shutting down...")
        # Add cleanup logic here if needed
    except Exception as e:
        print(f"Error during shutdown: {e}")


app = FastAPI(
    title="Edge Mining API",
    description="API for managing and monitoring the bitcoin mining energy optimization system.",
    version="0.1.0",
    lifespan=app_lifespan,
)

# TODO: set only localhost origins
origins = ["*"]

# User CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(miner_router, prefix="/api/v1", tags=["mining"])
app.include_router(policy_router, prefix="/api/v1", tags=["optimization_rules"])
# Add more routers here (e.g., for configuration)


@app.get("/health", tags=["system"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}


# Example endpoint using dependency injection
@app.post("/api/v1/evaluate", tags=["system"])
async def trigger_evaluation(
    logger: Annotated[LoggerPort, Depends(get_logger)],  # Inject logger
    optimization_service: Annotated[OptimizationService, Depends(get_optimization_service)],  # Inject service
):
    """Manually run all enabled optimization units."""
    logger.info("API run all enabled optimization units...")
    try:
        await optimization_service.run_all_enabled_units()
        return {"message": "All optimization units run successfully."}
    except Exception as e:
        logger.error("Error during API run optimization units.")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}") from e


# --- To run this API (after setting up services): ---
# uvicorn edge_mining.adapters.infrastructure.api.main_api:app --reload
