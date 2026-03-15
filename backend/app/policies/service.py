from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.policy import (
    CountryFeaturePolicy,
    PolicyAcceptanceRecord,
    PolicyDocument,
    PolicyDocumentVersion,
)
from backend.app.core.config import BACKEND_ROOT
from backend.app.models.base import utcnow
from backend.app.models.user_region import UserRegionProfile
from backend.app.observability.audit_service import AuditTrailService

DEFAULT_POLICY_DOCUMENTS: tuple[tuple[str, str, bool], ...] = (
    ("terms-and-conditions", "Terms & Conditions", True),
    ("privacy-policy", "Privacy Policy", True),
    ("aml-policy", "AML Policy", True),
    ("anti-fraud-policy", "Anti-Fraud Policy", True),
    ("community-guidelines", "Community Guidelines", True),
    ("competition-rules", "Competition Rules", True),
    ("spectator-match-viewing-terms", "Spectator / Match Viewing Terms", True),
    ("user-hosted-competition-rules", "User-Hosted Competition Rules", True),
    ("national-team-competition-rules", "National Team Competition Rules", True),
    ("rewards-promotional-pools-policy", "Rewards Funded by GTEX Promotional Pools Policy", True),
    ("fancoin-terms", "FanCoin Terms", True),
    ("marketplace-rules", "Player Card Marketplace Rules", True),
    ("withdrawal-policy", "Withdrawal Policy", True),
    ("refund-chargeback-policy", "Refund / Chargeback Policy", True),
    ("responsible-play-fair-play-statement", "Responsible Play / Fair Play Statement", True),
    ("app-store-compliance-disclosure", "App Store / Play Store Compliance Disclosure", False),
    ("data-usage-consent-disclosure", "Data Usage / Consent Disclosure", True),
    ("content-moderation-reporting-policy", "Content Moderation and Reporting Policy", True),
    ("fair-play-integrity-policy", "Fair Play / Integrity Policy", True),
)

LEGAL_DOCS_ROOT = BACKEND_ROOT / "docs" / "legal"

DEFAULT_COUNTRY_POLICIES: tuple[dict[str, object], ...] = (
    {
        "country_code": "NG",
        "bucket_type": "default",
        "deposits_enabled": True,
        "market_trading_enabled": True,
        "platform_reward_withdrawals_enabled": True,
        "user_hosted_gift_withdrawals_enabled": False,
        "gtex_competition_gift_withdrawals_enabled": False,
        "national_reward_withdrawals_enabled": False,
        "one_time_region_change_after_days": 365,
        "active": True,
    },
    {
        "country_code": "GLOBAL",
        "bucket_type": "default",
        "deposits_enabled": False,
        "market_trading_enabled": True,
        "platform_reward_withdrawals_enabled": False,
        "user_hosted_gift_withdrawals_enabled": False,
        "gtex_competition_gift_withdrawals_enabled": False,
        "national_reward_withdrawals_enabled": False,
        "one_time_region_change_after_days": 365,
        "active": True,
    },
)

REGION_CHANGE_LOCK_DAYS = 365


