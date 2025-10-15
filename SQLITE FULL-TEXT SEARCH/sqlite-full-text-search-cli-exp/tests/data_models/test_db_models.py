from datetime import timedelta, timezone

from fts_exp.conf import settings
from fts_exp.data_models.db_models import (
    ItemFTSIndexEng,
    ItemFTSIndexIta,
    ItemModel,
    LangEnum,
)

TEST_DATA_ENG = [
    dict(
        title="My first title",
        notes="My first note",
        lang=LangEnum.ENG,
    ),
    dict(
        title="My first books were about dentistry and leadership",
        notes="My first note is a lead to possibly archaeological things in the computer",
        lang=LangEnum.ENG,
    ),
]

TEST_DATA_ITA = [
    dict(
        title="Il primo titolo di papà: tanto va la gatta al lardo che ci lascia lo zampino",
        notes="La prima nota è che il dente sta dal dentista diventato anche quello di mio zio",
        lang=LangEnum.ITA,
    ),
    dict(
        title="I secondi titoli del santo Papa: lardi ecumenici su zampette",
        notes="I denti sani sono della zia dentistica al computer",
        lang=LangEnum.ITA,
    ),
]

TEST_DATA = TEST_DATA_ENG + TEST_DATA_ITA


def _make_search_query(index_class, text):
    return (
        index_class.select(
            index_class.rowid,
            index_class.bm25().alias("score"),
            index_class.title.snippet(
                settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START,
                settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END,
                max_tokens=settings.SQLITE_SEARCH_SNIPPET_SIZE,
            ).alias("title_s"),
            index_class.notes.snippet(
                settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START,
                settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END,
                max_tokens=settings.SQLITE_SEARCH_SNIPPET_SIZE,
            ).alias("notes_s"),
        )
        .where(index_class.match(text))
        .order_by(-index_class.bm25())
    )


class TestItemModel:
    # Only light testing as we assume that Peewee works!

    def test_create(self):
        assert ItemModel.select().count() == 0
        for test_datum in TEST_DATA_ENG[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ENG
            )
        assert ItemModel.select().count() == 2

    def test_db_isolation(self):
        # It's intentionally the same as the prev test. The purpose is to ensure that
        #  single tests isolation works and the 2 items inserted in the prev tests are
        #  gone.
        assert ItemModel.select().count() == 0
        for test_datum in TEST_DATA_ENG[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ENG
            )
        assert ItemModel.select().count() == 2

    def test_trigger_updated_at(self):
        # The goal is to test the trigger that updates the updated_at col on every
        #  SQL UPDATE statement.

        ItemModel.create(
            title=TEST_DATA_ENG[0]["title"],
            notes=TEST_DATA_ENG[0]["notes"],
            lang=LangEnum.ENG,
        )

        # The goal is to ensure that when updating an ItemModel, then its `updated_at`
        #  attribute is automatically updated.
        a = ItemModel.get_by_id(1)
        assert a.created_at.tzinfo == timezone.utc
        assert a.updated_at > a.created_at
        assert (a.updated_at - a.created_at) > timedelta(seconds=0)
        assert (a.updated_at - a.created_at) < timedelta(seconds=1)

        prev_updated_at = a.updated_at
        new_title = "title bis"
        a.title = new_title
        a.save()
        # Reload the model to get the new updated_at.
        a = ItemModel.get_by_id(1)
        assert a.title == new_title
        assert a.updated_at > prev_updated_at
        assert (a.updated_at - prev_updated_at) > timedelta(seconds=0)
        assert (a.updated_at - prev_updated_at) < timedelta(seconds=1)


