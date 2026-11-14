from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MatchBroadcastCategory(StrEnum):
    ORDINARY_LEAGUE = "ordinary_league"
    GROUP_STAGE = "group_stage"
    APPROVED_SHORTER_PRESENTATION = "approved_shorter_presentation"
    MAJOR_KNOCKOUT = "major_knockout"
    SEMI_FINAL = "semi_final"
    FINAL = "final"


# Maximum and window durations (in seconds) per Section 3.1
BROADCAST_CATEGORY_DURATION_WINDOWS: dict[MatchBroadcastCategory, tuple[int, int]] = {
    MatchBroadcastCategory.ORDINARY_LEAGUE: (480, 600),
    MatchBroadcastCategory.GROUP_STAGE: (480, 600),
    MatchBroadcastCategory.APPROVED_SHORTER_PRESENTATION: (180, 420),
    MatchBroadcastCategory.MAJOR_KNOCKOUT: (600, 900),
    MatchBroadcastCategory.SEMI_FINAL: (600, 900),
    MatchBroadcastCategory.FINAL: (600, 900),
}

BROADCAST_CATEGORY_MAX_SECONDS: dict[MatchBroadcastCategory, int] = {
    MatchBroadcastCategory.ORDINARY_LEAGUE: 600,
    MatchBroadcastCategory.GROUP_STAGE: 600,
    MatchBroadcastCategory.APPROVED_SHORTER_PRESENTATION: 600,
    MatchBroadcastCategory.MAJOR_KNOCKOUT: 900,
    MatchBroadcastCategory.SEMI_FINAL: 900,
    MatchBroadcastCategory.FINAL: 900,
}

PLAYABLE_OFFSIDE_BODY_PARTS: frozenset[str] = frozenset({"head", "torso", "foot"})
EXCLUDED_OFFSIDE_BODY_PARTS: frozenset[str] = frozenset({"hand", "arm", "forearm", "wrist"})

PERMITTED_VAR_CATEGORIES_2026_27: frozenset[str] = frozenset(
    {
        "goal_no_goal",
        "penalty_no_penalty",
        "red_card",
        "mistaken_identity",
        "corner_kick",
    }
)


@dataclass(slots=True, frozen=True)
class BodyPartLandmark:
    x: float
    y: float
    z: float
    body_part: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": round(float(self.x), 3),
            "y": round(float(self.y), 3),
            "z": round(float(self.z), 3),
            "body_part": self.body_part,
        }


@dataclass(slots=True, frozen=True)
class OffsideSnapshot:
    pass_contact_second: float
    passer_player_id: str | None
    passer_player_name: str | None
    attacker_player_id: str | None
    attacker_player_name: str | None
    second_last_opponent_id: str | None
    second_last_opponent_name: str | None
    last_opponent_id: str | None
    last_opponent_name: str | None
    attacking_direction: int
    ball_position: dict[str, float]
    attacker_position: dict[str, float]
    attacker_body_part: str
    attacker_landmark: BodyPartLandmark
    second_last_opponent_position: dict[str, float]
    second_last_opponent_body_part: str
    second_last_opponent_landmark: BodyPartLandmark
    offside_line_x: float
    attacker_line_x: float
    margin_meters: float
    is_offside_position: bool
    active_involvement: bool
    involvement_type: str
    deliberate_play_by_defender: bool
    deflection_or_save: str | None
    goalkeeper_throw_exception: bool
    is_penalised: bool
    assistant_flag_decision: str
    referee_decision: str
    restart_position: dict[str, float]
    law_reference: str = "IFAB_2026_27_LAW_11"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["attacker_landmark"] = self.attacker_landmark.to_dict()
        payload["second_last_opponent_landmark"] = self.second_last_opponent_landmark.to_dict()
        return payload


