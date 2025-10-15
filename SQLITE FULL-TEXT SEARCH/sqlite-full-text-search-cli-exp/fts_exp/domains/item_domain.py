import peewee
import pydantic_utils

from ..conf import settings
from ..data_models.db_models import (
    ItemFTSIndexEng,
    ItemFTSIndexIta,
    ItemModel,
    LangEnum,
    get_index_class_for_lang,
)


class CreateItemSchema(pydantic_utils.BasePydanticSchema):
    title: str
    notes: str | None = None
    lang: LangEnum


class ItemDomain:
    def create_item(self, schema: CreateItemSchema) -> ItemModel:
        # Note: this is only 1 INSERT query and it returns the model just created.
        # So it is better than ItemModel.insert().execute() which is also 1 INSERT
        #  query (the same one) but it returns only the id of the new model.
        return ItemModel.create(**schema.to_dict())

    def read_items(self, item_id: int | None = None) -> peewee.ModelSelect:
        items: peewee.ModelSelect = ItemModel.select()
        if item_id is not None:
            items = items.where(ItemModel.id == item_id)
        return items

    def search_items(self, text: str, lang: LangEnum) -> peewee.ModelSelect:
        _ItemFTSIndex = get_index_class_for_lang(lang)

        query: peewee.ModelSelect = (
            _ItemFTSIndex.select(
                _ItemFTSIndex.rowid,
                _ItemFTSIndex.bm25().alias("score"),
                _ItemFTSIndex.title.snippet(
                    settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START,
                    settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END,
                    max_tokens=settings.SQLITE_SEARCH_SNIPPET_SIZE,
                ).alias("title_s"),
                _ItemFTSIndex.notes.snippet(
                    settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START,
                    settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END,
                    max_tokens=settings.SQLITE_SEARCH_SNIPPET_SIZE,
                ).alias("notes_s"),
            )
            .where(_ItemFTSIndex.match(text))
            .order_by(-_ItemFTSIndex.bm25())
        )
        return query
