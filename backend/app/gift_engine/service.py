from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.admin_engine.service import AdminEngineService
from backend.app.economy.service import EconomyConfigService
from backend.app.models.base import generate_uuid, utcnow
from backend.app.models.economy_burn_event import EconomyBurnEvent
from backend.app.models.economy_config import GiftCatalogItem
from backend.app.models.gift_combo_event import GiftComboEvent
from backend.app.models.gift_combo_rule import GiftComboRule
from backend.app.models.gift_transaction import GiftTransaction
from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from backend.app.services.spending_control_service import SpendingControlService, SpendingControlViolation
from backend.app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal('0.0001')


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
            count = self._combo_count(
                sender_id=sender_id,
                recipient_id=recipient_id,
                gift_id=gift_id,
                window_seconds=int(rule.window_seconds),
            ) + 1
            if count >= int(rule.min_combo_count):
                return rule, count
        return None, 0

    def send_gift(
        self,
        *,
        sender: User,
        recipient_user_id: str,
        gift_key: str,
        quantity: Decimal,
        note: str | None = None,
        source_scope: str = "user_hosted",
    ) -> GiftTransaction:
        recipient = self.session.get(User, recipient_user_id)
        if recipient is None or not recipient.is_active:
            raise GiftEngineError('Recipient user was not found.')
        if recipient.id == sender.id:
            raise GiftEngineError('Users cannot send gifts to themselves.')

        normalized_scope = (source_scope or "user_hosted").strip().lower()
        if normalized_scope in {"gtex", "gtex_platform", "gtex_competition"}:
            normalized_scope = "gtex_competition"
        if normalized_scope not in {"user_hosted", "gtex_competition"}:
            raise GiftEngineError("Gift source scope must be user_hosted or gtex_competition.")

        gift = self.session.scalar(select(GiftCatalogItem).where(GiftCatalogItem.key == gift_key, GiftCatalogItem.active.is_(True)))
        if gift is None:
            raise GiftEngineError('Gift catalog item was not found.')

        normalized_quantity = self._normalize_amount(quantity)
        if normalized_quantity <= Decimal('0.0000'):
            raise GiftEngineError('Gift quantity must be positive.')

        unit_price = self._normalize_amount(gift.fancoin_price)
        gross_amount = self._normalize_amount(unit_price * normalized_quantity)
        if gross_amount <= Decimal('0.0000'):
            raise GiftEngineError('Gift gross amount must be positive.')

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
            postings.append(LedgerPosting(account=burn_account, amount=burn_amount, source_tag=LedgerSourceTag.GIFT_RAKE_BURN))

        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=income_tag,
            reference=f'gift:{gift.key}:{sender.id}:{recipient.id}',
            description=f'Gift {gift.display_name} x{normalized_quantity} sent by {sender.username}',
            external_reference=f'gift:{gift.key}:{sender.id}:{recipient.id}',
            actor=sender,
        )
        transaction = GiftTransaction(
            sender_user_id=sender.id,
            recipient_user_id=recipient.id,
            gift_catalog_item_id=gift.id,
            quantity=normalized_quantity,
            unit_price=unit_price,
            gross_amount=gross_amount,
            platform_rake_amount=platform_rake,
            recipient_net_amount=recipient_net,
            source_scope=normalized_scope,
            ledger_unit=ledger_unit,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            note=note,
        )
        self.session.add(transaction)
        self.session.flush()
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=transaction.id,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            metadata_json={
                "gift_transaction_id": transaction.id,
                "combo_rule_key": combo_rule.rule_key if combo_rule is not None else None,
            },
        )
        if burn_amount > Decimal("0.0000"):
            burn_event = EconomyBurnEvent(
                user_id=sender.id,
                source_type="gift",
                source_id=transaction.id,
                amount=burn_amount,
                unit=LedgerUnit.CREDIT,
                reason="gift_burn",
                ledger_transaction_id=entries[0].transaction_id if entries else None,
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
                    "quantity": str(normalized_quantity),
                    "gross_amount": str(gross_amount),
                    "ledger_unit": ledger_unit.value,
                    "source_scope": normalized_scope,
                    "transaction_id": entries[0].transaction_id if entries else None,
                },
            )
        )
        return transaction

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
            self.session.scalar(select(func.coalesce(func.sum(GiftTransaction.gross_amount), 0)).where(GiftTransaction.sender_user_id == user.id)) or 0
        )
        received_total = self._normalize_amount(
            self.session.scalar(select(func.coalesce(func.sum(GiftTransaction.recipient_net_amount), 0)).where(GiftTransaction.recipient_user_id == user.id)) or 0
        )
        rake_total = self._normalize_amount(
            self.session.scalar(select(func.coalesce(func.sum(GiftTransaction.platform_rake_amount), 0)).where(GiftTransaction.sender_user_id == user.id)) or 0
        )
        return {
            'sent_total': sent_total,
            'received_total': received_total,
            'rake_total': rake_total,
            'recent_transactions': self.list_transactions_for_user(user=user, limit=10),
        }

    def list_combo_events_for_user(self, *, user: User, role: str = "sender", limit: int = 50) -> list[GiftComboEvent]:
        if role == "recipient":
            stmt = select(GiftComboEvent).where(GiftComboEvent.recipient_user_id == user.id)
        else:
            stmt = select(GiftComboEvent).where(GiftComboEvent.sender_user_id == user.id)
        stmt = stmt.order_by(GiftComboEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def combo_summary_for_user(self, *, user: User, role: str = "sender") -> dict[str, Decimal | int | list[GiftComboEvent]]:
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
