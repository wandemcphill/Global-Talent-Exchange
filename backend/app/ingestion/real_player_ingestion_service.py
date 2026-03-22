from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.ingestion.models import (
    Club,
    Competition,
    Country,
    InjuryStatus,
    MarketSignal,
    Player,
    PlayerClubTenure,
    PlayerSeasonStat,
    PlayerVerification,
    VerificationStatus,
)
from app.ingestion.normalizers import clean_name, slugify
from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService, RealPlayerNormalizedProfile
from app.ingestion.real_player_signal_adapter import RealPlayerSignalAdapter
from app.models.player_cards import PlayerMarketValueSnapshot, PlayerStatsSnapshot
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.players.service import PlayerSummaryProjector
from app.schemas.real_player_ingestion import (
    RealPlayerIngestionItemResult,
    RealPlayerIngestionMode,
    RealPlayerIngestionRequest,
    RealPlayerIngestionResult,
    RealPlayerSeedInput,
)
from app.services.squad_assignment_service import SquadAssignmentService
from app.value_engine.read_models import PlayerValueSnapshotRecord
from app.value_engine.service import IngestionValueEngineBridge

from .real_player_identity_matcher import RealPlayerIdentityMatcher


class RealPlayerIngestionError(ValueError):
    pass


class RealPlayerPricingError(RealPlayerIngestionError):
    pass


@dataclass(frozen=True, slots=True)
class StagedRealPlayer:
    source_name: str
    source_player_key: str
    gtex_player_id: str
    action: str
    identity_confidence_score: float
    profile_id: str
    normalized: RealPlayerNormalizedProfile


