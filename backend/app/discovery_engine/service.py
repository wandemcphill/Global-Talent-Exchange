from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cache.hot_paths import HotPathCache
from app.core.cache import CacheBackend, NullCacheBackend
from app.models.competition_match import CompetitionMatch
from app.models.community_engine import CompetitionWatchlist, LiveThread
from app.models.daily_challenge import DailyChallenge, DailyChallengeStatus
from app.models.discovery_engine import FeaturedRail, SavedSearch
from app.models.hosted_competition import UserHostedCompetition
from app.models.match_event import MatchEvent, MatchEventType
from app.models.national_team import NationalTeamCompetition
from app.models.spectator_session import SpectatorSession
from app.models.story_feed import StoryFeedItem
from app.models.user import User
from app.models.youth_prospect import YouthProspect


class DiscoveryEngineError(ValueError):
    pass


@dataclass(slots=True)
class DiscoveryEngineService:
    session: Session
    cache_backend: CacheBackend | None = None
    broadcast_runtime: Any | None = None

    def seed_defaults(self) -> None:
        defaults = (
            {"rail_key": "featured_stories", "title": "Featured Stories", "rail_type": "story", "audience": "public", "query_hint": "world", "subtitle": "Big matches, giant killers, and rivalry sparks.", "display_order": 10, "metadata_json": {"icon": "newspaper"}},
            {"rail_key": "live_community", "title": "Live Community", "rail_type": "community", "audience": "public", "query_hint": "cup", "subtitle": "Threads buzzing around live and upcoming competitions.", "display_order": 20, "metadata_json": {"icon": "messages"}},
            {"rail_key": "prospect_radar", "title": "Prospect Radar", "rail_type": "prospect", "audience": "public", "query_hint": "academy", "subtitle": "Youth prospects and pipeline standouts worth watching.", "display_order": 30, "metadata_json": {"icon": "star"}},
            {"rail_key": "broadcast_now", "title": "Broadcast Now", "rail_type": "broadcast", "audience": "public", "query_hint": "live", "subtitle": "Network channels, auto-switched fixtures, and the Match of the Moment.", "display_order": 15, "metadata_json": {"icon": "tv"}},
        )
        for item in defaults:
            existing = self.session.scalar(select(FeaturedRail).where(FeaturedRail.rail_key == item["rail_key"]))
            if existing is None:
                self.session.add(FeaturedRail(**item))
        self.session.flush()

    def list_featured_rails(self, *, active_only: bool = True) -> list[FeaturedRail]:
        stmt = select(FeaturedRail)
        if active_only:
            stmt = stmt.where(FeaturedRail.active.is_(True))
        stmt = stmt.order_by(FeaturedRail.display_order.asc(), FeaturedRail.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def upsert_featured_rail(self, *, actor: User, payload) -> FeaturedRail:
        rail = self.session.scalar(select(FeaturedRail).where(FeaturedRail.rail_key == payload.rail_key))
        if rail is None:
            rail = FeaturedRail(rail_key=payload.rail_key, created_by_user_id=actor.id)
            self.session.add(rail)
        rail.title = payload.title
        rail.rail_type = payload.rail_type
        rail.audience = payload.audience
        rail.query_hint = payload.query_hint
        rail.subtitle = payload.subtitle
        rail.display_order = payload.display_order
        rail.active = payload.active
        rail.metadata_json = payload.metadata_json
        self.session.flush()
        return rail

    def save_search(self, *, actor: User, query: str, entity_scope: str, alerts_enabled: bool, metadata_json: dict[str, Any]) -> SavedSearch:
        existing = self.session.scalar(select(SavedSearch).where(SavedSearch.user_id == actor.id, SavedSearch.query == query))
        if existing is not None:
            existing.entity_scope = entity_scope
            existing.alerts_enabled = alerts_enabled
            existing.metadata_json = metadata_json
            self.session.flush()
            return existing
        item = SavedSearch(user_id=actor.id, query=query, entity_scope=entity_scope, alerts_enabled=alerts_enabled, metadata_json=metadata_json)
        self.session.add(item)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DiscoveryEngineError("That search has already been saved.") from exc
        return item

    def list_saved_searches(self, *, actor: User) -> list[SavedSearch]:
        stmt = select(SavedSearch).where(SavedSearch.user_id == actor.id).order_by(SavedSearch.updated_at.desc())
        return list(self.session.scalars(stmt).all())

    def delete_saved_search(self, *, actor: User, search_id: str) -> None:
        item = self.session.get(SavedSearch, search_id)
        if item is None or item.user_id != actor.id:
            raise DiscoveryEngineError("Saved search was not found.")
        self.session.delete(item)
        self.session.flush()

    def search(self, *, actor: User | None, query: str, entity_scope: str = "all", limit: int = 20) -> list[dict[str, Any]]:
        term = query.strip()
        if len(term) < 2:
            return []
        query_lower = term.lower()
        output: list[dict[str, Any]] = []
        scopes = {entity_scope} if entity_scope != "all" else {"stories", "competitions", "threads", "prospects", "challenges"}
        if "stories" in scopes:
            for item in self.session.scalars(select(StoryFeedItem).where(or_(StoryFeedItem.title.ilike(f"%{term}%"), StoryFeedItem.body.ilike(f"%{term}%"))).order_by(StoryFeedItem.featured.desc(), StoryFeedItem.created_at.desc()).limit(limit)).all():
                output.append({"item_type": "story", "item_id": item.id, "title": item.title, "subtitle": item.body[:140], "score": self._score(query_lower, item.title, item.body), "metadata": item.metadata_json})
        if "competitions" in scopes:
            for item in self.session.scalars(select(UserHostedCompetition).where(or_(UserHostedCompetition.title.ilike(f"%{term}%"), UserHostedCompetition.description.ilike(f"%{term}%"))).order_by(UserHostedCompetition.created_at.desc()).limit(limit)).all():
                output.append({"item_type": "hosted_competition", "item_id": item.id, "title": item.title, "subtitle": item.description[:140], "score": self._score(query_lower, item.title, item.description), "metadata": {"status": str(item.status), "slug": item.slug}})
            for item in self.session.scalars(select(NationalTeamCompetition).where(or_(NationalTeamCompetition.title.ilike(f"%{term}%"), NationalTeamCompetition.season_label.ilike(f"%{term}%"))).order_by(NationalTeamCompetition.created_at.desc()).limit(limit)).all():
                output.append({"item_type": "national_team_competition", "item_id": item.id, "title": item.title, "subtitle": item.season_label, "score": self._score(query_lower, item.title, item.season_label), "metadata": {"status": item.status, "key": item.key}})
        if "threads" in scopes:
            for item in self.session.scalars(select(LiveThread).where(LiveThread.title.ilike(f"%{term}%")).order_by(LiveThread.last_message_at.desc().nullslast(), LiveThread.created_at.desc()).limit(limit)).all():
                output.append({"item_type": "live_thread", "item_id": item.id, "title": item.title, "subtitle": item.competition_key or "community", "score": self._score(query_lower, item.title, item.competition_key or ""), "metadata": item.metadata_json})
        if "prospects" in scopes:
            for item in self.session.scalars(select(YouthProspect).where(or_(YouthProspect.player_name.ilike(f"%{term}%"), YouthProspect.country_code.ilike(f"%{term}%"))).order_by(YouthProspect.created_at.desc()).limit(limit)).all():
                output.append({"item_type": "prospect", "item_id": item.id, "title": item.player_name, "subtitle": f"{item.position_group} â€¢ {item.country_code}", "score": self._score(query_lower, item.player_name, item.country_code), "metadata": {"position_group": item.position_group, "potential_band": item.potential_band}})
        if "challenges" in scopes:
            for item in self.session.scalars(select(DailyChallenge).where(DailyChallenge.status == DailyChallengeStatus.ACTIVE, or_(DailyChallenge.challenge_key.ilike(f"%{term}%"), DailyChallenge.title.ilike(f"%{term}%"))).order_by(DailyChallenge.updated_at.desc()).limit(limit)).all():
                output.append({"item_type": "challenge", "item_id": item.id, "title": item.title, "subtitle": item.description[:140], "score": self._score(query_lower, item.title, item.description), "metadata": {"challenge_key": item.challenge_key}})
        output.sort(key=lambda item: (item["score"], item["title"]), reverse=True)
        return output[:limit]

    def home(self, *, actor: User) -> dict[str, Any]:
        featured_rails = self.list_featured_rails(active_only=True)
        featured_items = self.search(actor=actor, query="cup", entity_scope="all", limit=8)
        live_now_items = self._live_match_items(limit=8)
        broadcast_items: list[dict[str, Any]] = []
        match_of_the_moment: dict[str, Any] | None = None
        if not live_now_items:
            live_now_items = [
                {"item_type": "live_thread", "item_id": item.id, "title": item.title, "subtitle": item.competition_key or "community", "score": 1.0, "metadata": item.metadata_json}
                for item in self.session.scalars(select(LiveThread).order_by(LiveThread.last_message_at.desc().nullslast(), LiveThread.created_at.desc()).limit(8)).all()
            ]
        recommended_items: list[dict[str, Any]] = []
        watchlist = list(self.session.scalars(select(CompetitionWatchlist).where(CompetitionWatchlist.user_id == actor.id).limit(6)).all())
        for item in watchlist:
            recommended_items.extend(self.search(actor=actor, query=item.competition_title, entity_scope="competitions", limit=3))
            recommended_items.extend(self.search(actor=actor, query=item.competition_title, entity_scope="stories", limit=2))
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in recommended_items:
            marker = (item["item_type"], item["item_id"])
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(item)
        if not deduped:
            deduped = self.search(actor=actor, query="world", entity_scope="all", limit=8)
        if self.broadcast_runtime is not None:
            broadcast_home = self.broadcast_runtime.home()
            for channel in broadcast_home.channels:
                broadcast_items.append(
                    {
                        "item_type": "broadcast_channel",
                        "item_id": channel.channel_id,
                        "title": channel.name,
                        "subtitle": channel.description or (channel.current_program.subtitle if channel.current_program is not None else ""),
                        "rail_key": "broadcast_now",
                        "score": float(channel.current_program.score if channel.current_program is not None else 0.0),
                        "metadata": {
                            "channel_id": channel.channel_id,
                            "channel_type": channel.channel_type,
                            "viewer_count": channel.viewer_count,
                            "featured_match_id": channel.featured_match_id,
                            "watch_route": f"/broadcast/{channel.channel_id}",
                        },
                    }
                )
            if broadcast_home.match_of_the_moment is not None:
                match_of_the_moment = {
                    "item_type": "broadcast_match",
                    "item_id": str(broadcast_home.match_of_the_moment.match_id or broadcast_home.match_of_the_moment.slot_id),
                    "title": broadcast_home.match_of_the_moment.title,
                    "subtitle": broadcast_home.match_of_the_moment.subtitle,
                    "rail_key": "broadcast_now",
                    "score": float(broadcast_home.match_of_the_moment.score),
                    "metadata": {
                        "channel_id": broadcast_home.match_of_the_moment.channel_id,
                        "match_id": broadcast_home.match_of_the_moment.match_id,
                        "watch_route": broadcast_home.match_of_the_moment.watch_route,
                        "replay_route": broadcast_home.match_of_the_moment.replay_route,
                        "program_type": broadcast_home.match_of_the_moment.program_type,
                    },
                }
        return {
            "featured_rails": featured_rails,
            "featured_items": featured_items,
            "recommended_items": deduped[:10],
            "live_now_items": live_now_items,
            "broadcast_items": broadcast_items[:8],
            "match_of_the_moment": match_of_the_moment,
            "saved_searches": self.list_saved_searches(actor=actor),
        }

    def _live_match_items(self, *, limit: int) -> list[dict[str, Any]]:
        hot_cache = HotPathCache(self.cache_backend or NullCacheBackend())
        active_match_ids = hot_cache.list_active_matches()
        if not active_match_ids:
            return []
        matches = {
            item.id: item
            for item in self.session.scalars(
                select(CompetitionMatch).where(CompetitionMatch.id.in_(active_match_ids))
            ).all()
        }
        viewer_counts = {
            str(match_id): int(count)
            for match_id, count in self.session.execute(
                select(SpectatorSession.match_id, func.count(SpectatorSession.id))
                .where(SpectatorSession.match_id.in_(active_match_ids))
                .group_by(SpectatorSession.match_id)
            ).all()
        }
        goal_counts = {
            str(match_id): int(count)
            for match_id, count in self.session.execute(
                select(MatchEvent.match_id, func.count(MatchEvent.id))
                .where(
                    MatchEvent.match_id.in_(active_match_ids),
                    MatchEvent.event_type == MatchEventType.GOAL,
                )
                .group_by(MatchEvent.match_id)
            ).all()
        }
        ranked: list[tuple[int, int, int, dict[str, Any]]] = []
        for match_id in active_match_ids:
            state = hot_cache.get_match_state(match_id)
            if not isinstance(state, dict) or not bool(state.get("is_live")):
                continue
            match = matches.get(match_id)
            if match is None:
                continue
            metadata_json = dict(match.metadata_json or {}) if match is not None else {}
            replay_payload = metadata_json.get("replay_payload")
            summary = replay_payload.get("summary") if isinstance(replay_payload, dict) else {}
            home_stats = summary.get("home_stats") if isinstance(summary, dict) else {}
            away_stats = summary.get("away_stats") if isinstance(summary, dict) else {}
            snapshot = state.get("snapshot") if isinstance(state.get("snapshot"), dict) else {}
            score = snapshot.get("score") if isinstance(snapshot.get("score"), dict) else {}
            viewer_count = viewer_counts.get(match_id, int(state.get("spectator_count") or 0))
            goal_activity = goal_counts.get(match_id, 0)
            is_final = bool(metadata_json.get("competition_context", {}).get("is_final")) if isinstance(metadata_json.get("competition_context"), dict) else False
            if not is_final and match is not None:
                stage_label = str(match.stage or "").strip().lower()
                is_final = "final" in stage_label
            home_team_name = str(home_stats.get("team_name") or metadata_json.get("home_team_name") or "Home")
            away_team_name = str(away_stats.get("team_name") or metadata_json.get("away_team_name") or "Away")
            minute = int(snapshot.get("current_minute") or 0)
            item = {
                "item_type": "live_match",
                "item_id": match_id,
                "title": f"{home_team_name} vs {away_team_name}",
                "subtitle": f"{minute}' • {viewer_count} watching",
                "score": float((viewer_count * 10) + (25 if is_final else 0) + (goal_activity * 6)),
                "metadata": {
                    "match_id": match_id,
                    "home_team_name": home_team_name,
                    "away_team_name": away_team_name,
                    "home_score": int(score.get("home") or 0),
                    "away_score": int(score.get("away") or 0),
                    "minute": minute,
                    "viewer_count": viewer_count,
                    "goal_activity": goal_activity,
                    "featured": bool(is_final or goal_activity > 0 or viewer_count >= 10),
                    "is_final": is_final,
                    "status": snapshot.get("status") or "live",
                    "watch_route": f"/matches/{match_id}/watch",
                    "replay_route": f"/api/matches/{match_id}/replay",
                },
            }
            ranked.append((viewer_count, 1 if is_final else 0, goal_activity, item))
        ranked.sort(key=lambda entry: (entry[0], entry[1], entry[2], entry[3]["title"]), reverse=True)
        return [entry[3] for entry in ranked[:limit]]

    @staticmethod
    def _score(term: str, *texts: str | None) -> float:
        score = 0.0
        for text in texts:
            if not text:
                continue
            lowered = text.lower()
            if lowered == term:
                score += 8.0
            elif term in lowered:
                score += 4.0
            score += min(len(term) / max(len(lowered), 1), 0.5)
        return score
