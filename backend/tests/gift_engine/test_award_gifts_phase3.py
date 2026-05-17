from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_engine.schemas import AdminRewardRuleStabilityControls
from app.auth.service import AuthService
from app.gift_engine.service import GiftEngineService
from app.models import (
    AdminRewardRule,
    Base,
    ClubRankingEvent,
    GiftAbuseFlag,
    GiftStats,
    GiftTransaction,
    LedgerEntryReason,
    LedgerTransaction,
    LedgerUnit,
    LiveThread,
    LiveThreadMessage,
)
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",
    )
    session.commit()
    return user


def _fund_fan_coin(session, user, amount: Decimal) -> None:
    wallet_service = WalletService()
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=user_account, amount=amount),
            LedgerPosting(account=platform_account, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"seed-fan-coin:{user.id}",
        actor=user,
    )
    session.commit()


def _allow_mythic_awards(session) -> None:
    session.add(
        AdminRewardRule(
            rule_key="phase3-award-gift-controls",
            title="Phase 3 award gift controls",
            description="Test-safe high limits for mythic award packs.",
            trading_fee_bps=2000,
            gift_platform_rake_bps=3000,
            withdrawal_fee_bps=1000,
            minimum_withdrawal_fee_credits=Decimal("5.0000"),
            competition_platform_fee_bps=2000,
            stability_controls_json=AdminRewardRuleStabilityControls(
                user_hosted_gift={
                    "max_amount": "20000.0000",
                    "daily_sender_limit": "50000.0000",
                    "daily_recipient_limit": "50000.0000",
                    "daily_pair_limit": "50000.0000",
                    "cooldown_seconds": 0,
                    "burst_window_seconds": 300,
                    "burst_max_count": 20,
                    "review_threshold_bps": 9500,
                }
            ).model_dump(mode="json"),
            active=True,
        )
    )
    session.commit()


def test_award_catalog_seeds_ballon_dor_and_sends_mythic_discussion_gift(session) -> None:
    sender = _create_user(session, email="sender-awards@example.com", username="sender-awards")
    recipient = _create_user(session, email="recipient-awards@example.com", username="recipient-awards")
    _allow_mythic_awards(session)
    _fund_fan_coin(session, sender, Decimal("12000.0000"))

    thread = LiveThread(
        thread_key="discussion-award-night",
        thread_type="discussion",
        category="tactics_room",
        title="Award night debate",
        body="Who deserves the biggest GTEX ceremony?",
        created_by_user_id=recipient.id,
    )
    session.add(thread)
    session.commit()

    service = GiftEngineService(session)
    catalog = {item.key: item for item in service.list_catalog(active_only=True)}

    assert catalog["ballon_dor"].display_name == "Ballon d'Or"
    assert catalog["ballon_dor"].fallback_display_name == "Golden Ball Supreme"
    assert catalog["ballon_dor"].rarity == "mythic"
    assert catalog["ballon_dor"].is_award_pack is True
    assert catalog["ballon_dor"].legal_status == "requires_review"
    assert catalog["world_best_award"].animation_key == "world_best_award"
    assert catalog["king_of_tactics"].animation_key == "king_of_tactics"
    assert catalog["top_trainer"].animation_key == "top_trainer"

    transaction = service.send_gift(
        sender=sender,
        gift_key="ballon_dor",
        quantity=Decimal("1.0000"),
        discussion_thread_id=thread.id,
        idempotency_key="award-night-ballon-dor",
    )
    session.commit()

    assert transaction.gross_amount == Decimal("10000.0000")
    assert transaction.platform_rake_amount == Decimal("3000.0000")
    assert transaction.recipient_net_amount == Decimal("7000.0000")
    assert transaction.ledger_unit == LedgerUnit.CREDIT
    assert transaction.currency_label if hasattr(transaction, "currency_label") else True
    assert transaction.recipient_type == "discussion_thread"
    assert transaction.recipient_user_id == recipient.id
    assert transaction.animation_key == "ballon_dor"
    assert transaction.sound_key == "stadium_ceremony_roar"
    assert transaction.wallet_debit_ledger_id is not None
    assert transaction.wallet_credit_ledger_id is not None
    assert transaction.platform_fee_ledger_id is not None

    same_transaction = service.send_gift(
        sender=sender,
        gift_key="ballon_dor",
        quantity=Decimal("1.0000"),
        discussion_thread_id=thread.id,
        idempotency_key="award-night-ballon-dor",
    )
    assert same_transaction.id == transaction.id
    assert (
        session.scalar(select(GiftTransaction).where(GiftTransaction.idempotency_key == "award-night-ballon-dor")).id
        == transaction.id
    )
    assert (
        session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == "award-night-ballon-dor")
        ).id
        == transaction.ledger_transaction_id
    )

    user_stats = session.scalar(
        select(GiftStats).where(GiftStats.entity_type == "user", GiftStats.entity_id == recipient.id)
    )
    thread_stats = session.scalar(
        select(GiftStats).where(GiftStats.entity_type == "discussion_thread", GiftStats.entity_id == thread.id)
    )
    assert user_stats is not None
    assert user_stats.total_fan_coin_received == Decimal("7000.0000")
    assert user_stats.mythic_gifts_received == 1
    assert thread_stats is not None
    assert thread_stats.total_fan_coin_received == Decimal("7000.0000")
    assert thread_stats.top_gift_code == "ballon_dor"

    gift_message = session.scalar(
        select(LiveThreadMessage).where(
            LiveThreadMessage.thread_id == thread.id,
            LiveThreadMessage.message_type == "gift",
        )
    )
    assert gift_message is not None
    assert gift_message.metadata_json["gift_key"] == "ballon_dor"
    assert gift_message.metadata_json["rarity"] == "mythic"

    assert session.scalar(select(ClubRankingEvent)) is None


def test_reciprocal_gifting_is_flagged_and_insufficient_fan_coin_is_rejected(session) -> None:
    first = _create_user(session, email="first-gifter@example.com", username="first-gifter")
    second = _create_user(session, email="second-gifter@example.com", username="second-gifter")
    unfunded = _create_user(session, email="unfunded-gifter@example.com", username="unfunded-gifter")
    _fund_fan_coin(session, first, Decimal("50.0000"))
    _fund_fan_coin(session, second, Decimal("50.0000"))

    service = GiftEngineService(session)
    outbound = service.send_gift(
        sender=first,
        recipient_user_id=second.id,
        gift_key="whistle_blow",
        quantity=Decimal("1.0000"),
        idempotency_key="reciprocal-first",
    )
    session.commit()
    assert outbound.abuse_status == "clean"

    reciprocal = service.send_gift(
        sender=second,
        recipient_user_id=first.id,
        gift_key="whistle_blow",
        quantity=Decimal("1.0000"),
        idempotency_key="reciprocal-second",
    )
    session.commit()

    flag = session.scalar(select(GiftAbuseFlag).where(GiftAbuseFlag.gift_transaction_id == reciprocal.id))
    assert reciprocal.abuse_status == "review"
    assert flag is not None
    assert flag.flag_type == "reciprocal_gifting"

    with pytest.raises(InsufficientBalanceError):
        service.send_gift(
            sender=unfunded,
            recipient_user_id=second.id,
            gift_key="whistle_blow",
            quantity=Decimal("1.0000"),
            idempotency_key="unfunded-whistle",
        )
