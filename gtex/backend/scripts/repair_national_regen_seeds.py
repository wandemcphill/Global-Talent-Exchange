"""Repair every preseeded national regen: country codes, country-true unique names,
face-bank portraits (Cloudinary), tradeable player records.

Usage: python scripts/repair_national_regen_seeds.py [--dry-run]
Then:  python scripts/bulk_issue_regen_markets.py --provider gtex_national_seed --database-url $DATABASE_URL
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import uuid
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg  # noqa: E402
import psycopg.rows  # noqa: E402

from app.players.football_integrity import normalize_position  # noqa: E402
from app.player_cards.service import PlayerCardMarketService  # noqa: E402
from app.services.regen_country_name_pools import COUNTRY_SPECIFIC_NAME_POOLS  # noqa: E402
from app.services.regen_culture_name_pools import (  # noqa: E402
    COMPOUND_SURNAME_CULTURES,
    COUNTRY_CODE_REPAIRS,
    COUNTRY_PROFILES,
    C,
    country_pool_entries,
)
from app.services.regen_portrait_service import (  # noqa: E402
    FACE_RECIPE_VERSION,
    NEWGEN_FACE_BANK_COLLECTION,
    NEWGEN_FACE_BANK_PROVIDER,
    RegenPortraitService,
)

PROVIDER = "gtex_national_seed"
NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
COUNTRY_NAME_ALIASES = {"EN": "England", "SC": "Scotland", "NI": "Northern Ireland", "IE": "Republic of Ireland", "CZ": "Czech Republic"}
GENERIC_POOLS = {code for code, entry in country_pool_entries().items() if COUNTRY_SPECIFIC_NAME_POOLS.get(code) is entry}


def player_id_for(seed_id: str) -> str:
    return str(uuid.uuid5(NS, f"{PROVIDER}:{seed_id}"))


def cultures_for(code: str) -> list[tuple[str, tuple[str, ...], tuple[str, ...]]]:
    out = []
    hand = COUNTRY_SPECIFIC_NAME_POOLS.get(code)
    if hand is not None and code not in GENERIC_POOLS and code != "NG":
        out.append((f"{code}_local", tuple(hand["given"]), tuple(hand["surnames"])))
    for key in COUNTRY_PROFILES[code][0]:
        out.append((key, *C[key]))
    return out


def unique_name(rng: random.Random, code: str, taken: set[str]) -> str:
    cultures = cultures_for(code)
    for attempt in range(400):
        key, given, surnames = cultures[0] if (len(cultures) == 1 or rng.random() < 0.6) else rng.choice(cultures[1:])
        first, last = rng.choice(given), rng.choice(surnames)
        if attempt >= 120:
            if key in COMPOUND_SURNAME_CULTURES or key.endswith("_local"):
                other = rng.choice(surnames)
                last = f"{last} {other}" if other != last else last
            else:
                middle = rng.choice(given)
                first = f"{first} {middle}" if middle != first else first
        name = f"{first} {last}"
        if name.lower() not in taken:
            taken.add(name.lower())
            return name
    raise RuntimeError(f"name space exhausted for {code}")


class FaceDealer:
    """Deals each face once per ethnicity group before any face repeats."""

    def __init__(self, assets: list[dict]):
        self.by_group: dict[str, list[dict]] = defaultdict(list)
        for asset in assets:
            if asset.get("cloudinary_secure_url"):
                self.by_group[str(asset["ethnicity"])].append(asset)
        self.decks: dict[str, list[dict]] = {}
        self.rng = random.Random("gtex-national-faces-v1")

    def deal(self, groups: tuple[str, ...], rng: random.Random) -> tuple[str, dict]:
        weights = [0.6] + [0.4 / (len(groups) - 1)] * (len(groups) - 1) if len(groups) > 1 else [1.0]
        group = rng.choices(groups, weights=weights)[0]
        if not self.decks.get(group):
            deck = list(self.by_group[group])
            self.rng.shuffle(deck)
            self.decks[group] = deck
        return group, self.decks[group].pop()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    url = os.environ["DATABASE_URL"]
    manifest = json.loads((ROOT / "generated_media/regen_newgen_faces/manifest.json").read_text(encoding="utf-8"))
    dealer = FaceDealer([a for a in manifest["assets"] if a.get("collection") == NEWGEN_FACE_BANK_COLLECTION])
    portraits = RegenPortraitService.__new__(RegenPortraitService)
    now = datetime.now(UTC)

    with psycopg.connect(url, prepare_threshold=None, connect_timeout=60) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("select * from national_regen_seeds order by id")
            seeds = cur.fetchall()
            cur.execute("select id, name, alpha2_code, alpha3_code, fifa_code from ingestion_countries")
            countries = cur.fetchall()
        print("seeds", len(seeds), flush=True)
        by_alpha2 = {c["alpha2_code"]: c["id"] for c in countries if c["alpha2_code"]}
        by_name = {c["name"].lower(): c["id"] for c in countries}

        taken: set[str] = set()
        seed_updates, players, images = [], [], []
        stats = Counter()
        for seed in seeds:
            code, cname = COUNTRY_CODE_REPAIRS.get(seed["country_code"], (seed["country_code"], seed["country_name"]))
            if code not in COUNTRY_PROFILES:
                raise SystemExit(f"no profile for {code} ({cname})")
            rng = random.Random(f"national-seed-name:{seed['id']}")
            name = unique_name(rng, code, taken)
            group, asset = dealer.deal(COUNTRY_PROFILES[code][1], rng)
            meta = dict(seed["metadata_json"] or {})
            face_seed = meta.get("faceSeed") or portraits._deterministic_seed("national-seed", seed["seed_key"], name, code)
            recipe = portraits._face_recipe_from_context(seed=face_seed, age=seed["age"], country_code=code, position=seed["primary_position"], rating=seed["current_rating"])
            pid = player_id_for(seed["id"])
            portrait_url = asset["cloudinary_secure_url"]
            flags = {k: True for k in ("admin_trade_enabled", "admin_mint_enabled", "trade_enabled_by_admin", "card_mint_eligible", "transfer_market_eligible", "share_market_eligible", "market_eligible", "buy_cta_allowed", "buyable", "tradable")}
            snapshot = meta.get("profile_snapshot")
            if isinstance(snapshot, dict) and isinstance(snapshot.get("profile"), dict):
                for key in ("display_name", "name", "full_name"):
                    if key in snapshot["profile"]:
                        snapshot["profile"][key] = name
            meta.update({
                **flags,
                "national_pool_only": False,
                "nationality": code, "seed_country_code": code, "naming_country_code": code, "portraitCountryCode": code, "country_name": cname,
                "faceSeed": face_seed, "faceRecipe": recipe, "portraitUrl": portrait_url, "portraitStatus": "ready_newgen_face_bank",
                "portraitRecipeVersion": FACE_RECIPE_VERSION, "portraitStorageKey": asset["storage_key"],
                "portraitSourceProvider": NEWGEN_FACE_BANK_PROVIDER, "portraitSourceCollection": NEWGEN_FACE_BANK_COLLECTION,
                "portraitEthnicity": group, "minted_player_id": pid, "enabled_for_trade_at": now.isoformat(),
                "previous_display_name": seed["display_name"] if seed["display_name"] != name else meta.get("previous_display_name"),
            })
            seed_updates.append((code, cname, name, json.dumps(meta), seed["id"]))
            stats["renamed"] += seed["display_name"] != name
            stats["recoded"] += seed["country_code"] != code

            pos = normalize_position(seed["primary_position"])
            first, _, last = name.partition(" ")
            age = int(seed["age"] or 18)
            value = PlayerCardMarketService._market_value_from_seed(type("S", (), seed)())
            country_id = by_alpha2.get(code) or by_name.get(cname.lower()) or by_name.get(COUNTRY_NAME_ALIASES.get(code, "").lower())
            stats["no_country"] += country_id is None
            dna = {
                **flags, "source_type": "national_seed", "source_bucket": "preseeded", "is_regen": True, "is_preseeded_national_regen": True,
                "national_pool_only": False, "national_seed_id": seed["id"], "national_seed_key": seed["seed_key"], "country_code": code,
                "country_name": cname, "current_rating": int(seed["current_rating"]), "potential_rating": int(seed["potential_rating"]),
                "growth_curve": float(seed["growth_curve"] or 0), "rarity_tier": seed["rarity_tier"], "portraitUrl": portrait_url,
                "image_url": portrait_url, "faceSeed": face_seed, "enabled_for_trade_at": now.isoformat(),
            }
            players.append((
                pid, PROVIDER, seed["id"], name, first, last or None, name, name,
                pos.value if pos is not None else seed["primary_position"], pos.name if pos is not None else None,
                date(max(now.year - age, 1900), 1, 1), country_id, value, value, "EUR", 0.95, True, False, 0.98, now, now,
                json.dumps(dna), f"{cname} National Regen Pool", "GTEX National Regen Pool",
            ))
            images.append((str(uuid.uuid5(NS, f"{PROVIDER}:portrait:{seed['id']}")), NEWGEN_FACE_BANK_PROVIDER, f"{seed['id']}:portrait", pid, "portrait", portrait_url, asset["storage_key"], asset.get("width"), asset.get("height"), "image/png", asset.get("bytes"), "approved", True, True, now))

        print("stats", dict(stats), "unique names", len(taken), flush=True)
        if args.dry_run:
            for row in seed_updates[:12]:
                print(row[0], row[1], "->", row[2])
            return 0
        with conn.cursor() as cur:
            cur.executemany("update national_regen_seeds set country_code=%s, country_name=%s, display_name=%s, metadata_json=%s::json, updated_at=now() where id=%s", seed_updates)
            print("seeds updated", flush=True)
            cur.executemany(
                """insert into ingestion_players (id, source_provider, provider_external_id, full_name, first_name, last_name, short_name,
                   canonical_display_name, position, normalized_position, date_of_birth, country_id, market_value_eur,
                   current_market_reference_value, market_reference_currency, profile_completeness_score, is_tradable, is_real_player,
                   identity_confidence_score, source_last_refreshed_at, last_synced_at, dna_profile, real_world_club_name, real_world_league_name)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::json,%s,%s)
                   on conflict (id) do update set full_name=excluded.full_name, first_name=excluded.first_name, last_name=excluded.last_name,
                   short_name=excluded.short_name, canonical_display_name=excluded.canonical_display_name, country_id=excluded.country_id,
                   dna_profile=excluded.dna_profile, real_world_club_name=excluded.real_world_club_name, updated_at=now()""",
                players,
            )
            print("players upserted", flush=True)
            cur.executemany(
                """insert into ingestion_player_image_metadata (id, source_provider, provider_external_id, player_id, image_role, source_url,
                   storage_key, width, height, mime_type, file_size_bytes, moderation_status, rights_cleared, is_primary, last_processed_at)
                   values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict (player_id, image_role) do update set source_url=excluded.source_url, storage_key=excluded.storage_key,
                   moderation_status=excluded.moderation_status, updated_at=now()""",
                images,
            )
            print("portraits upserted", flush=True)
        conn.commit()
        print("committed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
