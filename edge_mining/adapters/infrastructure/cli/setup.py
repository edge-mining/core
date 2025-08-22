"""
Edge Mining CLI Setup.
"""

import click

from edge_mining.shared.infrastructure import Services
from edge_mining.shared.logging.port import LoggerPort


@click.group()
@click.pass_context
def cli(ctx: click.Context):
    """Edge Mining CLI"""

    if not isinstance(ctx.obj, dict) or not all(
        isinstance(ctx.obj.get(k), v) for k, v in {Services: Services, LoggerPort: LoggerPort}.items()
    ):
        print("WARNING: ctx.obj does not contain expected pre-initialized dependencies.")
        click.echo(click.style("Welcome to the Edge Mining CLI!", fg="red", bold=True))
