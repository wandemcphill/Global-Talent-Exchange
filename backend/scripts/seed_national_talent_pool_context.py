"""Phase 4 (N56) — give every GTEX regen a production-safe, searchable context.

Creates a GTEX-native federation context (no fake real-world clubs):

    Competition : "National Talent Pool"  (source_provider='gtex_native')
    Club        : "Free Agent"            (source_provider='gtex_native')

and backfills each regen (source_provider='gtex_regen') with:

    * country_id              -> resolved from its dna/summary nationality
    * current_competition_id  -> National Talent Pool
    * current_club_id         -> Free Agent
    * real_world_league_name  -> "National Talent Pool"  (display + _has_context)
    * real_world_club_name    -> "Free Agent"            (display + _has_context)

This satisfies the issuance eligibility gates (require_country +
require_club_or_competition_context) WITHOUT marking regens as real players
(is_real_player stays false). It writes only to context tables, never to
player_share_markets. Idempotent: re-runs converge and create zero duplicates.
"""

from __future__ import annotations

import argparse
import re
import unicodedata

import psycopg

NATIVE_PROVIDER = "gtex_native"
COMPETITION_EXT = "national-talent-pool"
COMPETITION_NAME = "National Talent Pool"
CLUB_EXT = "free-agent"
CLUB_NAME = "Free Agent"

# Nationalities whose display name does not match ingestion_countries.name
# directly; resolved via FIFA/alpha-3 code instead.
NATIONALITY_CODE_ALIASES = {
    "turkey": "TUR",
    "ivory coast": "CIV",
    "ethiopia": "ETH",
    "dr congo": "COD",
}


def _slug(value: str) -> str:
    norm = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")


