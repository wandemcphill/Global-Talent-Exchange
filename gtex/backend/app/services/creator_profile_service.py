from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.creator_profile_status import CreatorProfileStatus
from app.models.creator_profile import CreatorProfile
from app.services.referral_orchestrator import (
    CreatorProfileRecord,
    ReferralActionError,
    ReferralRuntimeStore,
    ShareCodeRecord,
    generate_id,
    utcnow,
)


class CreatorProfileService:
    # TODO: Replace this temporary app-scoped store with Thread A's durable creator profile model/repository when available.
    def __init__(self, store: ReferralRuntimeStore, session: Session | None = None) -> None:
        self.store = store
        self.session = session

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
        if self.session is not None:
            if self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user_id)) is not None:
                raise ReferralActionError("creator_profile_exists")
            if self.session.scalar(select(CreatorProfile).where(CreatorProfile.handle == handle)) is not None:
                raise ReferralActionError("creator_handle_taken")
            profile = CreatorProfile(
                id=generate_id("creator"),
                user_id=user_id,
                handle=handle,
                display_name=display_name,
                tier=tier,
                status=CreatorProfileStatus(status),
                default_share_code=None,
                default_competition_id=default_competition_id,
                revenue_share_percent=revenue_share_percent,
            )
            self.session.add(profile)
            self.session.flush()
            creator = self._from_model(profile)
            self._save(creator)
            return creator
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
        if self.session is not None:
            profile = self._get_model_by_user_id(user_id)
            profile.default_share_code = share_code.code
            self.session.flush()
            updated = self._from_model(profile)
            self._save(updated)
            return updated
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
        if self.session is not None:
            profile = self._get_model_by_user_id(user_id)
            profile.display_name = display_name or profile.display_name
            profile.tier = tier or profile.tier
            if status is not None:
                profile.status = CreatorProfileStatus(status)
            if default_competition_id is not None:
                profile.default_competition_id = default_competition_id
            if revenue_share_percent is not None:
                profile.revenue_share_percent = revenue_share_percent
            self.session.flush()
            updated = self._from_model(profile)
            self._save(updated)
            return updated
        with self.store.lock:
            creator = self._get_by_user_id(user_id)
            updated = replace(
                creator,
                display_name=display_name or creator.display_name,
                tier=tier or creator.tier,
                status=status or creator.status,
                default_competition_id=(
                    default_competition_id if default_competition_id is not None else creator.default_competition_id
                ),
                revenue_share_percent=(
                    revenue_share_percent if revenue_share_percent is not None else creator.revenue_share_percent
                ),
                updated_at=utcnow(),
            )
            self._save(updated)
            return updated

    def get_me(self, user_id: str) -> CreatorProfileRecord:
        if self.session is not None:
            creator = self.get_optional(user_id)
            if creator is None:
                raise ReferralActionError("creator_not_found")
            return creator
        with self.store.lock:
            return self._get_by_user_id(user_id)

    def get_by_handle(self, handle: str) -> CreatorProfileRecord:
        if self.session is not None:
            profile = self.session.scalar(select(CreatorProfile).where(CreatorProfile.handle == handle))
            if profile is None:
                raise ReferralActionError("creator_not_found")
            creator = self._from_model(profile)
            self._save(creator)
            return creator
        with self.store.lock:
            creator_id = self.store.creator_ids_by_handle.get(handle)
            if creator_id is None:
                raise ReferralActionError("creator_not_found")
            return self.store.creators_by_id[creator_id]

    def get_optional(self, user_id: str) -> CreatorProfileRecord | None:
        if self.session is not None:
            profile = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user_id))
            if profile is None:
                return None
            creator = self._from_model(profile)
            self._save(creator)
            return creator
        with self.store.lock:
            return self.store.creators_by_user_id.get(user_id)

    def get_by_id(self, creator_id: str) -> CreatorProfileRecord:
        if self.session is not None:
            profile = self.session.get(CreatorProfile, creator_id)
            if profile is None:
                raise ReferralActionError("creator_not_found")
            creator = self._from_model(profile)
            self._save(creator)
            return creator
        with self.store.lock:
            creator = self.store.creators_by_id.get(creator_id)
            if creator is None:
                raise ReferralActionError("creator_not_found")
            return creator

    def list_all(self) -> tuple[CreatorProfileRecord, ...]:
        if self.session is not None:
            profiles = tuple(
                self.session.scalars(
                    select(CreatorProfile).order_by(CreatorProfile.created_at, CreatorProfile.id)
                ).all()
            )
            creators = tuple(self._from_model(profile) for profile in profiles)
            for creator in creators:
                self._save(creator)
            return creators
        with self.store.lock:
            return tuple(self.store.creators_by_id.values())

    def _get_by_user_id(self, user_id: str) -> CreatorProfileRecord:
        creator = self.store.creators_by_user_id.get(user_id)
        if creator is None:
            raise ReferralActionError("creator_not_found")
        return creator

    def _get_model_by_user_id(self, user_id: str) -> CreatorProfile:
        profile = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user_id))
        if profile is None:
            raise ReferralActionError("creator_not_found")
        return profile

    @staticmethod
    def _from_model(profile: CreatorProfile) -> CreatorProfileRecord:
        status = profile.status.value if hasattr(profile.status, "value") else str(profile.status)
        return CreatorProfileRecord(
            creator_id=profile.id,
            user_id=profile.user_id,
            handle=profile.handle,
            display_name=profile.display_name,
            tier=profile.tier,
            status=status,
            default_share_code_id=None,
            default_share_code=profile.default_share_code,
            default_competition_id=profile.default_competition_id,
            revenue_share_percent=profile.revenue_share_percent,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    def _save(self, creator: CreatorProfileRecord) -> None:
        self.store.creators_by_user_id[creator.user_id] = creator
        self.store.creator_ids_by_handle[creator.handle] = creator.creator_id
        self.store.creators_by_id[creator.creator_id] = creator
