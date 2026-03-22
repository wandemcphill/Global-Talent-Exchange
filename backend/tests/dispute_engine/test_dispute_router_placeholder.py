from app.dispute_engine.service import DisputeEngineService


def test_dispute_service_symbol_exposed() -> None:
    assert DisputeEngineService is not None
