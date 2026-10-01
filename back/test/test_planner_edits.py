"""A traveller can move a night or pick another stay without the model rewriting the route."""

from datetime import UTC, date, datetime, timedelta

import mongomock

from app.modules.orchestrator.assembler import assemble_blocks, trade_nights
from app.modules.orchestrator.catalog import Catalog
from app.modules.orchestrator.service import PROPOSALS, adjust_nights, stay_choices, swap_stay
from app.modules.orchestrator.types import PlanRequest
from app.seeds.mock_seed import load_mock_collections


def _db():
    db = mongomock.MongoClient(tz_aware=True)["test_planner_edits"]
    load_mock_collections(db, real_server=False)
    return db


def test_a_night_moves_to_the_other_end_of_the_route():
    assert trade_nights([("place_kharkhorin", 1), ("place_uvs_lake", 6)], "place_kharkhorin", 1) == [
        ("place_kharkhorin", 2),
        ("place_uvs_lake", 5),
    ]
    assert trade_nights([("place_kharkhorin", 1), ("place_uvs_lake", 6)], "place_kharkhorin", -1) is None


def test_adjusting_nights_keeps_the_stops_in_order_and_uses_database_stays():
    db = _db()
    request = PlanRequest(
        text="Увс нуур",
        guests=2,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 8),
        budget_mnt=3_500_000,
        style="comfort",
        lang="mn",
    )
    assembly = assemble_blocks(db, Catalog.load(db), request, [("place_murun", 1), ("place_khatgal", 6)])
    now = datetime.now(UTC)
    db[PROPOSALS].insert_one(
        {
            "_id": "plan_edit",
            "version": 1,
            "request": request.model_dump(mode="json"),
            "changes": [],
            "days": [d.model_dump() for d in assembly.days],
            "totals": assembly.totals.model_dump(),
            "warnings": list(assembly.warnings),
            "fit": assembly.fit.model_dump(),
            "summary": "ноорог",
            "nights_hint": {},
            "accepted": None,
            "created_at": now,
            "expires_at": now + timedelta(hours=1),
        }
    )

    updated = adjust_nights(db, "plan_edit", "place_murun", 1, now)
    stayed = [d for d in updated["days"] if d["stay"]]
    assert [d["to_place_id"] for d in stayed] == ["place_murun", "place_khatgal"]
    assert stayed[0]["stay"]["nights"] == 2
    assert stayed[1]["stay"]["nights"] == 5

    choices = stay_choices(db, "plan_edit", "place_khatgal", now, "mn")
    ids = {c["id"] for c in choices}
    assert {"stay_khatgal_camp_blue_pearl", "stay_khatgal_guesthouse_lake"} <= ids
    other = next(stay_id for stay_id in ids if stay_id != stayed[1]["stay"]["stay_id"])
    swapped = swap_stay(db, "plan_edit", "place_khatgal", other, now)
    lake = next(d for d in swapped["days"] if d["stay"] and d["to_place_id"] == "place_khatgal")
    assert lake["stay"]["stay_id"] == other
