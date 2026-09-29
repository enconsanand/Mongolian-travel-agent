"""Pick one language out of bilingual ``{"mn": ..., "en": ...}`` values in documents."""

from typing import Annotated, Any, Literal

from fastapi import Header

Lang = Literal["mn", "en"]
SUPPORTED_LANGS: tuple[Lang, ...] = ("mn", "en")
DEFAULT_LANG: Lang = "mn"


def parse_accept_language(header: str | None) -> Lang:
    """Return the first supported language in an Accept-Language header, else Mongolian."""
    if not header:
        return DEFAULT_LANG
    ranked: list[tuple[float, str]] = []
    for part in header.split(","):
        tag, _, params = part.strip().partition(";")
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                quality = 1.0  # malformed weight: ignore it
        if quality > 0:  # q=0 means "not acceptable"
            ranked.append((quality, tag.strip().lower().split("-")[0]))
    for _, code in sorted(ranked, key=lambda item: item[0], reverse=True):
        if code in SUPPORTED_LANGS:
            return code  # type: ignore[return-value]
    return DEFAULT_LANG


def get_lang(accept_language: Annotated[str | None, Header()] = None) -> Lang:
    """FastAPI dependency: the caller's language from the Accept-Language header."""
    return parse_accept_language(accept_language)


def _is_localized(value: dict) -> bool:
    return bool(value) and set(value) <= set(SUPPORTED_LANGS)


def localize(value: Any, lang: Lang) -> Any:
    """Recursively replace every ``{"mn", "en"}`` dict with the text in ``lang``."""
    if isinstance(value, dict):
        if _is_localized(value):
            return value.get(lang) or next(iter(value.values()))
        return {k: localize(v, lang) for k, v in value.items()}
    if isinstance(value, list):
        return [localize(v, lang) for v in value]
    return value
