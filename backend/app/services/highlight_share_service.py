from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.highlight_share import HighlightShareAmplification, HighlightShareExport, HighlightShareTemplate
from app.models.user import User
from app.services.sponsorship_placement_service import SponsorshipPlacementService
from app.services.storage_media_service import MediaAssetDescriptor, MediaStorageService
from app.story_feed_engine.service import StoryFeedService


DEFAULT_SHARE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "code": "social-landscape",
        "name": "Social Landscape",
        "description": "16:9 export tuned for feed posts and video shares.",
        "aspect_ratio": "16:9",
        "overlay_defaults_json": {"watermark": True, "scoreline": True, "club_names": True, "match_metadata_card": True},
        "metadata_json": {"mobile_friendly": True},
    },
    {
        "code": "social-square",
        "name": "Social Square",
        "description": "1:1 export tuned for feed crops and reposts.",
        "aspect_ratio": "1:1",
        "overlay_defaults_json": {"watermark": True, "scoreline": True, "club_names": True, "match_metadata_card": True},
        "metadata_json": {"mobile_friendly": True},
    },
    {
        "code": "social-vertical",
        "name": "Social Vertical",
        "description": "9:16 export tuned for stories and mobile-first share flows.",
        "aspect_ratio": "9:16",
        "overlay_defaults_json": {"watermark": True, "scoreline": True, "club_names": True, "match_metadata_card": True},
        "metadata_json": {"mobile_friendly": True},
    },
)


class HighlightShareError(ValueError):
    pass


