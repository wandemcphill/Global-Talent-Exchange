from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import config as config_module
from app.core.field_encryption import (
    ENCRYPTION_PREFIX,
    blind_index,
    decrypt_field,
    encrypt_field,
    identifier_hash_clause,
)
from app.core.config import load_settings
from app.models import Base
from app.models.treasury import (
    KycProfile,
    RateDirection,
    TreasuryWithdrawalRequest,
    UserBankAccount,
)
from app.models.user import KycStatus, User
from app.models.wallet import LedgerAccount, LedgerUnit, PayoutRequest, PayoutStatus


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


def _user(session, *, user_id: str = "user-kyc-1") -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        display_name="KYC User",
        password_hash="x",
        kyc_status=KycStatus.UNVERIFIED,
    )
    session.add(user)
    session.flush()
    return user


def _kyc(session, *, nin: str | None, bvn: str | None) -> KycProfile:
    user = _user(session)
    profile = KycProfile(
        user_id=user.id,
        status=KycStatus.UNDER_REVIEW,
        nin=nin,
        bvn=bvn,
    )
    session.add(profile)
    session.flush()
    return profile


def test_encrypted_columns_round_trip_and_store_ciphertext(session) -> None:
    profile = _kyc(session, nin="12345678901", bvn="22112233445")
    session.commit()

    assert profile.nin == "12345678901"
    assert profile.bvn == "22112233445"
    assert profile.nin_hash == blind_index("12345678901")
    assert profile.bvn_hash == blind_index("22112233445")

    raw = session.execute(
        text("SELECT nin, bvn FROM kyc_profiles WHERE id = :id"),
        {"id": profile.id},
    ).one()
    assert raw[0].startswith(ENCRYPTION_PREFIX)
    assert raw[1].startswith(ENCRYPTION_PREFIX)
    assert "12345678901" not in raw[0]
    assert "22112233445" not in raw[1]

    session.expire_all()
    reloaded = session.get(KycProfile, profile.id)
    assert reloaded.nin == "12345678901"
    assert reloaded.bvn == "22112233445"


def test_bank_account_numbers_encrypt_at_rest(session) -> None:
    user = _user(session, user_id="user-bank-1")
    account = UserBankAccount(
        user_id=user.id,
        bank_name="Test Bank",
        account_number="0123456789",
        account_name="KYC User",
    )
    session.add(account)
    session.commit()

    raw = session.execute(
        text("SELECT account_number FROM user_bank_accounts WHERE id = :id"),
        {"id": account.id},
    ).scalar_one()
    assert raw.startswith(ENCRYPTION_PREFIX)
    assert "0123456789" not in raw

    session.expire_all()
    assert session.get(UserBankAccount, account.id).account_number == "0123456789"


def test_withdrawal_bank_account_encrypts_and_indexes(session) -> None:
    user = _user(session, user_id="user-wd-1")
    account = LedgerAccount(
        owner_user_id=user.id,
        code="acct-user-wd-1",
        label="User wallet",
        unit=LedgerUnit.COIN,
    )
    session.add(account)
    session.flush()
    payout = PayoutRequest(
        id="payout-1",
        user_id=user.id,
        account_id=account.id,
        amount=Decimal("10.0000"),
        unit=LedgerUnit.COIN,
        status=PayoutStatus.REQUESTED,
        destination_reference="dest-1",
    )
    session.add(payout)
    session.flush()
    withdrawal = TreasuryWithdrawalRequest(
        payout_request_id=payout.id,
        user_id=user.id,
        reference="wd-ref-1",
        unit=LedgerUnit.COIN,
        amount_coin=Decimal("10.0000"),
        amount_fiat=Decimal("9000.0000"),
        fee_amount=Decimal("0.0000"),
        net_amount=Decimal("10.0000"),
        rate_value=Decimal("900.000000"),
        rate_direction=RateDirection.FIAT_PER_COIN,
        bank_name="Test Bank",
        bank_account_number="5566778899",
        bank_account_name="KYC User",
    )
    session.add(withdrawal)
    session.commit()

    raw = session.execute(
        text("SELECT bank_account_number FROM treasury_withdrawal_requests WHERE id = :id"),
        {"id": withdrawal.id},
    ).scalar_one()
    assert raw.startswith(ENCRYPTION_PREFIX)
    assert "5566778899" not in raw
    assert withdrawal.bank_account_number_hash == blind_index("5566778899")


