from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.common.enums.sponsorship_surface import SponsorshipSurface
from app.common.enums.sponsorship_status import SponsorshipStatus
from app.core.config import Settings, SponsorshipCampaignConfig
from app.models.club_sponsor import ClubSponsor
from app.models.club_sponsorship_contract import ClubSponsorshipContract


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


SURFACE_ASSET_MAP: dict[SponsorshipSurface, tuple[SponsorshipAssetType, ...]] = {
    SponsorshipSurface.STADIUM_BOARD: (SponsorshipAssetType.CLUB_BANNER,),
    SponsorshipSurface.TUNNEL_WALKOUT: (SponsorshipAssetType.SHOWCASE_BACKDROP,),
    SponsorshipSurface.REPLAY_STING: (SponsorshipAssetType.JERSEY_FRONT,),
    SponsorshipSurface.HALFTIME_OVERLAY: (SponsorshipAssetType.SHOWCASE_BACKDROP, SponsorshipAssetType.TOURNAMENT_CARD_SLOT),
    SponsorshipSurface.LINEUP_STRIP: (SponsorshipAssetType.JERSEY_FRONT, SponsorshipAssetType.JERSEY_BACK, SponsorshipAssetType.SLEEVE_SLOT),
    SponsorshipSurface.FINALS_TROPHY_BACKDROP: (SponsorshipAssetType.SHOWCASE_BACKDROP,),
}


@dataclass(frozen=True, slots=True)
class SponsorshipPlacement:
    surface: str
    sponsor_name: str
    campaign_code: str
    source: str
    asset_type: str | None
    creative_url: str | None
    fallback: bool
    metadata: dict[str, Any]


