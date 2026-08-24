from __future__ import annotations

from app.scripts.audit_player_share_lifecycle import classify_market


def test_explicit_issue_is_not_auto_initialized() -> None:
    state = classify_market(
        status="active",
        eligible=True,
        metadata={
            "market_issued": True,
            "issued_by_user_id": "admin-1",
            "auto_initialized": False,
        },
    )
    assert state["explicitly_issued"] is True
    assert state["auto_initialized"] is False
    assert state["legacy_active"] is False


def test_auto_initialized_active_market_is_flagged() -> None:
    state = classify_market(
        status="active",
        eligible=True,
        metadata={
            "market_issued": True,
            "auto_initialized": True,
        },
    )
    assert state["auto_initialized"] is True
    assert state["explicitly_issued"] is False
    assert state["legacy_active"] is True


def test_ineligible_active_market_is_blocked() -> None:
    state = classify_market(
        status="active",
        eligible=False,
        metadata={
            "market_issued": True,
            "issued_by_user_id": "admin-1",
            "auto_initialized": False,
        },
    )
    assert state["blocked_active"] is True
    assert state["explicitly_issued"] is True


def test_closed_market_does_not_trigger_active_gates() -> None:
    state = classify_market(
        status="closed",
        eligible=False,
        metadata={"auto_initialized": True},
    )
    assert state["active"] is False
    assert state["blocked_active"] is False
