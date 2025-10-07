"""
A very basic settings manager. I chose this because this app requires only a few
 settings and no special features.

A better alternative, in case the app requires more settings and advanced features,
 is Dynaconf.
"""

from pathlib import Path

import settings_utils

CURR_DIR = Path(__file__).parent
ROOT_DIR = CURR_DIR.parent.parent


class settings:
    """
    Usage:
        from conf import settings
        print(setting.APP_NAME)
    """

    APP_NAME = "SQLite full-text search CLI experiment"
    IS_TEST = False
    ARE_CONSOLE_LOGS_ENABLED = True
    ARE_CONSOLE_PRINTS_ENABLED = True

    DB_PATH = settings_utils.get_string_from_env(
        "DB_PATH", str(ROOT_DIR / "fts-exp-db.sqlite3")
    )
    DO_LOG_PEEWEE_QUERIES = settings_utils.get_bool_from_env(
        "DO_LOG_PEEWEE_QUERIES", False
    )
    SQLITE_EXT_SNOWBALL_MACOS_PATH = (
        ROOT_DIR
        / "vendored-requirements"
        / "snowball-for-sqlite-fts5-macos"
        / "fts5stemmer.dylib"
    )

    # Separators used when performing a search with snippet() or highlight():
    # https://docs.peewee-orm.com/en/latest/peewee/sqlite_ext.html#SearchField.snippet
    SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START = "<<"
    SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END = ">>"
    # N. token returned when performing a search with snippet(), 1 - 64:
    # https://docs.peewee-orm.com/en/latest/peewee/sqlite_ext.html#SearchField.snippet
    SQLITE_SEARCH_SNIPPET_SIZE = 64


class test_settings:
    IS_TEST = True
    ARE_CONSOLE_LOGS_ENABLED = False
    ARE_CONSOLE_PRINTS_ENABLED = False

    DB_PATH = ":memory:"
    # DB_PATH = "test.sqlite3"
    DO_LOG_PEEWEE_QUERIES = True
