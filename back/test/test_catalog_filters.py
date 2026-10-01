"""Mongo filters for stays and events: free on every night, and on the calendar day."""

from app.modules.orchestrator.catalog import Catalog
from app.modules.orchestrator.filters import events_on_date, open_unit_nights, stay_ids_free_every_night, stays_within
from app.seeds.mock_seed import load_mock_collections

STAY = "stay_khatgal_camp_blue_pearl"
DAYS = ["2026-10-03", "2026-10-04", "2026-10-05"]


def test_a_unit_is_bookable_only_when_every_night_is_open(db):
    load_mock_collections(db, real_server=False)
    before = open_unit_nights(db, [STAY], DAYS)
    assert before
    unit = next(iter(before))
    db["stay_availability"].update_one(
        {"stay_id": STAY, "unit_type": unit[1], "date": "2026-10-04"},
        {"$set": {"status": "sold_out", "available": 0}},
    )
    assert unit not in open_unit_nights(db, [STAY], DAYS)


def test_one_sold_out_night_drops_the_stay_from_a_range(db):
    load_mock_collections(db, real_server=False)
    assert STAY in stay_ids_free_every_night(db, DAYS)
    db["stay_availability"].update_many(
        {"stay_id": STAY, "date": "2026-10-04"},
        {"$set": {"status": "sold_out", "available": 0}},
    )
    assert STAY not in stay_ids_free_every_night(db, DAYS)
    assert STAY in stay_ids_free_every_night(db, ["2026-10-03"])


def test_events_on_a_day_use_the_date_range(db):
    load_mock_collections(db, real_server=False)
    ids = {e["_id"] for e in events_on_date(db, "2026-10-03")}
    assert "event_khatgal_season_close_race" in ids
    assert "event_national_naadam_2027" not in ids


def test_nearby_stays_match_the_radius_used_by_the_planner(db):
    load_mock_collections(db, real_server=False)
    catalog = Catalog.load(db)
    assert stays_within(db, catalog, "place_khatgal", 60) == catalog.stays_near("place_khatgal", 60)
