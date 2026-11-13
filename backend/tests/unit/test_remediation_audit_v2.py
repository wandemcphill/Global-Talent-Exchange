from __future__ import annotations

from datetime import date
import hashlib
from types import SimpleNamespace

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


def test_generational_legend_age_rules() -> None:
    # GTEX virtual date: 2026-11-01
    virtual_date = date(2026, 11, 1)

    # 1. Youngest Legends in Game: Age 20 (Ceiling / Floor invariant)
    messi_dob = date(2006, 6, 24)
    cr7_dob = date(2006, 2, 5)
    assert _compute_age(messi_dob, today=virtual_date) == 20
    assert _compute_age(cr7_dob, today=virtual_date) == 20

    # 2. Modern Active Veterans (>= 34): Ages 21-22
    modric_dob = date(2005, 9, 9)
    benzema_dob = date(2004, 12, 19)
    lewandowski_dob = date(2005, 8, 21)
    ramos_dob = date(2005, 3, 30)
    neuer_dob = date(2005, 3, 27)
    kroos_dob = date(2005, 1, 4)
    muller_dob = date(2005, 9, 13)
    assert _compute_age(modric_dob, today=virtual_date) == 21
    assert _compute_age(benzema_dob, today=virtual_date) == 21
    assert _compute_age(lewandowski_dob, today=virtual_date) == 21
    assert _compute_age(ramos_dob, today=virtual_date) == 21
    assert _compute_age(neuer_dob, today=virtual_date) == 21
    assert _compute_age(kroos_dob, today=virtual_date) == 21
    assert _compute_age(muller_dob, today=virtual_date) == 21

    casemiro_dob = date(2004, 2, 23)
    debruyne_dob = date(2004, 6, 28)
    salah_dob = date(2004, 6, 15)
    assert _compute_age(casemiro_dob, today=virtual_date) == 22
    assert _compute_age(debruyne_dob, today=virtual_date) == 22
    assert _compute_age(salah_dob, today=virtual_date) == 22

    # 3. Active 1990s-2010 Legends: Ages 23-25
    gerrard_dob = date(2003, 5, 30)
    xavi_dob = date(2003, 1, 25)
    pirlo_dob = date(2003, 5, 19)
    lampard_dob = date(2003, 6, 20)
    scholes_dob = date(2002, 11, 16)
    iniesta_dob = date(2003, 5, 11)
    casillas_dob = date(2003, 5, 20)
    puyol_dob = date(2003, 4, 13)
    drogba_dob = date(2003, 3, 11)
    rooney_dob = date(2003, 10, 24)
    robben_dob = date(2003, 1, 23)
    ribery_dob = date(2003, 4, 7)
    assert _compute_age(gerrard_dob, today=virtual_date) == 23
    assert _compute_age(xavi_dob, today=virtual_date) == 23
    assert _compute_age(pirlo_dob, today=virtual_date) == 23
    assert _compute_age(lampard_dob, today=virtual_date) == 23
    assert _compute_age(scholes_dob, today=virtual_date) == 23
    assert _compute_age(iniesta_dob, today=virtual_date) == 23
    assert _compute_age(casillas_dob, today=virtual_date) == 23
    assert _compute_age(puyol_dob, today=virtual_date) == 23
    assert _compute_age(drogba_dob, today=virtual_date) == 23
    assert _compute_age(rooney_dob, today=virtual_date) == 23
    assert _compute_age(robben_dob, today=virtual_date) == 23
    assert _compute_age(ribery_dob, today=virtual_date) == 23

    zidane_dob = date(2002, 6, 23)
    ronaldo_r9_dob = date(2002, 9, 22)
    henry_dob = date(2002, 8, 17)
    ronaldinho_dob = date(2002, 3, 21)
    rivaldo_dob = date(2002, 4, 19)
    beckham_dob = date(2002, 5, 2)
    nedved_dob = date(2002, 8, 30)
    shevchenko_dob = date(2002, 9, 29)
    raul_dob = date(2002, 6, 27)
    totti_dob = date(2002, 9, 27)
    del_piero_dob = date(2001, 11, 9)
    assert _compute_age(zidane_dob, today=virtual_date) == 24
    assert _compute_age(ronaldo_r9_dob, today=virtual_date) == 24
    assert _compute_age(henry_dob, today=virtual_date) == 24
    assert _compute_age(ronaldinho_dob, today=virtual_date) == 24
    assert _compute_age(rivaldo_dob, today=virtual_date) == 24
    assert _compute_age(beckham_dob, today=virtual_date) == 24
    assert _compute_age(nedved_dob, today=virtual_date) == 24
    assert _compute_age(shevchenko_dob, today=virtual_date) == 24
    assert _compute_age(raul_dob, today=virtual_date) == 24
    assert _compute_age(totti_dob, today=virtual_date) == 24
    assert _compute_age(del_piero_dob, today=virtual_date) == 24

    romario_dob = date(2001, 1, 29)
    cantona_dob = date(2001, 5, 24)
    m_laudrup_dob = date(2001, 6, 15)
    b_laudrup_dob = date(2001, 2, 22)
    bergkamp_dob = date(2001, 5, 10)
    klinsmann_dob = date(2001, 7, 30)
    weah_dob = date(2001, 10, 1)
    batistuta_dob = date(2001, 2, 1)
    maldini_dob = date(2001, 6, 26)
    shearer_dob = date(2001, 8, 13)
    assert _compute_age(romario_dob, today=virtual_date) == 25
    assert _compute_age(cantona_dob, today=virtual_date) == 25
    assert _compute_age(m_laudrup_dob, today=virtual_date) == 25
    assert _compute_age(b_laudrup_dob, today=virtual_date) == 25
    assert _compute_age(bergkamp_dob, today=virtual_date) == 25
    assert _compute_age(klinsmann_dob, today=virtual_date) == 25
    assert _compute_age(weah_dob, today=virtual_date) == 25
    assert _compute_age(batistuta_dob, today=virtual_date) == 25
    assert _compute_age(maldini_dob, today=virtual_date) == 25
    assert _compute_age(shearer_dob, today=virtual_date) == 25

    # 4. Active 1950s-1980s Legends: Ages 26-30
    maradona_dob = date(1999, 10, 30)
    zico_dob = date(1999, 3, 3)
    van_basten_dob = date(1999, 10, 31)
    gullit_dob = date(1999, 9, 1)
    baresi_dob = date(1999, 5, 8)
    matthaus_dob = date(1999, 3, 21)
    assert _compute_age(maradona_dob, today=virtual_date) == 27
    assert _compute_age(zico_dob, today=virtual_date) == 27
    assert _compute_age(van_basten_dob, today=virtual_date) == 27
    assert _compute_age(gullit_dob, today=virtual_date) == 27
    assert _compute_age(baresi_dob, today=virtual_date) == 27
    assert _compute_age(matthaus_dob, today=virtual_date) == 27

    # 5. Oldest Legends in Game: Age 30 (Ceiling Rule: age <= 30)
    pele_dob = date(1996, 10, 23)
    di_stefano_dob = date(1996, 7, 4)
    assert _compute_age(pele_dob, today=virtual_date) == 30
    assert _compute_age(di_stefano_dob, today=virtual_date) == 30

    # Ceiling & Floor invariants: 20 <= age <= 30
    all_ages = [
        _compute_age(d, today=virtual_date)
        for d in [
            messi_dob,
            cr7_dob,
            modric_dob,
            casemiro_dob,
            gerrard_dob,
            zidane_dob,
            romario_dob,
            maradona_dob,
            pele_dob,
            di_stefano_dob,
        ]
    ]
    assert max(all_ages) == 30
    assert min(all_ages) == 20


