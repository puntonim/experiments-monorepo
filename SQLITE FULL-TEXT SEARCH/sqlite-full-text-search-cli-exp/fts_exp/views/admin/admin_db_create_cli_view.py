import click
import peewee_utils

from ...conf import settings
from ..base_cli_view import BaseClickCommand, ConsoleAdapter
from .admin_db_load_fixtures_cli_view import (
    DropDbException,
    admin_db_load_fixtures_cmd_view,
)

console = ConsoleAdapter()


@click.command(
    cls=BaseClickCommand,
    name="admin-db-create",
    help="""Create the SQLite db file.
    
    \b
    eg. sfts admin-db-create
    """,
)
@click.option(
    "--load-sample-fixtures",
    "-fix",
    "do_load_sample_fixtures",
    is_flag=True,
    default=None,
    help="Load sample fixtures in the db",
)
def admin_db_create_cli_view(do_load_sample_fixtures: bool | None = None):
    admin_db_create_cmd_view(do_load_sample_fixtures)


@peewee_utils.use_db()
def admin_db_create_cmd_view(do_load_sample_fixtures: bool | None = None) -> None:
    peewee_utils.create_all_tables()

    console.log(f"DB created: {settings.DB_PATH}")

    if do_load_sample_fixtures is False:
        return

    do_skip_confirmation = True if do_load_sample_fixtures else False
    try:
        admin_db_load_fixtures_cmd_view(do_skip_confirmation=do_skip_confirmation)
    except DropDbException:
        pass
