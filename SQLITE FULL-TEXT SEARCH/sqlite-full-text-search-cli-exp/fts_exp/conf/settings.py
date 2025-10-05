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

    DB_PATH = settings_utils.get_string_from_env(
        "DB_PATH", str(ROOT_DIR / "fts-exp-db.sqlite3")
    )
    DO_LOG_PEEWEE_QUERIES = False
    SQLITE_EXT_SNOWBALL_MACOS_PATH = (
        ROOT_DIR
        / "vendored-requirements"
        / "snowball-for-sqlite-fts5-macos"
        / "fts5stemmer.dylib"
    )

    SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START = "<<"
    SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END = ">>"


class test_settings:
    IS_TEST = True

    DB_PATH = ":memory:"
    # DB_PATH = "test.sqlite3"
    DO_LOG_PEEWEE_QUERIES = True
