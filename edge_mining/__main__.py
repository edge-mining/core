"""Start Edge Mining."""

import asyncio
import sys

import uvicorn

from edge_mining.adapters.infrastructure.api.main_api import app as fastapi_app
from edge_mining.adapters.infrastructure.api.setup import init_api_dependencies
from edge_mining.adapters.infrastructure.cli.main_cli import run_cli
from edge_mining.adapters.infrastructure.logging.terminal_logging import TerminalLogger
from edge_mining.adapters.infrastructure.sheduler.jobs import AutomationScheduler
from edge_mining.bootstrap import configure_dependencies
from edge_mining.shared.infrastructure import ApplicationMode, Services
from edge_mining.shared.settings.settings import AppSettings

settings = AppSettings()
logger = TerminalLogger(log_level=settings.log_level)


async def main_async():
    """Main entry point for the Edge Mining application."""
    logger.welcome()

    # --- Dependency Injection ---
    try:
        services: Services = configure_dependencies(logger, settings)
    except Exception as e:
        logger.critical(f"Failed to configure dependencies. Exiting. {e}")
        sys.exit(1)

    # Inject services into CLI and API
    init_api_dependencies(services, logger)
    logger.debug("API dependencies initialized successfully")

    # --- Determine Run Mode ---
    # Example: Use command-line argument to choose mode
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        # Remove mode argument so Click/FastAPI don't see it
        sys.argv.pop(1)
    else:
        mode = ApplicationMode.STANDARD  # Default mode

    logger.debug(f"Running in '{mode}' mode.")

    if mode == ApplicationMode.STANDARD.value:
        # --- Run the FastAPI server ---
        logger.debug("Starting FastAPI server with Uvicorn...")
        # Note: Uvicorn might reload and cause DI to run multiple times if
        # --reload is used.
        # We should to consider more robust DI setup for production APIs.
        api_config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=settings.api_port,
            log_level=settings.log_level.lower(),
        )
        api_server = uvicorn.Server(api_config)

        # --- Run the main automation loop ---
        scheduler = AutomationScheduler(
            optimization_service=services.optimization_service,
            logger=logger,
            settings=settings,
        )

        await asyncio.gather(
            api_server.serve(),  # Run the FastAPI server
            scheduler.start(),  # Run the automation scheduler
        )

    elif mode == ApplicationMode.CLI.value:
        # Run Click CLI with injected services
        run_cli(services, logger)

    else:
        logger.error(
            f"Unknown run mode: '{mode}'. Use '{ApplicationMode.STANDARD.value}', or '{ApplicationMode.CLI.value}'."
        )
        sys.exit(1)


def main():
    """Main entry point for the Edge Mining application (synchronous wrapper)."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
    except Exception as e:
        logger.error(f"Unhandled exception during main execution: {e}")
    finally:
        # Sure to flush logs before exiting
        logger.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()
