from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.legendary_player import LegendaryPlayerProfile
from app.models.regen import RegenProfile
from app.owner_console import engine
from app.owner_console.models import OwnerSquadPlayer

logger = logging.getLogger(__name__)

LEGEND_TIERS = {"legend", "icon", "hero", "prime", "legendary"}
RESTRICTED_GSI_THRESHOLD = 80


@dataclass(frozen=True, slots=True)
class PlayerAcquisitionClassification:
    player_id: str
    player_name: str
    category: str  # "real", "regen", "legend"
    current_gsi: int
    is_restricted: bool
    requires_deposited_funds: bool
    rejection_reason: str | None = None

    @property
    def is_eligible_for_promotional(self) -> bool:
        return not self.is_restricted


def classify_player_for_acquisition(
    session: Session,
    player_or_id: Any,
) -> PlayerAcquisitionClassification:
    """Authoritatively classify a player for club squad acquisition funding rules.

    Rules:
    - Real players, GSI <= 79: Eligible (Promotional or paid GTEX Coin).
    - Real players, GSI >= 80: Restricted (Deposited GTEX Coin ONLY).
    - Regens (any GSI): Restricted (Deposited GTEX Coin ONLY).
    - Legends (any GSI): Restricted (Deposited GTEX Coin ONLY).

    Does NOT trust frontend labels or client-submitted GSI/categories.
    Uses current GSI, NEVER potential GSI.
    """
    player = None
    player_id = ""
    name = "Unknown Player"

    if isinstance(player_or_id, str):
        player_id = player_or_id
        player = session.get(Player, player_id)
        if player is None:
            # Check OwnerSquadPlayer or LegendaryProfile or RegenProfile
            osp = session.get(OwnerSquadPlayer, player_id)
            if osp is not None:
                player_id = osp.player_ref or osp.id
                name = osp.name
                if osp.is_regen:
                    return PlayerAcquisitionClassification(
                        player_id=player_id,
                        player_name=name,
                        category="regen",
                        current_gsi=osp.rating,
                        is_restricted=True,
                        requires_deposited_funds=True,
                        rejection_reason="Regens are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
                    )
                # If osp has player_ref, try fetching underlying player
                if osp.player_ref:
                    player = session.get(Player, osp.player_ref)
    elif isinstance(player_or_id, Player):
        player = player_or_id
        player_id = player.id
    elif isinstance(player_or_id, OwnerSquadPlayer):
        osp = player_or_id
        player_id = osp.player_ref or osp.id
        name = osp.name
        if osp.is_regen:
            return PlayerAcquisitionClassification(
                player_id=player_id,
                player_name=name,
                category="regen",
                current_gsi=osp.rating,
                is_restricted=True,
                requires_deposited_funds=True,
                rejection_reason="Regens are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
            )
        if osp.player_ref:
            player = session.get(Player, osp.player_ref)
        else:
            # Standalone squad player
            is_restr = osp.rating >= RESTRICTED_GSI_THRESHOLD
            return PlayerAcquisitionClassification(
                player_id=player_id,
                player_name=name,
                category="real",
                current_gsi=osp.rating,
                is_restricted=is_restr,
                requires_deposited_funds=is_restr,
                rejection_reason=(
                    f"Real players with GSI 80+ ({osp.rating}) require deposited GTEX Coin. Promotional launch credit cannot be used."
                    if is_restr
                    else None
                ),
            )
    elif isinstance(player_or_id, LegendaryPlayerProfile):
        return PlayerAcquisitionClassification(
            player_id=player_or_id.id,
            player_name=player_or_id.full_name,
            category="legend",
            current_gsi=90,
            is_restricted=True,
            requires_deposited_funds=True,
            rejection_reason="Legends are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
        )
    elif isinstance(player_or_id, RegenProfile):
        return PlayerAcquisitionClassification(
            player_id=player_or_id.player_id,
            player_name="Regen Player",
            category="regen",
            current_gsi=player_or_id.current_gsi,
            is_restricted=True,
            requires_deposited_funds=True,
            rejection_reason="Regens are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
        )

    if player is None:
        # Check if direct LegendaryProfile exists
        legend_profile = session.scalar(
            select(LegendaryPlayerProfile).where(
                or_(
                    LegendaryPlayerProfile.id == player_id,
                    LegendaryPlayerProfile.slug == player_id,
                )
            )
        )
        if legend_profile is not None:
            return PlayerAcquisitionClassification(
                player_id=player_id,
                player_name=legend_profile.full_name,
                category="legend",
                current_gsi=90,
                is_restricted=True,
                requires_deposited_funds=True,
                rejection_reason="Legends are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
            )
        # Check if RegenProfile exists
        regen_profile = session.scalar(
            select(RegenProfile).where(
                or_(
                    RegenProfile.player_id == player_id,
                    RegenProfile.regen_id == player_id,
                )
            )
        )
        if regen_profile is not None:
            return PlayerAcquisitionClassification(
                player_id=player_id,
                player_name="Regen Player",
                category="regen",
                current_gsi=regen_profile.current_gsi,
                is_restricted=True,
                requires_deposited_funds=True,
                rejection_reason="Regens are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
            )

        # Unknown player fallback
        return PlayerAcquisitionClassification(
            player_id=player_id,
            player_name=name,
            category="unknown",
            current_gsi=60,
            is_restricted=False,
            requires_deposited_funds=False,
            rejection_reason=None,
        )

    # We have an Ingestion Player object
    name = player.canonical_display_name or player.full_name or "Player"
    dna = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
    real_tier = str(getattr(player, "real_player_tier", "") or "").strip().lower()
    source_prov = str(getattr(player, "source_provider", "") or "").strip().lower()
    ext_id = str(getattr(player, "provider_external_id", "") or "").strip().lower()

    # 1. Authoritative Legend Detection
    is_legend = (
        getattr(player, "legendary_profile_id", None) is not None
        or real_tier in LEGEND_TIERS
        or source_prov.startswith("gtex_legend")
        or ext_id.startswith("legend:")
        or dna.get("legendary_classification") is not None
        or dna.get("era") is not None
    )
    if not is_legend and player.id:
        has_legend_profile = session.scalar(
            select(LegendaryPlayerProfile.id).where(
                or_(
                    LegendaryPlayerProfile.id == player.id,
                    LegendaryPlayerProfile.slug == ext_id,
                )
            ).limit(1)
        )
        if has_legend_profile:
            is_legend = True

    if is_legend:
        return PlayerAcquisitionClassification(
            player_id=player.id,
            player_name=name,
            category="legend",
            current_gsi=90,
            is_restricted=True,
            requires_deposited_funds=True,
            rejection_reason="Legends are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
        )

    # 2. Authoritative Regen Detection
    is_regen = (
        getattr(player, "is_real_player", True) is False
        or source_prov in ("regen", "gtex_regen", "youth_academy")
        or ext_id.startswith("regen:")
    )
    if not is_regen and player.id:
        has_regen_profile = session.scalar(
            select(RegenProfile.id).where(
                or_(
                    RegenProfile.player_id == player.id,
                    RegenProfile.regen_id == player.id,
                )
            ).limit(1)
        )
        if has_regen_profile:
            is_regen = True

    if is_regen:
        # Determine GSI from regen profile or dna or fallback
        cur_candidates = [
            dna.get("overall"),
            dna.get("current_rating"),
            dna.get("sofifa_overall"),
            dna.get("current_gsi"),
        ]
        cur_gsi = max((int(float(v)) for v in cur_candidates if isinstance(v, (int, float)) and float(v) > 0), default=65)
        return PlayerAcquisitionClassification(
            player_id=player.id,
            player_name=name,
            category="regen",
            current_gsi=cur_gsi,
            is_restricted=True,
            requires_deposited_funds=True,
            rejection_reason="Regens are restricted players and require deposited GTEX Coin. Promotional launch credit cannot be used.",
        )

    # 3. Real Player Detection & Current GSI Calculation
    cur_candidates = [
        dna.get("overall"),
        dna.get("current_rating"),
        dna.get("sofifa_overall"),
    ]
    cur_gsi = max((int(float(v)) for v in cur_candidates if isinstance(v, (int, float)) and float(v) > 0), default=0)

    if cur_gsi <= 0:
        # Fall back to market quote calculation if dna lacks explicit rating
        credits = {}
        _, rating = engine.market_quote(getattr(player, "market_value_eur", None), None)
        cur_gsi = int(engine.clamp(rating, 40, 99))
    else:
        cur_gsi = int(engine.clamp(cur_gsi, 40, 99))

    is_restricted = cur_gsi >= RESTRICTED_GSI_THRESHOLD

    return PlayerAcquisitionClassification(
        player_id=player.id,
        player_name=name,
        category="real",
        current_gsi=cur_gsi,
        is_restricted=is_restricted,
        requires_deposited_funds=is_restricted,
        rejection_reason=(
            f"Real players with GSI 80+ ({cur_gsi}) require deposited GTEX Coin. Promotional launch credit cannot be used."
            if is_restricted
            else None
        ),
    )
