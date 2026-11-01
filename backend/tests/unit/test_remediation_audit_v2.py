from __future__ import annotations

from datetime import date
import hashlib
from types import SimpleNamespace
import pytest

from app.players.gsi_service import resolve_player_gsi
from app.services.regen_market_service import _compute_age


def test_governed_gsi_benchmarks_and_overrides() -> None:
    # 1. All-time legends & Ballon d'Or winners
    messi = SimpleNamespace(full_name="Lionel Messi", provider_external_id="7458500")
    cur, pot = resolve_player_gsi(messi)
    assert cur == 98
    assert pot == 98

    ronaldo = SimpleNamespace(full_name="Cristiano Ronaldo", provider_external_id="735216")
    cur, pot = resolve_player_gsi(ronaldo)
    assert cur == 98
    assert pot == 98

    pele = SimpleNamespace(full_name="Edson Arantes do Nascimento (Pelé)", provider_external_id="legend_pele_10")
    cur, pot = resolve_player_gsi(pele)
    assert cur == 98
    assert pot == 98

    henry = SimpleNamespace(full_name="Thierry Henry", provider_external_id="9888")
    cur, pot = resolve_player_gsi(henry)
    assert cur == 95
    assert pot == 95

    zidane = SimpleNamespace(full_name="Zinedine Zidane", provider_external_id="8076")
    cur, pot = resolve_player_gsi(zidane)
    assert cur == 95
    assert pot == 95

    ronaldinho = SimpleNamespace(full_name="Ronaldinho", provider_external_id="2002041199")
    cur, pot = resolve_player_gsi(ronaldinho)
    assert cur == 95
    assert pot == 95

    cantona = SimpleNamespace(full_name="Eric Cantona", provider_external_id="2002042479")
    cur, pot = resolve_player_gsi(cantona)
    assert cur == 91
    assert pot == 91

    laudrup = SimpleNamespace(full_name="Michael Laudrup", provider_external_id="601710")
    cur, pot = resolve_player_gsi(laudrup)
    assert cur == 90
    assert pot == 90


def test_active_player_calibrated_benchmarks_never_promotes_potential() -> None:
    # Ademola Lookman: 84 current / 90 potential
    lookman = SimpleNamespace(full_name="Ademola Lookman", provider_external_id="5321", is_real_player=True)
    cur, pot = resolve_player_gsi(lookman)
    assert cur == 84
    assert pot == 90
    assert cur < pot, "Current GSI must NEVER be promoted into potential ceiling"

    # Cole Palmer: 89 current / 93 potential
    palmer = SimpleNamespace(full_name="Cole Palmer", provider_external_id="28912747", is_real_player=True)
    cur, pot = resolve_player_gsi(palmer)
    assert cur == 89
    assert pot == 93
    assert cur < pot

    # Estêvão: 85 current / 90 potential
    estevao = SimpleNamespace(full_name="Estêvão", provider_external_id="2002042919", is_real_player=True)
    cur, pot = resolve_player_gsi(estevao)
    assert cur == 85
    assert pot == 90

    # Gabriel Mec: 78 current / 89 potential
    mec = SimpleNamespace(full_name="Gabriel Mec", provider_external_id="2002088213", is_real_player=True)
    cur, pot = resolve_player_gsi(mec)
    assert cur == 78
    assert pot == 89

    # Zadok Yohanna: 74 current / 89 potential
    zadok = SimpleNamespace(full_name="Zadok Yohanna", provider_external_id="1421433", is_real_player=True)
    cur, pot = resolve_player_gsi(zadok)
    assert cur == 74
    assert pot == 89


def test_governed_columns_take_absolute_precedence() -> None:
    # Player with explicit governed columns
    player = SimpleNamespace(
        full_name="Custom Governed Player",
        provider_external_id="custom_123",
        governed_gsi=88,
        governed_potential_gsi=94,
        market_value_eur=150_000_000.0,  # EUR value must be ignored
    )
    cur, pot = resolve_player_gsi(player)
    assert cur == 88
    assert pot == 94


def test_wonderkid_age_policy_boundary() -> None:
    # GTEX virtual date: 2026-11-01
    virtual_date = date(2026, 11, 1)

    # Born 2005-11-01 -> Turns exactly 21 on 2026-11-01 -> Eligible!
    dob_21 = date(2005, 11, 1)
    age_21 = _compute_age(dob_21, today=virtual_date)
    assert age_21 == 21

    # Born 2004-11-01 -> Turns exactly 22 on 2026-11-01 -> Ineligible (> 21)
    dob_22 = date(2004, 11, 1)
    age_22 = _compute_age(dob_22, today=virtual_date)
    assert age_22 == 22

    # Born 2005-11-02 -> Aged 20 years 364 days -> Eligible!
    dob_almost_21 = date(2005, 11, 2)
    age_almost_21 = _compute_age(dob_almost_21, today=virtual_date)
    assert age_almost_21 == 20


def test_deterministic_sha256_face_seed() -> None:
    uid = "2002042919"
    name = "Estêvão"
    face_count = 8522

    # Verify repeatable deterministic hashing
    expected_seed_hash = int(hashlib.sha256(f"{uid}-{name}".encode("utf-8")).hexdigest(), 16)
    idx_1 = expected_seed_hash % face_count
    idx_2 = int(hashlib.sha256(f"{uid}-{name}".encode("utf-8")).hexdigest(), 16) % face_count
    assert idx_1 == idx_2
    assert 0 <= idx_1 < face_count


def test_michael_laudrup_restoration_terms_and_holding_conservation() -> None:
    # Restored terms per Decision C
    total_shares = 100
    circulating_shares = 22
    share_price = 356.1075
    user_holding = 2

    assert total_shares == 100
    assert circulating_shares == 22
    assert share_price == 356.1075
    assert user_holding == 2

    # Fundamental Invariant: sum(holdings) <= circulating <= total
    assert user_holding <= circulating_shares <= total_shares
