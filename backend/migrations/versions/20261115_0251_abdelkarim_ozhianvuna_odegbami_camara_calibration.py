"""Calibrate Hamza Abdelkarim, Victor Ozhianvuna, Segun Odegbami, and Lamine Camara.

Updates:
1. Hamza Abdelkarim -> GSI 73, Potential 84
2. Victor Ozhianvuna -> GSI 74, Potential 86, Position CM/AM/LM/LW, Right-footed
3. Segun Odegbami -> Position RW/RM/LW/LM/AM/ST, Right-footed, Mathematical Dribbling + Goal Sense
4. Lamine Camara -> GSI 83, Potential 90

Revision ID: 20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration
Revises: 20261115_0250_academy_first_team_minutes
"""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "20261115_0251_abdelkarim_ozhianvuna_odegbami_camara_calibration"
down_revision = "20261115_0250_academy_first_team_minutes"
branch_labels = None
depends_on = None

HAMZA_ID = "d3d75031-9136-470a-a98e-4d3e13cac3b2"
VICTOR_ID = "30227832-9cfd-4529-92f0-2dbde53a937e"
ODEGBAMI_ID = "c477096f-c848-4d33-84fc-055bf3063eb8"
CAMARA_ACTIVE_ID = "746a2331-aa04-440e-9fac-59e6f1c98002"
CAMARA_DUPLICATE_ID = "4f9aa9f1-e043-4eef-8c77-4b135e49d084"


def _calc_price(cur: int, pot: int) -> float:
    eval_gsi = 0.40 * cur + 0.60 * pot
    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)
    if eval_gsi <= 70.0:
        base_price *= 0.40
    elif eval_gsi < 75.0:
        t = (eval_gsi - 70.0) / 5.0
        base_price *= 0.40 + 0.60 * t
    return round(base_price, 2)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            loaded = json.loads(value)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            return {}
    return {}


def _merge_attributes(existing: Any, patch: dict[str, Any]) -> dict[str, Any]:
    merged = _as_dict(existing)
    merged.update(patch)
    return merged


