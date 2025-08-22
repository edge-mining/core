"""Terminal CLI infrastructure adapter"""

from edge_mining.shared.infrastructure import Services
from edge_mining.shared.logging.port import LoggerPort

from edge_mining.adapters.infrastructure.cli.setup import cli

from edge_mining.adapters.infrastructure.cli.interactive import interactive
from edge_mining.adapters.infrastructure.cli.commands import (
    optimization_unit,
    miner,
    policy,
    manage_run_evaluation,
)

# Add interactive CLI command
cli.add_command(interactive, name="interactive")
# Add optimization unit CLI commands
cli.add_command(optimization_unit, name="optimization-unit")
# Add miner CLI commands
cli.add_command(miner, name="miner")
# Add policy CLI commands
cli.add_command(policy, name="policy")
# Add run evaluation command
cli.add_command(manage_run_evaluation, name="run-evaluation")


# --- CLI main execution ---
def run_cli(services: Services, logger: LoggerPort):
    """
    Main function to launch the CLI.
    """

    # Creates context object to pass services and logger
    context_data = {Services: services, LoggerPort: logger}

    # Creates a context object to pass services and logger using class names
    cli.main(obj=context_data)
