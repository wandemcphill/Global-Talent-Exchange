from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.cache import HotPathCache
from app.core.cache import CacheBackend, NullCacheBackend
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.events import DomainEvent, EventPublisher
from app.football_universe.service import FootballUniverseService
from app.live_matches.highlights import SmartHighlightService
from app.live_matches.schemas import LiveMatchSnapshotView, LiveMatchStateView, LiveMatchStreamEventView
from app.live_matches.service import LiveMatchHub, ensure_live_match_hub
from app.manager_duels.schemas import ManagerDuelCreateRequest, ManagerDuelLeaderboardEntryView, ManagerDuelView
from app.match_engine.schemas import MatchCompetitionContextInput, MatchSimulationRequest
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.match_engine.simulation.models import MatchCompetitionType
from app.models.manager_duel import ManagerDuel, ManagerDuelProfile
from app.models.manager_market import ManagerCatalogEntry, ManagerHolding, ManagerTeamAssignment
from app.models.user import User, UserRole
from app.services.commentary_service import MatchCommentaryService


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ManagerDuelError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _ResolvedManagerSelection:
    manager_key: str
    manager_id: str
    manager_name: str
    source_type: str
    owner_user_id: str
    asset_id: str | None
    profile: dict[str, object]
    strength_score: int


@dataclass(slots=True)
class ManagerDuelService:
    session_factory: sessionmaker[Session]
    event_publisher: EventPublisher
    live_hub: LiveMatchHub
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    match_service: MatchSimulationService = field(default_factory=MatchSimulationService)
    team_factory: SyntheticSquadFactory = field(default_factory=SyntheticSquadFactory)
    highlight_service: SmartHighlightService | None = None
    leaderboard_cache_ttl_seconds: int = 120
    _hot_cache: HotPathCache = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.team_factory.session_factory = self.session_factory
        self._hot_cache = HotPathCache(self.cache_backend)
        if self.highlight_service is None:
            self.highlight_service = SmartHighlightService(self.session_factory)

    def create_and_start_duel(self, *, actor: User, payload: ManagerDuelCreateRequest) -> ManagerDuelView:
        if payload.home_user_id == payload.away_user_id:
            raise ManagerDuelError("Manager duels require two different users.")
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN} and actor.id not in {payload.home_user_id, payload.away_user_id}:
            raise ManagerDuelError("You can only create a duel involving your own account.")

        with self.session_factory() as session:
            home_user = session.get(User, payload.home_user_id)
            away_user = session.get(User, payload.away_user_id)
            if home_user is None or away_user is None:
                raise ManagerDuelError("Both duel users must exist.")

            home_selection = self._resolve_selection(
                session,
                actor=actor,
                user=home_user,
                explicit_asset_id=payload.home_manager_asset_id,
                self_managed=payload.home_self_managed,
            )
            away_selection = self._resolve_selection(
                session,
                actor=actor,
                user=away_user,
                explicit_asset_id=payload.away_manager_asset_id,
                self_managed=payload.away_self_managed,
            )

            duel = ManagerDuel(
                competition_type="manager_duel",
                status="live",
                home_user_id=home_user.id,
                away_user_id=away_user.id,
                home_manager_id=home_selection.manager_id,
                away_manager_id=away_selection.manager_id,
                home_manager_name=home_selection.manager_name,
                away_manager_name=away_selection.manager_name,
                home_manager_source=home_selection.source_type,
                away_manager_source=away_selection.source_type,
                home_manager_asset_id=home_selection.asset_id,
                away_manager_asset_id=away_selection.asset_id,
                controller_home="manager",
                controller_away="manager",
                user_control_enabled=False,
                started_at=utcnow(),
                metadata_json={
                    "home_manager_key": home_selection.manager_key,
                    "away_manager_key": away_selection.manager_key,
                },
            )
            session.add(duel)
            session.flush()

            request = self._build_match_request(
                duel_id=duel.id,
                simulation_seed=payload.simulation_seed,
                home_selection=home_selection,
                away_selection=away_selection,
            )
            replay_payload = self.match_service.build_replay_payload(request)
            commentary_service = MatchCommentaryService(session)
            replay_payload = commentary_service.apply_to_replay_payload(
                replay_payload,
                request=request,
            )
            commentary_service.persist_replay_commentary(
                duel.id,
                replay_payload,
                audience_user_ids=(home_user.id, away_user.id),
            )
            FootballUniverseService(session).persist_match_universe(request=request, replay_payload=replay_payload)
            highlights = self.highlight_service.persist_from_replay_payload(duel.id, replay_payload, session=session)
            duel.metadata_json = {
                **(duel.metadata_json or {}),
                "replay_payload": replay_payload.model_dump(mode="json"),
                "highlight_preview": [item.model_dump(mode="json") for item in highlights],
                "controllers": {
                    "home": "manager",
                    "away": "manager",
                },
                "human_or_real_manager_only": True,
            }
            session.commit()
            session.refresh(duel)

        self.live_hub.start_stream(
            duel.id,
            replay_payload,
            read_only=True,
            on_batch=self._handle_live_batch,
            on_complete=self._complete_duel,
        )
        self._notify_participants(
            duel_id=duel.id,
            home_user_id=duel.home_user_id,
            away_user_id=duel.away_user_id,
            template_key="LIVE_MATCH_STARTED",
            message=f"{duel.home_manager_name} vs {duel.away_manager_name} is live.",
            metadata={"competition_type": "manager_duel"},
        )
        return self.get_duel(duel.id)

    def get_duel(self, duel_id: str) -> ManagerDuelView:
        with self.session_factory() as session:
            duel = session.get(ManagerDuel, duel_id)
            if duel is None:
                raise ManagerDuelError("Manager duel was not found.")
            live_state = self.live_hub.get_state(duel_id)
            return self._to_view(duel, live_state=live_state)

    def get_leaderboard(self, *, limit: int = 25) -> list[ManagerDuelLeaderboardEntryView]:
        cached_entries = self._hot_cache.get_global_leaderboard(limit=limit)
        if cached_entries:
            resolved_entries: list[ManagerDuelLeaderboardEntryView] = []
            for item in cached_entries:
                try:
                    resolved_entries.append(ManagerDuelLeaderboardEntryView.model_validate(item))
                except Exception:
                    resolved_entries.clear()
                    break
            if resolved_entries:
                return resolved_entries
        entries = self._load_leaderboard_entries(limit=limit)
        self._cache_leaderboard(entries)
        return entries

    def _load_leaderboard_entries(self, *, limit: int) -> list[ManagerDuelLeaderboardEntryView]:
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(ManagerDuelProfile)
                    .order_by(
                        ManagerDuelProfile.duel_wins.desc(),
                        ManagerDuelProfile.reputation_score.desc(),
                        ManagerDuelProfile.updated_at.asc(),
                    )
                    .limit(limit)
                ).all()
            )
        entries: list[ManagerDuelLeaderboardEntryView] = []
        for index, row in enumerate(rows, start=1):
            win_rate = (row.duel_wins / row.matches_played) if row.matches_played else 0.0
            entries.append(
                ManagerDuelLeaderboardEntryView(
                    manager_id=row.manager_id,
                    manager_name=row.display_name,
                    manager_source=row.source_type,
                    duel_wins=row.duel_wins,
                    duel_draws=row.duel_draws,
                    duel_losses=row.duel_losses,
                    matches_played=row.matches_played,
                    win_rate=round(win_rate, 4),
                    reputation_score=round(row.reputation_score, 2),
                    leaderboard_rank=index,
                )
            )
        return entries

    def _cache_leaderboard(self, entries: list[ManagerDuelLeaderboardEntryView]) -> None:
        self._hot_cache.replace_global_leaderboard(
            [
                (
                    entry.manager_id,
                    float((entry.duel_wins * 10000) + entry.reputation_score),
                    entry.model_dump(mode="json"),
                )
                for entry in entries
            ],
            ttl_seconds=self.leaderboard_cache_ttl_seconds,
        )

    def _build_match_request(
        self,
        *,
        duel_id: str,
        simulation_seed: int | None,
        home_selection: _ResolvedManagerSelection,
        away_selection: _ResolvedManagerSelection,
    ) -> MatchSimulationRequest:
        home_team = self.team_factory.build_team(
            team_id=f"duel:{home_selection.owner_user_id}",
            team_name=f"{home_selection.manager_name} XI",
            base_overall=home_selection.strength_score,
            manager_profile_override=home_selection.profile,
        )
        away_team = self.team_factory.build_team(
            team_id=f"duel:{away_selection.owner_user_id}",
            team_name=f"{away_selection.manager_name} XI",
            base_overall=away_selection.strength_score,
            manager_profile_override=away_selection.profile,
        )
        return MatchSimulationRequest(
            match_id=duel_id,
            seed=simulation_seed,
            competition=MatchCompetitionContextInput(
                competition_type=MatchCompetitionType.MANAGER_DUEL,
                stage="manager_duel",
                is_final=False,
                requires_winner=False,
            ),
            home_team=home_team,
            away_team=away_team,
            tactical_changes=[],
        )

    def _resolve_selection(
        self,
        session: Session,
        *,
        actor: User,
        user: User,
        explicit_asset_id: str | None,
        self_managed: bool,
    ) -> _ResolvedManagerSelection:
        if self_managed:
            if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN} and actor.id != user.id:
                raise ManagerDuelError("Only a user or an admin can enter that user as self-managed.")
            profile = {
                "display_name": user.display_name or user.username,
                "mentality": "balanced",
                "tactics": ["manual_management"],
                "traits": ["self_owned_manager"],
                "rarity": "self_owned",
                "philosophy_summary": "Human-managed dugout control.",
                "substitution_tendency": "balanced_substitution",
            }
            strength = self._manager_strength_score(profile)
            return _ResolvedManagerSelection(
                manager_key=f"self:{user.id}",
                manager_id=user.id,
                manager_name=user.display_name or user.username,
                source_type="self",
                owner_user_id=user.id,
                asset_id=None,
                profile=profile,
                strength_score=strength,
            )

        asset_id = explicit_asset_id or self._assigned_manager_asset_id(session, user.id)
        if asset_id is None:
            raise ManagerDuelError(f"{user.username} must use a hired manager or self-manage this duel.")
        holding = session.scalar(select(ManagerHolding).where(ManagerHolding.asset_id == asset_id))
        if holding is None or holding.owner_user_id != user.id or holding.status != "owned":
            raise ManagerDuelError("Selected hired manager is not owned by the specified user.")
        manager = session.scalar(select(ManagerCatalogEntry).where(ManagerCatalogEntry.manager_id == holding.manager_id))
        if manager is None:
            raise ManagerDuelError("Selected hired manager could not be loaded.")
        profile = {
            "display_name": manager.display_name,
            "mentality": manager.mentality,
            "tactics": list(manager.tactics or []),
            "traits": list(manager.traits or []),
            "rarity": manager.rarity,
            "philosophy_summary": manager.philosophy_summary,
            "substitution_tendency": manager.substitution_tendency,
        }
        strength = self._manager_strength_score(profile)
        return _ResolvedManagerSelection(
            manager_key=f"hired:{manager.manager_id}",
            manager_id=manager.manager_id,
            manager_name=manager.display_name,
            source_type="hired",
            owner_user_id=user.id,
            asset_id=holding.asset_id,
            profile=profile,
            strength_score=strength,
        )

    def _assigned_manager_asset_id(self, session: Session, user_id: str) -> str | None:
        assignment = session.scalar(select(ManagerTeamAssignment).where(ManagerTeamAssignment.user_id == user_id))
        return assignment.main_manager_asset_id if assignment is not None else None

    def _manager_strength_score(self, profile: dict[str, object]) -> int:
        rarity = str(profile.get("rarity", "common")).lower()
        tactics = list(profile.get("tactics") or [])
        traits = list(profile.get("traits") or [])
        mentality = str(profile.get("mentality", "balanced")).lower()
        rarity_bonus = {
            "common": 0,
            "rare": 4,
            "elite": 8,
            "legendary": 12,
            "self_owned": 3,
        }.get(rarity, 2)
        mentality_bonus = {
            "defensive": 2,
            "balanced": 4,
            "attacking": 6,
            "technical": 5,
            "pressing": 6,
            "pragmatic": 3,
            "possession": 5,
        }.get(mentality, 3)
        score = 66 + rarity_bonus + mentality_bonus + (min(len(tactics), 4) * 2) + min(len(traits), 4)
        return max(58, min(92, score))

    def _handle_live_batch(
        self,
        duel_id: str,
        events: list[LiveMatchStreamEventView],
        snapshot: LiveMatchSnapshotView,
    ) -> None:
        notable = next((event for event in events if event.event_type in {"goal", "card"}), None)
        if notable is None:
            return
        with self.session_factory() as session:
            duel = session.get(ManagerDuel, duel_id)
            if duel is None:
                return
        description = notable.metadata.get("description") or f"{notable.minute}' {notable.event_type}"
        self._notify_participants(
            duel_id=duel_id,
            home_user_id=duel.home_user_id,
            away_user_id=duel.away_user_id,
            template_key="LIVE_MATCH_UPDATE",
            message=str(description),
            metadata={
                "minute": notable.minute,
                "event_type": notable.event_type,
                "score": snapshot.score.model_dump(mode="json"),
            },
        )

    def _complete_duel(self, duel_id: str) -> None:
        with self.session_factory() as session:
            duel = session.get(ManagerDuel, duel_id)
            if duel is None or duel.status == "completed":
                return
            replay_data = (duel.metadata_json or {}).get("replay_payload")
            if not isinstance(replay_data, dict):
                return
            summary = replay_data.get("summary") or {}
            duel.home_score = int(summary.get("home_score", 0) or 0)
            duel.away_score = int(summary.get("away_score", 0) or 0)
            winner_team_id = str(summary.get("winner_team_id") or "")
            if winner_team_id == f"duel:{duel.home_user_id}":
                duel.winner_manager_id = duel.home_manager_id
                duel.winner_user_id = duel.home_user_id
            elif winner_team_id == f"duel:{duel.away_user_id}":
                duel.winner_manager_id = duel.away_manager_id
                duel.winner_user_id = duel.away_user_id
            else:
                duel.winner_manager_id = None
                duel.winner_user_id = None
            duel.completed_at = utcnow()
            duel.status = "completed"

            home_delta, away_delta = self._resolve_reputation_delta(
                session,
                duel=duel,
                home_manager_key=str((duel.metadata_json or {}).get("home_manager_key")),
                away_manager_key=str((duel.metadata_json or {}).get("away_manager_key")),
            )
            duel.reputation_delta_home = home_delta
            duel.reputation_delta_away = away_delta

            self._upsert_profile(
                session,
                manager_key=str((duel.metadata_json or {}).get("home_manager_key")),
                manager_id=duel.home_manager_id,
                display_name=duel.home_manager_name,
                source_type=duel.home_manager_source,
                owner_user_id=duel.home_user_id,
                delta=home_delta,
                outcome=self._outcome(duel.home_score, duel.away_score),
            )
            self._upsert_profile(
                session,
                manager_key=str((duel.metadata_json or {}).get("away_manager_key")),
                manager_id=duel.away_manager_id,
                display_name=duel.away_manager_name,
                source_type=duel.away_manager_source,
                owner_user_id=duel.away_user_id,
                delta=away_delta,
                outcome=self._outcome(duel.away_score, duel.home_score),
            )
            session.commit()
        self._cache_leaderboard(self._load_leaderboard_entries(limit=100))

        self._notify_participants(
            duel_id=duel_id,
            home_user_id=duel.home_user_id,
            away_user_id=duel.away_user_id,
            template_key="HIGHLIGHTS_READY",
            message=f"Highlights are ready for {duel.home_manager_name} vs {duel.away_manager_name}.",
            metadata={"competition_type": "manager_duel"},
        )

    def _resolve_reputation_delta(
        self,
        session: Session,
        *,
        duel: ManagerDuel,
        home_manager_key: str,
        away_manager_key: str,
    ) -> tuple[float, float]:
        home_profile = session.scalar(select(ManagerDuelProfile).where(ManagerDuelProfile.manager_key == home_manager_key))
        away_profile = session.scalar(select(ManagerDuelProfile).where(ManagerDuelProfile.manager_key == away_manager_key))
        home_reputation = home_profile.reputation_score if home_profile is not None else 100.0
        away_reputation = away_profile.reputation_score if away_profile is not None else 100.0
        if duel.home_score > duel.away_score:
            base = 12 + max(0, (away_reputation - home_reputation) / 25)
            return round(base, 2), round(-max(4.0, base / 2), 2)
        if duel.away_score > duel.home_score:
            base = 12 + max(0, (home_reputation - away_reputation) / 25)
            return round(-max(4.0, base / 2), 2), round(base, 2)
        return 4.0, 4.0

    def _upsert_profile(
        self,
        session: Session,
        *,
        manager_key: str,
        manager_id: str,
        display_name: str,
        source_type: str,
        owner_user_id: str,
        delta: float,
        outcome: str,
    ) -> None:
        profile = session.scalar(select(ManagerDuelProfile).where(ManagerDuelProfile.manager_key == manager_key))
        if profile is None:
            profile = ManagerDuelProfile(
                manager_key=manager_key,
                manager_id=manager_id,
                display_name=display_name,
                source_type=source_type,
                owner_user_id=owner_user_id,
                reputation_score=100.0,
                duel_wins=0,
                duel_draws=0,
                duel_losses=0,
                matches_played=0,
            )
            session.add(profile)
        profile.owner_user_id = owner_user_id
        profile.display_name = display_name
        profile.reputation_score = round(float(profile.reputation_score or 100.0) + delta, 2)
        profile.matches_played = int(profile.matches_played or 0) + 1
        if outcome == "win":
            profile.duel_wins = int(profile.duel_wins or 0) + 1
        elif outcome == "loss":
            profile.duel_losses = int(profile.duel_losses or 0) + 1
        else:
            profile.duel_draws = int(profile.duel_draws or 0) + 1
        profile.last_duel_at = utcnow()

    @staticmethod
    def _outcome(goals_for: int, goals_against: int) -> str:
        if goals_for > goals_against:
            return "win"
        if goals_for < goals_against:
            return "loss"
        return "draw"

    def _notify_participants(
        self,
        *,
        duel_id: str,
        home_user_id: str,
        away_user_id: str,
        template_key: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        for user_id in {home_user_id, away_user_id}:
            self.event_publisher.publish(
                DomainEvent(
                    name="competition.notification",
                    payload={
                        "user_id": user_id,
                        "template_key": template_key,
                        "message": message,
                        "resource_id": duel_id,
                        "fixture_id": duel_id,
                        "competition_id": duel_id,
                        "competition_type": "manager_duel",
                        **(metadata or {}),
                    },
                )
            )

    @staticmethod
    def _to_view(duel: ManagerDuel, *, live_state: LiveMatchStateView | None) -> ManagerDuelView:
        return ManagerDuelView(
            id=duel.id,
            competition_type=duel.competition_type,
            status=duel.status,
            home_user_id=duel.home_user_id,
            away_user_id=duel.away_user_id,
            home_manager_id=duel.home_manager_id,
            away_manager_id=duel.away_manager_id,
            home_manager_name=duel.home_manager_name,
            away_manager_name=duel.away_manager_name,
            home_manager_source=duel.home_manager_source,
            away_manager_source=duel.away_manager_source,
            controller_home=duel.controller_home,
            controller_away=duel.controller_away,
            user_control_enabled=duel.user_control_enabled,
            home_score=duel.home_score,
            away_score=duel.away_score,
            winner_manager_id=duel.winner_manager_id,
            winner_user_id=duel.winner_user_id,
            reputation_delta_home=duel.reputation_delta_home,
            reputation_delta_away=duel.reputation_delta_away,
            started_at=duel.started_at,
            completed_at=duel.completed_at,
            live_state=live_state,
        )


def ensure_manager_duel_service(app: FastAPI) -> ManagerDuelService:
    service = getattr(app.state, "manager_duel_service", None)
    if service is None:
        service = ManagerDuelService(
            session_factory=app.state.session_factory,
            event_publisher=app.state.event_publisher,
            live_hub=ensure_live_match_hub(app),
            cache_backend=getattr(app.state, "cache_backend", NullCacheBackend()),
        )
        app.state.manager_duel_service = service
        return service
    service.session_factory = app.state.session_factory
    service.event_publisher = app.state.event_publisher
    service.live_hub = ensure_live_match_hub(app)
    service.cache_backend = getattr(app.state, "cache_backend", service.cache_backend)
    service._hot_cache = HotPathCache(service.cache_backend)
    service.team_factory.session_factory = app.state.session_factory
    if service.highlight_service is None:
        service.highlight_service = SmartHighlightService(app.state.session_factory)
    else:
        service.highlight_service.session_factory = app.state.session_factory
    return service


__all__ = ["ManagerDuelError", "ManagerDuelService", "ensure_manager_duel_service"]
