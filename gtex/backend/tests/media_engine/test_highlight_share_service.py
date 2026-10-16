from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.highlight_share  # noqa: F401
import app.models.media_engine  # noqa: F401
import app.models.story_feed  # noqa: F401
from app.core.config import MediaStorageConfig
from app.media_engine.schemas import HighlightShareAmplificationRequest, HighlightShareExportRequest
from app.models.base import Base
from app.models.story_feed import StoryFeedItem
from app.models.user import User, UserRole
from app.services.highlight_share_service import HighlightShareService
from app.services.storage_media_service import MediaStorageService
from app.storage import LocalObjectStorage


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, SessionLocal


def _create_user(session, *, user_id: str) -> User:
    user = User(id=user_id, email=f"{user_id}@example.com", username=user_id, password_hash="hashed", role=UserRole.USER)
    session.add(user)
    session.flush()
    return user


def _storage(tmp_path: Path) -> MediaStorageService:
    config = MediaStorageConfig(
        storage_root=tmp_path,
        cdn_base_url=None,
        download_base_url="/media-engine/downloads",
        highlight_temp_prefix="media/highlights/temp",
        highlight_archive_prefix="media/highlights/archive",
        highlight_export_prefix="media/exports",
        highlight_temp_ttl_hours=72,
        highlight_archive_ttl_days=365,
        download_expiry_minutes=30,
        download_rate_limit_count=5,
        download_rate_limit_window_minutes=15,
        watermark_enabled=True,
    )
    return MediaStorageService(storage=LocalObjectStorage(tmp_path), config=config)


def test_highlight_share_export_generates_metadata_manifest(tmp_path: Path) -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        actor = _create_user(session, user_id="share-user")
        storage_service = _storage(tmp_path)
        source = storage_service.store_temporary_highlight(
            match_key="friendly-101",
            content=b"demo-highlight",
            content_type="video/mp4",
            clip_label="winning-goal",
        )
        service = HighlightShareService(session=session, storage_service=storage_service)

        export, asset = service.generate_export(
            actor=actor,
            payload=HighlightShareExportRequest(
                source_storage_key=source.storage_key,
                match_key="friendly-101",
                template_code="social-square",
                scoreline={"home": 2, "away": 1},
                club_names={"home": "Harbor FC", "away": "Dock FC"},
                share_title="Harbor FC late winner",
            ),
        )

        assert export.metadata_json["template"]["code"] == "social-square"
        assert export.metadata_json["branding"]["watermark_label"] == "GTEX"
        assert export.metadata_json["overlays"]["scoreline"] is True
        assert export.metadata_json["overlays"]["club_names"] is True
        assert export.metadata_json["overlays"]["match_metadata_card"] is True
        assert asset.content_type == "application/zip"

    engine.dispose()


def test_highlight_share_export_package_contains_manifest_and_clip(tmp_path: Path) -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        actor = _create_user(session, user_id="share-user-2")
        storage_service = _storage(tmp_path)
        source = storage_service.store_temporary_highlight(
            match_key="friendly-202",
            content=b"clip-binary",
            content_type="video/mp4",
            clip_label="counter-attack",
        )
        service = HighlightShareService(session=session, storage_service=storage_service)

        export, asset = service.generate_export(
            actor=actor,
            payload=HighlightShareExportRequest(
                source_storage_key=source.storage_key,
                match_key="friendly-202",
                aspect_ratio="9:16",
                watermark_label="GTEX Viral",
                share_caption="Post this one everywhere.",
            ),
        )

        package_bytes = storage_service.storage.get_bytes(key=asset.storage_key)
        with ZipFile(BytesIO(package_bytes)) as archive:
            names = set(archive.namelist())
            manifest = json.loads(archive.read("manifest.json"))

        assert "manifest.json" in names
        assert "clip.mp4" in names
        assert manifest["branding"]["watermark_label"] == "GTEX Viral"
        assert manifest["share_package"]["share_caption"] == "Post this one everywhere."
        assert export.aspect_ratio == "9:16"

    engine.dispose()


def test_highlight_share_amplification_publishes_story_and_lists_history(tmp_path: Path) -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        actor = _create_user(session, user_id="share-user-3")
        storage_service = _storage(tmp_path)
        source = storage_service.store_temporary_highlight(
            match_key="cup-303",
            content=b"viral-highlight",
            content_type="video/mp4",
            clip_label="top-corner",
        )
        service = HighlightShareService(session=session, storage_service=storage_service)

        export, _asset = service.generate_export(
            actor=actor,
            payload=HighlightShareExportRequest(
                source_storage_key=source.storage_key,
                match_key="cup-303",
                template_code="social-vertical",
                share_title="Top-corner finish",
                share_caption="This one is already going viral.",
            ),
        )
        amplification = service.amplify_export(
            actor=actor,
            export_id=export.id,
            payload=HighlightShareAmplificationRequest(
                channel="story_feed",
                subject_type="club_sale_transfer",
                subject_id="club_transfer_demo",
                featured=True,
                metadata_json={"campaign": "transfer-window"},
            ),
        )
        story = session.get(StoryFeedItem, amplification.story_feed_item_id)
        listed_exports = service.list_exports(actor=actor)
        listed_amplifications = service.list_amplifications(actor=actor, export_id=export.id)

        assert story is not None
        assert story.story_type == "viral_highlight"
        assert story.subject_type == "club_sale_transfer"
        assert story.subject_id == "club_transfer_demo"
        assert listed_exports[0].id == export.id
        assert listed_amplifications[0].id == amplification.id
        assert amplification.metadata_json["story_type"] == "viral_highlight"

    engine.dispose()
