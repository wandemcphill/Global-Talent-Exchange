from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.gift_engine.service import GiftEngineError, GiftEngineService
from app.ingestion.models import Competition as IngestionCompetition
from app.ingestion.models import Country as IngestionCountry
from app.ingestion.models import InternalLeague, Player, PlayerSeasonStat
from app.market.player_eligibility_policy import market_access_payload
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.club_social import ClubIdentityMetrics, RivalryProfile
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry, NationalTeamEntry
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.national_team_tournament import (
    FreePlayerTier,
    NationalTeamRentalSquadMember,
    RentalContract,
    RentalContractStatus,
    StadiumAd,
    StadiumAdPlacement,
    StoryEvent,
    StoryEventType,
    TournamentTheme,
)
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.integrity_engine.service import IntegrityEngineService
from app.national_team_engine.competition_profiles import seeded_competition_definitions
from app.players.read_models import PlayerSummaryReadModel
from app.services.competition_lock_service import CompetitionLockError, CompetitionLockService
from app.story_feed_engine.service import StoryFeedService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_MINIMUM_SQUAD_SIZE = 18
DEFAULT_MAXIMUM_SQUAD_SIZE = 30
DEFAULT_FREE_PLAYER_QUOTA = 5
DEFAULT_FREE_PLAYER_DISTRIBUTION = {
    FreePlayerTier.HIGH.value: 1,
    FreePlayerTier.MID.value: 2,
    FreePlayerTier.LOW.value: 2,
}
DEFAULT_RENTAL_DURATION_DAYS = 2
RENTAL_EXPIRING_WARNING_HOURS = 24
INFINITE_SUPPLY_MODE = "infinite"
SOURCE_BUCKET_REAL = "real"
SOURCE_BUCKET_PRESEEDED = "preseeded"
SOURCE_BUCKET_CLUB = "club"
SUPPORTED_SOURCE_BUCKETS = frozenset({SOURCE_BUCKET_REAL, SOURCE_BUCKET_PRESEEDED, SOURCE_BUCKET_CLUB})
NATIONAL_SEED_ACTIVE_STATUSES = frozenset({"active", "available"})
NATIONAL_POOL_ONLY_SUPPLY_MODE = "national_pool_only"
STARTER_PACK_SLOTS: tuple[str, ...] = ("GK", "ST", "WINGER", "MIDFIELDER", "MIDFIELDER")
AUTO_BUILD_FORMATIONS: dict[str, tuple[str, ...]] = {
    "4-3-3": ("GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"),
    "4-1-4-1": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "CM", "RW", "LW", "ST"),
    "4-4-2": ("GK", "RB", "CB", "CB", "LB", "RM", "CM", "CM", "LM", "ST", "ST"),
    "4-5-1": ("GK", "RB", "CB", "CB", "LB", "RM", "CM", "CM", "CM", "LM", "ST"),
    "4-2-3-1": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "RW", "AM", "LW", "ST"),
    "5-4-1": ("GK", "RWB", "CB", "CB", "CB", "LWB", "CM", "CM", "RW", "LW", "ST"),
}
TACTIC_TO_FORMATION = {
    "possession": "4-3-3",
    "direct": "4-4-2",
    "counter": "4-2-3-1",
    "balanced": "4-2-3-1",
}


def _player_age(player: Player, *, today: date | None = None) -> int | None:
    reference_date = today or date.today()
    if player.date_of_birth is None:
        return None
    age = reference_date.year - player.date_of_birth.year
    if (reference_date.month, reference_date.day) < (player.date_of_birth.month, player.date_of_birth.day):
        age -= 1
    return max(age, 0)


@dataclass(frozen=True, slots=True)
class NationalPoolFilters:
    country_code: str | None = None
    real_only: bool = False
    preseeded_only: bool = False
    source_buckets: tuple[str, ...] = ()
    max_price_coin: Decimal | None = None
    positions: tuple[str, ...] = ()
    tradable_only: bool = False


