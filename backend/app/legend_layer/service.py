from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.global_memory.models import PlayerHistory, UserDynasty
from app.ingestion.models import Player
from app.leaderboards.season_service import SeasonService
from app.models.club_cashflow_summary import ClubCashflowSummary
from app.models.club_profile import ClubProfile
from app.models.club_social import SocialFollow
from app.models.commentary_event import CommentaryEvent
from app.models.news_article import NewsArticle
from app.models.player_fan_reaction import PlayerFanReaction
from app.models.player_interview import PlayerInterview
from app.models.player_personality import PlayerPersonality
from app.models.player_story import PlayerStory
from app.models.player_token_market import PlayerShareMarket
from app.models.prestige_rating import PrestigeRating
from app.models.user import User
from app.story_feed_engine.service import StoryFeedService

SEASONAL_SCOPE = "seasonal"
LIFETIME_SCOPE = "lifetime"
LIFETIME_SEASON_KEY = "lifetime"
PLAYER_KEY = "leaderboard:global:players"
CLUB_KEY = "leaderboard:global:clubs"
USER_KEY = "leaderboard:global:users"
NATIONAL_TEAM_KEY = "leaderboard:global:national_teams"


class LegendLayerError(ValueError):
    pass


class LegendLayerNotFoundError(LegendLayerError):
    pass


