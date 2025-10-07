from pathlib import Path

import click
import peewee_utils
from rich.prompt import Confirm

from ...conf import settings
from ...conf.settings import ROOT_DIR
from ...data_models.db_fixtures.sample_data_db_fixture import ITEM_MODEL_FIXTURES
from ...data_models.db_models import ItemModel
from ..base_cli_view import BaseClickCommand, ConsoleAdapter, handle_common_exc

console = ConsoleAdapter()


class DropDbException(Exception):
    pass


@click.command(
    cls=BaseClickCommand,
    name="admin-db-load-fixtures",
    help="""Load sample fixtures in the db.
    
    \b
    eg. sfts admin-db-load-fixtures
    """,
)
@click.option(
    "--no-confirmation",
    "-y",
    "do_skip_confirmation",
    is_flag=True,
    default=False,
    help="Skip all confirmation inputs",
)
def admin_db_load_fixtures_cli_view(do_skip_confirmation: bool = False):
    admin_db_load_fixtures_cmd_view(do_skip_confirmation)


@handle_common_exc()
@peewee_utils.use_db()
def admin_db_load_fixtures_cmd_view(do_skip_confirmation: bool = False) -> None:
    if not do_skip_confirmation:
        in_data = Confirm.ask(
            f"Load sample fixtures in the existing DB: [bold blue_violet on yellow2]{Path(settings.DB_PATH).relative_to(ROOT_DIR.parent)}[/]?"
        )
        if not in_data:
            raise DropDbException("Abort")

    count = 0
    for data in ITEM_MODEL_FIXTURES:
        ItemModel.create(**data)
        count += 1
    console.log(f"#{count} sample fixture loaded in: {settings.DB_PATH}")
