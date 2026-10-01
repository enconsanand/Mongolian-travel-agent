"""Trip planner API: a request becomes a structured itinerary; changes make new versions; accepting holds its stays.

Planning is public; accepting needs a signed-in user and returns the checkout the trusted surface approves and
pays. Responses carry a ``catalog`` of the places, stays and events the plan refers to, in the caller's
language (``Accept-Language``), so the page needs no other calls.
"""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.api.v1.deps import ActiveUser, DbSession, OptionalUser
from app.api.v1.payments import Now
from app.api.v1.travel import LangDep
from app.models.user import User
from app.modules import booking
from app.modules.orchestrator import options, service
from app.modules.orchestrator.assembler import events_on
from app.modules.orchestrator.catalog import Catalog
from app.modules.orchestrator.intent import SlotRead, read_slot
from app.modules.orchestrator.types import PlanRequest
from app.utils.i18n import Lang, localize

router = APIRouter()

Gateway = Annotated[Any, Depends(service.gateway)]
Json = dict[str, Any]

_BOOKING_STATUS = {
    "trip_not_found": status.HTTP_404_NOT_FOUND,
    "stay_not_found": status.HTTP_409_CONFLICT,
    "unit_not_offered": status.HTTP_409_CONFLICT,
    "too_many_guests": status.HTTP_409_CONFLICT,
    "unavailable": status.HTTP_409_CONFLICT,
}


class ChangeIn(BaseModel):
    change: str = Field(min_length=1, max_length=500)


class ReadIn(BaseModel):
    slot: Literal["place", "guests", "dates", "budget"]
    text: str = Field(min_length=1, max_length=500)


class NightIn(BaseModel):
    place_id: str = Field(min_length=1, max_length=80)
    delta: Literal[1, -1]


class StayPickIn(BaseModel):
    place_id: str = Field(min_length=1, max_length=80)
    stay_id: str = Field(min_length=1, max_length=80)


def _error(code: int, name: str, **extra: Any) -> HTTPException:
    return HTTPException(code, detail={"code": name, **extra})


def _not_found() -> HTTPException:
    return _error(status.HTTP_404_NOT_FOUND, "proposal_not_found")


def _edit_access(
    proposal_id: str,
    db: DbSession,
    user: OptionalUser,
    now: Now,
    claim: Annotated[str | None, Header(alias="X-Plan-Token")] = None,
) -> User | None:
    try:
        service.authorize_edit(db, proposal_id, user, claim, now)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    except service.PlanEditRejected as exc:
        raise _error(409, "trip_locked") from exc
    return user


Editor = Annotated[User | None, Depends(_edit_access)]


def _saved_view(db: DbSession, proposal: Json, lang: Lang, user: User | None, now: Now) -> Json:
    if user:
        service.save_trip(db, proposal["id"], user, now, accept=False)
    return _view(db, proposal, lang)


def _with_nearby_events(db: DbSession, proposal: Json) -> Json:
    """Events near that day's places, including ones added after the plan was saved.

    This is display only: the stored totals and the stay booking are left as they were.
    """
    catalog = Catalog.load(db)
    days = []
    for day in proposal["days"]:
        places = [day["to_place_id"], *(day.get("via_place_ids") or [])]
        found = events_on(db, catalog, day["date"], places)
        days.append({**day, "event_ids": list(dict.fromkeys([*(day.get("event_ids") or []), *found]))})
    return {**proposal, "days": days}


def _view(db: DbSession, proposal: Json, lang: Lang) -> Json:
    """The proposal plus display data for every place, stay and event it names."""
    proposal = _with_nearby_events(db, proposal)
    days = proposal["days"]
    place_ids = {p for d in days for p in (d["from_place_id"], d["to_place_id"], *d["via_place_ids"])}
    place_ids |= {p["place_id"] for p in proposal["places"] if p["place_id"]}
    stay_ids = {d["stay_id"] for d in days if d["stay_id"]}
    event_ids = {e for d in days for e in d["event_ids"]}

    def by_id(collection: str, ids: set[str], fields: list[str]) -> Json:
        projection = dict.fromkeys(fields, 1)
        return {
            doc.pop("_id"): localize(doc, lang) for doc in db[collection].find({"_id": {"$in": list(ids)}}, projection)
        }

    catalog = {
        "places": by_id("places", place_ids, ["name", "aimag", "region", "kind"]),
        "stays": by_id(
            "stays",
            stay_ids,
            [
                "name",
                "type",
                "aimag",
                "rating",
                "reviews_count",
                "reviews",
                "cover_image_url",
                "images",
                "check_in",
                "check_out",
            ],
        ),
        "events": by_id(
            "events",
            event_ids,
            [
                "name",
                "description",
                "category",
                "start_date",
                "end_date",
                "ticket_price_mnt",
                "cover_image_url",
                "phone",
                "url",
            ],
        ),
    }
    for stay in catalog["stays"].values():
        stay["images"] = stay.get("images", [])[:4]
        stay["reviews"] = (stay.get("reviews") or [])[:2]
    return {**proposal, "catalog": catalog}


@router.get("/planner/options", tags=["Planner"])
def planner_options(
    db: DbSession,
    lang: LangDep,
    text: str = "",
    nights: int = 1,
    guests: int = 1,
    budget_mnt: int | None = None,
    start_date: date | None = None,
    nightly_min: int | None = None,
    nightly_max: int | None = None,
) -> Json:
    """Places and stays from the database for the request text, galig included."""
    nights = min(max(nights, 0), 30)
    guests = min(max(guests, 1), 60)
    if budget_mnt is not None and budget_mnt < 0:
        budget_mnt = None
    if nightly_min is not None and nightly_min < 0:
        nightly_min = None
    if nightly_max is not None and nightly_max < 0:
        nightly_max = None
    return options.search_options(
        db,
        text[:2000],
        nights=nights,
        guests=guests,
        budget_mnt=budget_mnt,
        lang=lang,
        start=start_date,
        nightly_min=nightly_min,
        nightly_max=nightly_max,
    )


@router.post("/planner/read", tags=["Planner"])
def read_reply(body: ReadIn, gateway: Gateway, now: Now) -> SlotRead:
    """Read one free-text chat answer into a phrase the trip form already accepts."""
    return read_slot(gateway, body.slot, body.text, now.date())


@router.post("/planner/proposals", tags=["Planner"], status_code=status.HTTP_201_CREATED)
def create_proposal(
    body: PlanRequest, db: DbSession, gateway: Gateway, lang: LangDep, now: Now, user: OptionalUser
) -> Json:
    request = body.model_copy(update={"lang": lang})
    try:
        proposal = service.propose(db, gateway, request, now)
    except service.PlannerUnavailable as exc:
        raise _error(status.HTTP_503_SERVICE_UNAVAILABLE, "planner_unavailable") from exc
    return _saved_view(db, proposal, lang, user, now)


@router.get("/planner/proposals/{proposal_id}", tags=["Planner"])
def get_proposal(proposal_id: str, db: DbSession, lang: LangDep, now: Now) -> Json:
    try:
        return _view(db, service.get(db, proposal_id, now), lang)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc


@router.get("/planner/proposals/{proposal_id}/stays", tags=["Planner"])
def proposal_stays(proposal_id: str, place_id: str, db: DbSession, lang: LangDep, now: Now) -> list[Json]:
    try:
        return service.stay_choices(db, proposal_id, place_id, now, lang)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    except service.PlanEditRejected as exc:
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "cannot_edit") from exc


@router.post("/planner/proposals/{proposal_id}/nights", tags=["Planner"])
def proposal_nights(proposal_id: str, body: NightIn, db: DbSession, lang: LangDep, now: Now, editor: Editor) -> Json:
    try:
        proposal = service.adjust_nights(db, proposal_id, body.place_id, body.delta, now)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    except service.PlanEditRejected as exc:
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "cannot_edit") from exc
    return _saved_view(db, proposal, lang, editor, now)


@router.post("/planner/proposals/{proposal_id}/stay", tags=["Planner"])
def proposal_stay(proposal_id: str, body: StayPickIn, db: DbSession, lang: LangDep, now: Now, editor: Editor) -> Json:
    try:
        proposal = service.swap_stay(db, proposal_id, body.place_id, body.stay_id, now)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    except service.PlanEditRejected as exc:
        raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "cannot_edit") from exc
    return _saved_view(db, proposal, lang, editor, now)


@router.post("/planner/proposals/{proposal_id}/revise", tags=["Planner"])
def revise_proposal(
    proposal_id: str, body: ChangeIn, db: DbSession, gateway: Gateway, lang: LangDep, now: Now, editor: Editor
) -> Json:
    try:
        proposal = service.revise(db, gateway, proposal_id, body.change.strip(), now)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    except service.PlannerUnavailable as exc:
        raise _error(status.HTTP_503_SERVICE_UNAVAILABLE, "planner_unavailable") from exc
    return _saved_view(db, proposal, lang, editor, now)


@router.post("/me/planner/proposals/{proposal_id}/accept", tags=["Planner"], status_code=status.HTTP_201_CREATED)
def accept_proposal(proposal_id: str, db: DbSession, user: ActiveUser, lang: LangDep, now: Now, editor: Editor) -> Json:
    """Save the plan as the user's trip and hold all its stays in one checkout (all or none)."""
    try:
        proposal = service.get(db, proposal_id, now)
        lines = service.stay_requests(proposal)
        if not lines:
            raise _error(status.HTTP_422_UNPROCESSABLE_CONTENT, "no_stays")
        trip_id = service.save_trip(db, proposal_id, user, now)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    try:
        stays = [booking.StayRequest(**line) for line in lines]
        checkout = booking.create_checkout(db, user_id=user.id, trip_id=trip_id, stays=stays, now=now)
    except booking.BookingError as exc:
        if exc.code != "unavailable":
            raise _error(_BOOKING_STATUS[exc.code], exc.code, detail=exc.detail) from exc
        # A stay filled up since the plan was made: pick again and let the traveller look before booking
        replanned = service.restay(db, proposal_id, now)
        service.save_trip(db, proposal_id, user, now, accept=False)
        raise _error(status.HTTP_409_CONFLICT, "unavailable", proposal=_view(db, replanned, lang)) from exc
    except ValidationError as exc:  # a stored line no longer fits the booking request
        raise _error(status.HTTP_409_CONFLICT, "unavailable") from exc
    return {"trip_id": trip_id, "checkout_id": checkout["_id"]}


@router.post("/me/planner/proposals/{proposal_id}/save", tags=["Planner"])
def save_proposal(proposal_id: str, db: DbSession, user: ActiveUser, now: Now, editor: Editor) -> Json:
    try:
        return {"trip_id": service.save_trip(db, proposal_id, user, now, accept=False)}
    except service.ProposalNotFound as exc:
        raise _not_found() from exc


@router.post("/me/trips/{trip_id}/resume", tags=["Planner"])
def resume_proposal(trip_id: str, db: DbSession, user: ActiveUser, now: Now) -> Json:
    try:
        return {"proposal_id": service.resume_trip(db, trip_id, user, now)}
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    except service.PlanEditRejected as exc:
        raise _error(409, "trip_locked") from exc
