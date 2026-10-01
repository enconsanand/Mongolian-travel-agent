"""The reference data a plan is built from, read once per request (a few hundred small documents)."""

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any

from pymongo.database import Database

from app.schemas.travel import EventDoc, PlaceDoc, RegionDoc, RouteDoc, StayDoc

Json = dict[str, Any]

HUB = "place_ub"


def km_between(a: Json, b: Json) -> float:
    """Great-circle distance between two documents' GeoJSON ``location`` points."""
    (lng1, lat1), (lng2, lat2) = a["location"]["coordinates"], b["location"]["coordinates"]
    dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
    h = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


@dataclass(frozen=True)
class Catalog:
    places: dict[str, Json]
    regions: list[Json]
    stays: list[Json]
    routes: list[Json]
    events: list[Json]

    @classmethod
    def load(cls, db: Database) -> "Catalog":
        """Load the reference collections once per request.

        Heavy fields the planner does not need (photo galleries, road geometry, region
        polygons, owner phones) are left in Mongo; stay and place pickers that need photos
        read them through ``filters.stays_within`` / a direct find.
        """
        return cls(
            places={p["_id"]: p for p in db[PlaceDoc.collection].find({}, {"images": 0})},
            regions=list(db[RegionDoc.collection].find({}, {"boundary": 0})),
            stays=list(db[StayDoc.collection].find({}, {"owner.phone": 0, "images": 0, "reviews": 0})),
            routes=list(db[RouteDoc.collection].find({}, {"geometry": 0, "segments": 0})),
            events=list(db[EventDoc.collection].find({}, {"images": 0})),
        )

    def stays_at(self, place_id: str) -> list[Json]:
        return [s for s in self.stays if s["place_id"] == place_id]

    def stays_near(self, place_id: str, radius_km: float) -> list[tuple[float, Json]]:
        """Stays within ``radius_km`` of the place, nearest first."""
        place = self.places[place_id]
        near = [(km_between(place, s), s) for s in self.stays]
        return sorted(((km, s) for km, s in near if km <= radius_km), key=lambda pair: pair[0])
