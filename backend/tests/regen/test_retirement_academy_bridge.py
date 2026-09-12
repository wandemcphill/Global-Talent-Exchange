from __future__ import annotations

from app.regen_career.retirement_academy_bridge import (
    RegenRetirementAcademyBridge,
    RetirementAcademyBridgeResult,
)


def test_bridge_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("GTE_REGEN_LEGACY_INTAKE_ENABLED", raising=False)
    assert not RegenRetirementAcademyBridge.enabled()


def test_bridge_returns_pending_without_writing_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("GTE_REGEN_LEGACY_INTAKE_ENABLED", raising=False)
    result = RegenRetirementAcademyBridge(session=None).consume(
        state={"legacy_intake_plan": {"trigger_key": "regen-retirement:r:c"}}
    )
    assert isinstance(result, RetirementAcademyBridgeResult)
    assert result.status == "pending"
    assert result.trigger_key == "regen-retirement:r:c"


def test_bridge_uses_explicit_enable_flag(monkeypatch) -> None:
    monkeypatch.setenv("GTE_REGEN_LEGACY_INTAKE_ENABLED", "true")
    assert RegenRetirementAcademyBridge.enabled()
