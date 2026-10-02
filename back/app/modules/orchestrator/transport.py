"""How the group gets around for the whole trip, and what it costs. No model involved.

Four ways are priced for every plan:

- ``public``: a bus, train, flight or shared van on every travel day (a timetable that runs that weekday with
  seats for the whole group); not offered when one travel day has none.
- ``with_driver``: a car or van with a driver from Ulaanbaatar for every day of the trip, plus fuel.
- ``self_drive``: a rental car from Ulaanbaatar (day rate, insurance, extra km) plus fuel.
- ``own_car``: the group's own car, fuel only. Offered when asked for, never assumed.

Cars are counted from seats against the group size. The choice: what the traveller asked for where it exists;
else the first option in the style's order that fits what is left of the budget after stays and events (value:
the cheapest); else, over budget, the cheapest.
"""

from collections.abc import Sequence
from datetime import date
from math import ceil

from pymongo.database import Database

from app.modules.orchestrator.types import (
    DayTransport,
    PlanDay,
    PlanRequest,
    Style,
    TransportKind,
    TransportOption,
    TransportPlan,
)
from app.schemas.travel import (
    AppConfigDoc,
    TransportAvailabilityDoc,
    TransportScheduleDoc,
    VehicleAvailabilityDoc,
    VehicleDoc,
)

OWN_CAR_SEATS = 5
OWN_CAR_L_PER_100_KM = 12
DEFAULT_FUEL_MNT = {"ai92": 2350, "ai95": 2950, "diesel": 2700}
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
HUB = "place_ub"

# Which way of travel each style tries first; own_car only when the traveller asks for it
STYLE_ORDER: dict[Style, tuple[TransportKind, ...]] = {
    "comfort": ("with_driver", "self_drive", "public"),
    "culture": ("with_driver", "public", "self_drive"),
    "value": (),  # the cheapest
}
# What the traveller may ask for (TripIntent.transport) and the option it means
ASKED: dict[str, TransportKind] = {
    "own_car": "own_car",
    "rental": "self_drive",
    "driver": "with_driver",
    "bus": "public",
    "train": "public",
    "flight": "public",
}


def _fuel_prices(db: Database) -> dict[str, int]:
    config = db[AppConfigDoc.collection].find_one({"_id": "fuel_prices"}) or {}
    return {**DEFAULT_FUEL_MNT, **config.get("price_per_liter_mnt", {})}


def _moving(days: Sequence[PlanDay]) -> list[PlanDay]:
    return [day for day in days if day.from_place_id != day.to_place_id and day.distance_km > 0]


# ----------------------------------------------------------------------------- public transport


def _departure(db: Database, schedule: dict, day: str, guests: int) -> str | None:
    """The first departure with seats for the whole group; the timetable's first one when nothing is known."""
    rows = list(
        db[TransportAvailabilityDoc.collection]
        .find({"schedule_id": schedule["_id"], "date": day, "status": "open"})
        .sort("departure_time", 1)
    )
    if not rows:
        return (schedule.get("departure_times") or [None])[0] or ""
    return next((row["departure_time"] for row in rows if row["seats_left"] >= guests), None)


def _tickets(db: Database, day: PlanDay, guests: int, mode: str) -> DayTransport | None:
    """The cheapest timetabled way for one travel day (of ``mode`` when it runs); trains also run back."""
    weekday = WEEKDAYS[date.fromisoformat(day.date).weekday()]
    a, b = day.from_place_id, day.to_place_id
    found = db[TransportScheduleDoc.collection].find(
        {
            "$or": [{"from_place_id": a, "to_place_id": b}, {"from_place_id": b, "to_place_id": a, "mode": "train"}],
            "days_of_week": weekday,
        }
    )
    options = []
    for schedule in found:
        departure = _departure(db, schedule, day.date, guests)
        if departure is None:
            continue
        options.append(
            DayTransport(
                mode=schedule["mode"],
                schedule_id=schedule["_id"],
                operator=schedule["operator"],
                departure_time=departure or None,
                duration_min=schedule["duration_min"],
                total_mnt=schedule["price_mnt"] * guests,
            )
        )
    asked = [option for option in options if option.mode == mode]
    return min(asked or options, key=lambda option: option.total_mnt, default=None)


def _public(db: Database, days: Sequence[PlanDay], guests: int, mode: str) -> tuple[TransportOption, list] | None:
    legs = [(day, _tickets(db, day, guests, mode)) for day in _moving(days)]
    if not legs or any(ticket is None for _, ticket in legs):
        return None
    tickets = sum(ticket.total_mnt for _, ticket in legs if ticket)
    operators = ", ".join(dict.fromkeys(ticket.operator or "" for _, ticket in legs if ticket))
    option = TransportOption(kind="public", operator=operators, days=len(days), tickets_mnt=tickets, total_mnt=tickets)
    return option, legs


