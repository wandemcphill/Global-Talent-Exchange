from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.club_ranking_integrity import ClubRankingAbuseFlag, ClubRankingEvent
from app.models.competition import Competition
from app.models.gift_transaction import GiftAbuseFlag, GiftTransaction, GiftTransactionStatus

DECIMAL_QUANTUM = Decimal("0.0001")
COLLUSION_WINDOW_DAYS = 7
MIN_REPEATED_MATCHES_FOR_REVIEW = 2
MIN_GIFTS_FOR_REVIEW = 2
HEAVY_PAIR_GIFT_AMOUNT = Decimal("50.0000")
REVIEW_RANKING_MULTIPLIER = Decimal("0.2500")
PROVISIONAL_RANKING_MULTIPLIER = Decimal("0.5000")


@dataclass(frozen=True, slots=True)
class SocialCollusionAssessment:
    club_id: str
    opponent_club_id: str
    owner_user_id: str | None
    opponent_owner_user_id: str | None
    recent_match_count: int
    recent_gift_count: int
    reciprocal_gift_directions: int
    total_gift_amount: Decimal
    risk_status: str
    reason: str | None

    @property
    def is_risky(self) -> bool:
        return self.risk_status in {"provisional", "review"}

    @property
    def ranking_multiplier(self) -> Decimal:
        if self.risk_status == "review":
            return REVIEW_RANKING_MULTIPLIER
        if self.risk_status == "provisional":
            return PROVISIONAL_RANKING_MULTIPLIER
        return Decimal("1.0000")

    def metadata(self) -> dict[str, object]:
        return {
            "club_id": self.club_id,
            "opponent_club_id": self.opponent_club_id,
            "owner_user_id": self.owner_user_id,
            "opponent_owner_user_id": self.opponent_owner_user_id,
            "recent_match_count": self.recent_match_count,
            "recent_gift_count": self.recent_gift_count,
            "reciprocal_gift_directions": self.reciprocal_gift_directions,
            "total_gift_amount": str(self.total_gift_amount),
            "risk_status": self.risk_status,
            "reason": self.reason,
            "window_days": COLLUSION_WINDOW_DAYS,
        }


