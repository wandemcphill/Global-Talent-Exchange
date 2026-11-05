"""Enforce database-level relationship pair uniqueness and deduplicate preserving history.

Revision ID: 20261105_0226_phase2_4_relationship_pair_uniqueness
Revises: 20261105_0225_phase2_4_living_club_world_events_relationships
Create Date: 2026-11-05 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261105_0226_phase2_4_relationship_pair_uniqueness"
down_revision = "20261105_0225_phase2_4_living_club_world_events_relationships"
branch_labels = None
depends_on = None


def _canonical_pair(part_a_id: str, part_b_id: str) -> tuple[str, str]:
    a = str(part_a_id or "").strip()
    b = str(part_b_id or "").strip()
    return (a, b) if a <= b else (b, a)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "owner_club_relationships" not in tables:
        return

    # 1. Inspect existing relationship rows and reconcile any duplicate or reversed pairs
    rel_table = sa.table(
        "owner_club_relationships",
        sa.column("id", sa.String),
        sa.column("club_id", sa.String),
        sa.column("pairing_key", sa.String),
        sa.column("participant_a_type", sa.String),
        sa.column("participant_a_id", sa.String),
        sa.column("participant_a_name", sa.String),
        sa.column("participant_b_type", sa.String),
        sa.column("participant_b_id", sa.String),
        sa.column("participant_b_name", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    hist_table = sa.table(
        "owner_club_relationship_history",
        sa.column("id", sa.String),
        sa.column("relationship_id", sa.String),
    )

    rows = conn.execute(
        sa.select(
            rel_table.c.id,
            rel_table.c.club_id,
            rel_table.c.pairing_key,
            rel_table.c.participant_a_type,
            rel_table.c.participant_a_id,
            rel_table.c.participant_a_name,
            rel_table.c.participant_b_type,
            rel_table.c.participant_b_id,
            rel_table.c.participant_b_name,
        ).order_by(rel_table.c.created_at.asc(), rel_table.c.id.asc())
    ).fetchall()

    seen_by_pair: dict[tuple[str, str], str] = {}
    for row in rows:
        p1, p2 = _canonical_pair(row.participant_a_id, row.participant_b_id)
        canonical_key = f"{row.club_id}:{p1}:{p2}"
        pair_tuple = (row.club_id, canonical_key)

        if pair_tuple not in seen_by_pair:
            seen_by_pair[pair_tuple] = row.id
            # Normalize participant ordering and pairing_key in place if reversed
            if row.pairing_key != canonical_key or row.participant_a_id != p1:
                if p1 == row.participant_a_id:
                    conn.execute(rel_table.update().where(rel_table.c.id == row.id).values(pairing_key=canonical_key))
                else:
                    conn.execute(
                        rel_table.update()
                        .where(rel_table.c.id == row.id)
                        .values(
                            pairing_key=canonical_key,
                            participant_a_type=row.participant_b_type,
                            participant_a_id=row.participant_b_id,
                            participant_a_name=row.participant_b_name,
                            participant_b_type=row.participant_a_type,
                            participant_b_id=row.participant_a_id,
                            participant_b_name=row.participant_a_name,
                        )
                    )
        else:
            canonical_id = seen_by_pair[pair_tuple]
            if "owner_club_relationship_history" in tables:
                conn.execute(
                    hist_table.update()
                    .where(hist_table.c.relationship_id == row.id)
                    .values(relationship_id=canonical_id)
                )
            conn.execute(rel_table.delete().where(rel_table.c.id == row.id))

    # 2. Enforce database-level uniqueness on (club_id, pairing_key)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("owner_club_relationships")}
    existing_uqs = {uq["name"] for uq in inspector.get_unique_constraints("owner_club_relationships") if uq.get("name")}

    if (
        "uq_owner_club_relationships_club_pairing" not in existing_indexes
        and "uq_owner_club_relationships_club_pairing" not in existing_uqs
    ):
        op.create_index(
            "uq_owner_club_relationships_club_pairing",
            "owner_club_relationships",
            ["club_id", "pairing_key"],
            unique=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "owner_club_relationships" in inspector.get_table_names():
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("owner_club_relationships")}
        if "uq_owner_club_relationships_club_pairing" in existing_indexes:
            op.drop_index("uq_owner_club_relationships_club_pairing", table_name="owner_club_relationships")
