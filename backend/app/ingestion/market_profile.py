from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.ingestion.models import (
    Competition,
    LiquidityBand as LiquidityBandModel,
    MarketSignal,
    Player,
    PlayerMatchStat,
    PlayerSeasonStat,
    SupplyTier as SupplyTierModel,
)

CURRENT_CREDITS_SIGNAL_TYPES = frozenset({"current_credits", "credits"})
REFERENCE_VALUE_SIGNAL_TYPES = frozenset({"reference_market_value_eur", "market_value_eur"})


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _normalize_ratio(value: float, *, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        return 0.0
    return _clamp((value - floor) / (ceiling - floor))


@dataclass(frozen=True, slots=True)
class MarketProfileAssignment:
    supply_tier_code: str
    liquidity_band_code: str
    player_score: float
    estimated_price_credits: float


@dataclass(slots=True)
class PlayerMarketProfileService:
    settings: Settings | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()

    def ensure_catalogs(self, session: Session) -> None:
        assert self.settings is not None

        configured_supply_codes = {tier.code for tier in self.settings.supply_tiers.tiers}
        configured_liquidity_codes = {band.code for band in self.settings.liquidity_bands.bands}

        existing_tiers = {
            row.code: row
            for row in session.scalars(
                select(SupplyTierModel).where(SupplyTierModel.code.in_(configured_supply_codes))
            )
        }
        for index, config_tier in enumerate(self.settings.supply_tiers.tiers, start=1):
            tier = existing_tiers.get(config_tier.code)
            if tier is None:
                tier = SupplyTierModel(code=config_tier.code, name=config_tier.name, rank=index)
                session.add(tier)
            tier.name = config_tier.name
            tier.rank = index
            tier.min_score = config_tier.min_score
            tier.max_score = config_tier.max_score
            tier.target_share = config_tier.target_share
            tier.circulating_supply = config_tier.circulating_supply
            tier.daily_pack_supply = config_tier.daily_pack_supply
            tier.season_mint_cap = config_tier.season_mint_cap
            tier.is_active = True

        existing_bands = {
            row.code: row
            for row in session.scalars(
                select(LiquidityBandModel).where(LiquidityBandModel.code.in_(configured_liquidity_codes))
            )
        }
        for index, config_band in enumerate(self.settings.liquidity_bands.bands, start=1):
            band = existing_bands.get(config_band.code)
            if band is None:
                band = LiquidityBandModel(code=config_band.code, name=config_band.name, rank=index)
                session.add(band)
            band.name = config_band.name
            band.rank = index
            band.min_price_credits = config_band.min_price_credits
            band.max_price_credits = config_band.max_price_credits
            band.max_spread_bps = config_band.max_spread_bps
            band.maker_inventory_target = config_band.maker_inventory_target
            band.instant_sell_fee_bps = config_band.instant_sell_fee_bps
            band.is_active = True

        session.flush()

    def refresh_player_profiles(self, session: Session, *, player_ids: set[str] | None = None) -> None:
        assert self.settings is not None

        self.ensure_catalogs(session)

        tier_lookup = {
            tier.code: tier
            for tier in session.scalars(
                select(SupplyTierModel).where(
                    SupplyTierModel.code.in_({item.code for item in self.settings.supply_tiers.tiers})
                )
            )
        }
        band_lookup = {
            band.code: band
            for band in session.scalars(
                select(LiquidityBandModel).where(
                    LiquidityBandModel.code.in_({item.code for item in self.settings.liquidity_bands.bands})
                )
            )
        }

        statement = (
            select(Player)
            .options(
                selectinload(Player.current_club),
                selectinload(Player.current_competition).selectinload(Competition.internal_league),
                selectinload(Player.internal_league),
                selectinload(Player.season_stats),
                selectinload(Player.match_stats),
                selectinload(Player.market_signals),
            )
        )
        if player_ids:
            statement = statement.where(Player.id.in_(player_ids))

        for player in session.scalars(statement):
            if not player.is_tradable:
                player.supply_tier = None
                player.liquidity_band = None
                continue

            assignment = self.assign_player(player)
            player.supply_tier = tier_lookup[assignment.supply_tier_code]
            player.liquidity_band = band_lookup[assignment.liquidity_band_code]

        session.flush()

    def assign_player(self, player: Player) -> MarketProfileAssignment:
        score = round(self._score_player(player), 4)
        price_credits = round(self._estimate_price_credits(player, score), 2)
        supply_tier = self._select_supply_tier(score)
        liquidity_band = self._select_liquidity_band(price_credits)
        return MarketProfileAssignment(
            supply_tier_code=supply_tier.code,
            liquidity_band_code=liquidity_band.code,
            player_score=score,
            estimated_price_credits=price_credits,
        )

    def _score_player(self, player: Player) -> float:
        visibility_score = self._visibility_score(player)
        performance_score = self._performance_score(player)
        profile_score = self._profile_score(player)
        market_value_score = self._market_value_score(player)

        if market_value_score > 0:
            score = (
                (visibility_score * 0.35)
                + (performance_score * 0.30)
                + (market_value_score * 0.25)
                + (profile_score * 0.10)
            )
        else:
            score = (
                (visibility_score * 0.45)
                + (performance_score * 0.35)
                + (profile_score * 0.20)
            )

        if player.current_competition is not None and player.current_competition.is_major:
            score += 0.05

        return _clamp(score)

    def _visibility_score(self, player: Player) -> float:
        internal_league = player.internal_league
        if internal_league is None and player.current_competition is not None:
            internal_league = player.current_competition.internal_league

        league_visibility = _clamp(
            internal_league.visibility_weight if internal_league is not None else 0.25
        )
        competition_strength_source = None
        if player.current_competition is not None and player.current_competition.competition_strength is not None:
            competition_strength_source = player.current_competition.competition_strength
        elif internal_league is not None:
            competition_strength_source = internal_league.competition_multiplier

        competition_strength = (
            _normalize_ratio(competition_strength_source, floor=0.75, ceiling=1.25)
            if competition_strength_source is not None
            else 0.35
        )
        club_popularity = _clamp(
            player.current_club.popularity_score
            if player.current_club is not None and player.current_club.popularity_score is not None
            else max(league_visibility * 0.6, 0.2)
        )

        return _clamp(
            (league_visibility * 0.50)
            + (competition_strength * 0.30)
            + (club_popularity * 0.20)
        )

    def _performance_score(self, player: Player) -> float:
        latest_season_stat = self._latest_season_stat(player.season_stats)
        if latest_season_stat is not None:
            minutes = latest_season_stat.minutes or 0
            rating = latest_season_stat.average_rating or 6.0
            availability_score = min(minutes / 2_600.0, 1.0)
            rating_score = _clamp((rating - 6.0) / 2.5)
            output_score = self._season_output_score(player, latest_season_stat)
            return _clamp(
                (availability_score * 0.45)
                + (rating_score * 0.25)
                + (output_score * 0.30)
            )

        latest_match_stat = self._latest_match_stat(player.match_stats)
        if latest_match_stat is None:
            return 0.0

        minutes = latest_match_stat.minutes or 0
        rating = latest_match_stat.rating or 6.0
        availability_score = min(minutes / 90.0, 1.0)
        rating_score = _clamp((rating - 6.0) / 2.5)
        output_score = self._match_output_score(player, latest_match_stat)
        return _clamp(
            (availability_score * 0.40)
            + (rating_score * 0.30)
            + (output_score * 0.30)
        )

    def _season_output_score(self, player: Player, stat: PlayerSeasonStat) -> float:
        if self._position_bucket(player) == "goalkeeper":
            saves_score = min((stat.saves or 0) / 80.0, 1.0)
            clean_sheet_score = min((stat.clean_sheets or 0) / 18.0, 1.0)
            return _clamp((saves_score * 0.55) + (clean_sheet_score * 0.45))

        goal_involvement = (stat.goals or 0) + (stat.assists or 0)
        return min(goal_involvement / 24.0, 1.0)

    def _match_output_score(self, player: Player, stat: PlayerMatchStat) -> float:
        if self._position_bucket(player) == "goalkeeper":
            saves_score = min((stat.saves or 0) / 8.0, 1.0)
            clean_sheet_score = 1.0 if stat.clean_sheet else 0.0
            return _clamp((saves_score * 0.65) + (clean_sheet_score * 0.35))

        goal_involvement = (stat.goals or 0) + (stat.assists or 0)
        return min(goal_involvement / 3.0, 1.0)

    def _profile_score(self, player: Player) -> float:
        if player.profile_completeness_score is not None:
            return _clamp(player.profile_completeness_score)

        candidate_values = (
            player.first_name,
            player.last_name,
            player.short_name,
            player.country_id,
            player.current_club_id,
            player.current_competition_id,
            player.position,
            player.normalized_position,
            player.date_of_birth,
            player.height_cm,
            player.weight_kg,
            player.preferred_foot,
            player.shirt_number,
        )
        present = sum(1 for value in candidate_values if value not in {None, ""})
        return round(present / len(candidate_values), 4)

    def _market_value_score(self, player: Player) -> float:
        market_value_eur = player.market_value_eur
        if market_value_eur is None or market_value_eur <= 0:
            reference_signal = self._latest_signal_value(player.market_signals, REFERENCE_VALUE_SIGNAL_TYPES)
            market_value_eur = reference_signal
        if market_value_eur is None or market_value_eur <= 0:
            return 0.0
        return min(market_value_eur / 100_000_000.0, 1.0)

    def _estimate_price_credits(self, player: Player, score: float) -> float:
        current_credits = self._latest_signal_value(player.market_signals, CURRENT_CREDITS_SIGNAL_TYPES)
        if current_credits is not None and current_credits > 0:
            return current_credits

        market_value_eur = player.market_value_eur
        if market_value_eur is None or market_value_eur <= 0:
            market_value_eur = self._latest_signal_value(player.market_signals, REFERENCE_VALUE_SIGNAL_TYPES)
        if market_value_eur is not None and market_value_eur > 0:
            assert self.settings is not None
            return round(
                market_value_eur / self.settings.value_engine_weighting.baseline_eur_per_credit,
                2,
            )

        return round(12.0 + (score**2.25) * 1_188.0, 2)

    def _latest_signal_value(
        self,
        market_signals: list[MarketSignal],
        signal_types: frozenset[str],
    ) -> float | None:
        matches = [
            signal
            for signal in market_signals
            if signal.signal_type.strip().lower().replace("-", "_") in signal_types
        ]
        if not matches:
            return None
        latest_signal = max(matches, key=lambda item: (item.as_of, item.created_at, item.id))
        return latest_signal.score

    def _select_supply_tier(self, score: float):
        assert self.settings is not None

        for tier in self.settings.supply_tiers.tiers:
            if tier.min_score <= score <= tier.max_score:
                return tier
        return self.settings.supply_tiers.tiers[0] if score > 1.0 else self.settings.supply_tiers.tiers[-1]

    def _select_liquidity_band(self, price_credits: float):
        assert self.settings is not None

        for band in self.settings.liquidity_bands.bands:
            if price_credits < band.min_price_credits:
                continue
            if band.max_price_credits is None or price_credits <= band.max_price_credits:
                return band
        return self.settings.liquidity_bands.bands[-1]

    def _latest_match_stat(self, match_stats: list[PlayerMatchStat]) -> PlayerMatchStat | None:
        if not match_stats:
            return None
        return max(match_stats, key=lambda item: (item.updated_at, item.created_at, item.id))

    def _latest_season_stat(self, season_stats: list[PlayerSeasonStat]) -> PlayerSeasonStat | None:
        if not season_stats:
            return None
        return max(season_stats, key=lambda item: (item.updated_at, item.created_at, item.id))

    def _position_bucket(self, player: Player) -> str:
        position = (player.normalized_position or player.position or "").strip().lower()
        if "goal" in position or position == "gk":
            return "goalkeeper"
        if "def" in position or "back" in position or position == "cb" or position == "fb":
            return "defender"
        if "wing" in position or "forward" in position or "striker" in position or position == "st":
            return "forward"
        return "midfielder"
