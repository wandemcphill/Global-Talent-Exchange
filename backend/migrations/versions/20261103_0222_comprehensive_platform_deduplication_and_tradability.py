"""Comprehensive platform deduplication, priority attribute retention, and universal tradability.

Revision ID: 20261103_0222_comprehensive_platform_deduplication_and_tradability
Revises: 20261103_0221_permanent_legend_ratings_and_market_governance
Create Date: 2026-11-03 16:30:00.000000
"""

from collections import defaultdict
import datetime
import re
import unicodedata

from alembic import op

revision = "20261103_0222_comprehensive_platform_deduplication_and_tradability"
down_revision = "20261103_0221_permanent_legend_ratings_and_market_governance"
branch_labels = None
depends_on = None

ACTIVE_SUPERSTARS = {
    "harry kane",
    "kylian mbappe",
    "vinicius junior",
    "jude bellingham",
    "rodri",
    "thibaut courtois",
    "erling haaland",
    "bukayo saka",
    "victor osimhen",
    "joshua kimmich",
    "joshua walter kimmich",
    "emre can",
    "adnan januzaj",
    "alessio romagnoli",
    "dante",
    "thelo aasgaard",
    "aaron wanbissaka",
    "aaron wan bissaka",
    "paul onuachu",
    "ebere paul onuachu",
    "mohamed salah",
    "kevin de bruyne",
    "virgil van dijk",
    "alisson becker",
    "bernardo silva",
    "bruno fernandes",
    "declan rice",
    "florian wirtz",
    "jamal musiala",
    "lamine yamal",
    "cole palmer",
}

ACTIVE_SUPERSTAR_KEEPER_IDS = [
    "0b429e4e-3588-4e05-aed4-70015f211585",  # Harry Kane
    "729dc5c1-fc66-4b4a-933b-b69785cebaf1",  # Kylian Mbappé
    "b89bf448-982b-4cfb-86cc-1525eb4e70d1",  # Vinicius Junior
    "517f060d-ea68-49f1-9e94-ddb3e5265585",  # Jude Bellingham
    "f4b4531b-a342-48b5-8f43-618cfa0dc49a",  # Bukayo Saka
    "2dc62da9-550b-423b-bfe3-445de565051e",  # Victor Osimhen
    "e7a8ab67-7737-457b-b717-ee457be4ef31",  # Paul Onuachu
    "557789ab-838f-4599-bb86-669b6cf100f4",  # Aaron Wan-Bissaka
    "9bb4b8c1-0b9e-4804-baa9-a62cf480c3d4",  # Joshua Kimmich
    "5f79b913-9e1f-4735-93b0-b3ce2c4d9577",  # Rodri
    "0fb47397-8e40-4f65-ad37-fd0760515e03",  # Thibaut Courtois
]

FAMOUS_MONONYMS = {
    "pele",
    "maradona",
    "ronaldinho",
    "kaka",
    "neymar",
    "zidane",
    "rivaldo",
    "cafu",
    "romario",
    "zico",
    "socrates",
    "garrincha",
    "eusebio",
    "figo",
}


def norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def simplify_club(club: str | None) -> str:
    c = norm(club)
    for w in [
        "fc",
        "cf",
        "sc",
        "ac",
        "as",
        "ssc",
        "sv",
        "rc",
        "cd",
        "sk",
        "fk",
        "club",
        "munchen",
        "munich",
        "de",
        "hotspur",
    ]:
        c = re.sub(rf"\b{w}\b", "", c)
    return c.strip()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    raw_conn = conn.connection
    with raw_conn.cursor() as cur:
        # 1. Fetch candidate players
        cur.execute("""
            SELECT 
                ip.id, 
                ip.full_name, 
                ip.canonical_display_name, 
                ip.source_provider, 
                ip.real_player_tier, 
                ip.governed_gsi,
                ip.date_of_birth,
                ip.factual_date_of_birth,
                ip.country_id,
                ic.name as country_name,
                ip.real_world_club_name,
                ip.position,
                ip.normalized_position,
                (ip.dna_profile::jsonb->'attributes'->>'pace') IS NOT NULL as has_pace,
                (ip.dna_profile::jsonb->>'portraitUrl') as portrait_url,
                (ip.dna_profile::jsonb->>'photo_url') as photo_url,
                (ip.dna_profile::jsonb->>'image_url') as image_url,
                COALESCE(psm.circulating_shares, 0) as circ_shares,
                psm.total_shares,
                ip.legendary_profile_id
            FROM ingestion_players ip
            LEFT JOIN ingestion_countries ic ON ic.id = ip.country_id
            LEFT JOIN player_share_markets psm ON psm.player_id = ip.id
            WHERE COALESCE(ip.real_player_tier, '') != 'archived_duplicate'
              AND (ip.is_tradable IS TRUE OR psm.status = 'active');
        """)
        rows = cur.fetchall()

        players = {}
        for r in rows:
            (
                pid,
                fname,
                cname,
                src,
                tier,
                gsi,
                dob,
                f_dob,
                cid,
                country,
                club,
                pos,
                npos,
                has_pace,
                port,
                photo,
                img_u,
                circ,
                shares,
                leg_id,
            ) = r
            birth_year = None
            actual_dob = f_dob or dob
            if actual_dob:
                if isinstance(actual_dob, (datetime.date, datetime.datetime)):
                    birth_year = actual_dob.year
                else:
                    try:
                        birth_year = int(str(actual_dob)[:4])
                    except (ValueError, TypeError):
                        pass

            has_valid_attrs = bool(has_pace)
            img = port or photo or img_u
            players[pid] = {
                "id": pid,
                "full_name": fname or "",
                "canonical": cname or fname or "",
                "source": src or "",
                "tier": tier or "",
                "gsi": gsi or 70,
                "dob": actual_dob,
                "birth_year": birth_year,
                "cid": cid,
                "country": country or "",
                "club": club or "",
                "pos": npos or pos or "MID",
                "has_standard_attrs": has_valid_attrs,
                "img": img,
                "has_img": bool(img),
                "circ": circ,
                "shares": shares,
                "leg_id": leg_id,
            }

        # 2. Group into duplicate clusters
        by_name = defaultdict(list)
        for pid, p in players.items():
            nc = norm(p["canonical"])
            nf = norm(p["full_name"])
            if nc and len(nc.split()) >= 2:
                by_name[nc].append(pid)
            if nf and len(nf.split()) >= 2 and nf != nc:
                by_name[nf].append(pid)

        for pid, p in players.items():
            nc = norm(p["canonical"])
            if nc in FAMOUS_MONONYMS:
                by_name[nc].append(pid)

        duplicate_groups = []
        seen_player_ids = set()

        for name_key, pids in by_name.items():
            unique_pids = [pid for pid in dict.fromkeys(pids) if pid not in seen_player_ids]
            if len(unique_pids) < 2:
                continue

            subclusters = []
            for pid in unique_pids:
                p = players[pid]
                assigned = False
                for sc in subclusters:
                    ref = sc[0]
                    same_country = (
                        p["country"]
                        and ref["country"]
                        and (p["country"].lower() == ref["country"].lower() or p["cid"] == ref["cid"])
                    )
                    c1 = simplify_club(p["club"])
                    c2 = simplify_club(ref["club"])
                    same_club = bool(c1 and c2 and (c1 in c2 or c2 in c1))
                    close_age = bool(
                        p["birth_year"] and ref["birth_year"] and abs(p["birth_year"] - ref["birth_year"]) <= 7
                    )

                    if same_club:
                        sc.append(p)
                        assigned = True
                        break
                    elif same_country and (close_age or p["pos"] == ref["pos"]):
                        sc.append(p)
                        assigned = True
                        break
                    elif close_age and (p["pos"] == ref["pos"]):
                        sc.append(p)
                        assigned = True
                        break

                if not assigned:
                    subclusters.append([p])

            for sc in subclusters:
                if len(sc) > 1:
                    duplicate_groups.append(sc)
                    for p in sc:
                        seen_player_ids.add(p["id"])

        retired_ids = []
        keepers = []
        holding_migrations = []
        image_propagations = []

        # 3. Select keepers with priority scoring
        for grp in duplicate_groups:
            names = [p["canonical"] for p in grp]
            norm_name = norm(names[0])
            is_active_superstar = (
                norm_name in ACTIVE_SUPERSTARS
                or any(norm(p["canonical"]) in ACTIVE_SUPERSTARS for p in grp)
                or any(norm(p["full_name"]) in ACTIVE_SUPERSTARS for p in grp)
            )

            def score_player(p):
                score = 0
                if is_active_superstar:
                    if p["tier"] == "legend" or p["leg_id"] or p["source"] in ("gtex_legend", "gtex_legend_prime"):
                        score -= 2000
                    else:
                        score += 500
                else:
                    if p["tier"] == "legend" or p["leg_id"] or p["source"] in ("gtex_legend", "gtex_legend_prime"):
                        score += 500

                if p["has_standard_attrs"]:
                    score += 200
                if p["has_img"]:
                    score += 100

                if p["source"] == "curated-wonderkids":
                    score += 80
                elif p["source"] == "sofifa_fc25":
                    score += 70
                elif p["source"] == "fm23_genie_scout":
                    score += 60
                elif p["source"] == "afcon_international_registry":
                    score += 40
                elif p["source"] == "sportmonks" and p["tier"] in ("marquee", "established", "wonderkid"):
                    score += 30
                elif p["source"] == "sportmonks":
                    score += 10

                if p["circ"] > 0:
                    score += 40
                if p["gsi"] >= 75:
                    score += 15
                return score

            sorted_grp = sorted(grp, key=score_player, reverse=True)
            keeper = sorted_grp[0]
            to_retire = sorted_grp[1:]

            if not keeper["has_img"]:
                for r in to_retire:
                    if r["has_img"]:
                        image_propagations.append((keeper["id"], r["img"]))
                        break

            keepers.append((keeper, to_retire))
            for r in to_retire:
                retired_ids.append(r["id"])
                if r["circ"] > 0:
                    holding_migrations.append((r["id"], keeper["id"], r["circ"]))

        # 4. Image propagation batch
        if image_propagations:
            cur.execute("CREATE TEMP TABLE tmp_image_props (kid VARCHAR, img TEXT) ON COMMIT DROP;")
            cur.executemany("INSERT INTO tmp_image_props (kid, img) VALUES (%s, %s);", image_propagations)
            cur.execute("""
                UPDATE ingestion_players ip
                SET dna_profile = jsonb_set(
                    COALESCE(ip.dna_profile::jsonb, '{}'::jsonb),
                    '{portraitUrl}',
                    to_jsonb(p.img)
                )
                FROM tmp_image_props p
                WHERE ip.id = p.kid;
            """)

        # 5. Holding migrations batch (safeguard existing user investments)
        if holding_migrations:
            cur.execute(
                "CREATE TEMP TABLE tmp_holding_migrations (src_id VARCHAR, dst_id VARCHAR, amount INT) ON COMMIT DROP;"
            )
            cur.executemany(
                "INSERT INTO tmp_holding_migrations (src_id, dst_id, amount) VALUES (%s, %s, %s);",
                holding_migrations,
            )

            cur.execute("""
                UPDATE player_share_holdings h
                SET player_id = m.dst_id
                FROM tmp_holding_migrations m
                WHERE h.player_id = m.src_id
                  AND h.user_id NOT IN (
                      SELECT user_id FROM player_share_holdings WHERE player_id = m.dst_id
                  );
            """)

            cur.execute("""
                UPDATE player_share_holdings dst
                SET share_count = dst.share_count + src.share_count,
                    updated_at = NOW()
                FROM player_share_holdings src
                JOIN tmp_holding_migrations m ON m.src_id = src.player_id
                WHERE dst.player_id = m.dst_id
                  AND src.user_id = dst.user_id;
            """)

            cur.execute("""
                DELETE FROM player_share_holdings
                WHERE player_id IN (SELECT src_id FROM tmp_holding_migrations);
            """)

            cur.execute("""
                UPDATE player_share_markets dst
                SET circulating_shares = COALESCE(dst.circulating_shares, 0) + agg.total_amt,
                    released_shares = GREATEST(COALESCE(dst.released_shares, 0), COALESCE(dst.circulating_shares, 0) + agg.total_amt),
                    total_shares = GREATEST(COALESCE(dst.total_shares, 0), GREATEST(COALESCE(dst.released_shares, 0), COALESCE(dst.circulating_shares, 0) + agg.total_amt)),
                    updated_at = NOW()
                FROM (
                    SELECT dst_id, SUM(amount) as total_amt
                    FROM tmp_holding_migrations
                    GROUP BY dst_id
                ) agg
                WHERE dst.player_id = agg.dst_id;
            """)

        # 6. Retire duplicates in temp table
        cur.execute("CREATE TEMP TABLE tmp_retire_ids (pid VARCHAR PRIMARY KEY) ON COMMIT DROP;")
        cur.executemany("INSERT INTO tmp_retire_ids (pid) VALUES (%s);", [(pid,) for pid in retired_ids])

        cur.execute("""
            UPDATE ingestion_players ip
            SET real_player_tier = 'archived_duplicate',
                is_tradable = false,
                is_real_player = false,
                legendary_profile_id = NULL,
                updated_at = NOW()
            FROM tmp_retire_ids r
            WHERE ip.id = r.pid;
        """)

        cur.execute("""
            UPDATE player_share_markets psm
            SET status = 'retired',
                total_shares = 0,
                released_shares = 0,
                circulating_shares = 0,
                updated_at = NOW()
            FROM tmp_retire_ids r
            WHERE psm.player_id = r.pid;
        """)

        cur.execute("""
            DELETE FROM player_summary_read_models
            WHERE player_id IN (SELECT pid FROM tmp_retire_ids);
        """)

        # 7. Active superstars governance
        cur.execute(
            """
            UPDATE ingestion_players
            SET real_player_tier = 'marquee',
                is_tradable = true,
                is_real_player = true,
                legendary_profile_id = NULL,
                updated_at = NOW()
            WHERE id = ANY(%s);
        """,
            (ACTIVE_SUPERSTAR_KEEPER_IDS,),
        )

        cur.execute(
            """
            UPDATE player_share_markets
            SET total_shares = GREATEST(200, COALESCE(circulating_shares, 0)),
                released_shares = GREATEST(200, COALESCE(circulating_shares, 0)),
                status = 'active',
                updated_at = NOW()
            WHERE player_id = ANY(%s);
        """,
            (ACTIVE_SUPERSTAR_KEEPER_IDS,),
        )

        # 8. Legends governance: strictly 1 share, status active
        cur.execute("""
            UPDATE player_share_markets
            SET total_shares = GREATEST(1, COALESCE(circulating_shares, 1)),
                released_shares = GREATEST(1, COALESCE(circulating_shares, 1)),
                status = 'active',
                updated_at = NOW()
            FROM ingestion_players ip
            WHERE player_share_markets.player_id = ip.id
              AND ip.real_player_tier = 'legend';
        """)

        # 9. Universal tradability for all kept players
        cur.execute("""
            UPDATE ingestion_players
            SET is_tradable = true,
                updated_at = NOW()
            WHERE COALESCE(real_player_tier, '') != 'archived_duplicate'
              AND is_tradable IS NOT TRUE;
        """)

        # 10. Insert missing player_share_markets
        cur.execute("""
            INSERT INTO player_share_markets (
                player_id, total_shares, released_shares, circulating_shares, 
                share_price_coin, status, created_at, updated_at
            )
            SELECT 
                ip.id,
                CASE 
                    WHEN ip.real_player_tier = 'legend' THEN 1
                    WHEN ip.real_player_tier = 'marquee' THEN 200
                    ELSE 600
                END,
                CASE 
                    WHEN ip.real_player_tier = 'legend' THEN 1
                    WHEN ip.real_player_tier = 'marquee' THEN 200
                    ELSE 600
                END,
                0,
                ROUND(250.0 * POWER(COALESCE(ip.governed_gsi, 75) / 90.0, 3.2) * 3.6, 2),
                'active',
                NOW(),
                NOW()
            FROM ingestion_players ip
            LEFT JOIN player_share_markets psm ON psm.player_id = ip.id
            WHERE COALESCE(ip.real_player_tier, '') != 'archived_duplicate'
              AND psm.player_id IS NULL
            ON CONFLICT (player_id) DO NOTHING;
        """)

        # 11. Activate non-duplicate player_share_markets
        cur.execute("""
            UPDATE player_share_markets psm
            SET status = 'active',
                updated_at = NOW()
            FROM ingestion_players ip
            WHERE psm.player_id = ip.id
              AND COALESCE(ip.real_player_tier, '') != 'archived_duplicate'
              AND psm.status != 'active';
        """)

        # 12. Ensure all kept players are in read models with attributes
        cur.execute("""
            INSERT INTO player_summary_read_models (
                player_id, player_name, current_club_name, current_value_credits,
                movement_pct, market_interest_score, average_rating, summary_json,
                created_at, updated_at
            )
            SELECT 
                ip.id,
                ip.full_name,
                ip.real_world_club_name,
                COALESCE(psm.share_price_coin::float8, 50.0),
                0.0,
                75,
                COALESCE(ip.governed_gsi::float8, 75.0),
                jsonb_build_object(
                    'id', ip.id,
                    'name', ip.full_name,
                    'canonical_name', COALESCE(ip.canonical_display_name, ip.full_name),
                    'real_player_tier', COALESCE(ip.real_player_tier, 'established'),
                    'is_legend', (ip.real_player_tier = 'legend'),
                    'is_tradable', true,
                    'total_shares', COALESCE(psm.total_shares, 600),
                    'released_shares', COALESCE(psm.released_shares, 600),
                    'circulating_shares', COALESCE(psm.circulating_shares, 0),
                    'share_price_coin', COALESCE(psm.share_price_coin, 50.0),
                    'gsi', COALESCE(ip.governed_gsi, 75),
                    'overall', COALESCE(ip.governed_gsi, 75),
                    'attributes', COALESCE(ip.dna_profile::jsonb->'attributes', '{}'::jsonb)
                )::json,
                NOW(),
                NOW()
            FROM ingestion_players ip
            LEFT JOIN player_share_markets psm ON psm.player_id = ip.id
            LEFT JOIN player_summary_read_models rm ON rm.player_id = ip.id
            WHERE COALESCE(ip.real_player_tier, '') != 'archived_duplicate'
              AND rm.player_id IS NULL
            ON CONFLICT (player_id) DO NOTHING;
        """)

        # 13. Sync is_tradable to existing read models
        cur.execute("""
            UPDATE player_summary_read_models rm
            SET summary_json = (
                COALESCE(rm.summary_json::jsonb, '{}'::jsonb) || jsonb_build_object('is_tradable', true)
            )::json,
            updated_at = NOW()
            FROM ingestion_players ip
            WHERE rm.player_id = ip.id
              AND COALESCE(ip.real_player_tier, '') != 'archived_duplicate'
              AND (rm.summary_json->>'is_tradable' IS NULL OR rm.summary_json->>'is_tradable' != 'true');
        """)


def downgrade() -> None:
    pass
