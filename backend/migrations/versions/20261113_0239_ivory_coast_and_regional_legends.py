"""Put Ivorian players on Côte d'Ivoire, raise Yaya Touré to 92, and add missing regional legends.

Kolo Touré and Yaya Touré were filed under England. The same club-country mistake
is corrected for other real Ivorians, for Wes Morgan (Jamaica, not Brazil), and
for England internationals who had been filed under Jamaica. Olivier Kapo
represented France, so he moves to France.

New cards are real retired internationals who were not already in the game.
Placeholder regens that reuse Kossi Agassa and Mohamed Kallon are archived
before the real players are inserted. Stéphane Sessegnon already exists for
Benin and is promoted in place. Juma Bah is an active Sierra Leone player and
is taken off the 1-of-1 legend market when nobody holds that share.

Revision ID: 20261113_0239_ivory_coast_and_regional_legends
Revises: 20261112_0238_automatic_coin_rails
"""

from __future__ import annotations

import json
import uuid
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "20261113_0239_ivory_coast_and_regional_legends"
down_revision = "20261112_0238_automatic_coin_rails"
branch_labels = None
depends_on = None

_NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://playgtex.app/legends/2026-11-13")
_VIRTUAL = date(2026, 11, 1)

# Lookup key -> (column, value). Nigeria and Jamaica have no alpha-3 on the country row.
_COUNTRY_MATCH = {
    "CIV": ("alpha3_code", "CIV"),
    "NGA": ("alpha2_code", "NG"),
    "ENG": ("alpha3_code", "ENG"),
    "FRA": ("alpha3_code", "FRA"),
    "JAM": ("alpha2_code", "JM"),
    "TGO": ("alpha3_code", "TGO"),
    "BEN": ("alpha3_code", "BEN"),
    "SLE": ("alpha3_code", "SLE"),
    "LBR": ("alpha3_code", "LBR"),
    "BFA": ("alpha3_code", "BFA"),
    "ZMB": ("alpha3_code", "ZMB"),
    "TTO": ("alpha3_code", "TTO"),
}
_NAT_CODE = {
    "CIV": "CIV",
    "NGA": "NGA",
    "ENG": "ENG",
    "FRA": "FRA",
    "JAM": "JAM",
    "TGO": "TGO",
    "BEN": "BEN",
    "SLE": "SLE",
    "LBR": "LBR",
    "BFA": "BFA",
    "ZMB": "ZMB",
    "TTO": "TTO",
}
# Legendary profiles for Ivory Coast and Nigeria already use these short codes.
_PROFILE_CODE = {**_NAT_CODE, "CIV": "IVO", "NGA": "NIG"}

# player_id, country key, previous country key (for downgrade)
_COUNTRY_FIXES = (
    ("58b7917e-ba01-4c3c-ab01-a88dadf4a051", "CIV", "ENG"),  # Kolo Touré
    ("3cfc43bb-a235-4b9a-9388-6305aa57bcda", "CIV", "ENG"),  # Yaya Touré
    ("c3fa358e-4bb5-46aa-94a9-6d3a233cc307", "CIV", "ENG"),  # Didier Drogba
    ("fa20d8ee-33ed-4287-af09-873537991fcd", "CIV", "ESP"),  # Emmanuel Eboué
    ("c7fcd2d9-6138-410e-b3a5-d56df4a7d0bf", "CIV", "ITA"),  # Gervinho
    ("be2e851f-a779-4811-b854-b40fa6f7ee46", "CIV", "ENG"),  # Wilfried Zaha
    ("14a09f72-fcaa-40a9-9a06-bb539c0606cb", "CIV", "NED"),  # Bonaventure Kalou
    ("ff20c37b-4502-4871-b547-262e63c0c655", "CIV", "FRA"),  # Emerse Faé
    ("e02d4b2c-c460-44ac-afb8-dfd6084d0d82", "CIV", "SRB"),  # Salomon Kalou
    ("f703cf30-b7f4-44f9-986f-ed65b56e16c2", "CIV", "ENG"),  # Wilfried Bony
    ("31176998-9c0f-4f67-8d0e-25ec8053855b", "CIV", "BEL"),  # Sébastien Haller
    ("a888d071-bbe8-4912-870f-18d194ae7cf5", "CIV", "NGA"),  # Serge Aurier
    ("6bcd20c1-ada7-444e-9165-1261403fde21", "CIV", "BRA"),  # Franck Kessié
    ("1ee5d7af-be2f-40e1-83ab-eaa8a2ada5b3", "CIV", "ENG"),  # Arouna Koné
    ("9a30ecec-f82a-467f-bd76-6cd367e3bfc9", "FRA", "ENG"),  # Olivier Kapo
    ("f934d2d9-6208-4c03-a398-0bc2c6c23d79", "JAM", "BRA"),  # Wes Morgan
    ("e3b103ec-4574-4fa7-9e79-27f4080573a4", "ENG", "JAM"),  # Max Aarons
    ("0b2cfcce-e9dc-4905-8b8d-d5a0bef74f3e", "ENG", "JAM"),  # Tyrick Mitchell
    ("28fdb6f8-8622-4e59-8334-95513766fdb3", "ENG", "JAM"),  # Nathan Dyer
    ("a34770fa-e5e4-4089-83cf-56116c493b9d", "ENG", "JAM"),  # Omar Richards
    ("cd651269-0207-449a-b8fa-db61319f945e", "ENG", "JAM"),  # Wes Harding
)

_PREVIOUS_COUNTRY = {pid: prev for pid, _new, prev in _COUNTRY_FIXES}

_PLACEHOLDER_REGENS = (
    ("d8ed8bde-3999-57fd-8d82-c297c94322cf", "Kossi Agassa"),
    ("63e04b26-e84d-5a26-af0a-16f1f5480643", "Mohamed Kallon"),
)

