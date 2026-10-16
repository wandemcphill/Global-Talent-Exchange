"""Talent Exchange query and orchestration service.

Responsibilities:

* project canonical football rows (`ingestion_players`, `ingestion_player_match_stats`,
  `ingestion_matches`, `ingestion_competitions`, `player_injury_cases`) into the
  pure ranking inputs;
* persist the ranking pipeline's output as auditable lineage and as the
  denormalised columns discovery searches on;
* answer bounded, stable, viewer-scoped discovery queries;
* run the scout-side shortlist workflow.

What it does *not* do: create football facts. Every value written to a talent
profile is either copied from a canonical row, supplied by an audited admin
correction, or computed by the deterministic pipeline from those two. Nothing
here fabricates attributes, appearances or ratings for a player who has none —
a talent with no record simply scores neutral with zero confidence, and says so.

It also never touches the economic authority. `value_engine` prices players;
this module ranks them on sporting merit. The two are deliberately separate
numbers and this service holds no write path into the former.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Competition, Country, Match, Player, PlayerMatchStat
from app.models.player_injury_case import PlayerInjuryCase
from app.models.user import User
from app.talent import privacy
from app.talent.constants import (
    AvailabilityStatus,
    COMPARE_MAX_TALENTS,
    CompetitionLevel,
    ModerationState,
    SEARCH_MAX_FILTER_VALUES,
    SEARCH_MAX_PAGE_SIZE,
    SEARCH_MAX_RESULT_WINDOW,
    SHORTLIST_MAX_ENTRIES,
    SHORTLIST_MAX_PER_OWNER,
    TALENT_SIGNAL_CONFIG_VERSION,
    VERIFICATION_TIER_RANK,
    VerificationTier,
    ViewerScope,
    VisibilityState,
)
from app.talent.inputs import (
    AvailabilityWindow,
    TalentMatchRecord,
    TalentRankingInput,
    normalise_attributes,
)
from app.talent.models import (
    TalentProfile,
    TalentRankingSnapshot,
    TalentShortlist,
    TalentShortlistEntry,
    TalentSignalRecord,
)
from app.talent.ranking import (
    COMPONENT_ORDER,
    TalentRankingResult,
    compute_ranking,
)
from app.talent.schemas import TalentSearchRequest

AVAILABILITY_WINDOW_DAYS = 365
AVAILABILITY_FIXTURE_LIMIT = 200
AVAILABILITY_INJURY_LIMIT = 100
MATCH_RECORD_WINDOW_DAYS = 1095  # three seasons of competitive record
MATCH_RECORD_LIMIT = 400
COMPLETED_MATCH_STATUSES = frozenset({"completed", "finished", "played", "full_time", "ft"})


class TalentExchangeError(Exception):
    """Base error for the talent exchange."""


class TalentNotFoundError(TalentExchangeError):
    pass


class TalentAccessDeniedError(TalentExchangeError):
    pass


class TalentValidationError(TalentExchangeError):
    pass


@dataclass(frozen=True, slots=True)
class TalentSearchPage:
    items: tuple[dict[str, Any], ...]
    page: int
    per_page: int
    total: int
    total_pages: int
    sort: str
    applied_filters: dict[str, Any]

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1 and self.total_pages > 0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_membership_index(values: Iterable[str]) -> str:
    """Render a pipe-delimited membership index, e.g. `|CB|LB|`."""

    cleaned = sorted({str(value).strip() for value in values if str(value).strip()})
    if not cleaned:
        return ""
    return "|" + "|".join(cleaned) + "|"


def derive_competition_level(competition: Competition | None) -> str:
    """Map a canonical competition onto the bounded talent level vocabulary.

    Ordered from most to least trustworthy signal so that a competition with a
    real strength rating is never overridden by a coarse fallback.
    """

    if competition is None:
        return CompetitionLevel.UNKNOWN.value

    age_bracket = (competition.age_bracket or "").strip().lower()
    if age_bracket and any(
        token in age_bracket for token in ("u15", "u16", "u17", "u18", "u19", "u20", "u21", "youth")
    ):
        return CompetitionLevel.YOUTH.value

    strength = competition.competition_strength
    if strength is not None:
        value = float(strength)
        if value >= 90:
            return CompetitionLevel.ELITE.value
        if value >= 78:
            return CompetitionLevel.TIER_1.value
        if value >= 64:
            return CompetitionLevel.TIER_2.value
        if value >= 50:
            return CompetitionLevel.TIER_3.value
        if value >= 36:
            return CompetitionLevel.TIER_4.value
        if value >= 24:
            return CompetitionLevel.SEMI_PRO.value
        return CompetitionLevel.AMATEUR.value

    if competition.is_major:
        return CompetitionLevel.ELITE.value

    domestic_level = competition.domestic_level
    if domestic_level is not None:
        mapping = {
            1: CompetitionLevel.TIER_1.value,
            2: CompetitionLevel.TIER_2.value,
            3: CompetitionLevel.TIER_3.value,
            4: CompetitionLevel.TIER_4.value,
        }
        return mapping.get(int(domestic_level), CompetitionLevel.SEMI_PRO.value)

    return CompetitionLevel.UNKNOWN.value


def _day_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """Half-open day range as timezone-aware datetimes, for `kickoff_at` filters.

    Comparing a `DateTime` column against a `date` behaves inconsistently across
    SQLite and Postgres, so the range is widened to explicit datetimes.
    """

    return (
        datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc),
        datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc),
    )


def _age_years(date_of_birth: date | None, as_of: date) -> int | None:
    if date_of_birth is None:
        return None
    years = as_of.year - date_of_birth.year
    if (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return max(0, years)


class TalentExchangeService:
    """Read/orchestration surface for talent discovery."""

    def __init__(self, session: Session, *, today: date | None = None) -> None:
        self.session = session
        self._today = today

    @property
    def today(self) -> date:
        return self._today or _utcnow().date()

    # ------------------------------------------------------------------
    # Profile lifecycle
    # ------------------------------------------------------------------

    def get_profile_row(self, player_id: str) -> TalentProfile:
        profile = self.session.execute(
            select(TalentProfile).where(TalentProfile.player_id == player_id)
        ).scalar_one_or_none()
        if profile is None:
            raise TalentNotFoundError(f"No talent profile exists for player '{player_id}'.")
        return profile

    def sync_profile_from_player(
        self,
        player_id: str,
        *,
        as_of: date | None = None,
        owner_user_id: str | None = None,
    ) -> TalentProfile:
        """Create or refresh the discovery projection of a canonical player.

        Fields an admin has explicitly corrected are preserved: the correction
        marks itself in `metadata_json['manual_fields']` and sync skips those
        keys rather than silently reverting a human decision on the next run.
        """

        reference_date = as_of or self.today
        player = self.session.get(Player, player_id)
        if player is None:
            raise TalentNotFoundError(f"No canonical player exists with id '{player_id}'.")

        profile = self.session.execute(
            select(TalentProfile).where(TalentProfile.player_id == player_id)
        ).scalar_one_or_none()
        created = profile is None
        if profile is None:
            profile = TalentProfile(player_id=player_id, display_name=player.full_name)
            self.session.add(profile)

        manual_fields = set(str(item) for item in (profile.metadata_json or {}).get("manual_fields", []))

        def assign(field_name: str, value: Any) -> None:
            if field_name in manual_fields:
                return
            setattr(profile, field_name, value)

        assign("display_name", player.canonical_display_name or player.full_name)
        assign("position_code", (player.normalized_position or "").strip().upper() or None)
        if "secondary_positions_json" not in manual_fields:
            profile.secondary_positions_json = sorted(
                {str(code).strip().upper() for code in (player.secondary_positions_json or []) if str(code).strip()}
            )
        assign("preferred_foot", (player.preferred_foot or "").strip().lower() or None)
        assign("date_of_birth", player.date_of_birth)
        assign("age_years", _age_years(player.date_of_birth, reference_date))
        assign("height_cm", player.height_cm)
        assign("weight_kg", player.weight_kg)
        assign("current_club_name", player.real_world_club_name)
        assign("current_competition_name", player.real_world_league_name)

        if "nationality_code" not in manual_fields:
            country = self.session.get(Country, player.country_id) if player.country_id else None
            # FIFA codes are what football audiences read; fall back through the
            # ISO codes so a partially-populated country row still yields one.
            code = ""
            if country is not None:
                code = country.fifa_code or country.alpha3_code or country.alpha2_code or ""
            profile.nationality_code = code.strip().upper() or None
            profile.nationality_name = getattr(country, "name", None)

        if owner_user_id is not None:
            profile.owner_user_id = owner_user_id

        if created:
            profile.visibility_state = VisibilityState.DRAFT.value
            profile.moderation_state = ModerationState.CLEAR.value
            profile.verification_tier = VerificationTier.UNVERIFIED.value
            profile.availability_status = AvailabilityStatus.UNKNOWN.value

        self.refresh_indexes(profile)
        self.session.flush()
        return profile

    def refresh_indexes(self, profile: TalentProfile) -> None:
        positions = [profile.position_code] if profile.position_code else []
        positions.extend(profile.secondary_positions_json or [])
        profile.position_index = build_membership_index(positions)
        profile.tactical_role_index = build_membership_index(profile.tactical_roles_json or [])
        profile.signal_index = build_membership_index(profile.active_signal_codes_json or [])

    # ------------------------------------------------------------------
    # Ranking pipeline
    # ------------------------------------------------------------------

    def build_ranking_input(self, profile: TalentProfile, *, as_of: date | None = None) -> TalentRankingInput:
        reference_date = as_of or self.today
        records = self._load_match_records(profile.player_id, as_of=reference_date)
        experience = self._resolve_experience_years(profile, records, reference_date)
        return TalentRankingInput(
            player_id=profile.player_id,
            as_of=reference_date,
            position_code=profile.position_code,
            age_years=(
                profile.age_years
                if profile.age_years is not None
                else _age_years(profile.date_of_birth, reference_date)
            ),
            experience_years=experience,
            verification_tier=profile.verification_tier,
            technical_attributes=normalise_attributes(profile.technical_attributes_json),
            tactical_attributes=normalise_attributes(profile.tactical_attributes_json),
            physical_attributes=normalise_attributes(profile.physical_attributes_json),
            match_records=records,
            availability=self._load_availability_window(profile.player_id, as_of=reference_date),
        )

    def _load_match_records(self, player_id: str, *, as_of: date) -> tuple[TalentMatchRecord, ...]:
        window_start, window_end = _day_bounds(as_of - timedelta(days=MATCH_RECORD_WINDOW_DAYS), as_of)
        # The window and the row cap are both pushed into SQL: a player with a
        # twenty-year record must not pull twenty years of rows into memory to
        # score three seasons.
        statement = (
            select(PlayerMatchStat, Match, Competition)
            .join(Match, Match.id == PlayerMatchStat.match_id)
            .outerjoin(Competition, Competition.id == Match.competition_id)
            .where(PlayerMatchStat.player_id == player_id)
            .where(Match.kickoff_at.is_not(None))
            .where(Match.kickoff_at >= window_start)
            .where(Match.kickoff_at <= window_end)
            .order_by(Match.kickoff_at.desc(), PlayerMatchStat.match_id.asc())
            .limit(MATCH_RECORD_LIMIT)
        )
        records: list[TalentMatchRecord] = []
        for stat, match, competition in self.session.execute(statement).all():
            kickoff = match.kickoff_at
            if kickoff is None:
                continue
            played_on = kickoff.date() if isinstance(kickoff, datetime) else kickoff
            records.append(
                TalentMatchRecord(
                    match_key=str(stat.match_id),
                    played_on=played_on,
                    competition_key=str(match.competition_id or "unknown"),
                    competition_level=derive_competition_level(competition),
                    stage=match.stage,
                    minutes=int(stat.minutes or 0),
                    rating=None if stat.rating is None else float(stat.rating),
                    goals=int(stat.goals or 0),
                    assists=int(stat.assists or 0),
                    clean_sheet=bool(stat.clean_sheet),
                    saves=int(stat.saves or 0),
                    started=bool(stat.starts or 0),
                    yellow_cards=0,
                    red_cards=0,
                )
            )
        return tuple(records)

    def _load_availability_window(self, player_id: str, *, as_of: date) -> AvailabilityWindow | None:
        """Availability measured against the club's fixture list, not selection.

        A fit player left on the bench is available; an injured player is not.
        The denominator is therefore every fixture their club played inside the
        window, and the numerator is those fixtures that did not fall inside a
        recorded injury period. If we have no club or no fixtures we return
        `None` rather than guessing — an absent signal is honest, a fabricated
        one is not.
        """

        player = self.session.get(Player, player_id)
        club_id = getattr(player, "current_club_id", None) if player else None
        if not club_id:
            return None

        window_start = as_of - timedelta(days=AVAILABILITY_WINDOW_DAYS)
        range_start, range_end = _day_bounds(window_start, as_of)
        fixture_rows = (
            self.session.execute(
                select(Match.kickoff_at)
                .where(or_(Match.home_club_id == club_id, Match.away_club_id == club_id))
                .where(Match.kickoff_at.is_not(None))
                .where(Match.kickoff_at >= range_start)
                .where(Match.kickoff_at <= range_end)
                .limit(AVAILABILITY_FIXTURE_LIMIT)
            )
            .scalars()
            .all()
        )
        fixture_dates = sorted(
            {(value.date() if isinstance(value, datetime) else value) for value in fixture_rows if value is not None}
        )
        if not fixture_dates:
            return None

        injury_rows = (
            self.session.execute(
                select(PlayerInjuryCase)
                .where(PlayerInjuryCase.player_id == player_id)
                .where(PlayerInjuryCase.occurred_on <= as_of)
                .order_by(PlayerInjuryCase.occurred_on.desc())
                .limit(AVAILABILITY_INJURY_LIMIT)
            )
            .scalars()
            .all()
        )
        intervals: list[tuple[date, date]] = []
        for case in injury_rows:
            start = case.occurred_on
            end = case.recovered_on or case.expected_return_on or as_of
            if start is None or end is None or end < start:
                continue
            if end < window_start:
                continue
            intervals.append((max(start, window_start), min(end, as_of)))

        unavailable_fixtures = sum(
            1 for fixture in fixture_dates if any(start <= fixture <= end for start, end in intervals)
        )
        days_unavailable = sum(max(0, (end - start).days + 1) for start, end in intervals)
        return AvailabilityWindow(
            eligible_matches=len(fixture_dates),
            available_matches=len(fixture_dates) - unavailable_fixtures,
            days_unavailable=days_unavailable,
            window_days=AVAILABILITY_WINDOW_DAYS,
        )

    def _resolve_experience_years(
        self,
        profile: TalentProfile,
        records: Sequence[TalentMatchRecord],
        as_of: date,
    ) -> float:
        metadata = profile.metadata_json or {}
        if "experience_years" in set(str(item) for item in metadata.get("manual_fields", [])):
            return float(profile.experience_years or 0.0)
        if not records:
            return float(profile.experience_years or 0.0)
        earliest = min(record.played_on for record in records)
        return round(max(0.0, (as_of - earliest).days / 365.25), 2)

    def recompute_ranking(
        self,
        player_id: str,
        *,
        as_of: date | None = None,
    ) -> TalentRankingResult:
        """Score a talent and persist the result plus its full lineage."""

        reference_date = as_of or self.today
        profile = self.get_profile_row(player_id)
        ranking_input = self.build_ranking_input(profile, as_of=reference_date)
        result = compute_ranking(ranking_input)
        self._persist_ranking(profile, result, as_of=reference_date)
        return result

    def _persist_ranking(
        self,
        profile: TalentProfile,
        result: TalentRankingResult,
        *,
        as_of: date,
    ) -> None:
        snapshot = self.session.execute(
            select(TalentRankingSnapshot)
            .where(TalentRankingSnapshot.player_id == profile.player_id)
            .where(TalentRankingSnapshot.as_of == as_of)
            .where(TalentRankingSnapshot.config_version == result.config_version)
        ).scalar_one_or_none()
        if snapshot is None:
            snapshot = TalentRankingSnapshot(
                profile_id=profile.id,
                player_id=profile.player_id,
                as_of=as_of,
                config_version=result.config_version,
                composite_score=result.composite_score,
                base_score=result.base_score,
                inputs_digest=result.inputs_digest,
            )
            self.session.add(snapshot)
        snapshot.profile_id = profile.id
        snapshot.composite_score = result.composite_score
        snapshot.base_score = result.base_score
        snapshot.adjustments_total = result.adjustments_total
        snapshot.confidence = result.confidence
        snapshot.sample_size = result.sample_size
        snapshot.components_json = [component.as_payload() for component in result.components]
        snapshot.adjustments_json = [adjustment.as_payload() for adjustment in result.adjustments]
        snapshot.signals_json = [signal.as_payload() for signal in result.signals]
        snapshot.inputs_digest = result.inputs_digest

        existing_signals = {
            record.signal_code: record
            for record in self.session.execute(
                select(TalentSignalRecord)
                .where(TalentSignalRecord.player_id == profile.player_id)
                .where(TalentSignalRecord.as_of == as_of)
            ).scalars()
        }
        emitted_codes: set[str] = set()
        for signal in result.signals:
            emitted_codes.add(signal.code)
            record = existing_signals.get(signal.code)
            if record is None:
                record = TalentSignalRecord(
                    profile_id=profile.id,
                    player_id=profile.player_id,
                    as_of=as_of,
                    signal_code=signal.code,
                    label=signal.label,
                    config_version=TALENT_SIGNAL_CONFIG_VERSION,
                )
                self.session.add(record)
            record.profile_id = profile.id
            record.label = signal.label
            record.polarity = signal.polarity
            record.strength = signal.strength
            record.sample_size = signal.sample_size
            record.explanation = signal.explanation
            record.evidence_json = dict(signal.evidence)
            record.config_version = TALENT_SIGNAL_CONFIG_VERSION
        for code, record in existing_signals.items():
            if code not in emitted_codes:
                # The evidence no longer supports this signal on this date.
                self.session.delete(record)

        profile.composite_score = result.composite_score
        profile.form_score = result.form_score
        profile.consistency_score = result.consistency_score
        profile.competition_level_score = result.competition_level_score
        profile.ranking_confidence = result.confidence
        profile.ranking_sample_size = result.sample_size
        profile.ranking_computed_at = _utcnow()
        profile.ranking_config_version = result.config_version
        profile.ranking_inputs_digest = result.inputs_digest
        profile.active_signal_codes_json = sorted(emitted_codes)
        self.refresh_indexes(profile)
        self.session.flush()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def search(self, request: TalentSearchRequest, *, viewer: User | None) -> TalentSearchPage:
        scope = privacy.resolve_viewer_scope(None, viewer)
        self._assert_search_bounds(request)

        statement = self._apply_search_filters(select(TalentProfile), request, scope)
        total = int(self.session.execute(select(func.count()).select_from(statement.subquery())).scalar_one())
        ordered = self._apply_search_order(statement, request.sort)
        offset = (request.page - 1) * request.per_page
        rows = self.session.execute(ordered.offset(offset).limit(request.per_page)).scalars().all()

        total_pages = (total + request.per_page - 1) // request.per_page if total else 0
        return TalentSearchPage(
            items=tuple(privacy.project_search_result(row, scope=scope) for row in rows),
            page=request.page,
            per_page=request.per_page,
            total=total,
            total_pages=total_pages,
            sort=request.sort,
            applied_filters=self._describe_filters(request, scope),
        )

    def _assert_search_bounds(self, request: TalentSearchRequest) -> None:
        """Re-assert the API-layer ceilings for non-HTTP callers."""

        if request.per_page > SEARCH_MAX_PAGE_SIZE:
            raise TalentValidationError(f"per_page exceeds the {SEARCH_MAX_PAGE_SIZE} ceiling.")
        if request.page * request.per_page > SEARCH_MAX_RESULT_WINDOW:
            raise TalentValidationError(f"Result window exceeds the {SEARCH_MAX_RESULT_WINDOW} row ceiling.")
        for field_name in (
            "positions",
            "preferred_positions",
            "tactical_roles",
            "nationality_codes",
            "location_country_codes",
            "availability",
            "required_signals",
        ):
            values = getattr(request, field_name, None)
            if values and len(values) > SEARCH_MAX_FILTER_VALUES:
                raise TalentValidationError(
                    f"Filter '{field_name}' exceeds the {SEARCH_MAX_FILTER_VALUES} value ceiling."
                )

    def _apply_search_filters(
        self,
        statement: Select[tuple[TalentProfile]],
        request: TalentSearchRequest,
        scope: ViewerScope,
    ) -> Select[tuple[TalentProfile]]:
        # Discovery only ever returns published profiles, for every scope
        # including admin. Admins inspect drafts and suspensions through the
        # admin profile endpoint, not by having search quietly widen.
        statement = statement.where(TalentProfile.visibility_state == VisibilityState.PUBLISHED.value)
        statement = statement.where(TalentProfile.moderation_state != ModerationState.RESTRICTED.value)

        if request.q:
            pattern = f"%{request.q.strip().lower()}%"
            statement = statement.where(func.lower(TalentProfile.display_name).like(pattern))
        if request.positions:
            for code in request.positions:
                statement = statement.where(TalentProfile.position_index.like(f"%|{code}|%"))
        if request.preferred_positions:
            statement = statement.where(TalentProfile.position_code.in_(request.preferred_positions))
        if request.tactical_roles:
            for role in request.tactical_roles:
                statement = statement.where(TalentProfile.tactical_role_index.like(f"%|{role}|%"))
        if request.preferred_foot:
            statement = statement.where(TalentProfile.preferred_foot == request.preferred_foot)
        if request.min_age is not None:
            statement = statement.where(TalentProfile.age_years >= request.min_age)
        if request.max_age is not None:
            statement = statement.where(TalentProfile.age_years <= request.max_age)
        if request.nationality_codes:
            statement = statement.where(TalentProfile.nationality_code.in_(request.nationality_codes))
        if request.location_country_codes:
            statement = statement.where(TalentProfile.location_country_code.in_(request.location_country_codes))
        if request.location_region:
            statement = statement.where(
                func.lower(TalentProfile.location_region) == request.location_region.strip().lower()
            )
        if request.availability:
            statement = statement.where(TalentProfile.availability_status.in_(request.availability))
        if request.min_verification_tier is not None:
            minimum_rank = VERIFICATION_TIER_RANK[request.min_verification_tier.value]
            allowed = [tier for tier, rank in VERIFICATION_TIER_RANK.items() if rank >= minimum_rank]
            statement = statement.where(TalentProfile.verification_tier.in_(allowed))
        if request.min_composite_score is not None:
            statement = statement.where(TalentProfile.composite_score >= request.min_composite_score)
        if request.max_composite_score is not None:
            statement = statement.where(TalentProfile.composite_score <= request.max_composite_score)
        if request.min_form_score is not None:
            statement = statement.where(TalentProfile.form_score >= request.min_form_score)
        if request.min_competition_level_score is not None:
            statement = statement.where(TalentProfile.competition_level_score >= request.min_competition_level_score)
        if request.min_experience_years is not None:
            statement = statement.where(TalentProfile.experience_years >= request.min_experience_years)
        if request.min_ranking_confidence is not None:
            statement = statement.where(TalentProfile.ranking_confidence >= request.min_ranking_confidence)
        if request.min_sample_size is not None:
            statement = statement.where(TalentProfile.ranking_sample_size >= request.min_sample_size)
        if request.required_signals:
            allowed_codes = privacy.visible_signal_codes(request.required_signals, scope)
            withheld = sorted(set(request.required_signals) - set(allowed_codes))
            if withheld:
                # Filtering on a restricted signal would let an anonymous caller
                # infer it by set subtraction, so refuse rather than silently drop.
                raise TalentAccessDeniedError(
                    "Signal filter(s) not available at this access level: " + ", ".join(withheld)
                )
            for code in allowed_codes:
                statement = statement.where(TalentProfile.signal_index.like(f"%|{code}|%"))
        if request.featured_only:
            statement = statement.where(TalentProfile.is_featured.is_(True))
        return statement

    def _apply_search_order(self, statement: Select[tuple[TalentProfile]], sort: str) -> Select[tuple[TalentProfile]]:
        """Every ordering ends in `player_id` so repeated requests never shuffle."""

        tie_break = TalentProfile.player_id.asc()
        if sort == "form":
            return statement.order_by(TalentProfile.form_score.desc(), tie_break)
        if sort == "age_asc":
            return statement.order_by(TalentProfile.age_years.asc(), tie_break)
        if sort == "age_desc":
            return statement.order_by(TalentProfile.age_years.desc(), tie_break)
        if sort == "competition_level":
            return statement.order_by(TalentProfile.competition_level_score.desc(), tie_break)
        if sort == "recently_updated":
            return statement.order_by(TalentProfile.updated_at.desc(), tie_break)
        if sort == "name":
            return statement.order_by(TalentProfile.display_name.asc(), tie_break)
        return statement.order_by(TalentProfile.composite_score.desc(), tie_break)

    def _describe_filters(self, request: TalentSearchRequest, scope: ViewerScope) -> dict[str, Any]:
        applied = {
            key: value
            for key, value in request.model_dump(exclude_none=True).items()
            if key not in {"page", "per_page", "sort"} and value not in ((), [], False)
        }
        applied["visibility_state"] = VisibilityState.PUBLISHED.value
        applied["viewer_scope"] = scope.value
        return applied

    # ------------------------------------------------------------------
    # Profile / ranking reads
    # ------------------------------------------------------------------

    def get_profile(self, player_id: str, *, viewer: User | None) -> dict[str, Any]:
        profile = self.get_profile_row(player_id)
        scope = privacy.resolve_viewer_scope(profile, viewer)
        if not privacy.can_view_profile(profile, scope):
            raise TalentNotFoundError(f"No published talent profile exists for player '{player_id}'.")
        signals = self.latest_signal_payloads(player_id)
        return privacy.project_profile(profile, scope=scope, signal_payloads=signals)

    def get_ranking(self, player_id: str, *, viewer: User | None) -> dict[str, Any]:
        profile = self.get_profile_row(player_id)
        scope = privacy.resolve_viewer_scope(profile, viewer)
        if not privacy.can_view_profile(profile, scope):
            raise TalentNotFoundError(f"No published talent profile exists for player '{player_id}'.")
        snapshot = self._latest_snapshot(player_id)
        if snapshot is None:
            result = compute_ranking(self.build_ranking_input(profile))
            payload = result.as_payload()
        else:
            payload = {
                "player_id": snapshot.player_id,
                "as_of": snapshot.as_of.isoformat(),
                "config_version": snapshot.config_version,
                "composite_score": snapshot.composite_score,
                "base_score": snapshot.base_score,
                "adjustments_total": snapshot.adjustments_total,
                "confidence": snapshot.confidence,
                "sample_size": snapshot.sample_size,
                "components": list(snapshot.components_json or []),
                "adjustments": list(snapshot.adjustments_json or []),
                "signals": list(snapshot.signals_json or []),
                "inputs_digest": snapshot.inputs_digest,
            }
        payload["signals"] = privacy.visible_signals(payload.get("signals", []), scope)
        if not privacy.is_scout_scope(scope):
            payload["inputs_digest"] = ""
        return payload

    def get_signals(self, player_id: str, *, viewer: User | None) -> dict[str, Any]:
        profile = self.get_profile_row(player_id)
        scope = privacy.resolve_viewer_scope(profile, viewer)
        if not privacy.can_view_profile(profile, scope):
            raise TalentNotFoundError(f"No published talent profile exists for player '{player_id}'.")
        records = self._latest_signal_records(player_id)
        as_of = records[0].as_of.isoformat() if records else None
        return {
            "player_id": player_id,
            "as_of": as_of,
            "config_version": TALENT_SIGNAL_CONFIG_VERSION,
            "signals": privacy.visible_signals([self._signal_payload(record) for record in records], scope),
        }

    def compare(self, player_ids: Sequence[str], *, viewer: User | None) -> dict[str, Any]:
        unique_ids = list(dict.fromkeys(player_id.strip() for player_id in player_ids if player_id.strip()))
        if len(unique_ids) < 2:
            raise TalentValidationError("Provide at least two distinct player ids to compare.")
        if len(unique_ids) > COMPARE_MAX_TALENTS:
            raise TalentValidationError(f"At most {COMPARE_MAX_TALENTS} talents can be compared at once.")

        rows = (
            self.session.execute(select(TalentProfile).where(TalentProfile.player_id.in_(unique_ids))).scalars().all()
        )
        by_player = {row.player_id: row for row in rows}

        talents: list[dict[str, Any]] = []
        missing: list[str] = []
        scopes: list[str] = []
        for player_id in unique_ids:
            profile = by_player.get(player_id)
            if profile is None:
                missing.append(player_id)
                continue
            scope = privacy.resolve_viewer_scope(profile, viewer)
            if not privacy.can_view_profile(profile, scope):
                missing.append(player_id)
                continue
            scopes.append(scope.value)
            talents.append(
                privacy.project_profile(
                    profile,
                    scope=scope,
                    signal_payloads=self.latest_signal_payloads(player_id),
                )
            )

        component_matrix = self._component_matrix([talent["player_id"] for talent in talents])
        effective_scope = privacy.resolve_viewer_scope(None, viewer).value
        return {
            "talents": talents,
            "component_matrix": component_matrix,
            "viewer_scope": scopes[0] if len(set(scopes)) == 1 and scopes else effective_scope,
            "missing_player_ids": missing,
        }

    def _component_matrix(self, player_ids: Sequence[str]) -> list[dict[str, Any]]:
        """One row per ranking component, one column per compared talent."""

        if not player_ids:
            return []
        snapshots = {player_id: self._latest_snapshot(player_id) for player_id in player_ids}
        matrix: list[dict[str, Any]] = []
        for code in COMPONENT_ORDER:
            row: dict[str, Any] = {"component": code, "scores": {}}
            for player_id in player_ids:
                snapshot = snapshots.get(player_id)
                score = None
                label = None
                if snapshot is not None:
                    for component in snapshot.components_json or []:
                        if component.get("code") == code:
                            score = component.get("score")
                            label = component.get("label")
                            break
                row["scores"][player_id] = score
                if label and "label" not in row:
                    row["label"] = label
            matrix.append(row)
        return matrix

    def _latest_snapshot(self, player_id: str) -> TalentRankingSnapshot | None:
        return self.session.execute(
            select(TalentRankingSnapshot)
            .where(TalentRankingSnapshot.player_id == player_id)
            .order_by(TalentRankingSnapshot.as_of.desc(), TalentRankingSnapshot.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _latest_signal_records(self, player_id: str) -> list[TalentSignalRecord]:
        latest_as_of = self.session.execute(
            select(func.max(TalentSignalRecord.as_of)).where(TalentSignalRecord.player_id == player_id)
        ).scalar_one_or_none()
        if latest_as_of is None:
            return []
        return list(
            self.session.execute(
                select(TalentSignalRecord)
                .where(TalentSignalRecord.player_id == player_id)
                .where(TalentSignalRecord.as_of == latest_as_of)
                .order_by(TalentSignalRecord.signal_code.asc())
            ).scalars()
        )

    def latest_signal_payloads(self, player_id: str) -> list[dict[str, Any]]:
        return [self._signal_payload(record) for record in self._latest_signal_records(player_id)]

    @staticmethod
    def _signal_payload(record: TalentSignalRecord) -> dict[str, Any]:
        return {
            "code": record.signal_code,
            "label": record.label,
            "polarity": record.polarity,
            "strength": round(float(record.strength or 0.0), 4),
            "sample_size": int(record.sample_size or 0),
            "explanation": record.explanation,
            "evidence": dict(record.evidence_json or {}),
            "as_of": record.as_of.isoformat(),
        }

    # ------------------------------------------------------------------
    # Shortlists
    # ------------------------------------------------------------------

    def list_shortlists(self, *, owner: User, include_entries: bool = False) -> list[dict[str, Any]]:
        rows = (
            self.session.execute(
                select(TalentShortlist)
                .where(TalentShortlist.owner_user_id == owner.id)
                .order_by(TalentShortlist.name.asc())
            )
            .scalars()
            .all()
        )
        return [self._shortlist_view(row, include_entries=include_entries, viewer=owner) for row in rows]

    def create_shortlist(
        self,
        *,
        owner: User,
        name: str,
        description: str | None = None,
        club_id: str | None = None,
    ) -> TalentShortlist:
        existing_count = int(
            self.session.execute(
                select(func.count()).select_from(TalentShortlist).where(TalentShortlist.owner_user_id == owner.id)
            ).scalar_one()
        )
        if existing_count >= SHORTLIST_MAX_PER_OWNER:
            raise TalentValidationError(
                f"Shortlist limit reached ({SHORTLIST_MAX_PER_OWNER}). Archive or delete one first."
            )
        duplicate = self.session.execute(
            select(TalentShortlist).where(TalentShortlist.owner_user_id == owner.id).where(TalentShortlist.name == name)
        ).scalar_one_or_none()
        if duplicate is not None:
            raise TalentValidationError(f"A shortlist named '{name}' already exists.")
        shortlist = TalentShortlist(
            owner_user_id=owner.id,
            name=name,
            description=description,
            club_id=club_id,
        )
        self.session.add(shortlist)
        self.session.flush()
        return shortlist

    def get_owned_shortlist(self, shortlist_id: str, *, owner: User) -> TalentShortlist:
        shortlist = self.session.get(TalentShortlist, shortlist_id)
        if shortlist is None:
            raise TalentNotFoundError(f"No shortlist exists with id '{shortlist_id}'.")
        if shortlist.owner_user_id != owner.id:
            # Deliberately the same error a missing list produces: existence of
            # another scout's shortlist is not this caller's to learn.
            raise TalentNotFoundError(f"No shortlist exists with id '{shortlist_id}'.")
        return shortlist

    def update_shortlist(
        self,
        shortlist_id: str,
        *,
        owner: User,
        name: str | None = None,
        description: str | None = None,
        is_archived: bool | None = None,
    ) -> TalentShortlist:
        shortlist = self.get_owned_shortlist(shortlist_id, owner=owner)
        if name is not None:
            shortlist.name = name
        if description is not None:
            shortlist.description = description
        if is_archived is not None:
            shortlist.is_archived = is_archived
        self.session.flush()
        return shortlist

    def delete_shortlist(self, shortlist_id: str, *, owner: User) -> None:
        shortlist = self.get_owned_shortlist(shortlist_id, owner=owner)
        self.session.delete(shortlist)
        self.session.flush()

    def add_shortlist_entry(
        self,
        shortlist_id: str,
        *,
        owner: User,
        player_id: str,
        status: str,
        priority: int = 0,
        note: str | None = None,
    ) -> TalentShortlistEntry:
        shortlist = self.get_owned_shortlist(shortlist_id, owner=owner)
        profile = self.get_profile_row(player_id)
        scope = privacy.resolve_viewer_scope(profile, owner)
        if not privacy.can_view_profile(profile, scope):
            raise TalentNotFoundError(f"No published talent profile exists for player '{player_id}'.")

        entry_count = int(
            self.session.execute(
                select(func.count())
                .select_from(TalentShortlistEntry)
                .where(TalentShortlistEntry.shortlist_id == shortlist.id)
            ).scalar_one()
        )
        if entry_count >= SHORTLIST_MAX_ENTRIES:
            raise TalentValidationError(f"Shortlist entry limit reached ({SHORTLIST_MAX_ENTRIES}).")
        existing = self.session.execute(
            select(TalentShortlistEntry)
            .where(TalentShortlistEntry.shortlist_id == shortlist.id)
            .where(TalentShortlistEntry.player_id == player_id)
        ).scalar_one_or_none()
        if existing is not None:
            raise TalentValidationError("That talent is already on this shortlist.")

        entry = TalentShortlistEntry(
            shortlist_id=shortlist.id,
            player_id=player_id,
            added_by_user_id=owner.id,
            status=status,
            priority=priority,
            note=note,
            score_at_add=round(float(profile.composite_score or 0.0), 2),
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def update_shortlist_entry(
        self,
        shortlist_id: str,
        entry_id: str,
        *,
        owner: User,
        status: str | None = None,
        priority: int | None = None,
        note: str | None = None,
    ) -> TalentShortlistEntry:
        shortlist = self.get_owned_shortlist(shortlist_id, owner=owner)
        entry = self.session.get(TalentShortlistEntry, entry_id)
        if entry is None or entry.shortlist_id != shortlist.id:
            raise TalentNotFoundError(f"No shortlist entry exists with id '{entry_id}'.")
        if status is not None:
            entry.status = status
        if priority is not None:
            entry.priority = priority
        if note is not None:
            entry.note = note
        self.session.flush()
        return entry

    def remove_shortlist_entry(self, shortlist_id: str, entry_id: str, *, owner: User) -> None:
        shortlist = self.get_owned_shortlist(shortlist_id, owner=owner)
        entry = self.session.get(TalentShortlistEntry, entry_id)
        if entry is None or entry.shortlist_id != shortlist.id:
            raise TalentNotFoundError(f"No shortlist entry exists with id '{entry_id}'.")
        self.session.delete(entry)
        self.session.flush()

    def shortlist_view(self, shortlist: TalentShortlist, *, viewer: User) -> dict[str, Any]:
        return self._shortlist_view(shortlist, include_entries=True, viewer=viewer)

    def _shortlist_view(
        self,
        shortlist: TalentShortlist,
        *,
        include_entries: bool,
        viewer: User,
    ) -> dict[str, Any]:
        entries = sorted(
            shortlist.entries,
            key=lambda item: (-int(item.priority or 0), item.created_at, item.id),
        )
        payload: dict[str, Any] = {
            "id": shortlist.id,
            "name": shortlist.name,
            "description": shortlist.description,
            "club_id": shortlist.club_id,
            "is_archived": bool(shortlist.is_archived),
            "entry_count": len(entries),
            "entries": [],
        }
        if not include_entries:
            return payload

        player_ids = [entry.player_id for entry in entries]
        profiles = {
            row.player_id: row
            for row in self.session.execute(
                select(TalentProfile).where(TalentProfile.player_id.in_(player_ids or [""]))
            ).scalars()
        }
        for entry in entries:
            profile = profiles.get(entry.player_id)
            talent = None
            if profile is not None:
                scope = privacy.resolve_viewer_scope(profile, viewer)
                if privacy.can_view_profile(profile, scope):
                    talent = privacy.project_search_result(profile, scope=scope)
            payload["entries"].append(
                {
                    "id": entry.id,
                    "player_id": entry.player_id,
                    "status": entry.status,
                    "priority": int(entry.priority or 0),
                    "note": entry.note,
                    "score_at_add": entry.score_at_add,
                    "added_at": entry.created_at.isoformat(),
                    "talent": talent,
                }
            )
        return payload


__all__ = [
    "TalentAccessDeniedError",
    "TalentExchangeError",
    "TalentExchangeService",
    "TalentNotFoundError",
    "TalentSearchPage",
    "TalentValidationError",
    "build_membership_index",
    "derive_competition_level",
]
