from __future__ import annotations

from datetime import datetime
from typing import Any

from app.match_engine.schemas import MatchPlayerVisualView, MatchReplayPayloadView
from app.models.competition_match import CompetitionMatch
from app.schemas.match_viewer import (
    MatchViewStateView,
    MatchViewerContextBoardView,
    MatchViewerPresentationPackageView,
    MatchViewerPresentationPlayerView,
    MatchViewerPresentationTeamView,
    MatchViewerReactionCardView,
    MatchViewerStandingsEntryView,
)

_LINE_Y_MAP: dict[int, tuple[float, ...]] = {
    1: (50.0,),
    2: (34.0, 66.0),
    3: (22.0, 50.0, 78.0),
    4: (18.0, 39.0, 61.0, 82.0),
    5: (14.0, 32.0, 50.0, 68.0, 86.0),
}
_LINE_X_BY_DEPTH: dict[int, float] = {
    1: 76.0,
    2: 58.0,
    3: 40.0,
    4: 24.0,
}


class MatchViewerPresentationService:
    def build(
        self,
        *,
        match_key: str,
        view_state: MatchViewStateView,
        metadata_json: dict[str, object] | None = None,
        match: CompetitionMatch | None = None,
    ) -> MatchViewerPresentationPackageView:
        metadata = dict(metadata_json or {})
        replay_payload = self._replay_payload(metadata)
        visible_complete = self._is_visible_fulltime(view_state)
        rating_lookup = self._rating_lookup(replay_payload)

        home = self._team_package(
            side="home",
            view_state=view_state,
            metadata=metadata,
            replay_payload=replay_payload,
            rating_lookup=rating_lookup,
        )
        away = self._team_package(
            side="away",
            view_state=view_state,
            metadata=metadata,
            replay_payload=replay_payload,
            rating_lookup=rating_lookup,
        )

        context = self._context_board(
            view_state=view_state,
            metadata=metadata,
            match=match,
            replay_payload=replay_payload,
        )
        reactions = self._reaction_cards(
            metadata=metadata,
            replay_payload=replay_payload,
            visible_complete=visible_complete,
            view_state=view_state,
        )

        return MatchViewerPresentationPackageView(
            match_label=f"{view_state.home_team.team_name} vs {view_state.away_team.team_name}",
            home=home,
            away=away,
            context=context,
            reactions=reactions[:8],
            rating_leaders=self._rating_leaders(replay_payload) if visible_complete else [],
            momentum_notes=self._momentum_notes(replay_payload) if visible_complete else [],
            coach_notes=self._coach_notes(replay_payload) if visible_complete else [],
            commentary_highlights=self._commentary_highlights(replay_payload) if visible_complete else [],
        )

    def _team_package(
        self,
        *,
        side: str,
        view_state: MatchViewStateView,
        metadata: dict[str, object],
        replay_payload: MatchReplayPayloadView | None,
        rating_lookup: dict[str, float],
    ) -> MatchViewerPresentationTeamView:
        team_view = view_state.home_team if side == "home" else view_state.away_team
        if replay_payload is not None and replay_payload.visual_identity is not None:
            identity = (
                replay_payload.visual_identity.home_team
                if side == "home"
                else replay_payload.visual_identity.away_team
            )
            team_stats = (
                replay_payload.summary.home_stats
                if side == "home"
                else replay_payload.summary.away_stats
            )
            starters = identity.player_visuals[:11]
            bench = identity.player_visuals[11:]
            return MatchViewerPresentationTeamView(
                team_id=team_view.team_id,
                team_name=team_view.team_name,
                short_name=team_view.short_name,
                formation=team_stats.current_formation or team_stats.started_formation or team_view.formation,
                coach_name=self._coach_name(metadata, side=side),
                recent_form=self._safe_percent(team_stats.strength.recent_form),
                mentality=self._team_mentality(metadata, side=side),
                instruction_summary=self._instruction_summary(metadata, side=side),
                starters=self._formation_players(
                    starters,
                    formation=team_stats.current_formation or team_stats.started_formation or team_view.formation,
                    rating_lookup=rating_lookup,
                ),
                bench=[
                    self._presentation_player(player, rating_lookup=rating_lookup)
                    for player in bench
                ],
            )

        fallback_players = self._fallback_players(view_state, side=side)
        return MatchViewerPresentationTeamView(
            team_id=team_view.team_id,
            team_name=team_view.team_name,
            short_name=team_view.short_name,
            formation=team_view.formation,
            coach_name=self._coach_name(metadata, side=side),
            recent_form=None,
            mentality=self._team_mentality(metadata, side=side),
            instruction_summary=self._instruction_summary(metadata, side=side),
            starters=self._fallback_formation_players(
                fallback_players,
                formation=team_view.formation,
            ),
            bench=[],
        )

    def _context_board(
        self,
        *,
        view_state: MatchViewStateView,
        metadata: dict[str, object],
        match: CompetitionMatch | None,
        replay_payload: MatchReplayPayloadView | None,
    ) -> MatchViewerContextBoardView:
        standings = self._standings(metadata)
        competition_name = (
            self._string(metadata.get("competition_name"))
            or self._string(metadata.get("competition_label"))
            or self._string(metadata.get("competition"))
            or self._string((metadata.get("broadcast_home") or {}).get("title"))
            or view_state.source.replace("_", " ").title()
        )
        competition_stage = (
            self._string(metadata.get("competition_stage"))
            or self._string(metadata.get("stage"))
            or (match.stage.replace("_", " ").title() if match is not None else None)
            or (replay_payload.summary.stage.replace("_", " ").title() if replay_payload is not None else None)
        )
        kickoff_at = match.scheduled_at if match is not None else self._datetime(metadata.get("scheduled_at"))
        venue_name = (
            self._string(metadata.get("venue_name"))
            or self._string(metadata.get("venue"))
            or self._string(metadata.get("stadium_name"))
            or self._string(metadata.get("stadium"))
        )
        storylines = self._storylines(metadata=metadata, replay_payload=replay_payload)
        return MatchViewerContextBoardView(
            competition_name=competition_name,
            competition_stage=competition_stage,
            venue_name=venue_name,
            kickoff_label=self._kickoff_label(kickoff_at),
            date_label=self._date_label(kickoff_at),
            referee_name=(
                self._string(metadata.get("referee_name"))
                or self._nested_string(metadata, "officials", "referee")
            ),
            match_significance=self._match_significance(
                standings=standings,
                competition_stage=competition_stage,
                replay_payload=replay_payload,
                fallback_storyline=storylines[0] if storylines else None,
            ),
            standings=standings,
            storylines=storylines[:6],
        )

    def _reaction_cards(
        self,
        *,
        metadata: dict[str, object],
        replay_payload: MatchReplayPayloadView | None,
        visible_complete: bool,
        view_state: MatchViewStateView,
    ) -> list[MatchViewerReactionCardView]:
        cards: list[MatchViewerReactionCardView] = []
        if replay_payload is None:
            return cards

        if replay_payload.broadcast_session is not None:
            headline_intro = self._string(replay_payload.broadcast_session.headline_intro)
            if headline_intro is not None:
                cards.append(
                    MatchViewerReactionCardView(
                        source="Match Desk",
                        headline="Headline intro",
                        detail=headline_intro,
                        tag="desk",
                    )
                )

        if not visible_complete:
            for identity in replay_payload.club_identities[:2]:
                philosophy = self._string(identity.philosophy) or "identity profile"
                cards.append(
                    MatchViewerReactionCardView(
                        source="Staff Desk",
                        headline=f"{identity.club_id} identity",
                        detail=f"{philosophy.title()} football. Culture {round(identity.culture_score)} and brand {round(identity.brand_strength)}.",
                        tag="identity",
                    )
                )
            return cards[:6]

        for reaction in replay_payload.fan_reactions:
            for event in reaction.events:
                cards.append(
                    MatchViewerReactionCardView(
                        source="Fans",
                        headline=event.title,
                        detail=f"{reaction.club_name}: {event.description}",
                        sentiment=reaction.sentiment,
                        tag=event.event_type,
                    )
                )
        for event in replay_payload.media_events:
            cards.append(
                MatchViewerReactionCardView(
                    source="Press",
                    headline=event.type.replace("_", " ").title(),
                    detail=event.content,
                    tag=event.type,
                )
            )
        for notification in replay_payload.notifications:
            cards.append(
                MatchViewerReactionCardView(
                    source="Alerts",
                    headline=notification.title,
                    detail=notification.message,
                    sentiment=notification.severity,
                    tag=notification.notification_type,
                )
            )
        if not cards:
            cards.append(
                MatchViewerReactionCardView(
                    source="Match Desk",
                    headline="Live contract only",
                    detail=f"{view_state.home_team.team_name} and {view_state.away_team.team_name} are on air, but the reaction feed is not present on this session payload.",
                    tag="reduced",
                )
            )
        return cards

    def _storylines(
        self,
        *,
        metadata: dict[str, object],
        replay_payload: MatchReplayPayloadView | None,
    ) -> list[str]:
        lines: list[str] = []
        if replay_payload is not None and replay_payload.broadcast_session is not None:
            headline_intro = self._string(replay_payload.broadcast_session.headline_intro)
            if headline_intro is not None:
                lines.append(headline_intro)
        if replay_payload is not None:
            lines.extend(self._non_empty_lines(replay_payload.summary.key_matchups))
            lines.extend(self._non_empty_lines(replay_payload.summary.tactical_impact_notes))
            lines.extend(self._non_empty_lines([replay_payload.summary.home_advantage_note]))
            lines.extend(self._non_empty_lines([replay_payload.summary.form_motivation_summary]))
        lines.extend(self._non_empty_lines(metadata.get("storylines")))
        lines.extend(self._non_empty_lines(self._nested_list(metadata, "context_board", "storylines")))
        return self._unique_preserve_order(lines)

    def _match_significance(
        self,
        *,
        standings: list[MatchViewerStandingsEntryView],
        competition_stage: str | None,
        replay_payload: MatchReplayPayloadView | None,
        fallback_storyline: str | None,
    ) -> str | None:
        if replay_payload is not None:
            if replay_payload.summary.is_final:
                return "Cup final. The match package is set for a title-deciding night."
            if replay_payload.summary.requires_winner:
                return "Knockout match. A winner is required on the night."
        if standings:
            return "Standings context is available from the current competition feed."
        if competition_stage is not None:
            return f"{competition_stage} fixture presented with live match context."
        return fallback_storyline

    def _standings(self, metadata: dict[str, object]) -> list[MatchViewerStandingsEntryView]:
        sources = [
            metadata.get("standings"),
            metadata.get("standings_summary"),
            self._nested_value(metadata, "competition_context", "standings"),
            self._nested_value(metadata, "competition_context", "table"),
            self._nested_value(metadata, "context_board", "standings"),
        ]
        for source in sources:
            if not isinstance(source, list):
                continue
            items: list[MatchViewerStandingsEntryView] = []
            for raw in source:
                if not isinstance(raw, dict):
                    continue
                team_name = (
                    self._string(raw.get("team_name"))
                    or self._string(raw.get("club_name"))
                    or self._string(raw.get("name"))
                )
                if team_name is None:
                    continue
                items.append(
                    MatchViewerStandingsEntryView(
                        team_id=self._string(raw.get("team_id")) or self._string(raw.get("club_id")),
                        team_name=team_name,
                        position=self._int(raw.get("position")) or self._int(raw.get("rank")),
                        played=self._int(raw.get("played")),
                        points=self._int(raw.get("points")),
                        goal_difference=self._int(raw.get("goal_difference")) or self._int(raw.get("gd")),
                        form=self._string(raw.get("form")),
                    )
                )
            if items:
                return items[:8]
        return []

    def _formation_players(
        self,
        starters: list[MatchPlayerVisualView],
        *,
        formation: str,
        rating_lookup: dict[str, float],
    ) -> list[MatchViewerPresentationPlayerView]:
        coordinates = self._formation_coordinates(formation)
        players = list(starters[:11])
        output: list[MatchViewerPresentationPlayerView] = []
        for index, player in enumerate(players):
            x, y, line = coordinates[min(index, len(coordinates) - 1)]
            output.append(
                MatchViewerPresentationPlayerView(
                    player_id=player.player_id,
                    player_name=player.display_name,
                    shirt_number=player.shirt_number,
                    role=getattr(player.role, "value", str(player.role)),
                    line=line,
                    x=x,
                    y=y,
                    rating=rating_lookup.get(player.player_id),
                )
            )
        return output

    def _fallback_formation_players(
        self,
        players: list[dict[str, object]],
        *,
        formation: str,
    ) -> list[MatchViewerPresentationPlayerView]:
        coordinates = self._formation_coordinates(formation)
        output: list[MatchViewerPresentationPlayerView] = []
        for index, player in enumerate(players[:11]):
            x, y, line = coordinates[min(index, len(coordinates) - 1)]
            output.append(
                MatchViewerPresentationPlayerView(
                    player_id=self._string(player.get("player_id")),
                    player_name=self._string(player.get("player_name")) or "?",
                    shirt_number=self._int(player.get("shirt_number")),
                    role=self._string(player.get("role")),
                    line=line,
                    x=x,
                    y=y,
                )
            )
        return output

    def _presentation_player(
        self,
        player: MatchPlayerVisualView,
        *,
        rating_lookup: dict[str, float],
    ) -> MatchViewerPresentationPlayerView:
        return MatchViewerPresentationPlayerView(
            player_id=player.player_id,
            player_name=player.display_name,
            shirt_number=player.shirt_number,
            role=getattr(player.role, "value", str(player.role)),
            line=None,
            rating=rating_lookup.get(player.player_id),
        )

    def _formation_coordinates(self, formation: str) -> list[tuple[float, float, str]]:
        chunks = self._parse_formation(formation)
        coordinates: list[tuple[float, float, str]] = [(90.0, 50.0, "goalkeeper")]
        line_labels = self._formation_line_labels(len(chunks))
        for depth, count in enumerate(chunks, start=1):
            x = _LINE_X_BY_DEPTH.get(depth, max(14.0, 76.0 - ((depth - 1) * 16.0)))
            y_positions = _LINE_Y_MAP.get(count)
            if y_positions is None:
                y_positions = tuple(
                    round((100.0 / (count + 1)) * (index + 1), 1)
                    for index in range(count)
                )
            line = line_labels[min(depth - 1, len(line_labels) - 1)]
            for y in y_positions:
                coordinates.append((x, y, line))
        return coordinates

    def _formation_line_labels(self, count: int) -> list[str]:
        if count <= 1:
            return ["attack"]
        if count == 2:
            return ["midfield", "attack"]
        if count == 3:
            return ["defense", "midfield", "attack"]
        return ["defense", "midfield", "midfield", "attack"]

    def _fallback_players(
        self,
        view_state: MatchViewStateView,
        *,
        side: str,
    ) -> list[dict[str, object]]:
        if not view_state.frames:
            return []
        target_side = view_state.home_team.side if side == "home" else view_state.away_team.side
        players = [player for player in view_state.frames[0].players if player.side == target_side]
        players.sort(
            key=lambda item: (
                self._line_rank(item.line),
                item.position.x,
                item.position.y,
            )
        )
        return [
            {
                "player_id": player.player_id,
                "player_name": player.label,
                "shirt_number": player.shirt_number,
                "role": getattr(player.role, "value", str(player.role)),
            }
            for player in players
        ]

    def _line_rank(self, line: object) -> int:
        normalized = str(getattr(line, "value", line or "")).strip().lower()
        return {
            "goalkeeper": 0,
            "defense": 1,
            "midfield": 2,
            "attack": 3,
        }.get(normalized, 9)

    def _coach_name(self, metadata: dict[str, object], *, side: str) -> str | None:
        direct = (
            self._string(metadata.get(f"{side}_coach_name"))
            or self._string(metadata.get(f"{side}_manager_name"))
        )
        if direct is not None:
            return direct
        nested_manager = self._nested_string(metadata, f"{side}_manager", "name")
        if nested_manager is not None:
            return nested_manager
        return self._nested_string(metadata, "replay_request", f"{side}_team", "manager_profile", "name")

    def _team_mentality(self, metadata: dict[str, object], *, side: str) -> str | None:
        return (
            self._nested_string(metadata, "replay_request", f"{side}_team", "tactics", "mentality")
            or self._nested_string(metadata, "replay_request", f"{side}_team", "tactics", "style")
            or self._nested_string(metadata, f"{side}_tactics", "mentality")
        )

    def _instruction_summary(self, metadata: dict[str, object], *, side: str) -> list[str]:
        instructions: list[str] = []
        tactics = self._nested_dict(metadata, "replay_request", f"{side}_team", "tactics")
        if not tactics:
            tactics = self._nested_dict(metadata, f"{side}_tactics")
        if not tactics:
            return instructions
        for key in ("pressing", "tempo", "width", "defensive_line", "set_piece_emphasis"):
            value = tactics.get(key)
            if isinstance(value, (int, float)):
                instructions.append(f"{key.replace('_', ' ').title()} {round(float(value))}")
        return instructions[:4]

    def _rating_lookup(self, replay_payload: MatchReplayPayloadView | None) -> dict[str, float]:
        if replay_payload is None:
            return {}
        return {
            item.player_id: item.rating
            for item in replay_payload.summary.player_stats
            if item.rating is not None
        }

    def _rating_leaders(
        self,
        replay_payload: MatchReplayPayloadView | None,
    ) -> list[MatchViewerPresentationPlayerView]:
        if replay_payload is None:
            return []
        player_stats = [
            item
            for item in replay_payload.summary.player_stats
            if item.rating is not None
        ]
        player_stats.sort(key=lambda item: item.rating or 0.0, reverse=True)
        return [
            MatchViewerPresentationPlayerView(
                player_id=item.player_id,
                player_name=item.player_name,
                shirt_number=None,
                role=getattr(item.role, "value", str(item.role)),
                line=None,
                rating=item.rating,
            )
            for item in player_stats[:8]
        ]

    def _momentum_notes(self, replay_payload: MatchReplayPayloadView | None) -> list[str]:
        if replay_payload is None:
            return []
        return self._unique_preserve_order(
            self._non_empty_lines(replay_payload.summary.momentum_swings)
            + self._non_empty_lines(replay_payload.summary.turning_points)
            + self._non_empty_lines(replay_payload.summary.key_highlights)
        )[:6]

    def _coach_notes(self, replay_payload: MatchReplayPayloadView | None) -> list[str]:
        if replay_payload is None:
            return []
        return self._unique_preserve_order(
            self._non_empty_lines(replay_payload.summary.manager_influence_notes)
            + self._non_empty_lines(replay_payload.summary.tactical_impact_notes)
        )[:6]

    def _commentary_highlights(self, replay_payload: MatchReplayPayloadView | None) -> list[str]:
        if replay_payload is None or replay_payload.broadcast_session is None:
            return []
        lines: list[str] = []
        for item in replay_payload.broadcast_session.dual_commentary[:6]:
            if item.play_by_play.strip():
                lines.append(item.play_by_play.strip())
            if item.analyst.strip():
                lines.append(item.analyst.strip())
        return self._unique_preserve_order(lines)[:6]

    def _replay_payload(self, metadata: dict[str, object]) -> MatchReplayPayloadView | None:
        raw = metadata.get("replay_payload")
        if not isinstance(raw, dict):
            return None
        try:
            return MatchReplayPayloadView.model_validate(raw)
        except Exception:
            return None

    def _is_visible_fulltime(self, view_state: MatchViewStateView) -> bool:
        if any(event.event_type.name.lower() == "fulltime" for event in view_state.events):
            return True
        if view_state.frames and view_state.frames[-1].phase.name.lower() == "fulltime":
            return True
        return False

    def _parse_formation(self, formation: str | None) -> list[int]:
        text = self._string(formation) or "4-3-3"
        try:
            values = [int(chunk) for chunk in text.split("-")]
        except ValueError:
            return [4, 3, 3]
        if not values or sum(values) not in {9, 10}:
            return [4, 3, 3]
        return values

    def _kickoff_label(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.strftime("%H:%M UTC")

    def _date_label(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.strftime("%d %b %Y")

    def _safe_percent(self, value: float | int | None) -> int | None:
        if value is None:
            return None
        return max(0, min(100, round(float(value))))

    def _datetime(self, value: object | None) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _string(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _int(self, value: object | None) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return round(value)
        try:
            return int(str(value).strip())
        except ValueError:
            return None

    def _nested_value(self, value: dict[str, object], *path: str) -> object | None:
        current: object | None = value
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    def _nested_dict(self, value: dict[str, object], *path: str) -> dict[str, object]:
        resolved = self._nested_value(value, *path)
        return resolved if isinstance(resolved, dict) else {}

    def _nested_list(self, value: dict[str, object], *path: str) -> list[object]:
        resolved = self._nested_value(value, *path)
        return resolved if isinstance(resolved, list) else []

    def _nested_string(self, value: dict[str, object], *path: str) -> str | None:
        return self._string(self._nested_value(value, *path))

    def _non_empty_lines(self, values: object) -> list[str]:
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            return []
        output: list[str] = []
        for item in values:
            text = self._string(item)
            if text is not None:
                output.append(text)
        return output

    def _unique_preserve_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        output: list[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            output.append(normalized)
        return output
