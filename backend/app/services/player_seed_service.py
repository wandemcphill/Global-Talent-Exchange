from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.ingestion.models import Player, PlayerClubTenure
from app.ingestion.player_universe_seeder import VerifiedPlayerUniverseSeeder
from app.players.service import PlayerSummaryProjector
from app.schemas.player_seed import PlayerSeedMode, PlayerSeedRequest, PlayerSeedResult
from app.services.player_generation_service import PlayerGenerationService
from app.value_engine.read_models import PlayerValueSnapshotRecord
from app.value_engine.service import IngestionValueEngineBridge


class PlayerSeedError(ValueError):
    pass


@dataclass(slots=True)
class PlayerSeedService:
    session_factory: sessionmaker[Session]
    value_engine_bridge: IngestionValueEngineBridge | None = None
    settings: Settings = field(default_factory=get_settings)
    generation_service: PlayerGenerationService = field(default_factory=PlayerGenerationService)

    def __post_init__(self) -> None:
        if self.value_engine_bridge is None:
            self.value_engine_bridge = IngestionValueEngineBridge(
                session_factory=self.session_factory,
                settings=self.settings,
                summary_projector=PlayerSummaryProjector(),
                default_lookback_days=self.settings.value_snapshot_lookback_days,
            )

    def seed(self, request: PlayerSeedRequest) -> PlayerSeedResult:
        if self.value_engine_bridge is None:
            raise PlayerSeedError("Authoritative value engine bridge is not configured.")

        snapshot_time = request.as_of or datetime.now(UTC)
        resolved_target = self._resolved_target_count(request)
        provider_name = self._resolved_provider_name(request)
        free_agent_count = self._resolved_free_agent_count(request, target_player_count=resolved_target)
        checkpoint = self._load_checkpoint(request.checkpoint_path)
        checkpoint_phase = self._checkpoint_phase(checkpoint, provider_name=provider_name, random_seed=request.random_seed)

        if request.resume_from_checkpoint and checkpoint_phase == "completed":
            return PlayerSeedResult.model_validate(checkpoint["result"])

        universe_seed: dict | None = checkpoint.get("universe_seed") if checkpoint_phase else None
        generation: dict | None = checkpoint.get("generation") if checkpoint_phase else None
        value_snapshots_seeded = int(checkpoint.get("value_snapshots_seeded") or 0) if checkpoint_phase else 0

        if checkpoint_phase not in {"seeded", "valued"}:
            with self.session_factory() as session:
                existing_count = self._count_provider_players(session, provider_name=provider_name)
                if existing_count and not request.replace_provider_data:
                    raise PlayerSeedError(
                        f"Provider slice '{provider_name}' already exists. "
                        "Use replace_provider_data=True or resume_from_checkpoint=True."
                    )

                universe_summary = VerifiedPlayerUniverseSeeder(session, settings=self.settings).seed(
                    target_player_count=resolved_target,
                    provider_name=provider_name,
                    random_seed=request.random_seed,
                    replace_provider_data=request.replace_provider_data,
                    batch_size=request.batch_size,
                )
                generation_summary = self.generation_service.seed_supporting_records(
                    session,
                    provider_name=provider_name,
                    mode=request.mode,
                    random_seed=request.random_seed,
                    as_of=snapshot_time,
                    batch_size=request.batch_size,
                )
                converted_free_agents = self._convert_players_to_free_agents(
                    session,
                    provider_name=provider_name,
                    free_agent_count=free_agent_count,
                )
                session.commit()

            universe_seed = universe_summary.to_dict()
            generation = generation_summary.to_dict()
            generation["free_agents_seeded"] = converted_free_agents
            checkpoint_phase = "seeded"
            self._save_checkpoint(
                request.checkpoint_path,
                {
                    "phase": checkpoint_phase,
                    "provider_name": provider_name,
                    "random_seed": request.random_seed,
                    "target_player_count": resolved_target,
                    "as_of": snapshot_time.isoformat(),
                    "universe_seed": universe_seed,
                    "generation": generation,
                },
            )
        elif request.resume_from_checkpoint:
            with self.session_factory() as session:
                if self._count_provider_players(session, provider_name=provider_name) == 0:
                    raise PlayerSeedError("Checkpoint resume requested but the provider slice is missing.")

        with self.session_factory() as session:
            player_ids = self.generation_service.list_provider_player_ids(session, provider_name=provider_name)
        if not player_ids:
            raise PlayerSeedError("No seeded players were found for the provider slice.")

        if checkpoint_phase != "valued":
            snapshots = self.value_engine_bridge.run(
                as_of=snapshot_time,
                lookback_days=request.lookback_days,
                player_ids=player_ids,
                run_type="manual_rebuild",
                triggered_by="player_seed_service",
                notes={
                    "seed_mode": request.mode,
                    "provider_name": provider_name,
                    "target_player_count": resolved_target,
                    "free_agent_count": free_agent_count,
                },
            )
            value_snapshots_seeded = len(snapshots)
            if value_snapshots_seeded == 0:
                raise PlayerSeedError("Authoritative value engine produced no snapshots. No fallback pricing path was used.")
            checkpoint_phase = "valued"
            self._save_checkpoint(
                request.checkpoint_path,
                {
                    "phase": checkpoint_phase,
                    "provider_name": provider_name,
                    "random_seed": request.random_seed,
                    "target_player_count": resolved_target,
                    "as_of": snapshot_time.isoformat(),
                    "universe_seed": universe_seed,
                    "generation": generation,
                    "value_snapshots_seeded": value_snapshots_seeded,
                },
            )
        elif value_snapshots_seeded == 0:
            with self.session_factory() as session:
                value_snapshots_seeded = self._count_authoritative_snapshots(
                    session,
                    provider_name=provider_name,
                    as_of=snapshot_time,
                )

        with self.session_factory() as session:
            projection_summary = self.generation_service.finalize_seed_views(
                session,
                provider_name=provider_name,
                mode=request.mode,
                random_seed=request.random_seed,
                as_of=snapshot_time,
                batch_size=request.batch_size,
            )
            session.commit()

        result = PlayerSeedResult.model_validate(
            {
                "mode": request.mode,
                "provider_name": provider_name,
                "target_player_count": resolved_target,
                "random_seed": request.random_seed,
                "batch_size": request.batch_size,
                "as_of": snapshot_time,
                "players_seeded": len(player_ids),
                "free_agents_seeded": int((generation or {}).get("free_agents_seeded") or 0),
                "value_snapshots_seeded": value_snapshots_seeded,
                "checkpoint_phase": "completed",
                "universe_seed": universe_seed or {},
                "generation": generation or {},
                "projection": projection_summary.to_dict(),
            }
        )
        self._save_checkpoint(
            request.checkpoint_path,
            {
                "phase": "completed",
                "provider_name": provider_name,
                "random_seed": request.random_seed,
                "target_player_count": resolved_target,
                "as_of": snapshot_time.isoformat(),
                "universe_seed": universe_seed,
                "generation": generation,
                "value_snapshots_seeded": value_snapshots_seeded,
                "result": result.model_dump(mode="json"),
            },
        )
        return result

    def _resolved_target_count(self, request: PlayerSeedRequest) -> int:
        if request.target_player_count is not None:
            return request.target_player_count
        if request.mode == PlayerSeedMode.TEST_SEED_SMALL:
            return 120
        if request.mode in {PlayerSeedMode.CLUB_SEED, PlayerSeedMode.FREE_AGENT_SEED}:
            return 5_000
        return int(self.settings.player_universe_weighting.target_player_count)

    @staticmethod
    def _resolved_provider_name(request: PlayerSeedRequest) -> str:
        if request.provider_name:
            return request.provider_name
        return f"gtex-{request.mode}"

    @staticmethod
    def _resolved_free_agent_count(request: PlayerSeedRequest, *, target_player_count: int) -> int:
        if request.free_agent_count is not None:
            return request.free_agent_count
        if request.mode == PlayerSeedMode.CLUB_SEED:
            return 0
        if request.mode == PlayerSeedMode.FREE_AGENT_SEED:
            return target_player_count
        if request.mode == PlayerSeedMode.TEST_SEED_SMALL:
            return max(2, min(target_player_count // 10, 12))
        if target_player_count < 500:
            return max(2, target_player_count // 12)
        if target_player_count < 5_000:
            return max(12, int(target_player_count * 0.08))
        return max(250, int(target_player_count * 0.06))

    @staticmethod
    def _count_provider_players(session: Session, *, provider_name: str) -> int:
        return int(
            session.scalar(
                select(func.count()).select_from(Player).where(Player.source_provider == provider_name)
            )
            or 0
        )

    @staticmethod
    def _count_authoritative_snapshots(session: Session, *, provider_name: str, as_of: datetime) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(PlayerValueSnapshotRecord)
                .join(Player, Player.id == PlayerValueSnapshotRecord.player_id)
                .where(Player.source_provider == provider_name, PlayerValueSnapshotRecord.as_of == as_of)
            )
            or 0
        )

    @staticmethod
    def _convert_players_to_free_agents(session: Session, *, provider_name: str, free_agent_count: int) -> int:
        if free_agent_count <= 0:
            return 0
        player_ids = list(
            session.scalars(
                select(Player.id)
                .where(Player.source_provider == provider_name)
                .order_by(Player.market_value_eur.asc(), Player.provider_external_id.asc())
                .limit(free_agent_count)
            )
        )
        if not player_ids:
            return 0
        session.execute(delete(PlayerClubTenure).where(PlayerClubTenure.player_id.in_(tuple(player_ids))))
        session.execute(
            update(Player)
            .where(Player.id.in_(tuple(player_ids)))
            .values(current_club_id=None, current_competition_id=None, internal_league_id=None)
        )
        session.flush()
        return len(player_ids)

    @staticmethod
    def _load_checkpoint(checkpoint_path: str | None) -> dict:
        if not checkpoint_path:
            return {}
        path = Path(checkpoint_path)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _checkpoint_phase(checkpoint: dict, *, provider_name: str, random_seed: int) -> str | None:
        if not checkpoint:
            return None
        if checkpoint.get("provider_name") != provider_name or int(checkpoint.get("random_seed") or -1) != random_seed:
            return None
        phase = checkpoint.get("phase")
        return str(phase) if phase is not None else None

    @staticmethod
    def _save_checkpoint(checkpoint_path: str | None, payload: dict) -> None:
        if not checkpoint_path:
            return
        path = Path(checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


__all__ = ["PlayerSeedError", "PlayerSeedService"]
