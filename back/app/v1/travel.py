"""Read API over the travel collections.

Every response is in the caller's language (``Accept-Language``, default Mongolian): bilingual
``{mn, en}`` fields are reduced to one string, and ``_id`` is returned as ``id``.
Catalog endpoints are public; ``/me/...`` endpoints only return the signed-in user's data.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.collection import Collection

from app.schemas import travel as s
from app.utils.i18n import Lang, get_lang, localize
from app.v1.deps import ActiveUser, DbSession

router = APIRouter()

LangDep = Annotated[Lang, Depends(get_lang)]
Limit = Annotated[int, Query(ge=1, le=500)]
RegionQ = Annotated[s.RegionOrHub | None, Query(description="north / west / east / south / hub")]
DateQ = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")]

Json = dict[str, Any]
Lng = Annotated[float, Query(ge=-180, le=180)]
Lat = Annotated[float, Query(ge=-90, le=90)]
RadiusKm = Annotated[float, Query(gt=0, le=500)]

# Contact details stay private on public endpoints; the booking flow reveals them after payment
_HIDDEN: dict[str, Json] = {
    "stays": {"owner.phone": 0},
    "shared_rides": {"posted_by.phone": 0},
    "drivers": {"phone": 0},
}


def _out(doc: Json, lang: Lang) -> Json:
    doc = localize(doc, lang)
    doc["id"] = doc.pop("_id")
    return doc


def _find(col: Collection, query: Json, lang: Lang, limit: int = 100, sort: list | None = None) -> list[Json]:
    cursor = col.find(query, _HIDDEN.get(col.name)).limit(limit)
    if sort:
        cursor = cursor.sort(sort)
    return [_out(doc, lang) for doc in cursor]


def _get(col: Collection, id: str, lang: Lang) -> Json:
    doc = col.find_one({"_id": id}, _HIDDEN.get(col.name))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{col.name} `{id}` not found")
    return _out(doc, lang)


def _near(lng: float | None, lat: float | None, radius_km: float) -> Json | None:
    """$nearSphere filter (results come back nearest first); needs the 2dsphere index."""
    if lng is None or lat is None:
        return None
    point = {"type": "Point", "coordinates": [lng, lat]}
    return {"$nearSphere": {"$geometry": point, "$maxDistance": radius_km * 1000}}


def _clean(query: Json) -> Json:
    return {k: v for k, v in query.items() if v is not None}


# ----------------------------------------------------------------------------- regions & places


@router.get("/regions", tags=["Travel - Catalog"])
def list_regions(db: DbSession, lang: LangDep) -> list[Json]:
    return _find(db[s.RegionDoc.collection], {}, lang, sort=[("_id", 1)])


@router.get("/regions/locate", tags=["Travel - Catalog"])
def locate_region(db: DbSession, lang: LangDep, lng: Lng, lat: Lat) -> Json:
    """Which of the 4 regions a point is in (e.g. the user's pin on the map)."""
    point = {"type": "Point", "coordinates": [lng, lat]}
    doc = db[s.RegionDoc.collection].find_one({"boundary": {"$geoIntersects": {"$geometry": point}}})
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Point is outside Mongolia's regions")
    return _out(doc, lang)


@router.get("/regions/{region_id}", tags=["Travel - Catalog"])
def get_region(db: DbSession, lang: LangDep, region_id: str) -> Json:
    return _get(db[s.RegionDoc.collection], region_id, lang)


@router.get("/places", tags=["Travel - Catalog"])
def list_places(
    db: DbSession,
    lang: LangDep,
    region: RegionQ = None,
    kind: str | None = None,
    lng: Lng | None = None,
    lat: Lat | None = None,
    radius_km: RadiusKm = 50,
    limit: Limit = 100,
) -> list[Json]:
    query = _clean({"region": region, "kind": kind, "location": _near(lng, lat, radius_km)})
    return _find(db[s.PlaceDoc.collection], query, lang, limit)


@router.get("/places/{place_id}", tags=["Travel - Catalog"])
def get_place(db: DbSession, lang: LangDep, place_id: str) -> Json:
    return _get(db[s.PlaceDoc.collection], place_id, lang)


# ----------------------------------------------------------------------------- stays


@router.get("/stays", tags=["Travel - Stays"])
def list_stays(
    db: DbSession,
    lang: LangDep,
    region: RegionQ = None,
    type: str | None = None,
    place_id: str | None = None,
    lng: Lng | None = None,
    lat: Lat | None = None,
    radius_km: RadiusKm = 30,
    date: DateQ = None,
    limit: Limit = 100,
) -> list[Json]:
    """Stays, optionally near a point; with ``date`` only stays that have a free unit that night."""
    query = _clean({"region": region, "type": type, "place_id": place_id, "location": _near(lng, lat, radius_km)})
    if date:
        free = db[s.StayAvailabilityDoc.collection].distinct(
            "stay_id", {"date": date, "status": "open", "available": {"$gt": 0}}
        )
        query["_id"] = {"$in": free}
    return _find(db[s.StayDoc.collection], query, lang, limit)


@router.get("/stays/{stay_id}", tags=["Travel - Stays"])
def get_stay(db: DbSession, lang: LangDep, stay_id: str, date_from: DateQ = None, date_to: DateQ = None) -> Json:
    """One stay with its cancellation policy and availability (optionally for a date range)."""
    stay = _get(db[s.StayDoc.collection], stay_id, lang)
    policy = db[s.CancellationPolicyDoc.collection].find_one({"_id": stay["cancellation_policy_id"]})
    stay["cancellation_policy"] = _out(policy, lang) if policy else None
    dates = _clean({"$gte": date_from, "$lte": date_to})
    query: Json = {"stay_id": stay_id, **({"date": dates} if dates else {})}
    stay["availability"] = _find(
        db[s.StayAvailabilityDoc.collection], query, lang, limit=500, sort=[("date", 1), ("unit_type", 1)]
    )
    return stay


# ----------------------------------------------------------------------------- routes & events


@router.get("/routes", tags=["Travel - Catalog"])
def list_routes(
    db: DbSession,
    lang: LangDep,
    region: RegionQ = None,
    from_place_id: str | None = None,
    to_place_id: str | None = None,
    limit: Limit = 100,
) -> list[Json]:
    query = _clean({"region": region, "from_place_id": from_place_id, "to_place_id": to_place_id})
    return _find(db[s.RouteDoc.collection], query, lang, limit)


@router.get("/routes/{route_id}", tags=["Travel - Catalog"])
def get_route(db: DbSession, lang: LangDep, route_id: str) -> Json:
    return _get(db[s.RouteDoc.collection], route_id, lang)


@router.get("/events", tags=["Travel - Catalog"])
def list_events(
    db: DbSession,
    lang: LangDep,
    region: RegionQ = None,
    category: str | None = None,
    date_from: DateQ = None,
    date_to: DateQ = None,
    limit: Limit = 100,
) -> list[Json]:
    """Events overlapping [date_from, date_to]."""
    query = _clean(
        {
            "region": region,
            "category": category,
            "end_date": {"$gte": date_from} if date_from else None,
            "start_date": {"$lte": date_to} if date_to else None,
        }
    )
    return _find(db[s.EventDoc.collection], query, lang, limit, sort=[("start_date", 1)])


@router.get("/cancellation-policies", tags=["Travel - Catalog"])
def list_cancellation_policies(db: DbSession, lang: LangDep) -> list[Json]:
    return _find(db[s.CancellationPolicyDoc.collection], {}, lang)


# ----------------------------------------------------------------------------- transport


@router.get("/transport/schedules", tags=["Travel - Transport"])
def list_schedules(
    db: DbSession,
    lang: LangDep,
    mode: str | None = None,
    region: RegionQ = None,
    from_place_id: str | None = None,
    to_place_id: str | None = None,
    limit: Limit = 100,
) -> list[Json]:
    """Bus, train, flight and shared-van timetables. Trains also match on intermediate stops."""
    query = _clean({"mode": mode, "region": region, "from_place_id": from_place_id})
    if to_place_id:
        query["$or"] = [{"to_place_id": to_place_id}, {"stops.place_id": to_place_id}]
    return _find(db[s.TransportScheduleDoc.collection], query, lang, limit)


@router.get("/transport/availability", tags=["Travel - Transport"])
def list_transport_availability(
    db: DbSession,
    lang: LangDep,
    schedule_id: str | None = None,
    date: DateQ = None,
    seat_class: str | None = None,
    only_open: bool = True,
    limit: Limit = 200,
) -> list[Json]:
    query = _clean({"schedule_id": schedule_id, "date": date, "seat_class": seat_class})
    if only_open:
        query["seats_left"] = {"$gt": 0}
    return _find(
        db[s.TransportAvailabilityDoc.collection], query, lang, limit, sort=[("date", 1), ("departure_time", 1)]
    )


@router.get("/shared-rides", tags=["Travel - Transport"])
def list_shared_rides(
    db: DbSession,
    lang: LangDep,
    region: RegionQ = None,
    from_place_id: str | None = None,
    to_place_id: str | None = None,
    date: DateQ = None,
    only_bookable: bool = True,
    limit: Limit = 100,
) -> list[Json]:
    query = _clean({"region": region, "from_place_id": from_place_id, "to_place_id": to_place_id, "date": date})
    if only_bookable:
        query["bookable"] = True
    return _find(db[s.SharedRideDoc.collection], query, lang, limit, sort=[("date", 1), ("depart_time", 1)])


@router.get("/vehicles", tags=["Travel - Transport"])
def list_vehicles(
    db: DbSession,
    lang: LangDep,
    region: RegionQ = None,
    rental_mode: Annotated[str | None, Query(description="with_driver / self_drive")] = None,
    offroad: bool | None = None,
    date: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$", description="free on this day")] = None,
    limit: Limit = 100,
) -> list[Json]:
    """Rentable vehicles (with a driver or self-drive), each with its driver if it has one."""
    query = _clean({"region": region, "rental.mode": rental_mode, "offroad_capable": offroad})
    query["rental"] = {"$ne": None}
    if date:
        free = db[s.VehicleAvailabilityDoc.collection].distinct("vehicle_id", {"date": date, "status": "available"})
        query["_id"] = {"$in": free}
    vehicles = _find(db[s.VehicleDoc.collection], query, lang, limit)
    driver_ids = [v["driver_id"] for v in vehicles if v.get("driver_id")]
    driver_col = db[s.DriverDoc.collection]
    drivers = {d["_id"]: _out(d, lang) for d in driver_col.find({"_id": {"$in": driver_ids}}, _HIDDEN["drivers"])}
    for v in vehicles:
        v["driver"] = drivers.get(v.get("driver_id") or "")
    return vehicles


@router.get("/drivers", tags=["Travel - Transport"])
def list_drivers(
    db: DbSession, lang: LangDep, region: RegionQ = None, language: str | None = None, limit: Limit = 100
) -> list[Json]:
    query = _clean({"regions_served": region, "languages": language})
    return _find(db[s.DriverDoc.collection], query, lang, limit)


@router.get("/config/fuel", tags=["Travel - Catalog"])
def get_fuel_prices(db: DbSession, lang: LangDep) -> Json:
    return _get(db[s.AppConfigDoc.collection], "fuel_prices", lang)


# ----------------------------------------------------------------------------- the signed-in user's trips


@router.get("/me/trips", tags=["Travel - My trips"])
def list_my_trips(db: DbSession, lang: LangDep, user: ActiveUser) -> list[Json]:
    return _find(db[s.TripDoc.collection], {"user_id": user.id}, lang, sort=[("start_date", 1)])


@router.get("/me/trips/{trip_id}", tags=["Travel - My trips"])
def get_my_trip(db: DbSession, lang: LangDep, user: ActiveUser, trip_id: str) -> Json:
    """Trip with its current itinerary, bookings, quotes, payments and refunds."""
    trip_doc = db[s.TripDoc.collection].find_one({"_id": trip_id, "user_id": user.id})
    if trip_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"trip `{trip_id}` not found")
    trip = _out(trip_doc, lang)
    by_trip = {"trip_id": trip_id}
    itinerary = db[s.ItineraryVersionDoc.collection].find_one({**by_trip, "version": trip["current_version"]})
    trip["itinerary"] = _out(itinerary, lang) if itinerary else None
    trip["bookings"] = _find(db[s.BookingDoc.collection], by_trip, lang)
    trip["quotes"] = _find(db[s.QuoteDoc.collection], by_trip, lang)
    trip["payments"] = _find(db[s.PaymentDoc.collection], by_trip, lang)
    trip["refunds"] = _find(db[s.RefundDoc.collection], by_trip, lang)
    return trip


@router.get("/me/payments", tags=["Travel - My trips"])
def list_my_payments(
    db: DbSession,
    lang: LangDep,
    user: ActiveUser,
    payment_status: Annotated[str | None, Query(alias="status")] = None,
) -> list[Json]:
    query = _clean({"user_id": user.id, "status": payment_status})
    return _find(db[s.PaymentDoc.collection], query, lang)
