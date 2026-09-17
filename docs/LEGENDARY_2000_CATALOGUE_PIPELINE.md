# GTEX 2,000 Legendary Player Catalogue Pipeline

## Objective

Build a launch catalogue of exactly 2,000 legendary historical footballers without fabricating missing facts. A record is not a launch record merely because a name exists in a source dataset.

The pipeline is deliberately split into four stages:

1. **Sourcing**: collect candidate identity facts and provenance from Wikidata.
2. **Football enrichment**: editorially establish one GTEX nationality, primary/secondary positions, preferred foot, historical height, era, signature traits, role, and technical/physical/mental profiles.
3. **Editorial and rights approval**: approve the football identity, confirm the record is appropriate for GTEX, and approve a fictional non-replicative portrait configuration. No source portrait is used as the GTEX portrait.
4. **Launch import**: materialize approved records through the canonical `LegendaryPlayerLaunchService`, which creates the ordinary GTEX Player and the normal active player-share market using the strict issuer.

## Candidate sourcing

`backend/scripts/build_legendary_catalogue_staging.py` queries the Wikidata SPARQL service and writes a JSON staging bundle. Wikidata exposes association-football player properties including occupation, country for sport, date of birth, height, position, image and footedness. The GTEX harvester records the source item and evidence URL, but it does not convert incomplete source data into fictional certainty.

Candidate selection is deterministic and country-diverse. The default selection cap is 35 records per country bucket, with known-country records preferred over unknown-country records and more complete source coverage preferred within the same bucket. Duplicate source IDs are removed before the target-count decision.

The source command refuses to pretend there are 2,000 records when fewer diverse candidates are available. The target is a release gate, not a license to invent names or football facts.

## Batch enrichment

`backend/scripts/apply_legendary_catalogue_enrichment.py` applies an explicit enrichment overlay to a staging bundle. The overlay is keyed by `source_id` and may only change fields explicitly supplied by the editorial/research pass.

This keeps the source harvester factual and reproducible while allowing separate batches to establish GTEX football attributes, nationality decisions, traits, role, and approval state. An enrichment patch referencing an unknown source ID fails instead of creating an orphan record.

Example shape:

```json
{
  "schema_version": "legendary-enrichment-v1",
  "generated_at": "2026-09-17T00:00:00Z",
  "patches": [
    {
      "source_id": "wikidata:Q123",
      "country_code": "NGA",
      "primary_position": "ST",
      "preferred_foot": "right",
      "signature_traits": ["composure", "link-up play"],
      "signature_role": "Complete Forward",
      "technical_profile": {"finishing": 91, "first_touch": 93},
      "physical_profile": {"strength": 82, "stamina": 72},
      "mental_profile": {"composure": 96, "vision": 90},
      "football_evidence": [
        {
          "provider": "editorial_review",
          "uri": "https://example.invalid/research-record",
          "claim_types": ["position", "footedness", "traits"]
        }
      ],
      "editorial_status": "approved",
      "rights_status": "approved",
      "portrait_metadata": {
        "avatar_system": "gtex_fictional_avatar_v1",
        "is_fictional_non_replicative": true
      }
    }
  ]
}
```

The example is a schema illustration only. It is not a production factual record.

## Release gate

`backend/scripts/validate_legendary_catalogue.py` is the release gate. Exactly 2,000 records are required for the launch bundle unless a smaller target is explicitly being used for test work.

Every launch record must have:

- one GTEX nationality
- date of birth
- historical height
- primary position
- preferred foot
- era
- legendary classification
- signature traits
- technical, physical and mental profiles
- source evidence
- football evidence
- editorial approval
- rights approval
- approved fictional non-replicative portrait metadata

Duplicate source IDs, incomplete records, unapproved records, and source-photo references in portrait metadata block release.

## Production import

`backend/scripts/import_approved_legendary_catalogue.py` is dry-run by default. Activation requires an explicit `ADMIN` or `SUPER_ADMIN` actor ID. It refuses to import a bundle that fails the release gate.

Activation uses `LegendaryPlayerLaunchService` and therefore follows the canonical lifecycle:

`approved catalogue record -> LegendaryPlayerProfile -> ordinary GTEX Player -> active PlayerShareMarket`

The importer does not create a separate legendary economy and does not use the disabled ingestion compatibility issuer. Activation is transactional: any import error causes the surrounding transaction to roll back rather than leaving a partially launched catalogue. Production activation also requires every referenced country to already exist in the canonical GTEX country table.

## Important boundary

The generated staging bundle is not a production seed. Every candidate remains blocked until the required football attributes, editorial approval, rights approval, and fictional portrait configuration exist. The 2,000 target is a release gate, not a license to invent facts.
