from __future__ import annotations

from backend.app.services.referral_orchestrator import CreatorCompetitionLinkRecord, ReferralStore


class CreatorCompetitionLinkService:
    # TODO: Replace these lightweight links with Thread A's durable creator/share-code associations when available.
    def __init__(self, store: ReferralStore) -> None:
        self.store = store

    def link_competition(
        self,
        *,
        creator_id: str,
        competition_id: str,
        linked_share_code: str | None,
    ) -> None:
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
        with self.store.lock:
            return list(self.store.creator_competitions.get(creator_id, {}).values())

    @staticmethod
    def _resolve_competition_title(competition_id: str) -> str:
        try:
            from backend.app.services.competition_orchestrator import get_competition_orchestrator

            competition = get_competition_orchestrator().get(competition_id, user_id=None, invite_code=None)
            if competition is not None:
                return competition.name
        except Exception:
            pass
        return f"Competition {competition_id}"
