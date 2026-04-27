"""Add national regen age bands and relax rental player foreign keys.

Revision ID: 20260423_0085_national_regen_age_bands_and_pool_ids
Revises: 20260412_0084_runtime_index_coverage_repair
Create Date: 2026-04-23 10:00:00.000000
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "20260423_0085_national_regen_age_bands_and_pool_ids"
down_revision = "20260412_0084_runtime_index_coverage_repair"
branch_labels = None
depends_on = None

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
CONTRACT_PLAYER_FK_NAME = "fk_national_team_rental_contracts_player_id_ingestion_players"
SQUAD_MEMBER_PLAYER_FK_NAME = "fk_national_team_rental_squad_members_player_id_ingesti_a300"


def _column_names(bind, table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _create_index_if_missing(bind, *, table_name: str, index_name: str, columns: list[str]) -> None:
    if index_name in _index_names(bind, table_name):
        return
    op.create_index(index_name, table_name, columns, unique=False)


def _has_player_fk(bind, table_name: str) -> bool:
    return (
        _get_foreign_key(
            bind,
            table_name,
            constrained_columns=("player_id",),
            referred_table="ingestion_players",
        )
        is not None
    )


def _get_foreign_key(
    bind, table_name: str, *, constrained_columns: tuple[str, ...], referred_table: str
) -> dict | None:
    for foreign_key in sa.inspect(bind).get_foreign_keys(table_name):
        if (
            tuple(foreign_key.get("constrained_columns") or ()) == constrained_columns
            and foreign_key.get("referred_table") == referred_table
        ):
            return foreign_key
    return None


def _metadata_dict(value) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(loaded) if isinstance(loaded, dict) else {}
    return {}


def _infer_seed_age(*, metadata: dict[str, object], preseed_batch: str | None) -> int:
    explicit_age = metadata.get("age")
    if isinstance(explicit_age, int):
        return explicit_age
    position_slot = metadata.get("position_slot")
    if isinstance(position_slot, int) and position_slot >= 1:
        if preseed_batch == "u17_batch":
            return 14 + ((position_slot - 1) % 4)
        if preseed_batch == "u20_batch":
            return 18 + ((position_slot - 1) % 3)
        return 17 + ((position_slot - 1) % 4)
    return 18


def _infer_age_band(*, age: int, metadata: dict[str, object], preseed_batch: str | None) -> str:
    metadata_band = str(metadata.get("age_band") or "").strip().lower()
    if metadata_band in {"u17", "u20", "senior"}:
        return metadata_band
    if preseed_batch == "u17_batch":
        return "u17"
    if preseed_batch == "u20_batch":
        return "u20"
    if age <= 17:
        return "u17"
    if age <= 20:
        return "u20"
    return "senior"


def _backfill_national_regen_seed_age_columns(bind) -> None:
    columns = _column_names(bind, "national_regen_seeds")
    if "age" not in columns or "age_band" not in columns:
        return
    rows = bind.execute(
        sa.text("SELECT id, age, age_band, preseed_batch, metadata_json FROM national_regen_seeds")
    ).mappings()
    for row in rows:
        metadata = _metadata_dict(row.get("metadata_json"))
        age = row.get("age")
        if age is None:
            age = _infer_seed_age(metadata=metadata, preseed_batch=row.get("preseed_batch"))
        age_band = row.get("age_band")
        if not age_band:
            age_band = _infer_age_band(age=int(age), metadata=metadata, preseed_batch=row.get("preseed_batch"))
        bind.execute(
            sa.text("UPDATE national_regen_seeds SET age = :age, age_band = :age_band WHERE id = :id"),
            {"id": row["id"], "age": int(age), "age_band": str(age_band)},
        )


def _drop_player_fk(table_name: str, *, constraint_name: str) -> None:
    with op.batch_alter_table(
        table_name,
        recreate="always",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.drop_constraint(constraint_name, type_="foreignkey")


def _restore_player_fk(table_name: str, *, constraint_name: str) -> None:
    with op.batch_alter_table(
        table_name,
        recreate="always",
        naming_convention=NAMING_CONVENTION,
    ) as batch_op:
        batch_op.create_foreign_key(
            constraint_name,
            "ingestion_players",
            ["player_id"],
            ["id"],
            ondelete="CASCADE",
        )


def _drop_foreign_key(table_name: str, *, constraint_name: str) -> None:
    op.drop_constraint(constraint_name, table_name, type_="foreignkey")


def _restore_foreign_key(table_name: str, *, foreign_key: dict) -> None:
    constraint_name = str(foreign_key.get("name") or "").strip()
    if not constraint_name:
        raise RuntimeError(f"Expected named foreign key on {table_name}.")

    local_columns = [str(column) for column in foreign_key.get("constrained_columns") or ()]
    remote_table = str(foreign_key.get("referred_table") or "").strip()
    remote_columns = [str(column) for column in foreign_key.get("referred_columns") or ()]
    options = foreign_key.get("options") if isinstance(foreign_key.get("options"), dict) else {}
    kwargs = {"ondelete": options.get("ondelete")} if options and options.get("ondelete") else {}

    op.create_foreign_key(
        constraint_name,
        table_name,
        remote_table,
        local_columns,
        remote_columns,
        **kwargs,
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    contract_player_fk = (
        _get_foreign_key(
            bind,
            "national_team_rental_contracts",
            constrained_columns=("player_id",),
            referred_table="ingestion_players",
        )
        if inspector.has_table("national_team_rental_contracts")
        else None
    )
    squad_member_player_fk = (
        _get_foreign_key(
            bind,
            "national_team_rental_squad_members",
            constrained_columns=("player_id",),
            referred_table="ingestion_players",
        )
        if inspector.has_table("national_team_rental_squad_members")
        else None
    )
    rental_contract_fk = (
        _get_foreign_key(
            bind,
            "national_team_rental_squad_members",
            constrained_columns=("rental_contract_id",),
            referred_table="national_team_rental_contracts",
        )
        if contract_player_fk is not None and inspector.has_table("national_team_rental_squad_members")
        else None
    )

    if inspector.has_table("national_regen_seeds"):
        columns = _column_names(bind, "national_regen_seeds")
        with op.batch_alter_table("national_regen_seeds", recreate="auto") as batch_op:
            if "age" not in columns:
                batch_op.add_column(sa.Column("age", sa.Integer(), nullable=False, server_default="18"))
            if "age_band" not in columns:
                batch_op.add_column(
                    sa.Column("age_band", sa.String(length=16), nullable=False, server_default="senior")
                )
        _backfill_national_regen_seed_age_columns(bind)
        _create_index_if_missing(
            bind,
            table_name="national_regen_seeds",
            index_name="ix_national_regen_seeds_age_band",
            columns=["age_band"],
        )
        _create_index_if_missing(
            bind,
            table_name="national_regen_seeds",
            index_name="ix_national_regen_seeds_country_age_band_position_status",
            columns=["country_code", "age_band", "primary_position", "status"],
        )

    if rental_contract_fk is not None:
        _drop_foreign_key(
            "national_team_rental_squad_members",
            constraint_name=str(rental_contract_fk["name"]),
        )
    if contract_player_fk is not None:
        _drop_player_fk(
            "national_team_rental_contracts",
            constraint_name=str(contract_player_fk["name"]),
        )
    if squad_member_player_fk is not None:
        _drop_player_fk(
            "national_team_rental_squad_members",
            constraint_name=str(squad_member_player_fk["name"]),
        )
    if rental_contract_fk is not None:
        _restore_foreign_key("national_team_rental_squad_members", foreign_key=rental_contract_fk)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    contract_player_fk_missing = inspector.has_table("national_team_rental_contracts") and not _has_player_fk(
        bind, "national_team_rental_contracts"
    )
    rental_contract_fk = (
        _get_foreign_key(
            bind,
            "national_team_rental_squad_members",
            constrained_columns=("rental_contract_id",),
            referred_table="national_team_rental_contracts",
        )
        if contract_player_fk_missing and inspector.has_table("national_team_rental_squad_members")
        else None
    )

    if rental_contract_fk is not None:
        _drop_foreign_key(
            "national_team_rental_squad_members",
            constraint_name=str(rental_contract_fk["name"]),
        )
    if inspector.has_table("national_team_rental_squad_members") and not _has_player_fk(
        bind, "national_team_rental_squad_members"
    ):
        _restore_player_fk(
            "national_team_rental_squad_members",
            constraint_name=SQUAD_MEMBER_PLAYER_FK_NAME,
        )
    if contract_player_fk_missing:
        _restore_player_fk(
            "national_team_rental_contracts",
            constraint_name=CONTRACT_PLAYER_FK_NAME,
        )
    if rental_contract_fk is not None:
        _restore_foreign_key("national_team_rental_squad_members", foreign_key=rental_contract_fk)

    if inspector.has_table("national_regen_seeds"):
        if "ix_national_regen_seeds_country_age_band_position_status" in _index_names(bind, "national_regen_seeds"):
            op.drop_index(
                "ix_national_regen_seeds_country_age_band_position_status",
                table_name="national_regen_seeds",
            )
        if "ix_national_regen_seeds_age_band" in _index_names(bind, "national_regen_seeds"):
            op.drop_index("ix_national_regen_seeds_age_band", table_name="national_regen_seeds")
        columns = _column_names(bind, "national_regen_seeds")
        with op.batch_alter_table("national_regen_seeds", recreate="auto") as batch_op:
            if "age_band" in columns:
                batch_op.drop_column("age_band")
            if "age" in columns:
                batch_op.drop_column("age")
