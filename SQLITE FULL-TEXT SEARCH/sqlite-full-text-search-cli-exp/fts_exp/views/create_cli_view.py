import click
import peewee_utils

from ..data_models.db_models import ItemFTSIndexEng, ItemFTSIndexIta, ItemModel
from ..domains.item_domain import CreateItemSchema, ItemDomain, LangEnum
from .base_cli_view import BaseClickCommand, ConsoleAdapter, handle_common_exc

console = ConsoleAdapter()


@click.command(
    cls=BaseClickCommand,
    name="create",
    help="""Create an item.
    
    \b
    eg. sfts create --title "My title" --notes "My notes" --lang eng
    """,
)
@click.option(
    "--title",
    "title",
    type=str,
    required=True,
    help="Title for the item",
)
@click.option(
    "--notes",
    "notes",
    type=str,
    required=True,
    help="Notes for the item",
)
@click.option(
    "--lang",
    "lang",
    type=click.Choice(LangEnum, case_sensitive=False),
    required=True,
    help="Language",
)
def create_cli_view(title: str, notes: str, lang: LangEnum):
    create_cmd_view(title, notes, lang)


@handle_common_exc()
@peewee_utils.use_db()
def create_cmd_view(
    title: str, notes: str, lang: LangEnum
) -> tuple[ItemModel, ItemFTSIndexEng | ItemFTSIndexIta]:
    domain = ItemDomain()
    item = domain.create_item(CreateItemSchema(title=title, notes=notes))
    ix = domain.create_fts_index_for_item(item, lang)
    # TODO use output schema?
    console.print(f"Created item id={item.id} and its index")
    return item, ix
