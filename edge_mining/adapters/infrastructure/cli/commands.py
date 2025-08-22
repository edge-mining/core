"""CLI Commands for the Edge Mining Application"""

from typing import cast
from uuid import UUID

import click

from edge_mining.adapters.domain.miner.cli.commands import list_miners
from edge_mining.adapters.domain.optimization_unit.cli.commands import list_optimization_units
from edge_mining.adapters.infrastructure.cli.setup import cli
from edge_mining.adapters.infrastructure.cli.utils import run_evaluation
from edge_mining.application.interfaces import OptimizationServiceInterface
from edge_mining.domain.common import EntityId, Watts
from edge_mining.domain.miner.value_objects import HashRate
from edge_mining.shared.infrastructure import Services


@cli.command("run-evaluation")
@click.pass_context
def manage_run_evaluation(ctx: click.Context):
    """Run a manual evaluation cycle for the Edge Mining system."""
    services: Services = ctx.obj[Services]

    optimization_service: OptimizationServiceInterface = services.optimization_service
    if not optimization_service:
        click.echo("Error: Optimization Service not initialized.", err=True)
        return
    run_evaluation(optimization_service=optimization_service)


@click.group()
def optimization_unit():
    """Optimization Unit Management"""
    pass


@optimization_unit.command("create")
@click.argument("name")
@click.option("--description", help="Description for the Optimization Unit")
@click.option("--energy_source_id", help="ID of the energy source to use")
@click.option("--target_miner_ids", help="Comma-separated list of target miner IDs")
@click.option("--policy_id", help="ID of the policy to use")
@click.option("--home_forecast_provider_id", help="ID of the home load forecast provider")
@click.option("--performance_tracker_id", help="ID of the performance tracker")
@click.option("--notifier_ids", help="Comma-separated list of notifier IDs")
@click.pass_context
def create_optimization_unit(
    ctx: click.Context,
    name: str,
    description: str,
    energy_source_id_str: str,
    target_miner_ids_str: str,
    policy_id_str: str,
    home_forecast_provider_id_str: str,
    performance_tracker_id_str: str,
    notifier_ids_str: str,
):
    """Create a new optimization unit."""
    services: Services = ctx.obj[Services]

    configuration_service = services.configuration_service
    if not configuration_service:
        click.echo("Error: Configuration Services not initialized.", err=True)
        return

    try:
        target_miner_ids = (
            [EntityId(cast(UUID, miner_id.strip())) for miner_id in target_miner_ids_str.split(",")]
            if target_miner_ids_str
            else []
        )
        notifier_ids = (
            [EntityId(cast(UUID, notifier_id.strip())) for notifier_id in notifier_ids_str.split(",")]
            if notifier_ids_str
            else []
        )
        energy_source_id = EntityId(cast(UUID, energy_source_id_str)) if energy_source_id_str else None
        policy_id = EntityId(cast(UUID, policy_id_str)) if policy_id_str else None
        home_forecast_provider_id = (
            EntityId(cast(UUID, home_forecast_provider_id_str)) if home_forecast_provider_id_str else None
        )
        performance_tracker_id = (
            EntityId(cast(UUID, performance_tracker_id_str)) if performance_tracker_id_str else None
        )

        created = configuration_service.create_optimization_unit(
            name=name,
            description=description,
            energy_source_id=energy_source_id,
            target_miner_ids=target_miner_ids,
            policy_id=policy_id,
            home_forecast_provider_id=home_forecast_provider_id,
            performance_tracker_id=performance_tracker_id,
            notifier_ids=notifier_ids,
        )
        if not created:
            click.echo("Error: Optimization Unit creation failed.", err=True)
            return
        click.echo(f"Optimization Unit '{created.name}' created successfully.")
    except Exception as e:
        click.echo(f"Error creating optimization unit: {e}", err=True)


@optimization_unit.command("list")
@click.pass_context
def handle_list_optimization_units(ctx: click.Context):
    """List all configured optimization units."""
    services: Services = ctx.obj[Services]

    configuration_service = services.configuration_service
    if not configuration_service:
        click.echo("Error: Configuration Services not initialized.", err=True)
        return

    list_optimization_units(configuration_service)


@cli.group()
def miner():
    """Manage Miners"""
    pass


@miner.command("add")
@click.argument("name")
@click.option("--hash_rate", help="Max HashRate of the miner", type=float, default=100.0)
@click.option("--hash_rate_units", help="HashRate units (e.g. TH/s, GH/s)", default="TH/s")
@click.option("--power_consumption", help="Max power consumption", type=float, default=3200.0)
@click.option("--controller_id", help="Reference ID of miner controller", type=int, default=None)
@click.pass_context
def add_miner(
    ctx: click.Context,
    name: str,
    hash_rate_str: str,
    hash_rate_unit_str: str,
    power_consumption_str: str,
    controller_id_str: str,
):
    """Add a new miner to the system."""
    services: Services = ctx.obj[Services]

    configuration_service = services.configuration_service
    if not configuration_service:
        click.echo("Error: Configuration Services not initialized.", err=True)
        return
    try:
        controller_id = EntityId(cast(UUID, controller_id_str)) if controller_id_str else None
        hash_rate = HashRate(value=float(hash_rate_str), unit=hash_rate_unit_str)
        power_consumption = Watts(float(power_consumption_str))

        added = configuration_service.add_miner(
            name=name,
            hash_rate_max=hash_rate,
            power_consumption_max=power_consumption,
            controller_id=controller_id,
        )
        click.echo(f"Miner '{added.name}' ({added.id}) added successfully.")
    except Exception as e:
        click.echo(f"Error adding miner: {e}", err=True)


@miner.command("list")
@click.pass_context
def handle_list_miners(ctx: click.Context):
    """List all configured miners."""
    services: Services = ctx.obj[Services]

    configuration_service = services.configuration_service
    if not configuration_service:
        click.echo("Error: Configuration Services not initialized.", err=True)
        return

    list_miners(configuration_service)


@miner.command("remove")
@click.argument("miner_id")
@click.pass_context
def remove_miner(ctx: click.Context, miner_id_str: str):
    """Remove a miner from the system."""
    services: Services = ctx.obj[Services]

    configuration_service = services.configuration_service
    if not configuration_service:
        click.echo("Error: Configuration Services not initialized.", err=True)
        return

    miner_id = EntityId(cast(UUID, miner_id_str))

    try:
        configuration_service.remove_miner(miner_id=miner_id)
        click.echo(f"Miner {miner_id} removed.")
    except Exception as e:
        click.echo(f"Error removing miner: {e}", err=True)


@cli.group()
def policy():
    """Manage Optimization Policies"""
    pass


@policy.command("create")
@click.argument("name")
@click.option("--description", help="Description for the Policy")
@click.pass_context
def create_policy(ctx: click.Context, name: str, description: str):
    """Create a new optimization policy."""
    services: Services = ctx.obj[Services]

    configuration_service = services.configuration_service
    if not configuration_service:
        click.echo("Error: Configuration Services not initialized.", err=True)
        return

    try:
        created = configuration_service.create_policy(name=name, description=description)
        click.echo(f"Optimization Policy '{created.name}' ({created.description}) created successfully.")
    except Exception as e:
        click.echo(f"Error adding miner: {e}", err=True)


# # TODO: Add commands for policy management (create, list, activate, add-rule)
