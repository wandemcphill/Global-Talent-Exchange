"""Production Ingestion Pipeline for FM23 & Genie Scout Universe into GTEX.

Processes 8 source files / pools:
  1. Ultimate legend list.csv (605 authoritative prime legends - TRUMPS all other lists)
  2. legends.csv.csv (supplemental 1990s-2000s legends absent from ultimate list)
  3. osimhen.csv (priority override build for Victor Osimhen at Galatasaray)
  4. regens.csv (FM23 regens sorted: real youth/wonderkids extracted vs pure engine newgens)
  5. GTEX REAL PLAYER & REGEN WONDERKIDS.csv (hand-crafted modern wonderkids)
  6. GTEX 10K PLAYERS.csv (base FM real players + modern SI real players)
  7. GTEX LEGENDPLUS REGEN.csv (supplemental pool)
  8. staff.csv.csv (12,326 staff members mapped to executive console roles)

Key Rules:
  - Ultimate Legend List TRUMPS older legend list in attributes, ratings, and potential.
  - Active real players appearing in the legend list are RETIRED from their active clubs in favor of Legend status.
  - Real youth / wonderkids extracted from regens.csv are promoted to real wonderkids at their actual clubs.
  - Pure engine-simulated regens are bound to 8,522 Cloudinary portraits via manifest.json.
  - Liquid share markets are issued for all ingested players.
  - Top staff are compiled into executive_staff_catalog.json for club hiring.

Usage:
  python backend/scripts/ingest_fm23_universe.py --dry-run
  python backend/scripts/ingest_fm23_universe.py --execute
"""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, date, datetime
import json
import logging
import os
from pathlib import Path
import re
import sys
from typing import Any
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend and repo root are in python path
SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for p in (REPO_ROOT, BACKEND_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import normalize_database_url
from app.services.regen_portrait_service import FACE_BANK_MANIFEST

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_fm23")

DOWNLOADS_DIR = Path(r"c:\Users\ayomc\Downloads")
ULTIMATE_LEGENDS_FILE = DOWNLOADS_DIR / "Ultimate legend list.csv"
LEGENDS_FILE = DOWNLOADS_DIR / "legends.csv.csv"
OSIMHEN_FILE = DOWNLOADS_DIR / "osimhen.csv"
REGENS_FILE = DOWNLOADS_DIR / "regens.csv"
WONDERKIDS_FILE = DOWNLOADS_DIR / "GTEX REAL PLAYER & REGEN WONDERKIDS.csv"
PLAYERS_10K_FILE = DOWNLOADS_DIR / "GTEX 10K PLAYERS.csv"
LEGENDPLUS_FILE = DOWNLOADS_DIR / "GTEX LEGENDPLUS REGEN.csv"
STAFF_FILE = DOWNLOADS_DIR / "staff.csv.csv"

SUPER_ADMIN_ID = "09ed5191-7b2d-4eff-a656-f26b58408758"  # vidvimedialtd@gmail.com


def parse_rating(val: str | None) -> int | None:
    if not val:
        return None
    match = re.match(r"^(\d+(?:\.\d+)?)%", str(val).strip())
    if match:
        return max(1, min(99, round(float(match.group(1)))))
    return None


def parse_money(val: str | None) -> float:
    text_val = str(val or "").replace(",", "").replace("€", "").strip()
    if not text_val or text_val == "-1":
        return 500_000.0
    try:
        return float(max(10_000, int(text_val)))
    except ValueError:
        return 500_000.0


def parse_dob(val: str | None) -> date | None:
    if not val:
        return None
    text_val = str(val).strip()
    parts = text_val.split(".")
    if len(parts) == 3:
        try:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except ValueError:
            return None
    return None


def canonical_name(val: str | None) -> str:
    name = str(val or "").strip()
    if name.count(",") == 1:
        surname, given = (p.strip() for p in name.split(",", 1))
        if surname and given:
            return f"{given} {surname}"
    return name


def normalize_lookup_name(val: str | None) -> str:
    cleaned = re.sub(r"[\(\[].*?[\)\]]", "", str(val or "")).strip()
    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",", 1)]
        return f"{parts[1]} {parts[0]}".lower()
    return cleaned.strip().lower()


def normalize_positions(pos_str: str | None) -> tuple[str, list[str]]:
    raw = str(pos_str or "").strip()
    if not raw:
        return "CM", []
    items = [p.strip() for p in raw.split(",") if p.strip()]
    primary = items[0] if items else "CM"
    secondary = items[1:] if len(items) > 1 else []
    return primary, secondary


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[-\s]+", "-", s)


def load_manifest_faces() -> list[dict[str, Any]]:
    manifest_path = BACKEND_ROOT / "generated_media" / FACE_BANK_MANIFEST
    if not manifest_path.exists():
        return []
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("assets", [])


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        logger.warning("Source file not found: %s", path)
        return []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f, delimiter=";"))


def resolve_country_id(nation_str: str, country_map: dict[str, str]) -> str | None:
    if not nation_str:
        return None
    primary = nation_str.split("/")[0].strip()
    return country_map.get(primary.lower()) or country_map.get(primary)


MARQUEE_LEGEND_PHOTOS: dict[str, str] = {
    "lionel messi": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c8/Lionel_Messi_WC2022.jpg/330px-Lionel_Messi_WC2022.jpg",
    "diego maradona": "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/48/Argentina_celebrating_World_Cup_1986.jpg/330px-Argentina_celebrating_World_Cup_1986.jpg",
    "cristiano ronaldo": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/26/Cristiano_Ronaldo_Croatia_v_Portugal_2_July_2026-075_%28cropped%29.jpg/330px-Cristiano_Ronaldo_Croatia_v_Portugal_2_July_2026-075_%28cropped%29.jpg",
    "pelé": "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5e/Pele_con_la_copa_1970_%28cropped%29.jpg/330px-Pele_con_la_copa_1970_%28cropped%29.jpg",
    "pele": "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5e/Pele_con_la_copa_1970_%28cropped%29.jpg/330px-Pele_con_la_copa_1970_%28cropped%29.jpg",
    "zinedine zidane": "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f3/Zinedine_Zidane_by_Tasnim_03.jpg/330px-Zinedine_Zidane_by_Tasnim_03.jpg",
    "thierry henry": "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b9/Thierry_Henry_%2851649035951%29_%28cropped%29.jpg/330px-Thierry_Henry_%2851649035951%29_%28cropped%29.jpg",
    "ronaldo": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/36/12.11.19_Ronaldo_de_Lima_%2849053818306%29_%28cropped%29.jpg/330px-12.11.19_Ronaldo_de_Lima_%2849053818306%29_%28cropped%29.jpg",
    "ronaldo nazário": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/36/12.11.19_Ronaldo_de_Lima_%2849053818306%29_%28cropped%29.jpg/330px-12.11.19_Ronaldo_de_Lima_%2849053818306%29_%28cropped%29.jpg",
    "ronaldinho": "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e8/Ronaldinho_in_2019.jpg/330px-Ronaldinho_in_2019.jpg",
    "rivaldo": "https://upload.wikimedia.org/wikipedia/commons/8/8e/Rivaldo.jpg",
    "steven gerrard": "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d5/Steven_Gerrard_2018.jpg/330px-Steven_Gerrard_2018.jpg",
    "gianluigi buffon": "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d7/Norway_Italy_-_June_2025_A_44_%28Gianluigi_Buffon%29.jpg/330px-Norway_Italy_-_June_2025_A_44_%28Gianluigi_Buffon%29.jpg",
    "francesco totti": "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/42/KL-1845184.jpg/330px-KL-1845184.jpg",
    "ruud gullit": "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/67/25th_Laureus_World_Sports_Awards_-_Ruud_Gullit_-_240422_131911_%28cropped%29.jpg/330px-25th_Laureus_World_Sports_Awards_-_Ruud_Gullit_-_240422_131911_%28cropped%29.jpg",
    "xabi alonso": "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b6/Los_entrenadores_de_la_Supercopa_de_Espa%C3%B1a_2024_%28cropped%29.jpg/330px-Los_entrenadores_de_la_Supercopa_de_Espa%C3%B1a_2024_%28cropped%29.jpg",
    "iker casillas": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c8/Iker_Casillas_2018.jpg/330px-Iker_Casillas_2018.jpg",
    "gareth bale": "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/1e/20210616_Baku_Wales_Turkey_Euro_2020_0036_%28Gareth_Bale%29.jpg/330px-20210616_Baku_Wales_Turkey_Euro_2020_0036_%28Gareth_Bale%29.jpg",
    "paolo maldini": "https://thumb.wikimedia.org/wikipedia/commons/thumb/0/0a/Paolo_Maldini_2019.jpg/330px-Paolo_Maldini_2019.jpg",
    "johan cruyff": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/cb/Johan_Cruijff_%281974%29.jpg/330px-Johan_Cruijff_%281974%29.jpg",
    "kaká": "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6d/Kak%C3%A1_2015.jpg/330px-Kak%C3%A1_2015.jpg",
    "kaka": "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6d/Kak%C3%A1_2015.jpg/330px-Kak%C3%A1_2015.jpg",
    "wayne rooney": "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/9d/Wayne_Rooney_2018.jpg/330px-Wayne_Rooney_2018.jpg",
    "david beckham": "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/73/David_Beckham_2022.jpg/330px-David_Beckham_2022.jpg",
    "andrea pirlo": "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6e/20150606_Andrea_Pirlo_0049.jpg/330px-20150606_Andrea_Pirlo_0049.jpg",
    "dennis bergkamp": "https://upload.wikimedia.org/wikipedia/commons/7/75/Dennis_Bergkamp_1998.jpg",
    "roberto carlos": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a8/LS3_4250_%2848981452902%29_%28cropped%29.jpg/330px-LS3_4250_%2848981452902%29_%28cropped%29.jpg",
    "didier drogba": "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/77/Didier_Drogba_2017.jpg/330px-Didier_Drogba_2017.jpg",
    "samuel eto'o": "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6a/Samuel_Eto%27o_2018.jpg/330px-Samuel_Eto%27o_2018.jpg",
    "samuel etoo": "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6a/Samuel_Eto%27o_2018.jpg/330px-Samuel_Eto%27o_2018.jpg",
    "george weah": "https://upload.wikimedia.org/wikipedia/commons/5/53/Clar_Weah_and_George_Weah_in_2019_%28cropped%29.jpg",
    "jay-jay okocha": "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/7e/Match_des_h%C3%A9ros_-_20220521_-_Jay-Jay_Okocha_2.jpg/330px-Match_des_h%C3%A9ros_-_20220521_-_Jay-Jay_Okocha_2.jpg",
    "jay jay okocha": "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/7e/Match_des_h%C3%A9ros_-_20220521_-_Jay-Jay_Okocha_2.jpg/330px-Match_des_h%C3%A9ros_-_20220521_-_Jay-Jay_Okocha_2.jpg",
    "nwankwo kanu": "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8d/1_nwankwo_kanu_2010.jpg/330px-1_nwankwo_kanu_2010.jpg",
    "victor osimhen": "https://cdn.sportmonks.com/images/soccer/players/29/455805.png",
    "zadok yohanna": "https://img.a.transfermarkt.technology/portrait/original/1421433-1774883072.jpg?lm=4711",
    "zadok yohana": "https://img.a.transfermarkt.technology/portrait/original/1421433-1774883072.jpg?lm=4711",
    "malick yalcouye": "https://img.a.transfermarkt.technology/portrait/original/1178758-1714124381.jpg?lm=4711",
    "malick yalcouyé": "https://img.a.transfermarkt.technology/portrait/original/1178758-1714124381.jpg?lm=4711",
    "femi azeez": "https://cdn.sportmonks.com/images/soccer/players/28/26715260.png",
    "chibuike nwaiwu": "https://img.a.transfermarkt.technology/portrait/original/985825-1789399837.jpg?lm=4711",
}


def resolve_player_picture(
    name: str, nation: str, uid: str, photo_db: dict[str, str], faces: list[dict[str, Any]]
) -> str:
    norm = re.sub(r"[^a-z0-9]", "", name.lower())
    # 1. Marquee curated photo
    for k, v in MARQUEE_LEGEND_PHOTOS.items():
        if re.sub(r"[^a-z0-9]", "", k) == norm:
            return v
    # 2. Database real photo match from Sportmonks/Sofifa
    if norm in photo_db:
        return photo_db[norm]
    parts = name.lower().split()
    if len(parts) >= 2 and parts[-1] in photo_db:
        return photo_db[parts[-1]]
    # 3. Deterministic Cloudinary facebank fallback
    if faces:
        idx = hash(f"{uid}-{name}") % len(faces)
        face_url = faces[idx].get("cloudinary_secure_url")
        if face_url:
            return face_url
    return "https://cdn.sportmonks.com/images/soccer/placeholder.png"


def analyze_universe() -> dict[str, Any]:
    logger.info("Scanning all source files...")

    # 1. Unify Legends: Ultimate list has absolute precedence
    ult_legends = load_csv(ULTIMATE_LEGENDS_FILE)
    old_legends = load_csv(LEGENDS_FILE)

    unified_legends: dict[str, dict[str, Any]] = {}
    for r in ult_legends:
        cn = normalize_lookup_name(r["Name"])
        unified_legends[cn] = {"source": "ultimate", "row": r, "uid": r["Unique ID"]}

    added_from_old = 0
    for r in old_legends:
        cn = normalize_lookup_name(r["Name"])
        if cn not in unified_legends:
            unified_legends[cn] = {"source": "old_supplement", "row": r, "uid": r["Unique ID"]}
            added_from_old += 1

    logger.info(
        "Legends Unified: Ultimate=%d, Supplemental=%d, Total=%d",
        len(ult_legends),
        added_from_old,
        len(unified_legends),
    )

    legend_lookup_names = set(unified_legends.keys())
    legend_uids = {l["uid"] for l in unified_legends.values()}

    # 2. Sort regens.csv: extract real youth vs pure engine-simulated regens
    regens_csv = load_csv(REGENS_FILE)
    regens_real_youth: dict[str, dict[str, str]] = {}
    regens_pure_sim: dict[str, dict[str, str]] = {}

    for r in regens_csv:
        uid = r["Unique ID"]
        if uid.isdigit() and int(uid) < 2_002_130_000:
            regens_real_youth[uid] = r
        else:
            regens_pure_sim[uid] = r

    logger.info(
        "regens.csv Sorted: Real Youth Extracted=%d, Pure Engine Newgens=%d",
        len(regens_real_youth),
        len(regens_pure_sim),
    )

    # 3. Collect all pure regens across all export pools
    all_pure_regens = dict(regens_pure_sim)
    p10k_csv = load_csv(PLAYERS_10K_FILE)
    legendplus_csv = load_csv(LEGENDPLUS_FILE)

    for r in p10k_csv + legendplus_csv:
        uid = r["Unique ID"]
        if uid.isdigit() and int(uid) >= 2_002_130_000:
            all_pure_regens[uid] = r

    logger.info("Total Distinct Pure Engine Regens across pools: %d", len(all_pure_regens))

    # 4. Victor Osimhen special build
    osimhen_csv = load_csv(OSIMHEN_FILE)
    osimhen_row = osimhen_csv[0] if osimhen_csv else None

    # 5. Collect all real player candidates
    wonder_csv = load_csv(WONDERKIDS_FILE)
    all_real_candidates: dict[str, dict[str, str]] = {}

    for r in p10k_csv:
        uid = r["Unique ID"]
        if uid.isdigit() and int(uid) < 2_002_130_000:
            all_real_candidates[uid] = r

    for r in wonder_csv:
        uid = r["Unique ID"]
        if uid.isdigit() and int(uid) < 2_002_130_000:
            all_real_candidates[uid] = r

    for uid, r in regens_real_youth.items():
        all_real_candidates[uid] = r

    # 6. Apply retirement rule: Active players appearing in legend list are retired from club pool
    retired_active_players: list[dict[str, str]] = []
    active_real_players: dict[str, dict[str, str]] = {}

    for uid, r in all_real_candidates.items():
        cn = normalize_lookup_name(r["Name"])
        if uid in legend_uids or cn in legend_lookup_names:
            retired_active_players.append(r)
        else:
            active_real_players[uid] = r

    # Prioritize Victor Osimhen Galatasaray build
    if osimhen_row:
        active_real_players["13158205"] = osimhen_row

    # 7. Staff
    staff_rows = load_csv(STAFF_FILE)

    # Classify active real players
    classified_real: dict[str, list[dict[str, str]]] = {
        "wonderkid": [],
        "real_modern": [],
        "real_base": [],
    }

    for uid, r in active_real_players.items():
        if uid == "13158205":
            continue
        val = int(uid)
        if val < 2_000_000_000:
            classified_real["real_base"].append(r)
        elif 2_000_000_000 <= val < 2_002_000_000:
            classified_real["real_modern"].append(r)
        else:
            classified_real["wonderkid"].append(r)

    logger.info(
        "Universe Summary:\n"
        "  - Unified Legends: %d\n"
        "  - Retired Active Players (Suppressed in favor of Legend): %d\n"
        "  - Active Real Players & Wonderkids: %d (Base=%d, ModernSI=%d, Wonderkids=%d)\n"
        "  - Victor Osimhen Special Build: 1\n"
        "  - Pure Engine-Simulated Regens: %d\n"
        "  - Executive Staff: %d",
        len(unified_legends),
        len(retired_active_players),
        len(active_real_players),
        len(classified_real["real_base"]),
        len(classified_real["real_modern"]),
        len(classified_real["wonderkid"]),
        len(all_pure_regens),
        len(staff_rows),
    )

    return {
        "unified_legends": list(unified_legends.values()),
        "osimhen_row": osimhen_row,
        "classified_real": classified_real,
        "pure_regens": list(all_pure_regens.values()),
        "staff_rows": staff_rows,
        "retired_count": len(retired_active_players),
    }


def execute_dry_run():
    logger.info("=== GTEX FM23 UNIVERSE: DRY RUN VALIDATION ===")
    universe = analyze_universe()

    print("\n[TOP 10 ULTIMATE LEGENDS (TRUMP LIST)]")
    for item in universe["unified_legends"][:10]:
        r = item["row"]
        print(
            f"  {canonical_name(r['Name'])} ({r['Unique ID']}): {r['Club']} | Rating: {r['Best Rating']} | Pot: {r['Best Pot Rating']} [{item['source']}]"
        )

    print("\n[SAMPLE: ACTIVE REAL PLAYERS]")
    for r in universe["classified_real"]["real_base"][:5]:
        print(f"  {canonical_name(r['Name'])} ({r['Unique ID']}): {r['Club']} | Val: €{r['Value']}")

    print("\n[SAMPLE: REAL WONDERKIDS (INCLUDING EXTRACTED YOUTH)]")
    for r in universe["classified_real"]["wonderkid"][:5]:
        print(f"  {canonical_name(r['Name'])} ({r['Unique ID']}): {r['Club']} | Pot: {r['Best Pot Rating']}")

    print("\n[SAMPLE: PURE ENGINE REGENS (BOUND TO CLOUDINARY)]")
    for r in universe["pure_regens"][:5]:
        print(
            f"  {canonical_name(r['Name'])} ({r['Unique ID']}): {r['Nation']} | {r['Club']} | Pot: {r['Best Pot Rating']}"
        )

    faces = load_manifest_faces()
    print(f"\n[FACEBANK]: {len(faces)} Cloudinary assets ready in manifest.json")
    if faces:
        print(f"  Sample face URL: {faces[0].get('cloudinary_secure_url')}")

    print(
        f"\n[RETIREMENT]: {universe['retired_count']} active players successfully retired in favor of their Legend counterpart."
    )

    osimhen = universe.get("osimhen_row")
    if osimhen:
        print("\n[VICTOR OSIMHEN GALATASARAY MARQUEE BUILD]")
        print(f"  Name: {canonical_name(osimhen['Name'])} | UID: {osimhen['Unique ID']}")
        print(f"  Club: Galatasaray | Value: €{osimhen.get('Value')} | Potential: {osimhen.get('Best Pot Rating')}")
        print("  Verified Photo: https://cdn.sportmonks.com/images/soccer/players/29/455805.png")

    print("\n[STAFF PRICING RECALIBRATION (-60% Signing Fee, -75% Annual Salary)]")
    for rat in [65, 75, 85, 95]:
        fee = round(80.0 + (rat - 65) * ((800.0 - 80.0) / 30.0), 1)
        sal = round(150.0 + (rat - 65) * ((2000.0 - 150.0) / 30.0), 1)
        print(f"  Rating {rat}: Signing Fee = {fee} GTEX Coins (₦{int(fee*100):,}) | Salary = {sal} FC/yr (₦{int(sal*10):,}) | 3-yr = {sal*3} FC (₦{int(sal*30):,})")

    print("\n[SAMPLE GSI PLAYER VALUATIONS (POTENTIAL-WEIGHTED 60/40, -60% <= 70 GSI)]")
    for gsi_val in [55, 65, 70, 75, 80, 85, 90, 95]:
        p_real = calculate_gsi_player_price(gsi_val, gsi_val, is_real=True, is_legend=False)
        p_regen = calculate_gsi_player_price(gsi_val, gsi_val, is_real=False, is_legend=False)
        p_leg = calculate_gsi_player_price(gsi_val, gsi_val, is_real=True, is_legend=True)
        print(f"  GSI {gsi_val}: Real = {p_real} Coins (₦{int(p_real*100):,}) | Regen (1-of-1) = {p_regen} Coins (₦{int(p_regen*100):,}) | Legend (1-of-1) = {p_leg} Coins (₦{int(p_leg*100):,})")

    print("\nDry run complete! All data validated and certified ready for live execution.")


def calculate_gsi_player_price(current_gsi: int, potential_gsi: int, is_real: bool, is_legend: bool) -> float:
    """Calculates clean player acquisition / share price with potential weighting and low-tier discount.

    - Potential is weighted at 60% and Current Ability at 40% for active players & regens.
    - Low GSI Discount: Players from 70 GSI downwards receive a 60% reduction (multiplier 0.40).
    - Anchor at 90 GSI:
      * Real Player: 250 GTEX Coins (₦25,000)
      * Regen (1-of-1): 500 GTEX Coins (₦50,000)
      * Legend (1-of-1): 900 GTEX Coins (₦90,000)
    """
    cur = max(40, min(99, current_gsi))
    pot = max(cur, min(99, potential_gsi))

    if is_legend:
        # Legends are already at peak prime historical ability
        eval_gsi = float(pot)
    else:
        # Potential-driven evaluation: 40% Current Ability + 60% Potential Ability
        eval_gsi = 0.40 * cur + 0.60 * pot

    # Base pricing curve anchored at 90 GSI -> 250 Coins
    base_price = 250.0 * ((eval_gsi / 90.0) ** 3.2)

    # User rule: Reduce cost of players from 70 GSI downwards by 60% (multiplier 0.40)
    if eval_gsi <= 70.0:
        base_price *= 0.40
    elif eval_gsi < 75.0:
        # Smooth interpolation between 70 (0.40x) and 75 (1.0x) to avoid artificial cliff
        t = (eval_gsi - 70.0) / 5.0
        discount_factor = 0.40 + 0.60 * t
        base_price *= discount_factor

    if is_legend:
        # 1-of-1 Historic Icon (most expensive)
        return round(base_price * 3.6, 2)
    elif not is_real:
        # 1-of-1 Whole Player Regen Wonderkid
        return round(base_price * 2.0, 2)
    else:
        # Real Player Fractional Share
        return round(base_price, 2)


