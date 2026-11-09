from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from decimal import Decimal
import hashlib
import hmac
import logging
import math
import os
import re
import struct
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.ads_engine.commercial_schemas import (
    AdPlacementSpecAdminUpdateRequest,
    AdPlacementSpecView,
    AdPricingPackageAdminUpsertRequest,
    AdPricingPackageView,
    AdminCampaignModerationRequest,
    AdminWorkspaceActionRequest,
    AdvertiserClientBrandCreateRequest,
    AdvertiserClientBrandView,
    AdvertiserLoginRequest,
    AdvertiserMediaAssetView,
    AdvertiserMemberInviteRequest,
    AdvertiserMemberView,
    AdvertiserRegisterRequest,
    AdvertiserWorkspaceUpdateRequest,
    AdvertiserWorkspaceView,
    BrandCampaignWizardCreateRequest,
    CommercialCampaignView,
    CommercialPriceCalculationRequest,
    CommercialPriceCalculationResponse,
    InvoiceView,
    MusicPromotionWizardCreateRequest,
    MusicRotationFeedResponse,
    MusicRotationTrackView,
    PaymentInitiateRequest,
    PaymentRecordView,
    RefundCreateRequest,
    RefundRecordView,
    SubscriptionActionRequest,
    SubscriptionView,
    format_ngn_from_minor,
)
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
from app.models.commercial_network import (
    AdPlacementSpec,
    AdPricingPackage,
    AdvertiserClientBrand,
    AdvertiserInvoice,
    AdvertiserMediaAsset,
    AdvertiserPaymentRecord,
    AdvertiserRefundRecord,
    AdvertiserSubscription,
    AdvertiserWebhookEvent,
    AdvertiserWorkspace,
    AdvertiserWorkspaceMember,
    CommercialAuditLog,
)
from app.models.user import PublicAccountType, User, UserRole


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _vat_inclusive_minor(total_minor: int) -> int:
    """VAT portion included in a VAT-inclusive total.

    Rate comes from GTEX_ADS_VAT_PERCENT (default 0 until finance confirms; Nigerian VAT is 7.5).
    """
    try:
        rate = Decimal(os.getenv("GTEX_ADS_VAT_PERCENT", "0"))
    except Exception:
        rate = Decimal("0")
    if rate <= 0:
        return 0
    net = Decimal(total_minor) / (Decimal(1) + rate / Decimal(100))
    return int((Decimal(total_minor) - net).to_integral_value())


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _env_minor_ngn(env_key: str) -> int | None:
    raw = os.getenv(env_key, "").strip()
    if not raw:
        return None
    try:
        val = int(raw)
        return val if val >= 0 else None
    except ValueError:
        return None


DEFAULT_PLACEMENT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "placement_key": "public_homepage",
        "name": "Public Homepage Spotlight & Banner",
        "division": "brand",
        "category": "Public Website",
        "description": "High-impact silent visual placement on the public GTEX homepage.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp", "video/mp4", "video/webm"],
        "aspect_ratio": "16:9",
        "recommended_width": 1920,
        "recommended_height": 1080,
        "max_file_size_bytes": 25 * 1024 * 1024,
        "max_duration_seconds": 30,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_PUBLIC_HOMEPAGE_KOBO",
        "frequency_cap_per_session": 12,
        "rotation_interval_seconds": 25,
        "priority_weight": 150,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "login_page",
        "name": "Login Page Canvas",
        "division": "brand",
        "category": "Authentication Surfaces",
        "description": "Brand showcase alongside the GTEX authentication sign-in experience.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp", "video/mp4"],
        "aspect_ratio": "16:9",
        "recommended_width": 1280,
        "recommended_height": 720,
        "max_file_size_bytes": 15 * 1024 * 1024,
        "max_duration_seconds": 20,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_LOGIN_PAGE_KOBO",
        "frequency_cap_per_session": 8,
        "rotation_interval_seconds": 30,
        "priority_weight": 120,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "registration_page",
        "name": "Registration Page Canvas",
        "division": "brand",
        "category": "Authentication Surfaces",
        "description": "Brand showcase on the public account registration onboarding screen.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp", "video/mp4"],
        "aspect_ratio": "16:9",
        "recommended_width": 1280,
        "recommended_height": 720,
        "max_file_size_bytes": 15 * 1024 * 1024,
        "max_duration_seconds": 20,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_REGISTRATION_PAGE_KOBO",
        "frequency_cap_per_session": 8,
        "rotation_interval_seconds": 30,
        "priority_weight": 120,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "gtex_application",
        "name": "GTEX Application Banner",
        "division": "brand",
        "category": "In-App Surfaces",
        "description": "Banner placement inside the core GTEX football & club application.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp", "video/mp4"],
        "aspect_ratio": "16:9",
        "recommended_width": 1280,
        "recommended_height": 720,
        "max_file_size_bytes": 15 * 1024 * 1024,
        "max_duration_seconds": 20,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_APPLICATION_KOBO",
        "frequency_cap_per_session": 15,
        "rotation_interval_seconds": 30,
        "priority_weight": 110,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "sponsored_cards",
        "name": "Sponsored In-App Cards",
        "division": "brand",
        "category": "In-App Surfaces",
        "description": "Native sponsored partner cards across GTEX discovery and hub feeds.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp"],
        "aspect_ratio": "4:3",
        "recommended_width": 1200,
        "recommended_height": 900,
        "max_file_size_bytes": 10 * 1024 * 1024,
        "max_duration_seconds": None,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_SPONSORED_CARDS_KOBO",
        "frequency_cap_per_session": 20,
        "rotation_interval_seconds": 45,
        "priority_weight": 100,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "match_sponsor_id",
        "name": "Match Sponsor Identification",
        "division": "brand",
        "category": "Live Match Broadcast",
        "description": "Persistent, discreet 'Sponsored by' brand identification badge on the live match broadcast header.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp"],
        "aspect_ratio": "4:1",
        "recommended_width": 800,
        "recommended_height": 200,
        "max_file_size_bytes": 10 * 1024 * 1024,
        "max_duration_seconds": None,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_MATCH_SPONSOR_ID_KOBO",
        "frequency_cap_per_session": 25,
        "rotation_interval_seconds": 60,
        "priority_weight": 180,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "live_match_panel",
        "name": "Live Match Silent Advertising Panel",
        "division": "brand",
        "category": "Live Match Broadcast",
        "description": "Split-screen / side-by-side silent broadcast advertising panel during active matches.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp", "video/mp4", "video/webm"],
        "aspect_ratio": "16:9",
        "recommended_width": 1280,
        "recommended_height": 720,
        "max_file_size_bytes": 25 * 1024 * 1024,
        "max_duration_seconds": 30,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_LIVE_MATCH_PANEL_KOBO",
        "frequency_cap_per_session": 20,
        "rotation_interval_seconds": 30,
        "priority_weight": 190,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "halftime_sponsorship",
        "name": "Halftime Broadcast Sponsorship",
        "division": "brand",
        "category": "Live Match Broadcast",
        "description": "Prominent halftime interval sponsorship showcase displayed when matches enter halftime.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp", "video/mp4", "video/webm"],
        "aspect_ratio": "16:9",
        "recommended_width": 1920,
        "recommended_height": 1080,
        "max_file_size_bytes": 25 * 1024 * 1024,
        "max_duration_seconds": 45,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_HALFTIME_KOBO",
        "frequency_cap_per_session": 10,
        "rotation_interval_seconds": 20,
        "priority_weight": 200,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "stadium_perimeter",
        "name": "Digital Perimeter Stadium Advertising",
        "division": "brand",
        "category": "Live Match Broadcast",
        "description": "Digital LED perimeter pitchside boards inside supported 2.5D and 3D match renderers.",
        "supported_media_types_json": ["image/png", "image/jpeg", "image/webp"],
        "aspect_ratio": "8:1",
        "recommended_width": 1600,
        "recommended_height": 200,
        "max_file_size_bytes": 10 * 1024 * 1024,
        "max_duration_seconds": None,
        "requires_silent_media": True,
        "env_rate_key": "GTEX_AD_RATE_STADIUM_PERIMETER_KOBO",
        "frequency_cap_per_session": 30,
        "rotation_interval_seconds": 30,
        "priority_weight": 170,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
    {
        "placement_key": "music_rotation",
        "name": "GTEX Global Music Player Rotation",
        "division": "music",
        "category": "GTEX Music Network",
        "description": "Fair-rotation audio promotion across the global GTEX background music player (Homepage, App, Club HQ, Halftime & Post-Match).",
        "supported_media_types_json": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/aac"],
        "aspect_ratio": "1:1",
        "recommended_width": 1000,
        "recommended_height": 1000,
        "max_file_size_bytes": 50 * 1024 * 1024,
        "max_duration_seconds": 420,
        "requires_silent_media": False,
        "env_rate_key": "GTEX_AD_RATE_MUSIC_ROTATION_KOBO",
        "frequency_cap_per_session": 6,
        "rotation_interval_seconds": 180,
        "priority_weight": 150,
        "device_compatibility_json": ["desktop", "mobile", "tablet"],
    },
)

DEFAULT_PRICING_PACKAGES: tuple[dict[str, Any], ...] = (
    {
        "package_code": "brand_7d",
        "name": "7-Day Brand Campaign",
        "division": "brand",
        "description": "Minimum 7-day brand advertising campaign on selected GTEX placements.",
        "duration_days": 7,
        "placement_keys_json": ["public_homepage"],
        "is_bundle": False,
        "is_subscription": False,
        "billing_interval_days": None,
        "env_price_key": "GTEX_AD_PKG_BRAND_7D_KOBO",
        "discount_percent": 0,
        "sort_order": 10,
    },
    {
        "package_code": "brand_14d",
        "name": "14-Day Multi-Week Brand Campaign",
        "division": "brand",
        "description": "2-week continuous brand presence across chosen GTEX commercial inventory.",
        "duration_days": 14,
        "placement_keys_json": ["public_homepage", "gtex_application"],
        "is_bundle": False,
        "is_subscription": False,
        "billing_interval_days": None,
        "env_price_key": "GTEX_AD_PKG_BRAND_14D_KOBO",
        "discount_percent": 5,
        "sort_order": 20,
    },
    {
        "package_code": "brand_30d",
        "name": "30-Day Brand Dominance Package",
        "division": "brand",
        "description": "Full 30-day brand campaign across web, application, and match broadcast surfaces.",
        "duration_days": 30,
        "placement_keys_json": ["public_homepage", "gtex_application", "live_match_panel", "halftime_sponsorship"],
        "is_bundle": True,
        "is_subscription": False,
        "billing_interval_days": None,
        "env_price_key": "GTEX_AD_PKG_BRAND_30D_KOBO",
        "discount_percent": 10,
        "sort_order": 30,
    },
    {
        "package_code": "brand_monthly_sub",
        "name": "Monthly Recurring Brand Subscription",
        "division": "brand",
        "description": "Auto-renewing 30-day monthly brand subscription in NGN with priority inventory access.",
        "duration_days": 30,
        "placement_keys_json": ["public_homepage", "gtex_application", "match_sponsor_id", "live_match_panel"],
        "is_bundle": True,
        "is_subscription": True,
        "billing_interval_days": 30,
        "env_price_key": "GTEX_AD_PKG_BRAND_SUB_KOBO",
        "discount_percent": 15,
        "sort_order": 40,
    },
    {
        "package_code": "music_7d",
        "name": "7-Day Music Promotion",
        "division": "music",
        "description": "7 days of verified promotional rotation in the GTEX Global Music Player.",
        "duration_days": 7,
        "placement_keys_json": ["music_rotation"],
        "is_bundle": False,
        "is_subscription": False,
        "billing_interval_days": None,
        "env_price_key": "GTEX_AD_PKG_MUSIC_7D_KOBO",
        "discount_percent": 0,
        "sort_order": 10,
    },
    {
        "package_code": "music_21d",
        "name": "21-Day Music Promotion",
        "division": "music",
        "description": "21 days of verified promotional rotation across GTEX Homepage, App, Halftime & Post-Match.",
        "duration_days": 21,
        "placement_keys_json": ["music_rotation"],
        "is_bundle": False,
        "is_subscription": False,
        "billing_interval_days": None,
        "env_price_key": "GTEX_AD_PKG_MUSIC_21D_KOBO",
        "discount_percent": 5,
        "sort_order": 20,
    },
    {
        "package_code": "music_30d",
        "name": "30-Day Music Promotion",
        "division": "music",
        "description": "30 days of high-frequency rotation in the GTEX Global Music Player.",
        "duration_days": 30,
        "placement_keys_json": ["music_rotation"],
        "is_bundle": False,
        "is_subscription": False,
        "billing_interval_days": None,
        "env_price_key": "GTEX_AD_PKG_MUSIC_30D_KOBO",
        "discount_percent": 10,
        "sort_order": 30,
    },
    {
        "package_code": "music_42d",
        "name": "42-Day Flagship Release Promotion",
        "division": "music",
        "description": "6-week flagship single/EP rotation campaign across the GTEX Music Network.",
        "duration_days": 42,
        "placement_keys_json": ["music_rotation"],
        "is_bundle": False,
        "is_subscription": False,
        "billing_interval_days": None,
        "env_price_key": "GTEX_AD_PKG_MUSIC_42D_KOBO",
        "discount_percent": 15,
        "sort_order": 40,
    },
    {
        "package_code": "music_monthly_sub",
        "name": "Monthly Recurring Music Rotation Subscription",
        "division": "music",
        "description": "Continuous 30-day recurring artist/label rotation subscription billed in NGN.",
        "duration_days": 30,
        "placement_keys_json": ["music_rotation"],
        "is_bundle": False,
        "is_subscription": True,
        "billing_interval_days": 30,
        "env_price_key": "GTEX_AD_PKG_MUSIC_SUB_KOBO",
        "discount_percent": 15,
        "sort_order": 50,
    },
)


