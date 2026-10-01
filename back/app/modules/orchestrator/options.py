"""Route choices for the request screen, read from the Mongo catalog. No invented stays.

The typed text (galig included) is matched against places. Overnight stops are the places with a stay on the
stored road from Ulaanbaatar to that place. Each choice lists only stays stored for that place.
"""

import heapq
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from math import ceil
from typing import Any

from pymongo.database import Database

from app.modules.orchestrator.assembler import MAX_DRIVE_DAY_MIN, leg, stay_options
from app.modules.orchestrator.catalog import HUB, Catalog, Json
from app.modules.orchestrator.resolver import candidates, is_trip_phrase, norm, starts_word
from app.utils.galig import latin_to_cyrillic
from app.utils.i18n import Lang

_KIND = {
    "ger_camp": {"mn": "Гэр бааз", "en": "Ger camp"},
    "guesthouse": {"mn": "Зочны байр", "en": "Guesthouse"},
    "hotel": {"mn": "Зочид буудал", "en": "Hotel"},
    "house": {"mn": "Байшин", "en": "House"},
}


def search_options(
    db: Database,
    text: str,
    *,
    nights: int,
    guests: int,
    budget_mnt: int | None,
    lang: Lang,
    start: date | None = None,
    nightly_min: int | None = None,
    nightly_max: int | None = None,
) -> Json:
    catalog = Catalog.load(db)
    destination = _destination(text, catalog)
    if destination is None:
        return {"feasible": True, "variants": []}

    drive_min = leg(catalog, HUB, destination)[1]
    drive_days = max(1, ceil(drive_min / MAX_DRIVE_DAY_MIN))
    min_nights = 2 * (drive_days - 1) + 1
    place = catalog.places[destination]
    header = {
        "feasible": nights >= min_nights,
        "min_nights": min_nights,
        "drive_min": drive_min,
        "place": _label(place["name"], lang),
        "variants": [],
    }
    if nights < min_nights:
        return header

    path = _road(catalog, destination)
    stays_on_road = [pid for pid in path if pid != HUB and catalog.stays_at(pid)]
    if destination not in stays_on_road and catalog.stays_at(destination):
        stays_on_road.append(destination)
    if not stays_on_road or stays_on_road[-1] != destination:
        return header

    middles = stays_on_road[:-1]
    plans: list[list[tuple[str, int]]] = []
    if middles:
        plans.append([(middles[0], 1), (destination, nights - 1)])
    if len(middles) >= 2 and nights >= 4:
        plans.append([(middles[0], 1), (middles[1], 1), (destination, nights - 2)])
    if middles and middles[-1] != middles[0] and nights >= 4:
        plans.append([(middles[-1], 2), (destination, nights - 2)])
    if not plans:
        plans.append([(destination, nights)])

    seen: set[tuple[tuple[str, int], ...]] = set()
    variants: list[Json] = []
    for plan in plans:
        key = tuple(plan)
        if key in seen or any(n < 1 for _, n in plan):
            continue
        seen.add(key)
        variants.append(
            _variant(
                db,
                catalog,
                plan,
                guests,
                budget_mnt,
                lang,
                start=start,
                nightly_min=nightly_min,
                nightly_max=nightly_max,
                recommended=not variants,
            )
        )
    header["variants"] = variants
    return header


def _destination(text: str, catalog: Catalog) -> str | None:
    written = latin_to_cyrillic(text.strip())
    words = [w for w in norm(written).split() if not w.isdigit() and not is_trip_phrase(w)]
    found: list[str] = []
    for query in [written, *words]:
        found = [pid for pid in candidates(query, catalog) if pid != HUB]
        if found:
            break
    if not found:
        return None
    named = [
        pid
        for pid in found
        if any(starts_word(word, norm(alias)) for word in words for alias in _aliases(catalog.places[pid]))
    ]
    pool = named or found
    with_stay = [pid for pid in pool if catalog.stays_at(pid)]
    pool = with_stay or pool
    return max(pool, key=lambda pid: (leg(catalog, HUB, pid)[1], pid))


def _aliases(place: Json) -> list[str]:
    return [place["name"]["mn"], place["name"]["en"], *place.get("aliases", [])]


def _road(catalog: Catalog, destination: str) -> list[str]:
    """Places along stored routes from Ulaanbaatar to ``destination``, or just the two ends."""
    graph: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for route in catalog.routes:
        points = [pid for pid in route.get("waypoint_place_ids") or [] if pid in catalog.places]
        if len(points) < 2:
            points = [pid for pid in (route["from_place_id"], route["to_place_id"]) if pid in catalog.places]
        for left, right in zip(points, points[1:], strict=False):
            minutes = leg(catalog, left, right)[1]
            graph[left].append((right, minutes))
            graph[right].append((left, minutes))

    dist = {HUB: 0}
    prev: dict[str, str] = {}
    heap = [(0, HUB)]
    while heap:
        so_far, place_id = heapq.heappop(heap)
        if so_far != dist.get(place_id):
            continue
        if place_id == destination:
            break
        for nxt, minutes in graph.get(place_id, []):
            total = so_far + minutes
            if total < dist.get(nxt, 10**12):
                dist[nxt] = total
                prev[nxt] = place_id
                heapq.heappush(heap, (total, nxt))
    if destination not in prev and destination != HUB:
        return [HUB, destination]
    path = [destination]
    while path[-1] != HUB:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def _per_person(unit: Json) -> int:
    if unit["price_basis"] == "per_person":
        return int(unit["price_mnt"])
    return max(1, round(int(unit["price_mnt"]) / int(unit["beds_per_unit"])))


