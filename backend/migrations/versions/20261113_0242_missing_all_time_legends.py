"""Add the all-time legends the catalogue scan could not find.

Cruyff, Beckenbauer, Platini, Eusébio, and Yashin were not in the legend table.
The same scan missed Garrincha, Puskás, Best, Charlton, Moore, Müller,
Rummenigge, Zoff, Banks, Facchetti, Kempes, Passarella, Rivellino, Tostão,
Jairzinho, and the real Sócrates. A generated Sócrates regen is archived
first. New cards are 1-of-1 legends. Peaks stay inside the governed bands:
96 for Cruyff and Beckenbauer, 90-95 for the Ballon d'Or and World Cup
defining players, and nobody below 80.

Revision ID: 20261113_0242_missing_all_time_legends
Revises: 20261113_0241_legend_fair_peaks
"""

from __future__ import annotations

import json
import uuid
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "20261113_0242_missing_all_time_legends"
down_revision = "20261113_0241_legend_fair_peaks"
branch_labels = None
depends_on = None

_NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://playgtex.app/legends/2026-11-13-pantheon")
_VIRTUAL = date(2026, 11, 1)
_SOCRATES_REGEN = "6cd0db91-f61c-44ee-b49b-a7657fe6bda6"

_COUNTRY_NAMES = {
    "NED": "Netherlands",
    "GER": "Germany",
    "FRA": "France",
    "POR": "Portugal",
    "RUS": "Russia",
    "BRA": "Brazil",
    "HUN": "Hungary",
    "NIR": "Northern Ireland",
    "ENG": "England",
    "ITA": "Italy",
    "ARG": "Argentina",
}
_PROFILE_CODE = {
    "NED": "NET",
    "GER": "GER",
    "FRA": "FRA",
    "POR": "POR",
    "RUS": "RUS",
    "BRA": "BRA",
    "HUN": "HUN",
    "NIR": "NIR",
    "ENG": "ENG",
    "ITA": "ITA",
    "ARG": "ARG",
}


def _pid(slug: str) -> str:
    return str(uuid.uuid5(_NS, "player:" + slug))


def _lid(slug: str) -> str:
    return str(uuid.uuid5(_NS, "profile:" + slug))


def _game_dob(factual: date, age: int) -> date:
    month, day = factual.month, factual.day
    year = _VIRTUAL.year - age if (month, day) <= (_VIRTUAL.month, _VIRTUAL.day) else _VIRTUAL.year - age - 1
    return date(year, month, day)


def _price(gsi: int) -> float:
    return round(250.0 * ((gsi / 90.0) ** 3.2) * 3.6, 2)


def _countries(conn) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for key, name in _COUNTRY_NAMES.items():
        row = conn.execute(
            sa.text("SELECT id, name FROM ingestion_countries WHERE name = :name"),
            {"name": name},
        ).first()
        if row is None:
            raise RuntimeError(f"ingestion_countries has no {name}")
        found[key] = {"id": row[0], "name": row[1]}
    return found


def _holdings(conn, player_id: str) -> int:
    return int(
        conn.execute(
            sa.text("SELECT COUNT(*) FROM player_share_holdings WHERE player_id = :pid"),
            {"pid": player_id},
        ).scalar()
        or 0
    )


def _archive_regen(conn) -> None:
    if _holdings(conn, _SOCRATES_REGEN) != 0:
        return
    conn.execute(
        sa.text(
            """
            UPDATE ingestion_players
            SET real_player_tier = 'archived_duplicate',
                is_tradable = false,
                updated_at = NOW()
            WHERE id = :pid
              AND full_name = 'Sócrates'
              AND real_player_tier = 'regen'
            """
        ),
        {"pid": _SOCRATES_REGEN},
    )
    conn.execute(
        sa.text(
            """
            UPDATE player_share_markets
            SET status = 'retired', updated_at = NOW()
            WHERE player_id = :pid
            """
        ),
        {"pid": _SOCRATES_REGEN},
    )
    conn.execute(
        sa.text(
            """
            UPDATE player_summary_read_models
            SET summary_json = (
                    COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                    jsonb_build_object(
                        'is_tradable', false,
                        'real_player_tier', 'archived_duplicate',
                        'market_visibility', jsonb_build_object('status', 'hidden', 'eligible', false)
                    )
                )::json,
                updated_at = NOW()
            WHERE player_id = :pid
            """
        ),
        {"pid": _SOCRATES_REGEN},
    )


