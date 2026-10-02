"""Planner over HTTP: propose (public), revise, read, and accept into a held checkout (signed in)."""

import json

import pytest

from app.api.v1 import payments as payments_api
from app.api.v1.deps import get_current_active_user, get_optional_user
from app.llm import Completion, FakeProvider, LLMError, ModelGateway, RolePolicy, Route
from app.main import app
from app.models.user import User
from app.modules.orchestrator import service
from app.seeds.mock_seed import load_mock_collections
from test.payment_helpers import NOW

USER = User(_id="user_jamba", email="jambaa@nashatech.com", hashed_password="x", first_name="Jambaa", last_name="G")
BODY = {
    "text": "Хатгал, Тэрэлж явна",
    "guests": 2,
    "start_date": "2026-10-03",
    "end_date": "2026-10-06",
    "budget_mnt": 5000000,
    "style": "comfort",
}


def intent(**fields) -> Completion:
    return Completion(json.dumps(fields, ensure_ascii=False))


@pytest.fixture
def fake():
    return FakeProvider()


@pytest.fixture
def api(client, db, fake):
    load_mock_collections(db, real_server=False)
    route = (Route("fake", "fake"),)
    gw = ModelGateway(providers={"fake": fake}, policies={"planner": RolePolicy(route), "writer": RolePolicy(route)})
    app.dependency_overrides.update({service.gateway: lambda: gw, payments_api.get_now: lambda: NOW})
    yield client
    for dep in (service.gateway, payments_api.get_now, get_current_active_user, get_optional_user):
        app.dependency_overrides.pop(dep, None)


def sign_in():
    app.dependency_overrides[get_current_active_user] = lambda: USER
    app.dependency_overrides[get_optional_user] = lambda: USER


def propose(api, fake, *, must=("Хатгал", "Тэрэлж"), body=BODY, **hints):
    fake.push(intent(must_places=list(must), **hints))
    response = api.post("/api/v1/planner/proposals", json=body)
    assert response.status_code == 201, response.text
    api.headers["X-Plan-Token"] = response.json()["claim_token"]
    return response.json()


def test_propose_returns_the_plan_with_display_names(api, fake):
    plan = propose(api, fake)
    assert plan["version"] == 1 and len(plan["days"]) == 4
    assert plan["places"][1] == {"query": "Тэрэлж", "place_id": "place_terelj", "status": "included"}
    assert plan["catalog"]["places"]["place_terelj"]["name"] == "Горхи-Тэрэлж"
    assert plan["catalog"]["places"]["place_khatgal"]["name"] == "Хатгал"
    stay_id = next(d["stay_id"] for d in plan["days"] if d["stay_id"])
    stay = plan["catalog"]["stays"][stay_id]
    assert stay["name"] and stay["cover_image_url"] and "phone" not in json.dumps(stay)


def test_english_callers_get_english_names_and_text(api, fake):
    fake.push(intent(must_places=["Khatgal"]))
    plan = api.post("/api/v1/planner/proposals", json=BODY, headers={"Accept-Language": "en"}).json()
    assert plan["request"]["lang"] == "en"
    assert plan["catalog"]["places"]["place_khatgal"]["name"] == "Khatgal"


@pytest.mark.parametrize(
    "change",
    [{"end_date": "2026-10-01"}, {"guests": 0}, {"style": "castle"}, {"end_date": "2026-11-20"}],
)
def test_bad_requests_are_422(api, change):
    assert api.post("/api/v1/planner/proposals", json={**BODY, **change}).status_code == 422


def test_planner_model_down_is_503(api, fake):
    fake.push(LLMError("rate_limited", "quota"))
    response = api.post("/api/v1/planner/proposals", json=BODY)
    assert response.status_code == 503 and response.json()["detail"]["code"] == "planner_unavailable"


def test_revise_and_read(api, fake):
    plan = propose(api, fake)
    fake.push(intent(must_places=["Хатгал", "Тэрхийн Цагаан нуур"]))
    revised = api.post(f"/api/v1/planner/proposals/{plan['id']}/revise", json={"change": "Тэрхийн Цагаан нуур нэм"})
    assert revised.status_code == 200 and revised.json()["version"] == 2
    assert api.get(f"/api/v1/planner/proposals/{plan['id']}").json()["version"] == 2
    assert api.get("/api/v1/planner/proposals/plan_nope").status_code == 404
    assert api.post(f"/api/v1/planner/proposals/{plan['id']}/revise", json={"change": ""}).status_code == 422


def test_accept_needs_sign_in(api, fake):
    plan = propose(api, fake)
    assert api.post(f"/api/v1/me/planner/proposals/{plan['id']}/accept").status_code == 401


