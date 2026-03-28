from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.broadcast_rights.service import BroadcastRightsService
from app.football_universe.schemas import (
    BroadcastCommentatorView,
    BroadcastFulltimeWrapView,
    BroadcastHalftimeSegmentView,
    BroadcastOverlayView,
    BroadcastPlayerSpotlightView,
    BroadcastScoreboardView,
    BroadcastSessionView,
    ClubIdentityView,
    DualCommentaryLineView,
    FanBaseView,
    FanEventView,
    FanReactionView,
    FootballUniverseNotificationView,
    MediaEventView,
)
from app.ingestion.models import Player
from app.match_engine.schemas import MatchReplayPayloadView, MatchSimulationRequest
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.competitive_integrity import Manager as CompetitiveManager
from app.models.competitive_integrity import Match as CompetitiveMatch
from app.models.football_universe import (
    BroadcastSession,
    ClubIdentity,
    ClubPhilosophy,
    FanBase,
    FanSentiment,
    MediaEvent,
    MediaEventType,
)
from app.models.manager_duel import ManagerDuel
from app.models.manager_marketplace import ManagerProfile
from app.models.notification_record import NotificationRecord
from app.models.player_agency_state import PlayerAgencyState


def _clamp_float(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _club_exists_map(session: Session, club_ids: list[str]) -> dict[str, ClubProfile]:
    if not club_ids:
        return {}
    rows = session.scalars(select(ClubProfile).where(ClubProfile.id.in_(club_ids))).all()
    return {row.id: row for row in rows}


@dataclass(frozen=True, slots=True)
class FootballUniverseBundle:
    broadcast_session: BroadcastSessionView
    fan_reactions: list[FanReactionView]
    club_identities: list[ClubIdentityView]
    media_events: list[MediaEventView]
    notifications: list[FootballUniverseNotificationView]


@dataclass(slots=True)
class FootballUniverseBuilder:
    play_by_play_names: tuple[str, ...] = (
        "Marcus Vale",
        "Jonah Kade",
        "Amina Cole",
        "Esi Grant",
    )
    analyst_names: tuple[str, ...] = (
        "Tara Mendes",
        "Leo Bassey",
        "Nadia Costa",
        "Ruth Salazar",
    )

    def build(self, *, request: MatchSimulationRequest, replay_payload: MatchReplayPayloadView) -> FootballUniverseBundle:
        player_inputs = {
            player.player_id: player
            for player in [
                *request.home_team.starters,
                *request.home_team.bench,
                *request.away_team.starters,
                *request.away_team.bench,
            ]
        }
        identities = {
            request.home_team.team_id: self._build_identity(team=request.home_team, player_inputs=player_inputs),
            request.away_team.team_id: self._build_identity(team=request.away_team, player_inputs=player_inputs),
        }
        fan_reactions = [
            self._build_fan_reaction(
                team=request.home_team,
                opponent=request.away_team,
                replay_payload=replay_payload,
                identity=identities[request.home_team.team_id],
            ),
            self._build_fan_reaction(
                team=request.away_team,
                opponent=request.home_team,
                replay_payload=replay_payload,
                identity=identities[request.away_team.team_id],
            ),
        ]
        media_events = self._build_media_events(
            request=request,
            replay_payload=replay_payload,
            fan_reactions=fan_reactions,
            identities=identities,
            player_inputs=player_inputs,
        )
        broadcast_session = self._build_broadcast_session(
            request=request,
            replay_payload=replay_payload,
            media_events=media_events,
            player_inputs=player_inputs,
        )
        notifications = self._build_notifications(
            replay_payload=replay_payload,
            fan_reactions=fan_reactions,
            media_events=media_events,
        )
        return FootballUniverseBundle(
            broadcast_session=broadcast_session,
            fan_reactions=fan_reactions,
            club_identities=list(identities.values()),
            media_events=media_events,
            notifications=notifications,
        )

    def _build_broadcast_session(
        self,
        *,
        request: MatchSimulationRequest,
        replay_payload: MatchReplayPayloadView,
        media_events: list[MediaEventView],
        player_inputs: dict[str, Any],
    ) -> BroadcastSessionView:
        commentators = self._commentators(replay_payload.match_id)
        player_of_match = self._player_of_match(replay_payload=replay_payload, player_inputs=player_inputs)
        halftime_analysis = None
        if replay_payload.halftime_analytics is not None:
            halftime_analysis = BroadcastHalftimeSegmentView(
                key_stats=list(replay_payload.halftime_analytics.key_stats),
                tactical_insights=list(replay_payload.halftime_analytics.tactical_insights),
                standout_players=[
                    BroadcastPlayerSpotlightView(
                        player_id=item.player_id,
                        player_name=item.player_name,
                        team_id=item.team_id,
                        team_name=item.team_name,
                        rating=item.rating,
                        headline=item.summary or f"{item.player_name} has driven the first-half story.",
                    )
                    for item in replay_payload.halftime_analytics.standout_players
                ],
            )
        headline = next((item.content for item in media_events if item.type == MediaEventType.HEADLINE.value), None)
        overlay_state = BroadcastOverlayView(
            scoreboard=BroadcastScoreboardView(
                home_team_name=replay_payload.summary.home_stats.team_name,
                away_team_name=replay_payload.summary.away_stats.team_name,
                home_score=replay_payload.summary.home_score,
                away_score=replay_payload.summary.away_score,
                minute=90 if replay_payload.summary.status.value == "completed" else 45,
                status=replay_payload.summary.status.value,
            ),
            team_names={
                "home": replay_payload.summary.home_stats.team_name,
                "away": replay_payload.summary.away_stats.team_name,
            },
            possession_indicator={
                "home": replay_payload.summary.home_stats.possession,
                "away": replay_payload.summary.away_stats.possession,
                "leader": (
                    "home"
                    if replay_payload.summary.home_stats.possession >= replay_payload.summary.away_stats.possession
                    else "away"
                ),
            },
            player_highlight_card=player_of_match,
            stadium_ads=[],
            sponsored_overlays=[],
            advanced_stats_enabled=False,
        )
        return BroadcastSessionView(
            match_id=replay_payload.match_id,
            commentators=commentators,
            overlay_state=overlay_state,
            headline_intro=(
                f"Coming into this match, all eyes are on {headline}"
                if headline is not None
                else f"Coming into this match, all eyes are on the tactical duel between {request.home_team.team_name} and {request.away_team.team_name}."
            ),
            dual_commentary=[
                DualCommentaryLineView(
                    event_id=event.event_id,
                    minute=event.minute,
                    event_type=event.event_type.value,
                    play_by_play=event.commentary,
                    analyst=event.analyst_commentary or "The structure of the move mattered as much as the finish.",
                )
                for event in replay_payload.timeline.events
            ],
            halftime_analysis=halftime_analysis,
            fulltime_wrap=BroadcastFulltimeWrapView(
                summary_narrative=replay_payload.summary.summary_line,
                key_moments_recap=list(replay_payload.summary.key_highlights[:4]),
                player_of_the_match=player_of_match,
            ),
            rights_owner_id=None,
            premium_features={},
            created_at=None,
        )

    def _build_identity(self, *, team, player_inputs: dict[str, Any]) -> ClubIdentityView:
        identity = team.identity
        context = team.club_context
        philosophy = getattr(identity, "philosophy", None) or self._infer_philosophy(team)
        culture_score = float(getattr(identity, "culture_score", None) or getattr(context, "culture_score", 55))
        tactical_consistency = float(
            getattr(identity, "tactical_consistency", None)
            or (team.tactics.tactical_quality * 0.55) + (team.tactics.adaptability * 0.25) + 14.0
        )
        brand_strength = float(getattr(identity, "brand_strength", None) or getattr(context, "brand_strength", 50))
        squad_fit = [
            float(getattr(player_inputs[player.player_id], "identity_fit_score", 68) or 68)
            for player in team.starters
            if player.player_id in player_inputs
        ]
        average_fit = mean(squad_fit) if squad_fit else 68.0
        chemistry_bonus = round(max(0.0, culture_score - 60.0) * 0.12, 2)
        development_bonus = round(
            max(0.0, culture_score - 58.0) * 0.08
            + (1.8 if philosophy == ClubPhilosophy.YOUTH_DEVELOPMENT.value else 0.0),
            2,
        )
        return ClubIdentityView(
            club_id=team.team_id,
            philosophy=str(philosophy),
            culture_score=round(_clamp_float(culture_score), 2),
            tactical_consistency=round(_clamp_float(tactical_consistency), 2),
            brand_strength=round(_clamp_float(brand_strength), 2),
            chemistry_bonus=chemistry_bonus,
            player_development_bonus=development_bonus,
            average_identity_fit=round(_clamp_float(average_fit), 2),
            metadata={
                "team_name": team.team_name,
                "style": team.tactics.style.value,
                "pressing": team.tactics.pressing,
                "tempo": team.tactics.tempo,
            },
        )

    def _build_fan_reaction(
        self,
        *,
        team,
        opponent,
        replay_payload: MatchReplayPayloadView,
        identity: ClubIdentityView,
    ) -> FanReactionView:
        expectation_score = float(getattr(team.club_context, "expectation_level", 55))
        fan_pressure = float(getattr(team.club_context, "fan_pressure", 48))
        media_pressure = float(getattr(team.club_context, "media_pressure", 45))
        rivalry_pressure = max(
            float(getattr(team.club_context, "rivalry_intensity", 0)),
            float(getattr(opponent.club_context, "rivalry_intensity", 0)),
        )
        pressure_score = _clamp_float(
            (expectation_score * 0.42)
            + (fan_pressure * 0.33)
            + (media_pressure * 0.25)
            + (rivalry_pressure * 0.18)
        )
        won = replay_payload.summary.winner_team_id == team.team_id
        drawn = replay_payload.summary.winner_team_id is None
        is_favorite = (
            replay_payload.summary.home_stats.strength.overall >= replay_payload.summary.away_stats.strength.overall + 2.0
            if team.team_id == replay_payload.summary.home_stats.team_id
            else replay_payload.summary.away_stats.strength.overall >= replay_payload.summary.home_stats.strength.overall + 2.0
        )
        upset_loss = (not won and not drawn) and is_favorite and replay_payload.summary.upset
        sentiment = (
            FanSentiment.HAPPY.value
            if won
            else FanSentiment.NEUTRAL.value
            if drawn
            else FanSentiment.VERY_NEGATIVE.value
            if upset_loss
            else FanSentiment.NEGATIVE.value
        )
        morale_delta = 4.0 if won else 1.0 if drawn else -7.0 if upset_loss else -4.0
        manager_reputation_delta = 3.0 if won else 0.5 if drawn else -5.0 if upset_loss else -2.0
        if expectation_score >= 70 and not won and not drawn:
            morale_delta -= round((expectation_score - 65.0) * 0.12, 2)
            manager_reputation_delta -= round((expectation_score - 65.0) * 0.08, 2)
        star_power = sum(
            1
            for player in replay_payload.summary.player_stats
            if player.team_id == team.team_id and ((player.rating or 0.0) >= 8.0 or player.goals >= 1)
        )
        fan_count_delta = 0
        if won:
            fan_count_delta += 180 + (star_power * 90)
            if replay_payload.summary.is_final:
                fan_count_delta += 1400
        elif drawn:
            fan_count_delta += 40 if is_favorite else 70
        else:
            fan_count_delta -= 110 + (160 if upset_loss else 0)
            if replay_payload.summary.is_final:
                fan_count_delta -= 280
        fan_events: list[FanEventView] = []
        if won and replay_payload.summary.is_final:
            fan_events.append(
                FanEventView(
                    event_type="celebration",
                    title="Citywide Celebration",
                    description=f"{team.team_name} supporters are in full celebration mode after the silverware moment.",
                    intensity=5,
                )
            )
        elif won and replay_payload.summary.home_score != replay_payload.summary.away_score:
            fan_events.append(
                FanEventView(
                    event_type="hype_wave",
                    title="Hype Wave",
                    description=f"The result has triggered a fresh hype wave around {team.team_name}.",
                    intensity=3,
                )
            )
        elif drawn and (rivalry_pressure >= 70 or replay_payload.summary.home_score + replay_payload.summary.away_score >= 2):
            fan_events.append(
                FanEventView(
                    event_type="debate",
                    title="Post-Match Debate",
                    description=(
                        f"{team.team_name} supporters are split after a tense draw that still carried rivalry energy."
                    ),
                    intensity=3 if rivalry_pressure < 85 else 4,
                )
            )
        elif upset_loss or (expectation_score >= 70 and not won and not drawn):
            fan_events.append(
                FanEventView(
                    event_type="protest",
                    title="Supporter Protest",
                    description=f"Sections of the {team.team_name} support are turning on the team after the result.",
                    intensity=4 if upset_loss else 3,
                )
            )
        return FanReactionView(
            club_id=team.team_id,
            club_name=team.team_name,
            sentiment=sentiment,
            expectation_level=self._expectation_bucket(expectation_score),
            morale_delta=round(morale_delta, 2),
            manager_reputation_delta=round(manager_reputation_delta, 2),
            fan_count_delta=int(fan_count_delta),
            pressure_score=round(pressure_score, 2),
            events=fan_events,
        )

    def _build_media_events(
        self,
        *,
        request: MatchSimulationRequest,
        replay_payload: MatchReplayPayloadView,
        fan_reactions: list[FanReactionView],
        identities: dict[str, ClubIdentityView],
        player_inputs: dict[str, Any],
    ) -> list[MediaEventView]:
        reaction_by_team = {item.club_id: item for item in fan_reactions}
        rivalry_level = max(
            float(getattr(request.home_team.club_context, "rivalry_intensity", 0)),
            float(getattr(request.away_team.club_context, "rivalry_intensity", 0)),
        )
        coverage_multiplier = round(
            1.0 + (rivalry_level / 100.0 * 0.85) + (0.35 if replay_payload.summary.is_final else 0.0),
            2,
        )
        headline = self.generate_headline(request=request, replay_payload=replay_payload)
        home_reaction = reaction_by_team[request.home_team.team_id]
        away_reaction = reaction_by_team[request.away_team.team_id]
        events = [
            MediaEventView(
                type=MediaEventType.HEADLINE.value,
                content=headline,
                match_id=replay_payload.match_id,
                impact={
                    "tone": "positive" if replay_payload.summary.winner_team_id is not None else "mixed",
                    "coverage_multiplier": coverage_multiplier,
                    "pressure_multiplier": coverage_multiplier + (0.25 if replay_payload.summary.upset else 0.0),
                },
            )
        ]
        for team, reaction in ((request.home_team, home_reaction), (request.away_team, away_reaction)):
            tone = "confident" if reaction.sentiment == FanSentiment.HAPPY.value else "aggressive" if reaction.sentiment == FanSentiment.VERY_NEGATIVE.value else "defensive"
            events.append(
                MediaEventView(
                    type=MediaEventType.INTERVIEW.value,
                    content=self._interview_quote(team_name=team.team_name, tone=tone, replay_payload=replay_payload),
                    match_id=replay_payload.match_id,
                    club_id=team.team_id,
                    impact={
                        "tone": tone,
                        "fan_sentiment_shift": 2.0 if tone == "confident" else -1.5 if tone == "aggressive" else -0.5,
                        "morale_delta": 1.5 if tone == "confident" else -1.0 if tone == "defensive" else -2.0,
                    },
                )
            )
        if any(event.event_type.value == "red_card" for event in replay_payload.timeline.events) or replay_payload.summary.upset:
            losing_team = (
                request.away_team
                if replay_payload.summary.winner_team_id == request.home_team.team_id
                else request.home_team
            )
            events.append(
                MediaEventView(
                    type=MediaEventType.CONTROVERSY.value,
                    content=(
                        f"Pressure rises around {losing_team.team_name} after the fallout from a heated night."
                        if replay_payload.summary.upset
                        else f"Refereeing and discipline become the talking point after {losing_team.team_name}'s collapse."
                    ),
                    match_id=replay_payload.match_id,
                    club_id=losing_team.team_id,
                    impact={
                        "tone": "negative",
                        "morale_delta": -2.5,
                        "manager_reputation_delta": -2.0,
                        "pressure_multiplier": coverage_multiplier + 0.35,
                    },
                )
            )
        rumor_player = self._rumor_player(replay_payload=replay_payload, player_inputs=player_inputs)
        if rumor_player is not None:
            events.append(
                MediaEventView(
                    type=MediaEventType.TRANSFER_NEWS.value,
                    content=f"Rumors gather around {rumor_player.player_name} after another high-pressure night.",
                    match_id=replay_payload.match_id,
                    club_id=rumor_player.team_id,
                    impact={
                        "tone": "speculative",
                        "morale_delta": -1.2,
                        "fan_sentiment_shift": -1.0,
                    },
                )
            )
        for event in events:
            if event.club_id is None and event.type == MediaEventType.HEADLINE.value:
                event.impact["featured_clubs"] = [request.home_team.team_id, request.away_team.team_id]
                event.impact["identity_profiles"] = {key: value.philosophy for key, value in identities.items()}
        return events

    def _build_notifications(
        self,
        *,
        replay_payload: MatchReplayPayloadView,
        fan_reactions: list[FanReactionView],
        media_events: list[MediaEventView],
    ) -> list[FootballUniverseNotificationView]:
        notifications: list[FootballUniverseNotificationView] = []
        for reaction in fan_reactions:
            notifications.append(
                FootballUniverseNotificationView(
                    notification_type="FAN_REACTION",
                    title=f"{reaction.club_name} fan mood: {reaction.sentiment.replace('_', ' ')}",
                    message=f"Supporter pressure is now {reaction.pressure_score:.0f}/100 for {reaction.club_name}.",
                    severity="warning" if reaction.sentiment in {FanSentiment.NEGATIVE.value, FanSentiment.VERY_NEGATIVE.value} else "info",
                    club_id=reaction.club_id,
                    match_id=replay_payload.match_id,
                    metadata=reaction.model_dump(mode="json"),
                )
            )
            if reaction.pressure_score >= 72 or reaction.sentiment == FanSentiment.VERY_NEGATIVE.value:
                notifications.append(
                    FootballUniverseNotificationView(
                        notification_type="PRESSURE_ALERT",
                        title=f"Pressure alert for {reaction.club_name}",
                        message="High expectation and supporter anger are now affecting morale and managerial standing.",
                        severity="critical" if reaction.sentiment == FanSentiment.VERY_NEGATIVE.value else "warning",
                        club_id=reaction.club_id,
                        match_id=replay_payload.match_id,
                        metadata={"pressure_score": reaction.pressure_score},
                    )
                )
        for event in media_events:
            if event.type == MediaEventType.HEADLINE.value:
                notifications.append(
                    FootballUniverseNotificationView(
                        notification_type="MEDIA_HEADLINE",
                        title="Media headline generated",
                        message=event.content,
                        severity="info",
                        club_id=event.club_id,
                        match_id=event.match_id,
                        metadata=event.impact,
                    )
                )
            if event.type == MediaEventType.INTERVIEW.value:
                notifications.append(
                    FootballUniverseNotificationView(
                        notification_type="INTERVIEW_AVAILABLE",
                        title="Post-match interview available",
                        message=event.content,
                        severity="info",
                        club_id=event.club_id,
                        match_id=event.match_id,
                        metadata=event.impact,
                    )
                )
        return notifications

    def _player_of_match(
        self,
        *,
        replay_payload: MatchReplayPayloadView,
        player_inputs: dict[str, Any],
    ) -> BroadcastPlayerSpotlightView | None:
        if not replay_payload.summary.player_stats:
            return None
        ranked = sorted(
            replay_payload.summary.player_stats,
            key=lambda item: (
                item.rating or 0.0,
                item.goals,
                item.assists,
                item.key_passes,
                item.saves,
            ),
            reverse=True,
        )
        pick = ranked[0]
        identity_fit = float(getattr(player_inputs.get(pick.player_id), "identity_fit_score", 68) or 68)
        return BroadcastPlayerSpotlightView(
            player_id=pick.player_id,
            player_name=pick.player_name,
            team_id=pick.team_id,
            team_name=pick.team_name,
            rating=pick.rating,
            headline=pick.rating_summary or f"{pick.player_name} shaped the decisive moments.",
            identity_fit_score=round(identity_fit, 2),
        )

    def _rumor_player(
        self,
        *,
        replay_payload: MatchReplayPayloadView,
        player_inputs: dict[str, Any],
    ) -> BroadcastPlayerSpotlightView | None:
        candidates = [
            stat
            for stat in replay_payload.summary.player_stats
            if (stat.rating or 0.0) >= 7.5 or stat.goals >= 1
        ]
        if not candidates:
            return None
        pick = max(
            candidates,
            key=lambda item: (
                item.rating or 0.0,
                item.goals,
                100.0 - float(getattr(player_inputs.get(item.player_id), "identity_fit_score", 68) or 68),
            ),
        )
        return BroadcastPlayerSpotlightView(
            player_id=pick.player_id,
            player_name=pick.player_name,
            team_id=pick.team_id,
            team_name=pick.team_name,
            rating=pick.rating,
            headline=f"{pick.player_name} is becoming the center of the next rumor cycle.",
            identity_fit_score=float(getattr(player_inputs.get(pick.player_id), "identity_fit_score", 68) or 68),
        )

    def _commentators(self, match_id: str) -> list[BroadcastCommentatorView]:
        seed = sum(ord(char) for char in match_id)
        play_by_play = self.play_by_play_names[seed % len(self.play_by_play_names)]
        analyst = self.analyst_names[(seed // 3) % len(self.analyst_names)]
        return [
            BroadcastCommentatorView(name=play_by_play, role="play_by_play", style="urgent"),
            BroadcastCommentatorView(name=analyst, role="analyst", style="tactical"),
        ]

    def generate_headline(self, *, request: MatchSimulationRequest, replay_payload: MatchReplayPayloadView) -> str:
        late_winner = any(
            event.event_type.value in {"goal", "penalty_scored"} and event.minute >= 85
            for event in replay_payload.timeline.events
        )
        if replay_payload.summary.upset:
            favorite_name = (
                request.home_team.team_name
                if replay_payload.summary.winner_team_id == request.away_team.team_id
                else request.away_team.team_name
            )
            return f"Underdogs Shock {favorite_name}!"
        if late_winner and replay_payload.summary.winner_team_name is not None:
            return f"Late Drama Seals Victory For {replay_payload.summary.winner_team_name}!"
        if replay_payload.summary.winner_team_name is None:
            return "Spoils Shared After a Tactical Standoff!"
        losing_team = (
            request.away_team.team_name
            if replay_payload.summary.winner_team_id == request.home_team.team_id
            else request.home_team.team_name
        )
        if replay_payload.summary.turning_points:
            return f"Manager Under Pressure After {losing_team} Defeat!"
        return f"{replay_payload.summary.winner_team_name} Control the Night!"

    def _infer_philosophy(self, team) -> str:
        manager_tactics = {str(item).strip().lower() for item in ((team.manager_profile or {}).get("tactics") or [])}
        manager_traits = {str(item).strip().lower() for item in ((team.manager_profile or {}).get("traits") or [])}
        if {"develops_young_players", "academy_promotion_bias", "uses young players"} & manager_traits:
            return ClubPhilosophy.YOUTH_DEVELOPMENT.value
        if {"counter_attack", "low_block_counter"} & manager_tactics:
            return ClubPhilosophy.COUNTER_ATTACK.value
        if {"tiki_taka", "possession_control", "technical_build_up"} & manager_tactics:
            return ClubPhilosophy.POSSESSION.value
        if team.tactics.style.value == "attacking":
            return ClubPhilosophy.ATTACKING.value
        if team.tactics.style.value == "defensive":
            return ClubPhilosophy.DEFENSIVE.value
        return ClubPhilosophy.POSSESSION.value

    def _interview_quote(self, *, team_name: str, tone: str, replay_payload: MatchReplayPayloadView) -> str:
        if tone == "confident":
            return f"{team_name} manager: We trusted the plan, stayed brave, and earned the right to control the closing moments."
        if tone == "aggressive":
            return f"{team_name} manager: Too much noise surrounds this club right now, but the dressing room will answer on the pitch."
        if replay_payload.summary.winner_team_name is None:
            return f"{team_name} manager: We had control in phases, but the final action and final decision were missing."
        return f"{team_name} manager: The pressure is real, but this group has to react faster and manage moments better."

    @staticmethod
    def _expectation_bucket(score: float) -> str:
        if score >= 72:
            return "high"
        if score <= 42:
            return "low"
        return "balanced"


@dataclass(slots=True)
class FootballUniverseService:
    session: Session
    builder: FootballUniverseBuilder = field(default_factory=FootballUniverseBuilder)

    def build_bundle(self, *, request: MatchSimulationRequest, replay_payload: MatchReplayPayloadView) -> FootballUniverseBundle:
        return self.builder.build(request=request, replay_payload=replay_payload)

    def persist_match_universe(
        self,
        *,
        request: MatchSimulationRequest,
        replay_payload: MatchReplayPayloadView,
    ) -> FootballUniverseBundle:
        bundle = self.build_bundle(request=request, replay_payload=replay_payload)
        self._upsert_broadcast_session(bundle.broadcast_session)
        club_ids = [request.home_team.team_id, request.away_team.team_id]
        clubs = _club_exists_map(self.session, club_ids)
        self._persist_identities(bundle.club_identities, clubs=clubs)
        self._persist_fan_reactions(bundle.fan_reactions, request=request, clubs=clubs)
        self._persist_media_events(bundle.media_events, clubs=clubs, request=request)
        self._persist_notifications(bundle.notifications, clubs=clubs)
        self.session.flush()
        return bundle

    def get_broadcast_session(self, match_id: str) -> BroadcastSessionView | None:
        rights_payload = BroadcastRightsService(self.session).get_match_enhancements(match_id=match_id)
        record = self.session.scalar(select(BroadcastSession).where(BroadcastSession.match_id == match_id))
        if record is not None:
            overlay_bundle = dict(record.overlay_state or {})
            overlay_payload = dict(overlay_bundle.get("overlay", {}))
            overlay_payload["stadium_ads"] = list(rights_payload.get("stadium_ads") or [])
            overlay_payload["sponsored_overlays"] = list(rights_payload.get("sponsored_overlays") or [])
            overlay_payload["advanced_stats_enabled"] = bool(
                (rights_payload.get("premium_features") or {}).get("advanced_stats_overlay", False)
            )
            return BroadcastSessionView(
                match_id=record.match_id,
                commentators=[
                    BroadcastCommentatorView.model_validate(item)
                    for item in list((record.commentators or {}).get("commentators", []))
                ],
                overlay_state=BroadcastOverlayView.model_validate(overlay_payload),
                headline_intro=overlay_bundle.get("headline_intro"),
                dual_commentary=[
                    DualCommentaryLineView.model_validate(item)
                    for item in overlay_bundle.get("dual_commentary", [])
                ],
                halftime_analysis=(
                    BroadcastHalftimeSegmentView.model_validate(overlay_bundle["halftime_analysis"])
                    if overlay_bundle.get("halftime_analysis") is not None
                    else None
                ),
                fulltime_wrap=(
                    BroadcastFulltimeWrapView.model_validate(overlay_bundle["fulltime_wrap"])
                    if overlay_bundle.get("fulltime_wrap") is not None
                    else None
                ),
                rights_owner_id=rights_payload.get("rights_owner_id"),
                premium_features=dict(rights_payload.get("premium_features") or {}),
                created_at=record.created_at,
            )
        replay_payload = self._replay_payload_from_fallback(match_id)
        if replay_payload is not None and replay_payload.get("broadcast_session") is not None:
            session_view = BroadcastSessionView.model_validate(replay_payload["broadcast_session"])
            return session_view.model_copy(
                update={
                    "rights_owner_id": rights_payload.get("rights_owner_id"),
                    "premium_features": dict(rights_payload.get("premium_features") or {}),
                    "overlay_state": session_view.overlay_state.model_copy(
                        update={
                            "stadium_ads": list(rights_payload.get("stadium_ads") or []),
                            "sponsored_overlays": list(rights_payload.get("sponsored_overlays") or []),
                            "advanced_stats_enabled": bool(
                                (rights_payload.get("premium_features") or {}).get("advanced_stats_overlay", False)
                            ),
                        }
                    ),
                }
            )
        return None

    def get_fan_base(self, club_id: str) -> FanBaseView | None:
        fan_base = self.session.scalar(select(FanBase).where(FanBase.club_id == club_id))
        if fan_base is None:
            club = self.session.get(ClubProfile, club_id)
            if club is None:
                return None
            fan_base = FanBase(
                club_id=club_id,
                fan_count=22000,
                loyalty_score=54.0,
                expectation_level="balanced",
                sentiment=FanSentiment.NEUTRAL,
                metadata_json={"auto_seeded": True, "club_name": club.club_name},
            )
            self.session.add(fan_base)
            self.session.flush()
        return FanBaseView(
            club_id=fan_base.club_id,
            fan_count=fan_base.fan_count,
            loyalty_score=float(fan_base.loyalty_score),
            expectation_level=fan_base.expectation_level,
            sentiment=fan_base.sentiment.value if isinstance(fan_base.sentiment, FanSentiment) else str(fan_base.sentiment),
            metadata=dict(fan_base.metadata_json or {}),
        )

    def get_club_identity(self, club_id: str) -> ClubIdentityView | None:
        identity = self.session.scalar(select(ClubIdentity).where(ClubIdentity.club_id == club_id))
        if identity is None:
            club = self.session.get(ClubProfile, club_id)
            if club is None:
                return None
            identity = ClubIdentity(
                club_id=club_id,
                philosophy=ClubPhilosophy.POSSESSION,
                culture_score=52.0,
                tactical_consistency=50.0,
                brand_strength=48.0,
                metadata_json={"auto_seeded": True, "club_name": club.club_name},
            )
            self.session.add(identity)
            self.session.flush()
        return ClubIdentityView(
            club_id=identity.club_id,
            philosophy=identity.philosophy.value if isinstance(identity.philosophy, ClubPhilosophy) else str(identity.philosophy),
            culture_score=float(identity.culture_score),
            tactical_consistency=float(identity.tactical_consistency),
            brand_strength=float(identity.brand_strength),
            chemistry_bonus=round(max(0.0, float(identity.culture_score) - 60.0) * 0.12, 2),
            player_development_bonus=round(max(0.0, float(identity.culture_score) - 58.0) * 0.08, 2),
            average_identity_fit=float((identity.metadata_json or {}).get("average_identity_fit", 68.0)),
            metadata=dict(identity.metadata_json or {}),
        )

    def list_media_events(
        self,
        *,
        club_id: str | None = None,
        match_id: str | None = None,
        limit: int = 25,
    ) -> list[MediaEventView]:
        stmt = select(MediaEvent).order_by(MediaEvent.created_at.desc()).limit(limit)
        if club_id is not None:
            stmt = stmt.where(MediaEvent.club_id == club_id)
        if match_id is not None:
            stmt = stmt.where(MediaEvent.match_id == match_id)
        rows = self.session.scalars(stmt).all()
        return [
            MediaEventView(
                id=row.id,
                type=row.type.value if isinstance(row.type, MediaEventType) else str(row.type),
                content=row.content,
                impact=dict(row.impact or {}),
                match_id=row.match_id,
                club_id=row.club_id,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def run_fan_update_cycle(self) -> dict[str, Any]:
        updated = 0
        for fan_base in self.session.scalars(select(FanBase)).all():
            sentiment = fan_base.sentiment.value if isinstance(fan_base.sentiment, FanSentiment) else str(fan_base.sentiment)
            if sentiment == FanSentiment.HAPPY.value:
                fan_base.loyalty_score = _clamp_float(float(fan_base.loyalty_score) + 0.6)
            elif sentiment in {FanSentiment.NEGATIVE.value, FanSentiment.VERY_NEGATIVE.value}:
                fan_base.loyalty_score = _clamp_float(float(fan_base.loyalty_score) - 0.8)
            fan_base.metadata_json = {
                **dict(fan_base.metadata_json or {}),
                "last_fan_update_cycle_at": utcnow().isoformat(),
            }
            updated += 1
        self.session.flush()
        return {"fan_bases_updated": updated}

    def run_media_generation_cycle(self) -> dict[str, Any]:
        generated = 0
        fan_bases = self.session.scalars(select(FanBase)).all()
        clubs = _club_exists_map(self.session, [item.club_id for item in fan_bases])
        for fan_base in fan_bases:
            club = clubs.get(fan_base.club_id)
            if club is None:
                continue
            sentiment = fan_base.sentiment.value if isinstance(fan_base.sentiment, FanSentiment) else str(fan_base.sentiment)
            if sentiment not in {FanSentiment.NEGATIVE.value, FanSentiment.VERY_NEGATIVE.value} and float(fan_base.loyalty_score) < 70:
                continue
            self.session.add(
                MediaEvent(
                    type=MediaEventType.TRANSFER_NEWS,
                    content=f"Fresh rumor cycle builds around {club.club_name} as supporters demand a response.",
                    impact={
                        "tone": "speculative",
                        "generated_by_job": True,
                        "fan_sentiment": sentiment,
                    },
                    club_id=club.id,
                )
            )
            generated += 1
        self.session.flush()
        return {"media_events_generated": generated}

    def run_identity_evolution_cycle(self) -> dict[str, Any]:
        evolved = 0
        for identity in self.session.scalars(select(ClubIdentity)).all():
            consistency = float(identity.tactical_consistency)
            delta = 0.6 if consistency >= 62 else -0.6 if consistency <= 44 else 0.0
            identity.culture_score = _clamp_float(float(identity.culture_score) + delta)
            identity.brand_strength = _clamp_float(float(identity.brand_strength) + (0.3 if consistency >= 62 else -0.2 if consistency <= 44 else 0.0))
            identity.metadata_json = {
                **dict(identity.metadata_json or {}),
                "last_identity_evolution_at": utcnow().isoformat(),
            }
            self._apply_identity_development_bonus(club_id=identity.club_id, identity=self.get_club_identity(identity.club_id))
            evolved += 1
        self.session.flush()
        return {"club_identities_evolved": evolved}

    def _upsert_broadcast_session(self, session_view: BroadcastSessionView) -> BroadcastSession:
        record = self.session.scalar(select(BroadcastSession).where(BroadcastSession.match_id == session_view.match_id))
        if record is None:
            record = BroadcastSession(match_id=session_view.match_id)
            self.session.add(record)
        record.commentators = {"commentators": [item.model_dump(mode="json") for item in session_view.commentators]}
        record.overlay_state = {
            "overlay": session_view.overlay_state.model_dump(mode="json"),
            "headline_intro": session_view.headline_intro,
            "dual_commentary": [item.model_dump(mode="json") for item in session_view.dual_commentary],
            "halftime_analysis": session_view.halftime_analysis.model_dump(mode="json") if session_view.halftime_analysis is not None else None,
            "fulltime_wrap": session_view.fulltime_wrap.model_dump(mode="json") if session_view.fulltime_wrap is not None else None,
            "rights_owner_id": session_view.rights_owner_id,
            "premium_features": dict(session_view.premium_features or {}),
        }
        self.session.flush()
        return record

    def _persist_fan_reactions(
        self,
        reactions: list[FanReactionView],
        *,
        request: MatchSimulationRequest,
        clubs: dict[str, ClubProfile],
    ) -> None:
        manager_profiles = {
            request.home_team.team_id: request.home_team.manager_profile,
            request.away_team.team_id: request.away_team.manager_profile,
        }
        for reaction in reactions:
            club = clubs.get(reaction.club_id)
            if club is None:
                continue
            fan_base = self.session.scalar(select(FanBase).where(FanBase.club_id == reaction.club_id))
            if fan_base is None:
                fan_base = FanBase(
                    club_id=reaction.club_id,
                    fan_count=0,
                    loyalty_score=50.0,
                    expectation_level="balanced",
                    sentiment=FanSentiment.NEUTRAL,
                    metadata_json={},
                )
                self.session.add(fan_base)
            fan_base.fan_count = max(0, int(fan_base.fan_count or 0) + int(reaction.fan_count_delta))
            fan_base.loyalty_score = _clamp_float(
                float(fan_base.loyalty_score or 50.0)
                + (
                    0.9
                    if reaction.sentiment == FanSentiment.HAPPY.value
                    else -1.2
                    if reaction.sentiment == FanSentiment.VERY_NEGATIVE.value
                    else -0.4
                    if reaction.sentiment == FanSentiment.NEGATIVE.value
                    else 0.2
                )
            )
            fan_base.expectation_level = reaction.expectation_level
            fan_base.sentiment = FanSentiment(reaction.sentiment)
            fan_base.metadata_json = {
                **dict(fan_base.metadata_json or {}),
                "club_name": club.club_name,
                "last_reaction": reaction.model_dump(mode="json"),
            }
            self._apply_player_morale_shift(club_id=club.id, delta=reaction.morale_delta, reason="fan_pressure")
            self._apply_manager_reputation_shift(
                manager_context=manager_profiles.get(reaction.club_id),
                delta=reaction.manager_reputation_delta,
            )

    def _persist_identities(self, identities: list[ClubIdentityView], *, clubs: dict[str, ClubProfile]) -> None:
        for identity_view in identities:
            club = clubs.get(identity_view.club_id)
            if club is None:
                continue
            record = self.session.scalar(select(ClubIdentity).where(ClubIdentity.club_id == identity_view.club_id))
            if record is None:
                record = ClubIdentity(
                    club_id=identity_view.club_id,
                    philosophy=ClubPhilosophy.POSSESSION,
                    culture_score=50.0,
                    tactical_consistency=50.0,
                    brand_strength=50.0,
                    metadata_json={},
                )
                self.session.add(record)
            existing_culture = float(record.culture_score or 50.0)
            existing_consistency = float(record.tactical_consistency or 50.0)
            existing_brand_strength = float(record.brand_strength or 50.0)
            consistency = float(identity_view.tactical_consistency)
            evolution = 0.75 if consistency >= 62 else -0.75 if consistency <= 44 else 0.0
            record.philosophy = ClubPhilosophy(identity_view.philosophy)
            record.culture_score = _clamp_float((existing_culture * 0.55) + (identity_view.culture_score * 0.45) + evolution)
            record.tactical_consistency = _clamp_float((existing_consistency * 0.45) + (identity_view.tactical_consistency * 0.55))
            record.brand_strength = _clamp_float((existing_brand_strength * 0.5) + (identity_view.brand_strength * 0.5))
            record.metadata_json = {
                **dict(record.metadata_json or {}),
                "club_name": club.club_name,
                "average_identity_fit": identity_view.average_identity_fit,
                "chemistry_bonus": identity_view.chemistry_bonus,
                "player_development_bonus": identity_view.player_development_bonus,
                "last_identity_update": identity_view.model_dump(mode="json"),
            }
            self._apply_identity_development_bonus(club_id=club.id, identity=identity_view)

    def _persist_media_events(
        self,
        events: list[MediaEventView],
        *,
        clubs: dict[str, ClubProfile],
        request: MatchSimulationRequest,
    ) -> None:
        manager_profiles = {
            request.home_team.team_id: request.home_team.manager_profile,
            request.away_team.team_id: request.away_team.manager_profile,
        }
        for event in events:
            club_id = event.club_id if event.club_id in clubs else None
            row = MediaEvent(
                type=MediaEventType(event.type),
                content=event.content,
                impact=event.impact,
                match_id=event.match_id,
                club_id=club_id,
            )
            self.session.add(row)
            morale_delta = float(event.impact.get("morale_delta", 0.0) or 0.0)
            if club_id is not None and morale_delta:
                self._apply_player_morale_shift(club_id=club_id, delta=morale_delta, reason="media_tone")
            manager_delta = float(event.impact.get("manager_reputation_delta", 0.0) or 0.0)
            if club_id is not None and manager_delta:
                self._apply_manager_reputation_shift(manager_context=manager_profiles.get(club_id), delta=manager_delta)

    def _persist_notifications(
        self,
        notifications: list[FootballUniverseNotificationView],
        *,
        clubs: dict[str, ClubProfile],
    ) -> None:
        for item in notifications:
            club = clubs.get(item.club_id) if item.club_id is not None else None
            user_id = club.owner_user_id if club is not None else None
            self.session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic=item.notification_type.lower(),
                    template_key=item.notification_type,
                    resource_type="football_universe",
                    resource_id=item.match_id or item.club_id,
                    fixture_id=item.match_id,
                    message=item.title,
                    metadata_json={
                        "body": item.message,
                        "severity": item.severity,
                        **dict(item.metadata or {}),
                    },
                )
            )

    def _apply_player_morale_shift(self, *, club_id: str, delta: float, reason: str) -> None:
        players = self.session.scalars(select(Player).where(Player.current_club_profile_id == club_id)).all()
        player_ids = [player.id for player in players]
        states = {
            state.player_id: state
            for state in self.session.scalars(select(PlayerAgencyState).where(PlayerAgencyState.player_id.in_(player_ids))).all()
        }
        for player in players:
            player.morale = _clamp_float(float(player.morale) + delta)
            state = states.get(player.id)
            if state is not None:
                state.morale = _clamp_float(float(state.morale) + delta)
                state.happiness = _clamp_float(float(state.happiness) + (delta * 0.65))
                state.metadata_json = {
                    **dict(state.metadata_json or {}),
                    "last_pressure_reason": reason,
                    "last_pressure_delta": round(delta, 2),
                }

    def _apply_identity_development_bonus(self, *, club_id: str, identity: ClubIdentityView | None) -> None:
        if identity is None:
            return
        players = self.session.scalars(select(Player).where(Player.current_club_profile_id == club_id)).all()
        player_ids = [player.id for player in players]
        states = {
            state.player_id: state
            for state in self.session.scalars(select(PlayerAgencyState).where(PlayerAgencyState.player_id.in_(player_ids))).all()
        }
        for player in players:
            state = states.get(player.id)
            if state is None:
                continue
            development_delta = identity.player_development_bonus * 0.4
            project_belief_delta = identity.chemistry_bonus * 0.35
            if identity.philosophy == ClubPhilosophy.YOUTH_DEVELOPMENT.value:
                development_delta += 1.2
                project_belief_delta += 0.8
            state.development_satisfaction = _clamp_float(float(state.development_satisfaction) + development_delta)
            state.club_project_belief = _clamp_float(float(state.club_project_belief) + project_belief_delta)
            state.metadata_json = {
                **dict(state.metadata_json or {}),
                "club_identity_philosophy": identity.philosophy,
                "club_identity_development_bonus": identity.player_development_bonus,
            }

    def _apply_manager_reputation_shift(self, *, manager_context: dict[str, Any] | None, delta: float) -> None:
        if manager_context is None or abs(delta) <= 0.01:
            return
        manager_user_id = manager_context.get("manager_id") or manager_context.get("user_id")
        competitive_manager_id = manager_context.get("competitive_manager_id")
        if manager_user_id is not None:
            profile = self.session.scalar(select(ManagerProfile).where(ManagerProfile.manager_id == str(manager_user_id)))
            if profile is not None:
                profile.reputation_score = int(round(float(profile.reputation_score) + delta))
            competitive_profiles = self.session.scalars(select(CompetitiveManager).where(CompetitiveManager.user_id == str(manager_user_id))).all()
            for profile in competitive_profiles:
                profile.reputation_score = round(float(profile.reputation_score) + delta, 2)
        if competitive_manager_id is not None:
            profile = self.session.get(CompetitiveManager, str(competitive_manager_id))
            if profile is not None:
                profile.reputation_score = round(float(profile.reputation_score) + delta, 2)

    def _replay_payload_from_fallback(self, match_id: str) -> dict[str, Any] | None:
        competitive = self.session.get(CompetitiveMatch, match_id)
        if competitive is not None and competitive.result_payload:
            return competitive.result_payload
        duel = self.session.get(ManagerDuel, match_id)
        if duel is not None:
            replay_payload = dict((duel.metadata_json or {}).get("replay_payload") or {})
            return replay_payload or None
        return None


__all__ = [
    "FootballUniverseBuilder",
    "FootballUniverseBundle",
    "FootballUniverseService",
]
