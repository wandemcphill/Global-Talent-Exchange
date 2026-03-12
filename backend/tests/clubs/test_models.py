from __future__ import annotations

from alembic import command
from sqlalchemy import create_engine, inspect

from backend.app.core.database import build_alembic_config
from backend.app.models.base import Base
from backend.app.models.club_branding_asset import ClubBrandingAsset
from backend.app.models.club_cosmetic_catalog_item import ClubCosmeticCatalogItem
from backend.app.models.club_cosmetic_purchase import ClubCosmeticPurchase
from backend.app.models.club_dynasty_milestone import ClubDynastyMilestone
from backend.app.models.club_dynasty_progress import ClubDynastyProgress
from backend.app.models.club_identity_theme import ClubIdentityTheme
from backend.app.models.club_jersey_design import ClubJerseyDesign
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_reputation_event import ClubReputationEvent
from backend.app.models.club_reputation_snapshot import ClubReputationSnapshot
from backend.app.models.club_showcase_snapshot import ClubShowcaseSnapshot
from backend.app.models.club_trophy import ClubTrophy
from backend.app.models.club_trophy_cabinet import ClubTrophyCabinet


def test_alembic_upgrade_creates_club_progression_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'clubs.db').as_posix()}"
    command.upgrade(build_alembic_config(database_url), "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        inspector = inspect(engine)
        assert {
            "club_profiles",
            "club_trophies",
            "club_trophy_cabinets",
            "club_dynasty_progress",
            "club_dynasty_milestones",
            "club_branding_assets",
            "club_jersey_designs",
            "club_cosmetic_catalog_items",
            "club_cosmetic_purchases",
            "club_identity_themes",
            "club_showcase_snapshots",
        }.issubset(set(inspector.get_table_names()))
    finally:
        engine.dispose()


def test_club_model_tables_are_registered_on_base_metadata() -> None:
    assert {
        ClubProfile.__table__.name,
        ClubTrophy.__table__.name,
        ClubTrophyCabinet.__table__.name,
        ClubDynastyProgress.__table__.name,
        ClubDynastyMilestone.__table__.name,
        ClubBrandingAsset.__table__.name,
        ClubJerseyDesign.__table__.name,
        ClubCosmeticCatalogItem.__table__.name,
        ClubCosmeticPurchase.__table__.name,
        ClubIdentityTheme.__table__.name,
        ClubShowcaseSnapshot.__table__.name,
    }.issubset(set(Base.metadata.tables))
    assert ClubReputationEvent.__table__.name == "reputation_event_log"
    assert ClubReputationSnapshot.__table__.name == "reputation_snapshot"
