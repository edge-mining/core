"""CLI commands for the Energy Optimization Unit domain."""

from uuid import UUID
import click

from edge_mining.application.interfaces import ConfigurationServiceInterface
from edge_mining.domain.common import EntityId
from edge_mining.shared.logging.port import LoggerPort


def handle_create_optimization_unit(configuration_service: ConfigurationServiceInterface, logger: LoggerPort):
    """Menu to create a new optimization unit."""

    click.echo(click.style("\n--- Creates a new Energy Optimization Unit ---", fg="yellow"))

    name: str = click.prompt("Name of the energy optimization unit", type=str)
    description: str = click.prompt("Description (optional)", type=str, default="")
    energy_source_id: str = click.prompt("Energy source ID (optional)", type=str, default="")
    target_miner_ids_str: str = click.prompt("Miner target IDs (comma separated, optional)", type=str, default="")
    policy_id: str = click.prompt("Policy ID (optional)", type=str, default="")
    home_forecast_provider_id: str = click.prompt("Home forcast provider ID (optional)", type=str, default="")
    performance_tracker_id: str = click.prompt("Performace tracker ID (optional)", type=str, default="")
    notifier_ids_str: str = click.prompt("Notifiers IDs (comma separated, optional)", type=str, default="")

    try:
        target_miner_ids = (
            [EntityId(UUID(m.strip())) for m in target_miner_ids_str.split(",")] if target_miner_ids_str else []
        )
        notifier_ids = [EntityId(UUID(n.strip())) for n in notifier_ids_str.split(",")] if notifier_ids_str else []

        created = configuration_service.create_optimization_unit(
            name=name,
            description=description if description else None,
            energy_source_id=(EntityId(UUID(energy_source_id)) if energy_source_id else None),
            target_miner_ids=target_miner_ids,
            policy_id=EntityId(UUID(policy_id)) if policy_id else None,
            home_forecast_provider_id=(
                EntityId(UUID(home_forecast_provider_id)) if home_forecast_provider_id else None
            ),
            performance_tracker_id=(EntityId(UUID(performance_tracker_id)) if performance_tracker_id else None),
            notifier_ids=notifier_ids,
        )
        if not created:
            raise ValueError("Failed to create the optimization unit.")
        click.echo(
            click.style(
                f"Energy Optimization Unit '{created.name}' successfully created (ID: {created.id}).",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error creating optimization unit: {e}")
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
    click.pause("Press any key to return to the menu...")


def list_optimization_units(
    configuration_service: ConfigurationServiceInterface,
) -> None:
    """List all configured optimization units."""
    units = configuration_service.list_optimization_units()
    if not units:
        click.echo(click.style("No optimization units configured.", fg="yellow"))
    else:
        for u in units:
            click.echo(
                f"-> ID: {u.id}, Name: {u.name}, "
                f"Description: {u.description if u.description else 'N/A'}, "
                f"Miner Target: {', '.join(str(u.target_miner_ids)) if u.target_miner_ids else 'N/A'}"
            )


def handle_list_optimization_units(
    configuration_service: ConfigurationServiceInterface,
) -> None:
    """Menu to list all configured optimization units."""
    click.echo(click.style("\n--- Configured Energy Optimization Units ---", fg="yellow"))

    list_optimization_units(configuration_service)

    click.pause("Press any key to return to the menu...")


def optimization_unit_menu(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu for managing Optimization Units."""
    while True:
        click.echo("\n" + click.style("--- MENU ENERGY OPTIMIZATION UNIT ---", fg="yellow", bold=True))
        click.echo("1. Create new Energy Optimization Unit")
        click.echo("2. List all configured Energy Optimization Units")
        click.echo("b. Back to main menu")
        click.echo("q. Close application")
        click.echo("---------------------------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            handle_create_optimization_unit(configuration_service=configuration_service, logger=logger)
        elif choice == "2":
            handle_list_optimization_units(configuration_service=configuration_service)
        elif choice == "b":
            break
        elif choice == "q":
            break
        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice
