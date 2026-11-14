from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import Integer, String, and_, case, cast, distinct, func, literal, or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.market.lifecycle_status import resolve_player_lifecycle_status
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.players.gsi_service import resolve_player_gsi
from app.players.traits_service import resolve_player_traits_and_playstyle
from app.players.real_player_schemas import RealPlayerMatchRequest
from app.players.real_player_read_models import (
    RealPlayerUniverseDetail,
    RealPlayerUniverseListItem,
    RealPlayerUniversePageResult,
)

REAL_PLAYER_DISCOVERY_SORTS = frozenset({"age", "current_value", "last_refreshed", "market_value", "name"})
REAL_PLAYER_DISCOVERY_AVAILABILITY = frozenset({"free_agent"})
REAL_PLAYER_IDENTITY_RAIL = "real_player_universe"
REAL_PLAYER_MATCH_MAX_CANDIDATES = 500
REAL_PLAYER_MATCH_SECONDARY_POSITION_SCORE = 0.45
REAL_PLAYER_MATCH_SCORE_KEYS = ("position", "age", "country", "height", "foot", "availability")
REAL_PLAYER_HEALTHY_INJURY_STATUSES = frozenset({"", "available", "fit", "healthy", "cleared", "match_fit"})
REAL_PLAYER_TIER_1_LEVELS = frozenset({"tier1", "elite", "featured", "premier", "top-flight", "top_flight"})
REAL_PLAYER_TIER_2_LEVELS = frozenset({"tier2", "core", "open_market", "open market", "development"})
ARCHIVED_DUPLICATE_PLAYER_IDS = frozenset(
    {
        "106bbc0a-a8b3-408e-b856-a4dad15799fd",  # Eric Cantona duplicate (wrong image 2002042479)
        "55f70b9b-dae9-4a55-8721-ccf9bdaa0154",  # Andres Iniesta duplicate
        "0704b985-6e51-49fc-bf74-45820da69183",  # Luis Figo duplicate
        "862d907b-917a-4508-a19d-da3481ae778d",  # Emerson duplicate
        "c02852d3-656f-49d8-bcb2-f83234525e27",  # Bukayo Saka duplicate
        "cd6eaa94-3e3a-4187-bc2c-8ec16f2be165",  # Victor Osimhen duplicate
        "50235403-679f-48c8-88a0-7614e76ccc0e",  # Harry Kane duplicate
        "62930b4f-ce7b-43c9-a6b7-17abd26125a4",  # Paul Onuachu duplicate
        "8f4f3204-985e-4244-ad1b-a820eaada964",  # Aaron Wan-Bissaka duplicate
        "db0bf799-9b9b-4084-be0a-8d3cff413a15",  # Joshua Kimmich duplicate
        "64b8ed47-c422-4b03-a0f6-c8bfef31aa35",  # Kylian Mbappé duplicate
        "42e150d2-dafe-4fd4-8c96-6bf0844893a6",  # Vinicius Junior duplicate
        "0ce1de07-ad08-43da-b34b-875e3ce600fb",  # Jude Bellingham duplicate
        "63ce3e82-7695-40ea-89ee-908126c0c038",  # Michael Olise duplicate
        "4db507e8-3e18-414b-9cbb-909b467ddfdf",  # Alexey Batrakov PSG fake duplicate
        "b025a176-5a02-4749-bbd1-55fc7a97ae48",  # Vitinha duplicate
        "41b9ae69-a1d2-43bb-a532-a50d2bb69a8b",  # Evanilson duplicate
        "d0f413d3-138b-4a5f-94ad-963d33dfc2e9",  # Marquinhos duplicate
        "52a13894-35bb-4aa4-afc3-568eb2260662",  # Taison duplicate
        "a38bcc33-2b4b-4eea-aaec-e6ada32f4221",  # Taison Metalist duplicate
    }
)
REAL_PLAYER_POSITION_SEARCH_TERMS: dict[str, frozenset[str]] = {
    "GK": frozenset({"gk", "goalkeeper"}),
    "CB": frozenset({"cb", "centre-back", "center-back", "central defender"}),
    "LB": frozenset({"lb", "left-back", "left back"}),
    "RB": frozenset({"rb", "right-back", "right back"}),
    "LWB": frozenset({"lwb", "left wing-back", "left wing back"}),
    "RWB": frozenset({"rwb", "right wing-back", "right wing back"}),
    "DM": frozenset({"dm", "cdm", "defensive midfielder", "holding midfielder", "midfielder"}),
    "CM": frozenset({"cm", "central midfielder", "midfielder"}),
    "AM": frozenset({"am", "cam", "attacking midfielder", "attacking midfield", "midfielder"}),
    "LW": frozenset({"lw", "left winger", "left wing", "winger", "forward"}),
    "RW": frozenset({"rw", "right winger", "right wing", "winger", "forward"}),
    "ST": frozenset(
        {"st", "striker", "centre-forward", "center-forward", "centre forward", "center forward", "cf", "forward"}
    ),
}


