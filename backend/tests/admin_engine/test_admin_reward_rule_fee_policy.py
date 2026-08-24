from app.admin_engine.schemas import AdminRewardRuleUpsertRequest


def test_competition_fee_policy_defaults_to_thirty_percent() -> None:
    payload = AdminRewardRuleUpsertRequest(
        rule_key="default",
        title="Default",
    )
    assert payload.competition_platform_fee_bps == 3000


def test_admin_can_edit_competition_fee_policy() -> None:
    payload = AdminRewardRuleUpsertRequest(
        rule_key="custom",
        title="Custom",
        competition_platform_fee_bps=1250,
    )
    assert payload.competition_platform_fee_bps == 1250
