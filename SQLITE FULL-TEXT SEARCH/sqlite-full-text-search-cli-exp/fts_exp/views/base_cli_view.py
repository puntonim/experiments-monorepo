import contextlib
import sys

import click
import log_utils as logger
import peewee
from rich.console import Console

from ..conf import settings

# Set the rich adapter to be used in peewee-utils libs and all other libs in
#  utils-monorepo.
rich = logger.RichAdapter()
logger.set_adapter(rich)


class BaseClickCommand(click.Command):
    pass
    ## Useful to do something after the command execution and right before exiting.
    # from click import Context
    # def invoke(self, ctx: Context) -> Any:
    #     try:
    #         result = super().invoke(ctx)
    #     finally:
    #         # Do something after the command execution and right before exiting.
    #         from ..clients.tws_api_client import disconnect
    #         disconnect()
    #     return result


class handle_common_exc(contextlib.ContextDecorator):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_instance, traceback):
        if exc_type == peewee.OperationalError:
            msg = "Have you created the db?! Run: sfts admin-db-create"
            ConsoleAdapter().error(msg)
            raise NoSqliteDbFile(msg) from exc_instance
        return False  # Do not suppress the exc.


class BaseCmdViewException(Exception):
    pass


class NoSqliteDbFile(BaseCmdViewException):
    pass


class ConsoleAdapter:
    def __init__(self):
        self.stdout_console = Console(file=sys.stdout)

    def log(self, message: str, extra: dict | None = None):
        if not settings.ARE_CONSOLE_LOGS_ENABLED:
            return
        logger.get_adapter()._log(message, extra)

    def error(self, message: str, extra: dict | None = None):
        if not settings.ARE_CONSOLE_LOGS_ENABLED:
            return
        logger.get_adapter().error(f"[bold white on red]{message}[/]", extra)

    def print(self, *args, **kwargs):
        if not settings.ARE_CONSOLE_PRINTS_ENABLED:
            return
        self.stdout_console.print(*args, **kwargs)