class NationalTeamTournamentError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class NationalTeamTournamentService:
    session: Session
    wallet_service: WalletService | None = None
    gift_service: GiftEngineService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.gift_service is None:
            self.gift_service = GiftEngineService(self.session, wallet_service=self.wallet_service)

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)

    def _competition_settings(self, competition: NationalTeamCompetition) -> dict[str, Any]:
        metadata = dict(competition.metadata_json or {})
        distribution = {
            FreePlayerTier.HIGH.value: int(
                (metadata.get("free_player_distribution") or {}).get("high", DEFAULT_FREE_PLAYER_DISTRIBUTION["high"])
            ),
            FreePlayerTier.MID.value: int(
                (metadata.get("free_player_distribution") or {}).get("mid", DEFAULT_FREE_PLAYER_DISTRIBUTION["mid"])
            ),
            FreePlayerTier.LOW.value: int(
                (metadata.get("free_player_distribution") or {}).get("low", DEFAULT_FREE_PLAYER_DISTRIBUTION["low"])
            ),
        }
        return {
            "minimum_squad_size": int(metadata.get("minimum_squad_size", DEFAULT_MINIMUM_SQUAD_SIZE)),
            "maximum_squad_size": int(metadata.get("maximum_squad_size", DEFAULT_MAXIMUM_SQUAD_SIZE)),
            "free_player_quota": int(metadata.get("free_player_quota", DEFAULT_FREE_PLAYER_QUOTA)),
            "free_player_distribution": distribution,
            "entry_mode": str(metadata.get("entry_mode", "rental_only")),
        }

    @staticmethod
    def _normalize_token(value: str | None, *, upper: bool = False) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return normalized.upper() if upper else normalized.lower()

    @staticmethod
    def _normalize_position(position: str | None) -> str | None:
        normalized = NationalTeamTournamentService._normalize_token(position, upper=True)
        if normalized is None:
            return None
        aliases = {
            "RCB": "CB",
            "LCB": "CB",
            "SW": "CB",
            "RDM": "DM",
            "LDM": "DM",
            "CAM": "AM",
            "LAM": "AM",
            "RAM": "AM",
            "RCM": "CM",
            "LCM": "CM",
            "CDM": "DM",
            "CF": "ST",
            "RF": "RW",
            "LF": "LW",
            "RWF": "RW",
            "LWF": "LW",
            "RWB": "RWB",
            "LWB": "LWB",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _position_family(position: str | None) -> set[str]:
        normalized = NationalTeamTournamentService._normalize_position(position)
        if normalized is None:
            return set()
        families = {
            "GK": {"GK"},
            "RB": {"RB", "RWB"},
            "LB": {"LB", "LWB"},
            "RWB": {"RWB", "RB", "RW", "RM"},
            "LWB": {"LWB", "LB", "LW", "LM"},
            "CB": {"CB", "DM"},
            "DM": {"DM", "CM", "CB"},
            "CM": {"CM", "DM", "AM"},
            "AM": {"AM", "CM", "RW", "LW", "ST"},
            "RW": {"RW", "RM", "RWB", "LW"},
            "LW": {"LW", "LM", "LWB", "RW"},
            "RM": {"RM", "RW", "RWB", "CM"},
            "LM": {"LM", "LW", "LWB", "CM"},
            "ST": {"ST", "AM", "RW", "LW"},
            "WINGER": {"RW", "LW", "RM", "LM"},
            "MIDFIELDER": {"DM", "CM", "AM", "RM", "LM"},
        }
        return families.get(normalized, {normalized})

    @staticmethod
    def _source_bucket_from_player(player: Player) -> str:
        payload = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        explicit = NationalTeamTournamentService._normalize_token(
            payload.get("regen_type") or payload.get("rental_source_bucket")
        )
        if explicit in SUPPORTED_SOURCE_BUCKETS:
            return explicit
        if player.is_real_player:
            return SOURCE_BUCKET_REAL
        if player.current_club_id or player.current_club_profile_id or player.current_competition_id:
            return SOURCE_BUCKET_CLUB
        return SOURCE_BUCKET_PRESEEDED

    @staticmethod
    def _source_price_multiplier(source_bucket: str) -> Decimal:
        if source_bucket == SOURCE_BUCKET_PRESEEDED:
            return Decimal("0.6000")
        if source_bucket == SOURCE_BUCKET_CLUB:
            return Decimal("0.9000")
        return Decimal("1.0000")

    def _require_competition(self, competition_id: str) -> NationalTeamCompetition:
        competition = self.session.scalar(
            select(NationalTeamCompetition)
            .where(NationalTeamCompetition.id == competition_id)
            .options(selectinload(NationalTeamCompetition.entries))
        )
        if competition is None:
            raise NationalTeamTournamentError(
                "National team competition was not found.", reason="competition_not_found"
            )
        return competition

    def _require_entry(self, entry_id: str) -> NationalTeamEntry:
        entry = self.session.scalar(
            select(NationalTeamEntry)
            .where(NationalTeamEntry.id == entry_id)
            .options(
                selectinload(NationalTeamEntry.competition),
                selectinload(NationalTeamEntry.squad_members),
                selectinload(NationalTeamEntry.manager_history),
            )
        )
        if entry is None:
            raise NationalTeamTournamentError("National team entry was not found.", reason="entry_not_found")
        return entry

    def _require_managed_entry(self, entry_id: str, actor: User) -> NationalTeamEntry:
        entry = self._require_entry(entry_id)
        allowed_user_ids = {entry.manager_user_id}
        if entry.entry_owner_user_id is not None:
            allowed_user_ids.add(entry.entry_owner_user_id)
        if actor.id not in allowed_user_ids:
            raise NationalTeamTournamentError(
                "Only the entry owner or assigned manager can manage this entry.", reason="entry_manager_required"
            )
        return entry

    def _validate_entry_window(self, competition: NationalTeamCompetition) -> None:
        now = utcnow()
        if competition.entry_opens_at is not None and competition.entry_opens_at > now:
            raise NationalTeamTournamentError("Entry is not open yet.", reason="competition_entry_not_open")
        if competition.entry_closes_at is not None and competition.entry_closes_at < now:
            raise NationalTeamTournamentError(
                "Entry has closed for this tournament.", reason="competition_entry_closed"
            )
        if str(competition.status).strip().lower() == "live":
            raise NationalTeamTournamentError(
                "Tournament squads are locked while the tournament is live.", reason="competition_already_live"
            )
        if competition.kickoff_at is not None and competition.kickoff_at <= now:
            raise NationalTeamTournamentError(
                "Tournament squads are locked after kickoff.", reason="competition_already_live"
            )
        if competition.linked_competition_id:
            try:
                CompetitionLockService(self.session).ensure_rentals_allowed(
                    competition_id=competition.linked_competition_id
                )
            except CompetitionLockError as exc:
                raise NationalTeamTournamentError(exc.detail, reason="competition_already_live") from exc
        if competition.completed_at is not None:
            raise NationalTeamTournamentError("Tournament has already completed.", reason="competition_completed")

    def _contract_window(self, competition: NationalTeamCompetition) -> tuple[Any, Any]:
        now = utcnow()
        return now, now + timedelta(days=DEFAULT_RENTAL_DURATION_DAYS)

    def _player_name(self, player: Player) -> str:
        return (
            player.canonical_display_name
            or player.short_name
            or " ".join(part for part in [player.first_name, player.last_name] if part)
            or player.full_name
        )

    def _player_market_value_eur(self, player: Player) -> Decimal:
        fallback = Decimal("1000000")
        current_reference = self._normalize_amount(player.current_market_reference_value)
        historical_reference = self._normalize_amount(player.market_value_eur)
        value = current_reference if current_reference > Decimal("0.0000") else historical_reference
        return value if value > Decimal("0.0000") else fallback

    def _player_overall_rating(self, player: Player, *, average_rating: float | None, league_rank: int | None) -> int:
        market_value = float(self._player_market_value_eur(player))
        if market_value >= 90_000_000:
            base = 91
        elif market_value >= 60_000_000:
            base = 88
        elif market_value >= 35_000_000:
            base = 85
        elif market_value >= 20_000_000:
            base = 82
        elif market_value >= 10_000_000:
            base = 79
        elif market_value >= 5_000_000:
            base = 76
        elif market_value >= 2_000_000:
            base = 73
        elif market_value >= 1_000_000:
            base = 70
        else:
            base = 67
        if average_rating is not None:
            base += int(round((average_rating - 7.0) * 4))
        if league_rank is not None:
            base += max(-2, min(3, 4 - int(league_rank)))
        if player.real_player_tier:
            tier = player.real_player_tier.strip().lower()
            if tier in {"elite", "world_class"}:
                base += 2
            elif tier in {"prospect", "rotational"}:
                base -= 1
        return max(65, min(96, base))

    def _player_tier(self, overall_rating: int) -> str:
        if overall_rating >= 85:
            return FreePlayerTier.HIGH.value
        if overall_rating >= 75:
            return FreePlayerTier.MID.value
        return FreePlayerTier.LOW.value

    def _player_gsi(
        self,
        *,
        player: Player,
        summary: PlayerSummaryReadModel | None,
        overall_rating: int,
    ) -> int:
        payload = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        for key in ("gsi", "global_scouting_index"):
            raw_value = payload.get(key)
            if raw_value is None:
                continue
            try:
                resolved = int(round(float(raw_value)))
            except (TypeError, ValueError):
                continue
            if resolved > 0:
                return resolved
        summary_payload = (
            dict(summary.summary_json or {}) if summary is not None and isinstance(summary.summary_json, dict) else {}
        )
        raw_summary_gsi = summary_payload.get("global_scouting_index")
        if raw_summary_gsi is not None:
            try:
                resolved_summary = int(round(float(raw_summary_gsi)))
            except (TypeError, ValueError):
                resolved_summary = 0
            if resolved_summary > 0:
                return resolved_summary
        return max(55, int(overall_rating))

    def _base_value_coin(self, *, gsi: int) -> Decimal:
        return self._normalize_amount(gsi)

    def _loan_price_coin(self, *, gsi: int, source_bucket: str) -> Decimal:
        return (self._normalize_amount(gsi) * self._source_price_multiplier(source_bucket)).quantize(
            AMOUNT_QUANTUM, rounding=ROUND_HALF_UP
        )

    def _demand_multiplier(self, *, player_id: str) -> Decimal:
        active_contracts = int(
            self.session.scalar(
                select(func.count())
                .select_from(RentalContract)
                .where(
                    RentalContract.player_id == player_id,
                    RentalContract.status == RentalContractStatus.ACTIVE,
                )
            )
            or 0
        )
        recent_contracts = int(
            self.session.scalar(
                select(func.count())
                .select_from(RentalContract)
                .where(
                    RentalContract.player_id == player_id,
                    RentalContract.created_at >= (utcnow() - timedelta(days=14)),
                )
            )
            or 0
        )
        multiplier = Decimal("1.0000")
        multiplier += Decimal(active_contracts) * Decimal("0.1500")
        multiplier += Decimal(max(recent_contracts - active_contracts, 0)) * Decimal("0.0500")
        return min(multiplier, Decimal("1.7500")).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)

    def _priced_pool_item(self, item: dict[str, Any]) -> dict[str, Any]:
        demand_multiplier = self._demand_multiplier(player_id=str(item["player_id"]))
        base_loan_price = self._normalize_amount(item["loan_price_coin"])
        priced = dict(item)
        priced["demand_multiplier"] = demand_multiplier
        priced["loan_price_coin"] = (base_loan_price * demand_multiplier).quantize(
            AMOUNT_QUANTUM,
            rounding=ROUND_HALF_UP,
        )
        return priced

    def _country_tokens(
        self,
        *,
        country_name: str | None,
        alpha2_code: str | None,
        alpha3_code: str | None,
        fifa_code: str | None,
    ) -> set[str]:
        tokens = {
            token
            for token in {
                self._normalize_token(country_name, upper=True),
                self._normalize_token(alpha2_code, upper=True),
                self._normalize_token(alpha3_code, upper=True),
                self._normalize_token(fifa_code, upper=True),
            }
            if token is not None
        }
        return tokens

    @staticmethod
    def _competition_age_band(competition: NationalTeamCompetition | None) -> str:
        normalized = str(getattr(competition, "age_band", None) or "senior").strip().lower()
        if normalized in {"u17", "under17"}:
            return "u17"
        if normalized in {"u20", "under20"}:
            return "u20"
        return "senior"

    @staticmethod
    def _competition_reference_date(competition: NationalTeamCompetition | None) -> date:
        if competition is not None and competition.kickoff_at is not None:
            return competition.kickoff_at.date()
        if competition is not None and competition.entry_closes_at is not None:
            return competition.entry_closes_at.date()
        return utcnow().date()

    @classmethod
    def _age_band_limit(cls, competition: NationalTeamCompetition | None) -> int | None:
        age_band = cls._competition_age_band(competition)
        if age_band == "u17":
            return 17
        if age_band == "u20":
            return 20
        return None

    @staticmethod
    def _seed_age(seed: NationalRegenSeed) -> int:
        if getattr(seed, "age", None) is not None:
            return int(seed.age)
        metadata = dict(seed.metadata_json or {})
        explicit_age = metadata.get("age")
        if isinstance(explicit_age, int):
            return explicit_age
        return 18

    @staticmethod
    def _seed_age_band(seed: NationalRegenSeed) -> str:
        normalized = str(getattr(seed, "age_band", None) or "").strip().lower()
        if normalized in {"u17", "u20", "senior"}:
            return normalized
        metadata = dict(seed.metadata_json or {})
        metadata_band = str(metadata.get("age_band") or "").strip().lower()
        if metadata_band in {"u17", "u20", "senior"}:
            return metadata_band
        age = NationalTeamTournamentService._seed_age(seed)
        if age <= 17:
            return "u17"
        if age <= 20:
            return "u20"
        return "senior"

    @staticmethod
    def _source_priority(item: dict[str, Any]) -> int:
        bucket = str(item.get("source_bucket") or "").strip().lower()
        if bucket == SOURCE_BUCKET_REAL:
            return 2
        if bucket == SOURCE_BUCKET_CLUB:
            return 1
        return 0

    @staticmethod
    def _pool_item_market_flags(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "is_regen": bool(item.get("is_regen", False)),
            "is_preseeded_national_regen": bool(item.get("is_preseeded_national_regen", False)),
            "market_eligible": bool(item.get("market_eligible", True)),
            "share_market_eligible": bool(item.get("share_market_eligible", True)),
            "tradable": bool(item.get("tradable", True)),
            "buyable": bool(item.get("buyable", True)),
            "transferable": bool(item.get("transferable", True)),
            "card_mint_eligible": bool(item.get("card_mint_eligible", True)),
            "buy_cta_allowed": bool(item.get("buy_cta_allowed", True)),
            "national_pool_only": bool(item.get("national_pool_only", False)),
        }

    def _player_catalog(
        self,
        *,
        limit: int = 300,
        reference_date: date | None = None,
    ) -> list[dict[str, Any]]:
        season_stats = (
            select(
                PlayerSeasonStat.player_id.label("player_id"),
                func.max(PlayerSeasonStat.average_rating).label("average_rating"),
            )
            .group_by(PlayerSeasonStat.player_id)
            .subquery()
        )
        stmt = (
            select(
                Player,
                season_stats.c.average_rating,
                IngestionCountry.name.label("country_name"),
                IngestionCountry.alpha2_code.label("country_alpha2"),
                IngestionCountry.alpha3_code.label("country_alpha3"),
                IngestionCountry.fifa_code.label("country_fifa"),
                IngestionCompetition.name.label("competition_name"),
                InternalLeague.name.label("league_name"),
                InternalLeague.rank.label("league_rank"),
                PlayerSummaryReadModel,
            )
            .outerjoin(season_stats, season_stats.c.player_id == Player.id)
            .outerjoin(IngestionCountry, IngestionCountry.id == Player.country_id)
            .outerjoin(IngestionCompetition, IngestionCompetition.id == Player.current_competition_id)
            .outerjoin(InternalLeague, InternalLeague.id == Player.internal_league_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .limit(limit)
        )
        rows: list[dict[str, Any]] = []
        for (
            player,
            average_rating,
            country_name,
            country_alpha2,
            country_alpha3,
            country_fifa,
            competition_name,
            league_name,
            league_rank,
            summary,
        ) in self.session.execute(stmt).all():
            overall_rating = self._player_overall_rating(
                player,
                average_rating=float(average_rating) if average_rating is not None else None,
                league_rank=int(league_rank) if league_rank is not None else None,
            )
            source_bucket = self._source_bucket_from_player(player)
            gsi = self._player_gsi(player=player, summary=summary, overall_rating=overall_rating)
            base_value_coin = self._base_value_coin(gsi=gsi)
            country_tokens = self._country_tokens(
                country_name=country_name,
                alpha2_code=country_alpha2,
                alpha3_code=country_alpha3,
                fifa_code=country_fifa,
            )
            rows.append(
                {
                    "player": player,
                    "player_id": player.id,
                    "player_name": self._player_name(player),
                    "overall_rating": overall_rating,
                    "primary_position": self._normalize_position(player.normalized_position or player.position),
                    "current_club_name": player.real_world_club_name,
                    "current_league_name": league_name or competition_name or player.real_world_league_name,
                    "nationality": country_name,
                    "country_code": country_alpha2 or country_fifa or country_alpha3,
                    "country_tokens": country_tokens,
                    "age": _player_age(player, today=reference_date),
                    "gsi": gsi,
                    "base_value_coin": base_value_coin,
                    "loan_price_coin": self._loan_price_coin(gsi=gsi, source_bucket=source_bucket),
                    "tier_label": self._player_tier(overall_rating),
                    "source_bucket": source_bucket,
                    "is_regen": not bool(player.is_real_player),
                    **market_access_payload(player),
                    "supply_mode": INFINITE_SUPPLY_MODE,
                }
            )
        rows.sort(
            key=lambda item: (
                -int(item["overall_rating"]),
                -float(item["base_value_coin"]),
                str(item["player_name"]).lower(),
            )
        )
        return rows

    def _country_filter_aliases(self, country_code: str | None) -> tuple[set[str], set[str]]:
        normalized = self._normalize_token(country_code, upper=True)
        if normalized is None:
            return set(), set()
        country = self.session.scalar(
            select(IngestionCountry).where(
                or_(
                    func.upper(IngestionCountry.alpha2_code) == normalized,
                    func.upper(IngestionCountry.alpha3_code) == normalized,
                    func.upper(IngestionCountry.fifa_code) == normalized,
                )
            )
        )
        if country is None:
            return {normalized}, set()
        code_aliases = {
            token
            for token in {
                self._normalize_token(country.alpha2_code, upper=True),
                self._normalize_token(country.alpha3_code, upper=True),
                self._normalize_token(country.fifa_code, upper=True),
            }
            if token is not None
        }
        name_aliases = {name for name in {self._normalize_token(country.name, upper=True)} if name is not None}
        if not code_aliases:
            code_aliases.add(normalized)
        return code_aliases, name_aliases

    def _national_seed_catalog(
        self,
        *,
        filters: NationalPoolFilters,
        competition: NationalTeamCompetition | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        age_band = self._competition_age_band(competition)
        stmt = (
            select(NationalRegenSeed)
            .where(NationalRegenSeed.status.in_(tuple(NATIONAL_SEED_ACTIVE_STATUSES)))
            .where(NationalRegenSeed.age_band == age_band)
            .order_by(
                NationalRegenSeed.country_name.asc(),
                NationalRegenSeed.potential_rating.desc(),
                NationalRegenSeed.current_rating.desc(),
                NationalRegenSeed.display_name.asc(),
            )
            .limit(limit)
        )
        code_aliases, name_aliases = self._country_filter_aliases(filters.country_code)
        if code_aliases or name_aliases:
            clauses: list[Any] = []
            if code_aliases:
                clauses.append(func.upper(NationalRegenSeed.country_code).in_(tuple(sorted(code_aliases))))
            if name_aliases:
                clauses.append(func.upper(NationalRegenSeed.country_name).in_(tuple(sorted(name_aliases))))
            stmt = stmt.where(or_(*clauses))
        countries = list(self.session.scalars(select(IngestionCountry)).all())
        countries_by_code: dict[str, IngestionCountry] = {}
        countries_by_name: dict[str, IngestionCountry] = {}
        for country in countries:
            for token in (
                self._normalize_token(country.alpha2_code, upper=True),
                self._normalize_token(country.alpha3_code, upper=True),
                self._normalize_token(country.fifa_code, upper=True),
            ):
                if token is not None:
                    countries_by_code.setdefault(token, country)
            normalized_name = self._normalize_token(country.name, upper=True)
            if normalized_name is not None:
                countries_by_name.setdefault(normalized_name, country)
        items: list[dict[str, Any]] = []
        for seed in self.session.scalars(stmt).all():
            seed_age = self._seed_age(seed)
            age_limit = self._age_band_limit(competition)
            if age_limit is not None and seed_age > age_limit:
                continue
            country = countries_by_code.get(
                self._normalize_token(seed.country_code, upper=True) or ""
            ) or countries_by_name.get(self._normalize_token(seed.country_name, upper=True) or "")
            country_tokens = self._country_tokens(
                country_name=country.name if country is not None else seed.country_name,
                alpha2_code=country.alpha2_code if country is not None else seed.country_code,
                alpha3_code=country.alpha3_code if country is not None else None,
                fifa_code=country.fifa_code if country is not None else None,
            )
            gsi = max(55, min(95, int(round((seed.current_rating * 0.7) + (seed.potential_rating * 0.3)))))
            items.append(
                {
                    "player_id": seed.id,
                    "player_name": seed.display_name,
                    "overall_rating": int(seed.current_rating),
                    "primary_position": self._normalize_position(seed.primary_position),
                    "current_club_name": None,
                    "current_league_name": None,
                    "nationality": seed.country_name,
                    "country_code": (
                        country.alpha2_code if country is not None and country.alpha2_code else seed.country_code
                    ),
                    "country_tokens": country_tokens,
                    "age": seed_age,
                    "gsi": gsi,
                    "base_value_coin": self._base_value_coin(gsi=gsi),
                    "loan_price_coin": self._loan_price_coin(gsi=gsi, source_bucket=SOURCE_BUCKET_PRESEEDED),
                    "tier_label": self._player_tier(int(seed.current_rating)),
                    "source_bucket": SOURCE_BUCKET_PRESEEDED,
                    "is_regen": True,
                    **market_access_payload(seed),
                    "supply_mode": NATIONAL_POOL_ONLY_SUPPLY_MODE,
                }
            )
        return items

    def _normalize_pool_filters(
        self,
        *,
        country_code: str | None = None,
        real_only: bool = False,
        preseeded_only: bool = False,
        source_buckets: tuple[str, ...] = (),
        max_price_coin: Decimal | None = None,
        positions: tuple[str, ...] = (),
        tradable_only: bool = False,
    ) -> NationalPoolFilters:
        if real_only and preseeded_only:
            raise NationalTeamTournamentError(
                "real_only and preseeded_only cannot both be enabled.",
                reason="invalid_source_filters",
            )
        normalized_source_buckets = {
            bucket
            for bucket in (
                self._normalize_token(value)
                for value in ((SOURCE_BUCKET_REAL,) if real_only else ())
                + ((SOURCE_BUCKET_PRESEEDED,) if preseeded_only else ())
                + tuple(source_buckets)
            )
            if bucket in SUPPORTED_SOURCE_BUCKETS
        }
        normalized_positions = tuple(
            position
            for position in (
                self._normalize_position(value) or self._normalize_token(value, upper=True) for value in positions
            )
            if position is not None
        )
        return NationalPoolFilters(
            country_code=self._normalize_token(country_code, upper=True),
            real_only=real_only,
            preseeded_only=preseeded_only,
            source_buckets=tuple(sorted(normalized_source_buckets)),
            max_price_coin=self._normalize_amount(max_price_coin) if max_price_coin is not None else None,
            positions=normalized_positions,
            tradable_only=tradable_only,
        )

    def _pool_item_matches(self, item: dict[str, Any], *, filters: NationalPoolFilters) -> bool:
        if filters.country_code and filters.country_code not in set(item.get("country_tokens") or ()):
            return False
        if filters.source_buckets and item.get("source_bucket") not in set(filters.source_buckets):
            return False
        if (
            filters.max_price_coin is not None
            and self._normalize_amount(item.get("loan_price_coin")) > filters.max_price_coin
        ):
            return False
        if filters.tradable_only and not bool(item.get("tradable")):
            return False
        if filters.positions:
            primary_position = item.get("primary_position")
            if not any(self._slot_fit_score(position, primary_position) > 0 for position in filters.positions):
                return False
        return True

    def _national_pool(
        self,
        *,
        filters: NationalPoolFilters,
        competition: NationalTeamCompetition | None = None,
        limit: int = 300,
    ) -> list[dict[str, Any]]:
        reference_date = self._competition_reference_date(competition)
        age_limit = self._age_band_limit(competition)
        catalog = [
            *self._player_catalog(limit=max(limit, 300), reference_date=reference_date),
            *self._national_seed_catalog(filters=filters, competition=competition, limit=max(limit, 300)),
        ]
        filtered = [
            item
            for item in catalog
            if (age_limit is None or (item.get("age") is not None and int(item["age"]) <= age_limit))
            and self._pool_item_matches(item, filters=filters)
        ]
        filtered.sort(
            key=lambda item: (
                -self._source_priority(item),
                -int(item["overall_rating"]),
                -int(item["gsi"]),
                float(self._normalize_amount(item["loan_price_coin"])),
                str(item["player_name"]).lower(),
            )
        )
        return filtered

    def _pool_item_payload(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "player_id": item["player_id"],
            "player_name": item["player_name"],
            "overall_rating": item["overall_rating"],
            "primary_position": item["primary_position"],
            "current_club_name": item["current_club_name"],
            "current_league_name": item["current_league_name"],
            "nationality": item["nationality"],
            "country_code": item["country_code"],
            "age": item.get("age"),
            "gsi": item["gsi"],
            "base_value_coin": item["base_value_coin"],
            "loan_price_coin": item["loan_price_coin"],
            "tier_label": item["tier_label"],
            "source_bucket": item["source_bucket"],
            "is_regen": bool(item.get("is_regen", False)),
            "is_preseeded_national_regen": bool(item.get("is_preseeded_national_regen", False)),
            "market_eligible": bool(item.get("market_eligible", True)),
            "share_market_eligible": bool(item.get("share_market_eligible", True)),
            "tradable": bool(item.get("tradable", True)),
            "buyable": bool(item.get("buyable", True)),
            "transferable": bool(item.get("transferable", True)),
            "card_mint_eligible": bool(item.get("card_mint_eligible", True)),
            "buy_cta_allowed": bool(item.get("buy_cta_allowed", True)),
            "national_pool_only": bool(item.get("national_pool_only", False)),
            "supply_mode": item["supply_mode"],
            "demand_multiplier": item.get("demand_multiplier", Decimal("1.0000")),
        }

    def list_rental_players(
        self,
        *,
        competition_id: str,
        limit: int = 100,
        offset: int = 0,
        country_code: str | None = None,
        real_only: bool = False,
        preseeded_only: bool = False,
        source_buckets: tuple[str, ...] = (),
        max_price_coin: Decimal | None = None,
        positions: tuple[str, ...] = (),
        tradable_only: bool = False,
    ) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        filters = self._normalize_pool_filters(
            country_code=country_code,
            real_only=real_only,
            preseeded_only=preseeded_only,
            source_buckets=source_buckets,
            max_price_coin=max_price_coin,
            positions=positions,
            tradable_only=tradable_only,
        )
        catalog = [
            self._priced_pool_item(item)
            for item in self._national_pool(
                filters=filters,
                competition=competition,
                limit=max(limit + offset, 1000),
            )
        ]
        items = catalog[offset : offset + limit]
        return {"total": len(catalog), "items": [self._pool_item_payload(item) for item in items]}

    def _slot_fit_score(self, slot: str, player_position: str | None) -> int:
        normalized_slot = self._normalize_position(slot) or self._normalize_token(slot, upper=True)
        normalized_position = self._normalize_position(player_position)
        if normalized_slot is None or normalized_position is None:
            return 0
        if normalized_slot == normalized_position:
            return 3
        slot_family = self._position_family(normalized_slot)
        player_family = self._position_family(normalized_position)
        if normalized_position in slot_family:
            return 2
        if slot_family & player_family:
            return 1
        return 0

    def _pick_slot_players(
        self,
        *,
        pool: list[dict[str, Any]],
        slots: tuple[str, ...],
        excluded_player_ids: set[str] | None = None,
        budget_coin: Decimal | None = None,
    ) -> dict[str, Any]:
        excluded_ids = set(excluded_player_ids or set())
        selected: list[dict[str, Any]] = []
        total_cost = Decimal("0.0000")
        unfilled_slots: list[str] = []

        for slot in slots:
            candidates = []
            for item in pool:
                if item["player_id"] in excluded_ids:
                    continue
                fit_score = self._slot_fit_score(slot, item.get("primary_position"))
                if fit_score <= 0:
                    continue
                price = self._normalize_amount(item.get("loan_price_coin"))
                if budget_coin is not None and total_cost + price > budget_coin:
                    continue
                candidates.append((fit_score, item))
            if not candidates:
                unfilled_slots.append(slot)
                continue
            _, chosen = max(
                candidates,
                key=lambda payload: (
                    payload[0],
                    self._source_priority(payload[1]),
                    int(payload[1]["overall_rating"]),
                    int(payload[1]["gsi"]),
                    -float(payload[1]["loan_price_coin"]),
                    str(payload[1]["player_name"]).lower(),
                ),
            )
            excluded_ids.add(chosen["player_id"])
            total_cost += self._normalize_amount(chosen["loan_price_coin"])
            selected.append({**self._pool_item_payload(chosen), "assigned_slot": slot})

        return {
            "selected": selected,
            "total_cost_coin": total_cost.quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP),
            "unfilled_slots": unfilled_slots,
        }

    def _source_mix_summary(self, players: list[dict[str, Any]]) -> dict[str, int]:
        summary = {
            SOURCE_BUCKET_REAL: 0,
            SOURCE_BUCKET_PRESEEDED: 0,
            SOURCE_BUCKET_CLUB: 0,
            "regen": 0,
        }
        for item in players:
            bucket = str(item.get("source_bucket") or "").strip().lower()
            if bucket in {SOURCE_BUCKET_REAL, SOURCE_BUCKET_PRESEEDED, SOURCE_BUCKET_CLUB}:
                summary[bucket] += 1
            if bucket != SOURCE_BUCKET_REAL:
                summary["regen"] += 1
        return summary

    @staticmethod
    def _remaining_slots(slots: tuple[str, ...], selected: list[dict[str, Any]]) -> tuple[str, ...]:
        remaining = list(slots)
        for item in selected:
            assigned_slot = item.get("assigned_slot")
            if assigned_slot in remaining:
                remaining.remove(assigned_slot)
        return tuple(remaining)

    def _pick_mixed_auto_build(
        self,
        *,
        pool: list[dict[str, Any]],
        slots: tuple[str, ...],
        budget_coin: Decimal,
    ) -> dict[str, Any]:
        base_selection = self._pick_slot_players(
            pool=pool, slots=slots, excluded_player_ids=set(), budget_coin=budget_coin
        )
        base_players = list(base_selection["selected"])
        base_mix = self._source_mix_summary(base_players)

        has_real = any(str(item.get("source_bucket") or "") == SOURCE_BUCKET_REAL for item in pool)
        has_regen = any(str(item.get("source_bucket") or "") != SOURCE_BUCKET_REAL for item in pool)
        if not has_real or not has_regen or (base_mix[SOURCE_BUCKET_REAL] > 0 and base_mix["regen"] > 0):
            return {**base_selection, "mix_applied": False}

        regen_pool = [item for item in pool if str(item.get("source_bucket") or "") != SOURCE_BUCKET_REAL]
        preferred_regen_slots = tuple(slot for slot in slots if slot in {"AM", "CM", "DM", "RW", "LW", "ST"})[:3]
        if not preferred_regen_slots:
            return {**base_selection, "mix_applied": False}

        regen_budget = (budget_coin * Decimal("0.40")).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
        seeded_selection = self._pick_slot_players(
            pool=regen_pool,
            slots=preferred_regen_slots,
            excluded_player_ids=set(),
            budget_coin=regen_budget,
        )
        seeded_players = list(seeded_selection["selected"])
        if not seeded_players:
            return {**base_selection, "mix_applied": False}

        remaining_slots = self._remaining_slots(slots, seeded_players)
        remaining_budget = (budget_coin - self._normalize_amount(seeded_selection["total_cost_coin"])).quantize(
            AMOUNT_QUANTUM, rounding=ROUND_HALF_UP
        )
        completion_selection = self._pick_slot_players(
            pool=pool,
            slots=remaining_slots,
            excluded_player_ids={item["player_id"] for item in seeded_players},
            budget_coin=remaining_budget,
        )
        mixed_players = [*seeded_players, *list(completion_selection["selected"])]
        mixed_mix = self._source_mix_summary(mixed_players)
        if mixed_mix[SOURCE_BUCKET_REAL] <= 0 or mixed_mix["regen"] <= 0:
            return {**base_selection, "mix_applied": False}
        if len(mixed_players) < len(base_players):
            return {**base_selection, "mix_applied": False}

        total_cost_coin = (
            self._normalize_amount(seeded_selection["total_cost_coin"])
            + self._normalize_amount(completion_selection["total_cost_coin"])
        ).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
        return {
            "selected": mixed_players,
            "total_cost_coin": total_cost_coin,
            "unfilled_slots": [
                *list(seeded_selection["unfilled_slots"]),
                *list(completion_selection["unfilled_slots"]),
            ],
            "mix_applied": True,
        }

    def _resolve_auto_build_formation(self, tactic: str | None) -> tuple[str, str]:
        normalized_tactic = self._normalize_token(tactic) or "balanced"
        if normalized_tactic in AUTO_BUILD_FORMATIONS:
            return normalized_tactic, normalized_tactic
        return normalized_tactic, TACTIC_TO_FORMATION.get(normalized_tactic, TACTIC_TO_FORMATION["balanced"])

    def _auto_build_slots(self, formation: str, squad_size: int | None) -> tuple[str, ...]:
        starters = tuple(AUTO_BUILD_FORMATIONS[formation])
        target_size = max(len(starters), min(int(squad_size or len(starters)), DEFAULT_MAXIMUM_SQUAD_SIZE))
        bench_pattern = ("GK", "CB", "RB", "LB", "DM", "CM", "WINGER", "AM", "ST")
        slots = list(starters)
        while len(slots) < target_size:
            slots.append(bench_pattern[(len(slots) - len(starters)) % len(bench_pattern)])
        return tuple(slots)

    def _age_grade_allows(self, item: dict[str, Any], age_grade: str | None) -> bool:
        normalized = self._normalize_token(age_grade)
        if normalized in {None, "", "senior"}:
            return True
        age = item.get("age")
        if age is None:
            return False
        if normalized in {"u17", "under17", "under_17"}:
            return int(age) <= 17
        if normalized in {"u20", "under20", "under_20"}:
            return int(age) <= 20
        return True

    def auto_build_squad(
        self,
        *,
        competition_id: str,
        country_code: str,
        budget_coin: Decimal,
        squad_size: int | None = None,
        age_grade: str | None = None,
        tactic: str | None = None,
        real_only: bool = False,
        preseeded_only: bool = False,
        source_buckets: tuple[str, ...] = (),
        positions: tuple[str, ...] = (),
        tradable_only: bool = False,
    ) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        normalized_country = self._normalize_token(country_code, upper=True)
        if normalized_country is None:
            raise NationalTeamTournamentError(
                "Country code is required for auto-build.", reason="country_code_required"
            )
        requested_budget = self._normalize_amount(budget_coin)
        if requested_budget <= Decimal("0.0000"):
            raise NationalTeamTournamentError(
                "Auto-build budget must be greater than zero.", reason="auto_build_budget_invalid"
            )

        tactic_label, formation = self._resolve_auto_build_formation(tactic)
        filters = self._normalize_pool_filters(
            country_code=normalized_country,
            real_only=real_only,
            preseeded_only=preseeded_only,
            source_buckets=source_buckets,
            positions=positions,
            tradable_only=tradable_only,
        )
        pool = [
            self._priced_pool_item(item)
            for item in self._national_pool(filters=filters, competition=competition, limit=1500)
            if self._age_grade_allows(item, age_grade)
        ]
        slots = self._auto_build_slots(formation, squad_size)
        selection = self._pick_mixed_auto_build(
            pool=pool,
            slots=slots,
            budget_coin=requested_budget,
        )
        total_cost_coin = self._normalize_amount(selection["total_cost_coin"])
        remaining_budget_coin = (requested_budget - total_cost_coin).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
        selected_players = list(selection["selected"])
        source_mix = self._source_mix_summary(selected_players)
        return {
            "competition_id": competition_id,
            "country_code": normalized_country,
            "tactic": tactic_label,
            "formation": formation,
            "squad_size": len(slots),
            "age_grade": self._normalize_token(age_grade),
            "requested_budget_coin": requested_budget,
            "total_cost_coin": total_cost_coin,
            "remaining_budget_coin": remaining_budget_coin,
            "selected_count": len(selected_players),
            "complete": not selection["unfilled_slots"] and len(selected_players) == len(slots),
            "mix_applied": bool(selection.get("mix_applied")),
            "source_mix": source_mix,
            "unfilled_slots": list(selection["unfilled_slots"]),
            "players": selected_players,
        }

    def previous_roster(
        self,
        *,
        user_id: str,
        country_code: str,
        age_grade: str | None = None,
    ) -> dict[str, Any] | None:
        normalized_country = self._normalize_token(country_code, upper=True)
        normalized_age_grade = self._normalize_token(age_grade)
        if normalized_country is None:
            raise NationalTeamTournamentError(
                "Country code is required for previous roster lookup.",
                reason="country_code_required",
            )
        stmt = (
            select(NationalTeamCompetitionEntry)
            .join(NationalTeamCompetition)
            .where(
                NationalTeamCompetitionEntry.user_id == user_id,
                NationalTeamCompetitionEntry.country_code == normalized_country,
            )
            .order_by(NationalTeamCompetitionEntry.updated_at.desc())
        )
        if normalized_age_grade:
            stmt = stmt.where(NationalTeamCompetition.age_band == normalized_age_grade)
        entry = self.session.scalar(stmt)
        if entry is None:
            return None
        return {
            "entry_id": entry.id,
            "competition_id": entry.competition_id,
            "country_code": entry.country_code,
            "country_name": entry.country_name,
            "age_grade": entry.competition.age_band if entry.competition is not None else normalized_age_grade,
            "squad": list(entry.squad_json or []),
            "updated_at": entry.updated_at,
        }

    def _entry_rental_contracts(self, entry_id: str) -> list[RentalContract]:
        contracts = list(
            self.session.scalars(
                select(RentalContract)
                .where(
                    RentalContract.entry_id == entry_id,
                    RentalContract.status == RentalContractStatus.ACTIVE,
                )
                .order_by(RentalContract.created_at.asc())
            ).all()
        )
        for contract in contracts:
            self._extend_contract_for_finalist(contract)
        return contracts

    def _extend_contract_for_finalist(self, contract: RentalContract) -> None:
        competition = self.session.get(NationalTeamCompetition, contract.tournament_id)
        if competition is None or competition.completed_at is None:
            return
        base_end_date = contract.start_date + timedelta(days=DEFAULT_RENTAL_DURATION_DAYS)
        if competition.completed_at <= base_end_date or contract.end_date >= competition.completed_at:
            return
        finalist = self.session.scalar(
            select(NationalTeamCompetitionEntry).where(
                NationalTeamCompetitionEntry.competition_id == competition.id,
                NationalTeamCompetitionEntry.user_id == contract.user_id,
                (
                    (NationalTeamCompetitionEntry.qualified.is_(True))
                    | (NationalTeamCompetitionEntry.status.in_(("finalist", "final", "winner", "qualified")))
                ),
            )
        )
        if finalist is None:
            return
        contract.end_date = competition.completed_at
        contract.metadata_json = {
            **dict(contract.metadata_json or {}),
            "extended_until": competition.completed_at.isoformat(),
            "extension_reason": "gtex_national_finalist",
        }
        self.session.flush()

    def _entry_rental_members(self, entry_id: str) -> list[NationalTeamRentalSquadMember]:
        return list(
            self.session.scalars(
                select(NationalTeamRentalSquadMember)
                .where(NationalTeamRentalSquadMember.entry_id == entry_id)
                .order_by(NationalTeamRentalSquadMember.created_at.asc())
            ).all()
        )

    def _entry_free_player_counts(self, entry_id: str) -> dict[str, int]:
        counts = {FreePlayerTier.HIGH.value: 0, FreePlayerTier.MID.value: 0, FreePlayerTier.LOW.value: 0}
        for contract in self._entry_rental_contracts(entry_id):
            if not contract.is_free_player:
                continue
            tier = (contract.free_player_tier or "").strip().lower()
            if tier in counts:
                counts[tier] += 1
        return counts

    def _refresh_entry_squad_size(self, entry: NationalTeamEntry) -> None:
        rental_count = int(
            self.session.scalar(
                select(func.count(NationalTeamRentalSquadMember.id)).where(
                    NationalTeamRentalSquadMember.entry_id == entry.id
                )
            )
            or 0
        )
        entry.squad_size = len(entry.squad_members) + rental_count
        self.session.flush()

    def _next_shirt_number(self, entry_id: str) -> int:
        entry = self._require_entry(entry_id)
        taken = {
            number
            for number in [
                *[member.shirt_number for member in self._entry_rental_members(entry.id)],
                *[member.shirt_number for member in entry.squad_members],
            ]
            if number is not None
        }
        for candidate in range(1, 100):
            if candidate not in taken:
                return candidate
        return 99

    def _entry_detail_payload(self, entry: NationalTeamEntry) -> dict[str, Any]:
        competition = entry.competition
        if competition is None:
            competition = self._require_competition(entry.competition_id)
        settings = self._competition_settings(competition)
        contracts = self._entry_rental_contracts(entry.id)
        members = self._entry_rental_members(entry.id)
        free_counts = self._entry_free_player_counts(entry.id)
        free_used = sum(free_counts.values())
        return {
            "id": entry.id,
            "competition_id": entry.competition_id,
            "country_code": entry.country_code,
            "country_name": entry.country_name,
            "entry_owner_user_id": entry.entry_owner_user_id,
            "manager_user_id": entry.manager_user_id,
            "squad_size": entry.squad_size,
            "metadata_json": dict(entry.metadata_json or {}),
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "squad_members": [
                {
                    "id": item.id,
                    "entry_id": item.entry_id,
                    "user_id": item.user_id,
                    "player_name": item.player_name,
                    "shirt_number": item.shirt_number,
                    "role_label": item.role_label,
                    "status": item.status,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in entry.squad_members
            ],
            "manager_history": [
                {
                    "id": item.id,
                    "entry_id": item.entry_id,
                    "user_id": item.user_id,
                    "action_type": item.action_type,
                    "note": item.note,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in entry.manager_history
            ],
            "rental_squad_members": [
                {
                    "id": item.id,
                    "entry_id": item.entry_id,
                    "rental_contract_id": item.rental_contract_id,
                    "player_id": item.player_id,
                    "player_name": item.player_name,
                    "overall_rating": item.overall_rating,
                    "shirt_number": item.shirt_number,
                    "source_type": item.source_type,
                    "status": item.status,
                    "metadata_json": dict(item.metadata_json or {}),
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in members
            ],
            "rental_contracts": [
                {
                    "id": item.id,
                    "player_id": item.player_id,
                    "user_id": item.user_id,
                    "tournament_id": item.tournament_id,
                    "entry_id": item.entry_id,
                    "start_date": item.start_date,
                    "end_date": item.end_date,
                    "loan_price_coin": item.loan_price_coin,
                    "is_free_player": item.is_free_player,
                    "free_player_tier": item.free_player_tier,
                    "status": item.status.value if isinstance(item.status, RentalContractStatus) else str(item.status),
                    "metadata_json": dict(item.metadata_json or {}),
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in contracts
            ],
            "free_players_remaining": max(0, int(settings["free_player_quota"]) - free_used),
            "minimum_squad_size": int(settings["minimum_squad_size"]),
            "maximum_squad_size": int(settings["maximum_squad_size"]),
        }

    def build_entry_detail_payload(self, entry_id: str) -> dict[str, Any]:
        entry = self._require_entry(entry_id)
        self._refresh_entry_squad_size(entry)
        return self._entry_detail_payload(entry)

    def _competition_payload(self, competition: NationalTeamCompetition) -> dict[str, Any]:
        return {
            "id": competition.id,
            "key": competition.key,
            "title": competition.title,
            "season_label": competition.season_label,
            "region_type": competition.region_type,
            "age_band": competition.age_band,
            "format_type": competition.format_type,
            "status": competition.status,
            "notes": competition.notes,
            "active": competition.active,
            "linked_competition_id": competition.linked_competition_id,
            "entry_opens_at": competition.entry_opens_at,
            "entry_closes_at": competition.entry_closes_at,
            "kickoff_at": competition.kickoff_at,
            "completed_at": competition.completed_at,
            "metadata_json": dict(competition.metadata_json or {}),
            "created_at": competition.created_at,
            "updated_at": competition.updated_at,
        }

    def _theme_payload(self, theme: TournamentTheme | None) -> dict[str, Any] | None:
        if theme is None:
            return None
        return {
            "id": theme.id,
            "competition_id": theme.competition_id,
            "video_asset_url": theme.video_asset_url,
            "audio_theme_url": theme.audio_theme_url,
            "visual_style": theme.visual_style,
            "metadata_json": dict(theme.metadata_json or {}),
            "created_at": theme.created_at,
            "updated_at": theme.updated_at,
        }

    def _ad_payload(self, ad: StadiumAd) -> dict[str, Any]:
        placement = ad.placement.value if isinstance(ad.placement, StadiumAdPlacement) else str(ad.placement)
        return {
            "id": ad.id,
            "competition_id": ad.competition_id,
            "asset_url": ad.asset_url,
            "placement": placement,
            "start_date": ad.start_date,
            "end_date": ad.end_date,
            "priority": ad.priority,
            "rotation_interval_seconds": ad.rotation_interval_seconds,
            "metadata_json": dict(ad.metadata_json or {}),
            "created_at": ad.created_at,
            "updated_at": ad.updated_at,
        }

    def _story_payload(self, event: StoryEvent) -> dict[str, Any]:
        event_type = event.type.value if isinstance(event.type, StoryEventType) else str(event.type)
        return {
            "id": event.id,
            "competition_id": event.competition_id,
            "match_id": event.match_id,
            "type": event_type,
            "entities": dict(event.entities or {}),
            "narrative_text": event.narrative_text,
            "metadata_json": dict(event.metadata_json or {}),
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }

    def _create_rental_contract(
        self,
        *,
        entry: NationalTeamEntry,
        actor: User,
        player_id: str,
        player_name: str,
        overall_rating: int,
        primary_position: str | None,
        source_bucket: str,
        gsi: int | None,
        loan_price_coin: Decimal,
        is_free_player: bool,
        free_player_tier: str | None,
        supply_mode: str = INFINITE_SUPPLY_MODE,
        extra_metadata: dict[str, Any] | None = None,
    ) -> RentalContract:
        start_date, end_date = self._contract_window(entry.competition)
        contract = RentalContract(
            player_id=player_id,
            user_id=actor.id,
            tournament_id=entry.competition_id,
            entry_id=entry.id,
            start_date=start_date,
            end_date=end_date,
            loan_price_coin=loan_price_coin,
            is_free_player=is_free_player,
            free_player_tier=free_player_tier,
            status=RentalContractStatus.ACTIVE,
            metadata_json={
                "entry_country_code": entry.country_code,
                "base_end_date": end_date.isoformat(),
                "rental_duration_hours": DEFAULT_RENTAL_DURATION_DAYS * 24,
                "player_name": player_name,
                "overall_rating": overall_rating,
                "primary_position": primary_position,
                "source_bucket": source_bucket,
                "gsi": gsi,
                "supply_mode": supply_mode,
                **dict(extra_metadata or {}),
            },
        )
        self.session.add(contract)
        self.session.flush()
        return contract

    def _create_rental_member(
        self,
        *,
        entry: NationalTeamEntry,
        contract: RentalContract,
        player_id: str,
        player_name: str,
        overall_rating: int,
        primary_position: str | None,
        source_bucket: str,
        gsi: int | None,
        shirt_number: int | None,
        source_type: str,
        assigned_slot: str | None = None,
        supply_mode: str = INFINITE_SUPPLY_MODE,
        extra_metadata: dict[str, Any] | None = None,
    ) -> NationalTeamRentalSquadMember:
        member = NationalTeamRentalSquadMember(
            entry_id=entry.id,
            rental_contract_id=contract.id,
            player_id=player_id,
            player_name=player_name,
            overall_rating=overall_rating,
            shirt_number=shirt_number if shirt_number is not None else self._next_shirt_number(entry.id),
            source_type=source_type,
            status="selected",
            metadata_json={
                "competition_id": entry.competition_id,
                "primary_position": primary_position,
                "source_bucket": source_bucket,
                "gsi": gsi,
                "assigned_slot": assigned_slot,
                "supply_mode": supply_mode,
                **dict(extra_metadata or {}),
            },
        )
        self.session.add(member)
        self.session.flush()
        return member

    def _flag_rental_abuse(
        self,
        *,
        actor: User,
        competition: NationalTeamCompetition,
        item: dict[str, Any],
        loan_price: Decimal,
    ) -> None:
        integrity = IntegrityEngineService(self.session)
        recent_rentals = int(
            self.session.scalar(
                select(func.count())
                .select_from(RentalContract)
                .where(
                    RentalContract.user_id == actor.id,
                    RentalContract.created_at >= (utcnow() - timedelta(minutes=15)),
                )
            )
            or 0
        )
        if recent_rentals >= 5:
            integrity.register_incident_once(
                user_id=actor.id,
                incident_type="rental_velocity_spike",
                subject=f"velocity:{actor.id}:{competition.id}",
                severity="high",
                title="Rental velocity spike detected",
                description="User rented an abnormal number of players in a short window.",
                score_delta=Decimal("-8.00"),
                metadata_json={
                    "competition_id": competition.id,
                    "recent_rentals": recent_rentals,
                },
            )

        demand_multiplier = Decimal(str(item.get("demand_multiplier") or "1.0000"))
        if str(item.get("source_bucket") or "") == SOURCE_BUCKET_PRESEEDED and demand_multiplier >= Decimal("1.3000"):
            integrity.register_incident_once(
                user_id=actor.id,
                incident_type="preseeded_rental_pressure",
                subject=f"player:{item['player_id']}",
                severity="medium",
                title="Preseeded rental pressure detected",
                description="Repeated demand on an infinite-supply player crossed the rental abuse threshold.",
                score_delta=Decimal("-4.00"),
                metadata_json={
                    "competition_id": competition.id,
                    "player_id": item["player_id"],
                    "loan_price_coin": str(loan_price),
                    "demand_multiplier": str(demand_multiplier),
                },
            )

    def claim_free_players(self, *, entry_id: str, actor: User) -> dict[str, Any]:
        entry = self._require_managed_entry(entry_id, actor)
        competition = entry.competition
        assert competition is not None
        self._validate_entry_window(competition)
        settings = self._competition_settings(competition)
        current_members = self._entry_rental_members(entry.id)
        current_player_ids = {item.player_id for item in current_members}
        free_counts = self._entry_free_player_counts(entry.id)
        remaining_distribution = {
            tier: max(0, int(required) - int(free_counts.get(tier, 0)))
            for tier, required in dict(settings["free_player_distribution"]).items()
        }
        total_remaining = sum(remaining_distribution.values())
        if total_remaining <= 0:
            raise NationalTeamTournamentError(
                "Free player quota has already been claimed.", reason="free_players_already_claimed"
            )
        if len(current_members) + len(entry.squad_members) + total_remaining > int(settings["maximum_squad_size"]):
            raise NationalTeamTournamentError(
                "Claiming free players would exceed the squad limit.", reason="squad_limit_reached"
            )

        starter_slots = STARTER_PACK_SLOTS + tuple(
            "MIDFIELDER" for _ in range(max(0, total_remaining - len(STARTER_PACK_SLOTS)))
        )
        pool = [
            self._priced_pool_item(item)
            for item in self._national_pool(
                filters=self._normalize_pool_filters(country_code=entry.country_code),
                competition=competition,
                limit=1000,
            )
        ]
        selection = self._pick_slot_players(
            pool=pool,
            slots=starter_slots[:total_remaining],
            excluded_player_ids=current_player_ids,
            budget_coin=None,
        )
        if selection["unfilled_slots"]:
            raise NationalTeamTournamentError(
                "Not enough players are available to satisfy the free squad distribution.",
                reason="free_distribution_unavailable",
            )
        selected = list(selection["selected"])

        for item in selected:
            market_flags = self._pool_item_market_flags(item)
            contract = self._create_rental_contract(
                entry=entry,
                actor=actor,
                player_id=item["player_id"],
                player_name=item["player_name"],
                overall_rating=int(item["overall_rating"]),
                primary_position=item["primary_position"],
                source_bucket=item["source_bucket"],
                gsi=int(item["gsi"]),
                loan_price_coin=Decimal("0.0000"),
                is_free_player=True,
                free_player_tier=item["tier_label"],
                supply_mode=str(item.get("supply_mode") or INFINITE_SUPPLY_MODE),
                extra_metadata=market_flags,
            )
            self._create_rental_member(
                entry=entry,
                contract=contract,
                player_id=item["player_id"],
                player_name=item["player_name"],
                overall_rating=int(item["overall_rating"]),
                primary_position=item["primary_position"],
                source_bucket=item["source_bucket"],
                gsi=int(item["gsi"]),
                shirt_number=None,
                source_type="free",
                assigned_slot=item.get("assigned_slot"),
                supply_mode=str(item.get("supply_mode") or INFINITE_SUPPLY_MODE),
                extra_metadata=market_flags,
            )

        self._refresh_entry_squad_size(entry)
        StoryFeedService(self.session).publish(
            story_type="national_team_free_squad",
            title=f"{entry.country_name} claimed its free tournament core",
            body=f"{entry.country_name} unlocked {len(selected)} free rental players for {competition.title}.",
            subject_type="national_team_entry",
            subject_id=entry.id,
            country_code=entry.country_code,
            metadata_json={"free_player_count": len(selected), "competition_id": competition.id},
            published_by_user_id=actor.id,
        )
        return self._entry_detail_payload(entry)

    def rent_player(
        self,
        *,
        entry_id: str,
        actor: User,
        player_id: str,
        shirt_number: int | None = None,
    ) -> dict[str, Any]:
        entry = self._require_managed_entry(entry_id, actor)
        competition = entry.competition
        assert competition is not None
        self._validate_entry_window(competition)
        settings = self._competition_settings(competition)
        current_members = self._entry_rental_members(entry.id)
        if len(current_members) + len(entry.squad_members) >= int(settings["maximum_squad_size"]):
            raise NationalTeamTournamentError(
                "Tournament squad has reached the maximum size.", reason="squad_limit_reached"
            )
        if any(member.player_id == player_id for member in current_members):
            raise NationalTeamTournamentError(
                "This player is already part of the rental squad.", reason="rental_contract_exists"
            )

        player_catalog = {
            item["player_id"]: self._priced_pool_item(item)
            for item in self._national_pool(
                filters=self._normalize_pool_filters(country_code=entry.country_code),
                competition=competition,
                limit=1000,
            )
        }
        item = player_catalog.get(player_id)
        if item is None:
            player_exists = self.session.get(Player, player_id) is not None
            seed_exists = self.session.get(NationalRegenSeed, player_id) is not None
            raise NationalTeamTournamentError(
                "Rental player is outside the national pool.",
                reason="player_not_eligible" if player_exists or seed_exists else "player_not_found",
            )

        loan_price = self._normalize_amount(item["loan_price_coin"])
        user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        if self.wallet_service.get_balance(self.session, user_account) < loan_price:
            raise InsufficientBalanceError("Available market balance is lower than the rental price.")
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=user_account, amount=-loan_price, source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND
                ),
                LedgerPosting(
                    account=platform_account, amount=loan_price, source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            reference=f"national-rental:{competition.id}:{entry.id}:{player_id}",
            description=f"National team rental for {item['player_name']} in {competition.title}",
            external_reference=f"national-rental:{competition.id}:{entry.id}:{player_id}",
            actor=actor,
            idempotency_key=f"national-rental:{competition.id}:{entry.id}:{player_id}:{actor.id}",
        )
        contract = self._create_rental_contract(
            entry=entry,
            actor=actor,
            player_id=item["player_id"],
            player_name=item["player_name"],
            overall_rating=int(item["overall_rating"]),
            primary_position=item["primary_position"],
            source_bucket=item["source_bucket"],
            gsi=int(item["gsi"]),
            loan_price_coin=loan_price,
            is_free_player=False,
            free_player_tier=None,
            supply_mode=str(item.get("supply_mode") or INFINITE_SUPPLY_MODE),
            extra_metadata=self._pool_item_market_flags(item),
        )
        contract.metadata_json = {
            **dict(contract.metadata_json or {}),
            "base_value_coin": str(item["base_value_coin"]),
            "demand_multiplier": str(item.get("demand_multiplier", Decimal("1.0000"))),
            "ledger_transaction_id": entries[0].transaction_id if entries else None,
        }
        self._create_rental_member(
            entry=entry,
            contract=contract,
            player_id=item["player_id"],
            player_name=item["player_name"],
            overall_rating=int(item["overall_rating"]),
            primary_position=item["primary_position"],
            source_bucket=item["source_bucket"],
            gsi=int(item["gsi"]),
            shirt_number=shirt_number,
            source_type="rental",
            assigned_slot=item["primary_position"],
            supply_mode=str(item.get("supply_mode") or INFINITE_SUPPLY_MODE),
            extra_metadata=self._pool_item_market_flags(item),
        )
        self._flag_rental_abuse(actor=actor, competition=competition, item=item, loan_price=loan_price)
        self._refresh_entry_squad_size(entry)
        return self._entry_detail_payload(entry)

    def get_theme(self, *, competition_id: str) -> dict[str, Any] | None:
        self._require_competition(competition_id)
        theme = self.session.scalar(select(TournamentTheme).where(TournamentTheme.competition_id == competition_id))
        return self._theme_payload(theme)

    def _competition_manager_ids(self, competition_id: str) -> set[str]:
        manager_ids = {
            manager_id
            for manager_id in self.session.scalars(
                select(NationalTeamEntry.manager_user_id).where(
                    NationalTeamEntry.competition_id == competition_id,
                    NationalTeamEntry.manager_user_id.is_not(None),
                )
            ).all()
            if manager_id
        }
        owner_ids = {
            owner_id
            for owner_id in self.session.scalars(
                select(NationalTeamEntry.entry_owner_user_id).where(
                    NationalTeamEntry.competition_id == competition_id,
                    NationalTeamEntry.entry_owner_user_id.is_not(None),
                )
            ).all()
            if owner_id
        }
        return manager_ids | owner_ids

    def _announce_theme_live_if_needed(self, competition: NationalTeamCompetition, theme: TournamentTheme) -> None:
        metadata = dict(theme.metadata_json or {})
        now = utcnow()
        if competition.kickoff_at is not None and competition.kickoff_at > now:
            return
        if metadata.get("live_announced_at"):
            return
        for user_id in sorted(self._competition_manager_ids(competition.id)):
            self.session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic="national_team",
                    template_key="TOURNAMENT_THEME_LIVE",
                    resource_type="national_team_competition",
                    resource_id=competition.id,
                    competition_id=competition.id,
                    message=f"{competition.title} theme package is now live.",
                    metadata_json={"theme_id": theme.id, "visual_style": theme.visual_style},
                )
            )
        theme.metadata_json = {**metadata, "live_announced_at": now.isoformat()}
        self.session.flush()

    def upsert_theme(self, *, competition_id: str, payload, actor: User) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        theme = self.session.scalar(select(TournamentTheme).where(TournamentTheme.competition_id == competition_id))
        if theme is None:
            theme = TournamentTheme(competition_id=competition_id)
            self.session.add(theme)
        theme.video_asset_url = payload.video_asset_url
        theme.audio_theme_url = payload.audio_theme_url
        theme.visual_style = payload.visual_style.strip()
        theme.metadata_json = {
            **dict(theme.metadata_json or {}),
            **dict(payload.metadata_json or {}),
            "updated_by_user_id": actor.id,
        }
        self.session.flush()
        self._announce_theme_live_if_needed(competition, theme)
        return self._theme_payload(theme) or {}

    def _active_ads_query(self, competition_id: str, *, now) -> list[StadiumAd]:
        return list(
            self.session.scalars(
                select(StadiumAd)
                .where(
                    or_(StadiumAd.competition_id == competition_id, StadiumAd.competition_id.is_(None)),
                    StadiumAd.start_date <= now,
                    StadiumAd.end_date >= now,
                )
                .order_by(StadiumAd.placement.asc(), StadiumAd.priority.desc(), StadiumAd.created_at.asc())
            ).all()
        )

    def _rotated_ads(self, competition_id: str, *, now) -> list[StadiumAd]:
        selected: list[StadiumAd] = []
        active_ads = self._active_ads_query(competition_id, now=now)
        grouped: dict[str, list[StadiumAd]] = {}
        for ad in active_ads:
            placement = ad.placement.value if isinstance(ad.placement, StadiumAdPlacement) else str(ad.placement)
            grouped.setdefault(placement, []).append(ad)
        for ads in grouped.values():
            rotation_interval = max(5, min(int(ads[0].rotation_interval_seconds), 600))
            slot = int(now.timestamp()) // rotation_interval
            selected.append(ads[slot % len(ads)])
        return selected

    def list_active_ads(self, *, competition_id: str) -> list[dict[str, Any]]:
        self._require_competition(competition_id)
        return [self._ad_payload(ad) for ad in self._rotated_ads(competition_id, now=utcnow())]

    def list_ads(self, *, competition_id: str) -> list[dict[str, Any]]:
        self._require_competition(competition_id)
        ads = list(
            self.session.scalars(
                select(StadiumAd)
                .where(or_(StadiumAd.competition_id == competition_id, StadiumAd.competition_id.is_(None)))
                .order_by(StadiumAd.priority.desc(), StadiumAd.created_at.desc())
            ).all()
        )
        return [self._ad_payload(ad) for ad in ads]

    def upsert_ad(
        self, *, competition_id: str | None, payload, actor: User, ad_id: str | None = None
    ) -> dict[str, Any]:
        if competition_id is not None:
            self._require_competition(competition_id)
        if payload.end_date <= payload.start_date:
            raise NationalTeamTournamentError("Ad end date must be after the start date.", reason="ad_window_invalid")
        ad = self.session.get(StadiumAd, ad_id) if ad_id is not None else None
        if ad_id is not None and ad is None:
            raise NationalTeamTournamentError("Stadium ad was not found.", reason="ad_not_found")
        if ad is None:
            ad = StadiumAd(competition_id=competition_id)
            self.session.add(ad)
        placement_value = payload.placement.strip().lower()
        if placement_value not in {item.value for item in StadiumAdPlacement}:
            raise NationalTeamTournamentError("Unsupported stadium ad placement.", reason="ad_placement_invalid")
        ad.competition_id = competition_id
        ad.asset_url = payload.asset_url.strip()
        ad.placement = StadiumAdPlacement(placement_value)
        ad.start_date = payload.start_date
        ad.end_date = payload.end_date
        ad.priority = payload.priority
        ad.rotation_interval_seconds = payload.rotation_interval_seconds
        ad.metadata_json = {
            **dict(ad.metadata_json or {}),
            **dict(payload.metadata_json or {}),
            "updated_by_user_id": actor.id,
        }
        self.session.flush()
        return self._ad_payload(ad)

    def rotate_ads(self, *, competition_id: str | None = None) -> dict[str, Any]:
        now = utcnow()
        competition_ids = (
            [competition_id]
            if competition_id is not None
            else list(
                self.session.scalars(
                    select(NationalTeamCompetition.id).where(NationalTeamCompetition.active.is_(True))
                ).all()
            )
        )
        rotated: list[dict[str, Any]] = []
        for current_competition_id in competition_ids:
            if current_competition_id is None:
                continue
            for ad in self._rotated_ads(current_competition_id, now=now):
                ad.metadata_json = {
                    **dict(ad.metadata_json or {}),
                    "last_rotated_at": now.isoformat(),
                    "rotation_slot": int(now.timestamp()) // max(5, min(int(ad.rotation_interval_seconds), 600)),
                }
                rotated.append(
                    {
                        "competition_id": current_competition_id,
                        "ad_id": ad.id,
                        "placement": self._ad_payload(ad)["placement"],
                    }
                )
        self.session.flush()
        return {"rotated_ads": rotated, "rotated_count": len(rotated)}

    def _club_name_map(self, club_ids: set[str]) -> dict[str, str]:
        if not club_ids:
            return {}
        stmt = select(ClubProfile.id, ClubProfile.club_name).where(ClubProfile.id.in_(club_ids))
        return {club_id: club_name for club_id, club_name in self.session.execute(stmt).all()}

    def _metrics_map(self, club_ids: set[str]) -> dict[str, ClubIdentityMetrics]:
        if not club_ids:
            return {}
        return {
            item.club_id: item
            for item in self.session.scalars(
                select(ClubIdentityMetrics).where(ClubIdentityMetrics.club_id.in_(club_ids))
            ).all()
        }

    def _rivalry_for_pair(self, club_a_id: str, club_b_id: str) -> RivalryProfile | None:
        return self.session.scalar(
            select(RivalryProfile).where(
                or_(
                    (RivalryProfile.club_a_id == club_a_id) & (RivalryProfile.club_b_id == club_b_id),
                    (RivalryProfile.club_a_id == club_b_id) & (RivalryProfile.club_b_id == club_a_id),
                )
            )
        )

    def _story_text(
        self,
        *,
        event_type: StoryEventType,
        winner_name: str,
        loser_name: str,
        scoreline: str,
        stage_label: str,
        star_name: str | None = None,
        rivalry_label: str | None = None,
        streak_length: int | None = None,
    ) -> str:
        if event_type is StoryEventType.GIANT_KILLING:
            if rivalry_label:
                return f"{winner_name} flipped the {rivalry_label.lower()} script, dropping {loser_name} {scoreline} on the {stage_label} stage."
            return f"{winner_name} stunned {loser_name} {scoreline}, turning the {stage_label} into a genuine giant-killing moment."
        if event_type is StoryEventType.REVENGE_MATCH:
            return f"{winner_name} got payback on {loser_name} with a {scoreline} revenge result after the last defeat still lingered."
        if event_type is StoryEventType.STAR_BREAKOUT and star_name:
            return f"{star_name} owned the spotlight as {winner_name} beat {loser_name} {scoreline}, announcing a breakout night in the {stage_label}."
        streak_note = f" for a {streak_length}-match surge" if streak_length else ""
        return f"{winner_name} kept its underdog charge alive{streak_note}, edging past {loser_name} {scoreline} in the {stage_label}."

    def generate_story_events(self, *, competition_id: str | None = None, actor: User | None = None) -> dict[str, Any]:
        competitions = (
            [self._require_competition(competition_id)]
            if competition_id
            else list(
                self.session.scalars(
                    select(NationalTeamCompetition).where(NationalTeamCompetition.linked_competition_id.is_not(None))
                ).all()
            )
        )
        created = 0
        created_ids: list[str] = []
        for competition in competitions:
            if competition.linked_competition_id is None:
                continue
            matches = list(
                self.session.scalars(
                    select(CompetitionMatch)
                    .where(
                        CompetitionMatch.competition_id == competition.linked_competition_id,
                        CompetitionMatch.completed_at.is_not(None),
                    )
                    .order_by(CompetitionMatch.completed_at.desc())
                    .limit(50)
                ).all()
            )
            club_ids = {
                club_id
                for match in matches
                for club_id in [match.home_club_id, match.away_club_id, match.winner_club_id]
                if club_id
            }
            club_names = self._club_name_map(club_ids)
            metrics_map = self._metrics_map(club_ids)
            manager_ids = self._competition_manager_ids(competition.id)
            for match in matches:
                existing_types = {
                    item
                    for item in self.session.scalars(
                        select(StoryEvent.type).where(
                            StoryEvent.competition_id == competition.id,
                            StoryEvent.match_id == match.id,
                        )
                    ).all()
                }
                winner_id = match.winner_club_id
                if winner_id is None or winner_id not in {match.home_club_id, match.away_club_id}:
                    continue
                loser_id = match.away_club_id if winner_id == match.home_club_id else match.home_club_id
                winner_name = club_names.get(winner_id, winner_id)
                loser_name = club_names.get(loser_id, loser_id)
                scoreline = f"{match.home_score}-{match.away_score}"
                stage_label = match.stage.replace("_", " ")
                rivalry = self._rivalry_for_pair(match.home_club_id, match.away_club_id)
                prior_meeting = self.session.scalar(
                    select(CompetitionMatch)
                    .where(
                        CompetitionMatch.competition_id == competition.linked_competition_id,
                        CompetitionMatch.id != match.id,
                        CompetitionMatch.completed_at.is_not(None),
                        or_(
                            (CompetitionMatch.home_club_id == match.home_club_id)
                            & (CompetitionMatch.away_club_id == match.away_club_id),
                            (CompetitionMatch.home_club_id == match.away_club_id)
                            & (CompetitionMatch.away_club_id == match.home_club_id),
                        ),
                    )
                    .order_by(CompetitionMatch.completed_at.desc())
                )
                player_events = list(
                    self.session.scalars(
                        select(CompetitionMatchEvent)
                        .where(CompetitionMatchEvent.match_id == match.id)
                        .order_by(CompetitionMatchEvent.created_at.asc())
                    ).all()
                )
                player_totals: dict[str, dict[str, Any]] = {}
                for event in player_events:
                    if event.player_id is None:
                        continue
                    payload = player_totals.setdefault(
                        event.player_id,
                        {
                            "player_id": event.player_id,
                            "player_name": (event.metadata_json or {}).get("player_name") or event.player_id,
                            "goals": 0,
                            "assists": 0,
                            "club_id": event.club_id,
                        },
                    )
                    normalized_type = event.event_type.strip().lower()
                    if normalized_type == "goal":
                        payload["goals"] += 1
                    if normalized_type == "assist":
                        payload["assists"] += 1
                breakout_candidate = next(
                    (
                        payload
                        for payload in sorted(
                            player_totals.values(),
                            key=lambda item: (
                                -(item["goals"] + item["assists"]),
                                -item["goals"],
                                str(item["player_name"]).lower(),
                            ),
                        )
                        if (payload["goals"] + payload["assists"]) >= 2
                    ),
                    None,
                )
                winner_metrics = metrics_map.get(winner_id)
                loser_metrics = metrics_map.get(loser_id)
                winner_reputation = int(winner_metrics.reputation_score) if winner_metrics is not None else 50
                loser_reputation = int(loser_metrics.reputation_score) if loser_metrics is not None else 50
                winner_fans = int(winner_metrics.fan_count) if winner_metrics is not None else 0
                loser_fans = int(loser_metrics.fan_count) if loser_metrics is not None else 0
                winner_streak = int(
                    self.session.scalar(
                        select(func.count(CompetitionMatch.id)).where(
                            CompetitionMatch.competition_id == competition.linked_competition_id,
                            CompetitionMatch.winner_club_id == winner_id,
                            CompetitionMatch.completed_at.is_not(None),
                        )
                    )
                    or 0
                )

                candidates: list[tuple[StoryEventType, dict[str, Any]]] = []
                if StoryEventType.GIANT_KILLING not in existing_types and (
                    (loser_reputation - winner_reputation) >= 15
                    or (loser_fans >= max(winner_fans * 2, 1) and loser_fans > 0)
                    or (rivalry is not None and rivalry.giant_killer_flag)
                ):
                    candidates.append(
                        (
                            StoryEventType.GIANT_KILLING,
                            {
                                "winner_id": winner_id,
                                "winner_name": winner_name,
                                "loser_id": loser_id,
                                "loser_name": loser_name,
                                "scoreline": scoreline,
                                "stage_label": stage_label,
                                "rivalry_label": rivalry.label if rivalry is not None else None,
                            },
                        )
                    )
                if (
                    StoryEventType.REVENGE_MATCH not in existing_types
                    and prior_meeting is not None
                    and prior_meeting.winner_club_id is not None
                    and prior_meeting.winner_club_id != winner_id
                ):
                    candidates.append(
                        (
                            StoryEventType.REVENGE_MATCH,
                            {
                                "winner_id": winner_id,
                                "winner_name": winner_name,
                                "loser_id": loser_id,
                                "loser_name": loser_name,
                                "scoreline": scoreline,
                                "stage_label": stage_label,
                                "prior_match_id": prior_meeting.id,
                            },
                        )
                    )
                if StoryEventType.STAR_BREAKOUT not in existing_types and breakout_candidate is not None:
                    candidates.append(
                        (
                            StoryEventType.STAR_BREAKOUT,
                            {
                                "winner_id": winner_id,
                                "winner_name": winner_name,
                                "loser_id": loser_id,
                                "loser_name": loser_name,
                                "scoreline": scoreline,
                                "stage_label": stage_label,
                                "player_id": breakout_candidate["player_id"],
                                "player_name": breakout_candidate["player_name"],
                                "goals": breakout_candidate["goals"],
                                "assists": breakout_candidate["assists"],
                            },
                        )
                    )
                if (
                    StoryEventType.UNDERDOG_RUN not in existing_types
                    and winner_streak >= 3
                    and winner_reputation <= loser_reputation
                ):
                    candidates.append(
                        (
                            StoryEventType.UNDERDOG_RUN,
                            {
                                "winner_id": winner_id,
                                "winner_name": winner_name,
                                "loser_id": loser_id,
                                "loser_name": loser_name,
                                "scoreline": scoreline,
                                "stage_label": stage_label,
                                "winner_streak": winner_streak,
                            },
                        )
                    )

                for event_type, entities in candidates:
                    story = StoryEvent(
                        competition_id=competition.id,
                        match_id=match.id,
                        type=event_type,
                        entities=entities,
                        narrative_text=self._story_text(
                            event_type=event_type,
                            winner_name=entities["winner_name"],
                            loser_name=entities["loser_name"],
                            scoreline=entities["scoreline"],
                            stage_label=entities["stage_label"],
                            star_name=entities.get("player_name"),
                            rivalry_label=entities.get("rivalry_label"),
                            streak_length=entities.get("winner_streak"),
                        ),
                        metadata_json={
                            "linked_competition_id": competition.linked_competition_id,
                            "generated_at": utcnow().isoformat(),
                        },
                    )
                    self.session.add(story)
                    self.session.flush()
                    created += 1
                    created_ids.append(story.id)
                    StoryFeedService(self.session).publish(
                        story_type="tournament_story",
                        title=f"{competition.title}: {event_type.value.replace('_', ' ')}",
                        body=story.narrative_text,
                        subject_type="national_team_competition",
                        subject_id=competition.id,
                        metadata_json={"story_event_id": story.id, "match_id": match.id, "type": event_type.value},
                        published_by_user_id=actor.id if actor is not None else None,
                    )
                    for user_id in sorted(manager_ids):
                        self.session.add(
                            NotificationRecord(
                                user_id=user_id,
                                topic="national_team",
                                template_key="STORY_EVENT_TRIGGERED",
                                resource_type="tournament_story_event",
                                resource_id=story.id,
                                competition_id=competition.id,
                                message=story.narrative_text[:255],
                                metadata_json={"match_id": match.id, "type": event_type.value},
                            )
                        )
        self.session.flush()
        return {"created_count": created, "story_event_ids": created_ids}

    def list_story_events(
        self, *, competition_id: str, match_id: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        self._require_competition(competition_id)
        stmt = select(StoryEvent).where(StoryEvent.competition_id == competition_id)
        if match_id is not None:
            stmt = stmt.where(StoryEvent.match_id == match_id)
        stmt = stmt.order_by(StoryEvent.created_at.desc()).limit(limit)
        return [self._story_payload(item) for item in self.session.scalars(stmt).all()]

    def cleanup_expired_rentals(self, *, competition_id: str | None = None) -> dict[str, Any]:
        now = utcnow()
        stmt = select(RentalContract).where(RentalContract.status == RentalContractStatus.ACTIVE)
        if competition_id is not None:
            stmt = stmt.where(RentalContract.tournament_id == competition_id)
        contracts = list(self.session.scalars(stmt).all())
        expiring_notifications = 0
        released = 0
        affected_entry_ids: set[str] = set()
        for contract in contracts:
            competition = self.session.get(NationalTeamCompetition, contract.tournament_id)
            should_release = contract.end_date <= now or (
                competition is not None and competition.completed_at is not None
            )
            if not should_release and contract.end_date <= (now + timedelta(hours=RENTAL_EXPIRING_WARNING_HOURS)):
                metadata = dict(contract.metadata_json or {})
                if not metadata.get("expiring_notified_at"):
                    self.session.add(
                        NotificationRecord(
                            user_id=contract.user_id,
                            topic="national_team",
                            template_key="RENTAL_EXPIRING",
                            resource_type="national_team_rental_contract",
                            resource_id=contract.id,
                            competition_id=contract.tournament_id,
                            message=f"Rental access for {(metadata.get('player_name') or contract.player_id)} is expiring soon.",
                            metadata_json={"entry_id": contract.entry_id, "end_date": contract.end_date.isoformat()},
                        )
                    )
                    contract.metadata_json = {**metadata, "expiring_notified_at": now.isoformat()}
                    expiring_notifications += 1
                continue
            if not should_release:
                continue
            contract.status = (
                RentalContractStatus.EXPIRED if contract.end_date <= now else RentalContractStatus.RELEASED
            )
            if contract.entry_id:
                affected_entry_ids.add(contract.entry_id)
                member = self.session.scalar(
                    select(NationalTeamRentalSquadMember).where(
                        NationalTeamRentalSquadMember.rental_contract_id == contract.id
                    )
                )
                if member is not None:
                    self.session.delete(member)
            released += 1
        for entry_id in affected_entry_ids:
            entry = self._require_entry(entry_id)
            self._refresh_entry_squad_size(entry)
        self.session.flush()
        return {
            "released_contracts": released,
            "expiring_notifications": expiring_notifications,
            "affected_entries": sorted(affected_entry_ids),
        }

    def build_competition_presentation_payload(
        self, *, competition_id: str, limit_story_events: int = 8
    ) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        theme = self.session.scalar(select(TournamentTheme).where(TournamentTheme.competition_id == competition_id))
        if theme is not None:
            self._announce_theme_live_if_needed(competition, theme)
        return {
            "competition": self._competition_payload(competition),
            "active_theme": self._theme_payload(theme),
            "active_ads": [self._ad_payload(ad) for ad in self._rotated_ads(competition_id, now=utcnow())],
            "story_events": self.list_story_events(competition_id=competition_id, limit=limit_story_events),
        }

    def build_rental_status_payload(self, *, entry_id: str) -> dict[str, Any]:
        entry = self._require_entry(entry_id)
        self._refresh_entry_squad_size(entry)
        competition = entry.competition
        assert competition is not None
        presentation = self.build_competition_presentation_payload(competition_id=competition.id, limit_story_events=6)
        return {
            "entry": self._entry_detail_payload(entry),
            "competition": presentation["competition"],
            "active_theme": presentation["active_theme"],
            "active_ads": presentation["active_ads"],
            "story_events": presentation["story_events"],
        }

    def send_tournament_gift(self, *, competition_id: str, actor: User, payload) -> dict[str, Any]:
        self._require_competition(competition_id)
        try:
            transaction = self.gift_service.send_gift(
                sender=actor,
                recipient_user_id=payload.recipient_user_id,
                gift_key=payload.gift_key,
                quantity=payload.quantity,
                note=payload.note,
                source_scope="gtex_competition",
            )
        except GiftEngineError as exc:
            raise NationalTeamTournamentError(str(exc), reason="gift_failed") from exc
        return {
            "transaction_id": transaction.id,
            "recipient_user_id": payload.recipient_user_id,
            "gift_key": payload.gift_key,
            "quantity": payload.quantity,
            "source_scope": "gtex_competition",
        }

    def seed_default_competitions(self, *, actor: User) -> list[dict[str, Any]]:
        current_year = str(utcnow().year)
        seeded: list[dict[str, Any]] = []
        for definition in seeded_competition_definitions(season_label=current_year):
            existing = self.session.scalar(
                select(NationalTeamCompetition).where(NationalTeamCompetition.key == definition["key"])
            )
            if existing is not None:
                seeded.append(self._competition_payload(existing))
                continue
            competition = NationalTeamCompetition(
                key=definition["key"],
                title=definition["title"],
                season_label=definition["season_label"],
                region_type=definition["region_type"],
                age_band=definition["age_band"],
                format_type=definition["format_type"],
                status=definition["status"],
                metadata_json={
                    "entry_mode": "rental_only",
                    "minimum_squad_size": DEFAULT_MINIMUM_SQUAD_SIZE,
                    "maximum_squad_size": DEFAULT_MAXIMUM_SQUAD_SIZE,
                    "free_player_quota": DEFAULT_FREE_PLAYER_QUOTA,
                    "free_player_distribution": dict(DEFAULT_FREE_PLAYER_DISTRIBUTION),
                    **dict(definition["metadata_json"]),
                },
                created_by_user_id=actor.id,
            )
            self.session.add(competition)
            self.session.flush()
            seeded.append(self._competition_payload(competition))
        return seeded
