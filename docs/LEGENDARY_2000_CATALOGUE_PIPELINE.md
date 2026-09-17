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

The source command refuses to pretend there are 2,000 records when fewer unique candidates are available.

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

Duplicate source IDs and incomplete records block release.

## Production import

`backend/scripts/import_approved_legendary_catalogue.py` is dry-run by default. Activation requires an explicit admin actor ID. It refuses to import a bundle that fails the release gate.

Activation uses `LegendaryPlayerLaunchService` and therefore follows the canonical lifecycle:

`approved catalogue record -> LegendaryPlayerProfile -> ordinary GTEX Player -> active PlayerShareMarket`

The importer does not create a separate legendary economy and does not use the disabled ingestion compatibility issuer.

## Important boundary

The generated staging bundle is not a production seed. The 2,000 target is a release gate, not a license to invent facts. A candidate stays blocked until editorial enrichment and approvals are complete.