@dataclass(slots=True)
class SponsorshipPlacementService:
    session: Session
    settings: Settings
    analytics: AnalyticsService | None = None

    def resolve_placements(
        self,
        *,
        home_club_id: str | None,
        away_club_id: str | None,
        competition_id: str | None,
        stage_name: str | None,
        region_code: str | None,
        surfaces: tuple[str, ...] | None = None,
    ) -> list[SponsorshipPlacement]:
        requested_surfaces = surfaces or self.settings.sponsorship_inventory.surfaces
        club_ids = tuple(filter(None, (home_club_id, away_club_id)))
        club_sponsors = self._load_active_club_sponsors(club_ids)
        contracts = self._load_active_contracts(club_ids)
        placements: list[SponsorshipPlacement] = []
        for surface in requested_surfaces:
            placement = self._resolve_surface(
                surface=surface,
                club_sponsors=club_sponsors,
                contracts=contracts,
                competition_id=competition_id,
                stage_name=stage_name,
                region_code=region_code,
            )
            placements.append(placement)
            self._track_event(placement, competition_id=competition_id, stage_name=stage_name, region_code=region_code)
        return placements

    def _resolve_surface(
        self,
        *,
        surface: str,
        club_sponsors: dict[str, ClubSponsor],
        contracts: dict[SponsorshipSurface, ClubSponsorshipContract],
        competition_id: str | None,
        stage_name: str | None,
        region_code: str | None,
    ) -> SponsorshipPlacement:
        surface_enum = SponsorshipSurface(surface)
        sponsor = club_sponsors.get(surface_enum.value)
        if sponsor is not None:
            return SponsorshipPlacement(
                surface=surface_enum.value,
                sponsor_name=sponsor.sponsor_name,
                campaign_code=f"club-sponsor:{sponsor.id}",
                source="club_sponsor",
                asset_type=sponsor.category,
                creative_url=sponsor.creative_url,
                fallback=False,
                metadata={"club_id": sponsor.club_id, "club_sponsor_id": sponsor.id, "offer_id": sponsor.sponsor_offer_id},
            )
        contract = contracts.get(surface_enum)
        if contract is not None:
            return SponsorshipPlacement(
                surface=surface_enum.value,
                sponsor_name=contract.sponsor_name,
                campaign_code=f"contract:{contract.id}",
                source="club_contract",
                asset_type=contract.asset_type.value if hasattr(contract.asset_type, "value") else str(contract.asset_type),
                creative_url=contract.custom_logo_url,
                fallback=False,
                metadata={"club_id": contract.club_id, "contract_id": contract.id},
            )
        campaign = self._select_campaign(
            surface=surface_enum.value,
            competition_id=competition_id,
            stage_name=stage_name,
            region_code=region_code,
        )
        fallback = campaign.code == self.settings.sponsorship_inventory.default_campaign
        return SponsorshipPlacement(
            surface=surface_enum.value,
            sponsor_name=campaign.sponsor_name,
            campaign_code=campaign.code,
            source="campaign",
            asset_type=None,
            creative_url=campaign.creative_url,
            fallback=fallback,
            metadata={"internal": campaign.is_internal},
        )

    def _load_active_contracts(
        self,
        club_ids: tuple[str, ...],
    ) -> dict[SponsorshipSurface, ClubSponsorshipContract]:
        if not club_ids:
            return {}
        now = _utcnow()
        rows = self.session.scalars(
            select(ClubSponsorshipContract)
            .where(
                ClubSponsorshipContract.club_id.in_(club_ids),
                ClubSponsorshipContract.status == SponsorshipStatus.ACTIVE,
                ClubSponsorshipContract.start_at <= now,
                ClubSponsorshipContract.end_at >= now,
            )
        ).all()
        resolved: dict[SponsorshipSurface, ClubSponsorshipContract] = {}
        for contract in rows:
            for surface, asset_types in SURFACE_ASSET_MAP.items():
                if contract.asset_type in asset_types and surface not in resolved:
                    resolved[surface] = contract
        return resolved

    def _load_active_club_sponsors(self, club_ids: tuple[str, ...]) -> dict[str, ClubSponsor]:
        if not club_ids:
            return {}
        now = _utcnow()
        rows = self.session.scalars(
            select(ClubSponsor).where(
                ClubSponsor.club_id.in_(club_ids),
                ClubSponsor.status == "active",
                ClubSponsor.start_at <= now,
                ClubSponsor.end_at >= now,
            )
        ).all()
        resolved: dict[str, ClubSponsor] = {}
        for sponsor in sorted(rows, key=lambda item: item.contract_value_minor, reverse=True):
            for surface in sponsor.approved_surfaces_json or ():
                if surface not in resolved:
                    resolved[str(surface)] = sponsor
        return resolved

    def _select_campaign(
        self,
        *,
        surface: str,
        competition_id: str | None,
        stage_name: str | None,
        region_code: str | None,
    ) -> SponsorshipCampaignConfig:
        candidates = [
            campaign
            for campaign in self.settings.sponsorship_inventory.campaigns
            if surface in campaign.surfaces
            and self._matches_targeting(campaign, competition_id=competition_id, stage_name=stage_name, region_code=region_code)
        ]
        if not candidates:
            for campaign in self.settings.sponsorship_inventory.campaigns:
                if campaign.code == self.settings.sponsorship_inventory.default_campaign:
                    return campaign
            return self.settings.sponsorship_inventory.campaigns[0]
        return sorted(candidates, key=lambda item: item.priority, reverse=True)[0]

    def _matches_targeting(
        self,
        campaign: SponsorshipCampaignConfig,
        *,
        competition_id: str | None,
        stage_name: str | None,
        region_code: str | None,
    ) -> bool:
        if campaign.region_codes and (region_code or "").upper() not in {code.upper() for code in campaign.region_codes}:
            return False
        if campaign.competition_ids and (competition_id or "") not in campaign.competition_ids:
            return False
        if campaign.stage_names and (stage_name or "").lower() not in {name.lower() for name in campaign.stage_names}:
            return False
        return True

    def _track_event(
        self,
        placement: SponsorshipPlacement,
        *,
        competition_id: str | None,
        stage_name: str | None,
        region_code: str | None,
    ) -> None:
        if self.analytics is None:
            return
        self.analytics.track_event(
            self.session,
            name="club_sponsor.rendered" if placement.source == "club_sponsor" else "sponsorship.placement.selected",
            user_id=None,
            metadata={
                "surface": placement.surface,
                "campaign_code": placement.campaign_code,
                "source": placement.source,
                "fallback": placement.fallback,
                "competition_id": competition_id,
                "stage_name": stage_name,
                "region_code": region_code,
            },
        )


__all__ = ["SponsorshipPlacement", "SponsorshipPlacementService"]
