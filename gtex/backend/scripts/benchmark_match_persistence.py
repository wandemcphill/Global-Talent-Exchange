from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import time

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import ensure_database_schema_current
from app.core.event_backbone import build_outbox_event
from app.core.events import DomainEvent
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.matches.service import MatchEventLoggerService
from app.services.commentary_service import MatchCommentaryService

from scripts.benchmark_match_simulation import build_request


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        database_path = Path(tmp_dir) / "benchmark-persistence.db"
        engine = create_engine(
            f"sqlite+pysqlite:///{database_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        try:
            ensure_database_schema_current(engine)
            SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

            replay_payload = MatchSimulationService().build_replay_payload(build_request(seed=7, match_id="persist-template"))
            iterations = 50
            started_at = time.perf_counter()
            commentary_rows = 0
            match_rows = 0
            for index in range(iterations):
                fixture_id = f"persist-{index + 1}"
                with SessionLocal() as session:
                    commentary_rows += len(
                        MatchCommentaryService(session).persist_replay_commentary(fixture_id, replay_payload)
                    )
                    insights = MatchEventLoggerService(session).persist_official_match(
                        match_id=fixture_id,
                        replay_payload=replay_payload,
                    )
                    match_rows += len(insights.replay.timeline)
                    session.add(
                        build_outbox_event(
                            domain_event=DomainEvent(
                                name="match.completed",
                                payload={
                                    "fixture_id": fixture_id,
                                    "competition_id": "benchmark-league",
                                    "home_club_id": "home",
                                    "away_club_id": "away",
                                    "home_club_name": "North City",
                                    "away_club_name": "South Town",
                                    "home_goals": replay_payload.summary.home_score,
                                    "away_goals": replay_payload.summary.away_score,
                                    "winner_team_id": replay_payload.summary.winner_team_id,
                                },
                                aggregate_id=fixture_id,
                                aggregate_type="fixture",
                                producer="benchmark",
                                partition_key=fixture_id,
                            )
                        )
                    )
                    session.commit()
            elapsed = time.perf_counter() - started_at
            result = {
                "benchmark": "match_persistence",
                "iterations": iterations,
                "elapsed_seconds": round(elapsed, 4),
                "matches_per_second": round(iterations / elapsed, 2) if elapsed else None,
                "commentary_rows_written": commentary_rows,
                "match_rows_written": match_rows,
            }
            print(json.dumps(result, indent=2))
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
