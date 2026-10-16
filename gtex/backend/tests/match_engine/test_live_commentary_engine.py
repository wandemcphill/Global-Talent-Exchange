from __future__ import annotations

from types import SimpleNamespace

from app.match_engine.commentary.live_engine import LiveCommentaryEngine
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchEventType
from backend.tests.match_engine.helpers import build_request


def _find_payload(*, seeds=range(1, 160)):
    service = MatchSimulationService()
    for seed in seeds:
        payload = service.build_replay_payload(build_request(seed=seed))
        if any(
            event.event_type in {
                MatchEventType.GOAL,
                MatchEventType.PENALTY_GOAL,
                MatchEventType.PENALTY_SCORED,
            }
            for event in payload.timeline.events
        ):
            return payload
    raise AssertionError("No replay payload with a goal event was generated in the seed range")


def test_live_commentary_engine_tracks_context_and_uses_high_tier_for_goals() -> None:
    payload = _find_payload()
    engine = LiveCommentaryEngine()
    generated_goal = None
    generated_shot = None

    for event in payload.timeline.events:
        generated = engine.generate(
            match_id=payload.match_id,
            event=event,
            home_team_id=payload.summary.home_stats.team_id,
            away_team_id=payload.summary.away_stats.team_id,
            home_team_name=payload.summary.home_stats.team_name,
            away_team_name=payload.summary.away_stats.team_name,
        )
        if generated_shot is None and event.event_type in {
            MatchEventType.SHOT,
            MatchEventType.SHOT_ON_TARGET,
            MatchEventType.MISSED_BIG_CHANCE,
        }:
            generated_shot = generated
        if event.event_type in {
            MatchEventType.GOAL,
            MatchEventType.PENALTY_GOAL,
            MatchEventType.PENALTY_SCORED,
        }:
            generated_goal = generated
            break

    assert generated_shot is not None
    assert generated_shot.tier in {"template", "llm"}
    assert generated_shot.context["scoreline"]
    assert isinstance(generated_shot.context["last_events"], list)

    assert generated_goal is not None
    assert generated_goal.tier == "llm"
    assert generated_goal.provider in {"local-dramatic", "remote-llm"}
    assert generated_goal.context["event_family"] == "goal"
    assert generated_goal.context["commentary_tier"] == "llm"
    assert generated_goal.context["generated_by"] == generated_goal.provider
    assert generated_goal.context["scoreline"] == (
        f"{generated_goal.context['home_score']}-{generated_goal.context['away_score']}"
    )
    assert generated_goal.intensity >= 0.4
    assert generated_goal.line
    assert isinstance(generated_goal.context["llm_budget"], dict)


class _StubLLMClient:
    provider_name = "test-llm"

    def __init__(self) -> None:
        self.prompts: list[dict[str, object]] = []

    def generate(self, prompt: dict[str, object]) -> str | None:
        self.prompts.append(prompt)
        return f"LLM line {len(self.prompts)}"


def _stub_event(
    *,
    minute: int,
    event_type: MatchEventType,
    team_id: str,
    team_name: str,
    player_name: str,
    home_score: int,
    away_score: int,
    metadata: dict[str, object] | None = None,
):
    return SimpleNamespace(
        event_type=event_type,
        minute=minute,
        team_id=team_id,
        team_name=team_name,
        primary_player=SimpleNamespace(player_name=player_name),
        secondary_player=None,
        home_score=home_score,
        away_score=away_score,
        metadata=dict(metadata or {}),
        commentary="Fallback commentary line.",
        clock_label=f"{minute}'",
    )


def test_live_commentary_engine_enforces_per_match_llm_budget() -> None:
    client = _StubLLMClient()
    engine = LiveCommentaryEngine(llm_client=client)
    engine.cost_guard.configure(max_calls_per_match=2)

    generated = [
        engine.generate(
            match_id="match-budget",
            event=event,
            home_team_id="home",
            away_team_id="away",
            home_team_name="Home FC",
            away_team_name="Away FC",
        )
        for event in [
            _stub_event(
                minute=10,
                event_type=MatchEventType.GOAL,
                team_id="home",
                team_name="Home FC",
                player_name="Ada Forward",
                home_score=1,
                away_score=0,
                metadata={"xg": 0.62, "importance": 5},
            ),
            _stub_event(
                minute=20,
                event_type=MatchEventType.GOAL,
                team_id="away",
                team_name="Away FC",
                player_name="Binta Striker",
                home_score=1,
                away_score=1,
                metadata={"xg": 0.48, "importance": 5},
            ),
            _stub_event(
                minute=88,
                event_type=MatchEventType.GOAL,
                team_id="home",
                team_name="Home FC",
                player_name="Chioma Finisher",
                home_score=2,
                away_score=1,
                metadata={"xg": 0.51, "importance": 5},
            ),
        ]
    ]

    assert len(client.prompts) == 2
    assert generated[0].provider == "test-llm"
    assert generated[1].provider == "test-llm"
    assert generated[2].tier == "llm"
    assert generated[2].provider == "local-dramatic"
    assert generated[2].line
    assert generated[2].context["llm_budget"]["enabled"] is True
    assert generated[2].context["llm_budget"]["call_allowed"] is False
    assert generated[2].context["llm_budget"]["exhausted"] is True
    assert generated[2].context["llm_budget"]["used_calls"] == 2
    assert generated[2].context["llm_budget"]["remaining_calls"] == 0
    assert generated[2].context["llm_budget"]["skip_reason"] == "budget_exhausted"

    engine.reset_match("match-budget")
    after_reset = engine.generate(
        match_id="match-budget",
        event=_stub_event(
            minute=89,
            event_type=MatchEventType.GOAL,
            team_id="home",
            team_name="Home FC",
            player_name="Dara Winner",
            home_score=3,
            away_score=1,
            metadata={"xg": 0.73, "importance": 5},
        ),
        home_team_id="home",
        away_team_id="away",
        home_team_name="Home FC",
        away_team_name="Away FC",
    )

    assert len(client.prompts) == 3
    assert after_reset.provider == "test-llm"
