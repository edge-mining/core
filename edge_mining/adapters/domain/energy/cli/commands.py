"""CLI commands for the energy domain."""

from typing import List, Optional

import click

from edge_mining.adapters.domain.forecast.cli.commands import (
    handle_add_forecast_provider,
    print_forecast_provider_details,
    select_forecast_providers,
)
from edge_mining.adapters.infrastructure.external_services.cli.commands import (
    handle_add_external_service,
    print_external_service_details,
    select_external_service,
)
from edge_mining.application.interfaces import ConfigurationServiceInterface
from edge_mining.domain.common import EntityId, WattHours, Watts
from edge_mining.domain.energy.common import EnergyMonitorAdapter, EnergySourceType
from edge_mining.domain.energy.entities import EnergyMonitor, EnergySource
from edge_mining.domain.energy.exceptions import EnergyMonitorNotFoundError
from edge_mining.domain.energy.value_objects import Battery, Grid
from edge_mining.domain.forecast.exceptions import ForecastProviderNotFoundError
from edge_mining.shared.adapter_configs.energy import (
    EnergyMonitorDummySolarConfig,
    EnergyMonitorHomeAssistantConfig,
)
from edge_mining.shared.adapter_maps.energy import (
    ENERGY_MONITOR_TYPE_EXTERNAL_SERVICE_MAP,
    ENERGY_SOURCE_TYPE_ENERGY_MONITOR_MAP,
    ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_TYPE_MAP,
)
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.interfaces.config import EnergyMonitorConfig
from edge_mining.shared.logging.port import LoggerPort

from edge_mining.adapters.infrastructure.cli.utils import (
    process_filters,
    print_configuration,
)


def select_energy_source_type() -> Optional[EnergySourceType]:
    """Select an energy source type from the list."""
    energy_source_type_colors = {
        EnergySourceType.SOLAR: "yellow",
        EnergySourceType.WIND: "blue",
        EnergySourceType.GRID: "green",
        EnergySourceType.HYDROELECTRIC: "cyan",
        EnergySourceType.OTHER: "magenta",
    }
    click.echo("Select an Energy Source Type:")
    for idx, energy_source_type in enumerate(EnergySourceType):
        click.echo(
            f"{idx}. "
            + click.style(
                f"{energy_source_type.name}",
                fg=energy_source_type_colors.get(energy_source_type, "white"),
            )
        )

    click.echo("")
    choice: str = click.prompt("Choose an energy source", type=str)
    choice = choice.strip().lower()

    if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(EnergySourceType):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    energy_source_type_values = [energy_source_type.value for energy_source_type in EnergySourceType]

    selected_type = EnergySourceType(energy_source_type_values[int(choice)])
    return selected_type


def select_energy_monitors(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
    filter_type: Optional[List[EnergyMonitorAdapter]] = None,
    filter_config: Optional[List[EnergyMonitorConfig]] = None,
) -> Optional[EnergyMonitor]:
    """Select an energy monitor from the list."""
    click.echo(click.style("\n--- Select Energy Monitor ---", fg="yellow"))

    energy_monitors: List[EnergyMonitor] = configuration_service.list_energy_monitors()
    if not energy_monitors:
        click.echo(click.style("No energy monitors configured.", fg="yellow"))
        return None

    filter_type = process_filters(filter_type)

    if filter_type:
        click.echo(
            "Filtering energy monitor by types: "
            + click.style(f"{', '.join([c.name for c in filter_type])}", fg="blue")
        )
        energy_monitors = [em for em in energy_monitors if em.adapter_type in filter_type]

    filter_config = process_filters(filter_config)

    if filter_config:
        click.echo(
            "Filtering energy monitors by config: "
            + click.style(f"{', '.join([type(c).__name__ for c in filter_config])}", fg="blue")
        )
        filtered_energy_monitors: List[EnergyMonitor] = []
        for fp in energy_monitors:
            for filtered_config_class in filter_config:
                if isinstance(fp.config, type(filtered_config_class)):
                    filtered_energy_monitors.append(fp)
        energy_monitors = filtered_energy_monitors

    default_idx = ""
    for idx, em in enumerate(energy_monitors):
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{em.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{em.id}, ", fg="yellow")
            + "Type: "
            + click.style(f"{em.adapter_type.name}", fg="green")
        )

        if default_id:
            if em.id == default_id:
                default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    em_idx: str = click.prompt("Choose a Energy Monitor index", type=str, default=default_idx)
    em_idx = em_idx.strip().lower()
    if em_idx == "b":
        return None

    if not em_idx.isdigit() or int(em_idx) < 0 or int(em_idx) >= len(energy_monitors):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_em = energy_monitors[int(em_idx)]
    return selected_em