def _load_url() -> str | None:
    try:
        for line in open(".env", encoding="utf-8"):
            if line.startswith("GTE_DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        return None
    return None


def ensure_competition(cur) -> str:
    cur.execute(
        """
        INSERT INTO ingestion_competitions
            (id, source_provider, provider_external_id, name, slug, competition_type,
             is_major, is_tradable, last_synced_at, created_at, updated_at)
        VALUES (gen_random_uuid()::text, %(prov)s, %(ext)s, %(name)s, %(slug)s, 'national_pool',
             false, true, now(), now(), now())
        ON CONFLICT (source_provider, provider_external_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        {"prov": NATIVE_PROVIDER, "ext": COMPETITION_EXT, "name": COMPETITION_NAME, "slug": COMPETITION_EXT},
    )
    return cur.fetchone()[0]


def ensure_club(cur, competition_id: str) -> str:
    cur.execute(
        """
        INSERT INTO ingestion_clubs
            (id, source_provider, provider_external_id, name, slug, short_name,
             current_competition_id, is_tradable, last_synced_at, created_at, updated_at)
        VALUES (gen_random_uuid()::text, %(prov)s, %(ext)s, %(name)s, %(slug)s, %(name)s,
             %(comp)s, true, now(), now(), now())
        ON CONFLICT (source_provider, provider_external_id)
            DO UPDATE SET current_competition_id = EXCLUDED.current_competition_id
        RETURNING id
        """,
        {"prov": NATIVE_PROVIDER, "ext": CLUB_EXT, "name": CLUB_NAME, "slug": CLUB_EXT, "comp": competition_id},
    )
    return cur.fetchone()[0]


def build_country_resolver(cur) -> dict[str, str]:
    """Map a lowercased nationality string -> country_id."""
    cur.execute("select id, name, alpha2_code, alpha3_code, fifa_code from ingestion_countries")
    by_name: dict[str, str] = {}
    by_code: dict[str, str] = {}
    for cid, name, a2, a3, fifa in cur.fetchall():
        if name:
            by_name[name.strip().lower()] = cid
        for code in (a2, a3, fifa):
            if code:
                by_code[code.strip().upper()] = cid
    return {"name": by_name, "code": by_code}


def resolve_country_id(cur, nationality: str, resolver: dict) -> str:
    key = nationality.strip().lower()
    cid = resolver["name"].get(key)
    if cid:
        return cid
    alias = NATIONALITY_CODE_ALIASES.get(key)
    if alias and alias in resolver["code"]:
        return resolver["code"][alias]
    # Last resort: create a GTEX-native country row so no regen is left unmapped.
    cur.execute(
        """
        INSERT INTO ingestion_countries
            (id, source_provider, provider_external_id, name, fifa_code,
             is_enabled_for_universe, last_synced_at, created_at, updated_at)
        VALUES (gen_random_uuid()::text, %(prov)s, %(ext)s, %(name)s, %(fifa)s,
             true, now(), now(), now())
        ON CONFLICT (source_provider, provider_external_id) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        {"prov": NATIVE_PROVIDER, "ext": _slug(nationality), "name": nationality, "fifa": (alias or None)},
    )
    cid = cur.fetchone()[0]
    resolver["name"][key] = cid
    return cid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    url = args.database_url or _load_url()
    if not url:
        raise SystemExit("No database URL (pass --database-url or set GTE_DATABASE_URL in .env)")

    with psycopg.connect(url) as conn:
        cur = conn.cursor()
        comp_id = ensure_competition(cur)
        club_id = ensure_club(cur, comp_id)
        print(f"National Talent Pool competition: {comp_id}")
        print(f"Free Agent club               : {club_id}")

        # Distinct regen nationalities from the read-model summary_json.
        cur.execute(
            """
            select distinct prm.summary_json->>'nationality'
            from player_summary_read_models prm
            join ingestion_players p on p.id = prm.player_id
            where p.source_provider = 'gtex_regen'
              and coalesce(prm.summary_json->>'nationality','') <> ''
            """
        )
        nationalities = [r[0] for r in cur.fetchall()]
        resolver = build_country_resolver(cur)
        nat_to_country = {nat: resolve_country_id(cur, nat, resolver) for nat in nationalities}
        print(f"resolved {len(nat_to_country)} nationalities -> country_id")

        # Backfill each regen's context. Group the UPDATE by nationality so we
        # set the correct country_id per cohort in a handful of statements.
        total = 0
        for nat, cid in nat_to_country.items():
            cur.execute(
                """
                UPDATE ingestion_players p
                SET country_id = %(cid)s,
                    current_competition_id = %(comp)s,
                    current_club_id = %(club)s,
                    real_world_league_name = %(lg)s,
                    real_world_club_name = %(club_name)s,
                    updated_at = now()
                FROM player_summary_read_models prm
                WHERE prm.player_id = p.id
                  AND p.source_provider = 'gtex_regen'
                  AND prm.summary_json->>'nationality' = %(nat)s
                """,
                {
                    "cid": cid, "comp": comp_id, "club": club_id,
                    "lg": COMPETITION_NAME, "club_name": CLUB_NAME, "nat": nat,
                },
            )
            total += cur.rowcount
        print(f"regens contextualized: {total}")

        # Safety: any regen still lacking country_id (no/blank nationality) gets
        # the native context + a fallback country so none are stranded.
        cur.execute(
            """
            UPDATE ingestion_players p
            SET current_competition_id = COALESCE(current_competition_id, %(comp)s),
                current_club_id = COALESCE(current_club_id, %(club)s),
                real_world_league_name = COALESCE(real_world_league_name, %(lg)s),
                real_world_club_name = COALESCE(real_world_club_name, %(club_name)s),
                updated_at = now()
            WHERE p.source_provider = 'gtex_regen'
              AND (p.current_competition_id IS NULL OR p.real_world_club_name IS NULL)
            """,
            {"comp": comp_id, "club": club_id, "lg": COMPETITION_NAME, "club_name": CLUB_NAME},
        )

        if args.dry_run:
            conn.rollback()
            print("DRY RUN — rolled back")
        else:
            conn.commit()
            print("committed")

        # Verification counts (post-commit / pre-rollback snapshot).
        cur.execute(
            "select count(*) from ingestion_players where source_provider='gtex_regen' and country_id is not null"
        )
        print("regens with country_id        :", cur.fetchone()[0])
        cur.execute(
            "select count(*) from ingestion_players where source_provider='gtex_regen' "
            "and current_competition_id is not null and current_club_id is not null"
        )
        print("regens with NTP context       :", cur.fetchone()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
