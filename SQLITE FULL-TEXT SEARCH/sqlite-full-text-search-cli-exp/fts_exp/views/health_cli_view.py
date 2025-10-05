from datetime import datetime

import click

from .base_cli_view import BaseClickCommand


@click.command(cls=BaseClickCommand, name="health", help="Just a testing command")
def health_cli_view() -> None:
    now = datetime.now().astimezone().isoformat()
    print(now)
