from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.hosted_competition_engine.coin_aware_service import (
    CoinAwareHostedCompetitionService as HostedCompetitionService,
)
from app.hosted_competition_engine.service import HostedCompetitionError
from app.ingestion.models import Country, Player
from app.models.club_infra import ClubStadium
from app.models.club_profile import ClubLifecycleStatus, ClubProfile
from app.models.club_social import SocialFollow
from app.models.club_trophy import ClubTrophy
from app.models.community_engine import (
    CommunityReaction,
    CommunityUserBlock,
    MessageVisibility,
    PrivateMessage,
    PrivateMessageParticipant,
    PrivateMessageThread,
)
from app.models.community_social import (
    CommunityBookmark,
    CommunityChannel,
    CommunityChannelMessage,
    CommunityCompetitionApplication,
    CommunityPollVote,
    CommunityPost,
    CommunityPostComment,
    CommunityUserMute,
)
from app.models.hosted_competition import (
    HostedCompetitionStatus,
    UserHostedCompetition,
    UserHostedCompetitionParticipant,
)
from app.models.moderation_report import (
    ModerationPriority,
    ModerationReport,
    ModerationReportStatus,
    ModerationResolutionAction,
)
from app.models.regen import RegenProfile
from app.models.user import User, UserRole
from app.models.history_engagement import UserFollow

CANONICAL_CHANNELS: tuple[dict[str, str], ...] = (
    {
        "slug": "global-lounge",
        "name": "GTEX Global Lounge",
        "category": "general",
        "description": "Open platform-wide lobby for football banter, platform updates, and meeting fellow managers.",
        "icon": "globe",
    },
    {
        "slug": "football-talk",
        "name": "Football Talk",
        "category": "football",
        "description": "Real-world and GTEX football discussion across leagues, tactics, and matchdays.",
        "icon": "message-circle",
    },
    {
        "slug": "gtex-players",
        "name": "GTEX Players",
        "category": "players",
        "description": "Spotlights, ratings debate, and form tracking across GTEX player assets and legends.",
        "icon": "star",
    },
    {
        "slug": "gtex-regens",
        "name": "GTEX Regens",
        "category": "regens",
        "description": "Academy breakthroughs, wonderkids, potential curves, and generational regen talent.",
        "icon": "sparkles",
    },
    {
        "slug": "club-showcase",
        "name": "Club Showcase",
        "category": "clubs",
        "description": "Promote your club identity, silverware, stadium projects, and supporter culture.",
        "icon": "shield",
    },
    {
        "slug": "transfer-talk",
        "name": "Transfer Talk",
        "category": "transfers",
        "description": "Market valuations, rumours, squad targets, and recruitment pitch decks.",
        "icon": "repeat",
    },
    {
        "slug": "matchday",
        "name": "Matchday",
        "category": "matchday",
        "description": "Live fixture reactions, tactical twists, and full-time verdicts.",
        "icon": "activity",
    },
    {
        "slug": "competitions-recruitment",
        "name": "Competitions & Recruitment",
        "category": "competitions",
        "description": "Find open cups, league openings, and recruit clubs into user-hosted competitions.",
        "icon": "trophy",
    },
    {
        "slug": "user-hosted-tournaments",
        "name": "User-Hosted Tournaments",
        "category": "tournaments",
        "description": "Organiser announcements, fixture schedules, and tournament community chat.",
        "icon": "award",
    },
    {
        "slug": "fans-and-supporters",
        "name": "Fans & Supporters",
        "category": "supporters",
        "description": "Supporter campaigns, club chants, fan groups, and rivalry stories.",
        "icon": "users",
    },
    {
        "slug": "tactics-debate",
        "name": "Tactics & Football Debate",
        "category": "tactics",
        "description": "Formations, pressing traps, buildup structures, and managerial philosophy.",
        "icon": "compass",
    },
)

ALLOWED_POST_TYPES: frozenset[str] = frozenset(
    {
        "football_discussion",
        "club_showcase",
        "club_achievement",
        "club_recruitment",
        "supporter_recruitment",
        "player_showcase",
        "regen_showcase",
        "transfer_update",
        "competition_ad",
        "competition_recruitment",
        "matchday",
        "poll",
        "club_announcement",
    }
)

_MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]{2,32})")
_SLUG_RE = re.compile(r"[^a-z0-9-]+")
_SPAM_WINDOW_SECONDS = 20
_SPAM_MAX_MESSAGES = 8


class CommunitySocialError(ValueError):
    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _is_admin(user: User | None) -> bool:
    return bool(user is not None and user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN})


def _user_summary(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "avatar_url": user.avatar_url,
        "account_type": user.account_type.value if hasattr(user.account_type, "value") else str(user.account_type),
        "favourite_club": user.favourite_club,
        "is_admin": _is_admin(user),
    }


def _blocked_and_muted_ids(session: Session, actor: User | None) -> tuple[set[str], set[str]]:
    if actor is None:
        return set(), set()
    blocked_out = set(
        session.scalars(
            select(CommunityUserBlock.blocked_user_id).where(CommunityUserBlock.blocker_user_id == actor.id)
        ).all()
    )
    blocked_in = set(
        session.scalars(
            select(CommunityUserBlock.blocker_user_id).where(CommunityUserBlock.blocked_user_id == actor.id)
        ).all()
    )
    muted = set(
        session.scalars(select(CommunityUserMute.muted_user_id).where(CommunityUserMute.user_id == actor.id)).all()
    )
    return blocked_out | blocked_in, muted


def _resolve_mentions(session: Session, body: str) -> list[dict[str, Any]]:
    usernames = list(dict.fromkeys(match.group(1) for match in _MENTION_RE.finditer(body)))[:10]
    if not usernames:
        return []
    users = list(session.scalars(select(User).where(User.username.in_(usernames), User.is_active.is_(True))).all())
    return [
        {
            "type": "user",
            "id": item.id,
            "username": item.username,
            "display_name": item.display_name or item.username,
        }
        for item in users
    ]


def _publish_community_realtime(topic: str, event_type: str, data: dict[str, Any]) -> None:
    try:
        from app.realtime.service import RealtimeDispatch, get_global_realtime_hub

        hub = get_global_realtime_hub()
        if hub is None:
            return
        hub.publish_direct_sync(RealtimeDispatch(type=event_type, topics=(topic,), data=data))
    except Exception:
        return


def _notify_mentions(
    session: Session,
    *,
    actor: User,
    mentions: list[dict[str, Any]],
    resource_id: str,
    deep_link_route: str,
    preview: str,
) -> None:
    target_ids = [item["id"] for item in mentions if item.get("id") and item["id"] != actor.id]
    if not target_ids:
        return
    try:
        from app.notifications.service import NotificationEventMatrixService

        NotificationEventMatrixService(session).publish_event(
            event_key="community_mention",
            target_user_ids=target_ids,
            resource_id=resource_id,
            message=f"{actor.display_name or actor.username} mentioned you: {preview[:100]}",
            metadata_json={"deep_link_route": deep_link_route, "actor_user_id": actor.id},
        )
    except Exception:
        return


def _check_channel_rate_limit(session: Session, actor: User, channel_id: str, body: str) -> None:
    window_start = datetime.now(timezone.utc) - timedelta(seconds=_SPAM_WINDOW_SECONDS)
    recent_msgs = list(
        session.scalars(
            select(CommunityChannelMessage)
            .where(
                CommunityChannelMessage.sender_user_id == actor.id,
                CommunityChannelMessage.created_at >= window_start,
            )
            .order_by(CommunityChannelMessage.created_at.desc())
        ).all()
    )
    if len(recent_msgs) >= _SPAM_MAX_MESSAGES:
        raise CommunitySocialError("Slow down: you are sending messages too quickly.", status_code=429)
    if recent_msgs:
        latest = recent_msgs[0]
        latest_at = latest.created_at if latest.created_at.tzinfo else latest.created_at.replace(tzinfo=timezone.utc)
        if (
            latest.channel_id == channel_id
            and latest.body.strip().lower() == body.strip().lower()
            and (datetime.now(timezone.utc) - latest_at) < timedelta(seconds=5)
        ):
            raise CommunitySocialError("Duplicate message sent too quickly.", status_code=429)