def _review_snippet(stay: Json, lang: Lang) -> str | None:
    reviews = stay.get("reviews") or []
    if not reviews:
        return None
    text = reviews[0].get("text") or {}
    if isinstance(text, str):
        return text
    return text.get(lang) or text.get("mn") or None


def _media(db: Database, stay_ids: Sequence[str]) -> dict[str, Json]:
    if not stay_ids:
        return {}
    return {
        s["_id"]: s
        for s in db["stays"].find(
            {"_id": {"$in": list(stay_ids)}},
            {"images": 1, "cover_image_url": 1, "reviews": 1},
        )
    }


def _stay_row(stay: Json, lang: Lang, *, price: int, km: float, media: Json | None = None) -> Json:
    unit = min(stay["units"], key=_per_person)
    meals = "Хоолтой" if lang == "mn" else "Meals included"
    shower = "Халуун ус" if lang == "mn" else "Hot shower"
    bits = [meals] if unit.get("meals_included") else []
    if "hot_shower" in stay.get("amenities", []):
        bits.append(shower)
    if km > 1:
        bits.append(f"{km:.0f} км" if lang == "mn" else f"{km:.0f} km away")
    kind = _KIND.get(stay["type"], {"mn": stay["type"], "en": stay["type"]})
    photo = media or stay
    return {
        "id": stay["_id"],
        "name": _label(stay["name"], lang),
        "kind": kind[lang],
        "blurb": " · ".join(bits),
        "pricePerNight": price,
        "coverImageUrl": photo.get("cover_image_url") or stay.get("cover_image_url"),
        "images": [img["url"] for img in (photo.get("images") or [])[:3] if img.get("url")],
        "rating": stay.get("rating"),
        "reviewsCount": stay.get("reviews_count"),
        "review": _review_snippet(photo, lang),
    }


def _variant(
    db: Database,
    catalog: Catalog,
    plan: list[tuple[str, int]],
    guests: int,
    budget_mnt: int | None,
    lang: Lang,
    *,
    start: date | None,
    nightly_min: int | None,
    nightly_max: int | None,
    recommended: bool,
) -> Json:
    stops: list[Json] = []
    cursor = start
    for place_id, nights in plan:
        place = catalog.places[place_id]
        if cursor is None:
            local = catalog.stays_at(place_id)
            photos = _media(db, [s["_id"] for s in local])
            rows = [
                _stay_row(
                    stay,
                    lang,
                    price=_per_person(min(stay["units"], key=_per_person)),
                    km=0,
                    media=photos.get(stay["_id"]),
                )
                for stay in local
            ]
        else:
            days = [(cursor + timedelta(days=i)).isoformat() for i in range(nights)]
            rows = []
            cheapest: dict[str, tuple[float, Json, Any]] = {}
            for km, stay, pick in stay_options(db, catalog, place_id, days, guests):
                prev = cheapest.get(stay["_id"])
                if prev is None or pick.total_mnt < prev[2].total_mnt:
                    cheapest[stay["_id"]] = (km, stay, pick)
            photos = _media(db, list(cheapest))
            for km, stay, pick in cheapest.values():
                per_night = max(1, round(pick.total_mnt / pick.nights / guests))
                rows.append(_stay_row(stay, lang, price=per_night, km=km, media=photos.get(stay["_id"])))
            cursor += timedelta(days=nights)
        stays = sorted(_priced(rows, nightly_min, nightly_max), key=lambda row: row["pricePerNight"])
        stops.append({"id": place_id, "place": _label(place["name"], lang), "nights": nights, "stays": stays})
    estimate = sum(stop["nights"] * stop["stays"][0]["pricePerNight"] * guests for stop in stops if stop["stays"])
    names = ", ".join(f"{stop['place']} {stop['nights']} {'хоног' if lang == 'mn' else 'nights'}" for stop in stops)
    title = stops[-1]["place"] if len(stops) == 1 else " · ".join(stop["place"] for stop in stops)
    return {
        "id": "-".join(stop["id"] for stop in stops),
        "title": title,
        "summary": f"{names}.",
        "recommended": recommended,
        "estimateMnt": estimate,
        "overBudget": budget_mnt is not None and estimate > budget_mnt,
        "stops": stops,
    }


def _priced(rows: list[Json], nightly_min: int | None, nightly_max: int | None) -> list[Json]:
    """Keep stays whose per-person nightly price sits inside the optional band."""
    if nightly_min is None and nightly_max is None:
        return rows
    if nightly_min is not None and nightly_max is not None and nightly_min > nightly_max:
        return rows
    kept = []
    for row in rows:
        price = row["pricePerNight"]
        if nightly_min is not None and price < nightly_min:
            continue
        if nightly_max is not None and price > nightly_max:
            continue
        kept.append(row)
    return kept


def _label(text: dict[str, Any], lang: Lang) -> str:
    return str(text.get(lang) or text.get("mn") or "")