@dataclass(slots=True, frozen=True)
class VarReviewDecision:
    review_id: str
    category: str
    check_type: str  # "silent_check" | "on_field_review" | "factual_review"
    formal_review_initiated: bool
    clear_and_obvious_threshold_met: bool
    original_decision: str
    var_recommendation: str
    referee_final_authority: bool
    final_decision: str  # "confirmed" | "overturned"
    decision_outcome: str
    reason: str
    consequence_restart: str
    timeline_duration_seconds: float
    slow_motion_factor: float
    competition_allows_corner_var: bool = False
    offending_player_id: str | None = None
    offending_player_name: str | None = None
    corrected_player_id: str | None = None
    corrected_player_name: str | None = None
    presentation_steps: list[dict[str, Any]] = field(default_factory=list)
    law_reference: str = "IFAB_2026_27_VAR_PROTOCOL"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_match_broadcast_category(
    *,
    is_final: bool = False,
    stage: str | None = None,
    competition_type: str | None = None,
    approved_shorter_presentation: bool = False,
    metadata: dict[str, Any] | None = None,
) -> MatchBroadcastCategory:
    """Resolve the authoritative broadcast category strictly from competition/match stage.

    User identity, club identity, device, subscription, connection speed, and viewer
    playback preferences are never inputs to this function.
    """
    meta = metadata or {}
    explicit = str(meta.get("match_broadcast_category") or meta.get("competition_category") or "").strip().lower()
    if explicit in {item.value for item in MatchBroadcastCategory}:
        return MatchBroadcastCategory(explicit)

    if bool(meta.get("approved_shorter_presentation")) or approved_shorter_presentation:
        return MatchBroadcastCategory.APPROVED_SHORTER_PRESENTATION

    stage_norm = str(stage or meta.get("competition_stage") or meta.get("stage") or "").strip().lower()
    if is_final or bool(meta.get("is_final")) or stage_norm in {"final", "grand_final", "cup_final", "champions_final"}:
        return MatchBroadcastCategory.FINAL
    if stage_norm in {"semi_final", "semifinal", "semi-final", "semi finals", "semi_finals"}:
        return MatchBroadcastCategory.SEMI_FINAL
    if stage_norm in {
        "quarter_final",
        "quarterfinal",
        "quarter-final",
        "major_knockout",
        "knockout_ tie",
        "knockout",
        "round_of_16",
        "playoff_final",
    } or (str(competition_type or "").strip().lower() == "cup" and bool(meta.get("designated_major_knockout"))):
        return MatchBroadcastCategory.MAJOR_KNOCKOUT
    if stage_norm in {"group", "group_stage", "group stage", "league_phase"}:
        return MatchBroadcastCategory.GROUP_STAGE
    return MatchBroadcastCategory.ORDINARY_LEAGUE


def resolve_assigned_broadcast_duration(
    category: MatchBroadcastCategory,
    *,
    event_count: int = 24,
    high_impact_count: int = 6,
    var_review_count: int = 0,
) -> int:
    """Compute the deterministic broadcast duration for a match before broadcast begins.

    - Ordinary league & group-stage matches: 480-600s (8-10 minutes, hard cap 600s).
    - Approved shorter presentation: 180-420s (finishes earlier than 8-10m, hard cap 600s).
    - Major knockout, semi-final, final: 600-900s (up to 15 minutes, hard cap 900s).
    Matches finish earlier than their maximum unless event density warrants the upper bound.
    """
    minimum, maximum = BROADCAST_CATEGORY_DURATION_WINDOWS[category]
    hard_cap = BROADCAST_CATEGORY_MAX_SECONDS[category]

    # Normalize richness in [0.0, 0.92] so typical matches finish earlier than the hard cap
    # while dramatic, incident-heavy matches approach the upper limit without exceeding it.
    richness_raw = (max(0, event_count - 10) * 0.018) + (max(0, high_impact_count) * 0.045) + (var_review_count * 0.05)
    richness_ratio = min(0.92, max(0.08, richness_raw))
    duration = int(round(minimum + ((maximum - minimum) * richness_ratio)))
    return max(minimum, min(hard_cap, duration))