@dataclass(frozen=True, slots=True)
class _MatchCandidateSnapshot:
    player_id: str
    player_name: str
    canonical_display_name: str | None
    real_player_tier: str | None
    country: str | None
    country_code: str | None
    country_tokens: frozenset[str]
    primary_position_label: str | None
    primary_position_codes: frozenset[str]
    secondary_position_codes: frozenset[str]
    age: int | None
    height_cm: int | None
    preferred_foot: str | None
    club_name: str | None
    current_league_name: str | None
    competition_level: str | None
    current_value_credits: float | None
    current_market_reference_value: float | None
    market_reference_currency: str | None
    source_name: str
    source_last_refreshed_at: datetime | None
    is_verified_real_player: bool
    is_free_agent: bool
    is_injured: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class _ScoredMatch:
    player_id: str
    score: float
    sort_rank_value: float
    sort_refreshed_rank: float
    sort_name: str
    payload: dict[str, Any]


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
        cursor: str | None = None,
        offset: int = 0,
        position: str | None = None,
        country: str | None = None,
        nationality: str | None = None,
        club: str | None = None,
        tier: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        availability: str | None = None,
        search: str | None = None,
        sort: str = "current_value",
    ) -> RealPlayerUniversePageResult:
        normalized_country = self._clean_filter_value(country) or self._clean_filter_value(nationality)
        normalized_availability = self._clean_filter_value(availability)
        normalized_tier = self._clean_filter_value(tier)
        query_signature = self._query_signature(
            position=position,
            country=normalized_country,
            club=club,
            tier=normalized_tier,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=normalized_availability,
            search=search,
            sort=sort,
        )
        effective_offset = self._resolve_offset(
            cursor=cursor,
            offset=offset,
            query_signature=query_signature,
        )
        self._validate_query(
            limit=limit,
            offset=effective_offset,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=normalized_availability,
            sort=sort,
        )
        base_statement = self._apply_filters(
            position=position,
            nationality=normalized_country,
            club=club,
            tier=normalized_tier,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=normalized_availability,
            search=search,
        )
        total = self._count_players(
            position=position,
            nationality=normalized_country,
            club=club,
            tier=normalized_tier,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=normalized_availability,
            search=search,
        )
        statement = (
            base_statement.order_by(*self._order_by(sort=sort, search=search)).offset(effective_offset).limit(limit)
        )
        rows = self.session.execute(statement).all()
        items = tuple(self._build_list_item(*row) for row in rows)
        next_offset = effective_offset + len(items)
        has_more = next_offset < total
        next_cursor = self._encode_cursor(next_offset, query_signature=query_signature) if has_more else None
        return RealPlayerUniversePageResult(
            items=items,
            limit=limit,
            offset=effective_offset,
            total=total,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def get_player_detail(self, player_id: str) -> RealPlayerUniverseDetail:
        row = self.session.execute(self._base_statement().where(Player.id == player_id)).first()
        if row is None:
            raise RealPlayerUniverseNotFoundError(f"real player {player_id} was not found")
        return self._build_detail(*row)

    def match_players(
        self,
        *,
        payload: RealPlayerMatchRequest,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        del user_id
        self._validate_match_query(payload)

        query_signature = self._match_query_signature(payload)
        candidate_limit = min(max(payload.pagination.limit * 25, 100), REAL_PLAYER_MATCH_MAX_CANDIDATES)
        prefiltered_statement = self._apply_match_prefilters(payload=payload)
        total_candidates = int(
            self.session.scalar(select(func.count()).select_from(prefiltered_statement.subquery())) or 0
        )
        rows = self.session.execute(
            prefiltered_statement.order_by(*self._match_candidate_order_by(payload=payload)).limit(candidate_limit)
        ).all()

        normalized_weights = self._normalized_match_weights(payload)
        requested_positions = self._requested_position_codes(payload)
        scored_matches = [
            self._score_match_candidate(
                self._build_match_candidate_snapshot(*row),
                payload=payload,
                weights=normalized_weights,
                requested_positions=requested_positions,
            )
            for row in rows
        ]

        eligible_matches = [match for match in scored_matches if match.score >= payload.constraints.min_match_score]
        eligible_matches.sort(key=self._match_sort_key)

        page_start = self._resolve_match_page_start(
            cursor=payload.pagination.cursor,
            matches=eligible_matches,
            query_signature=query_signature,
        )
        page_end = page_start + payload.pagination.limit
        page_matches = eligible_matches[page_start:page_end]
        has_more = page_end < len(eligible_matches)
        next_cursor = (
            self._encode_match_cursor(page_matches[-1], query_signature=query_signature)
            if has_more and page_matches
            else None
        )

        summary = self._build_match_summary(scored_matches)
        applied_weights = {key: round(value, 4) for key, value in normalized_weights.items()}
        response = {
            "matches": [match.payload for match in page_matches],
            "meta": {
                "total_candidates": total_candidates,
                "scored_candidates": len(scored_matches),
                "returned": len(page_matches),
                "next_cursor": next_cursor,
                "has_more": has_more,
            },
            "summary": summary,
            "applied_config": {
                "weights": applied_weights,
                "constraints": {
                    "strict_position": payload.constraints.strict_position,
                    "exclude_injured": payload.constraints.exclude_injured,
                    "min_match_score": round(payload.constraints.min_match_score, 4),
                },
            },
            "debug": (
                {
                    "candidate_limit": candidate_limit,
                    "query_signature": query_signature,
                    "scored_pool_size": len(scored_matches),
                }
                if payload.debug
                else None
            ),
        }
        return response

    def fetch_match_candidates(
        self,
        *,
        payload: RealPlayerMatchRequest,
    ):
        candidate_limit = min(max(payload.pagination.limit * 25, 100), REAL_PLAYER_MATCH_MAX_CANDIDATES)
        statement = self._apply_match_prefilters(payload=payload)
        statement = statement.order_by(*self._match_candidate_order_by(payload=payload)).limit(candidate_limit)
        return list(self.session.execute(statement).all())

    def _base_statement(self):
        bind = self.session.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
        base_filter = and_(
            Player.is_real_player.is_(True),
            Player.is_tradable.is_(True),
            or_(Player.real_player_tier.is_(None), Player.real_player_tier.notin_(["archived_duplicate", "retired"])),
            Player.id.notin_(ARCHIVED_DUPLICATE_PLAYER_IDS),
        )
        if dialect_name == "postgresql":
            return (
                select(Player, RealPlayerProfile, RealPlayerSourceLink, Country, PlayerSummaryReadModel)
                .outerjoin(RealPlayerProfile, RealPlayerProfile.gtex_player_id == Player.id)
                .outerjoin(RealPlayerSourceLink, RealPlayerSourceLink.id == RealPlayerProfile.source_link_id)
                .outerjoin(Country, Country.id == Player.country_id)
                .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
                .where(base_filter)
            )
        selected_profiles = self._selected_profiles_subquery()
        return (
            select(Player, RealPlayerProfile, RealPlayerSourceLink, Country, PlayerSummaryReadModel)
            .outerjoin(selected_profiles, selected_profiles.c.gtex_player_id == Player.id)
            .outerjoin(RealPlayerProfile, RealPlayerProfile.id == selected_profiles.c.profile_id)
            .outerjoin(RealPlayerSourceLink, RealPlayerSourceLink.id == RealPlayerProfile.source_link_id)
            .outerjoin(Country, Country.id == Player.country_id)
            .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(base_filter)
        )

    def _selected_profiles_subquery(self):
        ranked_profiles = select(
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
        ).subquery()
        return (
            select(ranked_profiles.c.profile_id, ranked_profiles.c.gtex_player_id)
            .where(ranked_profiles.c.profile_rank == 1)
            .subquery()
        )

    def _count_players(
        self,
        *,
        position: str | None,
        nationality: str | None,
        club: str | None,
        tier: str | None,
        min_age: int | None,
        max_age: int | None,
        min_value: float | None,
        max_value: float | None,
        availability: str | None,
        search: str | None,
    ) -> int:
        needs_profile = bool(position or club)
        needs_country = bool(nationality)
        needs_summary = bool(min_value is not None or max_value is not None)

        if not (needs_profile or needs_country or needs_summary or availability == "free_agent"):
            stmt = select(func.count(Player.id)).where(
                Player.is_real_player.is_(True),
                Player.is_tradable.is_(True),
                or_(
                    Player.real_player_tier.is_(None), Player.real_player_tier.notin_(["archived_duplicate", "retired"])
                ),
                Player.id.notin_(ARCHIVED_DUPLICATE_PLAYER_IDS),
            )
            if tier:
                tier_norm = tier.strip().lower()
                if tier_norm in {"legend", "legends", "legendary", "icon"}:
                    stmt = stmt.where(
                        or_(
                            func.lower(func.coalesce(Player.real_player_tier, "")) == "legend",
                            Player.source_provider == "gtex_legend_prime",
                        )
                    )
                elif tier_norm in {"wonderkid", "wonderkids"}:
                    stmt = stmt.where(func.lower(func.coalesce(Player.real_player_tier, "")) == "wonderkid")
                elif tier_norm in {"marquee", "elite", "stars"}:
                    stmt = stmt.where(
                        func.lower(func.coalesce(Player.real_player_tier, "")).in_(("marquee", "featured", "elite"))
                    )
                else:
                    stmt = stmt.where(func.lower(func.coalesce(Player.real_player_tier, "")) == tier_norm)
            if min_age is not None:
                stmt = stmt.where(self._age_expr() >= min_age)
            if max_age is not None:
                stmt = stmt.where(self._age_expr() <= max_age)
            if search:
                cleaned = search.strip()
                tokens = [t.lower() for t in cleaned.split() if t]
                bind = self.session.get_bind()
                dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
                if dialect_name == "postgresql":
                    token_conditions = []
                    for t in tokens:
                        term = f"%{t}%"
                        token_conditions.append(
                            or_(
                                func.f_unaccent(Player.full_name).ilike(term),
                                func.f_unaccent(Player.canonical_display_name).ilike(term),
                            )
                        )
                    stmt = stmt.where(and_(*token_conditions))
                else:
                    token_conditions = []
                    for t in tokens:
                        term = f"%{t}%"
                        token_conditions.append(
                            or_(
                                Player.full_name.ilike(term),
                                Player.canonical_display_name.ilike(term),
                            )
                        )
                    stmt = stmt.where(and_(*token_conditions))
            return int(self.session.scalar(stmt) or 0)

        # Fallback for queries with profile/country/summary join requirements
        filtered_stmt = self._apply_filters(
            position=position,
            nationality=nationality,
            club=club,
            tier=tier,
            min_age=min_age,
            max_age=max_age,
            min_value=min_value,
            max_value=max_value,
            availability=availability,
            search=search,
        )
        subq = filtered_stmt.subquery()
        return int(self.session.scalar(select(func.count(distinct(subq.c.id)))) or 0)

    def _apply_filters(
        self,
        *,
        position: str | None,
        nationality: str | None,
        club: str | None,
        tier: str | None = None,
        min_age: int | None,
        max_age: int | None,
        min_value: float | None,
        max_value: float | None,
        availability: str | None,
        search: str | None,
    ):
        statement = self._base_statement().where(Player.is_tradable.is_(True))
        if position:
            pos_raw = position.strip().lower()
            pos_codes = self._position_codes(pos_raw)
            if pos_raw in {"goalkeeper", "gk"}:
                pos_codes = {"GK"}
            elif pos_raw in {"defender", "def", "df"}:
                pos_codes = {"CB", "LB", "RB", "LWB", "RWB"}
            elif pos_raw in {"midfielder", "mid", "mf"}:
                pos_codes = {"DM", "CM", "AM"}
            elif pos_raw in {"forward", "fwd", "fw", "attacker"}:
                pos_codes = {"ST", "LW", "RW"}
            if pos_codes:
                pos_clauses = [self._lower_trimmed_expr(self._position_expr()) == pos_raw]
                for code in pos_codes:
                    pos_clauses.append(self._lower_trimmed_expr(self._position_expr()) == code.lower())
                    for st in REAL_PLAYER_POSITION_SEARCH_TERMS.get(code, frozenset()):
                        pos_clauses.append(self._lower_trimmed_expr(self._position_expr()) == st)
                pos_clauses.append(
                    cast(RealPlayerProfile.secondary_positions_json, String).ilike(f"%{position.strip()}%")
                )
                statement = statement.where(or_(*pos_clauses))
            else:
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
        if tier:
            tier_norm = tier.strip().lower()
            if tier_norm in {"legend", "legends", "legendary", "icon"}:
                statement = statement.where(
                    or_(
                        func.lower(func.coalesce(Player.real_player_tier, "")) == "legend",
                        Player.source_provider == "gtex_legend_prime",
                    )
                )
            elif tier_norm in {"wonderkid", "wonderkids"}:
                statement = statement.where(func.lower(func.coalesce(Player.real_player_tier, "")) == "wonderkid")
            elif tier_norm in {"marquee", "elite", "stars"}:
                statement = statement.where(
                    func.lower(func.coalesce(Player.real_player_tier, "")).in_(("marquee", "featured", "elite"))
                )
            else:
                statement = statement.where(func.lower(func.coalesce(Player.real_player_tier, "")) == tier_norm)
        if min_age is not None:
            statement = statement.where(self._age_expr() >= min_age)
        if max_age is not None:
            statement = statement.where(self._age_expr() <= max_age)
        if min_value is not None:
            statement = statement.where(self._current_value_expr() >= min_value)
        if max_value is not None:
            statement = statement.where(self._current_value_expr() <= max_value)
        if availability == "free_agent":
            statement = statement.where(self._free_agent_clause())
        if search:
            cleaned = search.strip()
            tokens = [t.lower() for t in cleaned.split() if t]
            bind = self.session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
            if dialect_name == "postgresql":
                token_conditions = []
                for t in tokens:
                    term = f"%{t}%"
                    token_conditions.append(
                        or_(
                            func.f_unaccent(Player.full_name).ilike(term),
                            func.f_unaccent(Player.canonical_display_name).ilike(term),
                        )
                    )
                statement = statement.where(and_(*token_conditions))
            else:
                token_conditions = []
                for t in tokens:
                    term = f"%{t}%"
                    token_conditions.append(
                        or_(
                            Player.full_name.ilike(term),
                            Player.canonical_display_name.ilike(term),
                            RealPlayerProfile.canonical_name.ilike(term),
                            cast(RealPlayerProfile.known_aliases_json, String).ilike(term),
                        )
                    )
                statement = statement.where(and_(*token_conditions))
        return statement

    def _apply_match_prefilters(
        self,
        *,
        payload: RealPlayerMatchRequest,
    ):
        statement = self._base_statement().where(Player.is_tradable.is_(True))
        requested_positions = self._requested_position_codes(payload)
        if payload.constraints.strict_position and requested_positions:
            statement = statement.where(self._position_match_clause(requested_positions))
        if payload.constraints.exclude_injured:
            statement = statement.where(~self._injured_clause())
        if payload.brief.club_level:
            statement = statement.where(self._competition_level_clause(payload.brief.club_level))
        if payload.brief.experience_years.min is not None:
            statement = statement.where(self._experience_years_expr() >= payload.brief.experience_years.min)
        if payload.brief.experience_years.max is not None:
            statement = statement.where(self._experience_years_expr() <= payload.brief.experience_years.max)
        return statement

    def _order_by(self, *, sort: str, search: str | None = None):
        name_expr = func.lower(Player.full_name)
        if search and search.strip():
            cleaned = search.strip()
            prefix = f"{cleaned}%"
            bind = self.session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
            if dialect_name == "postgresql":
                relevance = case(
                    (func.lower(func.f_unaccent(Player.full_name)) == func.lower(func.f_unaccent(cleaned)), 1),
                    (
                        func.lower(func.f_unaccent(func.coalesce(Player.canonical_display_name, "")))
                        == func.lower(func.f_unaccent(cleaned)),
                        1,
                    ),
                    (func.f_unaccent(Player.full_name).ilike(f"{cleaned} %"), 2),
                    (func.f_unaccent(Player.full_name).ilike(f"% {cleaned}"), 2),
                    (func.f_unaccent(Player.full_name).ilike(f"% {cleaned} %"), 2),
                    (func.f_unaccent(func.coalesce(Player.canonical_display_name, "")).ilike(f"{cleaned} %"), 2),
                    (func.f_unaccent(func.coalesce(Player.canonical_display_name, "")).ilike(f"% {cleaned}"), 2),
                    (func.f_unaccent(func.coalesce(Player.canonical_display_name, "")).ilike(f"% {cleaned} %"), 2),
                    (func.f_unaccent(Player.full_name).ilike(prefix), 3),
                    (func.f_unaccent(func.coalesce(Player.canonical_display_name, "")).ilike(prefix), 3),
                    else_=4,
                )
            else:
                relevance = case(
                    (func.lower(Player.full_name) == cleaned.lower(), 1),
                    (func.lower(func.coalesce(Player.canonical_display_name, "")) == cleaned.lower(), 1),
                    (Player.full_name.ilike(f"{cleaned} %"), 2),
                    (Player.full_name.ilike(f"% {cleaned}"), 2),
                    (Player.full_name.ilike(f"% {cleaned} %"), 2),
                    (Player.full_name.ilike(prefix), 3),
                    else_=4,
                )
            return (
                relevance.asc(),
                func.coalesce(Player.governed_gsi, 0).desc(),
                self._current_value_expr().is_(None),
                self._current_value_expr().desc(),
                name_expr.asc(),
                Player.id.asc(),
            )
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
        profile: RealPlayerProfile | None,
        source_link: RealPlayerSourceLink | None,
        country: Country | None,
        summary: PlayerSummaryReadModel | None,
    ) -> RealPlayerUniverseListItem:
        prof_canon = profile.canonical_name if profile is not None else None
        prof_nat = profile.nationality if profile is not None else None
        prof_pos = profile.primary_position if profile is not None else None
        prof_sec = tuple(profile.secondary_positions_json or ()) if profile is not None else ()
        prof_dob = profile.date_of_birth if profile is not None else None
        prof_club = profile.current_club_name if profile is not None else None
        prof_league = profile.current_league_name if profile is not None else None
        prof_level = profile.competition_level if profile is not None else player.real_player_tier
        prof_mkt_val = profile.current_market_reference_value if profile is not None else None
        prof_mkt_cur = profile.market_reference_currency if profile is not None else None
        prof_src = profile.source_name if profile is not None else player.source_provider
        prof_ref = profile.source_last_refreshed_at if profile is not None else None
        prof_upd = profile.updated_at if profile is not None else player.updated_at
        is_ver = bool(source_link.is_verified_real_player) if source_link is not None else True
        playstyle, traits, skills = resolve_player_traits_and_playstyle(player, profile, summary)

        return RealPlayerUniverseListItem(
            player_id=player.id,
            player_name=player.full_name,
            identity_rail=REAL_PLAYER_IDENTITY_RAIL,
            canonical_display_name=player.canonical_display_name or prof_canon or player.full_name,
            real_player_tier=player.real_player_tier,
            nationality=country.name if country is not None else prof_nat,
            nationality_code=getattr(country, "alpha2_code", None),
            position=prof_pos or player.normalized_position or player.position,
            secondary_positions=prof_sec,
            age=self._player_display_age(player, player.date_of_birth or prof_dob),
            current_club_name=prof_club or player.real_world_club_name,
            current_league_name=prof_league or player.real_world_league_name,
            competition_level=prof_level,
            current_value_credits=summary.current_value_credits if summary is not None else None,
            previous_value_credits=summary.previous_value_credits if summary is not None else None,
            movement_pct=summary.movement_pct if summary is not None else None,
            market_interest_score=summary.market_interest_score if summary is not None else None,
            average_rating=summary.average_rating if summary is not None else None,
            current_market_reference_value=prof_mkt_val or player.current_market_reference_value,
            market_reference_currency=prof_mkt_cur or player.market_reference_currency,
            image_url=self._profile_image_url(profile, player),
            source_name=prof_src,
            source_last_refreshed_at=prof_ref or player.source_last_refreshed_at,
            is_verified_real_player=is_ver,
            updated_at=prof_upd,
            playstyle=playstyle,
            traits=traits,
            skills=skills,
        )

    def _build_detail(
        self,
        player: Player,
        profile: RealPlayerProfile | None,
        source_link: RealPlayerSourceLink | None,
        country: Country | None,
        summary: PlayerSummaryReadModel | None,
    ) -> RealPlayerUniverseDetail:
        dna = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
        summary_data = (
            dict(summary.summary_json or {}) if summary is not None and isinstance(summary.summary_json, dict) else {}
        )
        football_attributes: dict[str, int] = {}
        raw_attrs = dna.get("attributes") or summary_data.get("attributes")
        if (
            not isinstance(raw_attrs, dict)
            and profile is not None
            and isinstance(profile.normalized_signals_json, dict)
        ):
            potential_traits = {"pace", "shooting", "passing", "dribbling", "defending", "physical"}
            if any(k.lower() in potential_traits for k in profile.normalized_signals_json):
                raw_attrs = profile.normalized_signals_json

        if isinstance(raw_attrs, dict):
            for k, v in raw_attrs.items():
                if isinstance(v, (int, float)):
                    val = min(99, max(1, int(float(v) * 5))) if float(v) <= 20 else min(99, max(1, int(float(v))))
                    football_attributes[str(k).lower()] = val

        profile_signals = dict(profile.normalized_signals_json or {}) if profile is not None else {}
        raw_signals = football_attributes if football_attributes else profile_signals
        is_legend = (
            str(player.real_player_tier or "").strip().lower() == "legend"
            or str(player.source_provider or "").strip().lower() in ("gtex_legend", "gtex_legend_prime")
            or player.legendary_profile_id is not None
        )
        cur_gsi, pot_gsi = resolve_player_gsi(player)
        detail_potential = None if is_legend else (player.potential or pot_gsi)
        playstyle, traits, skills = resolve_player_traits_and_playstyle(player, profile, summary)
        merged_metadata = {
            **dna,
            **dict((profile.metadata_json if profile is not None else None) or {}),
            "playstyle": playstyle,
            "traits": list(traits),
            "skills": list(skills),
        }
        detail_summary_json = {
            **self._summary_payload(summary),
            "playstyle": playstyle,
            "traits": list(traits),
            "skills": list(skills),
        }
        return RealPlayerUniverseDetail(
            player_id=player.id,
            player_name=player.full_name,
            identity_rail=REAL_PLAYER_IDENTITY_RAIL,
            canonical_display_name=(
                player.canonical_display_name
                or (profile.canonical_name if profile is not None else None)
                or player.full_name
            ),
            first_name=player.first_name,
            last_name=player.last_name,
            short_name=player.short_name,
            nationality=country.name if country is not None else (profile.nationality if profile is not None else None),
            nationality_code=getattr(country, "alpha2_code", None),
            position=player.position or (profile.primary_position if profile is not None else None),
            normalized_position=player.normalized_position,
            primary_position=(
                (profile.primary_position if profile is not None else None)
                or player.normalized_position
                or player.position
            ),
            secondary_positions=tuple((profile.secondary_positions_json if profile is not None else None) or ()),
            age=self._player_display_age(
                player, player.date_of_birth or (profile.date_of_birth if profile is not None else None)
            ),
            date_of_birth=player.date_of_birth or (profile.date_of_birth if profile is not None else None),
            dominant_foot=(profile.dominant_foot if profile is not None else None) or player.preferred_foot,
            height_cm=(profile.height_cm if profile is not None else None) or player.height_cm,
            weight_kg=(profile.weight_kg if profile is not None else None) or player.weight_kg,
            current_club_name=(profile.current_club_name if profile is not None else None)
            or player.real_world_club_name,
            current_league_name=(
                (profile.current_league_name if profile is not None else None) or player.real_world_league_name
            ),
            competition_level=(profile.competition_level if profile is not None else player.real_player_tier),
            current_value_credits=summary.current_value_credits if summary is not None else None,
            previous_value_credits=summary.previous_value_credits if summary is not None else None,
            movement_pct=summary.movement_pct if summary is not None else None,
            market_interest_score=summary.market_interest_score if summary is not None else None,
            average_rating=summary.average_rating if summary is not None else None,
            current_market_reference_value=(
                (profile.current_market_reference_value if profile is not None else None)
                or player.current_market_reference_value
            ),
            market_reference_currency=(
                (profile.market_reference_currency if profile is not None else None) or player.market_reference_currency
            ),
            appearances=profile.appearances if profile is not None else None,
            minutes_played=profile.minutes_played if profile is not None else None,
            goals=profile.goals if profile is not None else None,
            assists=profile.assists if profile is not None else None,
            clean_sheets=profile.clean_sheets if profile is not None else None,
            injury_status=profile.injury_status if profile is not None else None,
            is_tradable=bool(player.is_tradable),
            lifecycle_status=resolve_player_lifecycle_status(player, getattr(player, "share_market", None))[0],
            lifecycle_status_label=resolve_player_lifecycle_status(player, getattr(player, "share_market", None))[1],
            real_player_tier=player.real_player_tier,
            identity_confidence_score=player.identity_confidence_score,
            image_url=self._profile_image_url(profile, player),
            source_name=profile.source_name if profile is not None else player.source_provider,
            source_player_key=profile.source_player_key if profile is not None else player.provider_external_id,
            source_last_refreshed_at=(
                (profile.source_last_refreshed_at if profile is not None else None) or player.source_last_refreshed_at
            ),
            is_verified_real_player=(bool(source_link.is_verified_real_player) if source_link is not None else True),
            verification_state=source_link.verification_state if source_link is not None else "verified",
            known_aliases=tuple((profile.known_aliases_json if profile is not None else None) or ()),
            normalized_signals=raw_signals,
            ingestion_batch_id=profile.ingestion_batch_id if profile is not None else None,
            ingestion_source_version=profile.ingestion_source_version if profile is not None else None,
            pricing_snapshot_id=profile.pricing_snapshot_id if profile is not None else None,
            normalization_profile_version=(
                (profile.normalization_profile_version if profile is not None else None)
                or player.normalization_profile_version
            ),
            metadata_json=merged_metadata,
            summary_json=detail_summary_json,
            updated_at=profile.updated_at if profile is not None else player.updated_at,
            governed_gsi=cur_gsi,
            potential=detail_potential,
            attributes=football_attributes,
            playstyle=playstyle,
            traits=traits,
            skills=skills,
        )

    def _build_match_candidate_snapshot(
        self,
        player: Player,
        profile: RealPlayerProfile | None,
        source_link: RealPlayerSourceLink | None,
        country: Country | None,
        summary: PlayerSummaryReadModel | None,
    ) -> _MatchCandidateSnapshot:
        club_name = (profile.current_club_name if profile is not None else None) or player.real_world_club_name
        prof_pos = profile.primary_position if profile is not None else None
        primary_position_label = prof_pos or player.normalized_position or player.position
        return _MatchCandidateSnapshot(
            player_id=player.id,
            player_name=player.full_name,
            canonical_display_name=(
                player.canonical_display_name
                or (profile.canonical_name if profile is not None else None)
                or player.full_name
            ),
            real_player_tier=player.real_player_tier,
            country=country.name if country is not None else (profile.nationality if profile is not None else None),
            country_code=(getattr(country, "alpha2_code", None) or None),
            country_tokens=frozenset(self._country_tokens(country, profile)),
            primary_position_label=primary_position_label,
            primary_position_codes=frozenset(
                self._position_codes_for_values(prof_pos, player.normalized_position, player.position)
            ),
            secondary_position_codes=frozenset(
                self._position_codes_for_values(
                    *((profile.secondary_positions_json if profile is not None else None) or ())
                )
            ),
            age=self._player_age(player.date_of_birth or (profile.date_of_birth if profile is not None else None)),
            height_cm=(profile.height_cm if profile is not None else None) or player.height_cm,
            preferred_foot=self._normalize_match_value(
                (profile.dominant_foot if profile is not None else None) or player.preferred_foot
            ),
            club_name=club_name,
            current_league_name=(
                (profile.current_league_name if profile is not None else None) or player.real_world_league_name
            ),
            competition_level=profile.competition_level if profile is not None else player.real_player_tier,
            current_value_credits=summary.current_value_credits if summary is not None else None,
            current_market_reference_value=(
                (profile.current_market_reference_value if profile is not None else None)
                or player.current_market_reference_value
            ),
            market_reference_currency=(
                (profile.market_reference_currency if profile is not None else None) or player.market_reference_currency
            ),
            source_name=profile.source_name if profile is not None else player.source_provider,
            source_last_refreshed_at=(
                (profile.source_last_refreshed_at if profile is not None else None) or player.source_last_refreshed_at
            ),
            is_verified_real_player=(bool(source_link.is_verified_real_player) if source_link is not None else True),
            is_free_agent=self._is_free_agent_club(club_name),
            is_injured=self._is_injured(profile.injury_status if profile is not None else None),
            updated_at=profile.updated_at if profile is not None else player.updated_at,
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
        availability: str | None,
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
        if availability is not None and availability not in REAL_PLAYER_DISCOVERY_AVAILABILITY:
            raise RealPlayerUniverseValidationError("availability must be one of: free_agent")
        if sort not in REAL_PLAYER_DISCOVERY_SORTS:
            raise RealPlayerUniverseValidationError(
                "sort must be one of: age, current_value, last_refreshed, market_value, name"
            )

    def _validate_match_query(
        self,
        payload: RealPlayerMatchRequest,
    ) -> None:
        try:
            payload.weights.normalized()
        except ValueError as exc:
            raise RealPlayerUniverseValidationError(str(exc)) from exc

    def _query_signature(
        self,
        *,
        position: str | None,
        country: str | None,
        club: str | None,
        tier: str | None = None,
        min_age: int | None,
        max_age: int | None,
        min_value: float | None,
        max_value: float | None,
        availability: str | None,
        search: str | None,
        sort: str,
    ) -> dict[str, object | None]:
        sig: dict[str, object | None] = {
            "position": self._clean_filter_value(position),
            "country": country,
            "club": self._clean_filter_value(club),
            "min_age": min_age,
            "max_age": max_age,
            "min_value": min_value,
            "max_value": max_value,
            "availability": availability,
            "search": self._clean_filter_value(search),
            "sort": sort,
        }
        if tier is not None:
            sig["tier"] = tier
        return sig

    def _resolve_offset(
        self,
        *,
        cursor: str | None,
        offset: int,
        query_signature: dict[str, object | None],
    ) -> int:
        if cursor is None or not cursor.strip():
            return offset
        return self._decode_cursor(cursor, query_signature=query_signature)

    def _encode_cursor(
        self,
        offset: int,
        *,
        query_signature: dict[str, object | None],
    ) -> str:
        payload = {
            "v": 1,
            "offset": offset,
            "query": query_signature,
        }
        raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")

    def _decode_cursor(
        self,
        cursor: str,
        *,
        query_signature: dict[str, object | None],
    ) -> int:
        try:
            raw_cursor = cursor.strip()
            if not raw_cursor:
                raise ValueError("empty cursor")
            padding = "=" * (-len(raw_cursor) % 4)
            payload = json.loads(base64.urlsafe_b64decode(f"{raw_cursor}{padding}".encode("ascii")).decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
            raise RealPlayerUniverseValidationError("cursor is invalid") from exc

        if not isinstance(payload, dict) or payload.get("v") != 1:
            raise RealPlayerUniverseValidationError("cursor is invalid")
        if payload.get("query") != query_signature:
            raise RealPlayerUniverseValidationError("cursor does not match the current player query")

        raw_offset = payload.get("offset")
        if not isinstance(raw_offset, int) or raw_offset < 0:
            raise RealPlayerUniverseValidationError("cursor is invalid")
        return raw_offset

    def _match_query_signature(
        self,
        payload: RealPlayerMatchRequest,
    ) -> dict[str, object | None]:
        normalized_weights = {key: round(value, 6) for key, value in self._normalized_match_weights(payload).items()}
        return {
            "positions": sorted(self._requested_position_codes(payload)),
            "age": {
                "min": payload.brief.age.min,
                "max": payload.brief.age.max,
                "target": payload.brief.age.target,
            },
            "height_cm": {
                "min": payload.brief.height_cm.min,
                "max": payload.brief.height_cm.max,
                "target": payload.brief.height_cm.target,
            },
            "preferred_foot": sorted(self._normalized_tokens(payload.brief.preferred_foot)),
            "countries": sorted(self._normalized_tokens(payload.brief.countries)),
            "availability": sorted(self._normalized_tokens(payload.brief.availability)),
            "club_level": sorted(self._normalized_tokens(payload.brief.club_level)),
            "experience_years": {
                "min": payload.brief.experience_years.min,
                "max": payload.brief.experience_years.max,
            },
            "weights": normalized_weights,
            "constraints": {
                "strict_position": payload.constraints.strict_position,
                "exclude_injured": payload.constraints.exclude_injured,
                "min_match_score": round(payload.constraints.min_match_score, 6),
            },
            "sorting": {
                "primary": payload.sorting.primary,
                "order": payload.sorting.order,
            },
        }

    def _resolve_match_page_start(
        self,
        *,
        cursor: str | None,
        query_signature: dict[str, object | None],
        matches: list[_ScoredMatch],
    ) -> int:
        if cursor is None or not cursor.strip():
            return 0
        boundary = self._decode_match_cursor(cursor, query_signature=query_signature)
        for index, match in enumerate(matches):
            if self._match_cursor_boundary(match) == boundary:
                return index + 1
        raise RealPlayerUniverseValidationError("cursor is invalid")

    def _encode_match_cursor(
        self,
        match: _ScoredMatch,
        *,
        query_signature: dict[str, object | None],
    ) -> str:
        payload = {
            "v": 2,
            "query": query_signature,
            "boundary": self._match_cursor_boundary(match),
        }
        raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw_payload).decode("ascii").rstrip("=")

    def _decode_match_cursor(
        self,
        cursor: str,
        *,
        query_signature: dict[str, object | None],
    ) -> dict[str, object | None]:
        try:
            raw_cursor = cursor.strip()
            if not raw_cursor:
                raise ValueError("empty cursor")
            padding = "=" * (-len(raw_cursor) % 4)
            payload = json.loads(base64.urlsafe_b64decode(f"{raw_cursor}{padding}".encode("ascii")).decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
            raise RealPlayerUniverseValidationError("cursor is invalid") from exc

        if not isinstance(payload, dict) or payload.get("v") != 2:
            raise RealPlayerUniverseValidationError("cursor is invalid")
        if payload.get("query") != query_signature:
            raise RealPlayerUniverseValidationError("cursor does not match the current player query")
        boundary = payload.get("boundary")
        if not isinstance(boundary, dict):
            raise RealPlayerUniverseValidationError("cursor is invalid")
        return boundary

    def _player_display_age(self, player: Player, fallback_dob):
        from app.services.player_aging import age_years, aging_date_for_player

        dob = getattr(player, "date_of_birth", None) or fallback_dob
        age = age_years(dob, aging_date_for_player(player, self.session))
        if age is not None:
            return age
        dna = player.dna_profile if isinstance(player.dna_profile, dict) else {}
        for key in ("game_age", "gtex_age", "peak_age"):
            try:
                return int(dna.get(key))
            except (TypeError, ValueError):
                continue
        return None

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

    def _clean_filter_value(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _normalize_match_value(self, value: str | None) -> str | None:
        cleaned = self._clean_filter_value(value)
        return cleaned.lower() if cleaned is not None else None

    def _score_match_candidate(
        self,
        candidate: _MatchCandidateSnapshot,
        *,
        payload: RealPlayerMatchRequest,
        weights: dict[str, float],
        requested_positions: set[str],
    ) -> _ScoredMatch:
        position_score, is_exact_position, matched_position, position_label = self._position_metric(
            candidate,
            requested_positions=requested_positions,
        )
        age_score = self._range_metric(
            value=candidate.age,
            minimum=payload.brief.age.min,
            maximum=payload.brief.age.max,
            target=payload.brief.age.target,
        )
        country_score = self._country_metric(candidate, countries=payload.brief.countries)
        height_score = self._range_metric(
            value=candidate.height_cm,
            minimum=payload.brief.height_cm.min,
            maximum=payload.brief.height_cm.max,
            target=payload.brief.height_cm.target,
        )
        foot_score = self._foot_metric(candidate, preferred_foot=payload.brief.preferred_foot)
        availability_score = self._availability_metric(candidate, availability=payload.brief.availability)

        breakdown = {
            "position": round(position_score, 4),
            "age": round(age_score, 4),
            "country": round(country_score, 4),
            "height": round(height_score, 4),
            "foot": round(foot_score, 4),
            "availability": round(availability_score, 4),
        }
        score = self._clamp(
            sum(weights[key] * breakdown[key] for key in REAL_PLAYER_MATCH_SCORE_KEYS),
            0.0,
            1.0,
        )

        reasons = self._build_match_reasons(
            candidate=candidate,
            payload=payload,
            weights=weights,
            breakdown=breakdown,
            position_label=position_label,
        )
        payload_dict = {
            "player_id": candidate.player_id,
            "score": round(score, 4),
            "score_breakdown": breakdown,
            "reasons": reasons,
            "flags": {
                "is_free_agent": candidate.is_free_agent,
                "is_exact_position": is_exact_position,
                "is_high_potential": self._is_high_potential(candidate),
            },
            "player": {
                "name": candidate.player_name,
                "age": candidate.age,
                "position": matched_position or self._response_position(candidate, requested_positions),
                "country": (candidate.country_code or candidate.country),
                "height_cm": candidate.height_cm,
                "preferred_foot": candidate.preferred_foot,
                "club": None if candidate.is_free_agent else candidate.club_name,
            },
        }
        return _ScoredMatch(
            player_id=candidate.player_id,
            score=round(score, 4),
            sort_rank_value=self._rank_value(candidate),
            sort_refreshed_rank=(
                candidate.source_last_refreshed_at.timestamp()
                if candidate.source_last_refreshed_at is not None
                else -1.0
            ),
            sort_name=candidate.player_name.lower(),
            payload=payload_dict,
        )

    def _match_candidate_order_by(self, *, payload: RealPlayerMatchRequest):
        current_value_expr = self._current_value_expr()
        refreshed_expr = self._last_refreshed_expr()
        name_expr = func.lower(Player.full_name)
        order_by: list[Any] = []
        requested_positions = self._requested_position_codes(payload)
        if requested_positions and not payload.constraints.strict_position:
            order_by.append(case((self._position_match_clause(requested_positions), 0), else_=1).asc())
        order_by.extend(
            [
                current_value_expr.is_(None),
                current_value_expr.desc(),
                refreshed_expr.is_(None),
                refreshed_expr.desc(),
                name_expr.asc(),
                Player.id.asc(),
            ]
        )
        return tuple(order_by)

    def _match_sort_key(self, result: _ScoredMatch):
        return (
            -result.score,
            -result.sort_rank_value,
            -result.sort_refreshed_rank,
            result.sort_name,
            result.player_id,
        )

    def _build_match_summary(self, matches: list[_ScoredMatch]) -> dict[str, Any]:
        if not matches:
            return {
                "average_score": 0.0,
                "top_score": 0.0,
                "distribution": {
                    "90_100": 0,
                    "80_89": 0,
                    "70_79": 0,
                    "below_70": 0,
                },
            }
        scores = [match.score for match in matches]
        distribution = {
            "90_100": sum(1 for score in scores if score >= 0.90),
            "80_89": sum(1 for score in scores if 0.80 <= score < 0.90),
            "70_79": sum(1 for score in scores if 0.70 <= score < 0.80),
            "below_70": sum(1 for score in scores if score < 0.70),
        }
        return {
            "average_score": round(sum(scores) / len(scores), 4),
            "top_score": round(max(scores), 4),
            "distribution": distribution,
        }

    def _build_match_reasons(
        self,
        *,
        candidate: _MatchCandidateSnapshot,
        payload: RealPlayerMatchRequest,
        weights: dict[str, float],
        breakdown: dict[str, float],
        position_label: str | None,
    ) -> list[dict[str, str]]:
        reason_items: list[tuple[float, dict[str, str]]] = []

        def add_reason(reason_type: str, label: str | None) -> None:
            if not label:
                return
            impact = round(weights[reason_type] * breakdown[reason_type], 2)
            if impact <= 0:
                return
            reason_items.append(
                (
                    impact,
                    {
                        "type": reason_type,
                        "label": label,
                        "impact": f"+{impact:.2f}",
                    },
                )
            )

        if payload.brief.positions:
            add_reason("position", position_label)
        if (
            payload.brief.age.min is not None
            or payload.brief.age.max is not None
            or payload.brief.age.target is not None
        ):
            if candidate.age is not None and breakdown["age"] > 0:
                age_label = (
                    f"Age {candidate.age} (target {payload.brief.age.target})"
                    if payload.brief.age.target is not None
                    else f"Age {candidate.age} within range"
                )
                add_reason("age", age_label)
        if payload.brief.countries and breakdown["country"] > 0:
            add_reason("country", f"Country match ({candidate.country_code or candidate.country})")
        if (
            (
                payload.brief.height_cm.min is not None
                or payload.brief.height_cm.max is not None
                or payload.brief.height_cm.target is not None
            )
            and candidate.height_cm is not None
            and breakdown["height"] > 0
        ):
            add_reason("height", f"Height {candidate.height_cm}cm")
        if payload.brief.preferred_foot and candidate.preferred_foot is not None and breakdown["foot"] > 0:
            add_reason("foot", f"Preferred foot: {candidate.preferred_foot}")
        if payload.brief.availability and breakdown["availability"] > 0:
            add_reason("availability", "Free agent" if candidate.is_free_agent else "Under contract")

        reason_items.sort(key=lambda item: (-item[0], item[1]["type"], item[1]["label"]))
        return [item for _, item in reason_items[:3]]

    def _normalized_match_weights(self, payload: RealPlayerMatchRequest) -> dict[str, float]:
        return payload.weights.normalized()

    def _requested_position_codes(self, payload: RealPlayerMatchRequest) -> set[str]:
        return self._position_codes_for_values(*payload.brief.positions)

    def _normalized_tokens(self, values: list[str] | tuple[str, ...]) -> set[str]:
        return {
            normalized
            for normalized in (self._normalize_match_value(value) for value in values)
            if normalized is not None
        }

    def _position_metric(
        self,
        candidate: _MatchCandidateSnapshot,
        *,
        requested_positions: set[str],
    ) -> tuple[float, bool, str | None, str | None]:
        if not requested_positions:
            return 1.0, False, self._response_position(candidate, requested_positions), None
        primary_matches = sorted(requested_positions & set(candidate.primary_position_codes))
        if primary_matches:
            return 1.0, True, primary_matches[0], "Primary position match"
        secondary_matches = sorted(requested_positions & set(candidate.secondary_position_codes))
        if secondary_matches:
            return (
                REAL_PLAYER_MATCH_SECONDARY_POSITION_SCORE,
                False,
                secondary_matches[0],
                "Secondary position coverage",
            )
        return 0.0, False, None, None

    def _range_metric(
        self,
        *,
        value: int | None,
        minimum: int | None,
        maximum: int | None,
        target: int | None,
    ) -> float:
        if minimum is None and maximum is None and target is None:
            return 1.0
        if value is None:
            return 0.0
        if minimum is not None and value < minimum:
            return 0.0
        if maximum is not None and value > maximum:
            return 0.0
        if target is None:
            return 1.0
        span_candidates = [1]
        if minimum is not None and maximum is not None:
            span_candidates.append(maximum - minimum)
        if minimum is not None:
            span_candidates.append(abs(target - minimum))
        if maximum is not None:
            span_candidates.append(abs(maximum - target))
        span = max(span_candidates)
        return self._clamp(1 - (abs(value - target) / span), 0.0, 1.0)

    def _country_metric(self, candidate: _MatchCandidateSnapshot, *, countries: list[str]) -> float:
        normalized_countries = self._normalized_tokens(countries)
        if not normalized_countries:
            return 1.0
        return 1.0 if normalized_countries & set(candidate.country_tokens) else 0.0

    def _foot_metric(self, candidate: _MatchCandidateSnapshot, *, preferred_foot: list[str]) -> float:
        normalized_feet = self._normalized_tokens(preferred_foot)
        if not normalized_feet:
            return 1.0
        if candidate.preferred_foot is None:
            return 0.0
        return 1.0 if candidate.preferred_foot in normalized_feet else 0.0

    def _availability_metric(self, candidate: _MatchCandidateSnapshot, *, availability: list[str]) -> float:
        normalized_availability = self._normalized_tokens(availability)
        if not normalized_availability:
            return 1.0
        if normalized_availability == {"free_agent", "contract"}:
            return 1.0
        player_availability = "free_agent" if candidate.is_free_agent else "contract"
        return 1.0 if player_availability in normalized_availability else 0.0

    def _response_position(self, candidate: _MatchCandidateSnapshot, requested_positions: set[str]) -> str | None:
        primary_matches = sorted(requested_positions & set(candidate.primary_position_codes))
        if primary_matches:
            return primary_matches[0]
        if candidate.primary_position_codes:
            return sorted(candidate.primary_position_codes)[0]
        cleaned = self._clean_filter_value(candidate.primary_position_label)
        return cleaned.upper() if cleaned is not None and len(cleaned) <= 4 else cleaned

    def _rank_value(self, candidate: _MatchCandidateSnapshot) -> float:
        if candidate.current_value_credits is not None:
            return float(candidate.current_value_credits)
        if candidate.current_market_reference_value is not None:
            return float(candidate.current_market_reference_value)
        return -1.0

    def _match_cursor_boundary(self, match: _ScoredMatch) -> dict[str, object | None]:
        return {
            "score": round(match.score, 4),
            "rank_value": round(match.sort_rank_value, 4),
            "refreshed_rank": round(match.sort_refreshed_rank, 4),
            "name": match.sort_name,
            "player_id": match.player_id,
        }

    def _is_high_potential(self, candidate: _MatchCandidateSnapshot) -> bool:
        if candidate.age is None or candidate.age > 23:
            return False
        if candidate.current_market_reference_value is not None:
            return candidate.current_market_reference_value <= 20_000_000
        if candidate.current_value_credits is not None:
            return candidate.current_value_credits <= 200.0
        return True

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(value, maximum))

    def _position_match_clause(self, positions: set[str]):
        search_terms = self._position_search_terms(positions)
        if not search_terms:
            return literal(True)
        secondary_positions_expr = func.lower(cast(RealPlayerProfile.secondary_positions_json, String))
        clauses = []
        for term in search_terms:
            clauses.extend(
                [
                    self._lower_trimmed_expr(RealPlayerProfile.primary_position) == term,
                    self._lower_trimmed_expr(Player.normalized_position) == term,
                    self._lower_trimmed_expr(Player.position) == term,
                    secondary_positions_expr.like(f'%"{term}"%'),
                ]
            )
        return or_(*clauses)

    def _competition_level_clause(self, club_levels: list[str]):
        normalized_levels = self._normalized_tokens(club_levels)
        if not normalized_levels:
            return literal(True)
        clauses = []
        level_expr = self._lower_trimmed_expr(RealPlayerProfile.competition_level)
        for level in normalized_levels:
            clauses.extend(level_expr.like(f"%{term}%") for term in self._competition_level_terms(level))
        return or_(*clauses)

    def _competition_level_terms(self, level: str) -> set[str]:
        if level == "tier1":
            return set(REAL_PLAYER_TIER_1_LEVELS)
        if level == "tier2":
            return set(REAL_PLAYER_TIER_2_LEVELS)
        return {level}

    def _experience_years_expr(self):
        return func.max(self._age_expr() - 18, 0)

    def _injured_clause(self):
        injury_expr = self._lower_trimmed_expr(RealPlayerProfile.injury_status)
        return and_(
            injury_expr != "",
            ~injury_expr.in_(tuple(REAL_PLAYER_HEALTHY_INJURY_STATUSES)),
        )

    def _free_agent_clause(self):
        return or_(
            func.trim(self._club_expr()) == "",
            func.lower(func.trim(self._club_expr())) == "free agent",
            func.lower(func.trim(self._club_expr())) == "free-agent",
            func.lower(func.trim(self._club_expr())) == "unattached",
        )

    def _is_free_agent_club(self, club_name: str | None) -> bool:
        normalized_club_name = self._normalize_match_value(club_name)
        return normalized_club_name in {"", "free agent", "free-agent", "unattached"}

    def _is_injured(self, injury_status: str | None) -> bool:
        normalized_status = self._normalize_match_value(injury_status)
        if normalized_status is None:
            return False
        return normalized_status not in REAL_PLAYER_HEALTHY_INJURY_STATUSES

    def _country_tokens(self, country_record: Country | None, profile: RealPlayerProfile | None) -> set[str]:
        values = {
            self._normalize_match_value(profile.nationality if profile is not None else None),
        }
        if country_record is not None:
            values.update(
                {
                    self._normalize_match_value(country_record.name),
                    self._normalize_match_value(country_record.alpha2_code),
                    self._normalize_match_value(country_record.alpha3_code),
                    self._normalize_match_value(country_record.fifa_code),
                }
            )
        values.discard(None)
        return values

    @staticmethod
    def _clean_real_image_url(url: str | None) -> str | None:
        if not isinstance(url, str):
            return None
        cleaned = url.strip()
        if not cleaned:
            return None
        lowered = cleaned.lower()
        if any(
            tok in lowered
            for tok in (
                "regen_newgen_faces",
                "generated-media",
                "regen_portraits",
                "national_regen_portraits",
                "sportmonks.com/images/soccer/placeholder",
            )
        ):
            return None
        return cleaned

    @classmethod
    def _profile_image_url(cls, profile: RealPlayerProfile | None, player: Player | None = None) -> str | None:
        if profile is not None:
            metadata = dict(profile.metadata_json or {})
            photo_url = cls._clean_real_image_url(metadata.get("photo_url"))
            if photo_url:
                return photo_url
            image_payload = metadata.get("image")
            if isinstance(image_payload, dict):
                source_url = cls._clean_real_image_url(image_payload.get("source_url"))
                if source_url:
                    return source_url
        if player is not None and isinstance(player.dna_profile, dict):
            for key in ("portraitUrl", "photo_url", "image_url"):
                val = cls._clean_real_image_url(player.dna_profile.get(key))
                if val:
                    return val
        return None

    def _position_codes_for_values(self, *values: str | None) -> set[str]:
        codes: set[str] = set()
        for value in values:
            codes.update(self._position_codes(value))
        return codes

    def _position_codes(self, value: str | None) -> set[str]:
        normalized_value = self._normalize_match_value(value)
        if normalized_value is None:
            return set()
        codes = {
            code for code, search_terms in REAL_PLAYER_POSITION_SEARCH_TERMS.items() if normalized_value in search_terms
        }
        if codes:
            return codes
        if len(normalized_value) <= 4 and normalized_value.replace("-", "").isalpha():
            return {normalized_value.upper()}
        return set()

    def _position_search_terms(self, positions: set[str]) -> set[str]:
        search_terms: set[str] = set()
        for position in positions:
            normalized_position = position.upper()
            search_terms.update(
                REAL_PLAYER_POSITION_SEARCH_TERMS.get(normalized_position, frozenset({position.lower()}))
            )
        return search_terms

    def _lower_trimmed_expr(self, expression):
        return func.lower(func.trim(func.coalesce(expression, "")))

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

    def _height_expr(self):
        return func.coalesce(RealPlayerProfile.height_cm, Player.height_cm)

    def _age_expr(self):
        from app.services.player_aging import HUMAN_TIERS, LEGEND_SOURCES, LEGEND_TIERS, REGEN_SOURCES, world_date

        birth_date = func.coalesce(Player.date_of_birth, RealPlayerProfile.date_of_birth)
        human = date.today()
        virtual = world_date(self.session)
        tier = func.lower(func.coalesce(Player.real_player_tier, ""))
        source = func.lower(func.coalesce(Player.source_provider, ""))
        regen = and_(
            Player.legendary_profile_id.is_(None),
            source.notin_(tuple(LEGEND_SOURCES)),
            tier.notin_(tuple(LEGEND_TIERS | HUMAN_TIERS)),
            or_(tier == "regen", source.in_(tuple(REGEN_SOURCES)), Player.is_real_player.is_(False)),
        )
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            reference = case((regen, literal(virtual)), else_=literal(human))
            return cast(func.extract("year", func.age(reference, birth_date)), Integer)
        reference = case((regen, literal(virtual.isoformat())), else_=literal(human.isoformat()))
        return cast((func.julianday(reference) - func.julianday(birth_date)) / 365.2425, Integer)
