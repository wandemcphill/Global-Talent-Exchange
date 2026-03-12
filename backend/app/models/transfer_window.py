from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TransferWindow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transfer_windows"

    territory_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="upcoming", server_default="upcoming", index=True)
    opens_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    closes_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
