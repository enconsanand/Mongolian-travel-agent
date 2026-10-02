"""The English bridge: an English request read and written by the Mongolian oyu models through Orchu."""

import json
from datetime import UTC, date, datetime

import mongomock

from app.llm import Completion, FakeProvider, ModelGateway, RolePolicy, Route
from app.modules.orchestrator import service
from app.modules.orchestrator.types import PlanRequest
from app.seeds.mock_seed import load_mock_collections

NOW = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)


def test_an_english_request_is_planned_and_written_in_mongolian_then_translated(monkeypatch):
    db = mongomock.MongoClient(tz_aware=True)["test_oyu_bridge"]
    load_mock_collections(db, real_server=False)
    fake = FakeProvider()
    route = (Route("fake", "fake"),)
    gw = ModelGateway(providers={"fake": fake}, policies={"planner": RolePolicy(route), "writer": RolePolicy(route)})
    calls: list[tuple[str, str, str]] = []

    def translate(text: str, source: str, target: str) -> str:
        calls.append((text, source, target))
        return f"[{target}] {text}"

    monkeypatch.setattr(service, "_english_bridge", lambda request: translate if request.lang == "en" else None)
    read: list[PlanRequest] = []
    extract = service.extract_intent

    def reading(gateway, request, changes, today):
        read.append(request)
        return extract(gateway, request, changes, today)

    monkeypatch.setattr(service, "extract_intent", reading)
    fake.push(Completion(json.dumps({"must_places": ["Хатгал"]}, ensure_ascii=False)))
    request = PlanRequest(
        text="Khatgal please", guests=2, start_date=date(2026, 10, 3), end_date=date(2026, 10, 6), style="comfort"
    )
    proposal = service.propose(db, gw, request.model_copy(update={"lang": "en"}), NOW)

    assert ("Khatgal please", "en", "mn") in calls
    assert (read[0].text, read[0].lang) == ("[mn] Khatgal please", "mn")
    assert proposal["summary"].startswith("[en] ")
    assert all(day["note"].startswith("[en] ") for day in proposal["days"] if day["note"])
