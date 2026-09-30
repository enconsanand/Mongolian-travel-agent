"""Build the itinerary from resolved places: order, nights, legs, stays, events, totals. No model involved.

Every place asked for is on the plan: it gets nights when there are enough, else it is visited on the way
(``via_place_ids``) and the plan says ``too_many_places``. Nights go, in order: one to each place (farthest
from Ulaanbaatar first when short), the traveller's ``nights_hint``, an overnight on the way for a leg over
nine hours' drive, then the rest round-robin. A stay is booked only if a unit is free on every night of the
block and the units sleep the whole group; prices are the per-night ``stay_availability`` prices that the
checkout will charge.
"""

from collections.abc import Mapping, Sequence
from datetime import timedelta
from math import ceil
from typing import Any

from pymongo.database import Database

from app.modules.orchestrator.catalog import HUB, Catalog, Json, km_between
from app.modules.orchestrator.types import Assembly, PlanDay, PlanRequest, PlanWarning, StayPick, Totals
from app.schemas.travel import StayAvailabilityDoc

STAY_RADIUS_KM = 60
EVENT_RADIUS_KM = 50
LONG_LEG_MIN = 9 * 60
ROAD_FACTOR = 1.3  # straight line → road distance where no stored route joins two places
SPEED_KMH = 60
TRANSIT_DETOUR = 1.25  # an overnight stop may lengthen the leg by at most this factor
DEFAULT_PLACES = 3  # a request that names no place gets up to this many


# ----------------------------------------------------------------------------- legs


def _leg(catalog: Catalog, a: str, b: str) -> tuple[int, int, str | None]:
    """(km, minutes, route id) from a to b: the shortest stored route either way, else an estimate."""
    if a == b:
        return 0, 0, None
    stored = [r for r in catalog.routes if {r["from_place_id"], r["to_place_id"]} == {a, b}]
    if stored:
        best = min(stored, key=lambda r: r["total_drive_time_min"])
        return best["total_distance_km"], best["total_drive_time_min"], best["_id"]
    km = km_between(catalog.places[a], catalog.places[b]) * ROAD_FACTOR
    return round(km), round(km / SPEED_KMH * 60), None


def _path(catalog: Catalog, stops: Sequence[str]) -> tuple[int, int, str | None]:
    legs = [_leg(catalog, a, b) for a, b in zip(stops, stops[1:], strict=False)]
    route_id = legs[0][2] if len(legs) == 1 else None
    return sum(km for km, _, _ in legs), sum(minutes for _, minutes, _ in legs), route_id


# ----------------------------------------------------------------------------- order and nights


