"""Prepared scenic routes, used when the traveller did not name a place.

Each route is four to six real stops. Words in the request pick one: a lake or river, mountains
and rock, or sand desert. "Far" picks the longest route that still fits the dates. A named place
is never replaced by one of these.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.modules.orchestrator.assembler import leg, trip_fit
from app.modules.orchestrator.catalog import HUB, Catalog
from app.modules.orchestrator.resolver import GENERIC, candidates, norm, starts_word
from app.utils.galig import latin_to_cyrillic

_THEMES: dict[str, set[str]] = {
    "water": {norm(w) for w in ("нуур", "устай", "ус", "гол", "lake", "river", "water")},
    "mountain": {norm(w) for w in ("уул", "хад", "хадан", "mountain", "rock", "peak")},
    "desert": {norm(w) for w in ("элс", "элсэн", "цөл", "цөлийн", "говь", "gobi", "govi", "sand", "desert", "dune")},
}
_FAR = {norm(w) for w in ("хол", "холын", "far", "remote")}
_NEAR = {norm(w) for w in ("ойр", "ойрхон", "near", "close")}
_VAGUE = set().union(*_THEMES.values(), _FAR, _NEAR, GENERIC) | {
    norm(w)
    for w in (
        "газар",
        "place",
        "аймаг",
        "aimag",
        "баруун",
        "зүүн",
        "хойд",
        "өмнөд",
        "west",
        "east",
        "north",
        "south",
    )
}


@dataclass(frozen=True)
class ScenicRoute:
    theme: str
    far: bool
    places: tuple[str, ...]


# Road order, roughly outward from Ulaanbaatar, so a short trip keeps the nearer stops.
ITINERARIES: tuple[ScenicRoute, ...] = (
    ScenicRoute(
        "desert",
        True,
        (
            "place_mandalgovi",
            "place_tsagaan_suvarga",
            "place_dalanzadgad",
            "place_yolyn_am",
            "place_bayanzag",
            "place_khongoryn_els",
        ),
    ),
    ScenicRoute(
        "water",
        True,
        (
            "place_erdenet",
            "place_uran_togoo",
            "place_murun",
            "place_khatgal",
            "place_khuvsgul_lake",
            "place_khankh",
        ),
    ),
    ScenicRoute(
        "mountain",
        True,
        (
            "place_khogno_khan",
            "place_erdene_zuu",
            "place_orkhon_waterfall",
            "place_tsetserleg",
            "place_khorgo",
            "place_terkhiin_tsagaan",
        ),
    ),
    ScenicRoute(
        "mountain",
        False,
        (
            "place_terelj",
            "place_ariyabal",
            "place_khustain_nuruu",
            "place_manzushir",
        ),
    ),
    ScenicRoute(
        "water",
        False,
        (
            "place_ugii_nuur",
            "place_kharkhorin",
            "place_erdene_zuu",
            "place_orkhon_waterfall",
            "place_khogno_khan",
        ),
    ),
    ScenicRoute(
        "desert",
        False,
        (
            "place_mandalgovi",
            "place_tsagaan_suvarga",
            "place_khamar",
            "place_dalanzadgad",
            "place_yolyn_am",
        ),
    ),
)


def _words(text: str) -> set[str]:
    return set(norm(latin_to_cyrillic(text)).split())


def theme_of(text: str, hinted: str = "") -> str | None:
    """water, mountain, or desert, from the words they used. The model's hint fills a gap."""
    words = _words(text)
    scores = {name: len(words & vocab) for name, vocab in _THEMES.items()}
    best = max(scores, key=lambda name: scores[name])
    if scores[best]:
        return best
    return hinted if hinted in _THEMES else None


def wants_far(text: str) -> bool | None:
    words = _words(text)
    if words & _FAR:
        return True
    if words & _NEAR:
        return False
    return None


def is_specific(query: str) -> bool:
    """A real place name, not a landscape or region word such as говь, нуур, or уул."""
    words = [w for w in norm(latin_to_cyrillic(query)).split() if w not in GENERIC and not w.isdigit()]
    return any(w not in _VAGUE and len(w) >= 3 for w in words)


def mentioned(query: str, text: str) -> bool:
    """The place name actually appears in what the traveller wrote (case endings included)."""
    said = norm(latin_to_cyrillic(text))
    words = [w for w in norm(latin_to_cyrillic(query)).split() if w not in GENERIC and not w.isdigit()]
    distinctive = [w for w in words if len(w) >= 4] or words
    return any(starts_word(w, said) for w in distinctive)


def _named_first(word: str, name: dict[str, str]) -> bool:
    """The word starts the place's own name in some language ("Хөвсгөл нуур", not "Цагааннуур, Хөвсгөл")."""
    needle = norm(word)
    return any(norm(latin_to_cyrillic(value)).startswith(needle) for value in name.values() if value)


def named_words(text: str, catalog: Catalog) -> list[str]:
    """Place names written in the request that match exactly one catalog place."""
    found: list[str] = []
    seen: set[str] = set()
    for word in re.findall(r"\w+", latin_to_cyrillic(text)):
        if not is_specific(word):
            continue
        options = [pid for pid in candidates(word, catalog) if pid != HUB]
        query = word
        if len(options) > 1:
            # "Хөвсгөл" also appears in "Tsagaannuur, Khövsgöl": keep the place whose own name begins with it, and
            # ask for it by its full name so resolving it again lands on the same place
            options = [pid for pid in options if _named_first(word, catalog.places[pid]["name"])]
            if len(options) == 1:
                query = catalog.places[options[0]]["name"]["mn"]
        if len(options) != 1 or options[0] in seen:
            continue
        seen.add(options[0])
        found.append(query)
    return found


def _usable(route: ScenicRoute, catalog: Catalog, avoid: set[str]) -> list[str]:
    return [pid for pid in route.places if pid not in avoid and pid in catalog.places]


def _reach(catalog: Catalog, stops: Sequence[str]) -> int:
    return max(leg(catalog, HUB, pid)[1] for pid in stops)


def choose_itinerary(
    catalog: Catalog, *, theme: str | None, far: bool | None, nights: int, avoid: set[str]
) -> list[str]:
    """Stops from the prepared route that matches the request and fits the number of nights."""
    usable = {r: stops for r in ITINERARIES if (stops := _usable(r, catalog, avoid))}
    pool = list(usable)
    if not pool:
        return []
    if theme:
        themed = [r for r in pool if r.theme == theme]
        pool = themed or pool
    feasible = [r for r in pool if trip_fit(catalog, usable[r], nights).feasible]
    pool = feasible or pool
    if far is True:
        distant = [r for r in pool if r.far]
        pool = distant or pool
        best = max(pool, key=lambda r: _reach(catalog, usable[r]))
    elif far is False or (theme is None and nights < 5):
        close = [r for r in pool if not r.far]
        best = close[0] if close else pool[0]
    else:
        distant = [r for r in pool if r.far]
        best = distant[0] if distant else pool[0]
    stops = usable[best]
    count = len(stops) if nights >= 6 else max(2, min(len(stops), max(nights, 1)))
    return stops[:count]