class TestItemFTSIndexIta_TriggerOnInsertItem:
    # The goal is to test that the ITA index (ItemFTSIndexIta) is built after
    #  an INSERT on Item, by the trigger.

    def test_create(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ITA[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ITA
            )

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexIta.select().count() == 2
        # The ENG index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexEng.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 2
        assert query[0].rowid == 1
        assert query[1].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

    def test_insert(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ITA[:2]:
            ItemModel.insert(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ITA
            ).execute()

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexIta.select().count() == 2
        # The ENG index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexEng.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 2
        assert query[0].rowid == 1
        assert query[1].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

    def test_save(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ITA[:2]:
            item = ItemModel()
            item.title = test_datum["title"]
            item.notes = test_datum["notes"]
            item.lang = LangEnum.ITA
            item.save()

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexIta.select().count() == 2
        # The ENG index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexEng.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 2
        assert query[0].rowid == 1
        assert query[1].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0


class TestItemFTSIndexEng_TriggerOnInsertItem:
    # The goal is to test that the ENG index (ItemFTSIndexEng) is built after
    #  an INSERT on Item, by the trigger.

    def test_create(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ENG[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ENG
            )

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexEng.select().count() == 2
        # The ITA index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexIta.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 2
        assert query[0].rowid == 2
        assert query[1].rowid == 1
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

    def test_insert(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ENG[:2]:
            ItemModel.insert(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ENG
            ).execute()

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexEng.select().count() == 2
        # The ITA index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexIta.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 2
        assert query[0].rowid == 2
        assert query[1].rowid == 1
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

    def test_save(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ENG[:2]:
            item = ItemModel()
            item.title = test_datum["title"]
            item.notes = test_datum["notes"]
            item.lang = LangEnum.ENG
            item.save()

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexEng.select().count() == 2
        # The ITA index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexIta.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 2
        assert query[0].rowid == 2
        assert query[1].rowid == 1
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0


class TestItemFTSIndexIta_TriggerOnDeleteItem:
    # The goal is to test that the ITA index (ItemFTSIndexIta) is deleted after
    #  a DELETE on Item, by the trigger.

    def setup_method(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ITA[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ITA
            )

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexIta.select().count() == 2
        # The ENG index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexEng.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 2
        assert query[0].rowid == 1
        assert query[1].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

    def test_delete(self):
        assert ItemModel.select().count() == 2

        # Delete 1 item first.
        ItemModel.delete().where(ItemModel.id == 1).execute()
        assert ItemModel.select().count() == 1

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

        # Delete also the other item, so there are no items left.
        ItemModel.delete().where(ItemModel.id == 2).execute()
        assert ItemModel.select().count() == 0

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

    def test_delete_instance(self):
        assert ItemModel.select().count() == 2

        # Delete 1 item first.
        ItemModel.select().first().delete_instance()
        assert ItemModel.select().count() == 1

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

        # Delete also the other item, so there are no items left.
        ItemModel.select().first().delete_instance()
        assert ItemModel.select().count() == 0

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0


class TestItemFTSIndexEng_TriggerOnDeleteItem:
    # The goal is to test that the ENG index (ItemFTSIndexEng) is deleted after
    #  a DELETE on Item, by the trigger.

    def setup_method(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ENG[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ENG
            )

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexEng.select().count() == 2
        # The ITA index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexIta.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 2
        assert query[0].rowid == 2
        assert query[1].rowid == 1
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

    def test_delete(self):
        assert ItemModel.select().count() == 2

        # Delete 1 item first.
        ItemModel.delete().where(ItemModel.id == 1).execute()
        assert ItemModel.select().count() == 1

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

        # Delete also the other item, so there are no items left.
        ItemModel.delete().where(ItemModel.id == 2).execute()
        assert ItemModel.select().count() == 0

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

    def test_delete_instance(self):
        assert ItemModel.select().count() == 2

        # Delete 1 item first.
        ItemModel.select().first().delete_instance()
        assert ItemModel.select().count() == 1

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

        # Delete also the other item, so there are no items left.
        ItemModel.select().first().delete_instance()
        assert ItemModel.select().count() == 0

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0


class TestItemFTSIndexIta_TriggerOnUpdateItem:
    # The goal is to test that the ITA index (ItemFTSIndexIta) is updated after
    #  an UPDATE on Item, by the trigger.

    def setup_method(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ITA[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ITA
            )

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexIta.select().count() == 2
        # The ENG index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexEng.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 2
        assert query[0].rowid == 1
        assert query[1].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

    def test_update(self):
        assert ItemModel.select().count() == 2

        # Update the 1st item.
        ItemModel.update(
            title="primo titolo viaggeremo computer",
            notes="prima nota viaggerò computer",
        ).where(ItemModel.id == 1).execute()

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

        # Update also the 2nd item.
        ItemModel.update(
            title="secondo titolo viaggerei computer",
            notes="seconda nota viaggiammo computer",
        ).where(ItemModel.id == 2).execute()

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexIta, "viaggiano")
        assert query.count() == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

    def test_update_save(self):
        assert ItemModel.select().count() == 2

        # Update the 1st item.
        item = ItemModel.get_by_id(1)
        item.title = "primo titolo viaggeremo computer"
        item.notes = "prima nota viaggerò computer"
        item.save()

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

        # Update also the 2nd item.
        item = ItemModel.get_by_id(2)
        item.title = "secondo titolo viaggerei computer"
        item.notes = "seconda nota viaggiammo computer"
        item.save()

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexIta, "viaggiamo")
        assert query.count() == 2
        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0

    def test_switch_lang(self):
        # Test what happens when the update changes the lang Item.lang from ITA
        #  to ENG.

        assert ItemModel.select().count() == 2

        # Update the 1st item switching the lang to ENG.
        item = ItemModel.get_by_id(1)
        item.title = "first title travels"
        item.notes = "first note travel"
        item.lang = LangEnum.ENG
        item.save()

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexIta, "title")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "travel")
        assert query.count() == 1
        assert query[0].rowid == 1

        # Update also the 2nd item switching the lang to ENG.
        item = ItemModel.get_by_id(2)
        item.title = "second title travelled"
        item.notes = "second note traveling"
        item.lang = LangEnum.ENG
        item.save()

        query = _make_search_query(ItemFTSIndexIta, "dente")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexIta, "title")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "travel")
        assert query.count() == 2


class TestItemFTSIndexEng_TriggerOnUpdateItem:
    # The goal is to test that the ENG index (ItemFTSIndexEng) is updated after
    #  an UPDATE on Item, by the trigger.

    def setup_method(self):
        assert ItemModel.select().count() == 0
        assert ItemFTSIndexIta.select().count() == 0
        assert ItemFTSIndexEng.select().count() == 0

        for test_datum in TEST_DATA_ENG[:2]:
            ItemModel.create(
                title=test_datum["title"], notes=test_datum["notes"], lang=LangEnum.ENG
            )

        # Asserts on counts.
        assert ItemModel.select().count() == 2
        assert ItemFTSIndexEng.select().count() == 2
        # The ITA index has count == 2 and not 0, maybe because for external-content
        #  tables the count query is executed against the original table, under the
        #  hood.
        assert ItemFTSIndexIta.select().count() == 2

        # Asserts on search queries.
        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 2
        assert query[0].rowid == 2
        assert query[1].rowid == 1
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

    def test_update(self):
        assert ItemModel.select().count() == 2

        # Update the 1st item.
        ItemModel.update(
            title="updated title one computer", notes="updated note one computer"
        ).where(ItemModel.id == 1).execute()

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

        # Update also the 2nd item.
        ItemModel.update(
            title="updated title two computer", notes="updated note two computer"
        ).where(ItemModel.id == 2).execute()

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "update")
        assert query.count() == 2
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

    def test_update_save(self):
        assert ItemModel.select().count() == 2

        # Update the 1st item.
        item = ItemModel.get_by_id(1)
        item.title = "updated title one computer"
        item.notes = "updated note one computer"
        item.save()

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 1
        assert query[0].rowid == 2
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

        # Update also the 2nd item.
        item = ItemModel.get_by_id(2)
        item.title = "updated title two computer"
        item.notes = "updated note two computer"
        item.save()

        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "update")
        assert query.count() == 2
        query = _make_search_query(ItemFTSIndexIta, "computer")
        assert query.count() == 0

    def test_switch_lang(self):
        # Test what happens when the update changes the lang Item.lang from ENG
        #  to ITA.

        assert ItemModel.select().count() == 2

        # Update the 1st item switching the lang to ITA.
        item = ItemModel.get_by_id(1)
        item.title = "titolo uno viaggeremo computer"
        item.notes = "titolo uno viaggerò computer"
        item.lang = LangEnum.ITA
        item.save()

        query = _make_search_query(ItemFTSIndexIta, "viaggiamo")
        assert query.count() == 1
        assert query[0].rowid == 1
        query = _make_search_query(ItemFTSIndexEng, "title")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "first")
        assert query.count() == 1
        assert query[0].rowid == 2

        # Update also the 2nd item switching the lang to ENG.
        item = ItemModel.get_by_id(2)
        item.title = "titolo uno viaggiarono computer"
        item.notes = "titolo uno viaggiassimo computer"
        item.lang = LangEnum.ITA
        item.save()

        query = _make_search_query(ItemFTSIndexEng, "computer")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexEng, "title")
        assert query.count() == 0
        query = _make_search_query(ItemFTSIndexIta, "viaggiamo")
        assert query.count() == 2
