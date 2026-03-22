from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.club_cosmetic_purchase import ClubCosmeticPurchase
from app.models.club_infra import ClubFacility, ClubStadium
from app.models.club_profile import ClubProfile
from app.models.club_sale import ClubValuationSnapshot
from app.models.creator_monetization import CreatorStadiumProfile
from app.models.creator_provisioning import CreatorSquad
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_contract import PlayerContract
from app.models.regen import AcademyCandidate, RegenProfile
from app.players.read_models import PlayerSummaryReadModel
from app.risk_ops_engine.service import RiskOpsService
from app.services.club_sale_common import (
    CLUB_SALE_VALUATION_VERSION,
    ClubSaleError,
    append_club_sale_audit,
    normalize_coin,
)
from app.value_engine.scoring import credits_from_real_world_value


@dataclass(frozen=True, slots=True)
class ClubValuationBreakdown:
    club_id: str
    total_value_coin: Decimal
    first_team_value_coin: Decimal
    reserve_squad_value_coin: Decimal
    u19_squad_value_coin: Decimal
    academy_value_coin: Decimal
    stadium_value_coin: Decimal
    paid_enhancements_value_coin: Decimal
    metadata: dict[str, Any]


@dataclass(slots=True)
class ClubValuationService:
    session: Session
    risk_ops: RiskOpsService | None = None

    def __post_init__(self) -> None:
        if self.risk_ops is None:
            self.risk_ops = RiskOpsService(self.session)

    def compute_visible_valuation(self, *, club_id: str) -> ClubValuationBreakdown:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ClubSaleError("Club was not found.", reason="club_not_found")

        latest_roles = self._latest_career_roles(club_id)
        player_counts = {"first_team": 0, "reserve": 0, "u19": 0, "academy": 0}
        first_team_value = Decimal("0.0000")
        reserve_value = Decimal("0.0000")
        u19_value = Decimal("0.0000")
        academy_value = Decimal("0.0000")

        contract_rows = list(
            self.session.execute(
                select(
                    PlayerContract.player_id,
                    Player.date_of_birth,
                    Player.market_value_eur,
                    PlayerSummaryReadModel.current_value_credits,
                )
                .join(Player, Player.id == PlayerContract.player_id)
                .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == PlayerContract.player_id)
                .where(
                    PlayerContract.club_id == club_id,
                    PlayerContract.status == "active",
                )
            ).all()
        )
        for player_id, date_of_birth, market_value_eur, summary_value in contract_rows:
            player_value = self._player_value_coin(summary_value=summary_value, market_value_eur=market_value_eur)
            bucket = self._classify_player_bucket(
                squad_role=latest_roles.get(str(player_id)),
                date_of_birth=date_of_birth,
            )
            if bucket == "reserve":
                reserve_value += player_value
            elif bucket == "u19":
                u19_value += player_value
            elif bucket == "academy":
                academy_value += player_value
            else:
                first_team_value += player_value
            player_counts[bucket] += 1

        creator_squad_fallback_used = False
        if not contract_rows:
            creator_squad = self.session.scalar(
                select(CreatorSquad).where(CreatorSquad.club_id == club_id)
            )
            if creator_squad is not None:
                creator_squad_fallback_used = True
                first_team_payloads = list(creator_squad.first_team_json or [])
                academy_payloads = list(creator_squad.academy_json or [])
                first_team_value += sum(
                    (self._payload_value_coin(item) for item in first_team_payloads),
                    start=Decimal("0.0000"),
                )
                academy_value += sum(
                    (self._payload_value_coin(item) for item in academy_payloads),
                    start=Decimal("0.0000"),
                )
                player_counts["first_team"] += len(first_team_payloads)
                player_counts["academy"] += len(academy_payloads)

        academy_candidate_rows = list(
            self.session.execute(
                select(AcademyCandidate, RegenProfile)
                .join(RegenProfile, RegenProfile.id == AcademyCandidate.regen_profile_id)
                .where(AcademyCandidate.club_id == club_id)
            ).all()
        )
        academy_candidate_value = Decimal("0.0000")
        for _candidate, regen in academy_candidate_rows:
            academy_candidate_value += self._regen_value_coin(regen)
        if academy_candidate_value > Decimal("0.0000"):
            academy_value += academy_candidate_value
            player_counts["academy"] += len(academy_candidate_rows)

        stadium_value = self._stadium_value_coin(club_id)
        paid_enhancements_value = self._paid_enhancements_value_coin(club)

        first_team_value = normalize_coin(first_team_value)
        reserve_value = normalize_coin(reserve_value)
        u19_value = normalize_coin(u19_value)
        academy_value = normalize_coin(academy_value)
        stadium_value = normalize_coin(stadium_value)
        paid_enhancements_value = normalize_coin(paid_enhancements_value)
        total_value = normalize_coin(
            first_team_value
            + reserve_value
            + u19_value
            + academy_value
            + stadium_value
            + paid_enhancements_value
        )
        return ClubValuationBreakdown(
            club_id=club_id,
            total_value_coin=total_value,
            first_team_value_coin=first_team_value,
            reserve_squad_value_coin=reserve_value,
            u19_squad_value_coin=u19_value,
            academy_value_coin=academy_value,
            stadium_value_coin=stadium_value,
            paid_enhancements_value_coin=paid_enhancements_value,
            metadata={
                "version_key": CLUB_SALE_VALUATION_VERSION,
                "player_counts": player_counts,
                "contract_player_count": len(contract_rows),
                "academy_candidate_count": len(academy_candidate_rows),
                "creator_squad_fallback_used": creator_squad_fallback_used,
            },
        )

    def capture_snapshot(
        self,
        *,
        club_id: str,
        actor_user_id: str | None = None,
        reason: str,
    ) -> ClubValuationSnapshot:
        breakdown = self.compute_visible_valuation(club_id=club_id)
        snapshot = ClubValuationSnapshot(
            club_id=club_id,
            computed_by_user_id=actor_user_id,
            version_key=CLUB_SALE_VALUATION_VERSION,
            total_value_coin=breakdown.total_value_coin,
            first_team_value_coin=breakdown.first_team_value_coin,
            reserve_squad_value_coin=breakdown.reserve_squad_value_coin,
            u19_squad_value_coin=breakdown.u19_squad_value_coin,
            academy_value_coin=breakdown.academy_value_coin,
            stadium_value_coin=breakdown.stadium_value_coin,
            paid_enhancements_value_coin=breakdown.paid_enhancements_value_coin,
            metadata_json={
                **breakdown.metadata,
                "reason": reason,
            },
        )
        self.session.add(snapshot)
        self.session.flush()
        append_club_sale_audit(
            self.session,
            self.risk_ops,
            club_id=club_id,
            actor_user_id=actor_user_id,
            event_type="club_sale.valuation.snapshot_created",
            detail="Club sale valuation snapshot created.",
            payload={
                "snapshot_id": snapshot.id,
                "reason": reason,
                "total_value_coin": str(snapshot.total_value_coin),
            },
        )
        return snapshot

    def _latest_career_roles(self, club_id: str) -> dict[str, str | None]:
        rows = self.session.scalars(
            select(PlayerCareerEntry)
            .where(PlayerCareerEntry.club_id == club_id)
            .order_by(PlayerCareerEntry.created_at.desc(), PlayerCareerEntry.id.desc())
        ).all()
        latest_roles: dict[str, str | None] = {}
        for entry in rows:
            latest_roles.setdefault(str(entry.player_id), entry.squad_role)
        return latest_roles

    def _player_value_coin(
        self,
        *,
        summary_value: float | None,
        market_value_eur: float | None,
    ) -> Decimal:
        if summary_value is not None and float(summary_value) > 0:
            return normalize_coin(summary_value)
        if market_value_eur is not None and float(market_value_eur) > 0:
            return normalize_coin(credits_from_real_world_value(float(market_value_eur)))
        return Decimal("0.0000")

    def _classify_player_bucket(
        self,
        *,
        squad_role: str | None,
        date_of_birth: date | None,
    ) -> str:
        normalized_role = (squad_role or "").strip().lower().replace("-", " ").replace("_", " ")
        if any(token in normalized_role for token in ("academy", "youth")):
            return "academy"
        if "u19" in normalized_role or "under 19" in normalized_role:
            return "u19"
        if any(token in normalized_role for token in ("reserve", "bench", "b team", "second team")):
            return "reserve"
        age = self._age_on(date_of_birth)
        if age is not None and age <= 19:
            return "u19"
        return "first_team"

    def _payload_value_coin(self, payload: dict[str, object]) -> Decimal:
        current_gsi = int(payload.get("current_gsi", 0) or 0)
        potential_maximum = int(payload.get("potential_maximum", current_gsi) or current_gsi)
        current_component = Decimal(current_gsi) * Decimal("0.8000")
        upside_component = Decimal(max(potential_maximum - current_gsi, 0)) * Decimal("0.2000")
        return normalize_coin(current_component + upside_component)

    def _regen_value_coin(self, regen: RegenProfile) -> Decimal:
        potential_range = regen.potential_range_json or {}
        potential_maximum = int(potential_range.get("maximum", regen.current_gsi) or regen.current_gsi)
        return self._payload_value_coin(
            {
                "current_gsi": regen.current_gsi,
                "potential_maximum": potential_maximum,
            }
        )

    def _stadium_value_coin(self, club_id: str) -> Decimal:
        stadium = self.session.scalar(select(ClubStadium).where(ClubStadium.club_id == club_id))
        creator_profile = self.session.scalar(
            select(CreatorStadiumProfile).where(CreatorStadiumProfile.club_id == club_id)
        )
        if stadium is None and creator_profile is None:
            return Decimal("0.0000")

        capacity = max(
            int(getattr(stadium, "capacity", 0) or 0),
            int(getattr(creator_profile, "capacity", 0) or 0),
        )
        level = max(
            int(getattr(stadium, "level", 0) or 0),
            int(getattr(creator_profile, "level", 0) or 0),
        )
        revenue_multiplier_bps = int(getattr(stadium, "revenue_multiplier_bps", 10_000) or 10_000)
        prestige_bonus_bps = int(getattr(stadium, "prestige_bonus_bps", 0) or 0)
        capacity_component = Decimal(capacity) / Decimal("250")
        level_component = Decimal(level) * Decimal("12")
        revenue_component = Decimal(max(revenue_multiplier_bps - 10_000, 0)) / Decimal("250")
        prestige_component = Decimal(max(prestige_bonus_bps, 0)) / Decimal("200")
        return normalize_coin(capacity_component + level_component + revenue_component + prestige_component)

    def _paid_enhancements_value_coin(self, club: ClubProfile) -> Decimal:
        cosmetic_rows = self.session.scalars(
            select(ClubCosmeticPurchase).where(
                ClubCosmeticPurchase.club_id == club.id,
                ClubCosmeticPurchase.buyer_user_id == club.owner_user_id,
                ClubCosmeticPurchase.status == "completed",
            )
        ).all()
        cosmetic_value = sum(
            (Decimal(int(item.amount_minor)) / Decimal("100") for item in cosmetic_rows),
            start=Decimal("0.0000"),
        )

        facility = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club.id))
        creator_profile = self.session.scalar(
            select(CreatorStadiumProfile).where(CreatorStadiumProfile.club_id == club.id)
        )
        facility_levels = (
            max(int(getattr(facility, "training_level", 1) or 1) - 1, 0)
            + max(int(getattr(facility, "academy_level", 1) or 1) - 1, 0)
            + max(int(getattr(facility, "medical_level", 1) or 1) - 1, 0)
            + max(int(getattr(facility, "branding_level", 1) or 1) - 1, 0)
        )
        facility_value = Decimal(facility_levels) * Decimal("6")

        visual_upgrade_level = max(int(getattr(creator_profile, "visual_upgrade_level", 1) or 1) - 1, 0)
        customization_bonus = Decimal("0.0000")
        if creator_profile is not None and (
            getattr(creator_profile, "custom_chant_text", None) or getattr(creator_profile, "custom_visuals_json", None)
        ):
            customization_bonus = Decimal("2.5000")
        creator_upgrade_value = Decimal(visual_upgrade_level) * Decimal("5")

        return normalize_coin(cosmetic_value + facility_value + creator_upgrade_value + customization_bonus)

    @staticmethod
    def _age_on(date_of_birth: date | None) -> int | None:
        if date_of_birth is None:
            return None
        today = date.today()
        return today.year - date_of_birth.year - (
            (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
        )


__all__ = ["ClubValuationBreakdown", "ClubValuationService"]
