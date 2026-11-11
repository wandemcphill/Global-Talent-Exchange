from app.owner_console.showroom_inspection import inspection_reel


def test_sovereign_inspection_includes_the_cabin_and_lavatory() -> None:
    labels = [frame["label"] for frame in inspection_reel("sovereign_900x_jet")]
    assert "Cockpit" in labels
    assert "Cabin seats" in labels
    assert "Lavatory" in labels
    assert "Cabin walk" in labels
    reel = inspection_reel("sovereign_900x_jet")
    assert any(frame["kind"] == "video" and frame["src"].endswith("gtex-lux-jet-cabin-walk.mp4") for frame in reel)


def test_hypercar_inspection_includes_the_cabin() -> None:
    labels = [frame["label"] for frame in inspection_reel("veloce_gt9_hypercar")]
    assert "Cabin" in labels
    assert "Cabin walk" in labels


def test_unknown_item_has_no_reel() -> None:
    assert inspection_reel("not_a_luxury_item") == []
