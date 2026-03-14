from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.economy.schemas import (
    GiftCatalogItemUpsertRequest,
    ServicePricingRuleUpsertRequest,
    GiftComboRuleUpsertRequest,
    RevenueShareRuleUpsertRequest,
)
from backend.app.models.economy_config import GiftCatalogItem, ServicePricingRule
from backend.app.models.gift_combo_rule import GiftComboRule
from backend.app.models.revenue_share_rule import RevenueShareRule
from backend.app.models.user import User

DEFAULT_GIFTS: tuple[dict[str, object], ...] = (
    {
        "key": "cheer-burst",
        "display_name": "Cheer Burst",
        "tier": "standard",
        "fancoin_price": Decimal("25.0000"),
        "animation_key": "cheer_burst",
        "sound_key": "crowd_pop",
        "description": "Quick support pulse for a club, player, or creator stream.",
        "active": True,
    },
    {
        "key": "stadium-flare",
        "display_name": "Stadium Flare",
        "tier": "premium",
        "fancoin_price": Decimal("150.0000"),
        "animation_key": "stadium_flare",
        "sound_key": "flare_whoosh",
        "description": "Premium visual flare for big-match moments.",
        "active": True,
    },
    {
        "key": "trophy-rain",
        "display_name": "Trophy Rain",
        "tier": "legendary",
        "fancoin_price": Decimal("500.0000"),
        "animation_key": "trophy_rain",
        "sound_key": "trophy_shimmer",
        "description": "High-end celebration gift designed for finals and title-clinching nights.",
        "active": True,
    },
)

DEFAULT_SERVICE_PRICING: tuple[dict[str, object], ...] = (
    {
        "service_key": "premium-video-view",
        "title": "Premium Video View",
        "description": "Unlock premium match highlight or 3-5 minute cinematic replay package.",
        "price_coin": Decimal("2.5000"),
        "price_fancoin_equivalent": Decimal("250.0000"),
        "active": True,
    },
    {
        "service_key": "fast-match-entry",
        "title": "Fast Match Entry",
        "description": "Quick-entry competitive matchmaking surface.",
        "price_coin": Decimal("1.0000"),
        "price_fancoin_equivalent": Decimal("100.0000"),
        "active": True,
    },
    {
        "service_key": "stadium-upgrade-level-1",
        "title": "Stadium Upgrade Level 1",
        "description": "Base stadium upgrade from the default 5k capacity shell.",
        "price_coin": Decimal("50.0000"),
        "price_fancoin_equivalent": Decimal("5000.0000"),
        "active": True,
    },
)

DEFAULT_REVENUE_SHARE_RULES: tuple[dict[str, object], ...] = (
    {
        "rule_key": "gift-default",
        "scope": "gift",
        "title": "Gift Platform Rake",
        "description": "Default revenue split for gift transactions.",
        "platform_share_bps": 3000,
        "creator_share_bps": 0,
        "recipient_share_bps": None,
        "burn_bps": 0,
        "priority": 10,
        "active": True,
    },
    {
        "rule_key": "competition-reward-default",
        "scope": "competition_reward",
        "title": "Competition Reward Split",
        "description": "Default platform fee on competition rewards.",
        "platform_share_bps": 1000,
        "creator_share_bps": 0,
        "recipient_share_bps": None,
        "burn_bps": 0,
        "priority": 10,
        "active": True,
    },
)

DEFAULT_GIFT_COMBO_RULES: tuple[dict[str, object], ...] = (
    {
        "rule_key": "combo-streak-3",
        "title": "3 Gift Streak",
        "description": "Trigger a combo after 3 gifts to the same recipient within two minutes.",
        "min_combo_count": 3,
        "window_seconds": 120,
        "bonus_bps": 0,
        "priority": 10,
        "active": True,
    },
)


