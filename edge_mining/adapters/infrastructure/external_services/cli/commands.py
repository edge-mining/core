"""CLI commands for the External Service domain."""

from typing import List, Optional, Union

import click

from edge_mining.application.interfaces import ConfigurationServiceInterface
from edge_mining.domain.common import EntityId
from edge_mining.domain.energy.entities import EnergyMonitor
from edge_mining.domain.forecast.entities import ForecastProvider
from edge_mining.domain.home_load.entities import HomeForecastProvider
from edge_mining.domain.miner.entities import MinerController
from edge_mining.domain.notification.entities import Notifier
from edge_mining.shared.adapter_configs.external_services import (
    ExternalServiceHomeAssistantConfig,
)
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.interfaces.config import ExternalServiceConfig
from edge_mining.shared.logging.port import LoggerPort

from edge_mining.adapters.infrastructure.cli.utils import (
    process_filters,
    print_configuration,
)


def select_external_service_type() -> Optional[ExternalServiceAdapter]:
    """Prompt user to select an external service adapter type."""
    click.echo("Select an External Service Type:")
    for idx, es_type in enumerate(ExternalServiceAdapter):
        if es_type is not ExternalServiceAdapter.UNKNOWN:
            click.echo(f"{idx}. {es_type.name}")

    click.echo("")
    choice: str = click.prompt("Choose an external service", type=str, default="")
    choice = choice.strip().lower()

    if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(ExternalServiceAdapter):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    es_type_values = [controller_type.value for controller_type in ExternalServiceAdapter]

    selected_type = ExternalServiceAdapter(es_type_values[int(choice)])
    return selected_type


def handle_external_service_home_assistant_api_config() -> Optional[ExternalServiceConfig]:
    """Prompt user for Home Assistant API configuration."""
    click.echo(click.style("\n--- Home Assistant API Configuration ---", fg="yellow"))

    url: str = click.prompt("Home Assistant URL", type=str)
    token: str = click.prompt("Long-Lived Access Token", type=str)

    return ExternalServiceHomeAssistantConfig(url=url, token=token)


def handle_external_service_configuration(
    adapter_type: ExternalServiceAdapter,
) -> Optional[ExternalServiceConfig]:
    """Prompt user for configuration based on the selected external service adapter type."""
    if adapter_type == ExternalServiceAdapter.HOME_ASSISTANT_API:
        return handle_external_service_home_assistant_api_config()
    else:
        click.echo(
            click.style(
                f"Configuration for {adapter_type.name} is not implemented yet.",
                fg="red",
            )
        )
        return None


def handle_add_external_service(
    configuration_service: ConfigurationServiceInterface, logger: LoggerPort
) -> Optional[ExternalService]:
    """Menu to add a new external service"""
    click.echo(click.style("\n--- Add External Service ---", fg="yellow"))
    name: str = click.prompt("Name of the external service", type=str)
    adapter_type: Optional[ExternalServiceAdapter] = select_external_service_type()

    if adapter_type is None:
        click.echo(click.style("Invalid external service type selected. Aborting.", fg="red"))
        return None

    config: Optional[ExternalServiceConfig] = handle_external_service_configuration(adapter_type)

    if config is None:
        click.echo(click.style("Invalid configuration provided. Aborting.", fg="red"))
        return None

    try:
        created_service = configuration_service.create_external_service(
            name=name, adapter_type=adapter_type, config=config
        )
        click.echo(
            click.style(
                f"External Service '{created_service.name}' (ID: {created_service.id}) successfully added.",
                fg="green",
            )
        )
    except Exception as e:
        created_service = None
        logger.error(f"Error creating external service: {e}")
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)

    click.pause("Press any key to return to the menu...")
    return created_service


def handle_list_external_services(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """Menu to list all configured external services."""
    click.echo(click.style("\n--- Configured External Services ---", fg="yellow"))

    services = configuration_service.list_external_services()
    if not services:
        click.echo(click.style("No external services configured.", fg="yellow"))
    else:
        for service in services:
            click.echo(
                "-> "
                + "Name: "
                + click.style(f"{service.name}, ", fg="blue")
                + "ID: "
                + click.style(f"{service.id}, ", fg="yellow")
                + "Type: "
                + click.style(f"{service.adapter_type.name}", fg="green")
            )

    click.echo("")
    click.pause("Press any key to return to the menu...")


def select_external_service(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
    filter_type: Optional[Union[ExternalServiceAdapter, List[ExternalServiceAdapter]]] = None,
) -> Optional[ExternalService]:
    """Select an external service from the list of configured services."""
    click.echo(click.style("\n--- Select External Service ---", fg="yellow"))

    services = configuration_service.list_external_services()

    filter_type = process_filters(filter_type)

    if filter_type:
        click.echo(
            "Filtering services by types: " + click.style(f"{', '.join([t.name for t in filter_type])}", fg="blue")
        )
        services = [s for s in services if s.adapter_type in filter_type]

    if not services:
        click.echo(click.style("No external services configured.", fg="yellow"))
        return None

    default_idx = ""
    for idx, service in enumerate(services):
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{service.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{service.id}, ", fg="yellow")
            + "Type: "
            + click.style(f"{service.adapter_type.name}", fg="green")
        )

        if default_id:
            if service.id == default_id:
                default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    choice: str = click.prompt("Choose an external service by index", type=str, default=default_idx)
    choice = choice.strip().lower()
    if choice == "b":
        return None
    if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(services):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_service = services[int(choice)]
    return selected_service


def print_external_service_config(external_service: ExternalService) -> None:
    """Print the configuration of a selected External Service."""
    configuration_class = external_service.config.__class__.__name__ if external_service.config else "---"
    click.echo("| Configuration: " + click.style(f"{configuration_class}", fg="cyan"))
    if external_service.config:
        print_configuration(external_service.config.to_dict())


def print_external_service_details(
    service: ExternalService,
    configuration_service: ConfigurationServiceInterface,
    show_config: bool = True,
    show_linked_instances: bool = False,
) -> None:
    """Print details of the selected external service."""
    click.echo("")
    click.echo("| Name: " + click.style(service.name, fg="blue"))
    click.echo("| ID: " + click.style(service.id, fg="yellow"))
    click.echo("| Adapter: " + click.style(service.adapter_type.name, fg="green"))
    if show_config:
        print_external_service_config(service)
    click.echo("")

    if show_linked_instances:
        external_service_linked_entities = configuration_service.get_entities_by_external_service(service.id)

        e: Union[
            EnergyMonitor,
            MinerController,
            ForecastProvider,
            HomeForecastProvider,
            Notifier,
        ]
        if external_service_linked_entities.energy_monitors:
            click.echo("Energy Monitors assigned:")
            for e in external_service_linked_entities.energy_monitors:
                click.echo(f"-> Name: {e.name} (ID: {e.id})")
            click.echo("")

        if external_service_linked_entities.miner_controllers:
            click.echo("Miner Controllers assigned:")
            for e in external_service_linked_entities.miner_controllers:
                click.echo(f"-> Name: {e.name} (ID: {e.id})")
            click.echo("")

        if external_service_linked_entities.forecast_providers:
            click.echo("Forecast Providers assigned:")
            for e in external_service_linked_entities.forecast_providers:
                click.echo(f"-> Name: {e.name} (ID: {e.id})")
            click.echo("")

        if external_service_linked_entities.home_forecast_providers:
            click.echo("Home Forecast Providers assigned:")
            for e in external_service_linked_entities.home_forecast_providers:
                click.echo(f"-> Name: {e.name} (ID: {e.id})")
            click.echo("")

        if external_service_linked_entities.notifiers:
            click.echo("Notifiers assigned:")
            for e in external_service_linked_entities.notifiers:
                click.echo(f"-> Name: {e.name} (ID: {e.id})")
            click.echo("")


def update_single_external_service(
    service: ExternalService,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[ExternalService]:
    """Menu to update an external service"""
    name: str = click.prompt("New name of the external service", type=str, default=service.name)
    config: Optional[ExternalServiceConfig] = handle_external_service_configuration(adapter_type=service.adapter_type)

    if config is None:
        click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
        return None

    try:
        updated_external_service = configuration_service.update_external_service(
            service_id=service.id, name=name, config=config
        )
    except Exception as e:
        logger.error(f"Error updating external service: {e}")
        click.echo(
            click.style(f"Error updating external service: {e}", fg="red"),
            err=True,
        )
        updated_external_service = None

    click.pause("Press any key to return to the menu...")

    return updated_external_service


def delete_single_external_service(
    service: ExternalService,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> bool:
    """Delete a specific external service."""
    delete_confirm = click.confirm(
        f"Are you sure you want to remove the External Service '{service.name}' (ID: {service.id})?",
        abort=False,
        default=False,
        prompt_suffix="",
    )

    if not delete_confirm:
        click.echo(click.style("Removal cancelled.", fg="yellow"))
        return False

    try:
        removed_external_service = configuration_service.remove_external_service(service.id)
        click.echo(
            click.style(
                f"External Service '{removed_external_service.name}' successfully deleted.",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error deleting external service: {e}")
        click.echo(
            click.style(f"Error removing external service: {e}", fg="red"),
            err=True,
        )
        return False
    else:
        return True


def manage_single_external_service_menu(
    selected_service: ExternalService,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> str:
    """Menu to manage a single external service."""
    while True:
        click.echo("\n" + click.style("--- MANAGE EXTERNAL SERVICE ---", fg="yellow", bold=True))

        print_external_service_details(selected_service, configuration_service, show_linked_instances=True)

        click.echo("1. Update External Service")
        click.echo("2. Delete External Service")
        click.echo("")
        click.echo("b. Back to external services menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str, default="")
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            updated_external_service = update_single_external_service(
                service=selected_service,
                configuration_service=configuration_service,
                logger=logger,
            )
            selected_service = (
                updated_external_service or selected_service
            )  # Update external service if it was successfully updated
            continue

        elif choice == "2":
            delete_status = delete_single_external_service(
                service=selected_service,
                configuration_service=configuration_service,
                logger=logger,
            )
            if delete_status:
                return "b"  # Return to menu if deletion was successful
            continue

        elif choice == "b":
            break

        elif choice == "q":
            break
        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice


def external_services_menu(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu for managing External Services."""
    while True:
        click.echo("\n" + click.style("--- EXTERNAL SERVICES ---", fg="blue", bold=True))
        click.echo("1. Add an External Service")
        click.echo("2. List all External Services")
        click.echo("3. Manage an External Service")
        click.echo("")
        click.echo("b. Back to main menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            handle_add_external_service(configuration_service=configuration_service, logger=logger)
        elif choice == "2":
            handle_list_external_services(configuration_service=configuration_service, logger=logger)
        elif choice == "3":
            service = select_external_service(configuration_service, logger)
            if service is None:
                click.echo(click.style("No external service selected. Aborting.", fg="red"))
                continue

            sub_choice = manage_single_external_service_menu(
                selected_service=service,
                configuration_service=configuration_service,
                logger=logger,
            )
            if sub_choice == "q":
                choice = "q"  # Exit if user chose to quit from external service menu
                break

        elif choice == "b":
            break

        elif choice == "q":
            break

        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")
    return choice