def build_universal_broadcast_session(
    *,
    match_id: str,
    category: MatchBroadcastCategory,
    assigned_duration_seconds: int,
    server_start_timestamp: datetime | str | None = None,
    current_position_seconds: float = 0.0,
    broadcast_status: str = "live",
    events: list[dict[str, Any]] | None = None,
    completion_timestamp: datetime | str | None = None,
) -> dict[str, Any]:
    """Construct the durable server-authoritative broadcast session contract."""
    hard_cap = BROADCAST_CATEGORY_MAX_SECONDS[category]
    clamped_duration = max(60, min(hard_cap, int(assigned_duration_seconds)))
    if isinstance(server_start_timestamp, datetime):
        started_iso = server_start_timestamp.astimezone(UTC).isoformat()
    elif isinstance(server_start_timestamp, str) and server_start_timestamp.strip():
        started_iso = server_start_timestamp.strip()
    else:
        started_iso = datetime.now(UTC).isoformat()

    if isinstance(completion_timestamp, datetime):
        completed_iso: str | None = completion_timestamp.astimezone(UTC).isoformat()
    elif isinstance(completion_timestamp, str) and completion_timestamp.strip():
        completed_iso = completion_timestamp.strip()
    else:
        completed_iso = None

    ordered_events: list[dict[str, Any]] = []
    source_refs: list[str] = []
    replay_and_var_segments: list[dict[str, Any]] = []

    for item in events or []:
        ev_id = str(item.get("event_id") or "")
        src_id = str(item.get("source_event_id") or item.get("metadata", {}).get("source_event_id") or ev_id)
        t_sec = round(float(item.get("time_seconds") or item.get("presentation_second") or 0.0), 2)
        ev_type = str(item.get("event_type") or "neutral").lower()
        ordered_events.append(
            {
                "event_id": ev_id,
                "source_simulation_event_id": src_id,
                "sequence": int(item.get("sequence") or 0),
                "minute": int(item.get("minute") or 0),
                "time_seconds": t_sec,
                "event_type": ev_type,
            }
        )
        if src_id and src_id not in source_refs:
            source_refs.append(src_id)
        if (
            ev_type in {"goal", "penalty", "offside", "red_card"}
            or item.get("var_review")
            or item.get("offside_snapshot")
        ):
            seg_kind = (
                "var_review"
                if item.get("var_review")
                else ("offside_replay" if ev_type == "offside" else "incident_replay")
            )
            seg_dur = 6.0 if seg_kind == "var_review" else 4.2
            replay_and_var_segments.append(
                {
                    "segment_id": f"{ev_id}:{seg_kind}",
                    "source_event_id": src_id,
                    "kind": seg_kind,
                    "start_second": round(max(0.0, t_sec), 2),
                    "end_second": round(min(float(clamped_duration), t_sec + seg_dur), 2),
                    "duration_seconds": seg_dur,
                    "slow_motion_factor": 0.45 if seg_kind in {"var_review", "offside_replay"} else 0.65,
                }
            )

    pos_clamped = round(max(0.0, min(float(clamped_duration), float(current_position_seconds))), 2)
    return {
        "match_id": match_id,
        "competition_category": category.value,
        "match_category": category.value,
        "assigned_duration_seconds": clamped_duration,
        "max_allowed_duration_seconds": hard_cap,
        "server_start_timestamp": started_iso,
        "current_broadcast_position_seconds": pos_clamped,
        "broadcast_status": broadcast_status,
        "ordered_presentation_events": ordered_events,
        "source_simulation_event_refs": source_refs,
        "replay_and_var_segments": replay_and_var_segments,
        "completion_timestamp": completed_iso,
        "viewer_controls_disabled": True,
        "shared_clock_authority": "server_authoritative",
    }


