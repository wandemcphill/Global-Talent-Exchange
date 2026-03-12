from __future__ import annotations

from dataclasses import dataclass

from backend.app.config.competition_constants import FINAL_PRESENTATION_MAX_MINUTES
from backend.app.world_super_cup.models import TrophyCeremonyMetadata


@dataclass(slots=True)
class TrophyCeremonyService:
    def build_metadata(self) -> TrophyCeremonyMetadata:
        return TrophyCeremonyMetadata(
            trophy_name="GTEX World Super Cup",
            host_city="Global Exchange Arena",
            presentation_minutes=FINAL_PRESENTATION_MAX_MINUTES,
            award_sequence=(
                "champions_walk",
                "silver_medals",
                "gold_medals",
                "golden_ball",
                "golden_boot",
                "trophy_lift",
            ),
            confetti_colors=("gold", "white", "emerald"),
            no_extra_time=True,
            penalties_if_tied=True,
        )
