from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from backend.app.common.enums.sponsorship_status import SponsorshipStatus
from backend.app.models.base import utcnow
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_sponsorship_contract import ClubSponsorshipContract
from backend.app.models.club_sponsorship_package import ClubSponsorshipPackage
from backend.app.models.club_sponsorship_payout import ClubSponsorshipPayout
from backend.app.models.sponsorship_engine import SponsorshipLead
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.story_feed_engine.service import StoryFeedService
from backend.app.wallets.service import LedgerPosting, WalletService


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
            existing = self.session.scalar(select(ClubSponsorshipPackage).where(ClubSponsorshipPackage.code == item["code"]))
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
                select(SponsorshipLead).where(SponsorshipLead.requester_user_id == actor.id).order_by(SponsorshipLead.created_at.desc())
            ).all()
        )

    def request_contract(self, *, actor: User, payload) -> tuple[SponsorshipLead, ClubSponsorshipContract]:
        club = self.session.get(ClubProfile, payload.club_id)
        if club is None:
            raise SponsorshipEngineError("Club was not found.")
        if club.owner_user_id != actor.id and actor.role.value != "admin":
            raise SponsorshipEngineError("Only the club owner can request sponsorship for this club.")
        package = self.session.scalar(select(ClubSponsorshipPackage).where(ClubSponsorshipPackage.code == payload.package_code))
        if package is None or not package.is_active:
            raise SponsorshipEngineError("Sponsorship package is unavailable.")

        amount_minor = payload.custom_amount_minor if payload.custom_amount_minor is not None else package.base_amount_minor
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

    def review_contract(self, *, actor: User, contract_id: str, action: str, resolution_note: str = "") -> ClubSponsorshipContract:
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

    def settle_next_payout(self, *, actor: User, contract_id: str) -> tuple[ClubSponsorshipContract, ClubSponsorshipPayout, Decimal, str]:
        contract = self.session.get(ClubSponsorshipContract, contract_id)
        if contract is None:
            raise SponsorshipEngineError("Contract was not found.")
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
        credit_amount = (Decimal(payout.amount_minor) / Decimal("100")).quantize(Decimal("0.0001"))
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        owner_account = self.wallet_service.get_user_account(self.session, self.session.get(User, club.owner_user_id), LedgerUnit.CREDIT)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=owner_account, amount=credit_amount),
                LedgerPosting(account=platform_account, amount=-credit_amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=f"sponsorship:{contract.id}:{payout.id}",
            description=f"Sponsorship payout for {contract.sponsor_name}",
            actor=actor,
        )
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
            body=f"{contract.sponsor_name} sponsorship settled {credit_amount:.4f} credits into the club treasury lane.",
            subject_type="club_profile",
            subject_id=club.id,
            metadata_json={"contract_id": contract.id, "payout_id": payout.id, "credit_amount": str(credit_amount)},
            published_by_user_id=actor.id,
        )
        self.session.flush()
        return contract, payout, credit_amount, club.owner_user_id

    def dashboard(self, *, club_id: str) -> dict:
        contracts = self.list_club_contracts(club_id=club_id)
        active_contracts = [item for item in contracts if (item.status.value if hasattr(item.status, "value") else item.status) == SponsorshipStatus.ACTIVE.value]
        pending_contracts = [item for item in contracts if (item.status.value if hasattr(item.status, "value") else item.status) == SponsorshipStatus.PENDING_APPROVAL.value]
        completed_contracts = [item for item in contracts if (item.status.value if hasattr(item.status, "value") else item.status) == SponsorshipStatus.COMPLETED.value]
        monthly_run_rate_minor = sum(int(item.contract_amount_minor / max(item.duration_months, 1)) for item in active_contracts)
        settled_total_minor = sum(item.settled_amount_minor for item in contracts)
        outstanding_total_minor = sum(item.outstanding_amount_minor for item in contracts)
        open_leads = int(self.session.scalar(select(func.count(SponsorshipLead.id)).where(SponsorshipLead.club_id == club_id, SponsorshipLead.status.in_(["submitted", "approved"]))) or 0)
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

    def _ensure_payout_schedule(self, contract: ClubSponsorshipContract) -> None:
        count = max(contract.duration_months, 1)
        existing = int(self.session.scalar(select(func.count(ClubSponsorshipPayout.id)).where(ClubSponsorshipPayout.contract_id == contract.id)) or 0)
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