@dataclass(slots=True)
class HighlightShareService:
    session: Session
    storage_service: MediaStorageService
    placement_service: SponsorshipPlacementService | None = None

    def seed_default_templates(self) -> list[HighlightShareTemplate]:
        created: list[HighlightShareTemplate] = []
        for item in DEFAULT_SHARE_TEMPLATES:
            existing = self.session.scalar(select(HighlightShareTemplate).where(HighlightShareTemplate.code == item["code"]))
            if existing is not None:
                created.append(existing)
                continue
            template = HighlightShareTemplate(**item, is_active=True)
            self.session.add(template)
            self.session.flush()
            created.append(template)
        return created

    def list_templates(self, *, active_only: bool = True) -> list[HighlightShareTemplate]:
        self.seed_default_templates()
        stmt = select(HighlightShareTemplate).order_by(HighlightShareTemplate.created_at.asc())
        if active_only:
            stmt = stmt.where(HighlightShareTemplate.is_active.is_(True))
        return list(self.session.scalars(stmt).all())

    def list_exports(self, *, actor: User, match_key: str | None = None, limit: int = 50) -> list[HighlightShareExport]:
        stmt = select(HighlightShareExport).where(HighlightShareExport.user_id == actor.id)
        if match_key:
            stmt = stmt.where(HighlightShareExport.match_key == match_key)
        stmt = stmt.order_by(HighlightShareExport.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def generate_export(self, *, actor: User, payload) -> tuple[HighlightShareExport, MediaAssetDescriptor]:
        template = self._resolve_template(template_code=payload.template_code, aspect_ratio=payload.aspect_ratio)
        source = self.storage_service.describe(storage_key=payload.source_storage_key)
        source_bytes = self.storage_service.storage.get_bytes(key=payload.source_storage_key)

        placements = []
        if self.placement_service is not None and payload.include_sponsor_overlay:
            placements = self.placement_service.resolve_placements(
                home_club_id=payload.home_club_id,
                away_club_id=payload.away_club_id,
                competition_id=payload.competition_key,
                stage_name=payload.stage_name,
                region_code=payload.region_code,
                surfaces=("highlight_overlay",),
            )

        sponsor_overlay = None
        if placements:
            sponsor_overlay = {
                "sponsor_name": placements[0].sponsor_name,
                "source": placements[0].source,
                "creative_url": placements[0].creative_url,
            }

        manifest = self._build_manifest(template=template, payload=payload, source=source, sponsor_overlay=sponsor_overlay)
        package = self._build_package(source=source, source_bytes=source_bytes, manifest=manifest)
        asset = self.storage_service.store_export_package(
            match_key=payload.match_key,
            content=package,
            content_type="application/zip",
            export_label=template.code,
            metadata={
                "template_code": template.code,
                "aspect_ratio": template.aspect_ratio,
                "share_title": manifest["share_package"]["share_title"],
                "kind": "highlight_share_export",
            },
        )
        manifest["export_asset"] = {
            "storage_key": asset.storage_key,
            "content_type": asset.content_type,
            "size_bytes": asset.size_bytes,
            "metadata": dict(asset.metadata or {}),
        }
        export = HighlightShareExport(
            user_id=actor.id,
            template_id=template.id,
            match_key=payload.match_key,
            source_storage_key=payload.source_storage_key,
            export_storage_key=asset.storage_key,
            status="generated",
            aspect_ratio=template.aspect_ratio,
            watermark_label=manifest["branding"]["watermark_label"],
            share_title=manifest["share_package"]["share_title"],
            metadata_json=manifest,
        )
        self.session.add(export)
        self.session.flush()
        return export, asset

    def amplify_export(self, *, actor: User, export_id: str, payload) -> HighlightShareAmplification:
        export = self.session.get(HighlightShareExport, export_id)
        if export is None or export.user_id != actor.id:
            raise HighlightShareError("Highlight share export was not found.")
        manifest = dict(export.metadata_json or {})
        share_package = dict(manifest.get("share_package") or {})
        title = (payload.title or export.share_title or share_package.get("share_title") or f"GTEX Highlight | {export.match_key}").strip()
        caption = payload.caption or share_package.get("share_caption")
        subject_type = payload.subject_type or "highlight_share_export"
        subject_id = payload.subject_id or export.id
        story_type = "viral_highlight" if payload.channel.strip().lower() == "story_feed" else "highlight_amplification"
        story_item = StoryFeedService(self.session).publish(
            story_type=story_type,
            title=title,
            body=caption or title,
            subject_type=subject_type,
            subject_id=subject_id,
            country_code=payload.country_code,
            metadata_json={
                "export_id": export.id,
                "match_key": export.match_key,
                "aspect_ratio": export.aspect_ratio,
                "template_code": manifest.get("template", {}).get("code"),
                "storage_key": export.export_storage_key,
                **dict(payload.metadata_json),
            },
            featured=payload.featured,
            published_by_user_id=actor.id,
        )
        amplification = HighlightShareAmplification(
            export_id=export.id,
            user_id=actor.id,
            story_feed_item_id=story_item.id,
            channel=payload.channel.strip().lower(),
            status="published",
            subject_type=subject_type.strip().lower() if subject_type else None,
            subject_id=subject_id,
            title=title,
            caption=caption,
            metadata_json={
                "story_type": story_type,
                "country_code": payload.country_code,
                **dict(payload.metadata_json),
            },
        )
        self.session.add(amplification)
        self.session.flush()
        return amplification

    def list_amplifications(self, *, actor: User, export_id: str, limit: int = 50) -> list[HighlightShareAmplification]:
        export = self.session.get(HighlightShareExport, export_id)
        if export is None or export.user_id != actor.id:
            raise HighlightShareError("Highlight share export was not found.")
        stmt = (
            select(HighlightShareAmplification)
            .where(HighlightShareAmplification.export_id == export.id)
            .order_by(HighlightShareAmplification.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def _resolve_template(self, *, template_code: str | None, aspect_ratio: str | None) -> HighlightShareTemplate:
        self.seed_default_templates()
        if template_code:
            template = self.session.scalar(select(HighlightShareTemplate).where(HighlightShareTemplate.code == template_code))
            if template is None:
                raise HighlightShareError("Highlight share template was not found.")
            return template
        if aspect_ratio:
            template = self.session.scalar(
                select(HighlightShareTemplate).where(
                    HighlightShareTemplate.aspect_ratio == aspect_ratio,
                    HighlightShareTemplate.is_active.is_(True),
                )
            )
            if template is not None:
                return template
        template = self.session.scalar(
            select(HighlightShareTemplate).where(HighlightShareTemplate.code == "social-landscape")
        )
        if template is None:
            raise HighlightShareError("No default highlight share template is available.")
        return template

    def _build_manifest(
        self,
        *,
        template: HighlightShareTemplate,
        payload,
        source: MediaAssetDescriptor,
        sponsor_overlay: dict[str, Any] | None,
    ) -> dict[str, Any]:
        defaults = dict(template.overlay_defaults_json or {})
        scoreline = payload.scoreline or {}
        club_names = payload.club_names or {}
        share_title = payload.share_title or f"GTEX Highlight | {payload.match_key}"
        share_caption = payload.share_caption or "Share the moment. Discover the full match on GTEX."
        return {
            "template": {
                "code": template.code,
                "name": template.name,
                "aspect_ratio": template.aspect_ratio,
                "mobile_friendly": bool((template.metadata_json or {}).get("mobile_friendly", False)),
            },
            "source_asset": {
                "storage_key": source.storage_key,
                "content_type": source.content_type,
                "size_bytes": source.size_bytes,
                "metadata": dict(source.metadata or {}),
            },
            "branding": {
                "watermark_enabled": bool(payload.enable_watermark and defaults.get("watermark", True)),
                "watermark_label": payload.watermark_label or "GTEX",
            },
            "overlays": {
                "scoreline": bool(payload.include_scoreline_overlay and defaults.get("scoreline", True)),
                "club_names": bool(payload.include_club_name_overlay and defaults.get("club_names", True)),
                "match_metadata_card": bool(payload.include_match_metadata_card and defaults.get("match_metadata_card", True)),
                "scoreline_payload": scoreline,
                "club_names_payload": club_names,
                "sponsor_overlay": sponsor_overlay,
            },
            "match_metadata": {
                "match_key": payload.match_key,
                "competition_key": payload.competition_key,
                "stage_name": payload.stage_name,
                "home_club_id": payload.home_club_id,
                "away_club_id": payload.away_club_id,
                "region_code": payload.region_code,
                "rivalry_visibility": payload.rivalry_visibility,
            },
            "share_package": {
                "share_title": share_title,
                "share_caption": share_caption,
                "social_tags": ["GTEX", "football", "highlights"],
                "filename_stub": f"{payload.match_key}-{template.aspect_ratio.replace(':', 'x')}",
            },
        }

    def _build_package(self, *, source: MediaAssetDescriptor, source_bytes: bytes, manifest: dict[str, Any]) -> bytes:
        suffix = source.storage_key.split("/")[-1]
        extension = suffix.split(".")[-1] if "." in suffix else "bin"
        buffer = BytesIO()
        with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.writestr(f"clip.{extension}", source_bytes)
            archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True, indent=2))
        return buffer.getvalue()


__all__ = ["HighlightShareError", "HighlightShareService"]
