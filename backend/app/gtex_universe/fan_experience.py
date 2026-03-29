from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.awards.service import AwardsCultureService
from app.gtex_universe.social_warfare import GtexSocialWarfareService
from app.ingestion.models import Club, Player
from app.models.club_social import RivalryProfile
from app.models.fan_experience import FanExperienceTicket, FanProfile, FanReaction
from app.models.gtex_economy import GtexMatch
from app.models.news_article import NewsArticle
from app.models.notification_record import NotificationRecord
from app.models.player_fan_reaction import PlayerFanReaction
from app.models.prestige_rating import PrestigeRating
from app.models.regen_ecosystem import NationalRegenSeed, RegenAwardVote
from app.models.user import User
from app.regen_universe.models import RegenAward
from app.services.regen_ecosystem_service import RegenEcosystemService

AMOUNT_QUANTUM = Decimal("0.0001")
POSITIVE_REACTIONS = {"cheer", "hype"}
DEFAULT_CEREMONY_CAPACITY = 2400
DEFAULT_CEREMONY_VIP_CAPACITY = 180


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _quantize(value: Decimal | str | float | int | None) -> Decimal:
    return Decimal(str(value or "0")).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(slots=True)
class GtexFanExperienceService:
    session: Session

    def get_or_create_profile(self, *, actor: User) -> FanProfile:
        profile = self.session.scalar(select(FanProfile).where(FanProfile.user_id == actor.id))
        if profile is None:
            profile = FanProfile(user_id=actor.id)
            self.session.add(profile)
            self.session.flush()
        self._refresh_profile(profile)
        return profile

    def update_profile(
        self,
        *,
        actor: User,
        favorite_club_id: str | None = None,
        favorite_player_id: str | None = None,
        rival_club_ids: list[str] | None = None,
    ) -> FanProfile:
        profile = self.get_or_create_profile(actor=actor)
        if favorite_club_id is not None:
            club = self.session.get(Club, favorite_club_id)
            profile.favorite_club_id = favorite_club_id
            profile.favorite_club_name = club.name if club is not None else favorite_club_id
            if rival_club_ids is None:
                profile.rival_club_ids_json = self._default_rivals_for_club(favorite_club_id)
        if favorite_player_id is not None:
            player = self.session.get(Player, favorite_player_id)
            profile.favorite_player_id = favorite_player_id
            profile.favorite_player_name = player.full_name if player is not None else favorite_player_id
        if rival_club_ids is not None:
            profile.rival_club_ids_json = list(dict.fromkeys(item for item in rival_club_ids if item))
        profile.loyalty_score = round(max(float(profile.loyalty_score or 0.0), 6.0), 3)
        self._refresh_profile(profile)
        self.session.flush()
        return profile

    def profile_payload(self, profile: FanProfile) -> dict[str, Any]:
        social = GtexSocialWarfareService(self.session)
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "favorite_club": {"id": profile.favorite_club_id, "name": profile.favorite_club_name},
            "favorite_player": {"id": profile.favorite_player_id, "name": profile.favorite_player_name},
            "fan_tier": profile.fan_tier,
            "loyalty_score": round(float(profile.loyalty_score or 0.0), 3),
            "reputation_score": round(float(profile.reputation_score or 0.0), 3),
            "attendance_count": int(profile.attendance_count or 0),
            "attendance_history": list(profile.attendance_history_json or []),
            "rival_club_ids": list(profile.rival_club_ids_json or []),
            "badges": list(profile.badges_json or []),
            "metadata": dict(profile.metadata_json or {}),
            "current_tribe": social.tribe_payload(social.current_user_tribe(user_id=profile.user_id)),
        }

    def ticket_payload(self, ticket: FanExperienceTicket) -> dict[str, Any]:
        return {
            "id": ticket.id,
            "event_type": ticket.event_type,
            "event_key": ticket.event_key,
            "match_id": ticket.match_id,
            "ticket_tier": ticket.ticket_tier,
            "access_level": ticket.access_level,
            "status": ticket.status,
            "seat_label": ticket.seat_label,
            "price_coin": _quantize(ticket.price_coin),
            "discount_bps": int(ticket.discount_bps),
            "priority_stream": bool(ticket.priority_stream),
            "exclusive_commentary_lines": list(ticket.exclusive_commentary_lines_json or []),
            "loyalty_bonus": round(float(ticket.loyalty_bonus or 0.0), 3),
            "reputation_bonus": round(float(ticket.reputation_bonus or 0.0), 3),
            "metadata": dict(ticket.metadata_json or {}),
        }

    def reaction_payload(self, reaction: FanReaction) -> dict[str, Any]:
        return {
            "id": reaction.id,
            "match_id": reaction.match_id,
            "event_key": reaction.event_key,
            "channel": reaction.channel,
            "reaction_type": reaction.reaction_type,
            "supported_side": reaction.supported_side,
            "weight": round(float(reaction.weight or 0.0), 4),
            "tier_at_reaction": reaction.tier_at_reaction,
            "metadata": dict(reaction.metadata_json or {}),
        }

    def match_experience(self, *, match: GtexMatch, current_user: User | None = None) -> dict[str, Any]:
        social = GtexSocialWarfareService(self.session)
        offer = self._match_offer(match=match, current_user=current_user)
        reaction_summary = self._reaction_summary(event_key=offer["event_key"], match_id=match.id)
        atmosphere = self._atmosphere_summary(match=match, offer=offer, reaction_summary=reaction_summary)
        social_warfare = social.match_social_warfare(match=match, current_user=current_user, offer=offer)
        return {**offer, "reaction_summary": reaction_summary, "atmosphere": atmosphere, "social_warfare": social_warfare}

    def purchase_match_ticket(self, *, actor: User, match: GtexMatch, ticket_tier: str) -> FanExperienceTicket:
        profile = self.get_or_create_profile(actor=actor)
        normalized_tier = (ticket_tier or "matchday").strip().lower()
        if normalized_tier not in {"matchday", "vip"}:
            raise ValueError("Ticket tier must be matchday or vip.")
        event_key = self._match_event_key(match.id)
        existing = self.session.scalar(
            select(FanExperienceTicket).where(
                FanExperienceTicket.user_id == actor.id,
                FanExperienceTicket.event_key == event_key,
                FanExperienceTicket.ticket_tier == normalized_tier,
            )
        )
        if existing is not None:
            return existing
        offer = self._match_offer(match=match, current_user=actor)
        sold_before = int(offer["tickets_sold"])
        if sold_before >= int(offer["capacity"]):
            raise ValueError("Match tickets are sold out.")
        if normalized_tier == "vip" and int(offer["vip_tickets_sold"]) >= int(offer["vip_capacity"]):
            raise ValueError("VIP tickets are sold out.")
        base_price = _quantize(offer["vip_ticket_price_coin"] if normalized_tier == "vip" else offer["ticket_price_coin"])
        discount_bps = int(offer["discount_bps"])
        final_price = _quantize(base_price * (Decimal("1.0000") - (Decimal(discount_bps) / Decimal("10000"))))
        ticket = FanExperienceTicket(
            user_id=actor.id,
            fan_profile_id=profile.id,
            event_type="match",
            event_key=event_key,
            match_id=match.id,
            ticket_tier=normalized_tier,
            access_level="priority_stream",
            status="purchased",
            seat_label=f"{'VIP' if normalized_tier == 'vip' else 'General'}-{sold_before + 1}",
            price_coin=final_price,
            discount_bps=discount_bps,
            priority_stream=True,
            exclusive_commentary_lines_json=list(offer["exclusive_commentary_lines"]),
            loyalty_bonus=10.0 if normalized_tier == "vip" else 6.0,
            reputation_bonus=18.0 if offer["is_final"] else 6.0,
            metadata_json={
                "event_title": offer["event_title"],
                "dao_priority": offer["current_user"]["dao_priority"] if offer["current_user"] is not None else False,
                "ticket_release_phase": offer["ticket_access_phase"],
            },
        )
        self.session.add(ticket)
        profile.loyalty_score = round(float(profile.loyalty_score or 0.0) + float(ticket.loyalty_bonus), 3)
        self._refresh_profile(profile)
        self.session.flush()

        refreshed_offer = self._match_offer(match=match, current_user=actor)
        if bool(refreshed_offer["sell_out_hype"]["triggered"]):
            self._trigger_sell_out_hype(match=match, offer=refreshed_offer)
        return ticket

    def submit_match_reaction(
        self,
        *,
        actor: User,
        match: GtexMatch,
        reaction_type: str,
        supported_side: str | None = None,
    ) -> FanReaction:
        profile = self.get_or_create_profile(actor=actor)
        normalized_type = (reaction_type or "").strip().lower()
        if normalized_type not in {"cheer", "boo", "hype"}:
            raise ValueError("Reaction type must be cheer, boo, or hype.")
        resolved_side = (supported_side or "home").strip().lower()
        if resolved_side not in {"home", "away"}:
            resolved_side = "home"
        event_key = self._match_event_key(match.id)
        ticket = self.session.scalar(
            select(FanExperienceTicket).where(
                FanExperienceTicket.user_id == actor.id,
                FanExperienceTicket.event_key == event_key,
            )
        )
        weight = self._tier_weight(profile.fan_tier)
        if normalized_type == "hype":
            weight += 0.35
        elif normalized_type == "boo":
            weight += 0.15
        if ticket is not None:
            weight += 0.2
        reaction = FanReaction(
            user_id=actor.id,
            fan_profile_id=profile.id,
            match_id=match.id,
            event_key=event_key,
            channel="match",
            reaction_type=normalized_type,
            supported_side=resolved_side,
            weight=round(weight, 4),
            tier_at_reaction=profile.fan_tier,
            metadata_json={
                "commentary_tone": "hostile" if normalized_type == "boo" else "fever_pitch" if normalized_type == "hype" else "charged",
                "event_title": self._match_title(match),
            },
        )
        self.session.add(reaction)
        profile.loyalty_score = round(float(profile.loyalty_score or 0.0) + (0.9 * weight), 3)
        if ticket is not None:
            self._mark_attendance(
                profile=profile,
                event_key=event_key,
                event_type="match",
                title=self._match_title(match),
                status="live",
                metadata={"match_id": match.id, "ticket_tier": ticket.ticket_tier},
            )
        self._refresh_profile(profile)
        self.session.flush()
        return reaction

    def finalize_match_rewards(self, *, match: GtexMatch, fan_context: dict[str, Any]) -> dict[str, Any]:
        event_key = self._match_event_key(match.id)
        tickets = list(
            self.session.scalars(
                select(FanExperienceTicket).where(
                    FanExperienceTicket.event_key == event_key,
                    FanExperienceTicket.status == "purchased",
                )
            ).all()
        )
        rewarded_profiles: list[str] = []
        for ticket in tickets:
            if ticket.fan_profile_id is None:
                continue
            profile = self.session.get(FanProfile, ticket.fan_profile_id)
            if profile is None:
                continue
            ticket.status = "attended"
            metadata = dict(ticket.metadata_json or {})
            if not metadata.get("attendance_reward_applied"):
                profile.reputation_score = round(float(profile.reputation_score or 0.0) + float(ticket.reputation_bonus), 3)
                profile.loyalty_score = round(float(profile.loyalty_score or 0.0) + max(float(ticket.loyalty_bonus) * 0.35, 1.0), 3)
                metadata["attendance_reward_applied"] = True
                ticket.metadata_json = metadata
            self._mark_attendance(
                profile=profile,
                event_key=event_key,
                event_type="match",
                title=self._match_title(match),
                status="attended",
                metadata={"match_id": match.id, "ticket_tier": ticket.ticket_tier, "result": fan_context.get("winner_side")},
            )
            self._upsert_prestige_rating(profile)
            self._refresh_profile(profile)
            rewarded_profiles.append(profile.id)
        if fan_context.get("sell_out_triggered"):
            self._ensure_news_article(
                article_type="sell_out_hype",
                title=f"{self._match_title(match)} sells out",
                related_match_id=match.id,
                body=(
                    f"{self._match_title(match)} crossed the 90 percent attendance threshold and triggered the full hype stack: "
                    "price surge, homepage promotion, and the notification blast."
                ),
                tags=["tickets", "sell_out", "hype"],
                metadata={"match_id": match.id, "fan_context": dict(fan_context)},
            )
        social_warfare = GtexSocialWarfareService(self.session).finalize_match_social_warfare(
            match=match,
            fan_context=fan_context,
        )
        self.session.flush()
        return {
            "rewarded_fan_profiles": rewarded_profiles,
            "attendance_rewards_applied": len(rewarded_profiles),
            "social_warfare": social_warfare,
        }

    def purchase_ceremony_ticket(self, *, actor: User, season_id: str, ticket_tier: str) -> FanExperienceTicket:
        ceremony = self.ceremony_experience(season_id=season_id, current_user=actor)
        normalized_tier = (ticket_tier or "general").strip().lower()
        if normalized_tier not in {"general", "vip"}:
            raise ValueError("Ceremony tickets must be general or vip.")
        event_key = str(ceremony["season_event_key"])
        existing = self.session.scalar(
            select(FanExperienceTicket).where(
                FanExperienceTicket.user_id == actor.id,
                FanExperienceTicket.event_key == event_key,
                FanExperienceTicket.ticket_tier == normalized_tier,
            )
        )
        if existing is not None:
            return existing
        profile = self.get_or_create_profile(actor=actor)
        sold_total = int(ceremony["tickets_sold"])
        vip_sold = int(ceremony["vip_tickets_sold"])
        general_sold = max(0, sold_total - vip_sold)
        general_capacity = int(ceremony["general_seat_capacity"])
        vip_capacity = int(ceremony["vip_seat_capacity"])
        if sold_total >= (general_capacity + vip_capacity):
            raise ValueError("Ceremony tickets are sold out.")
        if normalized_tier == "vip" and vip_sold >= vip_capacity:
            raise ValueError("Ceremony VIP tickets are sold out.")
        if normalized_tier == "general" and general_sold >= general_capacity:
            raise ValueError("Ceremony general tickets are sold out.")
        base_price = _quantize(ceremony["vip_ticket_price_coin"] if normalized_tier == "vip" else ceremony["ticket_price_coin"])
        discount_bps = int(ceremony["discount_bps"])
        final_price = _quantize(base_price * (Decimal("1.0000") - (Decimal(discount_bps) / Decimal("10000"))))
        ticket = FanExperienceTicket(
            user_id=actor.id,
            fan_profile_id=profile.id,
            event_type="ceremony",
            event_key=event_key,
            match_id=None,
            ticket_tier=normalized_tier,
            access_level="tv_mode_only",
            status="purchased",
            seat_label=(
                f"VIP-{vip_sold + 1}"
                if normalized_tier == "vip"
                else f"General-{general_sold + 1}"
            ),
            price_coin=final_price,
            discount_bps=discount_bps,
            priority_stream=True,
            exclusive_commentary_lines_json=list(ceremony["exclusive_commentary_lines"]),
            loyalty_bonus=12.0 if normalized_tier == "vip" else 7.0,
            reputation_bonus=14.0,
            metadata_json={
                "season_id": season_id,
                "title": ceremony["title"],
                "discount_bps": discount_bps,
            },
        )
        self.session.add(ticket)
        profile.loyalty_score = round(float(profile.loyalty_score or 0.0) + float(ticket.loyalty_bonus), 3)
        self._mark_attendance(
            profile=profile,
            event_key=event_key,
            event_type="ceremony",
            title=str(ceremony["title"]),
            status="booked",
            metadata={"season_id": season_id, "ticket_tier": normalized_tier},
        )
        self._refresh_profile(profile)
        self.session.flush()
        return ticket

    def cast_ceremony_vote(self, *, actor: User, award_id: str, player_id: str, season_id: str | None = None) -> dict[str, Any]:
        vote = RegenEcosystemService(self.session).cast_award_vote(
            award_id,
            user_id=actor.id,
            player_id=player_id,
            season_id=season_id,
        )
        profile = self.get_or_create_profile(actor=actor)
        profile.loyalty_score = round(float(profile.loyalty_score or 0.0) + 2.0, 3)
        profile.reputation_score = round(float(profile.reputation_score or 0.0) + 0.75, 3)
        self._refresh_profile(profile)
        self.session.flush()
        return {
            "vote_id": vote.id,
            "award_id": vote.award_id,
            "player_id": vote.player_id,
            "season_id": vote.season_id,
            "fan_profile": self.profile_payload(profile),
        }

    def ceremony_experience(self, *, season_id: str, current_user: User | None = None) -> dict[str, Any]:
        payload = AwardsCultureService(self.session).get_ceremony(season_id=season_id)
        if payload is None:
            raise ValueError("Awards ceremony was not found for the requested season.")
        event_key = self._ceremony_event_key(season_id)
        sold, vip_sold = self._ticket_counts(event_key=event_key)
        user_profile = self.get_or_create_profile(actor=current_user) if current_user is not None else None
        discount_bps = 0
        if user_profile is not None:
            if user_profile.fan_tier == "Legend":
                discount_bps = 1500
            elif user_profile.fan_tier == "Ultra":
                discount_bps = 700
        live_vote_snapshot = self._live_vote_snapshot(season_id=season_id)
        reaction_summary = self._reaction_summary(event_key=event_key, match_id=None)
        legend_attendees = int(
            self.session.scalar(
                select(func.count())
                .select_from(FanExperienceTicket)
                .join(FanProfile, FanProfile.id == FanExperienceTicket.fan_profile_id, isouter=True)
                .where(
                    FanExperienceTicket.event_key == event_key,
                    FanExperienceTicket.status.in_(("purchased", "attended")),
                    FanProfile.fan_tier == "Legend",
                )
            )
            or 0
        )
        return {
            **payload,
            "season_event_key": event_key,
            "ceremony_flow": ["Nominees", "Top 3", "Live Reveal", "Winner", "Reaction Explosion"],
            "ticketed_access": True,
            "tv_mode_only": True,
            "general_seat_capacity": DEFAULT_CEREMONY_CAPACITY,
            "vip_seat_capacity": DEFAULT_CEREMONY_VIP_CAPACITY,
            "tickets_sold": sold,
            "vip_tickets_sold": vip_sold,
            "ticket_price_coin": _quantize("14.0000"),
            "vip_ticket_price_coin": _quantize("32.0000"),
            "discount_bps": discount_bps,
            "exclusive_commentary_lines": [
                "TV Mode unlocks the live reveal lane with isolated podium audio.",
                "Priority viewers hear the shortlist tension before the envelope opens.",
            ],
            "live_vote_enabled": True,
            "live_vote_note": "Live voting shapes the room and the reveal order, but the final award result remains deterministic.",
            "live_vote_snapshot": live_vote_snapshot,
            "reaction_explosion": {
                "magnitude": "iconic" if legend_attendees >= 5 or sold >= DEFAULT_CEREMONY_CAPACITY * 0.5 else "rising",
                "legend_attendees": legend_attendees,
                "fan_reaction_weight": round(float(reaction_summary["total_weight"]), 3),
            },
            "current_user_access": None
            if user_profile is None
            else {
                "fan_profile_id": user_profile.id,
                "fan_tier": user_profile.fan_tier,
                "discount_bps": discount_bps,
                "has_ticket": self._user_has_ticket(current_user.id, event_key) if current_user is not None else False,
            },
        }

    def regen_hype_board(self, *, season_id: str | None = None, country_limit: int = 12) -> dict[str, Any]:
        seed_rows = list(
            self.session.scalars(
                select(NationalRegenSeed).order_by(
                    NationalRegenSeed.potential_rating.desc(),
                    NationalRegenSeed.current_rating.desc(),
                    NationalRegenSeed.growth_curve.desc(),
                    NationalRegenSeed.display_name.asc(),
                )
            ).all()
        )
        wonderkids = seed_rows[:10]
        rising_stars = seed_rows[10:15] if len(seed_rows) >= 15 else seed_rows[:5]
        grouped: dict[str, list[NationalRegenSeed]] = defaultdict(list)
        for item in seed_rows:
            grouped[item.country_code].append(item)
        national_heroes = [
            {
                "country_code": country_code,
                "country_name": rows[0].country_name,
                "heroes": [self._national_seed_payload(seed) for seed in rows[:3]],
            }
            for country_code, rows in sorted(grouped.items(), key=lambda item: item[0])[:country_limit]
        ]
        award_nominees = self._award_nominee_headlines(season_id=season_id)
        wonderkid_article = self._ensure_news_article(
            article_type="regen_shortlist",
            title="Top 10 Wonderkids",
            related_match_id=None,
            body="The latest GTEX shortlist points to a generation of wonderkids with world-tournament potential already building.",
            tags=["wonderkids", "regen_hype", "shortlist"],
            metadata={"count": len(wonderkids)},
        )
        rising_star_article = self._ensure_news_article(
            article_type="regen_shortlist",
            title="Top 5 Rising Stars",
            related_match_id=None,
            body="These five rising stars are now carrying enough traction to punch through into the main GTEX conversation.",
            tags=["rising_stars", "regen_hype", "shortlist"],
            metadata={"count": len(rising_stars)},
        )
        return {
            "wonderkids": [self._national_seed_payload(item) for item in wonderkids],
            "rising_stars": [self._national_seed_payload(item) for item in rising_stars],
            "national_heroes": national_heroes,
            "award_nominee_headlines": award_nominees,
            "news_article_ids": [wonderkid_article.id, rising_star_article.id],
        }

    def simulate_full_experience(
        self,
        *,
        actor: User,
        match: GtexMatch,
        simulate_match,
        read_match_view,
        season_id: str | None = None,
    ) -> dict[str, Any]:
        profile = self.get_or_create_profile(actor=actor)
        metadata = dict(match.metadata_json or {})
        fan_meta = dict(metadata.get("fan_experience") or {})
        fan_meta.setdefault("is_final", True)
        fan_meta["capacity"] = max(10, int(fan_meta.get("capacity") or 0))
        fan_meta["vip_capacity"] = max(2, int(fan_meta.get("vip_capacity") or 0))
        fan_meta["synthetic_ticket_sales"] = max(0, int(fan_meta["capacity"]) - 1)
        metadata["fan_experience"] = fan_meta
        match.metadata_json = metadata

        ticket = self.purchase_match_ticket(actor=actor, match=match, ticket_tier="vip")
        reaction = self.submit_match_reaction(actor=actor, match=match, reaction_type="hype", supported_side="home")
        simulated_match = simulate_match(match.id)
        match_view = read_match_view(simulated_match.id)
        ceremony_payload = None
        if season_id:
            self.purchase_ceremony_ticket(actor=actor, season_id=season_id, ticket_tier="vip")
            ceremony_payload = self.ceremony_experience(season_id=season_id, current_user=actor)
            for segment in list(ceremony_payload.get("segments") or []):
                finalists = list(segment.get("finalists") or [])
                finalist_id = finalists[0].get("entity_id") if finalists else None
                award_code = str(segment.get("award_code") or "")
                if not finalist_id or not award_code:
                    continue
                award = self.session.scalar(select(RegenAward).where(RegenAward.code == award_code))
                if award is None:
                    continue
                try:
                    self.cast_ceremony_vote(
                        actor=actor,
                        award_id=award.id,
                        player_id=str(finalist_id),
                        season_id=season_id,
                    )
                except ValueError:
                    pass
                break
            ceremony_payload = self.ceremony_experience(season_id=season_id, current_user=actor)
        regen_hype = self.regen_hype_board(season_id=season_id)
        return {
            "fan_profile": self.profile_payload(profile),
            "ticket": self.ticket_payload(ticket),
            "reaction": self.reaction_payload(reaction),
            "match": match_view,
            "ceremony": ceremony_payload,
            "regen_hype": regen_hype,
            "timeline": [
                "Final announced",
                "Tickets released",
                "Sell-out trigger fired",
                "Fans attended",
                "Match completed",
                "Award nominees generated",
                "Ceremony broadcast queued",
                "Live reaction explosion armed",
            ],
        }

    def _match_offer(self, *, match: GtexMatch, current_user: User | None) -> dict[str, Any]:
        metadata = dict(match.metadata_json or {})
        fan_meta = dict(metadata.get("fan_experience") or {})
        event_key = self._match_event_key(match.id)
        is_final = bool(fan_meta.get("is_final") or fan_meta.get("stage") == "final")
        capacity = max(1, int(fan_meta.get("capacity") or (180 if is_final else 72)))
        vip_capacity = max(4, int(fan_meta.get("vip_capacity") or round(capacity * 0.08)))
        ticket_price = _quantize(fan_meta.get("base_ticket_price") or ("18.0000" if is_final else "8.0000"))
        vip_ticket_price = _quantize(fan_meta.get("vip_ticket_price") or (ticket_price * Decimal("2.4000")))
        real_sold, real_vip_sold = self._ticket_counts(event_key=event_key)
        synthetic_sales = max(0, int(fan_meta.get("synthetic_ticket_sales") or 0))
        synthetic_vip_sales = max(0, int(fan_meta.get("synthetic_vip_sales") or 0))
        social = GtexSocialWarfareService(self.session)
        fan_war = social.fan_war_summary(match=match)
        ticket_demand_multiplier = float(dict(fan_war.get("impact") or {}).get("ticket_demand_multiplier") or 1.0)
        social_sales_bonus = max(0, int(round(capacity * max(0.0, ticket_demand_multiplier - 1.0) * 0.4)))
        sold = real_sold + synthetic_sales
        vip_sold = real_vip_sold + synthetic_vip_sales
        sold += min(max(0, capacity - sold), social_sales_bonus)
        sold_ratio = sold / float(capacity)
        sell_out_triggered = sold_ratio > 0.9
        current_user_profile = self.get_or_create_profile(actor=current_user) if current_user is not None else None
        current_user_ticket = None
        if current_user is not None:
            current_user_ticket = self.session.scalar(
                select(FanExperienceTicket).where(
                    FanExperienceTicket.user_id == current_user.id,
                    FanExperienceTicket.event_key == event_key,
                )
            )
        dao_priority = self._is_dao_priority_user(current_user, match) if current_user is not None else False
        discount_bps = 0
        if current_user_profile is not None:
            if current_user_profile.fan_tier == "Legend":
                discount_bps = 1500
            elif current_user_profile.fan_tier == "Ultra":
                discount_bps = 700
        if dao_priority:
            discount_bps = max(discount_bps, 2000)
        if sell_out_triggered:
            ticket_price = _quantize(ticket_price * Decimal("1.2500"))
            vip_ticket_price = _quantize(vip_ticket_price * Decimal("1.2500"))
        exclusive_commentary_lines = [
            f"Priority stream: {self._match_title(match)} is tipping into a sell-out cauldron.",
            "Exclusive line: TV crews are tracking the crowd mood swing in real time.",
        ]
        return {
            "event_key": event_key,
            "match_id": match.id,
            "event_title": self._match_title(match),
            "is_final": is_final,
            "capacity": capacity,
            "vip_capacity": vip_capacity,
            "tickets_sold": sold,
            "vip_tickets_sold": vip_sold,
            "tickets_remaining": max(0, capacity - sold),
            "ticket_price_coin": ticket_price,
            "vip_ticket_price_coin": vip_ticket_price,
            "ticket_access_phase": "dao_early" if dao_priority and sold < capacity else "public_open",
            "exclusive_commentary_lines": exclusive_commentary_lines,
            "sell_out_hype": {
                "triggered": sell_out_triggered,
                "price_surge_multiplier": 1.25 if sell_out_triggered else 1.0,
                "homepage_promotion": sell_out_triggered,
                "notification_blast": sell_out_triggered,
            },
            "current_user": None
            if current_user_profile is None or current_user is None
            else {
                "fan_profile_id": current_user_profile.id,
                "fan_tier": current_user_profile.fan_tier,
                "dao_priority": dao_priority,
                "discount_bps": discount_bps,
                "has_ticket": current_user_ticket is not None,
            },
            "discount_bps": discount_bps,
            "social_ticket_demand_multiplier": round(ticket_demand_multiplier, 4),
            "tribe_pressure": round(float(fan_war.get("tribe_pressure") or 0.0), 4),
        }

    def _atmosphere_summary(self, *, match: GtexMatch, offer: dict[str, Any], reaction_summary: dict[str, Any]) -> dict[str, Any]:
        sold_ratio = int(offer["tickets_sold"]) / float(max(int(offer["capacity"]), 1))
        total_weight = float(reaction_summary["total_weight"])
        home_support = float(reaction_summary["home_support"])
        away_support = float(reaction_summary["away_support"])
        social = GtexSocialWarfareService(self.session)
        fan_war = social.fan_war_summary(match=match)
        live_chat = social.live_chat_summary(match=match)
        tribe_pressure = float(fan_war.get("tribe_pressure") or 0.0)
        chat_pressure = social.live_chat_pressure(match=match)
        crowd_boost = round(
            _clamp(
                (sold_ratio * 0.34)
                + (total_weight * 0.05)
                + (tribe_pressure * 0.22)
                + (chat_pressure * 0.16),
                0.08,
                0.99,
            ),
            4,
        )
        commentary_tone = (
            "viral_eruption"
            if float(live_chat.get("moment_spike_score") or 0.0) >= 2.0
            else str(dict(fan_war.get("impact") or {}).get("commentary_tone") or "charged")
        )
        if reaction_summary["dominant_reaction"] == "boo":
            commentary_tone = "hostile"
        elif sold_ratio > 0.9 or reaction_summary["dominant_reaction"] == "hype":
            commentary_tone = "fever_pitch" if commentary_tone == "charged" else commentary_tone
        narrative_tag = (
            "sell_out_cauldron"
            if sold_ratio > 0.9 and reaction_summary["legend_weight"] >= 2.0
            else "fan_war_cauldron"
            if tribe_pressure >= 0.6
            else "viral_reaction_storm"
            if chat_pressure >= 0.4
            else "rivalry_voltage"
            if reaction_summary["dominant_reaction"] == "boo"
            else "anthemic_rise"
        )
        return {
            "crowd_intensity_boost": crowd_boost,
            "commentary_tone": commentary_tone,
            "match_narrative_tag": narrative_tag,
            "home_strength_multiplier": round(
                1.0
                + max(home_support, 0.0) * 0.018
                + (crowd_boost * 0.03)
                + (tribe_pressure * 0.018),
                4,
            ),
            "away_strength_multiplier": round(
                1.0
                + max(away_support, 0.0) * 0.016
                + (crowd_boost * 0.02)
                + (chat_pressure * 0.014),
                4,
            ),
            "intensity_bonus_events": min(
                6,
                max(
                    1,
                    int(round((crowd_boost * 3) + total_weight + (tribe_pressure * 2) + (chat_pressure * 2))),
                ),
            ),
            "sell_out_triggered": bool(offer["sell_out_hype"]["triggered"]),
            "priority_stream": int(offer["tickets_sold"]) > 0,
            "exclusive_commentary_lines": list(offer["exclusive_commentary_lines"]),
            "fan_war_pressure": round(tribe_pressure, 4),
            "live_chat_pressure": round(chat_pressure, 4),
            "moment_spike_bonus": int(live_chat.get("moment_spike_bonus") or 0),
        }

    def _reaction_summary(self, *, event_key: str, match_id: str | None) -> dict[str, Any]:
        conditions = [FanReaction.event_key == event_key]
        if match_id is not None:
            conditions.append(FanReaction.match_id == match_id)
        rows = list(self.session.scalars(select(FanReaction).where(*conditions)).all())
        totals = defaultdict(float)
        legend_weight = 0.0
        home_support = 0.0
        away_support = 0.0
        for row in rows:
            totals[row.reaction_type] += float(row.weight or 0.0)
            if row.tier_at_reaction == "Legend":
                legend_weight += float(row.weight or 0.0)
            signed = float(row.weight or 0.0) if row.reaction_type in POSITIVE_REACTIONS else -float(row.weight or 0.0)
            if row.supported_side == "away":
                away_support += signed
            else:
                home_support += signed
        dominant = "neutral"
        if totals:
            dominant = max(totals.items(), key=lambda item: item[1])[0]
        return {
            "total_reactions": len(rows),
            "total_weight": round(sum(float(row.weight or 0.0) for row in rows), 4),
            "dominant_reaction": dominant,
            "cheer_weight": round(totals["cheer"], 4),
            "boo_weight": round(totals["boo"], 4),
            "hype_weight": round(totals["hype"], 4),
            "legend_weight": round(legend_weight, 4),
            "home_support": round(home_support, 4),
            "away_support": round(away_support, 4),
        }

    def _refresh_profile(self, profile: FanProfile) -> None:
        profile.fan_tier = self._fan_tier(float(profile.loyalty_score or 0.0))
        profile.badges_json = self._profile_badges(profile)
        profile.metadata_json = {
            **dict(profile.metadata_json or {}),
            "fan_tier": profile.fan_tier,
            "attendance_count": int(profile.attendance_count or 0),
        }

    def _fan_tier(self, loyalty_score: float) -> str:
        if loyalty_score >= 85:
            return "Legend"
        if loyalty_score >= 40:
            return "Ultra"
        return "Casual"

    def _tier_weight(self, fan_tier: str) -> float:
        return {"Casual": 1.0, "Ultra": 1.6, "Legend": 2.35}.get(fan_tier, 1.0)

    def _profile_badges(self, profile: FanProfile) -> list[str]:
        badges: list[str] = []
        attendance_count = int(profile.attendance_count or 0)
        if attendance_count >= 1:
            badges.append("match-going")
        if attendance_count >= 5:
            badges.append("stadium-core")
        if profile.fan_tier in {"Ultra", "Legend"}:
            badges.append("ultra-voice")
        if profile.fan_tier == "Legend":
            badges.append("legend-crest")
        if any(item.get("event_type") == "ceremony" for item in list(profile.attendance_history_json or [])):
            badges.append("ceremony-circle")
        if list(profile.rival_club_ids_json or []):
            badges.append("rivalry-marked")
        return sorted(dict.fromkeys(badges))

    def _default_rivals_for_club(self, club_id: str) -> list[str]:
        rows = list(
            self.session.scalars(
                select(RivalryProfile)
                .where(or_(RivalryProfile.club_a_id == club_id, RivalryProfile.club_b_id == club_id))
                .order_by(RivalryProfile.intensity_score.desc(), RivalryProfile.matches_played.desc())
            ).all()
        )
        rivals: list[str] = []
        for row in rows[:3]:
            rivals.append(row.club_b_id if row.club_a_id == club_id else row.club_a_id)
        return list(dict.fromkeys(rivals))

    def _mark_attendance(
        self,
        *,
        profile: FanProfile,
        event_key: str,
        event_type: str,
        title: str,
        status: str,
        metadata: dict[str, Any],
    ) -> None:
        history = [dict(item) for item in list(profile.attendance_history_json or []) if isinstance(item, dict)]
        found = False
        for item in history:
            if item.get("event_key") != event_key:
                continue
            item["status"] = status
            item["metadata"] = {**dict(item.get("metadata") or {}), **metadata}
            found = True
        if not found:
            history.insert(0, {"event_key": event_key, "event_type": event_type, "title": title, "status": status, "metadata": dict(metadata)})
        profile.attendance_history_json = history[:20]
        unique_events = {item.get("event_key") for item in history if item.get("event_key")}
        profile.attendance_count = len(unique_events)

    def _ticket_counts(self, *, event_key: str) -> tuple[int, int]:
        rows = list(
            self.session.scalars(
                select(FanExperienceTicket).where(
                    FanExperienceTicket.event_key == event_key,
                    FanExperienceTicket.status.in_(("purchased", "attended")),
                )
            ).all()
        )
        sold = len(rows)
        vip_sold = sum(1 for row in rows if row.ticket_tier in {"vip", "vip-seat"})
        return sold, vip_sold

    def _trigger_sell_out_hype(self, *, match: GtexMatch, offer: dict[str, Any]) -> None:
        metadata = dict(match.metadata_json or {})
        fan_meta = dict(metadata.get("fan_experience") or {})
        if fan_meta.get("sell_out_triggered"):
            return
        fan_meta["sell_out_triggered"] = True
        fan_meta["homepage_promotion"] = True
        fan_meta["notification_blast"] = True
        fan_meta["price_surge_multiplier"] = 1.25
        metadata["fan_experience"] = fan_meta
        match.metadata_json = metadata
        self._ensure_news_article(
            article_type="sell_out_hype",
            title=f"{offer['event_title']} enters sell-out mode",
            related_match_id=match.id,
            body="Ticket demand crossed the 90 percent mark, forcing the full hype stack online.",
            tags=["sell_out", "tickets", "homepage"],
            metadata={"event_key": offer["event_key"]},
        )
        recipients = {user_id for user_id in (match.home_user_id, match.away_user_id, match.requested_by_user_id) if user_id}
        recipients.update(
            str(user_id)
            for user_id in self.session.scalars(
                select(FanExperienceTicket.user_id).where(FanExperienceTicket.event_key == offer["event_key"])
            ).all()
            if user_id
        )
        for user_id in recipients:
            self.session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic="fan_experience",
                    template_key="sell_out_hype",
                    resource_type="gtex_match",
                    resource_id=match.id,
                    fixture_id=match.id,
                    message=f"{offer['event_title']} is now in sell-out mode.",
                    metadata_json={"homepage_promotion": True, "price_surge_multiplier": 1.25},
                )
            )

    def _upsert_prestige_rating(self, profile: FanProfile) -> None:
        rating = self.session.scalar(
            select(PrestigeRating).where(
                PrestigeRating.entity_type == "fan",
                PrestigeRating.entity_id == profile.id,
                PrestigeRating.scope == "fandom",
                PrestigeRating.season_key == "lifetime",
            )
        )
        prestige_score = round(float(profile.reputation_score or 0.0) + (float(profile.loyalty_score or 0.0) * 0.45), 3)
        if rating is None:
            rating = PrestigeRating(
                entity_type="fan",
                entity_id=profile.id,
                entity_name=profile.favorite_club_name or f"Fan {profile.user_id[:8]}",
                scope="fandom",
                season_key="lifetime",
                prestige_score=prestige_score,
                trophies=0.0,
                win_rate=0.0,
                player_development=0.0,
                earnings=0.0,
                difficulty_modifier=0.0,
                perception_score=round(float(profile.reputation_score or 0.0), 3),
                prestige_tier=self._prestige_tier(prestige_score),
                rank_position=None,
                metadata_json={"fan_tier": profile.fan_tier},
            )
            self.session.add(rating)
        else:
            rating.entity_name = profile.favorite_club_name or rating.entity_name
            rating.prestige_score = prestige_score
            rating.perception_score = round(float(profile.reputation_score or 0.0), 3)
            rating.prestige_tier = self._prestige_tier(prestige_score)
            rating.metadata_json = {**dict(rating.metadata_json or {}), "fan_tier": profile.fan_tier}

    def _prestige_tier(self, prestige_score: float) -> str:
        if prestige_score >= 120:
            return "Legend"
        if prestige_score >= 70:
            return "Gold"
        if prestige_score >= 30:
            return "Silver"
        return "Bronze"

    def _is_dao_priority_user(self, actor: User | None, match: GtexMatch | None) -> bool:
        if actor is None or match is None:
            return False
        return actor.id in {item for item in (match.home_user_id, match.away_user_id, match.requested_by_user_id) if item}

    def _match_event_key(self, match_id: str) -> str:
        return f"match:{match_id}"

    def _ceremony_event_key(self, season_id: str) -> str:
        return f"ceremony:{season_id}"

    def _match_title(self, match: GtexMatch) -> str:
        metadata = dict(match.metadata_json or {})
        home = str(metadata.get("home_label") or metadata.get("match_context", {}).get("home_label") or "Home")
        away = str(metadata.get("away_label") or metadata.get("match_context", {}).get("away_label") or "Away")
        return f"{home} vs {away}"

    def _ensure_news_article(
        self,
        *,
        article_type: str,
        title: str,
        related_match_id: str | None,
        body: str,
        tags: list[str],
        metadata: dict[str, Any],
    ) -> NewsArticle:
        article = self.session.scalar(select(NewsArticle).where(NewsArticle.article_type == article_type, NewsArticle.title == title))
        if article is None:
            article = NewsArticle(
                article_type=article_type,
                title=title,
                body=body,
                summary=body[:180],
                tags_json=list(tags),
                headline_variants_json={},
                related_match_id=related_match_id,
                trend_score=round(min(100.0, 24.0 + (len(tags) * 6.0)), 3),
                perception_delta=0.0,
                metadata_json=dict(metadata),
            )
            self.session.add(article)
            self.session.flush()
        return article

    def _user_has_ticket(self, user_id: str, event_key: str) -> bool:
        count = self.session.scalar(
            select(func.count())
            .select_from(FanExperienceTicket)
            .where(
                FanExperienceTicket.user_id == user_id,
                FanExperienceTicket.event_key == event_key,
                FanExperienceTicket.status.in_(("purchased", "attended")),
            )
        )
        return bool(count)

    def _live_vote_snapshot(self, *, season_id: str) -> dict[str, list[dict[str, Any]]]:
        awards = {award.id: award for award in self.session.scalars(select(RegenAward)).all()}
        rows = self.session.execute(
            select(
                RegenAwardVote.award_id,
                RegenAwardVote.player_id,
                func.count(RegenAwardVote.id).label("vote_count"),
            )
            .where(RegenAwardVote.season_id == season_id)
            .group_by(RegenAwardVote.award_id, RegenAwardVote.player_id)
            .order_by(func.count(RegenAwardVote.id).desc())
        ).all()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for award_id, player_id, vote_count in rows:
            award = awards.get(award_id)
            if award is None:
                continue
            grouped[award.code].append({"player_id": player_id, "vote_count": int(vote_count or 0)})
        return {code: items[:3] for code, items in grouped.items()}

    def _award_nominee_headlines(self, *, season_id: str | None) -> list[dict[str, Any]]:
        ceremony = AwardsCultureService(self.session).get_ceremony(season_id=season_id)
        if ceremony is None:
            return []
        headlines: list[dict[str, Any]] = []
        for segment in list(ceremony.get("segments") or []):
            finalists = list(segment.get("finalists") or [])
            headlines.append(
                {
                    "award_code": segment.get("award_code"),
                    "award_name": segment.get("title"),
                    "headline": f"{segment.get('title')} finalists are now locked in.",
                    "finalists": finalists[:3],
                }
            )
            article = self._ensure_news_article(
                article_type="award_nominee",
                title=f"{segment.get('title')} finalists",
                related_match_id=None,
                body=f"{segment.get('title')} has narrowed to the final shortlist heading into the live reveal.",
                tags=["awards", "nominees", str(segment.get("award_code") or "").lower()],
                metadata={"award_code": segment.get("award_code"), "finalists": finalists[:3]},
            )
            for rank, finalist in enumerate(finalists[:3], start=1):
                player_id = finalist.get("entity_id")
                if not player_id:
                    continue
                existing = self.session.scalar(
                    select(PlayerFanReaction).where(
                        PlayerFanReaction.player_id == player_id,
                        PlayerFanReaction.article_id == article.id,
                        PlayerFanReaction.reaction_type == "hype",
                    )
                )
                if existing is not None:
                    continue
                self.session.add(
                    PlayerFanReaction(
                        player_id=player_id,
                        article_id=article.id,
                        match_id=None,
                        reaction_type="hype",
                        intensity=max(0.5, 1.35 - (rank * 0.15)),
                        headline=f"{finalist.get('display_name')} enters the {segment.get('title')} top three",
                        body="Nomination momentum is now feeding straight into the awards-night conversation.",
                        metadata_json={"award_code": segment.get("award_code"), "rank": rank},
                    )
                )
        return headlines

    def _national_seed_payload(self, seed: NationalRegenSeed) -> dict[str, Any]:
        return {
            "id": seed.id,
            "seed_key": seed.seed_key,
            "display_name": seed.display_name,
            "country_code": seed.country_code,
            "country_name": seed.country_name,
            "primary_position": seed.primary_position,
            "current_rating": int(seed.current_rating),
            "potential_rating": int(seed.potential_rating),
            "growth_curve": round(float(seed.growth_curve or 0.0), 4),
            "rarity_tier": seed.rarity_tier,
            "seed_type": seed.seed_type,
            "metadata": dict(seed.metadata_json or {}),
        }


__all__ = ["GtexFanExperienceService"]