@dataclass(slots=True)
class RealPlayerIngestionService:
    session_factory: sessionmaker[Session]
    value_engine_bridge: IngestionValueEngineBridge | None = None
    settings: Settings = field(default_factory=get_settings)
    identity_matcher: RealPlayerIdentityMatcher = field(default_factory=RealPlayerIdentityMatcher)
    normalization_service: RealPlayerNormalizationService = field(default_factory=RealPlayerNormalizationService)
    signal_adapter: RealPlayerSignalAdapter = field(default_factory=RealPlayerSignalAdapter)
    summary_projector: PlayerSummaryProjector = field(default_factory=PlayerSummaryProjector)
    squad_assignment_service: SquadAssignmentService = field(default_factory=SquadAssignmentService)

    def __post_init__(self) -> None:
        if self.value_engine_bridge is None:
            self.value_engine_bridge = IngestionValueEngineBridge(
                session_factory=self.session_factory,
                settings=self.settings,
                summary_projector=self.summary_projector,
                default_lookback_days=self.settings.value_snapshot_lookback_days,
            )

    def ingest(self, request: RealPlayerIngestionRequest) -> RealPlayerIngestionResult:
        if self.value_engine_bridge is None:
            raise RealPlayerIngestionError("Authoritative value engine bridge is not configured.")
        if not request.players:
            raise RealPlayerIngestionError("At least one real player payload is required.")

        as_of = request.as_of or datetime.now(UTC)
        ingestion_batch_id = request.ingestion_batch_id or f"real-player-{uuid4().hex[:12]}"
        staged_players = self._stage_players(
            request=request,
            ingestion_batch_id=ingestion_batch_id,
            as_of=as_of,
        )
        player_ids = [item.gtex_player_id for item in staged_players]
        snapshots = self.value_engine_bridge.run(
            as_of=as_of,
            lookback_days=request.lookback_days,
            player_ids=player_ids,
            run_type="manual_rebuild",
            triggered_by="real_player_ingestion_service",
            notes={
                "ingestion_mode": request.mode,
                "ingestion_batch_id": ingestion_batch_id,
                "ingestion_source_version": request.ingestion_source_version,
                "player_count": len(player_ids),
            },
        )
        snapshot_player_ids = {snapshot.player_id for snapshot in snapshots}
        missing_snapshot_ids = [player_id for player_id in player_ids if player_id not in snapshot_player_ids]
        if missing_snapshot_ids:
            raise RealPlayerPricingError(
                "Authoritative value engine produced no snapshots for "
                f"{missing_snapshot_ids}. No fallback pricing path was used."
            )

        item_results = self._finalize_batch(
            staged_players=staged_players,
            request=request,
            ingestion_batch_id=ingestion_batch_id,
            as_of=as_of,
        )
        return RealPlayerIngestionResult(
            mode=request.mode,
            ingestion_batch_id=ingestion_batch_id,
            ingestion_source_version=request.ingestion_source_version,
            as_of=as_of,
            players_processed=len(item_results),
            players_created=sum(1 for item in item_results if item.action == "created"),
            players_updated=sum(1 for item in item_results if item.action == "updated"),
            authoritative_snapshots_seeded=len(item_results),
            player_ids=player_ids,
            results=item_results,
        )

    def _stage_players(
        self,
        *,
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
    ) -> list[StagedRealPlayer]:
        staged_players: list[StagedRealPlayer] = []
        ordered_payloads = sorted(request.players, key=lambda item: (item.source_name, item.source_player_key))
        with self.session_factory() as session:
            for payload in ordered_payloads:
                match = self.identity_matcher.match(session, payload)
                if request.mode == RealPlayerIngestionMode.REFRESH_EXISTING.value and match.action != "source_link":
                    raise RealPlayerIngestionError(
                        f"refresh_existing requires an existing source link for '{payload.canonical_name}'."
                    )
                normalized = self.normalization_service.normalize(payload, as_of=as_of)
                country = self._resolve_country(session, payload)
                competition = self._resolve_competition(session, payload, normalized, as_of=as_of)
                club = self._resolve_club(session, payload, normalized, country=country, competition=competition, as_of=as_of)
                player, action, was_real_player = self._upsert_player(
                    session,
                    payload=payload,
                    normalized=normalized,
                    country=country,
                    competition=competition,
                    club=club,
                    match=match,
                    as_of=as_of,
                )
                if action == "updated" and not was_real_player:
                    self._purge_seeded_supporting_records(session, player=player, source_name=payload.source_name)
                self._upsert_verification(
                    session,
                    player=player,
                    source_name=payload.source_name,
                    confidence_score=match.confidence_score,
                    is_verified_real_player=payload.is_verified_real_player,
                    as_of=as_of,
                )
                source_link = self._upsert_source_link(
                    session,
                    player=player,
                    payload=payload,
                    normalized=normalized,
                    confidence_score=match.confidence_score,
                )
                profile = self._upsert_profile(
                    session,
                    player=player,
                    source_link=source_link,
                    payload=payload,
                    normalized=normalized,
                    ingestion_batch_id=ingestion_batch_id,
                    ingestion_source_version=request.ingestion_source_version,
                    as_of=as_of,
                )
                self._upsert_tenure(session, player=player, payload=payload, club=club, as_of=as_of)
                self._upsert_season_stat(
                    session,
                    player=player,
                    payload=payload,
                    normalized=normalized,
                    club=club,
                    competition=competition,
                    as_of=as_of,
                )
                self._upsert_injury_status(session, player=player, payload=payload)
                self._upsert_market_signals(session, player=player, normalized=normalized, as_of=as_of)
                staged_players.append(
                    StagedRealPlayer(
                        source_name=payload.source_name,
                        source_player_key=payload.source_player_key,
                        gtex_player_id=player.id,
                        action=action,
                        identity_confidence_score=match.confidence_score,
                        profile_id=profile.id,
                        normalized=normalized,
                    )
                )
            session.commit()
        return staged_players

    def _finalize_batch(
        self,
        *,
        staged_players: list[StagedRealPlayer],
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
    ) -> list[RealPlayerIngestionItemResult]:
        player_ids = [item.gtex_player_id for item in staged_players]
        with self.session_factory() as session:
            player_records = {
                record.player_id: record
                for record in session.scalars(
                    select(PlayerValueSnapshotRecord).where(
                        PlayerValueSnapshotRecord.player_id.in_(tuple(player_ids)),
                        PlayerValueSnapshotRecord.as_of == as_of,
                        PlayerValueSnapshotRecord.snapshot_type == "intraday",
                    )
                )
            }
            summaries = {
                summary.player_id: summary
                for summary in session.scalars(
                    select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(tuple(player_ids)))
                )
            }

            item_results: list[RealPlayerIngestionItemResult] = []
            for staged in staged_players:
                player = session.get(Player, staged.gtex_player_id)
                if player is None:
                    raise RealPlayerIngestionError(f"Player '{staged.gtex_player_id}' disappeared before projection.")
                snapshot_record = player_records.get(staged.gtex_player_id)
                if snapshot_record is None:
                    raise RealPlayerPricingError(
                        f"Authoritative value snapshot record was not found for player '{staged.gtex_player_id}'."
                    )
                summary = summaries.get(staged.gtex_player_id)
                if summary is None:
                    raise RealPlayerPricingError(
                        f"Player summary projection was not produced for player '{staged.gtex_player_id}'."
                    )
                profile = session.get(RealPlayerProfile, staged.profile_id)
                if profile is None:
                    raise RealPlayerIngestionError(f"Real player profile '{staged.profile_id}' was not found.")

                assignment_profile = self.squad_assignment_service.build_profile(
                    player_id=player.id,
                    primary_position=player.position,
                    normalized_position=player.normalized_position,
                    preferred_foot=player.preferred_foot,
                    age=staged.normalized.age_years or 24,
                    current_club_id=player.current_club_id,
                )
                avatar_seed_token, avatar_dna_seed = self._avatar_seed(
                    source_name=staged.source_name,
                    source_player_key=staged.source_player_key,
                    canonical_name=staged.normalized.canonical_name,
                )
                self._upsert_stats_snapshot(
                    session,
                    player=player,
                    staged=staged,
                    assignment_profile=assignment_profile,
                    as_of=as_of,
                )
                self._upsert_market_value_snapshot(
                    session,
                    player_id=player.id,
                    snapshot_record=snapshot_record,
                    as_of=as_of,
                )
                self._enrich_summary(
                    player=player,
                    summary=summary,
                    staged=staged,
                    assignment_profile=assignment_profile,
                    avatar_seed_token=avatar_seed_token,
                    avatar_dna_seed=avatar_dna_seed,
                    snapshot_record=snapshot_record,
                    request=request,
                    ingestion_batch_id=ingestion_batch_id,
                    as_of=as_of,
                )
                profile.pricing_snapshot_id = snapshot_record.id

                item_results.append(
                    RealPlayerIngestionItemResult(
                        source_name=staged.source_name,
                        source_player_key=staged.source_player_key,
                        gtex_player_id=player.id,
                        action=staged.action,
                        pricing_snapshot_id=snapshot_record.id,
                        authoritative_price_credits=float(snapshot_record.target_credits),
                        identity_confidence_score=staged.identity_confidence_score,
                    )
                )
            session.commit()
        return item_results

    def _resolve_country(self, session: Session, payload: RealPlayerSeedInput) -> Country | None:
        if not payload.nationality and not payload.nationality_code:
            return None
        normalized_code = (payload.nationality_code or "").upper() or None
        normalized_name = clean_name(payload.nationality) or normalized_code
        country = None
        if normalized_code:
            country = session.scalar(
                select(Country).where(
                    (Country.alpha2_code == normalized_code)
                    | (Country.alpha3_code == normalized_code)
                    | (Country.fifa_code == normalized_code)
                )
            )
        if country is None and normalized_name:
            country = session.scalar(select(Country).where(Country.name == normalized_name))
        if country is not None:
            return country

        country = Country(
            source_provider=payload.source_name,
            provider_external_id=normalized_code or slugify(normalized_name),
            name=normalized_name or "Unknown",
            alpha2_code=normalized_code if normalized_code and len(normalized_code) == 2 else None,
            alpha3_code=normalized_code if normalized_code and len(normalized_code) == 3 else None,
            fifa_code=normalized_code if normalized_code and len(normalized_code) == 3 else None,
            last_synced_at=datetime.now(UTC),
        )
        session.add(country)
        session.flush()
        return country

    def _resolve_competition(
        self,
        session: Session,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        *,
        as_of: datetime,
    ) -> Competition | None:
        if not payload.current_real_world_league:
            return None
        provider_external_id = payload.current_real_world_league_key or slugify(payload.current_real_world_league)
        competition = session.scalar(
            select(Competition).where(
                Competition.source_provider == payload.source_name,
                Competition.provider_external_id == provider_external_id,
            )
        )
        if competition is None:
            competition = Competition(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                name=clean_name(payload.current_real_world_league) or payload.current_real_world_league,
                slug=slugify(payload.current_real_world_league),
                competition_type="league",
                format_type="real_world",
                is_major=normalized.competition_level in {"elite", "major", "continental"},
                is_tradable=True,
                competition_strength=normalized.competition_strength_multiplier,
                last_synced_at=as_of,
            )
            session.add(competition)
            session.flush()
        else:
            competition.name = clean_name(payload.current_real_world_league) or payload.current_real_world_league
            competition.slug = slugify(payload.current_real_world_league)
            competition.competition_strength = normalized.competition_strength_multiplier
            competition.is_major = normalized.competition_level in {"elite", "major", "continental"}
            competition.last_synced_at = as_of
        return competition

    def _resolve_club(
        self,
        session: Session,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        *,
        country: Country | None,
        competition: Competition | None,
        as_of: datetime,
    ) -> Club | None:
        if not payload.current_real_world_club:
            return None
        provider_external_id = payload.current_real_world_club_key or slugify(payload.current_real_world_club)
        club = session.scalar(
            select(Club).where(
                Club.source_provider == payload.source_name,
                Club.provider_external_id == provider_external_id,
            )
        )
        if club is None:
            club = Club(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                country_id=country.id if country is not None else None,
                current_competition_id=competition.id if competition is not None else None,
                name=clean_name(payload.current_real_world_club) or payload.current_real_world_club,
                slug=slugify(payload.current_real_world_club),
                short_name=(clean_name(payload.current_real_world_club) or payload.current_real_world_club)[:80],
                popularity_score=normalized.club_strength_score,
                is_tradable=True,
                last_synced_at=as_of,
            )
            session.add(club)
            session.flush()
        else:
            club.country_id = country.id if country is not None else club.country_id
            club.current_competition_id = competition.id if competition is not None else None
            club.name = clean_name(payload.current_real_world_club) or payload.current_real_world_club
            club.slug = slugify(payload.current_real_world_club)
            club.short_name = (clean_name(payload.current_real_world_club) or payload.current_real_world_club)[:80]
            club.popularity_score = normalized.club_strength_score
            club.last_synced_at = as_of
        return club

    def _upsert_player(
        self,
        session: Session,
        *,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        country: Country | None,
        competition: Competition | None,
        club: Club | None,
        match,
        as_of: datetime,
    ) -> tuple[Player, str, bool]:
        player: Player | None = session.get(Player, match.player_id) if match.player_id is not None else None
        was_real_player = bool(player.is_real_player) if player is not None else False
        if player is None:
            player = Player(
                source_provider=payload.source_name,
                provider_external_id=payload.source_player_key,
            )
            session.add(player)
            action = "created"
        else:
            action = "updated"

        first_name, last_name = self._split_name(payload.canonical_name)
        player.full_name = payload.canonical_name
        player.first_name = first_name
        player.last_name = last_name
        player.short_name = self._short_name(payload.canonical_name)
        player.country_id = country.id if country is not None else None
        player.current_club_id = club.id if club is not None else None
        player.current_competition_id = competition.id if competition is not None else None
        player.position = normalized.primary_position
        player.normalized_position = normalized.normalized_position
        player.date_of_birth = payload.date_of_birth
        player.height_cm = payload.height_cm
        player.weight_kg = payload.weight_kg
        player.preferred_foot = payload.dominant_foot
        player.market_value_eur = normalized.reference_market_value_eur
        player.profile_completeness_score = normalized.profile_completeness_score
        player.is_tradable = True
        player.is_real_player = True
        player.real_player_tier = normalized.real_player_tier
        player.canonical_display_name = payload.canonical_name
        player.identity_confidence_score = match.confidence_score
        player.source_last_refreshed_at = payload.source_last_refreshed_at or as_of
        player.real_world_club_name = payload.current_real_world_club
        player.real_world_league_name = payload.current_real_world_league
        player.current_market_reference_value = payload.current_market_reference_value
        player.market_reference_currency = payload.market_reference_currency
        player.normalization_profile_version = normalized.normalization_profile_version
        player.last_synced_at = as_of
        session.flush()
        return player, action, was_real_player

    def _upsert_verification(
        self,
        session: Session,
        *,
        player: Player,
        source_name: str,
        confidence_score: float,
        is_verified_real_player: bool,
        as_of: datetime,
    ) -> None:
        verification = session.scalar(select(PlayerVerification).where(PlayerVerification.player_id == player.id))
        if verification is None:
            verification = PlayerVerification(player_id=player.id)
            session.add(verification)
        verification.status = (
            VerificationStatus.VERIFIED.value if is_verified_real_player else VerificationStatus.PENDING.value
        )
        verification.verification_source = source_name
        verification.verified_at = as_of if is_verified_real_player else None
        verification.expires_at = None
        verification.confidence_score = confidence_score
        verification.rights_confirmed = is_verified_real_player
        verification.reviewer_notes = f"Real-player ingestion via {source_name}. Avatar-safe stylized profile only."

    def _upsert_source_link(
        self,
        session: Session,
        *,
        player: Player,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        confidence_score: float,
    ) -> RealPlayerSourceLink:
        source_link = session.scalar(
            select(RealPlayerSourceLink).where(
                RealPlayerSourceLink.source_name == payload.source_name,
                RealPlayerSourceLink.source_player_key == payload.source_player_key,
            )
        )
        if source_link is None:
            source_link = RealPlayerSourceLink(
                gtex_player_id=player.id,
                source_name=payload.source_name,
                source_player_key=payload.source_player_key,
                canonical_name=payload.canonical_name,
            )
            session.add(source_link)
        source_link.gtex_player_id = player.id
        source_link.canonical_name = payload.canonical_name
        source_link.known_aliases_json = list(payload.known_aliases)
        source_link.nationality = payload.nationality
        source_link.date_of_birth = payload.date_of_birth
        source_link.birth_year = payload.birth_year
        source_link.primary_position = normalized.primary_position
        source_link.secondary_positions_json = list(normalized.secondary_positions)
        source_link.current_real_world_club = payload.current_real_world_club
        source_link.identity_confidence_score = confidence_score
        source_link.is_verified_real_player = payload.is_verified_real_player
        source_link.verification_state = "verified" if payload.is_verified_real_player else "pending"
        session.flush()
        return source_link

    def _upsert_profile(
        self,
        session: Session,
        *,
        player: Player,
        source_link: RealPlayerSourceLink,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        ingestion_batch_id: str,
        ingestion_source_version: str | None,
        as_of: datetime,
    ) -> RealPlayerProfile:
        profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.source_link_id == source_link.id))
        if profile is None:
            profile = RealPlayerProfile(
                gtex_player_id=player.id,
                source_link_id=source_link.id,
                source_name=payload.source_name,
                source_player_key=payload.source_player_key,
                canonical_name=payload.canonical_name,
            )
            session.add(profile)
        profile.gtex_player_id = player.id
        profile.source_name = payload.source_name
        profile.source_player_key = payload.source_player_key
        profile.canonical_name = payload.canonical_name
        profile.known_aliases_json = list(payload.known_aliases)
        profile.nationality = payload.nationality
        profile.birth_year = payload.birth_year
        profile.date_of_birth = payload.date_of_birth
        profile.dominant_foot = payload.dominant_foot
        profile.primary_position = normalized.primary_position
        profile.secondary_positions_json = list(normalized.secondary_positions)
        profile.height_cm = payload.height_cm
        profile.weight_kg = payload.weight_kg
        profile.current_club_name = payload.current_real_world_club
        profile.current_league_name = payload.current_real_world_league
        profile.competition_level = normalized.competition_level
        profile.appearances = normalized.appearances
        profile.minutes_played = normalized.minutes_played
        profile.goals = normalized.goals
        profile.assists = normalized.assists
        profile.clean_sheets = normalized.clean_sheets
        profile.injury_status = payload.injury_status
        profile.current_market_reference_value = payload.current_market_reference_value
        profile.market_reference_currency = payload.market_reference_currency
        profile.source_last_refreshed_at = payload.source_last_refreshed_at or as_of
        profile.normalization_profile_version = normalized.normalization_profile_version
        profile.normalized_signals_json = normalized.normalized_signals()
        profile.ingestion_batch_id = ingestion_batch_id
        profile.ingestion_source_version = ingestion_source_version
        profile.metadata_json = {
            "avatar_safe": True,
            "no_real_photos": True,
            "real_player_tier": normalized.real_player_tier,
            "source_name": payload.source_name,
            "source_player_key": payload.source_player_key,
        }
        profile.notes = "Normalized real-player profile. External reference value is an input signal only."
        session.flush()
        return profile

    def _upsert_tenure(
        self,
        session: Session,
        *,
        player: Player,
        payload: RealPlayerSeedInput,
        club: Club | None,
        as_of: datetime,
    ) -> None:
        provider_external_id = f"{payload.source_player_key}:current_tenure"
        tenure = session.scalar(
            select(PlayerClubTenure).where(
                PlayerClubTenure.source_provider == payload.source_name,
                PlayerClubTenure.provider_external_id == provider_external_id,
            )
        )
        if club is None:
            if tenure is not None:
                session.delete(tenure)
            return
        if tenure is None:
            tenure = PlayerClubTenure(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                player_id=player.id,
                club_id=club.id,
            )
            session.add(tenure)
        tenure.player_id = player.id
        tenure.club_id = club.id
        tenure.season_id = None
        tenure.start_date = None
        tenure.end_date = None
        tenure.squad_number = None
        tenure.is_current = True
        tenure.updated_at = as_of

    def _upsert_season_stat(
        self,
        session: Session,
        *,
        player: Player,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        club: Club | None,
        competition: Competition | None,
        as_of: datetime,
    ) -> None:
        provider_external_id = f"{payload.source_player_key}:current_profile"
        stat = session.scalar(
            select(PlayerSeasonStat).where(
                PlayerSeasonStat.source_provider == payload.source_name,
                PlayerSeasonStat.provider_external_id == provider_external_id,
            )
        )
        if stat is None:
            stat = PlayerSeasonStat(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                player_id=player.id,
            )
            session.add(stat)
        stat.player_id = player.id
        stat.club_id = club.id if club is not None else None
        stat.competition_id = competition.id if competition is not None else None
        stat.season_id = None
        stat.appearances = normalized.appearances
        stat.starts = max(min(normalized.appearances, normalized.appearances - 2), 0)
        stat.minutes = normalized.minutes_played
        stat.goals = normalized.goals
        stat.assists = normalized.assists
        stat.clean_sheets = normalized.clean_sheets
        stat.saves = 0 if normalized.primary_position == "Goalkeeper" else None
        stat.average_rating = round(6.0 + (normalized.form_signal / 35.0), 2)
        stat.updated_at = as_of

    def _upsert_injury_status(self, session: Session, *, player: Player, payload: RealPlayerSeedInput) -> None:
        provider_external_id = f"{payload.source_player_key}:injury"
        injury = session.scalar(
            select(InjuryStatus).where(
                InjuryStatus.source_provider == payload.source_name,
                InjuryStatus.provider_external_id == provider_external_id,
            )
        )
        normalized_status = (payload.injury_status or "").strip().lower()
        if normalized_status in {"", "fit", "available", "none"}:
            if injury is not None:
                session.delete(injury)
            return
        if injury is None:
            injury = InjuryStatus(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                player_id=player.id,
            )
            session.add(injury)
        injury.player_id = player.id
        injury.club_id = player.current_club_id
        injury.status = payload.injury_status or "injured"
        injury.detail = payload.injury_status
        injury.expected_return_at = None

    def _upsert_market_signals(
        self,
        session: Session,
        *,
        player: Player,
        normalized: RealPlayerNormalizedProfile,
        as_of: datetime,
    ) -> None:
        bundle = self.signal_adapter.build_signal_bundle(normalized)
        for signal_type, score in bundle.market_signals.items():
            provider_external_id = f"{normalized.source_player_key}:signal:{signal_type}"
            signal = session.scalar(
                select(MarketSignal).where(
                    MarketSignal.source_provider == normalized.source_name,
                    MarketSignal.provider_external_id == provider_external_id,
                )
            )
            if signal is None:
                signal = MarketSignal(
                    source_provider=normalized.source_name,
                    provider_external_id=provider_external_id,
                    player_id=player.id,
                    signal_type=signal_type,
                    score=score,
                    as_of=as_of,
                )
                session.add(signal)
            signal.player_id = player.id
            signal.signal_type = signal_type
            signal.score = score
            signal.as_of = as_of
            signal.notes = json.dumps({**bundle.notes, "signal_type": signal_type}, sort_keys=True)

    def _purge_seeded_supporting_records(self, session: Session, *, player: Player, source_name: str) -> None:
        session.execute(
            delete(MarketSignal).where(
                MarketSignal.player_id == player.id,
                MarketSignal.source_provider != source_name,
                MarketSignal.notes.like('%"seeded": true%'),
            )
        )
        session.execute(
            delete(PlayerSeasonStat).where(
                PlayerSeasonStat.player_id == player.id,
                PlayerSeasonStat.source_provider != source_name,
                PlayerSeasonStat.provider_external_id.like("%:season%"),
            )
        )
        session.execute(
            delete(PlayerStatsSnapshot).where(
                PlayerStatsSnapshot.player_id == player.id,
                PlayerStatsSnapshot.source_type == "seed_snapshot",
            )
        )

    def _upsert_stats_snapshot(
        self,
        session: Session,
        *,
        player: Player,
        staged: StagedRealPlayer,
        assignment_profile,
        as_of: datetime,
    ) -> None:
        session.execute(
            delete(PlayerStatsSnapshot).where(
                PlayerStatsSnapshot.player_id == player.id,
                PlayerStatsSnapshot.as_of == as_of,
                PlayerStatsSnapshot.source_type == "real_player_ingestion",
            )
        )
        session.add(
            PlayerStatsSnapshot(
                player_id=player.id,
                as_of=as_of,
                competition_id=player.current_competition_id,
                season_id=None,
                source_type="real_player_ingestion",
                stats_json={
                    "appearances": staged.normalized.appearances,
                    "starts": max(min(staged.normalized.appearances, staged.normalized.appearances - 2), 0),
                    "minutes": staged.normalized.minutes_played,
                    "goals": staged.normalized.goals,
                    "assists": staged.normalized.assists,
                    "clean_sheets": staged.normalized.clean_sheets,
                    "average_rating": round(6.0 + (staged.normalized.form_signal / 35.0), 2),
                    "primary_position": staged.normalized.primary_position,
                    "secondary_positions": list(staged.normalized.secondary_positions),
                    "formation_slots": list(assignment_profile.formation_slots),
                    "role_archetype": assignment_profile.role_archetype,
                    "source_type": "real_player_ingestion",
                },
            )
        )

    def _upsert_market_value_snapshot(
        self,
        session: Session,
        *,
        player_id: str,
        snapshot_record: PlayerValueSnapshotRecord,
        as_of: datetime,
    ) -> None:
        session.execute(
            delete(PlayerMarketValueSnapshot).where(
                PlayerMarketValueSnapshot.player_id == player_id,
                PlayerMarketValueSnapshot.as_of == as_of,
            )
        )
        session.add(
            PlayerMarketValueSnapshot(
                player_id=player_id,
                as_of=as_of,
                last_trade_price_credits=None,
                avg_trade_price_credits=snapshot_record.target_credits,
                volume_24h=0,
                listing_floor_price_credits=snapshot_record.target_credits,
                listing_count=0,
                high_24h_price_credits=snapshot_record.target_credits,
                low_24h_price_credits=snapshot_record.target_credits,
                metadata_json={
                    "source": "authoritative_value_engine",
                    "authoritative_snapshot_id": snapshot_record.id,
                    "snapshot_type": snapshot_record.snapshot_type,
                    "real_player_ingestion": True,
                },
            )
        )

    def _enrich_summary(
        self,
        *,
        player: Player,
        summary: PlayerSummaryReadModel,
        staged: StagedRealPlayer,
        assignment_profile,
        avatar_seed_token: str,
        avatar_dna_seed: str,
        snapshot_record: PlayerValueSnapshotRecord,
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
    ) -> None:
        summary.current_club_name = summary.current_club_name or player.real_world_club_name
        summary.current_competition_name = summary.current_competition_name or player.real_world_league_name
        summary_payload = dict(summary.summary_json) if isinstance(summary.summary_json, dict) else {}
        summary_payload.update(
            {
                "source_type": "real_player",
                "ingestion_mode": request.mode,
                "primary_position": staged.normalized.primary_position,
                "secondary_positions": list(staged.normalized.secondary_positions),
                "dominant_foot": player.preferred_foot,
                "role_archetype": assignment_profile.role_archetype,
                "formation_slots": list(assignment_profile.formation_slots),
                "formation_ready": assignment_profile.formation_ready,
                "squad_eligibility": assignment_profile.squad_eligibility,
                "avatar_seed_token": avatar_seed_token,
                "avatar_dna_seed": avatar_dna_seed,
                "club_assignment": {
                    "status": "free_agent" if player.current_club_id is None else "club_assigned",
                    "current_club_id": player.current_club_id,
                    "current_club_name": summary.current_club_name,
                    "current_competition_id": player.current_competition_id,
                    "current_competition_name": summary.current_competition_name,
                },
                "nationality": {
                    "name": getattr(player.country, "name", None) or staged.normalized.nationality,
                    "alpha2_code": getattr(player.country, "alpha2_code", None) or staged.normalized.nationality_code,
                    "alpha3_code": getattr(player.country, "alpha3_code", None),
                    "fifa_code": getattr(player.country, "fifa_code", None),
                },
                "market_visibility": {
                    "eligible": bool(player.is_tradable and snapshot_record.target_credits > 0),
                    "status": "visible" if player.is_tradable and snapshot_record.target_credits > 0 else "hidden",
                    "surface_flags": [
                        "player_summary",
                        "market_listing",
                        "player_card",
                        "club_squad",
                        "lineup_builder",
                        "match_viewer",
                    ],
                },
                "real_player_profile": {
                    "is_real_player": True,
                    "is_verified_real_player": True,
                    "real_player_tier": player.real_player_tier,
                    "canonical_display_name": player.canonical_display_name or player.full_name,
                    "identity_confidence_score": player.identity_confidence_score,
                    "source_name": staged.source_name,
                    "source_player_key": staged.source_player_key,
                    "source_last_refreshed_at": (
                        player.source_last_refreshed_at.isoformat() if player.source_last_refreshed_at is not None else None
                    ),
                    "real_world_club_name": player.real_world_club_name,
                    "real_world_league_name": player.real_world_league_name,
                    "current_market_reference_value": player.current_market_reference_value,
                    "market_reference_currency": player.market_reference_currency,
                    "normalization_profile_version": player.normalization_profile_version,
                    "normalized_signals": staged.normalized.normalized_signals(),
                    "pricing_snapshot_id": snapshot_record.id,
                },
                "ingestion_metadata": {
                    "ingestion_batch_id": ingestion_batch_id,
                    "ingestion_source_version": request.ingestion_source_version,
                    "authoritative_snapshot_id": snapshot_record.id,
                    "as_of": as_of.isoformat(),
                },
            }
        )
        summary.summary_json = summary_payload

    def _split_name(self, canonical_name: str) -> tuple[str | None, str | None]:
        parts = canonical_name.split()
        if not parts:
            return None, None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], " ".join(parts[1:])

    def _short_name(self, canonical_name: str) -> str:
        parts = canonical_name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}. {' '.join(parts[1:])}"[:80]
        return canonical_name[:80]

    def _avatar_seed(self, *, source_name: str, source_player_key: str, canonical_name: str) -> tuple[str, str]:
        digest = hashlib.sha256(f"{source_name}|{source_player_key}|{canonical_name}|avatar".encode("utf-8")).hexdigest()
        return digest[:16], "-".join(digest[offset:offset + 8] for offset in range(0, 32, 8))


__all__ = [
    "RealPlayerIngestionError",
    "RealPlayerIngestionService",
    "RealPlayerPricingError",
]
