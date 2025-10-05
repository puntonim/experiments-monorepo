from typing import Sequence

from fts_exp.conf import settings
from fts_exp.data_models.db_models import (
    ItemFTSIndexEng,
    ItemFTSIndexIta,
    ItemModel,
    LangEnum,
)
from fts_exp.domains.item_domain import CreateItemSchema, ItemDomain

TEST_DATA = [
    dict(
        title="My first title",
        notes="My first note",
        lang=LangEnum.ENG,
    ),
    dict(
        title="My first books were about dentistry and leadership",
        notes="My first note is a lead to possibly archaeological things",
        lang=LangEnum.ENG,
    ),
    dict(
        title="Il primo titolo di papà: tanto va la gatta al lardo che ci lascia lo zampino",
        notes="La prima nota è che il dente sta dal dentista diventato anche quello di mio zio",
        lang=LangEnum.ITA,
    ),
    dict(
        title="I secondi titoli del santo Papa: lardi ecumenici su zampette",
        notes="I denti sani sono della zia dentistica",
        lang=LangEnum.ITA,
    ),
]


def _create_items(test_data: Sequence[dict]):
    for test_datum in test_data:
        yield ItemModel.create(
            title=test_datum["title"],
            notes=test_datum["notes"],
        )


def _create_indices(test_data: Sequence[dict]):
    items = ItemDomain().read_items()
    for item in items:
        yield ItemDomain().create_fts_index_for_item(
            item, lang=test_data[item.id - 1]["lang"]
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


class TestCreateFtsIndex:
    def setup_method(self):
        self.items = [x for x in _create_items(TEST_DATA)]

    def test_happy_flow(self):
        items = ItemDomain().read_items()
        assert items.count() == len(TEST_DATA)
        for item in items:
            ix = ItemDomain().create_fts_index_for_item(
                item, lang=TEST_DATA[item.id - 1]["lang"]
            )
            assert ix.rowid == item.id
            assert ix.title == item.title
            assert ix.notes == item.notes


class TestSearch:
    def setup_method(self):
        self.domain = ItemDomain()
        self.items = [x for x in _create_items(TEST_DATA)]
        self.indices = [x for x in _create_indices(TEST_DATA)]

    def test_eng_first(self):
        text = "first"
        results = self.domain.search(text, LangEnum.ENG)
        assert len(results) == 2
        assert results[0].title_h == _highlight_token(TEST_DATA[1]["title"], "first")
        assert results[1].title_h == _highlight_token(TEST_DATA[0]["title"], "first")

    def test_eng_dentist(self):
        text = "dentist"
        results = self.domain.search(text, LangEnum.ENG)
        assert len(results) == 0

    def test_eng_dentistsSTAR(self):
        text = "dentists*"
        results = self.domain.search(text, LangEnum.ENG)
        assert len(results) == 1
        assert results[0].title_h == _highlight_token(
            TEST_DATA[1]["title"], "dentistry"
        )

    def test_eng_leadsSTAR(self):
        text = "leads*"
        results = self.domain.search(text, LangEnum.ENG)
        assert len(results) == 1
        assert results[0].title_h == _highlight_token(
            TEST_DATA[1]["title"], "leadership"
        )
        assert results[0].notes_h == _highlight_token(TEST_DATA[1]["notes"], "lead")

    def test_eng_archaeology(self):
        text = "archaeology"
        results = self.domain.search(text, LangEnum.ENG)
        assert len(results) == 1
        assert results[0].notes_h == _highlight_token(
            TEST_DATA[1]["notes"], "archaeological"
        )

    def test_ita_titolo(self):
        text = "titolo"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 2
        assert results[0].title_h == _highlight_token(TEST_DATA[2]["title"], "titolo")
        assert results[1].title_h == _highlight_token(TEST_DATA[3]["title"], "titoli")

    def test_ita_zampina(self):
        text = "zampina"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 1
        assert results[0].title_h == _highlight_token(TEST_DATA[2]["title"], "zampino")

    def test_ita_zampa(self):
        text = "zampa"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 0

    def test_ita_zampeSTAR(self):
        text = "zampe*"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 2
        assert results[0].notes_h == _highlight_token(TEST_DATA[2]["notes"], "zampino")
        assert results[1].notes_h == _highlight_token(TEST_DATA[3]["notes"], "zampette")

    def test_ita_dentista(self):
        text = "dentista"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 2
        assert results[0].title_h == _highlight_token(TEST_DATA[2]["title"], "dentista")
        assert results[1].title_h == _highlight_token(
            TEST_DATA[3]["title"], "dentistica"
        )

    def test_ita_diventerebbe(self):
        text = "diventerebbe"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 1
        assert results[0].notes_h == _highlight_token(
            TEST_DATA[2]["notes"], "diventato"
        )

    def test_ita_diventerò(self):
        text = "diventerò"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 1
        assert results[0].notes_h == _highlight_token(
            TEST_DATA[2]["notes"], "diventato"
        )

    def test_ita_papa(self):
        text = "papa"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 2
        assert results[0].title_h == _highlight_token(TEST_DATA[2]["title"], "papà")
        assert results[1].title_h == _highlight_token(TEST_DATA[3]["title"], "Papa")

    def test_ita_papà(self):
        text = "papa"
        results = self.domain.search(text, LangEnum.ITA)
        assert len(results) == 2
        assert results[0].title_h == _highlight_token(TEST_DATA[2]["title"], "papà")
        assert results[1].title_h == _highlight_token(TEST_DATA[3]["title"], "Papa")
