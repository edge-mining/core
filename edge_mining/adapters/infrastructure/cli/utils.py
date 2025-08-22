"""Utility functions for CLI commands."""

import asyncio
from typing import Any, Dict, List, Optional, Union

import click

from edge_mining.application.interfaces import OptimizationServiceInterface


def run_evaluation(optimization_service: OptimizationServiceInterface):
    """Manually trigger one evaluation cycle."""
    if not optimization_service:
        click.echo("Error: Optimization Services not initialized.", err=True)
        return

    click.echo("Manually running evaluation cycle...")
    try:
        asyncio.run(optimization_service.run_all_enabled_units())
        click.echo("Evaluation cycle finished.")
    except Exception as e:
        click.echo(f"Error during evaluation: {e}", err=True)


def process_filters(
    filter_type: Optional[Union[Any, List[Any]]] = None,
) -> Optional[Union[List[Any]]]:
    """Process filter types for CLI commands."""
    if filter_type is None:
        return None

    # Convert single item to list
    if not isinstance(filter_type, list):
        filter_type_list = [filter_type]
    else:
        filter_type_list = filter_type

    return filter_type_list


def print_configuration(configuration: Dict):
    """Print configuration in a structured format."""
    for key, value in configuration.items():
        if isinstance(value, dict):
            click.echo(f"|-- {key}:")
            for sub_key, sub_value in value.items():
                click.echo(f"|   |-- {sub_key}: " + click.style(f"{sub_value}", fg="blue"))
        else:
            # For other types, just print the value directly
            if value is None:
                value = "None"
            elif isinstance(value, str):
                value = f'"{value}"'
            click.echo(f"|-- {key}: " + click.style(f"{value}", fg="blue"))