def _default_places(catalog: Catalog, nights: int) -> list[str]:
    """Nothing named: the attractions with stays of their own that are nearest Ulaanbaatar."""
    hub = catalog.places[HUB]
    options = [pid for pid, p in catalog.places.items() if p["kind"] == "attraction" and catalog.stays_at(pid)]
    options.sort(key=lambda pid: km_between(hub, catalog.places[pid]))
    return options[: max(1, min(DEFAULT_PLACES, nights // 2))]


def _order(catalog: Catalog, places: Sequence[str]) -> list[str]:
    """Nearest neighbour from Ulaanbaatar."""
    left, order, here = list(places), [], catalog.places[HUB]
    while left:
        nearest = min(left, key=lambda pid: km_between(here, catalog.places[pid]))
        order.append(nearest)
        left.remove(nearest)
        here = catalog.places[nearest]
    return order


def _transit_place(catalog: Catalog, a: str, b: str) -> str | None:
    """A place with stays near it, roughly halfway between a and b and not far off the way."""
    pa, pb = catalog.places[a], catalog.places[b]
    direct = km_between(pa, pb)
    best: tuple[float, str] | None = None
    for pid, p in catalog.places.items():
        if pid in (a, b, HUB):
            continue
        da, db = km_between(pa, p), km_between(p, pb)
        if da + db > direct * TRANSIT_DETOUR or not catalog.stays_near(pid, STAY_RADIUS_KM):
            continue
        if best is None or max(da, db) < best[0]:
            best = (max(da, db), pid)
    return best[1] if best else None


def _allot_nights(
    catalog: Catalog, stops: list[str], total: int, hints: Mapping[str, int]
) -> tuple[list[tuple[str, int]], bool]:
    """(place, nights) in visiting order, with overnight stops inserted on long legs; and whether it was short."""
    hub = catalog.places[HUB]
    nights = dict.fromkeys(stops, 0)
    by_distance = sorted(stops, key=lambda pid: km_between(hub, catalog.places[pid]), reverse=True)
    for pid in by_distance[:total]:
        nights[pid] = 1
    left = total - sum(nights.values())
    short = len(stops) > max(total, 1)  # a day trip to one place is not short of nights

    for pid in stops:
        extra = min(max(hints.get(pid, 0) - nights[pid], 0), left) if nights[pid] else 0
        nights[pid] += extra
        left -= extra

    plan = [(pid, nights[pid]) for pid in stops]
    while left > 0:
        split = _split_longest_leg(catalog, plan)
        if split is None:
            break
        plan = split
        left -= 1

    targets = [i for i, (pid, n) in enumerate(plan) if n and pid in nights and pid not in hints]
    targets = targets or [i for i, (_, n) in enumerate(plan) if n]
    i = 0
    while left > 0 and targets:
        pid, n = plan[targets[i % len(targets)]]
        plan[targets[i % len(targets)]] = (pid, n + 1)
        left -= 1
        i += 1
    return plan, short


def _split_longest_leg(catalog: Catalog, plan: list[tuple[str, int]]) -> list[tuple[str, int]] | None:
    """Insert a one-night stop into the longest leg between nights over the limit, if one can be found."""
    sleeps = [(i, pid) for i, (pid, n) in enumerate(plan) if n]
    points = [(-1, HUB), *sleeps, (len(plan), HUB)]
    legs = []
    for (ia, a), (ib, b) in zip(points, points[1:], strict=False):
        minutes = _leg(catalog, a, b)[1]
        if minutes > LONG_LEG_MIN:
            legs.append((minutes, ib, a, b))
    for _, insert_at, a, b in sorted(legs, reverse=True):
        stop = _transit_place(catalog, a, b)
        if stop:
            return [*plan[:insert_at], (stop, 1), *plan[insert_at:]]
    return None


# ----------------------------------------------------------------------------- stays


def _open_in_season(stay: Json, days: Sequence[str]) -> bool:
    season = stay["season"]
    if season["year_round"]:
        return True
    return all(season["open_from"] <= d[5:] <= season["open_to"] for d in days)


def _nightly_prices(db: Database, stay_id: str, unit_type: str, days: Sequence[str], units: int) -> list[int] | None:
    rows = {
        r["date"]: r
        for r in db[StayAvailabilityDoc.collection].find(
            {"stay_id": stay_id, "unit_type": unit_type, "date": {"$in": list(days)}}
        )
    }
    if any(d not in rows or rows[d]["status"] != "open" or rows[d]["available"] < units for d in days):
        return None
    return [rows[d]["price_mnt"] for d in days]


def _stay_options(
    db: Database, catalog: Catalog, place_id: str, days: Sequence[str], guests: int
) -> list[tuple[float, Json, StayPick]]:
    options = []
    for km, stay in catalog.stays_near(place_id, STAY_RADIUS_KM):
        if not _open_in_season(stay, days):
            continue
        for unit in stay["units"]:
            units = ceil(guests / unit["beds_per_unit"])
            if units > unit["count"]:
                continue
            prices = _nightly_prices(db, stay["_id"], unit["unit_type"], days, units)
            if prices is None:
                continue
            qty = guests if unit["price_basis"] == "per_person" else units
            pick = StayPick(
                stay_id=stay["_id"],
                unit_type=unit["unit_type"],
                units=units,
                nights=len(days),
                total_mnt=qty * sum(prices),
            )
            options.append((km, stay, pick))
    return options


def _event_km(catalog: Catalog, stay: Json, days: Sequence[str]) -> float:
    near = [km_between(stay, e) for e in catalog.events if e["start_date"] <= days[-1] and e["end_date"] >= days[0]]
    return min(near, default=float("inf"))


def _choose_stay(
    catalog: Catalog, options: list[tuple[float, Json, StayPick]], style: str, days: Sequence[str]
) -> StayPick | None:
    if not options:
        return None

    def rank(option: tuple[float, Json, StayPick]) -> tuple[Any, ...]:
        km, stay, pick = option
        if style == "value":
            return (pick.total_mnt, km)
        if style == "culture":
            return (_event_km(catalog, stay, days), -stay["rating"], pick.total_mnt)
        return (stay["type"] not in ("hotel", "ger_camp"), -stay["rating"], -pick.total_mnt)

    return min(options, key=rank)[2]


# ----------------------------------------------------------------------------- assemble


def _events_on(catalog: Catalog, day: str, place_ids: Sequence[str]) -> list[str]:
    places = [catalog.places[p] for p in place_ids]
    return [
        e["_id"]
        for e in sorted(catalog.events, key=lambda e: e["start_date"])
        if e["start_date"] <= day <= e["end_date"] and any(km_between(p, e) <= EVENT_RADIUS_KM for p in places)
    ]


def assemble(
    db: Database, catalog: Catalog, request: PlanRequest, place_ids: Sequence[str], nights_hint: Mapping[str, int]
) -> Assembly:
    stops = _order(
        catalog, [p for p in dict.fromkeys(place_ids) if p != HUB] or _default_places(catalog, request.nights)
    )
    plan, short = _allot_nights(catalog, stops, request.nights, nights_hint)
    warnings: list[PlanWarning] = ["too_many_places"] if short else []

    dates = [(request.start_date + timedelta(days=i)).isoformat() for i in range(request.nights + 1)]
    days: list[PlanDay] = []
    here, via = HUB, []
    for pid, n in [*plan, (HUB, 0)]:
        if n == 0 and pid != HUB:
            via.append(pid)
            continue
        legs = [(here, pid)] + [(pid, pid)] * (max(n, 1) - 1) if pid != HUB else [(here, HUB)]
        for a, b in legs:
            km, minutes, route_id = _path(catalog, [a, *via, b])
            day_places = [*via, b]
            days.append(
                PlanDay(
                    day=len(days) + 1,
                    date=dates[len(days)],
                    from_place_id=a,
                    to_place_id=b,
                    via_place_ids=via,
                    route_id=route_id,
                    distance_km=km,
                    drive_time_min=minutes,
                    event_ids=_events_on(catalog, dates[len(days)], day_places),
                )
            )
            via = []
        here = pid

    stays_mnt = 0
    for start, (pid, n) in _blocks(days):
        nights = [d.date for d in days[start : start + n]]
        pick = _choose_stay(catalog, _stay_options(db, catalog, pid, nights, request.guests), request.style, nights)
        if pick is None:
            if "no_availability" not in warnings:
                warnings.append("no_availability")
            continue
        days[start].stay = pick
        for d in days[start : start + n]:
            d.stay_id = pick.stay_id
        stays_mnt += pick.total_mnt

    events = {e["_id"]: e for e in catalog.events}
    events_mnt = sum(events[eid]["ticket_price_mnt"] * request.guests for eid in {e for d in days for e in d.event_ids})
    total = stays_mnt + events_mnt
    within = request.budget_mnt is None or total <= request.budget_mnt
    if not within:
        warnings.append("over_budget")
    totals = Totals(
        stays_mnt=stays_mnt, events_mnt=events_mnt, total_mnt=total, budget_mnt=request.budget_mnt, within_budget=within
    )
    return Assembly(days=days, totals=totals, warnings=warnings)


def _blocks(days: Sequence[PlanDay]) -> list[tuple[int, tuple[str, int]]]:
    """(first day index, (place, nights)) for each run of nights at one place; the last day has no night."""
    blocks: list[tuple[int, tuple[str, int]]] = []
    for i, day in enumerate(days[:-1]):
        if blocks and day.from_place_id == day.to_place_id == blocks[-1][1][0]:
            start, (pid, n) = blocks[-1]
            blocks[-1] = (start, (pid, n + 1))
        else:
            blocks.append((i, (day.to_place_id, 1)))
    return blocks
