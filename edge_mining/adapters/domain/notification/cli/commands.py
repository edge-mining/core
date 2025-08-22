"""CLI commands for the notification domain."""

from typing import List, Optional

import click

from edge_mining.adapters.infrastructure.external_services.cli.commands import (
    handle_add_external_service,
    print_external_service_details,
    select_external_service,
)
from edge_mining.application.interfaces import ConfigurationServiceInterface
from edge_mining.domain.common import EntityId
from edge_mining.domain.notification.common import NotificationAdapter
from edge_mining.domain.notification.entities import Notifier
from edge_mining.shared.adapter_configs.notification import (
    DummyNotificationConfig,
    TelegramNotificationConfig,
)
from edge_mining.shared.adapter_maps.notification import (
    NOTIFIER_TYPE_EXTERNAL_SERVICE_MAP,
)
from edge_mining.shared.external_services.entities import ExternalService
from edge_mining.shared.interfaces.config import NotificationConfig
from edge_mining.shared.logging.port import LoggerPort

from edge_mining.adapters.infrastructure.cli.utils import (
    process_filters,
    print_configuration,
)


def select_notifier_adapter() -> Optional[NotificationAdapter]:
    """Select a notifier adapter type from the list."""
    click.echo("Select Notifier Adapter:")
    for idx, adapter in enumerate(NotificationAdapter):
        click.echo(f"{idx}. {adapter.name}")

    click.echo("")
    choice: str = click.prompt("Choose a Notifier", type=str)
    choice = choice.strip().lower()

    if not choice.isdigit() or int(choice) < 0 or int(choice) >= len(NotificationAdapter):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    notifier_type_values = [n.value for n in NotificationAdapter]

    selected_type = NotificationAdapter(notifier_type_values[int(choice)])
    return selected_type


def handle_notifier_dummy_config() -> NotificationConfig:
    """Handle configuration for the Dummy notifier."""
    return DummyNotificationConfig()


def handle_notifier_telegram_config() -> NotificationConfig:
    """Handle configuration for the Telegram notifier."""
    bot_token: str = click.prompt("Telegram Bot Token", type=str)
    chat_id: str = click.prompt("Telegram Chat ID", type=str)

    return TelegramNotificationConfig(bot_token=bot_token, chat_id=chat_id)


def handle_notifier_configuration(
    adapter_type: NotificationAdapter,
) -> Optional[NotificationConfig]:
    """Handle configuration for a notifier."""
    config: Optional[NotificationConfig] = None
    if adapter_type == NotificationAdapter.DUMMY:
        config = handle_notifier_dummy_config()
    if adapter_type == NotificationAdapter.TELEGRAM:
        config = handle_notifier_telegram_config()
    if config is None:
        click.echo(click.style("Unsupported notifier type selected. Aborting.", fg="red"))
    return config


