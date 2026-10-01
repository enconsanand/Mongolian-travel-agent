"""Request-screen choices come from the seeded places, routes and stays."""

from datetime import date

import mongomock

from app.modules.orchestrator.options import search_options
from app.seeds.mock_seed import load_mock_collections


def _db():
    db = mongomock.MongoClient(tz_aware=True)["test_planner_options"]
    load_mock_collections(db, real_server=False)
    return db


def test_galig_uvs_options_use_database_stays():
    result = search_options(
        _db(),
        "uws ruu 7honogiin aylal",
        nights=7,
        guests=2,
        budget_mnt=3_500_000,
        lang="mn",
        start=date(2026, 10, 1),
    )
    assert result["feasible"] is True
    assert result["place"] == "Увс нуур"
    stay_ids = {stay["id"] for variant in result["variants"] for stop in variant["stops"] for stay in stop["stays"]}
    assert "stay_uvs_lake_camp" in stay_ids
    assert "stay_tsetserleg_hotel_bulgan" in stay_ids
    assert all(not stay_id.startswith("tsetserleg-") for stay_id in stay_ids)
    assert result["variants"][0]["stops"][-1]["id"] == "place_uvs_lake"


def test_a_nightly_price_cap_hides_stays_above_it():
    capped = search_options(
        _db(),
        "uws",
        nights=7,
        guests=2,
        budget_mnt=None,
        lang="mn",
        start=date(2026, 10, 1),
        nightly_max=1,
    )
    stay_ids = {stay["id"] for variant in capped["variants"] for stop in variant["stops"] for stay in stop["stays"]}
    assert stay_ids == set()


def test_one_night_at_uvs_is_not_offered():
    result = search_options(_db(), "Увс нуур", nights=1, guests=2, budget_mnt=None, lang="mn")
    assert result["feasible"] is False
    assert result["variants"] == []
    assert result["min_nights"] >= 3
