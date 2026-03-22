from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from app.services.referral_orchestrator import (
    CreatorProfileRecord,
    ReferralActionError,
    ReferralStore,
    ShareCodeRecord,
    generate_id,
    utcnow,
)


class CreatorProfileService:
    # TODO: Replace this temporary app-scoped store with Thread A's durable creator profile model/repository when available.
    def __init__(self, store: ReferralStore) -> None:
        self.store = store

    def create_profile(
        self,
        *,
        user_id: str,
        username: str,
        handle: str,
        display_name: str,
        tier: str,
        status: str,
        default_competition_id: str | None,
        revenue_share_percent: Decimal | None,
    ) -> CreatorProfileRecord:
        with self.store.lock:
            if user_id in self.store.creators_by_user_id:
                raise ReferralActionError("creator_profile_exists")
            if handle in self.store.creator_ids_by_handle:
                raise ReferralActionError("creator_handle_taken")
            now = utcnow()
            creator = CreatorProfileRecord(
                creator_id=generate_id("creator"),
                user_id=user_id,
                handle=handle,
                display_name=display_name,
                tier=tier,
                status=status,
                default_share_code_id=None,
                default_share_code=None,
                default_competition_id=default_competition_id,
                revenue_share_percent=revenue_share_percent,
                created_at=now,
                updated_at=now,
            )
            self.store.creators_by_user_id[user_id] = creator
            self.store.creator_ids_by_handle[handle] = creator.creator_id
            self.store.creators_by_id[creator.creator_id] = creator
            return creator

    def attach_default_share_code(self, *, user_id: str, share_code: ShareCodeRecord) -> CreatorProfileRecord:
        with self.store.lock:
            creator = self._get_by_user_id(user_id)
            updated = replace(
                creator,
                default_share_code_id=share_code.share_code_id,
                default_share_code=share_code.code,
                updated_at=utcnow(),
            )
            self._save(updated)
            return updated

    def update_profile(
        self,
        *,
        user_id: str,
        display_name: str | None,
        tier: str | None,
        status: str | None,
        default_competition_id: str | None,
        revenue_share_percent: Decimal | None,
    ) -> CreatorProfileRecord:
        with self.store.lock:
            creator = self._get_by_user_id(user_id)
            updated = replace(
                creator,
                display_name=display_name or creator.display_name,
                tier=tier or creator.tier,
                status=status or creator.status,
                default_competition_id=default_competition_id if default_competition_id is not None else creator.default_competition_id,
                revenue_share_percent=revenue_share_percent if revenue_share_percent is not None else creator.revenue_share_percent,
                updated_at=utcnow(),
            )
            self._save(updated)
            return updated

    def get_me(self, user_id: str) -> CreatorProfileRecord:
        with self.store.lock:
            return self._get_by_user_id(user_id)

    def get_by_handle(self, handle: str) -> CreatorProfileRecord:
        with self.store.lock:
            creator_id = self.store.creator_ids_by_handle.get(handle)
            if creator_id is None:
                raise ReferralActionError("creator_not_found")
            return self.store.creators_by_id[creator_id]

    def get_optional(self, user_id: str) -> CreatorProfileRecord | None:
        with self.store.lock:
            return self.store.creators_by_user_id.get(user_id)

    def _get_by_user_id(self, user_id: str) -> CreatorProfileRecord:
        creator = self.store.creators_by_user_id.get(user_id)
        if creator is None:
            raise ReferralActionError("creator_not_found")
        return creator

    def _save(self, creator: CreatorProfileRecord) -> None:
        self.store.creators_by_user_id[creator.user_id] = creator
        self.store.creators_by_id[creator.creator_id] = creator
