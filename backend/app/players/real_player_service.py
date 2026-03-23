from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Integer, String, cast, func, literal, or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.players.real_player_read_models import (
    RealPlayerUniverseDetail,
    RealPlayerUniverseListItem,
    RealPlayerUniverseListResult,
)

REAL_PLAYER_DISCOVERY_SORTS = frozenset({"age", "current_value", "last_refreshed", "market_value", "name"})
REAL_PLAYER_IDENTITY_RAIL = "real_player_universe"


class RealPlayerUniverseError(Exception):
    pass


class RealPlayerUniverseNotFoundError(RealPlayerUniverseError):
    pass


class RealPlayerUniverseValidationError(RealPlayerUniverseError):
    pass


@dataclass(slots=True)
class RealPlayerUniverseQueryService:
    session: Session
    today: date | None = None

    def __post_init__(self) -> None:
        if self.today is None:
            self.today = date.today()

    def list_players(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        position: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        search: str | None = None,
        sort: str = "current_value",
    ) -> RealPlayerUniverseListResult:
        self._validate_query(
            limit=limit,
            offset=offset,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            sort=sort,
        )
        base_statement = self._apply_filters(
            position=position,
            nationality=nationality,
            club=club,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            search=search,
        )
        total = int(self.session.scalar(select(func.count()).select_from(base_statement.subquery())) or 0)
        statement = base_statement.order_by(*self._order_by(sort=sort)).offset(offset).limit(limit)
        rows = self.session.execute(statement).all()
        items = tuple(self._build_list_item(*row) for row in rows)
        return RealPlayerUniverseListResult(items=items, limit=limit, offset=offset, total=total)

    def get_player_detail(self, player_id: str) -> RealPlayerUniverseDetail:
        row = self.session.execute(self._base_statement().where(Player.id == player_id)).first()
        if row is None:
            raise RealPlayerUniverseNotFoundError(f"real player {player_id} was not found")
        return self._build_detail(*row)

    def _base_statement(self):
        selected_profiles = self._selected_profiles_subquery()
        return (
            select(Player, RealPlayerProfile, RealPlayerSourceLink, Country, PlayerSummaryReadModel)
            .join(selected_profiles, selected_profiles.c.gtex_player_id == Player.id)
            .join(RealPlayerProfile, RealPlayerProfile.id == selected_profiles.c.profile_id)
            .join(RealPlayerSourceLink, RealPlayerSourceLink.id == RealPlayerProfile.source_link_id)
            .outerjoin(Country, Country.id == Player.country_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(Player.is_real_player.is_(True))
        )

    def _selected_profiles_subquery(self):
        ranked_profiles = (
            select(
                RealPlayerProfile.id.label("profile_id"),
                RealPlayerProfile.gtex_player_id.label("gtex_player_id"),
                func.row_number()
                .over(
                    partition_by=RealPlayerProfile.gtex_player_id,
                    order_by=(
                        RealPlayerProfile.source_last_refreshed_at.is_(None),
                        RealPlayerProfile.source_last_refreshed_at.desc(),
                        RealPlayerProfile.updated_at.desc(),
                        RealPlayerProfile.id.desc(),
                    ),
                )
                .label("profile_rank"),
            )
            .subquery()
        )
        return (
            select(ranked_profiles.c.profile_id, ranked_profiles.c.gtex_player_id)
            .where(ranked_profiles.c.profile_rank == 1)
            .subquery()
        )

    def _apply_filters(
        self,
        *,
        position: str | None,
        nationality: str | None,
        club: str | None,
        min_age: int | None,
        max_age: int | None,
        min_value: float | None,
        max_value: float | None,
        search: str | None,
    ):
        statement = self._base_statement()
        if position:
            term = f"%{position.strip()}%"
            statement = statement.where(
                or_(
                    self._position_expr().ilike(term),
                    cast(RealPlayerProfile.secondary_positions_json, String).ilike(term),
                )
            )
        if nationality:
            statement = statement.where(self._nationality_expr().ilike(f"%{nationality.strip()}%"))
        if club:
            statement = statement.where(self._club_expr().ilike(f"%{club.strip()}%"))
        if min_age is not None:
            statement = statement.where(self._age_expr() >= min_age)
        if max_age is not None:
            statement = statement.where(self._age_expr() <= max_age)
        if min_value is not None:
            statement = statement.where(self._current_value_expr() >= min_value)
        if max_value is not None:
            statement = statement.where(self._current_value_expr() <= max_value)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Player.full_name.ilike(term),
                    Player.canonical_display_name.ilike(term),
                    RealPlayerProfile.canonical_name.ilike(term),
                    cast(RealPlayerProfile.known_aliases_json, String).ilike(term),
                    self._club_expr().ilike(term),
                    self._league_expr().ilike(term),
                    self._nationality_expr().ilike(term),
                    self._position_expr().ilike(term),
                )
            )
        return statement

    def _order_by(self, *, sort: str):
        name_expr = func.lower(Player.full_name)
        if sort == "current_value":
            current_value_expr = self._current_value_expr()
            return (
                current_value_expr.is_(None),
                current_value_expr.desc(),
                name_expr.asc(),
                Player.id.asc(),
            )
        if sort == "market_value":
            market_value_expr = self._market_reference_value_expr()
            return (
                market_value_expr.is_(None),
                market_value_expr.desc(),
                name_expr.asc(),
                Player.id.asc(),
            )
        if sort == "last_refreshed":
            refreshed_expr = self._last_refreshed_expr()
            return (
                refreshed_expr.is_(None),
                refreshed_expr.desc(),
                name_expr.asc(),
                Player.id.asc(),
            )
        if sort == "age":
            age_expr = self._age_expr()
            return (
                age_expr.is_(None),
                age_expr.asc(),
                name_expr.asc(),
                Player.id.asc(),
            )
        return (
            name_expr.asc(),
            Player.id.asc(),
        )

    def _build_list_item(
        self,
        player: Player,
        profile: RealPlayerProfile,
        source_link: RealPlayerSourceLink,
        country: Country | None,
        summary: PlayerSummaryReadModel | None,
    ) -> RealPlayerUniverseListItem:
        return RealPlayerUniverseListItem(
            player_id=player.id,
            player_name=player.full_name,
            identity_rail=REAL_PLAYER_IDENTITY_RAIL,
            canonical_display_name=player.canonical_display_name or profile.canonical_name or player.full_name,
            real_player_tier=player.real_player_tier,
            nationality=country.name if country is not None else profile.nationality,
            nationality_code=getattr(country, "alpha2_code", None),
            position=profile.primary_position or player.normalized_position or player.position,
            secondary_positions=tuple(profile.secondary_positions_json or ()),
            age=self._player_age(player.date_of_birth or profile.date_of_birth),
            current_club_name=profile.current_club_name or player.real_world_club_name,
            current_league_name=profile.current_league_name or player.real_world_league_name,
            competition_level=profile.competition_level,
            current_value_credits=summary.current_value_credits if summary is not None else None,
            previous_value_credits=summary.previous_value_credits if summary is not None else None,
            movement_pct=summary.movement_pct if summary is not None else None,
            market_interest_score=summary.market_interest_score if summary is not None else None,
            average_rating=summary.average_rating if summary is not None else None,
            current_market_reference_value=profile.current_market_reference_value or player.current_market_reference_value,
            market_reference_currency=profile.market_reference_currency or player.market_reference_currency,
            source_name=profile.source_name,
            source_last_refreshed_at=profile.source_last_refreshed_at or player.source_last_refreshed_at,
            is_verified_real_player=bool(source_link.is_verified_real_player),
            updated_at=profile.updated_at,
        )

    def _build_detail(
        self,
        player: Player,
        profile: RealPlayerProfile,
        source_link: RealPlayerSourceLink,
        country: Country | None,
        summary: PlayerSummaryReadModel | None,
    ) -> RealPlayerUniverseDetail:
        return RealPlayerUniverseDetail(
            player_id=player.id,
            player_name=player.full_name,
            identity_rail=REAL_PLAYER_IDENTITY_RAIL,
            canonical_display_name=player.canonical_display_name or profile.canonical_name or player.full_name,
            first_name=player.first_name,
            last_name=player.last_name,
            short_name=player.short_name,
            nationality=country.name if country is not None else profile.nationality,
            nationality_code=getattr(country, "alpha2_code", None),
            position=player.position or profile.primary_position,
            normalized_position=player.normalized_position,
            primary_position=profile.primary_position or player.normalized_position or player.position,
            secondary_positions=tuple(profile.secondary_positions_json or ()),
            age=self._player_age(player.date_of_birth or profile.date_of_birth),
            date_of_birth=player.date_of_birth or profile.date_of_birth,
            dominant_foot=profile.dominant_foot or player.preferred_foot,
            height_cm=profile.height_cm or player.height_cm,
            weight_kg=profile.weight_kg or player.weight_kg,
            current_club_name=profile.current_club_name or player.real_world_club_name,
            current_league_name=profile.current_league_name or player.real_world_league_name,
            competition_level=profile.competition_level,
            current_value_credits=summary.current_value_credits if summary is not None else None,
            previous_value_credits=summary.previous_value_credits if summary is not None else None,
            movement_pct=summary.movement_pct if summary is not None else None,
            market_interest_score=summary.market_interest_score if summary is not None else None,
            average_rating=summary.average_rating if summary is not None else None,
            current_market_reference_value=profile.current_market_reference_value or player.current_market_reference_value,
            market_reference_currency=profile.market_reference_currency or player.market_reference_currency,
            appearances=profile.appearances,
            minutes_played=profile.minutes_played,
            goals=profile.goals,
            assists=profile.assists,
            clean_sheets=profile.clean_sheets,
            injury_status=profile.injury_status,
            real_player_tier=player.real_player_tier,
            identity_confidence_score=player.identity_confidence_score,
            source_name=profile.source_name,
            source_player_key=profile.source_player_key,
            source_last_refreshed_at=profile.source_last_refreshed_at or player.source_last_refreshed_at,
            is_verified_real_player=bool(source_link.is_verified_real_player),
            verification_state=source_link.verification_state,
            known_aliases=tuple(profile.known_aliases_json or ()),
            normalized_signals=dict(profile.normalized_signals_json or {}),
            ingestion_batch_id=profile.ingestion_batch_id,
            ingestion_source_version=profile.ingestion_source_version,
            pricing_snapshot_id=profile.pricing_snapshot_id,
            normalization_profile_version=profile.normalization_profile_version or player.normalization_profile_version,
            metadata_json=dict(profile.metadata_json or {}),
            summary_json=self._summary_payload(summary),
            updated_at=profile.updated_at,
        )

    def _validate_query(
        self,
        *,
        limit: int,
        offset: int,
        min_age: int | None,
        max_age: int | None,
        min_value: float | None,
        max_value: float | None,
        sort: str,
    ) -> None:
        if limit < 1:
            raise RealPlayerUniverseValidationError("limit must be at least 1")
        if offset < 0:
            raise RealPlayerUniverseValidationError("offset cannot be negative")
        if min_age is not None and min_age < 0:
            raise RealPlayerUniverseValidationError("min_age cannot be negative")
        if max_age is not None and max_age < 0:
            raise RealPlayerUniverseValidationError("max_age cannot be negative")
        if min_age is not None and max_age is not None and min_age > max_age:
            raise RealPlayerUniverseValidationError("min_age cannot exceed max_age")
        if min_value is not None and min_value < 0:
            raise RealPlayerUniverseValidationError("min_value cannot be negative")
        if max_value is not None and max_value < 0:
            raise RealPlayerUniverseValidationError("max_value cannot be negative")
        if min_value is not None and max_value is not None and min_value > max_value:
            raise RealPlayerUniverseValidationError("min_value cannot exceed max_value")
        if sort not in REAL_PLAYER_DISCOVERY_SORTS:
            raise RealPlayerUniverseValidationError(
                "sort must be one of: age, current_value, last_refreshed, market_value, name"
            )

    def _player_age(self, date_of_birth):
        if date_of_birth is None or self.today is None:
            return None
        age = self.today.year - date_of_birth.year
        if (self.today.month, self.today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
        return age

    def _summary_payload(self, summary: PlayerSummaryReadModel | None) -> dict:
        if summary is None or not isinstance(summary.summary_json, dict):
            return {}
        return dict(summary.summary_json)

    def _position_expr(self):
        return func.coalesce(RealPlayerProfile.primary_position, Player.normalized_position, Player.position, "")

    def _nationality_expr(self):
        return func.coalesce(Country.name, RealPlayerProfile.nationality, "")

    def _club_expr(self):
        return func.coalesce(RealPlayerProfile.current_club_name, Player.real_world_club_name, "")

    def _league_expr(self):
        return func.coalesce(RealPlayerProfile.current_league_name, Player.real_world_league_name, "")

    def _market_reference_value_expr(self):
        return func.coalesce(RealPlayerProfile.current_market_reference_value, Player.current_market_reference_value)

    def _current_value_expr(self):
        return func.coalesce(
            PlayerSummaryReadModel.current_value_credits,
            RealPlayerProfile.current_market_reference_value,
            Player.current_market_reference_value,
        )

    def _last_refreshed_expr(self):
        return func.coalesce(RealPlayerProfile.source_last_refreshed_at, Player.source_last_refreshed_at)

    def _age_expr(self):
        birth_date = func.coalesce(Player.date_of_birth, RealPlayerProfile.date_of_birth)
        return cast(
            (func.julianday(literal(self.today.isoformat())) - func.julianday(birth_date)) / 365.2425,
            Integer,
        )
