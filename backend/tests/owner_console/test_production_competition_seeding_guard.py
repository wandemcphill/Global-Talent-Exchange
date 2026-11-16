"""Production environment guard for owner-console competition auto-seeding."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.owner_console import competitions as comps
from app.owner_console.models import OwnerCompetition


def test_ensure_seed_skips_in_production_and_seeds_in_development(
    client,
    app_session_factory,
    auth_user_factory,
    monkeypatch,
) -> None:
    user = auth_user_factory(suffix=f"seed-guard-{uuid4().hex[:8]}")
    seed_names = tuple(spec["name"] for spec in comps.SEED)

    monkeypatch.setenv("GTE_APP_ENV", "production")
    with app_session_factory() as session:
        existing_ids = list(
            session.scalars(select(OwnerCompetition.id).where(OwnerCompetition.name.in_(seed_names))).all()
        )
        for comp_id in existing_ids:
            session.delete(session.get(OwnerCompetition, comp_id))
        session.flush()

        comps.ensure_seed(session)
        seeded_in_prod = session.scalars(select(OwnerCompetition).where(OwnerCompetition.name.in_(seed_names))).all()
        assert seeded_in_prod == []
        session.rollback()

    list_res = client.get("/api/owner/competitions", headers=user["headers"])
    assert list_res.status_code == 200, list_res.text
    returned_names = {item["name"] for item in list_res.json()["competitions"]}
    assert returned_names.isdisjoint(seed_names)

    monkeypatch.setenv("GTE_APP_ENV", "development")
    with app_session_factory() as session:
        comps.ensure_seed(session)
        seeded_in_dev = {
            row.name
            for row in session.scalars(select(OwnerCompetition).where(OwnerCompetition.name.in_(seed_names))).all()
        }
        assert seeded_in_dev == set(seed_names)
        session.rollback()