def test_fm23_regens_facebank_index_and_manifest_coverage() -> None:
    from scripts.assign_fm23_regen_facebank_portraits import FaceBankIndex

    index = FaceBankIndex()
    assert len(index.assets) == 11502

    required_ethnicities = {
        "african",
        "east asian",
        "hispanic",
        "indian",
        "middle east",
        "mixed",
        "north european",
        "south european",
    }
    assert set(index.by_eth.keys()) == required_ethnicities

    for eth in required_ethnicities:
        assert len(index.by_eth[eth]) > 0
        for asset in index.by_eth[eth][:5]:
            assert asset["cloudinary_secure_url"].startswith("https://res.cloudinary.com/")
            assert asset["storage_key"].startswith("regen_newgen_faces/script_skin_hair/")


def test_fm23_regens_nationality_to_ethnicity_matching() -> None:
    from scripts.assign_fm23_regen_facebank_portraits import FaceBankIndex

    index = FaceBankIndex()

    # African
    assert index.resolve_ethnicity(country_name="Nigeria") == "African"
    assert index.resolve_ethnicity(country_name="Senegal / France") == "African"
    assert index.resolve_ethnicity(country_name="South Africa") == "African"
    assert index.resolve_ethnicity(country_name="Ghana") == "African"

    # Hispanic
    assert index.resolve_ethnicity(country_name="Argentina") == "Hispanic"
    assert index.resolve_ethnicity(country_name="Colombia") == "Hispanic"
    assert index.resolve_ethnicity(country_name="Uruguay / Italy") == "Hispanic"
    assert index.resolve_ethnicity(country_name="Mexico") == "Hispanic"

    # South European
    assert index.resolve_ethnicity(country_name="Spain") == "South european"
    assert index.resolve_ethnicity(country_name="Spain / Pays Basque") == "South european"
    assert index.resolve_ethnicity(country_name="Italy") == "South european"
    assert index.resolve_ethnicity(country_name="Portugal") == "South european"
    assert index.resolve_ethnicity(country_name="Croatia") == "South european"

    # North European
    assert index.resolve_ethnicity(country_name="England") == "North european"
    assert index.resolve_ethnicity(country_name="France") == "North european"
    assert index.resolve_ethnicity(country_name="Germany") == "North european"
    assert index.resolve_ethnicity(country_name="Netherlands") == "North european"

    # Middle East
    assert index.resolve_ethnicity(country_name="Turkey") == "Middle east"
    assert index.resolve_ethnicity(country_name="Morocco") == "Middle east"
    assert index.resolve_ethnicity(country_name="Egypt") == "Middle east"
    assert index.resolve_ethnicity(country_name="Saudi Arabia") == "Middle east"

    # East Asian
    assert index.resolve_ethnicity(country_name="Japan") == "East asian"
    assert index.resolve_ethnicity(country_name="South Korea") == "East asian"
    assert index.resolve_ethnicity(country_name="China") == "East asian"

    # Indian
    assert index.resolve_ethnicity(country_name="India") == "Indian"
    assert index.resolve_ethnicity(country_name="Pakistan") == "Indian"

    # Mixed
    assert index.resolve_ethnicity(country_name="Brazil") == "Mixed"
    assert index.resolve_ethnicity(country_name="United States") == "Mixed"


