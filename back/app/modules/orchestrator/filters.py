"""Stay and event filters that MongoDB runs.

Bookable rooms come from one aggregation on ``stay_availability``: a unit is kept only when
every requested night is open. Nearby stays use the 2dsphere index (``$geoNear``). Events
for a day use the date indexes (``start_date`` / ``end_date``).

The distance cutoff stays the great-circle check in ``km_between``, so a stay on the radius
boundary is chosen the same way as before. mongomock cannot build a 2dsphere index, so the
radius search uses the in-memory catalog there; the availability aggregation runs in both.
"""

from collections.abc import Sequence
from typing import Any

from pymongo.database import Database
from pymongo.errors import OperationFailure

from app.modules.orchestrator.catalog import Catalog, Json, km_between
from app.schemas.travel import EventDoc, StayAvailabilityDoc, StayDoc

# $geoNear's metre radius is slightly wider than ``km_between``; the exact cutoff is applied after.
_GEO_SLACK = 1.02


def _memory_radius(db: Database) -> bool:
    return type(db.client).__module__.startswith("mongomock")


def stays_within(db: Database, catalog: Catalog, place_id: str, radius_km: float) -> list[tuple[float, Json]]:
    """Stays within ``radius_km`` of the place, nearest first."""
    place = catalog.places[place_id]
    if _memory_radius(db):
        return catalog.stays_near(place_id, radius_km)
    try:
        docs = db[StayDoc.collection].aggregate(
            [
                {
                    "$geoNear": {
                        "near": place["location"],
                        "key": "location",
                        "distanceField": "distance_m",
                        "maxDistance": radius_km * 1000 * _GEO_SLACK,
                        "spherical": True,
                    }
                },
                {
                    "$project": {
                        "owner.phone": 0,
                        "distance_m": 0,
                        "images": 0,
                        "reviews": 0,
                    }
                },
            ]
        )
    except OperationFailure:
        return catalog.stays_near(place_id, radius_km)
    near = []
    for stay in docs:
        km = km_between(place, stay)
        if km <= radius_km:
            near.append((km, stay))
    near.sort(key=lambda pair: pair[0])
    return near


def open_unit_nights(
    db: Database, stay_ids: Sequence[str], days: Sequence[str]
) -> dict[tuple[str, str], dict[str, Json]]:
    """``(stay_id, unit_type) → {date: row}`` for units that are open on every day.

    A missing or closed night drops the unit. ``available`` is left for the caller, because
    how many units the group needs depends on beds per unit.
    """
    if not stay_ids or not days:
        return {}
    wanted = list(days)
    pipeline: list[dict[str, Any]] = [
        {
            "$match": {
                "stay_id": {"$in": list(stay_ids)},
                "date": {"$in": wanted},
                "status": "open",
            }
        },
        {
            "$group": {
                "_id": {"stay_id": "$stay_id", "unit_type": "$unit_type"},
                "dates": {"$addToSet": "$date"},
                "rows": {"$push": {"date": "$date", "available": "$available", "price_mnt": "$price_mnt"}},
            }
        },
        {"$match": {"dates": {"$all": wanted}}},
    ]
    found: dict[tuple[str, str], dict[str, Json]] = {}
    for row in db[StayAvailabilityDoc.collection].aggregate(pipeline):
        key = (row["_id"]["stay_id"], row["_id"]["unit_type"])
        found[key] = {item["date"]: item for item in row["rows"]}
    return found


def stay_ids_free_every_night(db: Database, days: Sequence[str]) -> list[str]:
    """Stays with at least one unit open and free on every day. Two unit types on one night count once."""
    if not days:
        return []
    wanted = list(days)
    pipeline: list[dict[str, Any]] = [
        {"$match": {"date": {"$in": wanted}, "status": "open", "available": {"$gt": 0}}},
        {"$group": {"_id": {"stay_id": "$stay_id", "date": "$date"}}},
        {"$group": {"_id": "$_id.stay_id", "nights": {"$sum": 1}}},
        {"$match": {"nights": len(wanted)}},
    ]
    return [row["_id"] for row in db[StayAvailabilityDoc.collection].aggregate(pipeline)]


def events_on_date(db: Database, day: str) -> list[Json]:
    """Events whose [start_date, end_date] covers ``day``, earliest first."""
    return list(
        db[EventDoc.collection]
        .find({"start_date": {"$lte": day}, "end_date": {"$gte": day}})
        .sort([("start_date", 1), ("_id", 1)])
    )


def within_km(lng: float, lat: float, radius_km: float) -> Json:
    """``$geoWithin`` circle. Radius is radians on the same 6371 km sphere as ``km_between``."""
    return {"$geoWithin": {"$centerSphere": [[lng, lat], radius_km / 6371]}}