# Map legacy placement keys to new placement keys and vice versa so both delivery queries match seamlessly.
PLACEMENT_EQUIVALENCE_MAP: dict[str, tuple[str, ...]] = {
    "public_homepage": ("public_homepage", "homepage_hero", "homepage_rail", "partner_showcase"),
    "homepage_hero": ("homepage_hero", "public_homepage"),
    "homepage_rail": ("homepage_rail", "public_homepage", "gtex_application"),
    "partner_showcase": ("partner_showcase", "public_homepage", "sponsored_cards"),
    "login_page": ("login_page", "auth_canvas"),
    "registration_page": ("registration_page", "auth_canvas"),
    "auth_canvas": ("auth_canvas", "login_page", "registration_page"),
    "gtex_application": ("gtex_application", "homepage_rail"),
    "sponsored_cards": ("sponsored_cards", "partner_showcase"),
    "match_sponsor_id": ("match_sponsor_id",),
    "live_match_panel": ("live_match_panel",),
    "halftime_sponsorship": ("halftime_sponsorship",),
    "stadium_perimeter": ("stadium_perimeter",),
    "music_rotation": ("music_rotation", "music_track", "music_artist", "music_playlist"),
    "music_track": ("music_track", "music_rotation"),
    "music_artist": ("music_artist", "music_rotation"),
    "music_playlist": ("music_playlist", "music_rotation"),
}


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "upload.bin").strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return (cleaned or "asset")[:200]


def clean_track_title_from_filename(filename: str) -> str:
    base = os.path.basename(filename or "Untitled Track")
    stem, _ = os.path.splitext(base)
    cleaned = re.sub(r"[_-]+", " ", stem).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return (cleaned or "Untitled Track")[:180]


def inspect_and_validate_media_bytes(
    *,
    asset_kind: str,
    filename: str,
    declared_content_type: str | None,
    data: bytes,
) -> dict[str, Any]:
    """Validate media magic bytes, size limits, dimensions, and silent-video requirements."""
    if not data:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uploaded media file is empty.")

    size_bytes = len(data)
    max_sizes = {
        "logo": 5 * 1024 * 1024,
        "brand_image": 15 * 1024 * 1024,
        "music_artwork": 10 * 1024 * 1024,
        "brand_video": 50 * 1024 * 1024,
        "music_audio": 50 * 1024 * 1024,
    }
    max_allowed = max_sizes.get(asset_kind, 15 * 1024 * 1024)
    if size_bytes > max_allowed:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({size_bytes} bytes) exceeds maximum allowed for {asset_kind} ({max_allowed} bytes).",
        )

    detected_mime: str | None = None
    width: int | None = None
    height: int | None = None
    has_audio_track = False
    is_silent_verified = True

    # 1. Check image magic bytes (PNG, JPEG, WebP)
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        detected_mime = "image/png"
        width, height = struct.unpack(">II", data[16:24])
    elif data.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
        width, height = _extract_jpeg_dimensions(data)
    elif len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        detected_mime = "image/webp"
        width, height = _extract_webp_dimensions(data)
    # 2. Check MP4 / M4A container (ftyp box)
    elif len(data) >= 12 and data[4:8] == b"ftyp":
        major_brand = data[8:12]
        if asset_kind == "music_audio" or major_brand in {b"M4A ", b"M4B "}:
            detected_mime = "audio/mp4"
            has_audio_track = True
            is_silent_verified = False
        else:
            detected_mime = "video/mp4"
            has_audio_track = _mp4_contains_audio_track(data)
            is_silent_verified = not has_audio_track
    # 3. Check WebM container (EBML magic)
    elif data.startswith(b"\x1a\x45\xdf\xa3"):
        detected_mime = "video/webm"
        has_audio_track = _webm_contains_audio_track(data)
        is_silent_verified = not has_audio_track
    # 4. Check Audio formats (MP3, WAV, OGG, AAC)
    elif data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        if len(data) >= 2 and data[0] == 0xFF and (data[1] in {0xF1, 0xF9}):
            detected_mime = "audio/aac"
        else:
            detected_mime = "audio/mpeg"
        has_audio_track = True
        is_silent_verified = False
    elif len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        detected_mime = "audio/wav"
        has_audio_track = True
        is_silent_verified = False
    elif data.startswith(b"OggS"):
        detected_mime = "audio/ogg"
        has_audio_track = True
        is_silent_verified = False

    if detected_mime is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported or corrupted media file format. Magic-byte verification failed.",
        )

    allowed_mimes_by_kind: dict[str, set[str]] = {
        "logo": {"image/png", "image/jpeg", "image/webp"},
        "brand_image": {"image/png", "image/jpeg", "image/webp"},
        "music_artwork": {"image/png", "image/jpeg", "image/webp"},
        "brand_video": {"video/mp4", "video/webm"},
        "music_audio": {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/aac"},
    }
    expected_set = allowed_mimes_by_kind.get(asset_kind, set())
    if detected_mime not in expected_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid media format '{detected_mime}' for {asset_kind}. Allowed: {', '.join(sorted(expected_set))}.",
        )

    # Enforce Critical Requirement #10: Brand video advertisements must be silent
    if asset_kind == "brand_video" and has_audio_track:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Visual advertisements on GTEX must be silent. The uploaded video contains an audio track; please upload a silent video creative.",
        )

    return {
        "mime_type": detected_mime,
        "size_bytes": size_bytes,
        "width": width,
        "height": height,
        "has_audio_track": has_audio_track,
        "is_silent_verified": is_silent_verified,
        "sha256_hash": hashlib.sha256(data).hexdigest(),
        "sanitized_filename": sanitize_filename(filename),
    }


def _extract_jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    idx = 2
    length = len(data)
    while idx < length - 9:
        if data[idx] != 0xFF:
            idx += 1
            continue
        marker = data[idx + 1]
        while marker == 0xFF and idx + 2 < length:
            idx += 1
            marker = data[idx + 1]
        if marker in {0xD8, 0xD9} or (0xD0 <= marker <= 0xD7):
            idx += 2
            continue
        if idx + 4 > length:
            break
        seg_len = struct.unpack(">H", data[idx + 2 : idx + 4])[0]
        if seg_len < 2:
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if idx + 9 <= length:
                height, width = struct.unpack(">HH", data[idx + 5 : idx + 9])
                return width, height
            break
        idx += 2 + seg_len
    return None, None


def _extract_webp_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if len(data) < 30:
        return None, None
    chunk = data[12:16]
    if chunk == b"VP8X" and len(data) >= 30:
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return w, h
    if chunk == b"VP8 " and len(data) >= 30:
        w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return w, h
    return None, None


def _mp4_contains_audio_track(data: bytes) -> bool:
    audio_markers = (b"soun", b"mp4a", b"ac-3", b"ec-3", b"Opus", b"samr", b"sawb")
    return any(marker in data for marker in audio_markers)


def _webm_contains_audio_track(data: bytes) -> bool:
    audio_markers = (b"A_OPUS", b"A_VORBIS", b"A_AAC", b"A_MPEG", b"A_PCM")
    return any(marker in data for marker in audio_markers)


