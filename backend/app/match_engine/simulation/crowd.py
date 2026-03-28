from __future__ import annotations

from app.match_engine.simulation.models import MatchEvent, MatchEventType, TeamRuntimeState


class CrowdAtmosphereEngine:
    def initialize(
        self,
        *,
        home_context: dict[str, object] | None,
        away_context: dict[str, object] | None,
        stage_pressure: float,
        rivalry_intensity: float,
        is_final: bool,
    ) -> tuple[float, float]:
        home_fan_pressure = float((home_context or {}).get("fan_pressure", 48)) / 100.0
        away_fan_pressure = float((away_context or {}).get("fan_pressure", 48)) / 100.0
        home_brand = float((home_context or {}).get("brand_strength", 50)) / 100.0
        away_brand = float((away_context or {}).get("brand_strength", 50)) / 100.0

        home = self._clamp(
            0.50
            + (stage_pressure * 0.18)
            + (rivalry_intensity * 0.16)
            + (home_fan_pressure * 0.12)
            + (home_brand * 0.06)
            + (0.06 if is_final else 0.0),
            0.35,
            0.92,
        )
        away = self._clamp(
            0.34
            + (stage_pressure * 0.08)
            + (rivalry_intensity * 0.10)
            + (away_fan_pressure * 0.08)
            + (away_brand * 0.05)
            - (home_fan_pressure * 0.05),
            0.18,
            0.72,
        )
        return round(home, 3), round(away, 3)

    def react(self, *, event: MatchEvent, home_state: TeamRuntimeState, away_state: TeamRuntimeState) -> None:
        if event.event_type in {MatchEventType.KICKOFF, MatchEventType.FULLTIME}:
            return
        if event.event_type is MatchEventType.HALFTIME:
            self._decay(home_state)
            self._decay(away_state)
            return

        acting_state = self._acting_state(event=event, home_state=home_state, away_state=away_state)
        other_state = away_state if acting_state is home_state else home_state

        if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_SCORED, MatchEventType.PENALTY_GOAL} and event.metadata.get("review_decision") != "disallowed":
            self._shift(acting_state, other_state, swing=0.18 if acting_state.is_home else 0.15)
            return
        if event.event_type in {MatchEventType.GOALKEEPER_SAVE, MatchEventType.DOUBLE_SAVE, MatchEventType.PENALTY_MISSED}:
            self._shift(acting_state, other_state, swing=0.08 if acting_state.is_home else 0.06)
            return
        if event.event_type in {MatchEventType.RED_CARD, MatchEventType.INJURY}:
            if acting_state is home_state and event.event_type is MatchEventType.RED_CARD:
                self._shift(other_state, acting_state, swing=0.10)
            elif acting_state is away_state and event.event_type is MatchEventType.RED_CARD:
                self._shift(other_state, acting_state, swing=0.10)
            else:
                self._shift(other_state, acting_state, swing=0.06)
            return
        if event.event_type in {
            MatchEventType.DANGEROUS_ATTACK,
            MatchEventType.SHOT,
            MatchEventType.SHOT_ON_TARGET,
            MatchEventType.MISSED_BIG_CHANCE,
            MatchEventType.WOODWORK,
            MatchEventType.POSSESSION_SWING,
            MatchEventType.TACTICAL_SWING,
            MatchEventType.TACTICAL_CHANGE,
        }:
            self._shift(acting_state, other_state, swing=0.035 if acting_state.is_home else 0.02)

    def profile(self, *, home_state: TeamRuntimeState, away_state: TeamRuntimeState, is_final: bool) -> str:
        if is_final and max(home_state.crowd_intensity, away_state.crowd_intensity) >= 0.72:
            return "finals"
        if home_state.crowd_intensity >= 0.78 and away_state.crowd_intensity <= 0.34:
            return "fever_pitch"
        if away_state.crowd_intensity >= 0.58 and home_state.crowd_intensity <= 0.42:
            return "away_silencer"
        if max(home_state.crowd_intensity, away_state.crowd_intensity) >= 0.62:
            return "charged"
        if max(home_state.crowd_intensity, away_state.crowd_intensity) <= 0.42:
            return "muted"
        return "standard"

    def _acting_state(self, *, event: MatchEvent, home_state: TeamRuntimeState, away_state: TeamRuntimeState) -> TeamRuntimeState:
        if event.team_id == away_state.team_id:
            return away_state
        return home_state

    def _shift(self, beneficiary: TeamRuntimeState, affected: TeamRuntimeState, *, swing: float) -> None:
        beneficiary.crowd_intensity = self._clamp(beneficiary.crowd_intensity + swing, 0.15, 0.98)
        affected.crowd_intensity = self._clamp(affected.crowd_intensity - (swing * 0.62), 0.12, 0.92)
        beneficiary.dynamic_morale = self._clamp(beneficiary.dynamic_morale + (swing * (9.0 if beneficiary.is_home else 6.0)), 25.0, 99.0)
        beneficiary.dynamic_motivation = self._clamp(beneficiary.dynamic_motivation + (swing * (7.0 if beneficiary.is_home else 5.0)), 25.0, 99.0)
        affected.dynamic_morale = self._clamp(affected.dynamic_morale - (swing * (5.0 if beneficiary.is_home else 4.0)), 25.0, 99.0)

    def _decay(self, state: TeamRuntimeState) -> None:
        state.crowd_intensity = round(0.5 + ((state.crowd_intensity - 0.5) * 0.94), 3)

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