_JUMA_BAH = "5fd86421-78ac-44be-a2b2-55b62437743c"
_SESSEGNON = "33df56ba-3709-4040-84db-183b2b40f94f"
_YAYA = "3cfc43bb-a235-4b9a-9388-6305aa57bcda"


def _pid(slug: str) -> str:
    return str(uuid.uuid5(_NS, "player:" + slug))


def _lid(slug: str) -> str:
    return str(uuid.uuid5(_NS, "profile:" + slug))


def _game_dob(factual: date, age: int) -> date:
    month, day = factual.month, factual.day
    year = _VIRTUAL.year - age if (month, day) <= (_VIRTUAL.month, _VIRTUAL.day) else _VIRTUAL.year - age - 1
    if month == 2 and day == 29:
        try:
            return date(year, 2, 29)
        except ValueError:
            return date(year, 2, 28)
    return date(year, month, day)


def _price(gsi: int) -> float:
    return round(250.0 * ((gsi / 90.0) ** 3.2) * 3.6, 2)


def _load_countries(conn) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    extra = {
        "ITA": ("alpha3_code", "ITA"),
        "NED": ("alpha3_code", "NED"),
        "SRB": ("alpha3_code", "SRB"),
        "BEL": ("alpha3_code", "BEL"),
        "BRA": ("alpha2_code", "BR"),
        "ESP": ("alpha3_code", "ESP"),
    }
    for key, (column, value) in {**_COUNTRY_MATCH, **extra}.items():
        row = conn.execute(
            sa.text(f"SELECT id, name FROM ingestion_countries WHERE {column} = :value ORDER BY name LIMIT 1"),
            {"value": value},
        ).first()
        if row is None:
            raise RuntimeError(f"ingestion_countries has no row for {key}")
        found[key] = {"id": row[0], "name": row[1]}
    return found


def _set_country(conn, countries, player_id: str, country_key: str) -> None:
    country = countries[country_key]
    dna_patch = json.dumps(
        {"nationality": country["name"], "nationality_code": _NAT_CODE.get(country_key, country_key)}
    )
    summary_patch = json.dumps({"nationality": country["name"], "country_name": country["name"]})
    market_patch = json.dumps({"country": country["name"]})
    conn.execute(
        sa.text("""
            UPDATE ingestion_players
            SET country_id = :cid,
                dna_profile = (COALESCE(dna_profile::jsonb, '{}'::jsonb) || CAST(:patch AS jsonb))::json,
                updated_at = NOW()
            WHERE id = :pid
            """),
        {"cid": country["id"], "patch": dna_patch, "pid": player_id},
    )
    conn.execute(
        sa.text("""
            UPDATE player_summary_read_models
            SET summary_json = (COALESCE(summary_json::jsonb, '{}'::jsonb) || CAST(:patch AS jsonb))::json,
                updated_at = NOW()
            WHERE player_id = :pid
            """),
        {"patch": summary_patch, "pid": player_id},
    )
    conn.execute(
        sa.text("""
            UPDATE player_share_markets
            SET metadata_json = (COALESCE(metadata_json::jsonb, '{}'::jsonb) || CAST(:patch AS jsonb))::json,
                updated_at = NOW()
            WHERE player_id = :pid
            """),
        {"patch": market_patch, "pid": player_id},
    )
    conn.execute(
        sa.text("""
            UPDATE legendary_player_profiles AS lp
            SET country_code = :code, updated_at = NOW()
            FROM ingestion_players AS p
            WHERE p.legendary_profile_id = lp.id
              AND p.id = :pid
            """),
        {"code": _PROFILE_CODE.get(country_key, country_key), "pid": player_id},
    )


def _holdings(conn, player_id: str) -> int:
    return int(
        conn.execute(
            sa.text("SELECT COUNT(*) FROM player_share_holdings WHERE player_id = :pid"),
            {"pid": player_id},
        ).scalar_one()
    )


