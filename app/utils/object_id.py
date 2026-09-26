from typing import Annotated, Any
from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema


def validate_object_id(v: Any) -> str:
    """Validates that a value is or can be converted to a valid BSON ObjectId string."""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId format: '{v}'. Must be a 24-character hex string.")
        return v
    raise ValueError(f"Invalid ObjectId type: {type(v)}. Must be ObjectId or str.")


PyObjectId = Annotated[
    str,
    BeforeValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
    WithJsonSchema({"type": "string", "example": "65f1a2b3c4d5e6f7a8b9c0d1", "description": "24-character MongoDB ObjectId hex string"}),
]


def to_object_id(id_val: str | ObjectId) -> ObjectId:
    """Safely converts a string to a BSON ObjectId, raising ValueError on invalid format."""
    if isinstance(id_val, ObjectId):
        return id_val
    try:
        return ObjectId(id_val)
    except (InvalidId, TypeError) as exc:
        raise ValueError(f"Invalid ObjectId format: '{id_val}'. Must be a 24-character hex string.") from exc


def clean_mongo_doc(doc: Any) -> Any:
    """Recursively converts MongoDB BSON types (ObjectId, Decimal128) to JSON/Pydantic-friendly types."""
    from bson.decimal128 import Decimal128
    from decimal import Decimal

    if isinstance(doc, dict):
        cleaned = {}
        for k, v in doc.items():
            cleaned[k] = clean_mongo_doc(v)
        return cleaned
    elif isinstance(doc, list):
        return [clean_mongo_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, Decimal128):
        return doc.to_decimal()
    return doc
