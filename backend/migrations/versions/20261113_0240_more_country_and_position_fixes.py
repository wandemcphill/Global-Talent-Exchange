"""Correct more players filed under a club country or the wrong position.

Nationality comes from the senior national team. Position changes are limited
to cards whose listed role is a different job from the career they are known for.

Revision ID: 20261113_0240_more_country_and_position_fixes
Revises: 20261113_0239_ivory_coast_and_regional_legends
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "20261113_0240_more_country_and_position_fixes"
down_revision = "20261113_0239_ivory_coast_and_regional_legends"
branch_labels = None
depends_on = None

# id, country name or None, profile code or None, position, normalized, secondary or None
# None position means the playing role stays as it is.
_FIXES = (
    ("e6b7464f-f200-40e4-bf7d-eaf924dfdf67", "Wales", "WAL", None, None, None),  # Aaron Ramsey
    ("33608198-aaf2-4a86-8448-c5509a7d7f99", "Wales", "WAL", None, None, None),  # Ryan Giggs
    ("de2c5217-b64f-436b-b9fb-849b8c9760bf", "Wales", "WAL", None, None, None),  # Gareth Bale
    ("098b5e24-52be-4f9c-8c09-d6a9b6d870d2", "United States", "U.S", None, None, None),  # Brad Friedel
    ("e6e4f073-cc9b-4220-b6e0-99cab8f488c8", "United States", "U.S", None, None, None),  # Brian McBride
    ("27d4d81c-84aa-4359-8828-7c2a79d2c6ad", "United States", "U.S", None, None, None),  # Claudio Reyna
    ("6f61494a-79f1-46a8-a9f2-e23bbdccfd4a", "United States", "U.S", None, None, None),  # Clint Dempsey
    ("2db4f677-2b8a-444f-981b-1ffc41cfc2a2", "United States", "U.S", None, None, None),  # Tim Howard
    ("7858b882-bf72-455e-ad72-96a42e05d3f3", "United States", "U.S", None, None, None),  # Bobby Convey
    ("45fab65a-0545-4d5a-9396-97d8039b4b22", "Bosnia and Herzegovina", "BOS", None, None, None),  # Edin Džeko
    ("7190261e-d46d-47e3-aea6-03d1085578a3", "Bosnia and Herzegovina", "BOS", None, None, None),  # Miralem Pjanić
    ("846f1193-db2b-4598-90f8-f2b86ee90ce6", "Romania", "ROM", None, None, None),  # Adrian Ilie
    ("f627de0c-529e-49d6-9d91-1d926c1d151d", "Romania", "ROM", None, None, None),  # Daniel Prodan
    ("80d3dd87-a7da-4bed-9e6f-98908fb21885", "Romania", "ROM", None, None, None),  # Marian Popa
    ("5ad6714a-27a0-467d-a91e-3a315215d651", "Spain", "SPA", None, None, None),  # Paco Buyo
    ("1f680d0f-c3e1-4edd-9a2f-2f1b83b609d1", "Ukraine", "UKR", None, None, None),  # Oleg Blokhin
    ("a58e68eb-3d60-4932-8c93-213f5bc828c0", "France", "FRA", None, None, None),  # Sylvain Distin
    ("491ae859-a419-404c-a239-34b348d6f5d9", "Mexico", "MEX", None, None, None),  # Jared Borgetti
    ("df8e0b1e-9b6d-4955-b489-296fcc8cb9f6", "Brazil", "BRA", None, None, None),  # Nilmar
    ("e746ec19-78b2-4f49-bf19-2424a6eef044", "Ghana", "GH", None, None, None),  # Samuel Kuffour
    ("358d5753-9acc-4cbe-8d2a-ef584cfb7a7d", "Czech Republic", "CZE", None, None, None),  # Patrik Berger
    ("cc86fc7b-abb2-461d-b4c2-7a8d49f9afad", "Belgium", "BEL", None, None, None),  # Michel Preud'homme
    ("528d56c1-ccef-44db-9837-6bcf203f6a88", "Croatia", "CRO", None, None, None),  # Boris Živković
    ("0d660fa4-4fcc-443c-a04b-f705da6f154a", "England", "ENG", "ST", "ST", []),  # Andrew Johnson
    ("1a091045-a41c-4a44-b259-cb724276986a", "Turkey", "TUR", "ST/RW", "ST", ["RW"]),  # Arif Erdem
    ("4fed45e5-cfbb-44c5-8798-b7bc7cecdce0", "Germany", "GER", "LW/ST", "LW", ["ST"]),  # André Schürrle
    ("1a07bed0-b18d-4dfc-ad44-3ba8ac364ab7", "France", "FRA", "AM", "AM", ["LW"]),  # Samir Nasri
    ("3b81bd43-6b72-4b6a-b563-9a0859e678ec", None, "IS", None, None, None),  # Gylfi Sigurðsson
    ("e0f23fa4-c5d1-487f-b26b-ab6294781c4b", None, "ITA", None, None, None),  # Angelo Di Livio
    ("6f5487ee-1d8e-4409-986b-a38319ceada6", None, None, "DM", "DM", ["CM"]),  # Claude Makélélé
    ("965efafc-33f9-4b07-b551-4ac5addf5f70", None, None, "CM/DM", "CM", ["DM"]),  # Bastian Schweinsteiger
    ("243d73e1-f152-4840-941a-86696fb12076", None, None, "AM/ST", "AM", ["ST"]),  # Ruud Gullit
    ("1e897ec8-eb9f-4606-bca3-846ede2cdf98", None, None, "DM/CM", "DM", ["CM"]),  # Michael Essien
    ("c1a1f90f-0b11-4054-b98c-5397cc7dc2a9", None, None, "ST", "ST", []),  # Robert Lewandowski
    ("0aa9249f-3db0-4320-94c4-d70be5c326cb", None, None, "ST", "ST", []),  # Edinson Cavani
    ("8928be30-db1a-49a3-97be-669eb504730b", None, None, "ST", "ST", []),  # Claudio Pizarro
    ("fe3442e0-bbee-4c46-b586-48b78a4d992a", None, None, "CM", "CM", ["DM"]),  # Frenkie de Jong
    ("5151d03d-abb9-451d-a34e-82e265bf4562", None, None, "AM/RW", "AM", ["RW", "CM"]),  # Mohammed Kudus
    ("ba3d04ec-078b-4be0-9fdc-ecd15313a049", None, None, "AM", "AM", ["CM"]),  # Bruno Fernandes
    ("267d8895-ba83-4b09-a21e-64f5fd23196a", None, None, None, "DM", ["CM"]),  # Sunday Oliseh profile
)


def _countries(conn) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for name in {row[1] for row in _FIXES if row[1]}:
        got = conn.execute(
            sa.text("SELECT id, name FROM ingestion_countries WHERE name = :name"),
            {"name": name},
        ).first()
        if got is None:
            raise RuntimeError(f"ingestion_countries has no {name}")
        found[name] = {"id": got[0], "name": got[1]}
    return found


def _apply(conn, countries, row) -> None:
    player_id, country_name, profile_code, position, normalized, secondary = row
    if country_name:
        country = countries[country_name]
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET country_id = :cid,
                    dna_profile = (
                        COALESCE(dna_profile::jsonb, '{}'::jsonb)
                        || CAST(:patch AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE id = :pid
                """),
            {
                "cid": country["id"],
                "patch": json.dumps({"nationality": country["name"], "nationality_code": profile_code or ""}),
                "pid": player_id,
            },
        )
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET summary_json = (
                        COALESCE(summary_json::jsonb, '{}'::jsonb)
                        || CAST(:patch AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {
                "patch": json.dumps({"nationality": country["name"], "country_name": country["name"]}),
                "pid": player_id,
            },
        )
    if position:
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET position = :position,
                    normalized_position = :normalized,
                    secondary_positions_json = CAST(:secondary AS json),
                    dna_profile = (
                        COALESCE(dna_profile::jsonb, '{}'::jsonb)
                        || CAST(:dna AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE id = :pid
                """),
            {
                "position": position,
                "normalized": normalized,
                "secondary": json.dumps(secondary or []),
                "dna": json.dumps({"position": position, "secondary_positions": secondary or []}),
                "pid": player_id,
            },
        )
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET summary_json = (
                        COALESCE(summary_json::jsonb, '{}'::jsonb)
                        || CAST(:patch AS jsonb)
                    )::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"patch": json.dumps({"position": position}), "pid": player_id},
        )
    profile_sets = ["updated_at = NOW()"]
    params: dict[str, object] = {"pid": player_id}
    if profile_code:
        profile_sets.append("country_code = :code")
        params["code"] = profile_code
    if normalized:
        profile_sets.append("primary_position = :primary")
        params["primary"] = normalized
    if secondary is not None and (position or normalized):
        profile_sets.append("secondary_positions_json = CAST(:secondary AS json)")
        params["secondary"] = json.dumps(secondary)
    if len(profile_sets) > 1:
        conn.execute(
            sa.text(f"""
                UPDATE legendary_player_profiles AS lp
                SET {", ".join(profile_sets)}
                FROM ingestion_players AS p
                WHERE p.legendary_profile_id = lp.id
                  AND p.id = :pid
                """),
            params,
        )


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    countries = _countries(conn)
    for row in _FIXES:
        _apply(conn, countries, row)


def downgrade() -> None:
    pass