def _apply_rating(
    conn,
    player_id: str,
    gsi: int,
    *,
    potential: int | None = None,
    position: str | None = None,
    normalized: str | None = None,
    secondary: list[str] | None = None,
    attrs: dict[str, int] | None = None,
    tier: str | None = None,
    game_dob: date | None = None,
    factual_dob: date | None = None,
    prime_age: int | None = None,
    legend_shares: bool = False,
) -> None:
    potential = gsi if potential is None else potential
    price = _price(gsi if tier == "legend" or legend_shares else potential)
    dna_patch: dict[str, object] = {
        "overall": gsi,
        "current_rating": gsi,
        "potential": potential,
        "potential_rating": potential,
    }
    summary_patch: dict[str, object] = {
        "gsi": gsi,
        "overall": gsi,
        "global_scouting_index": gsi,
        "potential": potential,
        "current_rating": gsi,
    }
    if attrs:
        dna_patch.update(attrs)
        dna_patch["attributes"] = attrs
        summary_patch["attributes"] = attrs
    if position:
        dna_patch["position"] = position
        summary_patch["position"] = position
    if secondary is not None:
        dna_patch["secondary_positions"] = secondary
    if tier:
        summary_patch["real_player_tier"] = tier
        summary_patch["is_legend"] = tier == "legend"
        summary_patch["is_tradable"] = True
    sets = [
        "governed_gsi = :gsi",
        "governed_potential_gsi = :potential",
        "potential = :potential",
        "dna_profile = (COALESCE(dna_profile::jsonb, '{}'::jsonb) || CAST(:dna AS jsonb))::json",
        "updated_at = NOW()",
    ]
    params: dict[str, object] = {
        "pid": player_id,
        "gsi": gsi,
        "potential": potential,
        "dna": json.dumps(dna_patch),
    }
    if position:
        sets.append("position = :position")
        params["position"] = position
    if normalized:
        sets.append("normalized_position = :normalized")
        params["normalized"] = normalized
    if secondary is not None:
        sets.append("secondary_positions_json = CAST(:secondary AS json)")
        params["secondary"] = json.dumps(secondary)
    if tier:
        sets.append("real_player_tier = :tier")
        sets.append("is_real_player = true")
        sets.append("is_tradable = true")
        params["tier"] = tier
    if game_dob:
        sets.append("date_of_birth = :game_dob")
        sets.append("source_game_date_of_birth = :game_dob")
        params["game_dob"] = game_dob
        summary_patch["date_of_birth"] = game_dob.isoformat()
        summary_patch["age"] = prime_age
    if factual_dob:
        sets.append("factual_date_of_birth = :factual_dob")
        params["factual_dob"] = factual_dob
    if prime_age is not None:
        sets.append("prime_age_at_snapshot = :prime_age")
        params["prime_age"] = prime_age
    conn.execute(
        sa.text(f"UPDATE ingestion_players SET {', '.join(sets)} WHERE id = :pid"),
        params,
    )
    profile_sets = [
        "governed_gsi = :gsi",
        "governed_potential_gsi = :potential",
        "updated_at = NOW()",
    ]
    profile_params: dict[str, object] = {"gsi": gsi, "potential": potential, "pid": player_id}
    if normalized:
        profile_sets.append("primary_position = :position")
        profile_params["position"] = normalized
    if secondary is not None:
        profile_sets.append("secondary_positions_json = CAST(:secondary AS json)")
        profile_params["secondary"] = json.dumps(secondary)
    conn.execute(
        sa.text(f"""
            UPDATE legendary_player_profiles AS lp
            SET {", ".join(profile_sets)}
            FROM ingestion_players AS p
            WHERE p.legendary_profile_id = lp.id
              AND p.id = :pid
            """),
        profile_params,
    )
    summary_patch["share_price_coin"] = price
    conn.execute(
        sa.text("""
            UPDATE player_summary_read_models
            SET average_rating = :gsi,
                current_value_credits = :price,
                summary_json = (COALESCE(summary_json::jsonb, '{}'::jsonb) || CAST(:patch AS jsonb))::json,
                updated_at = NOW()
            WHERE player_id = :pid
            """),
        {"gsi": float(gsi), "price": price, "patch": json.dumps(summary_patch), "pid": player_id},
    )
    if legend_shares and _holdings(conn, player_id) == 0:
        summary_shares = json.dumps({"total_shares": 1, "released_shares": 1, "available_shares": 1})
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET total_shares = 1,
                    released_shares = 1,
                    circulating_shares = 0,
                    share_price_coin = :price,
                    status = 'active',
                    metadata_json = (COALESCE(metadata_json::jsonb, '{}'::jsonb) || CAST(:meta AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"price": price, "meta": json.dumps({"gsi": gsi, "governed_gsi": gsi}), "pid": player_id},
        )
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET summary_json = (COALESCE(summary_json::jsonb, '{}'::jsonb) || CAST(:patch AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"patch": summary_shares, "pid": player_id},
        )
    else:
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET share_price_coin = :price,
                    metadata_json = (COALESCE(metadata_json::jsonb, '{}'::jsonb) || CAST(:meta AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"price": price, "meta": json.dumps({"gsi": gsi, "governed_gsi": gsi}), "pid": player_id},
        )


def _archive_placeholder(conn, player_id: str, full_name: str) -> None:
    conn.execute(
        sa.text("""
            UPDATE ingestion_players
            SET real_player_tier = 'archived_duplicate',
                is_tradable = false,
                updated_at = NOW()
            WHERE id = :pid
              AND full_name = :name
            """),
        {"pid": player_id, "name": full_name},
    )
    conn.execute(
        sa.text("""
            UPDATE player_share_markets
            SET status = 'retired', updated_at = NOW()
            WHERE player_id = :pid
            """),
        {"pid": player_id},
    )
    conn.execute(
        sa.text("""
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
            """),
        {"pid": player_id},
    )


def _insert_legend(conn, countries, player: dict) -> None:
    slug = player["slug"]
    player_id = _pid(slug)
    profile_id = _lid(slug)
    country = countries[player["country"]]
    nat_code = _NAT_CODE[player["country"]]
    profile_code = _PROFILE_CODE[player["country"]]
    gsi = player["gsi"]
    factual = player["factual"]
    age = player["age"]
    game_dob = _game_dob(factual, age)
    price = _price(gsi)
    attrs = player["attrs"]
    secondary = player["secondary"]
    dna = {
        "overall": gsi,
        "current_rating": gsi,
        "potential": gsi,
        "potential_rating": gsi,
        "position": player["position"],
        "secondary_positions": secondary,
        "nationality": country["name"],
        "nationality_code": nat_code,
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
    conn.execute(
        sa.text("""
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
                is_searchable = true,
                is_active = true,
                updated_at = NOW()
            """),
        {
            "id": profile_id,
            "slug": slug,
            "full_name": player["full_name"],
            "country_code": profile_code,
            "primary_position": player["normalized"],
            "secondary": json.dumps(secondary),
            "foot": player["foot"],
            "height": player["height"],
            "era": player["era"],
            "gsi": gsi,
            "reason": "Peak GSI for a retired international, governed 2026-11-13.",
            "game_dob": game_dob,
            "factual_dob": factual,
            "age": age,
            "traits": json.dumps(player["traits"]),
            "notes": player["notes"],
        },
    )
    conn.execute(
        sa.text("""
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
                canonical_display_name = EXCLUDED.canonical_display_name,
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
            """),
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
            "reason": "Peak GSI for a retired international, governed 2026-11-13.",
            "height": player["height"],
            "weight": player["weight"],
            "foot": player["foot"],
            "club": player["club"],
            "dna": json.dumps(dna),
        },
    )
    conn.execute(
        sa.text("""
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
                metadata_json = EXCLUDED.metadata_json,
                updated_at = NOW()
            """),
        {
            "id": str(uuid.uuid5(_NS, "market:" + slug)),
            "pid": player_id,
            "price": price,
            "meta": json.dumps({"gsi": gsi, "country": country["name"], "source": "gtex_legend_registry"}),
        },
    )
    conn.execute(
        sa.text("""
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
            """),
        {
            "pid": player_id,
            "name": player["full_name"],
            "club": player["club"],
            "price": price,
            "gsi": float(gsi),
            "summary": json.dumps(summary),
        },
    )