def _insert(conn, countries, player: dict) -> None:
    slug = player["slug"]
    player_id = _pid(slug)
    profile_id = _lid(slug)
    country = countries[player["country"]]
    gsi = player["gsi"]
    if gsi < 80 or gsi > 96:
        raise RuntimeError(f"{player['full_name']} peak {gsi} is outside 80-96")
    factual = player["factual"]
    age = player["age"]
    game_dob = _game_dob(factual, age)
    price = _price(gsi)
    secondary = player["secondary"]
    attrs = player["attrs"]
    dna = {
        "overall": gsi,
        "current_rating": gsi,
        "potential": gsi,
        "potential_rating": gsi,
        "position": player["position"],
        "secondary_positions": secondary,
        "nationality": country["name"],
        "nationality_code": player["country"],
        "age": age,
        "attributes": attrs,
        **attrs,
    }
    summary = {
        "gsi": gsi,
        "overall": gsi,
        "global_scouting_index": gsi,
        "potential": gsi,
        "current_rating": gsi,
        "position": player["position"],
        "normalized_position": player["normalized"],
        "is_legend": True,
        "is_real_player": True,
        "real_player_tier": "legend",
        "is_tradable": True,
        "nationality": country["name"],
        "country_name": country["name"],
        "total_shares": 1,
        "released_shares": 1,
        "available_shares": 1,
        "share_price_coin": price,
        "age": age,
        "date_of_birth": game_dob.isoformat(),
        "attributes": attrs,
        "market_visibility": {"status": "visible", "eligible": True},
    }
    reason = "Peak GSI for a retired international, governed 2026-11-13."
    conn.execute(
        sa.text(
            """
            INSERT INTO legendary_player_profiles (
                id, slug, full_name, country_code, primary_position, secondary_positions_json,
                preferred_foot, historical_height_cm, gtex_height_cm, era,
                legendary_classification, is_active, is_searchable, is_tradable,
                is_rentable, is_national_team_eligible,
                governed_gsi, governed_potential_gsi, gsi_methodology_version, gsi_override_reason,
                date_of_birth, factual_date_of_birth, source_game_date_of_birth, prime_age_at_snapshot,
                signature_traits_json, technical_profile_json, physical_profile_json, mental_profile_json,
                portrait_metadata_json, source_evidence_json, football_evidence_json,
                editorial_status, rights_status, catalogue_status, metadata_json, source_notes,
                created_at, updated_at
            ) VALUES (
                :id, :slug, :full_name, :country_code, :primary_position, CAST(:secondary AS json),
                :foot, :height, :height, :era,
                'icon', true, true, true,
                true, true,
                :gsi, :gsi, 'v2.0', :reason,
                :game_dob, :factual_dob, :game_dob, :age,
                CAST(:traits AS json), CAST('{}' AS json), CAST('{}' AS json), CAST('{}' AS json),
                CAST('{}' AS json), CAST('[]' AS json), CAST('[]' AS json),
                'approved', 'unknown', 'approved', CAST('{}' AS json), :notes,
                NOW(), NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                country_code = EXCLUDED.country_code,
                primary_position = EXCLUDED.primary_position,
                secondary_positions_json = EXCLUDED.secondary_positions_json,
                governed_gsi = EXCLUDED.governed_gsi,
                governed_potential_gsi = EXCLUDED.governed_potential_gsi,
                updated_at = NOW()
            """
        ),
        {
            "id": profile_id,
            "slug": slug,
            "full_name": player["full_name"],
            "country_code": _PROFILE_CODE[player["country"]],
            "primary_position": player["normalized"],
            "secondary": json.dumps(secondary),
            "foot": player["foot"],
            "height": player["height"],
            "era": player["era"],
            "gsi": gsi,
            "reason": reason,
            "game_dob": game_dob,
            "factual_dob": factual,
            "age": age,
            "traits": json.dumps(player["traits"]),
            "notes": player["notes"],
        },
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO ingestion_players (
                id, legendary_profile_id, source_provider, provider_external_id, country_id,
                full_name, canonical_display_name, first_name, last_name, short_name,
                position, normalized_position, secondary_positions_json,
                date_of_birth, factual_date_of_birth, source_game_date_of_birth, prime_age_at_snapshot,
                governed_gsi, governed_potential_gsi, potential,
                gsi_methodology_version, gsi_override_reason,
                height_cm, weight_kg, preferred_foot,
                real_world_club_name, dna_profile, morale,
                is_tradable, is_real_player, real_player_tier, profile_completeness_score,
                created_at, updated_at, last_synced_at
            ) VALUES (
                :id, :profile_id, 'gtex_legend_registry', :external_id, :country_id,
                :full_name, :full_name, :first_name, :last_name, :short_name,
                :position, :normalized, CAST(:secondary AS json),
                :game_dob, :factual_dob, :game_dob, :age,
                :gsi, :gsi, :gsi,
                'v2.0', :reason,
                :height, :weight, :foot,
                :club, CAST(:dna AS json), 50.0,
                true, true, 'legend', 1.0,
                NOW(), NOW(), NOW()
            )
            ON CONFLICT (id) DO UPDATE SET
                country_id = EXCLUDED.country_id,
                full_name = EXCLUDED.full_name,
                position = EXCLUDED.position,
                normalized_position = EXCLUDED.normalized_position,
                secondary_positions_json = EXCLUDED.secondary_positions_json,
                governed_gsi = EXCLUDED.governed_gsi,
                governed_potential_gsi = EXCLUDED.governed_potential_gsi,
                potential = EXCLUDED.potential,
                real_player_tier = 'legend',
                is_tradable = true,
                is_real_player = true,
                legendary_profile_id = EXCLUDED.legendary_profile_id,
                dna_profile = EXCLUDED.dna_profile,
                updated_at = NOW()
            """
        ),
        {
            "id": player_id,
            "profile_id": profile_id,
            "external_id": slug,
            "country_id": country["id"],
            "full_name": player["full_name"],
            "first_name": player["first_name"],
            "last_name": player["last_name"],
            "short_name": player["short_name"],
            "position": player["position"],
            "normalized": player["normalized"],
            "secondary": json.dumps(secondary),
            "game_dob": game_dob,
            "factual_dob": factual,
            "age": age,
            "gsi": gsi,
            "reason": reason,
            "height": player["height"],
            "weight": player["weight"],
            "foot": player["foot"],
            "club": player["club"],
            "dna": json.dumps(dna),
        },
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO player_share_markets (
                id, player_id, total_shares, circulating_shares, released_shares, share_price_coin,
                status, revenue_distributed_coin, metadata_json, created_at, updated_at
            ) VALUES (
                :id, :pid, 1, 0, 1, :price,
                'active', 0.0, CAST(:meta AS json), NOW(), NOW()
            )
            ON CONFLICT (player_id) DO UPDATE SET
                total_shares = 1,
                released_shares = 1,
                circulating_shares = 0,
                share_price_coin = EXCLUDED.share_price_coin,
                status = 'active',
                updated_at = NOW()
            WHERE player_share_markets.circulating_shares = 0
            """
        ),
        {
            "id": str(uuid.uuid5(_NS, "market:" + slug)),
            "pid": player_id,
            "price": price,
            "meta": json.dumps({"gsi": gsi, "country": country["name"], "source": "gtex_legend_registry"}),
        },
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO player_summary_read_models (
                player_id, player_name, current_club_name, last_snapshot_at,
                current_value_credits, previous_value_credits, movement_pct,
                average_rating, market_interest_score, summary_json, created_at, updated_at
            ) VALUES (
                :pid, :name, :club, NOW(),
                :price, :price, 0.0,
                :gsi, 70, CAST(:summary AS json), NOW(), NOW()
            )
            ON CONFLICT (player_id) DO UPDATE SET
                player_name = EXCLUDED.player_name,
                current_club_name = EXCLUDED.current_club_name,
                current_value_credits = EXCLUDED.current_value_credits,
                average_rating = EXCLUDED.average_rating,
                summary_json = EXCLUDED.summary_json,
                updated_at = NOW()
            """
        ),
        {
            "pid": player_id,
            "name": player["full_name"],
            "club": player["club"],
            "price": price,
            "gsi": float(gsi),
            "summary": json.dumps(summary),
        },
    )


_LEGENDS = (
    {
        "slug": "johan-cruyff",
        "full_name": "Johan Cruyff",
        "first_name": "Johan",
        "last_name": "Cruyff",
        "short_name": "Cruyff",
        "country": "NED",
        "gsi": 96,
        "position": "AM/ST",
        "normalized": "AM",
        "secondary": ["ST"],
        "foot": "Right",
        "height": 180,
        "weight": 74,
        "factual": date(1947, 4, 25),
        "age": 28,
        "era": "1970s",
        "club": "Ajax",
        "attrs": {"pace": 92, "shooting": 86, "passing": 95, "dribbling": 96, "defending": 45, "physical": 72},
        "traits": ["Ballon d'Or 1971", "Ballon d'Or 1973", "Ballon d'Or 1974"],
        "notes": "Ajax and Netherlands. Three Ballon d'Or wins and the defining player of Total Football. Peak GSI 96.",
    },
    {
        "slug": "franz-beckenbauer",
        "full_name": "Franz Beckenbauer",
        "first_name": "Franz",
        "last_name": "Beckenbauer",
        "short_name": "Beckenbauer",
        "country": "GER",
        "gsi": 96,
        "position": "CB/DM",
        "normalized": "CB",
        "secondary": ["DM"],
        "foot": "Right",
        "height": 181,
        "weight": 75,
        "factual": date(1945, 9, 11),
        "age": 28,
        "era": "1970s",
        "club": "Bayern Munich",
        "attrs": {"pace": 82, "shooting": 68, "passing": 90, "dribbling": 84, "defending": 96, "physical": 84},
        "traits": ["Ballon d'Or 1972", "Ballon d'Or 1976", "World Cup 1974"],
        "notes": "Bayern and West Germany. The sweeper who won the World Cup as captain and two Ballons d'Or. Peak GSI 96.",
    },
    {
        "slug": "michel-platini",
        "full_name": "Michel Platini",
        "first_name": "Michel",
        "last_name": "Platini",
        "short_name": "Platini",
        "country": "FRA",
        "gsi": 95,
        "position": "AM",
        "normalized": "AM",
        "secondary": [],
        "foot": "Right",
        "height": 179,
        "weight": 74,
        "factual": date(1955, 6, 21),
        "age": 27,
        "era": "1980s",
        "club": "Juventus",
        "attrs": {"pace": 80, "shooting": 92, "passing": 94, "dribbling": 90, "defending": 48, "physical": 74},
        "traits": ["Ballon d'Or 1983", "Ballon d'Or 1984", "Ballon d'Or 1985", "Euro 1984"],
        "notes": "Juventus and France. Three straight Ballons d'Or and the Euro 1984 winner. Peak GSI 95.",
    },
    {
        "slug": "eusebio",
        "full_name": "Eusébio",
        "first_name": "Eusébio",
        "last_name": "da Silva Ferreira",
        "short_name": "Eusébio",
        "country": "POR",
        "gsi": 94,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 175,
        "weight": 73,
        "factual": date(1942, 1, 25),
        "age": 28,
        "era": "1960s",
        "club": "Benfica",
        "attrs": {"pace": 94, "shooting": 94, "passing": 78, "dribbling": 88, "defending": 36, "physical": 82},
        "traits": ["Ballon d'Or 1965", "European Cup 1962"],
        "notes": "Benfica and Portugal. Ballon d'Or 1965 and the 1966 World Cup's leading scorer. Peak GSI 94.",
    },
    {
        "slug": "lev-yashin",
        "full_name": "Lev Yashin",
        "first_name": "Lev",
        "last_name": "Yashin",
        "short_name": "Yashin",
        "country": "RUS",
        "gsi": 95,
        "position": "GK",
        "normalized": "GK",
        "secondary": [],
        "foot": "Right",
        "height": 189,
        "weight": 82,
        "factual": date(1929, 10, 22),
        "age": 28,
        "era": "1960s",
        "club": "Dynamo Moscow",
        "attrs": {"pace": 72, "shooting": 42, "passing": 70, "dribbling": 55, "defending": 96, "physical": 86},
        "traits": ["Ballon d'Or 1963"],
        "notes": "Dynamo Moscow and the Soviet Union. The only goalkeeper to win the Ballon d'Or. Filed under Russia. Peak GSI 95.",
    },
    {
        "slug": "garrincha",
        "full_name": "Garrincha",
        "first_name": "Manuel",
        "last_name": "dos Santos",
        "short_name": "Garrincha",
        "country": "BRA",
        "gsi": 95,
        "position": "RW",
        "normalized": "RW",
        "secondary": [],
        "foot": "Right",
        "height": 169,
        "weight": 69,
        "factual": date(1933, 10, 28),
        "age": 28,
        "era": "1960s",
        "club": "Botafogo",
        "attrs": {"pace": 96, "shooting": 84, "passing": 82, "dribbling": 97, "defending": 30, "physical": 68},
        "traits": ["World Cup 1958", "World Cup 1962"],
        "notes": "Botafogo and Brazil. World Cup winner in 1958 and 1962, and the outstanding player of 1962. Peak GSI 95.",
    },
    {
        "slug": "ferenc-puskas",
        "full_name": "Ferenc Puskás",
        "first_name": "Ferenc",
        "last_name": "Puskás",
        "short_name": "Puskás",
        "country": "HUN",
        "gsi": 95,
        "position": "ST",
        "normalized": "ST",
        "secondary": ["LW"],
        "foot": "Left",
        "height": 172,
        "weight": 72,
        "factual": date(1927, 4, 1),
        "age": 28,
        "era": "1950s",
        "club": "Real Madrid",
        "attrs": {"pace": 84, "shooting": 96, "passing": 84, "dribbling": 88, "defending": 32, "physical": 78},
        "traits": ["European Cup 1960", "Hungary 1954"],
        "notes": "Honvéd, Real Madrid, and Hungary. The left-footed scorer of the 1950s. Peak GSI 95.",
    },
    {
        "slug": "george-best",
        "full_name": "George Best",
        "first_name": "George",
        "last_name": "Best",
        "short_name": "Best",
        "country": "NIR",
        "gsi": 94,
        "position": "RW/AM",
        "normalized": "RW",
        "secondary": ["AM"],
        "foot": "Left",
        "height": 175,
        "weight": 70,
        "factual": date(1946, 5, 22),
        "age": 28,
        "era": "1960s",
        "club": "Manchester United",
        "attrs": {"pace": 94, "shooting": 88, "passing": 84, "dribbling": 96, "defending": 34, "physical": 68},
        "traits": ["Ballon d'Or 1968", "European Cup 1968"],
        "notes": "Manchester United and Northern Ireland. Ballon d'Or and European Cup in 1968. Peak GSI 94.",
    },
    {
        "slug": "bobby-charlton",
        "full_name": "Bobby Charlton",
        "first_name": "Bobby",
        "last_name": "Charlton",
        "short_name": "Charlton",
        "country": "ENG",
        "gsi": 94,
        "position": "AM/ST",
        "normalized": "AM",
        "secondary": ["ST"],
        "foot": "Right",
        "height": 173,
        "weight": 70,
        "factual": date(1937, 10, 11),
        "age": 28,
        "era": "1960s",
        "club": "Manchester United",
        "attrs": {"pace": 84, "shooting": 92, "passing": 88, "dribbling": 84, "defending": 52, "physical": 76},
        "traits": ["Ballon d'Or 1966", "World Cup 1966", "European Cup 1968"],
        "notes": "Manchester United and England. World Cup, European Cup, and the 1966 Ballon d'Or. Peak GSI 94.",
    },
    {
        "slug": "bobby-moore",
        "full_name": "Bobby Moore",
        "first_name": "Bobby",
        "last_name": "Moore",
        "short_name": "Moore",
        "country": "ENG",
        "gsi": 93,
        "position": "CB",
        "normalized": "CB",
        "secondary": [],
        "foot": "Right",
        "height": 178,
        "weight": 75,
        "factual": date(1941, 4, 12),
        "age": 28,
        "era": "1960s",
        "club": "West Ham United",
        "attrs": {"pace": 74, "shooting": 48, "passing": 82, "dribbling": 72, "defending": 94, "physical": 82},
        "traits": ["World Cup 1966"],
        "notes": "West Ham and England. Captain of the 1966 World Cup winners. Peak GSI 93.",
    },
    {
        "slug": "gerd-muller",
        "full_name": "Gerd Müller",
        "first_name": "Gerd",
        "last_name": "Müller",
        "short_name": "Müller",
        "country": "GER",
        "gsi": 95,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 176,
        "weight": 76,
        "factual": date(1945, 11, 3),
        "age": 28,
        "era": "1970s",
        "club": "Bayern Munich",
        "attrs": {"pace": 82, "shooting": 97, "passing": 74, "dribbling": 80, "defending": 30, "physical": 80},
        "traits": ["Ballon d'Or 1970", "World Cup 1974"],
        "notes": "Bayern and West Germany. Ballon d'Or 1970 and the decisive scorer of the 1974 World Cup. Peak GSI 95.",
    },
    {
        "slug": "karl-heinz-rummenigge",
        "full_name": "Karl-Heinz Rummenigge",
        "first_name": "Karl-Heinz",
        "last_name": "Rummenigge",
        "short_name": "Rummenigge",
        "country": "GER",
        "gsi": 94,
        "position": "ST/RW",
        "normalized": "ST",
        "secondary": ["RW"],
        "foot": "Right",
        "height": 182,
        "weight": 79,
        "factual": date(1955, 9, 25),
        "age": 27,
        "era": "1980s",
        "club": "Bayern Munich",
        "attrs": {"pace": 90, "shooting": 92, "passing": 80, "dribbling": 86, "defending": 40, "physical": 82},
        "traits": ["Ballon d'Or 1980", "Ballon d'Or 1981"],
        "notes": "Bayern, Inter, and West Germany. Ballon d'Or in 1980 and 1981. Peak GSI 94.",
    },
    {
        "slug": "dino-zoff",
        "full_name": "Dino Zoff",
        "first_name": "Dino",
        "last_name": "Zoff",
        "short_name": "Zoff",
        "country": "ITA",
        "gsi": 92,
        "position": "GK",
        "normalized": "GK",
        "secondary": [],
        "foot": "Right",
        "height": 182,
        "weight": 78,
        "factual": date(1942, 2, 28),
        "age": 28,
        "era": "1970s",
        "club": "Juventus",
        "attrs": {"pace": 68, "shooting": 40, "passing": 68, "dribbling": 52, "defending": 92, "physical": 80},
        "traits": ["World Cup 1982"],
        "notes": "Juventus and Italy. Captain of the 1982 World Cup winners. Peak GSI 92.",
    },
    {
        "slug": "gordon-banks",
        "full_name": "Gordon Banks",
        "first_name": "Gordon",
        "last_name": "Banks",
        "short_name": "Banks",
        "country": "ENG",
        "gsi": 92,
        "position": "GK",
        "normalized": "GK",
        "secondary": [],
        "foot": "Right",
        "height": 185,
        "weight": 86,
        "factual": date(1937, 12, 30),
        "age": 28,
        "era": "1960s",
        "club": "Stoke City",
        "attrs": {"pace": 70, "shooting": 40, "passing": 66, "dribbling": 52, "defending": 93, "physical": 82},
        "traits": ["World Cup 1966"],
        "notes": "Leicester, Stoke, and England. Goalkeeper of the 1966 World Cup winners. Peak GSI 92.",
    },
    {
        "slug": "socrates",
        "full_name": "Sócrates",
        "first_name": "Sócrates",
        "last_name": "Brasileiro",
        "short_name": "Sócrates",
        "country": "BRA",
        "gsi": 90,
        "position": "AM",
        "normalized": "AM",
        "secondary": ["CM"],
        "foot": "Right",
        "height": 192,
        "weight": 79,
        "factual": date(1954, 2, 19),
        "age": 27,
        "era": "1980s",
        "club": "Corinthians",
        "attrs": {"pace": 78, "shooting": 84, "passing": 90, "dribbling": 86, "defending": 55, "physical": 78},
        "traits": ["Brazil 1982"],
        "notes": "Corinthians and Brazil. The captain of the 1982 side. Peak GSI 90.",
    },
    {
        "slug": "giacinto-facchetti",
        "full_name": "Giacinto Facchetti",
        "first_name": "Giacinto",
        "last_name": "Facchetti",
        "short_name": "Facchetti",
        "country": "ITA",
        "gsi": 92,
        "position": "LB",
        "normalized": "LB",
        "secondary": [],
        "foot": "Left",
        "height": 188,
        "weight": 85,
        "factual": date(1942, 7, 18),
        "age": 28,
        "era": "1960s",
        "club": "Inter",
        "attrs": {"pace": 88, "shooting": 62, "passing": 80, "dribbling": 74, "defending": 90, "physical": 86},
        "traits": ["European Cup 1964", "European Cup 1965", "Euro 1968"],
        "notes": "Inter and Italy. The attacking left back of Herrera's Inter. Peak GSI 92.",
    },
    {
        "slug": "mario-kempes",
        "full_name": "Mario Kempes",
        "first_name": "Mario",
        "last_name": "Kempes",
        "short_name": "Kempes",
        "country": "ARG",
        "gsi": 92,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 184,
        "weight": 78,
        "factual": date(1954, 7, 15),
        "age": 28,
        "era": "1970s",
        "club": "Valencia",
        "attrs": {"pace": 88, "shooting": 92, "passing": 78, "dribbling": 84, "defending": 40, "physical": 84},
        "traits": ["World Cup 1978", "World Cup Golden Boot 1978"],
        "notes": "Valencia and Argentina. Golden Boot and the outstanding player of the 1978 World Cup. Peak GSI 92.",
    },
    {
        "slug": "daniel-passarella",
        "full_name": "Daniel Passarella",
        "first_name": "Daniel",
        "last_name": "Passarella",
        "short_name": "Passarella",
        "country": "ARG",
        "gsi": 91,
        "position": "CB",
        "normalized": "CB",
        "secondary": [],
        "foot": "Right",
        "height": 178,
        "weight": 74,
        "factual": date(1953, 5, 25),
        "age": 28,
        "era": "1970s",
        "club": "River Plate",
        "attrs": {"pace": 76, "shooting": 70, "passing": 78, "dribbling": 70, "defending": 92, "physical": 84},
        "traits": ["World Cup 1978"],
        "notes": "River Plate and Argentina. Captain of the 1978 World Cup winners. Peak GSI 91.",
    },
    {
        "slug": "rivellino",
        "full_name": "Rivellino",
        "first_name": "Roberto",
        "last_name": "Rivellino",
        "short_name": "Rivellino",
        "country": "BRA",
        "gsi": 90,
        "position": "AM/LW",
        "normalized": "AM",
        "secondary": ["LW"],
        "foot": "Left",
        "height": 169,
        "weight": 68,
        "factual": date(1946, 1, 1),
        "age": 28,
        "era": "1970s",
        "club": "Corinthians",
        "attrs": {"pace": 80, "shooting": 88, "passing": 90, "dribbling": 90, "defending": 42, "physical": 70},
        "traits": ["World Cup 1970"],
        "notes": "Corinthians and Brazil. Left-footed playmaker of the 1970 World Cup side. Peak GSI 90.",
    },
    {
        "slug": "tostao",
        "full_name": "Tostão",
        "first_name": "Eduardo",
        "last_name": "Gonçalves",
        "short_name": "Tostão",
        "country": "BRA",
        "gsi": 90,
        "position": "ST/AM",
        "normalized": "ST",
        "secondary": ["AM"],
        "foot": "Right",
        "height": 172,
        "weight": 68,
        "factual": date(1947, 1, 25),
        "age": 28,
        "era": "1970s",
        "club": "Cruzeiro",
        "attrs": {"pace": 84, "shooting": 88, "passing": 86, "dribbling": 86, "defending": 38, "physical": 72},
        "traits": ["World Cup 1970"],
        "notes": "Cruzeiro and Brazil. The forward who linked Pelé in the 1970 World Cup. Peak GSI 90.",
    },
    {
        "slug": "jairzinho",
        "full_name": "Jairzinho",
        "first_name": "Jair",
        "last_name": "Ventura Filho",
        "short_name": "Jairzinho",
        "country": "BRA",
        "gsi": 91,
        "position": "RW",
        "normalized": "RW",
        "secondary": [],
        "foot": "Right",
        "height": 173,
        "weight": 73,
        "factual": date(1944, 12, 25),
        "age": 28,
        "era": "1970s",
        "club": "Botafogo",
        "attrs": {"pace": 94, "shooting": 88, "passing": 78, "dribbling": 88, "defending": 40, "physical": 84},
        "traits": ["World Cup 1970"],
        "notes": "Botafogo and Brazil. Scored in every match of the 1970 World Cup. Peak GSI 91.",
    },
)


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    countries = _countries(conn)
    _archive_regen(conn)
    for player in _LEGENDS:
        _insert(conn, countries, player)


def downgrade() -> None:
    pass
