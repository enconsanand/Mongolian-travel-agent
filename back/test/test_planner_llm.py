"""The planner's two model calls: reading the request (intent, place choice) and writing the plan's text."""

import json
from datetime import date

import pytest

from app.llm import Completion, FakeProvider, LLMError, ModelGateway, RolePolicy, Route
from app.modules.orchestrator.intent import extract_intent, place_chooser
from app.modules.orchestrator.types import PlanDay, PlanRequest, TripIntent
from app.modules.orchestrator.writer import write

TODAY = date(2026, 9, 30)


def gateway(*steps) -> tuple[ModelGateway, FakeProvider]:
    fake = FakeProvider(*steps)
    route = (Route("fake", "fake"),)
    return ModelGateway(
        providers={"fake": fake}, policies={"planner": RolePolicy(route), "writer": RolePolicy(route)}
    ), fake


def reply(obj) -> Completion:
    return Completion(json.dumps(obj, ensure_ascii=False))


REQUEST = PlanRequest(
    text="Хөвсгөл, Тэрхийн Цагаан нуур явмаар байна. Морь унана.",
    guests=2,
    start_date=date(2026, 10, 3),
    end_date=date(2026, 10, 8),
    style="comfort",
)


def test_intent_is_read_from_the_request_with_today_and_the_dates_in_the_prompt():
    gw, fake = gateway(reply({"must_places": ["Хөвсгөл", "Тэрхийн Цагаан нуур"], "interests": ["horse riding"]}))
    intent = extract_intent(gw, REQUEST, [], TODAY)
    assert intent == TripIntent(must_places=["Хөвсгөл", "Тэрхийн Цагаан нуур"], interests=["horse riding"])
    system = fake.requests[0]["messages"][0].content
    assert "2026-09-30" in system and "2026-10-03" in system and "2026-10-08" in system


def test_changes_are_sent_after_the_request_in_order():
    gw, fake = gateway(reply({"must_places": ["Хөвсгөл"], "nights": [{"place": "Хөвсгөл", "nights": 3}]}))
    intent = extract_intent(gw, REQUEST, ["Тэрхийн Цагааныг хас", "Хөвсгөлд 3 хонъё"], TODAY)
    assert intent.nights_hint == {"Хөвсгөл": 3}
    user = fake.requests[0]["messages"][-1].content
    assert user.index(REQUEST.text) < user.index("Тэрхийн Цагааныг хас") < user.index("Хөвсгөлд 3 хонъё")


def test_an_empty_request_needs_no_model_call():
    gw, fake = gateway()
    assert extract_intent(gw, REQUEST.model_copy(update={"text": "  "}), [], TODAY) == TripIntent()
    assert fake.requests == []


def test_intent_failure_is_raised_to_the_caller():
    gw, _ = gateway(LLMError("rate_limited", "quota"))
    with pytest.raises(LLMError):
        extract_intent(gw, REQUEST, [], TODAY)


def test_the_place_chooser_asks_for_one_of_the_candidates():
    gw, fake = gateway(reply({"place_id": "place_khatgal"}))
    candidates = [
        {"id": "place_khatgal", "name": {"mn": "Хатгал", "en": "Khatgal"}, "kind": "soum_center", "aimag": "Khövsgöl"},
        {"id": "place_murun", "name": {"mn": "Мөрөн", "en": "Mörön"}, "kind": "aimag_center", "aimag": "Khövsgöl"},
    ]
    assert place_chooser(gw, REQUEST.text)("Хөвсгөл нуур", candidates) == "place_khatgal"
    prompt = " ".join(m.content for m in fake.requests[0]["messages"])
    assert "place_murun" in prompt and "Хөвсгөл нуур" in prompt


DAYS = [
    PlanDay(day=1, date="2026-10-03", from_place_id="place_ub", to_place_id="place_khatgal", distance_km=650),
    PlanDay(day=2, date="2026-10-04", from_place_id="place_khatgal", to_place_id="place_ub", distance_km=650),
]
NAMES = {"place_ub": "Улаанбаатар", "place_khatgal": "Хатгал"}


