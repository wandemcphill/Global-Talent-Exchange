"""Batch 25-27 club growth integration layer."""

from .academy_contract_bridge import ensure_academy_player_contract
from .service import ClubGrowthService

_original_promote_prospect = ClubGrowthService.promote_prospect


def _promote_prospect_with_contract(self, *, actor, club_id: str, prospect_id: str):
    result = _original_promote_prospect(
        self,
        actor=actor,
        club_id=club_id,
        prospect_id=prospect_id,
    )
    ensure_academy_player_contract(
        service=self,
        club_id=club_id,
        prospect_id=prospect_id,
    )
    return result


if getattr(ClubGrowthService.promote_prospect, "_gtex_academy_contract_bridge", False) is False:
    _promote_prospect_with_contract._gtex_academy_contract_bridge = True
    ClubGrowthService.promote_prospect = _promote_prospect_with_contract

__all__ = ["ClubGrowthService", "ensure_academy_player_contract"]
