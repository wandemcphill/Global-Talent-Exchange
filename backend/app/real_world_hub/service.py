from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService, RealPlayerNormalizedProfile
from app.models.notification_record import NotificationRecord
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.models.real_world_hub import (
    RealClub,
    RealCompetition,
    RealDataProvider,
    RealDataSyncJob,
    RealDataSyncStatus,
    RealPlayer,
    RealityMode,
    RealityModeSetting,
)
from app.schemas.real_player_ingestion import RealPlayerSeedInput
from app.real_world_hub.schemas import RealClubSeedRequest, RealCompetitionSeedRequest, RealWorldSyncRequest

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class RealWorldHubError(ValueError):
    pass


class RealWorldHubNotFoundError(RealWorldHubError):
    pass


class RealWorldHubValidationError(RealWorldHubError):
    pass


@dataclass(slots=True)
class RealWorldHubService:
    session: Session
    normalization_service: RealPlayerNormalizationService = field(default_factory=RealPlayerNormalizationService)

    def list_providers(self) -> list[RealDataProvider]:
        stmt = select(RealDataProvider).order_by(RealDataProvider.name.asc())
        return list(self.session.scalars(stmt).all())

    def upsert_provider(
        self,
        *,
        name: str,
        api_endpoint: str,
        refresh_interval: int,
        normalization_profile_version: str,
        is_active: bool,
        metadata_json: dict[str, Any],
    ) -> RealDataProvider:
        provider = self.session.scalar(select(RealDataProvider).where(RealDataProvider.name == name))
        if provider is None:
            provider = RealDataProvider(name=name)
            self.session.add(provider)
        provider.api_endpoint = api_endpoint
        provider.refresh_interval = refresh_interval
        provider.normalization_profile_version = normalization_profile_version
        provider.is_active = is_active
        provider.metadata_json = dict(metadata_json or {})
        self.session.flush()
        return provider

    def get_provider(self, provider_id: str) -> RealDataProvider:
        provider = self.session.get(RealDataProvider, provider_id)
        if provider is None:
            raise RealWorldHubNotFoundError("Real-world data provider was not found.")
        return provider

    def get_or_create_settings(self, *, user_id: str) -> RealityModeSetting:
        settings = self.session.scalar(select(RealityModeSetting).where(RealityModeSetting.owner_user_id == user_id))
        if settings is None:
            settings = RealityModeSetting(owner_user_id=user_id)
            self.session.add(settings)
            self.session.flush()
        return settings

    def upsert_settings(
        self,
        *,
        user_id: str,
        mode: RealityMode,
        enable_real_world_events: bool,
        enable_soft_injuries: bool,
        enable_transfer_mirror: bool,
        metadata_json: dict[str, Any],
    ) -> RealityModeSetting:
        settings = self.get_or_create_settings(user_id=user_id)
        settings.mode = mode.value
        settings.enable_real_world_events = enable_real_world_events
        settings.enable_soft_injuries = enable_soft_injuries
        settings.enable_transfer_mirror = enable_transfer_mirror
        settings.metadata_json = dict(metadata_json or {})
        self.session.flush()
        return settings

    def list_real_players(
        self,
        *,
        provider_id: str | None = None,
        limit: int = 50,
    ) -> list[RealPlayer]:
        stmt = select(RealPlayer).order_by(RealPlayer.real_world_rating.desc(), RealPlayer.last_updated.desc())
        if provider_id:
            stmt = stmt.where(RealPlayer.provider_id == provider_id)
        return list(self.session.scalars(stmt.limit(limit)).all())

    def get_real_player(self, real_player_id: str) -> RealPlayer:
        player = self.session.get(RealPlayer, real_player_id)
        if player is None:
            raise RealWorldHubNotFoundError("Real-world player projection was not found.")
        return player

    def normalize_player_seed(
        self,
        payload: RealPlayerSeedInput,
        *,
        as_of: datetime | None = None,
    ) -> dict[str, Any]:
        normalized = self.normalization_service.normalize(payload, as_of=as_of or datetime.now(UTC))
        real_world_rating = self._fairness_rating(
            (normalized.real_life_performance_score * 0.45)
            + (normalized.role_tier_signal * 0.30)
            + (normalized.market_prestige_signal * 0.25)
        )
        attributes = self._normalize_attributes(normalized)
        normalized_rating = self._fairness_rating(sum(attributes.values()) / len(attributes))
        soft_injury_impact = self._soft_injury_impact(payload.injury_status)
        normalized_rating = self._fairness_rating(normalized_rating - soft_injury_impact)
        return {
            "normalized": normalized,
            "real_world_rating": real_world_rating,
            "normalized_rating": normalized_rating,
            "attributes_json": attributes,
            "soft_injury_impact": soft_injury_impact,
        }

    def sync_provider(
        self,
        *,
        provider_id: str,
        payload: RealWorldSyncRequest | None = None,
    ) -> RealDataSyncJob:
        provider = self.get_provider(provider_id)
        effective_payload = payload or RealWorldSyncRequest(use_existing_profiles=True)
        if not effective_payload.players and not effective_payload.clubs and not effective_payload.competitions:
            effective_payload = RealWorldSyncRequest(use_existing_profiles=True, as_of=effective_payload.as_of)
        effective_as_of = self._normalize_datetime(effective_payload.as_of)

        job = RealDataSyncJob(
            provider_id=provider.id,
            status=RealDataSyncStatus.RUNNING.value,
            started_at=effective_as_of or datetime.now(UTC),
        )
        self.session.add(job)
        self.session.flush()

        try:
            projected_payload = self._build_projection_payload(provider, effective_payload)
            competitions = self._upsert_competitions(provider=provider, competitions=projected_payload.competitions)
            clubs = self._upsert_clubs(provider=provider, clubs=projected_payload.clubs, competitions=competitions)
            players_upserted = self._upsert_players(
                provider=provider,
                players=projected_payload.players,
                clubs=clubs,
                competitions=competitions,
                as_of=self._normalize_datetime(projected_payload.as_of),
            )
            total_entities = len(projected_payload.competitions) + len(projected_payload.clubs) + len(projected_payload.players)
            provider.last_sync_at = self._normalize_datetime(projected_payload.as_of) or datetime.now(UTC)
            job.status = RealDataSyncStatus.COMPLETED.value
            job.completed_at = datetime.now(UTC)
            job.entities_seen = total_entities
            job.entities_upserted = len(competitions) + len(clubs) + players_upserted
            job.summary_json = {
                "competitions": len(competitions),
                "clubs": len(clubs),
                "players": players_upserted,
                "used_existing_profiles": projected_payload.use_existing_profiles,
            }
            self._publish_notification(
                user_id=None,
                template_key="REAL_DATA_UPDATED",
                message=f"Real-world data sync completed for {provider.name}.",
                resource_type="real_data_provider",
                resource_id=provider.id,
                metadata_json={"job_id": job.id, "provider_id": provider.id, **job.summary_json},
            )
            self.session.flush()
            return job
        except Exception as exc:
            job.status = RealDataSyncStatus.FAILED.value
            job.completed_at = datetime.now(UTC)
            job.entities_failed = max(job.entities_failed, 1)
            job.error_message = str(exc)
            self.session.flush()
            raise

    def sync_due_providers(self) -> int:
        now = datetime.now(UTC)
        synced_count = 0
        providers = list(self.session.scalars(select(RealDataProvider).where(RealDataProvider.is_active.is_(True))).all())
        for provider in providers:
            last_sync_at = self._normalize_datetime(provider.last_sync_at)
            if last_sync_at is not None:
                delta = now - last_sync_at
                if delta.total_seconds() < int(provider.refresh_interval):
                    continue
            self.sync_provider(provider_id=provider.id)
            synced_count += 1
        return synced_count

    def list_hybrid_players(
        self,
        *,
        user_id: str | None = None,
        mode: RealityMode | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        resolved_mode = self._resolve_mode(user_id=user_id, mode=mode)
        stmt = select(Player, Country).outerjoin(Country, Country.id == Player.country_id).order_by(Player.full_name.asc()).limit(limit)
        if resolved_mode == RealityMode.PURE_REGEN:
            stmt = stmt.where(Player.is_real_player.is_(False))
        elif resolved_mode == RealityMode.REAL_ONLY:
            stmt = stmt.where(Player.is_real_player.is_(True))

        rows = self.session.execute(stmt).all()
        items: list[dict[str, Any]] = []
        for player, country in rows:
            projection = self.session.scalar(
                select(RealPlayer)
                .where(RealPlayer.gtex_player_id == player.id)
                .order_by(RealPlayer.last_updated.desc())
            )
            provider = self.session.get(RealDataProvider, projection.provider_id) if projection is not None else None
            items.append(
                {
                    "player_id": player.id,
                    "name": player.full_name,
                    "player_origin": "real_player" if player.is_real_player else "regen_player",
                    "nationality": country.name if country is not None else None,
                    "position": player.position,
                    "source_provider": provider.name if provider is not None else None,
                    "real_world_rating": projection.real_world_rating if projection is not None else None,
                    "normalized_rating": projection.normalized_rating if projection is not None else None,
                    "mode": resolved_mode,
                    "eligible": True,
                    "metadata_json": {
                        "fairness_cap": 92.0,
                        "uses_real_projection": projection is not None,
                    },
                }
            )
        return items

    def _build_projection_payload(
        self,
        provider: RealDataProvider,
        payload: RealWorldSyncRequest,
    ) -> RealWorldSyncRequest:
        if not payload.use_existing_profiles:
            return payload

        competition_map: dict[str, RealCompetitionSeedRequest] = {}
        club_map: dict[str, RealClubSeedRequest] = {}
        players: list[RealPlayerSeedInput] = []
        stmt = (
            select(RealPlayerProfile, RealPlayerSourceLink)
            .join(RealPlayerSourceLink, RealPlayerSourceLink.id == RealPlayerProfile.source_link_id)
            .where(RealPlayerProfile.source_name == provider.name)
            .order_by(RealPlayerProfile.source_last_refreshed_at.desc().nullslast())
        )
        for profile, source_link in self.session.execute(stmt).all():
            competition_key = self._stable_key(profile.current_league_name or "unknown-competition")
            club_key = self._stable_key(profile.current_club_name or "unknown-club")
            if profile.current_league_name:
                competition_map.setdefault(
                    competition_key,
                    RealCompetitionSeedRequest(
                        external_key=competition_key,
                        name=profile.current_league_name,
                        competition_type=profile.competition_level or "league",
                        metadata_json={"projection_source": "real_player_profiles"},
                    ),
                )
            if profile.current_club_name:
                club_map.setdefault(
                    club_key,
                    RealClubSeedRequest(
                        external_key=club_key,
                        competition_external_key=competition_key if profile.current_league_name else None,
                        name=profile.current_club_name,
                        metadata_json={"projection_source": "real_player_profiles"},
                    ),
                )
            players.append(
                RealPlayerSeedInput(
                    source_name=provider.name,
                    source_player_key=source_link.source_player_key,
                    canonical_name=profile.canonical_name,
                    display_name=profile.canonical_name,
                    known_aliases=list(profile.known_aliases_json or []),
                    nationality=profile.nationality,
                    date_of_birth=profile.date_of_birth,
                    birth_year=profile.birth_year,
                    dominant_foot=profile.dominant_foot,
                    primary_position=profile.primary_position,
                    secondary_positions=list(profile.secondary_positions_json or []),
                    current_real_world_club=profile.current_club_name,
                    current_real_world_club_key=club_key if profile.current_club_name else None,
                    current_real_world_league=profile.current_league_name,
                    current_real_world_league_key=competition_key if profile.current_league_name else None,
                    competition_level=profile.competition_level,
                    appearances=profile.appearances,
                    minutes_played=profile.minutes_played,
                    goals=profile.goals,
                    assists=profile.assists,
                    clean_sheets=profile.clean_sheets,
                    injury_status=profile.injury_status,
                    height_cm=profile.height_cm,
                    weight_kg=profile.weight_kg,
                    current_market_reference_value=profile.current_market_reference_value,
                    market_reference_currency=profile.market_reference_currency,
                    source_last_refreshed_at=profile.source_last_refreshed_at,
                    identity_confidence_score=source_link.identity_confidence_score,
                    is_verified_real_player=source_link.is_verified_real_player,
                    real_player_tier=(profile.metadata_json or {}).get("real_player_tier"),
                )
            )
        return RealWorldSyncRequest(
            competitions=list(competition_map.values()),
            clubs=list(club_map.values()),
            players=players,
            use_existing_profiles=True,
            as_of=payload.as_of,
        )

    def _upsert_competitions(
        self,
        *,
        provider: RealDataProvider,
        competitions: list[RealCompetitionSeedRequest],
    ) -> dict[str, RealCompetition]:
        items: dict[str, RealCompetition] = {}
        for payload in competitions:
            item = self.session.scalar(
                select(RealCompetition).where(
                    RealCompetition.provider_id == provider.id,
                    RealCompetition.external_key == payload.external_key,
                )
            )
            if item is None:
                item = RealCompetition(provider_id=provider.id, external_key=payload.external_key)
                self.session.add(item)
            item.name = payload.name
            item.country_name = payload.country_name
            item.competition_type = payload.competition_type
            item.gtex_competition_id = payload.gtex_competition_id
            item.metadata_json = dict(payload.metadata_json or {})
            item.last_updated = datetime.now(UTC)
            items[payload.external_key] = item
        self.session.flush()
        return items

    def _upsert_clubs(
        self,
        *,
        provider: RealDataProvider,
        clubs: list[RealClubSeedRequest],
        competitions: dict[str, RealCompetition],
    ) -> dict[str, RealClub]:
        items: dict[str, RealClub] = {}
        for payload in clubs:
            item = self.session.scalar(
                select(RealClub).where(
                    RealClub.provider_id == provider.id,
                    RealClub.external_key == payload.external_key,
                )
            )
            if item is None:
                item = RealClub(provider_id=provider.id, external_key=payload.external_key)
                self.session.add(item)
            competition = competitions.get(payload.competition_external_key or "")
            item.competition_id = competition.id if competition is not None else None
            item.name = payload.name
            item.country_name = payload.country_name
            item.gtex_club_id = payload.gtex_club_id
            item.metadata_json = dict(payload.metadata_json or {})
            item.last_updated = datetime.now(UTC)
            items[payload.external_key] = item
        self.session.flush()
        return items

    def _upsert_players(
        self,
        *,
        provider: RealDataProvider,
        players: list[RealPlayerSeedInput],
        clubs: dict[str, RealClub],
        competitions: dict[str, RealCompetition],
        as_of: datetime | None,
    ) -> int:
        count = 0
        for payload in players:
            normalized_payload = self.normalize_player_seed(payload, as_of=as_of)
            gtex_player_id = self._resolve_gtex_player_id(provider_name=provider.name, payload=payload)
            item = self.session.scalar(
                select(RealPlayer).where(
                    RealPlayer.provider_id == provider.id,
                    RealPlayer.external_key == payload.source_player_key,
                )
            )
            if item is None:
                item = RealPlayer(provider_id=provider.id, external_key=payload.source_player_key)
                self.session.add(item)
            club = clubs.get(payload.current_real_world_club_key or "")
            competition = competitions.get(payload.current_real_world_league_key or "")
            item.gtex_player_id = gtex_player_id
            item.real_club_id = club.id if club is not None else None
            item.real_competition_id = competition.id if competition is not None else None
            item.name = payload.display_name or payload.canonical_name
            item.nationality = payload.nationality
            item.position = normalized_payload["normalized"].primary_position
            item.player_origin = "real_player"
            item.real_world_rating = normalized_payload["real_world_rating"]
            item.normalized_rating = normalized_payload["normalized_rating"]
            item.attributes_json = normalized_payload["attributes_json"]
            item.injury_status = payload.injury_status
            item.soft_injury_impact = normalized_payload["soft_injury_impact"]
            item.metadata_json = {
                "normalization_profile_version": normalized_payload["normalized"].normalization_profile_version,
                "normalized_signals": normalized_payload["normalized"].normalized_signals(),
                "competitive_fairness": {
                    "cap": 92.0,
                    "floor": 35.0,
                },
            }
            item.last_updated = as_of or datetime.now(UTC)
            count += 1
        self.session.flush()
        return count

    def _resolve_gtex_player_id(self, *, provider_name: str, payload: RealPlayerSeedInput) -> str | None:
        source_link = self.session.scalar(
            select(RealPlayerSourceLink).where(
                RealPlayerSourceLink.source_name == provider_name,
                RealPlayerSourceLink.source_player_key == payload.source_player_key,
            )
        )
        if source_link is not None:
            return source_link.gtex_player_id
        player = self.session.scalar(
            select(Player).where(
                func.lower(Player.full_name) == payload.canonical_name.casefold(),
                Player.is_real_player.is_(True),
            )
        )
        return player.id if player is not None else None

    def _resolve_mode(self, *, user_id: str | None, mode: RealityMode | None) -> RealityMode:
        if mode is not None:
            return mode
        if user_id is None:
            return RealityMode.HYBRID
        settings = self.session.scalar(select(RealityModeSetting).where(RealityModeSetting.owner_user_id == user_id))
        if settings is None:
            return RealityMode.HYBRID
        return RealityMode(settings.mode)

    def _normalize_attributes(self, normalized: RealPlayerNormalizedProfile) -> dict[str, float]:
        performance = normalized.real_life_performance_score
        role = normalized.role_tier_signal
        prestige = normalized.market_prestige_signal
        age = normalized.age_trajectory_score
        club = normalized.club_strength_score
        form = normalized.form_signal
        primary_position = normalized.primary_position.lower()
        finishing_boost = 8.0 if "striker" in primary_position or "winger" in primary_position else 0.0
        defending_boost = 12.0 if "back" in primary_position or "goalkeeper" in primary_position else 0.0
        playmaking_boost = 10.0 if "midfielder" in primary_position else 0.0
        goalkeeping_value = self._fairness_rating((performance * 0.60) + (role * 0.40)) if "goalkeeper" in primary_position else 18.0
        return {
            "pace": self._fairness_rating((age * 0.55) + (form * 0.45)),
            "technique": self._fairness_rating((performance * 0.55) + (club * 0.45)),
            "passing": self._fairness_rating((performance * 0.45) + (role * 0.35) + playmaking_boost),
            "defending": self._fairness_rating((club * 0.40) + (role * 0.35) + defending_boost),
            "physical": self._fairness_rating((club * 0.35) + (age * 0.35) + (role * 0.30)),
            "finishing": self._fairness_rating((performance * 0.50) + (prestige * 0.20) + finishing_boost),
            "mentality": self._fairness_rating((performance * 0.35) + (role * 0.35) + (prestige * 0.30)),
            "goalkeeping": goalkeeping_value,
        }

    def _fairness_rating(self, value: float) -> float:
        return round(min(max(float(value), 35.0), 92.0), 2)

    def _soft_injury_impact(self, injury_status: str | None) -> float:
        if not injury_status:
            return 0.0
        normalized = injury_status.strip().lower()
        if normalized in {"fit", "available", "healthy", "cleared", "none"}:
            return 0.0
        return 4.0

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _publish_notification(
        self,
        *,
        user_id: str | None,
        template_key: str,
        message: str,
        resource_type: str,
        resource_id: str,
        metadata_json: dict[str, Any],
    ) -> None:
        self.session.add(
            NotificationRecord(
                user_id=user_id,
                topic="real_world",
                template_key=template_key,
                resource_type=resource_type,
                resource_id=resource_id,
                message=message[:255],
                metadata_json=dict(metadata_json or {}),
            )
        )

    @staticmethod
    def _stable_key(value: str) -> str:
        normalized = _SLUG_RE.sub("-", (value or "").strip().lower()).strip("-")
        return normalized or "unknown"


__all__ = [
    "RealWorldHubError",
    "RealWorldHubNotFoundError",
    "RealWorldHubService",
    "RealWorldHubValidationError",
]
