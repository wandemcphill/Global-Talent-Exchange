from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.creator_profile import CreatorProfile
from app.models.referral_attribution import ReferralAttribution
from app.models.referral_event import ReferralEvent
from app.models.share_code import ShareCode
from app.services.referral_orchestrator import CreatorCompetitionLinkRecord, ReferralRuntimeStore

_QUALIFIED_JOIN_MILESTONES = {
    "first_competition_joined",
    "first_paid_competition_joined",
    "first_creator_competition_joined",
}


class CreatorCompetitionLinkService:
    # TODO: Replace these lightweight links with Thread A's durable creator/share-code associations when available.
    def __init__(self, store: ReferralRuntimeStore, session: Session | None = None) -> None:
        self.store = store
        self.session = session

    def link_competition(
        self,
        *,
        creator_id: str,
        competition_id: str,
        linked_share_code: str | None,
    ) -> None:
        if self.session is not None:
            return
        title = self._resolve_competition_title(competition_id)
        with self.store.lock:
            creator_links = self.store.creator_competitions.setdefault(creator_id, {})
            existing = creator_links.get(competition_id)
            if existing is None:
                creator_links[competition_id] = CreatorCompetitionLinkRecord(
                    competition_id=competition_id,
                    title=title,
                    linked_share_code=linked_share_code,
                    active_participants=0,
                    attributed_signups=0,
                    qualified_joins=0,
                )
                return
            creator_links[competition_id] = CreatorCompetitionLinkRecord(
                competition_id=existing.competition_id,
                title=existing.title,
                linked_share_code=linked_share_code or existing.linked_share_code,
                active_participants=existing.active_participants,
                attributed_signups=existing.attributed_signups,
                qualified_joins=existing.qualified_joins,
            )

    def record_signup(self, *, creator_id: str | None, competition_id: str | None) -> None:
        if creator_id is None or competition_id is None:
            return
        if self.session is not None:
            return
        with self.store.lock:
            link = self.store.creator_competitions.setdefault(creator_id, {}).setdefault(
                competition_id,
                CreatorCompetitionLinkRecord(
                    competition_id=competition_id,
                    title=self._resolve_competition_title(competition_id),
                    linked_share_code=None,
                    active_participants=0,
                    attributed_signups=0,
                    qualified_joins=0,
                ),
            )
            self.store.creator_competitions[creator_id][competition_id] = CreatorCompetitionLinkRecord(
                competition_id=link.competition_id,
                title=link.title,
                linked_share_code=link.linked_share_code,
                active_participants=link.active_participants,
                attributed_signups=link.attributed_signups + 1,
                qualified_joins=link.qualified_joins,
            )

    def record_qualified_join(self, *, creator_id: str | None, competition_id: str | None) -> None:
        if creator_id is None or competition_id is None:
            return
        if self.session is not None:
            return
        with self.store.lock:
            link = self.store.creator_competitions.setdefault(creator_id, {}).setdefault(
                competition_id,
                CreatorCompetitionLinkRecord(
                    competition_id=competition_id,
                    title=self._resolve_competition_title(competition_id),
                    linked_share_code=None,
                    active_participants=0,
                    attributed_signups=0,
                    qualified_joins=0,
                ),
            )
            self.store.creator_competitions[creator_id][competition_id] = CreatorCompetitionLinkRecord(
                competition_id=link.competition_id,
                title=link.title,
                linked_share_code=link.linked_share_code,
                active_participants=link.active_participants + 1,
                attributed_signups=link.attributed_signups,
                qualified_joins=link.qualified_joins + 1,
            )

    def list_for_creator(self, creator_id: str) -> list[CreatorCompetitionLinkRecord]:
        if self.session is not None:
            profile = self.session.get(CreatorProfile, creator_id)
            if profile is None:
                return []

            records: dict[str, CreatorCompetitionLinkRecord] = {}

            def upsert(competition_id: str, linked_share_code: str | None) -> None:
                existing = records.get(competition_id)
                if existing is None:
                    records[competition_id] = CreatorCompetitionLinkRecord(
                        competition_id=competition_id,
                        title=self._resolve_competition_title(competition_id),
                        linked_share_code=linked_share_code,
                        active_participants=0,
                        attributed_signups=0,
                        qualified_joins=0,
                    )
                    return
                records[competition_id] = CreatorCompetitionLinkRecord(
                    competition_id=existing.competition_id,
                    title=existing.title,
                    linked_share_code=linked_share_code or existing.linked_share_code,
                    active_participants=existing.active_participants,
                    attributed_signups=existing.attributed_signups,
                    qualified_joins=existing.qualified_joins,
                )

            if profile.default_competition_id is not None:
                upsert(profile.default_competition_id, profile.default_share_code)

            share_codes = tuple(
                self.session.scalars(
                    select(ShareCode)
                    .where(
                        ShareCode.owner_creator_id == creator_id,
                        ShareCode.linked_competition_id.is_not(None),
                    )
                    .order_by(ShareCode.created_at, ShareCode.id)
                ).all()
            )
            for share_code in share_codes:
                if share_code.linked_competition_id is not None:
                    upsert(share_code.linked_competition_id, share_code.code)

            attributions = tuple(
                self.session.scalars(
                    select(ReferralAttribution)
                    .where(
                        ReferralAttribution.creator_profile_id == creator_id,
                        ReferralAttribution.linked_competition_id.is_not(None),
                    )
                    .order_by(ReferralAttribution.first_touch_at, ReferralAttribution.id)
                ).all()
            )
            if attributions:
                attribution_ids = [attribution.id for attribution in attributions]
                milestones_by_attribution: dict[str, set[str]] = defaultdict(set)
                events = self.session.scalars(
                    select(ReferralEvent).where(ReferralEvent.referral_attribution_id.in_(attribution_ids))
                ).all()
                for event in events:
                    if event.referral_attribution_id is None:
                        continue
                    milestone = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
                    milestones_by_attribution[event.referral_attribution_id].add(milestone)

                for attribution in attributions:
                    competition_id = attribution.linked_competition_id
                    if competition_id is None:
                        continue
                    linked_share_code = str((attribution.metadata_json or {}).get("share_code", "")) or None
                    upsert(competition_id, linked_share_code)
                    link = records[competition_id]
                    milestones = milestones_by_attribution.get(attribution.id, set())
                    qualified_joins = link.qualified_joins + (
                        1 if milestones.intersection(_QUALIFIED_JOIN_MILESTONES) else 0
                    )
                    active_participants = link.active_participants + (
                        1 if milestones.intersection(_QUALIFIED_JOIN_MILESTONES) else 0
                    )
                    records[competition_id] = CreatorCompetitionLinkRecord(
                        competition_id=link.competition_id,
                        title=link.title,
                        linked_share_code=link.linked_share_code,
                        active_participants=active_participants,
                        attributed_signups=link.attributed_signups + 1,
                        qualified_joins=qualified_joins,
                    )

            with self.store.lock:
                self.store.creator_competitions[creator_id] = {
                    record.competition_id: record for record in records.values()
                }
            return list(records.values())
        with self.store.lock:
            return list(self.store.creator_competitions.get(creator_id, {}).values())

    @staticmethod
    def _resolve_competition_title(competition_id: str) -> str:
        try:
            from app.services.competition_orchestrator import get_competition_orchestrator

            competition = get_competition_orchestrator().get(competition_id, user_id=None, invite_code=None)
            if competition is not None:
                return competition.name
        except Exception:
            pass
        return f"Competition {competition_id}"
