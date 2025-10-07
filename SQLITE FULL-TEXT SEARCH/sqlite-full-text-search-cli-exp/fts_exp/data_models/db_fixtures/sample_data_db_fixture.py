from ..db_models import LangEnum

ITEM_MODEL_FIXTURES = (
    # index: 0.
    dict(
        title="My first title",
        notes="My first note",
        lang=LangEnum.ENG,
    ),
    # index: 1.
    dict(
        title="My first books were about dentistry and leadership",
        notes="My first note is a lead to possibly archaeological things",
        lang=LangEnum.ENG,
    ),
    # index: 2.
    dict(
        title="Il primo titolo di papà: tanto va la gatta al lardo che ci lascia lo zampino",
        notes="La prima nota è che il dente sta dal dentista diventato anche quello di mio zio",
        lang=LangEnum.ITA,
    ),
    # index: 2.
    dict(
        title="I secondi titoli del santo Papa: lardi ecumenici su zampette",
        notes="I denti sani sono della zia dentistica",
        lang=LangEnum.ITA,
    ),
)