def test_legacy_plaintext_row_reads_through(session) -> None:
    user = _user(session, user_id="user-legacy-1")
    session.execute(
        text(
            "INSERT INTO kyc_profiles (id, user_id, status, nin, bvn) "
            "VALUES ('legacy-kyc', :uid, 'under_review', '99988877766', '11223344556')"
        ),
        {"uid": user.id},
    )
    session.commit()

    profile = session.get(KycProfile, "legacy-kyc")
    assert profile.nin == "99988877766"
    assert profile.bvn == "11223344556"


def test_encrypt_field_does_not_double_encrypt() -> None:
    once = encrypt_field("sensitive")
    twice = encrypt_field(once)
    assert once == twice
    assert decrypt_field(twice) == "sensitive"


def test_key_rotation_decrypts_with_secondary_key(monkeypatch) -> None:
    from cryptography.fernet import Fernet

    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")

    def fake_settings(field_encryption_key):
        return SimpleNamespace(
            field_encryption_key=field_encryption_key,
            auth_secret="test-secret",  # pragma: allowlist secret
        )

    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: fake_settings(old_key),
    )
    token = encrypt_field("rotate-me")
    assert token.startswith(ENCRYPTION_PREFIX)

    # After rotation the old key is secondary; new writes use the new key and
    # old ciphertext still decrypts.
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: fake_settings(f"{new_key},{old_key}"),
    )
    assert decrypt_field(token) == "rotate-me"
    fresh = encrypt_field("fresh-value")
    assert Fernet(new_key.encode()).decrypt(fresh[len(ENCRYPTION_PREFIX) :].encode()).decode() == "fresh-value"


def test_production_settings_require_field_encryption_key(tmp_path) -> None:
    environ = {
        "GTE_APP_ENV": "production",
        "GTE_DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'prod.db').as_posix()}",
        "DATABASE_URL": "",
        "GTE_AUTH_SECRET": "prod-auth-secret",  # pragma: allowlist secret
        "GTE_MEDIA_SIGNING_SECRET": "prod-media-secret",  # pragma: allowlist secret
        "GTE_BOOTSTRAP_ADMIN_ENABLED": "0",
    }
    with pytest.raises(ValueError, match="GTE_FIELD_ENCRYPTION_KEY"):
        load_settings(environ=environ)


def test_development_settings_derive_key_from_auth_secret(tmp_path) -> None:
    environ = {
        "GTE_APP_ENV": "development",
        "GTE_DATABASE_URL": f"sqlite+pysqlite:///{(tmp_path / 'dev.db').as_posix()}",
        "DATABASE_URL": "",
        "GTE_AUTH_SECRET": "dev-auth-secret",  # pragma: allowlist secret
        "GTE_MEDIA_SIGNING_SECRET": "dev-media-secret",  # pragma: allowlist secret
        "GTE_BOOTSTRAP_ADMIN_ENABLED": "0",
    }
    settings = load_settings(environ=environ)
    assert settings.field_encryption_key  # derived, non-empty
    other = load_settings(environ={**environ, "GTE_AUTH_SECRET": "different-secret"})
    assert settings.field_encryption_key != other.field_encryption_key


def test_blind_index_search_finds_kyc_and_withdrawal(session) -> None:
    profile = _kyc(session, nin=None, bvn="22112233445")
    withdrawal = TreasuryWithdrawalRequest(
        payout_request_id="payout-search-1",
        user_id=profile.user_id,
        reference="wd-search-1",
        unit=LedgerUnit.COIN,
        amount_coin=Decimal("1.0000"),
        amount_fiat=Decimal("900.0000"),
        fee_amount=Decimal("0.0000"),
        net_amount=Decimal("1.0000"),
        rate_value=Decimal("900.000000"),
        rate_direction=RateDirection.FIAT_PER_COIN,
        bank_name="Test Bank",
        bank_account_number="9988776655",
        bank_account_name="KYC User",
    )
    session.add(withdrawal)
    session.commit()

    found = session.scalars(select(KycProfile).where(KycProfile.bvn_hash == blind_index(" 22112233445 ".strip()))).all()
    assert [row.id for row in found] == [profile.id]

    found_wd = session.scalars(
        select(TreasuryWithdrawalRequest).where(
            TreasuryWithdrawalRequest.bank_account_number_hash == blind_index("9988776655")
        )
    ).all()
    assert [row.id for row in found_wd] == [withdrawal.id]

    # Non-matching term finds nothing.
    assert session.scalars(select(KycProfile).where(KycProfile.bvn_hash == blind_index("000"))).all() == []


