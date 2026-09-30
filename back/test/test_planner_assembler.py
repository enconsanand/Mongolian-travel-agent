"""Assembler: resolved places + request → days, stays, events, totals. No model involved."""

from datetime import date, timedelta
from math import ceil

import mongomock
import pytest

from app.modules.orchestrator.assembler import assemble
from app.modules.orchestrator.catalog import HUB, Catalog
from app.modules.orchestrator.types import PlanRequest
from app.seeds.mock_seed import load_mock_collections

KHATGAL, TERKH, OLGII = "place_khatgal", "place_terkhiin_tsagaan", "place_olgii"


@pytest.fixture(scope="module")
def db():
    database = mongomock.MongoClient(tz_aware=True)["test_planner_assembler"]
    load_mock_collections(database, real_server=False)
    return database


@pytest.fixture(scope="module")
def catalog(db):
    return Catalog.load(db)


def request(start="2026-10-03", end="2026-10-08", guests=2, style="comfort", budget=None):
    return PlanRequest(
        guests=guests,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end),
        style=style,
        budget_mnt=budget,
    )


def visited(plan):
    return {pid for d in plan.days for pid in (d.from_place_id, d.to_place_id, *d.via_place_ids)}


def test_every_must_place_is_in_the_plan_and_the_trip_starts_and_ends_in_ulaanbaatar(db, catalog):
    req = request()
    plan = assemble(db, catalog, req, [TERKH, KHATGAL], {})
    assert {KHATGAL, TERKH} <= visited(plan)
    assert len(plan.days) == req.nights + 1
    assert [d.date for d in plan.days] == [(req.start_date + timedelta(days=i)).isoformat() for i in range(6)]
    assert plan.days[0].from_place_id == HUB and plan.days[-1].to_place_id == HUB
    for before, after in zip(plan.days, plan.days[1:], strict=False):
        assert after.from_place_id == before.to_place_id


def test_every_night_has_a_stay_that_is_free_and_sleeps_the_group(db, catalog):
    req = request(guests=5)
    plan = assemble(db, catalog, req, [KHATGAL, TERKH], {})
    nights = plan.days[:-1]
    assert plan.days[-1].stay_id is None
    assert any(d.stay_id for d in nights)
    # Terkhiin Tsagaan's camp is closed for the season in October: those nights have no stay, and the plan says so
    assert all(d.stay_id for d in nights) or "no_availability" in plan.warnings
    for day in plan.days:
        if not day.stay:
            continue
        stay = db["stays"].find_one({"_id": day.stay.stay_id})
        unit = next(u for u in stay["units"] if u["unit_type"] == day.stay.unit_type)
        assert day.stay.units == ceil(5 / unit["beds_per_unit"])
        first = date.fromisoformat(day.date)
        for i in range(day.stay.nights):
            row = db["stay_availability"].find_one(
                {"stay_id": stay["_id"], "unit_type": unit["unit_type"], "date": (first + timedelta(i)).isoformat()}
            )
            assert row["status"] == "open" and row["available"] >= day.stay.units
    assert plan.totals.stays_mnt == sum(d.stay.total_mnt for d in plan.days if d.stay)


def test_a_stay_is_near_the_place_slept_at(db, catalog):
    plan = assemble(db, catalog, request(), [KHATGAL], {})
    for day in plan.days:
        if day.stay:
            assert day.stay.stay_id in {s["_id"] for _, s in catalog.stays_near(day.to_place_id, 60)}


def test_nights_hint_is_honoured(db, catalog):
    plan = assemble(db, catalog, request(), [KHATGAL, TERKH], {KHATGAL: 3})
    assert sum(1 for d in plan.days[:-1] if d.to_place_id == KHATGAL) == 3


def test_more_places_than_nights_still_visits_every_place(db, catalog):
    places = [KHATGAL, TERKH, "place_tsetserleg"]
    plan = assemble(db, catalog, request(end="2026-10-04"), places, {})
    assert set(places) <= visited(plan)
    assert "too_many_places" in plan.warnings
    assert len(plan.days) == 2


def test_dates_without_availability_still_give_a_plan(db, catalog):
    plan = assemble(db, catalog, request(start="2027-07-10", end="2027-07-13"), [KHATGAL], {})
    assert len(plan.days) == 4 and KHATGAL in visited(plan)
    assert all(d.stay is None for d in plan.days)
    assert "no_availability" in plan.warnings


def test_over_budget_is_flagged(db, catalog):
    plan = assemble(db, catalog, request(budget=1), [KHATGAL], {})
    assert plan.totals.budget_mnt == 1 and not plan.totals.within_budget
    assert "over_budget" in plan.warnings


def test_value_style_is_not_dearer_than_comfort(db, catalog):
    value = assemble(db, catalog, request(style="value"), [KHATGAL], {})
    comfort = assemble(db, catalog, request(style="comfort"), [KHATGAL], {})
    assert value.totals.stays_mnt <= comfort.totals.stays_mnt
    assert value.totals.stays_mnt > 0


def test_a_far_place_gets_an_overnight_on_the_way(db, catalog):
    plan = assemble(db, catalog, request(end="2026-10-09"), [OLGII], {})
    first_night = plan.days[0].to_place_id
    assert first_night not in (HUB, OLGII)  # Ulaanbaatar → Ölgii is ~1,700 km: not one day's drive
    assert OLGII in visited(plan)
    assert all(d.drive_time_min <= 16 * 60 for d in plan.days)


def test_events_on_the_day_near_the_place_are_attached(db, catalog):
    plan = assemble(db, catalog, request(start="2026-10-03", end="2026-10-05"), [KHATGAL], {KHATGAL: 2})
    day = next(d for d in plan.days if d.date == "2026-10-03")
    assert day.to_place_id == KHATGAL
    assert "event_khatgal_season_close_race" in day.event_ids


def test_no_named_place_still_gives_a_trip(db, catalog):
    plan = assemble(db, catalog, request(end="2026-10-05"), [], {})
    assert len(plan.days) == 3 and visited(plan) - {HUB}


def test_a_day_trip_has_no_nights(db, catalog):
    plan = assemble(db, catalog, request(start="2026-10-03", end="2026-10-03"), ["place_uran_togoo"], {})
    assert len(plan.days) == 1 and plan.days[0].stay is None and plan.warnings == []
