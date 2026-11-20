"""Bring staff contract demands down to the reduced scale.

Revision ID: 20261120_0273_staff_contract_demands
Revises: 20261120_0272_retire_sample_launch_competitions

Catalog wages were the old full demand. Real staff keep 35 percent of that
figure. Generated staff follow a lower rating scale, and Carlo Castiglione
asks for 700 Fan Coin. The statements are Postgres-only; SQLite test
databases have no staff rows when this revision runs.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261120_0273_staff_contract_demands"
down_revision = "20261120_0272_retire_sample_launch_competitions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(sa.text("""
            UPDATE club_staff_profiles
            SET salary_minor = GREATEST(100, (salary_minor * 35) / 100),
                metadata_json = CAST(
                    jsonb_set(
                        COALESCE(metadata_json::jsonb, '{}'::jsonb),
                        '{salary_scale}',
                        '"reduced_35"'::jsonb,
                        true
                    ) AS json
                )
            WHERE salary_minor > 0
              AND market_key NOT LIKE 'staff:regen-staff-%'
              AND market_key <> 'staff:mgr_carlo_castiglione'
              AND COALESCE(metadata_json->>'salary_scale', '') <> 'reduced_35'
            """))
    op.execute(sa.text("""
            UPDATE club_staff_profiles
            SET salary_minor = 70000
            WHERE market_key = 'staff:mgr_carlo_castiglione'
            """))
    op.execute(sa.text("""
            UPDATE club_staff_profiles
            SET salary_minor = (
                80 + (LEAST(91, GREATEST(60, COALESCE(rating, 60))) - 60) * 11
            ) * 100
            WHERE market_key LIKE 'staff:regen-staff-%'
              AND salary_minor > 0
            """))


def downgrade() -> None:
    """The previous demands are not stored, so this revision does not restore them."""
