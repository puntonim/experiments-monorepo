"""
Entrypoint for the CLI.
To be run (after a `poetry install`) from the root dir with:
$ sfts --help
"""

import click

from .views.create_item_cli_view import create_item_cli_view
from .views.health_cli_view import health_cli_view
from .views.read_items_cli_view import read_items_cli_view


@click.group(
    # The single line with \b disables the wrapping:
    #  https://click.palletsprojects.com/en/latest/documentation/#escaping-click-s-wrapping
    help="""SQLite full-text search CLI experiment.
    
    \b
    Docs: https://github.com/puntonim/experiments-monorepo/blob/main/SQLITE%20FULL-TEXT%20SEARCH/sqlite-full-text-search-cli-exp/README.md
    """
)
def cli() -> None:
    pass


# Register all sub-commands.
cli.add_command(health_cli_view)
cli.add_command(create_item_cli_view)
cli.add_command(read_items_cli_view)
