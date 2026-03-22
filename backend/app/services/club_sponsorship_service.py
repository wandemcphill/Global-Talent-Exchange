from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import uuid4

from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.schemas.club_ops_requests import CreateSponsorshipContractRequest, UpdateSponsorshipContractRequest
from app.schemas.club_ops_responses import ClubSponsorshipCatalogResponse, ClubSponsorshipOverviewResponse
from app.schemas.sponsorship_core import (
    ClubSponsorshipAssetView,
    ClubSponsorshipContractView,
)
from app.services.club_finance_service import ClubFinanceService, ClubOpsStore, get_club_finance_service, get_club_ops_store
from app.services.sponsorship_catalog_service import SponsorshipCatalogService, get_sponsorship_catalog_service
from app.services.sponsorship_payout_service import SponsorshipPayoutService, get_sponsorship_payout_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ClubSponsorshipService:
    def __init__(
        self,
        *,
        store: ClubOpsStore | None = None,
        finance_service: ClubFinanceService | None = None,
        catalog_service: SponsorshipCatalogService | None = None,
        payout_service: SponsorshipPayoutService | None = None,
    ) -> None:
        self.store = store or get_club_ops_store()
        self.finance_service = finance_service or get_club_finance_service()
        self.catalog_service = catalog_service or get_sponsorship_catalog_service()
        self.payout_service = payout_service or get_sponsorship_payout_service()

    def list_catalog(self) -> ClubSponsorshipCatalogResponse:
        return ClubSponsorshipCatalogResponse(packages=self.catalog_service.list_packages())

    def get_overview(self, club_id: str) -> ClubSponsorshipOverviewResponse:
        self._ensure_club_inventory(club_id)
        with self.store.lock:
            contracts = tuple(self.store.sponsorship_contracts_by_club.get(club_id, {}).values())
            assets = tuple(self.store.sponsorship_assets_by_club.get(club_id, {}).values())
        return ClubSponsorshipOverviewResponse(
            club_id=club_id,
            contracts=contracts,
            visible_assets=assets,
            active_contract_count=sum(1 for contract in contracts if contract.status == SponsorshipStatus.ACTIVE),
            total_settled_revenue_minor=sum(contract.settled_amount_minor for contract in contracts),
        )

    def list_assets(self, club_id: str) -> tuple[ClubSponsorshipAssetView, ...]:
        self._ensure_club_inventory(club_id)
        with self.store.lock:
            return tuple(self.store.sponsorship_assets_by_club.get(club_id, {}).values())

    def create_contract(self, club_id: str, payload: CreateSponsorshipContractRequest) -> ClubSponsorshipContractView:
        self._ensure_club_inventory(club_id)
        package = self.catalog_service.get_package(payload.package_code)
        if package is None:
            raise ValueError("package_not_found")

        asset = self._available_asset(club_id, package.asset_type)
        if asset is None:
            raise ValueError("sponsorship_slot_unavailable")

        duration_months = payload.duration_months or package.default_duration_months
        payout_schedule = payload.payout_schedule or package.payout_schedule
        if payload.contract_amount_minor is None:
            scaled_amount = round(package.base_amount_minor * (duration_months / package.default_duration_months))
            contract_amount_minor = max(package.base_amount_minor, int(scaled_amount))
        else:
            contract_amount_minor = payload.contract_amount_minor

        moderation_required = bool(payload.custom_copy or payload.custom_logo_url)
        status = (
            SponsorshipStatus.PENDING_APPROVAL
            if moderation_required
            else (SponsorshipStatus.ACTIVE if payload.activate_immediately else SponsorshipStatus.DRAFT)
        )
        start_at = _utcnow()
        contract = ClubSponsorshipContractView(
            id=f"con-{uuid4().hex[:12]}",
            club_id=club_id,
            package_code=package.code,
            asset_type=package.asset_type,
            sponsor_name=payload.sponsor_name,
            status=status,
            contract_amount_minor=contract_amount_minor,
            currency=payload.currency,
            duration_months=duration_months,
            payout_schedule=payout_schedule,
            start_at=start_at,
            end_at=start_at + timedelta(days=30 * duration_months),
            moderation_required=moderation_required,
            moderation_status="pending" if moderation_required else "not_required",
            custom_copy=payload.custom_copy,
            custom_logo_url=payload.custom_logo_url,
            performance_bonus_minor=payload.performance_bonus_minor,
            settled_amount_minor=0,
            outstanding_amount_minor=contract_amount_minor,
            asset_slot_codes=(asset.slot_code,),
            payouts=(),
        )
        contract.payouts = self.payout_service.build_schedule(
            contract_id=contract.id,
            total_amount_minor=contract.contract_amount_minor,
            duration_months=duration_months,
            payout_schedule=payout_schedule,
            start_at=start_at,
        )
        if contract.status == SponsorshipStatus.ACTIVE:
            self.payout_service.settle_due_payouts(club_id=club_id, contract=contract, payouts=contract.payouts)

        asset.contract_id = contract.id
        asset.rendered_text = payload.custom_copy or payload.sponsor_name
        asset.asset_url = payload.custom_logo_url
        asset.moderation_required = moderation_required
        asset.moderation_status = contract.moderation_status

        with self.store.lock:
            self.store.sponsorship_contracts_by_club.setdefault(club_id, {})[contract.id] = contract
            self.store.sponsorship_assets_by_club.setdefault(club_id, {})[asset.id] = asset
        return contract

    def update_contract(
        self,
        club_id: str,
        contract_id: str,
        payload: UpdateSponsorshipContractRequest,
    ) -> ClubSponsorshipContractView:
        self._ensure_club_inventory(club_id)
        with self.store.lock:
            contract = self.store.sponsorship_contracts_by_club.get(club_id, {}).get(contract_id)
            if contract is None:
                raise ValueError("contract_not_found")
            assets = [
                asset
                for asset in self.store.sponsorship_assets_by_club.get(club_id, {}).values()
                if asset.contract_id == contract_id
            ]

        if payload.custom_copy is not None:
            contract.custom_copy = payload.custom_copy
        if payload.custom_logo_url is not None:
            contract.custom_logo_url = payload.custom_logo_url
        if payload.performance_bonus_minor is not None:
            contract.performance_bonus_minor = payload.performance_bonus_minor
        if payload.status is not None:
            contract.status = payload.status
        if payload.moderation_status is not None:
            contract.moderation_status = payload.moderation_status
            if payload.moderation_status == "approved" and contract.status in {
                SponsorshipStatus.DRAFT,
                SponsorshipStatus.PENDING_APPROVAL,
            }:
                contract.status = SponsorshipStatus.ACTIVE

        for asset in assets:
            asset.rendered_text = contract.custom_copy or contract.sponsor_name
            asset.asset_url = contract.custom_logo_url
            asset.moderation_required = contract.moderation_required
            asset.moderation_status = contract.moderation_status

        if payload.settle_due_payouts:
            self.payout_service.settle_due_payouts(club_id=club_id, contract=contract, payouts=contract.payouts)

        if contract.status in {SponsorshipStatus.CANCELLED, SponsorshipStatus.EXPIRED, SponsorshipStatus.COMPLETED}:
            for asset in assets:
                asset.contract_id = None
                asset.rendered_text = None
                asset.asset_url = None
                asset.moderation_required = False
                asset.moderation_status = "not_required"

        return contract

    def _ensure_club_inventory(self, club_id: str) -> None:
        self.finance_service.ensure_club_setup(club_id)
        with self.store.lock:
            self.store.sponsorship_contracts_by_club.setdefault(club_id, {})
            slots = self.store.sponsorship_assets_by_club.setdefault(club_id, {})
            if slots:
                return
            for asset_type in SponsorshipAssetType:
                asset = ClubSponsorshipAssetView(
                    id=f"asset-{uuid4().hex[:12]}",
                    club_id=club_id,
                    asset_type=asset_type,
                    slot_code=f"{club_id}-{asset_type.value}",
                    contract_id=None,
                    is_visible=True,
                    rendered_text=None,
                    asset_url=None,
                    moderation_required=False,
                    moderation_status="not_required",
                )
                slots[asset.id] = asset

    def _available_asset(self, club_id: str, asset_type: SponsorshipAssetType) -> ClubSponsorshipAssetView | None:
        with self.store.lock:
            for asset in self.store.sponsorship_assets_by_club.get(club_id, {}).values():
                if asset.asset_type == asset_type and asset.contract_id is None:
                    return asset
        return None


@lru_cache
def get_club_sponsorship_service() -> ClubSponsorshipService:
    return ClubSponsorshipService(
        store=get_club_ops_store(),
        finance_service=get_club_finance_service(),
        catalog_service=get_sponsorship_catalog_service(),
        payout_service=get_sponsorship_payout_service(),
    )


__all__ = ["ClubSponsorshipService", "get_club_sponsorship_service"]
