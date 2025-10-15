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


def _highlight_token(text: str, token_to_highlight: str):
    return text.replace(
        token_to_highlight,
        f"{settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_START}{token_to_highlight}{settings.SQLITE_SEARCH_HIGHLIGHT_SEPARATOR_END}",
    )


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


class TestSearchEng:
    # The goal is to test the full-text search feature in English, that includes
    #  the stemming.

    def setup_method(self):
        for test_datum in TEST_DATA:
            ItemModel.create(**test_datum)

    def test_first(self):
        text = "first"
        query = _make_search_query(ItemFTSIndexEng, text)
        assert len(query) == 2
        assert query[0].title_s == _highlight_token(TEST_DATA[1]["title"], "first")
        assert query[1].title_s == _highlight_token(TEST_DATA[0]["title"], "first")

    def test_dentist(self):
        # "dentist" doe snot match "dentistry".
        text = "dentist"
        query = _make_search_query(ItemFTSIndexEng, text)
        assert len(query) == 0

    def test_dentistsSTAR(self):
        # "dentists*" matches "dentistry".
        text = "dentists*"
        query = _make_search_query(ItemFTSIndexEng, text)
        assert len(query) == 1
        assert query[0].title_s == _highlight_token(TEST_DATA[1]["title"], "dentistry")

    def test_leadsSTAR(self):
        # "leads*" matches "leadership" and "lead".
        text = "leads*"
        query = _make_search_query(ItemFTSIndexEng, text)
        assert len(query) == 1
        assert query[0].title_s == _highlight_token(TEST_DATA[1]["title"], "leadership")
        assert query[0].notes_s == _highlight_token(TEST_DATA[1]["notes"], "lead")

    def test_archaeology(self):
        # "archaeology" matches "archaeological".
        text = "archaeology"
        query = _make_search_query(ItemFTSIndexEng, text)
        assert len(query) == 1
        assert query[0].notes_s == _highlight_token(
            TEST_DATA[1]["notes"], "archaeological"
        )


class TestSearchIta:
    # The goal is to test the full-text search feature in Italian, that includes
    #  the stemming.

    def setup_method(self):
        for test_datum in TEST_DATA:
            ItemModel.create(**test_datum)

    def test_titolo(self):
        # "titolo" matches "titolo" and "titoli".
        text = "titolo"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 2
        assert query[0].title_s == _highlight_token(TEST_DATA[2]["title"], "titolo")
        assert query[1].title_s == _highlight_token(TEST_DATA[3]["title"], "titoli")

    def test_zampina(self):
        # "zampina" matches "zampino".
        text = "zampina"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 1
        assert query[0].title_s == _highlight_token(TEST_DATA[2]["title"], "zampino")

    def test_zampa(self):
        # "zampa" does not match "zampino" nor "zampette".
        text = "zampa"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 0

    def test_zampeSTAR(self):
        # "zampe*" matches "zampino" and "zampette".
        text = "zampe*"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 2
        assert query[0].notes_s == _highlight_token(TEST_DATA[2]["notes"], "zampino")
        assert query[1].notes_s == _highlight_token(TEST_DATA[3]["notes"], "zampette")

    def test_dentista(self):
        # "dentista" matches "dentista" and "dentistica".
        text = "dentista"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 2
        assert query[0].title_s == _highlight_token(TEST_DATA[2]["title"], "dentista")
        assert query[1].title_s == _highlight_token(TEST_DATA[3]["title"], "dentistica")

    def test_diventerebbe(self):
        # "diventerebbe" matches "diventato".
        text = "diventerebbe"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 1
        assert query[0].notes_s == _highlight_token(TEST_DATA[2]["notes"], "diventato")

    def test_diventerò(self):
        # "diventerò" matches "diventato".
        text = "diventerò"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 1
        assert query[0].notes_s == _highlight_token(TEST_DATA[2]["notes"], "diventato")

    def test_papa(self):
        # "papa" matches "papà" and "Papa".
        text = "papa"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 2
        assert query[0].title_s == _highlight_token(TEST_DATA[2]["title"], "papà")
        assert query[1].title_s == _highlight_token(TEST_DATA[3]["title"], "Papa")

    def test_papà(self):
        # "papà" matches "papà" and "Papa".
        text = "papà"
        query = _make_search_query(ItemFTSIndexIta, text)
        assert len(query) == 2
        assert query[0].title_s == _highlight_token(TEST_DATA[2]["title"], "papà")
        assert query[1].title_s == _highlight_token(TEST_DATA[3]["title"], "Papa")
