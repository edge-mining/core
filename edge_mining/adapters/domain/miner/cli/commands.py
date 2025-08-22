"""CLI commands for the Miner domain."""

from typing import List, Optional

import click

from edge_mining.adapters.infrastructure.cli.utils import print_configuration, process_filters
from edge_mining.adapters.infrastructure.external_services.cli.commands import (
    handle_add_external_service,
    select_external_service,
)
from edge_mining.application.interfaces import ConfigurationServiceInterface
from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.miner.common import MinerControllerAdapter, MinerStatus
from edge_mining.domain.miner.entities import Miner, MinerController
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.shared.adapter_configs.miner import MinerControllerDummyConfig
from edge_mining.shared.adapter_maps.miner import MINER_CONTROLLER_TYPE_EXTERNAL_SERVICE_MAP
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.interfaces.config import MinerControllerConfig
from edge_mining.shared.logging.port import LoggerPort


def handle_add_miner(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """Menu to add a new miner."""
    click.echo(click.style("\n--- Add Miner ---", fg="yellow"))
    name: str = click.prompt("Name of the miner", type=str)
    hash_rate_max: float = click.prompt("Max HashRate (eg. 100.0)", type=float, default=100.0)
    hash_rate_unit: str = click.prompt("HashRate unit (eg. TH/s, GH/s)", type=str, default="TH/s")
    power_consumption_max: float = click.prompt("Max power consumption (Watt, eg. 3200.0)", type=float, default=3200.0)

    new_miner = Miner()
    new_miner.name = name
    new_miner.hash_rate_max = HashRate(value=hash_rate_max, unit=hash_rate_unit)
    new_miner.power_consumption_max = Watts(power_consumption_max)
    new_miner.controller_id = None

    # Select a Miner Controller
    miner_controller: Optional[MinerController] = None

    miner_controllers = configuration_service.list_miner_controllers()
    if miner_controllers:
        miner_controller = select_miner_controller(configuration_service, logger)
        if miner_controller:
            new_miner.controller_id = miner_controller.id
    else:
        click.echo("")
        click.echo(click.style("No Miner Controller configured.", fg="yellow"))

        add_miner_controller: bool = click.confirm(
            "Do you want to add a Miner Controller now?",
            default=True,
            abort=False,
        )

        if add_miner_controller:
            miner_controller = handle_add_miner_controller(
                miner=new_miner,
                configuration_service=configuration_service,
                logger=logger,
            )
            if miner_controller:
                click.echo(
                    click.style(
                        f"Miner Controller '{miner_controller.name}', "
                        f"Type: {miner_controller.adapter_type.name} "
                        f"(ID: {miner_controller.id}) successfully added to current miner.",
                        fg="green",
                    )
                )
                new_miner.controller_id = miner_controller.id
        else:
            click.echo(
                click.style(
                    "No miner controller configured for this miner.",
                    fg="yellow",
                )
            )

    try:
        added = configuration_service.add_miner(
            name=new_miner.name,
            hash_rate_max=new_miner.hash_rate_max,
            power_consumption_max=new_miner.power_consumption_max,
            controller_id=new_miner.controller_id,
        )
        click.echo(
            click.style(
                f"Miner '{added.name}' (ID: {added.id}) successfully added.",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error adding miner: {e}")
        click.echo(click.style(f"Error adding miner: {e}", fg="red"), err=True)
    click.pause("Press any key to return to the menu...")


def list_miners(configuration_service: ConfigurationServiceInterface):
    """List all configured miners."""
    miners = configuration_service.list_miners()
    if not miners:
        click.echo(click.style("No miner configured.", fg="yellow"))
    else:
        for m in miners:
            hashrate_str = f"{m.hash_rate_max.value} {m.hash_rate_max.unit}" if m.hash_rate_max else "N/A"
            click.echo(
                "-> "
                + "Name: "
                + click.style(f"{m.name}, ", fg="blue")
                + "ID: "
                + click.style(f"{m.id}, ", fg="yellow")
                + "Status: "
                + click.style(
                    f"{m.status.name}, ",
                    fg=f"{'green' if m.status == MinerStatus.ON else 'red'}",
                )
                + "Max Power: "
                + click.style(f"{m.power_consumption_max}W, ", fg="cyan")
                + "Max HashRate: "
                + click.style(
                    f"{hashrate_str}, ",
                    fg="magenta",
                )
                + "Active: "
                + click.style(f"{m.active}", fg="green" if m.active else "red")
            )
    click.echo("")


def handle_list_miners(configuration_service: ConfigurationServiceInterface, logger: LoggerPort):
    """Handle List all configured miners."""
    click.echo(click.style("\n--- Configured Miner ---", fg="yellow"))

    list_miners(configuration_service)

    click.pause("Press any key to return to the menu...")


def select_miner(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
) -> Optional[Miner]:
    """Select a miner from the list."""
    click.echo(click.style("\n--- Select Miner ---", fg="yellow"))

    miners = configuration_service.list_miners()
    if not miners:
        click.echo(click.style("No miner configured.", fg="yellow"))
        return None

    default_idx = ""
    for idx, m in enumerate(miners):
        hashrate_str = f"{m.hash_rate_max.value} {m.hash_rate_max.unit}" if m.hash_rate_max else "N/A"
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{m.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{m.id}, ", fg="yellow")
            + "Max Power: "
            + click.style(f"{m.power_consumption_max}W, ", fg="cyan")
            + "Max HashRate: "
            + click.style(f"{hashrate_str}", fg="magenta")
            + "Active:"
            + click.style(f"{m.active}", fg="green" if m.active else "red")
        )

        if default_id:
            if m.id == default_id:
                default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    miner_idx: str = click.prompt("Choose a Miner index", type=str, default=default_idx)
    miner_idx = miner_idx.strip().lower()
    if miner_idx == "b":
        return None

    if not miner_idx.isdigit() or int(miner_idx) < 0 or int(miner_idx) >= len(miners):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_miner = miners[int(miner_idx)]
    return selected_miner


def update_single_miner(
    selected_miner: Miner,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[Miner]:
    """Menu to update a miner's details."""
    name: str = click.prompt("New name of the miner", type=str, default=selected_miner.name)
    hash_rate: float = click.prompt(
        "Max HashRate (eg. 100.0)",
        type=float,
        default=selected_miner.hash_rate_max.value if selected_miner.hash_rate_max else 100.0,
    )
    hash_rate_unit: str = click.prompt(
        "HashRate unit (eg. TH/s, GH/s)",
        type=str,
        default=selected_miner.hash_rate_max.unit if selected_miner.hash_rate_max else "",
    )
    power_consumption: float = click.prompt(
        "Max power consumption (Watt, eg. 3200.0)",
        type=float,
        default=selected_miner.power_consumption_max,
    )

    # Select a Miner Controller
    controller_id = selected_miner.controller_id
    miner_controllers = configuration_service.list_miner_controllers()
    if miner_controllers:
        miner_controller = select_miner_controller(configuration_service, logger)
        if miner_controller:
            controller_id = miner_controller.id
        else:
            click.echo(click.style("Miner Controller will not be changed!", fg="yellow"))

    hash_rate_max = HashRate(value=hash_rate, unit=hash_rate_unit)

    try:
        updated = configuration_service.update_miner(
            miner_id=selected_miner.id,
            name=name,
            hash_rate_max=hash_rate_max,
            power_consumption_max=Watts(power_consumption),
            controller_id=EntityId(controller_id) if controller_id else None,
        )
        click.echo(
            click.style(
                f"Miner '{updated.name}' (ID: {updated.id}) successfully updated.",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error updating miner: {e}")
        click.echo(click.style(f"Error updating miner: {e}", fg="red"), err=True)
        updated = None

    click.pause("Press any key to return to the menu...")

    return updated


def delete_single_miner(
    selected_miner: Miner,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> bool:
    """Delete a specific Miner."""
    delete_confirm = click.confirm(
        f"Are you sure you want to remove the Miner '{selected_miner.name}' (ID: {selected_miner.id})?",
        abort=False,
        default=False,
        prompt_suffix="",
    )
    if not delete_confirm:
        click.echo(click.style("Deletion cancelled.", fg="yellow"))
        return False
    try:
        removed_miner = configuration_service.remove_miner(miner_id=selected_miner.id)
        logger.info(f"Miner '{removed_miner.name}' (ID: {removed_miner.id}) successfully removed.")
        click.echo(
            click.style(
                f"Miner '{removed_miner.name}' (ID: {removed_miner.id}) successfully removed.",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error removing miner: {e}")
        click.echo(click.style(f"Error removing miner: {e}", fg="red"), err=True)
        return False
    else:
        return True


def assign_controller_to_miner(
    selected_miner: Miner,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[Miner]:
    """Assign a controller to a miner."""
    click.echo(click.style("\n--- Assign Controller to Miner ---", fg="yellow"))

    controller = select_miner_controller(configuration_service, logger)

    if controller is None:
        click.echo(click.style("No controller selected. Aborting.", fg="red"))
        return None

    try:
        selected_miner.controller_id = controller.id

        updated_miner = configuration_service.update_miner(
            miner_id=selected_miner.id,
            name=selected_miner.name,
            hash_rate_max=selected_miner.hash_rate_max,
            power_consumption_max=selected_miner.power_consumption_max,
            controller_id=selected_miner.controller_id,
            active=selected_miner.active,
        )
        click.echo(
            click.style(
                f"Controller Miner '{controller.name}' successfully assigned "
                f"to miner '{updated_miner.name}' (ID: {updated_miner.id}).",
                fg="green",
            )
        )
    except Exception as e:
        logger.error(f"Error assigning controller to miner: {e}")
        click.echo(
            click.style(f"Error assigning controller to miner: {e}", fg="red"),
            err=True,
        )
        return None

    return updated_miner


def handle_manage_miner(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu to manage a miner."""
    selected_miner = select_miner(configuration_service, logger)

    if selected_miner is None:
        click.echo(click.style("No miner selected. Aborting.", fg="red"))
        return "b"

    choice = manage_single_miner_menu(
        miner=selected_miner,
        configuration_service=configuration_service,
        logger=logger,
    )

    return choice


def print_miner_details(
    miner: Miner,
    configuration_service: ConfigurationServiceInterface,
) -> None:
    """Print details of a selected miner."""
    click.echo("")
    click.echo("| Name: " + click.style(miner.name, fg="blue"))
    click.echo("| ID: " + click.style(miner.id, fg="yellow"))
    click.echo(
        "| Status: "
        + click.style(
            miner.status.name,
            fg="green" if miner.status == MinerStatus.ON else "red",
        )
    )
    click.echo(
        "| Max HashRate: " + str(miner.hash_rate_max.value)
        if miner.hash_rate_max
        else "N/A" + " " + miner.hash_rate_max.unit
        if miner.hash_rate_max
        else "N/A"
    )
    click.echo("| Max Power Consumption: " + str(miner.power_consumption_max) + " W")
    click.echo("| Active: " + click.style(miner.active, fg="green" if miner.active else "red"))
    click.echo("| Controller ID: " + (str(miner.controller_id) if miner.controller_id else "None"))

    if miner.controller_id:
        controller = configuration_service.get_miner_controller(miner.controller_id)
        if controller:
            click.echo("\nCONTROLLER DETAILS:")
            print_miner_controller_details(controller, configuration_service, False)
        else:
            # If the controller is not found, we can still show the ID
            click.echo("| Controller ID: " + click.style(str(miner.controller_id), fg="red") + " (not found)")

    click.echo("")


def manage_single_miner_menu(
    miner: Miner,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> str:
    """Menu for managing a specific Miner."""
    while True:
        click.echo("\n" + click.style("--- MANAGE MINER ---", fg="blue", bold=True))

        print_miner_details(miner, configuration_service)

        click.echo("1. Activate Miner")
        click.echo("2. Deactivate Miner")
        click.echo("3. Update Miner")
        click.echo("4. Set Miner Controller")
        click.echo("5. Delete Miner")
        click.echo("")
        click.echo("b. Back to miner menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            try:
                miner = configuration_service.activate_miner(miner.id)
                logger.info(f"Miner {miner.name} activated successfully.")
            except Exception as e:
                logger.error(f"Error activating miner: {e}")
                click.echo(
                    click.style(f"Error activating miner: {e}", fg="red"),
                    err=True,
                )
            continue

        elif choice == "2":
            try:
                miner = configuration_service.deactivate_miner(miner.id)
                logger.info(f"Miner {miner.name} deactivated successfully.")
            except Exception as e:
                logger.error(f"Error deactivating miner: {e}")
                click.echo(
                    click.style(f"Error deactivating miner: {e}", fg="red"),
                    err=True,
                )
            continue

        elif choice == "3":
            updated_miner = update_single_miner(
                selected_miner=miner,
                configuration_service=configuration_service,
                logger=logger,
            )
            miner = updated_miner or miner  # Update miner if it was successfully updated
            continue

        elif choice == "4":
            updated_miner = assign_controller_to_miner(
                selected_miner=miner,
                configuration_service=configuration_service,
                logger=logger,
            )
            miner = updated_miner or miner  # Update miner if it was successfully updated
            continue

        elif choice == "5":
            delete_status = delete_single_miner(
                selected_miner=miner,
                configuration_service=configuration_service,
                logger=logger,
            )
            if delete_status:
                return "b"  # Return to menu if deletion was successful

        elif choice == "b":
            break

        elif choice == "q":
            break

    return choice


def select_miner_controller_type() -> Optional[MinerControllerAdapter]:
    """Select a miner controller type from the list."""
    click.echo("Select a Miner Controller Type:")
    for idx, controller_type in enumerate(MinerControllerAdapter):
        click.echo(f"{idx}. {controller_type.name}")

    click.echo("")
    choice: str = click.prompt("Choose a controller", type=str)
    choice = choice.strip().lower()

    if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(MinerControllerAdapter):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    controller_type_values = [controller_type.value for controller_type in MinerControllerAdapter]

    selected_type = MinerControllerAdapter(controller_type_values[int(choice)])
    return selected_type


def handle_miner_controller_dummy_config(
    miner: Optional[Miner],
) -> MinerControllerConfig:
    """Handle configuration for the Dummy Miner Controller."""
    click.echo(click.style("\n--- Dummy Miner Controller Configuration ---", fg="yellow"))

    default_power = miner.power_consumption_max if miner else 3200.0
    default_hash_rate = miner.hash_rate_max.value if miner and miner.hash_rate_max else 90.0
    default_hash_rate_unit = miner.hash_rate_max.unit if miner and miner.hash_rate_max else "TH/s"

    power_max: float = click.prompt(
        "Max power consumption (Watt, eg. 3200.0)",
        type=float,
        default=default_power,
    )
    hash_rate_max_value: float = click.prompt("Max HashRate value (eg. 90.0)", type=float, default=default_hash_rate)
    hash_rate_max_unit: str = click.prompt(
        "Max HashRate unit (eg. TH/s)",
        type=str,
        default=default_hash_rate_unit,
    )

    return MinerControllerDummyConfig(
        power_max=power_max,
        hashrate_max=HashRate(value=hash_rate_max_value, unit=hash_rate_max_unit),
    )


def handle_miner_controller_configuration(
    adapter_type: MinerControllerAdapter, miner: Optional[Miner]
) -> Optional[MinerControllerConfig]:
    """Handle configuration for the selected Miner Controller type."""
    config: Optional[MinerControllerConfig] = None
    if adapter_type.value == MinerControllerAdapter.DUMMY.value:
        config = handle_miner_controller_dummy_config(miner)
    else:
        click.echo(click.style("Unsupported controller type selected. Aborting.", fg="red"))
    return config


def handle_add_miner_controller(
    miner: Optional[Miner],
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[MinerController]:
    """Menu to add a new Miner Controller."""
    click.echo(click.style("\n--- Add Miner Controller ---", fg="yellow"))
    name: str = click.prompt("Name of the controller", type=str)
    adapter_type: Optional[MinerControllerAdapter] = select_miner_controller_type()

    if adapter_type is None:
        click.echo(click.style("Invalid controller type selected. Aborting.", fg="red"))
        return None

    new_controller = MinerController()
    new_controller.name = name
    new_controller.adapter_type = adapter_type
    new_controller.config = None
    new_controller.external_service_id = None

    config: Optional[MinerControllerConfig] = handle_miner_controller_configuration(
        adapter_type=new_controller.adapter_type, miner=miner
    )

    if config is None:
        click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
        return None

    new_controller.config = config

    needed_external_service = MINER_CONTROLLER_TYPE_EXTERNAL_SERVICE_MAP.get(adapter_type, None)
    # If an external service is required for the selected adapter type
    external_service: Optional[ExternalService] = None
    if needed_external_service:
        # If external service is needed, check if some one is already configured
        external_services: List[ExternalService] = configuration_service.list_external_services()
        if external_services:
            external_service = select_external_service(
                configuration_service=configuration_service,
                logger=logger,
                filter_type=[needed_external_service],
            )
            if external_service:
                new_controller.external_service_id = external_service.id if external_service else None
        else:
            click.echo("")
            click.echo(
                click.style(
                    "No external services configured. Please configure an external service first "
                    "and then add a miner controller.",
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
                            f"(ID: {external_service.id}) successfully added to current miner controller.",
                            fg="green",
                        )
                    )
                    new_controller.external_service_id = external_service.id
            else:
                click.echo(click.style("Aborting miner controller addition.", fg="red"))
                return None

    try:
        added_controller = configuration_service.add_miner_controller(
            name=new_controller.name,
            adapter=new_controller.adapter_type,
            config=new_controller.config,
            external_service_id=new_controller.external_service_id,
        )
        click.echo(
            click.style(
                f"Miner Controller '{added_controller.name}' (ID: {added_controller.id}) successfully added.",
                fg="green",
            )
        )
    except Exception as e:
        added_controller = None
        logger.error(f"Error adding miner controller: {e}")
        click.echo(
            click.style(f"Error adding miner controller: {e}", fg="red"),
            err=True,
        )
    click.pause("Press any key to return to the menu...")
    return added_controller


def handle_list_miner_controllers(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """List all configured Miner Controllers."""
    click.echo(click.style("\n--- Configured Miner Controllers ---", fg="yellow"))

    controllers = configuration_service.list_miner_controllers()
    if not controllers:
        click.echo(click.style("No miner controllers configured.", fg="yellow"))
    else:
        for c in controllers:
            click.echo(
                "-> "
                + "Name: "
                + click.style(f"{c.name}, ", fg="blue")
                + "ID: "
                + click.style(f"{c.id}, ", fg="yellow")
                + "Type: "
                + click.style(f"{c.adapter_type.name}", fg="green")
            )
    click.echo("")
    click.pause("Press any key to return to the menu...")


def print_miner_controller_details(
    controller: MinerController,
    configuration_service: ConfigurationServiceInterface,
    show_miner_list: bool = False,
) -> None:
    """Print details of a selected Miner Controller."""
    click.echo("")
    click.echo("| Name: " + click.style(controller.name, fg="blue"))
    click.echo("| ID: " + click.style(controller.id, fg="yellow"))
    click.echo("| Adapter Type: " + controller.adapter_type.name)
    click.echo(
        "| External Service ID:" + (str(controller.external_service_id) if controller.external_service_id else "None")
    )
    print_miner_controller_config(controller)
    click.echo("")

    if show_miner_list:
        miners = configuration_service.list_miners_by_controller(controller.id)
        if not miners:
            click.echo(click.style("No miners assigned to this controller.", fg="yellow"))
        else:
            click.echo("Miners assigned to this controller:")
            for m in miners:
                click.echo(
                    "-> "
                    + "Name: "
                    + click.style(f"{m.name}, ", fg="blue")
                    + "ID: "
                    + click.style(f"{m.id}, ", fg="yellow")
                    + "Type: "
                    + click.style(f"{m.power_consumption_max}", fg="green")
                )
            click.echo("")


def print_miner_controller_config(controller: MinerController) -> None:
    """Print the configuration of a selected Miner Controller."""
    configuration_class = controller.config.__class__.__name__ if controller.config else "---"
    click.echo("| Configuration: " + click.style(f"{configuration_class}", fg="cyan"))
    if controller.config:
        print_configuration(controller.config.to_dict())


def update_single_miner_controller(
    controller: MinerController,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[MinerController]:
    """Menu to update a miner controller"""
    name: str = click.prompt("New name of the controller", type=str, default=controller.name)
    config: Optional[MinerControllerConfig] = handle_miner_controller_configuration(
        adapter_type=controller.adapter_type,
        miner=None,  # No miner needed for controller update
    )

    if config is None:
        click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
        return None

    try:
        updated_controller = configuration_service.update_miner_controller(
            controller_id=controller.id, name=name, config=config
        )
        logger.info(f"Miner Controller '{updated_controller.name}' (ID: {updated_controller.id}) successfully updated.")
    except Exception as e:
        logger.error(f"Error updating miner controller: {e}")
        click.echo(
            click.style(f"Error updating miner controller: {e}", fg="red"),
            err=True,
        )
        updated_controller = None

    click.pause("Press any key to return to the menu...")

    return updated_controller


def delete_single_miner_controller(
    controller: MinerController,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> bool:
    """Delete a specific Miner Controller."""
    delete_confirm = click.confirm(
        f"Are you sure you want to remove the Miner Controller '{controller.name}' (ID: {controller.id})?",
        abort=False,
        default=False,
        prompt_suffix="",
    )

    if not delete_confirm:
        click.echo(click.style("Deletion cancelled.", fg="yellow"))
        return False

    try:
        removed_controller = configuration_service.remove_miner_controller(controller_id=controller.id)
        logger.info(f"Miner Controller '{removed_controller.name}' (ID: {removed_controller.id}) successfully removed.")
    except Exception as e:
        logger.error(f"Error removing miner controller: {e}")
        click.echo(
            click.style(f"Error removing miner controller: {e}", fg="red"),
            err=True,
        )
        return False
    else:
        return True


def manage_single_miner_controller_menu(
    controller: MinerController,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> str:
    """Menu for managing a specific Miner Controller."""
    while True:
        click.echo("\n" + click.style("--- MANAGE MINER CONTROLLER ---", fg="blue", bold=True))

        print_miner_controller_details(controller, configuration_service, show_miner_list=True)

        click.echo("1. Update Controller")
        click.echo("2. Delete Controller")
        click.echo("")
        click.echo("b. Back to miner menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str, default="")
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            updated_controller = update_single_miner_controller(
                controller=controller,
                configuration_service=configuration_service,
                logger=logger,
            )
            controller = updated_controller or controller  # Update controller if it was successfully updated
            continue

        elif choice == "2":
            delete_status = delete_single_miner_controller(
                controller=controller,
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


def select_miner_controller(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
    filter_type: Optional[List[MinerControllerAdapter]] = None,
) -> Optional[MinerController]:
    """Select a miner controller from the list."""
    click.echo(click.style("\n--- Select Miner Controller ---", fg="yellow"))

    controllers = configuration_service.list_miner_controllers()
    if not controllers:
        click.echo(click.style("No miner controllers configured.", fg="yellow"))
        return None

    filter_type = process_filters(filter_type)

    if filter_type:
        click.echo(
            "Filtering miner controller by types: "
            + click.style(f"{', '.join([c.name for c in filter_type])}", fg="blue")
        )
        controllers = [c for c in controllers if c.adapter_type in filter_type]

    default_idx = ""
    for idx, c in enumerate(controllers):
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{c.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{c.id}, ", fg="yellow")
            + "Type: "
            + click.style(f"{c.adapter_type.name}", fg="green")
        )

        if default_id:
            if c.id == default_id:
                default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    controller_idx: str = click.prompt("Choose a Controller index", type=str, default=default_idx)
    controller_idx = controller_idx.strip().lower()
    if controller_idx == "b":
        return None

    if not controller_idx.isdigit() or int(controller_idx) < 0 or int(controller_idx) >= len(controllers):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_controller = controllers[int(controller_idx)]
    return selected_controller


def handle_manage_miner_controller(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu to manage a miner controller."""
    controller = select_miner_controller(configuration_service, logger)

    if controller is None:
        click.echo(click.style("No controller selected. Aborting.", fg="red"))
        return "b"

    choice = manage_single_miner_controller_menu(
        controller=controller,
        configuration_service=configuration_service,
        logger=logger,
    )

    return choice


def miner_menu(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu for managing Miners."""
    while True:
        click.echo("\n" + click.style("--- MINER ---", fg="blue", bold=True))
        click.echo("1. Add a Miner")
        click.echo("2. List all Miners")
        click.echo("3. Manage a Miner")
        click.echo("")
        click.echo("4. Add a Miner Controller")
        click.echo("5. List Miner Controllers")
        click.echo("6. Manage a Miner Controller")
        click.echo("")
        click.echo("b. Back to main menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            handle_add_miner(configuration_service=configuration_service, logger=logger)

        elif choice == "2":
            handle_list_miners(configuration_service=configuration_service, logger=logger)

        elif choice == "3":
            sub_choice = handle_manage_miner(configuration_service=configuration_service, logger=logger)
            if sub_choice == "q":
                break

        elif choice == "4":
            handle_add_miner_controller(
                miner=None,
                configuration_service=configuration_service,
                logger=logger,
            )

        elif choice == "5":
            handle_list_miner_controllers(configuration_service=configuration_service, logger=logger)

        elif choice == "6":
            controller = select_miner_controller(configuration_service, logger)
            if controller is None:
                click.echo(click.style("No controller selected. Aborting.", fg="red"))
                continue

            sub_choice = manage_single_miner_controller_menu(
                controller=controller,
                configuration_service=configuration_service,
                logger=logger,
            )
            if sub_choice == "q":
                choice = "q"  # Exit if user chose to quit from controller menu
                break

        elif choice == "b":
            break

        elif choice == "q":
            break

        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice
