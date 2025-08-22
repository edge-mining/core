"""CLI commands for the energy forecast domain."""

from typing import List, Optional

import click

from edge_mining.adapters.infrastructure.cli.utils import print_configuration, process_filters
from edge_mining.adapters.infrastructure.external_services.cli.commands import (
    print_external_service_details,
    select_external_service,
)
from edge_mining.application.interfaces import ConfigurationServiceInterface
from edge_mining.domain.common import EntityId
from edge_mining.domain.forecast.common import ForecastProviderAdapter
from edge_mining.domain.forecast.entities import ForecastProvider
from edge_mining.shared.adapter_configs.forecast import (
    ForecastProviderDummySolarConfig,
    ForecastProviderHomeAssistantConfig,
)
from edge_mining.shared.adapter_maps.forecast import FORECAST_PROVIDER_TYPE_EXTERNAL_SERVICE_MAP
from edge_mining.shared.external_services.common import ExternalServiceAdapter
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.interfaces.config import ForecastProviderConfig
from edge_mining.shared.logging.port import LoggerPort


def select_forecast_provider_adapter() -> Optional[ForecastProviderAdapter]:
    """Select a forecast provider adapter from the available options."""
    click.echo("Select a Forecast Provider Adapter:")
    for idx, adapter in enumerate(ForecastProviderAdapter):
        click.echo(f"{idx}. " + click.style(f"{adapter.name}", fg="blue"))

    click.echo("")
    choice: str = click.prompt("Choose a forecast provider adapter", type=str, default="")
    choice = choice.strip().lower()

    if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(ForecastProviderAdapter):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    adapter_type_values = [adapter.value for adapter in ForecastProviderAdapter]

    selected_adapter = ForecastProviderAdapter(adapter_type_values[int(choice)])
    return selected_adapter


def handle_forecast_provider_dummy_config() -> ForecastProviderConfig:
    """Handle the configuration for the dummy forecast provider."""
    click.echo(click.style("\n--- Dummy Forecast Configuration ---", fg="yellow"))

    latitude: float = click.prompt("Latitude", type=float, default=41.90)
    longitude: float = click.prompt("Longitude", type=float, default=12.49)
    capacity_kwp: float = click.prompt("Capacity (kWp)", type=float, default=0.0)
    efficiency_percent: float = click.prompt("Efficiency (%)", type=float, default=80.0)
    production_start_hour: int = click.prompt("Production Start Hour (0-23)", type=int, default=6)
    production_end_hour: int = click.prompt("Production End Hour (0-23)", type=int, default=20)

    return ForecastProviderDummySolarConfig(
        latitude=latitude,
        longitude=longitude,
        capacity_kwp=capacity_kwp,
        efficiency_percent=efficiency_percent,
        production_start_hour=production_start_hour,
        production_end_hour=production_end_hour,
    )


def handle_forecast_provider_home_assistant_api_config() -> ForecastProviderConfig:
    """Handle the configuration for the Home Assistant API forecast provider."""
    click.echo(click.style("\n--- Home Assistant API Configuration ---", fg="yellow"))

    entity_forecast_power_actual_h: str = click.prompt("Entity Forecast Power Actual (h)", type=str, default="")
    entity_forecast_power_next_1h: str = click.prompt("Entity Forecast Power Next 1h", type=str, default="")
    entity_forecast_power_next_12h: str = click.prompt("Entity Forecast Power Next 12h", type=str, default="")
    entity_forecast_power_next_24h: str = click.prompt("Entity Forecast Power Next 24h", type=str, default="")
    entity_forecast_energy_actual_h: str = click.prompt("Entity Forecast Energy Actual (h)", type=str, default="")
    entity_forecast_energy_next_1h: str = click.prompt("Entity Forecast Energy Next 1h", type=str, default="")
    entity_forecast_energy_today: str = click.prompt("Entity Forecast Energy Today", type=str, default="")
    entity_forecast_energy_tomorrow: str = click.prompt("Entity Forecast Energy Tomorrow", type=str, default="")
    entity_forecast_energy_remaining_today: str = click.prompt(
        "Entity Forecast Energy Remaining Today", type=str, default=""
    )

    unit_forecast_power_actual_h: str = click.prompt("Unit Forecast Power Actual (h)", type=str, default="W")
    unit_forecast_power_next_1h: str = click.prompt("Unit Forecast Power Next 1h", type=str, default="W")
    unit_forecast_power_next_12h: str = click.prompt("Unit Forecast Power Next 12h", type=str, default="W")
    unit_forecast_power_next_24h: str = click.prompt("Unit Forecast Power Next 24h", type=str, default="W")
    unit_forecast_energy_actual_h: str = click.prompt("Unit Forecast Energy Actual (h)", type=str, default="kWh")
    unit_forecast_energy_next_1h: str = click.prompt("Unit Forecast Energy Next 1h", type=str, default="kWh")
    unit_forecast_energy_today: str = click.prompt("Unit Forecast Energy Today", type=str, default="kWh")
    unit_forecast_energy_tomorrow: str = click.prompt("Unit Forecast Energy Tomorrow", type=str, default="kWh")
    unit_forecast_energy_remaining_today: str = click.prompt(
        "Unit Forecast Energy Remaining Today", type=str, default="kWh"
    )
    return ForecastProviderHomeAssistantConfig(
        entity_forecast_power_actual_h=entity_forecast_power_actual_h,
        entity_forecast_power_next_1h=entity_forecast_power_next_1h,
        entity_forecast_power_next_12h=entity_forecast_power_next_12h,
        entity_forecast_power_next_24h=entity_forecast_power_next_24h,
        entity_forecast_energy_actual_h=entity_forecast_energy_actual_h,
        entity_forecast_energy_next_1h=entity_forecast_energy_next_1h,
        entity_forecast_energy_today=entity_forecast_energy_today,
        entity_forecast_energy_tomorrow=entity_forecast_energy_tomorrow,
        entity_forecast_energy_remaining_today=entity_forecast_energy_remaining_today,
        unit_forecast_power_actual_h=unit_forecast_power_actual_h,
        unit_forecast_power_next_1h=unit_forecast_power_next_1h,
        unit_forecast_power_next_12h=unit_forecast_power_next_12h,
        unit_forecast_power_next_24h=unit_forecast_power_next_24h,
        unit_forecast_energy_actual_h=unit_forecast_energy_actual_h,
        unit_forecast_energy_next_1h=unit_forecast_energy_next_1h,
        unit_forecast_energy_today=unit_forecast_energy_today,
        unit_forecast_energy_tomorrow=unit_forecast_energy_tomorrow,
        unit_forecast_energy_remaining_today=unit_forecast_energy_remaining_today,
    )


def handle_forecast_provider_configuration(
    adapter_type: ForecastProviderAdapter,
) -> Optional[ForecastProviderConfig]:
    """Handle the configuration of a forecast provider based on the selected adapter type."""
    if adapter_type.value == ForecastProviderAdapter.DUMMY_SOLAR.value:
        return handle_forecast_provider_dummy_config()
    elif adapter_type.value == ForecastProviderAdapter.HOME_ASSISTANT_API.value:
        return handle_forecast_provider_home_assistant_api_config()
    else:
        click.echo(click.style("Unsupported forecast provider adapter type.", fg="red"))
        return None


