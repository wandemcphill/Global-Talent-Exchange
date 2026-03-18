from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.analytics.service import AnalyticsService
from backend.app.core.config import Settings
from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.economy.service import EconomyConfigService
from backend.app.models.media_engine import PremiumVideoPurchase
from backend.app.models.risk_ops import AuditLog
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from backend.app.risk_ops_engine.service import RiskOpsService
from backend.app.services.creator_broadcast_service import CreatorBroadcastError, CreatorBroadcastService
from backend.app.services.signing_service import SignatureError, SignedTokenService
from backend.app.services.storage_media_service import MediaAssetDescriptor, MediaStorageService
from backend.app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService


class MediaAccessError(ValueError):
    pass


class MediaRateLimitError(MediaAccessError):
    pass


class MediaAccessDenied(MediaAccessError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MediaDownloadTicket:
    storage_key: str
    download_url: str
    expires_at: datetime
    content_type: str
    filename: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ResolvedDownload:
    storage_key: str
    content_type: str
    filename: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class MediaAccessService:
    session: Session
    settings: Settings
    storage_service: MediaStorageService
    signer: SignedTokenService
    analytics: AnalyticsService | None = None
    risk_ops: RiskOpsService | None = None
    event_publisher: EventPublisher | None = None
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.event_publisher is None:
            self.event_publisher = InMemoryEventPublisher()
        if self.wallet_service is None:
            self.wallet_service = WalletService(event_publisher=self.event_publisher)

    def issue_download(
        self,
        *,
        actor: User,
        storage_key: str,
        match_key: str | None,
        download_kind: str,
        premium_required: bool = True,
        watermark_label: str | None = None,
        watermark_metadata: dict[str, Any] | None = None,
    ) -> MediaDownloadTicket:
        descriptor = self.storage_service.describe(storage_key=storage_key)
        if premium_required and not self._has_premium_access(actor=actor, match_key=match_key):
            raise MediaAccessDenied("Premium video access is required for this download.")
        self._enforce_rate_limit(actor.id)
        download_id = uuid4().hex
        self._charge_highlight_download(
            actor=actor,
            match_key=match_key,
            download_kind=download_kind,
            download_id=download_id,
        )
        filename = self._build_filename(match_key=match_key, download_kind=download_kind, descriptor=descriptor)
        payload = {
            "download_id": download_id,
            "storage_key": storage_key,
            "match_key": match_key,
            "download_kind": download_kind,
            "user_id": actor.id,
            "filename": filename,
            "content_type": descriptor.content_type,
            "watermark_label": watermark_label,
            "watermark_metadata": watermark_metadata or {},
        }
        token = self.signer.sign(payload, expires_in_seconds=self.settings.media_storage.download_expiry_minutes * 60)
        download_url = f"{self.settings.media_storage.download_base_url.rstrip('/')}/{token.token}"
        self._log_audit(
            actor_user_id=actor.id,
            action_key="media.download.issued",
            resource_id=storage_key,
            detail="Media download token issued.",
            metadata={
                "download_id": download_id,
                "match_key": match_key,
                "download_kind": download_kind,
                "filename": filename,
                "expires_at": token.expires_at.isoformat(),
                "watermark_label": watermark_label,
            },
        )
        self._track_event("media_download_issued", actor.id, metadata={"download_kind": download_kind, "match_key": match_key})
        if self.event_publisher is not None and download_kind == "highlight":
            self.event_publisher.publish(
                DomainEvent(
                    name="highlight_download_requested",
                    payload={
                        "download_id": download_id,
                        "user_id": actor.id,
                        "storage_key": storage_key,
                        "match_key": match_key,
                        "download_kind": download_kind,
                    },
                )
            )
        return MediaDownloadTicket(
            storage_key=storage_key,
            download_url=download_url,
            expires_at=token.expires_at,
            content_type=descriptor.content_type,
            filename=filename,
            metadata=descriptor.metadata,
        )

    def _charge_highlight_download(
        self,
        *,
        actor: User,
        match_key: str | None,
        download_kind: str,
        download_id: str,
    ) -> None:
        if download_kind != "highlight":
            return
        creator_access = self._creator_access(actor=actor, match_key=match_key)
        if creator_access is not None and creator_access.season_pass is not None:
            return
        pricing = {item.service_key: item for item in EconomyConfigService(self.session).list_service_pricing(active_only=False)}
        rule = pricing.get("highlight-download") or pricing.get("premium-video-view")
        if rule is None:
            return
        price_fancoin = Decimal(rule.price_fancoin_equivalent or Decimal("0.0000"))
        if price_fancoin <= Decimal("0.0000"):
            return
        user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.CREDIT)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(account=user_account, amount=-price_fancoin, source_tag=LedgerSourceTag.HIGHLIGHT_DOWNLOAD_SPEND),
                    LedgerPosting(account=platform_account, amount=price_fancoin, source_tag=LedgerSourceTag.MATCH_VIEW_REVENUE),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                reference=f"highlight-download:{download_id}",
                description="Highlight download charge",
                actor=actor,
            )
        except InsufficientBalanceError as exc:
            raise MediaAccessDenied("Insufficient FanCoin balance to download highlight.") from exc

    def resolve_download(self, *, token: str) -> ResolvedDownload:
        try:
            payload = self.signer.verify(token)
        except SignatureError as exc:
            raise MediaAccessError(str(exc)) from exc
        storage_key = str(payload.get("storage_key") or "")
        if not storage_key:
            raise MediaAccessError("Invalid download token.")
        descriptor = self.storage_service.describe(storage_key=storage_key)
        filename = str(payload.get("filename") or self._build_filename(match_key=payload.get("match_key"), download_kind="download", descriptor=descriptor))
        self._log_audit(
            actor_user_id=str(payload.get("user_id") or None),
            action_key="media.download.served",
            resource_id=storage_key,
            detail="Media download served.",
            metadata={
                "download_id": payload.get("download_id"),
                "match_key": payload.get("match_key"),
                "download_kind": payload.get("download_kind"),
                "filename": filename,
            },
        )
        self._track_event("media_download_served", payload.get("user_id"), metadata={"download_kind": payload.get("download_kind")})
        return ResolvedDownload(
            storage_key=storage_key,
            content_type=descriptor.content_type,
            filename=filename,
            metadata=descriptor.metadata,
        )

    def _has_premium_access(self, *, actor: User, match_key: str | None) -> bool:
        if actor.role.value == "admin":
            return True
        if not match_key:
            return False
        purchase = self.session.scalar(
            select(PremiumVideoPurchase)
            .where(
                PremiumVideoPurchase.user_id == actor.id,
                PremiumVideoPurchase.match_key == match_key,
            )
        )
        if purchase is not None:
            return True
        creator_access = self._creator_access(actor=actor, match_key=match_key)
        if creator_access is None:
            return False
        return creator_access.purchase is not None or creator_access.season_pass is not None

    def _creator_access(self, *, actor: User, match_key: str | None):
        if not match_key:
            return None
        try:
            access = CreatorBroadcastService(self.session, wallet_service=self.wallet_service).access_for_match(
                actor=actor,
                match_id=match_key,
            )
        except CreatorBroadcastError:
            return None
        if not access.has_access:
            return None
        return access

    def _enforce_rate_limit(self, user_id: str) -> None:
        window_start = _utcnow() - timedelta(minutes=self.settings.media_storage.download_rate_limit_window_minutes)
        recent = self.session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.actor_user_id == user_id,
                AuditLog.action_key == "media.download.issued",
                AuditLog.created_at >= window_start,
            )
        ) or 0
        if recent >= self.settings.media_storage.download_rate_limit_count:
            raise MediaRateLimitError("Download rate limit exceeded. Please retry later.")

    def _build_filename(
        self,
        *,
        match_key: str | None,
        download_kind: str,
        descriptor: MediaAssetDescriptor,
    ) -> str:
        base = match_key or "highlight"
        suffix = descriptor.storage_key.split("/")[-1]
        if "." in suffix:
            extension = suffix.split(".")[-1]
        else:
            extension = "bin"
        return f"{base}-{download_kind}.{extension}"

    def _track_event(self, name: str, user_id: str | None, *, metadata: dict[str, Any] | None = None) -> None:
        if self.analytics is None:
            return
        self.analytics.track_event(self.session, name=name, user_id=user_id, metadata=metadata)

    def _log_audit(
        self,
        *,
        actor_user_id: str | None,
        action_key: str,
        resource_id: str | None,
        detail: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        service = self.risk_ops or RiskOpsService(self.session)
        service.log_audit(
            actor_user_id=actor_user_id,
            action_key=action_key,
            resource_type="media_asset",
            resource_id=resource_id,
            detail=detail,
            metadata_json=metadata or {},
        )


__all__ = [
    "MediaAccessDenied",
    "MediaAccessError",
    "MediaDownloadTicket",
    "MediaRateLimitError",
    "MediaAccessService",
    "ResolvedDownload",
]
