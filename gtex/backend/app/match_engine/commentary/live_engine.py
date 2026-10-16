from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Protocol

import requests

from app.core.cache import CacheBackend, JsonCacheNamespace, NullCacheBackend
from app.core.config import Settings
from app.match_engine.commentary.cost_guard import CommentaryBudget, CommentaryCostGuard
from app.match_engine.simulation.models import MatchEventType

_GOAL_EVENTS = {
    MatchEventType.GOAL.value,
    MatchEventType.PENALTY_GOAL.value,
    MatchEventType.PENALTY_SCORED.value,
}
_SHOT_EVENTS = {
    MatchEventType.SHOT.value,
    MatchEventType.SHOT_ON_TARGET.value,
    MatchEventType.MISSED_CHANCE.value,
    MatchEventType.MISSED_BIG_CHANCE.value,
    MatchEventType.WOODWORK.value,
    MatchEventType.DOUBLE_SAVE.value,
    MatchEventType.GOALKEEPER_SAVE.value,
    MatchEventType.PENALTY_MISSED.value,
}
_CARD_EVENTS = {MatchEventType.YELLOW_CARD.value, MatchEventType.RED_CARD.value}


@dataclass(slots=True)
class GeneratedCommentary:
    line: str
    tier: str
    provider: str
    tone: str
    commentator: str
    intensity: float
    audio_channel: str
    context: dict[str, Any]


@dataclass(slots=True)
class RollingMatchMemory:
    score: str = "0-0"
    previous_home_score: int = 0
    previous_away_score: int = 0
    momentum: str = "balanced"
    lead_changes: int = 0
    last_events: list[dict[str, Any]] = field(default_factory=list)
    player_impact: dict[str, float] = field(default_factory=dict)
    player_goals: dict[str, int] = field(default_factory=dict)
    player_form: dict[str, str] = field(default_factory=dict)

    def as_payload(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "previous_home_score": self.previous_home_score,
            "previous_away_score": self.previous_away_score,
            "momentum": self.momentum,
            "lead_changes": self.lead_changes,
            "last_events": [dict(item) for item in self.last_events],
            "player_impact": dict(self.player_impact),
            "player_goals": dict(self.player_goals),
            "player_form": dict(self.player_form),
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "RollingMatchMemory":
        raw = payload or {}
        return cls(
            score=str(raw.get("score") or "0-0"),
            previous_home_score=int(raw.get("previous_home_score") or 0),
            previous_away_score=int(raw.get("previous_away_score") or 0),
            momentum=str(raw.get("momentum") or "balanced"),
            lead_changes=int(raw.get("lead_changes") or 0),
            last_events=[
                dict(item)
                for item in raw.get("last_events", [])
                if isinstance(item, dict)
            ][-8:],
            player_impact={
                str(key): float(value)
                for key, value in dict(raw.get("player_impact") or {}).items()
            },
            player_goals={
                str(key): int(value)
                for key, value in dict(raw.get("player_goals") or {}).items()
            },
            player_form={
                str(key): str(value)
                for key, value in dict(raw.get("player_form") or {}).items()
            },
        )


class CommentaryLLMClient(Protocol):
    provider_name: str

    def generate(self, prompt: dict[str, Any]) -> str | None:
        ...


@dataclass(slots=True)
class NullCommentaryLLMClient:
    provider_name: str = "local-template"

    def generate(self, prompt: dict[str, Any]) -> str | None:
        return None


@dataclass(slots=True)
class RemoteCommentaryLLMClient:
    enabled: bool = False
    endpoint_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    timeout_seconds: int = 8
    provider_name: str = "remote-llm"

    @classmethod
    def from_settings(cls, settings: Settings | None) -> "RemoteCommentaryLLMClient":
        if settings is None:
            return cls()
        return cls(
            enabled=bool(settings.live_commentary_llm_enabled),
            endpoint_url=settings.live_commentary_llm_endpoint_url,
            model=settings.live_commentary_llm_model,
            api_key=settings.live_commentary_llm_api_key,
            timeout_seconds=settings.live_commentary_llm_timeout_seconds,
        )

    def generate(self, prompt: dict[str, Any]) -> str | None:
        if not self.enabled or not self.endpoint_url or not self.model:
            return None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are a world-class football commentator. "
                                "Style: energetic, emotional, concise, no fluff. "
                                "Return one or two short sentences only."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(prompt, ensure_ascii=True),
                        }
                    ],
                },
            ],
            "temperature": 0.9,
            "max_output_tokens": 120,
        }
        try:
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                json=body,
                timeout=max(self.timeout_seconds, 1),
            )
            response.raise_for_status()
        except Exception:
            return None
        return _normalize_line(_extract_llm_text(response.json()))


