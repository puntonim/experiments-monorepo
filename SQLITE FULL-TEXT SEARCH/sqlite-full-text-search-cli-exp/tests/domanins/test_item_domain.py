from typing import Sequence

from fts_exp.conf import settings
from fts_exp.data_models.db_models import (
    ItemModel,
    LangEnum,
)
from fts_exp.domains.item_domain import CreateItemSchema, ItemDomain

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


def _create_items(test_data: Sequence[dict]):
    for test_datum in test_data:
        yield ItemModel.create(
            title=test_datum["title"],
            notes=test_datum["notes"],
            lang=test_datum["lang"],
        )


def _highlight_token(text: str, token_to_highlight: str):
    return text.replace(
        token_to_highlight,
        f"{settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START}{token_to_highlight}{settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END}",
    )


class TestCreateItem:
    def setup_method(self):
        self.domain = ItemDomain()

    def test_happy_flow(self):
        for i, test_datum in enumerate(TEST_DATA):
            item = self.domain.create_item(CreateItemSchema(**test_datum))
            assert item.id == i + 1
            assert item.title == test_datum["title"]
            assert item.notes == test_datum["notes"]

        items = ItemModel.select()
        assert items.count() == len(TEST_DATA)
        for i, item in enumerate(items):
            assert item.title == TEST_DATA[i]["title"]
            assert item.notes == TEST_DATA[i]["notes"]


class TestReadAllItems:
    def setup_method(self):
        self.items = [x for x in _create_items(TEST_DATA)]

    def test_happy_flow(self):
        items = ItemDomain().read_items()
        assert items.count() == len(TEST_DATA)


class TestSearchItems:
    # Light testing the actual full-text search feature as it is heavily tested in
    #  test_db_models_search.py.

    def setup_method(self):
        self.domain = ItemDomain()
        self.items = [x for x in _create_items(TEST_DATA)]

    def test_eng_first(self):
        text = "first"
        results = self.domain.search_items(text, LangEnum.ENG)
        assert len(results) == 2
        assert results[0].title_s == _highlight_token(TEST_DATA[1]["title"], "first")
        assert results[1].title_s == _highlight_token(TEST_DATA[0]["title"], "first")

    def test_eng_archaeology(self):
        text = "archaeology"
        results = self.domain.search_items(text, LangEnum.ENG)
        assert len(results) == 1
        assert results[0].notes_s == _highlight_token(
            TEST_DATA[1]["notes"], "archaeological"
        )

    def test_ita_zampeSTAR(self):
        text = "zampe*"
        results = self.domain.search_items(text, LangEnum.ITA)
        assert len(results) == 2
        assert results[0].notes_s == _highlight_token(TEST_DATA[2]["notes"], "zampino")
        assert results[1].notes_s == _highlight_token(TEST_DATA[3]["notes"], "zampette")

    def test_ita_diventerebbe(self):
        text = "diventerebbe"
        results = self.domain.search_items(text, LangEnum.ITA)
        assert len(results) == 1
        assert results[0].notes_s == _highlight_token(
            TEST_DATA[2]["notes"], "diventato"
        )
