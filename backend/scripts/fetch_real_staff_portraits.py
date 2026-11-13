#!/usr/bin/env python3
"""Download a Wikimedia photograph for each real staff member.

Regen staff are not touched. Invented GTEX characters are not touched.
A page is kept only when the title matches the person and the description
is about football.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.manager_market.seed_catalog import build_seed_catalog  # noqa: E402
from app.owner_console.real_first_team_managers import canon_fold  # noqa: E402
from app.owner_console.real_staff_portraits import FICTIONAL_STAFF, MANIFEST_PATH  # noqa: E402

PHOTO_DIR = ROOT / "frontend" / "react-shell" / "public" / "staff-portraits" / "real"
SOURCE_PATH = BACKEND / "app" / "owner_console" / "real_staff_portrait_sources.json"
CATALOG_PATH = BACKEND / "app" / "owner_console" / "executive_staff_catalog.json"
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "GTEXStaffPortraitFetcher/1.0 (https://playgtex.app; real staff photographs)"
FOOTBALL_TERMS = (
    "football",
    "soccer",
    "coach",
    "manager",
    "footballer",
    "midfielder",
    "defender",
    "goalkeeper",
    "striker",
    "winger",
    "forward",
    "premier league",
    "serie a",
    "la liga",
    "bundesliga",
    "fifa",
    "uefa",
)
SKIP_TERMS = ("disambiguation", "film", "album", "song", "television series", "novel")
PARTICLES = {"de", "da", "di", "del", "della", "van", "von", "bin", "al", "st", "jr", "dr", "sir", "dame", "don"}
EXTRA_REAL = (
    ("Paul Mitchell", "England"),
    ("Michael Edwards", "England"),
    ("Sven Mislintat", "Germany"),
    ("Luis Campos", "Portugal"),
    ("Lieven Maesschalck", "Belgium"),
    ("Ramon Cugat", "Spain"),
)


def _request(params: dict[str, str]) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    delay = 1.0
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code not in {429, 503} or attempt == 3:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("wikipedia request failed")


def _search_name(name: str) -> str:
    text = name.replace("Dr.", "").replace("Dr ", "").strip()
    return " ".join(text.split())


def _slug(folded: str) -> str:
    return "".join(character if character.isalnum() else "-" for character in folded).strip("-")


def _title_matches(name: str, title: str) -> bool:
    folded_title = canon_fold(title)
    tokens = [token for token in canon_fold(name).split() if token not in PARTICLES and token != "dr"]
    if not tokens:
        return False
    if len(tokens) == 1:
        return folded_title.startswith(tokens[0])
    return all(token in folded_title for token in tokens)


def _about_football(title: str, description: str, snippet: str) -> bool:
    blob = canon_fold(f"{title} {description} {snippet}")
    if any(term in blob for term in SKIP_TERMS):
        return False
    return any(term in blob for term in FOOTBALL_TERMS)


def _page_image(title: str) -> tuple[str, str] | None:
    payload = _request(
        {
            "action": "query",
            "prop": "pageimages|pageterms",
            "piprop": "thumbnail",
            "pithumbsize": "330",
            "pilicense": "any",
            "redirects": "1",
            "titles": title,
            "wbptterms": "description",
            "format": "json",
        }
    )
    pages = (payload.get("query") or {}).get("pages") or {}
    for page in pages.values():
        if page.get("missing") is not None or page.get("invalid") is not None:
            continue
        terms = page.get("terms") or {}
        description = " ".join(terms.get("description") or [])
        thumbnail = (page.get("thumbnail") or {}).get("source") or ""
        resolved = str(page.get("title") or title)
        if not thumbnail or "wikimedia.org" not in thumbnail:
            return None
        if not _about_football(resolved, description, ""):
            return None
        return thumbnail, resolved
    return None


def find_photo(name: str, nation: str | None) -> tuple[str, str] | None:
    query = f'"{_search_name(name)}" {nation or ""} football'
    payload = _request(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": "4",
            "srnamespace": "0",
            "format": "json",
        }
    )
    for hit in (payload.get("query") or {}).get("search") or []:
        title = str(hit.get("title") or "")
        if not _title_matches(name, title):
            continue
        found = _page_image(title)
        if found and _title_matches(name, found[1]):
            return found
    return None


def _download(url: str, destination: Path) -> Path | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    if len(payload) < 2000 or payload[:2] not in {b"\xff\xd8", b"\x89P"}:
        return None
    suffix = ".png" if payload.startswith(b"\x89P") else ".jpg"
    target = destination.with_suffix(suffix)
    target.write_bytes(payload)
    return target


def _people() -> list[tuple[str, str, str | None]]:
    ordered: list[tuple[str, str, str | None]] = []
    seen: set[str] = set()

    def add(name: str | None, nation: str | None) -> None:
        clean = " ".join(str(name or "").split())
        folded = canon_fold(clean)
        if not clean or folded in seen or folded in FICTIONAL_STAFF or len(folded) < 4:
            return
        seen.add(folded)
        ordered.append((clean, folded, nation))

    for name, nation in EXTRA_REAL:
        add(name, nation)
    for record in build_seed_catalog():
        add(record.get("name"), record.get("nation"))
    if CATALOG_PATH.is_file():
        loaded = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        for record in loaded:
            add(record.get("name"), record.get("nation"))
    return ordered


def _one(person: tuple[str, str, str | None]) -> tuple[str, str, str, str] | None:
    name, folded, nation = person
    destination = PHOTO_DIR / f"{_slug(folded)}.jpg"
    existing = next(
        (
            path
            for path in (destination, destination.with_suffix(".png"))
            if path.is_file() and path.stat().st_size >= 2000
        ),
        None,
    )
    if existing is not None:
        return folded, f"/staff-portraits/real/{existing.name}", "", name
    try:
        found = find_photo(name, nation)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    if not found:
        return None
    source, title = found
    try:
        saved = _download(source, destination)
        if saved is None:
            return None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    return folded, f"/staff-portraits/real/{saved.name}", source, title


def main() -> None:
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    people = _people()
    manifest = {}
    sources = {}
    if MANIFEST_PATH.is_file():
        loaded = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            manifest.update({str(key): str(value) for key, value in loaded.items()})
    if SOURCE_PATH.is_file():
        loaded = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            sources.update(loaded)
    pending = [person for person in people if person[1] not in manifest]
    print(f"real staff {len(people)}; already saved {len(people) - len(pending)}; fetching {len(pending)}", flush=True)
    done = 0
    found = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_one, person) for person in pending]
        for future in as_completed(futures):
            done += 1
            try:
                result = future.result()
            except Exception as error:
                print(f"skip: {error}", flush=True)
                result = None
            if result:
                folded, public_url, source, title = result
                manifest[folded] = public_url
                if source:
                    sources[folded] = {"source": source, "title": title}
                found += 1
            if done % 25 == 0:
                MANIFEST_PATH.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
                )
                SOURCE_PATH.write_text(
                    json.dumps(sources, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
                )
                print(f"checked {done}/{len(pending)}; photographs {found}", flush=True)
            time.sleep(0.02)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    SOURCE_PATH.write_text(json.dumps(sources, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"saved {len(manifest)} photographs for {len(people)} real staff", flush=True)


if __name__ == "__main__":
    main()