def handle_add_forecast_provider(
    configuration_service: ConfigurationServiceInterface, logger: LoggerPort
) -> Optional[ForecastProvider]:
    """Menu to add a new forecast provider."""
    click.echo(click.style("\n--- Add Forecast Provider ---", fg="yellow"))

    name: str = click.prompt("Name of the forecast provider", type=str)
    adapter_type: Optional[ForecastProviderAdapter] = select_forecast_provider_adapter()

    if adapter_type is None:
        click.echo(
            click.style(
                "Invalid forecast provider adapter type selected. Aborting.",
                fg="red",
            )
        )
        return None

    config: Optional[ForecastProviderConfig] = handle_forecast_provider_configuration(adapter_type=adapter_type)

    if config is None:
        click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
        return None

    external_service_id: Optional[EntityId] = None
    if adapter_type != ForecastProviderAdapter.DUMMY_SOLAR:
        adapter_type_filter = FORECAST_PROVIDER_TYPE_EXTERNAL_SERVICE_MAP.get(adapter_type, None)
        external_service: Optional[ExternalService] = select_external_service(
            configuration_service=configuration_service,
            logger=logger,
            filter_type=adapter_type_filter,
        )
        external_service_id = external_service.id if external_service else None

    added: Optional[ForecastProvider] = None
    try:
        added = configuration_service.create_forecast_provider(
            name=name,
            adapter_type=adapter_type,
            config=config,
            external_service_id=external_service_id,
        )
        click.echo(
            click.style(
                f"Forecast Provider '{added.name}' successfully added (ID: {added.id}).",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error adding forecast provider: {e}")
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
    click.pause("Press any key to return to the menu...")
    return added


def handle_list_forecast_providers(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """List all forecast providers."""
    click.echo(click.style("\n--- List Forecast Providers ---", fg="yellow"))

    forecast_providers: List[ForecastProvider] = configuration_service.list_forecast_providers()
    if not forecast_providers:
        click.echo(click.style("No forecast providers found.", fg="yellow"))
    else:
        for provider in forecast_providers:
            click.echo(
                "-> "
                + "Name: "
                + click.style(f"{provider.name}, ", fg="blue")
                + "ID: "
                + click.style(f"{provider.id}, ", fg="yellow")
                + "Type: "
                + click.style(f"{provider.adapter_type.name}", fg="green")
            )

    click.echo("")
    click.pause("Press any key to return to the menu...")


def select_forecast_providers(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
    filter_type: Optional[List[ForecastProviderAdapter]] = None,
    filter_config: Optional[List[ForecastProviderConfig]] = None,
) -> Optional[ForecastProvider]:
    """Select a forecast provider from the list."""
    click.echo(click.style("\n--- Select Forecast Provider ---", fg="yellow"))

    forecast_providers: List[ForecastProvider] = configuration_service.list_forecast_providers()

    filter_type = process_filters(filter_type)

    if filter_type:
        click.echo(
            "Filtering forecast providers by types: "
            + click.style(f"{', '.join([t.name for t in filter_type])}", fg="blue")
        )
        forecast_providers = [fp for fp in forecast_providers if fp.adapter_type in filter_type]

    filter_config = process_filters(filter_config)
    if filter_config:
        click.echo(
            "Filtering forecast providers by config: "
            + click.style(f"{', '.join([type(c).__name__ for c in filter_config])}", fg="blue")
        )
        filtered_forecast_providers: List[ForecastProvider] = []
        for fp in forecast_providers:
            for filtered_config_class in filter_config:
                if isinstance(fp.config, type(filtered_config_class)):
                    filtered_forecast_providers.append(fp)
        forecast_providers = filtered_forecast_providers

    if not forecast_providers:
        click.echo(click.style("No forecast providers configured.", fg="yellow"))
        click.pause("Press any key to return to the menu...")
        return None

    default_idx = ""
    for idx, fp in enumerate(forecast_providers):
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{fp.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{fp.id}, ", fg="yellow")
            + "Type: "
            + click.style(f"{fp.adapter_type.name}", fg="green")
        )

        if default_id:
            if fp.id == default_id:
                default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    fp_idx: str = click.prompt("Choose a Forecast Provider index", type=str, default=default_idx)
    fp_idx = fp_idx.strip().lower()

    if fp_idx == "b":
        return None

    if not fp_idx.isdigit() or int(fp_idx) < 0 or int(fp_idx) >= len(forecast_providers):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_fp = forecast_providers[int(fp_idx)]
    return selected_fp


def print_forecast_provider_config(
    forecast_provider: ForecastProvider,
) -> None:
    """Print the configuration of a forecast provider."""
    configuration_class = forecast_provider.config.__class__.__name__ if forecast_provider.config else "---"
    click.echo("| Configuration: " + click.style(f"{configuration_class}", fg="cyan"))
    if forecast_provider.config:
        print_configuration(forecast_provider.config.to_dict())


def print_forecast_provider_details(
    forecast_provider: ForecastProvider,
    configuration_service: ConfigurationServiceInterface,
    show_energy_source_list: bool = False,
    show_external_service: bool = False,
) -> None:
    """Print the details of a forecast provider."""
    click.echo("")
    click.echo("| Name: " + click.style(forecast_provider.name, fg="blue"))
    click.echo("| ID: " + click.style(forecast_provider.id, fg="yellow"))
    click.echo("| Adapter: " + click.style(forecast_provider.adapter_type.name, fg="green"))
    click.echo("| External Service ID: " + click.style(forecast_provider.external_service_id or "---", fg="magenta"))
    print_forecast_provider_config(forecast_provider)
    click.echo("")

    if show_energy_source_list:
        energy_sources = configuration_service.list_energy_sources_by_forecast_provider(forecast_provider.id)
        if not energy_sources:
            click.echo(
                click.style(
                    "No energy sources assigned to this forecast provider.",
                    fg="yellow",
                )
            )
        else:
            click.echo("Energy sources assigned to this forecast provider:")
            for es in energy_sources:
                click.echo(
                    "-> "
                    + "Name: "
                    + click.style(f"{es.name}, ", fg="blue")
                    + "ID: "
                    + click.style(f"{es.id}, ", fg="yellow")
                    + "Type: "
                    + click.style(f"{es.type.name}", fg="green")
                )
        click.echo("")

    if show_external_service:
        if forecast_provider.external_service_id:
            external_service = configuration_service.get_external_service(forecast_provider.external_service_id)
            if external_service:
                click.echo("External Service:")
                click.echo("| Name: " + click.style(external_service.name, fg="blue"))
                click.echo("| ID: " + click.style(external_service.id, fg="yellow"))
                click.echo("| Adapter: " + click.style(external_service.adapter_type.name, fg="green"))
                click.echo(f"| Name: {external_service.name} (ID: {external_service.id})")
                click.echo("")


def update_single_forecast_provider(
    forecast_provider: ForecastProvider,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[ForecastProvider]:
    """Update a single forecast provider."""
    click.echo(click.style("\n--- Update Forecast Provider ---", fg="yellow"))
    name: str = click.prompt(
        "New name for the forecast provider",
        type=str,
        default=forecast_provider.name,
    )

    config: Optional[ForecastProviderConfig] = handle_forecast_provider_configuration(
        adapter_type=forecast_provider.adapter_type
    )

    if config is None:
        click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
        return None

    external_service_id: Optional[EntityId] = forecast_provider.external_service_id
    needed_external_service_type: Optional[ExternalServiceAdapter] = FORECAST_PROVIDER_TYPE_EXTERNAL_SERVICE_MAP.get(
        forecast_provider.adapter_type, None
    )

    # Ask to change the external service
    change_external_service: bool = False
    remove_external_service: bool = False
    if external_service_id:
        actual_external_service: Optional[ExternalService] = configuration_service.get_external_service(
            external_service_id
        )
        if actual_external_service:
            click.echo("\nCurrent external service: ")
            print_external_service_details(
                service=actual_external_service,
                configuration_service=configuration_service,
                show_linked_instances=False,
            )
        else:
            click.echo(
                click.style(
                    "\nCurrent external service not found. It might have been deleted.",
                    fg="yellow",
                )
            )

        # An external service is set but the forecast provider does not require it
        if not needed_external_service_type:
            click.echo(
                click.style(
                    "\nThis forecast provider does not require an external service. Do you want to remove it?",
                    fg="yellow",
                )
            )
            remove_external_service = click.confirm("Remove external service", default=False, prompt_suffix="")
            if remove_external_service:
                external_service_id = None
                click.echo(click.style("External service removed.", fg="green"))
        else:
            click.echo(
                click.style(
                    "\nDo you want to change the external service for this forecast provider?",
                    fg="yellow",
                )
            )
            change_external_service = click.confirm("Change external service", default=False, prompt_suffix="")

    if needed_external_service_type:
        if change_external_service:
            external_service: Optional[ExternalService] = select_external_service(
                configuration_service=configuration_service,
                logger=logger,
                filter_type=[needed_external_service_type],
            )

            if external_service is None:
                click.echo(
                    click.style(
                        "No external service selected. Keeping the current one.",
                        fg="yellow",
                    )
                )
            else:
                external_service_id = external_service.id
    else:
        click.echo(
            click.style(
                "No external service required for this forecast provider. Keeping the current one.",
                fg="yellow",
            )
        )

    try:
        updated: ForecastProvider = configuration_service.update_forecast_provider(
            provider_id=forecast_provider.id,
            name=name,
            adapter_type=forecast_provider.adapter_type,
            config=config,
            external_service_id=external_service_id,
        )
        logger.debug(f"Forecast Provider '{updated.name}' updated successfully.")
        click.echo(
            click.style(
                f"Forecast Provider '{updated.name}' successfully updated (ID: {updated.id}).",
                fg="green",
            )
        )
        return updated
    except Exception as e:
        logger.error(f"Error updating forecast provider: {e}")
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        return None


def delete_single_forecast_provider(
    forecast_provider: ForecastProvider,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> bool:
    """Delete a single forecast provider."""
    delete_confirm: bool = click.confirm(
        f"Are you sure you want to delete the forecast provider '{forecast_provider.name}' "
        f"(ID: {forecast_provider.id})?",
        abort=False,
        default=False,
        prompt_suffix="",
    )
    if not delete_confirm:
        click.echo(click.style("Deletion cancelled.", fg="yellow"))
        return False

    try:
        configuration_service.remove_forecast_provider(forecast_provider.id)
        logger.debug(f"Forecast Provider '{forecast_provider.name}' deleted successfully.")
        click.echo(
            click.style(
                f"Forecast Provider '{forecast_provider.name}' successfully deleted.",
                fg="green",
            )
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting forecast provider: {e}")
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        return False


def manage_single_forecast_provider_menu(
    forecast_provider: ForecastProvider,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> str:
    """Menu for managing a single forecast provider."""
    while True:
        click.echo("\n" + click.style("--- MANAGE FORECAST PROVIDER ---", fg="blue", bold=True))

        print_forecast_provider_details(
            forecast_provider=forecast_provider,
            configuration_service=configuration_service,
            show_energy_source_list=True,
            show_external_service=True,
        )

        click.echo("1. Update Forecast Provider")
        click.echo("2. Delete Forecast Provider")
        click.echo("")
        click.echo("b. Back to energy menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            updated_forecast_provider = update_single_forecast_provider(
                forecast_provider=forecast_provider,
                configuration_service=configuration_service,
                logger=logger,
            )
            forecast_provider = updated_forecast_provider or forecast_provider
            continue

        elif choice == "2":
            delete_status = delete_single_forecast_provider(
                forecast_provider=forecast_provider,
                configuration_service=configuration_service,
                logger=logger,
            )
            if delete_status:
                return "b"  # Return to the energy menu after deletion

        elif choice == "b":
            break

        elif choice == "q":
            break

        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice


def forecast_menu(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu for managing Forecast Providers."""
    while True:
        click.echo("\n" + click.style("--- FORECAST ---", fg="yellow", bold=True))
        click.echo("1. Add Forecast Provider")
        click.echo("2. List Forecast Providers")
        click.echo("3. Manage Forecast Provider")
        click.echo("")
        click.echo("b. Back to Main Menu")
        click.echo("q. Quit")
        click.echo("-----------------")

        choice: str = click.prompt("Select an action", type=str).strip().lower()

        if choice == "1":
            handle_add_forecast_provider(configuration_service, logger)
        elif choice == "2":
            handle_list_forecast_providers(configuration_service, logger)
        elif choice == "3":
            forecast_provider = select_forecast_providers(configuration_service, logger)
            if forecast_provider is None:
                click.echo(click.style("No forecast provider selected. Aborting.", fg="red"))
                continue

            sub_choice = manage_single_forecast_provider_menu(
                forecast_provider=forecast_provider,
                configuration_service=configuration_service,
                logger=logger,
            )
            if sub_choice == "q":
                choice = "q"  # Exit if user chose to quit from energy menu
                break

        elif choice == "b":
            break

        elif choice == "q":
            break

        else:
            click.echo(click.style("Invalid option. Please try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice
