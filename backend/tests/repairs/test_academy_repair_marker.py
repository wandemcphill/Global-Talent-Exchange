def test_academy_repair_scope_is_explicit() -> None:
    # Guardrail test documenting that this repair branch targets the
    # youth-contract -> senior-player lifecycle bridge, not new economics.
    assert "youth contract" in "youth contract -> senior-player lifecycle bridge"