@dataclass(slots=True)
class CommentaryMemoryStore:
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    ttl_seconds: int = 21_600
    _local: dict[str, RollingMatchMemory] = field(default_factory=dict)
    _cache: JsonCacheNamespace = field(init=False)

    def __post_init__(self) -> None:
        self._cache = JsonCacheNamespace(self.cache_backend)

    def configure(self, *, cache_backend: CacheBackend | None = None, ttl_seconds: int | None = None) -> None:
        if cache_backend is not None:
            self.cache_backend = cache_backend
        if ttl_seconds is not None:
            self.ttl_seconds = ttl_seconds
        self._cache = JsonCacheNamespace(self.cache_backend)

    def load(self, match_id: str) -> RollingMatchMemory:
        cached = self._local.get(match_id)
        if cached is not None:
            return RollingMatchMemory.from_payload(cached.as_payload())
        envelope = self._cache.get_json(self._key(match_id))
        if envelope is None:
            return RollingMatchMemory()
        payload = envelope.get("payload") if isinstance(envelope, dict) else None
        memory = RollingMatchMemory.from_payload(payload if isinstance(payload, dict) else None)
        self._local[match_id] = memory
        return RollingMatchMemory.from_payload(memory.as_payload())

    def save(self, match_id: str, memory: RollingMatchMemory) -> None:
        stored = RollingMatchMemory.from_payload(memory.as_payload())
        self._local[match_id] = stored
        self._cache.set_json(self._key(match_id), stored.as_payload(), ttl_seconds=max(self.ttl_seconds, 60))

    def reset(self, match_id: str) -> None:
        self._local.pop(match_id, None)
        self.cache_backend.delete_many([self._key(match_id)])

    @staticmethod
    def _key(match_id: str) -> str:
        return f"live-commentary:memory:{match_id}"