def _reaction_summary(
    session: Session, *, entity_type: str, entity_ids: list[str], actor_id: str | None
) -> tuple[dict[str, dict[str, int]], dict[str, list[str]]]:
    if not entity_ids:
        return {}, {}
    rows = list(
        session.scalars(
            select(CommunityReaction).where(
                CommunityReaction.entity_type == entity_type,
                CommunityReaction.entity_id.in_(entity_ids),
            )
        ).all()
    )
    counts: dict[str, dict[str, int]] = {}
    mine: dict[str, list[str]] = {}
    for row in rows:
        bucket = counts.setdefault(row.entity_id, {})
        bucket[row.reaction_type] = bucket.get(row.reaction_type, 0) + 1
        if actor_id and row.user_id == actor_id:
            mine.setdefault(row.entity_id, []).append(row.reaction_type)
    return counts, mine


@dataclass(slots=True)
class CommunitySocialService:
    session: Session

    def ensure_default_channels(self) -> list[CommunityChannel]:
        existing = {ch.slug: ch for ch in self.session.scalars(select(CommunityChannel)).all()}
        created_any = False
        for item in CANONICAL_CHANNELS:
            if item["slug"] in existing:
                continue
            ch = CommunityChannel(
                slug=item["slug"],
                name=item["name"],
                category=item["category"],
                description=item["description"],
                icon=item["icon"],
                is_official=True,
                is_archived=False,
                is_read_only=False,
                last_message_seq=0,
            )
            self.session.add(ch)
            existing[item["slug"]] = ch
            created_any = True
        if created_any:
            self.session.flush()
        return [existing[item["slug"]] for item in CANONICAL_CHANNELS if item["slug"] in existing]

    def list_channels(self) -> list[dict[str, Any]]:
        self.ensure_default_channels()
        channels = list(
            self.session.scalars(
                select(CommunityChannel)
                .where(CommunityChannel.is_archived.is_(False))
                .order_by(CommunityChannel.is_official.desc(), CommunityChannel.name.asc())
            ).all()
        )
        msg_counts = dict(
            self.session.execute(
                select(CommunityChannelMessage.channel_id, func.count(CommunityChannelMessage.id))
                .where(CommunityChannelMessage.visibility == "public")
                .group_by(CommunityChannelMessage.channel_id)
            ).all()
        )
        order_map = {item["slug"]: idx for idx, item in enumerate(CANONICAL_CHANNELS)}
        channels.sort(key=lambda ch: (order_map.get(ch.slug, 999), ch.name.lower()))
        return [
            {
                "id": ch.id,
                "slug": ch.slug,
                "name": ch.name,
                "category": ch.category,
                "description": ch.description,
                "icon": ch.icon,
                "is_official": bool(ch.is_official),
                "is_read_only": bool(ch.is_read_only),
                "message_count": int(msg_counts.get(ch.id, 0)),
                "last_message_seq": int(ch.last_message_seq or 0),
                "last_message_at": ch.last_message_at.isoformat() if ch.last_message_at else None,
            }
            for ch in channels
        ]

    def create_channel(self, *, actor: User, name: str, description: str, category: str = "general") -> dict[str, Any]:
        clean_name = name.strip()
        if len(clean_name) < 3:
            raise CommunitySocialError("Channel name must be at least 3 characters.")
        slug = _SLUG_RE.sub("-", clean_name.lower()).strip("-")[:72]
        if not slug:
            raise CommunitySocialError("Channel name must contain alphanumeric characters.")
        if self.session.scalar(select(CommunityChannel).where(CommunityChannel.slug == slug)) is not None:
            raise CommunitySocialError("A channel with this name already exists.", status_code=409)
        ch = CommunityChannel(
            slug=slug,
            name=clean_name,
            category=category.strip() or "general",
            description=description.strip(),
            icon="hash",
            is_official=_is_admin(actor),
            is_archived=False,
            is_read_only=False,
            created_by_user_id=actor.id,
        )
        self.session.add(ch)
        self.session.flush()
        return {
            "id": ch.id,
            "slug": ch.slug,
            "name": ch.name,
            "category": ch.category,
            "description": ch.description,
            "icon": ch.icon,
            "is_official": bool(ch.is_official),
            "is_read_only": bool(ch.is_read_only),
            "message_count": 0,
            "last_message_seq": 0,
            "last_message_at": None,
        }

    def list_channel_messages(
        self,
        *,
        slug: str,
        actor: User | None,
        before_seq: int | None = None,
        after_seq: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self.ensure_default_channels()
        ch = self.session.scalar(select(CommunityChannel).where(CommunityChannel.slug == slug))
        if ch is None:
            raise CommunitySocialError("Community channel not found.", status_code=404)
        blocked_ids, muted_ids = _blocked_and_muted_ids(self.session, actor)
        excluded_senders = blocked_ids | muted_ids

        q = select(CommunityChannelMessage).where(CommunityChannelMessage.channel_id == ch.id)
        if not _is_admin(actor):
            q = q.where(CommunityChannelMessage.visibility == "public")
        if excluded_senders:
            q = q.where(~CommunityChannelMessage.sender_user_id.in_(excluded_senders))
        if after_seq is not None:
            q = q.where(CommunityChannelMessage.seq > after_seq).order_by(CommunityChannelMessage.seq.asc())
            rows = list(self.session.scalars(q.limit(limit)).all())
            has_more = False
        else:
            if before_seq is not None:
                q = q.where(CommunityChannelMessage.seq < before_seq)
            rows_desc = list(
                self.session.scalars(q.order_by(CommunityChannelMessage.seq.desc()).limit(limit + 1)).all()
            )
            has_more = len(rows_desc) > limit
            rows = list(reversed(rows_desc[:limit]))

        pinned_rows = list(
            self.session.scalars(
                select(CommunityChannelMessage)
                .where(
                    CommunityChannelMessage.channel_id == ch.id,
                    CommunityChannelMessage.pinned.is_(True),
                    CommunityChannelMessage.visibility == "public",
                )
                .order_by(CommunityChannelMessage.seq.desc())
                .limit(5)
            ).all()
        )
        hydrated = self._hydrate_channel_messages(
            rows + [p for p in pinned_rows if p.id not in {r.id for r in rows}], actor
        )
        by_id = {item["id"]: item for item in hydrated}
        return {
            "channel": {
                "id": ch.id,
                "slug": ch.slug,
                "name": ch.name,
                "category": ch.category,
                "description": ch.description,
                "last_message_seq": int(ch.last_message_seq or 0),
                "is_read_only": bool(ch.is_read_only),
            },
            "messages": [by_id[r.id] for r in rows],
            "pinned_messages": [by_id[p.id] for p in pinned_rows],
            "has_more": has_more,
            "next_before_seq": int(rows[0].seq) if has_more and rows else None,
            "latest_seq": int(ch.last_message_seq or 0),
        }

    def post_channel_message(
        self,
        *,
        slug: str,
        actor: User,
        body: str,
        reply_to_message_id: str | None = None,
        linked_entities: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.ensure_default_channels()
        ch = self.session.scalar(select(CommunityChannel).where(CommunityChannel.slug == slug))
        if ch is None:
            raise CommunitySocialError("Community channel not found.", status_code=404)
        if ch.is_read_only and not _is_admin(actor):
            raise CommunitySocialError("This channel is currently read-only.", status_code=403)
        clean_body = body.strip()
        if not clean_body:
            raise CommunitySocialError("Message cannot be empty.")
        if len(clean_body) > 2000:
            raise CommunitySocialError("Message exceeds 2000 characters.")
        _check_channel_rate_limit(self.session, actor, ch.id, clean_body)

        if reply_to_message_id:
            parent = self.session.get(CommunityChannelMessage, reply_to_message_id)
            if parent is None or parent.channel_id != ch.id:
                raise CommunitySocialError("Reply target message not found in this channel.", status_code=404)

        next_seq = (
            max(
                int(ch.last_message_seq or 0),
                int(
                    self.session.scalar(
                        select(func.coalesce(func.max(CommunityChannelMessage.seq), 0)).where(
                            CommunityChannelMessage.channel_id == ch.id
                        )
                    )
                    or 0
                ),
            )
            + 1
        )
        mentions = _resolve_mentions(self.session, clean_body)
        now = datetime.now(timezone.utc)
        msg = CommunityChannelMessage(
            channel_id=ch.id,
            seq=next_seq,
            sender_user_id=actor.id,
            reply_to_message_id=reply_to_message_id,
            body=clean_body,
            visibility="public",
            mentions_json=mentions,
            linked_entities_json=dict(linked_entities or {}),
            created_at=now,
            updated_at=now,
        )
        self.session.add(msg)
        ch.last_message_seq = next_seq
        ch.last_message_at = now
        self.session.flush()

        _notify_mentions(
            self.session,
            actor=actor,
            mentions=mentions,
            resource_id=msg.id,
            deep_link_route=f"/app/community?tab=channels&channel={ch.slug}",
            preview=clean_body,
        )
        payload = self._hydrate_channel_messages([msg], actor)[0]
        _publish_community_realtime(
            f"community:channel:{ch.slug}",
            "community_channel_message",
            {"channel_slug": ch.slug, "message": payload},
        )
        return payload

    def toggle_channel_pin(self, *, message_id: str, actor: User, pinned: bool | None = None) -> dict[str, Any]:
        msg = self.session.get(CommunityChannelMessage, message_id)
        if msg is None:
            raise CommunitySocialError("Channel message not found.", status_code=404)
        ch = self.session.get(CommunityChannel, msg.channel_id)
        if not _is_admin(actor) and (ch is None or ch.created_by_user_id != actor.id):
            raise CommunitySocialError("Only moderators or the channel creator can pin messages.", status_code=403)
        target = (not msg.pinned) if pinned is None else bool(pinned)
        msg.pinned = target
        msg.pinned_at = datetime.now(timezone.utc) if target else None
        self.session.flush()
        return self._hydrate_channel_messages([msg], actor)[0]

    def _hydrate_channel_messages(
        self, rows: list[CommunityChannelMessage], actor: User | None
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        user_ids = list({r.sender_user_id for r in rows})
        users = {u.id: u for u in self.session.scalars(select(User).where(User.id.in_(user_ids))).all()}
        reply_ids = list({r.reply_to_message_id for r in rows if r.reply_to_message_id})
        replies = (
            {
                m.id: m
                for m in self.session.scalars(
                    select(CommunityChannelMessage).where(CommunityChannelMessage.id.in_(reply_ids))
                ).all()
            }
            if reply_ids
            else {}
        )
        counts, mine = _reaction_summary(
            self.session,
            entity_type="channel_message",
            entity_ids=[r.id for r in rows],
            actor_id=actor.id if actor else None,
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            reply_msg = replies.get(r.reply_to_message_id or "")
            out.append(
                {
                    "id": r.id,
                    "channel_id": r.channel_id,
                    "seq": int(r.seq or 0),
                    "sender_user_id": r.sender_user_id,
                    "sender": _user_summary(users.get(r.sender_user_id)),
                    "reply_to_message_id": r.reply_to_message_id,
                    "reply_preview": (
                        {
                            "id": reply_msg.id,
                            "body": reply_msg.body[:120],
                            "sender_user_id": reply_msg.sender_user_id,
                        }
                        if reply_msg
                        else None
                    ),
                    "body": r.body,
                    "visibility": r.visibility,
                    "pinned": bool(r.pinned),
                    "mentions": list(r.mentions_json or []),
                    "linked_entities": dict(r.linked_entities_json or {}),
                    "reactions": counts.get(r.id, {}),
                    "viewer_reactions": mine.get(r.id, []),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return out

    # ---------------- SOCIAL FEED POSTS ----------------

    def create_post(
        self,
        *,
        actor: User,
        post_type: str,
        body: str,
        title: str | None = None,
        channel_slug: str | None = None,
        club_id: str | None = None,
        player_id: str | None = None,
        competition_id: str | None = None,
        competition_source: str | None = None,
        tags: list[str] | None = None,
        poll_options: list[str] | None = None,
    ) -> dict[str, Any]:
        p_type = (post_type or "football_discussion").strip().lower()
        if p_type not in ALLOWED_POST_TYPES:
            raise CommunitySocialError(f"Unsupported post type '{p_type}'.")
        clean_body = body.strip()
        if not clean_body:
            raise CommunitySocialError("Post body cannot be empty.")
        if len(clean_body) > 4000:
            raise CommunitySocialError("Post body cannot exceed 4000 characters.")

        clean_title = (title or "").strip()[:200] or None
        is_official = False
        if _is_admin(actor) and (clean_title and "[official]" in clean_title.lower()):
            is_official = True

        if club_id:
            club = self.session.get(ClubProfile, club_id)
            if club is None:
                raise CommunitySocialError("Referenced club was not found.", status_code=404)
            if p_type == "club_announcement" and club.owner_user_id != actor.id and not _is_admin(actor):
                raise CommunitySocialError(
                    "Only the club owner can publish an official club announcement.", status_code=403
                )

        if player_id:
            player = self.session.get(Player, player_id)
            if player is None or (player.real_player_tier or "").lower() == "archived_duplicate":
                raise CommunitySocialError("Referenced player was not found.", status_code=404)

        resolved_comp_source = competition_source
        if competition_id:
            hosted = self.session.get(UserHostedCompetition, competition_id)
            if hosted is not None:
                resolved_comp_source = "hosted"
            else:
                from app.owner_console.models import OwnerCompetition

                owner_comp = self.session.get(OwnerCompetition, competition_id)
                if owner_comp is None:
                    raise CommunitySocialError("Referenced competition was not found.", status_code=404)
                resolved_comp_source = "owner"

        structured_poll: list[dict[str, Any]] = []
        if p_type == "poll":
            opts = [item.strip() for item in (poll_options or []) if item and item.strip()]
            if len(opts) < 2 or len(opts) > 6:
                raise CommunitySocialError("Polls require between 2 and 6 options.")
            structured_poll = [{"id": f"opt_{idx + 1}", "label": opt[:100]} for idx, opt in enumerate(opts)]

        clean_tags = [_SLUG_RE.sub("-", t.strip().lower()).strip("-")[:32] for t in (tags or []) if t and t.strip()][:8]
        mentions = _resolve_mentions(self.session, clean_body)
        post = CommunityPost(
            author_user_id=actor.id,
            post_type=p_type,
            title=clean_title,
            body=clean_body,
            channel_slug=channel_slug.strip() if channel_slug else None,
            club_id=club_id or None,
            player_id=player_id or None,
            competition_id=competition_id or None,
            competition_source=resolved_comp_source,
            tags_json=clean_tags,
            mentions_json=mentions,
            poll_options_json=structured_poll,
            visibility="public",
            is_official=is_official,
        )
        self.session.add(post)
        self.session.flush()

        _notify_mentions(
            self.session,
            actor=actor,
            mentions=mentions,
            resource_id=post.id,
            deep_link_route=f"/app/community?post={post.id}",
            preview=clean_title or clean_body,
        )
        hydrated = self._hydrate_posts([post], actor)[0]
        _publish_community_realtime("community:feed", "community_post_created", {"post": hydrated})
        return hydrated

    def list_posts(
        self,
        *,
        actor: User | None,
        post_type: str | None = None,
        channel_slug: str | None = None,
        club_id: str | None = None,
        competition_id: str | None = None,
        search: str | None = None,
        sort: str = "recent",
        saved_only: bool = False,
        limit: int = 30,
        offset: int = 0,
    ) -> dict[str, Any]:
        blocked_ids, muted_ids = _blocked_and_muted_ids(self.session, actor)
        excluded = blocked_ids | muted_ids

        q = select(CommunityPost)
        if not _is_admin(actor):
            q = q.where(CommunityPost.visibility == "public")
        if excluded:
            q = q.where(~CommunityPost.author_user_id.in_(excluded))
        if post_type:
            q = q.where(CommunityPost.post_type == post_type.strip().lower())
        if channel_slug:
            q = q.where(CommunityPost.channel_slug == channel_slug.strip().lower())
        if club_id:
            q = q.where(CommunityPost.club_id == club_id.strip())
        if competition_id:
            q = q.where(CommunityPost.competition_id == competition_id.strip())
        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.where(or_(CommunityPost.title.ilike(term), CommunityPost.body.ilike(term)))
        if saved_only:
            if actor is None:
                return {"posts": [], "total": 0}
            saved_ids = select(CommunityBookmark.post_id).where(CommunityBookmark.user_id == actor.id)
            q = q.where(CommunityPost.id.in_(saved_ids))

        sort_mode = (sort or "recent").strip().lower()
        if sort_mode == "recruiting":
            q = q.where(
                CommunityPost.post_type.in_(
                    ["club_recruitment", "supporter_recruitment", "competition_ad", "competition_recruitment"]
                )
            )
        if sort_mode == "trending":
            q = q.order_by(
                CommunityPost.is_pinned.desc(),
                (CommunityPost.reaction_count + CommunityPost.comment_count * 2).desc(),
                CommunityPost.created_at.desc(),
            )
        elif sort_mode == "top":
            q = q.order_by(CommunityPost.reaction_count.desc(), CommunityPost.created_at.desc())
        else:
            q = q.order_by(CommunityPost.is_pinned.desc(), CommunityPost.created_at.desc())

        rows = list(self.session.scalars(q.offset(offset).limit(limit)).all())
        return {"posts": self._hydrate_posts(rows, actor), "count": len(rows)}

    def update_or_delete_post(
        self,
        *,
        post_id: str,
        actor: User,
        title: str | None = None,
        body: str | None = None,
        delete: bool = False,
    ) -> dict[str, Any]:
        post = self.session.get(CommunityPost, post_id)
        if post is None:
            raise CommunitySocialError("Post not found.", status_code=404)
        if post.author_user_id != actor.id and not _is_admin(actor):
            raise CommunitySocialError("Only the author or an admin can modify this post.", status_code=403)
        if delete:
            post.visibility = "deleted"
            self.session.flush()
            return {"status": "deleted", "post_id": post.id}
        if title is not None:
            post.title = title.strip()[:200] or None
        if body is not None:
            clean = body.strip()
            if not clean:
                raise CommunitySocialError("Post body cannot be empty.")
            post.body = clean
            post.mentions_json = _resolve_mentions(self.session, clean)
        self.session.flush()
        return self._hydrate_posts([post], actor)[0]

    def toggle_post_reaction(self, *, post_id: str, actor: User, reaction_type: str = "like") -> dict[str, Any]:
        post = self.session.get(CommunityPost, post_id)
        if post is None or post.visibility == "deleted":
            raise CommunitySocialError("Post not found.", status_code=404)
        r_type = (reaction_type or "like").strip().lower()[:24]
        existing = self.session.scalar(
            select(CommunityReaction).where(
                CommunityReaction.entity_type == "post",
                CommunityReaction.entity_id == post.id,
                CommunityReaction.user_id == actor.id,
                CommunityReaction.reaction_type == r_type,
            )
        )
        if existing is not None:
            self.session.delete(existing)
            active = False
        else:
            self.session.add(
                CommunityReaction(
                    entity_type="post",
                    entity_id=post.id,
                    user_id=actor.id,
                    reaction_type=r_type,
                )
            )
            active = True
        self.session.flush()
        total = int(
            self.session.scalar(
                select(func.count(CommunityReaction.id)).where(
                    CommunityReaction.entity_type == "post",
                    CommunityReaction.entity_id == post.id,
                )
            )
            or 0
        )
        post.reaction_count = total
        self.session.flush()
        return {"post_id": post.id, "reaction_type": r_type, "active": active, "reaction_count": total}

    def toggle_bookmark(self, *, post_id: str, actor: User) -> dict[str, Any]:
        post = self.session.get(CommunityPost, post_id)
        if post is None or post.visibility == "deleted":
            raise CommunitySocialError("Post not found.", status_code=404)
        existing = self.session.scalar(
            select(CommunityBookmark).where(
                CommunityBookmark.user_id == actor.id,
                CommunityBookmark.post_id == post.id,
            )
        )
        if existing is not None:
            self.session.delete(existing)
            saved = False
        else:
            self.session.add(CommunityBookmark(user_id=actor.id, post_id=post.id))
            saved = True
        self.session.flush()
        total = int(
            self.session.scalar(select(func.count(CommunityBookmark.id)).where(CommunityBookmark.post_id == post.id))
            or 0
        )
        post.bookmark_count = total
        self.session.flush()
        return {"post_id": post.id, "bookmarked": saved, "bookmark_count": total}

    def vote_poll(self, *, post_id: str, actor: User, option_id: str) -> dict[str, Any]:
        post = self.session.get(CommunityPost, post_id)
        if post is None or post.visibility == "deleted" or post.post_type != "poll":
            raise CommunitySocialError("Poll not found.", status_code=404)
        valid_ids = {opt.get("id") for opt in (post.poll_options_json or []) if isinstance(opt, dict)}
        if option_id not in valid_ids:
            raise CommunitySocialError("Invalid poll option.")
        vote = self.session.scalar(
            select(CommunityPollVote).where(
                CommunityPollVote.post_id == post.id,
                CommunityPollVote.user_id == actor.id,
            )
        )
        if vote is None:
            self.session.add(CommunityPollVote(post_id=post.id, user_id=actor.id, option_id=option_id))
        else:
            vote.option_id = option_id
        self.session.flush()
        return self._hydrate_posts([post], actor)[0]

    def list_post_comments(self, *, post_id: str, actor: User | None) -> list[dict[str, Any]]:
        post = self.session.get(CommunityPost, post_id)
        if post is None or post.visibility == "deleted":
            raise CommunitySocialError("Post not found.", status_code=404)
        blocked_ids, muted_ids = _blocked_and_muted_ids(self.session, actor)
        excluded = blocked_ids | muted_ids
        q = select(CommunityPostComment).where(CommunityPostComment.post_id == post.id)
        if not _is_admin(actor):
            q = q.where(CommunityPostComment.visibility == "public")
        if excluded:
            q = q.where(~CommunityPostComment.author_user_id.in_(excluded))
        rows = list(self.session.scalars(q.order_by(CommunityPostComment.created_at.asc())).all())
        user_ids = list({r.author_user_id for r in rows})
        users = (
            {u.id: u for u in self.session.scalars(select(User).where(User.id.in_(user_ids))).all()} if user_ids else {}
        )
        return [
            {
                "id": r.id,
                "post_id": r.post_id,
                "parent_comment_id": r.parent_comment_id,
                "author_user_id": r.author_user_id,
                "author": _user_summary(users.get(r.author_user_id)),
                "body": r.body,
                "visibility": r.visibility,
                "mentions": list(r.mentions_json or []),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    def add_post_comment(
        self,
        *,
        post_id: str,
        actor: User,
        body: str,
        parent_comment_id: str | None = None,
    ) -> dict[str, Any]:
        post = self.session.get(CommunityPost, post_id)
        if post is None or post.visibility == "deleted":
            raise CommunitySocialError("Post not found.", status_code=404)
        if post.is_locked and not _is_admin(actor):
            raise CommunitySocialError("Comments are locked on this post.", status_code=403)
        clean_body = body.strip()
        if not clean_body:
            raise CommunitySocialError("Comment body cannot be empty.")
        mentions = _resolve_mentions(self.session, clean_body)
        comment = CommunityPostComment(
            post_id=post.id,
            author_user_id=actor.id,
            parent_comment_id=parent_comment_id,
            body=clean_body,
            mentions_json=mentions,
        )
        self.session.add(comment)
        self.session.flush()
        post.comment_count = int(
            self.session.scalar(
                select(func.count(CommunityPostComment.id)).where(
                    CommunityPostComment.post_id == post.id,
                    CommunityPostComment.visibility == "public",
                )
            )
            or 0
        )
        self.session.flush()
        _notify_mentions(
            self.session,
            actor=actor,
            mentions=mentions,
            resource_id=comment.id,
            deep_link_route=f"/app/community?post={post.id}",
            preview=clean_body,
        )
        return {
            "id": comment.id,
            "post_id": comment.post_id,
            "parent_comment_id": comment.parent_comment_id,
            "author_user_id": comment.author_user_id,
            "author": _user_summary(actor),
            "body": comment.body,
            "visibility": comment.visibility,
            "mentions": mentions,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }

    def _hydrate_posts(self, posts: list[CommunityPost], actor: User | None) -> list[dict[str, Any]]:
        if not posts:
            return []
        author_ids = list({p.author_user_id for p in posts})
        authors = {u.id: u for u in self.session.scalars(select(User).where(User.id.in_(author_ids))).all()}

        club_ids = list({p.club_id for p in posts if p.club_id})
        clubs = (
            {c.id: c for c in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(club_ids))).all()}
            if club_ids
            else {}
        )
        follower_counts: dict[str, int] = {}
        viewer_follows: set[str] = set()
        if club_ids:
            follower_counts = {
                str(k): int(v)
                for k, v in self.session.execute(
                    select(SocialFollow.club_id, func.count(SocialFollow.id))
                    .where(SocialFollow.club_id.in_(club_ids))
                    .group_by(SocialFollow.club_id)
                ).all()
                if k
            }
            if actor is not None:
                viewer_follows = {
                    str(item)
                    for item in self.session.scalars(
                        select(SocialFollow.club_id).where(
                            SocialFollow.user_id == actor.id,
                            SocialFollow.club_id.in_(club_ids),
                        )
                    ).all()
                    if item
                }

        player_ids = list({p.player_id for p in posts if p.player_id})
        players = (
            {pl.id: pl for pl in self.session.scalars(select(Player).where(Player.id.in_(player_ids))).all()}
            if player_ids
            else {}
        )
        comp_ids = list({p.competition_id for p in posts if p.competition_id})
        hosted_comps = (
            {
                hc.id: hc
                for hc in self.session.scalars(
                    select(UserHostedCompetition).where(UserHostedCompetition.id.in_(comp_ids))
                ).all()
            }
            if comp_ids
            else {}
        )
        comp_participant_counts: dict[str, int] = {}
        if hosted_comps:
            comp_participant_counts = {
                str(k): int(v)
                for k, v in self.session.execute(
                    select(
                        UserHostedCompetitionParticipant.competition_id, func.count(UserHostedCompetitionParticipant.id)
                    )
                    .where(UserHostedCompetitionParticipant.competition_id.in_(list(hosted_comps)))
                    .group_by(UserHostedCompetitionParticipant.competition_id)
                ).all()
            }

        counts, mine = _reaction_summary(
            self.session,
            entity_type="post",
            entity_ids=[p.id for p in posts],
            actor_id=actor.id if actor else None,
        )
        bookmarked_ids: set[str] = set()
        if actor is not None:
            bookmarked_ids = set(
                self.session.scalars(
                    select(CommunityBookmark.post_id).where(
                        CommunityBookmark.user_id == actor.id,
                        CommunityBookmark.post_id.in_([p.id for p in posts]),
                    )
                ).all()
            )

        poll_post_ids = [p.id for p in posts if p.post_type == "poll"]
        poll_counts: dict[str, dict[str, int]] = {}
        viewer_poll_votes: dict[str, str] = {}
        if poll_post_ids:
            votes = list(
                self.session.scalars(
                    select(CommunityPollVote).where(CommunityPollVote.post_id.in_(poll_post_ids))
                ).all()
            )
            for v in votes:
                b = poll_counts.setdefault(v.post_id, {})
                b[v.option_id] = b.get(v.option_id, 0) + 1
                if actor and v.user_id == actor.id:
                    viewer_poll_votes[v.post_id] = v.option_id

        result: list[dict[str, Any]] = []
        for p in posts:
            club = clubs.get(p.club_id or "")
            player = players.get(p.player_id or "")
            if player and (player.real_player_tier or "").lower() == "archived_duplicate":
                player = None
            comp = hosted_comps.get(p.competition_id or "")
            poll_out = None
            if p.post_type == "poll":
                pc = poll_counts.get(p.id, {})
                total_votes = sum(pc.values())
                poll_out = {
                    "total_votes": total_votes,
                    "viewer_option_id": viewer_poll_votes.get(p.id),
                    "options": [
                        {
                            "id": opt.get("id"),
                            "label": opt.get("label"),
                            "votes": pc.get(str(opt.get("id")), 0),
                        }
                        for opt in (p.poll_options_json or [])
                        if isinstance(opt, dict)
                    ],
                }
            result.append(
                {
                    "id": p.id,
                    "author_user_id": p.author_user_id,
                    "author": _user_summary(authors.get(p.author_user_id)),
                    "post_type": p.post_type,
                    "title": p.title,
                    "body": p.body,
                    "channel_slug": p.channel_slug,
                    "tags": list(p.tags_json or []),
                    "mentions": list(p.mentions_json or []),
                    "visibility": p.visibility,
                    "is_pinned": bool(p.is_pinned),
                    "is_locked": bool(p.is_locked),
                    "is_official": bool(p.is_official),
                    "comment_count": int(p.comment_count or 0),
                    "reaction_count": int(p.reaction_count or 0),
                    "bookmark_count": int(p.bookmark_count or 0),
                    "reactions": counts.get(p.id, {}),
                    "viewer_reactions": mine.get(p.id, []),
                    "viewer_bookmarked": p.id in bookmarked_ids,
                    "poll": poll_out,
                    "club_card": (
                        {
                            "id": club.id,
                            "club_name": club.club_name,
                            "slug": club.slug,
                            "crest_asset_ref": club.crest_asset_ref,
                            "primary_color": club.primary_color,
                            "city_name": club.city_name,
                            "country_code": club.country_code,
                            "follower_count": follower_counts.get(club.id, 0),
                            "viewer_follows": club.id in viewer_follows,
                        }
                        if club
                        else None
                    ),
                    "player_card": (
                        {
                            "id": player.id,
                            "name": player.canonical_display_name or player.full_name,
                            "position": player.normalized_position or player.position,
                            "gsi": player.governed_gsi,
                            "tier": player.real_player_tier,
                        }
                        if player
                        else None
                    ),
                    "competition_card": (
                        {
                            "id": comp.id,
                            "title": comp.title,
                            "slug": comp.slug,
                            "visibility": comp.visibility,
                            "status": comp.status.value if hasattr(comp.status, "value") else str(comp.status),
                            "current_participants": comp_participant_counts.get(comp.id, 0),
                            "max_participants": int(comp.max_participants),
                            "entry_fee_fancoin": 0,
                            "reward_pool_fancoin": float(comp.reward_pool_fancoin or 0),
                            "is_gtex_official": False,
                        }
                        if comp
                        else None
                    ),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
            )
        return result

    # ---------------- COMPETITION DISCOVERY & APPLICATIONS ----------------

    def list_discoverable_competitions(
        self,
        *,
        actor: User | None,
        source_filter: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        s_filter = (source_filter or "all").strip().lower()
        clean_search = (search or "").strip().lower()

        if s_filter in {"all", "user_hosted"}:
            hosted = list(
                self.session.scalars(
                    select(UserHostedCompetition).order_by(UserHostedCompetition.created_at.desc()).limit(limit)
                ).all()
            )
            comp_ids = [c.id for c in hosted]
            host_ids = list({c.host_user_id for c in hosted})
            hosts = (
                {u.id: u for u in self.session.scalars(select(User).where(User.id.in_(host_ids))).all()}
                if host_ids
                else {}
            )
            p_counts = (
                dict(
                    self.session.execute(
                        select(
                            UserHostedCompetitionParticipant.competition_id,
                            func.count(UserHostedCompetitionParticipant.id),
                        )
                        .where(UserHostedCompetitionParticipant.competition_id.in_(comp_ids))
                        .group_by(UserHostedCompetitionParticipant.competition_id)
                    ).all()
                )
                if comp_ids
                else {}
            )
            app_counts = (
                dict(
                    self.session.execute(
                        select(
                            CommunityCompetitionApplication.competition_id,
                            func.count(CommunityCompetitionApplication.id),
                        )
                        .where(
                            CommunityCompetitionApplication.competition_id.in_(comp_ids),
                            CommunityCompetitionApplication.status == "pending",
                        )
                        .group_by(CommunityCompetitionApplication.competition_id)
                    ).all()
                )
                if comp_ids
                else {}
            )

            joined_ids: set[str] = set()
            viewer_apps: dict[str, CommunityCompetitionApplication] = {}
            if actor is not None and comp_ids:
                joined_ids = set(
                    self.session.scalars(
                        select(UserHostedCompetitionParticipant.competition_id).where(
                            UserHostedCompetitionParticipant.competition_id.in_(comp_ids),
                            UserHostedCompetitionParticipant.user_id == actor.id,
                        )
                    ).all()
                )
                for app in self.session.scalars(
                    select(CommunityCompetitionApplication).where(
                        CommunityCompetitionApplication.competition_id.in_(comp_ids),
                        CommunityCompetitionApplication.applicant_user_id == actor.id,
                    )
                ).all():
                    viewer_apps[app.competition_id] = app

            for comp in hosted:
                if clean_search and clean_search not in f"{comp.title} {comp.description}".lower():
                    continue
                comp_status = comp.status.value if hasattr(comp.status, "value") else str(comp.status)
                if status_filter and status_filter != "all" and comp_status != status_filter:
                    continue
                cur_count = int(p_counts.get(comp.id, 0))
                my_app = viewer_apps.get(comp.id)
                items.append(
                    {
                        "id": comp.id,
                        "source_kind": "user_hosted",
                        "is_gtex_official": False,
                        "title": comp.title,
                        "slug": comp.slug,
                        "description": comp.description,
                        "visibility": comp.visibility,
                        "status": comp_status,
                        "entry_fee_fancoin": 0,
                        "reward_pool_fancoin": float(comp.reward_pool_fancoin or 0),
                        "current_participants": cur_count,
                        "max_participants": int(comp.max_participants),
                        "slots_remaining": max(0, int(comp.max_participants) - cur_count),
                        "pending_applications_count": int(app_counts.get(comp.id, 0)),
                        "organizer": _user_summary(hosts.get(comp.host_user_id)),
                        "is_organizer": bool(actor and comp.host_user_id == actor.id),
                        "viewer_joined": comp.id in joined_ids,
                        "viewer_application_status": my_app.status if my_app else None,
                        "viewer_application_id": my_app.id if my_app else None,
                        "created_at": comp.created_at.isoformat() if comp.created_at else None,
                    }
                )

        if s_filter in {"all", "gtex_official"}:
            from app.owner_console.models import OwnerCompetition, OwnerCompetitionEntry

            official = list(
                self.session.scalars(
                    select(OwnerCompetition)
                    .where(OwnerCompetition.host_type == "gtex")
                    .order_by(OwnerCompetition.created_at.desc())
                    .limit(20)
                ).all()
            )
            entry_counts = (
                dict(
                    self.session.execute(
                        select(OwnerCompetitionEntry.competition_id, func.count(OwnerCompetitionEntry.id))
                        .where(OwnerCompetitionEntry.competition_id.in_([o.id for o in official]))
                        .group_by(OwnerCompetitionEntry.competition_id)
                    ).all()
                )
                if official
                else {}
            )
            for oc in official:
                if clean_search and clean_search not in f"{oc.name} {oc.format}".lower():
                    continue
                if status_filter and status_filter != "all" and oc.status != status_filter:
                    continue
                cur = int(entry_counts.get(oc.id, 0))
                items.append(
                    {
                        "id": oc.id,
                        "source_kind": "gtex_official",
                        "is_gtex_official": True,
                        "title": oc.name,
                        "slug": oc.id,
                        "description": oc.description or f"Official GTEX {oc.format} competition ({oc.tier})",
                        "visibility": "public",
                        "status": oc.status,
                        "entry_fee_fancoin": 0,
                        "reward_pool_fancoin": float(oc.sponsored_pool or 0),
                        "current_participants": cur,
                        "max_participants": int(oc.max_clubs or 8),
                        "slots_remaining": max(0, int(oc.max_clubs or 8) - cur),
                        "pending_applications_count": 0,
                        "organizer": {
                            "id": "gtex-system",
                            "username": "gtex",
                            "display_name": "GTEX Official",
                            "is_admin": True,
                        },
                        "is_organizer": False,
                        "viewer_joined": False,
                        "viewer_application_status": None,
                        "viewer_application_id": None,
                        "created_at": oc.created_at.isoformat() if oc.created_at else None,
                    }
                )
        return items[:limit]

    def apply_to_hosted_competition(
        self,
        *,
        competition_id: str,
        actor: User,
        club_id: str | None = None,
        note: str | None = None,
        passcode: str | None = None,
    ) -> dict[str, Any]:
        comp = self.session.get(UserHostedCompetition, competition_id)
        if comp is None:
            raise CommunitySocialError("Hosted competition not found.", status_code=404)
        if comp.status not in {HostedCompetitionStatus.OPEN, HostedCompetitionStatus.DRAFT}:
            raise CommunitySocialError("Competition is no longer accepting applications.")

        blocked_ids, _ = _blocked_and_muted_ids(self.session, actor)
        if comp.host_user_id in blocked_ids:
            raise CommunitySocialError("Unable to apply to this competition.", status_code=403)

        already = self.session.scalar(
            select(UserHostedCompetitionParticipant).where(
                UserHostedCompetitionParticipant.competition_id == comp.id,
                UserHostedCompetitionParticipant.user_id == actor.id,
            )
        )
        if already is not None:
            raise CommunitySocialError("You are already entered in this competition.")

        if club_id:
            club = self.session.get(ClubProfile, club_id)
            if club is None or club.owner_user_id != actor.id:
                raise CommunitySocialError("You can only apply with a club you own.", status_code=403)

        # Public open competitions without application requirement can join directly if requested via open join,
        # OR submit an application for organizer review on invite_only / private / application flows.
        existing_app = self.session.scalar(
            select(CommunityCompetitionApplication).where(
                CommunityCompetitionApplication.competition_id == comp.id,
                CommunityCompetitionApplication.applicant_user_id == actor.id,
            )
        )
        if existing_app is not None and existing_app.status == "pending":
            raise CommunitySocialError("You already have a pending application for this competition.")

        if comp.visibility == "public" and passcode is None and not (note or "").strip():
            # Instant canonical join when slots available
            try:
                comp, participant = HostedCompetitionService(self.session).join_competition(
                    user=actor, competition_id=comp.id
                )
                return {
                    "mode": "joined",
                    "competition_id": comp.id,
                    "participant_id": participant.id,
                    "status": "accepted",
                }
            except HostedCompetitionError as exc:
                raise CommunitySocialError(str(exc)) from exc

        if existing_app is not None:
            existing_app.club_id = club_id
            existing_app.note = (note or "").strip()[:500] or None
            existing_app.status = "pending"
            existing_app.reviewed_by_user_id = None
            existing_app.reviewed_at = None
            existing_app.review_note = None
            app = existing_app
        else:
            app = CommunityCompetitionApplication(
                competition_id=comp.id,
                applicant_user_id=actor.id,
                club_id=club_id,
                note=(note or "").strip()[:500] or None,
                status="pending",
            )
            self.session.add(app)
        self.session.flush()

        try:
            from app.notifications.service import NotificationEventMatrixService

            NotificationEventMatrixService(self.session).publish_event(
                event_key="competition_application_received",
                target_user_ids=[comp.host_user_id],
                resource_id=app.id,
                message=f"{actor.display_name or actor.username} applied to join {comp.title}.",
                metadata_json={
                    "competition_id": comp.id,
                    "deep_link_route": f"/app/community?tab=competitions&competition={comp.id}",
                },
            )
        except Exception:
            pass

        return {
            "mode": "application",
            "id": app.id,
            "competition_id": comp.id,
            "applicant_user_id": actor.id,
            "club_id": club_id,
            "note": app.note,
            "status": app.status,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        }

    def list_competition_applications(self, *, competition_id: str, actor: User) -> list[dict[str, Any]]:
        comp = self.session.get(UserHostedCompetition, competition_id)
        if comp is None:
            raise CommunitySocialError("Hosted competition not found.", status_code=404)
        if comp.host_user_id != actor.id and not _is_admin(actor):
            raise CommunitySocialError("Only the competition organizer can review applications.", status_code=403)
        apps = list(
            self.session.scalars(
                select(CommunityCompetitionApplication)
                .where(CommunityCompetitionApplication.competition_id == comp.id)
                .order_by(CommunityCompetitionApplication.created_at.desc())
            ).all()
        )
        u_ids = list({a.applicant_user_id for a in apps})
        users = {u.id: u for u in self.session.scalars(select(User).where(User.id.in_(u_ids))).all()} if u_ids else {}
        c_ids = [a.club_id for a in apps if a.club_id]
        clubs = (
            {c.id: c for c in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(c_ids))).all()}
            if c_ids
            else {}
        )
        return [
            {
                "id": a.id,
                "competition_id": a.competition_id,
                "applicant_user_id": a.applicant_user_id,
                "applicant": _user_summary(users.get(a.applicant_user_id)),
                "club_id": a.club_id,
                "club_name": clubs[a.club_id].club_name if a.club_id and a.club_id in clubs else None,
                "note": a.note,
                "status": a.status,
                "review_note": a.review_note,
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in apps
        ]

    def review_competition_application(
        self,
        *,
        application_id: str,
        actor: User,
        decision: str,
        review_note: str | None = None,
    ) -> dict[str, Any]:
        app = self.session.get(CommunityCompetitionApplication, application_id)
        if app is None:
            raise CommunitySocialError("Competition application not found.", status_code=404)
        comp = self.session.get(UserHostedCompetition, app.competition_id)
        if comp is None:
            raise CommunitySocialError("Hosted competition not found.", status_code=404)
        if comp.host_user_id != actor.id and not _is_admin(actor):
            raise CommunitySocialError("Only the competition organizer can review applications.", status_code=403)
        if app.status != "pending":
            raise CommunitySocialError("Application has already been reviewed.")

        clean_dec = decision.strip().lower()
        if clean_dec not in {"accept", "reject"}:
            raise CommunitySocialError("Decision must be 'accept' or 'reject'.")

        now = datetime.now(timezone.utc)
        if clean_dec == "accept":
            applicant = self.session.get(User, app.applicant_user_id)
            if applicant is None:
                raise CommunitySocialError("Applicant user no longer exists.", status_code=404)
            try:
                HostedCompetitionService(self.session).join_competition(
                    user=applicant,
                    competition_id=comp.id,
                    invite_required_bypass=True,
                )
            except HostedCompetitionError as exc:
                raise CommunitySocialError(str(exc)) from exc
            app.status = "accepted"
        else:
            app.status = "rejected"

        app.reviewed_by_user_id = actor.id
        app.reviewed_at = now
        app.review_note = (review_note or "").strip()[:240] or None
        self.session.flush()

        try:
            from app.notifications.service import NotificationEventMatrixService

            NotificationEventMatrixService(self.session).publish_event(
                event_key="competition_application_reviewed",
                target_user_ids=[app.applicant_user_id],
                resource_id=app.id,
                message=f"Your application for {comp.title} was {app.status}.",
                metadata_json={
                    "competition_id": comp.id,
                    "status": app.status,
                    "deep_link_route": f"/app/community?tab=competitions&competition={comp.id}",
                },
            )
        except Exception:
            pass

        return {
            "id": app.id,
            "competition_id": app.competition_id,
            "status": app.status,
            "review_note": app.review_note,
            "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None,
        }

    # ---------------- PEOPLE, CLUBS & PUBLIC PLAYER DISCOVERY ----------------

    def search_users_directory(
        self, *, actor: User | None, query: str | None = None, limit: int = 30
    ) -> list[dict[str, Any]]:
        blocked_ids, muted_ids = _blocked_and_muted_ids(self.session, actor)
        q = select(User).where(User.is_active.is_(True))
        if actor is not None:
            q = q.where(User.id != actor.id)
        if blocked_ids:
            q = q.where(~User.id.in_(blocked_ids))
        clean_q = (query or "").strip()
        if clean_q:
            term = f"%{clean_q}%"
            q = q.where(
                or_(
                    User.username.ilike(term),
                    User.display_name.ilike(term),
                    User.favourite_club.ilike(term),
                )
            )
        users = list(self.session.scalars(q.order_by(User.created_at.desc()).limit(limit)).all())
        following_ids: set[str] = set()
        if actor is not None and users:
            following_ids = set(
                self.session.scalars(
                    select(UserFollow.target_user_id).where(
                        UserFollow.follower_user_id == actor.id,
                        UserFollow.target_user_id.in_([u.id for u in users]),
                    )
                ).all()
            )
        u_ids = [u.id for u in users]
        owned_clubs: dict[str, dict[str, str]] = {}
        if u_ids:
            for c in self.session.scalars(
                select(ClubProfile).where(
                    ClubProfile.owner_user_id.in_(u_ids),
                    ClubProfile.lifecycle_status == ClubLifecycleStatus.ACTIVE,
                )
            ).all():
                owned_clubs.setdefault(c.owner_user_id, {"id": c.id, "club_name": c.club_name, "slug": c.slug})
        return [
            {
                **_user_summary(u),
                "nationality": u.nationality,
                "preferred_position": u.preferred_position,
                "viewer_follows": u.id in following_ids,
                "viewer_muted": u.id in muted_ids,
                "club": owned_clubs.get(u.id),
            }
            for u in users
        ]

    def list_clubs_showcase(
        self, *, actor: User | None, query: str | None = None, limit: int = 30
    ) -> list[dict[str, Any]]:
        q = select(ClubProfile).where(
            ClubProfile.visibility == "public",
            ClubProfile.lifecycle_status == ClubLifecycleStatus.ACTIVE,
        )
        clean_q = (query or "").strip()
        if clean_q:
            term = f"%{clean_q}%"
            q = q.where(
                or_(
                    ClubProfile.club_name.ilike(term),
                    ClubProfile.city_name.ilike(term),
                    ClubProfile.description.ilike(term),
                )
            )
        clubs = list(self.session.scalars(q.order_by(ClubProfile.created_at.desc()).limit(limit)).all())
        club_ids = [c.id for c in clubs]
        owner_ids = list({c.owner_user_id for c in clubs})
        owners = (
            {u.id: u for u in self.session.scalars(select(User).where(User.id.in_(owner_ids))).all()}
            if owner_ids
            else {}
        )
        followers = (
            {
                str(k): int(v)
                for k, v in self.session.execute(
                    select(SocialFollow.club_id, func.count(SocialFollow.id))
                    .where(SocialFollow.club_id.in_(club_ids))
                    .group_by(SocialFollow.club_id)
                ).all()
                if k
            }
            if club_ids
            else {}
        )
        trophies = (
            {
                str(k): int(v)
                for k, v in self.session.execute(
                    select(ClubTrophy.club_id, func.count(ClubTrophy.id))
                    .where(ClubTrophy.club_id.in_(club_ids))
                    .group_by(ClubTrophy.club_id)
                ).all()
            }
            if club_ids
            else {}
        )
        stadiums = (
            {
                s.club_id: s.name
                for s in self.session.scalars(select(ClubStadium).where(ClubStadium.club_id.in_(club_ids))).all()
            }
            if club_ids
            else {}
        )
        viewer_follows: set[str] = set()
        if actor is not None and club_ids:
            viewer_follows = {
                str(i)
                for i in self.session.scalars(
                    select(SocialFollow.club_id).where(
                        SocialFollow.user_id == actor.id,
                        SocialFollow.club_id.in_(club_ids),
                    )
                ).all()
                if i
            }
        # Deliberately omit private OwnerClubState (treasury, inbox, medical, contracts)
        return [
            {
                "id": c.id,
                "club_name": c.club_name,
                "short_name": c.short_name,
                "slug": c.slug,
                "club_type": c.club_type.value if hasattr(c.club_type, "value") else str(c.club_type),
                "crest_asset_ref": c.crest_asset_ref,
                "primary_color": c.primary_color,
                "secondary_color": c.secondary_color,
                "country_code": c.country_code,
                "city_name": c.city_name,
                "stadium_name": stadiums.get(c.id) or c.home_venue_name,
                "description": c.description,
                "trophy_count": trophies.get(c.id, 0),
                "follower_count": followers.get(c.id, 0),
                "viewer_follows": c.id in viewer_follows,
                "owner": _user_summary(owners.get(c.owner_user_id)),
            }
            for c in clubs
        ]

    def search_public_players_and_regens(
        self, *, query: str | None = None, regens_only: bool = False, limit: int = 30
    ) -> list[dict[str, Any]]:
        q = (
            select(Player, RegenProfile)
            .outerjoin(RegenProfile, RegenProfile.player_id == Player.id)
            .where(
                or_(Player.real_player_tier.is_(None), Player.real_player_tier != "archived_duplicate"),
                Player.is_tradable.is_(True),
            )
        )
        if regens_only:
            q = q.where(RegenProfile.id.is_not(None))
        clean_q = (query or "").strip()
        if clean_q:
            term = f"%{clean_q}%"
            q = q.where(
                or_(
                    Player.full_name.ilike(term),
                    Player.canonical_display_name.ilike(term),
                    Player.normalized_position.ilike(term),
                )
            )
        rows = self.session.execute(
            q.order_by(Player.governed_gsi.desc().nullslast(), Player.created_at.desc()).limit(limit)
        ).all()
        country_ids = list({pl.country_id for pl, _ in rows if pl.country_id})
        countries = (
            {c.id: c.name for c in self.session.scalars(select(Country).where(Country.id.in_(country_ids))).all()}
            if country_ids
            else {}
        )
        return [
            {
                "id": pl.id,
                "name": pl.canonical_display_name or pl.full_name,
                "position": pl.normalized_position or pl.position,
                "gsi": pl.governed_gsi if pl.governed_gsi is not None else (reg.current_gsi if reg else None),
                "tier": pl.real_player_tier,
                "is_regen": reg is not None,
                "regen_id": reg.regen_id if reg else None,
                "country": countries.get(pl.country_id or ""),
                "real_world_club_name": pl.real_world_club_name,
            }
            for pl, reg in rows
        ]

    # ---------------- ENHANCED PRIVATE MESSAGES & SAFETY ----------------

    def list_pm_messages_paginated(
        self,
        *,
        thread_id: str,
        actor: User,
        before_seq: int | None = None,
        after_seq: int | None = None,
        limit: int = 40,
    ) -> dict[str, Any]:
        thread = self.session.get(PrivateMessageThread, thread_id)
        if thread is None:
            raise CommunitySocialError("Private message thread not found.", status_code=404)
        participant = self.session.scalar(
            select(PrivateMessageParticipant).where(
                PrivateMessageParticipant.thread_id == thread_id,
                PrivateMessageParticipant.user_id == actor.id,
            )
        )
        if participant is None:
            raise CommunitySocialError("You are not a participant in this thread.", status_code=403)
        if participant.left_at is not None:
            raise CommunitySocialError("You have left this conversation.", status_code=403)

        q = select(PrivateMessage).where(
            PrivateMessage.thread_id == thread_id,
            PrivateMessage.visibility != MessageVisibility.HIDDEN,
        )
        if after_seq is not None:
            q = q.where(PrivateMessage.seq > after_seq).order_by(PrivateMessage.seq.asc())
            rows = list(self.session.scalars(q.limit(limit)).all())
            has_more = False
        else:
            if before_seq is not None:
                q = q.where(PrivateMessage.seq < before_seq)
            rows_desc = list(
                self.session.scalars(
                    q.order_by(PrivateMessage.seq.desc(), PrivateMessage.created_at.desc()).limit(limit + 1)
                ).all()
            )
            has_more = len(rows_desc) > limit
            rows = list(reversed(rows_desc[:limit]))

        from app.community_engine.service import CommunityEngineService

        unread_state = CommunityEngineService(self.session).calculate_thread_unread_state(
            thread=thread,
            actor_id=actor.id,
        )

        sender_ids = list({m.sender_user_id for m in rows})
        senders = (
            {u.id: u for u in self.session.scalars(select(User).where(User.id.in_(sender_ids))).all()}
            if sender_ids
            else {}
        )
        return {
            "thread_id": thread.id,
            "subject": thread.subject,
            "is_group": bool(getattr(thread, "is_group", False)),
            "latest_seq": int(getattr(thread, "last_message_seq", 0) or 0),
            "unread_count": int(unread_state["unread_count"]),
            "last_read_seq": int(unread_state["last_read_seq"]),
            "last_read_at": (
                unread_state["last_read_at"].isoformat() if unread_state["last_read_at"] is not None else None
            ),
            "has_more": has_more,
            "next_before_seq": int(rows[0].seq) if has_more and rows and int(rows[0].seq or 0) > 0 else None,
            "messages": [
                {
                    "id": m.id,
                    "thread_id": m.thread_id,
                    "seq": int(getattr(m, "seq", 0) or 0),
                    "sender_user_id": m.sender_user_id,
                    "sender": _user_summary(senders.get(m.sender_user_id)),
                    "body": m.body,
                    "reply_to_message_id": getattr(m, "reply_to_message_id", None),
                    "mentions": list(getattr(m, "mentions_json", []) or []),
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in rows
            ],
        }

    def leave_pm_thread(self, *, thread_id: str, actor: User) -> dict[str, Any]:
        thread = self.session.get(PrivateMessageThread, thread_id)
        if thread is None:
            raise CommunitySocialError("Private message thread not found.", status_code=404)
        part = self.session.scalar(
            select(PrivateMessageParticipant).where(
                PrivateMessageParticipant.thread_id == thread_id,
                PrivateMessageParticipant.user_id == actor.id,
            )
        )
        if part is None:
            raise CommunitySocialError("You are not a participant in this thread.", status_code=403)
        if part.left_at is not None:
            raise CommunitySocialError("You have left this conversation.", status_code=403)
        if not bool(getattr(thread, "is_group", False)):
            raise CommunitySocialError("You can only leave group conversations.")
        part.left_at = datetime.now(timezone.utc)
        self.session.flush()
        return {"thread_id": thread_id, "left": True}

    def block_user(self, *, actor: User, target_user_id: str, reason: str | None = None) -> dict[str, Any]:
        """Delegate blocking to CommunityEngineService so DM threads and discovery share one rule."""
        from app.community_engine.service import CommunityEngineError, CommunityEngineService

        try:
            block = CommunityEngineService(self.session).block_user(
                actor=actor,
                target_user_id=target_user_id,
                reason=reason,
            )
        except CommunityEngineError as exc:
            status_code = 404 if "not found" in str(exc).lower() else 400
            raise CommunitySocialError(str(exc), status_code=status_code) from exc
        return {
            "id": block.id,
            "blocked_user_id": block.blocked_user_id,
            "blocked": True,
            "status": "blocked",
        }

    def unblock_user(self, *, actor: User, target_user_id: str) -> dict[str, Any]:
        block = self.session.scalar(
            select(CommunityUserBlock).where(
                CommunityUserBlock.blocker_user_id == actor.id,
                CommunityUserBlock.blocked_user_id == target_user_id,
            )
        )
        if block is not None:
            self.session.delete(block)
            self.session.flush()
        return {"blocked_user_id": target_user_id, "blocked": False}

    def toggle_mute_user(
        self, *, actor: User, target_user_id: str, muted: bool = True, reason: str | None = None
    ) -> dict[str, Any]:
        if target_user_id == actor.id:
            raise CommunitySocialError("You cannot mute yourself.")
        existing = self.session.scalar(
            select(CommunityUserMute).where(
                CommunityUserMute.user_id == actor.id,
                CommunityUserMute.muted_user_id == target_user_id,
            )
        )
        if muted and existing is None:
            self.session.add(CommunityUserMute(user_id=actor.id, muted_user_id=target_user_id, reason=reason))
        elif not muted and existing is not None:
            self.session.delete(existing)
        self.session.flush()
        return {"muted_user_id": target_user_id, "muted": muted}

    def create_moderation_report(
        self,
        *,
        actor: User,
        target_type: str,
        target_id: str,
        reason_code: str,
        description: str,
        subject_user_id: str | None = None,
    ) -> dict[str, Any]:
        existing = self.session.scalar(
            select(ModerationReport).where(
                ModerationReport.target_type == target_type,
                ModerationReport.target_id == target_id,
                ModerationReport.reporter_user_id == actor.id,
                ModerationReport.status.in_([ModerationReportStatus.OPEN, ModerationReportStatus.IN_REVIEW]),
            )
        )
        if existing is not None:
            raise CommunitySocialError("You already submitted an open report for this item.")
        count = (
            int(
                self.session.scalar(
                    select(func.count(ModerationReport.id)).where(
                        ModerationReport.target_type == target_type,
                        ModerationReport.target_id == target_id,
                    )
                )
                or 0
            )
            + 1
        )
        report = ModerationReport(
            reporter_user_id=actor.id,
            subject_user_id=subject_user_id,
            target_type=target_type.strip().lower()[:32],
            target_id=target_id.strip()[:64],
            reason_code=reason_code.strip().lower()[:48] or "community_guideline",
            description=description.strip() or "Reported via GTEX Community.",
            priority=ModerationPriority.HIGH if count >= 3 else ModerationPriority.NORMAL,
            report_count_for_target=count,
        )
        self.session.add(report)
        self.session.flush()
        return {
            "id": report.id,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "status": report.status.value,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }

    def resolve_community_moderation(
        self,
        *,
        admin_user: User,
        report_id: str | None,
        target_type: str,
        target_id: str,
        action: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        if not _is_admin(admin_user):
            raise CommunitySocialError("Admin privileges required.", status_code=403)
        clean_action = action.strip().lower()
        t_type = target_type.strip().lower()

        if t_type == "post":
            post = self.session.get(CommunityPost, target_id)
            if post is None:
                raise CommunitySocialError("Post not found.", status_code=404)
            if clean_action == "hide":
                post.visibility = "hidden"
            elif clean_action == "restore":
                post.visibility = "public"
            elif clean_action == "lock":
                post.is_locked = True
            elif clean_action == "unlock":
                post.is_locked = False
        elif t_type == "channel_message":
            msg = self.session.get(CommunityChannelMessage, target_id)
            if msg is None:
                raise CommunitySocialError("Channel message not found.", status_code=404)
            if clean_action == "hide":
                msg.visibility = "hidden"
            elif clean_action == "restore":
                msg.visibility = "public"

        if report_id:
            report = self.session.get(ModerationReport, report_id)
            if report is not None:
                report.status = (
                    ModerationReportStatus.DISMISSED if clean_action == "dismiss" else ModerationReportStatus.ACTIONED
                )
                report.resolution_action = (
                    ModerationResolutionAction.CONTENT_REMOVED
                    if clean_action == "hide"
                    else ModerationResolutionAction.NONE
                )
                report.resolved_by_user_id = admin_user.id
                report.resolution_note = (note or "").strip() or f"Community action: {clean_action}"
        self.session.flush()
        return {"status": "resolved", "target_type": t_type, "target_id": target_id, "action": clean_action}


__all__ = ["CANONICAL_CHANNELS", "CommunitySocialError", "CommunitySocialService"]