_NEW_LEGENDS = (
    {
        "slug": "emmanuel-amunike",
        "full_name": "Emmanuel Amunike",
        "first_name": "Emmanuel",
        "last_name": "Amunike",
        "short_name": "Amunike",
        "country": "NGA",
        "gsi": 88,
        "position": "LW/ST/AM",
        "normalized": "LW",
        "secondary": ["ST", "AM"],
        "foot": "Right",
        "height": 178,
        "weight": 74,
        "factual": date(1970, 12, 25),
        "age": 25,
        "era": "1990s",
        "club": "FC Barcelona",
        "attrs": {"pace": 91, "shooting": 84, "passing": 80, "dribbling": 88, "defending": 38, "physical": 74},
        "traits": ["Olympic gold 1996", "African Footballer of the Year 1994"],
        "notes": "Nigeria winger. African Footballer of the Year 1994 and Olympic gold in 1996. Peak GSI 88.",
    },
    {
        "slug": "samuel-okunowo",
        "full_name": "Samuel Okunowo",
        "first_name": "Samuel",
        "last_name": "Okunowo",
        "short_name": "Okunowo",
        "country": "NGA",
        "gsi": 83,
        "position": "RB/RM/RWB",
        "normalized": "RB",
        "secondary": ["RM", "RWB"],
        "foot": "Right",
        "height": 180,
        "weight": 74,
        "factual": date(1979, 3, 1),
        "age": 24,
        "era": "2000s",
        "club": "FC Barcelona",
        "attrs": {"pace": 88, "shooting": 62, "passing": 74, "dribbling": 76, "defending": 80, "physical": 76},
        "traits": ["Barcelona full-back", "Super Eagles"],
        "notes": "Nigeria right-back. Barcelona prospect whose peak is rated 83, inside the requested 80-83 band.",
    },
    {
        "slug": "emmanuel-adebayor",
        "full_name": "Emmanuel Adebayor",
        "first_name": "Emmanuel",
        "last_name": "Adebayor",
        "short_name": "Adebayor",
        "country": "TGO",
        "gsi": 88,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 191,
        "weight": 84,
        "factual": date(1984, 2, 26),
        "age": 23,
        "era": "2010s",
        "club": "Arsenal",
        "attrs": {"pace": 86, "shooting": 88, "passing": 74, "dribbling": 78, "defending": 40, "physical": 86},
        "traits": ["African Footballer of the Year 2008", "Togo captain"],
        "notes": "Togo striker. African Footballer of the Year 2008. Not the same record as the generated Adebayor regens.",
    },
    {
        "slug": "kossi-agassa",
        "full_name": "Kossi Agassa",
        "first_name": "Kossi",
        "last_name": "Agassa",
        "short_name": "Agassa",
        "country": "TGO",
        "gsi": 82,
        "position": "GK",
        "normalized": "GK",
        "secondary": [],
        "foot": "Right",
        "height": 190,
        "weight": 86,
        "factual": date(1978, 7, 2),
        "age": 24,
        "era": "2000s",
        "club": "FC Metz",
        "attrs": {"pace": 46, "shooting": 18, "passing": 55, "dribbling": 38, "defending": 82, "physical": 80},
        "traits": ["2006 World Cup", "Togo captain"],
        "notes": "Togo goalkeeper at the 2006 World Cup. Replaces a generated winger who reused this name.",
    },
    {
        "slug": "mohamed-kader",
        "full_name": "Mohamed Kader",
        "first_name": "Mohamed",
        "last_name": "Kader",
        "short_name": "M. Kader",
        "country": "TGO",
        "gsi": 81,
        "position": "ST/RW",
        "normalized": "ST",
        "secondary": ["RW"],
        "foot": "Right",
        "height": 178,
        "weight": 74,
        "factual": date(1979, 4, 8),
        "age": 24,
        "era": "2000s",
        "club": "SM Caen",
        "attrs": {"pace": 86, "shooting": 80, "passing": 70, "dribbling": 82, "defending": 34, "physical": 72},
        "traits": ["2006 World Cup goal"],
        "notes": "Togo forward. Scored Togo's goal at the 2006 World Cup. Distinct from Mohamed Kader Meïté.",
    },
    {
        "slug": "razak-omotoyossi",
        "full_name": "Razak Omotoyossi",
        "first_name": "Razak",
        "last_name": "Omotoyossi",
        "short_name": "Omotoyossi",
        "country": "BEN",
        "gsi": 84,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 177,
        "weight": 74,
        "factual": date(1985, 10, 8),
        "age": 24,
        "era": "2000s",
        "club": "Helsingborgs IF",
        "attrs": {"pace": 84, "shooting": 84, "passing": 68, "dribbling": 78, "defending": 36, "physical": 78},
        "traits": ["AFCON 2008 top scorer"],
        "notes": "Benin striker. Four goals at AFCON 2008, when Benin reached the quarter-finals.",
    },
    {
        "slug": "romuald-boco",
        "full_name": "Romuald Boco",
        "first_name": "Romuald",
        "last_name": "Boco",
        "short_name": "Boco",
        "country": "BEN",
        "gsi": 81,
        "position": "RB/RM/RWB",
        "normalized": "RB",
        "secondary": ["RM", "RWB"],
        "foot": "Right",
        "height": 178,
        "weight": 74,
        "factual": date(1985, 7, 8),
        "age": 24,
        "era": "2000s",
        "club": "Sligo Rovers",
        "attrs": {"pace": 82, "shooting": 66, "passing": 74, "dribbling": 76, "defending": 76, "physical": 74},
        "traits": ["Benin international"],
        "notes": "Benin right-sided player across more than a decade of internationals.",
    },
    {
        "slug": "mohamed-kallon",
        "full_name": "Mohamed Kallon",
        "first_name": "Mohamed",
        "last_name": "Kallon",
        "short_name": "Kallon",
        "country": "SLE",
        "gsi": 86,
        "position": "ST",
        "normalized": "ST",
        "secondary": ["LW"],
        "foot": "Right",
        "height": 180,
        "weight": 76,
        "factual": date(1979, 10, 6),
        "age": 24,
        "era": "2000s",
        "club": "Inter",
        "attrs": {"pace": 88, "shooting": 84, "passing": 72, "dribbling": 84, "defending": 34, "physical": 76},
        "traits": ["Inter striker", "Sierra Leone captain"],
        "notes": "Sierra Leone's leading striker of his generation. Replaces a generated centre-back who reused this name.",
    },
    {
        "slug": "kewullay-conteh",
        "full_name": "Kewullay Conteh",
        "first_name": "Kewullay",
        "last_name": "Conteh",
        "short_name": "Conteh",
        "country": "SLE",
        "gsi": 81,
        "position": "LB/CB",
        "normalized": "LB",
        "secondary": ["CB"],
        "foot": "Left",
        "height": 185,
        "weight": 80,
        "factual": date(1977, 12, 31),
        "age": 25,
        "era": "2000s",
        "club": "Ternana",
        "attrs": {"pace": 76, "shooting": 52, "passing": 68, "dribbling": 66, "defending": 82, "physical": 80},
        "traits": ["Sierra Leone defender"],
        "notes": "Sierra Leone left-back and centre-back of the late 1990s and 2000s.",
    },
    {
        "slug": "paul-kpaka",
        "full_name": "Paul Kpaka",
        "first_name": "Paul",
        "last_name": "Kpaka",
        "short_name": "Kpaka",
        "country": "SLE",
        "gsi": 82,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 178,
        "weight": 76,
        "factual": date(1981, 8, 7),
        "age": 24,
        "era": "2000s",
        "club": "Germinal Beerschot",
        "attrs": {"pace": 82, "shooting": 82, "passing": 66, "dribbling": 76, "defending": 32, "physical": 76},
        "traits": ["Belgian league striker"],
        "notes": "Sierra Leone striker who scored regularly in the Belgian league.",
    },
    {
        "slug": "james-debbah",
        "full_name": "James Debbah",
        "first_name": "James",
        "last_name": "Debbah",
        "short_name": "Debbah",
        "country": "LBR",
        "gsi": 84,
        "position": "ST/LW",
        "normalized": "ST",
        "secondary": ["LW"],
        "foot": "Right",
        "height": 180,
        "weight": 76,
        "factual": date(1969, 12, 14),
        "age": 25,
        "era": "1990s",
        "club": "AS Monaco",
        "attrs": {"pace": 86, "shooting": 82, "passing": 74, "dribbling": 82, "defending": 38, "physical": 78},
        "traits": ["Monaco", "Liberia captain"],
        "notes": "Liberia forward alongside George Weah. Played for Monaco and Paris Saint-Germain.",
    },
    {
        "slug": "christopher-wreh",
        "full_name": "Christopher Wreh",
        "first_name": "Christopher",
        "last_name": "Wreh",
        "short_name": "Wreh",
        "country": "LBR",
        "gsi": 81,
        "position": "ST",
        "normalized": "ST",
        "secondary": ["LW"],
        "foot": "Right",
        "height": 175,
        "weight": 72,
        "factual": date(1975, 5, 14),
        "age": 24,
        "era": "2000s",
        "club": "Arsenal",
        "attrs": {"pace": 84, "shooting": 78, "passing": 68, "dribbling": 76, "defending": 34, "physical": 70},
        "traits": ["Arsenal 1998"],
        "notes": "Liberia striker. Scored important goals for Arsenal in 1997-98.",
    },
    {
        "slug": "joe-nagbe",
        "full_name": "Joe Nagbe",
        "first_name": "Joe",
        "last_name": "Nagbe",
        "short_name": "Nagbe",
        "country": "LBR",
        "gsi": 82,
        "position": "CM/DM",
        "normalized": "CM",
        "secondary": ["DM"],
        "foot": "Right",
        "height": 184,
        "weight": 78,
        "factual": date(1968, 9, 2),
        "age": 25,
        "era": "1990s",
        "club": "OGC Nice",
        "attrs": {"pace": 74, "shooting": 72, "passing": 80, "dribbling": 76, "defending": 76, "physical": 78},
        "traits": ["Liberia most-capped midfielder"],
        "notes": "Joe Thunder Armstrong Nagbe. Liberia midfielder, Monaco and Nice, record international appearance holder of his era.",
    },
    {
        "slug": "charles-kabore",
        "full_name": "Charles Kaboré",
        "first_name": "Charles",
        "last_name": "Kaboré",
        "short_name": "Kaboré",
        "country": "BFA",
        "gsi": 83,
        "position": "DM/CM",
        "normalized": "DM",
        "secondary": ["CM"],
        "foot": "Right",
        "height": 181,
        "weight": 76,
        "factual": date(1988, 2, 9),
        "age": 23,
        "era": "2010s",
        "club": "Olympique de Marseille",
        "attrs": {"pace": 74, "shooting": 66, "passing": 80, "dribbling": 76, "defending": 82, "physical": 82},
        "traits": ["Marseille", "Burkina Faso captain"],
        "notes": "Burkina Faso holding midfielder. Long spell at Marseille and more than 100 caps.",
    },
    {
        "slug": "moumouni-dagano",
        "full_name": "Moumouni Dagano",
        "first_name": "Moumouni",
        "last_name": "Dagano",
        "short_name": "Dagano",
        "country": "BFA",
        "gsi": 83,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 186,
        "weight": 82,
        "factual": date(1981, 1, 1),
        "age": 24,
        "era": "2000s",
        "club": "AJ Auxerre",
        "attrs": {"pace": 80, "shooting": 84, "passing": 68, "dribbling": 74, "defending": 36, "physical": 84},
        "traits": ["Burkina Faso all-time scorer"],
        "notes": "Burkina Faso striker. Long the national team's leading scorer, with spells at Guingamp and Auxerre.",
    },
    {
        "slug": "aristide-bance",
        "full_name": "Aristide Bancé",
        "first_name": "Aristide",
        "last_name": "Bancé",
        "short_name": "Bancé",
        "country": "BFA",
        "gsi": 82,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 188,
        "weight": 84,
        "factual": date(1984, 9, 19),
        "age": 23,
        "era": "2010s",
        "club": "Mainz 05",
        "attrs": {"pace": 78, "shooting": 82, "passing": 66, "dribbling": 72, "defending": 36, "physical": 84},
        "traits": ["AFCON 2013"],
        "notes": "Burkina Faso striker and captain. Scored the extra-time winner against Togo at AFCON 2013.",
    },
    {
        "slug": "jonathan-pitroipa",
        "full_name": "Jonathan Pitroipa",
        "first_name": "Jonathan",
        "last_name": "Pitroipa",
        "short_name": "Pitroipa",
        "country": "BFA",
        "gsi": 84,
        "position": "RW/LW",
        "normalized": "RW",
        "secondary": ["LW"],
        "foot": "Right",
        "height": 176,
        "weight": 70,
        "factual": date(1986, 4, 12),
        "age": 23,
        "era": "2010s",
        "club": "Stade Rennais",
        "attrs": {"pace": 90, "shooting": 76, "passing": 76, "dribbling": 86, "defending": 40, "physical": 70},
        "traits": ["AFCON 2013 player of the tournament"],
        "notes": "Burkina Faso winger. Player of the tournament as Burkina Faso finished second at AFCON 2013.",
    },
    {
        "slug": "kalusha-bwalya",
        "full_name": "Kalusha Bwalya",
        "first_name": "Kalusha",
        "last_name": "Bwalya",
        "short_name": "Kalusha",
        "country": "ZMB",
        "gsi": 89,
        "position": "LW/AM",
        "normalized": "LW",
        "secondary": ["AM"],
        "foot": "Left",
        "height": 178,
        "weight": 74,
        "factual": date(1963, 8, 16),
        "age": 27,
        "era": "1980s",
        "club": "PSV",
        "attrs": {"pace": 88, "shooting": 86, "passing": 84, "dribbling": 90, "defending": 38, "physical": 74},
        "traits": ["African Footballer of the Year 1988"],
        "notes": "Zambia winger. African Footballer of the Year 1988 with PSV. Distinct from the George Bwalya regen.",
    },
    {
        "slug": "godfrey-chitalu",
        "full_name": "Godfrey Chitalu",
        "first_name": "Godfrey",
        "last_name": "Chitalu",
        "short_name": "Chitalu",
        "country": "ZMB",
        "gsi": 87,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 176,
        "weight": 74,
        "factual": date(1947, 10, 22),
        "age": 28,
        "era": "1970s",
        "club": "Nchanga Rangers",
        "attrs": {"pace": 84, "shooting": 90, "passing": 70, "dribbling": 80, "defending": 30, "physical": 76},
        "traits": ["Zambia all-time scorer", "1993 air disaster"],
        "notes": "Zambia's historic centre-forward. Died with the national team in the 1993 Gabon air disaster.",
    },
    {
        "slug": "charles-musonda",
        "full_name": "Charles Musonda",
        "first_name": "Charles",
        "last_name": "Musonda",
        "short_name": "Musonda",
        "country": "ZMB",
        "gsi": 84,
        "position": "AM/CM",
        "normalized": "AM",
        "secondary": ["CM"],
        "foot": "Right",
        "height": 173,
        "weight": 68,
        "factual": date(1969, 2, 22),
        "age": 26,
        "era": "1990s",
        "club": "RSC Anderlecht",
        "attrs": {"pace": 78, "shooting": 76, "passing": 86, "dribbling": 88, "defending": 52, "physical": 66},
        "traits": ["Anderlecht"],
        "notes": "Zambia attacking midfielder. Anderlecht technician of the late 1980s and early 1990s.",
    },
    {
        "slug": "christopher-katongo",
        "full_name": "Christopher Katongo",
        "first_name": "Christopher",
        "last_name": "Katongo",
        "short_name": "Katongo",
        "country": "ZMB",
        "gsi": 83,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 178,
        "weight": 76,
        "factual": date(1982, 8, 31),
        "age": 24,
        "era": "2010s",
        "club": "Zambia",
        "attrs": {"pace": 82, "shooting": 84, "passing": 70, "dribbling": 76, "defending": 42, "physical": 80},
        "traits": ["AFCON 2012 winner", "Golden Boot"],
        "notes": "Zambia captain and top scorer at AFCON 2012.",
    },
    {
        "slug": "theodore-whitmore",
        "full_name": "Theodore Whitmore",
        "first_name": "Theodore",
        "last_name": "Whitmore",
        "short_name": "Whitmore",
        "country": "JAM",
        "gsi": 84,
        "position": "AM",
        "normalized": "AM",
        "secondary": ["CM"],
        "foot": "Right",
        "height": 180,
        "weight": 74,
        "factual": date(1972, 8, 5),
        "age": 25,
        "era": "1990s",
        "club": "Hull City",
        "attrs": {"pace": 76, "shooting": 80, "passing": 84, "dribbling": 84, "defending": 58, "physical": 74},
        "traits": ["1998 World Cup brace"],
        "notes": "Jamaica attacking midfielder. Scored both goals against Japan at the 1998 World Cup.",
    },
    {
        "slug": "ricardo-fuller",
        "full_name": "Ricardo Fuller",
        "first_name": "Ricardo",
        "last_name": "Fuller",
        "short_name": "Fuller",
        "country": "JAM",
        "gsi": 83,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 191,
        "weight": 84,
        "factual": date(1979, 10, 31),
        "age": 24,
        "era": "2000s",
        "club": "Stoke City",
        "attrs": {"pace": 82, "shooting": 82, "passing": 68, "dribbling": 76, "defending": 38, "physical": 86},
        "traits": ["Stoke City", "Reggae Boyz"],
        "notes": "Jamaica striker. Premier League regular at Stoke City and a long-time Reggae Boy.",
    },
    {
        "slug": "robbie-earle",
        "full_name": "Robbie Earle",
        "first_name": "Robbie",
        "last_name": "Earle",
        "short_name": "Earle",
        "country": "JAM",
        "gsi": 83,
        "position": "AM/ST",
        "normalized": "AM",
        "secondary": ["ST"],
        "foot": "Right",
        "height": 175,
        "weight": 72,
        "factual": date(1965, 1, 27),
        "age": 25,
        "era": "1990s",
        "club": "Wimbledon",
        "attrs": {"pace": 74, "shooting": 80, "passing": 80, "dribbling": 78, "defending": 55, "physical": 74},
        "traits": ["1998 World Cup"],
        "notes": "Wimbledon forward who represented Jamaica at the 1998 World Cup.",
    },
    {
        "slug": "deon-burton",
        "full_name": "Deon Burton",
        "first_name": "Deon",
        "last_name": "Burton",
        "short_name": "Burton",
        "country": "JAM",
        "gsi": 82,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 173,
        "weight": 72,
        "factual": date(1976, 10, 25),
        "age": 24,
        "era": "2000s",
        "club": "Derby County",
        "attrs": {"pace": 82, "shooting": 82, "passing": 66, "dribbling": 74, "defending": 34, "physical": 74},
        "traits": ["1998 World Cup", "Jamaica all-time scorer"],
        "notes": "Jamaica striker. Derby County and Sheffield United, and one of the Reggae Boyz' leading scorers.",
    },
    {
        "slug": "russell-latapy",
        "full_name": "Russell Latapy",
        "first_name": "Russell",
        "last_name": "Latapy",
        "short_name": "Latapy",
        "country": "TTO",
        "gsi": 86,
        "position": "AM",
        "normalized": "AM",
        "secondary": ["CM"],
        "foot": "Right",
        "height": 170,
        "weight": 66,
        "factual": date(1968, 8, 2),
        "age": 25,
        "era": "1990s",
        "club": "Hibernian",
        "attrs": {"pace": 78, "shooting": 78, "passing": 88, "dribbling": 90, "defending": 40, "physical": 62},
        "traits": ["The Little Magician"],
        "notes": "Trinidad and Tobago playmaker, Dwight Yorke's international partner. Hibernian and Porto.",
    },
    {
        "slug": "stern-john",
        "full_name": "Stern John",
        "first_name": "Stern",
        "last_name": "John",
        "short_name": "Stern John",
        "country": "TTO",
        "gsi": 85,
        "position": "ST",
        "normalized": "ST",
        "secondary": [],
        "foot": "Right",
        "height": 180,
        "weight": 78,
        "factual": date(1976, 10, 30),
        "age": 24,
        "era": "2000s",
        "club": "Nottingham Forest",
        "attrs": {"pace": 80, "shooting": 86, "passing": 68, "dribbling": 74, "defending": 36, "physical": 82},
        "traits": ["2006 World Cup", "T&T all-time scorer"],
        "notes": "Trinidad and Tobago's all-time leading scorer. Nottingham Forest and the 2006 World Cup.",
    },
    {
        "slug": "shaka-hislop",
        "full_name": "Shaka Hislop",
        "first_name": "Shaka",
        "last_name": "Hislop",
        "short_name": "Hislop",
        "country": "TTO",
        "gsi": 84,
        "position": "GK",
        "normalized": "GK",
        "secondary": [],
        "foot": "Right",
        "height": 193,
        "weight": 88,
        "factual": date(1969, 2, 22),
        "age": 24,
        "era": "2000s",
        "club": "Newcastle United",
        "attrs": {"pace": 46, "shooting": 18, "passing": 58, "dribbling": 40, "defending": 84, "physical": 84},
        "traits": ["2006 World Cup", "Premier League goalkeeper"],
        "notes": "Trinidad and Tobago goalkeeper. Newcastle, West Ham and Portsmouth, and the 2006 World Cup.",
    },
    {
        "slug": "dennis-lawrence",
        "full_name": "Dennis Lawrence",
        "first_name": "Dennis",
        "last_name": "Lawrence",
        "short_name": "Lawrence",
        "country": "TTO",
        "gsi": 82,
        "position": "CB",
        "normalized": "CB",
        "secondary": [],
        "foot": "Right",
        "height": 196,
        "weight": 90,
        "factual": date(1974, 8, 1),
        "age": 24,
        "era": "2000s",
        "club": "Swansea City",
        "attrs": {"pace": 60, "shooting": 48, "passing": 62, "dribbling": 48, "defending": 84, "physical": 88},
        "traits": ["2006 World Cup qualifier"],
        "notes": "Trinidad and Tobago centre-back. Headed the goal against Bahrain that qualified the country for the 2006 World Cup.",
    },
)


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    countries = _load_countries(conn)
    for player_id, country_key, _previous in _COUNTRY_FIXES:
        _set_country(conn, countries, player_id, country_key)

    _apply_rating(
        conn,
        _YAYA,
        92,
        position="DM/CM/AM",
        normalized="DM",
        secondary=["CM", "AM"],
        attrs={"pace": 87, "shooting": 85, "passing": 90, "dribbling": 86, "defending": 79, "physical": 92},
        tier="legend",
        legend_shares=True,
    )

    for player_id, full_name in _PLACEHOLDER_REGENS:
        _archive_placeholder(conn, player_id, full_name)

    if _holdings(conn, _JUMA_BAH) == 0:
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET real_player_tier = 'established',
                    legendary_profile_id = NULL,
                    is_tradable = true,
                    is_real_player = true,
                    updated_at = NOW()
                WHERE id = :pid
                  AND real_player_tier = 'legend'
                """),
            {"pid": _JUMA_BAH},
        )
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET total_shares = 200,
                    released_shares = 200,
                    circulating_shares = 0,
                    status = 'active',
                    updated_at = NOW()
                WHERE player_id = :pid
                  AND total_shares = 1
                """),
            {"pid": _JUMA_BAH},
        )
        conn.execute(
            sa.text("""
                UPDATE player_summary_read_models
                SET summary_json = (
                        COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                        jsonb_build_object(
                            'is_legend', false,
                            'real_player_tier', 'established',
                            'is_tradable', true,
                            'total_shares', 200,
                            'released_shares', 200,
                            'available_shares', 200,
                            'market_visibility', jsonb_build_object('status', 'visible', 'eligible', true)
                        )
                    )::json,
                    updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": _JUMA_BAH},
        )

    sessegnon_dob = _game_dob(date(1984, 6, 1), 23)
    _apply_rating(
        conn,
        _SESSEGNON,
        86,
        position="AM/LW/ST",
        normalized="AM",
        secondary=["LW", "ST"],
        attrs={"pace": 84, "shooting": 78, "passing": 84, "dribbling": 88, "defending": 60, "physical": 70},
        tier="legend",
        game_dob=sessegnon_dob,
        factual_dob=date(1984, 6, 1),
        prime_age=23,
        legend_shares=True,
    )
    if _holdings(conn, _SESSEGNON) == 0:
        conn.execute(
            sa.text("""
                INSERT INTO legendary_player_profiles (
                    id, slug, full_name, country_code, primary_position, secondary_positions_json,
                    preferred_foot, historical_height_cm, gtex_height_cm, era,
                    legendary_classification, is_active, is_searchable, is_tradable,
                    is_rentable, is_national_team_eligible,
                    governed_gsi, governed_potential_gsi, gsi_methodology_version,
                    date_of_birth, factual_date_of_birth, prime_age_at_snapshot,
                    signature_traits_json, technical_profile_json, physical_profile_json, mental_profile_json,
                    portrait_metadata_json, source_evidence_json, football_evidence_json,
                    editorial_status, rights_status, catalogue_status, metadata_json, source_notes,
                    created_at, updated_at
                ) VALUES (
                    :id, 'stephane-sessegnon', 'Stéphane Sessegnon', 'BEN', 'AM', CAST('["LW", "ST"]' AS json),
                    'Right', 172, 172, '2010s',
                    'icon', true, true, true,
                    true, true,
                    86, 86, 'v2.0',
                    :game_dob, '1984-06-01', 23,
                    CAST('["Benin captain", "PSG"]' AS json), CAST('{}' AS json), CAST('{}' AS json), CAST('{}' AS json),
                    CAST('{}' AS json), CAST('[]' AS json), CAST('[]' AS json),
                    'approved', 'unknown', 'approved', CAST('{}' AS json),
                    'Existing Benin player promoted to a 1-of-1 legend instead of inserting a duplicate.',
                    NOW(), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    governed_gsi = 86,
                    governed_potential_gsi = 86,
                    primary_position = 'AM',
                    country_code = 'BEN',
                    is_searchable = true,
                    updated_at = NOW()
                """),
            {"id": _lid("stephane-sessegnon"), "game_dob": sessegnon_dob},
        )
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET legendary_profile_id = :lid,
                    height_cm = COALESCE(height_cm, 172),
                    updated_at = NOW()
                WHERE id = :pid
                """),
            {"lid": _lid("stephane-sessegnon"), "pid": _SESSEGNON},
        )

    for player in _NEW_LEGENDS:
        _insert_legend(conn, countries, player)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    countries = _load_countries(conn)
    for player in _NEW_LEGENDS:
        player_id = _pid(player["slug"])
        conn.execute(sa.text("DELETE FROM ingestion_players WHERE id = :pid"), {"pid": player_id})
        conn.execute(sa.text("DELETE FROM legendary_player_profiles WHERE id = :lid"), {"lid": _lid(player["slug"])})
    conn.execute(
        sa.text("DELETE FROM legendary_player_profiles WHERE id = :lid"),
        {"lid": _lid("stephane-sessegnon")},
    )
    for player_id, _new, _previous in _COUNTRY_FIXES:
        previous = _PREVIOUS_COUNTRY[player_id]
        _set_country(conn, countries, player_id, previous)
    _apply_rating(
        conn,
        _YAYA,
        89,
        position="DM",
        normalized="DM",
        secondary=["AM C"],
        tier="legend",
        legend_shares=True,
    )
    conn.execute(
        sa.text("""
            UPDATE ingestion_players
            SET real_player_tier = 'established',
                legendary_profile_id = NULL,
                position = 'DM',
                normalized_position = 'DM',
                secondary_positions_json = CAST('["AM RLC", "F C"]' AS json),
                governed_gsi = 80,
                governed_potential_gsi = 84,
                potential = 84,
                date_of_birth = '2004-06-01',
                updated_at = NOW()
            WHERE id = :pid
            """),
        {"pid": _SESSEGNON},
    )
    conn.execute(
        sa.text("""
            UPDATE ingestion_players
            SET real_player_tier = 'legend', updated_at = NOW()
            WHERE id = :pid
            """),
        {"pid": _JUMA_BAH},
    )
    if _holdings(conn, _JUMA_BAH) == 0:
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET total_shares = 1, released_shares = 1, circulating_shares = 0, updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": _JUMA_BAH},
        )
    for player_id, _full_name in _PLACEHOLDER_REGENS:
        conn.execute(
            sa.text("""
                UPDATE ingestion_players
                SET real_player_tier = NULL, is_tradable = true, updated_at = NOW()
                WHERE id = :pid
                """),
            {"pid": player_id},
        )
        conn.execute(
            sa.text("""
                UPDATE player_share_markets
                SET status = 'active', updated_at = NOW()
                WHERE player_id = :pid
                """),
            {"pid": player_id},
        )
