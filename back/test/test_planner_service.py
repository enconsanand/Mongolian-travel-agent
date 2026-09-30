"""Planner service: propose, revise, re-pick stays, and turn an accepted proposal into a trip."""

import json
from datetime import UTC, date, datetime, timedelta

import mongomock
import pytest

from app.llm import Completion, FakeProvider, LLMError, ModelGateway, RolePolicy, Route
from app.models.user import User
from app.modules.orchestrator import service
from app.modules.orchestrator.types import PlanRequest
from app.schemas.travel import ItineraryVersionDoc, TripDoc
from app.seeds.mock_seed import load_mock_collections

NOW = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)
USER = User(_id="user_jamba", email="jambaa@nashatech.com", hashed_password="x", first_name="Jambaa", last_name="G")
REQUEST = PlanRequest(
    text="Хатгал, Тэрэлж явна",
    guests=2,
    start_date=date(2026, 10, 3),
    end_date=date(2026, 10, 7),
    style="comfort",
    budget_mnt=5_000_000,
)


@pytest.fixture
def db():
    database = mongomock.MongoClient(tz_aware=True)["test_planner_service"]
    load_mock_collections(database, real_server=False)
    return database


@pytest.fixture
def fake():
    return FakeProvider()


@pytest.fixture
def gw(fake):
    route = (Route("fake", "fake"),)
    return ModelGateway(providers={"fake": fake}, policies={"planner": RolePolicy(route), "writer": RolePolicy(route)})


def intent(**fields) -> Completion:
    return Completion(json.dumps(fields, ensure_ascii=False))


def visited(proposal):
    return {p for d in proposal["days"] for p in (d["from_place_id"], d["to_place_id"], *d["via_place_ids"])}


def test_a_proposal_includes_the_places_and_reports_the_unknown_ones(db, gw, fake):
    fake.push(intent(must_places=["Хатгал", "Тэрэлж"]))
    proposal = service.propose(db, gw, REQUEST, NOW)

    assert proposal["version"] == 1 and proposal["id"].startswith("plan_")
    assert proposal["places"] == [
        {"query": "Хатгал", "place_id": "place_khatgal", "status": "included"},
        {"query": "Тэрэлж", "place_id": None, "status": "unresolved"},
    ]
    assert "place_khatgal" in visited(proposal) and "unresolved_place" in proposal["warnings"]
    assert proposal["summary"] and all(d["note"] for d in proposal["days"])  # the writer's template
    stored = db[service.PROPOSALS].find_one({"_id": proposal["id"]})
    assert stored["expires_at"] == NOW + timedelta(hours=24)
    assert service.get(db, proposal["id"], NOW)["days"] == proposal["days"]


def test_a_revision_rereads_the_request_with_every_change(db, gw, fake):
    fake.push(intent(must_places=["Хатгал"]))
    first = service.propose(db, gw, REQUEST, NOW)
    fake.push(intent(must_places=["Хатгал", "Тэрхийн Цагаан нуур"], nights=[{"place": "Хатгал", "nights": 2}]))

    second = service.revise(db, gw, first["id"], "Тэрхийн Цагаан нуурыг нэм, Хатгалд 2 хонъё", NOW)

    assert second["id"] == first["id"] and second["version"] == 2
    assert second["changes"] == ["Тэрхийн Цагаан нуурыг нэм, Хатгалд 2 хонъё"]
    assert {"place_khatgal", "place_terkhiin_tsagaan"} <= visited(second)
    assert sum(1 for d in second["days"][:-1] if d["to_place_id"] == "place_khatgal") == 2
    planner_calls = [r for r in fake.requests if "Changes, oldest first" in r["messages"][-1].content]
    assert planner_calls and "Тэрхийн Цагаан нуурыг нэм" in planner_calls[-1]["messages"][-1].content


def test_avoided_places_are_left_out(db, gw, fake):
    fake.push(intent(must_places=["Хатгал", "Тэрхийн Цагаан нуур"], avoid_places=["Тэрхийн Цагаан нуур"]))
    proposal = service.propose(db, gw, REQUEST, NOW)
    assert "place_terkhiin_tsagaan" not in visited(proposal)
    assert [p["place_id"] for p in proposal["places"]] == ["place_khatgal"]


def test_the_planner_model_being_down_is_its_own_error(db, gw, fake):
    fake.push(LLMError("rate_limited", "quota"))
    with pytest.raises(service.PlannerUnavailable):
        service.propose(db, gw, REQUEST, NOW)


