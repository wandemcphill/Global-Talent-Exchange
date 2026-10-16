from app.agents.agent_wallet import AgentWallet


def test_agent_wallet_defaults_to_payout_ineligible() -> None:
    wallet = AgentWallet()
    assert wallet.payout_eligible is False
