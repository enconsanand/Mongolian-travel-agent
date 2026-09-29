"""Language selection and localization of bilingual documents."""

import pytest

from app.utils.i18n import localize, parse_accept_language


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "mn"),
        ("", "mn"),
        ("en-US,en;q=0.9", "en"),
        ("mn-MN", "mn"),
        ("fr-FR,en;q=0.5", "en"),
        ("de,fr", "mn"),
        ("en;q=0.3,mn;q=0.8", "mn"),
        ("en;q=abc", "en"),
        ("en;q=0, fr", "mn"),
    ],
)
def test_parse_accept_language(header, expected):
    assert parse_accept_language(header) == expected


def test_localize_picks_language_recursively():
    doc = {
        "_id": "route_x",
        "name": {"mn": "Улаанбаатар – Дархан", "en": "Ulaanbaatar to Darkhan"},
        "segments": [{"notes": {"mn": "Зам", "en": "Road"}, "km": 10}],
        "highlights": [{"mn": "Нуур", "en": "Lake"}],
        "surface_km": {"paved": 200},
    }
    assert localize(doc, "en") == {
        "_id": "route_x",
        "name": "Ulaanbaatar to Darkhan",
        "segments": [{"notes": "Road", "km": 10}],
        "highlights": ["Lake"],
        "surface_km": {"paved": 200},
    }
    assert localize(doc, "mn")["name"] == "Улаанбаатар – Дархан"


def test_localize_falls_back_when_language_missing():
    assert localize({"title": {"en": "Only English"}}, "mn") == {"title": "Only English"}
    assert localize({}, "mn") == {}