def evaluate_law11_offside(
    *,
    pass_contact_second: float,
    attacking_direction: int,  # +1 if attacking toward x=100, -1 if attacking toward x=0
    ball_x: float,
    ball_y: float,
    attacker_id: str | None,
    attacker_name: str | None,
    attacker_x: float,
    attacker_y: float,
    attacker_body_part: str = "foot",
    attacker_lean_offset_x: float = 0.55,
    opponents: list[dict[str, Any]],
    passer_id: str | None = None,
    passer_name: str | None = None,
    restart_context: str = "open_play",  # "open_play" | "goal_kick" | "throw_in" | "corner_kick" | "gk_throw"
    active_involvement: bool = True,
    involvement_type: str = "interfering_with_play",
    deliberate_play_by_defender: bool = False,
    deflection_or_save: str | None = None,  # None | "deflection" | "rebound" | "deliberate_save"
) -> OffsideSnapshot:
    """Authoritative IFAB 2026/27 Law 11 offside calculation at exact ball-play contact moment."""
    direction = 1 if attacking_direction >= 0 else -1

    # Normalize body part: hands and arms are excluded under Law 11; map any arm/hand input
    # to the torso/shoulder line at the bottom of the armpit.
    raw_attacker_part = str(attacker_body_part or "foot").strip().lower()
    effective_attacker_part = (
        "torso"
        if raw_attacker_part in EXCLUDED_OFFSIDE_BODY_PARTS
        else (raw_attacker_part if raw_attacker_part in PLAYABLE_OFFSIDE_BODY_PARTS else "torso")
    )
    part_z_map = {"foot": 0.12, "torso": 1.15, "head": 1.68}
    part_reach_map = {
        "foot": abs(attacker_lean_offset_x),
        "torso": abs(attacker_lean_offset_x) * 0.75,
        "head": abs(attacker_lean_offset_x) * 0.85,
    }
    attacker_landmark_x = max(
        0.0, min(100.0, float(attacker_x) + (direction * part_reach_map[effective_attacker_part]))
    )
    attacker_landmark = BodyPartLandmark(
        x=attacker_landmark_x,
        y=float(attacker_y),
        z=part_z_map[effective_attacker_part],
        body_part=effective_attacker_part,
    )

    # Sort opponents by proximity to their own goal line (x=100 when direction=+1, x=0 when direction=-1)
    enriched_opponents: list[tuple[float, dict[str, Any], BodyPartLandmark]] = []
    for opp in opponents:
        opp_x = float(opp.get("x", 50.0))
        opp_y = float(opp.get("y", 50.0))
        raw_opp_part = str(opp.get("body_part") or "foot").strip().lower()
        eff_opp_part = (
            "torso"
            if raw_opp_part in EXCLUDED_OFFSIDE_BODY_PARTS
            else (raw_opp_part if raw_opp_part in PLAYABLE_OFFSIDE_BODY_PARTS else "foot")
        )
        opp_reach = float(opp.get("lean_offset_x", 0.42))
        opp_landmark_x = max(0.0, min(100.0, opp_x + (direction * opp_reach)))
        landmark = BodyPartLandmark(
            x=opp_landmark_x,
            y=opp_y,
            z=part_z_map[eff_opp_part],
            body_part=eff_opp_part,
        )
        # Distance to goal line: higher x is closer to x=100; lower x is closer to x=0
        goal_proximity = opp_landmark_x if direction == 1 else (100.0 - opp_landmark_x)
        enriched_opponents.append((goal_proximity, opp, landmark))

    enriched_opponents.sort(key=lambda item: item[0], reverse=True)
    if len(enriched_opponents) >= 2:
        last_opp = enriched_opponents[0][1]
        second_last_opp = enriched_opponents[1][1]
        second_last_landmark = enriched_opponents[1][2]
    elif len(enriched_opponents) == 1:
        last_opp = enriched_opponents[0][1]
        second_last_opp = enriched_opponents[0][1]
        second_last_landmark = enriched_opponents[0][2]
    else:
        default_x = 84.0 if direction == 1 else 16.0
        last_opp = {"player_id": "opp-gk", "player_name": "Goalkeeper", "x": 95.0 if direction == 1 else 5.0, "y": 50.0}
        second_last_opp = {"player_id": "opp-def", "player_name": "Defender", "x": default_x, "y": float(attacker_y)}
        second_last_landmark = BodyPartLandmark(x=default_x, y=float(attacker_y), z=0.12, body_part="foot")

    offside_line_x = second_last_landmark.x
    # Pitch length is 105m mapped across [0..100], so 1 pitch X unit = 1.05 meters.
    signed_pitch_delta = (attacker_landmark_x - offside_line_x) * direction
    margin_meters = round(signed_pitch_delta * 1.05, 2)

    # Check Law 11 exemptions:
    in_own_half = (attacker_landmark_x <= 50.0) if direction == 1 else (attacker_landmark_x >= 50.0)
    behind_or_level_with_ball = ((attacker_landmark_x - float(ball_x)) * direction) <= 0.05
    level_with_second_last_opponent = margin_meters <= 0.05  # Level with second-last opponent is ONSIDE
    restart_norm = str(restart_context or "open_play").strip().lower()
    gk_throw_exception = restart_norm in {"gk_throw", "goalkeeper_throw"}
    direct_exempt_restart = restart_norm in {"goal_kick", "throw_in", "corner_kick"} or gk_throw_exception

    is_offside_position = not (
        in_own_half or behind_or_level_with_ball or level_with_second_last_opponent or direct_exempt_restart
    )

    # Active play & deliberate play vs deflection/save evaluation
    if not is_offside_position:
        is_penalised = False
        resolved_involvement = "onside"
    elif not active_involvement or str(involvement_type).strip().lower() in {
        "passive",
        "passive_not_penalised",
        "none",
    }:
        # Standing in an offside position without active involvement is NOT an offence
        is_penalised = False
        resolved_involvement = "passive_not_penalised"
    elif deliberate_play_by_defender and deflection_or_save not in {"deflection", "rebound", "deliberate_save"}:
        # Opponent deliberately played the ball (not a deliberate save or accidental deflection) -> resets offside
        is_penalised = False
        resolved_involvement = "reset_by_deliberate_play"
    elif deflection_or_save in {"deflection", "rebound", "deliberate_save"}:
        # Attacker in offside position gaining advantage from rebound/deflection or deliberate save IS penalised
        is_penalised = True
        resolved_involvement = "gaining_advantage"
    else:
        is_penalised = True
        resolved_involvement = (
            involvement_type
            if involvement_type in {"interfering_with_play", "interfering_with_opponent", "gaining_advantage"}
            else "interfering_with_play"
        )

    assistant_flag = "flag_raised" if is_penalised else "keep_flag_down"
    referee_decision = "indirect_free_kick" if is_penalised else "play_continues"
    restart_pos = {
        "x": round(float(attacker_x), 2),
        "y": round(float(attacker_y), 2),
    }

    return OffsideSnapshot(
        pass_contact_second=round(float(pass_contact_second), 2),
        passer_player_id=passer_id,
        passer_player_name=passer_name,
        attacker_player_id=attacker_id,
        attacker_player_name=attacker_name,
        second_last_opponent_id=str(second_last_opp.get("player_id") or "") or None,
        second_last_opponent_name=str(second_last_opp.get("player_name") or "") or None,
        last_opponent_id=str(last_opp.get("player_id") or "") or None,
        last_opponent_name=str(last_opp.get("player_name") or "") or None,
        attacking_direction=direction,
        ball_position={"x": round(float(ball_x), 2), "y": round(float(ball_y), 2)},
        attacker_position={"x": round(float(attacker_x), 2), "y": round(float(attacker_y), 2)},
        attacker_body_part=effective_attacker_part,
        attacker_landmark=attacker_landmark,
        second_last_opponent_position={
            "x": round(float(second_last_opp.get("x", offside_line_x)), 2),
            "y": round(float(second_last_opp.get("y", attacker_y)), 2),
        },
        second_last_opponent_body_part=second_last_landmark.body_part,
        second_last_opponent_landmark=second_last_landmark,
        offside_line_x=round(offside_line_x, 3),
        attacker_line_x=round(attacker_landmark_x, 3),
        margin_meters=margin_meters,
        is_offside_position=is_offside_position,
        active_involvement=bool(active_involvement),
        involvement_type=resolved_involvement,
        deliberate_play_by_defender=bool(deliberate_play_by_defender),
        deflection_or_save=deflection_or_save,
        goalkeeper_throw_exception=gk_throw_exception,
        is_penalised=is_penalised,
        assistant_flag_decision=assistant_flag,
        referee_decision=referee_decision,
        restart_position=restart_pos,
    )


