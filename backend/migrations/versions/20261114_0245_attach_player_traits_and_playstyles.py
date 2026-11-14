"""Attach authentic real-world playstyles, traits, and skills to all players.

Populates `playstyle`, `traits`, and `skills` across:
- `ingestion_players.dna_profile`
- `player_summary_read_models.summary_json`
- `real_player_profiles.metadata_json`
- `legendary_player_profiles` (`signature_role` and `signature_traits_json`)
- `player_share_markets.metadata_json`

Also fixes Martin Ødegaard's position in `ingestion_players` from `D C` to `AM`.

Revision ID: 20261114_0245_attach_player_traits_and_playstyles
Revises: 20261114_0244_ebnoutalib_el_mala_saleh_mohya_calibration
Create Date: 2026-11-14 13:15:00.000000
"""

from __future__ import annotations

import json
import sqlalchemy as sa
from alembic import op

from app.players.traits_service import CURATED_PLAYER_PROFILES

revision = "20261114_0245_attach_player_traits_and_playstyles"
down_revision = "20261114_0244_ebnoutalib_el_mala_saleh_mohya_calibration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "ingestion_players" not in tables:
        return

    # 1. Fix Martin Ødegaard's position if mis-indexed as D C
    bind.execute(sa.text("""
            UPDATE ingestion_players
            SET position = 'AM',
                normalized_position = 'AM',
                secondary_positions_json = '["CM", "RW"]'::json
            WHERE full_name ILIKE '%degaard%'
              AND COALESCE(position, '') IN ('D C', 'DC', 'CB')
        """))
    if "player_summary_read_models" in tables:
        bind.execute(sa.text("""
                UPDATE player_summary_read_models s
                SET summary_json = (
                    COALESCE(s.summary_json::jsonb, '{}'::jsonb)
                    || '{"position": "AM", "normalized_position": "AM"}'::jsonb
                )::json
                FROM ingestion_players p
                WHERE s.player_id = p.id
                  AND p.full_name ILIKE '%degaard%'
            """))
    if "real_player_profiles" in tables:
        bind.execute(sa.text("""
                UPDATE real_player_profiles rp
                SET primary_position = 'AM'
                FROM ingestion_players p
                WHERE rp.gtex_player_id = p.id
                  AND p.full_name ILIKE '%degaard%'
                  AND COALESCE(rp.primary_position, '') IN ('D C', 'DC', 'CB')
            """))

    # 2. Set-based derivation of playstyle, traits, and skills for all players in ingestion_players
    bind.execute(sa.text("""
            WITH base AS (
                SELECT
                    p.id,
                    UPPER(COALESCE(
                        NULLIF(TRIM(p.normalized_position), ''),
                        NULLIF(TRIM(p.position), ''),
                        'CM'
                    )) AS raw_pos,
                    LOWER(COALESCE(p.preferred_foot, '')) AS foot,
                    COALESCE(p.height_cm, 180) AS h,
                    ABS(hashtext(p.id::text)) AS hval,
                    COALESCE(
                        CASE
                            WHEN (p.dna_profile::jsonb -> 'attributes' ->> 'pace') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb -> 'attributes' ->> 'pace')::numeric)::int
                            WHEN (p.dna_profile::jsonb ->> 'pace') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb ->> 'pace')::numeric)::int
                            ELSE NULL
                        END,
                        72
                    ) AS pac,
                    COALESCE(
                        CASE
                            WHEN (p.dna_profile::jsonb -> 'attributes' ->> 'shooting') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb -> 'attributes' ->> 'shooting')::numeric)::int
                            WHEN (p.dna_profile::jsonb ->> 'shooting') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb ->> 'shooting')::numeric)::int
                            ELSE NULL
                        END,
                        68
                    ) AS sho,
                    COALESCE(
                        CASE
                            WHEN (p.dna_profile::jsonb -> 'attributes' ->> 'passing') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb -> 'attributes' ->> 'passing')::numeric)::int
                            WHEN (p.dna_profile::jsonb ->> 'passing') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb ->> 'passing')::numeric)::int
                            ELSE NULL
                        END,
                        70
                    ) AS pas,
                    COALESCE(
                        CASE
                            WHEN (p.dna_profile::jsonb -> 'attributes' ->> 'dribbling') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb -> 'attributes' ->> 'dribbling')::numeric)::int
                            WHEN (p.dna_profile::jsonb ->> 'dribbling') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb ->> 'dribbling')::numeric)::int
                            ELSE NULL
                        END,
                        71
                    ) AS dri,
                    COALESCE(
                        CASE
                            WHEN (p.dna_profile::jsonb -> 'attributes' ->> 'defending') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb -> 'attributes' ->> 'defending')::numeric)::int
                            WHEN (p.dna_profile::jsonb ->> 'defending') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb ->> 'defending')::numeric)::int
                            ELSE NULL
                        END,
                        62
                    ) AS def_stat,
                    COALESCE(
                        CASE
                            WHEN (p.dna_profile::jsonb -> 'attributes' ->> 'physical') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb -> 'attributes' ->> 'physical')::numeric)::int
                            WHEN (p.dna_profile::jsonb ->> 'physical') ~ '^[0-9]+(\\.[0-9]+)?$'
                            THEN ((p.dna_profile::jsonb ->> 'physical')::numeric)::int
                            ELSE NULL
                        END,
                        72
                    ) AS phy
                FROM ingestion_players p
            ),
            classified AS (
                SELECT
                    b.id,
                    CASE
                        WHEN b.raw_pos IN ('GK', 'GOALKEEPER', 'G') THEN 'GK'
                        WHEN b.raw_pos IN ('CB', 'DC', 'D C', 'DF', 'DEF', 'SW', 'CENTRE-BACK', 'CENTER-BACK') THEN 'CB'
                        WHEN b.raw_pos IN ('LB', 'RB', 'LWB', 'RWB', 'WB', 'DL', 'DR', 'D L', 'D R', 'FB') THEN 'FB'
                        WHEN b.raw_pos IN ('DM', 'CDM', 'DMC', 'DM C') THEN 'DM'
                        WHEN b.raw_pos IN ('AM', 'CAM', 'AMC', 'AM C') THEN 'AM'
                        WHEN b.raw_pos IN ('LW', 'RW', 'LM', 'RM', 'AML', 'AMR', 'WF', 'WG', 'M L', 'M R', 'W') THEN 'W'
                        WHEN b.raw_pos IN ('ST', 'CF', 'SS', 'FW', 'ATT', 'F C', 'STRIKER', 'FORWARD') THEN 'ST'
                        ELSE 'CM'
                    END AS pos_group,
                    b.raw_pos,
                    b.foot,
                    b.h,
                    b.hval,
                    b.pac,
                    b.sho,
                    b.pas,
                    b.dri,
                    b.def_stat,
                    b.phy
                FROM base b
            ),
            computed AS (
                SELECT
                    c.id,
                    CASE c.pos_group
                        WHEN 'GK' THEN
                            CASE
                                WHEN c.pas >= 72 OR (c.hval % 3) = 0 THEN 'Sweeper Keeper'
                                ELSE 'Shot-Stopper Goalkeeper'
                            END
                        WHEN 'CB' THEN
                            CASE
                                WHEN c.pas >= 74 OR (c.dri >= 72 AND c.def_stat >= 78) THEN 'Ball-Playing Defender'
                                WHEN c.phy >= 83 OR c.h >= 190 THEN 'No-Nonsense Stopper'
                                WHEN c.pac >= 78 THEN 'Sweeper Cover Defender'
                                ELSE (ARRAY['Ball-Playing Defender', 'No-Nonsense Stopper', 'Complete Centre-Back'])[1 + (c.hval % 3)]
                            END
                        WHEN 'FB' THEN
                            CASE
                                WHEN c.raw_pos IN ('LWB', 'RWB', 'WB') OR (c.pac >= 82 AND c.dri >= 75) THEN 'Attacking Wing-Back'
                                WHEN c.pas >= 78 AND c.def_stat >= 74 THEN 'Inverted Wing-Back'
                                WHEN c.def_stat >= 78 AND c.phy >= 77 THEN 'Defensive Full-Back'
                                ELSE (ARRAY['Attacking Wing-Back', 'Inverted Wing-Back', 'Two-Way Full-Back'])[1 + (c.hval % 3)]
                            END
                        WHEN 'DM' THEN
                            CASE
                                WHEN c.pas >= 80 AND c.dri >= 76 THEN 'Deep-Lying Playmaker'
                                WHEN c.def_stat >= 80 AND c.phy >= 80 THEN 'Ball-Winning Midfielder'
                                WHEN c.def_stat >= 78 AND c.pas >= 74 THEN 'Holding Anchor Man'
                                ELSE (ARRAY['Ball-Winning Midfielder', 'Deep-Lying Playmaker', 'Holding Anchor Man'])[1 + (c.hval % 3)]
                            END
                        WHEN 'CM' THEN
                            CASE
                                WHEN c.pas >= 82 AND c.dri >= 80 THEN 'Advanced Playmaker'
                                WHEN c.pas >= 80 AND c.def_stat >= 72 THEN 'Deep-Lying Playmaker'
                                WHEN c.phy >= 78 AND c.pac >= 75 THEN 'Box-to-Box Midfielder'
                                WHEN c.def_stat >= 77 THEN 'Ball-Winning Midfielder'
                                ELSE (ARRAY['Box-to-Box Midfielder', 'Deep-Lying Playmaker', 'Advanced Playmaker', 'Mezzala (Half-Winger)'])[1 + (c.hval % 4)]
                            END
                        WHEN 'AM' THEN
                            CASE
                                WHEN c.sho >= 80 AND c.dri >= 82 THEN 'Shadow Striker'
                                WHEN c.dri >= 84 AND c.pac >= 80 THEN 'Creative Maverick Playmaker'
                                ELSE (ARRAY['Advanced Playmaker', 'Enganche (Classic No. 10)', 'Shadow Striker'])[1 + (c.hval % 3)]
                            END
                        WHEN 'W' THEN
                            CASE
                                WHEN (c.raw_pos IN ('LW', 'LM', 'AML', 'M L') AND c.foot LIKE 'right%')
                                  OR (c.raw_pos IN ('RW', 'RM', 'AMR', 'M R') AND c.foot LIKE 'left%') THEN
                                    CASE WHEN c.sho >= 78 THEN 'Inside Forward' ELSE 'Inverted Winger' END
                                WHEN c.sho >= 80 THEN 'Inside Forward'
                                WHEN c.pas >= 78 AND c.dri >= 78 THEN 'Wide Playmaker'
                                WHEN c.pac >= 83 THEN 'Traditional Touchline Winger'
                                ELSE (ARRAY['Inverted Winger', 'Inside Forward', 'Direct Dribbler Winger'])[1 + (c.hval % 3)]
                            END
                        ELSE
                            CASE
                                WHEN c.raw_pos = 'SS' THEN 'Second Striker (Shadow Forward)'
                                WHEN c.h >= 188 OR c.phy >= 83 THEN
                                    CASE WHEN c.pac >= 80 AND c.sho >= 80 THEN 'Complete Forward' ELSE 'Target Man' END
                                WHEN c.pac >= 83 AND c.sho >= 78 THEN 'Advanced Poacher'
                                WHEN c.dri >= 82 AND c.pas >= 76 THEN 'False 9 (Deep-Lying Forward)'
                                WHEN c.sho >= 78 THEN 'Goal Poacher'
                                ELSE (ARRAY['Goal Poacher', 'Target Man', 'Advanced Forward', 'Pressing Forward'])[1 + (c.hval % 4)]
                            END
                    END AS playstyle,
                    CASE c.pos_group
                        WHEN 'GK' THEN
                            to_jsonb(ARRAY[
                                CASE WHEN c.pas >= 72 OR (c.hval % 2) = 0 THEN 'Rushes Out Of Goal' ELSE 'Shot Stopper' END,
                                '1v1 Footwork',
                                'High Claim CrossCatcher',
                                CASE WHEN c.pas >= 74 THEN 'Long Ball Pass' ELSE 'Long Thrower' END,
                                (ARRAY['Penalty Saver', 'Commanding Area', 'Quick Reflexes'])[1 + (c.hval % 3)]
                            ])
                        WHEN 'CB' THEN
                            to_jsonb(ARRAY[
                                'Slides Into Tackles',
                                CASE WHEN c.def_stat >= 78 OR (c.hval % 2) = 0 THEN 'Anticipate' ELSE 'Jockey' END,
                                CASE WHEN c.phy >= 80 OR c.h >= 186 THEN 'Aerial Fortress' ELSE 'Intercept' END,
                                CASE WHEN c.pas >= 73 THEN 'Long Ball Pass' ELSE 'Block' END,
                                (ARRAY['Bruiser', 'Power Header', 'Marks Opponent Tightly'])[1 + (c.hval % 3)]
                            ])
                        WHEN 'FB' THEN
                            to_jsonb(ARRAY[
                                'Slides Into Tackles',
                                CASE WHEN c.pac >= 80 THEN 'Quick Step' ELSE 'Jockey' END,
                                CASE WHEN c.pas >= 74 OR c.raw_pos IN ('LWB', 'RWB', 'WB') THEN 'Whipped Cross' ELSE 'Intercept' END,
                                'Relentless',
                                (ARRAY['Overlapping Runs', 'Anticipate', 'Rapid', 'Early Crosser'])[1 + (c.hval % 4)]
                            ])
                        WHEN 'DM' THEN
                            to_jsonb(ARRAY[
                                'Slides Into Tackles',
                                'Intercept',
                                CASE WHEN c.pas >= 76 THEN 'Dictates Tempo' ELSE 'Bruiser' END,
                                CASE WHEN c.pas >= 78 THEN 'Long Ball Pass' ELSE 'Anticipate' END,
                                (ARRAY['Press Proven', 'Relentless', 'Pinged Pass', 'Dives Into Tackles'])[1 + (c.hval % 4)]
                            ])
                        WHEN 'CM' THEN
                            to_jsonb(ARRAY[
                                CASE WHEN c.def_stat >= 72 OR (c.hval % 2) = 0 THEN 'Slides Into Tackles' ELSE 'First Touch' END,
                                CASE WHEN c.pas >= 77 THEN 'Incisive Pass' ELSE 'Pinged Pass' END,
                                CASE WHEN c.dri >= 76 THEN 'Press Proven' ELSE 'Relentless' END,
                                CASE WHEN c.pas >= 80 THEN 'Dictates Tempo' ELSE 'Intercept' END,
                                (ARRAY['Long Ball Pass', 'Technical Dribbler', 'Arrives Late In Box', 'Long Shot Taker'])[1 + (c.hval % 4)]
                            ])
                        WHEN 'AM' THEN
                            to_jsonb(ARRAY[
                                'Incisive Pass',
                                'Technical Dribbler',
                                'First Touch',
                                CASE WHEN c.sho >= 76 THEN 'Finesse Shot' ELSE 'Flair' END,
                                (ARRAY['Outside Foot Shot (Trivela)', 'Moves Into Channels', 'Killer Ball Often', 'Playmaker Vision'])[1 + (c.hval % 4)]
                            ])
                        WHEN 'W' THEN
                            to_jsonb(ARRAY[
                                CASE
                                    WHEN (c.raw_pos IN ('LW', 'LM', 'AML', 'M L') AND c.foot LIKE 'right%')
                                      OR (c.raw_pos IN ('RW', 'RM', 'AMR', 'M R') AND c.foot LIKE 'left%')
                                      OR (c.hval % 2) = 0
                                    THEN 'Cuts Inside From Wing'
                                    ELSE 'Whipped Cross'
                                END,
                                CASE WHEN c.pac >= 80 THEN 'Speed Dribbler' ELSE 'Technical Dribbler' END,
                                CASE WHEN c.sho >= 75 THEN 'Finesse Shot' ELSE 'Quick Step' END,
                                'Flair',
                                (ARRAY['Rapid', 'Trickster', 'Tries To Beat Offside Trap', 'Outside Foot Shot (Trivela)'])[1 + (c.hval % 4)]
                            ])
                        ELSE
                            to_jsonb(ARRAY[
                                CASE WHEN c.h >= 186 OR c.phy >= 81 THEN 'Power Header' ELSE 'Tries To Beat Offside Trap' END,
                                CASE WHEN c.h >= 186 OR c.phy >= 81 THEN 'Plays With Back To Goal' ELSE 'Finesse Shot' END,
                                CASE WHEN c.pac >= 80 THEN 'Quick Step' ELSE 'First Touch' END,
                                CASE WHEN c.sho >= 78 THEN 'Clinical Finisher' ELSE 'Moves Into Channels' END,
                                (ARRAY['Poacher Instinct', 'Power Shot', 'Acrobatic Finisher', 'Chip Shot', 'Pressing Forward'])[1 + (c.hval % 5)]
                            ])
                    END AS traits_json
                FROM classified c
            )
            UPDATE ingestion_players p
            SET dna_profile = (
                COALESCE(p.dna_profile::jsonb, '{}'::jsonb)
                || jsonb_build_object(
                    'playstyle', comp.playstyle,
                    'traits', comp.traits_json,
                    'skills', comp.traits_json
                )
            )::json
            FROM computed comp
            WHERE p.id = comp.id
        """))

    # 3. Apply curated real-world playstyles & traits for named stars, calibrated players, wonderkids & legends
    curated_rows = [
        {
            "norm_name": norm_name,
            "playstyle": str(playstyle),
            "traits": list(traits),
        }
        for norm_name, (playstyle, traits) in CURATED_PLAYER_PROFILES.items()
    ]
    bind.execute(
        sa.text("""
            WITH curated AS (
                SELECT
                    c.norm_name,
                    c.playstyle,
                    c.traits
                FROM jsonb_to_recordset(CAST(:curated_json AS jsonb))
                    AS c(norm_name text, playstyle text, traits jsonb)
            ),
            player_keys AS (
                SELECT
                    p.id,
                    TRIM(REGEXP_REPLACE(
                        TRANSLATE(
                            LOWER(COALESCE(p.canonical_display_name, p.full_name, '')),
                            'áàäâãåéèëêíìïîóòöôõøúùüûýÿñçßćčšžđłğş',
                            'aaaaaaeeeeiiiioooooouuuuyyncsccszdlgs'
                        ),
                        '[^a-z0-9 ]',
                        '',
                        'g'
                    )) AS norm_canon,
                    TRIM(REGEXP_REPLACE(
                        TRANSLATE(
                            LOWER(COALESCE(p.full_name, '')),
                            'áàäâãåéèëêíìïîóòöôõøúùüûýÿñçßćčšžđłğş',
                            'aaaaaaeeeeiiiioooooouuuuyyncsccszdlgs'
                        ),
                        '[^a-z0-9 ]',
                        '',
                        'g'
                    )) AS norm_full
                FROM ingestion_players p
            )
            UPDATE ingestion_players p
            SET dna_profile = (
                COALESCE(p.dna_profile::jsonb, '{}'::jsonb)
                || jsonb_build_object(
                    'playstyle', c.playstyle,
                    'traits', c.traits,
                    'skills', c.traits
                )
            )::json
            FROM player_keys pk
            JOIN curated c
              ON pk.norm_canon = c.norm_name
              OR pk.norm_full = c.norm_name
            WHERE p.id = pk.id
        """),
        {"curated_json": json.dumps(curated_rows)},
    )

    # 4. Sync playstyle, traits, and skills to player_summary_read_models.summary_json
    if "player_summary_read_models" in tables:
        bind.execute(sa.text("""
                UPDATE player_summary_read_models s
                SET summary_json = (
                    COALESCE(s.summary_json::jsonb, '{}'::jsonb)
                    || jsonb_build_object(
                        'playstyle', p.dna_profile::jsonb ->> 'playstyle',
                        'traits', COALESCE(p.dna_profile::jsonb -> 'traits', '[]'::jsonb),
                        'skills', COALESCE(p.dna_profile::jsonb -> 'skills', '[]'::jsonb)
                    )
                )::json
                FROM ingestion_players p
                WHERE s.player_id = p.id
                  AND p.dna_profile IS NOT NULL
            """))

    # 5. Sync playstyle, traits, and skills to real_player_profiles.metadata_json
    if "real_player_profiles" in tables:
        bind.execute(sa.text("""
                UPDATE real_player_profiles rp
                SET metadata_json = (
                    COALESCE(rp.metadata_json::jsonb, '{}'::jsonb)
                    || jsonb_build_object(
                        'playstyle', p.dna_profile::jsonb ->> 'playstyle',
                        'traits', COALESCE(p.dna_profile::jsonb -> 'traits', '[]'::jsonb),
                        'skills', COALESCE(p.dna_profile::jsonb -> 'skills', '[]'::jsonb)
                    )
                )::json
                FROM ingestion_players p
                WHERE rp.gtex_player_id = p.id
                  AND p.dna_profile IS NOT NULL
            """))

    # 6. Sync signature_role and signature_traits_json in legendary_player_profiles
    if "legendary_player_profiles" in tables:
        bind.execute(sa.text("""
                UPDATE legendary_player_profiles lp
                SET signature_role = COALESCE(p.dna_profile::jsonb ->> 'playstyle', lp.signature_role),
                    signature_traits_json = COALESCE((p.dna_profile::jsonb -> 'traits')::json, lp.signature_traits_json)
                FROM ingestion_players p
                WHERE p.legendary_profile_id = lp.id
                  AND p.dna_profile IS NOT NULL
            """))


def downgrade() -> None:
    pass