@dataclass(slots=True)
class LiveCommentaryEngine:
    settings: Settings | None = None
    memory_store: CommentaryMemoryStore = field(default_factory=CommentaryMemoryStore)
    cost_guard: CommentaryCostGuard = field(default_factory=CommentaryCostGuard)
    llm_client: CommentaryLLMClient = field(default_factory=NullCommentaryLLMClient)

    def __post_init__(self) -> None:
        if self.settings is not None:
            self.configure(settings=self.settings)

    def configure(
        self,
        *,
        settings: Settings | None = None,
        cache_backend: CacheBackend | None = None,
    ) -> None:
        if settings is not None:
            self.settings = settings
            self.llm_client = RemoteCommentaryLLMClient.from_settings(settings)
            self.memory_store.configure(
                ttl_seconds=max(settings.live_commentary_memory_ttl_seconds, 60),
            )
            self.cost_guard.configure(
                max_calls_per_match=max(settings.live_commentary_max_llm_calls_per_match, 0),
                ttl_seconds=max(settings.live_commentary_memory_ttl_seconds, 60),
            )
        if cache_backend is not None:
            self.memory_store.configure(cache_backend=cache_backend)
            self.cost_guard.configure(cache_backend=cache_backend)

    def reset_match(self, match_id: str) -> None:
        self.memory_store.reset(match_id)
        self.cost_guard.reset(match_id)

    def generate(
        self,
        *,
        match_id: str,
        event,
        home_team_id: str,
        away_team_id: str,
        home_team_name: str,
        away_team_name: str,
    ) -> GeneratedCommentary:
        memory = self.memory_store.load(match_id)
        context = self._build_context(
            event=event,
            memory=memory,
            match_id=match_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_name=home_team_name,
            away_team_name=away_team_name,
        )
        tier = self._select_tier(context)
        line, provider, llm_budget = self._render_line(
            match_id=match_id,
            context=context,
            tier=tier,
            fallback=str(getattr(event, "commentary", "") or ""),
        )
        context["commentary_tier"] = tier
        context["generated_by"] = provider
        context["llm_budget"] = llm_budget
        intensity = self._intensity_for(context, tier=tier)
        tone = (
            "high_intensity"
            if context["is_final"]
            else "dramatic"
            if context["late_deadlock"]
            else "hype"
            if tier == "llm" or context["is_major_moment"]
            else "tactical"
        )
        commentator = "lead" if tier == "llm" or context["event_family"] in {"goal", "card"} else "analyst"
        audio_channel = "headline" if tone in {"high_intensity", "dramatic", "hype"} else "match_bed"

        self._update_memory(memory, context)
        self.memory_store.save(match_id, memory)
        return GeneratedCommentary(
            line=line,
            tier=tier,
            provider=provider,
            tone=tone,
            commentator=commentator,
            intensity=intensity,
            audio_channel=audio_channel,
            context=context,
        )

    def _build_context(
        self,
        *,
        event,
        memory: RollingMatchMemory,
        match_id: str,
        home_team_id: str,
        away_team_id: str,
        home_team_name: str,
        away_team_name: str,
    ) -> dict[str, Any]:
        event_type = _event_value(getattr(event, "event_type", None))
        team_id = getattr(event, "team_id", None)
        team_name = getattr(event, "team_name", None)
        team_side = None
        if team_id == home_team_id:
            team_side = "home"
        elif team_id == away_team_id:
            team_side = "away"
        opponent_team_name = away_team_name if team_side == "home" else home_team_name if team_side == "away" else None
        home_score = int(getattr(event, "home_score", 0) or 0)
        away_score = int(getattr(event, "away_score", 0) or 0)
        score_delta = home_score - away_score
        score_diff = abs(score_delta)
        previous_delta = memory.previous_home_score - memory.previous_away_score
        metadata = _metadata(event)
        xg = _float_value(metadata.get("xg"), default=_float_value(metadata.get("chance_quality"), default=0.0))
        minute = int(getattr(event, "minute", 0) or 0)
        player_name = (
            getattr(getattr(event, "primary_player", None), "player_name", None)
            or metadata.get("player_name")
        )
        secondary_player_name = (
            getattr(getattr(event, "secondary_player", None), "player_name", None)
            or metadata.get("secondary_player_name")
        )
        assisted = bool(metadata.get("assisted") and secondary_player_name)
        event_family = _event_family(event_type)
        equalizer = event_family == "goal" and previous_delta != 0 and score_delta == 0
        go_ahead = event_family == "goal" and (
            (previous_delta <= 0 and score_delta > 0)
            or (previous_delta >= 0 and score_delta < 0)
        )
        comeback = event_family == "goal" and (
            (team_side == "home" and previous_delta < 0 and score_delta >= 0)
            or (team_side == "away" and previous_delta > 0 and score_delta <= 0)
        )
        player_form = str(memory.player_form.get(self._player_key(player_name)) or "steady")
        last_events = [dict(item) for item in memory.last_events[-3:]]
        return {
            "match_id": match_id,
            "minute": minute,
            "clock": str(getattr(event, "clock_label", f"{minute}'")),
            "event_type": event_type,
            "event_family": event_family,
            "team_id": team_id,
            "team_name": team_name,
            "team_side": team_side,
            "opponent_team_name": opponent_team_name,
            "player_name": player_name,
            "secondary_player_name": secondary_player_name,
            "assisted": assisted,
            "home_score": home_score,
            "away_score": away_score,
            "scoreline": f"{home_score}-{away_score}",
            "previous_scoreline": f"{memory.previous_home_score}-{memory.previous_away_score}",
            "score_delta": score_delta,
            "score_diff": score_diff,
            "xg": round(xg, 2),
            "shot_distance": round(_float_value(metadata.get("shot_distance"), default=0.0), 2),
            "shot_angle": round(_float_value(metadata.get("shot_angle"), default=0.0), 2),
            "shot_body_part": _string_or_none(metadata.get("shot_body_part")),
            "chance_family": _string_or_none(metadata.get("chance_family")),
            "build_up_pattern": _string_or_none(metadata.get("build_up_pattern")),
            "build_up_profile": _string_or_none(metadata.get("build_up_profile")),
            "possession_route": _string_or_none(metadata.get("possession_route")),
            "pressure_level": _string_or_none(metadata.get("pressure_level")),
            "importance": int(metadata.get("importance") or 1),
            "reviewable": bool(metadata.get("reviewable")),
            "review_decision": _string_or_none(metadata.get("review_decision")),
            "review_reason": _string_or_none(metadata.get("review_reason")),
            "momentum": memory.momentum,
            "player_form": player_form,
            "goals_in_match": int(memory.player_goals.get(self._player_key(player_name), 0)),
            "equalizer": equalizer,
            "go_ahead": go_ahead,
            "comeback": comeback,
            "is_final": bool(metadata.get("is_final")),
            "competition_name": _string_or_none(metadata.get("competition_name")),
            "stage_name": _string_or_none(metadata.get("stage_name")),
            "player_story_hook": _string_or_none(metadata.get("player_story_hook")),
            "late_drama": minute >= 85 and abs(score_delta) <= 1,
            "late_deadlock": minute >= 85 and score_diff == 0,
            "is_major_moment": event_family in {"goal", "card"} or bool(
                minute >= 85 and (xg >= 0.35 or go_ahead or equalizer or comeback)
            ),
            "last_events": last_events,
        }

    def _select_tier(self, context: dict[str, Any]) -> str:
        if context["event_family"] == "goal":
            return "llm"
        if context["event_type"] == MatchEventType.RED_CARD.value:
            return "llm"
        if int(context["minute"]) > 85:
            return "llm"
        if context["late_drama"] and (context["xg"] >= 0.35 or context["event_family"] in {"shot", "card"}):
            return "llm"
        if context["reviewable"] and context["event_family"] in {"goal", "foul"}:
            return "llm"
        if context["event_family"] == "shot" and (
            context["xg"] >= 0.40 or int(context["importance"]) >= 4
        ):
            return "llm"
        if context["event_family"] in {"shot", "card", "substitution"}:
            return "template"
        return "rule"

    def _render_line(
        self,
        *,
        match_id: str,
        context: dict[str, Any],
        tier: str,
        fallback: str,
    ) -> tuple[str, str, dict[str, Any]]:
        if tier == "rule":
            line = self._render_rule_line(context)
            return (
                _normalize_line(line or fallback),
                "local-template",
                self._budget_payload(
                    self.cost_guard.snapshot(match_id),
                    enabled=self._llm_enabled(),
                    skip_reason="tier_not_selected",
                ),
            )
        if tier == "template":
            return (
                _normalize_line(self._render_template_line(context) or fallback),
                "local-template",
                self._budget_payload(
                    self.cost_guard.snapshot(match_id),
                    enabled=self._llm_enabled(),
                    skip_reason="tier_not_selected",
                ),
            )
        if not self._llm_enabled():
            budget = self.cost_guard.snapshot(match_id)
            return (
                _normalize_line(self._render_dramatic_line(context) or fallback),
                "local-dramatic",
                self._budget_payload(budget, enabled=False, skip_reason="llm_unavailable"),
            )
        budget = self.cost_guard.reserve_call(match_id)
        if not budget.call_allowed:
            return (
                _normalize_line(self._render_dramatic_line(context) or fallback),
                "local-dramatic",
                self._budget_payload(
                    budget,
                    enabled=True,
                    skip_reason="budget_exhausted",
                ),
            )
        prompt = self._build_prompt(context)
        llm_line = self.llm_client.generate(prompt)
        if llm_line:
            return (
                llm_line,
                getattr(self.llm_client, "provider_name", "remote-llm"),
                self._budget_payload(
                    budget,
                    enabled=True,
                    reserved=True,
                    attempted=True,
                ),
            )
        return (
            _normalize_line(self._render_dramatic_line(context) or fallback),
            "local-dramatic",
            self._budget_payload(
                budget,
                enabled=True,
                reserved=True,
                attempted=True,
                skip_reason="llm_no_output",
            ),
        )

    def _budget_payload(
        self,
        budget: CommentaryBudget,
        *,
        enabled: bool,
        reserved: bool = False,
        attempted: bool = False,
        skip_reason: str | None = None,
    ) -> dict[str, Any]:
        payload = budget.as_payload()
        payload["enabled"] = enabled
        payload["reserved"] = reserved
        payload["attempted"] = attempted
        payload["skip_reason"] = skip_reason
        return payload

    def _llm_enabled(self) -> bool:
        if isinstance(self.llm_client, NullCommentaryLLMClient):
            return False
        if isinstance(self.llm_client, RemoteCommentaryLLMClient):
            return bool(self.llm_client.enabled and self.llm_client.endpoint_url and self.llm_client.model)
        return True

    def _render_rule_line(self, context: dict[str, Any]) -> str:
        player = context.get("player_name") or context.get("team_name") or "The move"
        team = context.get("team_name") or "the side"
        if context["event_family"] == "foul":
            return f"{player} concedes the foul for {team}."
        if context["event_type"] == MatchEventType.YELLOW_CARD.value:
            return f"{player} goes into the book for {team}."
        if context["event_family"] == "substitution":
            outgoing = context.get("secondary_player_name")
            if outgoing:
                return f"{team} make a change as {player} replaces {outgoing}."
            return f"{team} make a substitution."
        if context["event_family"] == "shot":
            distance = int(round(float(context.get("shot_distance") or 0)))
            if distance > 0:
                return f"{player} tries from {distance} yards for {team}."
            return f"{player} has a go for {team}."
        return f"{team} keep the phase moving."

    def _render_template_line(self, context: dict[str, Any]) -> str:
        player = context.get("player_name") or context.get("team_name") or "The player"
        team = context.get("team_name") or "the side"
        options: list[str]
        if context["event_family"] == "shot":
            distance = int(round(float(context.get("shot_distance") or 0)))
            if context["event_type"] == MatchEventType.MISSED_BIG_CHANCE.value:
                options = [
                    f"{player} should score for {team}, but the chance goes begging.",
                    f"{team} carve it open and {player} cannot finish the move.",
                    f"A huge opening for {team}, and {player} leaves it behind.",
                ]
            elif context["event_type"] in {MatchEventType.WOODWORK.value, MatchEventType.DOUBLE_SAVE.value, MatchEventType.GOALKEEPER_SAVE.value}:
                options = [
                    f"{player} looks certain to score, but {team} are denied at full stretch.",
                    f"{team} are inches away as {player} comes close to a huge moment.",
                    f"{player} nearly lands it for {team}, and the stadium reacts all at once.",
                ]
            elif distance > 0:
                options = [
                    f"{player} lets fly from {distance} yards and {team} ask a real question.",
                    f"{team} work the lane and {player} takes it on from {distance} yards.",
                    f"{player} sees the picture early and drives one for {team} from {distance} yards.",
                ]
            else:
                options = [
                    f"{player} pulls the trigger for {team}.",
                    f"{team} fashion the look and {player} goes for it.",
                    f"{player} snaps at the opening for {team}.",
                ]
        elif context["event_type"] == MatchEventType.RED_CARD.value:
            options = [
                f"{player} is sent off and {team} have a major problem now.",
                f"Red card for {player}. {team} will have to survive with ten.",
                f"{team} lose {player}, and the whole shape of the match changes.",
            ]
        elif context["event_type"] == MatchEventType.YELLOW_CARD.value:
            options = [
                f"{player} is booked and {team} will have to manage the risk.",
                f"The referee reaches for the yellow, and {player} has to be careful now.",
                f"{team} pick up a caution through {player}.",
            ]
        else:
            incoming = context.get("player_name") or "Fresh legs"
            outgoing = context.get("secondary_player_name")
            if outgoing:
                options = [
                    f"{team} change the rhythm with {incoming} on for {outgoing}.",
                    f"{team} go to the bench as {incoming} replaces {outgoing}.",
                    f"{team} reset the phase with {incoming} entering for {outgoing}.",
                ]
            else:
                options = [
                    f"{team} make a switch from the bench.",
                    f"{team} turn to the substitutes.",
                    f"{team} look for a fresh angle with a change.",
                ]
        return self._pick(context, options, salt="template")

    def _render_dramatic_line(self, context: dict[str, Any]) -> str:
        player = context.get("player_name") or context.get("team_name") or "The player"
        team = context.get("team_name") or "the side"
        body_part = _display_body_part(context.get("shot_body_part"))
        distance = int(round(float(context.get("shot_distance") or 0)))
        player_form = context.get("player_form") or "steady"
        if context["event_family"] == "goal":
            stage = context.get("stage_name") or context.get("competition_name")
            if context["reviewable"] and context["review_decision"] == "disallowed":
                return f"Chaos for {team}, but the goal is wiped away after the review."
            if context["is_final"] and stage:
                return f"{player} lands a final-stage blow for {team}! {stage} pressure turns into release."
            if context["equalizer"]:
                return f"{player} drags {team} level! The pressure had been building and they finally break through."
            if context["go_ahead"] and context["late_drama"]:
                return f"{player} may have won it for {team}! This place has exploded in the closing minutes."
            if context["comeback"]:
                return f"{player} completes the comeback for {team}! The whole match has turned on its head."
            if distance > 0 and body_part:
                base = f"{player} buries it for {team} with a {body_part.lower()} finish from {distance} yards."
            elif distance > 0:
                base = f"{player} buries it for {team} from {distance} yards."
            else:
                base = f"{player} delivers for {team}!"
            story_hook = context.get("player_story_hook")
            if player_form == "on_fire":
                if story_hook:
                    return f"{base} {story_hook}"
                return f"{base} He has been threatening this all match."
            if context["momentum"] == context.get("team_side"):
                return f"{base} It felt like this moment was coming."
            if story_hook:
                return f"{base} {story_hook}"
            return base
        if context["event_type"] == MatchEventType.RED_CARD.value:
            if context["is_final"]:
                return f"{player} is off in the final stretch! {team} now face a brutal climb."
            return f"{player} is off! {team} are down to ten and the match tilts instantly."
        if context["event_family"] == "shot":
            if context["late_deadlock"]:
                return "The tension is unbearable as the chance opens up. Who breaks the deadlock now?"
            if context["late_drama"]:
                return f"{player} goes for the killer blow for {team}, and everyone inside the ground holds their breath."
            if context["xg"] >= 0.55:
                return f"{player} gets a massive look for {team}, but the finish does not arrive."
            return f"{player} forces the moment for {team}, and the tempo jumps immediately."
        return self._render_template_line(context)

    def _build_prompt(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "match_id": context["match_id"],
            "minute": context["minute"],
            "score": context["scoreline"],
            "event_type": context["event_type"],
            "team": context["team_name"],
            "player": context["player_name"],
            "secondary_player": context["secondary_player_name"],
            "xg": context["xg"],
            "distance": context["shot_distance"],
            "body_part": context["shot_body_part"],
            "chance_family": context["chance_family"],
            "pressure_level": context["pressure_level"],
            "momentum": context["momentum"],
            "player_form": context["player_form"],
            "last_events": context["last_events"],
            "flags": {
                "equalizer": context["equalizer"],
                "go_ahead": context["go_ahead"],
                "comeback": context["comeback"],
                "late_drama": context["late_drama"],
                "reviewable": context["reviewable"],
            },
        }

    def _update_memory(self, memory: RollingMatchMemory, context: dict[str, Any]) -> None:
        player_key = self._player_key(context.get("player_name"))
        if player_key:
            impact_delta = self._impact_delta(context)
            memory.player_impact[player_key] = round(memory.player_impact.get(player_key, 0.0) + impact_delta, 2)
            if context["event_family"] == "goal":
                memory.player_goals[player_key] = int(memory.player_goals.get(player_key, 0)) + 1
            memory.player_form[player_key] = self._form_label(
                goals=int(memory.player_goals.get(player_key, 0)),
                impact=float(memory.player_impact.get(player_key, 0.0)),
                event_family=context["event_family"],
            )

        swing = self._momentum_swing(context)
        memory.last_events.append(
            {
                "minute": int(context["minute"]),
                "event_type": str(context["event_type"]),
                "team_side": context.get("team_side"),
                "team_name": context.get("team_name"),
                "player_name": context.get("player_name"),
                "swing": swing,
            }
        )
        memory.last_events = memory.last_events[-8:]
        recent_swing = sum(float(item.get("swing") or 0.0) for item in memory.last_events[-5:])
        if recent_swing > 1.2:
            memory.momentum = "home"
        elif recent_swing < -1.2:
            memory.momentum = "away"
        else:
            memory.momentum = "balanced"
        if context["go_ahead"]:
            memory.lead_changes += 1
        memory.previous_home_score = int(context["home_score"])
        memory.previous_away_score = int(context["away_score"])
        memory.score = str(context["scoreline"])

    def _impact_delta(self, context: dict[str, Any]) -> float:
        family = str(context["event_family"])
        if family == "goal":
            return 3.4
        if context["event_type"] == MatchEventType.RED_CARD.value:
            return 0.4
        if family == "shot":
            return 1.8 if float(context["xg"]) >= 0.35 else 1.0
        if family == "substitution":
            return 0.5
        return 0.4

    def _form_label(self, *, goals: int, impact: float, event_family: str) -> str:
        if goals >= 2 or impact >= 4.2:
            return "on_fire"
        if event_family == "shot" and impact >= 2.2:
            return "heating_up"
        if impact >= 1.2:
            return "involved"
        return "steady"

    def _momentum_swing(self, context: dict[str, Any]) -> float:
        base = 0.0
        family = str(context["event_family"])
        if family == "goal":
            base = 3.0
        elif context["event_type"] == MatchEventType.RED_CARD.value:
            base = -3.0
        elif family == "shot":
            base = 1.8 if float(context["xg"]) >= 0.35 else 0.9
        elif family == "substitution":
            base = 0.4
        elif family == "foul":
            base = -0.2
        if context.get("team_side") == "away":
            return -base
        if context.get("team_side") == "home":
            return base
        return 0.0

    def _intensity_for(self, context: dict[str, Any], *, tier: str) -> float:
        base = 0.18 + ((int(context.get("importance") or 1) - 1) / 6.0)
        if tier == "llm":
            base += 0.26
        if context["late_drama"]:
            base += 0.12
        if context["event_family"] == "goal":
            base += 0.18
        return max(0.18, min(round(base, 3), 1.0))

    def _pick(self, context: dict[str, Any], options: list[str], *, salt: str) -> str:
        if not options:
            return ""
        seed = f"{context.get('match_id')}|{context.get('minute')}|{context.get('event_type')}|{salt}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(options)
        return options[index]

    @staticmethod
    def _player_key(player_name: object | None) -> str:
        return str(player_name or "").strip().lower()


