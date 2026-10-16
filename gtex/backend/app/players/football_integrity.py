from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.players.read_models import PlayerSummaryReadModel

logger = logging.getLogger(__name__)


class FootballPosition(StrEnum):
    GK = "Goalkeeper"
    CB = "Center Back"
    LB = "Left Back"
    RB = "Right Back"
    CDM = "Defensive Midfielder"
    CM = "Central Midfielder"
    CAM = "Attacking Midfielder"
    LW = "Left Winger"
    RW = "Right Winger"
    ST = "Striker"


POSITION_ALIASES: dict[str, FootballPosition] = {
    "gk": FootballPosition.GK,
    "goalkeeper": FootballPosition.GK,
    "goal keeper": FootballPosition.GK,
    "keeper": FootballPosition.GK,
    "cb": FootballPosition.CB,
    "center back": FootballPosition.CB,
    "centre back": FootballPosition.CB,
    "centerback": FootballPosition.CB,
    "centreback": FootballPosition.CB,
    "central defender": FootballPosition.CB,
    "defender": FootballPosition.CB,
    "full back": FootballPosition.CB,
    "fullback": FootballPosition.CB,
    "lb": FootballPosition.LB,
    "left back": FootballPosition.LB,
    "left fullback": FootballPosition.LB,
    "left full back": FootballPosition.LB,
    "lwb": FootballPosition.LB,
    "rb": FootballPosition.RB,
    "right back": FootballPosition.RB,
    "right fullback": FootballPosition.RB,
    "right full back": FootballPosition.RB,
    "rwb": FootballPosition.RB,
    "cdm": FootballPosition.CDM,
    "dm": FootballPosition.CDM,
    "defensive mid": FootballPosition.CDM,
    "defensive midfielder": FootballPosition.CDM,
    "cm": FootballPosition.CM,
    "centre mid": FootballPosition.CM,
    "center mid": FootballPosition.CM,
    "central midfielder": FootballPosition.CM,
    "midfielder": FootballPosition.CM,
    "cam": FootballPosition.CAM,
    "am": FootballPosition.CAM,
    "attacking mid": FootballPosition.CAM,
    "attacking midfielder": FootballPosition.CAM,
    "lw": FootballPosition.LW,
    "left wing": FootballPosition.LW,
    "left winger": FootballPosition.LW,
    "winger": FootballPosition.LW,
    "rw": FootballPosition.RW,
    "right wing": FootballPosition.RW,
    "right winger": FootballPosition.RW,
    "st": FootballPosition.ST,
    "cf": FootballPosition.ST,
    "striker": FootballPosition.ST,
    "forward": FootballPosition.ST,
    "centre forward": FootballPosition.ST,
    "center forward": FootballPosition.ST,
}

POSITION_WEIGHTS: dict[FootballPosition, dict[str, float]] = {
    FootballPosition.GK: {
        "reflexes": 0.30,
        "diving": 0.25,
        "handling": 0.22,
        "positioning": 0.15,
        "mentality": 0.08,
    },
    FootballPosition.CB: {
        "defending": 0.24,
        "tackling": 0.22,
        "interceptions": 0.18,
        "physical": 0.16,
        "aerials": 0.12,
        "mentality": 0.08,
    },
    FootballPosition.LB: {
        "pace": 0.16,
        "defending": 0.20,
        "tackling": 0.16,
        "passing": 0.12,
        "physical": 0.12,
        "dribbling": 0.12,
        "mentality": 0.12,
    },
    FootballPosition.RB: {
        "pace": 0.16,
        "defending": 0.20,
        "tackling": 0.16,
        "passing": 0.12,
        "physical": 0.12,
        "dribbling": 0.12,
        "mentality": 0.12,
    },
    FootballPosition.CDM: {
        "defending": 0.17,
        "tackling": 0.15,
        "passing": 0.18,
        "vision": 0.12,
        "control": 0.14,
        "physical": 0.12,
        "mentality": 0.12,
    },
    FootballPosition.CM: {
        "passing": 0.22,
        "vision": 0.18,
        "control": 0.18,
        "mentality": 0.14,
        "dribbling": 0.10,
        "physical": 0.08,
        "defending": 0.10,
    },
    FootballPosition.CAM: {
        "vision": 0.20,
        "passing": 0.18,
        "control": 0.16,
        "dribbling": 0.16,
        "shooting": 0.14,
        "movement": 0.08,
        "mentality": 0.08,
    },
    FootballPosition.LW: {
        "pace": 0.20,
        "dribbling": 0.20,
        "movement": 0.14,
        "shooting": 0.13,
        "passing": 0.11,
        "composure": 0.10,
        "mentality": 0.12,
    },
    FootballPosition.RW: {
        "pace": 0.20,
        "dribbling": 0.20,
        "movement": 0.14,
        "shooting": 0.13,
        "passing": 0.11,
        "composure": 0.10,
        "mentality": 0.12,
    },
    FootballPosition.ST: {
        "finishing": 0.24,
        "shooting": 0.18,
        "movement": 0.16,
        "pace": 0.13,
        "composure": 0.14,
        "physical": 0.08,
        "mentality": 0.07,
    },
}

