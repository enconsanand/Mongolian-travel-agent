"""Schemas vs. mock data, and the MongoDB validators generated from the schemas."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.db.validators import NOT_VALIDATED, json_schema_for, validator_for
from app.schemas.travel import DOC_MODELS, StayDoc

DATA = Path(settings.MOCK_DATA_DIR)


@pytest.mark.parametrize("collection", sorted(DOC_MODELS))
def test_every_mock_document_matches_its_schema(collection):
    docs = json.loads((DATA / f"{collection}.json").read_text(encoding="utf-8"))
    assert docs, f"{collection} has no mock documents"
    for doc in docs:
        DOC_MODELS[collection].model_validate(doc)


def test_every_mock_file_has_a_schema():
    files = {p.stem for p in DATA.glob("*.json")} - {"image_pool", "images", "translations.mn"}
    assert files == set(DOC_MODELS)


def test_schema_rejects_unknown_fields_and_bad_enums():
    stay = json.loads((DATA / "stays.json").read_text(encoding="utf-8"))[0]
    with pytest.raises(ValidationError):
        StayDoc.model_validate({**stay, "unexpected": 1})
    with pytest.raises(ValidationError):
        StayDoc.model_validate({**stay, "type": "castle"})
    with pytest.raises(ValidationError):
        StayDoc.model_validate({**stay, "name": "only one language"})


def _walk(node):
    """Yield every schema node (the ``properties`` maps themselves are field names, not schemas)."""
    if isinstance(node, dict):
        yield node
        for key, value in node.items():
            children = value.values() if key == "properties" else [value]
            for child in children:
                yield from _walk(child)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


@pytest.mark.parametrize("collection", sorted(set(DOC_MODELS) - NOT_VALIDATED))
def test_validator_uses_only_mongodb_json_schema_keywords(collection):
    schema = json_schema_for(DOC_MODELS[collection])
    for node in _walk(schema):
        assert "$ref" not in node and "type" not in node and "title" not in node and "const" not in node
        if "exclusiveMinimum" in node:
            assert node["exclusiveMinimum"] is True
    assert schema["bsonType"] == "object"
    assert schema["additionalProperties"] is False
    assert "_id" in schema["properties"]


def test_stay_validator_shape():
    schema = validator_for(StayDoc)["$jsonSchema"]
    assert set(schema["required"]) >= {"_id", "name", "type", "location", "units"}
    assert schema["properties"]["type"]["enum"] == ["ger_camp", "guesthouse", "hotel", "house"]
    assert schema["properties"]["name"]["required"] == ["mn", "en"]
    assert schema["properties"]["rating"]["maximum"] == 5