def handle_add_notifier(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> Optional[Notifier]:
    """Menu to add a new notifier."""
    click.echo(click.style("\n--- Add Notifier ---", fg="yellow"))
    name: str = click.prompt("Name of the notifier", type=str)
    adapter_type: Optional[NotificationAdapter] = select_notifier_adapter()

    if adapter_type is None:
        click.echo(click.style("Invalid notifier type selected. Aborting.", fg="red"))
        return None

    new_notifier: Notifier = Notifier()
    new_notifier.name = name
    new_notifier.adapter_type = adapter_type
    new_notifier.config = None
    new_notifier.external_service_id = None

    config: Optional[NotificationConfig] = handle_notifier_configuration(adapter_type=new_notifier.adapter_type)
    if config is None:
        click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
        return None

    new_notifier.config = config

    needed_external_service = NOTIFIER_TYPE_EXTERNAL_SERVICE_MAP.get(new_notifier.adapter_type, None)
    # If an external service is required for the selected adapter type
    if needed_external_service:
        # If external service is needed, check if some one is already configured
        external_services: List[ExternalService] = configuration_service.list_external_services()
        external_service: Optional[ExternalService] = None
        if external_services:
            external_service = select_external_service(
                configuration_service=configuration_service,
                logger=logger,
                filter_type=[needed_external_service],
            )
            if external_service:
                new_notifier.external_service_id = external_service.id
        else:
            click.echo("")
            click.echo(
                click.style(
                    "No external services configured. "
                    "Please configure an external service first "
                    "and then add a notifier.",
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
                            f"(ID: {external_service.id}) successfully added to current notifier.",
                            fg="green",
                        )
                    )
                    new_notifier.external_service_id = external_service.id
            else:
                click.echo(click.style("Aborting notifier addition.", fg="red"))
                return None

    added: Optional[Notifier] = None
    try:
        added = configuration_service.add_notifier(
            name=new_notifier.name,
            adapter_type=new_notifier.adapter_type,
            config=new_notifier.config,
            external_service_id=new_notifier.external_service_id,
        )
        click.echo(
            click.style(
                f"Notifier '{added.name}' (ID: {added.id}) successfully added.",
                fg="green",
            )
        )
    except Exception as e:
        added = None
        logger.error(f"Error adding notifier: {e}")
        click.echo(click.style(f"Error adding notifier: {e}", fg="red"), err=True)
    click.pause("Press any key to return to the menu...")
    return added


def handle_list_notifiers(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> None:
    """List all notifiers."""
    click.echo(click.style("\n--- Configured Notifiers ---", fg="yellow"))

    notifiers: List[Notifier] = configuration_service.list_notifiers()
    if not notifiers:
        click.echo(click.style("No notifiers configured.", fg="yellow"))
    else:
        for n in notifiers:
            click.echo(
                "-> "
                + "Name: "
                + click.style(f"{n.name}, ", fg="blue")
                + "ID: "
                + click.style(f"{n.id}, ", fg="yellow")
                + "Type: "
                + click.style(f"{n.adapter_type.name}", fg="green")
            )
    click.echo("")
    click.pause("Press any key to return to the menu...")


def select_notifier(
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
    default_id: Optional[EntityId] = None,
    filter_type: Optional[List[NotificationAdapter]] = None,
) -> Optional[Notifier]:
    """Select a notifier from the list."""
    click.echo(click.style("\n--- Select Notifier ---", fg="yellow"))

    notifiers: List[Notifier] = configuration_service.list_notifiers()
    if not notifiers:
        click.echo(click.style("No notifiers configured.", fg="yellow"))
        return None

    filter_type = process_filters(filter_type)

    if filter_type:
        click.echo(
            "Filtering notifier by types: " + click.style(f"{', '.join([n.name for n in filter_type])}", fg="blue")
        )
        notifiers = [n for n in notifiers if n.adapter_type in filter_type]

    default_idx = ""
    for idx, n in enumerate(notifiers):
        click.echo(
            f"{idx}. "
            + "Name: "
            + click.style(f"{n.name}, ", fg="blue")
            + "ID: "
            + click.style(f"{n.id}, ", fg="yellow")
            + "Type: "
            + click.style(f"{n.adapter_type.name}", fg="green")
        )

        if default_id and n.id == default_id:
            default_idx = str(idx)

    click.echo("\nb. Back to menu\n")

    n_idx: str = click.prompt("Choose a Notifier index", type=str, default=default_idx)
    n_idx = n_idx.strip().lower()
    if n_idx == "b":
        return None

    if not n_idx.isdigit() or int(n_idx) < 0 or int(n_idx) >= len(notifiers):
        click.echo(click.style("Invalid index. Aborting selection.", fg="red"))
        return None

    selected_n = notifiers[int(n_idx)]
    return selected_n


def print_notifier_config(notifier: Notifier) -> None:
    """Print the configuration of a notifier."""
    configuration_class = notifier.config.__class__.__name__ if notifier.config else "---"
    click.echo("| Configuration: " + click.style(f"{configuration_class}", fg="cyan"))
    if notifier.config:
        print_configuration(notifier.config.to_dict())


def print_notifier_details(
    notifier: Notifier,
    configuration_service: ConfigurationServiceInterface,
    show_external_service: bool = False,
    show_optimization_unit_list: bool = False,
) -> None:
    """Print the details of a notifier."""
    click.echo("")
    click.echo("| Name: " + click.style(notifier.name, fg="blue"))
    click.echo("| ID: " + click.style(notifier.id, fg="yellow"))
    click.echo("| Adapter: " + click.style(notifier.adapter_type.name, fg="green"))
    print_notifier_config(notifier)
    click.echo("")

    if show_external_service:
        if notifier.external_service_id:
            external_service = configuration_service.get_external_service(notifier.external_service_id)
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
                    "| External service: " + click.style(str(notifier.external_service_id), fg="red") + " (not found)"
                )
        else:
            click.echo("| External service: None")
        click.echo("")

    if show_optimization_unit_list:
        optimization_units = configuration_service.filter_optimization_units(filter_by_notifiers=[notifier.id])
        if not optimization_units:
            click.echo(click.style("No optimization units use this notifier.", fg="yellow"))
        else:
            click.echo("Optimization Units using this notifier:")
            for ou in optimization_units:
                click.echo(
                    "-> "
                    + "Name: "
                    + click.style(f"{ou.name}, ", fg="blue")
                    + "Enabled: "
                    + click.style(
                        f"{ou.is_enabled}",
                        fg="green" if ou.is_enabled else "red",
                    )
                )
        click.echo("")


def update_single_notifier(
    notifier: Notifier,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> Optional[Notifier]:
    """Update a single notifier."""
    click.echo(click.style("\n--- Update Notifier ---", fg="yellow"))
    name: str = click.prompt("New name of the notifier", type=str, default=notifier.name)

    new_notifier: Notifier = Notifier()
    new_notifier.name = name
    new_notifier.adapter_type = notifier.adapter_type
    new_notifier.config = notifier.config
    new_notifier.external_service_id = notifier.external_service_id

    click.echo("\nDo you want to change the notifier configuration?")
    change_config: bool = click.confirm("Change configuration", default=True, prompt_suffix="")
    if change_config:
        config: Optional[NotificationConfig] = handle_notifier_configuration(adapter_type=new_notifier.adapter_type)
        if config is None:
            click.echo(click.style("Invalid configuration. Aborting.", fg="red"))
            return None
        # Update the notifier configuration
        new_notifier.config = config

    if new_notifier.config is None:
        click.echo(click.style("Notifier configuration is required. Aborting.", fg="red"))
        return None

    needed_external_service = NOTIFIER_TYPE_EXTERNAL_SERVICE_MAP.get(new_notifier.adapter_type, None)

    if new_notifier.external_service_id:
        click.echo("\nCurrent external service: ")
        current_external_service = configuration_service.get_external_service(new_notifier.external_service_id)
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
            if new_notifier.external_service_id:
                # Ask to change the external service
                click.echo(
                    click.style(
                        "\nDo you want to change the external service for this notifier?",
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
                        new_notifier.external_service_id = external_service.id
                else:
                    # Check if external service exists
                    current_external_service = configuration_service.get_external_service(
                        new_notifier.external_service_id
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
                        new_notifier.external_service_id = external_service.id

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
                            new_notifier.external_service_id = external_service.id
            else:
                # If no external service is configured, ask to select one
                click.echo(
                    click.style(
                        "\nDo you want to select an external service for this notifier?",
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
                    new_notifier.external_service_id = external_service.id
        else:
            # Missing external service, ask to add one
            click.echo("")
            click.echo(
                click.style(
                    "No external services configured. Please configure an external service first "
                    "and then update the notifier.",
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
                            f"(ID: {external_service.id}) successfully added to current notifier.",
                            fg="green",
                        )
                    )
                    new_notifier.external_service_id = external_service.id
            else:
                click.echo(click.style("Aborting energy monitor addition.", fg="red"))
                return None

    try:
        updated_notifier = configuration_service.update_notifier(
            notifier_id=new_notifier.id,
            name=new_notifier.name,
            adapter_type=new_notifier.adapter_type,
            config=new_notifier.config,
            external_service_id=new_notifier.external_service_id,
        )
        click.echo(
            click.style(
                f"Notifier '{updated_notifier.name}' (ID: {updated_notifier.id}) successfully updated.",
                fg="green",
            )
        )
    except Exception as e:
        updated_notifier = None
        logger.error(f"Error updating notifier: {e}")
        click.echo(click.style(f"Error updating notifier: {e}", fg="red"), err=True)
        return None
    finally:
        click.pause("Press any key to return to the menu...")

    return updated_notifier


def delete_single_notifier(
    notifier: Notifier,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> bool:
    """Delete a single notifier."""
    delete_confirm: bool = click.confirm(
        f"Are you sure you want to delete the notifier '{notifier.name}' (ID: {notifier.id})?",
        abort=False,
        default=False,
        prompt_suffix="",
    )
    if not delete_confirm:
        click.echo(click.style("Deletion cancelled.", fg="yellow"))
        return False

    try:
        removed = configuration_service.remove_notifier(notifier_id=notifier.id)
        logger.info(f"Notifier '{removed.name}' (ID: {removed.id}) successfully removed.")
        click.echo(
            click.style(
                f"Notifier '{removed.name}' (ID: {removed.id}) successfully removed.",
                fg="green",
            )
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting notifier: {e}")
        click.echo(click.style(f"Error deleting notifier: {e}", fg="red"), err=True)
        return False


def manage_single_notifier_menu(
    notifier: Notifier,
    configuration_service: ConfigurationServiceInterface,
    logger: LoggerPort,
) -> str:
    """Menu for managing a single notifier."""
    while True:
        click.echo("\n" + click.style("--- MANAGE NOTIFIER ---", fg="blue", bold=True))
        print_notifier_details(
            notifier=notifier,
            configuration_service=configuration_service,
            show_external_service=True,
            show_optimization_unit_list=True,
        )
        click.echo("1. Update Notifier")
        click.echo("2. Delete Notifier")
        click.echo("")
        click.echo("b. Back to notifier menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            updated_notifier = update_single_notifier(
                notifier=notifier,
                configuration_service=configuration_service,
                logger=logger,
            )
            notifier = updated_notifier or notifier
            continue
        elif choice == "2":
            delete_status = delete_single_notifier(
                notifier=notifier,
                configuration_service=configuration_service,
                logger=logger,
            )
            if delete_status:
                return "b"
        elif choice == "b":
            break
        elif choice == "q":
            break
        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice


def handle_manage_notifier(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu to manage a notifier."""
    selected_notifier = select_notifier(configuration_service, logger)
    if selected_notifier is None:
        click.echo(click.style("No notifier selected. Aborting.", fg="red"))
        return "b"

    choice = manage_single_notifier_menu(
        notifier=selected_notifier,
        configuration_service=configuration_service,
        logger=logger,
    )
    return choice


def notifier_menu(configuration_service: ConfigurationServiceInterface, logger: LoggerPort) -> str:
    """Menu for managing Notifiers."""
    while True:
        click.echo("\n" + click.style("--- NOTIFIER MENU ---", fg="blue", bold=True))
        click.echo("1. Add Notifier")
        click.echo("2. List Notifiers")
        click.echo("3. Manage Notifier")
        click.echo("")
        click.echo("b. Back to main menu")
        click.echo("q. Close application")
        click.echo("-----------------")

        choice: str = click.prompt("Choose an option", type=str)
        choice = choice.strip().lower()

        click.clear()

        if choice == "1":
            handle_add_notifier(configuration_service, logger)
        elif choice == "2":
            handle_list_notifiers(configuration_service, logger)
        elif choice == "3":
            sub_choice = handle_manage_notifier(
                configuration_service=configuration_service,
                logger=logger,
            )
            if sub_choice == "q":
                choice = "q"
                break
        elif choice == "b":
            break
        elif choice == "q":
            break
        else:
            click.echo(click.style("Invalid choice. Try again.", fg="red"))
            click.pause("Press any key to return to the menu...")

    return choice