def evaluate_var_review_2026_27(
    *,
    review_id: str,
    category: str,
    original_decision: str,
    clear_and_obvious_error: bool,
    reason: str,
    factual_incident: bool = False,
    is_second_yellow_review: bool = False,
    competition_allows_corner_var: bool = False,
    restart_already_taken_or_delayed: bool = False,
    offending_player_id: str | None = None,
    offending_player_name: str | None = None,
    corrected_player_id: str | None = None,
    corrected_player_name: str | None = None,
) -> VarReviewDecision | None:
    """Evaluate a potential VAR intervention under the IFAB 2026/27 VAR protocol.

    Returns `None` if the category is not reviewable under the 2026/27 protocol
    (e.g., ordinary first yellow card without mistaken identity, throw-in, or corner
    kick when competition opt-in is disabled or restart would be delayed).
    """
    cat_norm = str(category or "").strip().lower()
    if cat_norm not in PERMITTED_VAR_CATEGORIES_2026_27:
        return None

    # Category 5: Optional corner kick review is ONLY permitted when the competition
    # explicitly enables it AND correction can be made immediately without delaying restart.
    if cat_norm == "corner_kick":
        if not competition_allows_corner_var or restart_already_taken_or_delayed:
            return None

    # If the clear-and-obvious-error / serious-missed-incident threshold is NOT met,
    # VAR performs a silent background check only and does NOT initiate a formal review.
    if not clear_and_obvious_error:
        return VarReviewDecision(
            review_id=review_id,
            category=cat_norm,
            check_type="silent_check",
            formal_review_initiated=False,
            clear_and_obvious_threshold_met=False,
            original_decision=original_decision,
            var_recommendation="check_complete_confirm",
            referee_final_authority=True,
            final_decision="confirmed",
            decision_outcome=f"{original_decision}_confirmed",
            reason=reason or "No clear and obvious error identified during silent VAR check.",
            consequence_restart=_consequence_restart_for(cat_norm, original_decision, overturned=False),
            timeline_duration_seconds=0.0,
            slow_motion_factor=1.0,
            competition_allows_corner_var=competition_allows_corner_var,
            offending_player_id=offending_player_id,
            offending_player_name=offending_player_name,
            presentation_steps=[],
        )

    # Formal review initiated: factual (offside line, inside/outside box, mistaken identity, corner)
    # vs on-field review (OFR at referee review area monitor).
    is_factual = factual_incident or cat_norm in {"mistaken_identity", "corner_kick"}
    check_type = "factual_review" if is_factual else "on_field_review"
    var_rec = "recommend_factual_overturn" if is_factual else "recommend_on_field_review"
    final_decision = "overturned"
    decision_outcome = _resolve_decision_outcome(
        cat_norm,
        original_decision=original_decision,
        overturned=True,
        is_second_yellow_review=is_second_yellow_review,
    )
    consequence_restart = _consequence_restart_for(cat_norm, original_decision, overturned=True)

    steps = [
        {
            "step": 1,
            "code": "original_referee_decision",
            "label": f"On-field call: {original_decision.replace('_', ' ').title()}",
        },
        {
            "step": 2,
            "code": "incident_replay",
            "label": "Broadcast replay of the key contact moment",
        },
        {
            "step": 3,
            "code": "var_check_in_progress",
            "label": f"VAR Check: {cat_norm.replace('_', ' ').title()}",
        },
        {
            "step": 4,
            "code": "referee_review_monitor" if check_type == "on_field_review" else "factual_communication",
            "label": (
                "Referee On-Field Review (OFR) at pitchside monitor"
                if check_type == "on_field_review"
                else "VAR factual communication to match referee"
            ),
        },
        {
            "step": 5,
            "code": "issue_under_review",
            "label": reason,
        },
        {
            "step": 6,
            "code": "referee_final_signal",
            "label": f"Referee Final Decision: {final_decision.upper()} ({decision_outcome.replace('_', ' ').title()})",
        },
        {
            "step": 7,
            "code": "resulting_match_consequence",
            "label": f"Restart: {consequence_restart.replace('_', ' ').title()}",
        },
    ]

    return VarReviewDecision(
        review_id=review_id,
        category=cat_norm,
        check_type=check_type,
        formal_review_initiated=True,
        clear_and_obvious_threshold_met=True,
        original_decision=original_decision,
        var_recommendation=var_rec,
        referee_final_authority=True,
        final_decision=final_decision,
        decision_outcome=decision_outcome,
        reason=reason,
        consequence_restart=consequence_restart,
        timeline_duration_seconds=6.0 if check_type == "on_field_review" else 3.5,
        slow_motion_factor=0.45,
        competition_allows_corner_var=competition_allows_corner_var,
        offending_player_id=offending_player_id,
        offending_player_name=offending_player_name,
        corrected_player_id=corrected_player_id,
        corrected_player_name=corrected_player_name,
        presentation_steps=steps,
    )


