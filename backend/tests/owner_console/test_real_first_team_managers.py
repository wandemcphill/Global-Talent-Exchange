from app.manager_market.seed_catalog import CATALOG_VERSION, build_seed_catalog
from app.owner_console.engine import EXECUTIVE_STAFF_CATALOG
from app.owner_console.real_first_team_managers import canon_fold


def _first_team(name: str) -> dict:
    folded = canon_fold(name)
    matches = [
        item
        for item in EXECUTIVE_STAFF_CATALOG
        if item.get("role") == "first_team_manager" and canon_fold(item.get("name")) == folded
    ]
    assert matches, name
    return matches[0]


def test_staff_market_hires_missing_real_managers() -> None:
    ferguson = _first_team("Sir Alex Ferguson")
    arteta = _first_team("Mikel Arteta")
    scaloni = _first_team("Lionel Scaloni")
    keshi = _first_team("Stephen Keshi")
    paisley = _first_team("Bob Paisley")
    inzaghi = _first_team("Simone Inzaghi")
    bompastor = _first_team("Sonia Bompastor")
    cruyff = _first_team("Johan Cruyff")

    assert ferguson["rating"] == 96
    assert ferguson["salary_fan_coin"] == ferguson["salary"]
    assert ferguson["salary_fan_coin"] > 1500
    assert ferguson["nation"] == "Scotland"
    assert arteta["rating"] == 88
    assert arteta["nation"] == "Spain"
    assert scaloni["preferred_formation"] == "4-3-3"
    assert scaloni["rarity"] == "elite"
    assert keshi["rarity"] == "legendary"
    assert paisley["real_club"] == "Liverpool"
    assert "Boot Room" in paisley["style"]
    assert inzaghi["preferred_formation"] == "3-5-2"
    assert bompastor["gender"] == "female"
    assert str(ferguson["portrait_url"]).startswith("/staff-portraits/real/")
    assert str(bompastor["portrait_url"]).startswith("/staff-portraits/real/")
    assert "mature_" not in str(ferguson["portrait_url"])
    assert ferguson["portrait_url"] == _first_team("Sir Alex Ferguson")["portrait_url"]
    tunde = next(item for item in EXECUTIVE_STAFF_CATALOG if item.get("id") == "gtex-staff-coach")
    assert "mature_" in str(tunde["portrait_url"])
    regen = next(item for item in EXECUTIVE_STAFF_CATALOG if str(item.get("id") or "").startswith("regen-staff-"))
    assert str(regen["portrait_url"]).startswith("/staff-portraits/mature_")
    assert cruyff["rating"] >= 94
    assert "high defensive line" in cruyff["bio"]

    scolari = [item for item in EXECUTIVE_STAFF_CATALOG if canon_fold(item.get("name")) == "luiz felipe scolari"]
    assert any(item.get("role") == "first_team_manager" for item in scolari)

    ids = [item.get("id") for item in EXECUTIVE_STAFF_CATALOG]
    assert len(ids) == len(set(ids))
    real_ids = [item_id for item_id in ids if str(item_id).startswith("mgr_real_")]
    assert len(real_ids) >= 120


def test_seed_catalog_keeps_one_of_each_real_manager() -> None:
    catalog = build_seed_catalog()
    folds = [canon_fold(item["name"]) for item in catalog]

    assert CATALOG_VERSION >= 10
    assert folds.count("sir alex ferguson") == 1
    assert folds.count("xavi hernandez") == 1
    assert folds.count("gernot rohr") == 1
    assert folds.count("guus hiddink") == 1
    assert "gus hiddink" not in folds
    assert "lionel scaloni" in folds
    assert "bob paisley" in folds
    assert "stephen keshi" in folds
    scaloni = next(item for item in catalog if canon_fold(item["name"]) == "lionel scaloni")
    assert scaloni["supply_total"] == 1
    assert scaloni["rarity"] == "elite_active"
