"""Add player summary current value index for discovery performance.

Revision ID: 20261103_0220_add_player_summary_current_val_indexes
Revises: 20261103_0219_search_performance_and_unaccent_indexes
Create Date: 2026-11-03 11:20:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20261103_0220_add_player_summary_current_val_indexes"
down_revision = "20261103_0219_search_performance_and_unaccent_indexes"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
    if dialect_name == "postgresql":
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_player_summary_current_val 
            ON player_summary_read_models (current_value_credits DESC);
            """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_player_summary_curr_val_pid 
            ON player_summary_read_models (current_value_credits DESC NULLS LAST, player_id ASC);
            """)


def downgrade():
    bind = op.get_bind()
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "")
    if dialect_name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_player_summary_curr_val_pid;")
        op.execute("DROP INDEX IF EXISTS ix_player_summary_current_val;")
