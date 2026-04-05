from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from backend.tests.support.secrets import MEDIA_SIGNING_TEST_SECRET, TEST_AUTH_SECRET
from app.core.config import load_settings, reset_settings_cache
from app.ingestion.demo_bootstrap import DEFAULT_DEMO_PASSWORD
from app.ingestion.dev_cli import rebuild_demo_market
from app.main import create_app

_NEGOTIATION_LISTING_ID = "00000000-0000-0000-0000-000000000503"


@contextmanager
def _demo_operator_environment(*, database_url: str, media_root: Path) -> Iterator[None]:
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_AUTH_SECRET": TEST_AUTH_SECRET,
        "GTE_MEDIA_SIGNING_SECRET": MEDIA_SIGNING_TEST_SECRET,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        "GTE_APP_ENV": "development",
        "RUN_STARTUP_SEEDING": "false",
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}
    try:
        for key, value in managed_env.items():
            os.environ[key] = value
        reset_settings_cache()
        yield
    finally:
        for key, previous in previous_env.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
        reset_settings_cache()


def _join_deferred_startup_if_needed(client: TestClient) -> None:
    startup_thread = getattr(client.app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=30)


def test_rebuild_demo_market_restores_seeded_live_visibility_routes(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'world-visibility-routes.db').as_posix()}"
    media_root = tmp_path / "media"
    media_root.mkdir(parents=True, exist_ok=True)

    with _demo_operator_environment(database_url=database_url, media_root=media_root):
        rebuild_demo_market(
            database_url=database_url,
            player_count=10,
            provider="cli-demo",
            signal_provider="cli-demo-signals",
            password=DEFAULT_DEMO_PASSWORD,
            seed=20260311,
            batch_size=5,
            liquid_player_count=3,
            illiquid_player_count=1,
        )

        settings = load_settings()
        engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
        app = create_app(settings=settings, engine=engine, run_migration_check=False)

        try:
            with TestClient(app) as client:
                _join_deferred_startup_if_needed(client)

                login = client.post(
                    "/auth/login",
                    json={
                        "email": "seed.fan@gte.local",
                        "password": DEFAULT_DEMO_PASSWORD,
                    },
                )
                assert login.status_code == 200, login.text
                auth_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

                marketplace = client.get("/marketplace/players", params={"limit": 20})
                assert marketplace.status_code == 200, marketplace.text
                marketplace_payload = marketplace.json()
                assert marketplace_payload["players"]

                transfer_listings = client.get(
                    "/api/transfer-market/listings",
                    params={"status": "open"},
                )
                assert transfer_listings.status_code == 200, transfer_listings.text
                listings_payload = transfer_listings.json()
                assert listings_payload

                transfer_detail = client.get(f"/api/transfer-market/listings/{_NEGOTIATION_LISTING_ID}")
                assert transfer_detail.status_code == 200, transfer_detail.text
                assert transfer_detail.json()["id"] == _NEGOTIATION_LISTING_ID

                transfer_negotiation = client.get(
                    f"/api/transfer-market/listings/{_NEGOTIATION_LISTING_ID}/negotiation",
                    headers=auth_headers,
                )
                assert transfer_negotiation.status_code == 200, transfer_negotiation.text
                negotiation_payload = transfer_negotiation.json()
                assert negotiation_payload["listing_id"] == _NEGOTIATION_LISTING_ID
                assert negotiation_payload["player_decision"] is not None
                assert negotiation_payload["coach_opinion"] is not None
                assert negotiation_payload["agent_negotiation"] is not None

                federations = client.get("/federations")
                assert federations.status_code == 200, federations.text
                assert federations.json()

                federation_rankings = client.get("/federations/rankings")
                assert federation_rankings.status_code == 200, federation_rankings.text
                assert federation_rankings.json()

                regional_tournaments = client.get("/federations/regional-tournaments")
                assert regional_tournaments.status_code == 200, regional_tournaments.text
                assert regional_tournaments.json()

                competitions = client.get("/national-team-engine/competitions")
                assert competitions.status_code == 200, competitions.text
                competitions_payload = competitions.json()
                assert competitions_payload
                competition_id = competitions_payload[0]["id"]

                rankings = client.get("/national-team-engine/rankings")
                assert rankings.status_code == 200, rankings.text
                assert rankings.json()

                lifecycle = client.get(f"/national-team-engine/competitions/{competition_id}/lifecycle")
                assert lifecycle.status_code == 200, lifecycle.text
                assert lifecycle.json()

                presentation = client.get(f"/national-team-engine/competitions/{competition_id}/presentation")
                assert presentation.status_code == 200, presentation.text
                assert presentation.json()["competition"]["id"] == competition_id

                rising_stars = client.get("/regen-universe/rising-stars", params={"limit": 12})
                assert rising_stars.status_code == 200, rising_stars.text
                assert rising_stars.json()["entries"]

                scouting_feed = client.get("/regen-universe/scouting-feed", params={"limit": 12})
                assert scouting_feed.status_code == 200, scouting_feed.text
                assert scouting_feed.json()["items"]

                seasons = client.get("/regen-universe/seasons", params={"limit": 12})
                assert seasons.status_code == 200, seasons.text
                assert seasons.json()["items"]

                awards = client.get("/regen-universe/awards", params={"limit": 12})
                assert awards.status_code == 200, awards.text
                assert awards.json()["items"]

                national_regens = client.get(
                    "/regen-universe/national-regens",
                    params={"limit": 12, "preseed_batch": "u17_batch"},
                )
                assert national_regens.status_code == 200, national_regens.text
                assert national_regens.json()["items"]

                tracking = client.get("/regen-universe/tracking")
                assert tracking.status_code == 200, tracking.text
                tracking_payload = tracking.json()
                assert tracking_payload["total_seeded_players"] > 0
                assert tracking_payload["country_distribution"]
        finally:
            engine.dispose()
