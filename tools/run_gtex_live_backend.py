from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Final

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_DATABASE_PATH = BACKEND_ROOT / "storage" / "gtex_live_unity.db"
DEFAULT_CONFIG_DIR = BACKEND_ROOT / "config"
DEFAULT_MEDIA_ROOT = BACKEND_ROOT / "storage"
DEFAULT_AUTH_SECRET = "gtex-local-unity-auth-secret-2026"  # pragma: allowlist secret
DEFAULT_MEDIA_SIGNING_SECRET = "gtex-local-unity-media-secret-2026"  # pragma: allowlist secret
LOCAL_PROFILE: Final[str] = "local"
STAGING_PROFILE: Final[str] = "staging"
PRODUCTION_PROFILE: Final[str] = "production"
PROFILE_CHOICES: Final[tuple[str, str, str]] = (LOCAL_PROFILE, STAGING_PROFILE, PRODUCTION_PROFILE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the GTEX backend for Unity live playback with explicit profile handling."
    )
    parser.add_argument(
        "--profile",
        choices=PROFILE_CHOICES,
        default=LOCAL_PROFILE,
        help="Environment profile. Local keeps the current lightweight defaults; staging/production require explicit settings.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Backend bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Backend bind port.")
    parser.add_argument(
        "--app-env",
        default="",
        help="Explicit GTE_APP_ENV override. Defaults to development for local, otherwise matches the selected profile.",
    )
    parser.add_argument(
        "--database-path",
        default="",
        help="Path to the dedicated SQLite database for local Unity live runs.",
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Explicit DATABASE_URL override. Required for non-local profiles.",
    )
    parser.add_argument(
        "--config-dir",
        default="",
        help="Backend config directory. Required for non-local profiles.",
    )
    parser.add_argument(
        "--media-root",
        default="",
        help="Backend media storage root. Required for non-local profiles.",
    )
    parser.add_argument("--auth-secret", default="", help="Auth secret. Required for non-local profiles.")
    parser.add_argument(
        "--media-signing-secret",
        default="",
        help="Media signing secret. Required for non-local profiles.",
    )
    parser.add_argument("--log-level", default="info", help="Uvicorn log level.")
    return parser.parse_args()


def build_sqlite_url(database_path: Path) -> str:
    return f"sqlite+pysqlite:///{database_path.resolve().as_posix()}"


def _resolve_cli_or_env(cli_value: str, env_key: str) -> str:
    candidate = str(cli_value or "").strip()
    if candidate:
        return candidate
    return str(os.environ.get(env_key, "") or "").strip()


def _require_cli_or_env(cli_value: str, env_key: str, *, label: str, profile: str) -> str:
    candidate = _resolve_cli_or_env(cli_value, env_key)
    if candidate:
        return candidate
    raise RuntimeError(f"{label} is required for the '{profile}' profile. Pass it explicitly or set {env_key}.")


def _resolve_app_env(args: argparse.Namespace) -> str:
    override = str(args.app_env or "").strip()
    if override:
        return override
    return "development" if args.profile == LOCAL_PROFILE else args.profile


def _apply_environment(values: dict[str, str], *, prefer_existing: bool) -> dict[str, str]:
    applied: dict[str, str] = {}
    for key, value in values.items():
        if prefer_existing:
            os.environ.setdefault(key, value)
        else:
            os.environ[key] = value
        applied[key] = os.environ[key]
    return applied