def test_an_unknown_or_expired_proposal_is_not_found(db, gw, fake):
    with pytest.raises(service.ProposalNotFound):
        service.get(db, "plan_missing", NOW)
    fake.push(intent(must_places=["Хатгал"]))
    proposal = service.propose(db, gw, REQUEST, NOW)
    later = NOW + timedelta(hours=25)
    with pytest.raises(service.ProposalNotFound):
        service.get(db, proposal["id"], later)
    with pytest.raises(service.ProposalNotFound):
        service.revise(db, gw, proposal["id"], "x", later)


def test_stay_requests_have_one_line_per_stay_block(db, gw, fake):
    fake.push(intent(must_places=["Хатгал"], nights=[{"place": "Хатгал", "nights": 4}]))
    proposal = service.propose(db, gw, REQUEST.model_copy(update={"text": "Хатгалд 4 хонъё"}), NOW)
    [line] = service.stay_requests(proposal)
    first = proposal["days"][0]["stay"]
    assert line == {
        "stay_id": first["stay_id"],
        "unit_type": first["unit_type"],
        "check_in": "2026-10-03",
        "nights": 4,
        "units": first["units"],
        "guests": 2,
    }


def test_restay_picks_again_when_a_stay_filled_up(db, gw, fake):
    fake.push(intent(must_places=["Хатгал"], nights=[{"place": "Хатгал", "nights": 4}]))
    proposal = service.propose(db, gw, REQUEST.model_copy(update={"text": "Хатгалд 4 хонъё"}), NOW)
    taken = proposal["days"][0]["stay"]
    db["stay_availability"].update_many(
        {"stay_id": taken["stay_id"], "unit_type": taken["unit_type"]}, {"$set": {"available": 0}}
    )
    again = service.restay(db, proposal["id"], NOW)
    assert again["version"] == 2
    now_picked = again["days"][0]["stay"]
    assert now_picked is None or (now_picked["stay_id"], now_picked["unit_type"]) != (
        taken["stay_id"],
        taken["unit_type"],
    )
    assert [d["note"] for d in again["days"]] == [d["note"] for d in proposal["days"]]


def test_accepting_saves_a_valid_trip_and_itinerary(db, gw, fake):
    fake.push(intent(must_places=["Хатгал"]))
    proposal = service.propose(db, gw, REQUEST, NOW)

    trip_id = service.save_trip(db, proposal["id"], USER, NOW)

    trip = TripDoc.model_validate(db["trips"].find_one({"_id": trip_id}))
    assert (trip.user_id, trip.status, trip.current_version) == ("user_jamba", "planned", 1)
    assert (trip.start_date, trip.end_date, trip.party.adults) == ("2026-10-03", "2026-10-07", 2)
    assert trip.budget and trip.budget.limit_mnt == 5_000_000
    itinerary = ItineraryVersionDoc.model_validate(db["itinerary_versions"].find_one({"trip_id": trip_id}))
    assert itinerary.reason == "initial_plan" and len(itinerary.days) == len(proposal["days"])
    assert itinerary.days[0].stay_id == proposal["days"][0]["stay_id"]


def test_accepting_again_reuses_the_trip_and_a_revision_adds_a_version(db, gw, fake):
    fake.push(intent(must_places=["Хатгал"]))
    proposal = service.propose(db, gw, REQUEST, NOW)
    trip_id = service.save_trip(db, proposal["id"], USER, NOW)
    assert service.save_trip(db, proposal["id"], USER, NOW) == trip_id
    assert db["itinerary_versions"].count_documents({"trip_id": trip_id}) == 1

    fake.push(intent(must_places=["Хатгал", "Тэрхийн Цагаан нуур"]))
    service.revise(db, gw, proposal["id"], "Тэрхийн Цагаан нуур нэм", NOW)
    assert service.save_trip(db, proposal["id"], USER, NOW) == trip_id
    assert db["trips"].find_one({"_id": trip_id})["current_version"] == 2
    assert db["itinerary_versions"].find_one({"trip_id": trip_id, "version": 2})["reason"] == "user_change"


def test_someone_elses_accepted_proposal_is_not_found(db, gw, fake):
    fake.push(intent(must_places=["Хатгал"]))
    proposal = service.propose(db, gw, REQUEST, NOW)
    service.save_trip(db, proposal["id"], USER, NOW)
    other = USER.model_copy(update={"id": "user_anand"})
    with pytest.raises(service.ProposalNotFound):
        service.save_trip(db, proposal["id"], other, NOW)


def test_proposals_expire_by_a_ttl_index():
    from app.db.mongo import INDEXES

    assert (service.PROPOSALS, [("expires_at", 1)], {"expireAfterSeconds": 0}) in INDEXES
