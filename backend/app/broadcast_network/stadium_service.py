from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.models.club_infra import ClubStadium
from app.models.creator_monetization import CreatorStadiumProfile


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True, slots=True)
class StadiumImmersionProfile:
    stadium_name: str
    stadium_theme: str
    region_personality: str
    crowd_personality: str
    home_bias: float
    away_bias: float


@dataclass(slots=True)
class StadiumImmersionService:
    session_factory: sessionmaker[Session] | None = None

    def resolve(
        self,
        *,
        home_team_id: str | None,
        away_team_id: str | None,
        atmosphere_profile: str,
    ) -> StadiumImmersionProfile:
        if self.session_factory is not None and home_team_id:
            with self.session_factory() as session:
                creator_profile = session.query(CreatorStadiumProfile).filter(CreatorStadiumProfile.club_id == home_team_id).one_or_none()
                if creator_profile is not None:
                    metadata = dict(creator_profile.metadata_json or {})
                    return StadiumImmersionProfile(
                        stadium_name=str(metadata.get("stadium_name") or metadata.get("display_name") or f"{home_team_id} Arena"),
                        stadium_theme=str(metadata.get("theme_key") or metadata.get("theme") or "creator_showcase"),
                        region_personality=str(metadata.get("region_personality") or "creator_league"),
                        crowd_personality=str(metadata.get("crowd_personality") or "charged"),
                        home_bias=0.68,
                        away_bias=0.32,
                    )
                club_stadium = session.query(ClubStadium).filter(ClubStadium.club_id == home_team_id).one_or_none()
                if club_stadium is not None:
                    return StadiumImmersionProfile(
                        stadium_name=club_stadium.name,
                        stadium_theme=club_stadium.theme_key,
                        region_personality=self._region_from_theme(club_stadium.theme_key),
                        crowd_personality=self._crowd_from_theme(club_stadium.theme_key),
                        home_bias=0.66,
                        away_bias=0.34,
                    )
        return self._catalog_default(atmosphere_profile=atmosphere_profile, home_team_id=home_team_id, away_team_id=away_team_id)

    def event_crowd_state(
        self,
        *,
        profile: StadiumImmersionProfile,
        base_home: float,
        base_away: float,
        raw_event_type: str,
        rivalry_intensity: float,
        scoring_side: str | None,
    ) -> dict[str, Any]:
        event_type = (raw_event_type or "").strip().lower()
        home_intensity = _clamp(base_home, 0.0, 1.0)
        away_intensity = _clamp(base_away, 0.0, 1.0)
        mood = "tense"
        spike = False
        stadium_fx = "ambient_loop"
        bias = "home" if home_intensity >= away_intensity else "away"

        if event_type in {"goal", "penalty_goal", "penalty_scored"}:
            spike = True
            mood = "celebratory"
            stadium_fx = "goal_horn"
            if scoring_side == "home":
                home_intensity = _clamp(home_intensity + 0.24, 0.0, 1.0)
                away_intensity = _clamp(away_intensity - 0.08, 0.0, 1.0)
                bias = "home"
            elif scoring_side == "away":
                away_intensity = _clamp(away_intensity + 0.24, 0.0, 1.0)
                home_intensity = _clamp(home_intensity - 0.08, 0.0, 1.0)
                bias = "away"
        elif event_type in {"missed_big_chance", "missed_chance", "woodwork", "shot_on_target", "shot"}:
            mood = "hype" if event_type == "shot_on_target" else "tense"
            spike = event_type in {"missed_big_chance", "woodwork"}
            stadium_fx = "crowd_groan" if event_type in {"missed_big_chance", "woodwork"} else "near_miss_swell"
            if scoring_side == "home":
                home_intensity = _clamp(home_intensity + 0.12, 0.0, 1.0)
            elif scoring_side == "away":
                away_intensity = _clamp(away_intensity + 0.12, 0.0, 1.0)
        elif event_type in {"red_card", "yellow_card", "card"}:
            mood = "angry" if event_type in {"red_card", "card"} else "tense"
            spike = event_type in {"red_card", "card"}
            stadium_fx = "whistle_sting"
        elif rivalry_intensity >= 0.7:
            mood = "hype"
            stadium_fx = "rivalry_bed"

        hostility = _clamp(abs(home_intensity - away_intensity) + (rivalry_intensity * 0.55), 0.0, 1.0)
        chant_level = _clamp(max(home_intensity, away_intensity) + (0.08 if rivalry_intensity >= 0.7 else 0.0), 0.0, 1.0)
        crowd_intensity = _clamp((home_intensity + away_intensity) / 2.0, 0.0, 1.0)
        return {
            "home_intensity": round(home_intensity, 3),
            "away_intensity": round(away_intensity, 3),
            "dominant_side": bias,
            "chant_level": round(chant_level, 3),
            "hostility": round(hostility, 3),
            "crowd_intensity": round(crowd_intensity, 3),
            "crowd_bias": bias,
            "crowd_mood": mood,
            "spike": spike,
            "stadium_fx": stadium_fx,
            "stadium_theme": profile.stadium_theme,
            "region_personality": profile.region_personality,
            "crowd_personality": profile.crowd_personality,
            "stadium_name": profile.stadium_name,
        }

    @staticmethod
    def _catalog_default(
        *,
        atmosphere_profile: str,
        home_team_id: str | None,
        away_team_id: str | None,
    ) -> StadiumImmersionProfile:
        profile = (atmosphere_profile or "standard").strip().lower()
        if profile in {"derby", "fever", "volatile"}:
            return StadiumImmersionProfile(
                stadium_name=f"{(home_team_id or 'Home').title()} Coliseum",
                stadium_theme=profile,
                region_personality="continental_cacophony" if away_team_id else "league_night",
                crowd_personality="restless",
                home_bias=0.67,
                away_bias=0.33,
            )
        return StadiumImmersionProfile(
            stadium_name=f"{(home_team_id or 'Home').title()} Park",
            stadium_theme="standard",
            region_personality="league_night",
            crowd_personality="measured",
            home_bias=0.64,
            away_bias=0.36,
        )

    @staticmethod
    def _region_from_theme(theme_key: str) -> str:
        normalized = (theme_key or "").strip().lower()
        if "derby" in normalized:
            return "inner_city_derby"
        if "final" in normalized or "elite" in normalized:
            return "continental_spotlight"
        return "league_night"

    @staticmethod
    def _crowd_from_theme(theme_key: str) -> str:
        normalized = (theme_key or "").strip().lower()
        if "creator" in normalized:
            return "performative"
        if "derby" in normalized:
            return "volatile"
        return "measured"


__all__ = ["StadiumImmersionProfile", "StadiumImmersionService"]