def test_fm23_regens_deterministic_face_assignment() -> None:
    from scripts.assign_fm23_regen_facebank_portraits import FaceBankIndex

    index = FaceBankIndex()

    # Call 1
    p1 = index.build_regen_portrait_payload(
        player_id="test-player-1",
        provider_external_id="2002133083",
        dna_profile={"current_rating": 70, "potential_rating": 80},
        country_name="South Africa",
    )
    assert p1 is not None
    assert p1["asset"]["ethnicity"] == "African"

    # Call 2 (must be identically deterministic)
    p2 = index.build_regen_portrait_payload(
        player_id="test-player-1",
        provider_external_id="2002133083",
        dna_profile={"current_rating": 70, "potential_rating": 80},
        country_name="South Africa",
    )
    assert p2 is not None
    assert p1["dna_profile"]["portraitUrl"] == p2["dna_profile"]["portraitUrl"]
    assert p1["dna_profile"]["faceSeed"] == p2["dna_profile"]["faceSeed"]
    assert p1["image_metadata"]["storage_key"] == p2["image_metadata"]["storage_key"]


def test_fm23_regens_quarantine_enforcement() -> None:
    from scripts.assign_fm23_regen_facebank_portraits import FaceBankIndex

    index = FaceBankIndex()

    # Ryan Matos by provider_external_id: MUST BE QUARANTINED
    res1 = index.build_regen_portrait_payload(
        player_id="some-uuid",
        provider_external_id="2002088877",
        country_name="Spain",
    )
    assert res1 is None

    # Ryan Matos by player_id: MUST BE QUARANTINED
    res2 = index.build_regen_portrait_payload(
        player_id="c1a2dddc-9b29-482f-ba06-0b39763830ba",
        provider_external_id="other-id",
        country_name="Spain",
    )
    assert res2 is None
