import click
import peewee
import peewee_utils

from ..data_models.db_models import ItemFTSIndexEng, ItemFTSIndexIta, ItemModel
from ..domains.item_domain import CreateItemSchema, ItemDomain, LangEnum
from .base_cli_view import BaseClickCommand


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
def read_items_cli_view(item_id: int | None = None):
    """
    Search the matching Garmin activity for the given Strava activity id.
    """
    read_items(item_id)


@peewee_utils.use_db()
def read_items(item_id: int | None = None) -> peewee.ModelSelect:
    domain = ItemDomain()
    items = domain.read_items(item_id)
    for item in items:
        print(item)  # TODO console.log (or rich) plus output schema
    return items
