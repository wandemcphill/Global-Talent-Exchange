from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


logger = logging.getLogger("real_player_import_loop")


@dataclass(slots=True)
class LoopRuntime:
    load_settings: Any
    create_database_engine: Any
    create_session_factory: Any
    RealPlayerImportService: Any
    RealPlayerBulkImportOpsService: Any
    RealPlayerBulkImportOpsError: type[Exception]


@dataclass(slots=True)
class LoopConfig:
    database_url: str
    run_id: str | None
    provider_name: str
    cursor_key: str
    batch_size: int
    max_pages: int
    publish_limit: int
    publish_priority: str
    max_publish_batches_per_cycle: int
    sleep_seconds: float
    idle_sleep_seconds: float
    max_consecutive_errors: int
    log_path: Path | None
    status_path: Path | None
    stop_path: Path | None
    once: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Continuously import, repair, and publish real players.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    parser.add_argument("--run-id", default=None, help="Tracked bulk import run id to continue.")
    parser.add_argument("--provider-name", default=os.environ.get("GTE_REAL_PLAYER_IMPORT_PROVIDER", "sportmonks"))
    parser.add_argument("--cursor-key", default="real-player-directory")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--publish-limit", type=int, default=100)
    parser.add_argument("--publish-priority", default="all")
    parser.add_argument("--max-publish-batches-per-cycle", type=int, default=5)
    parser.add_argument("--sleep-seconds", type=float, default=15.0)
    parser.add_argument("--idle-sleep-seconds", type=float, default=45.0)
    parser.add_argument("--max-consecutive-errors", type=int, default=5)
    parser.add_argument("--log-path", default=None)
    parser.add_argument("--status-path", default=None)
    parser.add_argument("--stop-path", default=None)
    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    _prepare_environment(database_url=args.database_url)
    runtime = _load_runtime()
    settings = runtime.load_settings(environ=dict(os.environ))
    engine = runtime.create_database_engine(args.database_url)
    session_factory = runtime.create_session_factory(engine)

    config = LoopConfig(
        database_url=args.database_url,
        run_id=args.run_id,
        provider_name=str(args.provider_name or "sportmonks"),
        cursor_key=str(args.cursor_key or "real-player-directory"),
        batch_size=max(int(args.batch_size), 1),
        max_pages=max(int(args.max_pages), 1),
        publish_limit=max(int(args.publish_limit), 1),
        publish_priority=str(args.publish_priority or "all"),
        max_publish_batches_per_cycle=max(int(args.max_publish_batches_per_cycle), 1),
        sleep_seconds=max(float(args.sleep_seconds), 1.0),
        idle_sleep_seconds=max(float(args.idle_sleep_seconds), 1.0),
        max_consecutive_errors=max(int(args.max_consecutive_errors), 1),
        log_path=Path(args.log_path).resolve() if args.log_path else None,
        status_path=Path(args.status_path).resolve() if args.status_path else None,
        stop_path=Path(args.stop_path).resolve() if args.stop_path else None,
        once=bool(args.once),
    )
    _configure_logging(log_path=config.log_path)

    loop = RealPlayerImportLoop(
        runtime=runtime,
        settings=settings,
        session_factory=session_factory,
        config=config,
    )
    try:
        return loop.run()
    finally:
        engine.dispose()


