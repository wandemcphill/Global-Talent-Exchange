from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.core.events import DomainEvent
from app.economy.conversion_service import EconomicConversionError, FanCoinGiftConversionService
from app.economy.economic_policy import compute_gift_split
from app.gift_engine.service import (
    MATCH_SCOPE_GIFT_MAX_COUNT,
    MATCH_SCOPE_GIFT_WINDOW_SECONDS,
    GiftEngineError,
    GiftEngineService as LegacyGiftEngineService,
)
from app.models.base import generate_uuid
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.economy_config import GiftCatalogItem
from app.models.gift_combo_event import GiftComboEvent
from app.models.gift_transaction import GiftTransaction
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.models.wallet import LedgerEntry, LedgerUnit
from app.services.social_collusion_detection_service import SocialCollusionDetectionService
from app.services.spending_control_service import SpendingControlService, SpendingControlViolation
from app.wallets.service import InsufficientBalanceError


class CanonicalGiftEngineService(LegacyGiftEngineService):
    """Canonical gift accounting: FanCoin is spent and the recipient receives GTEX Coin."""

    @staticmethod
    def _normalize_scope(source_scope: str | None) -> str:
        normalized = (source_scope or "user_hosted").strip().lower()
        if any(
            token in normalized for token in {"gtex", "platform", "official", "national", "qualifier", "international"}
        ):
            return "gtex_competition"
        if normalized in {
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
            return "user_hosted"
        return "user_hosted"

    def send_gift(self, *, sender: User, **kwargs: Any):  # type: ignore[override]
        requested_scope = self._normalize_scope(kwargs.get("source_scope"))
        recipient_user_id = kwargs.get("recipient_user_id")
        self.ensure_football_gift_catalog()
        normalized_idempotency_key = kwargs.get("idempotency_key")
        normalized_idempotency_key = normalized_idempotency_key.strip() if normalized_idempotency_key else None
        if normalized_idempotency_key:
            existing_transaction = self.session.scalar(
                select(GiftTransaction).where(GiftTransaction.idempotency_key == normalized_idempotency_key)
            )
            if existing_transaction is not None:
                return existing_transaction

        resolved = self._resolve_recipient_context(
            sender=sender,
            recipient_user_id=recipient_user_id,
            chat_thread_id=kwargs.get("chat_thread_id"),
            discussion_thread_id=kwargs.get("discussion_thread_id"),
            discussion_reply_id=kwargs.get("discussion_reply_id"),
        )
        recipient = resolved["recipient"]
        recipient_type = str(resolved["recipient_type"])
        recipient_entity_id = str(resolved["recipient_entity_id"])
        chat_thread_id = resolved.get("chat_thread_id")
        discussion_thread_id = resolved.get("discussion_thread_id")
        discussion_reply_id = resolved.get("discussion_reply_id")
        if not isinstance(recipient, User):
            raise GiftEngineError("Gift recipient could not be resolved.")
        if recipient.id == sender.id:
            raise GiftEngineError("Users cannot send gifts to themselves.")

        if requested_scope == "gtex_competition":
            # This anti-abuse control lived only in the legacy send_gift() this
            # class overrides. Overriding the method dropped the check entirely
            # rather than inheriting it, silently disabling match-scope gift
            # rate limiting once the canonical conversion path became the
            # runtime entrypoint.
            recent_pair_count = self._match_scope_gift_count(
                sender_id=sender.id,
                recipient_id=recipient.id,
                source_scope=requested_scope,
                window_seconds=MATCH_SCOPE_GIFT_WINDOW_SECONDS,
            )
            if recent_pair_count >= MATCH_SCOPE_GIFT_MAX_COUNT:
                raise GiftEngineError(
                    "Match gifting is rate limited to 5 gifts per minute for each sender-recipient pair.",
                    reason="match_gift_rate_limited",
                )

        gift_key = str(kwargs.get("gift_key") or "").strip()
        gift = self.session.scalar(
            select(GiftCatalogItem).where(
                GiftCatalogItem.key == gift_key,
                GiftCatalogItem.active.is_(True),
            )
        )
        if gift is None:
            raise GiftEngineError("Gift catalog item was not found.")

        normalized_quantity = self._normalize_amount(kwargs.get("quantity"))
        if normalized_quantity <= Decimal("0.0000"):
            raise GiftEngineError("Gift quantity must be positive.")
        unit_price = self._normalize_amount(gift.fancoin_price)
        gross_amount = self._normalize_amount(unit_price * normalized_quantity)
        if gross_amount <= Decimal("0.0000"):
            raise GiftEngineError("Gift gross amount must be positive.")

        split = compute_gift_split(self.session, gross_amount)
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

        source_account = self.wallet_service.get_user_account(self.session, sender, LedgerUnit.CREDIT)
        if self.wallet_service.get_balance(self.session, source_account) < gross_amount:
            raise InsufficientBalanceError("Available FanCoin balance is lower than the gift total.")

        control_reference = f"gift-control:{gift.key}:{sender.id}:{recipient.id}:{generate_uuid()}"
        try:
            control_evaluation = SpendingControlService(self.session).evaluate_gift(
                event_type="gift_send",
                control_scope=f"{requested_scope}_gift",
                reference_key=control_reference,
                amount=gross_amount,
                ledger_unit=LedgerUnit.CREDIT,
                actor_user_id=sender.id,
                target_user_id=recipient.id,
                metadata_json={
                    "gift_key": gift.key,
                    "quantity": str(normalized_quantity),
                    "source_scope": requested_scope,
                    "currency": "fancoin",
                },
            )
        except SpendingControlViolation as exc:
            raise GiftEngineError(exc.detail, reason="spending_controls_blocked") from exc

        transaction = GiftTransaction(
            id=generate_uuid(),
            sender_user_id=sender.id,
            recipient_user_id=recipient.id,
            gift_catalog_item_id=gift.id,
            idempotency_key=normalized_idempotency_key,
            recipient_type=recipient_type,
            recipient_entity_id=recipient_entity_id,
            chat_thread_id=chat_thread_id,
            discussion_thread_id=discussion_thread_id,
            discussion_reply_id=discussion_reply_id,
            match_id=kwargs.get("match_id"),
            competition_id=kwargs.get("competition_id"),
            quantity=normalized_quantity,
            unit_price=unit_price,
            gross_amount=gross_amount,
            platform_rake_amount=platform_rake,
            recipient_net_amount=recipient_net,
            source_scope=requested_scope,
            ledger_unit=LedgerUnit.COIN,
            source_ledger_unit=LedgerUnit.CREDIT,
            destination_ledger_unit=LedgerUnit.COIN,
            conversion_rate=Decimal("1"),
            animation_key=gift.animation_key,
            sound_key=gift.sound_key,
            note=kwargs.get("note"),
            metadata_json={
                "gift_name": gift.display_name,
                "fallback_gift_name": gift.fallback_display_name,
                "rarity": gift.rarity,
                "currency_label": "GTEX Coin",
                "duration_ms": gift.duration_ms,
                "currency_semantics": "fan_coin_gift_converted_to_gtex_coin",
                "source_ledger_unit": LedgerUnit.CREDIT.value,
                "destination_ledger_unit": LedgerUnit.COIN.value,
                "fee_policy_rule_key": split.rule_key,
                "fee_policy_version": split.policy_version,
            },
        )
        self.session.add(transaction)
        self.session.flush()

        conversion_key = f"gift-conversion:{transaction.id}"
        try:
            conversion = FanCoinGiftConversionService(self.session, wallet_service=self.wallet_service).convert(
                source_user_id=sender.id,
                recipient_user_id=recipient.id,
                gross_fancoin=gross_amount,
                platform_fee_fancoin=platform_rake,
                destination_coin_amount=recipient_net,
                burn_fancoin=burn_amount,
                conversion_key=conversion_key,
                gift_transaction_id=transaction.id,
                fee_rule_key=split.rule_key,
                fee_rule_version=split.policy_version,
                idempotency_key=conversion_key,
                metadata={
                    "gift_key": gift.key,
                    "source_scope": requested_scope,
                    "quantity": str(normalized_quantity),
                },
            )
        except EconomicConversionError as exc:
            raise GiftEngineError(str(exc), reason="gift_conversion_failed") from exc

        if conversion.status.value != "settled":
            raise GiftEngineError("Gift conversion did not settle atomically.", reason="gift_conversion_unsettled")

        ledger_transaction_id = conversion.source_ledger_transaction_id
        if not ledger_transaction_id:
            raise GiftEngineError(
                "Gift conversion completed without a ledger transaction.",
                reason="gift_conversion_missing_ledger",
            )
        ledger_entries = self.session.scalars(
            select(LedgerEntry).where(LedgerEntry.transaction_id == ledger_transaction_id)
        ).all()
        debit_entry = next(
            (entry for entry in ledger_entries if entry.account_id == source_account.id and entry.amount < 0),
            None,
        )
        destination_account = self.wallet_service.get_user_account(self.session, recipient, LedgerUnit.COIN)
        credit_entry = next(
            (entry for entry in ledger_entries if entry.account_id == destination_account.id and entry.amount > 0),
            None,
        )
        platform_fee_account = self.wallet_service.ensure_named_system_account(
            self.session,
            code="platform:credit:gift_conversion_fee_revenue",
            label="Platform FanCoin Gift Conversion Fee Revenue",
            unit=LedgerUnit.CREDIT,
            allow_negative=False,
        )
        platform_fee_entry = next(
            (entry for entry in ledger_entries if entry.account_id == platform_fee_account.id and entry.amount > 0),
            None,
        )

        transaction.economic_conversion_id = conversion.id
        transaction.ledger_transaction_id = ledger_transaction_id
        transaction.wallet_debit_ledger_id = debit_entry.id if debit_entry else None
        transaction.wallet_credit_ledger_id = credit_entry.id if credit_entry else None
        transaction.platform_fee_ledger_id = platform_fee_entry.id if platform_fee_entry else None
        transaction.metadata_json = {
            **(transaction.metadata_json or {}),
            "conversion_id": conversion.id,
            "conversion_source_amount": str(conversion.source_amount),
            "conversion_destination_amount": str(conversion.destination_amount),
            "conversion_fee_amount": str(conversion.platform_fee_amount),
            "ledger_transaction_id": ledger_transaction_id,
            "fee_policy_rule_key": conversion.fee_rule_key,
            "fee_policy_version": conversion.fee_rule_version,
        }
        self.session.flush()

        self._update_gift_stats(transaction=transaction, gift=gift, sender=sender)
        self._flag_reciprocal_gifting(transaction=transaction)
        SocialCollusionDetectionService(self.session).apply_after_gift(transaction=transaction)
        self._create_context_message(transaction=transaction, gift=gift, sender=sender, recipient=recipient)
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=transaction.id,
            ledger_transaction_id=ledger_transaction_id,
            metadata_json={
                "gift_transaction_id": transaction.id,
                "combo_rule_key": combo_rule.rule_key if combo_rule is not None else None,
            },
        )

        notification_metadata = {
            "gift_transaction_id": transaction.id,
            "gift_key": gift.key,
            "gift_display_name": gift.display_name,
            "sender_user_id": sender.id,
            "recipient_user_id": recipient.id,
            "quantity": str(normalized_quantity),
            "gross_amount": str(gross_amount),
            "recipient_net_amount": str(recipient_net),
            "ledger_unit": LedgerUnit.COIN.value,
            "source_ledger_unit": LedgerUnit.CREDIT.value,
            "destination_ledger_unit": LedgerUnit.COIN.value,
            "unit_label": "GTEX Coin",
            "source_scope": requested_scope,
            "ledger_transaction_id": ledger_transaction_id,
            "economic_conversion_id": conversion.id,
            "fee_policy_rule_key": split.rule_key,
            "fee_policy_version": split.policy_version,
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
                message=f"{sender_label} sent you {gift.display_name} worth {recipient_net} GTEX Coin.",
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
                message=f"Gift sent: {gift.display_name} to {recipient_label} for {gross_amount} FanCoin.",
                metadata_json=notification_metadata,
            )
        )
        if burn_amount > Decimal("0.0000"):
            self.session.add(
                EconomyBurnEvent(
                    user_id=sender.id,
                    source_type="gift",
                    source_id=transaction.id,
                    amount=burn_amount,
                    unit=LedgerUnit.CREDIT,
                    reason="gift_burn",
                    ledger_transaction_id=ledger_transaction_id,
                    metadata_json={"rule_key": split.rule_key or "fallback"},
                )
            )
        if combo_rule is not None:
            self.session.add(
                GiftComboEvent(
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
            )
        event = DomainEvent(
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
                "ledger_unit": LedgerUnit.COIN.value,
                "currency_label": "GTEX Coin",
                "source_scope": requested_scope,
                "animation_key": gift.animation_key,
                "sound_key": gift.sound_key,
                "chat_thread_id": chat_thread_id,
                "discussion_thread_id": discussion_thread_id,
                "discussion_reply_id": discussion_reply_id,
                "match_id": kwargs.get("match_id"),
                "competition_id": kwargs.get("competition_id"),
                "transaction_id": ledger_transaction_id,
                "economic_conversion_id": conversion.id,
                "fee_policy_rule_key": split.rule_key,
                "fee_policy_version": split.policy_version,
            },
        )
        self.wallet_service._stage_domain_event(self.session, event=event, durable=True)
        return transaction


GiftEngineService = CanonicalGiftEngineService

__all__ = ["CanonicalGiftEngineService", "GiftEngineError", "GiftEngineService"]
