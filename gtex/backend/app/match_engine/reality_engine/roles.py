from __future__ import annotations

from dataclasses import dataclass

from app.match_engine.simulation.models import InternalPlayer, PlayerRole


@dataclass(frozen=True, slots=True)
class RoleProfile:
    code: str
    display_name: str
    shot_volume: float = 1.0
    shot_quality: float = 1.0
    chance_creation: float = 1.0
    buildup: float = 1.0
    pressing: float = 1.0
    recovery: float = 1.0
    width: float = 1.0
    aerial: float = 1.0
    transition: float = 1.0
    goalkeeping: float = 1.0


_ROLE_PROFILES: dict[str, RoleProfile] = {
    "advanced_forward": RoleProfile(
        code="advanced_forward",
        display_name="Advanced Forward",
        shot_volume=1.22,
        shot_quality=1.14,
        chance_creation=0.92,
        buildup=0.94,
        pressing=1.04,
        transition=1.12,
    ),
    "inverted_winger": RoleProfile(
        code="inverted_winger",
        display_name="Inverted Winger",
        shot_volume=1.12,
        shot_quality=1.08,
        chance_creation=1.06,
        buildup=1.02,
        pressing=1.02,
        width=0.94,
        transition=1.08,
    ),
    "deep_lying_playmaker": RoleProfile(
        code="deep_lying_playmaker",
        display_name="Deep-Lying Playmaker",
        shot_volume=0.88,
        shot_quality=0.94,
        chance_creation=1.20,
        buildup=1.18,
        pressing=0.98,
        recovery=1.02,
        transition=0.98,
    ),
    "box_to_box_midfielder": RoleProfile(
        code="box_to_box_midfielder",
        display_name="Box-to-Box Midfielder",
        shot_volume=1.02,
        chance_creation=1.06,
        buildup=1.08,
        pressing=1.10,
        recovery=1.08,
        transition=1.08,
    ),
    "ball_playing_defender": RoleProfile(
        code="ball_playing_defender",
        display_name="Ball Playing Defender",
        shot_volume=0.84,
        shot_quality=0.92,
        chance_creation=0.96,
        buildup=1.10,
        pressing=1.00,
        recovery=1.08,
        aerial=1.06,
    ),
    "full_back": RoleProfile(
        code="full_back",
        display_name="Full Back",
        shot_volume=0.92,
        shot_quality=0.96,
        chance_creation=1.08,
        buildup=1.06,
        pressing=1.08,
        recovery=1.06,
        width=1.16,
        transition=1.06,
    ),
    "shot_stopper": RoleProfile(
        code="shot_stopper",
        display_name="Shot Stopper",
        buildup=0.92,
        recovery=0.96,
        goalkeeping=1.12,
    ),
    "center_back": RoleProfile(
        code="center_back",
        display_name="Center Back",
        shot_volume=0.76,
        shot_quality=0.90,
        buildup=0.96,
        recovery=1.12,
        aerial=1.10,
    ),
    "central_midfielder": RoleProfile(
        code="central_midfielder",
        display_name="Central Midfielder",
        shot_volume=0.96,
        chance_creation=1.05,
        buildup=1.04,
        pressing=1.04,
        recovery=1.03,
    ),
    "striker": RoleProfile(
        code="striker",
        display_name="Striker",
        shot_volume=1.10,
        shot_quality=1.05,
        chance_creation=0.96,
        transition=1.06,
    ),
}

_ALIASES = {
    "advancedforward": "advanced_forward",
    "poacher": "advanced_forward",
    "invertedwinger": "inverted_winger",
    "insideforward": "inverted_winger",
    "deeplyingplaymaker": "deep_lying_playmaker",
    "deepplaymaker": "deep_lying_playmaker",
    "playmaker": "deep_lying_playmaker",
    "controller": "deep_lying_playmaker",
    "boxtobox": "box_to_box_midfielder",
    "boxtoboxmidfielder": "box_to_box_midfielder",
    "ballplayingdefender": "ball_playing_defender",
    "fullback": "full_back",
    "wingback": "full_back",
    "shotstopper": "shot_stopper",
    "centerback": "center_back",
}

_DEFAULT_PROFILE_BY_ROLE = {
    PlayerRole.GOALKEEPER: _ROLE_PROFILES["shot_stopper"],
    PlayerRole.DEFENDER: _ROLE_PROFILES["center_back"],
    PlayerRole.MIDFIELDER: _ROLE_PROFILES["central_midfielder"],
    PlayerRole.FORWARD: _ROLE_PROFILES["striker"],
}


def resolve_role_profile(player: InternalPlayer) -> RoleProfile:
    archetype = _normalize_role_key(player.position_archetype)
    if archetype is not None:
        return _ROLE_PROFILES.get(archetype, _DEFAULT_PROFILE_BY_ROLE[player.role])
    return _DEFAULT_PROFILE_BY_ROLE[player.role]


def _normalize_role_key(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(character for character in value.lower() if character.isalnum())
    if not normalized:
        return None
    return _ALIASES.get(normalized, normalized if normalized in _ROLE_PROFILES else None)
