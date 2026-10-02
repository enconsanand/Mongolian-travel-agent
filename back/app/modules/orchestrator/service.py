"""Planner service: a request becomes a stored proposal; changes make new versions; an accepted one becomes a trip.

    propose     read the request (planner model), resolve places, assemble, write the text (writer model)
    revise      the same from the original request plus every change so far → version + 1
    restay      same places and dates, stays picked again (a stay filled up before the traveller booked it)
    save_trip   the proposal as the signer's trip + itinerary version (booking happens in the caller)

A proposal lives 24 hours (TTL index on ``expires_at``). Once accepted it belongs to that user.
"""

from collections.abc import Callable, Sequence
from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import sha256
from secrets import compare_digest, token_urlsafe
from typing import Any
from uuid import uuid4

from pymongo import ReturnDocument
from pymongo.database import Database

from app.llm import LLMError, ModelGateway, configured_gateway
from app.models.user import User
from app.modules.orchestrator.assembler import assemble, assemble_blocks, overnight_blocks, stay_options, trade_nights
from app.modules.orchestrator.catalog import HUB, Catalog
from app.modules.orchestrator.intent import extract_intent, place_chooser
from app.modules.orchestrator.resolver import candidates, resolve
from app.modules.orchestrator.scenic import choose_itinerary, is_specific, mentioned, named_words, theme_of, wants_far
from app.modules.orchestrator.types import Assembly, PlanDay, PlanRequest, ResolvedPlace, TripFit, TripIntent
from app.modules.orchestrator.writer import write
from app.oyu import OyuError, configured_oyu
from app.schemas.travel import ItineraryVersionDoc, TripDoc
from app.utils.i18n import Lang, localize

PROPOSALS = "plan_proposals"
TTL = timedelta(hours=24)

Json = dict[str, Any]


class ProposalNotFound(Exception):
    """No such proposal, it expired, or another user accepted it."""


class PlannerUnavailable(Exception):
    """The planner model could not read the request (unreachable, out of quota, or answered out of shape)."""


def gateway() -> ModelGateway:
    """The configured model gateway (a FastAPI dependency; tests override it)."""
    return configured_gateway()


def _name(doc: Json, lang: str) -> str:
    return doc["name"][lang]


def _resolve_stops(
    catalog: Catalog,
    gateway: ModelGateway,
    request: PlanRequest,
    changes: Sequence[str],
    intent: TripIntent,
) -> list[ResolvedPlace]:
    """Named places win; otherwise a prepared scenic route from landscape / distance words."""
    avoided = {pid for name in intent.avoid_places for pid in candidates(name, catalog)}
    said = " ".join([request.text, *changes])
    choose = place_chooser(gateway, request.text)

    asked = [name for name in intent.must_places if is_specific(name)]
    read = [p for p in resolve(asked, catalog, choose) if p.place_id not in avoided]
    specific = [p for p in read if p.place_id and mentioned(p.query, said)]
    if specific:
        return specific + [p for p in read if p.status == "unresolved"]

    named = [
        p for p in resolve(named_words(said, catalog), catalog, choose) if p.place_id and p.place_id not in avoided
    ]
    if named:
        return named

    stops = choose_itinerary(
        catalog,
        theme=theme_of(said, intent.landscape),
        far=wants_far(said),
        nights=request.nights,
        avoid=avoided,
    )
    return [ResolvedPlace(query=catalog.places[pid]["name"]["mn"], place_id=pid, status="included") for pid in stops]


Translate = Callable[[str, str, str], str]


def _english_bridge(request: PlanRequest) -> Translate | None:
    """Orchu between an English traveller and the Mongolian oyu models.

    When the writer runs on oyu (a Mongolian model) and the request is in English, the request and changes are
    read in Mongolian and the text the traveller reads is written in Mongolian, then translated back. A failed
    translation keeps the original text, so the plan still comes out.
    """
    from app.core.config import settings

    client = configured_oyu()
    if request.lang != "en" or client is None or not settings.LLM_WRITER.strip().startswith("oyu"):
        return None

    def translate(text: str, source: str, target: str) -> str:
        try:
            return client.translate(text, source=source, target=target)
        except OyuError:
            return text

    return translate


def _build(db: Database, gateway: ModelGateway, request: PlanRequest, changes: Sequence[str], now: datetime) -> Json:
    catalog = Catalog.load(db)
    bridge = _english_bridge(request)
    reading = request
    if bridge:
        reading = request.model_copy(update={"text": bridge(request.text, "en", "mn"), "lang": "mn"})
        changes = [bridge(change, "en", "mn") for change in changes]
    try:
        intent = extract_intent(gateway, reading, changes, now.date())
    except LLMError as exc:
        raise PlannerUnavailable(f"{exc.code}: {exc}") from exc

    places = _resolve_stops(catalog, gateway, reading, changes, intent)
    by_query = {p.query: p.place_id for p in places if p.place_id}
    hints = {by_query[name]: n for name, n in intent.nights_hint.items() if name in by_query and n > 0}
    place_ids = [p.place_id for p in places if p.place_id]

    assembly = assemble(db, catalog, request, place_ids, hints)
    if any(p.status == "unresolved" for p in places):
        assembly.warnings.insert(0, "unresolved_place")
    missing = [p.query for p in places if p.status == "unresolved"]
    summary = _write(gateway, request, assembly, catalog, missing, bridge)
    if not assembly.fit.feasible:
        summary = _unfit_summary(request, assembly.fit, catalog)
    return {
        "request": request.model_dump(mode="json"),
        "changes": list(changes),
        "intent": intent.model_dump(),
        "places": [p.model_dump() for p in places],
        "place_ids": place_ids,
        "nights_hint": hints,
        **_assembly(assembly, summary),
    }


def _unfit_summary(request: PlanRequest, fit: TripFit, catalog: Catalog) -> str:
    """The dates are too short. This sentence is fixed from the drive time; the model does not write it."""
    place = _name(catalog.places[fit.place_id or ""], request.lang) if fit.place_id else ""
    hours = max(1, round(fit.drive_min / 60))
    if request.lang == "mn":
        return (
            f"{place} хүртэл нэг талдаа ойролцоогоор {hours} цаг явна. "
            f"{request.nights} хоногт очиж, хоноод, буцаж ирэх боломжгүй — замд өнгөрнө. "
            f"Хамгийн багадаа {fit.min_nights} хоног хэрэгтэй."
        )
    return (
        f"{place} is about {hours} hours' drive one way. "
        f"{request.nights} nights is not enough to get there, stay, and come back — the days would be spent driving. "
        f"At least {fit.min_nights} nights are needed."
    )


def _write(
    gateway: ModelGateway,
    request: PlanRequest,
    assembly: Assembly,
    catalog: Catalog,
    missing: Sequence[str],
    bridge: Translate | None = None,
) -> str:
    """Put the writer's note on each day; return its summary (written in Mongolian and translated when bridged)."""
    writing_request = request.model_copy(update={"lang": "mn"}) if bridge else request
    lang = writing_request.lang
    stays = {s["_id"]: _name(s, lang) for s in catalog.stays}
    events = {e["_id"]: _name(e, lang) for e in catalog.events}
    places = {pid: _name(p, lang) for pid, p in catalog.places.items()}
    unfit = "" if assembly.fit.feasible else _unfit_summary(writing_request, assembly.fit, catalog)
    writing = write(gateway, writing_request, assembly.days, places, stays, events, missing, unfit)
    notes, summary = list(writing.notes), writing.summary
    if bridge:
        notes = [bridge(note, "mn", "en") if note else note for note in notes]
        summary = bridge(summary, "mn", "en")
    assembly.days = [d.model_copy(update={"note": note}) for d, note in zip(assembly.days, notes, strict=True)]
    return summary


def _assembly(assembly: Assembly, summary: str) -> Json:
    return {
        "days": [d.model_dump() for d in assembly.days],
        "totals": assembly.totals.model_dump(),
        "warnings": list(dict.fromkeys(assembly.warnings)),
        "fit": assembly.fit.model_dump(),
        "summary": summary,
    }


def _out(doc: Json) -> Json:
    """The public shape: anyone with the id may read a proposal, so who accepted it stays private."""
    out = {
        k: v
        for k, v in doc.items()
        if k not in ("_id", "accepted", "saved", "owner_id", "claim_hash", "created_at", "expires_at")
    }
    return {
        "id": doc["_id"],
        **out,
        "accepted": bool(doc.get("accepted")),
        "created_at": doc["created_at"].isoformat(),
        "expires_at": doc["expires_at"].isoformat(),
    }


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
    claim = token_urlsafe(32)
    doc["claim_hash"] = sha256(claim.encode()).hexdigest()
    db[PROPOSALS].insert_one(doc)
    return {**_out(doc), "claim_token": claim}


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


class PlanEditRejected(Exception):
    """The day change does not fit: no such stop, or a stop would be left with no night."""


def adjust_nights(db: Database, proposal_id: str, place_id: str, delta: int, now: datetime) -> Json:
    """Move one night along the route the traveller already has. Does not call a model or reorder stops."""
    doc = _live(db, proposal_id, now)
    days = [PlanDay.model_validate(d) for d in doc["days"]]
    blocks = [pair for _, pair in overnight_blocks(days)]
    moved = trade_nights(blocks, place_id, delta)
    if moved is None:
        raise PlanEditRejected(place_id)
    request = PlanRequest.model_validate(doc["request"])
    catalog = Catalog.load(db)
    prefer = {d.to_place_id: d.stay.stay_id for d in days if d.stay}
    assembly = assemble_blocks(db, catalog, request, moved, prefer)
    _keep_notes(assembly.days, days, catalog, request.lang)
    fields = _assembly(assembly, doc["summary"])
    fields["nights_hint"] = dict(moved)
    return _out(_replace(db, doc, fields, now))


def _public_images(stay: Json, limit: int = 4) -> list[Json]:
    slim = []
    for img in (stay.get("images") or [])[:limit]:
        slim.append(
            {
                "url": img.get("url"),
                "author": img.get("author") or "",
                "license": img.get("license") or "",
                "source": img.get("source") or "",
            }
        )
    return [img for img in slim if img["url"]]


def stay_choices(db: Database, proposal_id: str, place_id: str, now: datetime, lang: Lang) -> list[Json]:
    """Stays the database can actually book for this stop's nights."""
    doc = _live(db, proposal_id, now)
    days = [PlanDay.model_validate(d) for d in doc["days"]]
    block = next((item for item in overnight_blocks(days) if item[1][0] == place_id), None)
    if block is None:
        raise PlanEditRejected(place_id)
    start, (_, n) = block
    request = PlanRequest.model_validate(doc["request"])
    catalog = Catalog.load(db)
    nights = [d.date for d in days[start : start + n]]
    current_stay = days[start].stay
    current = current_stay.stay_id if current_stay else None
    choices = []
    cheapest: dict[str, tuple[float, Json, Any]] = {}
    for km, stay, pick in stay_options(db, catalog, place_id, nights, request.guests):
        prev = cheapest.get(stay["_id"])
        if prev is None or pick.total_mnt < prev[2].total_mnt:
            cheapest[stay["_id"]] = (km, stay, pick)
    media = {
        s["_id"]: s
        for s in db["stays"].find(
            {"_id": {"$in": list(cheapest)}},
            {"images": 1, "cover_image_url": 1, "reviews": 1},
        )
    }
    for km, stay, pick in cheapest.values():
        unit = next(u for u in stay["units"] if u["unit_type"] == pick.unit_type)
        photo = media.get(stay["_id"], stay)
        choices.append(
            {
                "id": stay["_id"],
                "name": _name(stay, lang),
                "type": stay["type"],
                "rating": stay["rating"],
                "reviews_count": stay["reviews_count"],
                "reviews": localize(photo.get("reviews") or [], lang)[:2],
                "cover_image_url": photo.get("cover_image_url") or stay.get("cover_image_url"),
                "images": _public_images(photo),
                "meals": bool(unit["meals_included"]),
                "total_mnt": pick.total_mnt,
                "km": round(km, 1),
                "selected": stay["_id"] == current,
            }
        )
    return choices


def swap_stay(db: Database, proposal_id: str, place_id: str, stay_id: str, now: datetime) -> Json:
    """Use another stay from the database for one stop. The route and the other days stay as they are."""
    doc = _live(db, proposal_id, now)
    days = [PlanDay.model_validate(d) for d in doc["days"]]
    block = next((item for item in overnight_blocks(days) if item[1][0] == place_id), None)
    if block is None:
        raise PlanEditRejected(place_id)
    start, (_, n) = block
    request = PlanRequest.model_validate(doc["request"])
    catalog = Catalog.load(db)
    nights = [d.date for d in days[start : start + n]]
    match = next(
        (pick for _, _, pick in stay_options(db, catalog, place_id, nights, request.guests) if pick.stay_id == stay_id),
        None,
    )
    if match is None:
        raise PlanEditRejected(stay_id)
    previous = days[start].stay
    old = previous.total_mnt if previous else 0
    days[start].stay = match
    for day in days[start : start + n]:
        day.stay_id = match.stay_id
    totals = dict(doc["totals"])
    totals["stays_mnt"] = totals["stays_mnt"] - old + match.total_mnt
    totals["total_mnt"] = totals["stays_mnt"] + totals["events_mnt"]
    totals["within_budget"] = totals["budget_mnt"] is None or totals["total_mnt"] <= totals["budget_mnt"]
    warnings = [w for w in doc["warnings"] if w != "over_budget"]
    if not totals["within_budget"]:
        warnings.append("over_budget")
    fields = {"days": [d.model_dump() for d in days], "totals": totals, "warnings": warnings}
    return _out(_replace(db, doc, fields, now))


def _keep_notes(days: list[PlanDay], previous: Sequence[PlanDay], catalog: Catalog, lang: str) -> None:
    by_place = {d.to_place_id: d.note for d in previous if d.note and d.from_place_id == d.to_place_id}
    for day in days:
        same = next(
            (
                old.note
                for old in previous
                if old.date == day.date
                and old.to_place_id == day.to_place_id
                and old.from_place_id == day.from_place_id
            ),
            None,
        )
        if same:
            day.note = same
            continue
        if day.from_place_id == day.to_place_id and day.to_place_id in by_place:
            day.note = by_place[day.to_place_id]
            continue
        place = _name(catalog.places[day.to_place_id], lang)
        if day.from_place_id == day.to_place_id:
            day.note = f"{place}-д хононо." if lang == "mn" else f"Stay in {place}."
        else:
            start = _name(catalog.places[day.from_place_id], lang)
            day.note = f"{start} → {place}."


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


def save_trip(db: Database, proposal_id: str, user: User, now: datetime, *, accept: bool = True) -> str:
    """The proposal as the user's trip; accepting again reuses the trip, adding a version if it was revised."""
    doc = _live(db, proposal_id, now)
    accepted = doc.get("saved") or doc.get("accepted")
    if accepted and accepted["user_id"] != user.id:
        raise ProposalNotFound(proposal_id)

    claimed = db[PROPOSALS].update_one(
        {"_id": proposal_id, "$or": [{"owner_id": {"$exists": False}}, {"owner_id": user.id}]},
        {"$set": {"owner_id": user.id}},
    )
    if not claimed.matched_count:
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
        trip = db[TripDoc.collection].find_one({"_id": trip_id})
        if trip and trip["status"] != "planned":
            # A held/paid booking is an immutable purchase, not the next draft revision.
            return trip_id
        version = doc["version"]
        itinerary = _itinerary(trip_id, version, doc, now)
        db["itinerary_versions"].update_one({"_id": itinerary["_id"]}, {"$setOnInsert": itinerary}, upsert=True)
        db[TripDoc.collection].update_one({"_id": trip_id}, {"$set": {**trip_fields, "current_version": version}})
    else:
        trip_id = f"trip_{proposal_id.removeprefix('plan_')}"
        trip = TripDoc.model_validate(
            {
                "_id": trip_id,
                "user_id": user.id,
                "user": {
                    "name": user.full_name,
                    "lang": request.lang,
                    "phone": getattr(user, "phone", None) or "",
                },
                "current_version": doc["version"],
                "status": "planned",
                "created_at": now.isoformat(),
                **trip_fields,
            }
        )
        stored_trip = trip.model_dump(by_alias=True, exclude={"is_mock"})
        db[TripDoc.collection].update_one({"_id": trip_id}, {"$setOnInsert": stored_trip}, upsert=True)
        itinerary = _itinerary(trip_id, doc["version"], doc, now)
        db["itinerary_versions"].update_one({"_id": itinerary["_id"]}, {"$setOnInsert": itinerary}, upsert=True)

    marker = {"user_id": user.id, "trip_id": trip_id, "version": doc["version"], "at": now}
    fields = {"saved": marker, **({"accepted": marker} if accept else {})}
    db[PROPOSALS].update_one({"_id": proposal_id}, {"$set": fields})
    snapshot = {k: v for k, v in doc.items() if k not in ("claim_hash", "saved", "accepted")}
    db["saved_plans"].update_one(
        {"_id": trip_id},
        {"$set": {"user_id": user.id, "proposal_id": proposal_id, "snapshot": snapshot}},
        upsert=True,
    )
    return trip_id


def authorize_edit(db: Database, proposal_id: str, user: User | None, claim: str | None, now: datetime) -> None:
    doc = _live(db, proposal_id, now)
    if doc.get("owner_id") and (not user or user.id != doc["owner_id"]):
        raise ProposalNotFound(proposal_id)
    owner = doc.get("saved") or doc.get("accepted")
    if owner:
        if not user or owner["user_id"] != user.id:
            raise ProposalNotFound(proposal_id)
        trip = db["trips"].find_one({"_id": owner["trip_id"]})
        if trip and trip["status"] != "planned":
            raise PlanEditRejected("This trip already has a checkout")
    elif doc.get("claim_hash") and not compare_digest(doc["claim_hash"], sha256((claim or "").encode()).hexdigest()):
        raise ProposalNotFound(proposal_id)


def resume_trip(db: Database, trip_id: str, user: User, now: datetime) -> str:
    saved = db["saved_plans"].find_one({"_id": trip_id, "user_id": user.id})
    trip = db["trips"].find_one({"_id": trip_id, "user_id": user.id})
    if not saved or not trip:
        raise ProposalNotFound(trip_id)
    if trip["status"] != "planned":
        raise PlanEditRejected("This trip already has a checkout")
    doc = deepcopy(saved["snapshot"])
    existing = db[PROPOSALS].find_one({"_id": doc["_id"]})
    if existing and existing["expires_at"] > now:
        return doc["_id"]
    marker = {"user_id": user.id, "trip_id": trip_id, "version": doc["version"], "at": now}
    doc.update(saved=marker, accepted=None, expires_at=now + TTL)
    db[PROPOSALS].replace_one({"_id": doc["_id"]}, doc, upsert=True)
    # Price and availability are refreshed before the traveller approves a checkout.
    restay(db, doc["_id"], now)
    save_trip(db, doc["_id"], user, now, accept=False)
    return doc["_id"]