def _update_ingestion_and_read_models(
    conn: sa.Connection,
    *,
    player_id: str,
    cur_gsi: int | None = None,
    pot_gsi: int | None = None,
    position: str | None = None,
    normalized_position: str | None = None,
    secondary_positions: list[str] | None = None,
    preferred_foot: str | None = None,
    real_player_tier: str | None = None,
    override_reason: str | None = None,
    playstyle: str | None = None,
    traits: list[str] | None = None,
    core_attrs: dict[str, int] | None = None,
    extra_attrs: dict[str, int] | None = None,
    position_display: str | None = None,
    all_positions: list[str] | None = None,
    new_price: float | None = None,
) -> None:
    row = conn.execute(
        sa.text(
            """
            SELECT id, governed_gsi, governed_potential_gsi, potential, dna_profile
            FROM ingestion_players
            WHERE id = :pid
            """
        ),
        {"pid": player_id},
    ).mappings().first()
    if row is None:
        return

    dna = _as_dict(row["dna_profile"])
    full_attrs = _merge_attributes(dna.get("attributes"), {**(core_attrs or {}), **(extra_attrs or {})})

    if cur_gsi is not None:
        dna["overall"] = cur_gsi
        dna["current_rating"] = cur_gsi
    if pot_gsi is not None:
        dna["potential"] = pot_gsi
        dna["potential_rating"] = pot_gsi
    if position is not None:
        dna["position"] = position
    if normalized_position is not None:
        dna["normalized_position"] = normalized_position
    if secondary_positions is not None:
        dna["secondary_positions"] = list(secondary_positions)
    if all_positions is not None:
        dna["positions"] = list(all_positions)
    if position_display is not None:
        dna["position_display"] = position_display
    if preferred_foot is not None:
        dna["preferred_foot"] = preferred_foot
    if playstyle is not None:
        dna["playstyle"] = playstyle
    if traits is not None:
        dna["traits"] = list(traits)
        dna["skills"] = list(traits)
    if core_attrs:
        for k, v in core_attrs.items():
            dna[k] = v
    if full_attrs:
        dna["attributes"] = full_attrs

    set_clauses = ["dna_profile = CAST(:dna AS json)", "updated_at = NOW()"]
    params: dict[str, Any] = {"pid": player_id, "dna": json.dumps(dna)}

    if cur_gsi is not None:
        set_clauses.append("governed_gsi = :cur_gsi")
        params["cur_gsi"] = cur_gsi
    if pot_gsi is not None:
        set_clauses.extend(["governed_potential_gsi = :pot_gsi", "potential = :pot_gsi"])
        params["pot_gsi"] = pot_gsi
    if position is not None:
        set_clauses.append("position = :position")
        params["position"] = position
    if normalized_position is not None:
        set_clauses.append("normalized_position = :norm_pos")
        params["norm_pos"] = normalized_position
    if secondary_positions is not None:
        set_clauses.append("secondary_positions_json = CAST(:sec_pos AS json)")
        params["sec_pos"] = json.dumps(secondary_positions)
    if preferred_foot is not None:
        set_clauses.append("preferred_foot = :foot")
        params["foot"] = preferred_foot
    if real_player_tier is not None:
        set_clauses.append("real_player_tier = :tier")
        params["tier"] = real_player_tier
    if override_reason is not None:
        set_clauses.append("gsi_override_reason = :reason")
        params["reason"] = override_reason

    conn.execute(
        sa.text(f"UPDATE ingestion_players SET {', '.join(set_clauses)} WHERE id = :pid"),
        params,
    )

    # Update player_summary_read_models
    rm_row = conn.execute(
        sa.text(
            """
            SELECT player_id, current_value_credits, summary_json
            FROM player_summary_read_models
            WHERE player_id = :pid
            """
        ),
        {"pid": player_id},
    ).mappings().first()
    if rm_row is not None:
        summary = _as_dict(rm_row["summary_json"])
        if cur_gsi is not None:
            summary["gsi"] = cur_gsi
            summary["overall"] = cur_gsi
            summary["global_scouting_index"] = cur_gsi
            summary["current_rating"] = cur_gsi
        if pot_gsi is not None:
            summary["potential"] = pot_gsi
            summary["potential_gsi"] = pot_gsi
        if position is not None:
            summary["position"] = position
        if normalized_position is not None:
            summary["normalized_position"] = normalized_position
        if secondary_positions is not None:
            summary["secondary_positions"] = list(secondary_positions)
        if all_positions is not None:
            summary["positions"] = list(all_positions)
        if position_display is not None:
            summary["position_display"] = position_display
        if preferred_foot is not None:
            summary["preferred_foot"] = preferred_foot
        if real_player_tier is not None:
            summary["real_player_tier"] = real_player_tier
            if isinstance(summary.get("real_player_profile"), dict):
                summary["real_player_profile"] = {
                    **summary["real_player_profile"],
                    "real_player_tier": real_player_tier,
                }
        if playstyle is not None:
            summary["playstyle"] = playstyle
        if traits is not None:
            summary["traits"] = list(traits)
            summary["skills"] = list(traits)
        if full_attrs:
            summary["attributes"] = full_attrs
        if new_price is not None:
            summary["share_price_coin"] = new_price

        rm_sets = ["summary_json = CAST(:summary AS json)", "updated_at = NOW()"]
        rm_params: dict[str, Any] = {"pid": player_id, "summary": json.dumps(summary)}
        if cur_gsi is not None:
            rm_sets.append("market_interest_score = :mis")
            rm_params["mis"] = cur_gsi
        if new_price is not None:
            old_val = rm_row["current_value_credits"]
            prev_val = float(old_val) if old_val is not None else new_price
            movement_pct = round(((new_price - prev_val) / prev_val) * 100.0, 4) if prev_val > 0 else 0.0
            rm_sets.extend(
                [
                    "previous_value_credits = :prev_val",
                    "current_value_credits = :cur_val",
                    "movement_pct = :mov_pct",
                ]
            )
            rm_params["prev_val"] = prev_val
            rm_params["cur_val"] = new_price
            rm_params["mov_pct"] = movement_pct

        conn.execute(
            sa.text(f"UPDATE player_summary_read_models SET {', '.join(rm_sets)} WHERE player_id = :pid"),
            rm_params,
        )

    # Update player_share_markets
    mkt_row = conn.execute(
        sa.text(
            """
            SELECT id, circulating_shares, metadata_json
            FROM player_share_markets
            WHERE player_id = :pid
            """
        ),
        {"pid": player_id},
    ).mappings().first()
    if mkt_row is not None:
        meta = _as_dict(mkt_row["metadata_json"])
        if cur_gsi is not None:
            meta["gsi"] = cur_gsi
            meta["current_gsi"] = cur_gsi
            meta["governed_gsi"] = cur_gsi
        if pot_gsi is not None:
            meta["potential_gsi"] = pot_gsi
            meta["governed_potential_gsi"] = pot_gsi
        if position is not None:
            meta["position"] = position
        if position_display is not None:
            meta["position_display"] = position_display
        if preferred_foot is not None:
            meta["preferred_foot"] = preferred_foot
        if playstyle is not None:
            meta["playstyle"] = playstyle
        if traits is not None:
            meta["traits"] = list(traits)
            meta["skills"] = list(traits)
        if new_price is not None and int(mkt_row["circulating_shares"] or 0) == 0:
            meta["initial_share_price_coin"] = new_price

        mkt_sets = ["metadata_json = CAST(:meta AS json)", "updated_at = NOW()"]
        mkt_params: dict[str, Any] = {"pid": player_id, "meta": json.dumps(meta)}
        if new_price is not None and int(mkt_row["circulating_shares"] or 0) == 0:
            mkt_sets.append("share_price_coin = :price")
            mkt_params["price"] = new_price

        conn.execute(
            sa.text(f"UPDATE player_share_markets SET {', '.join(mkt_sets)} WHERE player_id = :pid"),
            mkt_params,
        )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("ingestion_players"):
        return

    # 1. Hamza Abdelkarim -> GSI 73, Potential 84
    _update_ingestion_and_read_models(
        conn,
        player_id=HAMZA_ID,
        cur_gsi=73,
        pot_gsi=84,
        override_reason="Calibrated 2026-11-15: Hamza Abdelkarim GSI 73, Potential 84.",
        core_attrs={
            "pace": 77,
            "shooting": 77,
            "passing": 69,
            "dribbling": 76,
            "defending": 42,
            "physical": 72,
        },
        extra_attrs={
            "finishing": 78,
            "composure": 74,
            "positioning": 77,
            "acceleration": 78,
            "agility": 75,
            "ball_control": 75,
            "first_touch": 75,
            "heading": 72,
            "stamina": 73,
        },
        new_price=_calc_price(73, 84),
    )

    # 2. Victor Ozhianvuna -> GSI 74, Potential 86, CM/AM/LM/LW, Right-footed
    victor_traits = [
        "Technical Dribbler",
        "Incisive Pass",
        "First Touch",
        "Flair",
        "Press Proven",
        "Relentless",
    ]
    _update_ingestion_and_read_models(
        conn,
        player_id=VICTOR_ID,
        cur_gsi=74,
        pot_gsi=86,
        position="CM",
        normalized_position="CM",
        secondary_positions=["AM", "LM", "LW"],
        all_positions=["CM", "AM", "LM", "LW"],
        position_display="CM/AM/LM/LW",
        preferred_foot="Right",
        real_player_tier="wonderkid",
        override_reason="Calibrated 2026-11-15: Victor Ozhianvuna GSI 74, Potential 86, CM/AM/LM/LW, Right-footed.",
        playstyle="Advanced Playmaker",
        traits=victor_traits,
        core_attrs={
            "pace": 76,
            "shooting": 71,
            "passing": 75,
            "dribbling": 79,
            "defending": 56,
            "physical": 68,
        },
        extra_attrs={
            "agility": 80,
            "balance": 78,
            "ball_control": 78,
            "first_touch": 77,
            "vision": 76,
            "composure": 74,
            "flair": 78,
            "technique": 77,
            "acceleration": 78,
            "stamina": 75,
            "finishing": 69,
            "crossing": 74,
            "decisions": 74,
        },
        new_price=_calc_price(74, 86),
    )

    # 3. Segun Odegbami -> RW/RM/LW/LM/AM/ST, Right-footed, Mathematical Dribbling + Goal Sense
    odegbami_traits = [
        "Mathematical Dribbling",
        "Technical Dribbler",
        "Goal Sense",
        "Clinical Finisher",
        "Flair",
        "Finesse Shot",
    ]
    odegbami_core = {
        "pace": 86,
        "shooting": 87,
        "passing": 81,
        "dribbling": 89,
        "defending": 48,
        "physical": 79,
    }
    odegbami_extra = {
        "finishing": 87,
        "ball_control": 88,
        "first_touch": 87,
        "technique": 88,
        "flair": 88,
        "agility": 88,
        "balance": 86,
        "acceleration": 87,
        "positioning": 88,
        "anticipation": 87,
        "composure": 86,
        "vision": 83,
        "decisions": 84,
        "crossing": 82,
        "stamina": 82,
        "strength": 76,
        "skill_moves": 5,
        "goal_sense": 88,
    }
    _update_ingestion_and_read_models(
        conn,
        player_id=ODEGBAMI_ID,
        position="RW",
        normalized_position="RW",
        secondary_positions=["RM", "LW", "LM", "AM", "ST"],
        all_positions=["RW", "RM", "LW", "LM", "AM", "ST"],
        position_display="RW/RM/LW/LM/AM/ST",
        preferred_foot="Right",
        playstyle="Inside Forward",
        traits=odegbami_traits,
        core_attrs=odegbami_core,
        extra_attrs=odegbami_extra,
    )

    if inspector.has_table("legendary_player_profiles"):
        leg_row = conn.execute(
            sa.text("SELECT id, metadata_json FROM legendary_player_profiles WHERE id = :lid"),
            {"lid": ODEGBAMI_ID},
        ).mappings().first()
        if leg_row is not None:
            leg_meta = _as_dict(leg_row["metadata_json"])
            leg_meta["position_display"] = "RW/RM/LW/LM/AM/ST"
            leg_meta["playstyle"] = "Inside Forward"
            conn.execute(
                sa.text(
                    """
                    UPDATE legendary_player_profiles
                    SET primary_position = 'RW',
                        secondary_positions_json = CAST(:sec_pos AS json),
                        preferred_foot = 'right',
                        signature_role = 'Inside Forward',
                        signature_traits_json = CAST(:traits AS json),
                        technical_profile_json = CAST(:tech AS json),
                        mental_profile_json = CAST(:mental AS json),
                        physical_profile_json = CAST(:phys AS json),
                        metadata_json = CAST(:meta AS json),
                        updated_at = NOW()
                    WHERE id = :lid
                    """
                ),
                {
                    "lid": ODEGBAMI_ID,
                    "sec_pos": json.dumps(["RM", "LW", "LM", "AM", "ST"]),
                    "traits": json.dumps(odegbami_traits),
                    "tech": json.dumps(
                        {
                            "dribbling": 89,
                            "ball_control": 88,
                            "first_touch": 87,
                            "technique": 88,
                            "flair": 88,
                            "finishing": 87,
                            "shooting": 87,
                            "passing": 81,
                            "crossing": 82,
                            "skill_moves": 5,
                        }
                    ),
                    "mental": json.dumps(
                        {
                            "goal_sense": 88,
                            "positioning": 88,
                            "anticipation": 87,
                            "composure": 86,
                            "decisions": 84,
                            "vision": 83,
                            "off_the_ball": 88,
                            "work_rate": 81,
                        }
                    ),
                    "phys": json.dumps(
                        {
                            "pace": 86,
                            "acceleration": 87,
                            "agility": 88,
                            "balance": 86,
                            "stamina": 82,
                            "strength": 76,
                        }
                    ),
                    "meta": json.dumps(leg_meta),
                },
            )

    # 4. Lamine Camara -> GSI 83, Potential 90
    camara_core = {
        "pace": 84,
        "shooting": 82,
        "passing": 84,
        "dribbling": 85,
        "defending": 72,
        "physical": 80,
    }
    camara_extra = {
        "vision": 85,
        "composure": 83,
        "stamina": 86,
        "ball_control": 85,
        "first_touch": 84,
        "decisions": 83,
        "acceleration": 84,
        "agility": 83,
        "tackling": 73,
        "interception": 75,
    }
    _update_ingestion_and_read_models(
        conn,
        player_id=CAMARA_ACTIVE_ID,
        cur_gsi=83,
        pot_gsi=90,
        override_reason="Calibrated 2026-11-15: Lamine Camara GSI 83, Potential 90.",
        core_attrs=camara_core,
        extra_attrs=camara_extra,
        new_price=_calc_price(83, 90),
    )

    # Align archived duplicate record metadata cleanly while keeping it retired/non-tradable
    conn.execute(
        sa.text(
            """
            UPDATE ingestion_players
            SET governed_gsi = 83,
                governed_potential_gsi = 90,
                potential = 90,
                updated_at = NOW()
            WHERE id = :pid
            """
        ),
        {"pid": CAMARA_DUPLICATE_ID},
    )

    # Sync legacy players table rows if present
    if inspector.has_table("players"):
        conn.execute(
            sa.text(
                """
                UPDATE players
                SET position = 'CM',
                    overall = 74,
                    potential = 86,
                    pace = 76,
                    shooting = 71,
                    passing = 75,
                    dribbling = 79,
                    defending = 56,
                    physical = 68,
                    updated_at = NOW()
                WHERE player_id = 37917642
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE players
                SET position = 'CM',
                    overall = 83,
                    potential = 90,
                    pace = 84,
                    shooting = 82,
                    passing = 84,
                    dribbling = 85,
                    defending = 72,
                    physical = 80,
                    updated_at = NOW()
                WHERE player_id = 37642676
                """
            )
        )


def downgrade() -> None:
    # Calibration data migration; prior values are superseded by current player governance.
    pass