def test_accept_holds_every_stay_in_one_checkout(api, fake, db):
    plan = propose(
        api, fake, must=("Хатгал",), body={**BODY, "text": "Хатгалд 3 хонъё"}, nights=[{"place": "Хатгал", "nights": 3}]
    )
    sign_in()
    response = api.post(f"/api/v1/me/planner/proposals/{plan['id']}/accept")
    assert response.status_code == 201, response.text
    accepted = response.json()
    checkout = api.get(f"/api/v1/me/checkouts/{accepted['checkout_id']}").json()
    assert checkout["trip_id"] == accepted["trip_id"] and checkout["status"] == "open"
    assert checkout["total_mnt"] == plan["totals"]["stays_mnt"]
    assert db["trips"].find_one({"_id": accepted["trip_id"]})["user_id"] == "user_jamba"


def test_accept_when_a_stay_filled_up_is_409_with_a_new_plan(api, fake, db):
    plan = propose(
        api, fake, must=("Хатгал",), body={**BODY, "text": "Хатгалд 3 хонъё"}, nights=[{"place": "Хатгал", "nights": 3}]
    )
    taken = plan["days"][0]["stay"]
    db["stay_availability"].update_many(
        {"stay_id": taken["stay_id"], "unit_type": taken["unit_type"]}, {"$set": {"available": 0}}
    )
    sign_in()
    response = api.post(f"/api/v1/me/planner/proposals/{plan['id']}/accept")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "unavailable" and detail["proposal"]["version"] == 2


def test_accept_without_any_stay_is_422(api, fake):
    plan = propose(api, fake, body={**BODY, "start_date": "2027-07-10", "end_date": "2027-07-12"})
    sign_in()
    response = api.post(f"/api/v1/me/planner/proposals/{plan['id']}/accept")
    assert response.status_code == 422 and response.json()["detail"]["code"] == "no_stays"


def test_a_proposal_does_not_say_who_accepted_it(api, fake):
    plan = propose(api, fake, must=("Хатгал",))
    sign_in()
    api.post(f"/api/v1/me/planner/proposals/{plan['id']}/accept")
    app.dependency_overrides.pop(get_current_active_user)
    public = api.get(f"/api/v1/planner/proposals/{plan['id']}").json()
    assert public["accepted"] is True and "user_jamba" not in json.dumps(public)


def test_guest_claim_and_durable_draft(api, fake, db):
    plan = propose(api, fake)
    sign_in()
    url = f"/api/v1/me/planner/proposals/{plan['id']}/save"
    assert api.post(url, headers={"X-Plan-Token": "wrong"}).status_code == 404
    first = api.post(url)
    assert first.status_code == 200, first.text
    trip_id = first.json()["trip_id"]
    assert api.post(url).json()["trip_id"] == trip_id
    assert not db["checkouts"].count_documents({"trip_id": trip_id})
    assert not db["bookings"].count_documents({"trip_id": trip_id})
    public = api.get(f"/api/v1/planner/proposals/{plan['id']}").json()
    assert public["accepted"] is False
    assert "claim_token" not in public and "claim_hash" not in public and "user_jamba" not in json.dumps(public)
    db["plan_proposals"].delete_one({"_id": plan["id"]})
    detail = api.get(f"/api/v1/me/trips/{trip_id}").json()
    assert detail["plan"]["days"] == plan["days"] and detail["can_resume"]
    listed = next(t for t in api.get("/api/v1/me/trips").json() if t["id"] == trip_id)
    first_stop = detail["places"][plan["days"][0]["from_place_id"]]["name"]
    assert listed["route"][0] == first_stop and len(listed["route"]) == len(set(listed["route"]))
    resumed = api.post(f"/api/v1/me/trips/{trip_id}/resume")
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["proposal_id"] == plan["id"]


def test_signed_in_generation_saved_and_other_user_cannot_read_or_edit(api, fake, db):
    sign_in()
    plan = propose(api, fake)
    saved = db["saved_plans"].find_one({"proposal_id": plan["id"]})
    assert saved and saved["user_id"] == USER.id
    other = USER.model_copy(update={"id": "user_other"})
    app.dependency_overrides[get_current_active_user] = lambda: other
    app.dependency_overrides[get_optional_user] = lambda: other
    assert api.get(f"/api/v1/me/trips/{saved['_id']}").status_code == 404
    assert api.post(f"/api/v1/me/trips/{saved['_id']}/resume").status_code == 404
    assert api.post(f"/api/v1/me/planner/proposals/{plan['id']}/save").status_code == 404
    assert api.post(f"/api/v1/planner/proposals/{plan['id']}/revise", json={"change": "Хатгал"}).status_code == 404


def test_saved_trip_is_reused_by_checkout_and_locked(api, fake, db):
    sign_in()
    plan = propose(api, fake, must=("Хатгал",), nights=[{"place": "Хатгал", "nights": 3}])
    saved = db["saved_plans"].find_one({"proposal_id": plan["id"]})
    accepted = api.post(f"/api/v1/me/planner/proposals/{plan['id']}/accept")
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["trip_id"] == saved["_id"]
    assert api.post(f"/api/v1/planner/proposals/{plan['id']}/revise", json={"change": "Хатгал"}).status_code == 409
    detail = api.get(f"/api/v1/me/trips/{saved['_id']}").json()
    assert detail["bookings"][0]["units"] >= 1
    assert detail["stays"] and detail["checkouts"]
    assert detail["can_resume"] is False
