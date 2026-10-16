from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from hashlib import sha256
from uuid import uuid4

from app.common.enums.scout_assignment_status import ScoutAssignmentStatus
from app.common.enums.scouting_region_type import ScoutingRegionType
from app.common.enums.youth_prospect_rating_band import YouthProspectRatingBand
from app.schemas.club_ops_requests import CreateScoutAssignmentRequest
from app.schemas.scouting_core import ScoutAssignmentView, ScoutingRegionView

_FIRST_NAMES = ("Ayo", "Luka", "Noah", "Tobi", "Leo", "Kofi", "Musa", "Zane")
_LAST_NAMES = ("Mensah", "Okafor", "Kane", "Diallo", "Silva", "Bello", "Costa", "Adeyemi")
_POSITIONS = ("CB", "CM", "AM", "RW", "LW", "ST", "RB", "GK")
_SECONDARY = ("LB", "DM", "RM", "CF", "CAM", "WB", None)
_TRAITS = (
    "ball_progression",
    "press_resistance",
    "line_breaking_pass",
    "duel_timing",
    "recovery_speed",
    "box_arrivals",
    "finishing_timing",
    "goalkeeping_command",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True, frozen=True)
class ProspectBlueprint:
    display_name: str
    age: int
    nationality_code: str
    region_label: str
    primary_position: str
    secondary_position: str | None
    rating_band: YouthProspectRatingBand
    development_traits: tuple[str, ...]
    scouting_source: str
    confidence_bps: int
    strengths: tuple[str, ...]
    development_flags: tuple[str, ...]


class ScoutAssignmentService:
    def list_regions(self) -> tuple[ScoutingRegionView, ...]:
        return (
            ScoutingRegionView(
                id="region-domestic-core",
                code="domestic-core",
                name="Domestic Core",
                region_type=ScoutingRegionType.DOMESTIC,
                territory_codes=("NG", "GH", "ZA"),
                is_active=True,
            ),
            ScoutingRegionView(
                id="region-regional-west",
                code="regional-west",
                name="Regional West Corridor",
                region_type=ScoutingRegionType.REGIONAL,
                territory_codes=("CI", "SN", "ML"),
                is_active=True,
            ),
            ScoutingRegionView(
                id="region-euro-pathway",
                code="euro-pathway",
                name="Europe Pathway",
                region_type=ScoutingRegionType.INTERNATIONAL,
                territory_codes=("PT", "NL", "BE"),
                is_active=True,
            ),
            ScoutingRegionView(
                id="region-diaspora-link",
                code="diaspora-link",
                name="Diaspora Link",
                region_type=ScoutingRegionType.DIASPORA,
                territory_codes=("GB", "FR", "DE"),
                is_active=True,
            ),
        )

    def get_region(self, region_code: str) -> ScoutingRegionView | None:
        for region in self.list_regions():
            if region.code == region_code:
                return region
        return None

    def create_assignment(
        self,
        *,
        club_id: str,
        payload: CreateScoutAssignmentRequest,
    ) -> tuple[ScoutAssignmentView, tuple[ProspectBlueprint, ...]]:
        region = self.get_region(payload.region_code)
        if region is None:
            raise ValueError("scouting_region_not_found")

        starts_at = _utcnow()
        assignment = ScoutAssignmentView(
            id=f"sca-{uuid4().hex[:12]}",
            club_id=club_id,
            region_code=region.code,
            region_name=region.name,
            region_type=region.region_type,
            focus_area=payload.focus_area,
            budget_minor=payload.budget_minor,
            scout_count=payload.scout_count,
            status=ScoutAssignmentStatus.ACTIVE,
            report_confidence_floor_bps=payload.report_confidence_floor_bps,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(weeks=payload.duration_weeks),
            generated_prospect_ids=(),
        )
        blueprints = tuple(
            self._build_blueprint(
                club_id=club_id,
                assignment_id=assignment.id,
                region=region,
                focus_area=payload.focus_area,
                floor_bps=payload.report_confidence_floor_bps,
                index=index,
            )
            for index in range(max(2, min(5, payload.scout_count + 1)))
        )
        return assignment, blueprints

    def _build_blueprint(
        self,
        *,
        club_id: str,
        assignment_id: str,
        region: ScoutingRegionView,
        focus_area: str,
        floor_bps: int,
        index: int,
    ) -> ProspectBlueprint:
        digest = sha256(f"{club_id}:{assignment_id}:{region.code}:{focus_area}:{index}".encode("utf-8")).digest()
        first_name = _FIRST_NAMES[digest[0] % len(_FIRST_NAMES)]
        last_name = _LAST_NAMES[digest[1] % len(_LAST_NAMES)]
        primary_position = _POSITIONS[digest[2] % len(_POSITIONS)]
        secondary_position = _SECONDARY[digest[3] % len(_SECONDARY)]
        rating_band = (
            YouthProspectRatingBand.ELITE
            if digest[4] >= 220
            else YouthProspectRatingBand.HIGH_UPSIDE
            if digest[4] >= 150
            else YouthProspectRatingBand.DEVELOPMENT
            if digest[4] >= 80
            else YouthProspectRatingBand.FOUNDATION
        )
        confidence_bps = max(floor_bps, 6200 + (digest[5] % 2800))
        traits = (
            _TRAITS[digest[6] % len(_TRAITS)],
            _TRAITS[digest[7] % len(_TRAITS)],
        )
        strengths = (
            f"{primary_position.lower()} timing",
            focus_area.lower(),
        )
        return ProspectBlueprint(
            display_name=f"{first_name} {last_name}",
            age=14 + (digest[8] % 5),
            nationality_code=region.territory_codes[digest[9] % len(region.territory_codes)],
            region_label=region.name,
            primary_position=primary_position,
            secondary_position=secondary_position,
            rating_band=rating_band,
            development_traits=traits,
            scouting_source=f"{region.region_type.value}_assignment",
            confidence_bps=confidence_bps,
            strengths=strengths,
            development_flags=("academy_readiness", "match_exposure"),
        )


@lru_cache
def get_scout_assignment_service() -> ScoutAssignmentService:
    return ScoutAssignmentService()


__all__ = ["ProspectBlueprint", "ScoutAssignmentService", "get_scout_assignment_service"]
