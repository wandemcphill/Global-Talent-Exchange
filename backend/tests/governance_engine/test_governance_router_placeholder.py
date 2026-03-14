from backend.app.governance_engine.service import GovernanceEngineService


def test_governance_service_symbol_exposed() -> None:
    assert GovernanceEngineService is not None
