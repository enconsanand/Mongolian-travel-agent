"""Prepared scenic routes: theme words pick a multi-stop itinerary when no place is named."""

import mongomock
import pytest

from app.modules.orchestrator.catalog import Catalog
from app.modules.orchestrator.resolver import candidates
from app.modules.orchestrator.scenic import (
    ITINERARIES,
    choose_itinerary,
    is_specific,
    mentioned,
    named_words,
    theme_of,
    wants_far,
)
from app.seeds.mock_seed import load_mock_collections


@pytest.fixture
def catalog():
    db = mongomock.MongoClient(tz_aware=True)["test_scenic"]
    load_mock_collections(db, real_server=False)
    return Catalog.load(db)


def test_each_prepared_route_has_four_to_six_stops_that_exist(catalog):
    assert len(ITINERARIES) >= 5
    for route in ITINERARIES:
        assert 4 <= len(route.places) <= 6
        assert all(pid in catalog.places for pid in route.places)


def test_empty_pool_when_everything_is_avoided(catalog):
    avoid = {pid for route in ITINERARIES for pid in route.places}
    assert choose_itinerary(catalog, theme="water", far=True, nights=7, avoid=avoid) == []


def test_theme_words_are_read_from_mongolian_and_galig():
    assert theme_of("устай газар явмаар") == "water"
    assert theme_of("uul had uzmeer") == "mountain"
    assert theme_of("элсэн цөл рүү") == "desert"
    assert theme_of("говь үзмээр") == "desert"
    assert theme_of("арай хол газар") is None


def test_far_and_near_words():
    assert wants_far("Арай хол газар луу явмаар") is True
    assert wants_far("ойрхон газар") is False
    assert wants_far("устай газар") is None


def test_landscape_words_are_not_treated_as_place_names():
    assert is_specific("нуур") is False
    assert is_specific("уул хад") is False
    assert is_specific("говь") is False
    assert is_specific("Хатгал") is True
    assert is_specific("Эрдэнэзуу") is True


def test_invented_places_are_ignored_when_not_in_the_request():
    assert mentioned("Аглаг бүтээл", "Арай хол газар луу явмаар") is False
    assert mentioned("Хатгал", "Хатгалд 3 хонъё") is True


def test_water_request_picks_a_lake_route(catalog):
    stops = choose_itinerary(catalog, theme="water", far=True, nights=7, avoid=set())
    assert "place_khuvsgul_lake" in stops or "place_khatgal" in stops
    assert len(stops) >= 4


def test_desert_request_picks_sand_and_gobi(catalog):
    stops = choose_itinerary(catalog, theme="desert", far=True, nights=7, avoid=set())
    assert "place_khongoryn_els" in stops or "place_bayanzag" in stops


def test_mountain_near_request_stays_around_terelj(catalog):
    stops = choose_itinerary(catalog, theme="mountain", far=False, nights=4, avoid=set())
    assert "place_terelj" in stops
    assert "place_khuvsgul_lake" not in stops


def test_a_named_place_in_the_text_is_found(catalog):
    found = named_words("Хатгалд 4 хоног", catalog)
    assert found
    assert candidates(found[0], catalog) == ["place_khatgal"]
