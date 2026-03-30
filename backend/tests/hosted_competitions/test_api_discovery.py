from __future__ import annotations

from decimal import Decimal

from sqlalchemy import event

from app.hosted_competition_engine.service import HostedCompetitionService
from app.models.hosted_competition import HostedCompetitionStatus, UserHostedCompetition


def test_hosted_discovery_route_bypasses_lazy_module_hydration(app, client) -> None:
    assert app.state.modules_hydrated is False

    response = client.get("/hosted-competitions")

    assert response.status_code == 200
    assert response.json() == {"competitions": []}
    assert app.state.modules_hydrated is False


def test_hosted_discovery_query_budget_stays_single_pass(app_session_factory) -> None:
    with app_session_factory() as session:
        service = HostedCompetitionService(session)
        service.seed_defaults()
        template = service.get_template_by_key("queue-cup")
        assert template is not None
        session.add(
            UserHostedCompetition(
                template_id=template.id,
                host_user_id="hosted-discovery-host",
                title="Hosted Queue Cup",
                slug="hosted-queue-cup",
                description="Fast hosted discovery perf fixture.",
                status=HostedCompetitionStatus.OPEN,
                visibility="public",
                max_participants=4,
                entry_fee_fancoin=Decimal("100.0000"),
                reward_pool_fancoin=Decimal("320.0000"),
                platform_fee_amount=Decimal("80.0000"),
                metadata_json={"family": "hosted"},
            )
        )
        session.commit()

    query_count = 0

    def _count_query(*_args, **_kwargs) -> None:
        nonlocal query_count
        query_count += 1

    with app_session_factory() as session:
        bind = session.bind
        assert bind is not None
        event.listen(bind, "after_cursor_execute", _count_query)
        try:
            competitions = HostedCompetitionService(session).list_public_competitions()
        finally:
            event.remove(bind, "after_cursor_execute", _count_query)

    assert [competition.title for competition in competitions] == ["Hosted Queue Cup"]
    assert query_count <= 1
