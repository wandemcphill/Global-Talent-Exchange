from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.community_engine import CompetitionWatchlist, LiveThread
from app.models.daily_challenge import DailyChallenge, DailyChallengeStatus
from app.models.discovery_engine import FeaturedRail, SavedSearch
from app.models.hosted_competition import UserHostedCompetition
from app.models.national_team import NationalTeamCompetition
from app.models.story_feed import StoryFeedItem
from app.models.user import User
from app.models.youth_prospect import YouthProspect


class DiscoveryEngineError(ValueError):
    pass


@dataclass(slots=True)
class DiscoveryEngineService:
    session: Session

    def seed_defaults(self) -> None:
        defaults = (
            {"rail_key": "featured_stories", "title": "Featured Stories", "rail_type": "story", "audience": "public", "query_hint": "world", "subtitle": "Big matches, giant killers, and rivalry sparks.", "display_order": 10, "metadata_json": {"icon": "newspaper"}},
            {"rail_key": "live_community", "title": "Live Community", "rail_type": "community", "audience": "public", "query_hint": "cup", "subtitle": "Threads buzzing around live and upcoming competitions.", "display_order": 20, "metadata_json": {"icon": "messages"}},
            {"rail_key": "prospect_radar", "title": "Prospect Radar", "rail_type": "prospect", "audience": "public", "query_hint": "academy", "subtitle": "Youth prospects and pipeline standouts worth watching.", "display_order": 30, "metadata_json": {"icon": "star"}},
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
        return {
            "featured_rails": featured_rails,
            "featured_items": featured_items,
            "recommended_items": deduped[:10],
            "live_now_items": live_now_items,
            "saved_searches": self.list_saved_searches(actor=actor),
        }

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
