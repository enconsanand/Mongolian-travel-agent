"""Planner-role model calls: read the request into a ``TripIntent``, and pick one place among candidates."""

import json
import re
from collections.abc import Sequence
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.llm import LLMError, Message, ModelGateway
from app.modules.orchestrator.resolver import Chooser
from app.modules.orchestrator.types import PlanRequest, TripIntent
from app.utils.galig import latin_to_cyrillic

_INTENT_SYSTEM = """You read trip requests for Mongolia and list what the traveller wants. Today is {today}.
The trip runs {start} to {end} ({nights} nights) for {guests} people; the style is {style}.
- must_places: every place, lake, mountain, aimag or area the traveller named, written exactly as they
  wrote it (keep Mongolian as Mongolian). Do not add places they did not ask for. If they named no place,
  leave this empty: "somewhere far", a lake, mountains, rock, or the sand desert is not a place name.
  Do not include Ulaanbaatar unless they want to spend time there: every trip starts and ends there.
  A festival, concert, or event name is an interest, not a place.
- avoid_places: places they do not want.
- interests: activities they mention, in English (horse riding, stargazing, festival, hiking...).
- landscape: empty when they named a place. Otherwise water (lake, river, a place with water),
  mountain (mountain, rock), or desert (sand, dunes, gobi). Empty if they said none of these.
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
    # Galig ("uws", "7honogiin aylal") is read as Cyrillic so place names are not split into unknown words
    request_text = latin_to_cyrillic(request.text.strip())
    change_text = [latin_to_cyrillic(c) for c in changes]
    user = f"Request:\n{request_text}"
    if change_text:
        user += "\n\nChanges, oldest first:\n" + "\n".join(f"- {c}" for c in change_text)
    intent = gateway.structured("planner", [Message.system(system), Message.user(user)], TripIntent)
    # The model sometimes fills in nights nobody asked for; keep only numbers the traveller wrote
    said = " ".join([request.text, *changes])
    return intent.model_copy(update={"nights": [n for n in intent.nights if _mentions_number(said, n.nights)]})


SlotName = Literal["place", "guests", "dates", "budget"]


class SlotRead(BaseModel):
    """One chat reply, rewritten into a phrase the trip reader already accepts.

    Both fields are required: a model that only says it understood, and leaves the phrase out, is not usable.
    """

    understood: bool
    normalized: str = Field(max_length=200)


_READ_SYSTEM = """You read one short reply in a Mongolia trip chat. The question being answered is "{slot}".
Today is {today}.
Return JSON with both fields.
understood is true only when the message answers that question.
normalized is a short phrase, never empty when understood is true:
- place: the place name only, in the language they used
- guests: a number of people, like "2 хүн" or "2 people"
- dates: a real start and end, like "10 сарын 8-наас 10 сарын 10" or "Oct 8 to Oct 10".
  A duration alone is not a date range.
- budget: digits plus a unit, like "500 мянга", "1 сая", "500 thousand", or "1 million".
  "таван зуун мянга" is "500 мянга". "дотор" and "within" mean that amount is the maximum; still write the amount.
If they did not answer: {{"understood": false, "normalized": ""}}.
Do not invent a place, date, or amount. Example: {{"understood": true, "normalized": "500 мянга"}}."""


def read_slot(gateway: ModelGateway, slot: SlotName, text: str, today: date) -> SlotRead:
    """Turn a free-text chat reply into a phrase the form already understands.

    A model that cannot be reached, or that answers out of shape, is treated as not understood.
    """
    cleaned = text.strip()
    if not cleaned:
        return SlotRead(understood=False, normalized="")
    system = _READ_SYSTEM.format(slot=slot, today=today.isoformat())
    user = latin_to_cyrillic(cleaned)
    try:
        read = gateway.structured("planner", [Message.system(system), Message.user(user)], SlotRead)
    except LLMError:
        return SlotRead(understood=False, normalized="")
    if not read.understood or not read.normalized.strip():
        return SlotRead(understood=False, normalized="")
    return SlotRead(understood=True, normalized=read.normalized.strip()[:200])


def place_chooser(gateway: ModelGateway, request_text: str) -> Chooser:
    def choose(query: str, candidates: list[dict]) -> str | None:
        listing = json.dumps(candidates, ensure_ascii=False)
        messages = [
            Message.system(_CHOOSE_SYSTEM.format(query=query)),
            Message.user(f"Request: {request_text}\n\nPlaces: {listing}"),
        ]
        return gateway.structured("planner", messages, _Choice).place_id

    return choose
