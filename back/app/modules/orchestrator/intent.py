"""Planner-role model calls: read the request into a ``TripIntent``, and pick one place among candidates."""

import json
import re
from collections.abc import Sequence
from datetime import date

from pydantic import BaseModel

from app.llm import Message, ModelGateway
from app.modules.orchestrator.resolver import Chooser
from app.modules.orchestrator.types import PlanRequest, TripIntent

_INTENT_SYSTEM = """You read trip requests for Mongolia and list what the traveller wants. Today is {today}.
The trip runs {start} to {end} ({nights} nights) for {guests} people; the style is {style}.
- must_places: every place, lake, mountain, aimag or area the traveller wants to visit, written exactly as they
  wrote it (keep Mongolian as Mongolian). Do not add places they did not ask for. Do not include Ulaanbaatar
  unless they want to spend time there: every trip starts and ends there.
- avoid_places: places they do not want.
- interests: activities they mention, in English (horse riding, stargazing, festival, hiking...).
- nights: only where they asked for a number of nights at a place: the place as written and the nights.
Later changes override the request: a change can add or remove places or change nights."""

_CHOOSE_SYSTEM = """The traveller wrote "{query}" in a request for a trip in Mongolia. Pick the one place from the
list that best matches what they mean. Reply with its id."""


# Number words a traveller may use for nights (1-10), Mongolian (plain and attributive forms) and English
_NUMBER_WORDS = {
    1: ("нэг", "one"),
    2: ("хоёр", "хоёрхон", "two"),
    3: ("гурав", "гурван", "three"),
    4: ("дөрөв", "дөрвөн", "four"),
    5: ("тав", "таван", "five"),
    6: ("зургаа", "зургаан", "six"),
    7: ("долоо", "долоон", "seven"),
    8: ("найм", "найман", "eight"),
    9: ("ес", "есөн", "nine"),
    10: ("арав", "арван", "ten"),
}


def _mentions_number(text: str, n: int) -> bool:
    words = set(re.findall(r"\w+", text.lower()))
    return str(n) in words or any(w in words for w in _NUMBER_WORDS.get(n, ()))


class _Choice(BaseModel):
    place_id: str


def extract_intent(gateway: ModelGateway, request: PlanRequest, changes: Sequence[str], today: date) -> TripIntent:
    """Raises ``LLMError`` when the model cannot be reached or does not answer in shape."""
    if not request.text.strip() and not changes:
        return TripIntent()
    system = _INTENT_SYSTEM.format(
        today=today.isoformat(),
        start=request.start_date.isoformat(),
        end=request.end_date.isoformat(),
        nights=request.nights,
        guests=request.guests,
        style=request.style,
    )
    user = f"Request:\n{request.text.strip()}"
    if changes:
        user += "\n\nChanges, oldest first:\n" + "\n".join(f"- {c}" for c in changes)
    intent = gateway.structured("planner", [Message.system(system), Message.user(user)], TripIntent)
    # The model sometimes fills in nights nobody asked for; keep only numbers the traveller wrote
    said = " ".join([request.text, *changes])
    return intent.model_copy(update={"nights": [n for n in intent.nights if _mentions_number(said, n.nights)]})


def place_chooser(gateway: ModelGateway, request_text: str) -> Chooser:
    def choose(query: str, candidates: list[dict]) -> str | None:
        listing = json.dumps(candidates, ensure_ascii=False)
        messages = [
            Message.system(_CHOOSE_SYSTEM.format(query=query)),
            Message.user(f"Request: {request_text}\n\nPlaces: {listing}"),
        ]
        return gateway.structured("planner", messages, _Choice).place_id

    return choose
