"""Resolver: the place names a traveller wrote → place ids in the catalog, or ``unresolved``."""

import pytest

from app.modules.orchestrator.catalog import Catalog
from app.modules.orchestrator.resolver import resolve
from app.seeds.mock_seed import load_mock_collections


@pytest.fixture(scope="module")
def catalog():
    import mongomock

    db = mongomock.MongoClient(tz_aware=True)["test_planner_resolver"]
    load_mock_collections(db, real_server=False)
    return Catalog.load(db)


def never(query, candidates):
    raise AssertionError(f"no choice expected for {query!r}")


def ids(resolved):
    return [(r.query, r.place_id, r.status) for r in resolved]


@pytest.mark.parametrize(
    "name, place_id",
    [
        ("Тэрхийн Цагаан нуур", "place_terkhiin_tsagaan"),
        ("Terkhiin tsagaan", "place_terkhiin_tsagaan"),
        ("khongoryn els", "place_khongoryn_els"),  # no diacritics, any case
        ("Хонгорын элс", "place_khongoryn_els"),
        ("Хонгорын Элсэнд", "place_khongoryn_els"),  # Mongolian case ending
        ("Uran Togoo volcano", "place_uran_togoo"),
        ("Амарбаясгалант", "place_amarbayasgalant"),
    ],
)
def test_a_place_name_resolves_to_that_place(catalog, name, place_id):
    assert ids(resolve([name], catalog, never)) == [(name, place_id, "included")]


def test_an_aimag_name_lets_the_chooser_pick_one_of_its_places(catalog):
    seen = {}

    def choose(query, candidates):
        seen["candidates"] = {c["id"] for c in candidates}
        return "place_khatgal"

    assert ids(resolve(["Хөвсгөл нуур"], catalog, choose)) == [("Хөвсгөл нуур", "place_khatgal", "included")]
    assert {"place_khatgal", "place_jankhai", "place_toilogt", "place_murun"} <= seen["candidates"]
    assert all(catalog.places[i]["aimag"] == "Khövsgöl" for i in seen["candidates"])


def test_a_region_word_lets_the_chooser_pick_one_of_its_places(catalog):
    seen = {}

    def choose(query, candidates):
        seen["regions"] = {catalog.places[c["id"]]["region"] for c in candidates}
        return candidates[0]["id"]

    [place] = resolve(["Говь"], catalog, choose)
    assert place.status == "included" and seen["regions"] == {"south"}


@pytest.mark.parametrize("answer", ["place_olgii", "made_up_id", None])
def test_a_choice_outside_the_candidates_falls_back_to_the_best_candidate(catalog, answer):
    [place] = resolve(["Хөвсгөл"], catalog, lambda q, c: answer)
    # the best candidate is an attraction in that aimag that has a stay of its own
    chosen = catalog.places[place.place_id]
    assert chosen["aimag"] == "Khövsgöl" and chosen["kind"] == "attraction"
    assert catalog.stays_at(place.place_id)


def test_a_chooser_that_raises_falls_back_too(catalog):
    def broken(query, candidates):
        raise RuntimeError("model down")

    [place] = resolve(["Хөвсгөл"], catalog, broken)
    assert place.status == "included"


def test_an_unknown_place_is_reported_not_dropped(catalog):
    resolved = resolve(["Тэрэлж", "Хонгорын элс", "  "], catalog, never)
    assert ids(resolved) == [("Тэрэлж", None, "unresolved"), ("Хонгорын элс", "place_khongoryn_els", "included")]
