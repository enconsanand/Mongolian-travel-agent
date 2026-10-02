"""Offline catalog integrity and reproducibility, including source metadata."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

from app.core.config import settings
from app.schemas.travel import PlaceDoc

DATA = Path(settings.MOCK_DATA_DIR).parent


def test_curated_landmarks_have_unique_ids_bilingual_text_and_sourced_geojson():
    curated = json.loads((DATA / "landmarks/catalog.json").read_text())
    generated = json.loads((DATA / "mock/places.json").read_text())
    by_id = {p["_id"]: p for p in generated}
    assert len(by_id) == len(generated)
    assert len(curated) >= 100
    assert len({p["_id"] for p in curated}) == len(curated)
    assert {p["region"] for p in generated} == {"north", "south", "east", "west", "hub"}
    for place in curated:
        doc = by_id[place["_id"]]
        PlaceDoc.model_validate(doc, strict=True)
        assert doc["is_mock"] is False
        assert doc["name"]["mn"] != doc["name"]["en"]
        assert doc["note"]["mn"] and doc["note"]["en"]
        assert doc["aliases"] and all(a.strip() for a in doc["aliases"])
        lng, lat = doc["location"]["coordinates"]
        # Regional bounds catch swapped GeoJSON coordinates and foreign homonyms.
        # They are not a claim of cadastral/border precision.
        assert 87 <= lng <= 120 and 41 <= lat <= 53
        assert doc["coordinate_source"]["url"].startswith("https://")
        assert doc["coordinate_source"]["source_id"]
        assert doc["coordinate_source"]["coordinate_role"] in {"landmark", "representative_point"}


def test_generator_reproduces_every_committed_collection_offline(tmp_path):
    shutil.copytree(DATA / "mock", tmp_path / "mock")
    shutil.copytree(DATA / "landmarks", tmp_path / "landmarks")
    subprocess.run([sys.executable, str(tmp_path / "mock/generate.py")], check=True, capture_output=True)
    for source in (DATA / "mock").glob("*.json"):
        generated = json.loads((tmp_path / "mock" / source.name).read_text())
        committed = json.loads(source.read_text())
        assert generated == committed, source.name