@dataclass(frozen=True, slots=True)
class RevenueSplit:
    scope: str
    rule_key: str | None
    gross_amount: Decimal
    platform_amount: Decimal
    recipient_amount: Decimal
    creator_amount: Decimal
    burn_amount: Decimal



@dataclass(slots=True)
class EconomyConfigService:
    session: Session

    def seed_defaults(self) -> None:
        existing_gifts = {item.key for item in self.session.scalars(select(GiftCatalogItem)).all()}
        for payload in DEFAULT_GIFTS:
            if payload["key"] in existing_gifts:
                continue
            self.session.add(GiftCatalogItem(**payload))

        existing_rules = {item.service_key for item in self.session.scalars(select(ServicePricingRule)).all()}
        for payload in DEFAULT_SERVICE_PRICING:
            if payload["service_key"] in existing_rules:
                continue
            self.session.add(ServicePricingRule(**payload))

        existing_revenue = {item.rule_key for item in self.session.scalars(select(RevenueShareRule)).all()}
        for payload in DEFAULT_REVENUE_SHARE_RULES:
            if payload["rule_key"] in existing_revenue:
                continue
            self.session.add(RevenueShareRule(**payload))

        existing_combo = {item.rule_key for item in self.session.scalars(select(GiftComboRule)).all()}
        for payload in DEFAULT_GIFT_COMBO_RULES:
            if payload["rule_key"] in existing_combo:
                continue
            self.session.add(GiftComboRule(**payload))
        self.session.flush()

    def list_gifts(self, *, active_only: bool = True) -> list[GiftCatalogItem]:
        statement = select(GiftCatalogItem).order_by(GiftCatalogItem.fancoin_price.asc(), GiftCatalogItem.display_name.asc())
        if active_only:
            statement = statement.where(GiftCatalogItem.active.is_(True))
        return list(self.session.scalars(statement).all())

    def list_service_pricing(self, *, active_only: bool = True) -> list[ServicePricingRule]:
        statement = select(ServicePricingRule).order_by(ServicePricingRule.service_key.asc())
        if active_only:
            statement = statement.where(ServicePricingRule.active.is_(True))
        return list(self.session.scalars(statement).all())

    def upsert_gift(self, *, actor: User, payload: GiftCatalogItemUpsertRequest) -> GiftCatalogItem:
        item = self.session.scalar(select(GiftCatalogItem).where(GiftCatalogItem.key == payload.key))
        if item is None:
            item = GiftCatalogItem(key=payload.key)
            self.session.add(item)
        item.display_name = payload.display_name
        item.tier = payload.tier
        item.fancoin_price = payload.fancoin_price
        item.animation_key = payload.animation_key
        item.sound_key = payload.sound_key
        item.description = payload.description
        item.active = payload.active
        item.updated_by_user_id = actor.id
        self.session.flush()
        return item

    def upsert_service_pricing(self, *, actor: User, payload: ServicePricingRuleUpsertRequest) -> ServicePricingRule:
        item = self.session.scalar(select(ServicePricingRule).where(ServicePricingRule.service_key == payload.service_key))
        if item is None:
            item = ServicePricingRule(service_key=payload.service_key)
            self.session.add(item)
        item.title = payload.title
        item.description = payload.description
        item.price_coin = payload.price_coin
        item.price_fancoin_equivalent = payload.price_fancoin_equivalent
        item.active = payload.active
        item.updated_by_user_id = actor.id
        self.session.flush()
        return item

    def list_revenue_share_rules(self, *, active_only: bool = True) -> list[RevenueShareRule]:
        statement = select(RevenueShareRule).order_by(RevenueShareRule.priority.desc(), RevenueShareRule.rule_key.asc())
        if active_only:
            statement = statement.where(RevenueShareRule.active.is_(True))
        return list(self.session.scalars(statement).all())

    def resolve_revenue_share_rule(self, *, scope: str) -> RevenueShareRule | None:
        statement = (
            select(RevenueShareRule)
            .where(RevenueShareRule.scope == scope, RevenueShareRule.active.is_(True))
            .order_by(RevenueShareRule.priority.desc(), RevenueShareRule.updated_at.desc())
        )
        return self.session.scalar(statement)

    def compute_revenue_split(
        self,
        *,
        scope: str,
        gross_amount: Decimal,
        fallback_platform_bps: int | None = None,
    ) -> RevenueSplit:
        gross = Decimal(str(gross_amount))
        rule = self.resolve_revenue_share_rule(scope=scope)
        if rule is None:
            platform_bps = int(fallback_platform_bps or 0)
            creator_bps = 0
            burn_bps = 0
            recipient_bps = max(0, 10_000 - platform_bps)
            rule_key = None
        else:
            platform_bps = int(rule.platform_share_bps or 0)
            creator_bps = int(rule.creator_share_bps or 0)
            burn_bps = int(rule.burn_bps or 0)
            if rule.recipient_share_bps is None:
                recipient_bps = max(0, 10_000 - platform_bps - creator_bps - burn_bps)
            else:
                recipient_bps = int(rule.recipient_share_bps)
                remainder = 10_000 - platform_bps - creator_bps - burn_bps
                if recipient_bps > remainder:
                    recipient_bps = max(0, remainder)
            rule_key = rule.rule_key

        quant = Decimal("0.0001")
        platform_amount = (gross * Decimal(platform_bps) / Decimal(10_000)).quantize(quant)
        creator_amount = (gross * Decimal(creator_bps) / Decimal(10_000)).quantize(quant)
        burn_amount = (gross * Decimal(burn_bps) / Decimal(10_000)).quantize(quant)
        recipient_amount = gross - platform_amount - creator_amount - burn_amount
        return RevenueSplit(
            scope=scope,
            rule_key=rule_key,
            gross_amount=gross.quantize(quant),
            platform_amount=platform_amount,
            recipient_amount=recipient_amount.quantize(quant),
            creator_amount=creator_amount,
            burn_amount=burn_amount,
        )

    def upsert_revenue_share_rule(self, *, actor: User, payload: RevenueShareRuleUpsertRequest) -> RevenueShareRule:
        item = self.session.scalar(select(RevenueShareRule).where(RevenueShareRule.rule_key == payload.rule_key))
        if item is None:
            item = RevenueShareRule(rule_key=payload.rule_key)
            self.session.add(item)
        item.scope = payload.scope
        item.title = payload.title
        item.description = payload.description
        item.platform_share_bps = payload.platform_share_bps
        item.creator_share_bps = payload.creator_share_bps
        item.recipient_share_bps = payload.recipient_share_bps
        item.burn_bps = payload.burn_bps
        item.priority = payload.priority
        item.active = payload.active
        item.updated_by_user_id = actor.id
        self.session.flush()
        return item

    def list_gift_combo_rules(self, *, active_only: bool = True) -> list[GiftComboRule]:
        statement = select(GiftComboRule).order_by(GiftComboRule.priority.desc(), GiftComboRule.min_combo_count.desc())
        if active_only:
            statement = statement.where(GiftComboRule.active.is_(True))
        return list(self.session.scalars(statement).all())

    def upsert_gift_combo_rule(self, *, actor: User, payload: GiftComboRuleUpsertRequest) -> GiftComboRule:
        item = self.session.scalar(select(GiftComboRule).where(GiftComboRule.rule_key == payload.rule_key))
        if item is None:
            item = GiftComboRule(rule_key=payload.rule_key)
            self.session.add(item)
        item.title = payload.title
        item.description = payload.description
        item.min_combo_count = payload.min_combo_count
        item.window_seconds = payload.window_seconds
        item.bonus_bps = payload.bonus_bps
        item.priority = payload.priority
        item.active = payload.active
        item.updated_by_user_id = actor.id
        self.session.flush()
        return item