class SocialCollusionDetectionService:
    """Detects overlap between ranked match loops and social money movement.

    The detector never awards competitive ranking points. It can only reduce
    or mark existing/new ranking events for review, and it mirrors the concern
    into gift abuse flags so admin review sees both sides of the pattern.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def assess_club_pair(
        self,
        *,
        club_id: str,
        opponent_club_id: str | None,
    ) -> SocialCollusionAssessment | None:
        if not opponent_club_id:
            return None
        club_map = self._club_map([club_id, opponent_club_id])
        club = club_map.get(club_id)
        opponent = club_map.get(opponent_club_id)
        if club is None or opponent is None:
            return None
        owner_id = club.owner_user_id
        opponent_owner_id = opponent.owner_user_id
        if not owner_id or not opponent_owner_id or owner_id == opponent_owner_id:
            return None

        recent_match_count = self._recent_pair_match_count(club_id, opponent_club_id)
        gift_transactions = self._recent_pair_gifts(owner_id, opponent_owner_id)
        recent_gift_count = len(gift_transactions)
        total_gift_amount = sum(
            (Decimal(transaction.gross_amount or 0) for transaction in gift_transactions),
            Decimal("0.0000"),
        ).quantize(DECIMAL_QUANTUM)
        directions = {(transaction.sender_user_id, transaction.recipient_user_id) for transaction in gift_transactions}
        reciprocal_directions = len(directions)

        risk_status = "clean"
        reason: str | None = None
        if recent_match_count >= MIN_REPEATED_MATCHES_FOR_REVIEW and (
            reciprocal_directions >= 2
            or recent_gift_count >= MIN_GIFTS_FOR_REVIEW
            or total_gift_amount >= HEAVY_PAIR_GIFT_AMOUNT
        ):
            risk_status = "review"
            reason = "combined_play_gift_collusion"
        elif recent_match_count >= 1 and reciprocal_directions >= 2 and total_gift_amount >= HEAVY_PAIR_GIFT_AMOUNT:
            risk_status = "provisional"
            reason = "early_play_gift_collusion_signal"

        return SocialCollusionAssessment(
            club_id=club_id,
            opponent_club_id=opponent_club_id,
            owner_user_id=owner_id,
            opponent_owner_user_id=opponent_owner_id,
            recent_match_count=recent_match_count,
            recent_gift_count=recent_gift_count,
            reciprocal_gift_directions=reciprocal_directions,
            total_gift_amount=total_gift_amount,
            risk_status=risk_status,
            reason=reason,
        )

    def flag_pair(
        self,
        *,
        assessment: SocialCollusionAssessment,
        competition: Competition | None = None,
        match_id: str | None = None,
        gift_transaction: GiftTransaction | None = None,
        ranking_event: ClubRankingEvent | None = None,
    ) -> None:
        if not assessment.is_risky or not assessment.reason:
            return
        metadata = {
            **assessment.metadata(),
            "competition_id": competition.id if competition is not None else None,
            "match_id": match_id,
            "gift_transaction_id": gift_transaction.id if gift_transaction is not None else None,
            "ranking_event_id": ranking_event.id if ranking_event is not None else None,
        }
        severity = "high" if assessment.risk_status == "review" else "medium"
        for club_id, user_id in (
            (assessment.club_id, assessment.owner_user_id),
            (assessment.opponent_club_id, assessment.opponent_owner_user_id),
        ):
            self._upsert_ranking_flag(
                club_id=club_id,
                user_id=user_id,
                competition_id=competition.id if competition is not None else None,
                match_id=match_id,
                flag_type=assessment.reason,
                severity=severity,
                description="Repeated ranked play and reciprocal/heavy gifting were detected between club owners.",
                metadata=metadata,
            )
        flagged_transaction_ids: set[str] = set()
        for transaction in self._recent_pair_gifts(
            assessment.owner_user_id or "",
            assessment.opponent_owner_user_id or "",
        ):
            self._upsert_gift_flag(transaction=transaction, assessment=assessment, severity=severity)
            transaction.abuse_status = "review"
            flagged_transaction_ids.add(transaction.id)
        if gift_transaction is not None and gift_transaction.id not in flagged_transaction_ids:
            gift_transaction.abuse_status = "review"
            self._upsert_gift_flag(transaction=gift_transaction, assessment=assessment, severity=severity)
        self.session.flush()

    def apply_after_gift(self, *, transaction: GiftTransaction) -> list[SocialCollusionAssessment]:
        assessments: list[SocialCollusionAssessment] = []
        sender_clubs = self._clubs_for_owner(transaction.sender_user_id)
        recipient_clubs = self._clubs_for_owner(transaction.recipient_user_id)
        for sender_club in sender_clubs:
            for recipient_club in recipient_clubs:
                if sender_club.id == recipient_club.id:
                    continue
                assessment = self.assess_club_pair(
                    club_id=sender_club.id,
                    opponent_club_id=recipient_club.id,
                )
                if assessment is None or not assessment.is_risky:
                    continue
                assessments.append(assessment)
                self.flag_pair(assessment=assessment, gift_transaction=transaction)
                self._reduce_recent_ranking_events(assessment=assessment)
        return assessments

    def _reduce_recent_ranking_events(self, *, assessment: SocialCollusionAssessment) -> None:
        since = utcnow() - timedelta(days=COLLUSION_WINDOW_DAYS)
        events = self.session.scalars(
            select(ClubRankingEvent).where(
                ClubRankingEvent.event_kind == "match_result",
                ClubRankingEvent.created_at >= since,
                (
                    (ClubRankingEvent.club_id == assessment.club_id)
                    & (ClubRankingEvent.opponent_club_id == assessment.opponent_club_id)
                )
                | (
                    (ClubRankingEvent.club_id == assessment.opponent_club_id)
                    & (ClubRankingEvent.opponent_club_id == assessment.club_id)
                ),
            )
        ).all()
        for event in events:
            if event.integrity_status == "blocked":
                continue
            original_delta = Decimal(event.final_points_delta or 0).quantize(DECIMAL_QUANTUM)
            reduced_delta = min(
                original_delta,
                (Decimal(event.raw_points_delta or 0) * assessment.ranking_multiplier).quantize(DECIMAL_QUANTUM),
            )
            event.final_points_delta = reduced_delta
            event.anti_farm_multiplier = min(
                Decimal(event.anti_farm_multiplier or 1).quantize(DECIMAL_QUANTUM),
                assessment.ranking_multiplier,
            )
            event.integrity_status = assessment.risk_status
            existing_reason = event.reason or ""
            if assessment.reason and assessment.reason not in existing_reason:
                event.reason = f"{existing_reason}; {assessment.reason}".strip("; ")
            event.metadata_json = {
                **dict(event.metadata_json or {}),
                "phase6_social_collusion": assessment.metadata(),
                "pre_collusion_points_delta": str(original_delta),
            }
            competition = self.session.get(Competition, event.competition_id)
            if competition is not None:
                self.flag_pair(
                    assessment=assessment,
                    competition=competition,
                    match_id=event.match_id,
                    ranking_event=event,
                )
        self.session.flush()

    def _recent_pair_match_count(self, club_id: str, opponent_club_id: str) -> int:
        since = utcnow() - timedelta(days=COLLUSION_WINDOW_DAYS)
        count = self.session.scalar(
            select(func.count(func.distinct(ClubRankingEvent.match_id))).where(
                ClubRankingEvent.event_kind == "match_result",
                ClubRankingEvent.match_id.is_not(None),
                ClubRankingEvent.created_at >= since,
                ((ClubRankingEvent.club_id == club_id) & (ClubRankingEvent.opponent_club_id == opponent_club_id))
                | ((ClubRankingEvent.club_id == opponent_club_id) & (ClubRankingEvent.opponent_club_id == club_id)),
            )
        )
        return int(count or 0)

    def _recent_pair_gifts(self, first_user_id: str, second_user_id: str) -> list[GiftTransaction]:
        if not first_user_id or not second_user_id:
            return []
        since = utcnow() - timedelta(days=COLLUSION_WINDOW_DAYS)
        return list(
            self.session.scalars(
                select(GiftTransaction).where(
                    GiftTransaction.status == GiftTransactionStatus.SETTLED,
                    GiftTransaction.created_at >= since,
                    (
                        (GiftTransaction.sender_user_id == first_user_id)
                        & (GiftTransaction.recipient_user_id == second_user_id)
                    )
                    | (
                        (GiftTransaction.sender_user_id == second_user_id)
                        & (GiftTransaction.recipient_user_id == first_user_id)
                    ),
                )
            ).all()
        )

    def _club_map(self, club_ids: list[str]) -> dict[str, ClubProfile]:
        ids = tuple({club_id for club_id in club_ids if club_id})
        if not ids:
            return {}
        return {
            club.id: club for club in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(ids))).all()
        }

    def _clubs_for_owner(self, user_id: str) -> list[ClubProfile]:
        return list(self.session.scalars(select(ClubProfile).where(ClubProfile.owner_user_id == user_id)).all())

    def _upsert_ranking_flag(
        self,
        *,
        club_id: str,
        user_id: str | None,
        competition_id: str | None,
        match_id: str | None,
        flag_type: str,
        severity: str,
        description: str,
        metadata: dict[str, Any],
    ) -> ClubRankingAbuseFlag:
        flag_key = f"{flag_type}:{club_id}:{competition_id or 'none'}:{match_id or 'pair'}"
        for pending in self.session.new:
            if isinstance(pending, ClubRankingAbuseFlag) and pending.flag_key == flag_key:
                pending.metadata_json = {**dict(pending.metadata_json or {}), **metadata}
                pending.severity = severity
                return pending
        existing = self.session.scalar(select(ClubRankingAbuseFlag).where(ClubRankingAbuseFlag.flag_key == flag_key))
        if existing is not None:
            existing.metadata_json = {**dict(existing.metadata_json or {}), **metadata}
            existing.severity = severity
            return existing
        flag = ClubRankingAbuseFlag(
            flag_key=flag_key,
            club_id=club_id,
            user_id=user_id,
            competition_id=competition_id,
            match_id=match_id,
            flag_type=flag_type,
            severity=severity,
            description=description,
            metadata_json=metadata,
        )
        self.session.add(flag)
        return flag

    def _upsert_gift_flag(
        self,
        *,
        transaction: GiftTransaction,
        assessment: SocialCollusionAssessment,
        severity: str,
    ) -> GiftAbuseFlag:
        flag_key = f"competition-gift-collusion:{transaction.id}:{assessment.club_id}:{assessment.opponent_club_id}"
        for pending in self.session.new:
            if isinstance(pending, GiftAbuseFlag) and pending.flag_key == flag_key:
                pending.metadata_json = {**dict(pending.metadata_json or {}), **assessment.metadata()}
                pending.severity = severity
                return pending
        existing = self.session.scalar(select(GiftAbuseFlag).where(GiftAbuseFlag.flag_key == flag_key))
        if existing is not None:
            existing.metadata_json = {**dict(existing.metadata_json or {}), **assessment.metadata()}
            existing.severity = severity
            return existing
        flag = GiftAbuseFlag(
            flag_key=flag_key,
            sender_user_id=transaction.sender_user_id,
            recipient_type=transaction.recipient_type,
            recipient_id=transaction.recipient_entity_id or transaction.recipient_user_id,
            gift_transaction_id=transaction.id,
            flag_type="competition_gift_collusion",
            severity=severity,
            description="Gift activity overlaps with repeated ranked matches between the same club owners.",
            metadata_json=assessment.metadata(),
        )
        self.session.add(flag)
        return flag
