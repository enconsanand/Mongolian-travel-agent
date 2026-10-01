"""Place names as the traveller wrote them → place ids, never silently dropping one.

Matching, in order: a place's Mongolian/English name or alias; a region word; an aimag name. An explicit
"аймаг"/"aimag" query searches the province first. A
name matches at the start of a word, so case endings still match ("Хонгорын Элсэнд" → Хонгорын Элс). One
place → included. Several → ``choose`` (the planner model) picks one of them; an answer outside that list, or
a failure, falls back to the best candidate. Nothing → ``unresolved``, which the traveller is shown.
"""

import logging
import re
import unicodedata
from collections.abc import Callable, Sequence

from app.modules.orchestrator.catalog import Catalog, Json
from app.modules.orchestrator.types import ResolvedPlace
from app.utils.galig import latin_to_cyrillic

log = logging.getLogger(__name__)

# (query, candidates as {id, name, kind, aimag}) -> chosen place id
Chooser = Callable[[str, list[Json]], str | None]

_CYRILLIC_FOLD = str.maketrans({"ө": "о", "ү": "у", "ё": "е", "-": " "})
GENERIC = {"нуур", "lake", "уул", "mountain", "volcano", "хот", "city", "сум", "soum", "аймаг", "aimag"}
_REGION_WORDS = {
    "south": {"говь", "gobi", "govi", "омнод", "south"},
    "west": {"баруун", "west", "western"},
    "east": {"зуун", "east", "eastern"},
    "north": {"хойд", "north", "northern"},
}
_MIN_PARTIAL = 4  # a query shorter than this must match a whole name
# Trip words the model sometimes lists as places when the request was typed in galig
_NOT_A_PLACE = {
    "аялал",
    "аяллын",
    "аялалийн",
    "аялах",
    "аялмаар",
    "хоног",
    "хоногийн",
    "хоногт",
    "хоногоор",
    "хоногийг",
    "рүү",
    "руу",
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    # й is a distinct Cyrillic letter, not an optional Latin accent.
    text = text.replace("и\u0306", "й")
    text = "".join(c for c in text if not unicodedata.combining(c)).translate(_CYRILLIC_FOLD)
    return " ".join(re.findall(r"\w+", text))


def _significant(text: str) -> str:
    return " ".join(w for w in norm(text).split() if w not in GENERIC)


def starts_word(needle: str, haystack: str) -> bool:
    return bool(needle) and re.search(rf"(^| ){re.escape(needle)}", haystack) is not None


def _match_len(query: str, names: Sequence[str]) -> int:
    """Exact names beat names inside a sentence, which beat partial queries."""
    best = 0
    for raw in names:
        name = _significant(raw)
        if not name:
            continue
        if query == name:
            best = max(best, 3000 + len(name))
        elif starts_word(name, query):
            best = max(best, 2000 + len(name))
        elif len(query) >= _MIN_PARTIAL and starts_word(query, name):
            best = max(best, 1000 + len(query))
    return best


def _by_name(query: str, catalog: Catalog) -> list[str]:
    scored = {
        pid: _match_len(query, (p["name"]["mn"], p["name"]["en"], *p.get("aliases", [])))
        for pid, p in catalog.places.items()
    }
    top = max(scored.values(), default=0)
    return [pid for pid, score in scored.items() if top and score == top]


def _by_region(query: str, catalog: Catalog) -> list[str]:
    words = set(query.split())
    regions = {code for code, aliases in _REGION_WORDS.items() if words & aliases}
    return [pid for pid, p in catalog.places.items() if p["region"] in regions]


def _by_aimag(query: str, catalog: Catalog) -> list[str]:
    aimags = {
        a["name"] for r in catalog.regions for a in r.get("aimags", []) if _match_len(query, (a["name"], a["name_mn"]))
    }
    return [pid for pid, p in catalog.places.items() if p["aimag"] in aimags]


def _rank(catalog: Catalog, place_id: str) -> tuple[bool, int, str]:
    place = catalog.places[place_id]
    return (place["kind"] == "attraction", len(catalog.stays_at(place_id)), place_id)


def _pick(query: str, candidates: list[str], catalog: Catalog, choose: Chooser) -> str:
    if len(candidates) == 1:
        return candidates[0]
    offered = [{"id": pid, **{k: catalog.places[pid][k] for k in ("name", "kind", "aimag")}} for pid in candidates]
    try:
        chosen = choose(query, offered)
    except Exception as exc:  # noqa: BLE001 - any chooser failure falls back to ranking
        log.warning("place choice for %r failed: %s", query, exc)
        chosen = None
    if chosen in candidates:
        return chosen
    return max(candidates, key=lambda pid: _rank(catalog, pid))


def is_trip_phrase(name: str) -> bool:
    words = []
    for word in norm(latin_to_cyrillic(name)).split():
        word = re.sub(r"^\d+", "", word)
        if word and not word.isdigit():
            words.append(word)
    return bool(words) and all(w in _NOT_A_PLACE for w in words)


def _lookup(name: str, catalog: Catalog) -> list[str]:
    query = _significant(name) or norm(name)
    if not query:
        return []
    if set(norm(name).split()) & {"аймаг", "aimag"}:
        return _by_aimag(query, catalog)
    # Keep broad requests broad even when a landmark contains the same word
    # ("Говь" vs "Говь Гурвансайхан", "Хөвсгөл" vs "Хөвсгөл нуур").
    if any(norm(name) in aliases for aliases in _REGION_WORDS.values()):
        return _by_region(query, catalog)
    if any(
        norm(name) in {norm(a["name"]), norm(a["name_mn"])}
        for region in catalog.regions
        for a in region.get("aimags", [])
    ):
        return _by_aimag(query, catalog)
    return _by_name(query, catalog) or _by_region(query, catalog) or _by_aimag(query, catalog)


def candidates(name: str, catalog: Catalog) -> list[str]:
    """Every place the name could mean (empty: none). Galig is tried as Cyrillic when the original misses."""
    found = _lookup(name, catalog)
    cyrillic = latin_to_cyrillic(name)
    if found or norm(cyrillic) == norm(name):
        return found
    return _lookup(cyrillic, catalog)


def resolve(names: Sequence[str], catalog: Catalog, choose: Chooser) -> list[ResolvedPlace]:
    resolved: list[ResolvedPlace] = []
    for name in names:
        if not norm(name) or is_trip_phrase(name):
            continue
        options = candidates(name, catalog)
        if not options:
            resolved.append(ResolvedPlace(query=name, place_id=None, status="unresolved"))
            continue
        chosen = _pick(_significant(name) or norm(name), options, catalog, choose)
        resolved.append(ResolvedPlace(query=name, place_id=chosen, status="included"))
    return resolved
