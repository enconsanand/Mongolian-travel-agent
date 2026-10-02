"""oyu speech and translation: the client, the API that keeps the key on the server, and the English bridge."""

import json
from datetime import UTC, date, datetime

import httpx
import mongomock
import pytest

from app.api.v1 import speech as speech_api
from app.llm import Completion, FakeProvider, ModelGateway, RolePolicy, Route
from app.main import app
from app.modules.orchestrator import service
from app.modules.orchestrator.types import PlanRequest
from app.modules.oyu import OyuClient, OyuError
from app.seeds.mock_seed import load_mock_collections

NOW = datetime(2026, 9, 30, 9, 0, tzinfo=UTC)


class Recorder:
    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)


def oyu(*responses: httpx.Response) -> tuple[OyuClient, Recorder]:
    rec = Recorder(*responses)
    return OyuClient(api_key="oyu-key", transport=httpx.MockTransport(rec)), rec


def test_anir_gets_the_recording_as_multipart_with_the_key():
    client, rec = oyu(httpx.Response(200, json={"text": " Хөвсгөл явмаар байна "}))

    assert client.transcribe(b"RIFF....", filename="speech.wav", content_type="audio/wav") == "Хөвсгөл явмаар байна"
    req = rec.requests[0]
    assert str(req.url) == "https://api.oyu.so/v1/audio/transcriptions"
    assert req.headers["authorization"] == "Bearer oyu-key"
    assert req.headers["content-type"].startswith("multipart/form-data")
    assert b'name="model"' in req.content and b"v4" in req.content and b"RIFF...." in req.content


def test_orchu_translates_and_skips_what_needs_no_translation():
    client, rec = oyu(httpx.Response(200, json={"translation": "I want to go to Khuvsgul"}))

    assert client.translate("Хөвсгөл явмаар байна", source="mn", target="en") == "I want to go to Khuvsgul"
    assert json.loads(rec.requests[0].content) == {"text": "Хөвсгөл явмаар байна", "source": "mn", "target": "en"}
    assert client.translate("same", source="en", target="en") == "same"
    assert len(rec.requests) == 1


@pytest.mark.parametrize(("status", "code"), [(500, "unavailable"), (429, "unavailable"), (400, "refused")])
def test_oyu_errors_say_whether_to_retry(status, code):
    client, _ = oyu(httpx.Response(status, text="no"))
    with pytest.raises(OyuError) as exc:
        client.translate("сайн уу", source="mn", target="en")
    assert exc.value.code == code


@pytest.fixture
def speech(client):
    fake_client, rec = oyu(
        httpx.Response(200, json={"text": "Хөвсгөл"}), httpx.Response(200, json={"translation": "Khuvsgul"})
    )
    app.dependency_overrides[speech_api._client] = lambda: fake_client
    yield client, rec
    app.dependency_overrides.pop(speech_api._client, None)


def test_the_api_transcribes_a_recording_and_translates(speech):
    api, rec = speech
    response = api.post("/api/v1/speech/transcriptions", files={"file": ("speech.wav", b"RIFF", "audio/wav")})
    assert response.status_code == 200 and response.json() == {"text": "Хөвсгөл"}

    response = api.post("/api/v1/translations", json={"text": "Хөвсгөл", "source": "mn", "target": "en"})
    assert response.status_code == 200 and response.json() == {"translation": "Khuvsgul"}
    assert len(rec.requests) == 2


def test_the_api_refuses_what_is_not_audio(speech):
    api, rec = speech
    response = api.post("/api/v1/speech/transcriptions", files={"file": ("notes.txt", b"hi", "text/plain")})
    assert response.status_code == 415 and response.json()["detail"]["code"] == "unsupported_audio"
    assert rec.requests == []


def test_without_a_key_the_api_says_it_is_not_configured(client, monkeypatch):
    monkeypatch.setattr(speech_api, "configured_client", lambda: (_ for _ in ()).throw(OyuError("not_configured", "")))
    response = client.post("/api/v1/translations", json={"text": "сайн уу", "source": "mn", "target": "en"})
    assert response.status_code == 503 and response.json()["detail"]["code"] == "not_configured"


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
