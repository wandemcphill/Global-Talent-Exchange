from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


def make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return make_json_safe(value.value)
    if isinstance(value, BaseModel):
        return make_json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [make_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return make_json_safe(value.model_dump(mode="json"))
    return str(value)


__all__ = ["make_json_safe"]
