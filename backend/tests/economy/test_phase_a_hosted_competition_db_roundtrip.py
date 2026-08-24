from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.hosted_competition_engine.coin_aware_service import CoinAwareHostedCompetitionService
from app.models import Base
from app.models.admin_rules import AdminRewardRule
from app.models.hosted_competition import (
    CompetitionTemplate,
    HostedCompetitionSettlement,
    UserHostedCompetitionParticipant,
)
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService


def make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def seed_host_coin(session, host, amount: Decimal) -> None:
    wallet = WalletService()
    host_account = wallet.get_user_account(session, host, LedgerUnit.COIN)
    clearing = wallet.ensure_platform_account(session, LedgerUnit.COIN)
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=host_account, amount=amount),
            LedgerPosting(account=clearing, amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference="phase-a-host-funding-seed",
        actor=host,
    )
    session.commit()


def test_hosted_coin_competition_create_freeze_settle_roundtrip_uses_db_ledger() -> None:
    session = make_session()
    try:
        host = create_user(session, email="phase-a-host@example.com", username="phase-a-host")
        winner = create_user(session, email="phase-a-winner@example.com", username="phase-a-winner")

        session.add(
            AdminRewardRule(
                rule_key="phase-a-competition-fee",
                title="Phase A competition fee",
                description="Integration test fee policy",
                trading_fee_bps=2000,
                gift_platform_rake_bps=3000,
                withdrawal_fee_bps=1000,
                minimum_withdrawal_fee_credits=5,
                competition_platform_fee_bps=3000,
                stability_controls_json={},
                active=True,
            )
        )
        session.add(
            CompetitionTemplate(
                template_key="phase-a-db-cup",
                title="Phase A DB Cup",
                description="Database-backed economic proof",
                competition_type="football",
                team_type="club",
                age_grade="senior",
                cup_or_league="cup",
                participants=8,
                viewing_mode="standard",
                gift_rules={},
                seeding_method="random",
                is_user_hostable=True,
            )
        )
        session.commit()
        seed_host_coin(session, host, Decimal("1000.0000"))

        service = CoinAwareHostedCompetitionService(session=session, wallet_service=WalletService())
        payload = SimpleNamespace(
            funding_mode="host_funded_gtex_coin_prize",
            template_key="phase-a-db-cup",
            title="Phase A DB Cup",
            description="",
            slug="phase-a-db-cup",
            visibility="public",
            starts_at=None,
            lock_at=None,
            max_participants=8,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_coin=Decimal("1000.0000"),
            metadata_json={},
            join_passcode=None,
        )

        competition, _, host_participation_created = service.create_competition(host=host, payload=payload)
        session.commit()

        assert host_participation_created is True
        assert competition.metadata_json["platform_fee_bps"] == 3000
        assert competition.metadata_json["platform_fee_policy_frozen"] is True
        assert competition.host_funding_escrowed_coin == Decimal("1000.0000")
        assert WalletService().get_balance(
            session, WalletService().get_user_account(session, host, LedgerUnit.COIN)
        ) == Decimal("0.0000")

        session.add(
            UserHostedCompetitionParticipant(
                competition_id=competition.id,
                user_id=winner.id,
                entry_fee_fancoin=Decimal("0.0000"),
                payout_eligible=True,
                metadata_json={"payment_status": "host_funded"},
            )
        )
        session.commit()

        finance_before = service.finance_snapshot(competition.id)
        assert finance_before["currency"] == "coin"
        assert finance_before["escrow_balance"] == Decimal("1000.0000")
        assert finance_before["projected_reward_pool"] == Decimal("700.0000")
        assert finance_before["projected_platform_fee"] == Decimal("300.0000")

        rule = session.scalar(select(AdminRewardRule).where(AdminRewardRule.rule_key == "phase-a-competition-fee"))
        assert rule is not None
        rule.competition_platform_fee_bps = 1000
        session.commit()

        service.finalize_competition(
            actor=host,
            competition_id=competition.id,
            placements=[{"user_id": winner.id, "rank": 1, "payout_percent": 100}],
        )
        session.commit()

        winner_balance = WalletService().get_balance(
            session, WalletService().get_user_account(session, winner, LedgerUnit.COIN)
        )
        assert winner_balance == Decimal("700.0000")
        assert competition.host_funding_escrowed_coin == Decimal("0.0000")

        settlements = list(
            session.scalars(
                select(HostedCompetitionSettlement)
                .where(HostedCompetitionSettlement.competition_id == competition.id)
                .order_by(HostedCompetitionSettlement.settlement_type.asc())
            ).all()
        )
        assert len(settlements) == 2

        prize = next(row for row in settlements if row.settlement_type == "prize")
        platform_fee = next(row for row in settlements if row.settlement_type == "platform_fee")
        assert prize.currency == "coin"
        assert prize.net_amount == Decimal("700.0000")
        assert platform_fee.currency == "coin"
        assert platform_fee.net_amount == Decimal("300.0000")
        assert platform_fee.platform_fee_amount == Decimal("300.0000")
        assert prize.ledger_transaction_id == platform_fee.ledger_transaction_id

        finance_after = service.finance_snapshot(competition.id)
        assert finance_after["escrow_balance"] == Decimal("0.0000")
        assert finance_after["settled_prizes"] == Decimal("700.0000")
        assert finance_after["settled_platform_fee"] == Decimal("300.0000")
        assert finance_after["status"] == "completed"
    finally:
        session.close()
