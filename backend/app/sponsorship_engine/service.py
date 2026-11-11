from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_package import ClubSponsorshipPackage
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.sponsorship_engine import SponsorshipLead
from app.models.user import User
from app.models.wallet import (
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
)
from app.notifications.service import NotificationEventMatrixService
from app.sponsorship_engine.schemas import SPONSORSHIP_AMOUNT_CAP_ERROR, capped_sponsorship_amount_minor
from app.story_feed_engine.service import StoryFeedService
from app.wallets.service import LedgerError, LedgerPosting, WalletService

_AMOUNT_QUANTUM = Decimal("0.0001")
_OWNER_SHARE_RATE = Decimal("0.60")
SPONSORSHIP_FEE_ACCOUNT_CODE = "platform:credit:sponsorship_fee_revenue"
_SETTLEMENT_BALANCE_ERROR = "Platform Fan Coin balance cannot fund the owner share and the platform fee."
_SETTLEMENT_STATUS_ERROR = "Only an approved active sponsorship contract can be settled."


class SponsorshipEngineError(ValueError):
    pass


@dataclass(slots=True)
class SponsorshipEngineService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def seed_defaults(self) -> None:
        defaults = (
            {
                "code": "jersey-front-starter",
                "name": "Jersey Front Starter",
                "asset_type": SponsorshipAssetType.JERSEY_FRONT,
                "base_amount_minor": 250000,
                "currency": "CREDITS",
                "default_duration_months": 3,
                "payout_schedule": "monthly",
                "description": "Primary shirt-front slot for ambitious clubs building their first sponsor lane.",
            },
            {
                "code": "club-banner-regional",
                "name": "Club Banner Regional",
                "asset_type": SponsorshipAssetType.CLUB_BANNER,
                "base_amount_minor": 125000,
                "currency": "CREDITS",
                "default_duration_months": 2,
                "payout_schedule": "monthly",
                "description": "Banner inventory across club pages, dashboards, and community rails.",
            },
            {
                "code": "showcase-backdrop-premium",
                "name": "Showcase Backdrop Premium",
                "asset_type": SponsorshipAssetType.SHOWCASE_BACKDROP,
                "base_amount_minor": 400000,
                "currency": "CREDITS",
                "default_duration_months": 4,
                "payout_schedule": "monthly",
                "description": "Premium showcase branding for clubs with glossy presentation ambitions.",
            },
        )
        for item in defaults:
            existing = self.session.scalar(
                select(ClubSponsorshipPackage).where(ClubSponsorshipPackage.code == item["code"])
            )
            if existing is None:
                self.session.add(ClubSponsorshipPackage(**item))
        self.session.flush()

    def list_packages(self, *, active_only: bool = True) -> list[ClubSponsorshipPackage]:
        stmt = select(ClubSponsorshipPackage)
        if active_only:
            stmt = stmt.where(ClubSponsorshipPackage.is_active.is_(True))
        stmt = stmt.order_by(ClubSponsorshipPackage.base_amount_minor.desc(), ClubSponsorshipPackage.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def list_club_contracts(self, *, club_id: str) -> list[ClubSponsorshipContract]:
        return list(
            self.session.scalars(
                select(ClubSponsorshipContract)
                .where(ClubSponsorshipContract.club_id == club_id)
                .order_by(ClubSponsorshipContract.created_at.desc())
            ).all()
        )

    def list_my_leads(self, *, actor: User) -> list[SponsorshipLead]:
        return list(
            self.session.scalars(
                select(SponsorshipLead)
                .where(SponsorshipLead.requester_user_id == actor.id)
                .order_by(SponsorshipLead.created_at.desc())
            ).all()
        )

    def request_contract(self, *, actor: User, payload) -> tuple[SponsorshipLead, ClubSponsorshipContract]:
        club = self.session.get(ClubProfile, payload.club_id)
        if club is None:
            raise SponsorshipEngineError("Club was not found.")
        if club.owner_user_id != actor.id and actor.role.value != "admin":
            raise SponsorshipEngineError("Only the club owner can request sponsorship for this club.")
        package = self.session.scalar(
            select(ClubSponsorshipPackage).where(ClubSponsorshipPackage.code == payload.package_code)
        )
        if package is None or not package.is_active:
            raise SponsorshipEngineError("Sponsorship package is unavailable.")

        package_amount = int(package.base_amount_minor)
        custom_amount = getattr(payload, "custom_amount_minor", None)
        if custom_amount is None:
            amount_minor = package_amount
        elif type(custom_amount) is int:
            amount_minor = custom_amount
        else:
            amount_minor = 0
        if amount_minor <= 0 or amount_minor > package_amount:
            raise SponsorshipEngineError(SPONSORSHIP_AMOUNT_CAP_ERROR)
        try:
            schema_amount = capped_sponsorship_amount_minor(custom_amount, package_amount)
        except ValueError as exc:
            raise SponsorshipEngineError(SPONSORSHIP_AMOUNT_CAP_ERROR) from exc
        if schema_amount != amount_minor:
            raise SponsorshipEngineError(SPONSORSHIP_AMOUNT_CAP_ERROR)
        duration_months = payload.duration_months or package.default_duration_months
        payout_schedule = payload.payout_schedule or package.payout_schedule
        start_at = utcnow()
        end_at = start_at + timedelta(days=30 * duration_months)

        contract = ClubSponsorshipContract(
            club_id=club.id,
            package_id=package.id,
            asset_type=package.asset_type,
            sponsor_name=payload.sponsor_name,
            status=SponsorshipStatus.PENDING_APPROVAL,
            contract_amount_minor=amount_minor,
            currency=package.currency,
            duration_months=duration_months,
            payout_schedule=payout_schedule,
            start_at=start_at,
            end_at=end_at,
            moderation_required=True,
            moderation_status="pending_review",
            custom_copy=payload.custom_copy,
            custom_logo_url=payload.custom_logo_url,
            performance_bonus_minor=0,
            settled_amount_minor=0,
            outstanding_amount_minor=amount_minor,
        )
        self.session.add(contract)
        self.session.flush()

        lead = SponsorshipLead(
            contract_id=contract.id,
            club_id=club.id,
            requester_user_id=actor.id,
            sponsor_name=payload.sponsor_name,
            sponsor_email=payload.sponsor_email,
            sponsor_company=payload.sponsor_company,
            asset_type=package.asset_type.value if hasattr(package.asset_type, "value") else str(package.asset_type),
            status="submitted",
            proposal_note=payload.proposal_note,
            metadata_json=payload.metadata_json,
        )
        self.session.add(lead)
        self.session.flush()

        self._ensure_payout_schedule(contract)
        StoryFeedService(self.session).publish(
            story_type="sponsorship_request",
            title=f"{club.club_name} opened a sponsorship request",
            body=f"{payload.sponsor_name} requested the {package.name} package for {club.club_name}.",
            subject_type="club_profile",
            subject_id=club.id,
            metadata_json={"contract_id": contract.id, "package_code": package.code},
        )
        self.session.flush()
        return lead, contract

    def review_contract(
        self, *, actor: User, contract_id: str, action: str, resolution_note: str = ""
    ) -> ClubSponsorshipContract:
        contract = self.session.get(ClubSponsorshipContract, contract_id)
        if contract is None:
            raise SponsorshipEngineError("Contract was not found.")
        lead = self.session.scalar(select(SponsorshipLead).where(SponsorshipLead.contract_id == contract.id))

        if action == "approve":
            contract.status = SponsorshipStatus.ACTIVE
            contract.moderation_status = "approved"
            if lead is not None:
                lead.status = "approved"
                lead.reviewed_by_user_id = actor.id
        elif action == "reject":
            contract.status = SponsorshipStatus.CANCELLED
            contract.moderation_status = "rejected"
            if lead is not None:
                lead.status = "rejected"
                lead.reviewed_by_user_id = actor.id
                lead.metadata_json = {**(lead.metadata_json or {}), "resolution_note": resolution_note}
        elif action == "pause":
            contract.status = SponsorshipStatus.PAUSED
            contract.moderation_status = "paused"
        elif action == "resume":
            contract.status = SponsorshipStatus.ACTIVE
            contract.moderation_status = "approved"
        elif action == "complete":
            contract.status = SponsorshipStatus.COMPLETED
            contract.moderation_status = "completed"
            contract.outstanding_amount_minor = max(0, contract.contract_amount_minor - contract.settled_amount_minor)
        else:
            raise SponsorshipEngineError("Unsupported review action.")

        StoryFeedService(self.session).publish(
            story_type="sponsorship_update",
            title=f"Sponsorship contract {action}",
            body=f"{contract.sponsor_name} sponsorship for club {contract.club_id} moved to {contract.status.value if hasattr(contract.status, 'value') else contract.status}.",
            subject_type="sponsorship_contract",
            subject_id=contract.id,
            metadata_json={"action": action, "resolution_note": resolution_note},
            published_by_user_id=actor.id,
        )
        self.session.flush()
        return contract

    def settle_next_payout(
        self, *, actor: User, contract_id: str
    ) -> tuple[ClubSponsorshipContract, ClubSponsorshipPayout, Decimal, str]:
        contract = self.session.get(ClubSponsorshipContract, contract_id)
        if contract is None:
            raise SponsorshipEngineError("Contract was not found.")
        status_value = contract.status.value if hasattr(contract.status, "value") else str(contract.status)
        if status_value != SponsorshipStatus.ACTIVE.value:
            raise SponsorshipEngineError(_SETTLEMENT_STATUS_ERROR)
        club = self.session.get(ClubProfile, contract.club_id)
        if club is None:
            raise SponsorshipEngineError("Club was not found.")
        payout = self.session.scalar(
            select(ClubSponsorshipPayout)
            .where(ClubSponsorshipPayout.contract_id == contract.id, ClubSponsorshipPayout.status == "pending")
            .order_by(ClubSponsorshipPayout.due_at.asc())
        )
        if payout is None:
            raise SponsorshipEngineError("No pending sponsorship payout remains.")
        credit_amount = (Decimal(payout.amount_minor) / Decimal("100")).quantize(_AMOUNT_QUANTUM)
        # 60% club owner, 40% platform fee. Both legs must be funded or the settlement fails.
        owner_share = (credit_amount * _OWNER_SHARE_RATE).quantize(_AMOUNT_QUANTUM)
        platform_fee = (credit_amount - owner_share).quantize(_AMOUNT_QUANTUM)
        if owner_share <= 0 or platform_fee <= 0 or owner_share + platform_fee != credit_amount:
            raise SponsorshipEngineError("Sponsorship payout split is not payable.")
        wallet = self.wallet_service
        if wallet is None:
            raise SponsorshipEngineError("Wallet service is unavailable.")
        owner = self.session.get(User, club.owner_user_id)
        if owner is None:
            raise SponsorshipEngineError("Club owner was not found.")
        platform_account = wallet.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        platform_balance = self._backed_account_balance(platform_account)
        required_amount = (owner_share + platform_fee).quantize(_AMOUNT_QUANTUM)
        if platform_balance < owner_share or platform_balance < required_amount:
            raise SponsorshipEngineError(_SETTLEMENT_BALANCE_ERROR)
        projected_platform_balance = (platform_balance - required_amount).quantize(_AMOUNT_QUANTUM)
        if projected_platform_balance < Decimal("0.0000"):
            raise SponsorshipEngineError(_SETTLEMENT_BALANCE_ERROR)
        owner_account = wallet.get_user_account(self.session, owner, LedgerUnit.CREDIT)
        fee_account = wallet.ensure_named_system_account(
            self.session,
            code=SPONSORSHIP_FEE_ACCOUNT_CODE,
            label="Platform Fan Coin Sponsorship Fee Revenue",
            unit=LedgerUnit.CREDIT,
            allow_negative=False,
        )
        if fee_account.allow_negative:
            raise SponsorshipEngineError("Sponsorship platform fee cannot post to an allow-negative account.")
        # Clearing is created allow_negative and would mint Fan Coin. Hold that privilege
        # off for this posting so the ledger refuses an unbacked debit, then restore it.
        restore_allow_negative = bool(platform_account.allow_negative)
        platform_account.allow_negative = False
        try:
            wallet.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=owner_account,
                        amount=owner_share,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    ),
                    LedgerPosting(
                        account=fee_account,
                        amount=platform_fee,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    ),
                    LedgerPosting(
                        account=platform_account,
                        amount=-required_amount,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    ),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                reference=f"sponsorship:{contract.id}:{payout.id}",
                idempotency_key=f"sponsorship-settle:{contract.id}:{payout.id}",
                description=(
                    f"Sponsorship payout for {contract.sponsor_name} "
                    f"(owner 60%={owner_share}, platform 40%={platform_fee})"
                ),
                actor=actor,
            )
        except LedgerError as exc:
            raise SponsorshipEngineError(_SETTLEMENT_BALANCE_ERROR) from exc
        finally:
            platform_account.allow_negative = restore_allow_negative
        payout.status = "settled"
        payout.settled_at = utcnow()
        contract.settled_amount_minor += payout.amount_minor
        contract.outstanding_amount_minor = max(0, contract.contract_amount_minor - contract.settled_amount_minor)
        if contract.outstanding_amount_minor == 0:
            contract.status = SponsorshipStatus.COMPLETED
            contract.moderation_status = "completed"
        StoryFeedService(self.session).publish(
            story_type="sponsorship_payout",
            title=f"{club.club_name} received sponsorship revenue",
            body=(
                f"{contract.sponsor_name} sponsorship settled {owner_share:.4f} credits "
                f"to the club owner (60/40 split; platform retained {platform_fee:.4f})."
            ),
            subject_type="club_profile",
            subject_id=club.id,
            metadata_json={
                "contract_id": contract.id,
                "payout_id": payout.id,
                "credit_amount": str(credit_amount),
                "owner_share": str(owner_share),
                "platform_fee": str(platform_fee),
                "split": "60/40",
            },
            published_by_user_id=actor.id,
        )
        self._publish_matrix_notification(
            event_key="sponsorship_paid",
            target_user_ids=[club.owner_user_id],
            resource_id=payout.id,
            message=f"{contract.sponsor_name} sponsorship paid {owner_share:.4f} credits (60% owner share).",
            metadata={
                "club_id": club.id,
                "contract_id": contract.id,
                "payout_id": payout.id,
                "credit_amount": str(credit_amount),
                "owner_share": str(owner_share),
                "platform_fee": str(platform_fee),
                "currency": contract.currency,
                "route": "/app/club",
            },
        )
        self.session.flush()
        return contract, payout, owner_share, club.owner_user_id

    def dashboard(self, *, club_id: str) -> dict:
        contracts = self.list_club_contracts(club_id=club_id)
        active_contracts = [
            item
            for item in contracts
            if (item.status.value if hasattr(item.status, "value") else item.status) == SponsorshipStatus.ACTIVE.value
        ]
        pending_contracts = [
            item
            for item in contracts
            if (item.status.value if hasattr(item.status, "value") else item.status)
            == SponsorshipStatus.PENDING_APPROVAL.value
        ]
        completed_contracts = [
            item
            for item in contracts
            if (item.status.value if hasattr(item.status, "value") else item.status)
            == SponsorshipStatus.COMPLETED.value
        ]
        monthly_run_rate_minor = sum(
            int(item.contract_amount_minor / max(item.duration_months, 1)) for item in active_contracts
        )
        settled_total_minor = sum(item.settled_amount_minor for item in contracts)
        outstanding_total_minor = sum(item.outstanding_amount_minor for item in contracts)
        open_leads = int(
            self.session.scalar(
                select(func.count(SponsorshipLead.id)).where(
                    SponsorshipLead.club_id == club_id, SponsorshipLead.status.in_(["submitted", "approved"])
                )
            )
            or 0
        )
        currencies = sorted({item.currency for item in contracts})
        insights = [
            f"{len(active_contracts)} active sponsorship contract(s) currently power the club's commercial lane.",
            f"Outstanding sponsorship value sits at {outstanding_total_minor} minor units across signed deals.",
        ]
        if open_leads:
            insights.append(f"{open_leads} sponsorship lead(s) are still open in the review queue.")
        return {
            "club_id": club_id,
            "active_contracts": len(active_contracts),
            "pending_contracts": len(pending_contracts),
            "completed_contracts": len(completed_contracts),
            "monthly_run_rate_minor": monthly_run_rate_minor,
            "settled_total_minor": settled_total_minor,
            "outstanding_total_minor": outstanding_total_minor,
            "open_leads": open_leads,
            "currencies": currencies,
            "headline_insights": insights,
        }

    def _backed_account_balance(self, account) -> Decimal:
        """Read the lower of the projection and the entry sum, ignoring a hot balance cache."""
        self.session.flush()
        entry_sum = self.session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(LedgerEntry.account_id == account.id)
        )
        summed = Decimal(str(entry_sum or 0)).quantize(_AMOUNT_QUANTUM)
        projection = self.session.scalar(
            select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == account.id)
        )
        if projection is None:
            return summed
        projected = Decimal(str(projection.balance)).quantize(_AMOUNT_QUANTUM)
        return min(projected, summed)

    def _ensure_payout_schedule(self, contract: ClubSponsorshipContract) -> None:
        count = max(contract.duration_months, 1)
        existing = int(
            self.session.scalar(
                select(func.count(ClubSponsorshipPayout.id)).where(ClubSponsorshipPayout.contract_id == contract.id)
            )
            or 0
        )
        if existing >= count:
            return
        base_amount = int(contract.contract_amount_minor / count)
        remainder = int(contract.contract_amount_minor - (base_amount * count))
        for index in range(existing, count):
            amount = base_amount + (remainder if index == count - 1 else 0)
            payout = ClubSponsorshipPayout(
                contract_id=contract.id,
                due_at=contract.start_at + timedelta(days=30 * (index + 1)),
                amount_minor=amount,
                status="pending",
            )
            self.session.add(payout)
        self.session.flush()

    def _publish_matrix_notification(
        self,
        *,
        event_key: str,
        target_user_ids: list[str | None],
        resource_id: str,
        message: str,
        metadata: dict[str, object],
    ) -> None:
        if not self._notification_tables_available():
            return
        normalized_targets = [user_id for user_id in target_user_ids if user_id]
        if not normalized_targets:
            return
        NotificationEventMatrixService(self.session).publish_event(
            event_key=event_key,
            target_user_ids=normalized_targets,
            resource_id=resource_id,
            message=message,
            metadata_json=metadata,
        )

    def _notification_tables_available(self) -> bool:
        inspector = inspect(self.session.connection())
        return all(
            inspector.has_table(table_name)
            for table_name in ("notification_records", "notification_preferences", "users")
        )
