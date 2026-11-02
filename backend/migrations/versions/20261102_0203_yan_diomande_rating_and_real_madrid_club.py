"""Update Yan Diomandé rating (86 OVR / 92 POT), position (RW/LW), and club (Real Madrid).

Enforces:
1. Yan Diomandé (key diomande-001 / ID 37922937 / UUID f0aaed52-e87b-4936-91a9-5b8a6f049035):
   - Overall rating: 86
   - Potential rating: 92
   - Positions: Primary RW, secondaries LW, AM, ST
   - Club: Real Madrid (ID 3468 / UUID f441ca6f-8db5-449d-8710-dcb2f6a2b193)
   - League: La Liga (ID 564 / UUID ea8801e1-0e74-45a0-a746-79df288fabbd)
   - Attributes: Pace 93, Shooting 78, Passing 79, Dribbling 88, Defending 48, Physical 73
   - Market Value: 85,000,000 EUR
2. Synchronizes players, ingestion_players, real_player_profiles, real_player_source_links,
   ingestion_player_club_tenures, player_summary_read_models, and player_share_markets.

Revision ID: 20261102_0203_yan_diomande_rating_and_real_madrid_club
Revises: 20261101_0202_fm23_regens_facebank_pictures
"""

from __future__ import annotations

import json
from alembic import op
import sqlalchemy as sa

revision = "20261102_0203_yan_diomande_rating_and_real_madrid_club"
down_revision = "20261101_0202_fm23_regens_facebank_pictures"
branch_labels = None
depends_on = None

