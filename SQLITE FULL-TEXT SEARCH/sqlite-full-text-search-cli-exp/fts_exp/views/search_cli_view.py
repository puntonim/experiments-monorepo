import click
import peewee
import peewee_utils

from ..conf import settings
from ..data_models.db_models import LangEnum
from ..domains.item_domain import ItemDomain
from .base_cli_view import BaseClickCommand, ConsoleAdapter, handle_common_exc

console = ConsoleAdapter()


@click.command(
    cls=BaseClickCommand,
    name="search",
    help="""Search items.

    \b
    eg. sfts search "la zampina" --lang ita
    """,
)
@click.argument("text", type=str)
@click.option(
    "--lang",
    "lang",
    type=click.Choice(LangEnum, case_sensitive=False),
    required=True,
    help="Language",
)
def search_cli_view(text: str, lang: LangEnum):
    search_cmd_view(text, lang)


@handle_common_exc()
@peewee_utils.use_db()
def search_cmd_view(text: str, lang: LangEnum) -> peewee.ModelSelect:
    domain = ItemDomain()
    items = domain.search_items(text, lang)
    for item in items:
        # TODO use output schema?
        title = item.title_s.replace(
            settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START,
            "[bold black on green_yellow]",
        ).replace(settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END, "[/]")
        notes = item.notes_s.replace(
            settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START,
            "[bold black on green_yellow]",
        ).replace(settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END, "[/]")
        console.print(f"{title}\n{notes}\n")
    return items
