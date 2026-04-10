from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AdminRuntimeState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_runtime_states"

    state_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
