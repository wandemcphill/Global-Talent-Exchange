from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club_jersey_design import ClubJerseyDesign
from app.models.club_profile import ClubProfile
from app.schemas.club_branding_core import ClubJerseyDesignCore
from app.schemas.club_requests import JerseyCreateRequest, JerseyUpdateRequest


@dataclass(slots=True)
class ClubJerseyService:
    session: Session

    def create_jersey(
        self,
        *,
        club_id: str,
        owner_user_id: str,
        payload: JerseyCreateRequest,
    ) -> ClubJerseyDesign:
        self._require_owned_club(club_id, owner_user_id)
        jersey = ClubJerseyDesign(
            club_id=club_id,
            name=payload.name,
            slot_type=payload.slot_type.value,
            base_template_id=payload.base_template_id,
            primary_color=payload.primary_color,
            secondary_color=payload.secondary_color,
            trim_color=payload.trim_color,
            sleeve_style=payload.sleeve_style,
            motto_text=payload.motto_text,
            number_style=payload.number_style,
            crest_placement=payload.crest_placement,
            preview_asset_ref=payload.preview_asset_ref,
            moderation_status="pending_review" if payload.motto_text else "approved",
            metadata_json=payload.metadata_json,
        )
        self.session.add(jersey)
        self.session.commit()
        self.session.refresh(jersey)
        return jersey

    def update_jersey(
        self,
        *,
        club_id: str,
        jersey_id: str,
        owner_user_id: str,
        payload: JerseyUpdateRequest,
    ) -> ClubJerseyDesign:
        self._require_owned_club(club_id, owner_user_id)
        jersey = self.session.get(ClubJerseyDesign, jersey_id)
        if jersey is None or jersey.club_id != club_id:
            raise LookupError(f"jersey {jersey_id} was not found")
        updates = payload.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            setattr(jersey, field_name, value)
        if updates.get("motto_text"):
            jersey.moderation_status = "pending_review"
            jersey.moderation_reason = None
        self.session.commit()
        self.session.refresh(jersey)
        return jersey

    def list_jerseys(self, club_id: str) -> list[ClubJerseyDesignCore]:
        self._require_club(club_id)
        jerseys = self.session.scalars(
            select(ClubJerseyDesign)
            .where(ClubJerseyDesign.club_id == club_id)
            .order_by(ClubJerseyDesign.slot_type.asc(), ClubJerseyDesign.created_at.asc())
        ).all()
        return [ClubJerseyDesignCore.model_validate(item) for item in jerseys]

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError(f"club {club_id} was not found")
        return club

    def _require_owned_club(self, club_id: str, owner_user_id: str) -> ClubProfile:
        club = self._require_club(club_id)
        if club.owner_user_id != owner_user_id:
            raise PermissionError("club_owner_required")
        return club
