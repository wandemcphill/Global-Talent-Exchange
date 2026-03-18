from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.models.base import generate_uuid
from backend.app.models.club_profile import ClubProfile
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.creator_league import CreatorLeagueConfig, CreatorLeagueSeason, CreatorLeagueSeasonTier
from backend.app.models.creator_monetization import (
    CreatorBroadcastModeConfig,
    CreatorBroadcastPurchase,
    CreatorMatchGiftEvent,
    CreatorSeasonPass,
    CreatorStadiumPricing,
    CreatorStadiumTicketPurchase,
)
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorSquad
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from backend.app.services.spending_control_service import SpendingControlService, SpendingControlViolation
from backend.app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
CREATOR_LEAGUE_KEY = "creator_league"
CREATOR_BROADCAST_SHARE = Decimal("0.5000")
CREATOR_SEASON_PASS_SHARE = Decimal("0.5000")
CREATOR_GIFT_SHARE = Decimal("0.7000")
MIN_SEASON_PASS_PRICE = Decimal("60.0000")
SEASON_PASS_PRICE_PER_MATCH = Decimal("2.5000")


class CreatorBroadcastError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(frozen=True, slots=True)
class CreatorBeneficiary:
    club_id: str
    creator_user_id: str


@dataclass(frozen=True, slots=True)
class CreatorMatchContext:
    season: CreatorLeagueSeason
    season_tier: CreatorLeagueSeasonTier
    competition: Competition
    match: CompetitionMatch
    home_club: ClubProfile | None
    away_club: ClubProfile | None
    home_beneficiary: CreatorBeneficiary | None
    away_beneficiary: CreatorBeneficiary | None

    @property
    def creator_club_ids(self) -> tuple[str, ...]:
        values = []
        if self.home_beneficiary is not None:
            values.append(self.home_beneficiary.club_id)
        if self.away_beneficiary is not None and self.away_beneficiary.club_id not in values:
            values.append(self.away_beneficiary.club_id)
        return tuple(values)


@dataclass(frozen=True, slots=True)
class CreatorMatchAccess:
    has_access: bool
    source: str | None = None
    purchase: CreatorBroadcastPurchase | None = None
    season_pass: CreatorSeasonPass | None = None
    stadium_ticket: CreatorStadiumTicketPurchase | None = None


@dataclass(frozen=True, slots=True)
class CreatorBroadcastQuote:
    context: CreatorMatchContext
    mode: CreatorBroadcastModeConfig
    duration_minutes: int
    price_coin: Decimal
    access: CreatorMatchAccess


