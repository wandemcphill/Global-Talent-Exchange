from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    Base,
    HostedCompetitionFundingMode,
    UserHostedCompetition,
)


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _competition(**overrides):
    values = {
        "template_id": "template-1",
        "host_user_id": "user-1",
        "title": "Test Cup",
        "slug": "test-cup",
        "status": "draft",
        "funding_mode": HostedCompetitionFundingMode.FANCOIN_ENTRY_POOL,
        "entry_fee_fancoin": Decimal("100.0000"),
        "reward_pool_fancoin": Decimal("500.0000"),
    }
    values.update(overrides)
    return UserHostedCompetition(**values)


def test_fancoin_entry_pool_contract_is_valid() -> None:
    session = _session()
    try:
        competition = _competition()
        session.add(competition)
        session.flush()
    finally:
        session.close()


def test_coin_prize_contract_is_valid() -> None:
    session = _session()
    try:
        competition = _competition(
            funding_mode=HostedCompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            reward_pool_coin=Decimal("1000.0000"),
            host_funding_required_coin=Decimal("1000.0000"),
            host_funding_escrowed_coin=Decimal("0.0000"),
        )
        session.add(competition)
        session.flush()
    finally:
        session.close()


def test_coin_prize_rejects_participant_fancoin_entry() -> None:
    session = _session()
    try:
        competition = _competition(
            funding_mode=HostedCompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
            entry_fee_fancoin=Decimal("100.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            reward_pool_coin=Decimal("1000.0000"),
            host_funding_required_coin=Decimal("1000.0000"),
        )
        session.add(competition)
        with pytest.raises(ValueError, match="participant-funded"):
            session.flush()
    finally:
        session.rollback()
        session.close()


def test_fancoin_pool_rejects_coin_prize() -> None:
    session = _session()
    try:
        competition = _competition(
            reward_pool_coin=Decimal("100.0000"),
            host_funding_required_coin=Decimal("100.0000"),
        )
        session.add(competition)
        with pytest.raises(ValueError, match="GTEX Coin host-funded prize"):
            session.flush()
    finally:
        session.rollback()
        session.close()


def test_coin_prize_rejects_unfunded_contract() -> None:
    session = _session()
    try:
        competition = _competition(
            funding_mode=HostedCompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            reward_pool_coin=Decimal("0.0000"),
            host_funding_required_coin=Decimal("0.0000"),
        )
        session.add(competition)
        with pytest.raises(ValueError, match="positive host-funded prize"):
            session.flush()
    finally:
        session.rollback()
        session.close()