def handle_add_energy_source(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """Menu to add a new energy source."""
    click.echo(click.style("\n--- Add Energy Source ---", fg="yellow"))
    name: str = click.prompt("Name of the energy source", type=str)
    source_type: Optional[EnergySourceType] = select_energy_source_type()

    if source_type is None:
        click.echo(click.style("Invalid energy source type selected. Aborting.", fg="red"))
        return

    nominal_power_max: int = click.prompt("Max nominal power (Watt, eg. 5000)", type=int, default=5000)
    storage_nominal_capacity: int = click.prompt(
        "Battery nominal capacity (Watt. Insert 0 for No Battery)",
        type=int,
        default="0",
    )
    grid_contracted_power: int = click.prompt("Max power contracted on grid (Watt, eg. 3000)", type=int, default=3200)
    external_source_power: int = click.prompt(
        "Max power from the external source (Watt. Insert 0 for No external source)",
        type=int,
        default=0,
    )

    new_energy_source: EnergySource = EnergySource()
    new_energy_source.name = name
    new_energy_source.type = source_type
    new_energy_source.nominal_power_max = Watts(nominal_power_max)
    new_energy_source.storage = (
        Battery(nominal_capacity=WattHours(storage_nominal_capacity)) if storage_nominal_capacity > 0 else None
    )
    new_energy_source.grid = Grid(contracted_power=Watts(grid_contracted_power)) if grid_contracted_power > 0 else None
    new_energy_source.external_source = Watts(external_source_power) if external_source_power > 0 else None
    new_energy_source.energy_monitor_id = None
    new_energy_source.forecast_provider_id = None

    # Select an Energy Monitor
    energy_monitors = configuration_service.list_energy_monitors()
    if energy_monitors:
        energy_monitor = select_energy_monitors(
            configuration_service=configuration_service,
            logger=logger,
            filter_type=ENERGY_SOURCE_TYPE_ENERGY_MONITOR_MAP.get(source_type, None),
        )
        if energy_monitor:
            new_energy_source.energy_monitor_id = energy_monitor.id
    else:
        click.echo("")
        click.echo(
            click.style(
                "No energy monitors configured. Configure an energy monitor first and then add an energy source.",
                fg="yellow",
            )
        )

        add_energy_monitor: bool = click.confirm(
            "Do you want to add an energy monitor now?",
            default=True,
            abort=False,
        )

        if add_energy_monitor:
            energy_monitor = handle_add_energy_monitor(
                energy_source=new_energy_source,
                configuration_service=configuration_service,
                logger=logger,
            )
            if energy_monitor:
                click.echo(
                    click.style(
                        f"Energy Monitor '{energy_monitor.name}', "
                        f"Type: {energy_monitor.adapter_type.name} "
                        f"(ID: {energy_monitor.id}) successfully added to current energy source.",
                        fg="green",
                    )
                )
                new_energy_source.energy_monitor_id = energy_monitor.id
        else:
            click.echo(
                click.style(
                    "No energy monitor configured for this energy source.",
                    fg="yellow",
                )
            )
            click.echo(click.style("Aborting energy source update.", fg="red"))
            return None

    # Select an Energy Monitor
    forecast_providers = configuration_service.list_forecast_providers()
    if forecast_providers:
        forecast_provider = select_forecast_providers(
            configuration_service=configuration_service,
            logger=logger,
            filter_type=ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_TYPE_MAP.get(source_type, None),
        )
        if forecast_provider:
            new_energy_source.forecast_provider_id = forecast_provider.id
    else:
        click.echo("")
        click.echo(click.style("No forecast providers configured.", fg="yellow"))

        add_forecast_provider: bool = click.confirm(
            "Do you want to add a forecast provider now?",
            default=True,
            abort=False,
        )

        if add_forecast_provider:
            forecast_provider = handle_add_forecast_provider(configuration_service=configuration_service, logger=logger)
            if forecast_provider:
                click.echo(
                    click.style(
                        f"Forecast Provider '{forecast_provider.name}' "
                        f"Type: {forecast_provider.adapter_type.name} "
                        f"(ID: {forecast_provider.id}) successfully added "
                        "to current energy source.",
                        fg="green",
                    )
                )
                new_energy_source.forecast_provider_id = forecast_provider.id
        else:
            click.echo(
                click.style(
                    "No forecast provider configured for this energy source.",
                    fg="yellow",
                )
            )

    try:
        added: EnergySource = configuration_service.create_energy_source(
            name=new_energy_source.name,
            source_type=new_energy_source.type,
            nominal_power_max=new_energy_source.nominal_power_max,
            storage=new_energy_source.storage,
            grid=new_energy_source.grid,
            external_source=new_energy_source.external_source,
            energy_monitor_id=new_energy_source.energy_monitor_id,
            forecast_provider_id=new_energy_source.forecast_provider_id,
        )
        click.echo(
            click.style(
                f"Energy Source '{added.name}' (ID: {added.id}) successfully added.",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error adding energy source: {e}")
        click.echo(click.style(f"Error adding energy source: {e}", fg="red"), err=True)
    click.pause("Press any key to return to the menu...")


def handle_list_energy_sources(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """List all energy sources."""
    click.echo(click.style("\n--- List Energy Sources ---", fg="yellow"))

    energy_sources: List[EnergySource] = configuration_service.list_energy_sources()
    if not energy_sources:
        click.echo(click.style("No energy sources configured.", fg="yellow"))
    else:
        for es in energy_sources:
            click.echo(
                "-> "
                + "Name: "
                + click.style(f"{es.name}, ", fg="blue")
                + "ID: "
                + click.style(f"{es.id}, ", fg="yellow")
                + "Type: "
                + click.style(f"{es.type.name}, ", fg="green")
                + "Max power: "
                + click.style(f"{es.nominal_power_max}W", fg="blue")
            )
    click.echo("")
    click.pause("Press any key to return to the menu...")


def select_energy_source(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
    filter_type: Optional[List[EnergySourceType]] = None,
) -> Optional[EnergySource]:
    """Select an energy source from the list."""
    click.echo(click.style("\n--- Select Energy Source ---", fg="yellow"))

    energy_sources: List[EnergySource] = configuration_service.list_energy_sources()
    if not energy_sources:
        click.echo(click.style("No energy sources configured.", fg="yellow"))
        return None

    filter_type = process_filters(filter_type)

    if filter_type:
        click.echo(
            "Filtering energy source by types: " + click.style(f"{', '.join([t.name for t in filter_type])}", fg="blue")
        )
        energy_sources = [s for s in energy_sources if s.type in filter_type]

    default_idx = ""
    for idx, es in enumerate(energy_sources):
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{es.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{es.id}, ", fg="yellow")
            + "Type: "
            + click.style(f"{es.type.name}", fg="green")
        )

        if default_id:
            if es.id == default_id:
                default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    es_idx: str = click.prompt("Choose an Energy Source index", type=str, default=default_idx)
    es_idx = es_idx.strip().lower()
    if es_idx == "b":
        return None

    if not es_idx.isdigit() or int(es_idx) < 0 or int(es_idx) >= len(energy_sources):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_es = energy_sources[int(es_idx)]
    return selected_es


def print_energy_monitor_config(energy_monitor: EnergyMonitor) -> None:
    """Print the configuration of an energy monitor."""
    configuration_class = energy_monitor.config.__class__.__name__ if energy_monitor.config else "---"
    click.echo("| Configuration: " + click.style(f"{configuration_class}", fg="cyan"))
    if energy_monitor.config:
        print_configuration(energy_monitor.config.to_dict())


def print_energy_monitor_details(
    energy_monitor: EnergyMonitor,
    configuration_service: ConfigurationServiceInterface,
    show_external_service: bool = False,
    show_energy_source_list: bool = False,
) -> None:
    """Print the details of an energy monitor."""
    click.echo("")
    click.echo("| Name: " + click.style(energy_monitor.name, fg="blue"))
    click.echo("| ID: " + click.style(energy_monitor.id, fg="yellow"))
    click.echo("| Adapter: " + click.style(energy_monitor.adapter_type.name, fg="green"))
    print_energy_monitor_config(energy_monitor)
    click.echo("")

    if show_external_service:
        if energy_monitor.external_service_id:
            external_service = configuration_service.get_external_service(energy_monitor.external_service_id)
            if external_service:
                click.echo("EXTERNAL SERVICE DETAILS:")
                print_external_service_details(
                    service=external_service,
                    configuration_service=configuration_service,
                    show_config=False,
                    show_linked_instances=False,
                )
            else:
                click.echo(
                    "| External service: "
                    + click.style(str(energy_monitor.external_service_id), fg="red")
                    + " (not found)"
                )
        else:
            click.echo("| External service: None")
        click.echo("")

    if show_energy_source_list:
        energy_sources: List[EnergySource] = configuration_service.list_energy_sources_by_monitor(energy_monitor.id)
        if not energy_sources:
            click.echo(click.style("No energy sources assigned to this monitor.", fg="yellow"))
        else:
            click.echo("Energy sources assigned to this monitor:")
            for es in energy_sources:
                click.echo(
                    "-> "
                    + "Name: "
                    + click.style(f"{es.name}, ", fg="blue")
                    + "ID: "
                    + click.style(f"{es.id}, ", fg="yellow")
                    + "Type: "
                    + click.style(f"{es.type.name}, ", fg="green")
                    + "Max power: "
                    + click.style(f"{es.nominal_power_max}W", fg="blue")
                )
            click.echo("")


def print_energy_source_details(
    energy_source: EnergySource,
    configuration_service: ConfigurationServiceInterface,
    show_energy_monitor_list: bool = False,
    show_forecast_provider_list: bool = False,
    show_energy_source_list: bool = False,
) -> None:
    """Print the details of an energy source."""
    click.echo("")
    click.echo("| Name: " + click.style(energy_source.name, fg="blue"))
    click.echo("| ID: " + click.style(energy_source.id, fg="yellow"))
    click.echo("| Type: " + click.style(energy_source.type.name, fg="green"))
    click.echo("| Max power: " + str(energy_source.nominal_power_max) + " W")
    click.echo(
        "| Storage: " + ((str(energy_source.storage.nominal_capacity) + " Wh") if energy_source.storage else "None")
    )
    click.echo("| Grid: " + ((str(energy_source.grid.contracted_power) + " W") if energy_source.grid else "None"))
    click.echo(
        "| External source: "
        + ((str(energy_source.external_source) + " W") if energy_source.external_source else "None")
    )

    if show_energy_monitor_list:
        if energy_source.energy_monitor_id:
            try:
                energy_monitor = configuration_service.get_energy_monitor(energy_source.energy_monitor_id)
            except EnergyMonitorNotFoundError:
                energy_monitor = None

            if energy_monitor:
                click.echo("\nENERGY MONITOR DETAILS:")
                print_energy_monitor_details(
                    energy_monitor,
                    configuration_service,
                    show_external_service=True,
                    show_energy_source_list=show_energy_source_list,
                )
            else:
                click.echo(
                    "| Energy monitor: " + click.style(str(energy_source.energy_monitor_id), fg="red") + " (not found)"
                )
            click.echo("")

    if show_forecast_provider_list:
        if energy_source.forecast_provider_id:
            try:
                forecast_provider = configuration_service.get_forecast_provider(energy_source.forecast_provider_id)
            except ForecastProviderNotFoundError:
                forecast_provider = None

            if forecast_provider:
                click.echo("\nFORECAST PROVIDER DETAILS:")
                print_forecast_provider_details(
                    forecast_provider,
                    configuration_service,
                    show_energy_source_list=show_energy_source_list,
                )
            else:
                click.echo(
                    "| Forecast provider: "
                    + click.style(str(energy_source.forecast_provider_id), fg="red")
                    + " (not found)"
                )
    click.echo("")


def update_single_energy_source(
    energy_source: EnergySource,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[EnergySource]:
    """Update a single energy source."""
    click.echo(click.style("\n--- Update Energy Source ---", fg="yellow"))
    name: str = click.prompt("New name of the energy source", type=str, default=energy_source.name)
    nominal_power_max: int = click.prompt(
        "Max nominal power (Watt, eg. 5000)",
        type=int,
        default=energy_source.nominal_power_max,
    )
    storage_nominal_capacity: int = click.prompt(
        "Battery nominal capacity (Watt. Insert 0 for No Battery)",
        type=int,
        default=(energy_source.storage.nominal_capacity if energy_source.storage else 0),
    )
    grid_contracted_power: int = click.prompt(
        "Max power contracted on grid (Watt, eg. 3000)",
        type=int,
        default=(energy_source.grid.contracted_power if energy_source.grid else 3200),
    )
    external_source_power: int = click.prompt(
        "Max power from the external source (Watt. Insert 0 for No external source)",
        type=int,
        default=(energy_source.external_source if energy_source.external_source else 0),
    )

    new_energy_source: EnergySource = EnergySource()
    new_energy_source.id = energy_source.id
    new_energy_source.name = name
    new_energy_source.type = energy_source.type
    new_energy_source.nominal_power_max = Watts(nominal_power_max)
    new_energy_source.storage = (
        Battery(nominal_capacity=WattHours(storage_nominal_capacity)) if storage_nominal_capacity > 0 else None
    )
    new_energy_source.grid = Grid(contracted_power=Watts(grid_contracted_power)) if grid_contracted_power > 0 else None
    new_energy_source.external_source = Watts(external_source_power) if external_source_power > 0 else None
    new_energy_source.energy_monitor_id = energy_source.energy_monitor_id
    new_energy_source.forecast_provider_id = energy_source.forecast_provider_id

    # Select an Energy Monitor
    energy_monitors = configuration_service.list_energy_monitors()
    if energy_monitors:
        energy_monitor = select_energy_monitors(
            configuration_service=configuration_service,
            logger=logger,
        )
        if energy_monitor:
            new_energy_source.energy_monitor_id = energy_monitor.id
    else:
        click.echo("")
        click.echo(
            click.style(
                "No energy monitors configured. Configure an energy monitor first and then add an energy source.",
                fg="yellow",
            )
        )

        add_energy_monitor: bool = click.confirm(
            "Do you want to add an energy monitor now?",
            default=True,
            abort=False,
        )

        if add_energy_monitor:
            energy_monitor = handle_add_energy_monitor(
                energy_source=new_energy_source,
                configuration_service=configuration_service,
                logger=logger,
            )
            if energy_monitor:
                click.echo(
                    click.style(
                        f"Energy Monitor '{energy_monitor.name}', "
                        f"Type: {energy_monitor.adapter_type.name} "
                        f"(ID: {energy_monitor.id}) successfully added to "
                        "current energy source.",
                        fg="green",
                    )
                )
                new_energy_source.energy_monitor_id = energy_monitor.id
        else:
            click.echo(click.style("Aborting energy source update.", fg="red"))
            return None

    # Select a Forecast Provider
    forecast_providers = configuration_service.list_forecast_providers()
    if forecast_providers:
        forecast_provider = select_forecast_providers(
            configuration_service=configuration_service,
            logger=logger,
            default_id=new_energy_source.forecast_provider_id,
            filter_type=ENERGY_SOURCE_TYPE_FORECAST_PROVIDER_TYPE_MAP.get(energy_source.type, None),
        )
        if forecast_provider:
            new_energy_source.forecast_provider_id = forecast_provider.id

    try:
        updated: EnergySource = configuration_service.update_energy_source(
            source_id=new_energy_source.id,
            name=new_energy_source.name,
            source_type=new_energy_source.type,
            nominal_power_max=new_energy_source.nominal_power_max,
            storage=new_energy_source.storage,
            grid=new_energy_source.grid,
            external_source=new_energy_source.external_source,
            energy_monitor_id=new_energy_source.energy_monitor_id,
            forecast_provider_id=new_energy_source.forecast_provider_id,
        )
        click.echo(
            click.style(
                f"Energy Source '{updated.name}' (ID: {updated.id}) successfully updated.",
                fg="green",
            )
        )
        return updated
    except Exception as e:
        logger.error(f"Error updating energy source: {e}")
        click.echo(
            click.style(f"Error updating energy source: {e}", fg="red"),
            err=True,
        )
        return None


def assign_energy_monitor_to_energy_source(
    energy_source: EnergySource,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[EnergySource]:
    """Assign an energy monitor to an energy source."""
    click.echo(click.style("\n--- Assign Energy Monitor to Energy Source ---", fg="yellow"))

    energy_monitor = select_energy_monitors(configuration_service, logger)

    if energy_monitor is None:
        click.echo(click.style("No energy monitor selected. Aborting assignment.", fg="red"))
        click.pause("Press any key to return to the menu...")
        return None

    try:
        updated_energy_source = configuration_service.set_energy_monitor_to_energy_source(
            energy_source_id=energy_source.id,
            energy_monitor_id=energy_monitor.id,
        )
        click.echo(
            click.style(
                f"Energy Monitor '{energy_monitor.name}' assigned to Energy Source "
                f"'{updated_energy_source.name}' successfully.",
                fg="green",
            )
        )
        return updated_energy_source
    except Exception as e:
        logger.error(f"Error assigning energy monitor: {e}")
        click.echo(
            click.style(f"Error assigning energy monitor: {e}", fg="red"),
            err=True,
        )
        return None


def delete_single_energy_source(
    energy_source: EnergySource,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> bool:
    """Delete a single energy source."""
    delete_confirm: bool = click.confirm(
        f"Are you sure you want to delete the energy source '{energy_source.name}' (ID: {energy_source.id})?",
        abort=False,
        default=False,
        prompt_suffix="",
    )
    if not delete_confirm:
        click.echo(click.style("Deletion cancelled.", fg="yellow"))
        return False

    try:
        removed_energy_source = configuration_service.remove_energy_source(energy_source.id)
        logger.debug(f"Energy Source {removed_energy_source.name} deleted successfully.")
        click.echo(
            click.style(
                f"Energy Source '{removed_energy_source.name}' deleted successfully.",
                fg="green",
            )
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting energy source: {e}")
        click.echo(
            click.style(f"Error deleting energy source: {e}", fg="red"),
            err=True,
        )
        return False


def assign_forecast_provider_to_energy_source(
    energy_source: EnergySource,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[EnergySource]:
    """Assign a forecast provider to an energy source."""
    click.echo(click.style("\n--- Assign Forecast Provider to Energy Source ---", fg="yellow"))
    forecast_provider = select_forecast_providers(configuration_service, logger)
    if forecast_provider is None:
        click.echo(click.style("No forecast provider selected. Aborting assignment.", fg="red"))
        return None
    try:
        updated_energy_source = configuration_service.set_forecast_provider_to_energy_source(
            energy_source_id=energy_source.id,
            forecast_provider_id=forecast_provider.id,
        )
        click.echo(
            click.style(
                f"Forecast Provider '{forecast_provider.name}' assigned to "
                f"Energy Source '{updated_energy_source.name}' successfully.",
                fg="green",
            )
        )
        return updated_energy_source
    except Exception as e:
        logger.error(f"Error assigning forecast provider: {e}")
        click.echo(
            click.style(f"Error assigning forecast provider: {e}", fg="red"),
            err=True,
        )
        return None


def manage_single_energy_source_menu(
    energy_source: EnergySource,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> str:
    """Menu for managing a single energy source."""
    while True:
        click.echo("\n" + click.style("--- MANAGE ENERGY SOURCE ---", fg="blue", bold=True))

        print_energy_source_details(
            energy_source=energy_source,
            configuration_service=configuration_service,
            show_energy_monitor_list=True,
            show_forecast_provider_list=True,
            show_energy_source_list=False,
        )

        click.echo("1. Update Energy Source")
        click.echo("2. Delete Energy Source")
        click.echo("")
        click.echo("3. Set Energy Monitor")
        click.echo("4. Set Forecast Provider")
        click.echo("")
        click.echo("b. Back to energy menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            updated_energy_source = update_single_energy_source(
                energy_source=energy_source,
                configuration_service=configuration_service,
                logger=logger,
            )
            energy_source = updated_energy_source or energy_source
            continue

        elif choice == "2":
            delete_status = delete_single_energy_source(
                energy_source=energy_source,
                configuration_service=configuration_service,
                logger=logger,
            )
            if delete_status:
                return "b"  # Return to the energy menu after deletion

        elif choice == "3":
            updated_energy_source = assign_energy_monitor_to_energy_source(
                energy_source=energy_source,
                configuration_service=configuration_service,
                logger=logger,
            )
            energy_source = updated_energy_source or energy_source
            continue

        elif choice == "4":
            updated_energy_source = assign_forecast_provider_to_energy_source(
                energy_source=energy_source,
                configuration_service=configuration_service,
                logger=logger,
            )
            energy_source = updated_energy_source or energy_source
            continue

        elif choice == "b":
            break
        elif choice == "q":
            break
        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice


def select_energy_monitor_adapter() -> Optional[EnergyMonitorAdapter]:
    """Select an energy monitor adapter from the list."""
    click.echo("Select an Energy Monitor Adapter:")
    for idx, adapter in enumerate(EnergyMonitorAdapter):
        click.echo(f"{idx}. {adapter.name}")

    click.echo("")
    choice: str = click.prompt("Choose an energy monitor adapter", type=str)
    choice = choice.strip().lower()

    if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(EnergyMonitorAdapter):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    adapter_type_values = [adapter.value for adapter in EnergyMonitorAdapter]

    selected_adapter = EnergyMonitorAdapter(adapter_type_values[int(choice)])
    return selected_adapter


def handle_energy_monitor_dummy_solar_configuration(
    energy_monitor: Optional[EnergyMonitor] = None,
    energy_source: Optional[EnergySource] = None,
) -> Optional[EnergyMonitorConfig]:
    """Handle the configuration for the Dummy Solar energy monitor adapter."""
    click.echo(click.style("\n--- Dummy Solar Energy Monitor Configuration ---", fg="yellow"))

    default_max_consumption_power = Watts(3200)
    if energy_monitor:
        if isinstance(energy_monitor.config, EnergyMonitorDummySolarConfig):
            default_max_consumption_power = energy_monitor.config.max_consumption_power

    max_consumption_power: int = click.prompt(
        "Max consumption power (Watt, eg. 3200)",
        type=int,
        default=default_max_consumption_power,
    )

    return EnergyMonitorDummySolarConfig(max_consumption_power=Watts(max_consumption_power))


def handle_energy_monitor_home_assistant_configuration(
    energy_monitor: Optional[EnergyMonitor] = None,
    energy_source: Optional[EnergySource] = None,
) -> Optional[EnergyMonitorConfig]:
    """Handle the configuration for the Home Assistant energy monitor adapter."""
    click.echo(
        click.style(
            "\n--- Home Assistant Energy Monitor Configuration ---",
            fg="yellow",
        )
    )

    default_entity_production = ""
    default_entity_consumption = ""
    default_entity_grid = ""
    default_entity_battery_soc = ""
    default_entity_battery_power = ""
    default_entity_battery_remaining_capacity = ""
    default_unit_production = "W"
    default_unit_consumption = "W"
    default_unit_grid = "W"
    default_unit_battery_power = "W"
    default_unit_battery_remaining_capacity = "Wh"
    default_grid_positive_export = False
    default_battery_positive_charge = True
    if energy_monitor:
        if isinstance(energy_monitor.config, EnergyMonitorHomeAssistantConfig):
            default_entity_production = energy_monitor.config.entity_production
            default_entity_consumption = energy_monitor.config.entity_consumption
            default_entity_grid = energy_monitor.config.entity_grid
            default_entity_battery_soc = energy_monitor.config.entity_battery_soc
            default_entity_battery_power = energy_monitor.config.entity_battery_power
            default_entity_battery_remaining_capacity = energy_monitor.config.entity_battery_remaining_capacity
            default_unit_production = energy_monitor.config.unit_production
            default_unit_consumption = energy_monitor.config.unit_consumption
            default_unit_grid = energy_monitor.config.unit_grid
            default_unit_battery_power = energy_monitor.config.unit_battery_power
            default_unit_battery_remaining_capacity = energy_monitor.config.unit_battery_remaining_capacity
            default_grid_positive_export = energy_monitor.config.grid_positive_export
            default_battery_positive_charge = energy_monitor.config.battery_positive_charge

    entity_production: str = click.prompt(
        "Entity ID for production (e.g. sensor.solar_production)",
        type=str,
        default=default_entity_production,
    )
    entity_consumption: str = click.prompt(
        "Entity ID for consumption (e.g. sensor.home_consumption)",
        type=str,
        default=default_entity_consumption,
    )

    entity_grid: str = ""
    if energy_source and energy_source.grid:
        entity_grid = click.prompt(
            "Entity ID for grid (optional, e.g. sensor.grid_power)",
            type=str,
            default=default_entity_grid,
        )

    entity_battery_soc: str = ""
    entity_battery_power: str = ""
    entity_battery_remaining_capacity: str = ""
    if energy_source and energy_source.storage:
        entity_battery_soc = click.prompt(
            "Entity ID for battery state of charge (optional, e.g. sensor.battery_soc)",
            type=str,
            default=default_entity_battery_soc,
        )
        entity_battery_power = click.prompt(
            "Entity ID for battery power (optional, e.g. sensor.battery_power)",
            type=str,
            default=default_entity_battery_power,
        )
        entity_battery_remaining_capacity = click.prompt(
            "Entity ID for battery remaining capacity (optional, e.g. sensor.battery_remaining_capacity)",
            type=str,
            default=default_entity_battery_remaining_capacity,
        )

    unit_production: str = click.prompt(
        "Unit for production (default: W)",
        type=str,
        default=default_unit_production,
    )
    unit_consumption: str = click.prompt(
        "Unit for consumption (default: W)",
        type=str,
        default=default_unit_consumption,
    )

    unit_grid: str = default_unit_grid
    if energy_source and energy_source.grid:
        unit_grid = click.prompt("Unit for grid (default: W)", type=str, default=default_unit_grid)

    unit_battery_power: str = default_unit_battery_power
    unit_battery_remaining_capacity: str = "Wh"
    if energy_source and energy_source.storage:
        unit_battery_power = click.prompt(
            "Unit for battery power (default: W)",
            type=str,
            default=default_unit_battery_power,
        )
        unit_battery_remaining_capacity = click.prompt(
            "Unit for battery remaining capacity (default: Wh)",
            type=str,
            default=default_unit_battery_remaining_capacity,
        )

    # Set to True if your grid sensor reports positive for EXPORTING energy
    grid_positive_export: bool = click.confirm(
        "Direction of grid export (Set to true if positive grid power means EXPORTING)",
        default=default_grid_positive_export,
    )
    # Set to True if your battery sensor reports positive for CHARGING
    battery_positive_charge: bool = click.confirm(
        "Direction of battery charge (Set to true if positive battery power means CHARGING)",
        default=default_battery_positive_charge,
    )

    return EnergyMonitorHomeAssistantConfig(
        entity_production=entity_production,
        entity_consumption=entity_consumption,
        entity_grid=entity_grid,
        entity_battery_soc=entity_battery_soc,
        entity_battery_power=entity_battery_power,
        entity_battery_remaining_capacity=entity_battery_remaining_capacity,
        unit_production=unit_production,
        unit_consumption=unit_consumption,
        unit_grid=unit_grid,
        unit_battery_power=unit_battery_power,
        unit_battery_remaining_capacity=unit_battery_remaining_capacity,
        grid_positive_export=grid_positive_export,
        battery_positive_charge=battery_positive_charge,
    )


def handle_energy_monitor_configuration(
    adapter_type: EnergyMonitorAdapter,
    energy_monitor: Optional[EnergyMonitor] = None,
    energy_source: Optional[EnergySource] = None,
) -> Optional[EnergyMonitorConfig]:
    """
    Handle the configuration of an energy monitor based on the selected adapter type.
    """
    if adapter_type == EnergyMonitorAdapter.DUMMY_SOLAR:
        return handle_energy_monitor_dummy_solar_configuration(
            energy_monitor=energy_monitor, energy_source=energy_source
        )
    elif adapter_type == EnergyMonitorAdapter.HOME_ASSISTANT_API:
        return handle_energy_monitor_home_assistant_configuration(
            energy_monitor=energy_monitor, energy_source=energy_source
        )
    else:
        click.echo(
            click.style(
                "Unsupported energy monitor adapter type selected. Aborting.",
                fg="red",
            )
        )
        return None


def handle_add_energy_monitor(
    energy_source: Optional[EnergySource],
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[EnergyMonitor]:
    """Menu to add a new energy monitor."""
    click.echo(click.style("\n--- Add Energy Monitor ---", fg="yellow"))
    name: str = click.prompt("Name of the energy monitor", type=str)
    adapter_type: Optional[EnergyMonitorAdapter] = select_energy_monitor_adapter()

    if adapter_type is None:
        click.echo(
            click.style(
                "Invalid energy monitor adapter type selected. Aborting.",
                fg="red",
            )
        )
        return None

    new_energy_monitor = EnergyMonitor()
    new_energy_monitor.name = name
    new_energy_monitor.adapter_type = adapter_type
    new_energy_monitor.config = None
    new_energy_monitor.external_service_id = None

    config: Optional[EnergyMonitorConfig] = handle_energy_monitor_configuration(
        adapter_type=new_energy_monitor.adapter_type,
        energy_source=energy_source,
        energy_monitor=None,  # No existing monitor to update, so pass None
    )

    if config is None:
        click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
        return None

    new_energy_monitor.config = config

    needed_external_service = ENERGY_MONITOR_TYPE_EXTERNAL_SERVICE_MAP.get(new_energy_monitor.adapter_type, None)
    # If an external service is required for the selected adapter type
    if needed_external_service:
        external_service: Optional[ExternalService]
        # If external service is needed, check if some one is already configured
        external_services: List[ExternalService] = configuration_service.list_external_services()
        if external_services:
            external_service = select_external_service(
                configuration_service=configuration_service,
                logger=logger,
                filter_type=[needed_external_service],
            )
            if external_service:
                new_energy_monitor.external_service_id = external_service.id if external_service else None
        else:
            click.echo("")
            click.echo(
                click.style(
                    "No external services configured. "
                    "Please configure an external service first "
                    "and then add an energy monitor.",
                    fg="yellow",
                )
            )
            add_external_service: bool = click.confirm(
                "Do you want to add an external service now?",
                default=True,
                abort=False,
            )
            if add_external_service:
                external_service = handle_add_external_service(
                    configuration_service=configuration_service,
                    logger=logger,
                )
                if external_service:
                    click.echo(
                        click.style(
                            f"External Service '{external_service.name}', "
                            f"Type: {external_service.adapter_type.name} "
                            f"(ID: {external_service.id}) successfully added "
                            "to current energy monitor.",
                            fg="green",
                        )
                    )
                    new_energy_monitor.external_service_id = external_service.id
            else:
                click.echo(click.style("Aborting energy monitor addition.", fg="red"))
                return None

    added: Optional[EnergyMonitor] = None
    try:
        added = configuration_service.create_energy_monitor(
            name=new_energy_monitor.name,
            adapter_type=new_energy_monitor.adapter_type,
            config=new_energy_monitor.config,
            external_service_id=new_energy_monitor.external_service_id,
        )
        click.echo(
            click.style(
                f"Energy Monitor '{added.name}' (ID: {added.id}) successfully added.",
                fg="green",
            )
        )
    except Exception as e:
        added = None
        logger.error(f"Error adding energy monitor: {e}")
        click.echo(
            click.style(f"Error adding energy monitor: {e}", fg="red"),
            err=True,
        )
    click.pause("Press any key to return to the menu...")
    return added


def handle_list_energy_monitors(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """List all energy monitors."""
    click.echo(click.style("\n--- List Energy Monitors ---", fg="yellow"))

    energy_monitors = configuration_service.list_energy_monitors()
    if not energy_monitors:
        click.echo(click.style("No energy monitors configured.", fg="yellow"))
    else:
        for em in energy_monitors:
            click.echo(
                "-> "
                + "Name: "
                + click.style(f"{em.name}, ", fg="blue")
                + "ID: "
                + click.style(f"{em.id}, ", fg="yellow")
                + "Type: "
                + click.style(f"{em.adapter_type.name}", fg="green")
            )
    click.echo("")
    click.pause("Press any key to return to the menu...")


def select_energy_monitor(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
) -> Optional[EnergyMonitor]:
    """Select an energy monitor from the list."""
    click.echo(click.style("\n--- Select Energy Monitor ---", fg="yellow"))

    energy_monitors: List[EnergyMonitor] = configuration_service.list_energy_monitors()
    if not energy_monitors:
        click.echo(click.style("No energy monitors configured.", fg="yellow"))
        return None

    default_idx: str = ""
    for idx, em in enumerate(energy_monitors):
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{em.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{em.id}, ", fg="yellow")
            + "Type: "
            + click.style(f"{em.adapter_type.name}", fg="green")
        )

        if default_id and em.id == default_id:
            default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    em_idx: str = click.prompt("Choose a Energy Monitor index", type=str, default=default_idx)
    em_idx = em_idx.strip().lower()
    if em_idx == "b":
        return None

    if not em_idx.isdigit() or int(em_idx) < 0 or int(em_idx) >= len(energy_monitors):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_em = energy_monitors[int(em_idx)]
    return selected_em


def update_single_energy_monitor(
    monitor: EnergyMonitor,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[EnergyMonitor]:
    """Update a single energy monitor."""
    click.echo(click.style("\n--- Update Energy Monitor ---", fg="yellow"))
    name: str = click.prompt("New name of the energy monitor", type=str, default=monitor.name)

    new_energy_monitor: EnergyMonitor = EnergyMonitor()
    new_energy_monitor.id = monitor.id
    new_energy_monitor.name = name
    new_energy_monitor.adapter_type = monitor.adapter_type
    new_energy_monitor.config = monitor.config
    new_energy_monitor.external_service_id = monitor.external_service_id

    click.echo("\nDo you want to change the energy monitor configuration?")
    change_config: bool = click.confirm("Change configuration", default=True, prompt_suffix="")
    if change_config:
        config: Optional[EnergyMonitorConfig] = handle_energy_monitor_configuration(
            adapter_type=new_energy_monitor.adapter_type,
            energy_monitor=new_energy_monitor,
        )

        if config is None:
            click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
            return None

        new_energy_monitor.config = config

    if new_energy_monitor.config is None:
        click.echo(click.style("Energy monitor configuration is required. Aborting.", fg="red"))
        return None

    needed_external_service = ENERGY_MONITOR_TYPE_EXTERNAL_SERVICE_MAP.get(new_energy_monitor.adapter_type, None)

    if new_energy_monitor.external_service_id:
        click.echo("\nCurrent external service: ")
        current_external_service = configuration_service.get_external_service(new_energy_monitor.external_service_id)
        if current_external_service:
            print_external_service_details(
                service=current_external_service,
                configuration_service=configuration_service,
                show_linked_instances=False,
            )
        else:
            click.echo(
                click.style(
                    "Current external service is not valid. Please select a new one.",
                    fg="red",
                )
            )

    if needed_external_service:
        external_service: Optional[ExternalService] = None

        # If external service is needed, check if some one is already configured
        external_services: List[ExternalService] = configuration_service.list_external_services()
        if external_services:
            if new_energy_monitor.external_service_id:
                # Ask to change the external service
                click.echo(
                    click.style(
                        "\nDo you want to change the external service for this energy monitor?",
                        fg="yellow",
                    )
                )
                change_external_service: bool = click.confirm("Change external service", default=True, prompt_suffix="")
                if change_external_service:
                    external_service = select_external_service(
                        configuration_service=configuration_service,
                        logger=logger,
                        filter_type=[needed_external_service],
                    )

                    if external_service is None:
                        click.echo(
                            click.style(
                                "No external service selected. Keeping the current one.",
                                fg="yellow",
                            )
                        )
                    else:
                        new_energy_monitor.external_service_id = external_service.id
                else:
                    # Check if external service exists
                    current_external_service = configuration_service.get_external_service(
                        new_energy_monitor.external_service_id
                    )

                    # If current external service not exists, ask to select a new one
                    if not current_external_service:
                        click.echo(
                            click.style(
                                "Current external service is not valid. Please select a new one.",
                                fg="red",
                            )
                        )
                        external_service = select_external_service(
                            configuration_service=configuration_service,
                            logger=logger,
                            filter_type=[needed_external_service],
                        )
                        if external_service is None:
                            click.echo(
                                click.style(
                                    "No external service selected. Aborting update.",
                                    fg="red",
                                )
                            )
                            return None
                        new_energy_monitor.external_service_id = external_service.id

                    if current_external_service and current_external_service.config:
                        # Check if the current external service is still valid
                        external_service_valid = current_external_service.config.is_valid(
                            current_external_service.adapter_type
                        )
                        if not external_service_valid:
                            click.echo(
                                click.style(
                                    "Current external service configuration is not valid. Please select a new one.",
                                    fg="red",
                                )
                            )
                            external_service = select_external_service(
                                configuration_service=configuration_service,
                                logger=logger,
                                filter_type=[needed_external_service],
                            )
                            if external_service is None:
                                click.echo(
                                    click.style(
                                        "No external service selected. Aborting update.",
                                        fg="red",
                                    )
                                )
                                return None
                            new_energy_monitor.external_service_id = external_service.id
            else:
                # If no external service is configured, ask to select one
                click.echo(
                    click.style(
                        "\nDo you want to select an external service for this energy monitor?",
                        fg="yellow",
                    )
                )
                add_external_service = click.confirm("Add external service", default=True, prompt_suffix="")
                if add_external_service:
                    external_service = select_external_service(
                        configuration_service=configuration_service,
                        logger=logger,
                        filter_type=[needed_external_service],
                    )
                    if external_service is None:
                        click.echo(
                            click.style(
                                "No external service selected. Aborting update.",
                                fg="red",
                            )
                        )
                        return None
                    new_energy_monitor.external_service_id = external_service.id
        else:
            # Missing external service, ask to add one
            click.echo("")
            click.echo(
                click.style(
                    "No external services configured. "
                    "Please configure an external service first "
                    "and then update the energy monitor.",
                    fg="yellow",
                )
            )
            add_external_service = click.confirm(
                "Do you want to add an external service now?",
                default=True,
                abort=False,
            )
            if add_external_service:
                external_service = handle_add_external_service(
                    configuration_service=configuration_service,
                    logger=logger,
                )
                if external_service:
                    click.echo(
                        click.style(
                            f"External Service '{external_service.name}', "
                            f"Type: {external_service.adapter_type.name} "
                            f"(ID: {external_service.id}) successfully added "
                            "to current energy monitor.",
                            fg="green",
                        )
                    )
                    new_energy_monitor.external_service_id = external_service.id
            else:
                click.echo(click.style("Aborting energy monitor addition.", fg="red"))
                return None

    try:
        updated_monitor: EnergyMonitor = configuration_service.update_energy_monitor(
            monitor_id=new_energy_monitor.id,
            name=new_energy_monitor.name,
            adapter_type=new_energy_monitor.adapter_type,
            config=new_energy_monitor.config,
            external_service_id=new_energy_monitor.external_service_id,
        )
        logger.debug(f"Energy Monitor {updated_monitor.name} updated successfully.")
        click.echo(
            click.style(
                f"Energy Monitor '{updated_monitor.name}' (ID: {updated_monitor.id}) successfully updated.",
                fg="green",
            )
        )
        return updated_monitor
    except Exception as e:
        logger.error(f"Error updating energy monitor: {e}")
        click.echo(
            click.style(f"Error updating energy monitor: {e}", fg="red"),
            err=True,
        )
        return None


def delete_single_energy_monitor(
    monitor: EnergyMonitor,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> bool:
    """Delete a single energy monitor."""
    delete_confirm = click.confirm(
        f"Are you sure you want to delete the energy monitor '{monitor.name}' (ID: {monitor.id})?",
        abort=False,
        default=False,
        prompt_suffix="",
    )

    if not delete_confirm:
        click.echo(click.style("Deletion cancelled.", fg="yellow"))
        return False

    try:
        removed_energy_monitor = configuration_service.remove_energy_monitor(monitor.id)
        logger.debug(f"Energy Monitor {removed_energy_monitor.name} deleted successfully.")
        click.echo(
            click.style(
                f"Energy Monitor '{monitor.name}' deleted successfully.",
                fg="green",
            )
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting energy monitor: {e}")
        click.echo(
            click.style(f"Error deleting energy monitor: {e}", fg="red"),
            err=True,
        )
        return False


def manage_single_energy_monitor_menu(
    monitor: EnergyMonitor,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> str:
    """Menu for managing a single energy monitor."""
    while True:
        click.echo("\n" + click.style("--- MANAGE ENERGY MONITOR ---", fg="blue", bold=True))

        print_energy_monitor_details(
            energy_monitor=monitor,
            configuration_service=configuration_service,
            show_external_service=True,
            show_energy_source_list=True,
        )

        click.echo("1. Update Energy Monitor")
        click.echo("2. Delete Energy Monitor")
        click.echo("")
        click.echo("b. Back to energy menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            updated_energy_monitor = update_single_energy_monitor(
                monitor=monitor,
                configuration_service=configuration_service,
                logger=logger,
            )
            monitor = updated_energy_monitor or monitor
            continue

        elif choice == "2":
            delete_status = delete_single_energy_monitor(
                monitor=monitor,
                configuration_service=configuration_service,
                logger=logger,
            )
            if delete_status:
                return "b"
            continue

        elif choice == "b":
            break

        elif choice == "q":
            break

        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice


def energy_menu(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu for managing Energy Sources."""
    while True:
        click.echo("\n" + click.style("--- ENERGY ---", fg="blue", bold=True))
        click.echo("1. Add an Energy Source")
        click.echo("2. List all Energy Sources")
        click.echo("3. Manage an Energy Source")
        click.echo("")
        click.echo("4. Add an Energy Monitor")
        click.echo("5. List all Energy Monitors")
        click.echo("6. Manage an Energy Monitor")
        click.echo("")
        click.echo("b. Back to main menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            handle_add_energy_source(configuration_service=configuration_service, logger=logger)

        elif choice == "2":
            handle_list_energy_sources(configuration_service=configuration_service, logger=logger)

        elif choice == "3":
            energy_source = select_energy_source(configuration_service, logger)
            if energy_source is None:
                click.echo(click.style("No energy source selected. Aborting.", fg="red"))
                continue

            sub_choice = manage_single_energy_source_menu(
                energy_source=energy_source,
                configuration_service=configuration_service,
                logger=logger,
            )
            if sub_choice == "q":
                break

        elif choice == "4":
            handle_add_energy_monitor(
                energy_source=None,
                configuration_service=configuration_service,
                logger=logger,
            )

        elif choice == "5":
            handle_list_energy_monitors(configuration_service=configuration_service, logger=logger)

        elif choice == "6":
            monitor = select_energy_monitor(configuration_service, logger)
            if monitor is None:
                click.echo(click.style("No monitor selected. Aborting.", fg="red"))
                continue

            sub_choice = manage_single_energy_monitor_menu(
                monitor=monitor,
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
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice
