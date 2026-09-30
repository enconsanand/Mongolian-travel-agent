"""Trip planner API: a request becomes a structured itinerary; changes make new versions; accepting holds its stays.

Planning is public; accepting needs a signed-in user and returns the checkout the trusted surface approves and
pays. Responses carry a ``catalog`` of the places, stays and events the plan refers to, in the caller's
language (``Accept-Language``), so the page needs no other calls.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.api.v1.deps import ActiveUser, DbSession
from app.api.v1.payments import Now
from app.api.v1.travel import LangDep
from app.modules import booking
from app.modules.orchestrator import service
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


def _error(code: int, name: str, **extra: Any) -> HTTPException:
    return HTTPException(code, detail={"code": name, **extra})


def _not_found() -> HTTPException:
    return _error(status.HTTP_404_NOT_FOUND, "proposal_not_found")


def _view(db: DbSession, proposal: Json, lang: Lang) -> Json:
    """The proposal plus display data for every place, stay and event it names."""
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
            ["name", "type", "aimag", "rating", "reviews_count", "cover_image_url", "images", "check_in", "check_out"],
        ),
        "events": by_id("events", event_ids, ["name", "category", "start_date", "end_date", "ticket_price_mnt"]),
    }
    for stay in catalog["stays"].values():
        stay["images"] = stay.get("images", [])[:1]  # the cover's credit (author, license, source)
    return {**proposal, "catalog": catalog}


@router.post("/planner/proposals", tags=["Planner"], status_code=status.HTTP_201_CREATED)
def create_proposal(body: PlanRequest, db: DbSession, gateway: Gateway, lang: LangDep, now: Now) -> Json:
    request = body.model_copy(update={"lang": lang})
    try:
        proposal = service.propose(db, gateway, request, now)
    except service.PlannerUnavailable as exc:
        raise _error(status.HTTP_503_SERVICE_UNAVAILABLE, "planner_unavailable") from exc
    return _view(db, proposal, lang)


@router.get("/planner/proposals/{proposal_id}", tags=["Planner"])
def get_proposal(proposal_id: str, db: DbSession, lang: LangDep, now: Now) -> Json:
    try:
        return _view(db, service.get(db, proposal_id, now), lang)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc


@router.post("/planner/proposals/{proposal_id}/revise", tags=["Planner"])
def revise_proposal(proposal_id: str, body: ChangeIn, db: DbSession, gateway: Gateway, lang: LangDep, now: Now) -> Json:
    try:
        proposal = service.revise(db, gateway, proposal_id, body.change.strip(), now)
    except service.ProposalNotFound as exc:
        raise _not_found() from exc
    except service.PlannerUnavailable as exc:
        raise _error(status.HTTP_503_SERVICE_UNAVAILABLE, "planner_unavailable") from exc
    return _view(db, proposal, lang)


@router.post("/me/planner/proposals/{proposal_id}/accept", tags=["Planner"], status_code=status.HTTP_201_CREATED)
def accept_proposal(proposal_id: str, db: DbSession, user: ActiveUser, lang: LangDep, now: Now) -> Json:
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
        raise _error(status.HTTP_409_CONFLICT, "unavailable", proposal=_view(db, replanned, lang)) from exc
    except ValidationError as exc:  # a stored line no longer fits the booking request
        raise _error(status.HTTP_409_CONFLICT, "unavailable") from exc
    return {"trip_id": trip_id, "checkout_id": checkout["_id"]}
