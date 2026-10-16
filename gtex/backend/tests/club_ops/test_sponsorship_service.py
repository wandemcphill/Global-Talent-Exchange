from __future__ import annotations

from app.common.enums.sponsorship_status import SponsorshipStatus
from app.schemas.club_ops_requests import CreateSponsorshipContractRequest, UpdateSponsorshipContractRequest


def test_sponsorship_service_exposes_catalog_and_contract_state(club_ops_services) -> None:
    sponsorship = club_ops_services["sponsorship"]

    catalog = sponsorship.list_catalog()

    assert len(catalog.packages) >= 4
    assert any(package.code == "community-jersey-front" for package in catalog.packages)


def test_sponsorship_contract_requires_moderation_and_posts_revenue_when_approved(club_ops_services) -> None:
    sponsorship = club_ops_services["sponsorship"]
    finance = club_ops_services["finance"]

    contract = sponsorship.create_contract(
        "club-sponsor",
        CreateSponsorshipContractRequest(
            package_code="community-jersey-front",
            sponsor_name="North Dock",
            duration_months=6,
            custom_copy="North Dock Academy",
        ),
    )
    assert contract.status == SponsorshipStatus.PENDING_APPROVAL
    assert contract.moderation_required is True

    updated = sponsorship.update_contract(
        "club-sponsor",
        contract.id,
        UpdateSponsorshipContractRequest(
            moderation_status="approved",
            status=SponsorshipStatus.ACTIVE,
        ),
    )
    overview = sponsorship.get_overview("club-sponsor")
    cashflow = finance.get_cashflow_summary("club-sponsor")

    assert updated.status == SponsorshipStatus.ACTIVE
    assert overview.active_contract_count == 1
    assert overview.visible_assets[0].contract_id == contract.id
    assert cashflow.sponsorship_income_minor > 0