def test_backfill_script_encrypts_legacy_rows_and_is_idempotent(tmp_path, capsys) -> None:
    from backend.scripts.encrypt_sensitive_fields import main as backfill_main

    db_path = tmp_path / "backfill.db"
    url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as seed:
        seed.execute(
            text(
                "INSERT INTO users (id, email, username, display_name, password_hash, role, kyc_status) "
                "VALUES ('u1', 'u1@example.com', 'u1', 'U One', 'x', 'user', 'unverified')"
            )
        )
        seed.execute(
            text(
                "INSERT INTO kyc_profiles (id, user_id, status, nin, bvn) "
                "VALUES ('k1', 'u1', 'under_review', '11122233344', '55566677788')"
            )
        )
        seed.execute(
            text(
                "INSERT INTO user_bank_accounts (id, user_id, bank_name, account_number, account_name, currency_code, is_active) "
                "VALUES ('b1', 'u1', 'Bank', '1231231231', 'U One', 'NGN', 1)"
            )
        )
        seed.execute(
            text(
                "INSERT INTO wallets (id, owner_user_id, code, label, unit, kind, allow_negative, is_active) "
                "VALUES ('acct-1', 'u1', 'acct-1', 'Wallet', 'coin', 'user', 0, 1)"
            )
        )
        seed.execute(
            text(
                "INSERT INTO payout_requests (id, user_id, account_id, amount, unit, status, destination_reference) "
                "VALUES ('p1', 'u1', 'acct-1', 10, 'coin', 'requested', 'dest-1')"
            )
        )
        seed.execute(
            text(
                "INSERT INTO treasury_withdrawal_requests "
                "(id, payout_request_id, user_id, reference, status, unit, amount_coin, amount_fiat, "
                "fee_amount, net_amount, rate_value, rate_direction, bank_name, bank_account_number, "
                "bank_account_name, bank_snapshot_json, kyc_status_snapshot, kyc_tier_snapshot) "
                "VALUES ('w1', 'p1', 'u1', 'ref-1', 'PENDING_REVIEW', 'COIN', 10, 9000, 0, 10, 900, "
                "'FIAT_PER_COIN', 'Bank', '9876543210', 'U One', "
                '\'{"bank_name": "Bank", "account_number": "9876543210", "account_name": "U One"}\', '
                "'unverified', 'unverified')"
            )
        )
        seed.commit()

    assert backfill_main(["--database-url", url, "--dry-run"]) == 0
    dry_counts = capsys.readouterr().out
    assert "kyc_profiles: 1 legacy plaintext row(s)" in dry_counts
    assert "treasury_withdrawal_requests: 1 legacy plaintext row(s)" in dry_counts

    assert backfill_main(["--database-url", url]) == 0
    with SessionLocal() as check:
        raw = check.execute(text("SELECT nin, bvn FROM kyc_profiles WHERE id='k1'")).one()
        assert raw[0].startswith(ENCRYPTION_PREFIX)
        assert raw[1].startswith(ENCRYPTION_PREFIX)
        acct = check.execute(text("SELECT account_number FROM user_bank_accounts WHERE id='b1'")).scalar_one()
        assert acct.startswith(ENCRYPTION_PREFIX)
        profile = check.get(KycProfile, "k1")
        assert profile.nin == "11122233344"
        assert profile.bvn_hash == blind_index("55566677788")

        withdrawal = check.get(TreasuryWithdrawalRequest, "w1")
        assert withdrawal.bank_account_number == "9876543210"
        assert "account_number" not in withdrawal.bank_snapshot_json
        assert withdrawal.bank_snapshot_json["account_number_masked"] == "******3210"

    # Dry-run now reports no legacy rows, and a second run writes nothing.
    assert backfill_main(["--database-url", url, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "kyc_profiles: 0 legacy plaintext row(s)" in out
    assert "user_bank_accounts: 0 legacy plaintext row(s)" in out
    assert "treasury_withdrawal_requests: 0 legacy plaintext row(s)" in out

    assert backfill_main(["--database-url", url]) == 0
    assert "Done. 0 row(s) updated." in capsys.readouterr().out


def test_blank_identifier_search_does_not_match_null_hashes() -> None:
    from sqlalchemy.dialects import sqlite

    assert identifier_hash_clause(KycProfile.nin_hash, None) is None
    assert identifier_hash_clause(KycProfile.bvn_hash, "   ") is None
    assert identifier_hash_clause(TreasuryWithdrawalRequest.bank_account_number_hash, "\t") is None

    clause = identifier_hash_clause(KycProfile.bvn_hash, " 2211 2233445 ")
    compiled = str(clause.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    assert "IS NULL" not in compiled.upper()
    assert blind_index("22112233445") in compiled


def test_reload_keeps_ciphertext_and_blind_index(session) -> None:
    profile = _kyc(session, nin="12345678901", bvn="22112233445")
    session.commit()
    raw_before = session.execute(
        text("SELECT nin, bvn, nin_hash, bvn_hash FROM kyc_profiles WHERE id = :id"),
        {"id": profile.id},
    ).one()

    session.expire_all()
    reloaded = session.get(KycProfile, profile.id)
    assert reloaded is not None
    assert reloaded.nin == "12345678901"
    assert reloaded.bvn_hash == blind_index("22112233445")
    session.commit()

    raw_after = session.execute(
        text("SELECT nin, bvn, nin_hash, bvn_hash FROM kyc_profiles WHERE id = :id"),
        {"id": profile.id},
    ).one()
    assert raw_after == raw_before
    assert raw_after[2] == blind_index("12345678901")
    assert raw_after[3] == blind_index("22112233445")


def test_backfill_repairs_stale_blind_index_without_rewriting_ciphertext(tmp_path, capsys) -> None:
    from backend.scripts.encrypt_sensitive_fields import main as backfill_main

    db_path = tmp_path / "stale-index.db"
    url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as seed:
        user = User(
            id="u-stale",
            email="stale@example.com",
            username="u-stale",
            display_name="Stale",
            password_hash="x",
            kyc_status=KycStatus.UNVERIFIED,
        )
        seed.add(user)
        seed.flush()
        profile = KycProfile(
            id="k-stale",
            user_id=user.id,
            status=KycStatus.UNDER_REVIEW,
            nin="11122233344",
            bvn="55566677788",
        )
        seed.add(profile)
        seed.commit()
        raw_before = seed.execute(text("SELECT nin, bvn FROM kyc_profiles WHERE id='k-stale'")).one()
        seed.execute(text("UPDATE kyc_profiles SET nin_hash='stale', bvn_hash=NULL WHERE id='k-stale'"))
        seed.commit()

    assert backfill_main(["--database-url", url, "--dry-run"]) == 0
    dry_run = capsys.readouterr().out
    assert "kyc_profiles: 0 legacy plaintext row(s), 1 stale blind index row(s)" in dry_run

    assert backfill_main(["--database-url", url]) == 0
    assert "Done. 1 row(s) updated." in capsys.readouterr().out
    with SessionLocal() as check:
        raw_after = check.execute(text("SELECT nin, bvn, nin_hash, bvn_hash FROM kyc_profiles WHERE id='k-stale'")).one()
        assert raw_after[0] == raw_before[0]
        assert raw_after[1] == raw_before[1]
        assert raw_after[2] == blind_index("11122233344")
        assert raw_after[3] == blind_index("55566677788")

    assert backfill_main(["--database-url", url]) == 0
    assert "Done. 0 row(s) updated." in capsys.readouterr().out
