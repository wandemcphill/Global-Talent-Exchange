"""Production environment guard for owner-console competition auto-seeding."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.owner_console import competitions as comps
from app.owner_console.models import OwnerCompetition


def test_sample_launch_competitions_are_retired_in_every_environment(
    client,
    app_session_factory,
    auth_user_factory,
    monkeypatch,
) -> None:
    user = auth_user_factory(suffix=f"seed-guard-{uuid4().hex[:8]}")
    seed_names = tuple(spec["name"] for spec in comps.SEED)

    for env_name in ("production", "development"):
        monkeypatch.setenv("GTE_APP_ENV", env_name)
        with app_session_factory() as session:
            for comp_id in session.scalars(select(OwnerCompetition.id).where(OwnerCompetition.name.in_(seed_names))).all():
                session.delete(session.get(OwnerCompetition, comp_id))
            session.flush()
            session.add(
                OwnerCompetition(
                    name=seed_names[0],
                    host_type="gtex",
                    format="league",
                    tier="Launch",
                    entry_fee=0,
                    max_clubs=6,
                    status="open",
                    description="Sample competition that should not be offered.",
                )
            )
            session.flush()
            comps.ensure_seed(session)
            rows = session.scalars(select(OwnerCompetition).where(OwnerCompetition.name.in_(seed_names))).all()
            assert rows
            assert all(row.status == "cancelled" for row in rows)
            session.rollback()

    list_res = client.get("/api/owner/competitions", headers=user["headers"])
    assert list_res.status_code == 200, list_res.text
    returned_names = {item["name"] for item in list_res.json()["competitions"]}
    assert returned_names.isdisjoint(seed_names)
