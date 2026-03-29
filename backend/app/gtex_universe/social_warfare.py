from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.fan_experience import (
    FanProfile,
    FanTribe,
    LegacySnapshot,
    MarketShockEvent,
    MatchChatMessage,
    MatchChatRoom,
    MegaEvent,
    NarrativeConflict,
)
from app.models.gtex_economy import GtexMatch
from app.models.manager_marketplace import ManagerProfile
from app.models.news_article import NewsArticle
from app.models.prestige_rating import PrestigeRating
from app.models.user import User


_POSITIVE_EMOJIS = frozenset({"🔥", "⚔️", "👏", "🙌", "🚀", "💥", "🏆"})
_NEGATIVE_EMOJIS = frozenset({"😡", "👎", "💀", "😤", "🥶"})
_POSITIVE_TOKENS = frozenset({"win", "cook", "legend", "boss", "ice", "go", "vamos"})
_NEGATIVE_TOKENS = frozenset({"boo", "fraud", "sack", "washed", "choke", "flop"})


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _clean(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(slots=True)
class GtexSocialWarfareService:
    session: Session

    def current_user_tribe(self, *, user_id: str) -> FanTribe | None:
        for tribe in self.session.scalars(select(FanTribe).order_by(FanTribe.updated_at.desc())).all():
            if user_id in list(tribe.members or []):
                self._refresh_tribe_power(tribe)
                return tribe
        return None

    def tribe_payload(self, tribe: FanTribe | None) -> dict[str, Any] | None:
        if tribe is None:
            return None
        return {
            "id": tribe.id,
            "club_id": tribe.club_id,
            "club_name": tribe.club_name,
            "tribe_name": tribe.tribe_name,
            "members": list(tribe.members or []),
            "rivalry_targets": list(tribe.rivalry_targets or []),
            "power_score": round(float(tribe.power_score or 0.0), 4),
            "metadata": dict(tribe.metadata_json or {}),
        }

    def chat_message_payload(self, message: MatchChatMessage, *, tribe: FanTribe | None = None) -> dict[str, Any]:
        return {
            "id": message.id,
            "room_id": message.room_id,
            "match_id": message.match_id,
            "user_id": message.user_id,
            "fan_tribe_id": message.fan_tribe_id,
            "fan_tribe_name": tribe.tribe_name if tribe is not None else None,
            "message": message.message,
            "emoji": message.emoji,
            "intensity": round(float(message.intensity or 0.0), 4),
            "sentiment": message.sentiment,
            "spike_score": round(float(message.spike_score or 0.0), 4),
            "metadata": dict(message.metadata_json or {}),
            "created_at": message.created_at,
        }

    def narrative_conflict_payload(self, conflict: NarrativeConflict) -> dict[str, Any]:
        return {
            "id": conflict.id,
            "match_id": conflict.match_id,
            "club_id": conflict.club_id,
            "player_id": conflict.player_id,
            "manager_profile_id": conflict.manager_profile_id,
            "conflict_type": conflict.conflict_type,
            "headline": conflict.headline,
            "status": conflict.status,
            "severity": conflict.severity,
            "impact_score": round(float(conflict.impact_score or 0.0), 4),
            "triggers": dict(conflict.triggers_json or {}),
            "impact": dict(conflict.impact_json or {}),
            "metadata": dict(conflict.metadata_json or {}),
            "created_at": conflict.created_at,
            "updated_at": conflict.updated_at,
        }

    def market_shock_payload(self, shock: MarketShockEvent) -> dict[str, Any]:
        return {
            "id": shock.id,
            "match_id": shock.match_id,
            "club_id": shock.club_id,
            "player_id": shock.player_id,
            "shock_type": shock.shock_type,
            "headline": shock.headline,
            "status": shock.status,
            "magnitude": round(float(shock.magnitude or 0.0), 4),
            "player_price_delta_bps": int(shock.player_price_delta_bps or 0),
            "fan_sentiment_delta": round(float(shock.fan_sentiment_delta or 0.0), 4),
            "betting_odds_delta_bps": int(shock.betting_odds_delta_bps or 0),
            "impact": dict(shock.impact_json or {}),
            "metadata": dict(shock.metadata_json or {}),
            "created_at": shock.created_at,
            "updated_at": shock.updated_at,
        }

    def mega_event_payload(self, event: MegaEvent | None, *, preview: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if event is None and preview is None:
            return None
        if event is None:
            return dict(preview or {})
        return {
            "id": event.id,
            "event_key": event.event_key,
            "match_id": event.match_id,
            "event_type": event.event_type,
            "title": event.title,
            "status": event.status,
            "limited_tickets": int(event.limited_tickets or 0),
            "exclusive_commentary": bool(event.exclusive_commentary),
            "global_broadcast": bool(event.global_broadcast),
            "hype_score": round(float(event.hype_score or 0.0), 4),
            "metadata": dict(event.metadata_json or {}),
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }

    def join_tribe(
        self,
        *,
        actor: User,
        club_id: str | None = None,
        match: GtexMatch | None = None,
    ) -> FanTribe:
        profile = self._fan_profile(actor)
        clubs = self._club_context(match) if match is not None else {}
        resolved_club_id = _clean(club_id) or _clean(profile.favorite_club_id)
        resolved_club_name = profile.favorite_club_name
        if resolved_club_id is None and clubs:
            favorite_name = str(profile.favorite_club_name or "").strip().lower()
            if favorite_name and favorite_name == str(clubs["home"]["club_name"]).strip().lower():
                resolved_club_id = clubs["home"]["club_id"]
                resolved_club_name = clubs["home"]["club_name"]
            elif favorite_name and favorite_name == str(clubs["away"]["club_name"]).strip().lower():
                resolved_club_id = clubs["away"]["club_id"]
                resolved_club_name = clubs["away"]["club_name"]
        if resolved_club_id is None and clubs:
            if _clean(profile.favorite_club_id) in {clubs["home"]["club_id"], clubs["away"]["club_id"]}:
                resolved_club_id = profile.favorite_club_id
                resolved_club_name = (
                    clubs["home"]["club_name"]
                    if clubs["home"]["club_id"] == resolved_club_id
                    else clubs["away"]["club_name"]
                )
            else:
                resolved_club_id = clubs["home"]["club_id"]
                resolved_club_name = clubs["home"]["club_name"]
        if resolved_club_id is None:
            raise ValueError("Joining a tribe requires a favorite club or a target club.")
        if clubs:
            if clubs["home"]["club_id"] == resolved_club_id:
                rivalry_targets = [clubs["away"]["club_id"], *list(profile.rival_club_ids_json or [])]
                resolved_club_name = clubs["home"]["club_name"]
            elif clubs["away"]["club_id"] == resolved_club_id:
                rivalry_targets = [clubs["home"]["club_id"], *list(profile.rival_club_ids_json or [])]
                resolved_club_name = clubs["away"]["club_name"]
            else:
                rivalry_targets = list(profile.rival_club_ids_json or [])
        else:
            rivalry_targets = list(profile.rival_club_ids_json or [])
        tribe = self._get_or_create_tribe(
            club_id=resolved_club_id,
            club_name=resolved_club_name,
            rivalry_targets=rivalry_targets,
        )
        members = list(tribe.members or [])
        if actor.id not in members:
            members.append(actor.id)
            tribe.members = members
        if profile.favorite_club_id is None:
            profile.favorite_club_id = resolved_club_id
            profile.favorite_club_name = resolved_club_name
        self._refresh_tribe_power(tribe)
        self.session.flush()
        return tribe

    def post_chat_message(
        self,
        *,
        actor: User,
        match: GtexMatch,
        message: str | None,
        emoji: str | None,
        intensity: float,
    ) -> dict[str, Any]:
        resolved_message = (message or "").strip() or None
        resolved_emoji = (emoji or "").strip() or None
        if resolved_message is None and resolved_emoji is None:
            raise ValueError("Chat storms require a message, an emoji, or both.")
        profile = self._fan_profile(actor)
        room = self._get_or_create_room(match=match)
        tribe = self.current_user_tribe(user_id=actor.id)
        if tribe is None:
            clubs = self._club_context(match)
            favorite_name = str(profile.favorite_club_name or "").strip().lower()
            if profile.favorite_club_id in {clubs["home"]["club_id"], clubs["away"]["club_id"]}:
                tribe = self.join_tribe(actor=actor, match=match, club_id=profile.favorite_club_id)
            elif favorite_name and favorite_name == str(clubs["home"]["club_name"]).strip().lower():
                tribe = self.join_tribe(actor=actor, match=match, club_id=clubs["home"]["club_id"])
            elif favorite_name and favorite_name == str(clubs["away"]["club_name"]).strip().lower():
                tribe = self.join_tribe(actor=actor, match=match, club_id=clubs["away"]["club_id"])
        recent_messages = self._recent_messages(room_id=room.id, limit=6)
        repeat_count = sum(1 for item in recent_messages if item.emoji and item.emoji == resolved_emoji)
        sentiment = self._message_sentiment(message=resolved_message, emoji=resolved_emoji)
        base_intensity = _clamp(float(intensity or 1.0), 0.2, 3.0)
        spike_score = round(
            _clamp(
                base_intensity
                + (repeat_count * 0.34)
                + (0.28 if sentiment == "positive" else 0.18 if sentiment == "negative" else 0.08)
                + (0.16 if tribe is not None else 0.0),
                0.1,
                5.0,
            ),
            4,
        )
        chat_message = MatchChatMessage(
            room_id=room.id,
            match_id=match.id,
            user_id=actor.id,
            fan_profile_id=profile.id,
            fan_tribe_id=tribe.id if tribe is not None else None,
            message=resolved_message,
            emoji=resolved_emoji,
            intensity=base_intensity,
            sentiment=sentiment,
            spike_score=spike_score,
            metadata_json={
                "repeat_count": repeat_count,
                "event_title": self._match_title(match),
            },
        )
        self.session.add(chat_message)
        self.session.flush()

        room.message_count = int(room.message_count or 0) + 1
        room.emoji_burst_score = round(
            _clamp((float(room.emoji_burst_score or 0.0) * 0.72) + (1.1 if resolved_emoji else 0.38) * base_intensity + (repeat_count * 0.22), 0.0, 6.0),
            4,
        )
        room.moment_spike_score = round(
            _clamp((float(room.moment_spike_score or 0.0) * 0.68) + (spike_score * 0.42), 0.0, 6.0),
            4,
        )
        room.metadata_json = self._updated_room_metadata(room=room, chat_message=chat_message)
        self.session.flush()

        if tribe is not None:
            self._refresh_tribe_power(tribe)
        return {
            "message": self.chat_message_payload(chat_message, tribe=tribe),
            "live_chat": self.live_chat_summary(match=match, room=room),
            "fan_war": self.fan_war_summary(match=match, live_chat=self.live_chat_summary(match=match, room=room)),
        }

    def fan_war_pressure(self, *, match: GtexMatch) -> float:
        summary = self.fan_war_summary(match=match)
        return round(float(summary.get("tribe_pressure") or 0.0), 4)

    def live_chat_pressure(self, *, match: GtexMatch) -> float:
        room = self._room_for_match(match_id=match.id)
        if room is None:
            return 0.0
        return round(_clamp(float(room.moment_spike_score or 0.0) / 5.0, 0.0, 1.0), 4)

    def live_chat_summary(self, *, match: GtexMatch, room: MatchChatRoom | None = None) -> dict[str, Any]:
        resolved_room = room or self._room_for_match(match_id=match.id)
        if resolved_room is None:
            return {
                "room_id": None,
                "room_key": f"match:{match.id}:chat",
                "total_messages": 0,
                "emoji_burst_score": 0.0,
                "moment_spike_score": 0.0,
                "moment_spike_bonus": 0,
                "dominant_emoji": None,
                "recent_messages": [],
                "moment_spikes": [],
            }
        recent_messages = self._recent_messages(room_id=resolved_room.id, limit=8)
        emoji_counts = Counter(item.emoji for item in recent_messages if item.emoji)
        dominant_emoji = None
        if emoji_counts:
            dominant_emoji = emoji_counts.most_common(1)[0][0]
        elif isinstance((resolved_room.metadata_json or {}).get("emoji_counts"), dict):
            stored_counts = Counter((resolved_room.metadata_json or {}).get("emoji_counts") or {})
            dominant_emoji = stored_counts.most_common(1)[0][0] if stored_counts else None
        tribe_map = {
            tribe.id: tribe
            for tribe in self.session.scalars(select(FanTribe)).all()
        }
        return {
            "room_id": resolved_room.id,
            "room_key": resolved_room.room_key,
            "total_messages": int(resolved_room.message_count or 0),
            "emoji_burst_score": round(float(resolved_room.emoji_burst_score or 0.0), 4),
            "moment_spike_score": round(float(resolved_room.moment_spike_score or 0.0), 4),
            "moment_spike_bonus": min(4, max(0, int(round(float(resolved_room.moment_spike_score or 0.0))))),
            "dominant_emoji": dominant_emoji,
            "recent_messages": [
                self.chat_message_payload(item, tribe=tribe_map.get(item.fan_tribe_id))
                for item in recent_messages
            ],
            "moment_spikes": list((resolved_room.metadata_json or {}).get("moment_spikes") or []),
        }

    def fan_war_summary(
        self,
        *,
        match: GtexMatch,
        live_chat: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clubs = self._club_context(match)
        tribes = self._match_tribes(match=match, create=False)
        by_club = {tribe.club_id: tribe for tribe in tribes}
        home = by_club.get(clubs["home"]["club_id"])
        away = by_club.get(clubs["away"]["club_id"])
        home_payload = self.tribe_payload(home)
        away_payload = self.tribe_payload(away)
        if home is None and away is None:
            return {
                "week_key": _utcnow().strftime("%Y-W%V"),
                "home_tribe": home_payload,
                "away_tribe": away_payload,
                "leader": None,
                "rivalry_heat": 0.0,
                "tribe_pressure": 0.0,
                "impact": {
                    "match_atmosphere_boost": 1.0,
                    "ticket_demand_multiplier": 1.0,
                    "commentary_tone": "charged",
                },
            }
        live_chat_payload = live_chat or self.live_chat_summary(match=match)
        home_power = float(home.power_score if home is not None else 10.0)
        away_power = float(away.power_score if away is not None else 10.0)
        mutual_target = bool(
            home is not None
            and away is not None
            and (
                away.club_id in list(home.rivalry_targets or [])
                or home.club_id in list(away.rivalry_targets or [])
            )
        )
        total = max(home_power + away_power, 1.0)
        edge = (home_power - away_power) / total
        chat_boost = float(live_chat_payload.get("moment_spike_score") or 0.0) / 5.0
        rivalry_heat = round(
            _clamp(
                0.24
                + (0.26 if mutual_target else 0.08)
                + min(0.22, abs(edge) * 0.7)
                + min(0.2, chat_boost * 0.24),
                0.0,
                1.0,
            ),
            4,
        )
        commentary_tone = "combative" if rivalry_heat >= 0.62 else "electric" if chat_boost >= 0.35 else "charged"
        return {
            "week_key": _utcnow().strftime("%Y-W%V"),
            "home_tribe": home_payload,
            "away_tribe": away_payload,
            "leader": clubs["home"]["club_name"] if edge > 0.05 else clubs["away"]["club_name"] if edge < -0.05 else "draw",
            "rivalry_heat": rivalry_heat,
            "tribe_pressure": round(_clamp(rivalry_heat + (abs(edge) * 0.32), 0.0, 1.0), 4),
            "impact": {
                "match_atmosphere_boost": round(1.0 + (rivalry_heat * 0.12), 4),
                "ticket_demand_multiplier": round(1.0 + (rivalry_heat * 0.08) + (abs(edge) * 0.06), 4),
                "commentary_tone": commentary_tone,
            },
        }

    def legacy_board(self, *, limit: int = 5) -> dict[str, Any]:
        resolved_limit = max(1, int(limit))
        greatest_matches = [
            {
                "entity_id": item.entity_id,
                "headline": item.headline,
                "score": round(float(item.score or 0.0), 4),
                "season_key": item.season_key,
                "rank_position": item.rank_position,
                "metadata": dict(item.metadata_json or {}),
            }
            for item in self.session.scalars(
                select(LegacySnapshot)
                .where(LegacySnapshot.category == "greatest_matches")
                .order_by(LegacySnapshot.score.desc(), LegacySnapshot.updated_at.desc())
                .limit(resolved_limit)
            ).all()
        ]
        top_players = [
            {
                "entity_id": item.entity_id,
                "entity_name": item.entity_name,
                "prestige_score": round(float(item.prestige_score or 0.0), 4),
                "prestige_tier": item.prestige_tier,
                "rank_position": item.rank_position,
                "metadata": dict(item.metadata_json or {}),
            }
            for item in self.session.scalars(
                select(PrestigeRating)
                .where(
                    PrestigeRating.entity_type == "player",
                    PrestigeRating.scope == "lifetime",
                    PrestigeRating.season_key == "lifetime",
                )
                .order_by(PrestigeRating.prestige_score.desc(), PrestigeRating.updated_at.desc())
                .limit(resolved_limit)
            ).all()
        ]
        club_dynasties = [
            {
                "entity_id": item.entity_id,
                "entity_name": item.entity_name,
                "prestige_score": round(float(item.prestige_score or 0.0), 4),
                "prestige_tier": item.prestige_tier,
                "rank_position": item.rank_position,
                "metadata": dict(item.metadata_json or {}),
            }
            for item in self.session.scalars(
                select(PrestigeRating)
                .where(
                    PrestigeRating.entity_type == "club",
                    PrestigeRating.scope == "lifetime",
                    PrestigeRating.season_key == "lifetime",
                )
                .order_by(PrestigeRating.prestige_score.desc(), PrestigeRating.updated_at.desc())
                .limit(resolved_limit)
            ).all()
        ]
        return {
            "generated_at": _utcnow(),
            "greatest_matches": greatest_matches,
            "top_players": top_players,
            "club_dynasties": club_dynasties,
        }

    def match_social_warfare(
        self,
        *,
        match: GtexMatch,
        current_user: User | None,
        offer: dict[str, Any],
    ) -> dict[str, Any]:
        live_chat = self.live_chat_summary(match=match)
        fan_war = self.fan_war_summary(match=match, live_chat=live_chat)
        active_conflicts = [
            self.narrative_conflict_payload(item)
            for item in self._active_conflicts(match=match)
        ]
        if not active_conflicts:
            active_conflicts = self._preview_conflicts(match=match, fan_war=fan_war)
        active_shocks = [
            self.market_shock_payload(item)
            for item in self._active_shocks(match=match)
        ]
        if not active_shocks:
            active_shocks = self._preview_market_shocks(match=match, fan_war=fan_war, offer=offer)
        mega_event = self._mega_event_summary(match=match, offer=offer, fan_war=fan_war, live_chat=live_chat)
        tribes = [self.tribe_payload(item) for item in self._match_tribes(match=match, create=False)]
        return {
            "match_id": match.id,
            "current_user_tribe": self.tribe_payload(self.current_user_tribe(user_id=current_user.id)) if current_user is not None else None,
            "fan_tribes": [item for item in tribes if item is not None],
            "fan_war": fan_war,
            "live_chat": live_chat,
            "narrative_conflicts": active_conflicts,
            "market_shocks": active_shocks,
            "mega_event": mega_event,
            "legacy": self.legacy_board(limit=3),
        }

    def finalize_match_social_warfare(self, *, match: GtexMatch, fan_context: dict[str, Any]) -> dict[str, Any]:
        offer = {
            "match_id": match.id,
            "is_final": bool(dict(match.metadata_json or {}).get("fan_experience", {}).get("is_final")),
            "capacity": int(dict(match.metadata_json or {}).get("fan_experience", {}).get("capacity") or 0),
            "tickets_sold": int(fan_context.get("tickets_sold") or 0),
            "sell_out_hype": {"triggered": bool(fan_context.get("sell_out_triggered"))},
        }
        live_chat = self.live_chat_summary(match=match)
        fan_war = self.fan_war_summary(match=match, live_chat=live_chat)
        clubs = self._club_context(match)
        goal_delta = abs(int(match.home_score or 0) - int(match.away_score or 0))
        winner_side = str(fan_context.get("winner_side") or "draw")

        if winner_side in {"home", "away"}:
            winning_club = clubs[winner_side]
            self._increment_weekly_war(club_id=winning_club["club_id"])

        losing_manager_id = (
            fan_context.get("away_manager_id")
            if winner_side == "home"
            else fan_context.get("home_manager_id")
            if winner_side == "away"
            else None
        )
        if losing_manager_id:
            manager = self.session.get(ManagerProfile, losing_manager_id)
            if manager is not None and int(manager.current_losing_streak or 0) >= 2:
                conflict = self._upsert_conflict(
                    match=match,
                    conflict_type="manager_under_pressure",
                    headline=f"{self._manager_name(manager)} is under pressure",
                    club_id=clubs["away"]["club_id"] if winner_side == "home" else clubs["home"]["club_id"] if winner_side == "away" else None,
                    manager_profile_id=manager.id,
                    severity="high" if int(manager.current_losing_streak or 0) >= 3 else "medium",
                    impact_score=0.72 + min(0.18, float(manager.current_losing_streak or 0) * 0.05),
                    triggers={"current_losing_streak": int(manager.current_losing_streak or 0), "winner_side": winner_side},
                    impact={"commentary_tone": "pressure_cooker", "fan_sentiment_delta": -0.28},
                )
                self._upsert_article(
                    article_type="narrative_conflict",
                    title=conflict.headline,
                    match_id=match.id,
                    body="The latest result pushed the dugout storyline into crisis territory.",
                    tags=["manager", "pressure", "social_warfare"],
                )

        if fan_war["rivalry_heat"] >= 0.62 or str(fan_context.get("commentary_tone") or "").lower() == "hostile":
            backlash_side = "home" if winner_side == "away" else "away" if winner_side == "home" else "home"
            backlash_club = clubs[backlash_side]
            conflict = self._upsert_conflict(
                match=match,
                conflict_type="fan_backlash",
                headline=f"Fan backlash erupts around {backlash_club['club_name']}",
                club_id=backlash_club["club_id"],
                manager_profile_id=None,
                severity="high" if fan_war["rivalry_heat"] >= 0.8 else "medium",
                impact_score=0.64 + min(0.2, fan_war["rivalry_heat"] * 0.2),
                triggers={"rivalry_heat": fan_war["rivalry_heat"], "winner_side": winner_side},
                impact={"commentary_tone": "combative", "fan_sentiment_delta": -0.24},
            )
            self._upsert_article(
                article_type="narrative_conflict",
                title=conflict.headline,
                match_id=match.id,
                body="The result and the tribe war combined into a genuine supporter backlash.",
                tags=["fans", "backlash", "social_warfare"],
            )

        metadata = dict(match.metadata_json or {})
        transfer_story = _clean(metadata.get("transfer_story"))
        if transfer_story is not None:
            self._upsert_conflict(
                match=match,
                conflict_type="player_betrayal",
                headline=transfer_story,
                club_id=None,
                manager_profile_id=None,
                severity="medium",
                impact_score=0.61,
                triggers={"source": "transfer_story"},
                impact={"fan_sentiment_delta": -0.18},
            )

        if _clean(metadata.get("dao_vote_result")):
            shock = self._upsert_market_shock(
                match=match,
                shock_type="dao_corruption_vote",
                headline="DAO corruption vote rocks the market",
                club_id=None,
                magnitude=0.78,
                player_price_delta_bps=-180,
                fan_sentiment_delta=-0.32,
                betting_odds_delta_bps=140,
                impact={"source": metadata.get("dao_vote_result")},
            )
            self._upsert_article(
                article_type="market_shock",
                title=shock.headline,
                match_id=match.id,
                body="Governance pressure has spilled into pricing, sentiment, and odds.",
                tags=["dao", "market_shock", "social_warfare"],
            )

        if bool(metadata.get("scandal")):
            self._upsert_market_shock(
                match=match,
                shock_type="scandal",
                headline="Scandal slams confidence across the fan market",
                club_id=None,
                magnitude=0.74,
                player_price_delta_bps=-140,
                fan_sentiment_delta=-0.3,
                betting_odds_delta_bps=120,
                impact={"source": "scandal_flag"},
            )

        if bool(metadata.get("injury_crisis")):
            self._upsert_market_shock(
                match=match,
                shock_type="injury_crisis",
                headline="Injury crisis hits lineup confidence",
                club_id=None,
                magnitude=0.66,
                player_price_delta_bps=-120,
                fan_sentiment_delta=-0.18,
                betting_odds_delta_bps=110,
                impact={"source": "injury_crisis"},
            )

        if winner_side in {"home", "away"} and (goal_delta >= 2 or bool(fan_context.get("sell_out_triggered")) or fan_war["rivalry_heat"] >= 0.68):
            winning_club = clubs[winner_side]
            shock = self._upsert_market_shock(
                match=match,
                shock_type="breakout_star",
                headline=f"Breakout-star momentum lifts {winning_club['club_name']}",
                club_id=winning_club["club_id"],
                magnitude=0.71 + min(0.16, goal_delta * 0.04),
                player_price_delta_bps=160 + (goal_delta * 20),
                fan_sentiment_delta=0.28,
                betting_odds_delta_bps=-125,
                impact={"winner_side": winner_side, "goal_delta": goal_delta},
            )
            self._upsert_article(
                article_type="market_shock",
                title=shock.headline,
                match_id=match.id,
                body="A decisive performance triggered a positive shock through prices, sentiment, and betting lines.",
                tags=["breakout", "market_shock", "social_warfare"],
            )

        mega_event = self._ensure_mega_event(match=match, offer=offer, fan_war=fan_war, live_chat=live_chat)
        if mega_event is not None:
            mega_event.status = "completed"

        if (
            bool(fan_context.get("sell_out_triggered"))
            or offer["is_final"]
            or goal_delta >= 3
            or fan_war["rivalry_heat"] >= 0.7
            or float(live_chat.get("moment_spike_score") or 0.0) >= 2.0
        ):
            snapshot = self._upsert_legacy_snapshot(
                category="greatest_matches",
                entity_type="match",
                entity_id=match.id,
                match_id=match.id,
                headline=f"{self._match_title(match)} enters the greatest-match archive",
                score=0.68
                + (0.08 if offer["is_final"] else 0.0)
                + min(0.14, goal_delta * 0.03)
                + min(0.12, fan_war["rivalry_heat"] * 0.12),
                metadata={
                    "winner_side": winner_side,
                    "goal_delta": goal_delta,
                    "sell_out_triggered": bool(fan_context.get("sell_out_triggered")),
                },
            )
            self._upsert_article(
                article_type="legacy_snapshot",
                title=snapshot.headline,
                match_id=match.id,
                body="The social warfare layer has locked this match into GTEX history.",
                tags=["legacy", "greatest_matches", "social_warfare"],
            )

        self.session.flush()
        return self.match_social_warfare(match=match, current_user=None, offer=offer)

    def _fan_profile(self, actor: User) -> FanProfile:
        profile = self.session.scalar(select(FanProfile).where(FanProfile.user_id == actor.id))
        if profile is None:
            profile = FanProfile(user_id=actor.id)
            self.session.add(profile)
            self.session.flush()
        return profile

    def _club_context(self, match: GtexMatch) -> dict[str, dict[str, str]]:
        metadata = dict(match.metadata_json or {})
        match_context = dict(metadata.get("match_context") or {})

        def _normalized_key(raw_name: str, *, side: str, user_id: str | None, ai_id: str | None) -> str:
            direct_id = _clean(metadata.get(f"{side}_club_id")) or _clean(match_context.get(f"{side}_club_id"))
            if direct_id is not None:
                return direct_id
            if ai_id is not None:
                return f"ai:{ai_id}"
            if user_id is not None:
                return f"user:{user_id}"
            normalized = "".join(character.lower() if character.isalnum() else "-" for character in raw_name).strip("-")
            while "--" in normalized:
                normalized = normalized.replace("--", "-")
            return f"club:{normalized or side}"

        home_name = str(metadata.get("home_label") or match_context.get("home_label") or "Home")
        away_name = str(metadata.get("away_label") or match_context.get("away_label") or "Away")
        return {
            "home": {
                "club_id": _normalized_key(home_name, side="home", user_id=match.home_user_id, ai_id=match.home_ai_id),
                "club_name": home_name,
            },
            "away": {
                "club_id": _normalized_key(away_name, side="away", user_id=match.away_user_id, ai_id=match.away_ai_id),
                "club_name": away_name,
            },
        }

    def _get_or_create_tribe(
        self,
        *,
        club_id: str,
        club_name: str | None,
        rivalry_targets: list[str],
    ) -> FanTribe:
        tribe = self.session.scalar(select(FanTribe).where(FanTribe.club_id == club_id))
        if tribe is None:
            tribe = FanTribe(
                club_id=club_id,
                club_name=club_name,
                tribe_name=f"{club_name or club_id} Army",
                members=[],
                rivalry_targets=[],
                metadata_json={},
            )
            self.session.add(tribe)
            self.session.flush()
        tribe.club_name = club_name or tribe.club_name
        tribe.tribe_name = tribe.tribe_name or f"{tribe.club_name or tribe.club_id} Army"
        tribe.rivalry_targets = list(
            dict.fromkeys(
                item
                for item in [*list(tribe.rivalry_targets or []), *list(rivalry_targets or [])]
                if _clean(item) and item != tribe.club_id
            )
        )
        self._refresh_tribe_power(tribe)
        return tribe

    def _match_tribes(self, *, match: GtexMatch, create: bool) -> list[FanTribe]:
        clubs = self._club_context(match)
        rows = list(
            self.session.scalars(
                select(FanTribe).where(
                    or_(
                        FanTribe.club_id == clubs["home"]["club_id"],
                        FanTribe.club_id == clubs["away"]["club_id"],
                    )
                )
            ).all()
        )
        by_club = {row.club_id: row for row in rows}
        if create:
            for side, other_side in (("home", "away"), ("away", "home")):
                club = clubs[side]
                if club["club_id"] not in by_club:
                    by_club[club["club_id"]] = self._get_or_create_tribe(
                        club_id=club["club_id"],
                        club_name=club["club_name"],
                        rivalry_targets=[clubs[other_side]["club_id"]],
                    )
        return [row for row in (by_club.get(clubs["home"]["club_id"]), by_club.get(clubs["away"]["club_id"])) if row is not None]

    def _refresh_tribe_power(self, tribe: FanTribe) -> None:
        metadata = dict(tribe.metadata_json or {})
        week_key = _utcnow().strftime("%Y-W%V")
        if metadata.get("weekly_war_key") != week_key:
            metadata["weekly_war_key"] = week_key
            metadata["weekly_wins"] = 0
        member_count = len(dict.fromkeys(item for item in list(tribe.members or []) if _clean(item)))
        rivalry_count = len(dict.fromkeys(item for item in list(tribe.rivalry_targets or []) if _clean(item)))
        weekly_wins = int(metadata.get("weekly_wins") or 0)
        tribe.power_score = round(
            _clamp(8.0 + (member_count * 2.0) + (rivalry_count * 0.75) + (weekly_wins * 2.35), 0.0, 1000.0),
            4,
        )
        metadata["member_count"] = member_count
        metadata["weekly_wins"] = weekly_wins
        metadata["last_power_refresh_at"] = _utcnow().isoformat()
        tribe.metadata_json = metadata

    def _room_for_match(self, *, match_id: str) -> MatchChatRoom | None:
        return self.session.scalar(select(MatchChatRoom).where(MatchChatRoom.match_id == match_id))

    def _get_or_create_room(self, *, match: GtexMatch) -> MatchChatRoom:
        room = self._room_for_match(match_id=match.id)
        if room is None:
            room = MatchChatRoom(
                match_id=match.id,
                room_key=f"match:{match.id}:chat",
                room_title=f"{self._match_title(match)} Live Chat",
                message_count=0,
                emoji_burst_score=0.0,
                moment_spike_score=0.0,
                metadata_json={},
            )
            self.session.add(room)
            self.session.flush()
        return room

    def _recent_messages(self, *, room_id: str, limit: int) -> list[MatchChatMessage]:
        rows = list(
            self.session.scalars(
                select(MatchChatMessage)
                .where(MatchChatMessage.room_id == room_id)
                .order_by(MatchChatMessage.created_at.desc())
                .limit(max(1, limit))
            ).all()
        )
        rows.reverse()
        return rows

    def _message_sentiment(self, *, message: str | None, emoji: str | None) -> str:
        text = (message or "").strip().lower()
        tokens = {token for token in text.replace("!", " ").replace("?", " ").replace(".", " ").split() if token}
        positive_score = len(tokens & _POSITIVE_TOKENS) + (1 if emoji in _POSITIVE_EMOJIS else 0)
        negative_score = len(tokens & _NEGATIVE_TOKENS) + (1 if emoji in _NEGATIVE_EMOJIS else 0)
        if positive_score > negative_score:
            return "positive"
        if negative_score > positive_score:
            return "negative"
        return "neutral"

    def _updated_room_metadata(self, *, room: MatchChatRoom, chat_message: MatchChatMessage) -> dict[str, Any]:
        metadata = dict(room.metadata_json or {})
        created_at = chat_message.created_at or _utcnow()
        emoji_counts = {
            str(key): int(value)
            for key, value in dict(metadata.get("emoji_counts") or {}).items()
            if _clean(key)
        }
        if chat_message.emoji:
            emoji_counts[chat_message.emoji] = int(emoji_counts.get(chat_message.emoji) or 0) + 1
        moment_spikes = [
            dict(item)
            for item in list(metadata.get("moment_spikes") or [])
            if isinstance(item, dict)
        ]
        if float(chat_message.spike_score or 0.0) >= 1.45:
            moment_spikes.insert(
                0,
                {
                    "message_id": chat_message.id,
                    "emoji": chat_message.emoji,
                    "sentiment": chat_message.sentiment,
                    "spike_score": round(float(chat_message.spike_score or 0.0), 4),
                    "headline": chat_message.message or chat_message.emoji or "fan storm",
                    "created_at": created_at.isoformat(),
                },
            )
        return {
            **metadata,
            "emoji_counts": emoji_counts,
            "moment_spikes": moment_spikes[:6],
            "last_message_id": chat_message.id,
            "last_sentiment": chat_message.sentiment,
            "last_message_at": created_at.isoformat(),
        }

    def _active_conflicts(self, *, match: GtexMatch) -> list[NarrativeConflict]:
        clubs = self._club_context(match)
        return list(
            self.session.scalars(
                select(NarrativeConflict)
                .where(
                    NarrativeConflict.status == "active",
                    or_(
                        NarrativeConflict.match_id == match.id,
                        NarrativeConflict.club_id.in_([clubs["home"]["club_id"], clubs["away"]["club_id"]]),
                    ),
                )
                .order_by(NarrativeConflict.updated_at.desc(), NarrativeConflict.created_at.desc())
                .limit(6)
            ).all()
        )

    def _preview_conflicts(self, *, match: GtexMatch, fan_war: dict[str, Any]) -> list[dict[str, Any]]:
        metadata = dict(match.metadata_json or {})
        clubs = self._club_context(match)
        previews: list[dict[str, Any]] = []
        if fan_war["rivalry_heat"] >= 0.55:
            previews.append(
                {
                    "id": None,
                    "match_id": match.id,
                    "club_id": clubs["away"]["club_id"],
                    "player_id": None,
                    "manager_profile_id": None,
                    "conflict_type": "fan_backlash",
                    "headline": f"Backlash is brewing around {clubs['away']['club_name']}",
                    "status": "preview",
                    "severity": "medium",
                    "impact_score": round(0.46 + min(0.2, fan_war["rivalry_heat"] * 0.18), 4),
                    "triggers": {"rivalry_heat": fan_war["rivalry_heat"]},
                    "impact": {"commentary_tone": "combative"},
                    "metadata": {"preview": True},
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                }
            )
        transfer_story = _clean(metadata.get("transfer_story"))
        if transfer_story is not None:
            previews.append(
                {
                    "id": None,
                    "match_id": match.id,
                    "club_id": None,
                    "player_id": None,
                    "manager_profile_id": None,
                    "conflict_type": "player_betrayal",
                    "headline": transfer_story,
                    "status": "preview",
                    "severity": "medium",
                    "impact_score": 0.61,
                    "triggers": {"source": "transfer_story"},
                    "impact": {"fan_sentiment_delta": -0.18},
                    "metadata": {"preview": True},
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                }
            )
        return previews[:3]

    def _active_shocks(self, *, match: GtexMatch) -> list[MarketShockEvent]:
        clubs = self._club_context(match)
        return list(
            self.session.scalars(
                select(MarketShockEvent)
                .where(
                    MarketShockEvent.status == "active",
                    or_(
                        MarketShockEvent.match_id == match.id,
                        MarketShockEvent.club_id.in_([clubs["home"]["club_id"], clubs["away"]["club_id"]]),
                    ),
                )
                .order_by(MarketShockEvent.updated_at.desc(), MarketShockEvent.created_at.desc())
                .limit(6)
            ).all()
        )

    def _preview_market_shocks(
        self,
        *,
        match: GtexMatch,
        fan_war: dict[str, Any],
        offer: dict[str, Any],
    ) -> list[dict[str, Any]]:
        metadata = dict(match.metadata_json or {})
        clubs = self._club_context(match)
        previews: list[dict[str, Any]] = []
        if bool(metadata.get("injury_crisis")):
            previews.append(
                {
                    "id": None,
                    "match_id": match.id,
                    "club_id": clubs["home"]["club_id"],
                    "player_id": None,
                    "shock_type": "injury_crisis",
                    "headline": "Injury crisis threatens the match economy",
                    "status": "preview",
                    "magnitude": 0.64,
                    "player_price_delta_bps": -120,
                    "fan_sentiment_delta": -0.18,
                    "betting_odds_delta_bps": 110,
                    "impact": {"source": "injury_crisis"},
                    "metadata": {"preview": True},
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                }
            )
        if bool(metadata.get("scandal")):
            previews.append(
                {
                    "id": None,
                    "match_id": match.id,
                    "club_id": None,
                    "player_id": None,
                    "shock_type": "scandal",
                    "headline": "Scandal risk hangs over the market",
                    "status": "preview",
                    "magnitude": 0.7,
                    "player_price_delta_bps": -140,
                    "fan_sentiment_delta": -0.26,
                    "betting_odds_delta_bps": 120,
                    "impact": {"source": "scandal"},
                    "metadata": {"preview": True},
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                }
            )
        if bool(metadata.get("dao_vote_result")):
            previews.append(
                {
                    "id": None,
                    "match_id": match.id,
                    "club_id": None,
                    "player_id": None,
                    "shock_type": "dao_corruption_vote",
                    "headline": "DAO vote turbulence is shaking pricing",
                    "status": "preview",
                    "magnitude": 0.75,
                    "player_price_delta_bps": -180,
                    "fan_sentiment_delta": -0.32,
                    "betting_odds_delta_bps": 140,
                    "impact": {"source": metadata.get("dao_vote_result")},
                    "metadata": {"preview": True},
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                }
            )
        if offer.get("is_final") or bool(offer.get("sell_out_hype", {}).get("triggered")) or fan_war["rivalry_heat"] >= 0.62:
            previews.append(
                {
                    "id": None,
                    "match_id": match.id,
                    "club_id": clubs["home"]["club_id"],
                    "player_id": None,
                    "shock_type": "breakout_star",
                    "headline": f"Breakout-star watch is rising around {clubs['home']['club_name']}",
                    "status": "preview",
                    "magnitude": round(0.58 + min(0.16, fan_war["rivalry_heat"] * 0.18), 4),
                    "player_price_delta_bps": 150,
                    "fan_sentiment_delta": 0.24,
                    "betting_odds_delta_bps": -115,
                    "impact": {"source": "fan_war_heat"},
                    "metadata": {"preview": True},
                    "created_at": _utcnow(),
                    "updated_at": _utcnow(),
                }
            )
        return previews[:4]

    def _mega_event_summary(
        self,
        *,
        match: GtexMatch,
        offer: dict[str, Any],
        fan_war: dict[str, Any],
        live_chat: dict[str, Any],
    ) -> dict[str, Any] | None:
        event = self.session.scalar(select(MegaEvent).where(MegaEvent.match_id == match.id))
        if event is not None:
            return self.mega_event_payload(event)
        return self.mega_event_payload(None, preview=self._mega_event_preview(match=match, offer=offer, fan_war=fan_war, live_chat=live_chat))

    def _ensure_mega_event(
        self,
        *,
        match: GtexMatch,
        offer: dict[str, Any],
        fan_war: dict[str, Any],
        live_chat: dict[str, Any],
    ) -> MegaEvent | None:
        preview = self._mega_event_preview(match=match, offer=offer, fan_war=fan_war, live_chat=live_chat)
        if preview is None:
            return None
        event = self.session.scalar(select(MegaEvent).where(MegaEvent.match_id == match.id))
        if event is None:
            event = MegaEvent(
                event_key=str(preview["event_key"]),
                match_id=match.id,
                event_type=str(preview["event_type"]),
                title=str(preview["title"]),
                status=str(preview["status"]),
                limited_tickets=int(preview["limited_tickets"]),
                exclusive_commentary=bool(preview["exclusive_commentary"]),
                global_broadcast=bool(preview["global_broadcast"]),
                hype_score=float(preview["hype_score"]),
                metadata_json=dict(preview.get("metadata") or {}),
            )
            self.session.add(event)
            self.session.flush()
        else:
            event.event_key = str(preview["event_key"])
            event.event_type = str(preview["event_type"])
            event.title = str(preview["title"])
            event.status = str(preview["status"])
            event.limited_tickets = int(preview["limited_tickets"])
            event.exclusive_commentary = bool(preview["exclusive_commentary"])
            event.global_broadcast = bool(preview["global_broadcast"])
            event.hype_score = float(preview["hype_score"])
            event.metadata_json = dict(preview.get("metadata") or {})
        return event

    def _mega_event_preview(
        self,
        *,
        match: GtexMatch,
        offer: dict[str, Any],
        fan_war: dict[str, Any],
        live_chat: dict[str, Any],
    ) -> dict[str, Any] | None:
        is_final = bool(offer.get("is_final"))
        sell_out = bool(dict(offer.get("sell_out_hype") or {}).get("triggered"))
        rivalry_heat = float(fan_war.get("rivalry_heat") or 0.0)
        moment_spike = float(live_chat.get("moment_spike_score") or 0.0)
        total_messages = int(live_chat.get("total_messages") or 0)
        if not any((is_final, sell_out, rivalry_heat >= 0.65, moment_spike >= 2.0, total_messages >= 8)):
            return None
        if is_final and rivalry_heat >= 0.6:
            event_type = "world_club_clash"
            title = "World Club Clash"
        elif is_final:
            event_type = "final_of_the_year"
            title = "Final of the Year"
        else:
            event_type = "legend_night"
            title = "Legend Night"
        hype_score = round(
            _clamp(
                0.58
                + (0.18 if is_final else 0.0)
                + (0.12 if sell_out else 0.0)
                + min(0.16, rivalry_heat * 0.18)
                + min(0.14, moment_spike * 0.06),
                0.0,
                1.0,
            ),
            4,
        )
        capacity = int(offer.get("capacity") or 0)
        limited_tickets = max(24, min(750, int(round(max(capacity, 40) * (0.12 + (hype_score * 0.12))))))
        return {
            "id": None,
            "event_key": f"mega:{match.id}:{event_type}",
            "match_id": match.id,
            "event_type": event_type,
            "title": title,
            "status": "live" if getattr(match.status, "value", str(match.status)) == "running" else "scheduled",
            "limited_tickets": limited_tickets,
            "exclusive_commentary": True,
            "global_broadcast": is_final or rivalry_heat >= 0.72 or moment_spike >= 2.2,
            "hype_score": hype_score,
            "metadata": {
                "match_title": self._match_title(match),
                "sell_out_triggered": sell_out,
                "rivalry_heat": rivalry_heat,
                "moment_spike_score": moment_spike,
            },
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        }

    def _upsert_conflict(
        self,
        *,
        match: GtexMatch,
        conflict_type: str,
        headline: str,
        club_id: str | None,
        manager_profile_id: str | None,
        severity: str,
        impact_score: float,
        triggers: dict[str, Any],
        impact: dict[str, Any],
        player_id: str | None = None,
    ) -> NarrativeConflict:
        conflict = self.session.scalar(
            select(NarrativeConflict).where(
                NarrativeConflict.match_id == match.id,
                NarrativeConflict.conflict_type == conflict_type,
            )
        )
        if conflict is None:
            conflict = NarrativeConflict(
                match_id=match.id,
                club_id=club_id,
                player_id=player_id,
                manager_profile_id=manager_profile_id,
                conflict_type=conflict_type,
                headline=headline,
                status="active",
                severity=severity,
                impact_score=round(float(impact_score), 4),
                triggers_json=dict(triggers),
                impact_json=dict(impact),
                metadata_json={},
            )
            self.session.add(conflict)
            self.session.flush()
        else:
            conflict.club_id = club_id
            conflict.player_id = player_id
            conflict.manager_profile_id = manager_profile_id
            conflict.headline = headline
            conflict.status = "active"
            conflict.severity = severity
            conflict.impact_score = round(float(impact_score), 4)
            conflict.triggers_json = dict(triggers)
            conflict.impact_json = dict(impact)
        return conflict

    def _upsert_market_shock(
        self,
        *,
        match: GtexMatch,
        shock_type: str,
        headline: str,
        club_id: str | None,
        magnitude: float,
        player_price_delta_bps: int,
        fan_sentiment_delta: float,
        betting_odds_delta_bps: int,
        impact: dict[str, Any],
        player_id: str | None = None,
    ) -> MarketShockEvent:
        shock = self.session.scalar(
            select(MarketShockEvent).where(
                MarketShockEvent.match_id == match.id,
                MarketShockEvent.shock_type == shock_type,
            )
        )
        if shock is None:
            shock = MarketShockEvent(
                match_id=match.id,
                club_id=club_id,
                player_id=player_id,
                shock_type=shock_type,
                headline=headline,
                status="active",
                magnitude=round(float(magnitude), 4),
                player_price_delta_bps=int(player_price_delta_bps),
                fan_sentiment_delta=round(float(fan_sentiment_delta), 4),
                betting_odds_delta_bps=int(betting_odds_delta_bps),
                impact_json=dict(impact),
                metadata_json={},
            )
            self.session.add(shock)
            self.session.flush()
        else:
            shock.club_id = club_id
            shock.player_id = player_id
            shock.headline = headline
            shock.status = "active"
            shock.magnitude = round(float(magnitude), 4)
            shock.player_price_delta_bps = int(player_price_delta_bps)
            shock.fan_sentiment_delta = round(float(fan_sentiment_delta), 4)
            shock.betting_odds_delta_bps = int(betting_odds_delta_bps)
            shock.impact_json = dict(impact)
        return shock

    def _upsert_legacy_snapshot(
        self,
        *,
        category: str,
        entity_type: str,
        entity_id: str,
        match_id: str | None,
        headline: str,
        score: float,
        metadata: dict[str, Any],
        entity_name: str | None = None,
    ) -> LegacySnapshot:
        snapshot = self.session.scalar(
            select(LegacySnapshot).where(
                LegacySnapshot.category == category,
                LegacySnapshot.entity_id == entity_id,
            )
        )
        if snapshot is None:
            snapshot = LegacySnapshot(
                category=category,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                match_id=match_id,
                season_key="lifetime",
                headline=headline,
                score=round(float(score), 4),
                rank_position=None,
                metadata_json=dict(metadata),
            )
            self.session.add(snapshot)
            self.session.flush()
        else:
            snapshot.entity_type = entity_type
            snapshot.entity_name = entity_name or snapshot.entity_name
            snapshot.match_id = match_id
            snapshot.headline = headline
            snapshot.score = round(float(score), 4)
            snapshot.metadata_json = dict(metadata)
        ranked = list(
            self.session.scalars(
                select(LegacySnapshot)
                .where(LegacySnapshot.category == category)
                .order_by(LegacySnapshot.score.desc(), LegacySnapshot.updated_at.desc())
            ).all()
        )
        for index, row in enumerate(ranked, start=1):
            row.rank_position = index
        return snapshot

    def _increment_weekly_war(self, *, club_id: str) -> None:
        tribe = self.session.scalar(select(FanTribe).where(FanTribe.club_id == club_id))
        if tribe is None:
            return
        metadata = dict(tribe.metadata_json or {})
        week_key = _utcnow().strftime("%Y-W%V")
        if metadata.get("weekly_war_key") != week_key:
            metadata["weekly_war_key"] = week_key
            metadata["weekly_wins"] = 0
        metadata["weekly_wins"] = int(metadata.get("weekly_wins") or 0) + 1
        tribe.metadata_json = metadata
        self._refresh_tribe_power(tribe)

    def _upsert_article(
        self,
        *,
        article_type: str,
        title: str,
        match_id: str | None,
        body: str,
        tags: list[str],
    ) -> NewsArticle:
        article = self.session.scalar(
            select(NewsArticle).where(NewsArticle.article_type == article_type, NewsArticle.title == title)
        )
        if article is None:
            article = NewsArticle(
                article_type=article_type,
                title=title,
                body=body,
                summary=body[:180],
                tags_json=list(tags),
                headline_variants_json={},
                related_match_id=match_id,
                trend_score=round(26.0 + (len(tags) * 5.5), 3),
                perception_delta=0.0,
                metadata_json={"source": "social_warfare"},
            )
            self.session.add(article)
            self.session.flush()
        else:
            article.body = body
            article.summary = body[:180]
            article.related_match_id = match_id
            article.tags_json = list(dict.fromkeys([*list(article.tags_json or []), *list(tags)]))
            article.metadata_json = {**dict(article.metadata_json or {}), "source": "social_warfare"}
        return article

    def _manager_name(self, manager: ManagerProfile | None) -> str:
        if manager is None:
            return "Unknown manager"
        return manager.name or manager.manager_id or manager.gtex_ai_id or f"Manager {manager.id[:8]}"

    def _match_title(self, match: GtexMatch) -> str:
        metadata = dict(match.metadata_json or {})
        match_context = dict(metadata.get("match_context") or {})
        home = str(metadata.get("home_label") or match_context.get("home_label") or "Home")
        away = str(metadata.get("away_label") or match_context.get("away_label") or "Away")
        return f"{home} vs {away}"


__all__ = ["GtexSocialWarfareService"]
