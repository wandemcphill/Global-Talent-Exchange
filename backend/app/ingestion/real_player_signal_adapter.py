from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.real_player_normalization_service import RealPlayerNormalizedProfile


@dataclass(frozen=True, slots=True)
class RealPlayerSignalBundle:
    market_signals: dict[str, float]
    notes: dict[str, object]


@dataclass(slots=True)
class RealPlayerSignalAdapter:
    def build_signal_bundle(self, normalized: RealPlayerNormalizedProfile) -> RealPlayerSignalBundle:
        market_signals: dict[str, float] = {
            "watchlist_adds": float(max(int(round((normalized.popularity_signal * 0.34) + 4)), 1)),
            "shortlist_adds": float(max(int(round((normalized.real_life_performance_score * 0.18) + (normalized.role_tier_signal * 0.16))), 1)),
            "transfer_room_adds": float(max(int(round((normalized.liquidity_seed_signal * 0.17) + (normalized.market_prestige_signal * 0.12))), 1)),
            "scouting_activity": float(max(int(round((normalized.real_life_performance_score * 0.20) + (normalized.competition_strength_score * 0.10))), 1)),
            "competition_selection_count": float(max(int(round((normalized.form_signal * 0.24) + (normalized.popularity_signal * 0.14))), 1)),
            "featured_performance_count": float(max(int(round(normalized.form_signal / 24.0)), 0)),
            "follows": float(max(int(round((normalized.popularity_signal * 0.22) + 2)), 1)),
            "transfer_interest_score": round(
                (normalized.liquidity_seed_signal * 0.50)
                + (normalized.market_prestige_signal * 0.30)
                + (normalized.club_strength_score * 0.20),
                2,
            ),
        }
        if normalized.reference_market_value_eur is not None:
            market_signals["reference_market_value_eur"] = round(normalized.reference_market_value_eur, 2)

        return RealPlayerSignalBundle(
            market_signals=market_signals,
            notes={
                "real_player_normalized": True,
                "normalization_profile_version": normalized.normalization_profile_version,
                "source_name": normalized.source_name,
                "source_player_key": normalized.source_player_key,
                "real_player_tier": normalized.real_player_tier,
                "normalized_signals": normalized.normalized_signals(),
            },
        )


__all__ = ["RealPlayerSignalAdapter", "RealPlayerSignalBundle"]
