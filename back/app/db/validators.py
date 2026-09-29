"""MongoDB ``$jsonSchema`` validators generated from the Pydantic document schemas.

MongoDB's $jsonSchema is JSON Schema draft 4 with ``bsonType`` and without ``$ref``, so the
Pydantic schema is inlined and translated. This keeps one source of truth (``app.schemas.travel``).
"""

from typing import Any

from pymongo.database import Database

from app.schemas.travel import DOC_MODELS, Doc

_BSON_TYPES: dict[str, str | list[str]] = {
    "string": "string",
    "integer": ["int", "long"],
    "number": ["double", "int", "long", "decimal"],
    "boolean": "bool",
    "object": "object",
    "array": "array",
    "null": "null",
}
# JSON Schema keywords MongoDB understands and that we copy as-is
_KEEP = {"required", "enum", "minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength", "pattern"}

# ``users`` also holds login fields owned by app.models.User, so it has no strict validator
NOT_VALIDATED = {"users"}


def _convert(node: Any, defs: dict[str, Any]) -> Any:
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        return _convert(defs[node["$ref"].rsplit("/", 1)[-1]], defs)

    out: dict[str, Any] = {}
    for key, value in node.items():
        if key == "type":
            out["bsonType"] = _BSON_TYPES[value]
        elif key == "const":
            out["enum"] = [value]
        elif key == "exclusiveMinimum":  # draft 2020 number -> draft 4 boolean
            out["minimum"], out["exclusiveMinimum"] = value, True
        elif key == "exclusiveMaximum":
            out["maximum"], out["exclusiveMaximum"] = value, True
        elif key == "properties":
            out["properties"] = {name: _convert(prop, defs) for name, prop in value.items()}
        elif key == "items":
            out["items"] = _convert(value, defs)
        elif key == "anyOf":
            out["anyOf"] = [_convert(option, defs) for option in value]
        elif key == "additionalProperties":
            out["additionalProperties"] = value if isinstance(value, bool) else _convert(value, defs)
        elif key in _KEEP:
            out[key] = value
        # title, default, description, format, propertyNames, $defs ... are not supported: dropped
    return out


def json_schema_for(model: type[Doc]) -> dict[str, Any]:
    schema = model.model_json_schema(by_alias=True, mode="validation")
    return _convert(schema, schema.get("$defs", {}))


def validator_for(model: type[Doc]) -> dict[str, Any]:
    return {"$jsonSchema": json_schema_for(model)}


def create_validated_collection(db: Database, name: str, schema: str | None = None) -> None:
    """Create collection ``name`` (must not exist) with the validator of collection ``schema`` (default: name)."""
    model = DOC_MODELS.get(schema or name)
    if model is None or (schema or name) in NOT_VALIDATED:
        db.create_collection(name)
        return
    db.create_collection(name, validator=validator_for(model), validationLevel="strict", validationAction="error")


def refresh_validator(db: Database, name: str) -> None:
    """Replace the validator of an existing collection with the current schema (needs collMod rights)."""
    model = DOC_MODELS.get(name)
    if model is None or name in NOT_VALIDATED:
        return
    db.command({"collMod": name, "validator": validator_for(model), "validationLevel": "strict"})
