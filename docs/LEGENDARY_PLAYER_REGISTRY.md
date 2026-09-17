# GTEX Foundational Legendary Player Registry

## Overview

The Foundational Legendary Player Registry serves as the authoritative source-of-truth definition layer for historical and legendary footballers (~2,000 launch targets) within the GTEX platform.

Crucially, legendary players are **not** a separate type of marketplace asset, nor do they introduce a secondary economy or parallel player lifecycle. Instead, `LegendaryPlayerProfile` acts as the seed specification layer from which canonical GTEX `Player` (`ingestion_players`) records are instantiated.

Once instantiated, legendary players participate directly in all existing GTEX systems:
- Real Player universe & market listings (`PlayerShareMarket`, `PlayerCard`)
- Squad registration and tier assignments (`ClubSquadTierMembership`)
- National team eligibility and competition rules (`NationalTeamSquadMember`, `NationalTeamRentalSquadMember`)
- Replay engines and match simulations

---

## Architecture

```
+------------------------------------+
|     LegendaryPlayerProfile         |
|  (backend/app/models/legendary.py) |
| - Stable Slug (e.g. legend-pel-10) |
| - Full Historical Name             |
| - GTEX Nationality                 |
| - Position & Secondary Positions   |
| - Preferred Foot                   |
| - Historical & GTEX Height (-1/0/+1)|
| - Technical/Physical/Mental Profile|
| - Signature Traits & Role          |
| - Era & Legendary Classification   |
| - Portrait Generation Metadata     |
+------------------------------------+
                  |
                  |  instantiate_gtex_player()
                  v
+------------------------------------+
|         ingestion_players          |
|       (app.ingestion.models.Player)|
| - legendary_profile_id (FK)        |
| - source_provider="gtex_legend"    |
| - provider_external_id="legend:..."|
| - is_real_player=True              |
| - dna_profile (traits, profiles)   |
+------------------------------------+
                  |
        +---------+---------+
        |                   |
        v                   v
+---------------+   +---------------+
| PlayerShareMkt|   |  PlayerCard   |
+---------------+   +---------------+
```

### Key Integration Principles

1. **Full Historical Name**: The registry stores and projects the full canonical name (e.g., "Pelé", "Diego Maradona", "Johan Cruyff").
2. **Single GTEX Nationality**: Each profile carries exactly one authoritative GTEX country code. Nationality switching is strictly prohibited.
3. **GTEX Height Generation**: GTEX height (`gtex_height_cm`) is calculated using exactly `-1`, `0`, or `+1` cm relative to historical height (`historical_height_cm`). The calculation uses a deterministic RNG seeded by the profile's immutable `slug`.
4. **Non-Replicative Fictional Portraits**: The registry does not store or process real-person facial likenesses. It generates visual avatar metadata (`gtex_fictional_avatar_v1`) compatible with GTEX avatar renderers, ensuring visual distinction while respecting nationality and appearance parameters.
5. **Idempotency**: All seed and import operations (upserts, bulk imports, player instantiations) are replay-safe and idempotent.

---

## Data Schema

### `legendary_player_profiles` Table

| Column | Type | Constraints / Description |
|---|---|---|
| `id` | VARCHAR(36) | Primary Key (UUID) |
| `slug` | VARCHAR(128) | UNIQUE, Index. Stable unique identifier (e.g., `legend-pel-10`) |
| `full_name` | VARCHAR(160) | Full historical player name |
| `country_code` | VARCHAR(8) | GTEX country alpha code (e.g. `BRA`, `ARG`, `NLD`) |
| `primary_position` | VARCHAR(40) | Primary position (`ST`, `CAM`, `CB`, `GK`, etc.) |
| `secondary_positions_json` | JSON | List of secondary positions (e.g. `["CF", "LW"]`) |
| `preferred_foot` | VARCHAR(16) | `left`, `right`, or `both` |
| `historical_height_cm` | INTEGER | Reference historical height |
| `gtex_height_cm` | INTEGER | Generated GTEX height (`historical_height_cm` ± 1 cm) |
| `signature_traits_json` | JSON | List of signature football traits |
| `signature_role` | VARCHAR(80) | Signature tendency or tactical role |
| `technical_profile_json` | JSON | Technical attribute map |
| `physical_profile_json` | JSON | Physical attribute map |
| `mental_profile_json` | JSON | Mental / decision tendency map |
| `era` | VARCHAR(64) | Historical era (e.g., `1970s`, `1986-1994`) |
| `legendary_classification` | VARCHAR(40) | Classification (`icon`, `world_class`, `immortal`, `hero`) |
| `is_active` | BOOLEAN | Profile status |
| `is_searchable` | BOOLEAN | Searchability status |
| `is_tradable` | BOOLEAN | Tradability status |
| `is_rentable` | BOOLEAN | Rentability status |
| `is_national_team_eligible` | BOOLEAN | National team eligibility flag |
| `portrait_metadata_json` | JSON | Avatar metadata configuration |
| `source_notes` | TEXT | Historical research / reference notes |
| `metadata_json` | JSON | Extension metadata |

---

## Service Layer & Usage Contract

The service layer is implemented in `app.services.legendary_player_service.LegendaryPlayerRegistryService`.

### Python API Example

```python
from app.services.legendary_player_service import LegendaryPlayerRegistryService
from app.schemas.legendary_player import LegendaryPlayerProfileCreate, LegendarySeedImportRequest, LegendarySeedImportItem

service = LegendaryPlayerRegistryService(db_session)

# 1. Upsert a single legendary profile
profile_in = LegendaryPlayerProfileCreate(
    slug="legend-pele-10",
    full_name="Edson Arantes do Nascimento (Pelé)",
    country_code="BRA",
    primary_position="ST",
    secondary_positions=["CAM", "CF"],
    preferred_foot="right",
    historical_height_cm=173,
    signature_traits=["Bicycle Kick", "Acrobatic Finishing", "Master Dribbler"],
    signature_role="Attacking Free Role",
    technical_profile={"finishing": 99, "dribbling": 97, "passing": 92},
    physical_profile={"pace": 93, "acceleration": 95, "stamina": 90},
    mental_profile={"vision": 96, "composure": 98, "flair": 99},
    era="1958-1970",
    legendary_classification="immortal",
)

profile, created = service.upsert_legendary_profile(profile_in)

# 2. Instantiate into an ordinary GTEX player
player = service.instantiate_gtex_player(profile)

# 3. Bulk Seed / Import Contract (Idempotent)
import_req = LegendarySeedImportRequest(
    profiles=[
        LegendarySeedImportItem(
            slug="legend-maradona-10",
            full_name="Diego Armando Maradona",
            country_code="ARG",
            primary_position="CAM",
            secondary_positions=["ST"],
            preferred_foot="left",
            historical_height_cm=165,
            era="1982-1990",
            legendary_classification="immortal",
            instantiate_gtex_player=True,
        )
    ],
    instantiate_all=True
)

result = service.bulk_import(import_req)
print(f"Processed: {result.processed_count}, Created: {result.created_count}, Instantiated: {result.instantiated_player_count}")
```
