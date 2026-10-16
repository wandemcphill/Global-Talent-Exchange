#!/usr/bin/env python
"""Backfill first_team squad-tier memberships for every actively-contracted player.

Idempotent: only inserts a membership where the (club_id, player_id) pair has an
active contract and no existing active membership. Run AFTER migration 0104 has
created club_squad_tier_memberships.

Usage:
    python scripts/backfill_squad_tiers.py --database-url "postgresql://...?sslmode=require"
    python scripts/backfill_squad_tiers.py --database-url "..." --dry-run
"""

from __future__ import annotations

import argparse
import sys
import uuid

import psycopg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with psycopg.connect(args.database_url) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            select distinct c.club_id, c.player_id
            from player_contracts c
            where c.club_id is not null
              and c.status in ('active', 'expiring')
              and not exists (
                select 1 from club_squad_tier_memberships m
                where m.club_id = c.club_id
                  and m.player_id = c.player_id
                  and m.status = 'active'
              )
            """
        )
        rows = cur.fetchall()
        print(f"squad-tier backfill: {len(rows)} contracted players to add as first_team")
        if args.dry_run:
            print("DRY RUN -- no writes")
            return 0
        for club_id, player_id in rows:
            cur.execute(
                """
                insert into club_squad_tier_memberships
                  (id, club_id, player_id, tier, source, status,
                   joined_club_at, joined_tier_at, metadata_json, created_at, updated_at)
                values (%s, %s, %s, 'first_team', 'transfer', 'active',
                        now(), now(), '{}', now(), now())
                """,
                (str(uuid.uuid4()), club_id, player_id),
            )
        conn.commit()
        print(f"inserted {len(rows)} first_team memberships")
    return 0


if __name__ == "__main__":
    sys.exit(main())
