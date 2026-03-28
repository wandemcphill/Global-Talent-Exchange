from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import random
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.match_engine.schemas import MatchReplayPayloadView, MatchSimulationRequest
from app.matches.schemas import CommentaryEventView, CommentaryVoiceView, MatchCommentaryView
from app.models.commentary_event import CommentaryEvent
from app.models.manager_duel import ManagerDuel
from app.models.notification_record import NotificationRecord
from app.models.player_rivalry import PlayerRivalry
from app.models.player_story import PlayerStory
from app.models.regen import RegenLegacyRecord, RegenProfile

_TEMPLATES = {
    "neutral": {
        "goal": [
            "{player} finds the net for {team}.",
            "{player} strikes for {team}.",
        ],
        "shot": [
            "{player} lets it go for {team}.",
            "{team} work the opening for {player}.",
        ],
        "save": [
            "{player} keeps it out for {team}.",
            "{player} makes the stop for {team}.",
        ],
        "card": [
            "{player} goes into the book for {team}.",
            "{team} pay for the foul as {player} is cautioned.",
        ],
        "substitution": [
            "{team} turn to the bench.",
            "{team} make a change.",
        ],
        "foul": [
            "{player} halts the move for {team}.",
            "{team} concede the foul through {player}.",
        ],
        "stage": [
            "The match settles into another phase.",
            "The rhythm of the contest shifts again.",
        ],
        "generic": [
            "Another beat in the story of this contest.",
            "The match takes another turn.",
        ],
    },
    "hype": {
        "goal": [
            "{player} detonates for {team}!",
            "{team} erupt as {player} lands the finish!",
        ],
        "shot": [
            "{player} pulls the trigger for {team}!",
            "{team} surge forward through {player}!",
        ],
        "save": [
            "{player} comes up huge for {team}!",
            "{player} slams the door shut for {team}!",
        ],
        "card": [
            "{player} pushes the temperature up again!",
            "{team} feel the heat as {player} sees the card!",
        ],
        "substitution": [
            "{team} roll the dice from the bench!",
            "Fresh energy arrives for {team}!",
        ],
        "foul": [
            "{player} crashes into the phase and the whistle follows!",
            "{team} stop the move with force through {player}!",
        ],
        "stage": [
            "The pressure keeps building in this stadium!",
            "Another surge in the energy of this contest!",
        ],
        "generic": [
            "This match keeps adding drama!",
            "The story keeps accelerating!",
        ],
    },
    "analytical": {
        "goal": [
            "{player} converts for {team} after a decisive sequence.",
            "{team} capitalize through {player}.",
        ],
        "shot": [
            "{player} concludes the move for {team}.",
            "{team} generate the attempt through {player}.",
        ],
        "save": [
            "{player} preserves the shape for {team} with the save.",
            "{team} stay intact because of {player}.",
        ],
        "card": [
            "{player} is penalized and the risk profile shifts.",
            "The card changes the defensive margin for {team}.",
        ],
        "substitution": [
            "{team} adjust personnel from the bench.",
            "The substitution changes the balance for {team}.",
        ],
        "foul": [
            "{player} disrupts the action and concedes the foul.",
            "{team} interrupt the sequence through {player}.",
        ],
        "stage": [
            "The game moves into a new management phase.",
            "The contest settles into a different rhythm.",
        ],
        "generic": [
            "The match context changes again.",
            "Another tactical data point arrives.",
        ],
    },
}


class MatchCommentaryError(ValueError):
    pass


class MatchCommentaryNotFoundError(MatchCommentaryError):
    pass


class MatchCommentaryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def apply_to_replay_payload(
        self,
        replay_payload: MatchReplayPayloadView,
        *,
        request: MatchSimulationRequest | None = None,
        tone: str = "neutral",
        language: str = "en",
    ) -> MatchReplayPayloadView:
        player_ids = {
            item
            for event in replay_payload.timeline.events
            for item in (
                event.primary_player.player_id if event.primary_player is not None else None,
                event.secondary_player.player_id if event.secondary_player is not None else None,
            )
            if item
        }
        players = self._players(player_ids)
        stories = self._stories(player_ids)
        legacies = self._legacies(player_ids)
        regens = self._regens(player_ids)
        rivalries = self._rivalries(player_ids)
        request_lookup = self._request_lookup(request)
        recent_lines: deque[str] = deque(maxlen=5)
        cache: dict[tuple[str, str, str], str] = {}
        goals_by_player: dict[str, int] = {}
        previous_home_score = 0
        previous_away_score = 0
        tone_key = self._resolve_tone(tone)
        language_key = self._resolve_language(language)

        for event in replay_payload.timeline.events:
            player_id = event.primary_player.player_id if event.primary_player is not None else None
            if self._event_family(self._event_value(event.event_type)) == "goal" and player_id:
                goals_by_player[player_id] = goals_by_player.get(player_id, 0) + 1
            context = self._build_context(
                replay_payload=replay_payload,
                event=event,
                request_lookup=request_lookup,
                players=players,
                stories=stories,
                legacies=legacies,
                regens=regens,
                rivalries=rivalries,
                goals_by_player=goals_by_player,
                previous_home_score=previous_home_score,
                previous_away_score=previous_away_score,
                tone=tone_key,
                language=language_key,
            )
            line = self._render_line(
                context,
                tone=tone_key,
                language=language_key,
                recent_lines=recent_lines,
                line_cache=cache,
                fallback=event.commentary,
            )
            metadata = dict(event.metadata or {})
            metadata["commentary_context"] = context
            metadata["commentary_type"] = context["commentary_type"]
            metadata["crowd_state"] = context["crowd_state"]
            metadata["description"] = line
            event.commentary = line
            event.metadata = metadata
            recent_lines.append(line)
            previous_home_score = event.home_score
            previous_away_score = event.away_score
        return replay_payload

    def persist_replay_commentary(
        self,
        match_id: str,
        replay_payload: MatchReplayPayloadView,
        *,
        audience_user_ids: tuple[str | None, ...] = (),
    ) -> list[CommentaryEvent]:
        self.session.execute(delete(CommentaryEvent).where(CommentaryEvent.match_id == match_id))
        rows: list[CommentaryEvent] = []
        highlight_sent = False
        star_sent = False
        for event in replay_payload.timeline.events:
            context = dict((event.metadata or {}).get("commentary_context") or {})
            rows.append(
                CommentaryEvent(
                    match_id=match_id,
                    minute=event.minute,
                    event_type=self._event_value(event.event_type),
                    context=context,
                    generated_line=event.commentary,
                )
            )
            if not highlight_sent and self._is_highlight_context(context):
                self._notify_audience(
                    audience_user_ids,
                    template_key="COMMENTARY_HIGHLIGHT",
                    message=event.commentary,
                    match_id=match_id,
                    context=context,
                )
                highlight_sent = True
            if not star_sent and self._is_star_context(context):
                self._notify_audience(
                    audience_user_ids,
                    template_key="STAR_PLAYER_FEATURED",
                    message=f"{context.get('player_name') or 'A featured talent'} took the spotlight in live commentary.",
                    match_id=match_id,
                    context=context,
                )
                star_sent = True
        self.session.add_all(rows)
        self.session.flush()
        return rows

    def get_match_commentary(
        self,
        match_id: str,
        *,
        tone: str = "neutral",
        language: str = "en",
        voice_enabled: bool = False,
    ) -> MatchCommentaryView:
        rows = self._commentary_rows(match_id)
        if not rows and self._hydrate_from_manager_duel(match_id):
            rows = self._commentary_rows(match_id)
        if not rows:
            raise MatchCommentaryNotFoundError(match_id)
        tone_key = self._resolve_tone(tone)
        language_key = self._resolve_language(language)
        recent_lines: deque[str] = deque(maxlen=5)
        cache: dict[tuple[str, str, str], str] = {}
        voice = CommentaryVoiceView(enabled=voice_enabled, status="not_configured", audio_url=None)
        events: list[CommentaryEventView] = []
        for row in rows:
            context = dict(row.context or {})
            line = self._render_line(
                context,
                tone=tone_key,
                language=language_key,
                recent_lines=recent_lines,
                line_cache=cache,
                fallback=row.generated_line,
            )
            events.append(
                CommentaryEventView(
                    id=row.id,
                    match_id=row.match_id,
                    minute=row.minute,
                    event_type=row.event_type,
                    context=context,
                    generated_line=line,
                    voice=voice,
                )
            )
            recent_lines.append(line)
        return MatchCommentaryView(
            match_id=match_id,
            tone=tone_key,
            language=language_key,
            voice_enabled=voice_enabled,
            events=events,
        )

    def _build_context(
        self,
        *,
        replay_payload: MatchReplayPayloadView,
        event,
        request_lookup: dict[str, dict[str, Any]],
        players: dict[str, Player],
        stories: dict[str, PlayerStory],
        legacies: dict[str, RegenLegacyRecord],
        regens: dict[str, RegenProfile],
        rivalries: dict[frozenset[str], PlayerRivalry],
        goals_by_player: dict[str, int],
        previous_home_score: int,
        previous_away_score: int,
        tone: str,
        language: str,
    ) -> dict[str, Any]:
        event_type = self._event_value(event.event_type)
        family = self._event_family(event_type)
        player_id = event.primary_player.player_id if event.primary_player is not None else None
        secondary_player_id = event.secondary_player.player_id if event.secondary_player is not None else None
        player = players.get(player_id) if player_id else None
        legacy = legacies.get(player_id) if player_id else None
        regen = regens.get(player_id) if player_id else None
        story = stories.get(player_id) if player_id else None
        rivalry = rivalries.get(frozenset({player_id, secondary_player_id})) if player_id and secondary_player_id else None
        request_context = request_lookup.get(player_id or "", {})
        rivalry_intensity = float(rivalry.intensity_score) if rivalry is not None else float(request_context.get("rivalry_intensity") or 0.0)
        legacy_score = float(legacy.legacy_score) if legacy is not None else 0.0
        awards_total = int(legacy.awards_total) if legacy is not None else 0
        player_rarity = self._player_rarity(regen=regen, legacy=legacy)
        recognition_line = self._recognition_line(
            legacy_score=legacy_score,
            awards_total=awards_total,
            player_rarity=player_rarity,
        )
        documentary_insert = self._documentary_insert(story=story, player_name=event.primary_player.player_name if event.primary_player is not None else None)
        equalizer = self._is_equalizer(event.home_score, event.away_score, previous_home_score, previous_away_score)
        go_ahead = self._is_go_ahead_goal(event.home_score, event.away_score, previous_home_score, previous_away_score)
        narrative_insert = self._narrative_insert(
            family=family,
            player_name=event.primary_player.player_name if event.primary_player is not None else None,
            rivalry_intensity=rivalry_intensity,
            equalizer=equalizer,
            go_ahead=go_ahead,
            goals_in_match=goals_by_player.get(player_id or "", 0),
            recognition_line=recognition_line,
            documentary_insert=documentary_insert,
        )
        crowd_state = self._crowd_state(
            minute=event.minute,
            family=family,
            importance=self._match_importance(replay_payload),
            rivalry_intensity=rivalry_intensity,
            home_score=event.home_score,
            away_score=event.away_score,
        )
        commentary_type = "narrative_insert" if narrative_insert else "color_commentary" if family in {"save", "substitution", "stage"} else "play_by_play"
        return {
            "match_id": replay_payload.match_id,
            "source_event_id": event.event_id,
            "minute": event.minute,
            "event_type": event_type,
            "event_family": family,
            "tone": tone,
            "language": language,
            "team_id": event.team_id,
            "team_name": event.team_name,
            "opponent_team_name": self._opponent_team_name(replay_payload, event.team_id),
            "player_id": player_id,
            "player_name": event.primary_player.player_name if event.primary_player is not None else None,
            "secondary_player_id": secondary_player_id,
            "secondary_player_name": event.secondary_player.player_name if event.secondary_player is not None else None,
            "home_score": event.home_score,
            "away_score": event.away_score,
            "match_importance": self._match_importance(replay_payload),
            "stage": str(replay_payload.summary.stage or ""),
            "is_final": bool(replay_payload.summary.is_final),
            "rivalry_intensity": round(rivalry_intensity, 2),
            "recent_form": request_context.get("recent_form"),
            "leadership": request_context.get("leadership"),
            "dna_archetype": str((player.dna_profile or {}).get("archetype", "balanced")) if player is not None else None,
            "documentary_insert": documentary_insert,
            "recognition_line": recognition_line,
            "player_rarity": player_rarity,
            "legacy_score": round(legacy_score, 2),
            "awards_total": awards_total,
            "goals_in_match": goals_by_player.get(player_id or "", 0),
            "narrative_insert": narrative_insert,
            "commentary_type": commentary_type,
            "crowd_state": crowd_state,
        }

    def _render_line(
        self,
        context: dict[str, Any],
        *,
        tone: str,
        language: str,
        recent_lines: deque[str],
        line_cache: dict[tuple[str, str, str], str],
        fallback: str,
    ) -> str:
        signature = self._signature(context)
        cache_key = (tone, language, signature)
        cached = line_cache.get(cache_key)
        if cached and cached not in recent_lines:
            return cached
        family = str(context.get("event_family") or "generic")
        templates = _TEMPLATES.get(tone, _TEMPLATES["neutral"]).get(family) or _TEMPLATES["neutral"]["generic"]
        indexes = list(range(len(templates)))
        random.Random(self._seed_int(signature, tone, language)).shuffle(indexes)
        format_data = {
            "player": context.get("player_name") or context.get("team_name") or "The player",
            "team": context.get("team_name") or "the side",
        }
        line = fallback
        for index in indexes:
            candidate = templates[index].format(**format_data)
            line = candidate
            if candidate not in recent_lines:
                break
        insert = self._preferred_insert(context, tone=tone)
        if insert:
            line = f"{line} {insert}"
        line_cache[cache_key] = line
        return line

    def _commentary_rows(self, match_id: str) -> list[CommentaryEvent]:
        return list(
            self.session.scalars(
                select(CommentaryEvent)
                .where(CommentaryEvent.match_id == match_id)
                .order_by(CommentaryEvent.minute.asc(), CommentaryEvent.created_at.asc(), CommentaryEvent.id.asc())
            ).all()
        )

    def _hydrate_from_manager_duel(self, match_id: str) -> bool:
        duel = self.session.get(ManagerDuel, match_id)
        if duel is None:
            return False
        replay_data = (duel.metadata_json or {}).get("replay_payload")
        if not isinstance(replay_data, dict):
            return False
        replay_payload = MatchReplayPayloadView.model_validate(replay_data)
        self.apply_to_replay_payload(replay_payload)
        self.persist_replay_commentary(
            match_id,
            replay_payload,
            audience_user_ids=(duel.home_user_id, duel.away_user_id),
        )
        duel.metadata_json = {
            **(duel.metadata_json or {}),
            "replay_payload": replay_payload.model_dump(mode="json"),
        }
        self.session.flush()
        return True

    def _players(self, player_ids: set[str]) -> dict[str, Player]:
        if not player_ids:
            return {}
        return {
            item.id: item
            for item in self.session.scalars(select(Player).where(Player.id.in_(player_ids))).all()
        }

    def _stories(self, player_ids: set[str]) -> dict[str, PlayerStory]:
        if not player_ids:
            return {}
        return {
            item.player_id: item
            for item in self.session.scalars(select(PlayerStory).where(PlayerStory.player_id.in_(player_ids))).all()
        }

    def _legacies(self, player_ids: set[str]) -> dict[str, RegenLegacyRecord]:
        if not player_ids:
            return {}
        return {
            item.player_id: item
            for item in self.session.scalars(select(RegenLegacyRecord).where(RegenLegacyRecord.player_id.in_(player_ids))).all()
        }

    def _regens(self, player_ids: set[str]) -> dict[str, RegenProfile]:
        if not player_ids:
            return {}
        return {
            item.player_id: item
            for item in self.session.scalars(select(RegenProfile).where(RegenProfile.player_id.in_(player_ids))).all()
        }

    def _rivalries(self, player_ids: set[str]) -> dict[frozenset[str], PlayerRivalry]:
        if not player_ids:
            return {}
        return {
            frozenset({item.player_a_id, item.player_b_id}): item
            for item in self.session.scalars(
                select(PlayerRivalry).where(
                    or_(
                        PlayerRivalry.player_a_id.in_(player_ids),
                        PlayerRivalry.player_b_id.in_(player_ids),
                    )
                )
            ).all()
        }

    def _request_lookup(self, request: MatchSimulationRequest | None) -> dict[str, dict[str, Any]]:
        if request is None:
            return {}
        lookup: dict[str, dict[str, Any]] = {}
        for team in (request.home_team, request.away_team):
            for player in [*team.starters, *team.bench]:
                lookup[player.player_id] = {
                    "recent_form": player.recent_form,
                    "leadership": player.leadership,
                    "rivalry_intensity": team.club_context.rivalry_intensity,
                }
        return lookup

    @staticmethod
    def _preferred_insert(context: dict[str, Any], *, tone: str) -> str | None:
        if tone == "analytical":
            value = str(context.get("narrative_insert") or "").strip()
            return value or None
        for key in ("narrative_insert", "recognition_line", "documentary_insert"):
            value = str(context.get(key) or "").strip()
            if value:
                return value
        return None

    @staticmethod
    def _crowd_state(
        *,
        minute: int,
        family: str,
        importance: str,
        rivalry_intensity: float,
        home_score: int,
        away_score: int,
    ) -> dict[str, int]:
        impact = {"goal": 32, "save": 18, "card": 16, "substitution": 10, "stage": 6}.get(family, 8)
        importance_bonus = {"final": 24, "knockout": 16, "derby": 18, "featured": 10, "standard": 0}.get(importance, 0)
        score_gap = abs(home_score - away_score)
        excitement = min(100, round(26 + impact + importance_bonus + (rivalry_intensity * 0.24) + (minute * 0.35)))
        tension = min(100, round(22 + importance_bonus + (rivalry_intensity * 0.32) + ((2 - min(score_gap, 2)) * 12) + (minute * 0.4)))
        return {"excitement_level": max(0, excitement), "tension_level": max(0, tension)}

    @staticmethod
    def _match_importance(replay_payload: MatchReplayPayloadView) -> str:
        stage = str(replay_payload.summary.stage or "").lower()
        if replay_payload.summary.is_final:
            return "final"
        if "semi" in stage or "quarter" in stage or "knockout" in stage:
            return "knockout"
        if "derby" in stage:
            return "derby"
        if replay_payload.summary.highlight_profile.value != "normal":
            return "featured"
        return "standard"

    @staticmethod
    def _event_family(event_type: str) -> str:
        if event_type in {"goal", "penalty_goal", "penalty_scored"}:
            return "goal"
        if event_type in {"shot", "shot_on_target", "missed_chance", "missed_big_chance", "woodwork"}:
            return "shot"
        if event_type in {"save", "goalkeeper_save", "double_save"}:
            return "save"
        if event_type in {"yellow_card", "red_card"}:
            return "card"
        if event_type in {"substitution", "substitution_impact"}:
            return "substitution"
        if event_type in {"kickoff", "halftime", "fulltime", "tactical_change", "tactical_swing"}:
            return "stage"
        if event_type in {"foul", "tactical_foul", "penalty_awarded", "offside"}:
            return "foul"
        return "generic"

    @staticmethod
    def _recognition_line(*, legacy_score: float, awards_total: int, player_rarity: str) -> str | None:
        if legacy_score >= 85 or awards_total >= 3:
            return "One of the finest talents in the league keeps answering the moment."
        if player_rarity == "generational":
            return "The generational talent keeps adding weight to the story."
        if legacy_score >= 70:
            return "A proven name in this universe delivers again."
        return None

    @staticmethod
    def _documentary_insert(*, story: PlayerStory | None, player_name: str | None) -> str | None:
        if story is None or float(story.narrative_score or 0.0) < 60:
            return None
        if player_name:
            return f"{player_name}'s documentary arc keeps building."
        return "The documentary thread grows stronger."

    @staticmethod
    def _narrative_insert(
        *,
        family: str,
        player_name: str | None,
        rivalry_intensity: float,
        equalizer: bool,
        go_ahead: bool,
        goals_in_match: int,
        recognition_line: str | None,
        documentary_insert: str | None,
    ) -> str | None:
        if family == "goal" and rivalry_intensity >= 70:
            return "This rivalry just got another chapter."
        if family == "goal" and go_ahead:
            return "That may be the swing the match was waiting for."
        if family == "goal" and equalizer:
            return "The comeback pulse is alive now."
        if family == "goal" and goals_in_match >= 3 and player_name:
            return f"{player_name} is writing a night to remember."
        if family == "goal" and recognition_line:
            return recognition_line
        if family in {"goal", "substitution"} and documentary_insert:
            return documentary_insert
        return None

    @staticmethod
    def _is_equalizer(home_score: int, away_score: int, previous_home_score: int, previous_away_score: int) -> bool:
        return (previous_home_score - previous_away_score) != 0 and (home_score - away_score) == 0

    @staticmethod
    def _is_go_ahead_goal(home_score: int, away_score: int, previous_home_score: int, previous_away_score: int) -> bool:
        return (previous_home_score - previous_away_score) == 0 and (home_score - away_score) != 0

    @staticmethod
    def _player_rarity(*, regen: RegenProfile | None, legacy: RegenLegacyRecord | None) -> str:
        potential_max = int((regen.potential_range_json or {}).get("maximum", regen.current_gsi)) if regen is not None else 0
        legacy_score = float(legacy.legacy_score) if legacy is not None else 0.0
        if (regen is not None and regen.is_special_lineage) or potential_max >= 94 or legacy_score >= 88:
            return "generational"
        if potential_max >= 90 or legacy_score >= 72:
            return "elite"
        return "standard"

    @staticmethod
    def _opponent_team_name(replay_payload: MatchReplayPayloadView, team_id: str | None) -> str | None:
        if team_id == replay_payload.summary.home_stats.team_id:
            return replay_payload.summary.away_stats.team_name
        if team_id == replay_payload.summary.away_stats.team_id:
            return replay_payload.summary.home_stats.team_name
        return None

    @staticmethod
    def _resolve_language(language: str) -> str:
        return "en" if language != "en" else language

    @staticmethod
    def _resolve_tone(tone: str) -> str:
        return tone if tone in _TEMPLATES else "neutral"

    @staticmethod
    def _event_value(value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _signature(context: dict[str, Any]) -> str:
        return "|".join(
            [
                str(context.get("match_id") or ""),
                str(context.get("source_event_id") or ""),
                str(context.get("event_family") or ""),
                str(context.get("player_name") or ""),
                str(context.get("team_name") or ""),
                str(context.get("minute") or ""),
                str(context.get("goals_in_match") or ""),
                str(context.get("narrative_insert") or ""),
            ]
        )

    @staticmethod
    def _seed_int(*parts: str) -> int:
        return int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:8], 16)

    @staticmethod
    def _is_highlight_context(context: dict[str, Any]) -> bool:
        crowd = dict(context.get("crowd_state") or {})
        return str(context.get("event_family") or "") == "goal" or int(crowd.get("excitement_level") or 0) >= 78

    @staticmethod
    def _is_star_context(context: dict[str, Any]) -> bool:
        return str(context.get("player_rarity") or "") == "generational" or float(context.get("legacy_score") or 0.0) >= 82

    def _notify_audience(
        self,
        audience_user_ids: tuple[str | None, ...],
        *,
        template_key: str,
        message: str,
        match_id: str,
        context: dict[str, Any],
    ) -> None:
        for user_id in {value for value in audience_user_ids if value}:
            self.session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic="commentary",
                    template_key=template_key,
                    resource_type="match_commentary",
                    resource_id=match_id,
                    fixture_id=match_id,
                    competition_id=match_id,
                    message=message[:255],
                    created_at=datetime.now(timezone.utc),
                    metadata_json={
                        "match_id": match_id,
                        "minute": context.get("minute"),
                        "event_type": context.get("event_type"),
                        "player_name": context.get("player_name"),
                        "team_name": context.get("team_name"),
                    },
                )
            )


__all__ = ["MatchCommentaryError", "MatchCommentaryNotFoundError", "MatchCommentaryService"]