GENERIC_GSI_WEIGHTS: dict[str, float] = {
    "pace": 0.15,
    "shooting": 0.18,
    "passing": 0.17,
    "dribbling": 0.15,
    "defending": 0.15,
    "physical": 0.10,
    "mentality": 0.10,
}


@dataclass(frozen=True, slots=True)
class PositionRepairChange:
    player_id: str
    player_name: str
    previous_position: str | None
    previous_normalized_position: str | None
    repaired_position: str
    repaired_code: str
    reason: str


def normalize_position(value: str | FootballPosition | None) -> FootballPosition | None:
    if isinstance(value, FootballPosition):
        return value
    normalized = " ".join(str(value or "").replace("_", " ").replace("-", " ").split()).lower()
    if not normalized:
        return None
    return POSITION_ALIASES.get(normalized)


def validate_position_profile(position: FootballPosition, stats: Mapping[str, Any]) -> tuple[str, ...]:
    values = _normalized_attributes(stats)
    scores = _role_scores(values)
    if position == FootballPosition.GK:
        attacking = max(scores["fwd"], _attribute(values, "pace", "dribbling"))
        goalkeeping = scores["gk"]
        if attacking > goalkeeping + 12:
            return ("goalkeeper_profile_has_outfield_attributes",)
    if position in {FootballPosition.LW, FootballPosition.RW, FootballPosition.ST}:
        goalkeeping = scores["gk"]
        forward = scores["fwd"]
        if goalkeeping > forward + 10:
            return ("forward_profile_has_goalkeeper_attributes",)
    if position in {FootballPosition.CB, FootballPosition.LB, FootballPosition.RB}:
        defender = scores["def"]
        if scores["gk"] > defender + 10:
            return ("defender_profile_has_goalkeeper_attributes",)
        if scores["fwd"] > defender + 10:
            return ("defender_profile_has_forward_attributes",)
        if scores["mid"] > defender + 12:
            return ("defender_profile_has_midfielder_attributes",)
    if position in {FootballPosition.CDM, FootballPosition.CM, FootballPosition.CAM}:
        midfielder = scores["mid"]
        if scores["gk"] > midfielder + 10:
            return ("midfielder_profile_has_goalkeeper_attributes",)
        if scores["fwd"] > midfielder + 12:
            return ("midfielder_profile_has_forward_attributes",)
        if scores["def"] > midfielder + 12:
            return ("midfielder_profile_has_defender_attributes",)
    return tuple()


def infer_position_from_stat_profile(
    stats: Mapping[str, Any],
    *,
    fallback: str | FootballPosition | None = None,
    stable_key: str | None = None,
) -> FootballPosition:
    values = _normalized_attributes(stats)
    scores = _role_scores(values)
    best_role = max(scores.items(), key=lambda item: (item[1], item[0]))[0]
    if max(scores.values()) <= 0:
        return normalize_position(fallback) or FootballPosition.CM
    if best_role == "gk":
        return FootballPosition.GK
    if best_role == "def":
        wide_score = _attribute(values, "pace", "dribbling", "crossing")
        if wide_score >= _attribute(values, "strength", "aerials", "tackling"):
            return FootballPosition.RB if _stable_bit(stable_key or str(stats)) else FootballPosition.LB
        return FootballPosition.CB
    if best_role == "mid":
        attacking = _attribute(values, "vision", "shooting", "dribbling")
        defensive = _attribute(values, "tackling", "defending", "physical")
        if defensive > attacking + 8:
            return FootballPosition.CDM
        if attacking > defensive + 8:
            return FootballPosition.CAM
        return FootballPosition.CM
    wing_score = _attribute(values, "pace", "dribbling")
    striker_score = _attribute(values, "finishing", "shooting", "movement", "composure")
    if wing_score > striker_score + 4:
        return FootballPosition.RW if _stable_bit(stable_key or str(stats)) else FootballPosition.LW
    return FootballPosition.ST


def calculate_gsi(
    player: Player | Mapping[str, Any],
    *,
    position: str | FootballPosition | None = None,
    apply_variance: bool = True,
) -> int:
    stats = _player_stats_payload(player)
    resolved_position = normalize_position(position) or normalize_position(_position_value(player))
    weights = POSITION_WEIGHTS.get(resolved_position) if resolved_position is not None else GENERIC_GSI_WEIGHTS
    values = _normalized_attributes(stats)
    weighted_components = [
        (_attribute(values, key), weight)
        for key, weight in weights.items()
        if key in values
    ]
    total_weight = sum(weight for _, weight in weighted_components)
    weighted_score = (
        sum(value * weight for value, weight in weighted_components) / total_weight
        if total_weight > 0
        else 0.0
    )
    if weighted_score <= 0:
        weighted_score = _fallback_rating(player, resolved_position)
    if apply_variance:
        weighted_score += _deterministic_variance(_stable_player_key(player, resolved_position))
    return int(round(max(30.0, min(99.0, weighted_score))))


def gsi_band(score: int | float | None) -> str | None:
    if score is None:
        return None
    value = float(score)
    if value >= 90:
        return "World Class"
    if value >= 84:
        return "Elite"
    if value >= 75:
        return "Professional"
    if value >= 65:
        return "Average"
    if value >= 50:
        return "Developing"
    return "Youth"


def repairPlayerPositions(
    session: Session,
    *,
    dry_run: bool = True,
    limit: int | None = None,
) -> list[PositionRepairChange]:
    stmt = select(Player).order_by(Player.updated_at.desc(), Player.id.asc())
    if limit is not None:
        stmt = stmt.limit(max(1, limit))
    changes: list[PositionRepairChange] = []
    for player in session.scalars(stmt):
        stats = _player_stats_payload(player)
        current = normalize_position(player.normalized_position or player.position)
        inferred = infer_position_from_stat_profile(
            stats,
            fallback=player.normalized_position or player.position,
            stable_key=player.id,
        )
        reasons = validate_position_profile(current or inferred, stats)
        needs_repair = current is None or bool(reasons)
        if not needs_repair:
            continue
        change = PositionRepairChange(
            player_id=player.id,
            player_name=player.full_name,
            previous_position=player.position,
            previous_normalized_position=player.normalized_position,
            repaired_position=inferred.value,
            repaired_code=inferred.name,
            reason=",".join(reasons) if reasons else "invalid_or_missing_position",
        )
        changes.append(change)
        logger.info("player.position_repair %s", change)
        if not dry_run:
            player.position = inferred.value
            player.normalized_position = inferred.name
    if not dry_run:
        session.flush()
    return changes


def repair_player_positions(
    session: Session,
    *,
    dry_run: bool = True,
    limit: int | None = None,
) -> list[PositionRepairChange]:
    return repairPlayerPositions(session, dry_run=dry_run, limit=limit)


def repair_gsi_clusters(
    session: Session,
    *,
    dry_run: bool = True,
    clustered_values: tuple[int, ...] = (65, 75, 85),
    limit: int | None = None,
) -> list[dict[str, Any]]:
    stmt = select(Player, PlayerSummaryReadModel).join(
        PlayerSummaryReadModel,
        PlayerSummaryReadModel.player_id == Player.id,
    )
    if limit is not None:
        stmt = stmt.limit(max(1, limit))
    changes: list[dict[str, Any]] = []
    for player, summary in session.execute(stmt):
        payload = dict(summary.summary_json or {})
        raw_gsi = payload.get("global_scouting_index")
        try:
            current_gsi = int(round(float(raw_gsi)))
        except (TypeError, ValueError):
            continue
        if current_gsi not in clustered_values:
            continue
        repaired = calculate_gsi(player)
        if repaired == current_gsi:
            continue
        change = {
            "player_id": player.id,
            "player_name": player.full_name,
            "previous_gsi": current_gsi,
            "repaired_gsi": repaired,
        }
        changes.append(change)
        logger.info("player.gsi_repair %s", change)
        if not dry_run:
            payload["global_scouting_index"] = repaired
            payload["gsi_repair_source"] = "position_weighted_integrity_engine"
            summary.summary_json = payload
    if not dry_run:
        session.flush()
    return changes


def _player_stats_payload(player: Player | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(player, Mapping):
        return player
    payload: dict[str, Any] = {}
    if isinstance(player.dna_profile, Mapping):
        payload.update(player.dna_profile)
    payload.setdefault("height_cm", player.height_cm)
    payload.setdefault("weight_kg", player.weight_kg)
    payload.setdefault("market_value_eur", player.market_value_eur)
    payload.setdefault("position", player.position)
    payload.setdefault("normalized_position", player.normalized_position)
    return payload


def _position_value(player: Player | Mapping[str, Any]) -> str | None:
    if isinstance(player, Mapping):
        return str(player.get("normalized_position") or player.get("position") or "") or None
    return player.normalized_position or player.position


def _stable_player_key(player: Player | Mapping[str, Any], position: FootballPosition | None) -> str:
    if isinstance(player, Mapping):
        key = str(player.get("id") or player.get("player_id") or player.get("name") or player)
    else:
        key = f"{player.id}:{player.full_name}"
    return f"{key}:{position.name if position else 'GEN'}"


def _normalized_attributes(stats: Mapping[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    _collect_attributes(stats, values)
    if "strength" in values and "physical" not in values:
        values["physical"] = values["strength"]
    if "ball_control" in values and "control" not in values:
        values["control"] = values["ball_control"]
    if "positioning" not in values and "gk_positioning" in values:
        values["positioning"] = values["gk_positioning"]
    return values


def _collect_attributes(value: Any, output: dict[str, float]) -> None:
    if not isinstance(value, Mapping):
        return
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip().lower().replace(" ", "_")
        if isinstance(raw_value, Mapping):
            _collect_attributes(raw_value, output)
            continue
        try:
            numeric = float(raw_value)
        except (TypeError, ValueError):
            continue
        if 0 <= numeric <= 1:
            numeric *= 100
        output[key] = max(0.0, min(100.0, numeric))


def _attribute(values: Mapping[str, float], *keys: str) -> float:
    matches = [float(values[key]) for key in keys if key in values]
    if not matches:
        return 0.0
    return sum(matches) / len(matches)


def _role_scores(values: Mapping[str, float]) -> dict[str, float]:
    return {
        "gk": _attribute(values, "reflexes", "diving", "handling", "positioning", "saves"),
        "def": _attribute(values, "defending", "tackling", "interceptions", "strength", "aerials"),
        "mid": _attribute(values, "passing", "vision", "control", "mentality"),
        "fwd": _attribute(values, "finishing", "shooting", "movement", "pace", "dribbling", "composure"),
    }


def _fallback_rating(player: Player | Mapping[str, Any], position: FootballPosition | None) -> float:
    stats = _player_stats_payload(player)
    for key in ("overall", "overall_rating", "rating", "current_rating", "gsi", "global_scouting_index"):
        try:
            value = float(stats.get(key))  # type: ignore[arg-type]
        except (AttributeError, TypeError, ValueError):
            continue
        return value
    if position == FootballPosition.GK:
        return 62.0
    return 68.0


def _deterministic_variance(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    magnitude = 1 + digest[0] % 4
    sign = -1 if digest[1] % 2 else 1
    return sign * magnitude


def _stable_bit(key: str) -> bool:
    return hashlib.sha256(key.encode("utf-8")).digest()[0] % 2 == 0


__all__ = [
    "FootballPosition",
    "PositionRepairChange",
    "calculate_gsi",
    "gsi_band",
    "infer_position_from_stat_profile",
    "normalize_position",
    "repairPlayerPositions",
    "repair_gsi_clusters",
    "repair_player_positions",
    "validate_position_profile",
]