def _apply_local_environment(args: argparse.Namespace) -> dict[str, str]:
    database_path = Path(str(args.database_path or "").strip() or DEFAULT_DATABASE_PATH).resolve()
    config_dir = Path(str(args.config_dir or "").strip() or DEFAULT_CONFIG_DIR).resolve()
    media_root = Path(str(args.media_root or "").strip() or DEFAULT_MEDIA_ROOT).resolve()
    auth_secret = str(args.auth_secret or "").strip() or DEFAULT_AUTH_SECRET
    media_signing_secret = str(args.media_signing_secret or "").strip() or DEFAULT_MEDIA_SIGNING_SECRET

    database_path.parent.mkdir(parents=True, exist_ok=True)
    media_root.mkdir(parents=True, exist_ok=True)

    defaults = {
        "DATABASE_URL": args.database_url.strip() or build_sqlite_url(database_path),
        "GTE_APP_ENV": _resolve_app_env(args),
        "GTE_CONFIG_DIR": str(config_dir),
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        "GTE_AUTH_SECRET": auth_secret,
        "GTE_MEDIA_SIGNING_SECRET": media_signing_secret,
        "GTE_RUN_MIGRATION_CHECK": "true",
        "RUN_STARTUP_SEEDING": "false",
        "GTE_BOOTSTRAP_ADMIN_ENABLED": "false",
        "GTE_API_CACHE_ENABLED": "false",
        "GTE_DISTRIBUTED_RATE_LIMIT_ENABLED": "false",
        "GTE_TASK_QUEUE_ENABLED": "false",
        "GTE_OUTBOX_RELAY_ENABLED": "false",
        "GTE_KAFKA_API_QUEUE_CONSUMER_ENABLED": "false",
        "GTE_KAFKA_SIMULATION_CONSUMER_ENABLED": "false",
        "GTE_PROJECTION_WORKERS_ENABLED": "false",
        "GTE_LIVE_COMMENTARY_LLM_ENABLED": "false",
        "GTE_SOCIAL_CONTENT_LLM_ENABLED": "false",
    }

    return _apply_environment(defaults, prefer_existing=True)


def _apply_non_local_environment(args: argparse.Namespace) -> dict[str, str]:
    database_url = _require_cli_or_env(args.database_url, "DATABASE_URL", label="DATABASE_URL", profile=args.profile)
    config_dir = _require_cli_or_env(args.config_dir, "GTE_CONFIG_DIR", label="Config directory", profile=args.profile)
    media_root = _require_cli_or_env(
        args.media_root,
        "GTE_MEDIA_STORAGE_ROOT",
        label="Media root",
        profile=args.profile,
    )
    auth_secret = _require_cli_or_env(args.auth_secret, "GTE_AUTH_SECRET", label="Auth secret", profile=args.profile)
    media_signing_secret = _require_cli_or_env(
        args.media_signing_secret,
        "GTE_MEDIA_SIGNING_SECRET",
        label="Media signing secret",
        profile=args.profile,
    )

    if auth_secret == DEFAULT_AUTH_SECRET or media_signing_secret == DEFAULT_MEDIA_SIGNING_SECRET:
        raise RuntimeError(f"Local GTEX dev secrets are not allowed for the '{args.profile}' profile.")

    if args.profile == PRODUCTION_PROFILE and database_url.lower().startswith("sqlite"):
        raise RuntimeError("Production profile requires a non-SQLite DATABASE_URL.")

    values = {
        "DATABASE_URL": database_url,
        "GTE_APP_ENV": _resolve_app_env(args),
        "GTE_CONFIG_DIR": str(Path(config_dir).resolve()),
        "GTE_MEDIA_STORAGE_ROOT": str(Path(media_root).resolve()),
        "GTE_AUTH_SECRET": auth_secret,
        "GTE_MEDIA_SIGNING_SECRET": media_signing_secret,
    }

    return _apply_environment(values, prefer_existing=False)


def apply_backend_environment(args: argparse.Namespace) -> dict[str, str]:
    if args.profile == LOCAL_PROFILE:
        return _apply_local_environment(args)
    return _apply_non_local_environment(args)


def main() -> None:
    args = parse_args()
    applied = apply_backend_environment(args)

    summary = {
        "profile": args.profile,
        "app_env": applied["GTE_APP_ENV"],
        "backend_root": str(BACKEND_ROOT),
        "base_url": f"http://{args.host}:{args.port}",
        "database_url": applied["DATABASE_URL"],
        "config_dir": applied["GTE_CONFIG_DIR"],
        "media_root": applied["GTE_MEDIA_STORAGE_ROOT"],
    }
    print(json.dumps(summary, indent=2), flush=True)

    uvicorn.run(
        "app.main:app",
        app_dir=str(BACKEND_ROOT),
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        access_log=True,
        reload=False,
    )


if __name__ == "__main__":
    main()