REAL_MADRID_CLUB_ID = "f441ca6f-8db5-449d-8710-dcb2f6a2b193"
LA_LIGA_COMP_ID = "ea8801e1-0e74-45a0-a746-79df288fabbd"
DIOMANDE_UUID = "f0aaed52-e87b-4936-91a9-5b8a6f049035"
DIOMANDE_PLAYER_ID = 37922937


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Update players table
    if "players" in tables:
        if is_postgres:
            op.execute("""
                UPDATE players
                SET overall = 86,
                    potential = 92,
                    position = 'RW',
                    team_id = 3468,
                    league_id = 564,
                    pace = 93,
                    shooting = 78,
                    passing = 79,
                    dribbling = 88,
                    defending = 48,
                    physical = 73,
                    traits = ARRAY['quick_step', 'rapid', 'flair', 'technical_dribbler'],
                    updated_at = NOW()
                WHERE player_id = 37922937
                """)
        else:
            op.execute("""
                UPDATE players
                SET overall = 86,
                    potential = 92,
                    position = 'RW',
                    team_id = 3468,
                    league_id = 564,
                    pace = 93,
                    shooting = 78,
                    passing = 79,
                    dribbling = 88,
                    defending = 48,
                    physical = 73
                WHERE player_id = 37922937
                """)

    # 2. Update ingestion_players table
    if "ingestion_players" in tables:
        dna_obj = {
            "source": "fc25_sofifa_curated",
            "overall": 86,
            "potential": 92,
            "pace": 93,
            "shooting": 78,
            "passing": 79,
            "dribbling": 88,
            "defending": 48,
            "physical": 73,
            "attributes": {
                "pace": 93,
                "shooting": 78,
                "passing": 79,
                "dribbling": 88,
                "defending": 48,
                "physical": 73,
            },
        }
        dna_json = json.dumps(dna_obj)
        secondary_json = json.dumps(["LW", "AM", "ST"])

        if is_postgres:
            op.execute(
                sa.text("""
                    UPDATE ingestion_players
                    SET current_club_id = :club_id,
                        real_world_club_name = 'Real Madrid',
                        current_competition_id = :comp_id,
                        real_world_league_name = 'La Liga',
                        position = 'RW',
                        normalized_position = 'RW',
                        secondary_positions_json = CAST(:sec_pos AS jsonb),
                        potential = 92,
                        governed_gsi = 86,
                        governed_potential_gsi = 92,
                        real_player_tier = 'elite',
                        market_value_eur = 85000000.0,
                        current_market_reference_value = 85000000.0,
                        market_reference_currency = 'EUR',
                        preferred_foot = 'right',
                        dna_profile = CAST(:dna AS jsonb),
                        updated_at = NOW()
                    WHERE id = :player_uuid
                    """).bindparams(
                    club_id=REAL_MADRID_CLUB_ID,
                    comp_id=LA_LIGA_COMP_ID,
                    sec_pos=secondary_json,
                    dna=dna_json,
                    player_uuid=DIOMANDE_UUID,
                )
            )
        else:
            op.execute(
                sa.text("""
                    UPDATE ingestion_players
                    SET current_club_id = :club_id,
                        real_world_club_name = 'Real Madrid',
                        current_competition_id = :comp_id,
                        real_world_league_name = 'La Liga',
                        position = 'RW',
                        normalized_position = 'RW',
                        potential = 92,
                        governed_gsi = 86,
                        governed_potential_gsi = 92,
                        real_player_tier = 'elite',
                        market_value_eur = 85000000.0,
                        current_market_reference_value = 85000000.0,
                        market_reference_currency = 'EUR',
                        preferred_foot = 'right'
                    WHERE id = :player_uuid
                    """).bindparams(
                    club_id=REAL_MADRID_CLUB_ID,
                    comp_id=LA_LIGA_COMP_ID,
                    player_uuid=DIOMANDE_UUID,
                )
            )

    # 3. Update real_player_profiles
    if "real_player_profiles" in tables:
        signals_json = json.dumps(
            {
                "real_life_performance_score": 86,
                "competition_strength_score": 96,
                "club_strength_score": 95,
                "age_trajectory_score": 92,
                "market_prestige_signal": 88,
                "popularity_signal": 85,
                "liquidity_seed_signal": 86,
                "form_signal": 86,
                "role_tier_signal": 86,
            }
        )
        sec_pos_json = json.dumps(["Left Winger", "Attacking Midfielder", "Striker"])

        if is_postgres:
            op.execute(
                sa.text("""
                    UPDATE real_player_profiles
                    SET primary_position = 'Right Winger',
                        secondary_positions_json = CAST(:sec_pos AS json),
                        current_club_name = 'Real Madrid',
                        current_league_name = 'La Liga',
                        competition_level = 'elite',
                        current_market_reference_value = 85000000.0,
                        market_reference_currency = 'EUR',
                        dominant_foot = 'Right',
                        normalized_signals_json = CAST(:signals AS json),
                        updated_at = NOW()
                    WHERE gtex_player_id = :player_uuid
                    """).bindparams(
                    sec_pos=sec_pos_json,
                    signals=signals_json,
                    player_uuid=DIOMANDE_UUID,
                )
            )
        else:
            op.execute(sa.text("""
                    UPDATE real_player_profiles
                    SET primary_position = 'Right Winger',
                        current_club_name = 'Real Madrid',
                        current_league_name = 'La Liga',
                        competition_level = 'elite',
                        current_market_reference_value = 85000000.0,
                        market_reference_currency = 'EUR',
                        dominant_foot = 'Right'
                    WHERE gtex_player_id = :player_uuid
                    """).bindparams(player_uuid=DIOMANDE_UUID))

    # 4. Update real_player_source_links
    if "real_player_source_links" in tables:
        aliases_json = json.dumps(["Yan Diomande", "Yan Diomandé", "Yanis Diomande", "Y. Diomandé", "Y. Diomande"])
        sec_pos_json = json.dumps(["Left Winger", "Attacking Midfielder", "Striker"])
        if is_postgres:
            op.execute(
                sa.text("""
                    UPDATE real_player_source_links
                    SET primary_position = 'Winger',
                        secondary_positions_json = CAST(:sec_pos AS json),
                        current_real_world_club = 'Real Madrid',
                        known_aliases_json = CAST(:aliases AS json),
                        updated_at = NOW()
                    WHERE gtex_player_id = :player_uuid
                    """).bindparams(
                    sec_pos=sec_pos_json,
                    aliases=aliases_json,
                    player_uuid=DIOMANDE_UUID,
                )
            )
        else:
            op.execute(sa.text("""
                    UPDATE real_player_source_links
                    SET primary_position = 'Winger',
                        current_real_world_club = 'Real Madrid'
                    WHERE gtex_player_id = :player_uuid
                    """).bindparams(player_uuid=DIOMANDE_UUID))

    # 5. Update ingestion_player_club_tenures
    if "ingestion_player_club_tenures" in tables:
        if is_postgres:
            op.execute(
                sa.text("""
                    UPDATE ingestion_player_club_tenures
                    SET club_id = :club_id,
                        updated_at = NOW()
                    WHERE player_id = :player_uuid
                    """).bindparams(
                    club_id=REAL_MADRID_CLUB_ID,
                    player_uuid=DIOMANDE_UUID,
                )
            )
        else:
            op.execute(
                sa.text("""
                    UPDATE ingestion_player_club_tenures
                    SET club_id = :club_id
                    WHERE player_id = :player_uuid
                    """).bindparams(
                    club_id=REAL_MADRID_CLUB_ID,
                    player_uuid=DIOMANDE_UUID,
                )
            )

    # 6. Update player_summary_read_models
    if "player_summary_read_models" in tables:
        summary_obj = {
            "gsi": 86,
            "overall": 86,
            "position": "RW",
            "is_legend": False,
            "potential": 92,
            "total_shares": 200,
            "real_player_tier": "elite",
            "share_price_coin": 230.00,
            "market_visibility": {"status": "visible", "eligible": True},
            "real_player_profile": {
                "source_name": "fc25_sofifa_curated",
                "is_real_player": True,
                "real_player_tier": "elite",
                "source_player_key": "diomande-001",
                "real_world_club_name": "Real Madrid",
                "canonical_display_name": "Yan Diomandé",
                "real_world_league_name": "La Liga",
                "is_verified_real_player": True,
                "market_reference_currency": "EUR",
                "current_market_reference_value": 85000000.0,
            },
        }
        summary_json = json.dumps(summary_obj)
        if is_postgres:
            op.execute(
                sa.text("""
                    UPDATE player_summary_read_models
                    SET current_club_id = :club_id,
                        current_club_name = 'Real Madrid',
                        current_competition_id = :comp_id,
                        current_competition_name = 'La Liga',
                        average_rating = 8.6,
                        market_interest_score = 88,
                        summary_json = CAST(:summary AS json),
                        updated_at = NOW()
                    WHERE player_id = :player_uuid
                    """).bindparams(
                    club_id=REAL_MADRID_CLUB_ID,
                    comp_id=LA_LIGA_COMP_ID,
                    summary=summary_json,
                    player_uuid=DIOMANDE_UUID,
                )
            )
        else:
            op.execute(
                sa.text("""
                    UPDATE player_summary_read_models
                    SET current_club_id = :club_id,
                        current_club_name = 'Real Madrid',
                        current_competition_id = :comp_id,
                        current_competition_name = 'La Liga',
                        average_rating = 8.6,
                        market_interest_score = 88
                    WHERE player_id = :player_uuid
                    """).bindparams(
                    club_id=REAL_MADRID_CLUB_ID,
                    comp_id=LA_LIGA_COMP_ID,
                    player_uuid=DIOMANDE_UUID,
                )
            )

    # 7. Update player_share_markets
    if "player_share_markets" in tables:
        market_meta = {
            "club": "Real Madrid",
            "position": "RW",
            "current_gsi": 86,
            "potential_gsi": 92,
            "eval_gsi": 89.0,
            "tier_code": "elite",
            "asset_type": "real_player_fractional_share",
            "pricing_tier": "gsi_elite",
            "total_shares": 200,
            "circulating_shares": 40,
        }
        market_json = json.dumps(market_meta)
        if is_postgres:
            op.execute(
                sa.text("""
                    UPDATE player_share_markets
                    SET share_price_coin = 230.0000,
                        metadata_json = CAST(:metadata AS json),
                        updated_at = NOW()
                    WHERE player_id = :player_uuid
                    """).bindparams(
                    metadata=market_json,
                    player_uuid=DIOMANDE_UUID,
                )
            )
        else:
            op.execute(sa.text("""
                    UPDATE player_share_markets
                    SET share_price_coin = 230.0000
                    WHERE player_id = :player_uuid
                    """).bindparams(player_uuid=DIOMANDE_UUID))


def downgrade() -> None:
    pass
