"""Interactive CLI for Edge Mining."""

import click

from edge_mining.adapters.domain.energy.cli.commands import energy_menu
from edge_mining.adapters.domain.forecast.cli.commands import forecast_menu
from edge_mining.adapters.domain.miner.cli.commands import miner_menu
from edge_mining.adapters.domain.notification.cli.commands import notifier_menu
from edge_mining.adapters.domain.optimization_unit.cli.commands import optimization_unit_menu
from edge_mining.adapters.domain.policy.cli.commands import policy_menu
from edge_mining.adapters.infrastructure.cli.setup import cli
from edge_mining.adapters.infrastructure.cli.utils import run_evaluation
from edge_mining.adapters.infrastructure.external_services.cli.commands import external_services_menu
from edge_mining.shared.infrastructure import Services
from edge_mining.shared.logging.port import LoggerPort


# --- Main Menu Logic ---
@cli.command("interactive")
@click.pass_context
def interactive(ctx: click.Context):
    """Interactive main CLI menu for Edge Mining."""
    services: Services = ctx.obj[Services]
    logger: LoggerPort = ctx.obj[LoggerPort]

    click.echo(click.style("Welcome to the Edge Mining CLI!", fg="cyan", bold=True))
    click.echo("Select an option or use 'q' to quit.")

    sub_choice: str = ""

    while True:
        click.echo(click.style("\n--- Main Menu ---", fg="blue"))
        click.echo("1. Manage Energy")
        click.echo("2. Manage Forecast")
        click.echo("3. Manage Miners")
        click.echo("4. Manage Policies")
        click.echo("5. Manage Notifiers")
        click.echo("")
        click.echo("6. Manage Energy Optimization Units")
        click.echo("")
        click.echo("7. Manage External Services")
        click.echo("")
        click.echo("8. Run all optimization units)")
        click.echo("q. Close application")
        click.echo("--------------------------")

        sub_choice = ""
        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        if choice == "1":
            sub_choice = energy_menu(
                configuration_service=services.configuration_service,
                logger=logger,
            )

            if sub_choice == "q":
                break
        elif choice == "2":
            sub_choice = forecast_menu(
                configuration_service=services.configuration_service,
                logger=logger,
            )

            if sub_choice == "q":
                break
        elif choice == "3":
            sub_choice = miner_menu(
                configuration_service=services.configuration_service,
                logger=logger,
            )

            if sub_choice == "q":
                break
        elif choice == "4":
            sub_choice = policy_menu(
                configuration_service=services.configuration_service,
                logger=logger,
            )

            if sub_choice == "q":
                break
        elif choice == "5":
            sub_choice = notifier_menu(
                configuration_service=services.configuration_service,
                logger=logger,
            )

            if sub_choice == "q":
                break
        elif choice == "6":
            sub_choice = optimization_unit_menu(
                configuration_service=services.configuration_service,
                logger=logger,
            )

            if sub_choice == "q":
                break
        elif choice == "7":
            sub_choice = external_services_menu(
                configuration_service=services.configuration_service,
                logger=logger,
            )

            if sub_choice == "q":
                break
        elif choice == "8":
            run_evaluation(services.optimization_service)
        elif choice == "q":
            break
        else:
            click.echo(click.style("Invalid option, please try again.", fg="red"))
