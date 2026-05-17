from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.enums.match_status import MatchStatus
from app.models.club_profile import ClubProfile
from app.models.club_ranking_integrity import ClubRankingAbuseFlag, ClubRankingEvent, CompetitionIntegrityScore
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.ownership_groups.service import OwnershipGroupService

DECIMAL_QUANTUM = Decimal("0.0001")
MAX_POINTS_PER_EVENT = Decimal("6.0000")
MAX_POINTS_PER_DAY_SAME_OPPONENT = Decimal("6.0000")
MAX_POINTS_PER_WEEK_SAME_HOST = Decimal("18.0000")
LOW_QUALITY_MATCH_CAP = Decimal("3.0000")


@dataclass(slots=True)
class ClubRankingIntegrityService:
    session: Session

    def record_match_result(
        self,
        *,
        competition: Competition,
        match: CompetitionMatch,
        result_type: str = "played",
        forfeit_reason: str | None = None,
    ) -> list[ClubRankingEvent]:
        if self._skip_competition(competition):
            return []
        if match.status != MatchStatus.COMPLETED.value:
            return []
        if not match.home_club_id or not match.away_club_id:
            return []

        integrity = self.refresh_competition_integrity(competition)
        home_result, away_result = self._result_for_match(match)
        created: list[ClubRankingEvent] = []
        created.append(
            self._record_result_event(
                competition=competition,
                match=match,
                club_id=match.home_club_id,
                opponent_club_id=match.away_club_id,
                result=home_result,
                result_type=result_type,
                forfeit_reason=forfeit_reason,
                integrity=integrity,
            )
        )
        created.append(
            self._record_result_event(
                competition=competition,
                match=match,
                club_id=match.away_club_id,
                opponent_club_id=match.home_club_id,
                result=away_result,
                result_type=result_type,
                forfeit_reason=forfeit_reason,
                integrity=integrity,
            )
        )
        self.session.flush()
        return [event for event in created if event is not None]

    def record_competition_placements(
        self,
        *,
        competition: Competition,
        standings: Iterable[CompetitionParticipant],
    ) -> list[ClubRankingEvent]:
        if self._skip_competition(competition):
            return []
        integrity = self.refresh_competition_integrity(competition)
        events: list[ClubRankingEvent] = []
        for placement, participant in enumerate(list(standings), start=1):
            bonus = self._placement_bonus(placement)
            if bonus <= Decimal("0"):
                continue
            event = self._record_placement_event(
                competition=competition,
                club_id=participant.club_id,
                placement=placement,
                placement_bonus=bonus,
                integrity=integrity,
            )
            if event is not None:
                events.append(event)
        self.session.flush()
        return events

    def refresh_competition_integrity(self, competition: Competition) -> CompetitionIntegrityScore:
        participants = list(
            self.session.scalars(
                select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition.id)
            ).all()
        )
        matches = list(
            self.session.scalars(
                select(CompetitionMatch).where(CompetitionMatch.competition_id == competition.id)
            ).all()
        )
        club_ids = [participant.club_id for participant in participants if participant.club_id]
        unique_participants = len(set(club_ids))
        pair_counts = Counter(
            tuple(sorted([match.home_club_id, match.away_club_id]))
            for match in matches
            if match.home_club_id and match.away_club_id
        )
        repeated_pair_count = sum(count - 1 for count in pair_counts.values() if count > 1)
        completed_matches = [match for match in matches if match.status == MatchStatus.COMPLETED.value]
        forfeits = [match for match in completed_matches if self._match_result_type(match) == "forfeit"]
        forfeit_rate = (
            Decimal(len(forfeits)) / Decimal(len(completed_matches)) if completed_matches else Decimal("0.0000")
        ).quantize(DECIMAL_QUANTUM)

        suspicious_owner_links = self._suspicious_owner_link_count(club_ids)
        quality = Decimal("100.00")
        if unique_participants < 4:
            quality -= Decimal("15.00")
        quality -= Decimal(repeated_pair_count * 10)
        quality -= (forfeit_rate * Decimal("40.00")).quantize(Decimal("0.01"))
        quality -= Decimal(suspicious_owner_links * 20)
        quality = max(Decimal("0.00"), min(Decimal("100.00"), quality)).quantize(Decimal("0.01"))
        if quality >= Decimal("70.00"):
            ranking_weight = Decimal("1.0000")
        elif quality >= Decimal("40.00"):
            ranking_weight = Decimal("0.5000")
        else:
            ranking_weight = Decimal("0.2500")
        review_required = quality < Decimal("60.00") or suspicious_owner_links > 0

        row = self.session.scalar(
            select(CompetitionIntegrityScore).where(CompetitionIntegrityScore.competition_id == competition.id)
        )
        if row is None:
            row = CompetitionIntegrityScore(competition_id=competition.id)
            self.session.add(row)
        row.unique_participants = unique_participants
        row.repeated_pair_count = repeated_pair_count
        row.forfeit_rate = forfeit_rate
        row.suspicious_owner_links = suspicious_owner_links
        row.quality_score = quality
        row.ranking_weight = ranking_weight
        row.review_required = review_required
        row.metadata_json = {
            **dict(row.metadata_json or {}),
            "pair_counts": {"|".join(pair): count for pair, count in pair_counts.items()},
            "completed_matches": len(completed_matches),
            "forfeit_matches": len(forfeits),
        }
        self.session.flush()
        return row

    def has_ranking_events(self) -> bool:
        return bool(self.session.scalar(select(func.count()).select_from(ClubRankingEvent)) or 0)

    def leaderboard_rows(self, *, limit: int = 50) -> list[dict[str, Any]]:
        events = list(
            self.session.scalars(
                select(ClubRankingEvent).order_by(ClubRankingEvent.created_at.asc(), ClubRankingEvent.id.asc())
            ).all()
        )
        by_club: dict[str, dict[str, Any]] = {}
        for event in events:
            row = by_club.setdefault(
                event.club_id,
                {
                    "club_id": event.club_id,
                    "ranking_points": Decimal("0.0000"),
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "trophies": 0,
                    "form": [],
                    "updated_at": event.updated_at,
                },
            )
            row["ranking_points"] += Decimal(event.final_points_delta or 0)
            row["updated_at"] = max(row["updated_at"], event.updated_at)
            if event.event_kind == "match_result":
                if event.result == "win":
                    row["wins"] += 1
                    row["form"].append("W")
                elif event.result == "draw":
                    row["draws"] += 1
                    row["form"].append("D")
                elif event.result == "loss":
                    row["losses"] += 1
                    row["form"].append("L")
            if event.event_kind == "placement_bonus" and int((event.metadata_json or {}).get("placement") or 0) == 1:
                row["trophies"] += 1

        rows = sorted(
            by_club.values(),
            key=lambda item: (Decimal(item["ranking_points"]), item["updated_at"]),
            reverse=True,
        )[:limit]
        club_map = self._club_map([row["club_id"] for row in rows])
        for row in rows:
            club = club_map.get(row["club_id"])
            row["club_name"] = club.club_name if club is not None else row["club_id"]
            row["owner_user_id"] = club.owner_user_id if club is not None else None
            row["recent_form"] = "".join(row["form"][-5:])
        return rows

    def list_events_for_club(self, club_id: str, *, limit: int = 100) -> list[ClubRankingEvent]:
        return list(
            self.session.scalars(
                select(ClubRankingEvent)
                .where(ClubRankingEvent.club_id == club_id)
                .order_by(ClubRankingEvent.created_at.desc(), ClubRankingEvent.id.desc())
                .limit(limit)
            ).all()
        )

    def list_events(self, *, limit: int = 100, status: str | None = None) -> list[ClubRankingEvent]:
        stmt = select(ClubRankingEvent)
        if status:
            stmt = stmt.where(ClubRankingEvent.integrity_status == status)
        return list(
            self.session.scalars(
                stmt.order_by(ClubRankingEvent.created_at.desc(), ClubRankingEvent.id.desc()).limit(limit)
            ).all()
        )

    def list_flags(self, *, limit: int = 100, status: str | None = None) -> list[ClubRankingAbuseFlag]:
        stmt = select(ClubRankingAbuseFlag)
        if status:
            stmt = stmt.where(ClubRankingAbuseFlag.status == status)
        return list(
            self.session.scalars(
                stmt.order_by(ClubRankingAbuseFlag.created_at.desc(), ClubRankingAbuseFlag.id.desc()).limit(limit)
            ).all()
        )

    def _record_result_event(
        self,
        *,
        competition: Competition,
        match: CompetitionMatch,
        club_id: str,
        opponent_club_id: str,
        result: str,
        result_type: str,
        forfeit_reason: str | None,
        integrity: CompetitionIntegrityScore,
    ) -> ClubRankingEvent | None:
        event_key = f"match:{match.id}:{club_id}"
        existing = self._existing_event(event_key)
        if existing is not None:
            self._flag(
                club_id=club_id,
                competition=competition,
                match_id=match.id,
                flag_type="duplicate_settlement",
                severity="low",
                description="Duplicate match result settlement attempted; existing ranking event was reused.",
                metadata={"event_key": event_key},
            )
            return existing
        base_points = {"win": Decimal("3.0000"), "draw": Decimal("1.0000"), "loss": Decimal("0.0000")}.get(
            result,
            Decimal("0.0000"),
        )
        return self._create_event(
            event_key=event_key,
            event_kind="match_result",
            competition=competition,
            club_id=club_id,
            match_id=match.id,
            opponent_club_id=opponent_club_id,
            result=result,
            base_points=base_points,
            placement_bonus=Decimal("0.0000"),
            integrity=integrity,
            result_type=result_type,
            forfeit_reason=forfeit_reason,
            placement=None,
        )

    def _record_placement_event(
        self,
        *,
        competition: Competition,
        club_id: str,
        placement: int,
        placement_bonus: Decimal,
        integrity: CompetitionIntegrityScore,
    ) -> ClubRankingEvent | None:
        event_key = f"placement:{competition.id}:{club_id}:{placement}"
        existing = self._existing_event(event_key)
        if existing is not None:
            return existing
        return self._create_event(
            event_key=event_key,
            event_kind="placement_bonus",
            competition=competition,
            club_id=club_id,
            match_id=None,
            opponent_club_id=None,
            result=f"placement_{placement}",
            base_points=Decimal("0.0000"),
            placement_bonus=placement_bonus,
            integrity=integrity,
            result_type="placement",
            forfeit_reason=None,
            placement=placement,
        )

    def _create_event(
        self,
        *,
        event_key: str,
        event_kind: str,
        competition: Competition,
        club_id: str,
        match_id: str | None,
        opponent_club_id: str | None,
        result: str,
        base_points: Decimal,
        placement_bonus: Decimal,
        integrity: CompetitionIntegrityScore,
        result_type: str,
        forfeit_reason: str | None,
        placement: int | None,
    ) -> ClubRankingEvent:
        opponent_multiplier = self._opponent_strength_multiplier(club_id, opponent_club_id)
        size_multiplier = self._competition_size_multiplier(int(integrity.unique_participants or 0))
        tier_multiplier = self._competition_tier_multiplier(competition)
        stage_multiplier = self._stage_multiplier(competition=competition, match_id=match_id, placement=placement)
        anti_multiplier, status, reasons = self._anti_farm_multiplier(
            competition=competition,
            club_id=club_id,
            opponent_club_id=opponent_club_id,
            match_id=match_id,
            result=result,
            result_type=result_type,
            integrity=integrity,
        )
        raw = (
            (base_points * opponent_multiplier * size_multiplier * tier_multiplier * stage_multiplier * anti_multiplier)
            + placement_bonus
        ).quantize(DECIMAL_QUANTUM, rounding=ROUND_HALF_UP)
        final = self._apply_caps(
            raw,
            competition=competition,
            club_id=club_id,
            opponent_club_id=opponent_club_id,
            integrity=integrity,
            reasons=reasons,
        )
        if final < raw and status == "clean":
            status = "reduced"
        if final <= Decimal("0.0000") and raw > Decimal("0.0000") and status != "review":
            status = "blocked"
        event = ClubRankingEvent(
            event_key=event_key,
            event_kind=event_kind,
            club_id=club_id,
            competition_id=competition.id,
            match_id=match_id,
            opponent_club_id=opponent_club_id,
            result=result,
            base_points=base_points.quantize(DECIMAL_QUANTUM),
            opponent_strength_multiplier=opponent_multiplier,
            competition_size_multiplier=size_multiplier,
            competition_tier_multiplier=tier_multiplier,
            stage_multiplier=stage_multiplier,
            anti_farm_multiplier=anti_multiplier,
            placement_bonus=placement_bonus.quantize(DECIMAL_QUANTUM),
            raw_points_delta=raw,
            final_points_delta=final,
            integrity_status=status,
            reason="; ".join(reasons) if reasons else "ranked_result",
            metadata_json={
                "result_type": result_type,
                "forfeit_reason": forfeit_reason,
                "placement": placement,
                "quality_score": str(integrity.quality_score),
                "ranking_weight": str(integrity.ranking_weight),
            },
        )
        self.session.add(event)
        self._flag_for_status(
            club_id=club_id,
            competition=competition,
            match_id=match_id,
            status=status,
            reasons=reasons,
            metadata={"event_key": event_key, "final_points_delta": str(final)},
        )
        return event

    def _anti_farm_multiplier(
        self,
        *,
        competition: Competition,
        club_id: str,
        opponent_club_id: str | None,
        match_id: str | None,
        result: str,
        result_type: str,
        integrity: CompetitionIntegrityScore,
    ) -> tuple[Decimal, str, list[str]]:
        multiplier = Decimal(integrity.ranking_weight or 1).quantize(DECIMAL_QUANTUM)
        status = "clean"
        reasons: list[str] = []
        if Decimal(integrity.quality_score or 100) < Decimal("70.00"):
            status = "reduced" if Decimal(integrity.quality_score or 100) >= Decimal("40.00") else "review"
            reasons.append("weak_competition_quality")

        if opponent_club_id and self._shared_ownership(club_id, opponent_club_id):
            return Decimal("0.0000"), "blocked", ["same_owner_or_ownership_group"]

        if opponent_club_id:
            repeated = self._recent_same_opponent_events(club_id, opponent_club_id, days=7)
            if repeated >= 6:
                return Decimal("0.0000"), "blocked", ["same_opponent_limit_exceeded"]
            if repeated >= 3:
                multiplier = min(multiplier, Decimal("0.5000"))
                status = "reduced"
                reasons.append("same_opponent_decay")

        if result == "win" and result_type == "forfeit":
            multiplier = min(multiplier, Decimal("0.5000"))
            status = "reduced"
            reasons.append("forfeit_result_reduction")
            if self._recent_forfeit_wins(club_id, days=7) >= 2:
                multiplier = min(multiplier, Decimal("0.2500"))
                status = "review"
                reasons.append("forfeit_farming_pattern")

        if self._is_new_club_or_owner(club_id):
            multiplier = min(multiplier, Decimal("0.5000"))
            if status == "clean":
                status = "provisional"
            reasons.append("new_club_or_owner_throttle")

        weekly_host_points = self._weekly_points_from_host(club_id, competition.host_user_id)
        if weekly_host_points >= MAX_POINTS_PER_WEEK_SAME_HOST:
            return Decimal("0.0000"), "review", ["same_host_weekly_cap_reached"]
        if weekly_host_points >= (MAX_POINTS_PER_WEEK_SAME_HOST * Decimal("0.75")):
            multiplier = min(multiplier, Decimal("0.5000"))
            status = "reduced"
            reasons.append("same_host_decay")

        return multiplier.quantize(DECIMAL_QUANTUM), status, reasons

    def _apply_caps(
        self,
        value: Decimal,
        *,
        competition: Competition,
        club_id: str,
        opponent_club_id: str | None,
        integrity: CompetitionIntegrityScore,
        reasons: list[str],
    ) -> Decimal:
        capped = min(value, MAX_POINTS_PER_EVENT)
        if capped < value:
            reasons.append("max_points_per_match_cap")
        if Decimal(integrity.quality_score or 100) < Decimal("70.00") and capped > LOW_QUALITY_MATCH_CAP:
            capped = LOW_QUALITY_MATCH_CAP
            reasons.append("low_quality_competition_cap")
        if opponent_club_id:
            remaining = MAX_POINTS_PER_DAY_SAME_OPPONENT - self._daily_points_against_opponent(
                club_id, opponent_club_id
            )
            if remaining <= Decimal("0.0000"):
                capped = Decimal("0.0000")
                reasons.append("same_opponent_daily_cap")
            elif capped > remaining:
                capped = remaining
                reasons.append("same_opponent_daily_cap")
        remaining_host = MAX_POINTS_PER_WEEK_SAME_HOST - self._weekly_points_from_host(
            club_id, competition.host_user_id
        )
        if remaining_host <= Decimal("0.0000"):
            capped = Decimal("0.0000")
            reasons.append("same_host_weekly_cap")
        elif capped > remaining_host:
            capped = remaining_host
            reasons.append("same_host_weekly_cap")
        return max(Decimal("0.0000"), capped).quantize(DECIMAL_QUANTUM, rounding=ROUND_HALF_UP)

    def _flag_for_status(
        self,
        *,
        club_id: str,
        competition: Competition,
        match_id: str | None,
        status: str,
        reasons: list[str],
        metadata: dict[str, Any],
    ) -> None:
        if status == "clean":
            return
        for reason in reasons or [status]:
            severity = "high" if status in {"blocked", "review"} else "medium"
            self._flag(
                club_id=club_id,
                competition=competition,
                match_id=match_id,
                flag_type=reason,
                severity=severity,
                description=f"Ranking event was marked {status}: {reason}.",
                metadata={**metadata, "integrity_status": status},
            )

    def _flag(
        self,
        *,
        club_id: str,
        competition: Competition,
        match_id: str | None,
        flag_type: str,
        severity: str,
        description: str,
        metadata: dict[str, Any],
    ) -> ClubRankingAbuseFlag:
        club = self.session.get(ClubProfile, club_id)
        flag_key = f"{flag_type}:{club_id}:{competition.id}:{match_id or 'competition'}"
        existing = self.session.scalar(select(ClubRankingAbuseFlag).where(ClubRankingAbuseFlag.flag_key == flag_key))
        if existing is not None:
            existing.metadata_json = {**dict(existing.metadata_json or {}), **metadata}
            return existing
        flag = ClubRankingAbuseFlag(
            flag_key=flag_key,
            club_id=club_id,
            user_id=club.owner_user_id if club is not None else None,
            competition_id=competition.id,
            match_id=match_id,
            flag_type=flag_type,
            severity=severity,
            description=description,
            metadata_json=metadata,
        )
        self.session.add(flag)
        return flag

    def _skip_competition(self, competition: Competition) -> bool:
        if not bool(getattr(competition, "is_ranked", True)):
            return True
        values = {
            str(getattr(competition, "competition_type", "") or "").lower(),
            str(getattr(competition, "competition_mode", "") or "").lower(),
            str(getattr(competition, "source_type", "") or "").lower(),
        }
        return "national_team" in values

    def _existing_event(self, event_key: str) -> ClubRankingEvent | None:
        return self.session.scalar(select(ClubRankingEvent).where(ClubRankingEvent.event_key == event_key))

    def _result_for_match(self, match: CompetitionMatch) -> tuple[str, str]:
        if match.home_score > match.away_score:
            return "win", "loss"
        if match.away_score > match.home_score:
            return "loss", "win"
        return "draw", "draw"

    def _match_result_type(self, match: CompetitionMatch) -> str:
        return str((match.metadata_json or {}).get("result_type") or "played").strip().lower()

    def _opponent_strength_multiplier(self, club_id: str, opponent_club_id: str | None) -> Decimal:
        if not opponent_club_id:
            return Decimal("1.0000")
        club_points = self._club_points(club_id)
        opponent_points = self._club_points(opponent_club_id)
        if club_points <= Decimal("0.0000") and opponent_points <= Decimal("0.0000"):
            return Decimal("1.0000")
        ratio = (opponent_points + Decimal("100.0000")) / (club_points + Decimal("100.0000"))
        return max(Decimal("0.7500"), min(Decimal("1.5000"), ratio)).quantize(DECIMAL_QUANTUM)

    def _club_points(self, club_id: str) -> Decimal:
        value = self.session.scalar(
            select(func.coalesce(func.sum(ClubRankingEvent.final_points_delta), 0)).where(
                ClubRankingEvent.club_id == club_id
            )
        )
        return Decimal(value or 0).quantize(DECIMAL_QUANTUM)

    @staticmethod
    def _competition_size_multiplier(size: int) -> Decimal:
        if size <= 2:
            return Decimal("0.7500")
        if size <= 7:
            return Decimal("1.0000")
        if size <= 15:
            return Decimal("1.1500")
        return Decimal("1.2500")

    @staticmethod
    def _competition_tier_multiplier(competition: Competition) -> Decimal:
        source_type = str(getattr(competition, "source_type", "") or "").lower()
        created_by_admin = bool(getattr(competition, "created_by_admin", False))
        if created_by_admin or source_type in {"admin", "gtex", "platform", "official"}:
            return Decimal("1.2500")
        return Decimal("1.0000")

    def _stage_multiplier(self, *, competition: Competition, match_id: str | None, placement: int | None) -> Decimal:
        if placement == 1:
            return Decimal("1.3000")
        if placement in {2, 3}:
            return Decimal("1.1500")
        match = self.session.get(CompetitionMatch, match_id) if match_id else None
        if match is None:
            return Decimal("1.0000")
        stage = str(match.stage or competition.stage or "").lower()
        if stage == "final":
            return Decimal("1.3000")
        if stage in {"semifinal", "semi_final", "knockout"} and int(match.round_number or 0) >= 2:
            return Decimal("1.1500")
        return Decimal("1.0000")

    @staticmethod
    def _placement_bonus(placement: int) -> Decimal:
        return {1: Decimal("1.0000"), 2: Decimal("0.5000"), 3: Decimal("0.2500")}.get(
            placement,
            Decimal("0.0000"),
        )

    def _recent_same_opponent_events(self, club_id: str, opponent_club_id: str, *, days: int) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(ClubRankingEvent)
                .where(
                    ClubRankingEvent.club_id == club_id,
                    ClubRankingEvent.opponent_club_id == opponent_club_id,
                    ClubRankingEvent.event_kind == "match_result",
                    ClubRankingEvent.created_at >= since,
                )
            )
            or 0
        )

    def _daily_points_against_opponent(self, club_id: str, opponent_club_id: str) -> Decimal:
        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        value = self.session.scalar(
            select(func.coalesce(func.sum(ClubRankingEvent.final_points_delta), 0)).where(
                ClubRankingEvent.club_id == club_id,
                ClubRankingEvent.opponent_club_id == opponent_club_id,
                ClubRankingEvent.event_kind == "match_result",
                ClubRankingEvent.created_at >= start,
            )
        )
        return Decimal(value or 0).quantize(DECIMAL_QUANTUM)

    def _weekly_points_from_host(self, club_id: str, host_user_id: str | None) -> Decimal:
        if not host_user_id:
            return Decimal("0.0000")
        since = datetime.now(timezone.utc) - timedelta(days=7)
        value = self.session.scalar(
            select(func.coalesce(func.sum(ClubRankingEvent.final_points_delta), 0))
            .select_from(ClubRankingEvent)
            .join(Competition, Competition.id == ClubRankingEvent.competition_id)
            .where(
                ClubRankingEvent.club_id == club_id,
                Competition.host_user_id == host_user_id,
                ClubRankingEvent.created_at >= since,
            )
        )
        return Decimal(value or 0).quantize(DECIMAL_QUANTUM)

    def _recent_forfeit_wins(self, club_id: str, *, days: int) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        events = self.session.scalars(
            select(ClubRankingEvent).where(
                ClubRankingEvent.club_id == club_id,
                ClubRankingEvent.result == "win",
                ClubRankingEvent.event_kind == "match_result",
                ClubRankingEvent.created_at >= since,
            )
        ).all()
        return sum(1 for event in events if (event.metadata_json or {}).get("result_type") == "forfeit")

    def _shared_ownership(self, club_id: str, opponent_club_id: str) -> bool:
        clubs = self._club_map([club_id, opponent_club_id])
        first = clubs.get(club_id)
        second = clubs.get(opponent_club_id)
        if first is not None and second is not None and first.owner_user_id == second.owner_user_id:
            return True
        ownership_map = OwnershipGroupService(self.session).ownership_map([club_id, opponent_club_id])
        return bool(
            ownership_map.get(club_id)
            and ownership_map.get(opponent_club_id)
            and ownership_map.get(club_id) == ownership_map.get(opponent_club_id)
        )

    def _suspicious_owner_link_count(self, club_ids: list[str]) -> int:
        clubs = self._club_map(club_ids)
        owner_counts = Counter(club.owner_user_id for club in clubs.values())
        direct_links = sum(count - 1 for count in owner_counts.values() if count > 1)
        ownership_summary = OwnershipGroupService(self.session).build_competition_integrity_summary(club_ids)
        group_links = sum(max(len(clubs) - 1, 0) for clubs in ownership_summary.get("restricted_groups", {}).values())
        return int(direct_links + group_links)

    def _is_new_club_or_owner(self, club_id: str) -> bool:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            return False
        now = datetime.now(timezone.utc)
        created_at = club.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        prior_events = int(
            self.session.scalar(
                select(func.count()).select_from(ClubRankingEvent).where(ClubRankingEvent.club_id == club_id)
            )
            or 0
        )
        return (now - created_at) < timedelta(days=7) or prior_events < 5

    def _club_map(self, club_ids: Iterable[str]) -> dict[str, ClubProfile]:
        ids = tuple({club_id for club_id in club_ids if club_id})
        if not ids:
            return {}
        return {
            club.id: club for club in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(ids))).all()
        }
