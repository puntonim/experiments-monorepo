from datetime import datetime
from enum import StrEnum
from typing import Type

import datetime_utils
import peewee
import peewee_utils
from playhouse import sqlite_ext

from ..conf import settings


class LangEnum(StrEnum):
    ITA = "ITA"
    ENG = "ENG"


class ItemModel(peewee_utils.BasePeeweeModel):
    # The `id` would be implicitly added even of we comment this line, as we do
    #  not specify a primary key.
    id: int = peewee.AutoField()
    created_at: datetime = peewee_utils.UtcDateTimeField(default=datetime_utils.now_utc)
    # See trigger `update_item_updated_at_after_update_on_item` defined later.
    # Mind that you have to reload the model to get a fresh value for `updated_at`.
    updated_at: datetime = peewee_utils.UtcDateTimeField(default=datetime_utils.now_utc)

    title: str = peewee.CharField(max_length=512)
    notes: str = peewee.TextField(null=True)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, title={self.title!r})"


# Docs: https://www.sqlite.org/fts5.html
# To check if FTS5 is enabled: FTS5Model.fts5_installed()
class ItemFTSIndexIta(peewee_utils.BaseFtsModelModel):
    _LANG = LangEnum.ITA
    rowid = sqlite_ext.RowIDField()  # Must be named `rowid`.
    title = sqlite_ext.SearchField()
    notes = sqlite_ext.SearchField()

    class Meta:
        # Disable `remove_diacritics` or "diventerò" does not match "diventate".
        options = {"tokenize": "snowball italian unicode61 remove_diacritics 0"}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(rowid={self.rowid!r}, title={self.title!r})"


class ItemFTSIndexEng(peewee_utils.BaseFtsModelModel):
    _LANG = LangEnum.ENG
    rowid = sqlite_ext.RowIDField()  # Must be named `rowid`.
    title = sqlite_ext.SearchField()
    notes = sqlite_ext.SearchField()

    class Meta:
        options = {"tokenize": "snowball english unicode61 remove_diacritics 2"}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(rowid={self.rowid!r}, title={self.title!r})"


def get_index_class_for_lang(lang: LangEnum) -> Type[ItemFTSIndexIta | ItemFTSIndexEng]:
    for klass in (ItemFTSIndexIta, ItemFTSIndexEng):
        if klass._LANG == lang:
            return klass


# Register all tables.
peewee_utils.register_tables(ItemModel, ItemFTSIndexIta, ItemFTSIndexEng)

# Add a custom SQL function that serves as feature toggle for the updated_at triggers.
#  It returns 1 (True) always and it's invoked by every updated_at trigger.
#  We can overwrite this function to return 0 in order to temp disable triggers.
#  See gymiq/tests/testfactories/domains/exercise_domain_factory.py.
UPDATED_AT_TRIGGERS_TOGGLE_FUNCTION_NAME = "are_updated_at_triggers_enabled"
peewee_utils.register_sql_function(
    lambda: 1,
    UPDATED_AT_TRIGGERS_TOGGLE_FUNCTION_NAME,
    0,
)

# Register a trigger to update Activity.updated_at on every update.
# Update trigger: https://stackoverflow.com/questions/30780722/sqlite-and-recursive-triggers
# STRFTIME for timestamp with milliseconds: https://stackoverflow.com/questions/17574784/sqlite-current-timestamp-with-milliseconds
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_item_updated_at_after_update_on_item
AFTER UPDATE ON item
FOR EACH ROW
WHEN (SELECT are_updated_at_triggers_enabled()) = 1
BEGIN
    UPDATE item
    SET updated_at = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW');
END;
"""
)

# At last, configure peewee_utils with the SQLite DB path.
# Using lambda functions, instead of actual values, for lazy init, which is necessary
#  when overriding settings in tests.
peewee_utils.configure(
    get_sqlite_db_path_fn=lambda: settings.DB_PATH,
    get_do_log_peewee_queries_fn=lambda: settings.DO_LOG_PEEWEE_QUERIES,
    get_load_extensions_fn=lambda: (settings.SQLITE_EXT_SNOWBALL_MACOS_PATH,),
)
