"""The way of travel for a whole trip: priced four ways, then picked by request, style, budget and group size."""

from datetime import date

import mongomock
import pytest

from app.modules.orchestrator.transport import choose_transport
from app.modules.orchestrator.types import PlanDay, PlanRequest

WEEK = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def schedule(_id: str, mode: str, a: str, b: str, price: int) -> dict:
    return {
        "_id": _id,
        "mode": mode,
        "operator": "Op",
        "from_place_id": a,
        "to_place_id": b,
        "days_of_week": WEEK,
        "departure_times": ["08:00"],
        "duration_min": 600,
        "price_mnt": price,
    }


def car(_id: str, mode: str, seats: int, per_day: int, **rental) -> dict:
    return {
        "_id": _id,
        "model": _id,
        "seats": seats,
        "fuel_type": "ai92",
        "fuel_l_per_100km": 10,
        "base_place_id": "place_ub",
        "operator": "Rent",
        "rental": {"mode": mode, "price_per_day_mnt": per_day, **rental},
    }


@pytest.fixture
def db():
    database = mongomock.MongoClient(tz_aware=True)["test_transport"]
    database["app_config"].insert_one({"_id": "fuel_prices", "price_per_liter_mnt": {"ai92": 2000}})
    database["transport_schedules"].insert_many(
        [
            schedule("bus_out", "bus", "place_ub", "place_murun", 58000),
            schedule("bus_back", "bus", "place_murun", "place_ub", 58000),
            schedule("fly_out", "flight", "place_ub", "place_murun", 360000),
        ]
    )
    database["vehicles"].insert_many(
        [
            car("driver_suv", "with_driver", 5, 300000),
            car("driver_van", "with_driver", 9, 350000),
            car("rent_suv", "self_drive", 5, 150000, insurance_per_day_mnt=20000, km_included_per_day=1000),
        ]
    )
    return database


def trip(style="comfort", budget=None, guests=2) -> PlanRequest:
    return PlanRequest(
        guests=guests, start_date=date(2026, 10, 5), end_date=date(2026, 10, 7), style=style, budget_mnt=budget
    )


def days() -> list[PlanDay]:
    move = {"distance_km": 700, "drive_time_min": 660}
    return [
        PlanDay(day=1, date="2026-10-05", from_place_id="place_ub", to_place_id="place_murun", **move),
        PlanDay(day=2, date="2026-10-06", from_place_id="place_murun", to_place_id="place_murun"),
        PlanDay(day=3, date="2026-10-07", from_place_id="place_murun", to_place_id="place_ub", **move),
    ]


def test_comfort_without_budget_takes_a_car_with_driver(db):
    plan = days()
    travel = choose_transport(db, trip(), plan, 0, "")
    # 3 days * 300,000 + fuel 1400 km * 10 L/100 km * 2000
    assert (travel.chosen.kind, travel.chosen.vehicle, travel.reason) == ("with_driver", "driver_suv", "style")
    assert travel.chosen.total_mnt == 900000 + 280000
    assert [d.transport.mode if d.transport else None for d in plan] == ["car", None, "car"]
    assert {o.kind for o in travel.alternatives} == {"public", "self_drive", "own_car"}


def test_a_big_group_needs_the_van_or_two_cars(db):
    travel = choose_transport(db, trip(guests=8), days(), 0, "")
    assert travel.chosen.vehicle == "driver_van" and travel.chosen.vehicles == 1


def test_a_tight_budget_moves_down_the_list_then_to_the_cheapest(db):
    travel = choose_transport(db, trip(budget=1_100_000), days(), 300000, "")
    assert (travel.chosen.kind, travel.reason) == ("self_drive", "budget")  # 3 * 170,000 + 280,000 = 790,000

    plan = days()
    travel = choose_transport(db, trip(budget=400000), plan, 300000, "")
    assert (travel.chosen.kind, travel.reason) == ("public", "over_budget")
    assert plan[0].transport.mode == "bus" and plan[0].transport.total_mnt == 2 * 58000


def test_value_takes_the_cheapest_and_an_asked_way_wins(db):
    assert choose_transport(db, trip("value"), days(), 0, "").chosen.kind == "public"
    travel = choose_transport(db, trip("value"), days(), 0, "own_car")
    assert (travel.chosen.kind, travel.reason) == ("own_car", "asked")

    plan = days()
    choose_transport(db, trip(), plan, 0, "flight")
    assert plan[0].transport.mode == "flight" and plan[2].transport.mode == "bus"  # no flight back


def test_no_public_option_when_a_travel_day_has_no_timetable(db):
    db["transport_schedules"].delete_one({"_id": "bus_back"})
    travel = choose_transport(db, trip("value"), days(), 0, "")
    assert travel.chosen.kind != "public" and "public" not in {o.kind for o in travel.alternatives}


def test_a_booked_car_is_not_offered(db):
    db["vehicle_availability"].insert_one({"vehicle_id": "driver_suv", "date": "2026-10-06", "status": "booked"})
    assert choose_transport(db, trip(), days(), 0, "").chosen.vehicle == "driver_van"