class RealPlayerImportLoop:
    def __init__(
        self,
        *,
        runtime: LoopRuntime,
        settings: Any,
        session_factory: Any,
        config: LoopConfig,
    ) -> None:
        self.runtime = runtime
        self.settings = settings
        self.session_factory = session_factory
        self.config = config
        self.consecutive_errors = 0
        self.cycles_completed = 0
        self.started_at = _now_iso()

    def run(self) -> int:
        logger.info(
            "loop started run_id=%s provider=%s cursor_key=%s batch_size=%s max_pages=%s publish_limit=%s priority=%s pid=%s",
            self.config.run_id,
            self.config.provider_name,
            self.config.cursor_key,
            self.config.batch_size,
            self.config.max_pages,
            self.config.publish_limit,
            self.config.publish_priority,
            os.getpid(),
        )
        self._write_status({"state": "running", "message": "loop started"})
        while True:
            if self._stop_requested():
                logger.info("stop file detected path=%s", self.config.stop_path)
                self._write_status({"state": "stopped", "message": "stop file detected"})
                return 0

            try:
                cycle = self._run_cycle()
                self.cycles_completed += 1
                self.consecutive_errors = 0
                self._write_status(
                    {
                        "state": "running",
                        "last_cycle": cycle,
                        "message": cycle.get("summary"),
                    }
                )
                if cycle.get("should_exit"):
                    logger.info("loop completed reason=%s", cycle.get("exit_reason"))
                    self._write_status(
                        {
                            "state": "completed",
                            "last_cycle": cycle,
                            "message": cycle.get("exit_reason"),
                        }
                    )
                    return 0
                if self.config.once:
                    logger.info("loop exiting after single cycle")
                    return 0
                sleep_seconds = (
                    self.config.sleep_seconds if cycle.get("made_progress") else self.config.idle_sleep_seconds
                )
                logger.info("sleeping seconds=%s", sleep_seconds)
                time.sleep(sleep_seconds)
            except Exception as exc:
                self.consecutive_errors += 1
                logger.exception("cycle failed consecutive_errors=%s", self.consecutive_errors)
                self._write_status(
                    {
                        "state": "error",
                        "message": str(exc),
                        "consecutive_errors": self.consecutive_errors,
                    }
                )
                if self.consecutive_errors >= self.config.max_consecutive_errors:
                    logger.error(
                        "loop aborting after too many consecutive errors threshold=%s",
                        self.config.max_consecutive_errors,
                    )
                    return 1
                time.sleep(self.config.idle_sleep_seconds)

    def _run_cycle(self) -> dict[str, Any]:
        cycle_started_at = _now_iso()
        ops_service = self.runtime.RealPlayerBulkImportOpsService(
            session_factory=self.session_factory,
            settings=self.settings,
        )

        before_report = self._safe_report(ops_service)
        before_run = before_report.get("run") if before_report else None
        if before_run and not self.config.run_id:
            self.config.run_id = before_run.get("id")

        import_summary = None
        import_run_id = None
        if before_run is None or before_run.get("resume_cursor"):
            with self.session_factory() as session:
                import_service = self.runtime.RealPlayerImportService(
                    session,
                    settings=self.settings,
                )
                import_result = import_service.import_directory(
                    provider_name=self.config.provider_name,
                    batch_size=self.config.batch_size,
                    max_pages=self.config.max_pages,
                    cursor_key=self.config.cursor_key,
                    restart=False,
                )
            import_summary = _model_payload(import_result)
            import_run_id = import_summary.get("import_run_id")
            if import_run_id:
                if self.config.run_id and import_run_id != self.config.run_id:
                    logger.warning(
                        "active run changed from %s to %s; continuing with returned run id",
                        self.config.run_id,
                        import_run_id,
                    )
                self.config.run_id = str(import_run_id)
            logger.info(
                "import cycle status=%s records_seen=%s inserted=%s updated=%s failed=%s next_cursor=%s import_run_id=%s",
                import_summary.get("status"),
                import_summary.get("records_seen"),
                import_summary.get("inserted_count"),
                import_summary.get("updated_count"),
                import_summary.get("failed_count"),
                import_summary.get("next_cursor"),
                self.config.run_id,
            )

        if not self.config.run_id:
            raise RuntimeError("No tracked real-player import run is available.")

        repair_summary = None
        try:
            repair_result = ops_service.repair_mappings(run_id=self.config.run_id)
            repair_summary = _model_payload(repair_result)
            logger.info(
                "repair cycle targeted=%s reclassified=%s transitioned_ready=%s remaining_unresolved=%s",
                repair_summary["details_json"].get("targeted_rows"),
                repair_summary["details_json"].get("reclassified_rows"),
                repair_summary["details_json"].get("transitioned_ready_rows"),
                repair_summary["details_json"].get("remaining_unresolved_rows"),
            )
        except self.runtime.RealPlayerBulkImportOpsError as exc:
            if "No staged real-player rows matched" not in str(exc):
                raise
            logger.info("repair skipped because no unresolved rows matched run_id=%s", self.config.run_id)

        publish_results: list[dict[str, Any]] = []
        for _ in range(self.config.max_publish_batches_per_cycle):
            report_result = ops_service.report_run(run_id=self.config.run_id)
            report_payload = _model_payload(report_result)
            current_run = report_payload.get("run") or {}
            if int(current_run.get("publish_ready_rows") or 0) <= 0:
                break
            try:
                publish_result = ops_service.publish_ready_players(
                    run_id=self.config.run_id,
                    limit=self.config.publish_limit,
                    priority_bucket=self.config.publish_priority,
                )
            except self.runtime.RealPlayerBulkImportOpsError as exc:
                if exc.status_code == 409 and "No publish-ready rows matched" in str(exc):
                    break
                raise
            publish_payload = _model_payload(publish_result)
            publish_results.append(publish_payload)
            details = publish_payload.get("details_json") or {}
            logger.info(
                "publish cycle selected=%s published=%s excluded=%s validation_issues=%s batch_id=%s",
                details.get("selected_rows"),
                details.get("published_now"),
                details.get("excluded_rows"),
                details.get("validation_issue_count"),
                details.get("write_batch_id"),
            )
            if int(details.get("published_now") or 0) <= 0 and int(details.get("would_publish_rows") or 0) <= 0:
                break

        after_report_result = ops_service.report_run(run_id=self.config.run_id)
        after_report = _model_payload(after_report_result)
        after_run = after_report.get("run") or {}
        summary = (
            f"cursor={after_run.get('resume_cursor')} "
            f"discovered={after_run.get('total_rows_discovered')} "
            f"published={after_run.get('published_rows')} "
            f"ready={after_run.get('publish_ready_rows')} "
            f"unresolved={after_run.get('unresolved_rows')} "
            f"failed={after_run.get('failed_rows')}"
        )
        made_progress = _made_progress(before_run, after_run, import_summary, repair_summary, publish_results)
        should_exit = not after_run.get("resume_cursor") and int(after_run.get("publish_ready_rows") or 0) == 0
        exit_reason = None
        if should_exit:
            exit_reason = "source exhausted and no publish-ready rows remain"

        return {
            "started_at": cycle_started_at,
            "completed_at": _now_iso(),
            "run_id": self.config.run_id,
            "import": import_summary,
            "repair": repair_summary,
            "publish": publish_results,
            "report": after_report,
            "summary": summary,
            "made_progress": made_progress,
            "should_exit": should_exit,
            "exit_reason": exit_reason,
        }

    def _safe_report(self, ops_service: Any) -> dict[str, Any] | None:
        if not self.config.run_id:
            return None
        try:
            return _model_payload(ops_service.report_run(run_id=self.config.run_id))
        except self.runtime.RealPlayerBulkImportOpsError as exc:
            if exc.status_code == 404:
                logger.warning("tracked run not found; a fresh provider run will be created")
                self.config.run_id = None
                return None
            raise

    def _stop_requested(self) -> bool:
        return self.config.stop_path is not None and self.config.stop_path.exists()

    def _write_status(self, payload: dict[str, Any]) -> None:
        if self.config.status_path is None:
            return
        status = {
            "pid": os.getpid(),
            "started_at": self.started_at,
            "heartbeat_at": _now_iso(),
            "cycles_completed": self.cycles_completed,
            "run_id": self.config.run_id,
            **payload,
        }
        self.config.status_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.config.status_path.parent,
            delete=False,
            suffix=".tmp",
        ) as handle:
            json.dump(status, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temp_path = Path(handle.name)
        temp_path.replace(self.config.status_path)


def _prepare_environment(*, database_url: str) -> None:
    os.environ.setdefault("DATABASE_URL", database_url)
    os.environ.setdefault("GTE_DATABASE_URL", database_url)
    os.environ.setdefault("GTE_AUTH_SECRET", "codex-temporary-auth-secret")
    os.environ.setdefault("GTE_MEDIA_SIGNING_SECRET", "codex-temporary-media-secret")
    os.environ.setdefault("GTE_REAL_PLAYER_IMPORT_PROVIDER", "sportmonks")
    os.environ.setdefault("GTE_REAL_PLAYER_IMPORT_TIMEOUT_SECONDS", "60")
    os.environ.setdefault("GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES", "true")


def _load_runtime() -> LoopRuntime:
    try:
        from app.core.config import load_settings
        from app.core.database import create_database_engine, create_session_factory
        from app.ingestion.real_player_bulk_ops_service import (
            RealPlayerBulkImportOpsError,
            RealPlayerBulkImportOpsService,
        )
        from app.ingestion.real_player_import_service import RealPlayerImportService
    except Exception:
        _bootstrap_model_imports()
        from app.core.config import load_settings
        from app.core.database import create_database_engine, create_session_factory
        from app.ingestion.real_player_bulk_ops_service import (
            RealPlayerBulkImportOpsError,
            RealPlayerBulkImportOpsService,
        )
        from app.ingestion.real_player_import_service import RealPlayerImportService

    return LoopRuntime(
        load_settings=load_settings,
        create_database_engine=create_database_engine,
        create_session_factory=create_session_factory,
        RealPlayerImportService=RealPlayerImportService,
        RealPlayerBulkImportOpsService=RealPlayerBulkImportOpsService,
        RealPlayerBulkImportOpsError=RealPlayerBulkImportOpsError,
    )


def _bootstrap_model_imports() -> None:
    import importlib
    import pkgutil
    import types

    backend_app_root = BACKEND_ROOT / "app"
    backend_model_root = backend_app_root / "models"

    app_module = sys.modules.get("app")
    if app_module is None:
        app_module = types.ModuleType("app")
        sys.modules["app"] = app_module
    app_module.__path__ = [str(backend_app_root)]

    models_module = sys.modules.get("app.models")
    if models_module is None:
        models_module = types.ModuleType("app.models")
        sys.modules["app.models"] = models_module
    models_module.__path__ = [str(backend_model_root)]

    for _finder, module_name, _is_package in pkgutil.walk_packages(
        [str(backend_model_root)],
        prefix="app.models.",
    ):
        importlib.import_module(module_name)

    extra_modules = [
        "app.agents.models",
        "app.leaderboards.models",
        "app.models.economy_governor",
        "app.models.fx_pricing",
        "app.models.player_token_market",
        "app.models.event_backbone",
        "app.models.projections",
        "app.club_finance.models",
        "app.club_identity.models.reputation",
        "app.fast_cups.repositories.database",
        "app.ingestion.models",
        "app.ingestion.real_player_import_models",
        "app.leagues.repository",
        "app.live_ops.models",
        "app.market.read_models",
        "app.players.read_models",
        "app.predictions.models",
        "app.regen_universe.models",
        "app.replay_archive.persistence",
        "app.team_dynamics.models",
        "app.value_engine.read_models",
        "app.value_engine.service",
        "app.ingestion.real_player_import_service",
        "app.ingestion.real_player_ingestion_service",
        "app.ingestion.real_player_bulk_ops_service",
    ]
    for module_name in extra_modules:
        importlib.import_module(module_name)

    from sqlalchemy.orm import configure_mappers

    configure_mappers()


def _configure_logging(*, log_path: Path | None) -> None:
    handlers: list[logging.Handler] = []
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    else:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )


def _model_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError(f"Unsupported payload type: {type(value)!r}")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _int_value(payload: dict[str, Any] | None, key: str) -> int:
    if not payload:
        return 0
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _made_progress(
    before_run: dict[str, Any] | None,
    after_run: dict[str, Any] | None,
    import_summary: dict[str, Any] | None,
    repair_summary: dict[str, Any] | None,
    publish_results: list[dict[str, Any]],
) -> bool:
    if import_summary is not None:
        if _int_value(import_summary, "records_seen") > 0:
            return True
        if _int_value(import_summary, "inserted_count") > 0:
            return True
        if _int_value(import_summary, "updated_count") > 0:
            return True
    if repair_summary is not None:
        details = repair_summary.get("details_json") or {}
        try:
            if int(details.get("reclassified_rows") or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
    for publish_result in publish_results:
        details = publish_result.get("details_json") or {}
        try:
            if int(details.get("published_now") or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
    if before_run and after_run:
        if before_run.get("resume_cursor") != after_run.get("resume_cursor"):
            return True
        for key in (
            "total_rows_discovered",
            "published_rows",
            "publish_ready_rows",
            "unresolved_rows",
            "failed_rows",
        ):
            if before_run.get(key) != after_run.get(key):
                return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