@dataclass(slots=True)
class LegendLayerService:
    session: Session
    redis_url: str | None = None
    _redis: Redis | None = None
    _redis_attempted: bool = False

    def process_match_completed(
        self,
        payload: dict[str, Any],
        *,
        event_id: str,
    ) -> list[NewsArticle]:
        context = self._build_match_context(payload)
        articles = self._generate_articles(context=context, event_id=event_id)
        standout_stat = self._standout_stat(context["player_stats"])
        controversy_stat = self._controversy_stat(context["player_stats"])
        if standout_stat is not None:
            self._apply_player_narrative(
                stat=standout_stat,
                context=context,
                article=self._article_for_player(articles, standout_stat.get("player_id")),
            )
        if controversy_stat is not None and controversy_stat.get("player_id") != (standout_stat or {}).get("player_id"):
            self._apply_player_narrative(
                stat=controversy_stat,
                context=context,
                article=self._article_for_player(articles, controversy_stat.get("player_id")),
            )
        self._apply_prestige_updates(context=context, articles=articles)
        return articles

    def list_news_feed(self, *, current_user: User | None, limit: int = 25) -> list[NewsArticle]:
        resolved_limit = max(1, int(limit))
        pool_limit = max(resolved_limit * 6, 25)
        articles = list(
            self.session.scalars(
                select(NewsArticle)
                .order_by(NewsArticle.created_at.desc(), NewsArticle.trend_score.desc())
                .limit(pool_limit)
            ).all()
        )
        if current_user is None:
            return sorted(
                articles,
                key=lambda article: (float(article.trend_score or 0.0), article.created_at),
                reverse=True,
            )[:resolved_limit]

        owned_club_ids = {
            club_id
            for club_id in self.session.scalars(
                select(ClubProfile.id).where(ClubProfile.owner_user_id == current_user.id)
            ).all()
        }
        follows = list(self.session.scalars(select(SocialFollow).where(SocialFollow.user_id == current_user.id)).all())
        followed_club_ids = {item.club_id for item in follows if item.club_id}
        followed_player_ids = {item.player_id for item in follows if item.player_id}
        owned_player_ids: set[str] = set()
        if owned_club_ids:
            owned_player_ids = {
                player_id
                for player_id in self.session.scalars(
                    select(Player.id).where(Player.current_club_profile_id.in_(owned_club_ids))
                ).all()
            }

        def _score(article: NewsArticle) -> float:
            age_hours = max(
                0.0,
                (self._now() - self._normalize_timestamp(article.created_at)).total_seconds() / 3600.0,
            )
            recency = max(0.0, 24.0 - age_hours)
            relevance = 0.0
            if article.related_user_id == current_user.id:
                relevance += 70.0
            if article.related_club_id and article.related_club_id in owned_club_ids:
                relevance += 45.0
            if article.related_club_id and article.related_club_id in followed_club_ids:
                relevance += 24.0
            if article.related_player_id and article.related_player_id in owned_player_ids:
                relevance += 30.0
            if article.related_player_id and article.related_player_id in followed_player_ids:
                relevance += 22.0
            if article.article_type == "breaking_news":
                relevance += 6.0
            return float(article.trend_score or 0.0) + recency + relevance

        return sorted(articles, key=_score, reverse=True)[:resolved_limit]

    def get_article(self, article_id: str) -> NewsArticle:
        article = self.session.get(NewsArticle, article_id)
        if article is None:
            raise LegendLayerNotFoundError(f"News article {article_id} was not found.")
        return article

    def get_global_rankings(
        self,
        *,
        scope: str = LIFETIME_SCOPE,
        season_key: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        resolved_scope, resolved_season_key = self._resolve_scope(scope=scope, season_key=season_key)
        return {
            "scope": resolved_scope,
            "season_key": resolved_season_key,
            "generated_at": self._now(),
            "players": self._list_rankings("player", resolved_scope, resolved_season_key, limit),
            "clubs": self._list_rankings("club", resolved_scope, resolved_season_key, limit),
            "users": self._list_rankings("user", resolved_scope, resolved_season_key, limit),
            "national_teams": self._list_rankings("national_team", resolved_scope, resolved_season_key, limit),
        }

    def get_rankings(
        self,
        *,
        entity_type: str,
        scope: str = LIFETIME_SCOPE,
        season_key: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        resolved_scope, resolved_season_key = self._resolve_scope(scope=scope, season_key=season_key)
        return {
            "entity_type": entity_type,
            "scope": resolved_scope,
            "season_key": resolved_season_key,
            "generated_at": self._now(),
            "entries": self._list_rankings(entity_type, resolved_scope, resolved_season_key, limit),
        }

    def get_player_personality_profile(self, player_id: str) -> dict[str, Any]:
        player = self.session.get(Player, player_id)
        if player is None:
            raise LegendLayerNotFoundError(f"Player {player_id} was not found.")
        personality = self._ensure_personality(player)
        return {
            "player_id": player.id,
            "player_name": player.canonical_display_name or player.full_name,
            "aggression": int(personality.aggression),
            "confidence": int(personality.confidence),
            "loyalty": int(personality.loyalty),
            "ego": int(personality.ego),
            "consistency": int(personality.consistency),
            "clutch_factor": int(personality.clutch_factor),
            "competitiveness": int(personality.competitiveness),
            "professionalism": int(personality.professionalism),
            "media_appetite": int(personality.media_appetite),
            "metadata_json": dict(personality.metadata_json or {}),
            "updated_at": personality.updated_at,
        }

    def list_player_interviews(self, player_id: str, *, limit: int = 20) -> list[PlayerInterview]:
        player = self.session.get(Player, player_id)
        if player is None:
            raise LegendLayerNotFoundError(f"Player {player_id} was not found.")
        return list(
            self.session.scalars(
                select(PlayerInterview)
                .where(PlayerInterview.player_id == player_id)
                .order_by(PlayerInterview.created_at.desc(), PlayerInterview.updated_at.desc())
                .limit(max(1, int(limit)))
            ).all()
        )

    def _build_match_context(self, payload: dict[str, Any]) -> dict[str, Any]:
        match_id = str(payload.get("fixture_id") or payload.get("match_id") or "").strip()
        if not match_id:
            raise LegendLayerError("Narrative engine requires fixture_id or match_id in the payload.")
        commentary = list(
            self.session.scalars(
                select(CommentaryEvent)
                .where(CommentaryEvent.match_id == match_id)
                .order_by(CommentaryEvent.minute.asc(), CommentaryEvent.created_at.asc())
            ).all()
        )
        return {
            "match_id": match_id,
            "season_key": self._event_season_key(payload),
            "competition_id": self._clean(payload.get("competition_id")),
            "competition_type": self._clean(payload.get("competition_type")) or "league",
            "home_club_id": self._clean(payload.get("home_club_id")),
            "away_club_id": self._clean(payload.get("away_club_id")),
            "home_club_name": self._clean(payload.get("home_club_name")) or "Home Club",
            "away_club_name": self._clean(payload.get("away_club_name")) or "Away Club",
            "home_goals": int(payload.get("home_goals") or 0),
            "away_goals": int(payload.get("away_goals") or 0),
            "winner_team_id": self._clean(payload.get("winner_team_id")),
            "home_user_id": self._clean(payload.get("home_user_id")),
            "away_user_id": self._clean(payload.get("away_user_id")),
            "user_ids": [str(item) for item in payload.get("user_ids") or [] if str(item).strip()],
            "is_final": bool(payload.get("is_final")),
            "player_stats": [item for item in payload.get("player_stats") or [] if isinstance(item, dict)],
            "commentary": commentary,
        }

    def _generate_articles(self, *, context: dict[str, Any], event_id: str) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        standout = self._standout_stat(context["player_stats"])
        controversy = self._controversy_stat(context["player_stats"])

        articles.append(self._create_match_report(context=context, standout=standout, event_id=event_id))
        if standout is not None:
            articles.append(self._create_player_story(context=context, standout=standout, event_id=event_id))
        if controversy is not None:
            articles.append(self._create_controversy_story(context=context, controversy=controversy, event_id=event_id))

        for article in articles:
            self._publish_article_to_story_feed(article)
        return articles

    def _create_match_report(
        self,
        *,
        context: dict[str, Any],
        standout: dict[str, Any] | None,
        event_id: str,
    ) -> NewsArticle:
        late_drama = self._late_drama(context["commentary"])
        winner_name = self._winner_name(context)
        scoreline = self._scoreline(context)
        variants = {
            "dramatic": (
                f"Late Drama Sends {winner_name} Through"
                if late_drama and winner_name
                else (
                    f"{winner_name} Take the Points in {scoreline}"
                    if winner_name
                    else f"{context['home_club_name']} and {context['away_club_name']} Share the Spoils"
                )
            ),
            "neutral": f"{context['home_club_name']} {context['home_goals']}-{context['away_goals']} {context['away_club_name']}",
            "click_worthy": (
                f"{winner_name} Seize Control as {scoreline} Delivers Another Twist"
                if winner_name
                else f"{scoreline}: Why This Draw Still Changes the Table"
            ),
        }
        standout_line = ""
        related_player_id = None
        if standout is not None:
            related_player_id = self._clean(standout.get("player_id"))
            contribution_parts = []
            goals = int(standout.get("goals") or 0)
            assists = int(standout.get("assists") or 0)
            if goals:
                contribution_parts.append(f"{goals} goal{'s' if goals != 1 else ''}")
            if assists:
                contribution_parts.append(f"{assists} assist{'s' if assists != 1 else ''}")
            if contribution_parts:
                standout_line = (
                    f"{standout.get('player_name') or 'A standout performer'} supplied "
                    + " and ".join(contribution_parts)
                    + "."
                )
        commentary_excerpt = self._commentary_excerpt(context["commentary"])
        body = (
            f"{context['home_club_name']} and {context['away_club_name']} closed out a {scoreline} result in a "
            f"{'final' if context['is_final'] else context['competition_type']} fixture.\n\n"
            f"{standout_line or 'The result was built from the live match stats and broadcast log, not static copy.'}\n\n"
            f"{commentary_excerpt or 'No extra narrative was injected beyond the recorded match events and final statistics.'}"
        ).strip()
        article = NewsArticle(
            article_type="match_report",
            title=variants["dramatic"],
            body=body,
            summary=f"{scoreline}. {winner_name + ' won.' if winner_name else 'Points were shared.'}".strip(),
            tags_json=self._clean_tags(
                [
                    "match_report",
                    context["competition_type"],
                    "final" if context["is_final"] else None,
                    context["home_club_name"],
                    context["away_club_name"],
                ]
            ),
            headline_variants_json=variants,
            related_match_id=context["match_id"],
            related_player_id=related_player_id,
            related_club_id=self._winner_team_id(context),
            related_user_id=self._winner_user_id(context),
            trend_score=58.0 + (12.0 if context["is_final"] else 0.0) + (6.0 if late_drama else 0.0),
            perception_delta=8.0 if winner_name else 2.0,
            metadata_json={
                "event_id": event_id,
                "scoreline": scoreline,
                "commentary_excerpt": commentary_excerpt,
                "winner_team_id": context["winner_team_id"],
            },
        )
        self.session.add(article)
        self.session.flush()
        return article

    def _create_player_story(
        self,
        *,
        context: dict[str, Any],
        standout: dict[str, Any],
        event_id: str,
    ) -> NewsArticle:
        player_name = str(standout.get("player_name") or "Standout player")
        team_name = str(standout.get("team_name") or self._team_name_for_player(context, standout))
        goals = int(standout.get("goals") or 0)
        assists = int(standout.get("assists") or 0)
        rating = float(standout.get("rating") or 0.0)
        player_id = self._clean(standout.get("player_id"))
        player = self.session.get(Player, player_id) if player_id else None
        story = (
            self.session.scalar(select(PlayerStory).where(PlayerStory.player_id == player.id))
            if player is not None
            else None
        )
        is_rise = story is None or float(story.narrative_score or 0.0) < 65.0
        article_type = "rise_of_a_star" if is_rise else "player_spotlight"
        variants = {
            "dramatic": f"{player_name} Drives {team_name} Forward",
            "neutral": f"{player_name} leads {team_name} with {goals} goals and {assists} assists",
            "click_worthy": f"Is {player_name} the next face of {team_name}?",
        }
        history_hook = self._history_hook(player_id)
        body = (
            f"{player_name} shaped the result for {team_name} with {goals} goal{'s' if goals != 1 else ''} "
            f"and {assists} assist{'s' if assists != 1 else ''}, finishing with a {rating:.1f} rating.\n\n"
            f"{history_hook or 'The spotlight article is built from the live match output, player performance, and stored memory only.'}"
        )
        related_club_id = self._clean(standout.get("team_id"))
        article = NewsArticle(
            article_type=article_type,
            title=variants["dramatic"],
            body=body,
            summary=f"{player_name} posted a {rating:.1f} rating for {team_name}.",
            tags_json=self._clean_tags([article_type, player_name, team_name, "trending_player"]),
            headline_variants_json=variants,
            related_match_id=context["match_id"],
            related_player_id=player_id,
            related_club_id=related_club_id,
            related_user_id=self._club_owner_id(related_club_id),
            trend_score=54.0 + (goals * 8.0) + (assists * 5.0) + (rating * 2.0),
            perception_delta=12.0 + (goals * 3.0) + (assists * 2.0),
            metadata_json={
                "event_id": event_id,
                "player_rating": rating,
                "goals": goals,
                "assists": assists,
                "team_id": related_club_id,
            },
        )
        self.session.add(article)
        self.session.flush()
        return article

    def _create_controversy_story(
        self,
        *,
        context: dict[str, Any],
        controversy: dict[str, Any],
        event_id: str,
    ) -> NewsArticle:
        player_name = str(controversy.get("player_name") or "Unnamed player")
        team_name = str(controversy.get("team_name") or self._team_name_for_player(context, controversy))
        rating = float(controversy.get("rating") or 0.0)
        red_card = bool(controversy.get("red_card"))
        yellow_cards = int(controversy.get("yellow_cards") or 0)
        variants = {
            "dramatic": f"Pressure Builds Around {player_name} After Rough Night",
            "neutral": f"{player_name} draws reaction after {team_name} performance",
            "click_worthy": f"Fans Turn on {player_name}: What Went Wrong?",
        }
        body = (
            f"{player_name} came under pressure after finishing the match with a {rating:.1f} rating"
            f"{' and a red card' if red_card else ''}"
            f"{f' plus {yellow_cards} yellow cards' if yellow_cards and not red_card else ''}.\n\n"
            f"The controversy layer is triggered by the recorded performance data and player personality profile, not static scripting."
        )
        related_club_id = self._clean(controversy.get("team_id"))
        article = NewsArticle(
            article_type="breaking_news",
            title=variants["dramatic"],
            body=body,
            summary=f"{player_name} is facing criticism after the latest result.",
            tags_json=self._clean_tags(["breaking_news", "controversy", player_name, team_name]),
            headline_variants_json=variants,
            related_match_id=context["match_id"],
            related_player_id=self._clean(controversy.get("player_id")),
            related_club_id=related_club_id,
            related_user_id=self._club_owner_id(related_club_id),
            trend_score=68.0 + (10.0 if red_card else 0.0),
            perception_delta=-10.0 - (5.0 if red_card else 0.0),
            metadata_json={
                "event_id": event_id,
                "player_rating": rating,
                "red_card": red_card,
                "yellow_cards": yellow_cards,
            },
        )
        self.session.add(article)
        self.session.flush()
        return article

    def _publish_article_to_story_feed(self, article: NewsArticle) -> None:
        StoryFeedService(self.session).publish(
            story_type="news_article",
            title=article.title,
            body=article.summary or article.body[:280],
            audience="public",
            subject_type="news_article",
            subject_id=article.id,
            metadata_json={
                "article_type": article.article_type,
                "related_match_id": article.related_match_id,
                "related_player_id": article.related_player_id,
                "related_club_id": article.related_club_id,
            },
            featured=article.article_type in {"breaking_news", "rise_of_a_star"},
            published_by_user_id=article.related_user_id,
        )

    def _apply_player_narrative(
        self,
        *,
        stat: dict[str, Any],
        context: dict[str, Any],
        article: NewsArticle | None,
    ) -> None:
        player_id = self._clean(stat.get("player_id"))
        if not player_id:
            return
        player = self.session.get(Player, player_id)
        if player is None:
            return
        personality = self._ensure_personality(player)
        shift = self._evolve_personality(player=player, personality=personality, stat=stat, context=context)
        story = self._ensure_player_story(player)
        story.narrative_score = max(0.0, float(story.narrative_score or 0.0) + shift["narrative_delta"])
        story.chapters = {
            **dict(story.chapters or {}),
            "last_match": {
                "match_id": context["match_id"],
                "article_id": article.id if article is not None else None,
                "confidence_delta": round(shift["confidence_delta"], 2),
                "ego_delta": round(shift["ego_delta"], 2),
                "clutch_delta": round(shift["clutch_delta"], 2),
            },
        }
        self.session.add(
            self._build_player_interview(
                player=player,
                personality=personality,
                stat=stat,
                context=context,
                article=article,
            )
        )
        fan_reaction = self._build_fan_reaction(
            player=player,
            personality=personality,
            stat=stat,
            context=context,
            article=article,
        )
        if fan_reaction is not None:
            self.session.add(fan_reaction)
        self._apply_market_reaction(player=player, article=article, stat=stat)
        self.session.flush()

    def _apply_prestige_updates(self, *, context: dict[str, Any], articles: list[NewsArticle]) -> None:
        touched: set[tuple[str, str, str]] = set()
        season_key = context["season_key"]
        scopes = ((SEASONAL_SCOPE, season_key), (LIFETIME_SCOPE, LIFETIME_SEASON_KEY))
        winner_team_id = context["winner_team_id"]
        draw = winner_team_id is None and context["home_goals"] == context["away_goals"]
        article_perception: dict[str, float] = {}
        for article in articles:
            if article.related_player_id:
                article_perception[article.related_player_id] = article_perception.get(
                    article.related_player_id, 0.0
                ) + float(article.perception_delta or 0.0)
            if article.related_club_id:
                article_perception[article.related_club_id] = article_perception.get(
                    article.related_club_id, 0.0
                ) + float(article.perception_delta or 0.0)
            if article.related_user_id:
                article_perception[article.related_user_id] = article_perception.get(
                    article.related_user_id, 0.0
                ) + float(article.perception_delta or 0.0)

        for stat in context["player_stats"]:
            player_id = self._clean(stat.get("player_id"))
            team_id = self._clean(stat.get("team_id"))
            if not player_id or not team_id:
                continue
            team_result = "draw" if draw else "win" if winner_team_id == team_id else "loss"
            development_delta = (
                max(float(stat.get("rating") or 0.0) - 6.0, 0.0) * 6.0
                + (int(stat.get("goals") or 0) * 8.0)
                + (int(stat.get("assists") or 0) * 6.0)
                + (8.0 if self._is_big_moment(stat=stat, context=context) else 0.0)
            )
            trophy_delta = 1.0 if context["is_final"] and team_result == "win" else 0.0
            earnings_value = self._player_earnings_value(player_id, development_delta)
            perception_delta = article_perception.get(player_id, 0.0)
            for scope, scope_season_key in scopes:
                self._update_prestige_row(
                    entity_type="player",
                    entity_id=player_id,
                    entity_name=str(stat.get("player_name") or player_id),
                    scope=scope,
                    season_key=scope_season_key,
                    result=team_result,
                    trophy_delta=trophy_delta,
                    development_delta=development_delta,
                    earnings_value=earnings_value,
                    difficulty_delta=self._difficulty_delta(context=context),
                    perception_delta=perception_delta,
                    metadata_updates={
                        "goals": int(stat.get("goals") or 0),
                        "assists": int(stat.get("assists") or 0),
                        "saves": int(stat.get("saves") or 0),
                        "team_id": team_id,
                        "match_id": context["match_id"],
                    },
                )
                touched.add(("player", scope, scope_season_key))

        for club_id, club_name, team_stats in (
            (context["home_club_id"], context["home_club_name"], self._team_stats(context, context["home_club_id"])),
            (context["away_club_id"], context["away_club_name"], self._team_stats(context, context["away_club_id"])),
        ):
            if not club_id:
                continue
            team_result = "draw" if draw else "win" if winner_team_id == club_id else "loss"
            development_delta = sum(
                max(float(item.get("rating") or 0.0) - 6.0, 0.0) * 2.5
                + (int(item.get("goals") or 0) * 3.0)
                + (int(item.get("assists") or 0) * 2.0)
                for item in team_stats
            )
            trophy_delta = 1.0 if context["is_final"] and team_result == "win" else 0.0
            earnings_value = self._club_earnings_value(club_id)
            perception_delta = article_perception.get(club_id, 0.0)
            for scope, scope_season_key in scopes:
                self._update_prestige_row(
                    entity_type="club",
                    entity_id=club_id,
                    entity_name=club_name or club_id,
                    scope=scope,
                    season_key=scope_season_key,
                    result=team_result,
                    trophy_delta=trophy_delta,
                    development_delta=development_delta,
                    earnings_value=earnings_value,
                    difficulty_delta=self._difficulty_delta(context=context),
                    perception_delta=perception_delta,
                    metadata_updates={
                        "match_id": context["match_id"],
                        "goals_for": (
                            context["home_goals"] if club_id == context["home_club_id"] else context["away_goals"]
                        ),
                        "goals_against": (
                            context["away_goals"] if club_id == context["home_club_id"] else context["home_goals"]
                        ),
                    },
                )
                touched.add(("club", scope, scope_season_key))

            owner_user_id = self._club_owner_id(club_id)
            if owner_user_id:
                user_perception = article_perception.get(owner_user_id, 0.0) + (perception_delta * 0.5)
                for scope, scope_season_key in scopes:
                    self._update_prestige_row(
                        entity_type="user",
                        entity_id=owner_user_id,
                        entity_name=self._user_display_name(owner_user_id),
                        scope=scope,
                        season_key=scope_season_key,
                        result=team_result,
                        trophy_delta=trophy_delta,
                        development_delta=development_delta * 0.75,
                        earnings_value=self._user_earnings_value(owner_user_id),
                        difficulty_delta=self._difficulty_delta(context=context),
                        perception_delta=user_perception,
                        metadata_updates={"club_id": club_id, "match_id": context["match_id"]},
                    )
                    touched.add(("user", scope, scope_season_key))

        for entity_type, scope, scope_season_key in touched:
            self._rank_prestige_rows(entity_type=entity_type, scope=scope, season_key=scope_season_key)

    def _update_prestige_row(
        self,
        *,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        scope: str,
        season_key: str,
        result: str,
        trophy_delta: float,
        development_delta: float,
        earnings_value: float | None,
        difficulty_delta: float,
        perception_delta: float,
        metadata_updates: dict[str, Any] | None = None,
    ) -> PrestigeRating:
        row = self.session.scalar(
            select(PrestigeRating).where(
                PrestigeRating.entity_type == entity_type,
                PrestigeRating.entity_id == entity_id,
                PrestigeRating.scope == scope,
                PrestigeRating.season_key == season_key,
            )
        )
        if row is None:
            row = PrestigeRating(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                scope=scope,
                season_key=season_key,
                metadata_json={},
            )
            self.session.add(row)
            self.session.flush()
        metadata = dict(row.metadata_json or {})
        matches = int(metadata.get("matches", 0)) + 1
        wins = int(metadata.get("wins", 0))
        draws = int(metadata.get("draws", 0))
        losses = int(metadata.get("losses", 0))
        if result == "win":
            wins += 1
        elif result == "draw":
            draws += 1
        else:
            losses += 1
        row.entity_name = entity_name
        row.trophies = max(0.0, float(row.trophies or 0.0) + float(trophy_delta or 0.0))
        row.win_rate = wins / matches if matches else 0.0
        row.player_development = max(0.0, float(row.player_development or 0.0) + float(development_delta or 0.0))
        row.earnings = max(0.0, float(earnings_value if earnings_value is not None else row.earnings or 0.0))
        row.difficulty_modifier = max(0.0, float(row.difficulty_modifier or 0.0) + float(difficulty_delta or 0.0))
        row.perception_score = max(0.0, float(row.perception_score or 0.0) + float(perception_delta or 0.0))
        row.prestige_score = self._prestige_formula(
            trophies=row.trophies,
            win_rate=row.win_rate,
            player_development=row.player_development,
            earnings=row.earnings,
            difficulty_modifier=row.difficulty_modifier,
            perception_score=row.perception_score,
        )
        row.prestige_tier = self._prestige_tier(row.prestige_score)
        row.metadata_json = {
            **metadata,
            "matches": matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "last_result": result,
            **dict(metadata_updates or {}),
        }
        self.session.flush()
        return row

    def _rank_prestige_rows(self, *, entity_type: str, scope: str, season_key: str) -> None:
        rows = list(
            self.session.scalars(
                select(PrestigeRating)
                .where(
                    PrestigeRating.entity_type == entity_type,
                    PrestigeRating.scope == scope,
                    PrestigeRating.season_key == season_key,
                )
                .order_by(
                    PrestigeRating.prestige_score.desc(),
                    PrestigeRating.updated_at.asc(),
                    PrestigeRating.entity_name.asc(),
                )
            ).all()
        )
        for index, row in enumerate(rows, start=1):
            row.rank_position = index
        self._sync_redis_rows(entity_type=entity_type, scope=scope, rows=rows)

    def _sync_redis_rows(self, *, entity_type: str, scope: str, rows: list[PrestigeRating]) -> None:
        redis_client = self._redis_client()
        if redis_client is None:
            return
        key = self._redis_key(entity_type=entity_type, scope=scope)
        try:
            pipeline = redis_client.pipeline(transaction=False)
            pipeline.delete(key)
            for row in rows:
                pipeline.zadd(key, {row.entity_id: float(row.prestige_score or 0.0)})
            pipeline.execute()
        except RedisError:
            return

    def _list_rankings(self, entity_type: str, scope: str, season_key: str, limit: int) -> list[PrestigeRating]:
        return list(
            self.session.scalars(
                select(PrestigeRating)
                .where(
                    PrestigeRating.entity_type == entity_type,
                    PrestigeRating.scope == scope,
                    PrestigeRating.season_key == season_key,
                )
                .order_by(
                    PrestigeRating.rank_position.asc().nulls_last(),
                    PrestigeRating.prestige_score.desc(),
                    PrestigeRating.updated_at.desc(),
                )
                .limit(max(1, int(limit)))
            ).all()
        )

    def _ensure_personality(self, player: Player) -> PlayerPersonality:
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player.id))
        if personality is not None:
            return personality
        personality = PlayerPersonality(
            player_id=player.id,
            source_scope="legend_layer",
            metadata_json={"created_by": "legend_layer"},
        )
        self.session.add(personality)
        self.session.flush()
        return personality

    def _ensure_player_story(self, player: Player) -> PlayerStory:
        story = self.session.scalar(select(PlayerStory).where(PlayerStory.player_id == player.id))
        if story is not None:
            return story
        story = PlayerStory(player_id=player.id, chapters={}, narrative_score=0.0)
        self.session.add(story)
        self.session.flush()
        return story

    def _evolve_personality(
        self,
        *,
        player: Player,
        personality: PlayerPersonality,
        stat: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, float]:
        rating = float(stat.get("rating") or 0.0)
        goals = int(stat.get("goals") or 0)
        assists = int(stat.get("assists") or 0)
        yellow_cards = int(stat.get("yellow_cards") or 0)
        red_card = bool(stat.get("red_card"))
        team_result = "draw"
        if context["winner_team_id"] is not None:
            team_result = "win" if context["winner_team_id"] == self._clean(stat.get("team_id")) else "loss"
        is_big_moment = self._is_big_moment(stat=stat, context=context)
        age = self._player_age(player)

        confidence_delta = (6.0 if team_result == "win" else -5.0 if team_result == "loss" else 1.0) + (
            (rating - 6.5) * 2.2
        )
        ego_delta = (goals * 3.0) + (assists * 2.0) + (3.0 if rating >= 8.2 else -2.0 if rating <= 5.8 else 0.0)
        loyalty_delta = 2.0 if team_result == "win" else -3.0 if team_result == "loss" and context["is_final"] else 0.0
        aggression_delta = (yellow_cards * 3.0) + (10.0 if red_card else -1.0 if rating >= 7.0 else 1.0)
        consistency_delta = 4.0 if rating >= 8.0 else -4.0 if rating <= 5.8 else 1.0
        clutch_delta = 6.0 if is_big_moment else 1.0 if team_result == "win" else -2.0
        if age is not None and age <= 22 and (goals > 0 or assists > 0):
            confidence_delta += 2.0
            ego_delta += 1.0
        if age is not None and age >= 30 and team_result == "win":
            consistency_delta += 2.0
            loyalty_delta += 1.0

        personality.confidence = self._clamp_trait(personality.confidence + confidence_delta)
        personality.ego = self._clamp_trait(personality.ego + ego_delta)
        personality.loyalty = self._clamp_trait(personality.loyalty + loyalty_delta)
        personality.aggression = self._clamp_trait(personality.aggression + aggression_delta)
        personality.consistency = self._clamp_trait(personality.consistency + consistency_delta)
        personality.clutch_factor = self._clamp_trait(personality.clutch_factor + clutch_delta)
        metadata = dict(personality.metadata_json or {})
        personality.metadata_json = {
            **metadata,
            "observed_matches": int(metadata.get("observed_matches", 0)) + 1,
            "last_match_id": context["match_id"],
            "last_result": team_result,
            "last_shift": {
                "confidence": round(confidence_delta, 2),
                "ego": round(ego_delta, 2),
                "loyalty": round(loyalty_delta, 2),
                "aggression": round(aggression_delta, 2),
                "consistency": round(consistency_delta, 2),
                "clutch_factor": round(clutch_delta, 2),
            },
        }
        return {
            "confidence_delta": confidence_delta,
            "ego_delta": ego_delta,
            "clutch_delta": clutch_delta,
            "narrative_delta": max(4.0, confidence_delta + clutch_delta + goals + assists),
        }

    def _build_player_interview(
        self,
        *,
        player: Player,
        personality: PlayerPersonality,
        stat: dict[str, Any],
        context: dict[str, Any],
        article: NewsArticle | None,
    ) -> PlayerInterview:
        team_result = "draw"
        if context["winner_team_id"] is not None:
            team_result = "win" if context["winner_team_id"] == self._clean(stat.get("team_id")) else "loss"
        sentiment = (
            "confident"
            if personality.confidence >= 68 and team_result == "win"
            else "defiant" if personality.ego >= 72 and team_result == "loss" else "measured"
        )
        team_name = str(stat.get("team_name") or self._team_name_for_player(context, stat))
        quote = (
            f"We stayed with the data of the game and kept pushing for {team_name}."
            if team_result == "win"
            else (
                "The level was not where it needs to be, and I take responsibility for that."
                if team_result == "loss"
                else "We had moments, but the match was decided by fine margins."
            )
        )
        if int(stat.get("goals") or 0) or int(stat.get("assists") or 0):
            quote += " I knew I had to turn the chances into numbers tonight."
        if personality.ego >= 75 and team_result == "win":
            quote += " Big players are meant to decide big moments."
        return PlayerInterview(
            player_id=player.id,
            article_id=article.id if article is not None else None,
            match_id=context["match_id"],
            interview_type="post_match",
            sentiment=sentiment,
            question="What decided the match for you?",
            quote=quote.strip(),
            metadata_json={
                "team_result": team_result,
                "confidence": int(personality.confidence),
                "ego": int(personality.ego),
            },
        )

    def _build_fan_reaction(
        self,
        *,
        player: Player,
        personality: PlayerPersonality,
        stat: dict[str, Any],
        context: dict[str, Any],
        article: NewsArticle | None,
    ) -> PlayerFanReaction | None:
        rating = float(stat.get("rating") or 0.0)
        red_card = bool(stat.get("red_card"))
        goals = int(stat.get("goals") or 0)
        assists = int(stat.get("assists") or 0)
        if (
            rating <= 5.8
            or red_card
            or (personality.ego >= 72 and context["winner_team_id"] != self._clean(stat.get("team_id")))
        ):
            return PlayerFanReaction(
                player_id=player.id,
                article_id=article.id if article is not None else None,
                match_id=context["match_id"],
                reaction_type="controversy",
                intensity=72.0 + (12.0 if red_card else 0.0),
                headline=f"Reaction turns on {player.full_name}",
                body=f"Fan sentiment swung negative after {player.full_name} posted a {rating:.1f} rating.",
                metadata_json={"rating": rating, "red_card": red_card},
            )
        if goals > 0 or assists > 0 or rating >= 8.0:
            return PlayerFanReaction(
                player_id=player.id,
                article_id=article.id if article is not None else None,
                match_id=context["match_id"],
                reaction_type="adoration",
                intensity=65.0 + (goals * 8.0) + (assists * 6.0),
                headline=f"{player.full_name} is trending upward",
                body=f"Supporters amplified {player.full_name} after a decisive performance for the latest result.",
                metadata_json={"rating": rating, "goals": goals, "assists": assists},
            )
        return None

    def _apply_market_reaction(
        self,
        *,
        player: Player,
        article: NewsArticle | None,
        stat: dict[str, Any],
    ) -> None:
        # Records the story's footprint on the market without pricing it.
        #
        # The valuation consequence of matchday form is owned by
        # app.value_engine.matchday_signal -- "the contract between football and
        # money" -- which is bounded, averaged over a rolling window, requires a
        # minimum sample, and is applied as an overlay to a ValueSnapshot. It is
        # live in production via MatchdayValuationSignalProvider in
        # value_engine/service.py, so matchday still moves value; it does so
        # there.
        #
        # This method predates that contract (2026-03-29 vs 2026-09-02) and used
        # to reach around it, writing:
        #   * market.share_price_coin -- the tradable price, whose only other
        #     writers are trading, issuance and governed admin repricing; and
        #   * player.market_value_eur -- which is the value engine's *input*, so
        #     moving it shifted the very baseline the bounded overlay is computed
        #     from. That is how one match could swing a valuation 18% while the
        #     canonical signal is capped near 2.4%.
        # It also invented a market value out of a rating when the player had
        # none. Unknown is not a number a single rating can supply.
        market = self.session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id))
        if market is None:
            return
        rating = stat.get("rating")
        market.metadata_json = {
            **dict(market.metadata_json or {}),
            "last_narrative_article_id": article.id if article is not None else None,
            "last_narrative_rating": float(rating) if rating is not None else None,
        }

    def _standout_stat(self, player_stats: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not player_stats:
            return None
        return max(
            player_stats,
            key=lambda item: (
                (int(item.get("goals") or 0) * 8)
                + (int(item.get("assists") or 0) * 6)
                + (int(item.get("saves") or 0) * 2)
                + (float(item.get("rating") or 0.0) * 3)
                - (6 if bool(item.get("red_card")) else 0)
            ),
        )

    def _controversy_stat(self, player_stats: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates = [item for item in player_stats if self._is_controversial(item)]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda item: (
                float(item.get("rating") or 10.0),
                0 if bool(item.get("red_card")) else 1,
                -int(item.get("yellow_cards") or 0),
            ),
        )

    def _is_controversial(self, stat: dict[str, Any]) -> bool:
        player_id = self._clean(stat.get("player_id"))
        profile = (
            self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player_id))
            if player_id
            else None
        )
        rating = float(stat.get("rating") or 0.0)
        red_card = bool(stat.get("red_card"))
        yellow_cards = int(stat.get("yellow_cards") or 0)
        ego = int(profile.ego) if profile is not None else 50
        return red_card or rating <= 5.8 or (ego >= 72 and rating <= 6.2) or yellow_cards >= 2

    def _article_for_player(self, articles: list[NewsArticle], player_id: str | None) -> NewsArticle | None:
        if not player_id:
            return None
        for article in reversed(articles):
            if article.related_player_id == player_id:
                return article
        return None

    def _resolve_scope(self, *, scope: str, season_key: str | None) -> tuple[str, str]:
        normalized_scope = scope.strip().lower()
        if normalized_scope not in {LIFETIME_SCOPE, SEASONAL_SCOPE}:
            raise LegendLayerError("Scope must be lifetime or seasonal.")
        if normalized_scope == LIFETIME_SCOPE:
            return normalized_scope, LIFETIME_SEASON_KEY
        if season_key:
            return normalized_scope, season_key
        latest = self.session.scalar(
            select(PrestigeRating.season_key)
            .where(PrestigeRating.scope == SEASONAL_SCOPE)
            .order_by(PrestigeRating.updated_at.desc())
            .limit(1)
        )
        return normalized_scope, str(latest) if latest else self._default_season_key()

    def _event_season_key(self, payload: dict[str, Any]) -> str:
        return self._clean(payload.get("season_id")) or self._default_season_key()

    def _default_season_key(self) -> str:
        season = SeasonService(session=self.session, redis_url=self.redis_url).get_current_season(auto_rollover=True)
        return season.id

    def _redis_client(self) -> Redis | None:
        if self._redis_attempted:
            return self._redis
        self._redis_attempted = True
        if not self.redis_url:
            return None
        try:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
            self._redis.ping()
        except RedisError:
            self._redis = None
        return self._redis

    def _redis_key(self, *, entity_type: str, scope: str) -> str:
        base_key = {
            "player": PLAYER_KEY,
            "club": CLUB_KEY,
            "user": USER_KEY,
            "national_team": NATIONAL_TEAM_KEY,
        }[entity_type]
        return base_key if scope == SEASONAL_SCOPE else f"{base_key}:lifetime"

    def _winner_name(self, context: dict[str, Any]) -> str | None:
        if context["winner_team_id"] == context["home_club_id"]:
            return context["home_club_name"]
        if context["winner_team_id"] == context["away_club_id"]:
            return context["away_club_name"]
        return None

    def _winner_team_id(self, context: dict[str, Any]) -> str | None:
        return self._clean(context.get("winner_team_id"))

    def _winner_user_id(self, context: dict[str, Any]) -> str | None:
        if context["winner_team_id"] == context["home_club_id"]:
            return context["home_user_id"] or self._club_owner_id(context["home_club_id"])
        if context["winner_team_id"] == context["away_club_id"]:
            return context["away_user_id"] or self._club_owner_id(context["away_club_id"])
        return None

    def _history_hook(self, player_id: str | None) -> str | None:
        if not player_id:
            return None
        history = self.session.scalar(
            select(PlayerHistory)
            .where(PlayerHistory.player_id == player_id)
            .order_by(PlayerHistory.created_at.desc())
            .limit(1)
        )
        if history is None:
            return None
        return f"Global memory already tracked {history.event.lower()} in {history.competition}."

    def _commentary_excerpt(self, commentary: list[CommentaryEvent]) -> str | None:
        if not commentary:
            return None
        last_lines = commentary[-2:]
        return " ".join(f"{item.minute}': {item.generated_line}" for item in last_lines if item.generated_line).strip()

    def _late_drama(self, commentary: list[CommentaryEvent]) -> bool:
        return any(
            int(item.minute) >= 85
            and str(item.event_type or "").lower() in {"goal", "winner", "late_goal", "match_winner"}
            for item in commentary
        )

    def _team_name_for_player(self, context: dict[str, Any], stat: dict[str, Any]) -> str:
        team_id = self._clean(stat.get("team_id"))
        if team_id == context["home_club_id"]:
            return context["home_club_name"]
        if team_id == context["away_club_id"]:
            return context["away_club_name"]
        return str(stat.get("team_name") or "Unknown Team")

    def _scoreline(self, context: dict[str, Any]) -> str:
        return (
            f"{context['home_club_name']} {context['home_goals']}-{context['away_goals']} {context['away_club_name']}"
        )

    def _clean_tags(self, items: list[str | None]) -> list[str]:
        tags: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item is None:
                continue
            normalized = str(item).strip().lower().replace(" ", "_")
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tags.append(normalized)
        return tags

    def _club_owner_id(self, club_id: str | None) -> str | None:
        if not club_id:
            return None
        club = self.session.get(ClubProfile, club_id)
        return club.owner_user_id if club is not None else None

    def _user_display_name(self, user_id: str) -> str:
        user = self.session.get(User, user_id)
        if user is None:
            return user_id
        return user.display_name or user.full_name or user.username or user.email or user.id

    def _player_earnings_value(self, player_id: str, development_delta: float) -> float:
        player = self.session.get(Player, player_id)
        if player is None:
            row = self.session.scalar(
                select(PrestigeRating).where(
                    PrestigeRating.entity_type == "player",
                    PrestigeRating.entity_id == player_id,
                    PrestigeRating.scope == LIFETIME_SCOPE,
                    PrestigeRating.season_key == LIFETIME_SEASON_KEY,
                )
            )
            return float((row.earnings if row is not None else 0.0) or 0.0) + (development_delta * 1000.0)
        return float(player.market_value_eur or player.current_market_reference_value or 0.0)

    def _club_earnings_value(self, club_id: str) -> float:
        summary = self.session.scalar(
            select(ClubCashflowSummary)
            .where(ClubCashflowSummary.club_id == club_id)
            .order_by(ClubCashflowSummary.created_at.desc())
            .limit(1)
        )
        if summary is None:
            row = self.session.scalar(
                select(PrestigeRating).where(
                    PrestigeRating.entity_type == "club",
                    PrestigeRating.entity_id == club_id,
                    PrestigeRating.scope == LIFETIME_SCOPE,
                    PrestigeRating.season_key == LIFETIME_SEASON_KEY,
                )
            )
            return float((row.earnings if row is not None else 0.0) or 0.0)
        return float(summary.total_income_minor or 0) / 100.0

    def _user_earnings_value(self, user_id: str) -> float:
        dynasty = self.session.scalar(select(UserDynasty).where(UserDynasty.user_id == user_id))
        if dynasty is None:
            row = self.session.scalar(
                select(PrestigeRating).where(
                    PrestigeRating.entity_type == "user",
                    PrestigeRating.entity_id == user_id,
                    PrestigeRating.scope == LIFETIME_SCOPE,
                    PrestigeRating.season_key == LIFETIME_SEASON_KEY,
                )
            )
            return float((row.earnings if row is not None else 0.0) or 0.0)
        return float(dynasty.earnings_minor or 0) / 100.0

    def _team_stats(self, context: dict[str, Any], team_id: str | None) -> list[dict[str, Any]]:
        if not team_id:
            return []
        return [item for item in context["player_stats"] if self._clean(item.get("team_id")) == team_id]

    def _difficulty_delta(self, *, context: dict[str, Any]) -> float:
        base = 1.0 if context["competition_type"] == "league" else 1.4
        if context["is_final"]:
            base += 0.8
        return base

    def _is_big_moment(self, *, stat: dict[str, Any], context: dict[str, Any]) -> bool:
        goals = int(stat.get("goals") or 0)
        assists = int(stat.get("assists") or 0)
        if context["is_final"] and (goals > 0 or assists > 0):
            return True
        return (
            bool(context["winner_team_id"])
            and self._clean(stat.get("team_id")) == context["winner_team_id"]
            and (goals > 0 or assists > 0)
        )

    def _player_age(self, player: Player) -> int | None:
        if player.date_of_birth is None:
            return None
        today = self._now().date()
        years = today.year - player.date_of_birth.year
        if (today.month, today.day) < (player.date_of_birth.month, player.date_of_birth.day):
            years -= 1
        return years

    def _prestige_formula(
        self,
        *,
        trophies: float,
        win_rate: float,
        player_development: float,
        earnings: float,
        difficulty_modifier: float,
        perception_score: float,
    ) -> float:
        normalized_earnings = min(max(earnings, 0.0) / 1_000_000.0, 120.0)
        return round(
            (trophies * 25.0)
            + (max(win_rate, 0.0) * 60.0)
            + (min(max(player_development, 0.0), 250.0) * 0.45)
            + (normalized_earnings * 0.7)
            + (max(difficulty_modifier, 0.0) * 10.0)
            + (max(perception_score, 0.0) * 0.6),
            2,
        )

    def _prestige_tier(self, prestige_score: float) -> str:
        if prestige_score >= 260.0:
            return "Legendary"
        if prestige_score >= 180.0:
            return "Elite"
        if prestige_score >= 110.0:
            return "Gold"
        if prestige_score >= 55.0:
            return "Silver"
        return "Bronze"

    @staticmethod
    def _clamp_trait(value: float | int) -> int:
        return max(1, min(99, int(round(float(value)))))

    @staticmethod
    def _clean(value: Any) -> str | None:
        if value is None:
            return None
        resolved = str(value).strip()
        return resolved or None

    @staticmethod
    def _normalize_timestamp(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