def test_the_writer_gives_a_summary_and_a_note_per_day():
    gw, fake = gateway(reply({"summary": "Хөвсгөл рүү 2 өдөр", "notes": ["Хатгал руу", "Буцна"]}))
    writing = write(gw, REQUEST, DAYS, NAMES, {}, {})
    assert (writing.summary, writing.notes) == ("Хөвсгөл рүү 2 өдөр", ["Хатгал руу", "Буцна"])
    prompt = fake.requests[0]["messages"][-1].content
    assert "Хатгал" in prompt and "650" in prompt


@pytest.mark.parametrize(
    "step", [LLMError("unavailable"), reply({"summary": "x", "notes": ["only one"]}), reply({"summary": ""})]
)
def test_the_writer_falls_back_to_a_template(step):
    gw, _ = gateway(step, step)
    writing = write(gw, REQUEST, DAYS, NAMES, {}, {})
    assert "Хатгал" in writing.summary and len(writing.notes) == 2
    assert writing.notes[0].startswith("Улаанбаатар → Хатгал")


def test_the_template_is_in_english_for_english_requests():
    gw, _ = gateway(LLMError("unavailable"))
    writing = write(
        gw,
        REQUEST.model_copy(update={"lang": "en"}),
        DAYS,
        {"place_ub": "Ulaanbaatar", "place_khatgal": "Khatgal"},
        {},
        {},
    )
    assert "day" in writing.summary.lower() and writing.notes[0].startswith("Ulaanbaatar → Khatgal, 650 km")


def test_the_template_calls_a_day_in_one_place_a_free_day():
    gw, _ = gateway(LLMError("unavailable"))
    rest = PlanDay(day=2, date="2026-10-04", from_place_id="place_khatgal", to_place_id="place_khatgal")
    writing = write(gw, REQUEST, [DAYS[0], rest, DAYS[1].model_copy(update={"day": 3})], NAMES, {}, {})
    assert writing.notes[1] == "Хатгал: чөлөөт өдөр"
    english = write(gw, REQUEST.model_copy(update={"lang": "en"}), [rest], {"place_khatgal": "Khatgal"}, {}, {})
    assert english.notes == ["Free day in Khatgal"]


def _objects(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _objects(value)
    elif isinstance(node, list):
        for value in node:
            yield from _objects(value)


def test_the_intent_schema_leaves_the_model_nothing_open_ended():
    # Workers AI's llama, decoding against a free-form map, invented keys until it ran out of tokens
    schema = TripIntent.model_json_schema()
    assert not [n for n in _objects(schema) if isinstance(n.get("additionalProperties"), dict)]
    assert all("maxItems" in n for n in _objects(schema) if n.get("type") == "array")


def test_nights_are_read_as_a_list_of_places():
    gw, _ = gateway(reply({"must_places": ["Хатгал"], "nights": [{"place": "Хатгал", "nights": 3}]}))
    request = REQUEST.model_copy(update={"text": "Хатгалд 3 хонъё"})
    assert extract_intent(gw, request, [], TODAY).nights_hint == {"Хатгал": 3}


@pytest.mark.parametrize(
    "text, kept",
    [
        ("Хатгал явна", {}),  # the model's own idea: no number of nights in the request
        ("Хатгалд 3 хонъё", {"Хатгал": 3}),
        ("Хатгалд гурван шөнө", {"Хатгал": 3}),
        ("three nights in Khatgal", {"Хатгал": 3}),
    ],
)
def test_nights_the_traveller_did_not_ask_for_are_dropped(text, kept):
    gw, _ = gateway(reply({"must_places": ["Хатгал"], "nights": [{"place": "Хатгал", "nights": 3}]}))
    assert extract_intent(gw, REQUEST.model_copy(update={"text": text}), [], TODAY).nights_hint == kept


def test_nights_from_a_change_are_kept():
    gw, _ = gateway(reply({"must_places": ["Хатгал"], "nights": [{"place": "Хатгал", "nights": 2}]}))
    intent = extract_intent(gw, REQUEST, ["Хатгалд 2 хонъё"], TODAY)
    assert intent.nights_hint == {"Хатгал": 2}


def test_the_writer_is_told_which_places_are_not_in_the_plan():
    gw, fake = gateway(reply({"summary": "x", "notes": ["a", "b"]}))
    write(gw, REQUEST, DAYS, NAMES, {}, {}, missing=["Тэрэлж"])
    prompt = fake.requests[0]["messages"][-1].content
    assert "Тэрэлж" in prompt.split("Not in the plan")[1]