def _resolve_decision_outcome(
    category: str,
    *,
    original_decision: str,
    overturned: bool,
    is_second_yellow_review: bool = False,
) -> str:
    orig = original_decision.strip().lower()
    if not overturned:
        return f"{orig}_confirmed"
    if category == "goal_no_goal":
        return "goal_disallowed" if "goal" in orig and "no_goal" not in orig else "goal_awarded"
    if category == "penalty_no_penalty":
        return "penalty_cancelled" if "penalty" in orig and "no_penalty" not in orig else "penalty_awarded"
    if category == "red_card":
        if is_second_yellow_review or "second_yellow" in orig:
            return "second_yellow_rescinded"
        return "red_card_rescinded" if "red" in orig else "red_card_issued"
    if category == "mistaken_identity":
        return "card_transferred_mistaken_identity"
    if category == "corner_kick":
        return "corner_overturned_to_goal_kick"
    return f"{orig}_overturned"


def _consequence_restart_for(category: str, original_decision: str, *, overturned: bool) -> str:
    orig = original_decision.strip().lower()
    if category == "goal_no_goal":
        if overturned:
            return "indirect_free_kick" if "goal" in orig and "no_goal" not in orig else "kick_off"
        return "kick_off" if "goal" in orig and "no_goal" not in orig else "indirect_free_kick"
    if category == "penalty_no_penalty":
        if overturned:
            return "drop_ball" if "penalty" in orig and "no_penalty" not in orig else "penalty_kick"
        return "penalty_kick" if "penalty" in orig and "no_penalty" not in orig else "play_continues"
    if category == "red_card":
        return "direct_free_kick" if overturned and "red" not in orig else "drop_ball"
    if category == "mistaken_identity":
        return "direct_free_kick"
    if category == "corner_kick":
        return "goal_kick" if overturned else "corner_kick"
    return "play_continues"


__all__ = [
    "BROADCAST_CATEGORY_DURATION_WINDOWS",
    "BROADCAST_CATEGORY_MAX_SECONDS",
    "BodyPartLandmark",
    "EXCLUDED_OFFSIDE_BODY_PARTS",
    "MatchBroadcastCategory",
    "OffsideSnapshot",
    "PERMITTED_VAR_CATEGORIES_2026_27",
    "PLAYABLE_OFFSIDE_BODY_PARTS",
    "VarReviewDecision",
    "build_universal_broadcast_session",
    "evaluate_law11_offside",
    "evaluate_var_review_2026_27",
    "resolve_assigned_broadcast_duration",
    "resolve_match_broadcast_category",
]
