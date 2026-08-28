from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.community_engine.service import CommunityEngineError, CommunityEngineService
from app.economy.service import EconomyConfigService
from app.gift_engine.catalog import FOOTBALL_GIFT_CATALOG
from app.models.base import generate_uuid, utcnow
from app.models.community_engine import LiveThread, LiveThreadMessage, MessageVisibility, PrivateMessageParticipant
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.economy_config import GiftCatalogItem
from app.models.gift_transaction import GiftAbuseFlag, GiftStats
from app.models.gift_combo_event import GiftComboEvent
from app.models.gift_combo_rule import GiftComboRule
from app.models.gift_transaction import GiftTransaction
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.services.spending_control_service import SpendingControlService, SpendingControlViolation
from app.services.social_collusion_detection_service import SocialCollusionDetectionService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
MATCH_SCOPE_GIFT_WINDOW_SECONDS = 60
MATCH_SCOPE_GIFT_MAX_COUNT = 5


class GiftEngineError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class GiftEngineService:
    session: Session
    wallet_service: WalletService | None = None
    event_publisher: EventPublisher | None = None

    def __post_init__(self) -> None:
        if self.event_publisher is None:
            self.event_publisher = InMemoryEventPublisher()
        if self.wallet_service is None:
            self.wallet_service = WalletService(event_publisher=self.event_publisher)

    def _normalize_amount(self, amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)

    def _active_gift_rake_bps(self) -> int:
        rule = next(iter(AdminEngineService(self.session).list_reward_rules(active_only=True)), None)
        return int(rule.gift_platform_rake_bps if rule is not None else 3000)

    def _active_combo_rules(self) -> list[GiftComboRule]:
        return EconomyConfigService(self.session).list_gift_combo_rules(active_only=True)

    def ensure_football_gift_catalog(self) -> None:
        existing = {
            item.key: item
            for item in self.session.scalars(
                select(GiftCatalogItem).where(
                    GiftCatalogItem.key.in_([str(payload["key"]) for payload in FOOTBALL_GIFT_CATALOG])
                )
            ).all()
        }
        for payload in FOOTBALL_GIFT_CATALOG:
            item = existing.get(str(payload["key"]))
            if item is None:
                self.session.add(GiftCatalogItem(currency="credit", active=True, **payload))
                continue
            item.fallback_display_name = payload.get("fallback_display_name") or item.fallback_display_name
            item.rarity = str(payload.get("rarity") or item.rarity or payload.get("tier") or "common")
            item.currency = "credit"
            item.animation_key = str(payload.get("animation_key") or item.animation_key or "")
            item.sound_key = str(payload.get("sound_key") or item.sound_key or "")
            item.duration_ms = int(payload.get("duration_ms") or item.duration_ms or 2500)
            item.legal_status = str(payload.get("legal_status") or item.legal_status or "safe")
            item.sort_order = int(payload.get("sort_order") or item.sort_order or 0)
            item.is_award_pack = bool(payload.get("is_award_pack") or item.is_award_pack)
        self.session.flush()

    def list_catalog(self, *, active_only: bool = True, award_only: bool = False) -> list[GiftCatalogItem]:
        self.ensure_football_gift_catalog()
        statement = select(GiftCatalogItem).order_by(
            GiftCatalogItem.sort_order.asc(), GiftCatalogItem.fancoin_price.asc()
        )
        if active_only:
            statement = statement.where(GiftCatalogItem.active.is_(True))
        if award_only:
            statement = statement.where(GiftCatalogItem.is_award_pack.is_(True))
        return list(self.session.scalars(statement).all())

    def _combo_count(
        self,
        *,
        sender_id: str,
        recipient_id: str,
        gift_id: str,
        window_seconds: int,
    ) -> int:
        window_start = utcnow() - timedelta(seconds=window_seconds)
        count = self.session.scalar(
            select(func.count(GiftTransaction.id)).where(
                GiftTransaction.sender_user_id == sender_id,
                GiftTransaction.recipient_user_id == recipient_id,
                GiftTransaction.gift_catalog_item_id == gift_id,
                GiftTransaction.created_at >= window_start,
            )
        )
        return int(count or 0)

    def _select_combo_rule(
        self,
        *,
        sender_id: str,
        recipient_id: str,
        gift_id: str,
    ) -> tuple[GiftComboRule | None, int]:
        rules = self._active_combo_rules()
        if not rules:
            return None, 0
        for rule in rules:
            count = (
                self._combo_count(
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    gift_id=gift_id,
                    window_seconds=int(rule.window_seconds),
                )
                + 1
            )
            if count >= int(rule.min_combo_count):
                return rule, count
        return None, 0

    def _match_scope_gift_count(
        self,
        *,
        sender_id: str,
        recipient_id: str,
        source_scope: str,
        window_seconds: int,
    ) -> int:
        window_start = utcnow() - timedelta(seconds=window_seconds)
        count = self.session.scalar(
            select(func.count(GiftTransaction.id)).where(
                GiftTransaction.sender_user_id == sender_id,
                GiftTransaction.recipient_user_id == recipient_id,
                GiftTransaction.source_scope == source_scope,
                GiftTransaction.created_at >= window_start,
            )
        )
        return int(count or 0)

    def send_gift(
        self,
        *,
        sender: User,
        recipient_user_id: str | None = None,
        gift_key: str,
        quantity: Decimal,
        note: str | None = None,
        source_scope: str = "user_hosted",
        idempotency_key: str | None = None,
        chat_thread_id: str | None = None,
        discussion_thread_id: str | None = None,
        discussion_reply_id: str | None = None,
        match_id: str | None = None,
        competition_id: str | None = None,
    ) -> GiftTransaction:
        self.ensure_football_gift_catalog()
        normalized_idempotency_key = idempotency_key.strip() if idempotency_key else None
        if normalized_idempotency_key:
            existing_transaction = self.session.scalar(
                select(GiftTransaction).where(GiftTransaction.idempotency_key == normalized_idempotency_key)
            )
            if existing_transaction is not None:
                return existing_transaction

        resolved = self._resolve_recipient_context(
            sender=sender,
            recipient_user_id=recipient_user_id,
            chat_thread_id=chat_thread_id,
            discussion_thread_id=discussion_thread_id,
            discussion_reply_id=discussion_reply_id,
        )
        recipient = resolved["recipient"]
        recipient_type = str(resolved["recipient_type"])
        recipient_entity_id = str(resolved["recipient_entity_id"])
        chat_thread_id = resolved.get("chat_thread_id")
        discussion_thread_id = resolved.get("discussion_thread_id")
        discussion_reply_id = resolved.get("discussion_reply_id")

        assert isinstance(recipient, User)
        if recipient.id == sender.id:
            raise GiftEngineError("Users cannot send gifts to themselves.")

        normalized_scope = (source_scope or "user_hosted").strip().lower()
        if any(
            token in normalized_scope
            for token in {"gtex", "platform", "official", "national", "qualifier", "international"}
        ):
            normalized_scope = "gtex_competition"
        elif normalized_scope in {
            "user",
            "creator",
            "creator_hosted",
            "hosted",
            "hosted_competition",
            "club_competition",
            "area_competition",
            "state_competition",
            "community",
            "competition",
            "user_hosted",
        }:
            normalized_scope = "user_hosted"
        else:
            normalized_scope = "user_hosted"
        if normalized_scope == "gtex_competition":
            recent_pair_count = self._match_scope_gift_count(
                sender_id=sender.id,
                recipient_id=recipient.id,
                source_scope=normalized_scope,
                window_seconds=MATCH_SCOPE_GIFT_WINDOW_SECONDS,
            )
            if recent_pair_count >= MATCH_SCOPE_GIFT_MAX_COUNT:
                raise GiftEngineError(
                    "Match gifting is rate limited to 5 gifts per minute for each sender-recipient pair.",
                    reason="match_gift_rate_limited",
                )

        gift = self.session.scalar(
            select(GiftCatalogItem).where(GiftCatalogItem.key == gift_key, GiftCatalogItem.active.is_(True))
        )
        if gift is None:
            raise GiftEngineError("Gift catalog item was not found.")

        normalized_quantity = self._normalize_amount(quantity)
        if normalized_quantity <= Decimal("0.0000"):
            raise GiftEngineError("Gift quantity must be positive.")

        unit_price = self._normalize_amount(gift.fancoin_price)
        gross_amount = self._normalize_amount(unit_price * normalized_quantity)
        if gross_amount <= Decimal("0.0000"):
            raise GiftEngineError("Gift gross amount must be positive.")

        economy_service = EconomyConfigService(self.session)
        split = economy_service.compute_revenue_split(
            scope="gift",
            gross_amount=gross_amount,
            fallback_platform_bps=self._active_gift_rake_bps(),
        )
        platform_rake = self._normalize_amount(split.platform_amount)
        recipient_net = self._normalize_amount(split.recipient_amount)
        burn_amount = self._normalize_amount(split.burn_amount)

        combo_rule, combo_count = self._select_combo_rule(
            sender_id=sender.id,
            recipient_id=recipient.id,
            gift_id=gift.id,
        )
        combo_bonus = Decimal("0.0000")
        if combo_rule is not None and combo_rule.bonus_bps:
            combo_bonus = self._normalize_amount(gross_amount * Decimal(combo_rule.bonus_bps) / Decimal(10_000))
            if combo_bonus > platform_rake:
                combo_bonus = platform_rake
            platform_rake = self._normalize_amount(platform_rake - combo_bonus)
            recipient_net = self._normalize_amount(recipient_net + combo_bonus)

        ledger_unit = LedgerUnit.CREDIT if normalized_scope == "user_hosted" else LedgerUnit.COIN
        income_tag = (
            LedgerSourceTag.USER_HOSTED_GIFT_INCOME_FANCOIN
            if normalized_scope == "user_hosted"
            else LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
        )
        sender_account = self.wallet_service.get_user_account(self.session, sender, ledger_unit)
        recipient_account = self.wallet_service.get_user_account(self.session, recipient, ledger_unit)
        platform_account = self.wallet_service.ensure_platform_account(self.session, ledger_unit)

        if self.wallet_service.get_balance(self.session, sender_account) < gross_amount:
            unit_label = "FanCoin" if ledger_unit == LedgerUnit.CREDIT else "market balance"
            raise InsufficientBalanceError(f"Available {unit_label} balance is lower than the gift total.")

        control_reference = f"gift-control:{gift.key}:{sender.id}:{recipient.id}:{generate_uuid()}"
        try:
            control_evaluation = SpendingControlService(self.session).evaluate_gift(
                event_type="gift_send",
                control_scope=f"{normalized_scope}_gift",
                reference_key=control_reference,
                amount=gross_amount,
                ledger_unit=ledger_unit,
                actor_user_id=sender.id,
                target_user_id=recipient.id,
                metadata_json={
                    "gift_key": gift.key,
                    "quantity": str(normalized_quantity),
                    "source_scope": normalized_scope,
                },
            )
        except SpendingControlViolation as exc:
            raise GiftEngineError(exc.detail, reason="spending_controls_blocked") from exc

        postings = [
            LedgerPosting(account=sender_account, amount=-gross_amount, source_tag=income_tag),
            LedgerPosting(account=recipient_account, amount=recipient_net, source_tag=income_tag),
            LedgerPosting(account=platform_account, amount=platform_rake, source_tag=income_tag),
        ]
        if burn_amount > Decimal("0.0000"):
            burn_account = self.wallet_service.ensure_platform_burn_account(self.session, ledger_unit)
            postings.append(
                LedgerPosting(account=burn_account, amount=burn_amount, source_tag=LedgerSourceTag.GIFT_RAKE_BURN)
            )

        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=income_tag,
            reference=f"gift:{gift.key}:{sender.id}:{recipient.id}",
            description=f"Gift {gift.display_name} x{normalized_quantity} sent by {sender.username}",
            external_reference=f"gift:{gift.key}:{sender.id}:{recipient.id}",
            actor=sender,
            idempotency_key=normalized_idempotency_key,
            metadata={
                "gift_key": gift.key,
                "recipient_type": recipient_type,
                "recipient_entity_id": recipient_entity_id,
                "chat_thread_id": chat_thread_id,
                "discussion_thread_id": discussion_thread_id,
                "discussion_reply_id": discussion_reply_id,
                "match_id": match_id,
                "competition_id": competition_id,
            },
        )
        debit_entry_id = next(
            (entry.id for entry in entries if entry.account_id == sender_account.id and entry.amount < Decimal("0")),
            None,
        )
        credit_entry_id = next(
            (entry.id for entry in entries if entry.account_id == recipient_account.id and entry.amount > Decimal("0")),
            None,
        )
        platform_entry_id = next(
            (entry.id for entry in entries if entry.account_id == platform_account.id and entry.amount > Decimal("0")),
            None,
        )
        transaction = GiftTransaction(
            sender_user_id=sender.id,
            recipient_user_id=recipient.id,
            gift_catalog_item_id=gift.id,
            idempotency_key=normalized_idempotency_key,
            recipient_type=recipient_type,
            recipient_entity_id=recipient_entity_id,
            chat_thread_id=chat_thread_id,
            discussion_thread_id=discussion_thread_id,
            discussion_reply_id=discussion_reply_id,
            match_id=match_id,
            competition_id=competition_id,
            quantity=normalized_quantity,
            unit_price=unit_price,
            gross_amount=gross_amount,
            platform_rake_amount=platform_rake,
            recipient_net_amount=recipient_net,
            source_scope=normalized_scope,
            ledger_unit=ledger_unit,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            wallet_debit_ledger_id=debit_entry_id,
            wallet_credit_ledger_id=credit_entry_id,
            platform_fee_ledger_id=platform_entry_id,
            animation_key=gift.animation_key,
            sound_key=gift.sound_key,
            note=note,
            metadata_json={
                "gift_name": gift.display_name,
                "fallback_gift_name": gift.fallback_display_name,
                "rarity": gift.rarity,
                "currency_label": "Fan Coin" if ledger_unit == LedgerUnit.CREDIT else "GTEX Coin",
                "duration_ms": gift.duration_ms,
            },
        )
        self.session.add(transaction)
        self.session.flush()
        self._update_gift_stats(transaction=transaction, gift=gift, sender=sender)
        self._flag_reciprocal_gifting(transaction=transaction)
        SocialCollusionDetectionService(self.session).apply_after_gift(transaction=transaction)
        self._create_context_message(
            transaction=transaction,
            gift=gift,
            sender=sender,
            recipient=recipient,
        )
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=transaction.id,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            metadata_json={
                "gift_transaction_id": transaction.id,
                "combo_rule_key": combo_rule.rule_key if combo_rule is not None else None,
            },
        )
        ledger_transaction_id = entries[0].transaction_id if entries else None
        unit_label = "Fan Coin" if ledger_unit == LedgerUnit.CREDIT else "GTEX Coin"
        notification_metadata = {
            "gift_transaction_id": transaction.id,
            "gift_key": gift.key,
            "gift_display_name": gift.display_name,
            "sender_user_id": sender.id,
            "recipient_user_id": recipient.id,
            "quantity": str(normalized_quantity),
            "gross_amount": str(gross_amount),
            "recipient_net_amount": str(recipient_net),
            "ledger_unit": ledger_unit.value,
            "unit_label": unit_label,
            "source_scope": normalized_scope,
            "ledger_transaction_id": ledger_transaction_id,
        }
        sender_label = sender.display_name or sender.username or "A supporter"
        recipient_label = recipient.display_name or recipient.username or "recipient"
        self.session.add(
            NotificationRecord(
                user_id=recipient.id,
                topic="gift",
                template_key="GIFT_RECEIVED",
                resource_type="gift_transaction",
                resource_id=transaction.id,
                message=f"{sender_label} sent you {gift.display_name} worth {recipient_net} {unit_label}.",
                metadata_json=notification_metadata,
            )
        )
        self.session.add(
            NotificationRecord(
                user_id=sender.id,
                topic="gift",
                template_key="GIFT_SENT",
                resource_type="gift_transaction",
                resource_id=transaction.id,
                message=f"Gift sent: {gift.display_name} to {recipient_label} for {gross_amount} {unit_label}.",
                metadata_json=notification_metadata,
            )
        )
        if burn_amount > Decimal("0.0000"):
            burn_event = EconomyBurnEvent(
                user_id=sender.id,
                source_type="gift",
                source_id=transaction.id,
                amount=burn_amount,
                unit=ledger_unit,
                reason="gift_burn",
                ledger_transaction_id=ledger_transaction_id,
                metadata_json={"rule_key": split.rule_key or "fallback"},
            )
            self.session.add(burn_event)
        if combo_rule is not None:
            combo_event = GiftComboEvent(
                gift_transaction_id=transaction.id,
                sender_user_id=sender.id,
                recipient_user_id=recipient.id,
                gift_catalog_item_id=gift.id,
                combo_rule_id=combo_rule.id,
                combo_rule_key=combo_rule.rule_key,
                combo_count=combo_count,
                window_seconds=combo_rule.window_seconds,
                bonus_bps=combo_rule.bonus_bps,
                bonus_amount=combo_bonus,
            )
            self.session.add(combo_event)
        self.event_publisher.publish(
            DomainEvent(
                name="gift_sent",
                payload={
                    "gift_transaction_id": transaction.id,
                    "sender_user_id": sender.id,
                    "recipient_user_id": recipient.id,
                    "gift_key": gift.key,
                    "gift_name": gift.display_name,
                    "fallback_gift_name": gift.fallback_display_name,
                    "rarity": gift.rarity,
                    "quantity": str(normalized_quantity),
                    "gross_amount": str(gross_amount),
                    "ledger_unit": ledger_unit.value,
                    "currency_label": unit_label,
                    "source_scope": normalized_scope,
                    "animation_key": gift.animation_key,
                    "sound_key": gift.sound_key,
                    "chat_thread_id": chat_thread_id,
                    "discussion_thread_id": discussion_thread_id,
                    "discussion_reply_id": discussion_reply_id,
                    "match_id": match_id,
                    "competition_id": competition_id,
                    "transaction_id": entries[0].transaction_id if entries else None,
                },
            )
        )
        return transaction

    def _resolve_recipient_context(
        self,
        *,
        sender: User,
        recipient_user_id: str | None,
        chat_thread_id: str | None,
        discussion_thread_id: str | None,
        discussion_reply_id: str | None,
    ) -> dict[str, object]:
        resolved_discussion_thread_id = discussion_thread_id
        if discussion_reply_id:
            reply = self.session.get(LiveThreadMessage, discussion_reply_id)
            if reply is None:
                raise GiftEngineError("Discussion reply was not found.")
            resolved_discussion_thread_id = reply.thread_id
            recipient_user_id = recipient_user_id or reply.author_user_id
            recipient_type = "discussion_reply"
            recipient_entity_id = reply.id
        elif discussion_thread_id:
            thread = self.session.get(LiveThread, discussion_thread_id)
            if thread is None or thread.thread_type != "discussion" or thread.created_by_user_id is None:
                raise GiftEngineError("Discussion thread was not found.")
            recipient_user_id = recipient_user_id or thread.created_by_user_id
            recipient_type = "discussion_thread"
            recipient_entity_id = thread.id
        elif chat_thread_id and recipient_user_id is None:
            participants = self.session.scalars(
                select(PrivateMessageParticipant).where(PrivateMessageParticipant.thread_id == chat_thread_id)
            ).all()
            other_participants = [item.user_id for item in participants if item.user_id != sender.id]
            if len(other_participants) != 1:
                raise GiftEngineError("Gift recipient is required for this chat thread.")
            recipient_user_id = other_participants[0]
            recipient_type = "chat_thread"
            recipient_entity_id = chat_thread_id
        else:
            recipient_type = "user"
            recipient_entity_id = recipient_user_id or ""

        if not recipient_user_id:
            raise GiftEngineError("Gift recipient is required.")
        recipient = self.session.get(User, recipient_user_id)
        if recipient is None or not recipient.is_active:
            raise GiftEngineError("Recipient user was not found.")
        return {
            "recipient": recipient,
            "recipient_type": recipient_type,
            "recipient_entity_id": recipient_entity_id or recipient.id,
            "chat_thread_id": chat_thread_id,
            "discussion_thread_id": resolved_discussion_thread_id,
            "discussion_reply_id": discussion_reply_id,
        }

    def _update_gift_stats(self, *, transaction: GiftTransaction, gift: GiftCatalogItem, sender: User) -> None:
        targets = [("user", transaction.recipient_user_id)]
        if transaction.recipient_type != "user" and transaction.recipient_entity_id:
            targets.append((transaction.recipient_type, transaction.recipient_entity_id))
        for entity_type, entity_id in targets:
            stats = self.session.scalar(
                select(GiftStats).where(GiftStats.entity_type == entity_type, GiftStats.entity_id == entity_id)
            )
            if stats is None:
                stats = GiftStats(entity_type=entity_type, entity_id=entity_id)
                self.session.add(stats)
                self.session.flush()
            stats.total_gifts_received += 1
            stats.total_fan_coin_received = self._normalize_amount(
                Decimal(stats.total_fan_coin_received) + Decimal(transaction.recipient_net_amount)
            )
            stats.top_gift_code = gift.key
            if gift.rarity == "mythic":
                stats.mythic_gifts_received += 1
            if entity_type == "user":
                sender_count = self.session.scalar(
                    select(func.count(func.distinct(GiftTransaction.sender_user_id))).where(
                        GiftTransaction.recipient_user_id == entity_id
                    )
                )
            else:
                sender_count = self.session.scalar(
                    select(func.count(func.distinct(GiftTransaction.sender_user_id))).where(
                        GiftTransaction.recipient_type == entity_type,
                        GiftTransaction.recipient_entity_id == entity_id,
                    )
                )
            stats.total_unique_senders = max(int(sender_count or 0), 1 if sender.id else 0)
        self.session.flush()

    def _flag_reciprocal_gifting(self, *, transaction: GiftTransaction) -> None:
        reciprocal = self.session.scalar(
            select(GiftTransaction.id).where(
                GiftTransaction.sender_user_id == transaction.recipient_user_id,
                GiftTransaction.recipient_user_id == transaction.sender_user_id,
                GiftTransaction.created_at >= utcnow() - timedelta(days=7),
            )
        )
        if reciprocal is None:
            return
        transaction.abuse_status = "review"
        flag_key = f"wash-gift:{transaction.sender_user_id}:{transaction.recipient_user_id}:{transaction.id}"
        existing = self.session.scalar(select(GiftAbuseFlag).where(GiftAbuseFlag.flag_key == flag_key))
        if existing is None:
            self.session.add(
                GiftAbuseFlag(
                    flag_key=flag_key,
                    sender_user_id=transaction.sender_user_id,
                    recipient_type=transaction.recipient_type,
                    recipient_id=transaction.recipient_entity_id or transaction.recipient_user_id,
                    gift_transaction_id=transaction.id,
                    flag_type="reciprocal_gifting",
                    severity="medium",
                    description="Reciprocal gifting detected within a short review window.",
                    metadata_json={"reciprocal_transaction_id": reciprocal},
                )
            )
        self.session.flush()

    def _create_context_message(
        self,
        *,
        transaction: GiftTransaction,
        gift: GiftCatalogItem,
        sender: User,
        recipient: User,
    ) -> None:
        sender_label = sender.display_name or sender.username or "A supporter"
        recipient_label = recipient.display_name or recipient.username or "recipient"
        body = f"{sender_label} sent {gift.display_name} to {recipient_label}."
        metadata = {
            "kind": "gift",
            "gift_transaction_id": transaction.id,
            "gift_key": gift.key,
            "gift_name": gift.display_name,
            "fallback_gift_name": gift.fallback_display_name,
            "rarity": gift.rarity,
            "animation_key": gift.animation_key,
            "sound_key": gift.sound_key,
        }
        if transaction.chat_thread_id:
            try:
                CommunityEngineService(self.session).post_private_message(
                    actor=sender,
                    thread_id=transaction.chat_thread_id,
                    body=body,
                    metadata_json=metadata,
                )
            except CommunityEngineError:
                return
        if transaction.discussion_thread_id:
            thread = self.session.get(LiveThread, transaction.discussion_thread_id)
            if thread is None:
                return
            message = LiveThreadMessage(
                thread_id=thread.id,
                author_user_id=sender.id,
                parent_message_id=transaction.discussion_reply_id,
                message_type="gift",
                body=body,
                visibility=MessageVisibility.PUBLIC,
                metadata_json=metadata,
            )
            self.session.add(message)
            thread.last_message_at = utcnow()
            thread.trend_score += 1
            self.session.flush()

    def list_transactions_for_user(self, *, user: User, limit: int = 50) -> list[GiftTransaction]:
        stmt = (
            select(GiftTransaction)
            .where(or_(GiftTransaction.sender_user_id == user.id, GiftTransaction.recipient_user_id == user.id))
            .order_by(GiftTransaction.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def summary_for_user(self, *, user: User) -> dict[str, Decimal | list[GiftTransaction]]:
        sent_total = self._normalize_amount(
            self.session.scalar(
                select(func.coalesce(func.sum(GiftTransaction.gross_amount), 0)).where(
                    GiftTransaction.sender_user_id == user.id
                )
            )
            or 0
        )
        received_total = self._normalize_amount(
            self.session.scalar(
                select(func.coalesce(func.sum(GiftTransaction.recipient_net_amount), 0)).where(
                    GiftTransaction.recipient_user_id == user.id
                )
            )
            or 0
        )
        rake_total = self._normalize_amount(
            self.session.scalar(
                select(func.coalesce(func.sum(GiftTransaction.platform_rake_amount), 0)).where(
                    GiftTransaction.sender_user_id == user.id
                )
            )
            or 0
        )
        return {
            "sent_total": sent_total,
            "received_total": received_total,
            "rake_total": rake_total,
            "recent_transactions": self.list_transactions_for_user(user=user, limit=10),
        }

    def list_combo_events_for_user(self, *, user: User, role: str = "sender", limit: int = 50) -> list[GiftComboEvent]:
        if role == "recipient":
            stmt = select(GiftComboEvent).where(GiftComboEvent.recipient_user_id == user.id)
        else:
            stmt = select(GiftComboEvent).where(GiftComboEvent.sender_user_id == user.id)
        stmt = stmt.order_by(GiftComboEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def combo_summary_for_user(
        self, *, user: User, role: str = "sender"
    ) -> dict[str, Decimal | int | list[GiftComboEvent]]:
        if role == "recipient":
            base = GiftComboEvent.recipient_user_id == user.id
        else:
            base = GiftComboEvent.sender_user_id == user.id
        total_combos = int(self.session.scalar(select(func.count(GiftComboEvent.id)).where(base)) or 0)
        total_bonus = self._normalize_amount(
            self.session.scalar(select(func.coalesce(func.sum(GiftComboEvent.bonus_amount), 0)).where(base)) or 0
        )
        recent = self.list_combo_events_for_user(user=user, role=role, limit=10)
        return {
            "total_combos": total_combos,
            "total_bonus_amount": total_bonus,
            "recent_combos": recent,
        }