def _extract_llm_text(payload: dict[str, Any]) -> str | None:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    choices = payload.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text")
                            if isinstance(text, str) and text.strip():
                                return text
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    return None


def _event_value(value: object | None) -> str:
    if hasattr(value, "value"):
        return str(getattr(value, "value"))
    return str(value or "")


def _event_family(event_type: str) -> str:
    if event_type in _GOAL_EVENTS:
        return "goal"
    if event_type in _SHOT_EVENTS:
        return "shot"
    if event_type in _CARD_EVENTS:
        return "card"
    if event_type == MatchEventType.SUBSTITUTION.value:
        return "substitution"
    if event_type in {MatchEventType.FOUL.value, MatchEventType.TACTICAL_FOUL.value}:
        return "foul"
    return "generic"


def _float_value(value: object | None, *, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _string_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


def _display_body_part(value: object | None) -> str | None:
    body_part = _string_or_none(value)
    if body_part is None:
        return None
    return body_part.replace("_", " ").title()


def _metadata(event) -> dict[str, Any]:
    metadata = getattr(event, "metadata", None)
    return dict(metadata) if isinstance(metadata, dict) else {}


def _normalize_line(value: object | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).replace("\n", " ").split())
    return text[:280] if text else None


__all__ = [
    "GeneratedCommentary",
    "LiveCommentaryEngine",
]
