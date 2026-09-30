"""Planner service: a request becomes a stored proposal; changes make new versions; an accepted one becomes a trip.

    propose     read the request (planner model), resolve places, assemble, write the text (writer model)
    revise      the same from the original request plus every change so far → version + 1
    restay      same places and dates, stays picked again (a stay filled up before the traveller booked it)
    save_trip   the proposal as the signer's trip + itinerary version (booking happens in the caller)

A proposal lives 24 hours (TTL index on ``expires_at``). Once accepted it belongs to that user.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pymongo import ReturnDocument
from pymongo.database import Database

from app.llm import LLMError, ModelGateway
from app.models.user import User
from app.modules.orchestrator.assembler import assemble
from app.modules.orchestrator.catalog import HUB, Catalog
from app.modules.orchestrator.intent import extract_intent, place_chooser
from app.modules.orchestrator.resolver import candidates, resolve
from app.modules.orchestrator.types import Assembly, PlanDay, PlanRequest
from app.modules.orchestrator.writer import write
from app.schemas.travel import ItineraryVersionDoc, TripDoc

PROPOSALS = "plan_proposals"
TTL = timedelta(hours=24)

Json = dict[str, Any]


class ProposalNotFound(Exception):
    """No such proposal, it expired, or another user accepted it."""


class PlannerUnavailable(Exception):
    """The planner model could not read the request (unreachable, out of quota, or answered out of shape)."""


def _name(doc: Json, lang: str) -> str:
    return doc["name"][lang]


def _build(db: Database, gateway: ModelGateway, request: PlanRequest, changes: Sequence[str], now: datetime) -> Json:
    catalog = Catalog.load(db)
    try:
        intent = extract_intent(gateway, request, changes, now.date())
    except LLMError as exc:
        raise PlannerUnavailable(f"{exc.code}: {exc}") from exc

    avoided = {pid for name in intent.avoid_places for pid in candidates(name, catalog)}
    places = [
        p
        for p in resolve(intent.must_places, catalog, place_chooser(gateway, request.text))
        if p.place_id not in avoided
    ]
    by_query = {p.query: p.place_id for p in places if p.place_id}
    hints = {by_query[name]: n for name, n in intent.nights_hint.items() if name in by_query and n > 0}
    place_ids = [p.place_id for p in places if p.place_id]

    assembly = assemble(db, catalog, request, place_ids, hints)
    if any(p.status == "unresolved" for p in places):
        assembly.warnings.insert(0, "unresolved_place")
    summary = _write(gateway, request, assembly, catalog)
    return {
        "request": request.model_dump(mode="json"),
        "changes": list(changes),
        "intent": intent.model_dump(),
        "places": [p.model_dump() for p in places],
        "place_ids": place_ids,
        "nights_hint": hints,
        **_assembly(assembly, summary),
    }


def _write(gateway: ModelGateway, request: PlanRequest, assembly: Assembly, catalog: Catalog) -> str:
    """Put the writer's note on each day; return its summary."""
    lang = request.lang
    stays = {s["_id"]: _name(s, lang) for s in catalog.stays}
    events = {e["_id"]: _name(e, lang) for e in catalog.events}
    places = {pid: _name(p, lang) for pid, p in catalog.places.items()}
    writing = write(gateway, request, assembly.days, places, stays, events)
    assembly.days = [d.model_copy(update={"note": note}) for d, note in zip(assembly.days, writing.notes, strict=True)]
    return writing.summary


def _assembly(assembly: Assembly, summary: str) -> Json:
    return {
        "days": [d.model_dump() for d in assembly.days],
        "totals": assembly.totals.model_dump(),
        "warnings": list(dict.fromkeys(assembly.warnings)),
        "summary": summary,
    }


def _out(doc: Json) -> Json:
    out = {k: v for k, v in doc.items() if k not in ("_id", "expires_at")}
    return {"id": doc["_id"], **out, "expires_at": doc["expires_at"].isoformat()}


def _live(db: Database, proposal_id: str, now: datetime) -> Json:
    doc = db[PROPOSALS].find_one({"_id": proposal_id})
    if doc is None or doc["expires_at"] <= now:  # the TTL monitor runs once a minute
        raise ProposalNotFound(proposal_id)
    return doc


def propose(db: Database, gateway: ModelGateway, request: PlanRequest, now: datetime) -> Json:
    doc = {
        "_id": f"plan_{uuid4().hex[:16]}",
        "version": 1,
        **_build(db, gateway, request, [], now),
        "accepted": None,
        "created_at": now,
        "expires_at": now + TTL,
    }
    db[PROPOSALS].insert_one(doc)
    return _out(doc)


def get(db: Database, proposal_id: str, now: datetime) -> Json:
    return _out(_live(db, proposal_id, now))


def _replace(db: Database, doc: Json, fields: Json, now: datetime) -> Json:
    updated = db[PROPOSALS].find_one_and_update(
        {"_id": doc["_id"], "version": doc["version"]},
        {"$set": {**fields, "version": doc["version"] + 1, "expires_at": now + TTL}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:  # changed meanwhile: the other writer's version stands
        return _live(db, doc["_id"], now)
    return updated


def revise(db: Database, gateway: ModelGateway, proposal_id: str, change: str, now: datetime) -> Json:
    doc = _live(db, proposal_id, now)
    request = PlanRequest.model_validate(doc["request"])
    fields = _build(db, gateway, request, [*doc["changes"], change], now)
    return _out(_replace(db, doc, fields, now))


def restay(db: Database, proposal_id: str, now: datetime) -> Json:
    """Pick the stays again for the same places and dates; the written text stays as it was."""
    doc = _live(db, proposal_id, now)
    request = PlanRequest.model_validate(doc["request"])
    assembly = assemble(db, Catalog.load(db), request, doc["place_ids"], doc["nights_hint"])
    if "unresolved_place" in doc["warnings"]:
        assembly.warnings.insert(0, "unresolved_place")
    notes = [d["note"] for d in doc["days"]]
    assembly.days = [d.model_copy(update={"note": n}) for d, n in zip(assembly.days, notes, strict=True)]
    return _out(_replace(db, doc, _assembly(assembly, doc["summary"]), now))


def stay_requests(proposal: Json) -> list[Json]:
    """One booking line per stay block (the checkout's ``StayIn`` fields)."""
    guests = proposal["request"]["guests"]
    return [
        {
            "stay_id": d["stay"]["stay_id"],
            "unit_type": d["stay"]["unit_type"],
            "check_in": d["date"],
            "nights": d["stay"]["nights"],
            "units": d["stay"]["units"],
            "guests": guests,
        }
        for d in proposal["days"]
        if d["stay"]
    ]


# ----------------------------------------------------------------------------- accept → trip


def _title(catalog: Catalog, days: Sequence[PlanDay]) -> dict[str, str]:
    stops = list(dict.fromkeys(p for d in days for p in (*d.via_place_ids, d.to_place_id) if p != HUB))
    return {
        lang: ", ".join(catalog.places[p]["name"][lang] for p in stops[:4]) or "Ulaanbaatar" for lang in ("mn", "en")
    }


def _region(catalog: Catalog, days: Sequence[PlanDay]) -> str:
    counts: dict[str, int] = {}
    for d in days[:-1] or days:
        region = catalog.places[d.to_place_id]["region"]
        if region != "hub":
            counts[region] = counts.get(region, 0) + 1
    return max(counts, key=lambda r: counts[r]) if counts else "north"


def _itinerary(trip_id: str, version: int, doc: Json, now: datetime) -> Json:
    days = [
        {
            "day": d["day"],
            "date": d["date"],
            "from_place_id": d["from_place_id"],
            "to_place_id": d["to_place_id"],
            "route_id": d["route_id"],
            "stay_id": d["stay_id"],
            "event_ids": d["event_ids"] or None,
            "note": {"mn": d["note"], "en": d["note"]} if d["note"] else None,
        }
        for d in doc["days"]
    ]
    itinerary = ItineraryVersionDoc.model_validate(
        {
            "_id": f"itv_{trip_id}_v{version}",
            "trip_id": trip_id,
            "version": version,
            "created_at": now.isoformat(),
            "reason": "initial_plan" if version == 1 else "user_change",
            "change_request": "; ".join(doc["changes"]) or None,
            "agent_summary": {"mn": doc["summary"], "en": doc["summary"]} if doc["summary"] else None,
            "days": days,
        }
    )
    return itinerary.model_dump(by_alias=True, exclude={"is_mock"})


def save_trip(db: Database, proposal_id: str, user: User, now: datetime) -> str:
    """The proposal as the user's trip; accepting again reuses the trip, adding a version if it was revised."""
    doc = _live(db, proposal_id, now)
    accepted = doc.get("accepted")
    if accepted and accepted["user_id"] != user.id:
        raise ProposalNotFound(proposal_id)

    request = PlanRequest.model_validate(doc["request"])
    catalog = Catalog.load(db)
    days = [PlanDay.model_validate(d) for d in doc["days"]]
    trip_fields = {
        "title": _title(catalog, days),
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "region": _region(catalog, days),
        "party": {"adults": request.guests, "children": 0},
        "budget": {"limit_mnt": request.budget_mnt, "spent_mnt": 0} if request.budget_mnt is not None else None,
    }

    if accepted:
        trip_id = accepted["trip_id"]
        if accepted["version"] == doc["version"]:
            return trip_id
        trip = db[TripDoc.collection].find_one({"_id": trip_id})
        version = trip["current_version"] + 1 if trip else 1
        db["itinerary_versions"].insert_one(_itinerary(trip_id, version, doc, now))
        db[TripDoc.collection].update_one({"_id": trip_id}, {"$set": {**trip_fields, "current_version": version}})
    else:
        trip_id = f"trip_{uuid4().hex[:16]}"
        trip = TripDoc.model_validate(
            {
                "_id": trip_id,
                "user_id": user.id,
                "user": {
                    "name": user.full_name,
                    "lang": request.lang,
                    "phone": getattr(user, "phone", None) or "",
                },
                "current_version": 1,
                "status": "planned",
                "created_at": now.isoformat(),
                **trip_fields,
            }
        )
        db[TripDoc.collection].insert_one(trip.model_dump(by_alias=True, exclude={"is_mock"}))
        db["itinerary_versions"].insert_one(_itinerary(trip_id, 1, doc, now))

    db[PROPOSALS].update_one(
        {"_id": proposal_id},
        {"$set": {"accepted": {"user_id": user.id, "trip_id": trip_id, "version": doc["version"], "at": now}}},
    )
    return trip_id
