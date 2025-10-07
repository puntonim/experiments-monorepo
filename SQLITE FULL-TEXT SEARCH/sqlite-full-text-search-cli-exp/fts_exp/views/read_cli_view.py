import click
import peewee
import peewee_utils

from ..domains.item_domain import ItemDomain
from .base_cli_view import BaseClickCommand, ConsoleAdapter, handle_common_exc

console = ConsoleAdapter()


@click.command(
    cls=BaseClickCommand,
    name="read",
    help="""Read items.

    \b
    eg. sfts read
    eg. sfts read --id 1
    """,
)
@click.option(
    "--id",
    "item_id",
    type=int,
    required=False,
    help="Item id",
)
def read_cli_view(item_id: int | None = None):
    read_cmd_view(item_id)


@handle_common_exc()
@peewee_utils.use_db()
def read_cmd_view(item_id: int | None = None) -> peewee.ModelSelect:
    domain = ItemDomain()
    items = domain.read_items(item_id)
    for item in items:
        # TODO use output schema?
        console.print(item)
    return items
