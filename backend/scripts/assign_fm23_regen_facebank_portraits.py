"""Assign deterministic nationality/ethnicity-matched facebank portraits to FM23 regens.

Requirements:
1. Every active FM23 regen introduced to the game receives a facebank picture.
2. The assigned portrait strictly matches the regen's nationality/ethnicity.
3. Assets come from the approved newgen facebank (manifest.json, Cloudinary CDN).
4. Ryan Matos (2002088877) is quarantined and must NOT receive a portrait.
5. Preserves existing real player photos (Transfermarkt/Sportmonks) for real wonderkids.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "generated_media"
    / "regen_newgen_faces"
    / "manifest.json"
)

QUARANTINED_PROVIDER_IDS = {"2002088877"}
QUARANTINED_PLAYER_IDS = {"c1a2dddc-9b29-482f-ba06-0b39763830ba"}

NATION_TO_ETHNICITY = {
    # African
    "nigeria": "African", "ghana": "African", "cameroon": "African", "senegal": "African",
    "ivory coast": "African", "côte d'ivoire": "African", "mali": "African", "guinea": "African",
    "congo": "African", "dr congo": "African", "democratic republic of congo": "African",
    "south africa": "African", "angola": "African", "burkina faso": "African", "benin": "African",
    "gabon": "African", "zambia": "African", "zimbabwe": "African", "kenya": "African",
    "uganda": "African", "tanzania": "African", "togo": "African", "sierra leone": "African",
    "liberia": "African", "gambia": "African", "guinea-bissau": "African", "cape verde": "African",
    "mozambique": "African", "madagascar": "African", "equatorial guinea": "African", "namibia": "African",
    "rwanda": "African", "burundi": "African", "malawi": "African", "mauritania": "African",
    "niger": "African", "chad": "African", "central african republic": "African", "eritrea": "African",
    "ethiopia": "African", "somalia": "African", "sudan": "African", "south sudan": "African",
    "jamaica": "African", "haiti": "African", "trinidad & tobago": "African", "barbados": "African",
    "guadeloupe": "African", "martinique": "African", "french guiana": "African", "curacao": "African",
    "curaçao": "African", "suriname": "African", "lesotho": "African",

    # Hispanic / Latin American
    "argentina": "Hispanic", "colombia": "Hispanic", "uruguay": "Hispanic", "chile": "Hispanic",
    "paraguay": "Hispanic", "peru": "Hispanic", "ecuador": "Hispanic", "venezuela": "Hispanic",
    "bolivia": "Hispanic", "mexico": "Hispanic", "costa rica": "Hispanic", "panama": "Hispanic",
    "honduras": "Hispanic", "guatemala": "Hispanic", "el salvador": "Hispanic", "nicaragua": "Hispanic",
    "cuba": "Hispanic", "dominican republic": "Hispanic", "puerto rico": "Hispanic",

    # Brazil / Mixed / Diverse
    "brazil": "Mixed", "united states": "Mixed", "usa": "Mixed", "u.s.a.": "Mixed",
    "canada": "Mixed", "australia": "Mixed", "new zealand": "Mixed",

    # North European / Central / Eastern European
    "england": "North european", "france": "North european", "germany": "North european",
    "netherlands": "North european", "belgium": "North european", "scotland": "North european",
    "wales": "North european", "northern ireland": "North european", "ireland": "North european",
    "republic of ireland": "North european", "sweden": "North european", "norway": "North european",
    "denmark": "North european", "poland": "North european", "austria": "North european",
    "switzerland": "North european", "czech republic": "North european", "czechia": "North european",
    "slovakia": "North european", "ukraine": "North european", "russia": "North european",
    "finland": "North european", "hungary": "North european", "belarus": "North european",
    "iceland": "North european", "romania": "North european", "bulgaria": "North european",
    "lithuania": "North european", "latvia": "North european", "estonia": "North european",
    "luxembourg": "North european", "moldova": "North european",

    # South European / Mediterranean / Balkans
    "spain": "South european", "italy": "South european", "portugal": "South european",
    "greece": "South european", "croatia": "South european", "serbia": "South european",
    "bosnia & herzegovina": "South european", "bosnia and herzegovina": "South european",
    "slovenia": "South european", "montenegro": "South european", "north macedonia": "South european",
    "macedonia": "South european", "albania": "South european", "kosovo": "South european",
    "cyprus": "South european", "malta": "South european", "georgia": "South european",
    "armenia": "South european", "pays basque": "South european", "catalonia": "South european",

    # Middle East / North Africa / West Asia
    "turkey": "Middle east", "morocco": "Middle east", "algeria": "Middle east",
    "tunisia": "Middle east", "egypt": "Middle east", "iran": "Middle east",
    "iraq": "Middle east", "saudi arabia": "Middle east", "uae": "Middle east",
    "u.a.e.": "Middle east", "united arab emirates": "Middle east", "qatar": "Middle east",
    "kuwait": "Middle east", "bahrain": "Middle east", "oman": "Middle east", "yemen": "Middle east",
    "jordan": "Middle east", "lebanon": "Middle east", "syria": "Middle east",
    "israel": "Middle east", "palestine": "Middle east", "libya": "Middle east",
    "azerbaijan": "Middle east", "kazakhstan": "Middle east", "uzbekistan": "Middle east",

    # East Asian
    "japan": "East asian", "south korea": "East asian", "korea republic": "East asian",
    "korea dpr": "East asian", "north korea": "East asian", "china": "East asian",
    "taiwan": "East asian", "hong kong": "East asian", "vietnam": "East asian",
    "thailand": "East asian", "indonesia": "East asian", "malaysia": "East asian",
    "philippines": "East asian", "singapore": "East asian", "mongolia": "East asian",

    # Indian / South Asian
    "india": "Indian", "pakistan": "Indian", "bangladesh": "Indian", "sri lanka": "Indian",
    "nepal": "Indian", "afghanistan": "Indian",
}

VALID_ETHNICITIES = {
    "african": "African",
    "east asian": "East asian",
    "hispanic": "Hispanic",
    "indian": "Indian",
    "middle east": "Middle east",
    "mixed": "Mixed",
    "north european": "North european",
    "south european": "South european",
}


class FaceBankIndex:
    def __init__(self, manifest_path: Path | str = MANIFEST_PATH) -> None:
        self.manifest_path = Path(manifest_path)
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assets: list[dict[str, Any]] = data.get("assets", [])
        self.by_eth: dict[str, list[dict[str, Any]]] = {}
        self.by_eth_hair: dict[tuple[str, str], list[dict[str, Any]]] = {}

        for asset in self.assets:
            eth = self.norm_key(asset.get("ethnicity"))
            hair = self.norm_key(asset.get("hair_colour"))
            if eth not in self.by_eth:
                self.by_eth[eth] = []
            self.by_eth[eth].append(asset)

            pair = (eth, hair)
            if pair not in self.by_eth_hair:
                self.by_eth_hair[pair] = []
            self.by_eth_hair[pair].append(asset)

    @staticmethod
    def norm_key(val: Any) -> str:
        return " ".join(str(val or "").strip().lower().split())

    def resolve_ethnicity(
        self,
        *,
        dna_ethnicity: str | None = None,
        country_name: str | None = None,
        country_code: str | None = None,
    ) -> str:
        # 1. Existing DNA profile ethnicity
        if dna_ethnicity:
            norm_dna = self.norm_key(dna_ethnicity)
            if norm_dna in VALID_ETHNICITIES:
                return VALID_ETHNICITIES[norm_dna]

        # 2. Country name mapping
        if country_name:
            parts = [p.strip().lower() for p in country_name.split("/")]
            for part in parts:
                if part in NATION_TO_ETHNICITY:
                    return NATION_TO_ETHNICITY[part]
                for k, v in NATION_TO_ETHNICITY.items():
                    if k in part:
                        return v

        # 3. ISO Code mapping fallback
        if country_code:
            code = country_code.strip().upper()
            from app.services.regen_portrait_service import RegenPortraitService

            groups = RegenPortraitService._portrait_ethnicity_groups(code)
            if groups and self.norm_key(groups[0]) in VALID_ETHNICITIES:
                return VALID_ETHNICITIES[self.norm_key(groups[0])]

        return "Mixed"

    def select_face_asset(
        self,
        *,
        seed: str,
        ethnicity: str,
        hair_colour: str | None = None,
    ) -> dict[str, Any]:
        eth_k = self.norm_key(ethnicity)
        if eth_k not in self.by_eth:
            eth_k = "mixed"

        hair_k = self.norm_key(hair_colour)
        # Normalize compound hair colors (e.g. "dark brown / black" -> "dark brown")
        if "/" in hair_k:
            hair_k = hair_k.split("/")[0].strip()

        pool = self.by_eth_hair.get((eth_k, hair_k))
        if not pool:
            # Fallback to general ethnicity pool
            pool = self.by_eth.get(eth_k) or self.by_eth["mixed"]

        digest = hashlib.sha256(f"{seed}:{eth_k}:{hair_k}".encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % len(pool)
        return pool[index]

    def build_regen_portrait_payload(
        self,
        player_id: str,
        provider_external_id: str,
        dna_profile: dict[str, Any] | None = None,
        country_name: str | None = None,
        country_code: str | None = None,
    ) -> dict[str, Any] | None:
        if (
            provider_external_id in QUARANTINED_PROVIDER_IDS
            or player_id in QUARANTINED_PLAYER_IDS
        ):
            return None

        dna = dict(dna_profile or {})
        ethnicity = self.resolve_ethnicity(
            dna_ethnicity=dna.get("ethnicity"),
            country_name=country_name,
            country_code=country_code,
        )
        hair_colour = dna.get("hairColour") or dna.get("hair_colour") or "Dark Brown"
        seed = dna.get("faceSeed") or f"fm23-{provider_external_id or player_id}"

        asset = self.select_face_asset(
            seed=seed,
            ethnicity=ethnicity,
            hair_colour=hair_colour,
        )

        portrait_url = asset["cloudinary_secure_url"]
        storage_key = asset["storage_key"]

        updated_dna = {
            **dna,
            "faceSeed": seed,
            "portraitUrl": portrait_url,
            "portraitStatus": "ready_newgen_face_bank",
            "portraitStorageKey": storage_key,
            "portraitEthnicity": asset["ethnicity"],
            "portraitSourceProvider": "gtex_regen_newgen_face_bank",
            "portraitSourceCollection": "script_skin_tone_hair_colour",
            "portraitRecipeVersion": "gtex_regen_portrait_assignment_v4",
            "portraitGeneratedAt": "2026-11-01T21:00:00+00:00",
            "ethnicity": asset["ethnicity"],
            "hairColour": asset["hair_colour"],
        }

        image_metadata = {
            "source_provider": "gtex_regen_newgen_face_bank",
            "provider_external_id": f"gtex_regen_newgen_face_bank:{player_id}",
            "player_id": player_id,
            "image_role": "portrait",
            "source_url": portrait_url,
            "storage_key": storage_key,
            "width": asset.get("width") or 250,
            "height": asset.get("height") or 250,
            "mime_type": "image/png",
            "file_size_bytes": asset.get("bytes"),
            "checksum_sha256": asset.get("sha256") or "",
            "moderation_status": "approved",
            "rights_cleared": True,
            "is_primary": True,
        }

        player_face = {
            "player_id": player_id,
            "avatar_seed": seed,
            "facial_features": {
                "ethnicity": asset["ethnicity"],
                "hair_colour": asset["hair_colour"],
                "storage_key": storage_key,
                "portrait_url": portrait_url,
                "source_provider": "gtex_regen_newgen_face_bank",
            },
            "hairstyle": asset.get("hair_colour"),
            "skin_tone": asset.get("ethnicity"),
            "accessories": [],
        }

        return {
            "player_id": player_id,
            "dna_profile": updated_dna,
            "image_metadata": image_metadata,
            "player_face": player_face,
            "asset": asset,
        }
