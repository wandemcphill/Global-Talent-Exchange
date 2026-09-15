from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend.tests.support.economic_policy import seed_economic_policy
from backend.tests.support.secrets import (
    BOOTSTRAP_TEST_ADMIN_PASSWORD,
    MEDIA_SIGNING_TEST_SECRET,
    TEST_AUTH_SECRET,
    TEST_PASSWORD,
)
from backend.tests.support.signup_payloads import user_signup_payload

SMOKE_DEMO_PLAYER_COUNT = 12
DEFAULT_TEST_DATABASE_URL = (
    f"sqlite+pysqlite:///{(Path(__file__).resolve().parents[2] / '.tmp_pytest_default.db').as_posix()}"
)

os.environ.setdefault("GTE_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
os.environ.setdefault("GTE_AUTH_SECRET", TEST_AUTH_SECRET)
os.environ.setdefault("GTE_MEDIA_SIGNING_SECRET", MEDIA_SIGNING_TEST_SECRET)
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_ENABLED", "1")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_EMAIL", "admin@test.gtex.local")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_PASSWORD", BOOTSTRAP_TEST_ADMIN_PASSWORD)
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_USERNAME", "gtex_test_admin")
os.environ.setdefault("GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME", "GTEX Test Admin")
os.environ.setdefault("GTE_DEFERRED_STARTUP_ENABLED", "0")
os.environ.setdefault("GTE_COMPETITIVE_INTEGRITY_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_FEDERATION_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_HISTORY_ENGAGEMENT_WORKER_ENABLED", "0")
os.environ.setdefault("GTE_OUTBOX_RELAY_ENABLED", "0")
os.environ.setdefault("GTE_PORTRAIT_PRELOAD_ENABLED", "0")
os.environ.setdefault("GTE_PROJECTION_WORKERS_ENABLED", "0")
os.environ.setdefault("GTE_REGEN_PRELOAD_ENABLED", "0")
os.environ.setdefault("GTE_REAL_WORLD_SYNC_ENABLED", "0")
os.environ.setdefault("GTE_RUN_STARTUP_SEEDING", "0")
os.environ.setdefault("GTE_STARTUP_PROFILE", "test")
os.environ.setdefault("GTE_TASK_QUEUE_ENABLED", "0")

