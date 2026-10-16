from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.calendar_engine import GlobalEvent
from app.models.competition_match import CompetitionMatch
from app.models.pundit_profile import PunditProfile
from app.pundits.analysis import analyze_match
from app.pundits.debate import DebateGenerator
from app.pundits.formatter import build_headline
from app.pundits.hot_takes import generate_hot_takes
from app.pundits.personas import DEFAULT_PUNDITS
from app.pundits.schemas import (
    PunditDebateLineView,
    PunditDebateResponse,
    PunditInteractionView,
    PunditMatchAnalysisView,
    PunditPersonaView,
    PunditPlayerRatingView,
    PunditPredictionView,
    PunditShowMatchContextView,
    PunditShowResponse,
    PunditShowSegmentView,
    PunditShowStatsView,
)
from app.viral.service import ViralFeedError, load_replay_payload


def _table_exists(session: Session, table_name: str) -> bool:
    try:
        return bool(inspect(session.connection()).has_table(table_name))
    except Exception:
        return False


def _enum_value(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(getattr(value, "value", value))


def _normalize_probabilities(home: float, draw: float, away: float) -> tuple[int, int, int]:
    total = max(home + draw + away, 0.0001)
    raw = [int(round((home / total) * 100)), int(round((draw / total) * 100)), int(round((away / total) * 100))]
    raw[0] += 100 - sum(raw)
    return max(0, raw[0]), max(0, raw[1]), max(0, raw[2])


@dataclass(slots=True)
class _ResolvedMatchContext:
    match_id: str
    home_team_name: str
    away_team_name: str
    status: str
    stage: str
    competition_type: str
    is_final: bool
    kickoff_at: datetime | None
    replay_payload: Any | None
    preview_request: Any | None
    metadata_json: dict[str, Any]
    home_user_id: str | None = None
    away_user_id: str | None = None


@dataclass(slots=True)
class PunditService:
    session: Session
    settings: Settings | None = None
    debate_generator: DebateGenerator | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        if self.debate_generator is None:
            self.debate_generator = DebateGenerator.from_settings(self.settings)

    def build_pre_match_show(self, match_id: str) -> PunditShowResponse:
        context = self._resolve_context(match_id)
        profiles = self._load_profiles()
        stats = self._build_stats(context)
        prediction = self._build_prediction(context, stats)
        memory = self._build_memory(context)
        return PunditShowResponse(
            match_id=context.match_id,
            show_type="pre_match",
            headline=f"{context.home_team_name} vs {context.away_team_name}: the desk sets the tone",
            match_context=self._build_context_view(context),
            pundit_profiles=profiles,
            stats=stats,
            global_memory=memory,
            segments=self._pre_segments(context, profiles, prediction, memory),
            interactions=self._pre_interactions(context, profiles, prediction, memory),
            player_ratings=self._pre_watchlist(context),
            controversial_decisions=self._pre_watchpoints(context),
            prediction=prediction,
            pipeline=self._pipeline(),
            generated_at=datetime.now(UTC),
        )

    def build_post_match_show(self, match_id: str) -> PunditShowResponse:
        context = self._resolve_context(match_id)
        if context.replay_payload is None:
            raise ViralFeedError(f"Replay payload for {match_id} was not found.")
        profiles = self._load_profiles()
        memory = self._build_memory(context)
        analysis = analyze_match(context.replay_payload)
        return PunditShowResponse(
            match_id=context.match_id,
            show_type="post_match",
            headline=build_headline(analysis),
            match_context=self._build_context_view(context),
            pundit_profiles=profiles,
            stats=self._build_stats(context),
            global_memory=memory,
            segments=self._post_segments(context, profiles, memory),
            interactions=self._post_interactions(context, profiles, analysis),
            player_ratings=self._post_ratings(context),
            controversial_decisions=self._post_controversies(context),
            prediction=None,
            pipeline=self._pipeline(),
            generated_at=datetime.now(UTC),
        )

    def build_debate_show(self, *, match_id: str | None = None, topic: str | None = None) -> PunditShowResponse:
        if match_id:
            context = self._resolve_context(match_id)
            base = self.build_post_match_show(match_id) if context.replay_payload is not None else self.build_pre_match_show(match_id)
            return base.model_copy(update={"show_type": "debate", "headline": f"Debate Desk: {context.home_team_name} vs {context.away_team_name}"})
        profiles = self._load_profiles()
        interactions = [
            PunditInteractionView(speaker=profiles[1].name, interaction_type="opening_salvo", target_speaker=profiles[0].name, line=f"{topic or 'The biggest GTEX finals are shaped by hype as much as structure.'}", tone="aggressive"),
            PunditInteractionView(speaker=profiles[0].name, interaction_type="counter", target_speaker=profiles[1].name, line="The structure still decides who survives the pressure.", tone="measured"),
            PunditInteractionView(speaker=profiles[3].name, interaction_type="interruption", target_speaker=profiles[0].name, line="Only if the dressing room believes the plan after the first punch.", tone="sharp"),
            PunditInteractionView(speaker=profiles[2].name, interaction_type="agreement", target_speaker=profiles[3].name, line="That is why the calendar matters. Occasion changes the emotional weight of every decision.", tone="narrative"),
        ]
        context = _ResolvedMatchContext("studio-topic", "GTEX Studio", "Open Panel", "scheduled", "debate", "studio", False, None, None, None, {})
        return PunditShowResponse(
            match_id=context.match_id,
            show_type="debate",
            headline="GTEX Debate Night",
            match_context=self._build_context_view(context),
            pundit_profiles=profiles,
            stats=PunditShowStatsView(),
            global_memory=["Studio topic mode is active for open-ended football debate."],
            segments=[PunditShowSegmentView(order=1, segment_type="debate", title="Debate Night", speaker=profiles[1].name, summary="The panel pushes conflicting reads on the same question.", talking_points=[item.line for item in interactions])],
            interactions=interactions,
            player_ratings=[],
            controversial_decisions=[],
            prediction=None,
            pipeline=self._pipeline(),
            generated_at=datetime.now(UTC),
        )

    def build_match_debate(self, match_key: str, *, format: str = "chat") -> PunditDebateResponse:
        context = self._resolve_context(match_key)
        analysis = analyze_match(context.replay_payload) if context.replay_payload is not None else self._preview_analysis(context)
        hot_takes = generate_hot_takes(analysis)
        lines = self.debate_generator.generate(analysis=analysis, hot_takes=hot_takes)
        return PunditDebateResponse(
            match_id=context.match_id,
            headline=build_headline(analysis),
            format=format,
            analysis=PunditMatchAnalysisView(**analysis),
            personas=self._load_profiles(),
            hot_takes=hot_takes,
            lines=[PunditDebateLineView(speaker=line.speaker, style=line.style, stance=line.stance, line=line.line, emphasis=line.emphasis) for line in lines],
            generated_at=datetime.now(UTC),
        )

    def _resolve_context(self, match_id: str) -> _ResolvedMatchContext:
        match = self.session.get(CompetitionMatch, match_id)
        if match is not None:
            metadata = dict(match.metadata_json or {})
            preview = self._parse_preview(metadata.get("preview_request"))
            replay = self._parse_replay(metadata.get("replay_payload"))
            return _ResolvedMatchContext(
                match_id=match.id,
                home_team_name=self._preview_team_name(preview, "home") or self._replay_team_name(replay, "home") or match.home_club_id,
                away_team_name=self._preview_team_name(preview, "away") or self._replay_team_name(replay, "away") or match.away_club_id,
                status=str(match.status or "scheduled"),
                stage=str(match.stage or self._preview_stage(preview) or self._replay_stage(replay)),
                competition_type=str(self._preview_competition_type(preview) or self._replay_competition_type(replay) or "league"),
                is_final=bool(self._preview_is_final(preview) or self._replay_is_final(replay)),
                kickoff_at=match.scheduled_at or self._preview_kickoff(preview),
                replay_payload=replay,
                preview_request=preview,
                metadata_json=metadata,
            )
        if _table_exists(self.session, "competitive_matches"):
            from app.models.competitive_integrity import Match as CompetitiveMatch

            match = self.session.get(CompetitiveMatch, match_id)
            if match is not None:
                preview = self._competitive_preview(match)
                replay = self._parse_replay(match.result_payload)
                home = dict(match.locked_lineup_home or {})
                away = dict(match.locked_lineup_away or {})
                return _ResolvedMatchContext(
                    match_id=match.id,
                    home_team_name=str(home.get("team_name") or self._replay_team_name(replay, "home") or "Home"),
                    away_team_name=str(away.get("team_name") or self._replay_team_name(replay, "away") or "Away"),
                    status=_enum_value(match.status, "scheduled"),
                    stage=str(self._preview_stage(preview) or "competitive"),
                    competition_type=_enum_value(match.competition_type, "competitive"),
                    is_final=bool(self._preview_is_final(preview)),
                    kickoff_at=match.kickoff_at,
                    replay_payload=replay,
                    preview_request=preview,
                    metadata_json={},
                    home_user_id=match.home_user_id,
                    away_user_id=match.away_user_id,
                )
        replay = load_replay_payload(self.session, match_id)
        return _ResolvedMatchContext(
            match_id=match_id,
            home_team_name=self._replay_team_name(replay, "home") or "Home",
            away_team_name=self._replay_team_name(replay, "away") or "Away",
            status=_enum_value(replay.status, "completed"),
            stage=self._replay_stage(replay),
            competition_type=self._replay_competition_type(replay),
            is_final=self._replay_is_final(replay),
            kickoff_at=None,
            replay_payload=replay,
            preview_request=None,
            metadata_json={},
        )

    def _load_profiles(self) -> list[PunditPersonaView]:
        if not _table_exists(self.session, PunditProfile.__tablename__):
            return [self._profile_view(payload) for payload in DEFAULT_PUNDITS]
        records = list(self.session.scalars(select(PunditProfile).where(PunditProfile.is_active.is_(True)).order_by(PunditProfile.name.asc())).all())
        if not records:
            for payload in DEFAULT_PUNDITS:
                self.session.add(
                    PunditProfile(
                        name=str(payload["name"]),
                        style=str(payload["style"]),
                        bias=dict(payload.get("bias") or {}),
                        confidence_level=float(payload.get("confidence_level") or 0.65),
                        debate_style=str(payload.get("debate_style") or "measured"),
                        signature_line=str(payload.get("signature_line") or ""),
                        metadata_json={"stance": payload.get("stance")},
                    )
                )
            self.session.flush()
            records = list(self.session.scalars(select(PunditProfile).where(PunditProfile.is_active.is_(True)).order_by(PunditProfile.name.asc())).all())
        return [
            PunditPersonaView(
                name=item.name,
                style=item.style,
                stance=str((item.metadata_json or {}).get("stance") or ""),
                bias={key: [str(value) for value in values] for key, values in dict(item.bias or {}).items()},
                confidence_level=float(item.confidence_level),
                debate_style=item.debate_style,
                signature_line=item.signature_line,
            )
            for item in records
        ]

    def _profile_view(self, payload: dict[str, object]) -> PunditPersonaView:
        return PunditPersonaView(
            name=str(payload["name"]),
            style=str(payload["style"]),
            stance=str(payload.get("stance") or ""),
            bias={key: [str(value) for value in values] for key, values in dict(payload.get("bias") or {}).items()},
            confidence_level=float(payload.get("confidence_level") or 0.65),
            debate_style=str(payload.get("debate_style") or "measured"),
            signature_line=str(payload.get("signature_line") or ""),
        )

    def _build_context_view(self, context: _ResolvedMatchContext) -> PunditShowMatchContextView:
        featured_event_name = None
        if _table_exists(self.session, GlobalEvent.__tablename__):
            event = self.session.scalar(select(GlobalEvent).where(GlobalEvent.match_id == context.match_id).order_by(GlobalEvent.priority.desc(), GlobalEvent.start_time.asc()))
            if event is not None:
                featured_event_name = event.event_name
        score = None
        winner = None
        if context.replay_payload is not None:
            score = f"{context.replay_payload.summary.home_score}-{context.replay_payload.summary.away_score}"
            winner = context.replay_payload.summary.winner_team_name
        return PunditShowMatchContextView(
            match_id=context.match_id,
            home_team_name=context.home_team_name,
            away_team_name=context.away_team_name,
            status=context.status,
            stage=context.stage,
            competition_type=context.competition_type,
            is_final=context.is_final,
            kickoff_at=context.kickoff_at,
            score=score,
            winner_team_name=winner,
            featured_event_name=featured_event_name,
        )

    def _build_stats(self, context: _ResolvedMatchContext) -> PunditShowStatsView:
        if context.replay_payload is not None:
            analysis = analyze_match(context.replay_payload)
            return PunditShowStatsView(
                home_win_probability=int(context.replay_payload.win_probability_home),
                draw_probability=int(context.replay_payload.win_probability_draw),
                away_win_probability=int(context.replay_payload.win_probability_away),
                expected_goals_home=round(float(context.replay_payload.expected_goals_home), 2),
                expected_goals_away=round(float(context.replay_payload.expected_goals_away), 2),
                total_expected_goals=round(float(context.replay_payload.expected_goals_home + context.replay_payload.expected_goals_away), 2),
                possession_winner=analysis.get("possession_winner"),
                key_player=analysis.get("key_player"),
                key_player_rating=analysis.get("key_player_rating"),
                summary_line=context.replay_payload.summary.summary_line,
            )
        home_prob, draw_prob, away_prob, xg_home, xg_away = self._preview_probabilities(context)
        return PunditShowStatsView(
            home_win_probability=home_prob,
            draw_probability=draw_prob,
            away_win_probability=away_prob,
            expected_goals_home=xg_home,
            expected_goals_away=xg_away,
            total_expected_goals=round(xg_home + xg_away, 2),
            possession_winner=context.home_team_name if home_prob >= away_prob else context.away_team_name,
            key_player=self._preview_star(context),
            key_player_rating=None,
            summary_line=f"{context.home_team_name} hold the slight edge on the desk numbers." if home_prob >= away_prob else f"{context.away_team_name} look marginally stronger on the desk numbers.",
        )

    def _build_prediction(self, context: _ResolvedMatchContext, stats: PunditShowStatsView) -> PunditPredictionView:
        winner = context.home_team_name if stats.home_win_probability >= max(stats.draw_probability, stats.away_win_probability) else context.away_team_name
        if stats.draw_probability > max(stats.home_win_probability, stats.away_win_probability):
            winner = None
        predicted_score = f"{max(0, round(stats.expected_goals_home))}-{max(0, round(stats.expected_goals_away))}"
        return PunditPredictionView(
            predicted_winner=winner,
            predicted_score=predicted_score if predicted_score != "0-0" else "1-1",
            confidence=round(max(stats.home_win_probability, stats.draw_probability, stats.away_win_probability) / 100, 2),
            home_win_probability=stats.home_win_probability,
            draw_probability=stats.draw_probability,
            away_win_probability=stats.away_win_probability,
            reasons=[
                f"Expected goals lean {stats.expected_goals_home:.2f} to {stats.expected_goals_away:.2f}.",
                f"Primary player watch: {self._preview_star(context) or 'team structure'}",
                "Global memory and calendar pressure have been folded into the desk verdict.",
            ],
        )

    def _build_memory(self, context: _ResolvedMatchContext) -> list[str]:
        items: list[str] = []
        if context.is_final:
            items.append("This event sits in a finals slot, so the panel is reading it through a legacy lens.")
        if context.replay_payload is not None and context.replay_payload.summary.turning_points:
            items.append(f"Turning-point memory: {context.replay_payload.summary.turning_points[0]}")
        if context.home_user_id and _table_exists(self.session, "user_dynasty"):
            from app.global_memory.models import UserDynasty

            home_dynasty = self.session.scalar(select(UserDynasty).where(UserDynasty.user_id == context.home_user_id))
            away_dynasty = self.session.scalar(select(UserDynasty).where(UserDynasty.user_id == context.away_user_id)) if context.away_user_id else None
            if home_dynasty is not None:
                items.append(f"Home dynasty ledger: {int(home_dynasty.total_titles)} total titles.")
            if away_dynasty is not None:
                items.append(f"Away dynasty ledger: {int(away_dynasty.total_titles)} total titles.")
        if context.replay_payload is not None and _table_exists(self.session, "player_history"):
            from app.global_memory.models import PlayerHistory

            player_ids = [item.player_id for item in context.replay_payload.summary.player_stats[:5] if getattr(item, "player_id", None)]
            rows = list(self.session.scalars(select(PlayerHistory).where(PlayerHistory.player_id.in_(player_ids)).order_by(PlayerHistory.created_at.desc()).limit(2)).all()) if player_ids else []
            items.extend(item.event for item in rows if item.event)
        if not items:
            items.append("Global memory is quiet here, so the panel is leaning on present form and event context.")
        return items[:4]

    def _pre_segments(self, context: _ResolvedMatchContext, profiles: list[PunditPersonaView], prediction: PunditPredictionView, memory: list[str]) -> list[PunditShowSegmentView]:
        return [
            PunditShowSegmentView(order=1, segment_type="opening", title="Opening Headlines", speaker=profiles[2].name, summary=f"{context.home_team_name} and {context.away_team_name} arrive with pressure in different places.", talking_points=[memory[0], f"Kickoff stage: {context.stage}"]),
            PunditShowSegmentView(order=2, segment_type="lineups", title="Lineup Radar", speaker=profiles[3].name, summary="The desk checks the key duels before kickoff.", talking_points=[f"Player watch: {item.player_name}" for item in self._pre_watchlist(context)[:3]]),
            PunditShowSegmentView(order=3, segment_type="tactics", title="Tactical Preview", speaker=profiles[0].name, summary="Structure, pressure, and transition control frame the preview.", talking_points=prediction.reasons[:3]),
            PunditShowSegmentView(order=4, segment_type="predictions", title="Final Verdicts", speaker=profiles[1].name, summary="The panel commits to a score line before kickoff.", talking_points=[f"Predicted score: {prediction.predicted_score}", f"Projected winner: {prediction.predicted_winner or 'draw'}"]),
        ]

    def _post_segments(self, context: _ResolvedMatchContext, profiles: list[PunditPersonaView], memory: list[str]) -> list[PunditShowSegmentView]:
        summary = context.replay_payload.summary
        return [
            PunditShowSegmentView(order=1, segment_type="analysis", title="Result Breakdown", speaker=profiles[0].name, summary=summary.summary_line, talking_points=[f"Score: {summary.home_score}-{summary.away_score}", f"Winner: {summary.winner_team_name or 'draw'}"]),
            PunditShowSegmentView(order=2, segment_type="ratings", title="Ratings Board", speaker=profiles[3].name, summary="The studio separates match-winners from passengers.", talking_points=[f"{item.player_name}: {item.rating:.1f}" for item in self._post_ratings(context)[:4]]),
            PunditShowSegmentView(order=3, segment_type="controversy", title="Controversy Corner", speaker=profiles[1].name, summary="Every big result leaves a fresh argument on the table.", talking_points=self._post_controversies(context)[:3]),
            PunditShowSegmentView(order=4, segment_type="legacy", title="Global Memory Check", speaker=profiles[2].name, summary="The desk drops the result into the longer GTEX arc.", talking_points=memory[:3]),
        ]

    def _pre_interactions(self, context: _ResolvedMatchContext, profiles: list[PunditPersonaView], prediction: PunditPredictionView, memory: list[str]) -> list[PunditInteractionView]:
        star = self._preview_star(context) or "the main forward"
        return [
            PunditInteractionView(speaker=profiles[0].name, interaction_type="analysis", target_speaker=None, line=f"The shape battle points toward {prediction.predicted_winner or 'a draw'} because the control zones lean that way.", tone="measured"),
            PunditInteractionView(speaker=profiles[1].name, interaction_type="interruption", target_speaker=profiles[0].name, line=f"That is too polite. If {star} catches fire, the script blows up early.", tone="aggressive"),
            PunditInteractionView(speaker=profiles[3].name, interaction_type="agreement", target_speaker=profiles[1].name, line="I agree on the momentum point. Big games are never just geometry once the duels turn personal.", tone="firm"),
            PunditInteractionView(speaker=profiles[2].name, interaction_type="narrative_shift", target_speaker=None, line=memory[0], tone="narrative"),
            PunditInteractionView(speaker=profiles[1].name, interaction_type="prediction", target_speaker=None, line=f"My call is {prediction.predicted_score}, and I am not hedging that on this desk.", tone="aggressive"),
        ]

    def _post_interactions(self, context: _ResolvedMatchContext, profiles: list[PunditPersonaView], analysis: dict[str, Any]) -> list[PunditInteractionView]:
        lines = self.debate_generator.generate(analysis=analysis, hot_takes=generate_hot_takes(analysis))
        interactions: list[PunditInteractionView] = []
        previous = None
        for index, line in enumerate(lines):
            interaction_type = "analysis"
            if index == 1:
                interaction_type = "interruption"
            elif index in {2, 4}:
                interaction_type = "disagreement"
            elif index in {3, 5}:
                interaction_type = "agreement"
            interactions.append(PunditInteractionView(speaker=line.speaker, interaction_type=interaction_type, target_speaker=previous, line=line.line, tone="aggressive" if line.emphasis == "high" else "measured"))
            previous = line.speaker
        return interactions

    def _pre_watchlist(self, context: _ResolvedMatchContext) -> list[PunditPlayerRatingView]:
        players = sorted(self._preview_players(context), key=lambda item: item["overall"], reverse=True)
        return [PunditPlayerRatingView(player_id=item.get("player_id"), player_name=str(item["player_name"]), team_name=str(item["team_name"]), rating=min(10.0, round(float(item["overall"]) / 10, 1)), verdict="key matchup") for item in players[:5]]

    def _post_ratings(self, context: _ResolvedMatchContext) -> list[PunditPlayerRatingView]:
        if context.replay_payload is None:
            return self._pre_watchlist(context)
        ordered = sorted(context.replay_payload.summary.player_stats, key=lambda item: (item.rating or 0.0, item.goals, item.assists, item.saves), reverse=True)
        return [PunditPlayerRatingView(player_id=item.player_id, player_name=item.player_name, team_name=item.team_name, rating=round(float(item.rating or 0.0), 1), verdict=self._rating_verdict(float(item.rating or 0.0))) for item in ordered[:5]]

    def _post_controversies(self, context: _ResolvedMatchContext) -> list[str]:
        issues: list[str] = []
        for event in getattr(context.replay_payload.timeline, "events", []) if context.replay_payload is not None else []:
            event_type = _enum_value(getattr(event, "event_type", None), "").lower()
            if "penalty" in event_type:
                issues.append(f"Penalty flashpoint in minute {event.minute}: {event.description or 'decision review'}")
            if "red" in event_type:
                issues.append(f"Red-card debate in minute {event.minute}: {event.description or 'discipline swing'}")
        if context.replay_payload is not None:
            issues.extend(context.replay_payload.summary.turning_points[:2])
        return issues[:4] or ["No single officiating flashpoint dominated, so the desk is focusing on execution instead."]

    def _pre_watchpoints(self, context: _ResolvedMatchContext) -> list[str]:
        items = [
            "Selection balance in midfield could reshape the first hour.",
            "An early booking on the key enforcer changes the press and the duel map.",
        ]
        if context.is_final:
            items.append("Final pressure means the first mistake can redraw the whole script.")
        return items[:3]

    def _preview_analysis(self, context: _ResolvedMatchContext) -> dict[str, Any]:
        stats = self._build_stats(context)
        prediction = self._build_prediction(context, stats)
        return {
            "score": prediction.predicted_score,
            "winner_team_name": prediction.predicted_winner,
            "xg_diff": round(stats.expected_goals_home - stats.expected_goals_away, 2),
            "shot_diff": 0,
            "possession_winner": stats.possession_winner,
            "upset": False,
            "is_final": context.is_final,
            "key_player": stats.key_player,
            "key_player_team": context.home_team_name if stats.home_win_probability >= stats.away_win_probability else context.away_team_name,
            "key_player_rating": stats.key_player_rating,
            "summary_line": stats.summary_line or "The desk is leaning on preview indicators before kickoff.",
            "turning_point": "The lineup reveal is likely to shape the early narrative.",
        }

    def _preview_probabilities(self, context: _ResolvedMatchContext) -> tuple[int, int, int, float, float]:
        home_strength = self._team_strength(getattr(context.preview_request, "home_team", None))
        away_strength = self._team_strength(getattr(context.preview_request, "away_team", None))
        delta = (home_strength - away_strength) / 100
        home_prob, draw_prob, away_prob = _normalize_probabilities(0.38 + (delta * 0.28), 0.28 - abs(delta) * 0.08, 0.34 - (delta * 0.24))
        xg_home = round(max(0.8, 1.35 + (delta * 1.1)), 2)
        xg_away = round(max(0.7, 1.15 - (delta * 0.9)), 2)
        return home_prob, draw_prob, away_prob, xg_home, xg_away

    def _team_strength(self, team: Any | None) -> float:
        players = list(getattr(team, "starters", []) or [])
        return sum(float(player.overall) for player in players) / len(players) if players else 75.0

    def _preview_players(self, context: _ResolvedMatchContext) -> list[dict[str, Any]]:
        preview = context.preview_request
        if preview is None:
            return []
        items: list[dict[str, Any]] = []
        for team in (preview.home_team, preview.away_team):
            for player in team.starters:
                items.append({"player_id": player.player_id, "player_name": player.player_name, "team_name": team.team_name, "overall": int(player.overall)})
        return items

    def _preview_star(self, context: _ResolvedMatchContext) -> str | None:
        players = self._preview_players(context)
        return str(max(players, key=lambda item: item["overall"])["player_name"]) if players else None

    def _parse_preview(self, payload: Any) -> Any | None:
        if not isinstance(payload, dict):
            return None
        try:
            from app.match_engine.schemas import MatchSimulationRequest

            return MatchSimulationRequest.model_validate(payload)
        except Exception:
            return None

    def _parse_replay(self, payload: Any) -> Any | None:
        if not isinstance(payload, dict):
            return None
        try:
            from app.match_engine.schemas import MatchReplayPayloadView

            return MatchReplayPayloadView.model_validate(payload)
        except Exception:
            return None

    def _competitive_preview(self, match: Any) -> Any | None:
        try:
            from app.match_engine.schemas import MatchCompetitionContextInput, MatchSimulationRequest, MatchTeamInput

            return MatchSimulationRequest(
                match_id=match.id,
                competition=MatchCompetitionContextInput(competition_type="cup", stage="competitive", is_final=False),
                home_team=MatchTeamInput.model_validate(match.locked_lineup_home),
                away_team=MatchTeamInput.model_validate(match.locked_lineup_away),
            )
        except Exception:
            return None

    def _preview_team_name(self, preview: Any | None, side: str) -> str | None:
        if preview is None:
            return None
        return str(preview.home_team.team_name if side == "home" else preview.away_team.team_name)

    def _preview_stage(self, preview: Any | None) -> str | None:
        return str(preview.competition.stage) if preview is not None else None

    def _preview_competition_type(self, preview: Any | None) -> str | None:
        return _enum_value(preview.competition.competition_type, "league") if preview is not None else None

    def _preview_is_final(self, preview: Any | None) -> bool:
        return bool(preview.competition.is_final) if preview is not None else False

    def _preview_kickoff(self, preview: Any | None) -> datetime | None:
        return preview.kickoff_at if preview is not None else None

    def _replay_team_name(self, replay: Any | None, side: str) -> str | None:
        if replay is None:
            return None
        return str(replay.summary.home_stats.team_name if side == "home" else replay.summary.away_stats.team_name)

    def _replay_stage(self, replay: Any | None) -> str | None:
        return str(replay.summary.stage) if replay is not None else None

    def _replay_competition_type(self, replay: Any | None) -> str | None:
        return _enum_value(replay.summary.competition_type, "league") if replay is not None else None

    def _replay_is_final(self, replay: Any | None) -> bool:
        return bool(replay.summary.is_final) if replay is not None else False

    def _rating_verdict(self, rating: float) -> str:
        if rating >= 8.7:
            return "commanding"
        if rating >= 7.8:
            return "decisive"
        if rating >= 6.8:
            return "steady"
        return "under pressure"

    def _pipeline(self) -> list[str]:
        return ["match_context", "stats", "global_memory", "pundit_profiles", "debate_engine", "script_output"]
