"""An event the traveller names but that does not happen on the trip's dates is reported, not silently dropped."""

from datetime import date

from app.modules.orchestrator.service import event_off_dates
from app.modules.orchestrator.types import PlanRequest


def event(mn: str, en: str, start: str, end: str) -> dict:
    return {"name": {"mn": mn, "en": en}, "start_date": start, "end_date": end}


class Events:
    events = [
        event("АРА фестиваль", "ARA Festival", "2026-07-01", "2026-08-01"),
        event("Бүргэдийн баяр", "Eagle Festival", "2026-10-03", "2026-10-04"),
    ]


def ask(text: str, start: date, end: date, changes: tuple[str, ...] = ()) -> bool:
    request = PlanRequest(text=text, guests=2, start_date=start, end_date=end, style="comfort")
    return event_off_dates(Events(), request, changes)  # type: ignore[arg-type]


def test_a_named_event_in_another_year_is_off_dates():
    assert ask("Цэцэрлэг. АРА фестиваль.. 3 хүн", date(2027, 7, 1), date(2027, 7, 4))


def test_a_named_event_on_the_trip_dates_is_fine():
    assert not ask("АРА фестиваль үзнэ", date(2026, 7, 2), date(2026, 7, 5))
    assert not ask("eagle festival please", date(2026, 10, 2), date(2026, 10, 5))


def test_no_named_event_or_a_later_change_naming_one():
    assert not ask("Хөвсгөл явна", date(2027, 7, 1), date(2027, 7, 4))
    assert ask("Хөвсгөл явна", date(2027, 7, 1), date(2027, 7, 4), ("Бүргэдийн баяр нэм",))