class CreatorBroadcastService:
    DEFAULT_MODE_CONFIGS = (
        {
            "mode_key": "key_moments",
            "name": "Key Moments Mode",
            "description": "10-15 minute creator match recap.",
            "min_duration_minutes": 10,
            "max_duration_minutes": 15,
            "min_price_coin": Decimal("2.0000"),
            "max_price_coin": Decimal("3.0000"),
        },
        {
            "mode_key": "extended",
            "name": "Extended Mode",
            "description": "15-20 minute creator match stream.",
            "min_duration_minutes": 16,
            "max_duration_minutes": 20,
            "min_price_coin": Decimal("3.0000"),
            "max_price_coin": Decimal("5.0000"),
        },
        {
            "mode_key": "full_match",
            "name": "Full Match Mode",
            "description": "Full 90 minute creator match simulation.",
            "min_duration_minutes": 21,
            "max_duration_minutes": 90,
            "min_price_coin": Decimal("8.0000"),
            "max_price_coin": Decimal("12.0000"),
        },
    )

    def __init__(self, session: Session, wallet_service: WalletService | None = None) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()

    def list_mode_configs(self) -> list[CreatorBroadcastModeConfig]:
        self._ensure_default_mode_configs()
        return list(
            self.session.scalars(
                select(CreatorBroadcastModeConfig)
                .where(CreatorBroadcastModeConfig.is_active.is_(True))
                .order_by(CreatorBroadcastModeConfig.min_duration_minutes.asc(), CreatorBroadcastModeConfig.created_at.asc())
            ).all()
        )

    def get_match_context(self, match_id: str) -> CreatorMatchContext:
        match = self.session.get(CompetitionMatch, match_id)
        if match is None:
            raise CreatorBroadcastError("Creator League match was not found.", reason="match_not_found")
        competition = self.session.get(Competition, match.competition_id)
        if competition is None:
            raise CreatorBroadcastError("Competition for match was not found.", reason="competition_not_found")
        if not self._is_creator_league_competition(competition):
            raise CreatorBroadcastError(
                "Creator monetization only supports Creator League matches.",
                reason="creator_league_only",
            )
        season_tier = None
        if competition.source_id:
            season_tier = self.session.get(CreatorLeagueSeasonTier, competition.source_id)
        if season_tier is None:
            season_tier = self.session.scalar(
                select(CreatorLeagueSeasonTier).where(CreatorLeagueSeasonTier.competition_id == competition.id)
            )
        if season_tier is None:
            raise CreatorBroadcastError(
                "Creator League season tier metadata is missing for this competition.",
                reason="creator_league_metadata_missing",
            )
        season = self.session.get(CreatorLeagueSeason, season_tier.season_id)
        if season is None:
            raise CreatorBroadcastError("Creator League season was not found.", reason="season_not_found")
        clubs = {
            club.id: club
            for club in self.session.scalars(
                select(ClubProfile).where(ClubProfile.id.in_((match.home_club_id, match.away_club_id)))
            ).all()
        }
        beneficiaries = self._beneficiaries_for_clubs((match.home_club_id, match.away_club_id))
        return CreatorMatchContext(
            season=season,
            season_tier=season_tier,
            competition=competition,
            match=match,
            home_club=clubs.get(match.home_club_id),
            away_club=clubs.get(match.away_club_id),
            home_beneficiary=beneficiaries.get(match.home_club_id),
            away_beneficiary=beneficiaries.get(match.away_club_id),
        )

    def quote_for_match(self, *, actor: User, match_id: str, duration_minutes: int) -> CreatorBroadcastQuote:
        context = self.get_match_context(match_id)
        mode = self._mode_for_duration(duration_minutes)
        access = self.access_for_match(actor=actor, match_id=match_id)
        price = self._calculate_price(mode, duration_minutes)
        return CreatorBroadcastQuote(
            context=context,
            mode=mode,
            duration_minutes=duration_minutes,
            price_coin=price,
            access=access,
        )

    def access_for_match(self, *, actor: User, match_id: str) -> CreatorMatchAccess:
        context = self.get_match_context(match_id)
        if actor.role.value in {"admin", "super_admin"}:
            return CreatorMatchAccess(has_access=True, source="admin")
        purchase = self.session.scalar(
            select(CreatorBroadcastPurchase).where(
                CreatorBroadcastPurchase.user_id == actor.id,
                CreatorBroadcastPurchase.match_id == context.match.id,
            )
        )
        if purchase is not None:
            return CreatorMatchAccess(has_access=True, source="broadcast_purchase", purchase=purchase)
        season_pass = self.session.scalar(
            select(CreatorSeasonPass).where(
                CreatorSeasonPass.user_id == actor.id,
                CreatorSeasonPass.season_id == context.season.id,
                CreatorSeasonPass.club_id.in_((context.match.home_club_id, context.match.away_club_id)),
            )
        )
        if season_pass is not None:
            return CreatorMatchAccess(has_access=True, source="season_pass", season_pass=season_pass)
        stadium_ticket = self.session.scalar(
            select(CreatorStadiumTicketPurchase).where(
                CreatorStadiumTicketPurchase.user_id == actor.id,
                CreatorStadiumTicketPurchase.match_id == context.match.id,
            )
        )
        if stadium_ticket is not None:
            return CreatorMatchAccess(has_access=True, source="stadium_ticket", stadium_ticket=stadium_ticket)
        return CreatorMatchAccess(has_access=False)

    def purchase_broadcast(self, *, actor: User, match_id: str, duration_minutes: int) -> CreatorBroadcastPurchase:
        if not self._broadcast_purchases_enabled():
            raise CreatorBroadcastError(
                "Creator League broadcast purchases are currently disabled by admin policy.",
                reason="broadcast_sales_disabled",
            )
        quote = self.quote_for_match(actor=actor, match_id=match_id, duration_minutes=duration_minutes)
        if quote.access.season_pass is not None:
            raise CreatorBroadcastError(
                "Season pass already grants access to this Creator League match.",
                reason="season_pass_already_grants_access",
            )
        if quote.access.stadium_ticket is not None:
            raise CreatorBroadcastError(
                "A creator stadium ticket already grants live access to this Creator League match.",
                reason="stadium_ticket_already_grants_access",
            )
        if quote.access.purchase is not None:
            return quote.access.purchase

        price_coin = self._normalize_amount(quote.price_coin)
        control_evaluation = self._evaluate_creator_purchase_controls(
            actor=actor,
            amount=price_coin,
            purchase_scope="broadcast_purchase",
            metadata_json={
                "match_id": quote.context.match.id,
                "competition_id": quote.context.competition.id,
                "season_id": quote.context.season.id,
                "duration_minutes": quote.duration_minutes,
                "mode_key": quote.mode.mode_key,
            },
        )
        creator_total = self._normalize_amount(price_coin * CREATOR_BROADCAST_SHARE)
        creator_split = self._creator_split(
            creator_total=creator_total,
            home_beneficiary=quote.context.home_beneficiary,
            away_beneficiary=quote.context.away_beneficiary,
        )
        platform_share = self._normalize_amount(price_coin - sum(creator_split.values(), Decimal("0.0000")))
        creator_user_ids = {
            club_id: beneficiary.creator_user_id
            for club_id, beneficiary in (
                (quote.context.match.home_club_id, quote.context.home_beneficiary),
                (quote.context.match.away_club_id, quote.context.away_beneficiary),
            )
            if beneficiary is not None
        }

        purchase = CreatorBroadcastPurchase(
            user_id=actor.id,
            season_id=quote.context.season.id,
            competition_id=quote.context.competition.id,
            match_id=quote.context.match.id,
            mode_key=quote.mode.mode_key,
            duration_minutes=quote.duration_minutes,
            price_coin=price_coin,
            platform_share_coin=platform_share,
            home_creator_share_coin=creator_split.get(quote.context.match.home_club_id, Decimal("0.0000")),
            away_creator_share_coin=creator_split.get(quote.context.match.away_club_id, Decimal("0.0000")),
            metadata_json={
                "mode_name": quote.mode.name,
                "creator_league_only": True,
            },
        )
        self.session.add(purchase)
        self.session.flush()
        self._post_creator_transaction(
            actor=actor,
            total_amount=price_coin,
            creator_split=creator_split,
            platform_share=platform_share,
            reference=f"creator-broadcast:{purchase.id}",
            description=f"Creator broadcast purchase for match {quote.context.match.id}",
            creator_user_ids=creator_user_ids,
        )
        for club_id, creator_amount in creator_split.items():
            self._distribute_shareholder_revenue(
                actor=actor,
                club_id=club_id,
                creator_user_id=creator_user_ids[club_id],
                source_type="match_video",
                source_reference_id=purchase.id,
                eligible_revenue_coin=creator_amount,
                season_id=quote.context.season.id,
                competition_id=quote.context.competition.id,
                match_id=quote.context.match.id,
                metadata_json={"mode_key": quote.mode.mode_key, "duration_minutes": quote.duration_minutes},
            )
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=purchase.id,
            metadata_json={"creator_broadcast_purchase_id": purchase.id},
        )
        return purchase

    def purchase_season_pass(self, *, actor: User, season_id: str, club_id: str) -> CreatorSeasonPass:
        if not self._season_pass_sales_enabled():
            raise CreatorBroadcastError(
                "Creator League season-pass sales are currently disabled by admin policy.",
                reason="season_pass_sales_disabled",
            )
        season = self.session.get(CreatorLeagueSeason, season_id)
        if season is None:
            raise CreatorBroadcastError("Creator League season was not found.", reason="season_not_found")
        existing = self.session.scalar(
            select(CreatorSeasonPass).where(
                CreatorSeasonPass.user_id == actor.id,
                CreatorSeasonPass.season_id == season_id,
                CreatorSeasonPass.club_id == club_id,
            )
        )
        if existing is not None:
            return existing

        season_tiers = list(
            self.session.scalars(
                select(CreatorLeagueSeasonTier).where(CreatorLeagueSeasonTier.season_id == season_id)
            ).all()
        )
        if not any(club_id in (season_tier.club_ids_json or []) for season_tier in season_tiers):
            raise CreatorBroadcastError(
                "Season passes only apply to Creator League clubs in the selected season.",
                reason="season_pass_creator_league_only",
            )

        beneficiary = self._beneficiaries_for_clubs((club_id,)).get(club_id)
        if beneficiary is None:
            raise CreatorBroadcastError(
                "Creator club is not linked to an active creator profile.",
                reason="creator_profile_missing",
            )

        competition_ids = tuple(season_tier.competition_id for season_tier in season_tiers)
        scheduled_matches = int(
            self.session.scalar(
                select(func.count())
                .select_from(CompetitionMatch)
                .where(
                    CompetitionMatch.competition_id.in_(competition_ids),
                    or_(
                        CompetitionMatch.home_club_id == club_id,
                        CompetitionMatch.away_club_id == club_id,
                    ),
                )
            )
            or 0
        )
        billable_matches = scheduled_matches or 38
        configured_price = self.session.scalar(
            select(CreatorStadiumPricing.season_pass_price_coin).where(
                CreatorStadiumPricing.season_id == season_id,
                CreatorStadiumPricing.club_id == club_id,
                CreatorStadiumPricing.is_active.is_(True),
            )
        )
        if configured_price is not None:
            price_coin = self._normalize_amount(configured_price)
        else:
            price_coin = self._normalize_amount(
                max(MIN_SEASON_PASS_PRICE, Decimal(billable_matches) * SEASON_PASS_PRICE_PER_MATCH)
            )
        control_evaluation = self._evaluate_creator_purchase_controls(
            actor=actor,
            amount=price_coin,
            purchase_scope="season_pass",
            metadata_json={
                "season_id": season_id,
                "club_id": club_id,
                "scheduled_matches": billable_matches,
            },
        )
        creator_share = self._normalize_amount(price_coin * CREATOR_SEASON_PASS_SHARE)
        platform_share = self._normalize_amount(price_coin - creator_share)

        item = CreatorSeasonPass(
            user_id=actor.id,
            creator_user_id=beneficiary.creator_user_id,
            season_id=season_id,
            club_id=club_id,
            price_coin=price_coin,
            creator_share_coin=creator_share,
            platform_share_coin=platform_share,
            metadata_json={
                "scheduled_matches": billable_matches,
                "creator_league_only": True,
            },
        )
        self.session.add(item)
        self.session.flush()
        self._post_creator_transaction(
            actor=actor,
            total_amount=price_coin,
            creator_split={club_id: creator_share},
            platform_share=platform_share,
            creator_user_ids={club_id: beneficiary.creator_user_id},
            reference=f"creator-season-pass:{item.id}",
            description=f"Creator season pass for club {club_id}",
        )
        self._distribute_shareholder_revenue(
            actor=actor,
            club_id=club_id,
            creator_user_id=beneficiary.creator_user_id,
            source_type="season_pass",
            source_reference_id=item.id,
            eligible_revenue_coin=creator_share,
            season_id=season_id,
            competition_id=None,
            match_id=None,
            metadata_json={"scheduled_matches": billable_matches},
        )
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=item.id,
            metadata_json={"creator_season_pass_id": item.id},
        )
        return item

    def list_passes(self, *, actor: User) -> list[CreatorSeasonPass]:
        return list(
            self.session.scalars(
                select(CreatorSeasonPass)
                .where(CreatorSeasonPass.user_id == actor.id)
                .order_by(CreatorSeasonPass.created_at.desc())
            ).all()
        )

    def send_match_gift(
        self,
        *,
        actor: User,
        match_id: str,
        club_id: str,
        amount_coin: Decimal,
        gift_label: str,
        note: str | None = None,
    ) -> CreatorMatchGiftEvent:
        if not self._match_gifting_enabled():
            raise CreatorBroadcastError(
                "Creator League match gifting is currently disabled by admin policy.",
                reason="match_gifting_disabled",
            )
        context = self.get_match_context(match_id)
        beneficiary = None
        if club_id == context.match.home_club_id:
            beneficiary = context.home_beneficiary
        elif club_id == context.match.away_club_id:
            beneficiary = context.away_beneficiary
        if beneficiary is None:
            raise CreatorBroadcastError(
                "Match gifts must target one of the creator clubs in the selected Creator League match.",
                reason="gift_target_invalid",
            )
        if beneficiary.creator_user_id == actor.id:
            raise CreatorBroadcastError("Users cannot gift their own creator club.", reason="gift_self_target")

        gross_amount = self._normalize_amount(amount_coin)
        if gross_amount <= Decimal("0.0000"):
            raise CreatorBroadcastError("Gift amount must be positive.", reason="gift_amount_invalid")
        control_reference = f"creator-gift-control:{match_id}:{club_id}:{actor.id}:{generate_uuid()}"
        try:
            control_evaluation = SpendingControlService(self.session).evaluate_gift(
                event_type="creator_match_gift",
                control_scope="creator_match_gift",
                reference_key=control_reference,
                amount=gross_amount,
                ledger_unit=LedgerUnit.COIN,
                actor_user_id=actor.id,
                target_user_id=beneficiary.creator_user_id,
                metadata_json={
                    "match_id": match_id,
                    "club_id": club_id,
                    "gift_label": gift_label.strip(),
                },
            )
        except SpendingControlViolation as exc:
            raise CreatorBroadcastError(exc.detail, reason="spending_controls_blocked") from exc
        creator_share = self._normalize_amount(gross_amount * CREATOR_GIFT_SHARE)
        platform_share = self._normalize_amount(gross_amount - creator_share)
        item = CreatorMatchGiftEvent(
            season_id=context.season.id,
            competition_id=context.competition.id,
            match_id=context.match.id,
            sender_user_id=actor.id,
            recipient_creator_user_id=beneficiary.creator_user_id,
            club_id=club_id,
            gift_label=gift_label.strip(),
            gross_amount_coin=gross_amount,
            creator_share_coin=creator_share,
            platform_share_coin=platform_share,
            note=(note or "").strip() or None,
            metadata_json={"creator_league_only": True},
        )
        self.session.add(item)
        self.session.flush()
        self._post_creator_transaction(
            actor=actor,
            total_amount=gross_amount,
            creator_split={club_id: creator_share},
            platform_share=platform_share,
            creator_user_ids={club_id: beneficiary.creator_user_id},
            reference=f"creator-gift:{item.id}",
            description=f"Creator match gift for club {club_id}",
        )
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=item.id,
            metadata_json={"creator_match_gift_event_id": item.id},
        )
        self._distribute_shareholder_revenue(
            actor=actor,
            club_id=club_id,
            creator_user_id=beneficiary.creator_user_id,
            source_type="gifts",
            source_reference_id=item.id,
            eligible_revenue_coin=creator_share,
            season_id=context.season.id,
            competition_id=context.competition.id,
            match_id=context.match.id,
            metadata_json={"gift_label": item.gift_label},
        )
        return item

    def _ensure_default_mode_configs(self) -> None:
        existing = {
            item.mode_key: item
            for item in self.session.scalars(select(CreatorBroadcastModeConfig)).all()
        }
        changed = False
        for payload in self.DEFAULT_MODE_CONFIGS:
            item = existing.get(payload["mode_key"])
            if item is None:
                item = CreatorBroadcastModeConfig(**payload, metadata_json={})
                self.session.add(item)
                changed = True
                continue
            if item.name != payload["name"]:
                item.name = payload["name"]
                changed = True
            if item.description != payload["description"]:
                item.description = payload["description"]
                changed = True
            if item.min_duration_minutes != payload["min_duration_minutes"]:
                item.min_duration_minutes = payload["min_duration_minutes"]
                changed = True
            if item.max_duration_minutes != payload["max_duration_minutes"]:
                item.max_duration_minutes = payload["max_duration_minutes"]
                changed = True
            if self._normalize_amount(item.min_price_coin) != self._normalize_amount(payload["min_price_coin"]):
                item.min_price_coin = payload["min_price_coin"]
                changed = True
            if self._normalize_amount(item.max_price_coin) != self._normalize_amount(payload["max_price_coin"]):
                item.max_price_coin = payload["max_price_coin"]
                changed = True
            if not item.is_active:
                item.is_active = True
                changed = True
        if changed:
            self.session.flush()

    def _mode_for_duration(self, duration_minutes: int) -> CreatorBroadcastModeConfig:
        if duration_minutes < 10 or duration_minutes > 90:
            raise CreatorBroadcastError(
                "Creator broadcast duration must be between 10 and 90 minutes.",
                reason="duration_out_of_range",
            )
        configs = self.list_mode_configs()
        for item in configs:
            if duration_minutes <= item.max_duration_minutes:
                return item
        return configs[-1]

    def _calculate_price(self, config: CreatorBroadcastModeConfig, duration_minutes: int) -> Decimal:
        lower = config.min_duration_minutes
        upper = config.max_duration_minutes
        if upper <= lower:
            return self._normalize_amount(config.max_price_coin)
        clamped_duration = min(max(duration_minutes, lower), upper)
        span = Decimal(upper - lower)
        progress = Decimal(clamped_duration - lower) / span
        price_delta = Decimal(str(config.max_price_coin)) - Decimal(str(config.min_price_coin))
        return self._normalize_amount(Decimal(str(config.min_price_coin)) + (price_delta * progress))

    def _beneficiaries_for_clubs(self, club_ids: tuple[str, ...]) -> dict[str, CreatorBeneficiary]:
        rows = self.session.execute(
            select(CreatorSquad.club_id, CreatorProfile.user_id)
            .join(CreatorProfile, CreatorProfile.id == CreatorSquad.creator_profile_id)
            .where(CreatorSquad.club_id.in_(club_ids))
        ).all()
        return {
            str(club_id): CreatorBeneficiary(club_id=str(club_id), creator_user_id=str(creator_user_id))
            for club_id, creator_user_id in rows
        }

    def _creator_split(
        self,
        *,
        creator_total: Decimal,
        home_beneficiary: CreatorBeneficiary | None,
        away_beneficiary: CreatorBeneficiary | None,
    ) -> dict[str, Decimal]:
        active = [
            beneficiary
            for beneficiary in (home_beneficiary, away_beneficiary)
            if beneficiary is not None
        ]
        if not active or creator_total <= Decimal("0.0000"):
            return {}
        base_share = self._normalize_amount(creator_total / Decimal(len(active)))
        allocations = {beneficiary.club_id: base_share for beneficiary in active}
        remainder = self._normalize_amount(creator_total - sum(allocations.values(), Decimal("0.0000")))
        if remainder != Decimal("0.0000"):
            first_key = active[0].club_id
            allocations[first_key] = self._normalize_amount(allocations[first_key] + remainder)
        return allocations

    def _post_creator_transaction(
        self,
        *,
        actor: User,
        total_amount: Decimal,
        creator_split: dict[str, Decimal],
        platform_share: Decimal,
        reference: str,
        description: str,
        creator_user_ids: dict[str, str] | None = None,
    ) -> None:
        viewer_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        postings = [
            LedgerPosting(
                account=viewer_account,
                amount=-self._normalize_amount(total_amount),
                source_tag=LedgerSourceTag.VIDEO_VIEW_SPEND,
            )
        ]
        if creator_user_ids is None:
            creator_user_ids = {
                club_id: beneficiary.creator_user_id
                for club_id, beneficiary in self._beneficiaries_for_clubs(tuple(creator_split.keys())).items()
            }
        for club_id, amount in creator_split.items():
            normalized = self._normalize_amount(amount)
            if normalized <= Decimal("0.0000"):
                continue
            creator_user = self.session.get(User, creator_user_ids[club_id])
            if creator_user is None:
                continue
            creator_account = self.wallet_service.get_user_account(self.session, creator_user, LedgerUnit.COIN)
            postings.append(
                LedgerPosting(
                    account=creator_account,
                    amount=normalized,
                    source_tag=LedgerSourceTag.MATCH_VIEW_REVENUE,
                )
            )
        normalized_platform_share = self._normalize_amount(platform_share)
        if normalized_platform_share > Decimal("0.0000"):
            postings.append(
                LedgerPosting(
                    account=platform_account,
                    amount=normalized_platform_share,
                    source_tag=LedgerSourceTag.MATCH_VIEW_REVENUE,
                )
            )
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=postings,
                reason=LedgerEntryReason.ADJUSTMENT,
                reference=reference,
                description=description,
                actor=actor,
            )
        except InsufficientBalanceError as exc:
            raise CreatorBroadcastError(
                "Insufficient coin balance for this creator transaction.",
                reason="insufficient_balance",
            ) from exc

    def _evaluate_creator_purchase_controls(
        self,
        *,
        actor: User,
        amount: Decimal,
        purchase_scope: str,
        metadata_json: dict[str, object] | None = None,
    ):
        reference_key = f"creator-purchase-control:{purchase_scope}:{actor.id}:{generate_uuid()}"
        try:
            return SpendingControlService(self.session).evaluate_purchase(
                reference_key=reference_key,
                amount=amount,
                ledger_unit=LedgerUnit.COIN,
                actor_user_id=actor.id,
                purchase_scope=purchase_scope,
                metadata_json=metadata_json,
            )
        except SpendingControlViolation as exc:
            raise CreatorBroadcastError(exc.detail, reason="spending_controls_blocked") from exc

    def _distribute_shareholder_revenue(
        self,
        *,
        actor: User,
        club_id: str,
        creator_user_id: str,
        source_type: str,
        source_reference_id: str,
        eligible_revenue_coin: Decimal,
        season_id: str | None,
        competition_id: str | None,
        match_id: str | None,
        metadata_json: dict[str, object] | None = None,
    ) -> None:
        from backend.app.services.creator_share_market_service import CreatorClubShareMarketError, CreatorClubShareMarketService

        try:
            CreatorClubShareMarketService(
                self.session,
                wallet_service=self.wallet_service,
            ).distribute_creator_revenue(
                actor=actor,
                club_id=club_id,
                creator_user_id=creator_user_id,
                source_type=source_type,
                source_reference_id=source_reference_id,
                eligible_revenue_coin=eligible_revenue_coin,
                season_id=season_id,
                competition_id=competition_id,
                match_id=match_id,
                metadata_json=metadata_json,
            )
        except CreatorClubShareMarketError as exc:
            if exc.reason != "share_market_not_found":
                raise CreatorBroadcastError(exc.detail, reason=exc.reason) from exc

    def _is_creator_league_competition(self, competition: Competition) -> bool:
        metadata = competition.metadata_json or {}
        return (
            competition.source_type == CREATOR_LEAGUE_KEY
            or competition.competition_type == CREATOR_LEAGUE_KEY
            or bool(metadata.get("creator_league"))
        )

    def _creator_league_config(self) -> CreatorLeagueConfig | None:
        return self.session.scalar(
            select(CreatorLeagueConfig).where(CreatorLeagueConfig.league_key == CREATOR_LEAGUE_KEY)
        )

    def _broadcast_purchases_enabled(self) -> bool:
        config = self._creator_league_config()
        return True if config is None else bool(config.broadcast_purchases_enabled)

    def _season_pass_sales_enabled(self) -> bool:
        config = self._creator_league_config()
        return True if config is None else bool(config.season_pass_sales_enabled)

    def _match_gifting_enabled(self) -> bool:
        config = self._creator_league_config()
        return True if config is None else bool(config.match_gifting_enabled)

    @staticmethod
    def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


__all__ = [
    "CreatorBeneficiary",
    "CreatorBroadcastError",
    "CreatorBroadcastQuote",
    "CreatorBroadcastService",
    "CreatorMatchAccess",
    "CreatorMatchContext",
]