class CommercialNetworkService:
    """Shared service for GTEX Brand Advertising and GTEX Music Promotion."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_default_catalog(self) -> None:
        """Seed default placement specs and NGN pricing package definitions if missing."""
        existing_placements = {row.placement_key for row in self.session.scalars(select(AdPlacementSpec)).all()}
        for spec_def in DEFAULT_PLACEMENT_SPECS:
            if spec_def["placement_key"] in existing_placements:
                continue
            rate = _env_minor_ngn(spec_def["env_rate_key"])
            self.session.add(
                AdPlacementSpec(
                    placement_key=spec_def["placement_key"],
                    name=spec_def["name"],
                    division=spec_def["division"],
                    category=spec_def["category"],
                    description=spec_def["description"],
                    supported_media_types_json=list(spec_def["supported_media_types_json"]),
                    aspect_ratio=spec_def["aspect_ratio"],
                    recommended_width=spec_def["recommended_width"],
                    recommended_height=spec_def["recommended_height"],
                    max_file_size_bytes=spec_def["max_file_size_bytes"],
                    max_duration_seconds=spec_def["max_duration_seconds"],
                    requires_silent_media=spec_def["requires_silent_media"],
                    weekly_rate_minor_ngn=rate,
                    is_enabled=True,
                    delivery_surface_ready=True,
                    frequency_cap_per_session=spec_def["frequency_cap_per_session"],
                    rotation_interval_seconds=spec_def["rotation_interval_seconds"],
                    priority_weight=spec_def["priority_weight"],
                    device_compatibility_json=list(spec_def["device_compatibility_json"]),
                )
            )

        existing_packages = {row.package_code for row in self.session.scalars(select(AdPricingPackage)).all()}
        for pkg_def in DEFAULT_PRICING_PACKAGES:
            if pkg_def["package_code"] in existing_packages:
                continue
            price = _env_minor_ngn(pkg_def["env_price_key"])
            self.session.add(
                AdPricingPackage(
                    package_code=pkg_def["package_code"],
                    name=pkg_def["name"],
                    division=pkg_def["division"],
                    description=pkg_def["description"],
                    duration_days=pkg_def["duration_days"],
                    placement_keys_json=list(pkg_def["placement_keys_json"]),
                    is_bundle=pkg_def["is_bundle"],
                    is_subscription=pkg_def["is_subscription"],
                    billing_interval_days=pkg_def["billing_interval_days"],
                    price_minor_ngn=price,
                    currency="NGN",
                    discount_percent=pkg_def["discount_percent"],
                    is_active=True,
                    sort_order=pkg_def["sort_order"],
                )
            )
        self.session.flush()

    def record_audit_log(
        self,
        *,
        actor_user_id: str | None,
        workspace_id: str | None = None,
        campaign_id: str | None = None,
        entity_type: str,
        entity_id: str,
        action: str,
        note: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> CommercialAuditLog:
        entry = CommercialAuditLog(
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            note=note,
            metadata_json=metadata_json or {},
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    # ------------------------------------------------------------------
    # Advertiser Authentication & Workspace Management
    # ------------------------------------------------------------------
    def register_advertiser(
        self,
        payload: AdvertiserRegisterRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, AdvertiserWorkspace, Any]:
        from app.auth.service import AuthError, AuthService, DuplicateUserError

        auth_service = AuthService()
        base_handle = re.sub(r"[^a-z0-9._-]+", "", payload.email.split("@", 1)[0].lower())[:32] or "advertiser"
        username = f"adv.{base_handle}.{uuid4().hex[:6]}"[:64]

        try:
            user = auth_service.register_user(
                self.session,
                email=payload.email,
                full_name=payload.contact_name or payload.company_name,
                phone_number=payload.phone_number,
                is_over_18=True,
                username=username,
                password=payload.password,
                display_name=payload.company_name,
                role=UserRole.ADVERTISER,
                account_type=PublicAccountType.ADVERTISER,
            )
        except DuplicateUserError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except AuthError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        workspace = AdvertiserWorkspace(
            owner_user_id=user.id,
            account_type=payload.account_type,
            company_name=payload.company_name,
            contact_name=payload.contact_name or payload.company_name,
            contact_email=payload.email,
            contact_phone=payload.phone_number,
            website_url=payload.website_url,
            stage_name=payload.stage_name,
            label_name=payload.label_name,
            status="active",
            default_currency="NGN",
        )
        self.session.add(workspace)
        self.session.flush()

        member = AdvertiserWorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            invited_email=user.email,
            role="owner",
            status="active",
            permissions_json=["manage_workspace", "manage_campaigns", "manage_billing", "view_reports", "manage_team"],
        )
        self.session.add(member)

        # Sync legacy BrandAdvertiserProfile for backwards compatibility
        legacy_profile = self.session.scalar(
            select(BrandAdvertiserProfile).where(BrandAdvertiserProfile.user_id == user.id)
        )
        if legacy_profile is None:
            self.session.add(
                BrandAdvertiserProfile(
                    user_id=user.id,
                    company_name=payload.company_name[:160],
                    contact_name=(payload.contact_name or payload.company_name)[:160],
                    website_url=payload.website_url,
                    billing_email=payload.email,
                )
            )

        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            entity_type="advertiser_workspace",
            entity_id=workspace.id,
            action="registered",
            metadata_json={"account_type": payload.account_type, "company_name": payload.company_name},
        )
        issued_session = auth_service.issue_session_tokens(
            user,
            session=self.session,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.commit()
        return user, workspace, issued_session

    def login_advertiser(
        self,
        payload: AdvertiserLoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[User, AdvertiserWorkspace, Any]:
        from app.auth.service import AuthError, AuthService, InvalidCredentialsError

        auth_service = AuthService()
        try:
            user = auth_service.authenticate_user(
                self.session,
                email=payload.email,
                password=payload.password,
            )
        except (InvalidCredentialsError, AuthError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        workspace = self.resolve_workspace_for_user(user, auto_provision_if_advertiser=True)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account does not have an Advertiser Workspace. Please register a dedicated advertiser account at /advertiser/register.",
            )
        if workspace.status == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Advertiser workspace is suspended: {workspace.suspended_reason or 'Contact GTEX Commercial Support.'}",
            )

        issued_session = auth_service.issue_session_tokens(
            user,
            session=self.session,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.commit()
        return user, workspace, issued_session

    def resolve_workspace_for_user(
        self,
        user: User,
        *,
        auto_provision_if_advertiser: bool = True,
    ) -> AdvertiserWorkspace | None:
        owned = self.session.scalar(
            select(AdvertiserWorkspace)
            .where(AdvertiserWorkspace.owner_user_id == user.id)
            .order_by(AdvertiserWorkspace.created_at.asc())
        )
        if owned is not None:
            return owned

        member_row = self.session.scalar(
            select(AdvertiserWorkspaceMember)
            .where(
                or_(
                    AdvertiserWorkspaceMember.user_id == user.id,
                    AdvertiserWorkspaceMember.invited_email == user.email.lower(),
                ),
                AdvertiserWorkspaceMember.status.in_(("active", "invited")),
            )
            .order_by(AdvertiserWorkspaceMember.created_at.asc())
        )
        if member_row is not None:
            if member_row.user_id is None:
                member_row.user_id = user.id
                member_row.status = "active"
                self.session.flush()
            return self.session.get(AdvertiserWorkspace, member_row.workspace_id)

        # Preserve & migrate legacy BrandAdvertiserProfile rows automatically
        legacy_profile = self.session.scalar(
            select(BrandAdvertiserProfile).where(BrandAdvertiserProfile.user_id == user.id)
        )
        if legacy_profile is not None or (
            auto_provision_if_advertiser
            and (
                user.account_type == PublicAccountType.ADVERTISER
                or user.role in {UserRole.ADVERTISER, UserRole.ADMIN, UserRole.SUPER_ADMIN}
            )
        ):
            company = (
                legacy_profile.company_name
                if legacy_profile is not None
                else (user.display_name or user.full_name or user.username)
            )
            workspace = AdvertiserWorkspace(
                owner_user_id=user.id,
                account_type="business",
                company_name=company[:180],
                contact_name=(legacy_profile.contact_name if legacy_profile else user.full_name or company)[:160],
                contact_email=legacy_profile.billing_email if legacy_profile else user.email,
                contact_phone=user.phone_number or "",
                website_url=legacy_profile.website_url if legacy_profile else None,
                status="active",
                default_currency="NGN",
            )
            self.session.add(workspace)
            self.session.flush()
            self.session.add(
                AdvertiserWorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    invited_email=user.email,
                    role="owner",
                    status="active",
                    permissions_json=[
                        "manage_workspace",
                        "manage_campaigns",
                        "manage_billing",
                        "view_reports",
                        "manage_team",
                    ],
                )
            )
            self.session.flush()
            return workspace

        return None

    def require_active_workspace(self, user: User) -> AdvertiserWorkspace:
        workspace = self.resolve_workspace_for_user(user, auto_provision_if_advertiser=True)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dedicated GTEX Commercial Network workspace is required.",
            )
        if workspace.status == "suspended":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Advertiser workspace is suspended: {workspace.suspended_reason or 'Contact support.'}",
            )
        return workspace

    def serialize_workspace(self, workspace: AdvertiserWorkspace) -> AdvertiserWorkspaceView:
        logo_url = f"/api/v2/public/ads/media/{workspace.logo_asset_id}" if workspace.logo_asset_id else None
        return AdvertiserWorkspaceView(
            id=workspace.id,
            owner_user_id=workspace.owner_user_id,
            account_type=workspace.account_type,
            company_name=workspace.company_name,
            contact_name=workspace.contact_name,
            contact_email=workspace.contact_email,
            contact_phone=workspace.contact_phone,
            website_url=workspace.website_url,
            logo_asset_id=workspace.logo_asset_id,
            logo_url=logo_url,
            stage_name=workspace.stage_name,
            label_name=workspace.label_name,
            status=workspace.status,
            verified_at=_as_utc(workspace.verified_at),
            suspended_reason=workspace.suspended_reason,
            default_currency=workspace.default_currency,
            created_at=_as_utc(workspace.created_at) or _utcnow(),
            updated_at=_as_utc(workspace.updated_at) or _utcnow(),
        )

    def update_workspace(
        self,
        user: User,
        payload: AdvertiserWorkspaceUpdateRequest,
    ) -> AdvertiserWorkspaceView:
        workspace = self.require_active_workspace(user)
        updates = payload.model_dump(exclude_unset=True)
        if "logo_asset_id" in updates and updates["logo_asset_id"]:
            self._require_valid_asset(updates["logo_asset_id"], expected_kinds={"logo", "brand_image"})
        for key, val in updates.items():
            setattr(workspace, key, val)
        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            entity_type="advertiser_workspace",
            entity_id=workspace.id,
            action="updated",
            metadata_json=updates,
        )
        self.session.commit()
        self.session.refresh(workspace)
        return self.serialize_workspace(workspace)

    # ------------------------------------------------------------------
    # Agency Team Members & Client Brands
    # ------------------------------------------------------------------
    def list_members(self, user: User) -> list[AdvertiserMemberView]:
        workspace = self.require_active_workspace(user)
        rows = self.session.scalars(
            select(AdvertiserWorkspaceMember)
            .where(AdvertiserWorkspaceMember.workspace_id == workspace.id)
            .order_by(AdvertiserWorkspaceMember.created_at.asc())
        ).all()
        return [
            AdvertiserMemberView(
                id=row.id,
                workspace_id=row.workspace_id,
                user_id=row.user_id,
                invited_email=row.invited_email,
                role=row.role,
                status=row.status,
                permissions_json=list(row.permissions_json or []),
                created_at=_as_utc(row.created_at) or _utcnow(),
            )
            for row in rows
        ]

    def invite_member(
        self,
        user: User,
        payload: AdvertiserMemberInviteRequest,
    ) -> AdvertiserMemberView:
        workspace = self.require_active_workspace(user)
        existing = self.session.scalar(
            select(AdvertiserWorkspaceMember).where(
                AdvertiserWorkspaceMember.workspace_id == workspace.id,
                AdvertiserWorkspaceMember.invited_email == payload.email,
            )
        )
        matched_user = self.session.scalar(select(User).where(User.email == payload.email))
        default_perms = {
            "owner": ["manage_workspace", "manage_campaigns", "manage_billing", "view_reports", "manage_team"],
            "admin": ["manage_workspace", "manage_campaigns", "manage_billing", "view_reports", "manage_team"],
            "campaign_manager": ["manage_campaigns", "view_reports"],
            "billing": ["manage_billing", "view_reports"],
            "analyst": ["view_reports"],
        }
        resolved_perms = payload.permissions or default_perms.get(payload.role, ["view_reports"])
        if existing is not None:
            existing.role = payload.role
            existing.status = "active" if matched_user else "invited"
            existing.user_id = matched_user.id if matched_user else existing.user_id
            existing.permissions_json = resolved_perms
            row = existing
        else:
            row = AdvertiserWorkspaceMember(
                workspace_id=workspace.id,
                user_id=matched_user.id if matched_user else None,
                invited_email=payload.email,
                role=payload.role,
                status="active" if matched_user else "invited",
                permissions_json=resolved_perms,
                invited_by_user_id=user.id,
            )
            self.session.add(row)
        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            entity_type="workspace_member",
            entity_id=payload.email,
            action="invited_member",
            metadata_json={"role": payload.role, "email": payload.email},
        )
        self.session.commit()
        self.session.refresh(row)
        return AdvertiserMemberView(
            id=row.id,
            workspace_id=row.workspace_id,
            user_id=row.user_id,
            invited_email=row.invited_email,
            role=row.role,
            status=row.status,
            permissions_json=list(row.permissions_json or []),
            created_at=_as_utc(row.created_at) or _utcnow(),
        )

    def list_client_brands(self, user: User) -> list[AdvertiserClientBrandView]:
        workspace = self.require_active_workspace(user)
        rows = self.session.scalars(
            select(AdvertiserClientBrand)
            .where(AdvertiserClientBrand.workspace_id == workspace.id)
            .order_by(AdvertiserClientBrand.created_at.desc())
        ).all()
        return [
            AdvertiserClientBrandView(
                id=row.id,
                workspace_id=row.workspace_id,
                brand_name=row.brand_name,
                contact_name=row.contact_name,
                contact_email=row.contact_email,
                contact_phone=row.contact_phone,
                website_url=row.website_url,
                logo_asset_id=row.logo_asset_id,
                logo_url=f"/api/v2/public/ads/media/{row.logo_asset_id}" if row.logo_asset_id else None,
                industry=row.industry,
                is_active=row.is_active,
                created_at=_as_utc(row.created_at) or _utcnow(),
            )
            for row in rows
        ]

    def create_client_brand(
        self,
        user: User,
        payload: AdvertiserClientBrandCreateRequest,
    ) -> AdvertiserClientBrandView:
        workspace = self.require_active_workspace(user)
        if payload.logo_asset_id:
            self._require_valid_asset(payload.logo_asset_id, expected_kinds={"logo", "brand_image"})
        row = AdvertiserClientBrand(
            workspace_id=workspace.id,
            brand_name=payload.brand_name.strip(),
            contact_name=payload.contact_name,
            contact_email=payload.contact_email,
            contact_phone=payload.contact_phone,
            website_url=payload.website_url,
            logo_asset_id=payload.logo_asset_id,
            industry=payload.industry,
            is_active=True,
        )
        self.session.add(row)
        self.session.flush()
        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            entity_type="client_brand",
            entity_id=row.id,
            action="created",
            metadata_json={"brand_name": row.brand_name},
        )
        self.session.commit()
        self.session.refresh(row)
        return AdvertiserClientBrandView(
            id=row.id,
            workspace_id=row.workspace_id,
            brand_name=row.brand_name,
            contact_name=row.contact_name,
            contact_email=row.contact_email,
            contact_phone=row.contact_phone,
            website_url=row.website_url,
            logo_asset_id=row.logo_asset_id,
            logo_url=f"/api/v2/public/ads/media/{row.logo_asset_id}" if row.logo_asset_id else None,
            industry=row.industry,
            is_active=row.is_active,
            created_at=_as_utc(row.created_at) or _utcnow(),
        )

    def get_storage(self):
        from app.storage import get_default_object_storage

        return get_default_object_storage()

    # ------------------------------------------------------------------
    # Direct Media Upload & Validation
    # ------------------------------------------------------------------
    def upload_media_asset(
        self,
        *,
        user: User,
        asset_kind: str,
        filename: str,
        declared_content_type: str | None,
        data: bytes,
    ) -> AdvertiserMediaAssetView:
        workspace = self.require_active_workspace(user)
        inspected = inspect_and_validate_media_bytes(
            asset_kind=asset_kind,
            filename=filename,
            declared_content_type=declared_content_type,
            data=data,
        )

        storage_key = f"commercial/{workspace.id}/{asset_kind}/{uuid4().hex}_{inspected['sanitized_filename']}"
        try:
            storage = self.get_storage()
            storage_provider_name = "s3" if hasattr(storage, "bucket") else "local_disk"
            storage.put_bytes(
                key=storage_key,
                content=data,
                content_type=inspected["mime_type"],
                metadata={
                    "workspace_id": workspace.id,
                    "asset_kind": asset_kind,
                    "sha256": inspected["sha256_hash"],
                },
            )
        except Exception as storage_ex:
            logger.error("Durable object storage write failed for media upload: %s", storage_ex)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Durable object storage service is unavailable. Media upload cannot proceed.",
            )

        asset = AdvertiserMediaAsset(
            workspace_id=workspace.id,
            uploaded_by_user_id=user.id,
            asset_kind=asset_kind,
            original_filename=(filename or "upload")[:255],
            sanitized_filename=inspected["sanitized_filename"],
            mime_type=inspected["mime_type"],
            size_bytes=inspected["size_bytes"],
            sha256_hash=inspected["sha256_hash"],
            width=inspected["width"],
            height=inspected["height"],
            has_audio_track=inspected["has_audio_track"],
            is_silent_verified=inspected["is_silent_verified"],
            validation_status="valid",
            storage_provider=storage_provider_name,
            storage_key=storage_key,
            access_classification="public",
            data=None,  # Stored in durable object storage, not in DB!
            metadata_json={
                "declared_content_type": declared_content_type,
                "auto_track_title": clean_track_title_from_filename(filename) if asset_kind == "music_audio" else None,
            },
        )
        self.session.add(asset)
        self.session.flush()
        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            entity_type="media_asset",
            entity_id=asset.id,
            action="uploaded",
            metadata_json={
                "asset_kind": asset.asset_kind,
                "mime_type": asset.mime_type,
                "size_bytes": asset.size_bytes,
                "is_silent_verified": asset.is_silent_verified,
                "storage_key": storage_key,
            },
        )
        self.session.commit()
        self.session.refresh(asset)
        return self.serialize_media_asset(asset)

    def get_media_asset_bytes(self, asset: AdvertiserMediaAsset) -> bytes:
        """Retrieve media binary bytes with dual-read support (storage first, legacy DB BLOB fallback)."""
        if asset.storage_key:
            try:
                storage = self.get_storage()
                return storage.get_bytes(key=asset.storage_key)
            except Exception as ex:
                logger.warning("Object storage read failed for asset %s (%s): %s", asset.id, asset.storage_key, ex)
                if asset.data:
                    return bytes(asset.data)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Media asset binary not found in storage."
                )
        if asset.data:
            return bytes(asset.data)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset binary data not available.")

    def backfill_legacy_media_blobs(self) -> dict[str, Any]:
        """Idempotently migrate any legacy database BLOBs to durable object storage without data loss."""
        records = self.session.scalars(
            select(AdvertiserMediaAsset).where(
                and_(
                    AdvertiserMediaAsset.data.isnot(None),
                    AdvertiserMediaAsset.storage_key.is_(None),
                )
            )
        ).all()
        migrated = 0
        errors = []
        storage = self.get_storage()
        storage_provider_name = "s3" if hasattr(storage, "bucket") else "local_disk"
        for asset in records:
            try:
                content = bytes(asset.data or b"")
                actual_hash = hashlib.sha256(content).hexdigest()
                if actual_hash != asset.sha256_hash:
                    errors.append(f"Checksum mismatch for asset {asset.id}")
                    continue
                key = f"commercial/{asset.workspace_id or 'global'}/{asset.asset_kind}/{asset.id}_{asset.sanitized_filename}"
                stored = storage.put_bytes(
                    key=key,
                    content=content,
                    content_type=asset.mime_type,
                    metadata={"workspace_id": asset.workspace_id, "migrated_from_blob": True},
                )
                asset.storage_provider = storage_provider_name
                if stored.size_bytes != len(content):
                    errors.append(f"Size verification failed for asset {asset.id}")
                    continue
                asset.storage_provider = "local_object_storage"
                asset.storage_key = key
                migrated += 1
            except Exception as ex:
                errors.append(f"Migration error on asset {asset.id}: {ex}")
        self.session.commit()
        return {"total_found": len(records), "migrated": migrated, "errors": errors}

    def serialize_media_asset(self, asset: AdvertiserMediaAsset) -> AdvertiserMediaAssetView:
        return AdvertiserMediaAssetView(
            id=asset.id,
            workspace_id=asset.workspace_id,
            asset_kind=asset.asset_kind,
            original_filename=asset.original_filename,
            sanitized_filename=asset.sanitized_filename,
            mime_type=asset.mime_type,
            size_bytes=asset.size_bytes,
            sha256_hash=asset.sha256_hash,
            width=asset.width,
            height=asset.height,
            duration_seconds=asset.duration_seconds,
            has_audio_track=asset.has_audio_track,
            is_silent_verified=asset.is_silent_verified,
            validation_status=asset.validation_status,
            storage_provider=asset.storage_provider,
            storage_key=asset.storage_key,
            access_classification=asset.access_classification,
            delivery_url=f"/api/v2/public/ads/media/{asset.id}",
            created_at=_as_utc(asset.created_at) or _utcnow(),
        )

    def _require_valid_asset(self, asset_id: str, *, expected_kinds: set[str]) -> AdvertiserMediaAsset:
        asset = self.session.get(AdvertiserMediaAsset, asset_id)
        if asset is None or asset.validation_status != "valid":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Uploaded media asset '{asset_id}' was not found or failed validation.",
            )
        if asset.asset_kind not in expected_kinds:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Media asset '{asset_id}' has kind '{asset.asset_kind}', expected one of: {', '.join(sorted(expected_kinds))}.",
            )
        return asset

    # ------------------------------------------------------------------
    # Placement Registry & NGN Pricing Engine
    # ------------------------------------------------------------------
    def list_placements(self, *, division: str | None = None, public_only: bool = True) -> list[AdPlacementSpecView]:
        self.ensure_default_catalog()
        stmt = select(AdPlacementSpec).order_by(AdPlacementSpec.priority_weight.desc(), AdPlacementSpec.name.asc())
        if division:
            stmt = stmt.where(AdPlacementSpec.division == division)
        if public_only:
            stmt = stmt.where(
                AdPlacementSpec.is_enabled.is_(True),
                AdPlacementSpec.delivery_surface_ready.is_(True),
            )
        rows = self.session.scalars(stmt).all()
        return [self.serialize_placement(row) for row in rows]

    def serialize_placement(self, row: AdPlacementSpec) -> AdPlacementSpecView:
        return AdPlacementSpecView(
            id=row.id,
            placement_key=row.placement_key,
            name=row.name,
            division=row.division,
            category=row.category,
            description=row.description,
            supported_media_types=list(row.supported_media_types_json or []),
            aspect_ratio=row.aspect_ratio,
            recommended_width=row.recommended_width,
            recommended_height=row.recommended_height,
            max_file_size_bytes=row.max_file_size_bytes,
            max_duration_seconds=row.max_duration_seconds,
            requires_silent_media=row.requires_silent_media,
            weekly_rate_minor_ngn=row.weekly_rate_minor_ngn,
            weekly_rate_formatted_ngn=format_ngn_from_minor(row.weekly_rate_minor_ngn),
            pricing_configured=row.weekly_rate_minor_ngn is not None,
            is_enabled=row.is_enabled,
            delivery_surface_ready=row.delivery_surface_ready,
            frequency_cap_per_session=row.frequency_cap_per_session,
            rotation_interval_seconds=row.rotation_interval_seconds,
            priority_weight=row.priority_weight,
            device_compatibility=list(row.device_compatibility_json or []),
        )

    def admin_update_placement(
        self,
        *,
        admin_user: User,
        placement_key: str,
        payload: AdPlacementSpecAdminUpdateRequest,
    ) -> AdPlacementSpecView:
        self.ensure_default_catalog()
        row = self.session.scalar(select(AdPlacementSpec).where(AdPlacementSpec.placement_key == placement_key))
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placement not found.")
        updates = payload.model_dump(exclude_unset=True)
        for key, val in updates.items():
            setattr(row, key, val)
        self.record_audit_log(
            actor_user_id=admin_user.id,
            entity_type="ad_placement_spec",
            entity_id=row.placement_key,
            action="updated_placement",
            metadata_json=updates,
        )
        self.session.commit()
        self.session.refresh(row)
        return self.serialize_placement(row)

    def list_pricing_packages(
        self, *, division: str | None = None, active_only: bool = True
    ) -> list[AdPricingPackageView]:
        self.ensure_default_catalog()
        stmt = select(AdPricingPackage).order_by(AdPricingPackage.division.asc(), AdPricingPackage.sort_order.asc())
        if division:
            stmt = stmt.where(AdPricingPackage.division == division)
        if active_only:
            stmt = stmt.where(AdPricingPackage.is_active.is_(True))
        rows = self.session.scalars(stmt).all()
        return [self.serialize_pricing_package(row) for row in rows]

    def serialize_pricing_package(self, row: AdPricingPackage) -> AdPricingPackageView:
        return AdPricingPackageView(
            id=row.id,
            package_code=row.package_code,
            name=row.name,
            division=row.division,
            description=row.description,
            duration_days=row.duration_days,
            placement_keys=list(row.placement_keys_json or []),
            is_bundle=row.is_bundle,
            is_subscription=row.is_subscription,
            billing_interval_days=row.billing_interval_days,
            price_minor_ngn=row.price_minor_ngn,
            price_formatted_ngn=format_ngn_from_minor(row.price_minor_ngn),
            pricing_configured=row.price_minor_ngn is not None,
            currency="NGN",
            discount_percent=row.discount_percent,
            is_active=row.is_active,
            sort_order=row.sort_order,
        )

    def admin_upsert_pricing_package(
        self,
        *,
        admin_user: User,
        payload: AdPricingPackageAdminUpsertRequest,
    ) -> AdPricingPackageView:
        self.ensure_default_catalog()
        if payload.duration_days < 7:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Minimum campaign package duration is 7 days.",
            )
        row = self.session.scalar(select(AdPricingPackage).where(AdPricingPackage.package_code == payload.package_code))
        if row is None:
            row = AdPricingPackage(
                package_code=payload.package_code,
                name=payload.name,
                division=payload.division,
                description=payload.description,
                duration_days=payload.duration_days,
                placement_keys_json=list(payload.placement_keys),
                is_bundle=payload.is_bundle,
                is_subscription=payload.is_subscription,
                billing_interval_days=payload.billing_interval_days,
                price_minor_ngn=payload.price_minor_ngn,
                currency="NGN",
                discount_percent=payload.discount_percent,
                is_active=payload.is_active,
                sort_order=payload.sort_order,
            )
            self.session.add(row)
        else:
            row.name = payload.name
            row.division = payload.division
            row.description = payload.description
            row.duration_days = payload.duration_days
            row.placement_keys_json = list(payload.placement_keys)
            row.is_bundle = payload.is_bundle
            row.is_subscription = payload.is_subscription
            row.billing_interval_days = payload.billing_interval_days
            row.price_minor_ngn = payload.price_minor_ngn
            row.discount_percent = payload.discount_percent
            row.is_active = payload.is_active
            row.sort_order = payload.sort_order
        self.record_audit_log(
            actor_user_id=admin_user.id,
            entity_type="ad_pricing_package",
            entity_id=payload.package_code,
            action="upserted_pricing_package",
            metadata_json=payload.model_dump(),
        )
        self.session.commit()
        self.session.refresh(row)
        return self.serialize_pricing_package(row)

    def calculate_price_ngn(
        self,
        payload: CommercialPriceCalculationRequest,
    ) -> CommercialPriceCalculationResponse:
        self.ensure_default_catalog()
        if payload.duration_days < 7:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Minimum campaign duration is 7 days.",
            )

        breakdown: list[dict[str, Any]] = []
        unconfigured: list[str] = []

        # 1. If a package_code is explicitly selected, check if its NGN price is configured
        pkg: AdPricingPackage | None = None
        if payload.package_code:
            pkg = self.session.scalar(
                select(AdPricingPackage).where(
                    AdPricingPackage.package_code == payload.package_code,
                    AdPricingPackage.is_active.is_(True),
                )
            )
            if pkg is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pricing package '{payload.package_code}' was not found or is inactive.",
                )

        # If package has a configured price and matches the division/bundle
        if pkg is not None and pkg.price_minor_ngn is not None and (pkg.is_bundle or payload.division == "music"):
            subtotal = int(pkg.price_minor_ngn)
            discount = int(round(subtotal * (pkg.discount_percent / 100.0)))
            total = max(0, subtotal - discount)
            breakdown.append(
                {
                    "item": pkg.name,
                    "package_code": pkg.package_code,
                    "duration_days": pkg.duration_days,
                    "amount_minor_ngn": total,
                    "formatted_ngn": format_ngn_from_minor(total),
                }
            )
            return CommercialPriceCalculationResponse(
                division=payload.division,
                placements=payload.placements or list(pkg.placement_keys_json or []),
                duration_days=pkg.duration_days,
                package_code=pkg.package_code,
                is_subscription=pkg.is_subscription or payload.is_subscription,
                currency="NGN",
                pricing_configured=True,
                pricing_status="configured",
                subtotal_minor_ngn=subtotal,
                discount_minor_ngn=discount,
                total_minor_ngn=total,
                formatted_total_ngn=format_ngn_from_minor(total),
                breakdown=breakdown,
                unconfigured_items=[],
            )

        # 2. Otherwise calculate from selected placement weekly rates * weeks
        placement_keys = payload.placements or (
            ["music_rotation"] if payload.division == "music" else ["public_homepage"]
        )
        weeks = max(1, math.ceil(payload.duration_days / 7.0))
        subtotal_minor = 0

        for key in placement_keys:
            spec = self.session.scalar(select(AdPlacementSpec).where(AdPlacementSpec.placement_key == key))
            if spec is None or not spec.is_enabled or not spec.delivery_surface_ready:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Placement '{key}' is not enabled or not available for booking.",
                )
            if spec.weekly_rate_minor_ngn is None:
                unconfigured.append(spec.name)
                breakdown.append(
                    {
                        "placement_key": spec.placement_key,
                        "name": spec.name,
                        "weeks": weeks,
                        "weekly_rate_minor_ngn": None,
                        "amount_minor_ngn": None,
                        "status": "unconfigured",
                    }
                )
            else:
                line_total = int(spec.weekly_rate_minor_ngn) * weeks
                subtotal_minor += line_total
                breakdown.append(
                    {
                        "placement_key": spec.placement_key,
                        "name": spec.name,
                        "weeks": weeks,
                        "weekly_rate_minor_ngn": int(spec.weekly_rate_minor_ngn),
                        "amount_minor_ngn": line_total,
                        "formatted_ngn": format_ngn_from_minor(line_total),
                        "status": "configured",
                    }
                )

        if unconfigured:
            return CommercialPriceCalculationResponse(
                division=payload.division,
                placements=placement_keys,
                duration_days=payload.duration_days,
                package_code=payload.package_code,
                is_subscription=payload.is_subscription,
                currency="NGN",
                pricing_configured=False,
                pricing_status="unconfigured",
                subtotal_minor_ngn=None,
                discount_minor_ngn=0,
                total_minor_ngn=None,
                formatted_total_ngn=None,
                breakdown=breakdown,
                unconfigured_items=unconfigured,
            )

        discount_pct = pkg.discount_percent if pkg is not None else (10 if len(placement_keys) >= 3 else 0)
        discount_minor = int(round(subtotal_minor * (discount_pct / 100.0)))
        total_minor = max(0, subtotal_minor - discount_minor)

        return CommercialPriceCalculationResponse(
            division=payload.division,
            placements=placement_keys,
            duration_days=payload.duration_days,
            package_code=payload.package_code,
            is_subscription=payload.is_subscription,
            currency="NGN",
            pricing_configured=True,
            pricing_status="configured",
            subtotal_minor_ngn=subtotal_minor,
            discount_minor_ngn=discount_minor,
            total_minor_ngn=total_minor,
            formatted_total_ngn=format_ngn_from_minor(total_minor),
            breakdown=breakdown,
            unconfigured_items=[],
        )

    # ------------------------------------------------------------------
    # Campaign Creation (4-Step Brand Wizard & Dedicated Music Workflow)
    # ------------------------------------------------------------------
    def create_brand_campaign_wizard(
        self,
        *,
        user: User,
        payload: BrandCampaignWizardCreateRequest,
    ) -> CommercialCampaignView:
        workspace = self.require_active_workspace(user)
        self.ensure_default_catalog()

        if payload.client_brand_id:
            client_brand = self.session.get(AdvertiserClientBrand, payload.client_brand_id)
            if client_brand is None or client_brand.workspace_id != workspace.id or not client_brand.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client brand not found.")

        # Validate creative asset (must be uploaded image or silent video)
        creative_asset = self._require_valid_asset(
            payload.creative_asset_id,
            expected_kinds={"brand_image", "brand_video"},
        )
        if not creative_asset.is_silent_verified or creative_asset.has_audio_track:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Visual brand advertisements must be silent.",
            )

        logo_asset: AdvertiserMediaAsset | None = None
        if payload.logo_asset_id:
            logo_asset = self._require_valid_asset(payload.logo_asset_id, expected_kinds={"logo", "brand_image"})

        # Validate placements against central registry & supported media types
        deduped_placements = list(dict.fromkeys(payload.placements))
        for placement_key in deduped_placements:
            spec = self.session.scalar(
                select(AdPlacementSpec).where(
                    AdPlacementSpec.placement_key == placement_key,
                    AdPlacementSpec.division == "brand",
                )
            )
            if spec is None or not spec.is_enabled or not spec.delivery_surface_ready:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Placement '{placement_key}' is not enabled or available in the GTEX placement registry.",
                )
            if creative_asset.mime_type not in (spec.supported_media_types_json or []):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Creative format '{creative_asset.mime_type}' is not supported by placement '{spec.name}'. Supported: {', '.join(spec.supported_media_types_json or [])}.",
                )

        price_calc = self.calculate_price_ngn(
            CommercialPriceCalculationRequest(
                division="brand",
                placements=deduped_placements,
                duration_days=payload.duration_days,
                package_code=payload.package_code,
                is_subscription=payload.is_subscription,
            )
        )
        price_minor = price_calc.total_minor_ngn or 0
        now = _utcnow()
        initial_status = "awaiting_payment" if payload.submit_immediately else "draft"

        campaign = BrandAdCampaign(
            advertiser_id=user.id,
            workspace_id=workspace.id,
            client_brand_id=payload.client_brand_id,
            brand_name=payload.company_name.strip(),
            contact_email=payload.contact_email.strip().lower(),
            contact_phone=payload.contact_phone.strip(),
            contact_name=payload.contact_name.strip() if payload.contact_name else None,
            website_url=payload.website_url.strip() if payload.website_url else None,
            headline=payload.headline.strip(),
            description=payload.description.strip(),
            placement=deduped_placements[0],
            placements_json=deduped_placements,
            destination_url=(payload.website_url or workspace.website_url or "https://gtex.app").strip(),
            logo_asset_id=logo_asset.id if logo_asset else workspace.logo_asset_id,
            logo_url=(
                f"/api/v2/public/ads/media/{logo_asset.id}"
                if logo_asset
                else (f"/api/v2/public/ads/media/{workspace.logo_asset_id}" if workspace.logo_asset_id else None)
            ),
            creative_asset_id=creative_asset.id,
            creative_url=f"/api/v2/public/ads/media/{creative_asset.id}",
            creative_media_type=creative_asset.mime_type,
            is_silent_creative=True,
            duration_days=payload.duration_days,
            # Placeholder window until system calculates exact start_at/end_at upon approval + verified payment
            start_at=now,
            end_at=now + timedelta(days=payload.duration_days),
            priority=120,
            is_approved=False,
            is_active=False,
            campaign_type="brand",
            status=initial_status,
            payment_status="unpaid",
            price_minor_ngn=price_minor,
            is_subscription=payload.is_subscription,
            budget_amount=Decimal(price_minor) / Decimal(100),
            currency="NGN",
            pricing_model="SUBSCRIPTION_NGN" if payload.is_subscription else "DURATION_NGN",
            unit_price=Decimal(price_minor) / Decimal(100),
            submitted_at=now if payload.submit_immediately else None,
        )
        self.session.add(campaign)
        self.session.flush()

        self.session.add(
            BrandAdReviewEvent(
                campaign_id=campaign.id,
                actor_user_id=user.id,
                action="submitted" if payload.submit_immediately else "created",
                note="Created via 4-step GTEX Brand Campaign Wizard",
                from_status="draft",
                to_status=initial_status,
            )
        )
        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            campaign_id=campaign.id,
            entity_type="brand_campaign",
            entity_id=campaign.id,
            action="created_brand_campaign",
            metadata_json={
                "placements": deduped_placements,
                "duration_days": payload.duration_days,
                "price_minor_ngn": price_minor,
                "pricing_configured": price_calc.pricing_configured,
            },
        )
        self.session.commit()
        self.session.refresh(campaign)
        return self.serialize_campaign(campaign)

    def create_music_promotion_wizard(
        self,
        *,
        user: User,
        payload: MusicPromotionWizardCreateRequest,
    ) -> CommercialCampaignView:
        workspace = self.require_active_workspace(user)
        self.ensure_default_catalog()

        audio_asset = self._require_valid_asset(payload.audio_asset_id, expected_kinds={"music_audio"})
        artwork_asset: AdvertiserMediaAsset | None = None
        if payload.artwork_asset_id:
            artwork_asset = self._require_valid_asset(
                payload.artwork_asset_id, expected_kinds={"music_artwork", "brand_image", "logo"}
            )

        track_title = (payload.track_title or "").strip() or clean_track_title_from_filename(
            audio_asset.original_filename
        )
        artist_name = (
            payload.stage_name
            or payload.artist_name
            or workspace.stage_name
            or workspace.company_name
            or "GTEX Featured Artist"
        ).strip()
        label_name = (payload.label_name or workspace.label_name or workspace.company_name).strip()

        price_calc = self.calculate_price_ngn(
            CommercialPriceCalculationRequest(
                division="music",
                placements=["music_rotation"],
                duration_days=payload.duration_days,
                package_code=payload.package_code or f"music_{payload.duration_days}d",
                is_subscription=payload.is_subscription,
            )
        )
        price_minor = price_calc.total_minor_ngn or 0
        now = _utcnow()

        audio_url = f"/api/v2/public/ads/media/{audio_asset.id}"
        artwork_url = f"/api/v2/public/ads/media/{artwork_asset.id}" if artwork_asset else None

        campaign = BrandAdCampaign(
            advertiser_id=user.id,
            workspace_id=workspace.id,
            brand_name=artist_name[:160],
            contact_email=workspace.contact_email,
            contact_phone=workspace.contact_phone,
            contact_name=workspace.contact_name,
            website_url=payload.external_profile_url or workspace.website_url,
            headline=f"{track_title} — {artist_name}"[:180],
            description=f"Promoted track by {artist_name} ({label_name})"[:360],
            placement="music_rotation",
            placements_json=["music_rotation"],
            destination_url=(payload.external_profile_url or workspace.website_url or "https://gtex.app").strip(),
            logo_asset_id=artwork_asset.id if artwork_asset else workspace.logo_asset_id,
            logo_url=artwork_url,
            creative_asset_id=artwork_asset.id if artwork_asset else None,
            creative_url=artwork_url,
            creative_media_type=audio_asset.mime_type,
            is_silent_creative=False,
            duration_days=payload.duration_days,
            start_at=now,
            end_at=now + timedelta(days=payload.duration_days),
            priority=130,
            is_approved=False,
            is_active=False,
            campaign_type="music",
            status="awaiting_payment",
            payment_status="unpaid",
            price_minor_ngn=price_minor,
            is_subscription=payload.is_subscription,
            budget_amount=Decimal(price_minor) / Decimal(100),
            currency="NGN",
            pricing_model="SUBSCRIPTION_NGN" if payload.is_subscription else "PACKAGE",
            unit_price=Decimal(price_minor) / Decimal(100),
            submitted_at=now,
            music_target_type="track",
            music_target_id=f"promo-track-{audio_asset.id[:12]}",
            music_title=track_title[:180],
            music_artist_name=artist_name[:160],
            music_genre=(payload.genre or "Afrobeats")[:80],
            music_audio_asset_id=audio_asset.id,
            music_artwork_asset_id=artwork_asset.id if artwork_asset else None,
            music_audio_url=audio_url,
            music_artwork_url=artwork_url,
            music_explicit_content=payload.explicit_content,
            music_rights_declaration_accepted=True,
            music_rights_declaration_at=now,
            music_rights_verified=False,
            music_rights_holder=(payload.rights_holder or label_name or artist_name)[:160],
        )
        self.session.add(campaign)
        self.session.flush()

        self.session.add(
            BrandAdReviewEvent(
                campaign_id=campaign.id,
                actor_user_id=user.id,
                action="submitted",
                note="Submitted via GTEX Music Promotion workflow",
                from_status="draft",
                to_status="awaiting_payment",
            )
        )
        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            campaign_id=campaign.id,
            entity_type="music_campaign",
            entity_id=campaign.id,
            action="created_music_promotion",
            metadata_json={
                "track_title": track_title,
                "artist_name": artist_name,
                "duration_days": payload.duration_days,
                "price_minor_ngn": price_minor,
                "explicit_content": payload.explicit_content,
            },
        )
        self.session.commit()
        self.session.refresh(campaign)
        return self.serialize_campaign(campaign)

    def serialize_campaign(self, campaign: BrandAdCampaign) -> CommercialCampaignView:
        placements = list(campaign.placements_json or [])
        if not placements and campaign.placement:
            placements = [campaign.placement]
        return CommercialCampaignView(
            id=campaign.id,
            workspace_id=campaign.workspace_id,
            advertiser_id=campaign.advertiser_id,
            client_brand_id=campaign.client_brand_id,
            campaign_type=campaign.campaign_type,
            brand_name=campaign.brand_name,
            contact_email=campaign.contact_email,
            contact_phone=campaign.contact_phone,
            contact_name=campaign.contact_name,
            website_url=campaign.website_url,
            headline=campaign.headline,
            description=campaign.description,
            placement=campaign.placement,
            placements=placements,
            destination_url=campaign.destination_url,
            logo_asset_id=campaign.logo_asset_id,
            logo_url=campaign.logo_url,
            creative_asset_id=campaign.creative_asset_id,
            creative_url=campaign.creative_url,
            creative_media_type=campaign.creative_media_type,
            is_silent_creative=campaign.is_silent_creative,
            duration_days=campaign.duration_days or 7,
            start_at=_as_utc(campaign.start_at),
            end_at=_as_utc(campaign.end_at),
            status=campaign.status,
            payment_status=campaign.payment_status or "unpaid",
            payment_reference=campaign.payment_reference,
            price_minor_ngn=int(campaign.price_minor_ngn or 0),
            price_formatted_ngn=format_ngn_from_minor(int(campaign.price_minor_ngn or 0)) or "₦0.00",
            currency=campaign.currency,
            pricing_model=campaign.pricing_model,
            is_subscription=bool(campaign.is_subscription),
            is_approved=bool(campaign.is_approved),
            is_active=bool(campaign.is_active),
            review_note=campaign.review_note,
            music_title=campaign.music_title,
            music_artist_name=campaign.music_artist_name,
            music_genre=campaign.music_genre,
            music_audio_asset_id=campaign.music_audio_asset_id,
            music_artwork_asset_id=campaign.music_artwork_asset_id,
            music_audio_url=campaign.music_audio_url,
            music_artwork_url=campaign.music_artwork_url,
            music_explicit_content=bool(campaign.music_explicit_content),
            music_rights_declaration_accepted=bool(campaign.music_rights_declaration_accepted),
            music_rights_verified=bool(campaign.music_rights_verified),
            music_rights_holder=campaign.music_rights_holder,
            created_at=_as_utc(campaign.created_at) or _utcnow(),
            updated_at=_as_utc(campaign.updated_at) or _utcnow(),
        )

    def activate_campaign_if_ready(self, campaign: BrandAdCampaign) -> bool:
        """System-calculated start and end dates upon creative approval + verified payment."""
        is_paid = campaign.payment_status == "paid"
        rights_ok = True if campaign.campaign_type != "music" else bool(campaign.music_rights_verified)
        workspace_ok = True
        if campaign.workspace_id:
            ws = self.session.get(AdvertiserWorkspace, campaign.workspace_id)
            if ws is not None and ws.status != "active":
                workspace_ok = False

        if campaign.is_approved and is_paid and rights_ok and workspace_ok:
            now = _utcnow()
            duration = max(7, int(campaign.duration_days or 7))
            campaign.start_at = now
            campaign.end_at = now + timedelta(days=duration)
            campaign.status = "active"
            campaign.is_active = True
            return True
        return False

    def refresh_expired_campaigns(self) -> int:
        now = _utcnow()
        active_rows = self.session.scalars(
            select(BrandAdCampaign).where(
                BrandAdCampaign.is_active.is_(True),
                BrandAdCampaign.end_at <= now,
            )
        ).all()
        count = 0
        for row in active_rows:
            row.is_active = False
            row.status = "completed"
            count += 1
        if count:
            self.session.flush()
        return count

    # ------------------------------------------------------------------
    # Nigerian Naira (NGN) Payment, Verification, Webhook, Invoice & Subscription
    # ------------------------------------------------------------------
    def initiate_campaign_payment(
        self,
        *,
        user: User,
        payload: PaymentInitiateRequest,
    ) -> PaymentRecordView:
        workspace = self.require_active_workspace(user)
        campaign = self.session.get(BrandAdCampaign, payload.campaign_id)
        if campaign is None or (campaign.workspace_id != workspace.id and campaign.advertiser_id != user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")
        existing_sub: AdvertiserSubscription | None = None
        if campaign.payment_status == "paid":
            if not campaign.is_subscription:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Campaign has already been paid.")
            existing_sub = self.session.scalar(
                select(AdvertiserSubscription)
                .where(
                    AdvertiserSubscription.campaign_id == campaign.id,
                    AdvertiserSubscription.status.in_(["active", "paused", "past_due", "expired"]),
                )
                .order_by(AdvertiserSubscription.created_at.desc())
            )
            if existing_sub is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Campaign has already been paid.")

        self._validate_callback_url(payload.callback_url)

        # A single in-flight checkout per campaign: reuse it instead of creating a duplicate.
        in_flight = self.session.scalar(
            select(AdvertiserPaymentRecord)
            .where(
                AdvertiserPaymentRecord.campaign_id == campaign.id,
                AdvertiserPaymentRecord.status == "pending",
            )
            .order_by(AdvertiserPaymentRecord.created_at.desc())
        )
        if in_flight is not None:
            return self.serialize_payment(in_flight)

        amount_minor = int(campaign.price_minor_ngn or 0)
        if amount_minor <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Commercial NGN pricing is not yet configured for the selected package or placement. An administrator must configure NGN pricing before payment initiation.",
            )

        if campaign.is_subscription and existing_sub is None and not payload.subscription_consent_accepted:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Explicit consent to recurring NGN subscription billing is required before checkout.",
            )

        attempt_count = (
            self.session.scalar(
                select(func.count())
                .select_from(AdvertiserPaymentRecord)
                .where(AdvertiserPaymentRecord.campaign_id == campaign.id)
            )
            or 0
        )
        idem_key = (payload.idempotency_key or f"pay-{campaign.id}-{amount_minor}-{attempt_count}").strip()[:120]
        existing_payment = self.session.scalar(
            select(AdvertiserPaymentRecord).where(AdvertiserPaymentRecord.idempotency_key == idem_key)
        )
        if existing_payment is not None:
            if existing_payment.campaign_id != campaign.id or existing_payment.workspace_id != workspace.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key already in use.")
            if existing_payment.status in {"pending", "processing", "paid"}:
                return self.serialize_payment(existing_payment)
            # Prior attempt ended (failed/reversed/etc.): a retry gets a fresh unique key.
            idem_key = f"{idem_key[:105]}-r{uuid4().hex[:8]}"

        reference = f"GTEX-ADV-NGN-{uuid4().hex[:12].upper()}"
        now = _utcnow()

        subscription: AdvertiserSubscription | None = existing_sub
        if campaign.is_subscription and existing_sub is None:
            subscription = AdvertiserSubscription(
                workspace_id=workspace.id,
                campaign_id=campaign.id,
                package_id=campaign.package_id,
                provider=payload.provider,
                amount_minor_ngn=amount_minor,
                currency="NGN",
                billing_interval_days=30,
                status="pending_consent",
                consent_accepted=True,
                consent_accepted_at=now,
                consent_terms_text=(
                    f"Authorised recurring monthly charge of {format_ngn_from_minor(amount_minor)} every 30 days "
                    "for GTEX Commercial Network advertising. Cancel anytime before renewal."
                ),
            )
            self.session.add(subscription)
            self.session.flush()

        amount_naira = Decimal(amount_minor) / Decimal(100)
        from app.wallets.providers.registry import get_provider_adapter

        try:
            adapter = get_provider_adapter(payload.provider)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported payment provider: {payload.provider}",
            )

        if not adapter.is_configured():
            logger.error("Payment provider %s is not configured", payload.provider)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Payment provider '{payload.provider}' is not currently configured.",
            )

        customer_email = (workspace.contact_email or user.email or "").strip()
        customer_name = (workspace.company_name or user.display_name or user.username or customer_email).strip()
        metadata = {
            "campaign_id": campaign.id,
            "workspace_id": workspace.id,
            "reference": reference,
            "amount_minor_ngn": amount_minor,
        }

        try:
            order = adapter.initialize_checkout(
                order_reference=reference,
                amount=amount_naira,
                currency="NGN",
                customer_email=customer_email,
                customer_name=customer_name,
                callback_url=payload.callback_url,
                metadata=metadata,
                narration=f"GTEX Commercial: {getattr(campaign, 'headline', None) or getattr(campaign, 'name', 'Campaign')}",
            )
            checkout_url = order.checkout_url
            provider_ref = order.reference or reference
        except Exception as ex:
            logger.error("Gateway checkout initialization failed for %s: %s", payload.provider, ex)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to initialize checkout session with {payload.provider}. Please try again later.",
            )

        payment = AdvertiserPaymentRecord(
            reference=reference,
            idempotency_key=idem_key,
            workspace_id=workspace.id,
            campaign_id=campaign.id,
            subscription_id=subscription.id if subscription else None,
            initiated_by_user_id=user.id,
            provider=payload.provider,
            provider_reference=provider_ref,
            amount_minor_ngn=amount_minor,
            currency="NGN",
            status="pending",
            checkout_url=checkout_url,
            pricing_snapshot_json={
                "campaign_id": campaign.id,
                "campaign_type": campaign.campaign_type,
                "placements": list(campaign.placements_json or [campaign.placement]),
                "duration_days": campaign.duration_days,
                "amount_minor_ngn": amount_minor,
            },
        )
        self.session.add(payment)
        self.session.flush()

        invoice_number = f"INV-NGN-{now.strftime('%Y%m%d')}-{payment.id[:6].upper()}"
        invoice = AdvertiserInvoice(
            invoice_number=invoice_number,
            workspace_id=workspace.id,
            campaign_id=campaign.id,
            payment_record_id=payment.id,
            subtotal_minor_ngn=amount_minor - _vat_inclusive_minor(amount_minor),
            tax_minor_ngn=_vat_inclusive_minor(amount_minor),
            discount_minor_ngn=0,
            total_minor_ngn=amount_minor,
            currency="NGN",
            status="issued",
            issued_at=now,
            line_items_json=[
                {
                    "description": f"{campaign.campaign_type.upper()} Campaign: {campaign.headline} ({campaign.duration_days} days)",
                    "placements": list(campaign.placements_json or [campaign.placement]),
                    "amount_minor_ngn": amount_minor,
                    "formatted_ngn": format_ngn_from_minor(amount_minor),
                }
            ],
            billing_details_json={
                "company_name": workspace.company_name,
                "contact_email": workspace.contact_email,
                "contact_phone": workspace.contact_phone,
            },
        )
        self.session.add(invoice)

        campaign.payment_status = "pending"
        campaign.payment_reference = reference
        if campaign.status in {"draft", "awaiting_payment"}:
            campaign.status = "under_review"

        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            campaign_id=campaign.id,
            entity_type="payment_record",
            entity_id=payment.id,
            action="payment_initiated",
            metadata_json={"reference": reference, "amount_minor_ngn": amount_minor, "provider": payload.provider},
        )
        self.session.commit()
        self.session.refresh(payment)
        return self.serialize_payment(payment, invoice_number=invoice_number)

    def _validate_callback_url(self, url: str | None) -> None:
        """Only allow checkout redirects back to configured GTEX origins (prevents open redirect)."""
        if not url:
            return
        from urllib.parse import urlparse

        allowed = {
            h.strip().lower()
            for h in os.getenv("GTEX_ALLOWED_CALLBACK_HOSTS", "gtex.app,www.gtex.app,localhost,127.0.0.1").split(",")
            if h.strip()
        }
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        local = host in {"localhost", "127.0.0.1"}
        if parsed.scheme not in ({"https", "http"} if local else {"https"}) or host not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="callback_url must be an https URL on an approved GTEX domain.",
            )

    def _apply_reversal_side_effects(self, payment: AdvertiserPaymentRecord) -> None:
        """Keep campaign, invoice and subscription consistent after a reversal/chargeback."""
        if payment.campaign_id:
            campaign = self.session.get(BrandAdCampaign, payment.campaign_id)
            if campaign is not None:
                campaign.payment_status = "reversed"
                campaign.is_active = False
                campaign.status = "paused"
        invoice = self.session.scalar(
            select(AdvertiserInvoice).where(AdvertiserInvoice.payment_record_id == payment.id)
        )
        if invoice is not None and invoice.status == "paid":
            invoice.status = "void"
        if payment.subscription_id:
            sub = self.session.get(AdvertiserSubscription, payment.subscription_id)
            if sub is not None and sub.status != "cancelled":
                sub.status = "cancelled"
                sub.cancelled_at = _utcnow()
                sub.cancellation_reason = "Payment reversed"
                sub.next_billing_at = None

    def verify_payment_server_side(
        self,
        *,
        reference: str,
        actor_user_id: str | None = None,
        verification_source: str = "server_verify",
        provider_payload: dict[str, Any] | None = None,
    ) -> PaymentRecordView:
        payment = self.session.scalar(
            select(AdvertiserPaymentRecord).where(
                or_(
                    AdvertiserPaymentRecord.reference == reference,
                    AdvertiserPaymentRecord.provider_reference == reference,
                )
            )
        )
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment reference not found.")

        if payment.status == "paid":
            return self.serialize_payment(payment)

        if payment.status in {"refunded", "reversed"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment reference '{payment.reference}' is already in terminal state '{payment.status}'.",
            )

        # -------------------------------------------------------------
        # Server-to-server gateway verification (No Client Bypass!)
        # -------------------------------------------------------------
        from app.wallets.providers.registry import get_provider_adapter

        try:
            adapter = get_provider_adapter(payment.provider)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported payment provider: {payment.provider}",
            )

        if not adapter.is_configured():
            logger.error("Payment provider %s is not configured for verification", payment.provider)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Payment provider '{payment.provider}' is not configured.",
            )

        verification_ref = payment.provider_reference or payment.reference
        try:
            verification = adapter.verify_payment(reference=verification_ref)
        except Exception as ex:
            logger.error(
                "Provider verification request failed for %s (ref %s): %s", payment.provider, verification_ref, ex
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to verify payment with gateway {payment.provider}. Please try again later.",
            )

        # -------------------------------------------------------------
        # Independent Status Handling (Reversed, Failed, Pending, Paid)
        # -------------------------------------------------------------
        if verification.status in {"reversed", "chargeback"}:
            payment.status = "reversed"
            payment.verification_source = verification_source
            payment.failure_reason = f"Payment was reversed by provider ({verification.status})."
            if provider_payload or verification.raw_payload:
                payment.provider_payload_json = provider_payload or verification.raw_payload
            self._apply_reversal_side_effects(payment)
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment reversed: provider reported '{verification.status}'.",
            )

        if verification.status in {"failed", "abandoned"}:
            payment.status = "failed"
            payment.verification_source = verification_source
            payment.failure_reason = f"Provider reported status '{verification.status}'."
            if provider_payload or verification.raw_payload:
                payment.provider_payload_json = provider_payload or verification.raw_payload
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment verification failed: provider reported status '{verification.status}'.",
            )

        if verification.status in {"pending", "processing", "ongoing"}:
            payment.status = "processing"
            payment.verification_source = verification_source
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment is still pending confirmation from provider.",
            )

        if verification.status != "success":
            payment.status = "failed"
            payment.verification_source = verification_source
            payment.failure_reason = f"Unexpected provider verification status '{verification.status}'."
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment verification failed with provider status '{verification.status}'.",
            )

        # -------------------------------------------------------------
        # Currency Validation (NGN Invariant)
        # -------------------------------------------------------------
        if str(verification.currency).upper() != "NGN":
            payment.status = "failed"
            payment.failure_reason = f"Payment currency mismatch: expected NGN, got {verification.currency}."
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment currency mismatch: expected NGN, got {verification.currency}.",
            )

        # -------------------------------------------------------------
        # Exact Payment Amount Reconciliation (Integer Kobo Arithmetic)
        # -------------------------------------------------------------
        # Note: Do not use floating-point comparisons.
        # Do not compare net settlement after gateway fees against gross charge.
        # Paystack & Korapay adapters return verification.amount as gross charged Decimal in Naira.
        raw_amount = verification.amount
        if raw_amount is None:
            payment.status = "failed"
            payment.failure_reason = "Provider verification payload missing amount."
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount is missing from provider response.",
            )

        try:
            dec_amount = Decimal(str(raw_amount).strip())
        except Exception:
            payment.status = "failed"
            payment.failure_reason = f"Invalid non-numeric payment amount '{raw_amount}'."
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount '{raw_amount}' is not a valid numeric decimal.",
            )

        if not dec_amount.is_finite():
            payment.status = "failed"
            payment.failure_reason = f"Payment amount {dec_amount} is not finite (NaN or Infinity)."
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid payment amount: {dec_amount} is not finite (NaN or Infinity).",
            )

        if dec_amount <= Decimal("0"):
            payment.status = "failed"
            payment.failure_reason = f"Payment amount must be strictly positive, received {dec_amount}."
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount must be strictly positive, received {dec_amount}.",
            )

        scaled = dec_amount * Decimal("100")
        if scaled != scaled.to_integral_value():
            payment.status = "failed"
            payment.failure_reason = f"Payment amount {dec_amount} contains fractional kobo."
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount {dec_amount} contains fractional kobo (sub-kobo precision is rejected).",
            )

        provider_minor = int(scaled.to_integral_value())
        expected_minor = int(payment.amount_minor_ngn)

        if provider_minor < expected_minor:
            # Underpayment case: Underpayment must not activate a campaign
            payment.status = "failed"
            payment.failure_reason = (
                f"Underpayment detected: expected {expected_minor} kobo, received {provider_minor} kobo."
            )
            reconciliation_data = {
                "type": "underpayment",
                "expected_minor": expected_minor,
                "received_minor": provider_minor,
                "difference_minor": expected_minor - provider_minor,
                "processor_fee": str(verification.processor_fee) if verification.processor_fee is not None else None,
            }
            snapshot = dict(payment.pricing_snapshot_json or {})
            snapshot["reconciliation"] = reconciliation_data
            payment.pricing_snapshot_json = snapshot
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Underpayment detected: expected {expected_minor} kobo, received {provider_minor} kobo.",
            )

        if provider_minor > expected_minor:
            # Overpayment case: Overpayment must not silently activate a campaign as an exact match.
            # Record it for an explicit reconciliation decision.
            payment.status = "flagged_overpayment"
            payment.failure_reason = f"Overpayment detected: expected {expected_minor} kobo, received {provider_minor} kobo. Flagged for explicit reconciliation decision."
            reconciliation_data = {
                "type": "overpayment",
                "expected_minor": expected_minor,
                "received_minor": provider_minor,
                "excess_minor": provider_minor - expected_minor,
                "requires_decision": True,
                "decision_status": "pending_finance_review",
                "processor_fee": str(verification.processor_fee) if verification.processor_fee is not None else None,
            }
            snapshot = dict(payment.pricing_snapshot_json or {})
            snapshot["reconciliation"] = reconciliation_data
            payment.pricing_snapshot_json = snapshot
            if payment.campaign_id:
                campaign = self.session.get(BrandAdCampaign, payment.campaign_id)
                if campaign is not None:
                    campaign.payment_status = "flagged_overpayment"
                    campaign.status = "under_review"
            self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Overpayment detected: expected {expected_minor} kobo, received {provider_minor} kobo. Transaction flagged for manual reconciliation decision.",
            )

        # -------------------------------------------------------------
        # Exact Payment Match (provider_minor == expected_minor)
        # -------------------------------------------------------------
        now = _utcnow()
        payment.status = "paid"
        payment.verified_at = now
        payment.verification_source = verification_source
        if provider_payload or verification.raw_payload:
            payment.provider_payload_json = provider_payload or verification.raw_payload
        reconciliation_data = {
            "type": "exact_match",
            "expected_minor": expected_minor,
            "received_minor": provider_minor,
            "processor_fee": str(verification.processor_fee) if verification.processor_fee is not None else None,
        }
        snapshot = dict(payment.pricing_snapshot_json or {})
        snapshot["reconciliation"] = reconciliation_data
        payment.pricing_snapshot_json = snapshot

        invoice = self.session.scalar(
            select(AdvertiserInvoice).where(AdvertiserInvoice.payment_record_id == payment.id)
        )
        if invoice is not None:
            invoice.status = "paid"
            invoice.paid_at = now

        if payment.subscription_id:
            sub = self.session.get(AdvertiserSubscription, payment.subscription_id)
            if sub is not None:
                prev_end = _as_utc(sub.current_period_end)
                # Renewal paid before expiry extends the existing period instead of overlapping it.
                period_start = prev_end if (sub.status == "active" and prev_end and prev_end > now) else now
                sub.status = "active"
                sub.current_period_start = period_start
                sub.current_period_end = period_start + timedelta(days=sub.billing_interval_days)
                sub.next_billing_at = sub.current_period_end
                sub.grace_period_ends_at = None

        if payment.campaign_id:
            campaign = self.session.get(BrandAdCampaign, payment.campaign_id)
            if campaign is not None:
                campaign.payment_status = "paid"
                campaign.payment_reference = payment.reference
                if not self.activate_campaign_if_ready(campaign):
                    campaign.status = "under_review"

        self.record_audit_log(
            actor_user_id=actor_user_id,
            workspace_id=payment.workspace_id,
            campaign_id=payment.campaign_id,
            entity_type="payment_record",
            entity_id=payment.id,
            action="payment_verified",
            metadata_json={"reference": payment.reference, "source": verification_source, "provider": payment.provider},
        )
        self.session.commit()
        self.session.refresh(payment)
        return self.serialize_payment(payment, invoice_number=invoice.invoice_number if invoice else None)

    def handle_provider_webhook(
        self,
        *,
        provider: str,
        raw_body: bytes,
        headers: dict[str, str],
        payload_dict: dict[str, Any],
    ) -> dict[str, Any]:
        from app.wallets.providers.registry import get_provider_adapter

        try:
            adapter = get_provider_adapter(provider)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported webhook provider: {provider}",
            )

        if not adapter.is_configured():
            logger.error("Webhook received for unconfigured provider %s", provider)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Payment provider '{provider}' is not configured.",
            )

        norm_headers = {str(k).lower(): str(v).strip() for k, v in headers.items()}
        signature_verified = False

        if provider == "paystack":
            primary_secret = adapter._webhook_secret()
            if not primary_secret:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Paystack secret key is missing.",
                )
            # Support signing key rotation and legitimate overlap (including whsec_ and whk_ keys)
            candidate_secrets = [s.strip() for s in primary_secret.split(",") if s.strip()]
            for env_name in (
                "PAYSTACK_WEBHOOK_SECRET",
                "GTE_PAYSTACK_WEBHOOK_SECRET",
                "PAYSTACK_WEBHOOK_SECRET_FALLBACK",
            ):
                env_sec = os.getenv(env_name)
                if env_sec and env_sec.strip() not in candidate_secrets:
                    candidate_secrets.append(env_sec.strip())

            newer_sig = norm_headers.get("paystack-signature")
            legacy_sig = norm_headers.get("x-paystack-signature")

            if newer_sig and "t=" in newer_sig:
                # Documented Paystack-Signature scheme: t=<timestamp>,v1=<sig1>,v1=<sig2>
                # Also handles key IDs: v1=whk_id:sig, or whk=whk_id,v1=sig
                parts = [item.strip() for item in newer_sig.split(",") if "=" in item]
                ts_str = None
                v1_sigs: list[tuple[str | None, str]] = []
                header_key_id = None
                for p in parts:
                    k, v = p.split("=", 1)
                    k_clean = k.strip().lower()
                    if k_clean == "t":
                        ts_str = v.strip()
                    elif k_clean in {"whk", "key_id", "kid"}:
                        header_key_id = v.strip()
                    elif k_clean in {"v1", "s"}:
                        raw_v1 = v.strip()
                        if ":" in raw_v1:
                            kid, sig_hex = raw_v1.split(":", 1)
                            v1_sigs.append((kid.strip(), sig_hex.strip()))
                        else:
                            v1_sigs.append((header_key_id, raw_v1))

                if not ts_str or not v1_sigs:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed Paystack-Signature header."
                    )
                try:
                    ts = int(ts_str)
                    now_ts = int(_utcnow().timestamp())
                    if abs(now_ts - ts) > 300:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Paystack webhook timestamp outside validity window (past or future drift exceeded 300s).",
                        )
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid timestamp in Paystack-Signature."
                    )

                signed_content = f"{ts_str}.".encode("utf-8") + raw_body
                for secret in candidate_secrets:
                    expected_v1 = hmac.new(secret.encode("utf-8"), signed_content, hashlib.sha512).hexdigest()
                    for kid, sig in v1_sigs:
                        if hmac.compare_digest(expected_v1, sig):
                            signature_verified = True
                            break
                    if signature_verified:
                        break

                if not signature_verified:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Paystack webhook signature verification failed.",
                    )

            elif legacy_sig or newer_sig:
                sig_to_check = legacy_sig or newer_sig
                for secret in candidate_secrets:
                    expected_legacy = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
                    if hmac.compare_digest(expected_legacy, sig_to_check):
                        signature_verified = True
                        break

                if not signature_verified:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Paystack legacy signature verification failed.",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Paystack signature header."
                )

        elif provider == "korapay":
            # Documented Korapay signature scheme: x-korapay-signature header
            sig = norm_headers.get("x-korapay-signature")
            if not sig:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Korapay signature header (x-korapay-signature).",
                )

            primary_kora_secret = adapter._webhook_secret()
            if not primary_kora_secret:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Korapay secret key is missing."
                )

            candidate_kora_secrets = [s.strip() for s in primary_kora_secret.split(",") if s.strip()]
            fallback_kora = os.getenv("KORAPAY_WEBHOOK_SECRET_FALLBACK")
            if fallback_kora and fallback_kora.strip() not in candidate_kora_secrets:
                candidate_kora_secrets.append(fallback_kora.strip())

            # Korapay requires HMAC-SHA256 over the canonical JSON string of the 'data' object
            from app.wallets.providers.korapay import _js_json_stringify

            data_source = payload_dict.get("data")
            if not isinstance(data_source, dict):
                # Try parsing raw bytes if payload_dict missing data
                try:
                    parsed_raw = json.loads(raw_body.decode("utf-8"))
                    data_source = parsed_raw.get("data") if isinstance(parsed_raw, dict) else None
                except Exception:
                    data_source = None

            if not isinstance(data_source, dict):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Korapay payload.data object is missing or invalid.",
                )

            canonical_data = _js_json_stringify(data_source).encode("utf-8")
            for secret in candidate_kora_secrets:
                expected_kora = hmac.new(secret.encode("utf-8"), canonical_data, hashlib.sha256).hexdigest()
                if hmac.compare_digest(expected_kora, sig):
                    signature_verified = True
                    break

            if not signature_verified:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Korapay webhook signature verification failed."
                )

        if not signature_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook signature could not be verified."
            )

        event_id = str(
            payload_dict.get("id")
            or payload_dict.get("data", {}).get("id")
            or payload_dict.get("data", {}).get("reference")
            or hashlib.sha256(raw_body).hexdigest()[:32]
        )
        existing_event = self.session.scalar(
            select(AdvertiserWebhookEvent).where(AdvertiserWebhookEvent.event_id == event_id)
        )
        if existing_event is not None and existing_event.processed:
            return {"status": "duplicate", "event_id": event_id}

        event_type = str(payload_dict.get("event") or "charge.success")
        data_obj = payload_dict.get("data") if isinstance(payload_dict.get("data"), dict) else {}
        reference = str(data_obj.get("reference") or payload_dict.get("reference") or "").strip()

        webhook_row = existing_event or AdvertiserWebhookEvent(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payment_reference=reference or None,
            signature_verified=True,
            processed=False,
            payload_json=payload_dict,
        )
        if existing_event is None:
            self.session.add(webhook_row)
            self.session.flush()

        if reference and event_type in {"charge.success", "payment_intent.succeeded"}:
            try:
                self.verify_payment_server_side(
                    reference=reference,
                    verification_source="webhook",
                    provider_payload=payload_dict,
                )
            except HTTPException as ex:
                if ex.status_code == status.HTTP_404_NOT_FOUND:
                    self.session.commit()
                    return {"status": "ignored_unknown_reference", "event_id": event_id}
                raise

        elif reference and event_type in {"charge.reversed", "payment_intent.reversed"}:
            # Handle charge reversal
            target_payment = self.session.scalar(
                select(AdvertiserPaymentRecord).where(
                    or_(
                        AdvertiserPaymentRecord.reference == reference,
                        AdvertiserPaymentRecord.provider_reference == reference,
                    )
                )
            )
            if target_payment is not None:
                target_payment.status = "reversed"
                target_payment.failure_reason = f"Payment reversed via webhook event '{event_type}'."
                target_payment.provider_payload_json = payload_dict
                self._apply_reversal_side_effects(target_payment)
                self.record_audit_log(
                    actor_user_id=None,
                    workspace_id=target_payment.workspace_id,
                    campaign_id=target_payment.campaign_id,
                    entity_type="payment_record",
                    entity_id=target_payment.id,
                    action="payment_reversed_webhook",
                    metadata_json={"reference": reference, "event_type": event_type},
                )

        elif reference and event_type in {"refund.processed", "refund.completed"}:
            # Handle webhook refund notifications
            target_payment = self.session.scalar(
                select(AdvertiserPaymentRecord).where(
                    or_(
                        AdvertiserPaymentRecord.reference == reference,
                        AdvertiserPaymentRecord.provider_reference == reference,
                    )
                )
            )
            if target_payment is not None:
                refund_amount_minor = 0
                raw_refund_amount = data_obj.get("amount") or payload_dict.get("amount")
                if raw_refund_amount is not None:
                    # If Paystack, amount in kobo; if Korapay, in Naira
                    if provider == "paystack":
                        refund_amount_minor = int(raw_refund_amount)
                    else:
                        refund_amount_minor = int(
                            (Decimal(str(raw_refund_amount)) * Decimal("100")).to_integral_value()
                        )
                else:
                    refund_amount_minor = int(target_payment.amount_minor_ngn)

                if refund_amount_minor >= int(target_payment.amount_minor_ngn):
                    target_payment.status = "refunded"
                    if target_payment.campaign_id:
                        campaign = self.session.get(BrandAdCampaign, target_payment.campaign_id)
                        if campaign is not None:
                            campaign.payment_status = "refunded"
                            campaign.is_active = False
                            campaign.status = "paused"
                else:
                    target_payment.status = "partially_refunded"

                target_payment.provider_payload_json = payload_dict
                self.record_audit_log(
                    actor_user_id=None,
                    workspace_id=target_payment.workspace_id,
                    campaign_id=target_payment.campaign_id,
                    entity_type="payment_record",
                    entity_id=target_payment.id,
                    action="payment_refunded_webhook",
                    metadata_json={"reference": reference, "refund_minor": refund_amount_minor},
                )

        webhook_row.processed = True
        self.session.commit()
        return {"status": "processed", "event_id": event_id, "reference": reference}

    def serialize_payment(
        self,
        payment: AdvertiserPaymentRecord,
        *,
        invoice_number: str | None = None,
    ) -> PaymentRecordView:
        if invoice_number is None:
            inv = self.session.scalar(
                select(AdvertiserInvoice).where(AdvertiserInvoice.payment_record_id == payment.id)
            )
            invoice_number = inv.invoice_number if inv else None
        return PaymentRecordView(
            id=payment.id,
            reference=payment.reference,
            idempotency_key=payment.idempotency_key,
            workspace_id=payment.workspace_id,
            campaign_id=payment.campaign_id,
            subscription_id=payment.subscription_id,
            provider=payment.provider,
            provider_reference=payment.provider_reference,
            amount_minor_ngn=int(payment.amount_minor_ngn),
            amount_formatted_ngn=format_ngn_from_minor(int(payment.amount_minor_ngn)) or "₦0.00",
            currency=payment.currency,
            status=payment.status,
            checkout_url=payment.checkout_url,
            verified_at=_as_utc(payment.verified_at),
            verification_source=payment.verification_source,
            failure_reason=payment.failure_reason,
            invoice_number=invoice_number,
            created_at=_as_utc(payment.created_at) or _utcnow(),
        )

    def list_workspace_payments(self, user: User) -> list[PaymentRecordView]:
        workspace = self.require_active_workspace(user)
        rows = self.session.scalars(
            select(AdvertiserPaymentRecord)
            .where(AdvertiserPaymentRecord.workspace_id == workspace.id)
            .order_by(AdvertiserPaymentRecord.created_at.desc())
        ).all()
        return [self.serialize_payment(row) for row in rows]

    def list_workspace_invoices(self, user: User) -> list[InvoiceView]:
        workspace = self.require_active_workspace(user)
        rows = self.session.scalars(
            select(AdvertiserInvoice)
            .where(AdvertiserInvoice.workspace_id == workspace.id)
            .order_by(AdvertiserInvoice.created_at.desc())
        ).all()
        return [self.serialize_invoice(row) for row in rows]

    def serialize_invoice(self, row: AdvertiserInvoice) -> InvoiceView:
        return InvoiceView(
            id=row.id,
            invoice_number=row.invoice_number,
            workspace_id=row.workspace_id,
            campaign_id=row.campaign_id,
            payment_record_id=row.payment_record_id,
            subtotal_minor_ngn=int(row.subtotal_minor_ngn),
            tax_minor_ngn=int(row.tax_minor_ngn),
            discount_minor_ngn=int(row.discount_minor_ngn),
            total_minor_ngn=int(row.total_minor_ngn),
            total_formatted_ngn=format_ngn_from_minor(int(row.total_minor_ngn)) or "₦0.00",
            currency=row.currency,
            status=row.status,
            issued_at=_as_utc(row.issued_at) or _utcnow(),
            paid_at=_as_utc(row.paid_at),
            line_items=list(row.line_items_json or []),
            billing_details=dict(row.billing_details_json or {}),
        )

    def list_workspace_subscriptions(self, user: User) -> list[SubscriptionView]:
        workspace = self.require_active_workspace(user)
        rows = self.session.scalars(
            select(AdvertiserSubscription)
            .where(AdvertiserSubscription.workspace_id == workspace.id)
            .order_by(AdvertiserSubscription.created_at.desc())
        ).all()
        return [self.serialize_subscription(row) for row in rows]

    def manage_subscription(
        self,
        *,
        user: User,
        subscription_id: str,
        payload: SubscriptionActionRequest,
    ) -> SubscriptionView:
        workspace = self.require_active_workspace(user)
        sub = self.session.get(AdvertiserSubscription, subscription_id)
        if sub is None or sub.workspace_id != workspace.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")

        now = _utcnow()
        if payload.action == "cancel":
            sub.status = "cancelled"
            sub.cancelled_at = now
            sub.cancellation_reason = payload.reason or "Cancelled by advertiser"
            sub.next_billing_at = None
        elif payload.action == "pause":
            if sub.status != "active":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only active subscriptions can be paused.")
            sub.status = "paused"
        elif payload.action == "resume":
            # Resume never grants new paid time: only allowed inside an already-paid period.
            period_end = _as_utc(sub.current_period_end)
            if sub.status != "paused" or period_end is None or period_end <= now:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Subscription period has lapsed. Start a new payment to renew.",
                )
            sub.status = "active"
        elif payload.action == "renew":
            # Renewal requires a verified payment; time is only extended in verify_payment_server_side.
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Renewal requires payment. Initiate a new payment for this campaign.",
            )

        self.record_audit_log(
            actor_user_id=user.id,
            workspace_id=workspace.id,
            campaign_id=sub.campaign_id,
            entity_type="subscription",
            entity_id=sub.id,
            action=f"subscription_{payload.action}",
            note=payload.reason,
        )
        self.session.commit()
        self.session.refresh(sub)
        return self.serialize_subscription(sub)

    def serialize_subscription(self, row: AdvertiserSubscription) -> SubscriptionView:
        return SubscriptionView(
            id=row.id,
            workspace_id=row.workspace_id,
            campaign_id=row.campaign_id,
            provider=row.provider,
            amount_minor_ngn=int(row.amount_minor_ngn),
            amount_formatted_ngn=format_ngn_from_minor(int(row.amount_minor_ngn)) or "₦0.00",
            currency=row.currency,
            billing_interval_days=row.billing_interval_days,
            status=row.status,
            consent_accepted=row.consent_accepted,
            consent_accepted_at=_as_utc(row.consent_accepted_at),
            consent_terms_text=row.consent_terms_text,
            current_period_start=_as_utc(row.current_period_start),
            current_period_end=_as_utc(row.current_period_end),
            next_billing_at=_as_utc(row.next_billing_at),
            grace_period_ends_at=_as_utc(row.grace_period_ends_at),
            retry_count=row.retry_count,
            cancelled_at=_as_utc(row.cancelled_at),
            cancellation_reason=row.cancellation_reason,
            created_at=_as_utc(row.created_at) or _utcnow(),
        )

    def create_admin_refund(
        self,
        *,
        finance_admin: User,
        payload: RefundCreateRequest,
    ) -> RefundRecordView:
        payment = self.session.get(AdvertiserPaymentRecord, payload.payment_record_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
        if payment.status not in {"paid", "partially_refunded"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only paid transactions can be refunded.")

        refund_amount = int(payload.amount_minor_ngn or 0)
        already_refunded = int(
            self.session.scalar(
                select(func.coalesce(func.sum(AdvertiserRefundRecord.amount_minor_ngn), 0)).where(
                    AdvertiserRefundRecord.payment_record_id == payment.id,
                    AdvertiserRefundRecord.status != "failed",
                )
            )
            or 0
        )
        remaining = int(payment.amount_minor_ngn) - already_refunded
        if payload.amount_minor_ngn is None:
            refund_amount = remaining
        if refund_amount <= 0 or refund_amount > remaining:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Refund amount must be between 1 and the remaining refundable balance ({remaining} kobo).",
            )

        # The provider adapters expose no refund API, so the money movement is performed
        # out-of-band on the gateway dashboard. Record it honestly as pending, not completed.
        refund = AdvertiserRefundRecord(
            payment_record_id=payment.id,
            workspace_id=payment.workspace_id,
            campaign_id=payment.campaign_id,
            amount_minor_ngn=refund_amount,
            currency="NGN",
            reason=payload.reason.strip(),
            status="pending_provider",
            approved_by_user_id=finance_admin.id,
            provider_refund_reference=None,
        )
        self.session.add(refund)

        payment.status = "refunded" if already_refunded + refund_amount >= int(payment.amount_minor_ngn) else "partially_refunded"
        if payment.status == "refunded":
            invoice = self.session.scalar(
                select(AdvertiserInvoice).where(AdvertiserInvoice.payment_record_id == payment.id)
            )
            if invoice is not None:
                invoice.status = "refunded"
            if payment.subscription_id:
                sub = self.session.get(AdvertiserSubscription, payment.subscription_id)
                if sub is not None:
                    sub.status = "cancelled"
                    sub.cancelled_at = _utcnow()
                    sub.cancellation_reason = "Payment refunded"
                    sub.next_billing_at = None
        if payment.campaign_id and payment.status == "refunded":
            campaign = self.session.get(BrandAdCampaign, payment.campaign_id)
            if campaign is not None:
                campaign.payment_status = "refunded"
                campaign.is_active = False
                campaign.status = "paused"

        self.record_audit_log(
            actor_user_id=finance_admin.id,
            workspace_id=payment.workspace_id,
            campaign_id=payment.campaign_id,
            entity_type="refund_record",
            entity_id=payment.id,
            action="issued_refund",
            note=payload.reason,
            metadata_json={"amount_minor_ngn": refund_amount},
        )
        self.session.commit()
        self.session.refresh(refund)
        return RefundRecordView(
            id=refund.id,
            payment_record_id=refund.payment_record_id,
            workspace_id=refund.workspace_id,
            campaign_id=refund.campaign_id,
            amount_minor_ngn=int(refund.amount_minor_ngn),
            amount_formatted_ngn=format_ngn_from_minor(int(refund.amount_minor_ngn)) or "₦0.00",
            currency=refund.currency,
            reason=refund.reason,
            status=refund.status,
            approved_by_user_id=refund.approved_by_user_id,
            created_at=_as_utc(refund.created_at) or _utcnow(),
        )

    # ------------------------------------------------------------------
    # Admin Moderation & Account Management
    # ------------------------------------------------------------------
    def admin_moderate_campaign(
        self,
        *,
        admin_user: User,
        campaign_id: str,
        payload: AdminCampaignModerationRequest,
    ) -> CommercialCampaignView:
        campaign = self.session.get(BrandAdCampaign, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        previous_status = campaign.status
        now = _utcnow()
        action = payload.action

        if action == "approve":
            campaign.is_approved = True
            campaign.reviewed_at = now
            campaign.reviewed_by_user_id = admin_user.id
            campaign.review_note = payload.note
            # Rights are NEVER inferred from the advertiser's own declaration;
            # an admin must explicitly verify them via the "verify_rights" action.
            if not self.activate_campaign_if_ready(campaign):
                campaign.status = "awaiting_payment" if campaign.payment_status != "paid" else "scheduled"
                campaign.is_active = False
        elif action == "verify_rights":
            if campaign.campaign_type != "music" or not campaign.music_rights_declaration_accepted:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Only music campaigns with an accepted rights declaration can be rights-verified.",
                )
            campaign.music_rights_verified = True
            campaign.review_note = payload.note
            if campaign.is_approved:
                self.activate_campaign_if_ready(campaign)
        elif action in {"reject", "request_changes"}:
            campaign.is_approved = False
            campaign.is_active = False
            campaign.status = "rejected"
            campaign.reviewed_at = now
            campaign.reviewed_by_user_id = admin_user.id
            campaign.review_note = payload.note
        elif action == "pause":
            campaign.is_active = False
            campaign.status = "paused"
            campaign.review_note = payload.note
        elif action == "resume":
            if campaign.is_approved:
                self.activate_campaign_if_ready(campaign)
        elif action in {"suspend", "takedown"}:
            campaign.is_approved = False
            campaign.is_active = False
            campaign.status = "taken_down" if action == "takedown" else "suspended"
            campaign.review_note = payload.note
        elif action == "archive":
            campaign.is_active = False
            campaign.status = "archived"
            campaign.archived_at = now

        self.session.add(
            BrandAdReviewEvent(
                campaign_id=campaign.id,
                actor_user_id=admin_user.id,
                action=action,
                note=payload.note,
                from_status=previous_status,
                to_status=campaign.status,
            )
        )
        self.record_audit_log(
            actor_user_id=admin_user.id,
            workspace_id=campaign.workspace_id,
            campaign_id=campaign.id,
            entity_type="campaign",
            entity_id=campaign.id,
            action=f"admin_{action}",
            note=payload.note,
            metadata_json={"from_status": previous_status, "to_status": campaign.status},
        )
        self.session.commit()
        self.session.refresh(campaign)
        return self.serialize_campaign(campaign)

    def admin_manage_workspace(
        self,
        *,
        admin_user: User,
        workspace_id: str,
        payload: AdminWorkspaceActionRequest,
    ) -> AdvertiserWorkspaceView:
        workspace = self.session.get(AdvertiserWorkspace, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

        now = _utcnow()
        if payload.action == "verify":
            workspace.status = "active"
            workspace.verified_at = now
            workspace.suspended_reason = None
        elif payload.action == "suspend":
            workspace.status = "suspended"
            workspace.suspended_reason = payload.note or "Suspended by GTEX Commercial Administration"
            # Pause all active campaigns belonging to suspended workspace
            campaigns = self.session.scalars(
                select(BrandAdCampaign).where(BrandAdCampaign.workspace_id == workspace.id)
            ).all()
            for camp in campaigns:
                camp.is_active = False
                if camp.status == "active":
                    camp.status = "suspended"
        elif payload.action == "reactivate":
            workspace.status = "active"
            workspace.suspended_reason = None

        self.record_audit_log(
            actor_user_id=admin_user.id,
            workspace_id=workspace.id,
            entity_type="advertiser_workspace",
            entity_id=workspace.id,
            action=f"admin_{payload.action}",
            note=payload.note,
        )
        self.session.commit()
        self.session.refresh(workspace)
        return self.serialize_workspace(workspace)

    # ------------------------------------------------------------------
    # Global Music Player Fair-Rotation Feed
    # ------------------------------------------------------------------
    def get_music_rotation_feed(self, *, limit: int = 20) -> MusicRotationFeedResponse:
        self.refresh_expired_campaigns()
        now = _utcnow()
        rows = self.session.scalars(
            select(BrandAdCampaign)
            .where(
                BrandAdCampaign.campaign_type == "music",
                BrandAdCampaign.status.in_(("approved", "active")),
                BrandAdCampaign.is_approved.is_(True),
                BrandAdCampaign.is_active.is_(True),
                BrandAdCampaign.music_rights_verified.is_(True),
                BrandAdCampaign.start_at <= now,
                BrandAdCampaign.end_at >= now,
            )
            .order_by(BrandAdCampaign.priority.desc(), BrandAdCampaign.updated_at.desc())
            .limit(limit)
        ).all()

        tracks: list[MusicRotationTrackView] = []
        for row in rows:
            audio_url = row.music_audio_url or (
                f"/api/v2/public/ads/media/{row.music_audio_asset_id}" if row.music_audio_asset_id else None
            )
            if not audio_url:
                continue
            artwork_url = row.music_artwork_url or (
                f"/api/v2/public/ads/media/{row.music_artwork_asset_id}" if row.music_artwork_asset_id else row.logo_url
            )
            tracks.append(
                MusicRotationTrackView(
                    campaign_id=row.id,
                    track_id=row.music_target_id or f"promo-{row.id[:12]}",
                    title=row.music_title or row.headline,
                    artist=row.music_artist_name or row.brand_name,
                    genre=row.music_genre,
                    audio_url=audio_url,
                    artwork_url=artwork_url,
                    explicit_content=bool(row.music_explicit_content),
                    sponsored_disclosure="Promoted on GTEX Music Network",
                    rights_holder=row.music_rights_holder,
                    priority=row.priority,
                    duration_days=row.duration_days or 7,
                    start_at=_as_utc(row.start_at) or now,
                    end_at=_as_utc(row.end_at) or now,
                )
            )

        return MusicRotationFeedResponse(
            generated_at=now,
            rotation_policy={
                "mode": "fair_weighted_rotation",
                "frequency_cap_per_session": 6,
                "qualified_listen_threshold_seconds": 30,
                "active_surfaces": [
                    "public_homepage",
                    "app_navigation",
                    "club_management",
                    "halftime_break",
                    "post_match",
                ],
                "pause_during_active_match_commentary": True,
            },
            tracks=tracks,
        )

    # ------------------------------------------------------------------
    # Genuine Event-Based Analytics & Reporting
    # ------------------------------------------------------------------
    def get_campaign_analytics(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.session.get(BrandAdCampaign, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

        counts = dict(
            self.session.execute(
                select(BrandAdEvent.event_type, func.count(BrandAdEvent.id))
                .where(BrandAdEvent.campaign_id == campaign_id)
                .group_by(BrandAdEvent.event_type)
            ).all()
        )
        unique_listeners = int(
            self.session.scalar(
                select(func.count(func.distinct(BrandAdEvent.user_id))).where(
                    BrandAdEvent.campaign_id == campaign_id,
                    BrandAdEvent.user_id.is_not(None),
                    BrandAdEvent.event_type.in_(("play_started", "qualified_listen", "completed")),
                )
            )
            or 0
        )

        impressions = int(counts.get("impression", 0))
        viewable_impressions = int(counts.get("viewable_impression", 0))
        clicks = int(counts.get("click", 0))
        conversions = int(counts.get("conversion", 0))
        plays_started = int(counts.get("play_started", 0))
        qualified_listens = int(counts.get("qualified_listen", 0)) + int(counts.get("milestone_50", 0))
        completed_listens = int(counts.get("completed", 0)) + int(counts.get("completed_listen", 0))
        skipped = int(counts.get("skipped", 0))
        ctr_percent = round((clicks / impressions) * 100.0, 2) if impressions > 0 else 0.0

        # Placement breakdown from metadata_json
        events = self.session.scalars(select(BrandAdEvent).where(BrandAdEvent.campaign_id == campaign_id)).all()
        placement_breakdown: dict[str, dict[str, int]] = {}
        daily_timeline: dict[str, dict[str, int]] = {}
        for ev in events:
            meta = ev.metadata_json if isinstance(ev.metadata_json, dict) else {}
            pl = str(meta.get("placement") or campaign.placement)
            bucket = placement_breakdown.setdefault(pl, {"impressions": 0, "clicks": 0, "plays": 0})
            if ev.event_type == "impression":
                bucket["impressions"] += 1
            elif ev.event_type == "click":
                bucket["clicks"] += 1
            elif ev.event_type == "play_started":
                bucket["plays"] += 1

            day_key = (_as_utc(ev.created_at) or _utcnow()).strftime("%Y-%m-%d")
            day_bucket = daily_timeline.setdefault(
                day_key,
                {"impressions": 0, "clicks": 0, "plays_started": 0, "qualified_listens": 0, "completed_listens": 0},
            )
            if ev.event_type == "impression":
                day_bucket["impressions"] += 1
            elif ev.event_type == "click":
                day_bucket["clicks"] += 1
            elif ev.event_type == "play_started":
                day_bucket["plays_started"] += 1
            elif ev.event_type in {"qualified_listen", "milestone_50"}:
                day_bucket["qualified_listens"] += 1
            elif ev.event_type in {"completed", "completed_listen"}:
                day_bucket["completed_listens"] += 1

        return {
            "campaign": self.serialize_campaign(campaign).model_dump(mode="json"),
            "metrics": {
                "impressions": impressions,
                "viewable_impressions": viewable_impressions,
                "clicks": clicks,
                "ctr_percent": ctr_percent,
                "conversions": conversions,
                "plays_started": plays_started,
                "qualified_listens": qualified_listens,
                "completed_listens": completed_listens,
                "skipped": skipped,
                "unique_authenticated_listeners": unique_listeners,
            },
            "placement_breakdown": placement_breakdown,
            "daily_timeline": [{"date": day, **vals} for day, vals in sorted(daily_timeline.items())],
        }
