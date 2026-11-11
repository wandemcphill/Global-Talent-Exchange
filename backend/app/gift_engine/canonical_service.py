from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select

from app.core.events import DomainEvent
from app.economy.conversion_service import EconomicConversionError, FanCoinGiftConversionService
from app.economy.economic_policy import compute_gift_split
from app.gift_engine.service import (
    MATCH_SCOPE_GIFT_MAX_COUNT,
    MATCH_SCOPE_GIFT_WINDOW_SECONDS,
    GiftEngineError,
    GiftEngineService as LegacyGiftEngineService,
)
from app.models.base import generate_uuid, utcnow
from app.models.club_profile import ClubProfile
from app.models.community_engine import LiveThread
from app.models.competition_match import CompetitionMatch
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.economy_config import GiftCatalogItem
from app.models.fast_match import FastMatchSession, FastMatchSessionStatus
from app.models.gift_combo_event import GiftComboEvent
from app.models.gift_transaction import GiftTransaction
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.models.wallet import LedgerEntry, LedgerUnit
from app.services.social_collusion_detection_service import SocialCollusionDetectionService
from app.services.spending_control_service import SpendingControlService, SpendingControlViolation
from app.wallets.service import InsufficientBalanceError

ACTIVE_COMPETITION_MATCH_STATUSES = ("live", "in_progress", "halftime", "paused", "ready", "scheduled")


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

    def _resolve_canonical_recipient_identity(
        self,
        *,
        recipient_user_id: str | None,
        recipient_club_id: str | None,
    ) -> tuple[str | None, str | None]:
        """Validate optional club context at the canonical service boundary.

        The authenticated sender/recipient profiles remain the economic identity.
        A club is optional recipient context and, when supplied, must belong to
        the recipient profile. This keeps direct service callers subject to the
        same identity contract as the HTTP router.
        """
        if recipient_club_id is None:
            return recipient_user_id, None

        club = self.session.get(ClubProfile, recipient_club_id)
        if club is None or club.owner_user_id is None:
            raise GiftEngineError("Recipient club was not found.", reason="recipient_club_not_found")
        if recipient_user_id is not None and recipient_user_id != club.owner_user_id:
            raise GiftEngineError(
                "Recipient profile does not own the selected recipient club.",
                reason="recipient_club_identity_mismatch",
            )
        return club.owner_user_id, club.id

    def _resolve_authoritative_match_context(
        self,
        *,
        recipient_user_id: str,
        recipient_club_id: str | None,
        requested_scope: str,
        raw_match_id: str | None,
        raw_competition_id: str | None,
        discussion_thread_id: str | None,
    ) -> tuple[str, str | None, str | None]:
        """Resolve and validate match/competition context on the server.

        Ensures a caller cannot bypass match-scoped rate limiting by omitting
        `source_scope="gtex_competition"` or `match_id` while gifting a club or
        recipient participating in an active match or live match thread, and
        validates explicit `match_id` / `competition_id` references against
        persisted match state when present.
        """
        match_id = (raw_match_id or "").strip() or None
        competition_id = (raw_competition_id or "").strip() or None
        authoritative_scope = requested_scope

        owned_club_ids = list(
            self.session.scalars(select(ClubProfile.id).where(ClubProfile.owner_user_id == recipient_user_id)).all()
        )
        candidate_club_ids = list(dict.fromkeys(([recipient_club_id] if recipient_club_id else []) + owned_club_ids))

        # 1. Inspect discussion thread context if present
        if discussion_thread_id:
            thread = self.session.get(LiveThread, discussion_thread_id)
            if thread is not None:
                thread_meta = dict(thread.metadata_json or {})
                thread_match_id = str(thread_meta.get("match_id") or "").strip() or None
                thread_comp_id = str(thread.competition_key or thread_meta.get("competition_id") or "").strip() or None
                if thread_match_id and not match_id:
                    match_id = thread_match_id
                if thread_comp_id and not competition_id:
                    competition_id = thread_comp_id
                if (
                    thread_match_id
                    or thread_comp_id
                    or (thread.category or "").strip().lower()
                    in {
                        "match",
                        "live_match",
                        "competition",
                    }
                ):
                    authoritative_scope = "gtex_competition"

        # 2. Validate explicit match_id against CompetitionMatch / FastMatchSession if persisted
        if match_id:
            comp_match = self.session.get(CompetitionMatch, match_id)
            if comp_match is not None:
                if competition_id and competition_id != comp_match.competition_id:
                    raise GiftEngineError(
                        "Match does not belong to the specified competition.",
                        reason="invalid_match_context",
                    )
                if recipient_club_id and recipient_club_id not in {
                    comp_match.home_club_id,
                    comp_match.away_club_id,
                }:
                    raise GiftEngineError(
                        "Recipient club does not participate in the specified match.",
                        reason="invalid_match_context",
                    )
                participating_owners = list(
                    self.session.scalars(
                        select(ClubProfile.owner_user_id).where(
                            ClubProfile.id.in_([comp_match.home_club_id, comp_match.away_club_id]),
                            ClubProfile.owner_user_id.is_not(None),
                        )
                    ).all()
                )
                if participating_owners and recipient_user_id not in participating_owners:
                    raise GiftEngineError(
                        "Recipient profile does not participate in the specified match.",
                        reason="invalid_match_context",
                    )
                match_id = comp_match.id
                competition_id = comp_match.competition_id
                return "gtex_competition", match_id, competition_id

            fast_match = self.session.scalar(
                select(FastMatchSession).where(
                    or_(
                        FastMatchSession.match_id == match_id,
                        FastMatchSession.live_match_key == match_id,
                    )
                )
            )
            if fast_match is not None:
                fast_clubs = {c for c in (fast_match.home_club_id, fast_match.away_club_id) if c}
                if recipient_club_id and fast_clubs and recipient_club_id not in fast_clubs:
                    raise GiftEngineError(
                        "Recipient club does not participate in the specified match.",
                        reason="invalid_match_context",
                    )
                fast_users = {u for u in (fast_match.user_id, fast_match.opponent_user_id) if u}
                if (
                    fast_users
                    and recipient_user_id not in fast_users
                    and (not fast_clubs or not set(candidate_club_ids).intersection(fast_clubs))
                ):
                    raise GiftEngineError(
                        "Recipient profile does not participate in the specified match.",
                        reason="invalid_match_context",
                    )
                return "gtex_competition", fast_match.match_id, competition_id

            return authoritative_scope, match_id, competition_id

        # 3. Server-side inference when client omitted match_id: check active CompetitionMatch or FastMatchSession
        if candidate_club_ids:
            active_comp_match = self.session.scalar(
                select(CompetitionMatch)
                .where(
                    or_(
                        CompetitionMatch.home_club_id.in_(candidate_club_ids),
                        CompetitionMatch.away_club_id.in_(candidate_club_ids),
                    ),
                    CompetitionMatch.status.in_(ACTIVE_COMPETITION_MATCH_STATUSES),
                )
                .order_by(CompetitionMatch.updated_at.desc())
            )
            if active_comp_match is not None:
                if competition_id and competition_id != active_comp_match.competition_id:
                    raise GiftEngineError(
                        "Recipient's active match does not belong to the specified competition.",
                        reason="invalid_match_context",
                    )
                return (
                    "gtex_competition",
                    active_comp_match.id,
                    competition_id or active_comp_match.competition_id,
                )

        fast_filters = [
            FastMatchSession.user_id == recipient_user_id,
            FastMatchSession.opponent_user_id == recipient_user_id,
        ]
        if candidate_club_ids:
            fast_filters.extend(
                [
                    FastMatchSession.home_club_id.in_(candidate_club_ids),
                    FastMatchSession.away_club_id.in_(candidate_club_ids),
                ]
            )
        active_fast_match = self.session.scalar(
            select(FastMatchSession)
            .where(
                or_(*fast_filters),
                FastMatchSession.status.in_((FastMatchSessionStatus.QUEUED, FastMatchSessionStatus.READY)),
            )
            .order_by(FastMatchSession.updated_at.desc())
        )
        if active_fast_match is not None:
            return "gtex_competition", active_fast_match.match_id, competition_id

        if competition_id and any(
            token in competition_id.lower() for token in {"gtex", "platform", "official", "national", "qualifier"}
        ):
            authoritative_scope = "gtex_competition"
        elif competition_id and authoritative_scope != "user_hosted":
            authoritative_scope = "gtex_competition"

        return authoritative_scope, match_id, competition_id

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
                or_(
                    GiftTransaction.source_scope == source_scope,
                    GiftTransaction.source_scope == "gtex_competition",
                    GiftTransaction.match_id.is_not(None),
                    GiftTransaction.competition_id.is_not(None),
                ),
                GiftTransaction.created_at >= window_start,
            )
        )
        return int(count or 0)

    def send_gift(self, *, sender: User, **kwargs: Any):  # type: ignore[override]
        caller_scope = self._normalize_scope(kwargs.get("source_scope"))
        recipient_user_id, recipient_club_id = self._resolve_canonical_recipient_identity(
            recipient_user_id=kwargs.get("recipient_user_id"),
            recipient_club_id=kwargs.get("recipient_club_id"),
        )
        self.ensure_football_gift_catalog()
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

        requested_scope, resolved_match_id, resolved_competition_id = self._resolve_authoritative_match_context(
            recipient_user_id=recipient.id,
            recipient_club_id=recipient_club_id,
            requested_scope=caller_scope,
            raw_match_id=kwargs.get("match_id"),
            raw_competition_id=kwargs.get("competition_id"),
            discussion_thread_id=str(discussion_thread_id) if discussion_thread_id else None,
        )

        requested_gift_key = str(kwargs.get("gift_key") or "").strip()
        requested_catalog_item = self.session.scalar(
            select(GiftCatalogItem).where(GiftCatalogItem.key == requested_gift_key)
        )
        normalized_quantity = self._normalize_amount(kwargs.get("quantity"))
        if normalized_quantity <= Decimal("0.0000"):
            raise GiftEngineError("Gift quantity must be positive.")
        if normalized_quantity != normalized_quantity.to_integral_value():
            raise GiftEngineError("Gift quantity must be a whole number.", reason="invalid_gift_quantity")

        normalized_idempotency_key = kwargs.get("idempotency_key")
        normalized_idempotency_key = normalized_idempotency_key.strip() if normalized_idempotency_key else None
        if normalized_idempotency_key:
            existing_transaction = self.session.scalar(
                select(GiftTransaction).where(GiftTransaction.idempotency_key == normalized_idempotency_key)
            )
            if existing_transaction is not None:
                if existing_transaction.sender_user_id != sender.id:
                    raise GiftEngineError(
                        "Idempotent gift reference belongs to a different sender profile.",
                        reason="sender_identity_conflict",
                    )
                if (
                    existing_transaction.recipient_user_id != recipient.id
                    or existing_transaction.recipient_club_id != recipient_club_id
                    or existing_transaction.recipient_type != recipient_type
                    or existing_transaction.recipient_entity_id != recipient_entity_id
                ):
                    raise GiftEngineError(
                        "Idempotent gift reference belongs to a different recipient profile or context.",
                        reason="recipient_identity_conflict",
                    )
                if (
                    requested_catalog_item is None
                    or existing_transaction.gift_catalog_item_id != requested_catalog_item.id
                ):
                    raise GiftEngineError(
                        "Idempotent gift reference was already used for a different gift item.",
                        reason="idempotency_key_conflict",
                    )
                request_identity = {
                    "quantity": normalized_quantity,
                    "source_scope": requested_scope,
                    "caller_source_scope": caller_scope,
                    "chat_thread_id": chat_thread_id,
                    "discussion_thread_id": discussion_thread_id,
                    "discussion_reply_id": discussion_reply_id,
                    "match_id": resolved_match_id,
                    "competition_id": resolved_competition_id,
                    "note": kwargs.get("note"),
                }
                stored_meta = existing_transaction.metadata_json or {}
                stored_identity = {
                    "quantity": self._normalize_amount(existing_transaction.quantity),
                    "source_scope": existing_transaction.source_scope,
                    "caller_source_scope": stored_meta.get("caller_source_scope", existing_transaction.source_scope),
                    "chat_thread_id": existing_transaction.chat_thread_id,
                    "discussion_thread_id": existing_transaction.discussion_thread_id,
                    "discussion_reply_id": existing_transaction.discussion_reply_id,
                    "match_id": existing_transaction.match_id,
                    "competition_id": existing_transaction.competition_id,
                    "note": existing_transaction.note,
                }
                if request_identity != stored_identity:
                    raise GiftEngineError(
                        "Idempotent gift reference was already used for a different gift request.",
                        reason="idempotency_key_conflict",
                    )
                return existing_transaction

        if requested_scope == "gtex_competition":
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

        requested_currency = str(kwargs.get("currency") or kwargs.get("ledger_unit") or "").strip().lower()
        if requested_currency in {"coin", "gtex_coin"}:
            raise GiftEngineError(
                "GTEX Coin cannot be used as a gift source currency. Gifts must use FanCoin/CREDIT.",
                reason="invalid_gift_source_currency",
            )

        gift = requested_catalog_item if requested_catalog_item is not None and requested_catalog_item.active else None
        if gift is None:
            raise GiftEngineError("Gift catalog item was not found.")
        if (gift.currency or "").strip().lower() in {"coin", "gtex_coin"}:
            raise GiftEngineError(
                "GTEX Coin cannot be used as a gift source currency. Gifts must use FanCoin/CREDIT.",
                reason="invalid_gift_source_currency",
            )
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

        sender_label = sender.display_name or sender.username or "A supporter"
        recipient_label = recipient.display_name or recipient.username or "recipient"

        transaction = GiftTransaction(
            id=generate_uuid(),
            sender_user_id=sender.id,
            recipient_user_id=recipient.id,
            gift_catalog_item_id=gift.id,
            idempotency_key=normalized_idempotency_key,
            recipient_club_id=recipient_club_id,
            recipient_type=recipient_type,
            recipient_entity_id=recipient_entity_id,
            chat_thread_id=chat_thread_id,
            discussion_thread_id=discussion_thread_id,
            discussion_reply_id=discussion_reply_id,
            match_id=resolved_match_id,
            competition_id=resolved_competition_id,
            quantity=normalized_quantity,
            unit_price=unit_price,
            gross_amount=gross_amount,
            platform_rake_amount=platform_rake,
            recipient_net_amount=recipient_net,
            source_scope=requested_scope,
            ledger_unit=LedgerUnit.COIN,
            source_ledger_unit=LedgerUnit.CREDIT,
            destination_ledger_unit=LedgerUnit.COIN,
            conversion_rate=Decimal("0.0100"),
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
                "caller_source_scope": caller_scope,
                "source_ledger_unit": LedgerUnit.CREDIT.value,
                "destination_ledger_unit": LedgerUnit.COIN.value,
                "fee_policy_rule_key": split.rule_key,
                "fee_policy_version": split.policy_version,
                "recipient_profile_id": recipient.id,
                "recipient_club_id": recipient_club_id,
                "club_id": recipient_club_id,
                "sender_display_name": sender_label,
                "recipient_display_name": recipient_label,
                "identity_semantics": "profile_is_canonical_sender_recipient_identity_club_is_context_only",
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
                    "recipient_profile_id": recipient.id,
                    "recipient_club_id": recipient_club_id,
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

        gtex_out = conversion.destination_amount
        transaction.conversion_rate = conversion.conversion_rate
        transaction.economic_conversion_id = conversion.id
        transaction.ledger_transaction_id = ledger_transaction_id
        transaction.wallet_debit_ledger_id = debit_entry.id if debit_entry else None
        transaction.wallet_credit_ledger_id = credit_entry.id if credit_entry else None
        transaction.platform_fee_ledger_id = platform_fee_entry.id if platform_fee_entry else None
        transaction.metadata_json = {
            **(transaction.metadata_json or {}),
            "conversion_id": conversion.id,
            "conversion_source_amount": str(conversion.source_amount),
            "conversion_destination_amount": str(gtex_out),
            "gtex_out": str(gtex_out),
            "fan_remainder": str(recipient_net),
            "conversion_rate": str(conversion.conversion_rate),
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
            "recipient_club_id": recipient_club_id,
            "quantity": str(normalized_quantity),
            "gross_amount": str(gross_amount),
            "recipient_net_amount": str(recipient_net),
            "gtex_out": str(gtex_out),
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
                message=f"{sender_label} sent you {gift.display_name} worth {gtex_out} GTEX Coin.",
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
                "recipient_club_id": recipient_club_id,
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
                "match_id": resolved_match_id,
                "competition_id": resolved_competition_id,
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
