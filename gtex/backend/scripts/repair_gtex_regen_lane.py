"""Repair the gtex_regen player lane: country-true unique names + face-bank portraits.

Names stay unique against the national-seed cohort too. Usage: python scripts/repair_gtex_regen_lane.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg  # noqa: E402

from repair_national_regen_seeds import NS, ROOT, FaceDealer, unique_name  # noqa: E402

from app.services.regen_country_name_pools import COUNTRY_NAME_PROFILE_ALIASES as COUNTRY_NAME_TO_CODE  # noqa: E402
from app.services.regen_culture_name_pools import COUNTRY_PROFILES  # noqa: E402
from app.services.regen_portrait_service import NEWGEN_FACE_BANK_COLLECTION, NEWGEN_FACE_BANK_PROVIDER  # noqa: E402

NAME_CODES = {"england": "EN", "scotland": "SC", "northern ireland": "NI", "wales": "EN", "republic of ireland": "IE", "ireland": "IE", "czech republic": "CZ", "turkey": "TR", "türkiye": "TR", "korea republic": "KR", "south korea": "KR", "usa": "US", "united states": "US", "ivory coast": "CI", "côte d'ivoire": "CI"}


def code_for(alpha2: str | None, name: str | None, seed_names: dict[str, str]) -> str | None:
    key = (name or "").strip().lower()
    for candidate in (NAME_CODES.get(key), seed_names.get(key), (alpha2 or "").upper() or None, COUNTRY_NAME_TO_CODE.get(key)):
        if candidate and candidate in COUNTRY_PROFILES:
            return candidate
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    manifest = json.loads((ROOT / "generated_media/regen_newgen_faces/manifest.json").read_text(encoding="utf-8"))
    dealer = FaceDealer([a for a in manifest["assets"] if a.get("collection") == NEWGEN_FACE_BANK_COLLECTION])
    dealer.rng = random.Random("gtex-regen-lane-faces-v1")
    now = datetime.now(UTC)
    with psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None, connect_timeout=60) as conn:
        with conn.cursor() as cur:
            cur.execute("select lower(display_name) from national_regen_seeds")
            taken = {r[0] for r in cur.fetchall()}
            cur.execute("select distinct lower(full_name) from ingestion_players where source_provider not in ('gtex_regen', 'gtex_national_seed') and full_name is not null")
            taken |= {r[0] for r in cur.fetchall()}
            cur.execute("select distinct lower(country_name), country_code from national_regen_seeds")
            seed_names = dict(cur.fetchall())
            cur.execute(
                """select p.id, p.full_name, p.dna_profile, c.alpha2_code, c.name from ingestion_players p
                   left join ingestion_countries c on c.id = p.country_id where p.source_provider = 'gtex_regen' order by p.id"""
            )
            rows = cur.fetchall()
        stats, players, images = Counter(), [], []
        for pid, old_name, dna, alpha2, cname in rows:
            dna = dict(dna or {})
            code = code_for(alpha2, cname or dna.get("nationality"), seed_names)
            if code is None:
                stats["unmapped"] += 1
                stats[f"unmapped:{cname or dna.get('nationality')}"] += 1
                continue
            rng = random.Random(f"gtex-regen-name:{pid}")
            name = unique_name(rng, code, taken)
            group, asset = dealer.deal(COUNTRY_PROFILES[code][1], rng)
            url = asset["cloudinary_secure_url"]
            dna.update({"previous_full_name": dna.get("previous_full_name") or old_name, "naming_country_code": code, "portraitUrl": url, "image_url": url, "portraitStorageKey": asset["storage_key"], "portraitEthnicity": group, "portraitSourceProvider": NEWGEN_FACE_BANK_PROVIDER})
            first, _, last = name.partition(" ")
            players.append((name, first, last or None, name, name, json.dumps(dna), pid))
            images.append((str(uuid.uuid5(NS, f"gtex_regen:portrait:{pid}")), NEWGEN_FACE_BANK_PROVIDER, f"{pid}:portrait", pid, "portrait", url, asset["storage_key"], asset.get("width"), asset.get("height"), "image/png", asset.get("bytes"), "approved", True, True, now))
            stats["repaired"] += 1
        print("stats", {k: v for k, v in stats.items() if not k.startswith("unmapped:")}, [k for k in stats if k.startswith("unmapped:")][:20], flush=True)
        if args.dry_run:
            for row in players[:8]:
                print(json.loads(row[5])["previous_full_name"], "->", row[0], json.loads(row[5])["naming_country_code"])
            return 0
        with conn.cursor() as cur:
            cur.executemany("update ingestion_players set full_name=%s, first_name=%s, last_name=%s, short_name=%s, canonical_display_name=%s, dna_profile=%s::json, updated_at=now() where id=%s", players)
            cur.executemany(
                """insert into ingestion_player_image_metadata (id, source_provider, provider_external_id, player_id, image_role, source_url,
                   storage_key, width, height, mime_type, file_size_bytes, moderation_status, rights_cleared, is_primary, last_processed_at)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict (player_id, image_role) do update set source_url=excluded.source_url, storage_key=excluded.storage_key, updated_at=now()""",
                images,
            )
        conn.commit()
        print("committed", len(players), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