@dataclass(slots=True)
class PolicyService:
    session: Session

    def seed_defaults(self) -> None:
        for document_key, title, is_mandatory in DEFAULT_POLICY_DOCUMENTS:
            document = self.session.scalar(select(PolicyDocument).where(PolicyDocument.document_key == document_key))
            if document is None:
                document = PolicyDocument(
                    document_key=document_key,
                    title=title,
                    is_mandatory=is_mandatory,
                    active=True,
                )
                self.session.add(document)
                self.session.flush()
            existing_versions = self.session.scalars(
                select(PolicyDocumentVersion).where(PolicyDocumentVersion.policy_document_id == document.id)
            ).all()
            if existing_versions:
                continue
            body_markdown = _load_default_policy_markdown(document_key=document_key, title=title)
            self.session.add(
                PolicyDocumentVersion(
                    policy_document_id=document.id,
                    version_label="v1.0",
                    body_markdown=body_markdown,
                    changelog="Initial seeded policy shell.",
                    effective_at=utcnow(),
                    published_at=utcnow(),
                    is_published=True,
                )
            )

        existing_country_pairs = {
            (item.country_code, item.bucket_type)
            for item in self.session.scalars(select(CountryFeaturePolicy)).all()
        }
        for item in DEFAULT_COUNTRY_POLICIES:
            key = (str(item["country_code"]), str(item["bucket_type"]))
            if key in existing_country_pairs:
                continue
            self.session.add(CountryFeaturePolicy(**item))

        self.session.flush()

    def list_documents(self, *, mandatory_only: bool = False) -> list[PolicyDocument]:
        statement = (
            select(PolicyDocument)
            .options(selectinload(PolicyDocument.versions))
            .where(PolicyDocument.active.is_(True))
            .order_by(PolicyDocument.title.asc())
        )
        if mandatory_only:
            statement = statement.where(PolicyDocument.is_mandatory.is_(True))
        return list(self.session.scalars(statement).all())

    def get_document(self, document_key: str, *, version_label: str | None = None, include_unpublished: bool = False) -> PolicyDocumentVersion:
        statement: Select[tuple[PolicyDocumentVersion]] = (
            select(PolicyDocumentVersion)
            .join(PolicyDocument)
            .where(PolicyDocument.document_key == document_key)
            .options(selectinload(PolicyDocumentVersion.document))
        )
        if version_label is not None:
            statement = statement.where(PolicyDocumentVersion.version_label == version_label)
        else:
            statement = statement.order_by(desc(PolicyDocumentVersion.published_at))
            if not include_unpublished:
                statement = statement.where(PolicyDocumentVersion.effective_at <= utcnow())
        if not include_unpublished:
            statement = statement.where(PolicyDocumentVersion.is_published.is_(True))
        version = self.session.scalars(statement.limit(1)).first()
        if version is None:
            raise LookupError(f"Policy document '{document_key}' could not be found.")
        return version

    def accept_document(
        self,
        *,
        user_id: str,
        document_key: str,
        version_label: str,
        ip_address: str | None,
        device_id: str | None,
    ) -> PolicyAcceptanceRecord:
        version = self.get_document(document_key, version_label=version_label)
        existing = self.session.scalar(
            select(PolicyAcceptanceRecord).where(
                PolicyAcceptanceRecord.user_id == user_id,
                PolicyAcceptanceRecord.policy_document_version_id == version.id,
            )
        )
        if existing is not None:
            return existing
        acceptance = PolicyAcceptanceRecord(
            user_id=user_id,
            policy_document_version_id=version.id,
            accepted_at=utcnow(),
            ip_address=ip_address,
            device_id=device_id,
        )
        self.session.add(acceptance)
        self.session.flush()
        return acceptance

    def list_acceptances(self, *, user_id: str) -> list[PolicyAcceptanceRecord]:
        statement = (
            select(PolicyAcceptanceRecord)
            .join(PolicyDocumentVersion)
            .join(PolicyDocument)
            .where(PolicyAcceptanceRecord.user_id == user_id)
            .options(
                selectinload(PolicyAcceptanceRecord.document_version).selectinload(PolicyDocumentVersion.document)
            )
            .order_by(desc(PolicyAcceptanceRecord.accepted_at))
        )
        return list(self.session.scalars(statement).all())

    def upsert_document_version(self, *, payload) -> PolicyDocumentVersion:
        document = self.session.scalar(select(PolicyDocument).where(PolicyDocument.document_key == payload.document_key))
        if document is None:
            document = PolicyDocument(
                document_key=payload.document_key,
                title=payload.title,
                is_mandatory=payload.is_mandatory,
                active=payload.active,
            )
            self.session.add(document)
            self.session.flush()
        else:
            document.title = payload.title
            document.is_mandatory = payload.is_mandatory
            document.active = payload.active

        version = self.session.scalar(
            select(PolicyDocumentVersion).where(
                PolicyDocumentVersion.policy_document_id == document.id,
                PolicyDocumentVersion.version_label == payload.version_label,
            )
        )
        if version is None:
            version = PolicyDocumentVersion(
                policy_document_id=document.id,
                version_label=payload.version_label,
                body_markdown=payload.body_markdown,
                changelog=payload.changelog,
                effective_at=payload.effective_at or utcnow(),
                published_at=payload.published_at or utcnow(),
                is_published=payload.is_published,
            )
            self.session.add(version)
        else:
            version.body_markdown = payload.body_markdown
            version.changelog = payload.changelog
            version.effective_at = payload.effective_at or version.effective_at
            version.published_at = payload.published_at or version.published_at
            version.is_published = payload.is_published
        if payload.is_published:
            self.session.flush()
            for other in self.session.scalars(
                select(PolicyDocumentVersion).where(
                    PolicyDocumentVersion.policy_document_id == document.id,
                    PolicyDocumentVersion.id != version.id,
                )
            ).all():
                other.is_published = False
        self.session.flush()
        return version

    def list_country_policies(self) -> list[CountryFeaturePolicy]:
        statement = select(CountryFeaturePolicy).order_by(
            CountryFeaturePolicy.country_code.asc(),
            CountryFeaturePolicy.bucket_type.asc(),
        )
        return list(self.session.scalars(statement).all())

    def upsert_country_policy(self, *, payload) -> CountryFeaturePolicy:
        normalized_country_code = self.normalize_country_code(payload.country_code)
        policy = self.session.scalar(
            select(CountryFeaturePolicy).where(
                CountryFeaturePolicy.country_code == normalized_country_code,
                CountryFeaturePolicy.bucket_type == payload.bucket_type,
            )
        )
        if policy is None:
            policy = CountryFeaturePolicy(
                country_code=normalized_country_code,
                bucket_type=payload.bucket_type,
            )
            self.session.add(policy)

        policy.deposits_enabled = payload.deposits_enabled
        policy.market_trading_enabled = payload.market_trading_enabled
        policy.platform_reward_withdrawals_enabled = payload.platform_reward_withdrawals_enabled
        policy.user_hosted_gift_withdrawals_enabled = payload.user_hosted_gift_withdrawals_enabled
        policy.gtex_competition_gift_withdrawals_enabled = payload.gtex_competition_gift_withdrawals_enabled
        policy.national_reward_withdrawals_enabled = payload.national_reward_withdrawals_enabled
        policy.one_time_region_change_after_days = payload.one_time_region_change_after_days
        policy.active = payload.active
        self.session.flush()
        return policy

    def get_country_policy(self, country_code: str) -> CountryFeaturePolicy:
        normalized = country_code.strip().upper()
        policy = self.session.scalar(
            select(CountryFeaturePolicy)
            .where(CountryFeaturePolicy.country_code == normalized, CountryFeaturePolicy.active.is_(True))
            .order_by(CountryFeaturePolicy.bucket_type.asc())
        )
        if policy is not None:
            return policy
        fallback = self.session.scalar(
            select(CountryFeaturePolicy)
            .where(CountryFeaturePolicy.country_code == "GLOBAL", CountryFeaturePolicy.active.is_(True))
            .order_by(CountryFeaturePolicy.bucket_type.asc())
        )
        if fallback is None:
            raise LookupError(f"Country feature policy '{normalized}' could not be found.")
        return fallback


    def list_missing_acceptances(self, *, user_id: str) -> list[PolicyDocumentVersion]:
        documents = self.list_documents(mandatory_only=True)
        accepted_version_ids = {
            row.policy_document_version_id
            for row in self.session.scalars(
                select(PolicyAcceptanceRecord).where(PolicyAcceptanceRecord.user_id == user_id)
            ).all()
        }
        missing: list[PolicyDocumentVersion] = []
        now = utcnow()
        for document in documents:
            latest_version = next(
                (version for version in document.versions if version.is_published and version.effective_at <= now),
                None,
            )
            if latest_version is None:
                continue
            if latest_version.id not in accepted_version_ids:
                missing.append(latest_version)
        return missing

    def has_user_accepted_required_documents(self, *, user_id: str) -> bool:
        return not self.list_missing_acceptances(user_id=user_id)

    def get_user_region_profile(self, *, user_id: str) -> UserRegionProfile | None:
        return self.session.scalar(select(UserRegionProfile).where(UserRegionProfile.user_id == user_id))

    def ensure_user_region_profile(self, *, user, region_code: str | None = None) -> UserRegionProfile:
        profile = self.get_user_region_profile(user_id=user.id)
        if profile is not None:
            return profile
        normalized = self.normalize_country_code(region_code)
        now = utcnow()
        profile = UserRegionProfile(
            user_id=user.id,
            region_code=normalized,
            selected_at=now,
            last_changed_at=now,
            locked_until=now + timedelta(days=REGION_CHANGE_LOCK_DAYS),
            change_count=0,
            permanent_locked=False,
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def change_user_region(self, *, user, region_code: str) -> UserRegionProfile:
        normalized = self.normalize_country_code(region_code)
        profile = self.ensure_user_region_profile(user=user, region_code=normalized)
        if profile.region_code == normalized:
            return profile
        if profile.permanent_locked or profile.change_count >= 1:
            raise ValueError("Region is permanently locked after the one-time change.")
        if profile.locked_until and utcnow() < profile.locked_until:
            raise ValueError(f"Region cannot be changed until {profile.locked_until.date().isoformat()}.")
        profile.region_code = normalized
        profile.change_count += 1
        profile.last_changed_at = utcnow()
        profile.permanent_locked = True
        self.session.flush()
        return profile

    def override_user_region(
        self,
        *,
        user_id: str,
        region_code: str,
        actor_user_id: str | None,
        reason: str | None = None,
    ) -> UserRegionProfile:
        normalized = self.normalize_country_code(region_code)
        profile = self.get_user_region_profile(user_id=user_id)
        now = utcnow()
        if profile is None:
            profile = UserRegionProfile(
                user_id=user_id,
                region_code=normalized,
                selected_at=now,
                last_changed_at=now,
                locked_until=now + timedelta(days=REGION_CHANGE_LOCK_DAYS),
                change_count=0,
                permanent_locked=False,
            )
            self.session.add(profile)
        profile.region_code = normalized
        profile.last_changed_at = now
        profile.change_count = max(int(profile.change_count or 0), 1)
        profile.permanent_locked = True
        if profile.locked_until is None:
            profile.locked_until = profile.selected_at + timedelta(days=REGION_CHANGE_LOCK_DAYS)
        AuditTrailService(self.session).log_admin_override(
            actor_user_id=actor_user_id,
            action_key="policy.region.override",
            detail="Admin override applied to user region profile.",
            metadata={"user_id": user_id, "region_code": normalized, "reason": reason or ""},
        )
        self.session.flush()
        return profile

    def resolve_country_code_for_user(self, *, user) -> str:
        from backend.app.models.treasury import KycProfile

        region_profile = self.session.scalar(select(UserRegionProfile).where(UserRegionProfile.user_id == user.id))
        if region_profile is not None:
            return self.normalize_country_code(region_profile.region_code)

        profile = self.session.scalar(select(KycProfile).where(KycProfile.user_id == user.id))
        candidate = None
        if profile is not None:
            candidate = profile.country
        return self.normalize_country_code(candidate)

    def get_country_policy_for_user(self, *, user) -> CountryFeaturePolicy:
        return self.get_country_policy(self.resolve_country_code_for_user(user=user))

    @staticmethod
    def normalize_country_code(value: str | None) -> str:
        if value is None:
            return "GLOBAL"
        candidate = value.strip().upper()
        if not candidate:
            return "GLOBAL"
        aliases = {
            "NIGERIA": "NG",
            "NG": "NG",
            "NIG": "NG",
        }
        if candidate in aliases:
            return aliases[candidate]
        if len(candidate) == 2 and candidate.isalpha():
            return candidate
        return "GLOBAL"


def _load_default_policy_markdown(*, document_key: str, title: str) -> str:
    path = LEGAL_DOCS_ROOT / f"{document_key}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"# {title}\n\nThis policy shell is active but its detailed content has not been published yet."
