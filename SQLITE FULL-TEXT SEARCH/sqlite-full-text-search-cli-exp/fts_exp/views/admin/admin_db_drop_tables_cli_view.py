from pathlib import Path

import click
import peewee_utils
from rich.prompt import Confirm

from ...conf import settings
from ...conf.settings import ROOT_DIR
from ..base_cli_view import BaseClickCommand, ConsoleAdapter, handle_common_exc

console = ConsoleAdapter()


class DropDbException(Exception):
    pass


@click.command(
    cls=BaseClickCommand,
    name="admin-db-drop-tables",
    help="""Drop all tables and make the db completely empty.
    
    \b
    eg. sfts admin-db-drop-tables
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
def admin_db_drop_tables_cli_view(do_skip_confirmation: bool = False):
    admin_db_drop_tables_cmd_view(do_skip_confirmation)


@handle_common_exc()
@peewee_utils.use_db()
def admin_db_drop_tables_cmd_view(do_skip_confirmation: bool = False) -> None:
    if not do_skip_confirmation:
        in_data = Confirm.ask(
            f"Drop all DB tables in [bold blue_violet on yellow2]{Path(settings.DB_PATH).relative_to(ROOT_DIR.parent)}[/]?"
        )
        if not in_data:
            raise DropDbException("Abort")

    peewee_utils.drop_all_tables()
    console.log(
        f"All tables dropped, the db is now completely empty: {settings.DB_PATH}"
    )