# ----------------------------------------------------------------------------- cars


def _free_every_day(db: Database, vehicle_id: str, dates: Sequence[str]) -> bool:
    """No booked or maintenance day on the trip (days without a row are taken as free)."""
    return not db[VehicleAvailabilityDoc.collection].find_one(
        {"vehicle_id": vehicle_id, "date": {"$in": list(dates)}, "status": {"$ne": "available"}}
    )


def _rentals(db: Database, days: Sequence[PlanDay], guests: int, fuel: dict[str, int]) -> list[TransportOption]:
    """The cheapest car of each rental mode that starts in Ulaanbaatar and is free for the whole trip."""
    km = sum(day.distance_km for day in days)
    dates = [day.date for day in days]
    best: dict[str, TransportOption] = {}
    for car in db[VehicleDoc.collection].find({"rental": {"$ne": None}, "base_place_id": HUB}):
        rental = car["rental"]
        if not _free_every_day(db, car["_id"], dates):
            continue
        count = ceil(guests / car["seats"])
        rent = (rental["price_per_day_mnt"] + (rental.get("insurance_per_day_mnt") or 0)) * len(days)
        if rental.get("km_included_per_day"):
            extra_km = max(0, km - rental["km_included_per_day"] * len(days))
            rent += extra_km * (rental.get("price_per_extra_km_mnt") or 0)
        litres = km * car["fuel_l_per_100km"] / 100
        fuel_mnt = round(litres * fuel[car["fuel_type"]]) * count
        option = TransportOption(
            kind=rental["mode"],
            vehicle=car["model"],
            operator=car.get("operator"),
            vehicles=count,
            days=len(days),
            rent_mnt=rent * count,
            fuel_mnt=fuel_mnt,
            total_mnt=rent * count + fuel_mnt,
        )
        kept = best.get(option.kind)
        if kept is None or option.total_mnt < kept.total_mnt:
            best[option.kind] = option
    return list(best.values())


def _own_car(days: Sequence[PlanDay], guests: int, fuel: dict[str, int]) -> TransportOption:
    km = sum(day.distance_km for day in days)
    count = ceil(guests / OWN_CAR_SEATS)
    fuel_mnt = round(km * OWN_CAR_L_PER_100_KM / 100 * fuel["ai92"]) * count
    return TransportOption(kind="own_car", vehicles=count, days=len(days), fuel_mnt=fuel_mnt, total_mnt=fuel_mnt)


# ----------------------------------------------------------------------------- choice


def _pick(
    options: dict[TransportKind, TransportOption], request: PlanRequest, left: int | None, wanted: str
) -> tuple[TransportOption, str]:
    asked = ASKED.get(wanted)
    if asked and asked in options:
        return options[asked], "asked"
    automatic = [option for kind, option in options.items() if kind != "own_car"] or list(options.values())
    cheapest = min(automatic, key=lambda option: option.total_mnt)
    order = [options[kind] for kind in STYLE_ORDER[request.style] if kind in options]
    if wanted == "cheapest" or not order:
        return cheapest, "style" if left is None or cheapest.total_mnt <= left else "over_budget"
    if left is None:
        return order[0], "style"
    fitting = [option for option in order if option.total_mnt <= left]
    if fitting:
        return fitting[0], "style" if fitting[0] is order[0] else "budget"
    return cheapest, "over_budget"


def choose_transport(
    db: Database, request: PlanRequest, days: Sequence[PlanDay], spent_mnt: int, wanted: str
) -> TransportPlan | None:
    """Price every way of travel, pick one, and set ``transport`` on each travel day. ``spent_mnt``: stays, events."""
    for day in days:
        day.transport = None
    if not _moving(days):
        return None
    fuel = _fuel_prices(db)
    options: dict[TransportKind, TransportOption] = {o.kind: o for o in _rentals(db, days, request.guests, fuel)}
    public = _public(db, days, request.guests, wanted if wanted in ("bus", "train", "flight") else "")
    if public:
        options["public"] = public[0]
    options["own_car"] = _own_car(days, request.guests, fuel)

    left = None if request.budget_mnt is None else request.budget_mnt - spent_mnt
    chosen, reason = _pick(options, request, left, wanted)

    if chosen.kind == "public" and public:
        for day, ticket in public[1]:
            day.transport = ticket
    else:
        km = sum(day.distance_km for day in days) or 1
        for day in _moving(days):
            day.transport = DayTransport(
                mode="car",
                operator=chosen.vehicle,
                duration_min=day.drive_time_min,
                total_mnt=round(chosen.fuel_mnt * day.distance_km / km),
            )
    alternatives = sorted((o for o in options.values() if o is not chosen), key=lambda option: option.total_mnt)
    return TransportPlan(chosen=chosen, reason=reason, alternatives=alternatives)  # type: ignore[arg-type]
