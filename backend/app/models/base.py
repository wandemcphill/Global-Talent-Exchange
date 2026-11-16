from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, Final
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SqlAlchemyEnum, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION: Final[dict[str, str]] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _str_enum_values(enum_class: type[enum.Enum]) -> list[str]:
    return [str(member.value) for member in enum_class]


class CaseInsensitiveStrEnum(SqlAlchemyEnum):
    """Non-native StrEnum column that writes .value and reads any legacy casing."""

    def __init__(self, *enums: Any, **kw: Any) -> None:
        kw.setdefault("native_enum", False)
        first_enum = (
            enums[0] if enums else (kw["_enums"][0] if isinstance(kw.get("_enums"), tuple) and kw["_enums"] else None)
        )
        if isinstance(first_enum, type) and issubclass(first_enum, enum.Enum):
            kw.setdefault("values_callable", _str_enum_values)
        super().__init__(*enums, **kw)

    def _setup_for_values(self, values: Any, objects: Any, kw: Any) -> None:
        super()._setup_for_values(values, objects, kw)
        self._ci_object_lookup: dict[str, Any] = {}
        if self.enum_class is not None:
            for member_name, member in reversed(list(self.enum_class.__members__.items())):
                self._ci_object_lookup[member_name.lower()] = member
                self._ci_object_lookup[str(member.value).lower()] = member
        for value, obj in zip(reversed(values), reversed(objects)):
            self._ci_object_lookup[str(value).lower()] = obj

    def _object_value_for_elem(self, elem: Any) -> Any:
        if elem in self._object_lookup:
            return self._object_lookup[elem]
        if isinstance(elem, str):
            matched = self._ci_object_lookup.get(elem.strip().lower())
            if matched is not None:
                return matched
        return super()._object_value_for_elem(elem)

    def adapt(self, cls: type[Any], **kw: Any) -> Any:
        if self.values_callable is not None:
            kw.setdefault("values_callable", self.values_callable)
        kw.setdefault("native_enum", self.native_enum)
        return super().adapt(cls, **kw)


def generate_uuid() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
