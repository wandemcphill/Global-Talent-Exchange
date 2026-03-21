from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.club_identity.models.reputation import ClubReputationProfile
from app.config.club_social import (
    CHALLENGE_DEEP_LINK_PREFIX,
    CHALLENGE_WEB_PATH_PREFIX,
    DEFAULT_HIGH_GIFT_THRESHOLD,
    DEFAULT_HIGH_VIEW_THRESHOLD,
)
from app.models.club_profile import ClubProfile
from app.models.club_social import (
    ChallengeShareEvent,
    ClubChallenge,
    ClubChallengeLink,
    ClubChallengeResponse,
    ClubIdentityMetrics,
    MatchReactionEvent,
    RivalryMatchHistory,
    RivalryProfile,
)
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.user import User

_NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9]+")


class ClubSocialError(ValueError):
    pass


@dataclass(slots=True)
class ClubSocialService:
    session: Session

    def create_challenge(
        self,
        *,
        actor: User,
        club_id: str,
        title: str,
        message: str,
        stakes_text: str | None,
        target_club_id: str | None,
        visibility: str,
        country_code: str | None,
        region_name: str | None,
        city_name: str | None,
        competition_id: str | None,
        accept_by: datetime | None,
        scheduled_for: datetime | None,
        metadata_json: dict[str, object],
    ) -> ClubChallenge:
        issuing_club = self._require_owned_club(actor.id, club_id)
        target_club = self._require_club(target_club_id) if target_club_id else None
        if target_club is not None and target_club.id == issuing_club.id:
            raise ClubSocialError("challenge_target_must_be_different_club")
        challenge = ClubChallenge(
            issuing_club_id=issuing_club.id,
            target_club_id=target_club.id if target_club is not None else None,
            issuing_user_id=actor.id,
            competition_id=competition_id,
            title=title,
            slug=self._generate_unique_slug(title),
            message=message,
            stakes_text=stakes_text,
            visibility=self._normalize(visibility, default="public"),
            country_code=self._normalize(country_code, upper=True),
            region_name=self._clean(region_name),
            city_name=self._clean(city_name),
            accept_by=accept_by,
            scheduled_for=scheduled_for,
            metadata_json=dict(metadata_json),
        )
        self.session.add(challenge)
        self.session.flush()
        self._sync_challenge_status(challenge)
        self.refresh_identity_metrics(club_id=issuing_club.id)
        return challenge

    def publish_challenge(self, *, actor: User, challenge_id: str) -> dict[str, object]:
        challenge = self._require_owned_challenge(actor.id, challenge_id)
        was_published = challenge.published_at is not None
        if not was_published:
            challenge.published_at = self._now()
        self._sync_challenge_status(challenge)
        primary_link = self._primary_link(challenge.id)
        if primary_link is None:
            primary_link = self.create_challenge_link(
                actor=actor,
                challenge_id=challenge.id,
                channel="primary",
                is_primary=True,
                metadata_json={"created_via": "publish"},
            )
        self.refresh_identity_metrics(club_id=challenge.issuing_club_id)
        if challenge.accepted_club_id is not None:
            self.refresh_identity_metrics(club_id=challenge.accepted_club_id)
        self.session.flush()
        return self.challenge_page(challenge_id=challenge.id)

    def create_challenge_link(
        self,
        *,
        actor: User,
        challenge_id: str,
        channel: str,
        is_primary: bool,
        metadata_json: dict[str, object],
    ) -> ClubChallengeLink:
        challenge = self._require_owned_challenge(actor.id, challenge_id)
        if is_primary:
            for existing in self.session.scalars(
                select(ClubChallengeLink).where(
                    ClubChallengeLink.challenge_id == challenge.id,
                    ClubChallengeLink.is_primary.is_(True),
                )
            ).all():
                existing.is_primary = False
        link_code = self._generate_unique_link_code()
        vanity_path = f"{challenge.slug}-{self._normalize(channel, default='share')}-{link_code}"
        link = ClubChallengeLink(
            challenge_id=challenge.id,
            created_by_user_id=actor.id,
            channel=self._normalize(channel, default="share"),
            link_code=link_code,
            vanity_path=vanity_path,
            web_path=f"{CHALLENGE_WEB_PATH_PREFIX}/{vanity_path}",
            deep_link_path=f"{CHALLENGE_DEEP_LINK_PREFIX}/{challenge.id}?code={link_code}",
            is_primary=is_primary,
            metadata_json=dict(metadata_json),
        )
        self.session.add(link)
        self.session.flush()
        return link

    def record_share_event(
        self,
        *,
        challenge_id: str,
        link_id: str | None,
        link_code: str | None,
        actor_user_id: str | None,
        event_type: str,
        source_platform: str | None,
        country_code: str | None,
        metadata_json: dict[str, object],
    ) -> ChallengeShareEvent:
        challenge = self._require_challenge(challenge_id)
        link = None
        if link_id:
            link = self.session.get(ClubChallengeLink, link_id)
        elif link_code:
            link = self.session.scalar(select(ClubChallengeLink).where(ClubChallengeLink.link_code == link_code))
        if link is not None and link.challenge_id != challenge.id:
            raise ClubSocialError("challenge_link_mismatch")
        normalized_event = self._normalize(event_type, default="share")
        share_event = ChallengeShareEvent(
            challenge_id=challenge.id,
            link_id=link.id if link is not None else None,
            actor_user_id=actor_user_id,
            event_type=normalized_event,
            source_platform=self._normalize(source_platform),
            country_code=self._normalize(country_code, upper=True),
            metadata_json=dict(metadata_json),
        )
        self.session.add(share_event)
        if link is not None and normalized_event in {"open", "click", "view"}:
            link.click_count += 1
        self.session.flush()
        self.refresh_identity_metrics(club_id=challenge.issuing_club_id)
        if challenge.accepted_club_id is not None:
            self.refresh_identity_metrics(club_id=challenge.accepted_club_id)
        return share_event

    def accept_challenge(
        self,
        *,
        actor: User,
        challenge_id: str,
        responding_club_id: str,
        message: str | None,
        scheduled_for: datetime | None,
        competition_id: str | None,
        linked_match_id: str | None,
        metadata_json: dict[str, object],
    ) -> dict[str, object]:
        challenge = self._require_challenge(challenge_id)
        responding_club = self._require_owned_club(actor.id, responding_club_id)
        if challenge.issuing_club_id == responding_club.id:
            raise ClubSocialError("club_cannot_accept_own_challenge")
        if challenge.target_club_id is not None and challenge.target_club_id != responding_club.id:
            raise ClubSocialError("challenge_target_mismatch")
        if challenge.accepted_club_id is not None and challenge.accepted_club_id != responding_club.id:
            raise ClubSocialError("challenge_already_accepted")
        response = self.session.scalar(
            select(ClubChallengeResponse).where(
                ClubChallengeResponse.challenge_id == challenge.id,
                ClubChallengeResponse.responding_club_id == responding_club.id,
            )
        )
        if response is None:
            response = ClubChallengeResponse(
                challenge_id=challenge.id,
                responding_club_id=responding_club.id,
                responder_user_id=actor.id,
            )
            self.session.add(response)
        response.response_type = "accept"
        response.response_status = "accepted"
        response.message = self._clean(message)
        response.scheduled_for = scheduled_for
        response.metadata_json = dict(metadata_json)
        challenge.accepted_club_id = responding_club.id
        if competition_id is not None:
            challenge.competition_id = competition_id
        if linked_match_id is not None:
            challenge.linked_match_id = linked_match_id
        if scheduled_for is not None:
            challenge.scheduled_for = scheduled_for
        self._sync_challenge_status(challenge)
        rivalry = self._ensure_rivalry_profile(challenge.issuing_club_id, responding_club.id)
        rivalry.intensity_score = max(rivalry.intensity_score, 12)
        rivalry.label = self._derive_rivalry_label(
            rivalry,
            derby=self._is_derby(self._require_club(challenge.issuing_club_id), responding_club),
            upset=False,
            challenge_match=True,
        )
        rivalry.narrative_tags_json = self._merge_strings(rivalry.narrative_tags_json, ["challenge_grudge"])
        self.session.flush()
        self.refresh_identity_metrics(club_id=challenge.issuing_club_id)
        self.refresh_identity_metrics(club_id=responding_club.id)
        return self.challenge_page(challenge_id=challenge.id)

    def challenge_page(self, *, challenge_id: str | None = None, link_code: str | None = None) -> dict[str, object]:
        challenge = self._resolve_challenge(challenge_id=challenge_id, link_code=link_code)
        self._sync_challenge_status(challenge)
        responses = list(
            self.session.scalars(
                select(ClubChallengeResponse)
                .where(ClubChallengeResponse.challenge_id == challenge.id)
                .order_by(ClubChallengeResponse.created_at.desc())
            ).all()
        )
        links = list(
            self.session.scalars(
                select(ClubChallengeLink)
                .where(ClubChallengeLink.challenge_id == challenge.id)
                .order_by(ClubChallengeLink.is_primary.desc(), ClubChallengeLink.created_at.desc())
            ).all()
        )
        share_stats = self._share_stats(challenge.id)
        rivalry_summary = None
        opponent_club_id = challenge.accepted_club_id or challenge.target_club_id
        if opponent_club_id is not None:
            profile = self._rivalry_profile(challenge.issuing_club_id, opponent_club_id)
            if profile is not None:
                rivalry_summary = self._rivalry_summary(profile, challenge.issuing_club_id)
        reactions = self.list_match_reactions(challenge.linked_match_id) if challenge.linked_match_id else []
        return {
            "challenge": self._challenge_view(challenge),
            "card": self._challenge_card(
                challenge=challenge,
                primary_link=links[0] if links else None,
                share_stats=share_stats,
                rivalry=rivalry_summary,
                reactions=reactions,
            ),
            "responses": [self._challenge_response_view(item) for item in responses],
            "links": [self._challenge_link_view(item) for item in links],
            "share_stats": share_stats,
            "rivalry": rivalry_summary,
            "recent_reactions": reactions,
        }

    def list_club_challenges(
        self,
        *,
        club_id: str,
        direction: str = "all",
        status: str | None = None,
    ) -> list[dict[str, object]]:
        self._require_club(club_id)
        normalized_direction = self._normalize(direction, default="all")
        stmt = select(ClubChallenge)
        if normalized_direction == "issued":
            stmt = stmt.where(ClubChallenge.issuing_club_id == club_id)
        elif normalized_direction == "incoming":
            stmt = stmt.where(or_(ClubChallenge.target_club_id == club_id, ClubChallenge.accepted_club_id == club_id))
        else:
            stmt = stmt.where(
                or_(
                    ClubChallenge.issuing_club_id == club_id,
                    ClubChallenge.target_club_id == club_id,
                    ClubChallenge.accepted_club_id == club_id,
                )
            )
        if status:
            stmt = stmt.where(ClubChallenge.status == self._normalize(status))
        stmt = stmt.order_by(ClubChallenge.updated_at.desc())
        challenges = list(self.session.scalars(stmt).all())
        cards: list[dict[str, object]] = []
        for challenge in challenges:
            self._sync_challenge_status(challenge)
            links = list(
                self.session.scalars(
                    select(ClubChallengeLink)
                    .where(ClubChallengeLink.challenge_id == challenge.id)
                    .order_by(ClubChallengeLink.is_primary.desc(), ClubChallengeLink.created_at.desc())
                    .limit(1)
                ).all()
            )
            profile = None
            opponent_club_id = challenge.accepted_club_id or challenge.target_club_id
            if opponent_club_id:
                profile = self._rivalry_profile(challenge.issuing_club_id, opponent_club_id)
            cards.append(
                self._challenge_card(
                    challenge=challenge,
                    primary_link=links[0] if links else None,
                    share_stats=self._share_stats(challenge.id),
                    rivalry=self._rivalry_summary(profile, challenge.issuing_club_id) if profile is not None else None,
                    reactions=[],
                )
            )
        return cards

    def refresh_identity_metrics(self, *, club_id: str) -> ClubIdentityMetrics:
        self._require_club(club_id)
        metrics = self.session.scalar(select(ClubIdentityMetrics).where(ClubIdentityMetrics.club_id == club_id))
        if metrics is None:
            metrics = ClubIdentityMetrics(club_id=club_id, challenge_history_json={}, metadata_json={})
            self.session.add(metrics)
        now = self._now()
        thirty_days_ago = now - timedelta(days=30)
        issued_challenges = list(
            self.session.scalars(select(ClubChallenge).where(ClubChallenge.issuing_club_id == club_id)).all()
        )
        accepted_challenges = list(
            self.session.scalars(select(ClubChallenge).where(ClubChallenge.accepted_club_id == club_id)).all()
        )
        related_challenge_ids = {item.id for item in issued_challenges} | {item.id for item in accepted_challenges}
        if related_challenge_ids:
            share_events = list(
                self.session.scalars(
                    select(ChallengeShareEvent).where(ChallengeShareEvent.challenge_id.in_(related_challenge_ids))
                ).all()
            )
        else:
            share_events = []
        reaction_count = int(
            self.session.scalar(select(func.count(MatchReactionEvent.id)).where(MatchReactionEvent.club_id == club_id))
            or 0
        )
        recent_reaction_count = int(
            self.session.scalar(
                select(func.count(MatchReactionEvent.id)).where(
                    MatchReactionEvent.club_id == club_id,
                    MatchReactionEvent.created_at >= thirty_days_ago,
                )
            )
            or 0
        )
        rivalry_profiles = list(
            self.session.scalars(
                select(RivalryProfile).where(or_(RivalryProfile.club_a_id == club_id, RivalryProfile.club_b_id == club_id))
            ).all()
        )
        reputation_profile = self.session.scalar(
            select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id)
        )
        reputation_score = reputation_profile.current_score if reputation_profile is not None else 0
        rivalry_intensity = max((profile.intensity_score for profile in rivalry_profiles), default=0)
        share_event_count = len(share_events)
        recent_share_count = sum(1 for event in share_events if self._coerce_datetime(event.created_at) >= thirty_days_ago)
        challenge_wins = sum(1 for item in issued_challenges + accepted_challenges if item.winner_club_id == club_id)
        challenge_losses = sum(
            1
            for item in issued_challenges + accepted_challenges
            if item.status == "settled" and item.winner_club_id is not None and item.winner_club_id != club_id
        )
        settled_challenges = sum(1 for item in issued_challenges + accepted_challenges if item.status == "settled")
        fan_count = max(
            100,
            100 + (reputation_score * 3) + (share_event_count * 25) + (reaction_count * 10) + (challenge_wins * 40) + (rivalry_intensity * 2),
        )
        media_popularity = max(
            0,
            (reputation_score // 10) + (share_event_count * 6) + (reaction_count * 4) + (len(issued_challenges) * 8) + (settled_challenges * 5),
        )
        support_momentum = max(
            0,
            (recent_share_count * 8) + (recent_reaction_count * 6) + (challenge_wins * 12) + (rivalry_intensity // 2),
        )
        metrics.fan_count = fan_count
        metrics.reputation_score = reputation_score
        metrics.media_popularity_score = media_popularity
        metrics.media_value_minor = (media_popularity * 2500) + (fan_count * 120)
        metrics.club_valuation_minor = (reputation_score * 1000) + (fan_count * 350) + (rivalry_intensity * 500) + (challenge_wins * 5000)
        metrics.rivalry_intensity_score = rivalry_intensity
        metrics.support_momentum_score = support_momentum
        metrics.sponsorship_potential_score = (reputation_score // 8) + media_popularity + (fan_count // 100) + (challenge_wins * 10)
        metrics.discoverability_score = media_popularity + (rivalry_intensity // 2) + (share_event_count * 4)
        metrics.challenge_history_json = {
            "issued": len(issued_challenges),
            "accepted": len(accepted_challenges),
            "settled": settled_challenges,
            "wins": challenge_wins,
            "losses": challenge_losses,
        }
        metrics.metadata_json = {
            "share_events": share_event_count,
            "reaction_events": reaction_count,
            "rivalry_count": len(rivalry_profiles),
        }
        self.session.flush()
        return metrics

    def record_reaction_from_match_event(self, *, event: CompetitionMatchEvent) -> MatchReactionEvent | None:
        mapping = self._reaction_mapping(event)
        if mapping is None:
            return None
        existing = self.session.scalar(
            select(MatchReactionEvent).where(
                MatchReactionEvent.source_event_id == event.id,
                MatchReactionEvent.reaction_type == mapping["reaction_type"],
            )
        )
        if existing is not None:
            return existing
        match = self.session.get(CompetitionMatch, event.match_id)
        challenge = self._resolve_challenge_for_match(match) if match is not None else None
        rivalry = None
        if match is not None and self._has_club_profiles(match.home_club_id, match.away_club_id):
            rivalry = self._rivalry_profile(match.home_club_id, match.away_club_id)
        club_id = event.club_id if event.club_id is not None and self._club(event.club_id) is not None else None
        reaction = MatchReactionEvent(
            match_id=event.match_id,
            competition_id=event.competition_id,
            source_event_id=event.id,
            challenge_id=challenge.id if challenge is not None else None,
            rivalry_profile_id=rivalry.id if rivalry is not None else None,
            club_id=club_id,
            reaction_type=mapping["reaction_type"],
            reaction_label=mapping["reaction_label"],
            intensity_score=mapping["intensity_score"],
            minute=event.minute,
            happened_at=self._event_happened_at(event),
            metadata_json={
                "event_type": event.event_type,
                "card_type": event.card_type,
                "highlight": event.highlight,
                "player_id": event.player_id,
                "secondary_player_id": event.secondary_player_id,
                "added_time": event.added_time,
                **(event.metadata_json or {}),
            },
        )
        self.session.add(reaction)
        self.session.flush()
        if club_id is not None:
            self.refresh_identity_metrics(club_id=club_id)
        return reaction

    def list_match_reactions(self, match_id: str, *, limit: int = 30) -> list[dict[str, object]]:
        reactions = list(
            self.session.scalars(
                select(MatchReactionEvent)
                .where(MatchReactionEvent.match_id == match_id)
                .order_by(MatchReactionEvent.happened_at.desc(), MatchReactionEvent.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [self._reaction_view(item) for item in reactions]

    def record_match_outcome(
        self,
        *,
        home_club_id: str,
        away_club_id: str,
        home_score: int,
        away_score: int,
        winner_club_id: str | None,
        match_id: str | None,
        competition_id: str | None,
        challenge_id: str | None,
        happened_at: datetime | None,
        final_flag: bool,
        challenge_match_flag: bool,
        high_view_flag: bool | None,
        high_gift_flag: bool | None,
        upset_flag: bool | None,
        view_count: int,
        gift_count: int,
        notable_moments: list[str],
        metadata_json: dict[str, object],
    ) -> RivalryProfile:
        home_club = self._require_club(home_club_id)
        away_club = self._require_club(away_club_id)
        if home_club.id == away_club.id:
            raise ClubSocialError("rivalry_requires_two_distinct_clubs")
        profile = self._ensure_rivalry_profile(home_club.id, away_club.id)
        if match_id is not None:
            existing_history = self.session.scalar(
                select(RivalryMatchHistory).where(
                    RivalryMatchHistory.rivalry_id == profile.id,
                    RivalryMatchHistory.match_id == match_id,
                )
            )
            if existing_history is not None:
                return profile
        resolved_winner = winner_club_id or self._winner_from_score(home_club.id, away_club.id, home_score, away_score)
        happened_at = happened_at or self._now()
        derby = self._is_derby(home_club, away_club)
        resolved_high_view = high_view_flag if high_view_flag is not None else view_count >= DEFAULT_HIGH_VIEW_THRESHOLD
        resolved_high_gift = high_gift_flag if high_gift_flag is not None else gift_count >= DEFAULT_HIGH_GIFT_THRESHOLD
        resolved_upset = upset_flag if upset_flag is not None else self._is_upset(home_club.id, away_club.id, resolved_winner)
        resolved_challenge_match = challenge_match_flag or challenge_id is not None
        profile.matches_played += 1
        profile.regional_derby = profile.regional_derby or derby
        profile.giant_killer_flag = resolved_upset
        if final_flag:
            profile.finals_played += 1
        if resolved_upset:
            profile.upset_count += 1
        if resolved_challenge_match:
            profile.challenge_matches += 1
        if resolved_high_view:
            profile.high_view_matches += 1
        if resolved_high_gift:
            profile.high_gift_matches += 1
        a_home = profile.club_a_id == home_club.id
        profile.club_a_goals += home_score if a_home else away_score
        profile.club_b_goals += away_score if a_home else home_score
        if resolved_winner is None:
            profile.draws += 1
            profile.streak_holder_club_id = None
            profile.streak_length = 0
        elif resolved_winner == profile.club_a_id:
            profile.club_a_wins += 1
            self._advance_streak(profile, resolved_winner)
        else:
            profile.club_b_wins += 1
            self._advance_streak(profile, resolved_winner)
        intensity_delta = 8 + min(profile.matches_played, 5) * 3
        if derby:
            intensity_delta += 10
        if final_flag:
            intensity_delta += 12
        if resolved_challenge_match:
            intensity_delta += 10
        if resolved_upset:
            intensity_delta += 14
        if resolved_high_view:
            intensity_delta += 6
        if resolved_high_gift:
            intensity_delta += 6
        profile.intensity_score += intensity_delta
        profile.last_match_at = happened_at
        profile.notable_moments_json = self._merge_strings(profile.notable_moments_json, notable_moments, limit=8)
        narrative_tags = self._match_tags(
            derby=derby,
            upset=resolved_upset,
            final_flag=final_flag,
            challenge_match=resolved_challenge_match,
            high_view=resolved_high_view,
            high_gift=resolved_high_gift,
        )
        profile.narrative_tags_json = self._merge_strings(profile.narrative_tags_json, narrative_tags)
        profile.label = self._derive_rivalry_label(profile, derby=derby, upset=resolved_upset, challenge_match=resolved_challenge_match)
        profile.metadata_json = {
            **(profile.metadata_json or {}),
            "last_match_id": match_id,
            "last_challenge_id": challenge_id,
            "last_winner_club_id": resolved_winner,
        }
        history = RivalryMatchHistory(
            rivalry_id=profile.id,
            match_id=match_id,
            competition_id=competition_id,
            challenge_id=challenge_id,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
            winner_club_id=resolved_winner,
            home_score=home_score,
            away_score=away_score,
            upset_flag=resolved_upset,
            final_flag=final_flag,
            challenge_match_flag=resolved_challenge_match,
            high_view_flag=resolved_high_view,
            high_gift_flag=resolved_high_gift,
            view_count=view_count,
            gift_count=gift_count,
            match_weight=intensity_delta,
            notable_moments_json=list(notable_moments),
            happened_at=happened_at,
            metadata_json=dict(metadata_json),
        )
        self.session.add(history)
        self._settle_linked_challenge(
            challenge_id=challenge_id,
            match_id=match_id,
            competition_id=competition_id,
            winner_club_id=resolved_winner,
            happened_at=happened_at,
            home_club_id=home_club.id,
            away_club_id=away_club.id,
        )
        if resolved_upset and match_id is not None:
            self._create_outcome_reaction(
                match_id=match_id,
                competition_id=competition_id,
                challenge_id=challenge_id,
                rivalry_profile_id=profile.id,
                club_id=resolved_winner,
                reaction_type="giant_killer_alert",
                reaction_label="Giant-killer alert",
                intensity_score=96,
                happened_at=happened_at,
                metadata_json={
                    "winner_club_id": resolved_winner,
                    "home_club_id": home_club.id,
                    "away_club_id": away_club.id,
                    "home_score": home_score,
                    "away_score": away_score,
                },
            )
        self.session.flush()
        self.refresh_identity_metrics(club_id=home_club.id)
        self.refresh_identity_metrics(club_id=away_club.id)
        return profile

    def record_match_outcome_from_match(self, *, match: CompetitionMatch) -> RivalryProfile | None:
        if not self._has_club_profiles(match.home_club_id, match.away_club_id):
            return None
        challenge = self._resolve_challenge_for_match(match)
        return self.record_match_outcome(
            home_club_id=match.home_club_id,
            away_club_id=match.away_club_id,
            home_score=match.home_score,
            away_score=match.away_score,
            winner_club_id=match.winner_club_id,
            match_id=match.id,
            competition_id=match.competition_id,
            challenge_id=challenge.id if challenge is not None else None,
            happened_at=match.completed_at or self._now(),
            final_flag=self._normalize(match.stage) in {"final", "grand_final"},
            challenge_match_flag=challenge is not None,
            high_view_flag=None,
            high_gift_flag=None,
            upset_flag=None,
            view_count=self._coerce_int((match.metadata_json or {}).get("view_count")),
            gift_count=self._coerce_int((match.metadata_json or {}).get("gift_count")),
            notable_moments=self._notable_match_moments(match.id),
            metadata_json=match.metadata_json or {},
        )

    def list_rivalries(self, *, club_id: str) -> list[dict[str, object]]:
        self._require_club(club_id)
        profiles = list(
            self.session.scalars(
                select(RivalryProfile)
                .where(or_(RivalryProfile.club_a_id == club_id, RivalryProfile.club_b_id == club_id))
                .order_by(RivalryProfile.intensity_score.desc(), RivalryProfile.last_match_at.desc())
            ).all()
        )
        return [self._rivalry_summary(profile, club_id) for profile in profiles]

    def rivalry_detail(self, *, club_id: str, opponent_club_id: str) -> dict[str, object]:
        self._require_club(club_id)
        self._require_club(opponent_club_id)
        profile = self._rivalry_profile(club_id, opponent_club_id)
        if profile is None:
            raise ClubSocialError("rivalry_not_found")
        history = list(
            self.session.scalars(
                select(RivalryMatchHistory)
                .where(RivalryMatchHistory.rivalry_id == profile.id)
                .order_by(RivalryMatchHistory.happened_at.desc(), RivalryMatchHistory.created_at.desc())
            ).all()
        )
        return {
            "summary": self._rivalry_summary(profile, club_id),
            "history": [self._rivalry_history_view(item) for item in history],
        }

    def _resolve_challenge(self, *, challenge_id: str | None, link_code: str | None) -> ClubChallenge:
        if challenge_id is not None:
            return self._require_challenge(challenge_id)
        if link_code is None:
            raise ClubSocialError("challenge_lookup_requires_id_or_link")
        link = self.session.scalar(select(ClubChallengeLink).where(ClubChallengeLink.link_code == link_code))
        if link is None:
            raise ClubSocialError("challenge_link_not_found")
        return self._require_challenge(link.challenge_id)

    def _require_challenge(self, challenge_id: str) -> ClubChallenge:
        challenge = self.session.get(ClubChallenge, challenge_id)
        if challenge is None:
            raise ClubSocialError("challenge_not_found")
        return challenge

    def _require_owned_challenge(self, actor_user_id: str, challenge_id: str) -> ClubChallenge:
        challenge = self._require_challenge(challenge_id)
        club = self._require_club(challenge.issuing_club_id)
        if club.owner_user_id != actor_user_id:
            raise ClubSocialError("challenge_owner_required")
        return challenge

    def _club(self, club_id: str | None) -> ClubProfile | None:
        if not club_id:
            return None
        return self.session.get(ClubProfile, club_id)

    def _require_club(self, club_id: str | None) -> ClubProfile:
        club = self._club(club_id)
        if club is None:
            raise ClubSocialError("club_not_found")
        return club

    def _require_owned_club(self, actor_user_id: str, club_id: str) -> ClubProfile:
        club = self._require_club(club_id)
        if club.owner_user_id != actor_user_id:
            raise ClubSocialError("club_owner_required")
        return club

    def _generate_unique_slug(self, title: str) -> str:
        base = _NON_ALPHANUMERIC_RE.sub("-", title.strip().lower()).strip("-") or "club-challenge"
        candidate = base
        counter = 2
        while self.session.scalar(select(ClubChallenge).where(ClubChallenge.slug == candidate)) is not None:
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def _generate_unique_link_code(self) -> str:
        while True:
            candidate = token_urlsafe(6).replace("-", "").replace("_", "").lower()[:10]
            if not candidate:
                continue
            existing = self.session.scalar(select(ClubChallengeLink).where(ClubChallengeLink.link_code == candidate))
            if existing is None:
                return candidate

    def _sync_challenge_status(self, challenge: ClubChallenge) -> None:
        now = self._now()
        if challenge.settled_at is not None or challenge.winner_club_id is not None:
            challenge.status = "settled"
            return
        if challenge.accepted_club_id is None:
            challenge.status = "open"
            return
        if challenge.scheduled_for is not None:
            scheduled_for = self._coerce_datetime(challenge.scheduled_for)
            if scheduled_for <= now:
                challenge.status = "live"
                if challenge.live_at is None:
                    challenge.live_at = scheduled_for
            else:
                challenge.status = "scheduled"
            return
        challenge.status = "accepted"

    def _challenge_view(self, challenge: ClubChallenge) -> dict[str, object]:
        issuing_club = self._require_club(challenge.issuing_club_id)
        target_club = self._club(challenge.target_club_id)
        accepted_club = self._club(challenge.accepted_club_id)
        winner_club = self._club(challenge.winner_club_id)
        return {
            "id": challenge.id,
            "issuing_club_id": challenge.issuing_club_id,
            "issuing_club_name": issuing_club.club_name,
            "target_club_id": challenge.target_club_id,
            "target_club_name": target_club.club_name if target_club is not None else None,
            "accepted_club_id": challenge.accepted_club_id,
            "accepted_club_name": accepted_club.club_name if accepted_club is not None else None,
            "competition_id": challenge.competition_id,
            "linked_match_id": challenge.linked_match_id,
            "winner_club_id": challenge.winner_club_id,
            "winner_club_name": winner_club.club_name if winner_club is not None else None,
            "title": challenge.title,
            "slug": challenge.slug,
            "message": challenge.message,
            "stakes_text": challenge.stakes_text,
            "visibility": challenge.visibility,
            "country_code": challenge.country_code,
            "region_name": challenge.region_name,
            "city_name": challenge.city_name,
            "status": challenge.status,
            "accept_by": challenge.accept_by,
            "scheduled_for": challenge.scheduled_for,
            "live_at": challenge.live_at,
            "published_at": challenge.published_at,
            "settled_at": challenge.settled_at,
            "countdown_seconds": self._challenge_countdown(challenge),
            "metadata_json": challenge.metadata_json or {},
            "created_at": challenge.created_at,
            "updated_at": challenge.updated_at,
        }

    def _challenge_response_view(self, response: ClubChallengeResponse) -> dict[str, object]:
        club = self._require_club(response.responding_club_id)
        return {
            "id": response.id,
            "challenge_id": response.challenge_id,
            "responding_club_id": response.responding_club_id,
            "responding_club_name": club.club_name,
            "responder_user_id": response.responder_user_id,
            "response_type": response.response_type,
            "response_status": response.response_status,
            "message": response.message,
            "scheduled_for": response.scheduled_for,
            "metadata_json": response.metadata_json or {},
            "created_at": response.created_at,
            "updated_at": response.updated_at,
        }

    def _challenge_link_view(self, link: ClubChallengeLink) -> dict[str, object]:
        return {
            "id": link.id,
            "challenge_id": link.challenge_id,
            "channel": link.channel,
            "link_code": link.link_code,
            "vanity_path": link.vanity_path,
            "web_path": link.web_path,
            "deep_link_path": link.deep_link_path,
            "is_primary": link.is_primary,
            "is_active": link.is_active,
            "click_count": link.click_count,
            "metadata_json": link.metadata_json or {},
            "created_at": link.created_at,
            "updated_at": link.updated_at,
        }

    def _share_stats(self, challenge_id: str) -> dict[str, object]:
        events = list(
            self.session.scalars(
                select(ChallengeShareEvent).where(ChallengeShareEvent.challenge_id == challenge_id)
            ).all()
        )
        country_breakdown: dict[str, int] = {}
        share_count = 0
        click_count = 0
        open_count = 0
        for event in events:
            normalized = self._normalize(event.event_type)
            if normalized == "share":
                share_count += 1
            if normalized == "click":
                click_count += 1
            if normalized in {"open", "view"}:
                open_count += 1
            if event.country_code:
                country_breakdown[event.country_code] = country_breakdown.get(event.country_code, 0) + 1
        return {
            "challenge_id": challenge_id,
            "total_events": len(events),
            "share_count": share_count,
            "click_count": click_count,
            "open_count": open_count,
            "country_breakdown": country_breakdown,
        }

    def _challenge_card(
        self,
        *,
        challenge: ClubChallenge,
        primary_link: ClubChallengeLink | None,
        share_stats: dict[str, object],
        rivalry: dict[str, object] | None,
        reactions: list[dict[str, object]],
    ) -> dict[str, object]:
        issuing_club = self._require_club(challenge.issuing_club_id)
        opponent_club_id = challenge.accepted_club_id or challenge.target_club_id
        opponent_club = self._club(opponent_club_id)
        reaction_weight = sum(int(item["intensity_score"]) for item in reactions[:5]) if reactions else 0
        rivalry_intensity = int(rivalry["intensity_score"]) if rivalry is not None else 0
        share_count = int(share_stats["share_count"]) if share_stats else 0
        return {
            "challenge_id": challenge.id,
            "title": challenge.title,
            "issuing_club_id": challenge.issuing_club_id,
            "issuing_club_name": issuing_club.club_name,
            "opponent_club_id": opponent_club_id,
            "opponent_club_name": opponent_club.club_name if opponent_club is not None else None,
            "status": challenge.status,
            "stakes_text": challenge.stakes_text,
            "countdown_seconds": self._challenge_countdown(challenge),
            "spectator_hype_score": (share_count * 8) + rivalry_intensity + (reaction_weight // 4),
            "rivalry_label": rivalry["label"] if rivalry is not None else None,
            "derby_indicator": bool(rivalry["derby_indicator"]) if rivalry is not None else False,
            "giant_killer_flag": bool(rivalry["giant_killer_flag"]) if rivalry is not None else False,
            "primary_web_path": primary_link.web_path if primary_link is not None else None,
            "primary_deep_link_path": primary_link.deep_link_path if primary_link is not None else None,
            "share_count": share_count,
        }

    def _challenge_countdown(self, challenge: ClubChallenge) -> int | None:
        now = self._now()
        target = None
        if challenge.status in {"scheduled", "accepted"} and challenge.scheduled_for is not None:
            scheduled_for = self._coerce_datetime(challenge.scheduled_for)
            if scheduled_for > now:
                target = scheduled_for
        elif challenge.status == "open" and challenge.accept_by is not None:
            accept_by = self._coerce_datetime(challenge.accept_by)
            if accept_by > now:
                target = accept_by
        if target is None:
            return None
        return max(0, int((target - now).total_seconds()))

    def _reaction_view(self, reaction: MatchReactionEvent) -> dict[str, object]:
        return {
            "id": reaction.id,
            "match_id": reaction.match_id,
            "competition_id": reaction.competition_id,
            "challenge_id": reaction.challenge_id,
            "rivalry_profile_id": reaction.rivalry_profile_id,
            "club_id": reaction.club_id,
            "reaction_type": reaction.reaction_type,
            "reaction_label": reaction.reaction_label,
            "intensity_score": reaction.intensity_score,
            "minute": reaction.minute,
            "happened_at": reaction.happened_at,
            "metadata_json": reaction.metadata_json or {},
            "created_at": reaction.created_at,
        }

    def _rivalry_profile(self, club_one_id: str, club_two_id: str) -> RivalryProfile | None:
        club_a_id, club_b_id = self._canonical_pair(club_one_id, club_two_id)
        return self.session.scalar(
            select(RivalryProfile).where(
                RivalryProfile.club_a_id == club_a_id,
                RivalryProfile.club_b_id == club_b_id,
            )
        )

    def _ensure_rivalry_profile(self, club_one_id: str, club_two_id: str) -> RivalryProfile:
        profile = self._rivalry_profile(club_one_id, club_two_id)
        if profile is not None:
            return profile
        club_a_id, club_b_id = self._canonical_pair(club_one_id, club_two_id)
        club_a = self._require_club(club_a_id)
        club_b = self._require_club(club_b_id)
        derby = self._is_derby(club_a, club_b)
        profile = RivalryProfile(
            club_a_id=club_a_id,
            club_b_id=club_b_id,
            label="Derby brewing" if derby else "Emerging rivalry",
            regional_derby=derby,
            notable_moments_json=[],
            narrative_tags_json=["derby"] if derby else [],
            metadata_json={},
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def _rivalry_summary(self, profile: RivalryProfile, perspective_club_id: str) -> dict[str, object]:
        if perspective_club_id not in {profile.club_a_id, profile.club_b_id}:
            raise ClubSocialError("rivalry_perspective_invalid")
        club = self._require_club(perspective_club_id)
        opponent_id = profile.club_b_id if perspective_club_id == profile.club_a_id else profile.club_a_id
        opponent = self._require_club(opponent_id)
        is_club_a = perspective_club_id == profile.club_a_id
        wins = profile.club_a_wins if is_club_a else profile.club_b_wins
        losses = profile.club_b_wins if is_club_a else profile.club_a_wins
        goals_for = profile.club_a_goals if is_club_a else profile.club_b_goals
        goals_against = profile.club_b_goals if is_club_a else profile.club_a_goals
        rematch_prompt = None
        if profile.giant_killer_flag or profile.challenge_matches > 0 or profile.streak_length >= 2:
            rematch_prompt = f"{club.club_name} and {opponent.club_name} are set up for a rematch."
        return {
            "rivalry_id": profile.id,
            "club_id": perspective_club_id,
            "club_name": club.club_name,
            "opponent_club_id": opponent.id,
            "opponent_club_name": opponent.club_name,
            "label": profile.label,
            "intensity_score": profile.intensity_score,
            "derby_indicator": profile.regional_derby,
            "giant_killer_flag": profile.giant_killer_flag,
            "matches_played": profile.matches_played,
            "wins": wins,
            "losses": losses,
            "draws": profile.draws,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "streak_holder_club_id": profile.streak_holder_club_id,
            "streak_length": profile.streak_length,
            "upset_count": profile.upset_count,
            "challenge_matches": profile.challenge_matches,
            "high_view_matches": profile.high_view_matches,
            "high_gift_matches": profile.high_gift_matches,
            "notable_moments": list(profile.notable_moments_json or []),
            "narrative_tags": list(profile.narrative_tags_json or []),
            "rematch_prompt": rematch_prompt,
            "last_match_at": profile.last_match_at,
        }

    def _rivalry_history_view(self, history: RivalryMatchHistory) -> dict[str, object]:
        return {
            "id": history.id,
            "rivalry_id": history.rivalry_id,
            "match_id": history.match_id,
            "competition_id": history.competition_id,
            "challenge_id": history.challenge_id,
            "home_club_id": history.home_club_id,
            "away_club_id": history.away_club_id,
            "winner_club_id": history.winner_club_id,
            "home_score": history.home_score,
            "away_score": history.away_score,
            "upset_flag": history.upset_flag,
            "final_flag": history.final_flag,
            "challenge_match_flag": history.challenge_match_flag,
            "high_view_flag": history.high_view_flag,
            "high_gift_flag": history.high_gift_flag,
            "view_count": history.view_count,
            "gift_count": history.gift_count,
            "match_weight": history.match_weight,
            "notable_moments": list(history.notable_moments_json or []),
            "happened_at": history.happened_at,
            "metadata_json": history.metadata_json or {},
            "created_at": history.created_at,
        }

    def _canonical_pair(self, club_one_id: str, club_two_id: str) -> tuple[str, str]:
        return tuple(sorted((club_one_id, club_two_id)))  # type: ignore[return-value]

    def _is_derby(self, home_club: ClubProfile, away_club: ClubProfile) -> bool:
        if home_club.city_name and away_club.city_name and home_club.city_name.strip().lower() == away_club.city_name.strip().lower():
            return True
        if home_club.region_name and away_club.region_name and home_club.region_name.strip().lower() == away_club.region_name.strip().lower():
            return True
        return bool(home_club.country_code and away_club.country_code and home_club.country_code == away_club.country_code)

    def _is_upset(self, home_club_id: str, away_club_id: str, winner_club_id: str | None) -> bool:
        if winner_club_id is None:
            return False
        home_power = self._club_power(home_club_id)
        away_power = self._club_power(away_club_id)
        if home_power <= 0 or away_power <= 0:
            return False
        winner_power = home_power if winner_club_id == home_club_id else away_power
        loser_power = away_power if winner_club_id == home_club_id else home_power
        return (winner_power + 120) < loser_power

    def _club_power(self, club_id: str) -> int:
        metrics = self.session.scalar(select(ClubIdentityMetrics).where(ClubIdentityMetrics.club_id == club_id))
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        rating = 0
        if reputation is not None:
            rating += reputation.current_score
        if metrics is not None:
            rating += metrics.fan_count // 10
            rating += metrics.club_valuation_minor // 5000
        return rating

    def _advance_streak(self, profile: RivalryProfile, winner_club_id: str | None) -> None:
        if winner_club_id is None:
            profile.streak_holder_club_id = None
            profile.streak_length = 0
            return
        if profile.streak_holder_club_id == winner_club_id:
            profile.streak_length += 1
            return
        profile.streak_holder_club_id = winner_club_id
        profile.streak_length = 1

    def _derive_rivalry_label(self, profile: RivalryProfile, *, derby: bool, upset: bool, challenge_match: bool) -> str:
        if derby and profile.matches_played >= 2:
            return "Local derby"
        if derby:
            return "Derby brewing"
        if upset and profile.upset_count >= 2:
            return "Giant-killer feud"
        if challenge_match and profile.challenge_matches >= 2:
            return "Challenge grudge"
        if profile.finals_played >= 1:
            return "Finals rivalry"
        if profile.matches_played >= 4:
            return "Running feud"
        return "Emerging rivalry"

    def _match_tags(
        self,
        *,
        derby: bool,
        upset: bool,
        final_flag: bool,
        challenge_match: bool,
        high_view: bool,
        high_gift: bool,
    ) -> list[str]:
        tags: list[str] = []
        if derby:
            tags.append("derby")
        if upset:
            tags.append("giant_killer")
        if final_flag:
            tags.append("high_stakes_final")
        if challenge_match:
            tags.append("challenge_grudge")
        if high_view:
            tags.append("viewer_surge")
        if high_gift:
            tags.append("gift_surge")
        return tags

    def _resolve_challenge_for_match(self, match: CompetitionMatch | None) -> ClubChallenge | None:
        if match is None:
            return None
        direct = self.session.scalar(select(ClubChallenge).where(ClubChallenge.linked_match_id == match.id))
        if direct is not None:
            return direct
        return self.session.scalar(
            select(ClubChallenge)
            .where(
                ClubChallenge.competition_id == match.competition_id,
                ClubChallenge.accepted_club_id.is_not(None),
                or_(
                    (
                        (ClubChallenge.issuing_club_id == match.home_club_id)
                        & (ClubChallenge.accepted_club_id == match.away_club_id)
                    ),
                    (
                        (ClubChallenge.issuing_club_id == match.away_club_id)
                        & (ClubChallenge.accepted_club_id == match.home_club_id)
                    ),
                ),
            )
            .order_by(ClubChallenge.updated_at.desc())
        )

    def _settle_linked_challenge(
        self,
        *,
        challenge_id: str | None,
        match_id: str | None,
        competition_id: str | None,
        winner_club_id: str | None,
        happened_at: datetime,
        home_club_id: str,
        away_club_id: str,
    ) -> None:
        challenge = None
        if challenge_id is not None:
            challenge = self.session.get(ClubChallenge, challenge_id)
        if challenge is None and match_id is not None:
            challenge = self.session.scalar(select(ClubChallenge).where(ClubChallenge.linked_match_id == match_id))
        if challenge is None and competition_id is not None:
            challenge = self.session.scalar(
                select(ClubChallenge)
                .where(
                    ClubChallenge.competition_id == competition_id,
                    ClubChallenge.status.in_(("accepted", "scheduled", "live")),
                    ClubChallenge.accepted_club_id.is_not(None),
                    or_(
                        (
                            (ClubChallenge.issuing_club_id == home_club_id)
                            & (ClubChallenge.accepted_club_id == away_club_id)
                        ),
                        (
                            (ClubChallenge.issuing_club_id == away_club_id)
                            & (ClubChallenge.accepted_club_id == home_club_id)
                        ),
                    ),
                )
                .order_by(ClubChallenge.updated_at.desc())
            )
        if challenge is None:
            return
        challenge.linked_match_id = match_id or challenge.linked_match_id
        challenge.winner_club_id = winner_club_id
        challenge.settled_at = happened_at
        challenge.status = "settled"

    def _create_outcome_reaction(
        self,
        *,
        match_id: str,
        competition_id: str | None,
        challenge_id: str | None,
        rivalry_profile_id: str | None,
        club_id: str | None,
        reaction_type: str,
        reaction_label: str,
        intensity_score: int,
        happened_at: datetime,
        metadata_json: dict[str, object],
    ) -> MatchReactionEvent:
        existing = self.session.scalar(
            select(MatchReactionEvent).where(
                MatchReactionEvent.match_id == match_id,
                MatchReactionEvent.reaction_type == reaction_type,
            )
        )
        if existing is not None:
            return existing
        reaction = MatchReactionEvent(
            match_id=match_id,
            competition_id=competition_id,
            challenge_id=challenge_id,
            rivalry_profile_id=rivalry_profile_id,
            club_id=club_id if club_id and self._club(club_id) is not None else None,
            reaction_type=reaction_type,
            reaction_label=reaction_label,
            intensity_score=intensity_score,
            happened_at=happened_at,
            metadata_json=dict(metadata_json),
        )
        self.session.add(reaction)
        self.session.flush()
        return reaction

    def _reaction_mapping(self, event: CompetitionMatchEvent) -> dict[str, object] | None:
        event_type = self._normalize(event.event_type)
        if event_type in {"goal", "penalty_goal"}:
            return {
                "reaction_type": "what_a_goal",
                "reaction_label": "What a goal",
                "intensity_score": 92 if event.highlight else 78,
            }
        if event_type in {"save", "penalty_save"}:
            return {
                "reaction_type": "big_save",
                "reaction_label": "Big save",
                "intensity_score": 84 if event.highlight else 70,
            }
        if event_type in {"missed_chance", "penalty_miss", "big_miss"}:
            return {
                "reaction_type": "missed_chance",
                "reaction_label": "Missed chance",
                "intensity_score": 68,
            }
        if event_type in {"red_card", "card"} and self._normalize(event.card_type) == "red":
            return {
                "reaction_type": "red_card_chaos",
                "reaction_label": "Red card chaos",
                "intensity_score": 88,
            }
        return None

    def _event_happened_at(self, event: CompetitionMatchEvent) -> datetime:
        return event.created_at

    def _notable_match_moments(self, match_id: str) -> list[str]:
        events = list(
            self.session.scalars(
                select(CompetitionMatchEvent)
                .where(
                    CompetitionMatchEvent.match_id == match_id,
                    CompetitionMatchEvent.highlight.is_(True),
                )
                .order_by(CompetitionMatchEvent.created_at.desc())
                .limit(4)
            ).all()
        )
        notable: list[str] = []
        for event in events:
            label = self._normalize(event.event_type, default="moment").replace("_", " ")
            if event.minute is not None:
                notable.append(f"{label} {event.minute}'")
            else:
                notable.append(label)
        return notable

    def _winner_from_score(self, home_club_id: str, away_club_id: str, home_score: int, away_score: int) -> str | None:
        if home_score > away_score:
            return home_club_id
        if away_score > home_score:
            return away_club_id
        return None

    def _primary_link(self, challenge_id: str) -> ClubChallengeLink | None:
        return self.session.scalar(
            select(ClubChallengeLink)
            .where(
                ClubChallengeLink.challenge_id == challenge_id,
                ClubChallengeLink.is_primary.is_(True),
            )
            .order_by(ClubChallengeLink.created_at.desc())
        )

    def _club_name(self, club_id: str) -> str:
        club = self._club(club_id)
        return club.club_name if club is not None else club_id

    def _has_club_profiles(self, club_one_id: str | None, club_two_id: str | None) -> bool:
        return self._club(club_one_id) is not None and self._club(club_two_id) is not None

    def _merge_strings(self, existing: list[str] | None, incoming: list[str], *, limit: int | None = None) -> list[str]:
        merged: list[str] = []
        for item in (existing or []) + incoming:
            cleaned = self._clean(item)
            if not cleaned or cleaned in merged:
                continue
            merged.append(cleaned)
        if limit is not None:
            return merged[:limit]
        return merged

    def _coerce_int(self, value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _coerce_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _normalize(self, value: str | None, *, default: str | None = None, upper: bool = False) -> str | None:
        if value is None:
            return default.upper() if upper and default is not None else default
        cleaned = value.strip()
        if not cleaned:
            return default.upper() if upper and default is not None else default
        return cleaned.upper() if upper else cleaned.lower()

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _now(self) -> datetime:
        return datetime.now(UTC)
