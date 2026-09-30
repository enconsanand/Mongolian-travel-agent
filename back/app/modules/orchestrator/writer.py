"""Writer-role model call: the plan's summary and one short note per day, in the traveller's language.

The model only writes prose from facts the code settled; if it fails or answers out of shape (a note missing),
a plain template says the same facts.
"""

import logging
from collections.abc import Mapping, Sequence

from pydantic import BaseModel, Field

from app.llm import LLMError, Message, ModelGateway
from app.modules.orchestrator.types import PlanDay, PlanRequest

log = logging.getLogger(__name__)

_SYSTEM = {
    "mn": "Та Монголын аяллын хөтөч. Доорх баримтаар аяллын товч тайлбар (2-3 өгүүлбэр) болон өдөр бүрт нэг "
    "богино тэмдэглэл монгол хэлээр (кирилл) бич. Баримтад байхгүй газар, буудал, үнэ бүү нэм.",
    "en": "You are a Mongolia travel guide. From the facts below write a short trip summary (2-3 sentences) and "
    "one short note per day, in English. Do not add places, stays or prices that are not in the facts.",
}


class Writing(BaseModel):
    summary: str = Field(min_length=1)
    notes: list[str]


def _facts(
    days: Sequence[PlanDay], places: Mapping[str, str], stays: Mapping[str, str], events: Mapping[str, str]
) -> str:
    lines = []
    for d in days:
        route = " → ".join(places.get(p, p) for p in (d.from_place_id, *d.via_place_ids, d.to_place_id))
        line = f"Day {d.day} {d.date}: {route}, {d.distance_km} km, {d.drive_time_min // 60} h drive"
        if d.stay_id:
            line += f"; sleep at {stays.get(d.stay_id, d.stay_id)}"
        if d.event_ids:
            line += "; events: " + ", ".join(events.get(e, e) for e in d.event_ids)
        lines.append(line)
    return "\n".join(lines)


def _template(request: PlanRequest, days: Sequence[PlanDay], places: Mapping[str, str]) -> Writing:
    stops = list(dict.fromkeys(places.get(d.to_place_id, d.to_place_id) for d in days[:-1])) or [
        places.get(p, p) for d in days for p in d.via_place_ids
    ]
    km, h = ("км", "цаг") if request.lang == "mn" else ("km", "h")
    notes = []
    for d in days:
        route = " → ".join(places.get(p, p) for p in (d.from_place_id, *d.via_place_ids, d.to_place_id))
        notes.append(f"{route}, {d.distance_km} {km} (~{round(d.drive_time_min / 60)} {h})" if d.distance_km else route)
    if request.lang == "mn":
        summary = f"{len(days)} өдрийн аялал: " + " → ".join(stops)
    else:
        summary = f"A {len(days)}-day trip: " + " → ".join(stops)
    return Writing(summary=summary, notes=notes)


def write(
    gateway: ModelGateway,
    request: PlanRequest,
    days: Sequence[PlanDay],
    places: Mapping[str, str],
    stays: Mapping[str, str],
    events: Mapping[str, str],
) -> Writing:
    """``places``/``stays``/``events``: id → name in the request's language."""
    messages = [
        Message.system(_SYSTEM[request.lang]),
        Message.user(f"Traveller's request: {request.text}\n\nFacts:\n{_facts(days, places, stays, events)}"),
    ]
    try:
        writing = gateway.structured("writer", messages, Writing)
    except LLMError as exc:
        log.warning("plan writer failed, using the template: %s %s", exc.code, exc)
        return _template(request, days, places)
    if len(writing.notes) != len(days):
        log.warning("plan writer gave %d notes for %d days, using the template", len(writing.notes), len(days))
        return _template(request, days, places)
    return writing