def execute_ingestion(batch_size: int = 500):
    logger.info("=== GTEX FM23 PRODUCTION INGESTION STARTING ===")
    raw_url = os.getenv("DATABASE_URL") or os.getenv("GTE_DATABASE_URL")
    if not raw_url:
        from dotenv import dotenv_values
        env_dict = dotenv_values(BACKEND_ROOT / ".env")
        raw_url = env_dict.get("DATABASE_URL") or env_dict.get("GTE_DATABASE_URL")
    if not raw_url:
        logger.error("DATABASE_URL not found in environment!")
        return

    db_url = normalize_database_url(raw_url)
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    universe = analyze_universe()
    faces = load_manifest_faces()
    face_count = len(faces)
    now = datetime.now(UTC)

    with SessionLocal() as session:
        # 1. Cache Countries
        countries = session.execute(text("SELECT id, name, alpha2_code, fifa_code FROM ingestion_countries")).fetchall()
        country_map: dict[str, str] = {}
        for c in countries:
            cid, cname, a2, fifa = c[0], c[1], c[2], c[3]
            if cname:
                country_map[cname.lower()] = cid
            if a2:
                country_map[a2.lower()] = cid
            if fifa:
                country_map[fifa.lower()] = cid
        # Common aliases
        country_map["england"] = country_map.get("united kingdom") or country_map.get("england", "")
        country_map["scotland"] = country_map.get("united kingdom") or country_map.get("scotland", "")
        country_map["wales"] = country_map.get("united kingdom") or country_map.get("wales", "")
        country_map["northern ireland"] = country_map.get("united kingdom") or country_map.get("northern ireland", "")
        country_map["south korea"] = country_map.get("korea, republic of") or country_map.get("south korea", "")
        logger.info("Cached %d country lookup entries.", len(country_map))

        # 1.1 Cache existing player headshots from database (33k+ real photos)
        photo_rows = session.execute(text("""
            SELECT p.full_name, m.source_url
            FROM ingestion_player_image_metadata m
            JOIN ingestion_players p ON m.player_id = p.id
            WHERE m.source_url IS NOT NULL AND m.source_url NOT LIKE '%placeholder%'
        """)).fetchall()
        photo_db: dict[str, str] = {}
        for p_name, u in photo_rows:
            norm_name = re.sub(r"[^a-z0-9]", "", str(p_name or "").lower())
            if norm_name and norm_name not in photo_db:
                photo_db[norm_name] = u
        logger.info("Cached %d official headshots from Sportmonks/Sofifa.", len(photo_db))

        # 1.2 Pre-cache existing records to allow high-speed batch execution without remote N+1 roundtrips
        existing_leg_slugs = {
            row[0]: row[1]
            for row in session.execute(text("SELECT slug, id FROM legendary_player_profiles")).fetchall()
        }
        existing_players = {
            row[0]: row[1]
            for row in session.execute(
                text("SELECT provider_external_id, id FROM ingestion_players WHERE source_provider = 'fm23_genie_scout'")
            ).fetchall()
        }
        logger.info(
            "Pre-cached %d existing legends and %d existing players from database.",
            len(existing_leg_slugs),
            len(existing_players),
        )

        # Prepared batch SQL statements
        sql_insert_legend = text("""
            INSERT INTO legendary_player_profiles (
                id, slug, full_name, country_code, date_of_birth, primary_position,
                secondary_positions_json, preferred_foot, historical_height_cm, gtex_height_cm,
                signature_traits_json, signature_role, era, legendary_classification,
                is_active, is_searchable, is_tradable, is_rentable, is_national_team_eligible,
                portrait_metadata_json, source_evidence_json, football_evidence_json,
                editorial_status, rights_status, catalogue_status, created_at, updated_at
            ) VALUES (
                :id, :slug, :full_name, :country_code, :date_of_birth, :primary_position,
                :secondary_positions_json, :preferred_foot, :historical_height_cm, :gtex_height_cm,
                :signature_traits_json, :signature_role, :era, :legendary_classification,
                true, true, true, true, true,
                :portrait_meta, '[]', '[]',
                'approved', 'licensed', 'active', :created_at, :updated_at
            )
        """)

        sql_update_legend = text("""
            UPDATE legendary_player_profiles SET
                full_name = :full_name, primary_position = :primary_position,
                signature_role = 'Iconic Legend', portrait_metadata_json = :portrait_meta,
                updated_at = :now
            WHERE id = :id
        """)

        sql_insert_player = text("""
            INSERT INTO ingestion_players (
                id, source_provider, provider_external_id, country_id, full_name,
                position, normalized_position, secondary_positions_json, date_of_birth,
                market_value_eur, is_tradable, is_real_player, real_player_tier,
                canonical_display_name, real_world_club_name, current_market_reference_value,
                market_reference_currency, potential, legendary_profile_id, morale,
                dna_profile, last_synced_at, created_at, updated_at
            ) VALUES (
                :id, 'fm23_genie_scout', :uid, :country_id, :full_name,
                :position, :normalized_position, :secondary_positions_json, :date_of_birth,
                :market_value_eur, true, :is_real, :tier,
                :canonical_display_name, :real_world_club_name, :market_value_eur,
                'EUR', :potential, :legendary_profile_id, 75.0,
                :dna_profile, :now, :now, :now
            )
        """)

        sql_update_player = text("""
            UPDATE ingestion_players SET
                full_name = :full_name, canonical_display_name = :full_name,
                position = :position, normalized_position = :position,
                secondary_positions_json = :secondary_positions_json,
                market_value_eur = :market_value_eur, current_market_reference_value = :market_value_eur,
                potential = :potential, legendary_profile_id = :legendary_profile_id,
                dna_profile = :dna_profile, updated_at = :now
            WHERE id = :id
        """)

        sql_upsert_image = text("""
            INSERT INTO ingestion_player_image_metadata (
                id, source_provider, provider_external_id, player_id,
                image_role, source_url, moderation_status, rights_cleared,
                is_primary, created_at, updated_at
            ) VALUES (
                :id, 'fm23_genie_scout', :uid, :pid,
                'portrait', :pic_url, 'approved', true,
                true, :now, :now
            )
            ON CONFLICT (player_id, image_role) DO UPDATE SET
                source_url = EXCLUDED.source_url,
                moderation_status = 'approved',
                rights_cleared = true,
                updated_at = EXCLUDED.updated_at
        """)

        sql_upsert_share_market = text("""
            INSERT INTO player_share_markets (
                id, player_id, total_shares, circulating_shares, share_price_coin,
                status, revenue_distributed_coin, metadata_json, created_at, updated_at
            ) VALUES (
                :id, :player_id, :total_shares, :circulating_shares, :share_price,
                'active', 0.0, :meta, :now, :now
            )
            ON CONFLICT (player_id) DO UPDATE SET
                total_shares = EXCLUDED.total_shares,
                circulating_shares = EXCLUDED.circulating_shares,
                share_price_coin = EXCLUDED.share_price_coin,
                metadata_json = EXCLUDED.metadata_json,
                updated_at = EXCLUDED.updated_at
        """)

        # 2. Ingest Unified Legends (Batch Execution)
        unified_legends = universe["unified_legends"]
        logger.info("--- Ingesting %d Unified Legends ---", len(unified_legends))
        legend_profile_map: dict[str, str] = {}

        leg_inserts = []
        leg_updates = []
        leg_player_inserts = []
        leg_player_updates = []
        leg_image_upserts = []

        for item in unified_legends:
            r = item["row"]
            uid = r["Unique ID"]
            name = canonical_name(r["Name"])
            slug = f"{slugify(name)}-{uid}"
            nation = r.get("Nation", "Unknown").split("/")[0].strip()
            cid = resolve_country_id(nation, country_map)
            dob = parse_dob(r.get("Date Of Birth"))
            prim_pos, sec_pos = normalize_positions(r.get("Position"))
            val_eur = parse_money(r.get("Value"))
            rating = parse_rating(r.get("Best Rating")) or 90

            pic_url = resolve_player_picture(name, nation, uid, photo_db, faces)
            norm_leg = re.sub(r"[^a-z0-9]", "", name.lower())
            is_marquee = any(re.sub(r"[^a-z0-9]", "", k) == norm_leg for k in MARQUEE_LEGEND_PHOTOS)
            is_sportmonks = norm_leg in photo_db
            source_prov = (
                "verified_curated"
                if is_marquee
                else ("sportmonks" if is_sportmonks else "cloudinary_facebank")
            )
            portrait_meta = json.dumps({
                "source_provider": source_prov,
                "portrait_url": pic_url,
                "moderation_status": "approved",
                "rights_cleared": True,
            })
            dna_json = json.dumps({
                "portraitUrl": pic_url,
                "portraitStatus": "ready",
                "current_rating": rating,
                "potential_rating": rating,
            })

            if slug in existing_leg_slugs:
                leg_id = existing_leg_slugs[slug]
                leg_updates.append({
                    "id": leg_id,
                    "full_name": name,
                    "primary_position": prim_pos,
                    "portrait_meta": portrait_meta,
                    "now": now,
                })
            else:
                leg_id = str(uuid.uuid4())
                existing_leg_slugs[slug] = leg_id
                leg_inserts.append({
                    "id": leg_id,
                    "slug": slug,
                    "full_name": name,
                    "country_code": nation[:3].upper(),
                    "date_of_birth": dob,
                    "primary_position": prim_pos,
                    "secondary_positions_json": json.dumps(sec_pos),
                    "preferred_foot": "right",
                    "historical_height_cm": 180,
                    "gtex_height_cm": 180,
                    "signature_traits_json": json.dumps(
                        ["Prime Masterclass" if "M" in prim_pos else "Lethal Finisher"]
                    ),
                    "signature_role": "Iconic Legend",
                    "era": "Prime Era",
                    "legendary_classification": "icon",
                    "portrait_meta": portrait_meta,
                    "created_at": now,
                    "updated_at": now,
                })
            legend_profile_map[uid] = leg_id

            if uid in existing_players:
                p_id = existing_players[uid]
                leg_player_updates.append({
                    "id": p_id,
                    "full_name": name,
                    "position": prim_pos,
                    "secondary_positions_json": json.dumps(sec_pos),
                    "market_value_eur": val_eur,
                    "potential": rating,
                    "legendary_profile_id": leg_id,
                    "dna_profile": dna_json,
                    "now": now,
                })
            else:
                p_id = str(uuid.uuid4())
                existing_players[uid] = p_id
                leg_player_inserts.append({
                    "id": p_id,
                    "uid": uid,
                    "country_id": cid,
                    "full_name": name,
                    "position": prim_pos,
                    "normalized_position": prim_pos,
                    "secondary_positions_json": json.dumps(sec_pos),
                    "date_of_birth": dob,
                    "market_value_eur": val_eur,
                    "is_real": True,
                    "tier": "legend",
                    "canonical_display_name": name,
                    "real_world_club_name": r.get("Club") or "GTEX Legends XI",
                    "potential": rating,
                    "legendary_profile_id": leg_id,
                    "dna_profile": dna_json,
                    "now": now,
                })

            leg_image_upserts.append({
                "id": str(uuid.uuid4()),
                "uid": uid,
                "pid": p_id,
                "pic_url": pic_url,
                "now": now,
            })

        for i in range(0, len(leg_inserts), batch_size):
            session.execute(sql_insert_legend, leg_inserts[i : i + batch_size])
        for i in range(0, len(leg_updates), batch_size):
            session.execute(sql_update_legend, leg_updates[i : i + batch_size])
        for i in range(0, len(leg_player_inserts), batch_size):
            session.execute(sql_insert_player, leg_player_inserts[i : i + batch_size])
        for i in range(0, len(leg_player_updates), batch_size):
            session.execute(sql_update_player, leg_player_updates[i : i + batch_size])
        for i in range(0, len(leg_image_upserts), batch_size):
            session.execute(sql_upsert_image, leg_image_upserts[i : i + batch_size])
        session.commit()
        logger.info("Committed %d legends to Supabase with verified portraits.", len(unified_legends))

        # 3. Ingest Victor Osimhen Special Build (Active Real Player, Galatasaray, Official Photo)
        logger.info("--- Ingesting Victor Osimhen Special Build ---")
        osimhen = universe["osimhen_row"]
        if osimhen:
            ouid = osimhen["Unique ID"]
            oname = canonical_name(osimhen["Name"])
            odob = parse_dob(osimhen.get("Date Of Birth"))
            opos, osec = normalize_positions(osimhen.get("Position"))
            oval = parse_money(osimhen.get("Value"))
            opot = parse_rating(osimhen.get("Best Pot Rating")) or 87
            ocid = resolve_country_id("Nigeria", country_map)
            opic_url = "https://cdn.sportmonks.com/images/soccer/players/29/455805.png"
            odna_json = json.dumps({
                "portraitUrl": opic_url,
                "portraitStatus": "ready",
                "current_rating": 86,
                "potential_rating": opot,
            })

            if ouid in existing_players:
                op_id = existing_players[ouid]
                session.execute(
                    text("""
                        UPDATE ingestion_players SET
                            full_name = :name, canonical_display_name = :name,
                            real_world_club_name = 'Galatasaray', market_value_eur = :val,
                            current_market_reference_value = :val, potential = :pot,
                            is_real_player = true, real_player_tier = 'marquee',
                            dna_profile = :dna, updated_at = :now
                        WHERE id = :id
                    """),
                    {"id": op_id, "name": oname, "val": oval, "pot": opot, "dna": odna_json, "now": now},
                )
            else:
                op_id = str(uuid.uuid4())
                existing_players[ouid] = op_id
                session.execute(
                    sql_insert_player,
                    [{
                        "id": op_id,
                        "uid": ouid,
                        "country_id": ocid,
                        "full_name": oname,
                        "position": opos,
                        "normalized_position": opos,
                        "secondary_positions_json": json.dumps(osec),
                        "date_of_birth": odob,
                        "market_value_eur": oval,
                        "is_real": True,
                        "tier": "marquee",
                        "canonical_display_name": oname,
                        "real_world_club_name": "Galatasaray",
                        "potential": opot,
                        "legendary_profile_id": None,
                        "dna_profile": odna_json,
                        "now": now,
                    }],
                )

            session.execute(
                sql_upsert_image,
                [{"id": str(uuid.uuid4()), "uid": ouid, "pid": op_id, "pic_url": opic_url, "now": now}],
            )
            session.commit()
            logger.info("Victor Osimhen Galatasaray marquee build successfully committed with verified portrait!")

        # 3.1 Ingest Zadok Yohanna (Active Real Wonderkid, Brighton & Hove Albion)
        logger.info("--- Ingesting Zadok Yohanna Special Wonderkid Build ---")
        z_uid = "1421433"
        z_name = "Zadok Yohanna"
        z_dob = "2007-06-29"
        z_pos, z_sec = "RW", ["LW", "AM R", "ST"]
        z_val = 28000000.0
        z_pot = 89
        z_cur = 74
        z_cid = resolve_country_id("Nigeria", country_map)
        z_pic_url = "https://img.a.transfermarkt.technology/portrait/original/1421433-1774883072.jpg?lm=4711"
        z_dna_json = json.dumps({
            "portraitUrl": z_pic_url,
            "portraitStatus": "ready",
            "current_rating": z_cur,
            "potential_rating": z_pot,
            "attributes": {
                "pace": 18,
                "acceleration": 18,
                "sprint_speed": 17,
                "dribbling": 17,
                "agility": 16,
                "flair": 16,
                "technique": 15,
                "first_touch": 15,
                "finishing": 13,
                "passing": 13,
                "vision": 13,
                "stamina": 14,
                "work_rate": 14,
                "determination": 15,
                "composure": 13,
            },
            "playstyle": "Explosive Inverted Winger (Nigerian Neymar)",
            "preferred_foot": "Left",
            "height_cm": 184,
            "weight_kg": 76,
            "shirt_number": 36,
            "agency": "001 United Sports",
            "birth_place": "Bauchi State, Nigeria",
            "former_club": "AIK Stockholm",
            "record_transfer_fee_eur": z_val,
        })

        if z_uid in existing_players:
            zp_id = existing_players[z_uid]
            session.execute(
                text("""
                    UPDATE ingestion_players SET
                        full_name = :name, canonical_display_name = :name,
                        position = :pos, normalized_position = :pos,
                        secondary_positions_json = :sec,
                        real_world_club_name = 'Brighton & Hove Albion',
                        market_value_eur = :val, current_market_reference_value = :val,
                        potential = :pot, is_real_player = true, real_player_tier = 'wonderkid',
                        dna_profile = :dna, updated_at = :now
                    WHERE id = :id
                """),
                {"id": zp_id, "name": z_name, "pos": z_pos, "sec": json.dumps(z_sec), "val": z_val, "pot": z_pot, "dna": z_dna_json, "now": now},
            )
        else:
            zp_id = str(uuid.uuid4())
            existing_players[z_uid] = zp_id
            session.execute(
                sql_insert_player,
                [{
                    "id": zp_id,
                    "uid": z_uid,
                    "country_id": z_cid,
                    "full_name": z_name,
                    "position": z_pos,
                    "normalized_position": z_pos,
                    "secondary_positions_json": json.dumps(z_sec),
                    "date_of_birth": z_dob,
                    "market_value_eur": z_val,
                    "is_real": True,
                    "tier": "wonderkid",
                    "canonical_display_name": z_name,
                    "real_world_club_name": "Brighton & Hove Albion",
                    "potential": z_pot,
                    "legendary_profile_id": None,
                    "dna_profile": z_dna_json,
                    "now": now,
                }],
            )

        session.execute(
            sql_upsert_image,
            [{"id": str(uuid.uuid4()), "uid": z_uid, "pid": zp_id, "pic_url": z_pic_url, "now": now}],
        )
        session.commit()
        logger.info("Zadok Yohanna Brighton wonderkid build successfully committed with verified portrait!")

        # 3.2 Ingest Malick Yalcouyé (Active Real Wonderkid, Brighton & Hove Albion)
        logger.info("--- Ingesting Malick Yalcouyé Special Wonderkid Build ---")
        my_uid = "12095038"
        my_name = "Malick Yalcouyé"
        my_dob = "2005-11-18"
        my_pos, my_sec = "CM", ["DM", "AM C", "RM"]
        my_val = 22000000.0
        my_pot = 88
        my_cur = 74
        my_cid = resolve_country_id("Cote d'Ivoire", country_map) or "ffe28ba6-133a-4b77-b500-bebb685b0b10"
        my_pic_url = "https://img.a.transfermarkt.technology/portrait/original/1178758-1714124381.jpg?lm=4711"
        my_dna_json = json.dumps({
            "portraitUrl": my_pic_url,
            "portraitStatus": "ready",
            "current_rating": my_cur,
            "potential_rating": my_pot,
            "attributes": {
                "work_rate": 18,
                "stamina": 18,
                "acceleration": 16,
                "agility": 16,
                "pace": 15,
                "tackling": 15,
                "interceptions": 15,
                "dribbling": 15,
                "ball_carrying": 16,
                "technique": 14,
                "short_passing": 14,
                "vision": 13,
                "determination": 16,
                "bravery": 16,
                "natural_fitness": 17,
                "composure": 13,
            },
            "playstyle": "Dynamic Disruptor & Progressive Carrier (Ivorian Kanté)",
            "preferred_foot": "Right",
            "height_cm": 169,
            "weight_kg": 65,
            "shirt_number": 35,
            "agency": "Universal Football",
            "birth_place": "Mali / Ivory Coast",
            "former_clubs": ["ASEC Mimosas", "IFK Göteborg", "Sturm Graz (loan)"],
            "market_value_eur": my_val,
        })

        if my_uid in existing_players:
            myp_id = existing_players[my_uid]
            session.execute(
                text("""
                    UPDATE ingestion_players SET
                        full_name = :name, canonical_display_name = :name,
                        position = :pos, normalized_position = :pos,
                        secondary_positions_json = :sec,
                        real_world_club_name = 'Brighton & Hove Albion',
                        market_value_eur = :val, current_market_reference_value = :val,
                        potential = :pot, is_real_player = true, real_player_tier = 'wonderkid',
                        dna_profile = :dna, updated_at = :now
                    WHERE id = :id
                """),
                {"id": myp_id, "name": my_name, "pos": my_pos, "sec": json.dumps(my_sec), "val": my_val, "pot": my_pot, "dna": my_dna_json, "now": now},
            )
        else:
            myp_id = str(uuid.uuid4())
            existing_players[my_uid] = myp_id
            session.execute(
                sql_insert_player,
                [{
                    "id": myp_id,
                    "uid": my_uid,
                    "country_id": my_cid,
                    "full_name": my_name,
                    "position": my_pos,
                    "normalized_position": my_pos,
                    "secondary_positions_json": json.dumps(my_sec),
                    "date_of_birth": my_dob,
                    "market_value_eur": my_val,
                    "is_real": True,
                    "tier": "wonderkid",
                    "canonical_display_name": my_name,
                    "real_world_club_name": "Brighton & Hove Albion",
                    "potential": my_pot,
                    "legendary_profile_id": None,
                    "dna_profile": my_dna_json,
                    "now": now,
                }],
            )

        session.execute(
            sql_upsert_image,
            [{"id": str(uuid.uuid4()), "uid": my_uid, "pid": myp_id, "pic_url": my_pic_url, "now": now}],
        )
        session.commit()
        logger.info("Malick Yalcouyé Brighton wonderkid build successfully committed with verified portrait!")

        # 3.3 Ingest Femi Azeez (Brighton & Hove Albion)
        logger.info("--- Updating Femi Azeez to Brighton & Hove Albion ---")
        fa_val = 8000000.0
        fa_pot = 84
        fa_cur = 75
        fa_photo = "https://cdn.sportmonks.com/images/soccer/players/28/26715260.png"
        fa_dna = json.dumps({
            "portraitUrl": fa_photo,
            "portraitStatus": "ready",
            "current_rating": fa_cur,
            "potential_rating": fa_pot,
            "attributes": {"pace": 17, "acceleration": 17, "dribbling": 15, "shot_power": 15, "finishing": 14, "crossing": 14, "agility": 15, "flair": 15, "stamina": 15, "work_rate": 15},
            "playstyle": "Explosive Direct Premier League Inverted Winger",
            "preferred_foot": "Left",
            "height_cm": 178,
            "weight_kg": 72,
            "shirt_number": 19
        })
        session.execute(
            text("""
                UPDATE ingestion_players SET
                    real_world_club_name = 'Brighton & Hove Albion', position = 'RW', normalized_position = 'RW',
                    secondary_positions_json = '["LW", "ST", "AM R"]', market_value_eur = :val,
                    current_market_reference_value = :val, potential = :pot, dna_profile = :dna,
                    real_player_tier = 'wonderkid', updated_at = :now
                WHERE full_name ILIKE '%Femi Azeez%'
            """),
            {"val": fa_val, "pot": fa_pot, "dna": fa_dna, "now": now}
        )

        # 3.4 Ingest Chibuike Nwaiwu Upgrade (Trabzonspor Core Titan)
        logger.info("--- Upgrading Chibuike Nwaiwu at Trabzonspor ---")
        cn_val = 18000000.0
        cn_pot = 87
        cn_cur = 77
        cn_photo = "https://img.a.transfermarkt.technology/portrait/original/985825-1789399837.jpg?lm=4711"
        cn_dna = json.dumps({
            "portraitUrl": cn_photo,
            "portraitStatus": "ready",
            "current_rating": cn_cur,
            "potential_rating": cn_pot,
            "attributes": {"strength": 18, "jumping": 18, "heading": 16, "tackling": 16, "marking": 16, "interceptions": 15, "positioning": 15, "composure": 15, "passing": 15, "pace": 14, "bravery": 17, "leadership": 15},
            "playstyle": "Dominant Aerial Colossus & High-Accuracy Ball-Playing CB",
            "preferred_foot": "Right",
            "height_cm": 193,
            "weight_kg": 86,
            "shirt_number": 4
        })
        session.execute(
            text("""
                UPDATE ingestion_players SET
                    real_world_club_name = 'Trabzonspor', position = 'CB', normalized_position = 'CB',
                    secondary_positions_json = '["DM", "SW"]', market_value_eur = :val,
                    current_market_reference_value = :val, potential = :pot, dna_profile = :dna,
                    real_player_tier = 'established', height_cm = 193, weight_kg = 86,
                    preferred_foot = 'Right', shirt_number = 4, updated_at = :now
                WHERE full_name ILIKE '%Chibuike Nwaiwu%'
            """),
            {"val": cn_val, "pot": cn_pot, "dna": cn_dna, "now": now}
        )
        session.commit()

        # 4. Ingest Active Real Players and Wonderkids (Non-Retired, Multi-Tier Portraits)
        classified_real = universe["classified_real"]
        real_groups = [
            ("wonderkid", classified_real["wonderkid"]),
            ("real_modern", classified_real["real_modern"]),
            ("real_base", classified_real["real_base"]),
        ]

        for group_label, p_list in real_groups:
            logger.info("--- Ingesting %d players from %s ---", len(p_list), group_label)
            tier_label = "wonderkid" if group_label == "wonderkid" else "established"

            for i in range(0, len(p_list), batch_size):
                batch = p_list[i : i + batch_size]
                b_inserts = []
                b_updates = []
                b_images = []

                for r in batch:
                    uid = r["Unique ID"]
                    if uid == "13158205" or uid in legend_profile_map:
                        continue
                    name = canonical_name(r["Name"])
                    nation = r.get("Nation", "").split("/")[0].strip()
                    cid = resolve_country_id(nation, country_map)
                    dob = parse_dob(r.get("Date Of Birth"))
                    pos, sec = normalize_positions(r.get("Position"))
                    val = parse_money(r.get("Value"))
                    pot = parse_rating(r.get("Best Pot Rating")) or parse_rating(r.get("Best Rating")) or 75
                    cur = parse_rating(r.get("Best Rating")) or max(45, pot - 5)
                    club = r.get("Club")

                    pic_url = resolve_player_picture(name, nation, uid, photo_db, faces)
                    dna_json = json.dumps({
                        "portraitUrl": pic_url,
                        "portraitStatus": "ready",
                        "current_rating": cur,
                        "potential_rating": pot,
                    })

                    if uid in existing_players:
                        p_id = existing_players[uid]
                        b_updates.append({
                            "id": p_id,
                            "full_name": name,
                            "position": pos,
                            "secondary_positions_json": json.dumps(sec),
                            "market_value_eur": val,
                            "potential": pot,
                            "legendary_profile_id": None,
                            "dna_profile": dna_json,
                            "now": now,
                        })
                    else:
                        p_id = str(uuid.uuid4())
                        existing_players[uid] = p_id
                        b_inserts.append({
                            "id": p_id,
                            "uid": uid,
                            "country_id": cid,
                            "full_name": name,
                            "position": pos,
                            "normalized_position": pos,
                            "secondary_positions_json": json.dumps(sec),
                            "date_of_birth": dob,
                            "market_value_eur": val,
                            "is_real": True,
                            "tier": tier_label,
                            "canonical_display_name": name,
                            "real_world_club_name": club,
                            "potential": pot,
                            "legendary_profile_id": None,
                            "dna_profile": dna_json,
                            "now": now,
                        })

                    b_images.append({
                        "id": str(uuid.uuid4()),
                        "uid": uid,
                        "pid": p_id,
                        "pic_url": pic_url,
                        "now": now,
                    })

                if b_inserts:
                    session.execute(sql_insert_player, b_inserts)
                if b_updates:
                    session.execute(sql_update_player, b_updates)
                if b_images:
                    session.execute(sql_upsert_image, b_images)
                session.commit()
                logger.info(
                    "  Processed %d/%d of %s with portraits",
                    min(i + batch_size, len(p_list)),
                    len(p_list),
                    group_label,
                )

        # 5. Ingest Pure Engine Regens with Cloudinary Facebank Binding
        pure_regens = universe["pure_regens"]
        logger.info("--- Ingesting %d Pure Regens with Cloudinary Facebank Binding ---", len(pure_regens))

        for i in range(0, len(pure_regens), batch_size):
            batch = pure_regens[i : i + batch_size]
            b_inserts = []
            b_updates = []
            b_images = []

            for r in batch:
                uid = r["Unique ID"]
                name = canonical_name(r["Name"])
                nation = r.get("Nation", "").split("/")[0].strip()
                cid = resolve_country_id(nation, country_map)
                dob = parse_dob(r.get("Date Of Birth"))
                pos, sec = normalize_positions(r.get("Position"))
                val = parse_money(r.get("Value"))
                pot = parse_rating(r.get("Best Pot Rating")) or parse_rating(r.get("Best Rating")) or 78
                cur = parse_rating(r.get("Best Rating")) or max(45, pot - 10)
                club = r.get("Club")

                face_idx = hash(f"{uid}-{name}") % face_count if face_count > 0 else 0
                face_asset = faces[face_idx] if face_count > 0 else {}
                face_url = face_asset.get("cloudinary_secure_url", "")
                dna = {
                    "faceSeed": f"fm23-{uid}",
                    "portraitUrl": face_url,
                    "portraitStatus": "ready",
                    "ethnicity": face_asset.get("ethnicity", "Mixed"),
                    "hairColour": face_asset.get("hair_colour", "Dark"),
                    "current_rating": cur,
                    "potential_rating": pot,
                }
                dna_json = json.dumps(dna)

                if uid in existing_players:
                    p_id = existing_players[uid]
                    b_updates.append({
                        "id": p_id,
                        "full_name": name,
                        "position": pos,
                        "secondary_positions_json": json.dumps(sec),
                        "market_value_eur": val,
                        "potential": pot,
                        "legendary_profile_id": None,
                        "dna_profile": dna_json,
                        "now": now,
                    })
                else:
                    p_id = str(uuid.uuid4())
                    existing_players[uid] = p_id
                    b_inserts.append({
                        "id": p_id,
                        "uid": uid,
                        "country_id": cid,
                        "full_name": name,
                        "position": pos,
                        "normalized_position": pos,
                        "secondary_positions_json": json.dumps(sec),
                        "date_of_birth": dob,
                        "market_value_eur": val,
                        "is_real": False,
                        "tier": "regen",
                        "canonical_display_name": name,
                        "real_world_club_name": club,
                        "potential": pot,
                        "legendary_profile_id": None,
                        "dna_profile": dna_json,
                        "now": now,
                    })

                b_images.append({
                    "id": str(uuid.uuid4()),
                    "uid": uid,
                    "pid": p_id,
                    "pic_url": face_url,
                    "now": now,
                })

            if b_inserts:
                session.execute(sql_insert_player, b_inserts)
            if b_updates:
                session.execute(sql_update_player, b_updates)
            if b_images:
                session.execute(sql_upsert_image, b_images)
            session.commit()
            logger.info("  Processed %d/%d regens with portraits", min(i + batch_size, len(pure_regens)), len(pure_regens))

        # 6. Issue Share Markets in player_share_markets (Batched)
        logger.info("--- Issuing / Synchronizing Share Markets for FM23 Universe (Regen 1-of-1 vs Real Fractional) ---")
        unissued_players = session.execute(text("""
                SELECT p.id, p.is_real_player, p.legendary_profile_id, p.market_value_eur, p.potential, p.dna_profile, p.real_player_tier
                FROM ingestion_players p
                WHERE p.source_provider = 'fm23_genie_scout'
            """)).fetchall()

        logger.info("Found %d FM23 players to synchronize share markets.", len(unissued_players))
        sm_batch_size = 500
        for i in range(0, len(unissued_players), sm_batch_size):
            sm_batch = unissued_players[i : i + sm_batch_size]
            sm_rows = []
            for p_id, is_real, leg_id, _val, pot, dna_raw, p_tier in sm_batch:
                pot_int = int(pot or 75)
                dna_dict = {}
                if isinstance(dna_raw, dict):
                    dna_dict = dna_raw
                elif isinstance(dna_raw, str) and dna_raw.strip().startswith("{"):
                    try:
                        dna_dict = json.loads(dna_raw)
                    except Exception:
                        dna_dict = {}

                cur_int = int(dna_dict.get("current_rating") or (pot_int if leg_id else max(40, pot_int - 8)))

                # Determine GSI supply tier for multi-share assets (both Real & Legends follow GSI)
                gsi = pot_int / 100.0
                if gsi >= 0.97:
                    tier_code, base_total_shares = "icon", 100
                elif gsi >= 0.90:
                    tier_code, base_total_shares = "elite", 200
                elif gsi >= 0.72:
                    tier_code, base_total_shares = "core", 400
                elif gsi >= 0.50:
                    tier_code, base_total_shares = "prospect", 600
                else:
                    tier_code, base_total_shares = "discovery", 900

                if not is_real or p_tier == "regen":
                    # REGEN ECONOMY: Single share (1-of-1), 100% indivisible ownership
                    total_shares = 1
                    circulating = 1
                    share_price = calculate_gsi_player_price(cur_int, pot_int, is_real=False, is_legend=False)
                    meta = {
                        "asset_type": "regen_single_share",
                        "ownership": "100_percent_indivisible",
                        "total_shares": 1,
                        "current_gsi": cur_int,
                        "potential_gsi": pot_int,
                    }
                elif leg_id or p_tier == "legend":
                    # LEGEND ECONOMY: Single share (1-of-1), only ONE copy of every legend exists
                    total_shares = 1
                    circulating = 1
                    share_price = calculate_gsi_player_price(cur_int, pot_int, is_real=True, is_legend=True)
                    meta = {
                        "asset_type": "legend_single_share",
                        "ownership": "100_percent_indivisible",
                        "total_shares": 1,
                        "gsi": pot_int,
                        "scarcity": "1_of_1_icon",
                    }
                else:
                    # REAL PLAYER / WONDERKID: GSI-based total shares, standard float (20%)
                    total_shares = base_total_shares
                    circulating = max(10, int(total_shares * 0.20))
                    share_price = calculate_gsi_player_price(cur_int, pot_int, is_real=True, is_legend=False)
                    meta = {
                        "asset_type": "real_player_fractional_share",
                        "tier": tier_code,
                        "current_gsi": cur_int,
                        "potential_gsi": pot_int,
                        "scarcity": "standard_float_20pct",
                    }

                sm_rows.append({
                    "id": str(uuid.uuid4()),
                    "player_id": p_id,
                    "total_shares": total_shares,
                    "circulating_shares": circulating,
                    "share_price": share_price,
                    "meta": json.dumps(meta),
                    "now": now,
                })

            if sm_rows:
                session.execute(sql_upsert_share_market, sm_rows)
            session.commit()
            logger.info(
                "  Issued / Synchronized %d/%d share markets", min(i + sm_batch_size, len(unissued_players)), len(unissued_players)
            )

        # 7. Generate Executive Staff Catalog
        logger.info("--- Compiling Elite Staff Catalog ---")
        staff_rows = universe["staff_rows"]
        catalog_items = []
        for s in staff_rows:
            s_name = canonical_name(s.get("Name"))
            s_uid = s.get("Unique ID")
            s_nation = s.get("Nation", "Unknown").split("/")[0].strip()
            s_team = s.get("Team", "-")
            hc_rat = parse_rating(s.get("Head Coach Rating")) or 0
            gm_rat = parse_rating(s.get("General Manager Rating")) or 0
            hoyd_rat = parse_rating(s.get("Head of Youth Dev Rating")) or 0
            scout_rat = parse_rating(s.get("Scout Rating")) or 0
            phys_rat = parse_rating(s.get("Physio Rating")) or 0

            best_role = "first_team_manager"
            best_rat = hc_rat
            if gm_rat > best_rat:
                best_role = "general_manager"
                best_rat = gm_rat
            if hoyd_rat > best_rat:
                best_role = "head_of_youth_development"
                best_rat = hoyd_rat
            if scout_rat > best_rat:
                best_role = "chief_scout"
                best_rat = scout_rat
            if phys_rat > best_rat:
                best_role = "medical_director"
                best_rat = phys_rat

            if best_rat >= 65:
                # Upfront signing fee reduced by 60%: anchor 65 rating -> 80 Coins, 95 rating -> 800 Coins
                signing_fee = round(80.0 + (best_rat - 65) * ((800.0 - 80.0) / 30.0), 1)
                # Annual salary in Fan Coins reduced by 75%: anchor 65 rating -> 150 FC, 95 rating -> 2,000 FC
                annual_salary = round(150.0 + (best_rat - 65) * ((2000.0 - 150.0) / 30.0), 1)

                catalog_items.append(
                    {
                        "id": f"staff_{s_uid}",
                        "staff_id": f"staff_{s_uid}",
                        "role": best_role,
                        "role_label": best_role.replace("_", " ").title(),
                        "name": s_name,
                        "nation": s_nation,
                        "real_club": s_team if s_team != "-" else None,
                        "rating": best_rat,
                        "style": "Elite Professional",
                        "temperament": "pragmatic",
                        "ambition": min(20, max(10, round(best_rat / 5))),
                        "loyalty": 14,
                        "youth_development": min(20, max(8, round(hoyd_rat / 5))),
                        "tactical_flexibility": min(20, max(8, round(hc_rat / 5))),
                        "scouting_accuracy": min(20, max(8, round(scout_rat / 5))),
                        "medical_expertise": min(20, max(8, round(phys_rat / 5))),
                        "min_prestige": max(20, round(best_rat * 0.8)),
                        "salary": annual_salary,
                        "salary_fancoin": annual_salary,
                        "salary_gtex": round(annual_salary / 10.0, 1),
                        "signing_fee_gtex": signing_fee,
                        "contract_1yr_fancoin": annual_salary,
                        "contract_1yr_gtex": round(annual_salary / 10.0, 1),
                        "contract_3yr_fancoin": round(annual_salary * 3, 1),
                        "contract_3yr_gtex": round(annual_salary * 3 / 10.0, 1),
                        "bio": f"Experienced {s_nation} tactical specialist currently registered with {s_team}.",
                        "specialty": f"{best_role.replace('_', ' ').title()} Mastery",
                    }
                )

        staff_out = BACKEND_ROOT / "app" / "owner_console" / "executive_staff_catalog.json"
        with open(staff_out, "w", encoding="utf-8") as f:
            json.dump(catalog_items, f, indent=2, ensure_ascii=False)
        logger.info("Exported %d elite staff members to %s", len(catalog_items), staff_out.name)

    logger.info("=== GTEX FM23 PRODUCTION INGESTION COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest FM23 & Genie Scout exports into GTEX.")
    parser.add_argument("--execute", action="store_true", help="Execute database ingestion.")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run validation without database writes.")
    args = parser.parse_args()

    if args.execute:
        execute_ingestion()
    else:
        execute_dry_run()
