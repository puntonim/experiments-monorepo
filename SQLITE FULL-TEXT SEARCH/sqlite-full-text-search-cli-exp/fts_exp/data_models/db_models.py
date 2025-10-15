from datetime import datetime
from enum import StrEnum
from typing import Type

import datetime_utils
import peewee
import peewee_utils
from playhouse import sqlite_ext

from ..conf import settings


class LangEnum(StrEnum):
    # str(LangEnum.ITA) == "I".
    # LangEnum.ITA.value = "I"
    # LangEnum.ITA.name = "ITA"
    ITA = "I"
    ENG = "E"


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

    # Mind that the choices are not enforced, they are just for metadata.
    #  See docs: https://docs.peewee-orm.com/en/latest/peewee/models.html#field-initialization-arguments
    # Eg. ItemModel.create(title="...", notes="...", lang=LangEnum.ENG)
    lang: str = peewee.FixedCharField(
        max_length=1, choices=[(x.value, x.name) for x in LangEnum]
    )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, title={self.title!r}, lang={self.lang!r})"


# Docs: https://www.sqlite.org/fts5.html
# To check if FTS5 is enabled: FTS5Model.fts5_installed()
class ItemFTSIndexIta(peewee_utils.BaseFtsModelModel):
    """
    Italian index table with external-content.
    Docs:
        https://sqlite.org/fts5.html#external_content_tables
        https://docs.peewee-orm.com/en/latest/peewee/sqlite_ext.html#FTSModel
    """

    _LANG = LangEnum.ITA
    rowid = sqlite_ext.RowIDField()  # Must be named `rowid`.
    title = sqlite_ext.SearchField()
    notes = sqlite_ext.SearchField()

    class Meta:
        options = {
            # Disable `remove_diacritics` or "diventerò" does not match "diventate".
            "tokenize": "snowball italian unicode61 remove_diacritics 0",
            # External-content.
            "content": ItemModel,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(rowid={self.rowid!r}, title={self.title!r})"


class ItemFTSIndexEng(peewee_utils.BaseFtsModelModel):
    """
    English index table with external-content.
    Docs:
        https://sqlite.org/fts5.html#external_content_tables
        https://docs.peewee-orm.com/en/latest/peewee/sqlite_ext.html#FTSModel
    """

    _LANG = LangEnum.ENG
    rowid = sqlite_ext.RowIDField()  # Must be named `rowid`.
    title = sqlite_ext.SearchField()
    notes = sqlite_ext.SearchField()

    class Meta:
        options = {
            "tokenize": "snowball english unicode61 remove_diacritics 2",
            # External-content.
            "content": ItemModel,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(rowid={self.rowid!r}, title={self.title!r})"


def get_index_class_for_lang(
    lang: LangEnum | str,
) -> Type[ItemFTSIndexIta | ItemFTSIndexEng]:
    # Convert str to LangEnum. And it does not fail if `lang` is already a LangEnum.
    lang = LangEnum(lang)
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

# Register a TRIGGER to update **Activity.updated_at** on every update.
# Update trigger: https://stackoverflow.com/questions/30780722/sqlite-and-recursive-triggers
# STRFTIME for timestamp with milliseconds: https://stackoverflow.com/questions/17574784/sqlite-current-timestamp-with-milliseconds
peewee_utils.register_trigger(
    f"""
CREATE TRIGGER IF NOT EXISTS update_item_updated_at_after_update_on_item
AFTER UPDATE ON item
FOR EACH ROW
WHEN (SELECT {UPDATED_AT_TRIGGERS_TOGGLE_FUNCTION_NAME}()) = 1
BEGIN
    UPDATE item
    SET updated_at = STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW');
END;
"""
)

# Register TRIGGERS to keep **ItemFTSIndexIta** automatically updated with ItemModel.
# Docs: https://sqlite.org/fts5.html#external_content_tables
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_itemftsindexita_after_insert_on_item
AFTER INSERT ON item
FOR EACH ROW
WHEN new.lang = 'I'
BEGIN
    INSERT INTO itemftsindexita(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;
"""
)
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_itemftsindexita_after_delete_on_item
AFTER DELETE ON item
FOR EACH ROW
WHEN old.lang = 'I'
BEGIN
    INSERT INTO itemftsindexita(itemftsindexita, rowid, title, notes) VALUES('delete', old.id, old.title, old.notes);
END;
"""
)
# The next 4 triggers manages the update on item in the 4 cases when the old and new
#  language can be both ita, both eng, or one ita and one eng.
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_indices_after_update_on_item_1
AFTER UPDATE ON item
FOR EACH ROW
WHEN old.lang = 'I' AND new.lang = 'I'
BEGIN
    INSERT INTO itemftsindexita(itemftsindexita, rowid, title, notes) VALUES('delete', old.id, old.title, old.notes);
    INSERT INTO itemftsindexita(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;
"""
)
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_indices_after_update_on_item_2
AFTER UPDATE ON item
FOR EACH ROW
WHEN old.lang = 'I' AND new.lang = 'E'
BEGIN
    INSERT INTO itemftsindexita(itemftsindexita, rowid, title, notes) VALUES('delete', old.id, old.title, old.notes);
    INSERT INTO itemftsindexeng(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;
"""
)
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_indices_after_update_on_item_3
AFTER UPDATE ON item
FOR EACH ROW
WHEN old.lang = 'E' AND new.lang = 'I'
BEGIN
    INSERT INTO itemftsindexeng(itemftsindexeng, rowid, title, notes) VALUES('delete', old.id, old.title, old.notes);
    INSERT INTO itemftsindexita(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;
"""
)
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_indices_after_update_on_item_4
AFTER UPDATE ON item
FOR EACH ROW
WHEN old.lang = 'E' AND new.lang = 'E'
BEGIN
    INSERT INTO itemftsindexeng(itemftsindexeng, rowid, title, notes) VALUES('delete', old.id, old.title, old.notes);
    INSERT INTO itemftsindexeng(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;
"""
)

# Register TRIGGERS to keep **ItemFTSIndexEng** automatically updated with ItemModel.
# Docs: https://sqlite.org/fts5.html#external_content_tables
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_itemftsindexeng_after_insert_on_item
AFTER INSERT ON item
FOR EACH ROW
WHEN new.lang = 'E'
BEGIN
    INSERT INTO itemftsindexeng(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;
"""
)
peewee_utils.register_trigger(
    """
CREATE TRIGGER IF NOT EXISTS update_itemftsindexeng_after_delete_on_item
AFTER DELETE ON item
FOR EACH ROW
WHEN old.lang = 'E'
BEGIN
    INSERT INTO itemftsindexeng(itemftsindexeng, rowid, title, notes) VALUES('delete', old.id, old.title, old.notes);
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
