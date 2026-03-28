from __future__ import annotations

from decimal import Decimal

from app.models.risk_ops import RiskActionType
from app.risk_ops_engine.service import RiskActionBlockedError, RiskOpsService


def test_signal_evaluation_flags_multi_account_and_fake_deposit(service: RiskOpsService) -> None:
    service.ingest_signal(
        actor_user_id="admin-user",
        user_id="user-alpha",
        signal_type="device_id",
        signal_value="shared-device",
        source="analytics",
    )
    service.ingest_signal(
        actor_user_id="admin-user",
        user_id="user-bravo",
        signal_type="device_id",
        signal_value="shared-device",
        source="analytics",
    )
    service.ingest_signal(
        actor_user_id="admin-user",
        user_id="user-alpha",
        signal_type="transaction_pattern",
        signal_key="fake_deposit",
        signal_value="duplicate_reference",
        source="payments",
        confidence_score=Decimal("99.00"),
        metadata_json={"fake_deposit": True, "duplicate_deposit": True},
    )

    result = service.evaluate_signals(admin_user_id="admin-user")

    alpha_cases = service.list_fraud_cases(user_id="user-alpha")
    bravo_cases = service.list_fraud_cases(user_id="user-bravo")
    alpha_restrictions = service.get_user_restrictions("user-alpha")
    bravo_restrictions = service.get_user_restrictions("user-bravo")

    assert result["users_flagged"] == 2
    assert {case.fraud_type for case in alpha_cases} == {"multi_account_farming", "fake_deposit"}
    assert {case.fraud_type for case in bravo_cases} == {"multi_account_farming"}
    assert alpha_restrictions["wallet_frozen"] is True
    assert alpha_restrictions["withdrawals_blocked"] is True
    assert bravo_restrictions["manual_review_required"] is True


def test_signal_evaluation_blocks_trading_for_rapid_loops_and_collusion(service: RiskOpsService) -> None:
    service.ingest_signal(
        actor_user_id="admin-user",
        user_id="user-alpha",
        signal_type="match_behavior",
        signal_key="win_rate",
        signal_value="0.95",
        source="match_engine",
        metadata_json={"win_rate": "0.95", "sample_size": 12, "repeated_opponent_rate": "0.80"},
    )
    service.ingest_signal(
        actor_user_id="admin-user",
        user_id="user-alpha",
        signal_type="transaction_pattern",
        signal_key="rapid_trade_loop",
        signal_value="burst-loop",
        source="market",
        metadata_json={"loop_count": 8, "window_minutes": 10},
    )

    result = service.evaluate_signals(admin_user_id="admin-user", user_id="user-alpha")
    restrictions = service.get_user_restrictions("user-alpha")
    active_action_types = {item.action_type for item in restrictions["active_actions"]}

    assert result["users_flagged"] == 1
    assert restrictions["trading_blocked"] is True
    assert restrictions["manual_review_required"] is True
    assert RiskActionType.BLOCK_TRADING in active_action_types
    assert RiskActionType.MANUAL_REVIEW in active_action_types

    try:
        service.assert_trading_allowed("user-alpha")
    except RiskActionBlockedError:
        blocked = True
    else:
        blocked = False
    assert blocked is True
