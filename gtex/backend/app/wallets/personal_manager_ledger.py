from __future__ import annotations

from typing import Any

from sqlalchemy import event

from app.models.wallet import LedgerEntry, LedgerSourceTag, LedgerTransaction

PERSONAL_MANAGER_CREATE_REFERENCE_PREFIX = "personal-manager:create:"


def _is_personal_manager_creation_reference(reference: str | None) -> bool:
    return bool(reference and reference.startswith(PERSONAL_MANAGER_CREATE_REFERENCE_PREFIX))


@event.listens_for(LedgerTransaction, "before_insert", propagate=True)
def _tag_personal_manager_transaction(_: Any, __: Any, target: LedgerTransaction) -> None:
    if _is_personal_manager_creation_reference(target.reference):
        target.source_tag = LedgerSourceTag.PERSONAL_MANAGER_CREATION_SPEND


@event.listens_for(LedgerEntry, "before_insert", propagate=True)
def _tag_personal_manager_entry(_: Any, __: Any, target: LedgerEntry) -> None:
    if _is_personal_manager_creation_reference(target.reference):
        target.source_tag = LedgerSourceTag.PERSONAL_MANAGER_CREATION_SPEND
