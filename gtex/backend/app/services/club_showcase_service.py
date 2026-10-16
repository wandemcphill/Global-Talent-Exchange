from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.models.club_showcase_snapshot import ClubShowcaseSnapshot
from app.models.club_trophy import ClubTrophy
from app.schemas.club_identity_core import ClubBrandingAssetCore
from app.schemas.club_responses import ClubShowcaseView
from app.schemas.club_trophy_core import ClubTrophyCore
from app.services.club_branding_service import ClubBrandingService
from app.services.club_dynasty_service import ClubDynastyService
from app.services.club_reputation_service import ClubReputationService


@dataclass(slots=True)
class ClubShowcaseService:
    session: Session

    def get_showcase(self, club_id: str) -> ClubShowcaseView:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError(f"club {club_id} was not found")
        reputation = ClubReputationService(self.session).get_reputation(club_id)
        dynasty, _ = ClubDynastyService(self.session).get_dynasty(club_id)
        profile, theme, assets = ClubBrandingService(self.session).get_branding(club_id)
        trophies = self.session.scalars(
            select(ClubTrophy)
            .where(ClubTrophy.club_id == club_id)
            .order_by(ClubTrophy.is_featured.desc(), ClubTrophy.awarded_at.desc())
        ).all()
        featured = trophies[0] if trophies else None
        generated_at = datetime.now(timezone.utc)
        self.session.add(
            ClubShowcaseSnapshot(
                club_id=club_id,
                snapshot_key=f"showcase:{club_id}:{generated_at.isoformat()}",
                reputation_score=reputation.current_score,
                dynasty_score=dynasty.dynasty_score,
                featured_trophy_id=featured.id if featured is not None else None,
                theme_name=theme.name if theme is not None else None,
                showcase_json={
                    "asset_ids": [item.id for item in assets[:5]],
                    "trophy_ids": [item.id for item in trophies[:5]],
                },
            )
        )
        self.session.commit()
        return ClubShowcaseView(
            club_id=club_id,
            club_name=profile.club_name,
            slug=profile.slug,
            reputation_score=reputation.current_score,
            reputation_tier=reputation.tier,
            dynasty_score=dynasty.dynasty_score,
            dynasty_title=dynasty.dynasty_title,
            featured_trophy=ClubTrophyCore.model_validate(featured) if featured is not None else None,
            active_theme=theme,
            assets=[ClubBrandingAssetCore.model_validate(item) for item in assets],
            recent_trophies=[ClubTrophyCore.model_validate(item) for item in trophies[:5]],
            generated_at=generated_at,
        )
