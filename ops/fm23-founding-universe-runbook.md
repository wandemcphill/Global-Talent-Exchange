# FM23 Founding Universe Import

The GTEX founding-universe path treats an FM23 basic export as a **one-time game-data snapshot**, not as an authoritative real-world player feed.

## Input contract

The converter accepts the FM23 basic semicolon-delimited export with these columns, in this order:

- `Name`
- `Nation`
- `Position`
- `Club`
- `Age`
- `Wage`
- `Value`
- `Sale Value`
- `Best Rating`
- `Best Pot Rating`

The converter records the SHA-256 fingerprint of the original file and supports the UTF-8/CP1252 text commonly produced by the export.

## Safety boundary

The converter deliberately **does not** promote these FM fields into canonical GTEX factual fields:

- FM age is stored as `source_metadata.fm23_age`, not `age`.
- FM `Value` is stored as `source_metadata.fm23_value`, not `current_market_reference_value`.
- FM `Sale Value` is stored as `source_metadata.fm23_sale_value`.
- FM rating/potential strings are stored under `source_metadata`.
- FM club and league are not promoted into `current_real_world_club` / `current_real_world_league`, because the supplied custom universe uses historical career contexts.
- Preferred foot, height, DOB, league and any other missing facts are not invented.
- Rows are marked `is_verified_real_player=false` at this stage.

A successfully staged FM batch is therefore **not automatically publish-ready**. Authoritative real-world enrichment and pricing must still satisfy the normal GTEX publish gates.

## Identity policy

The export contains no stable player UID. GTEX creates a deterministic provisional source key from `Name + Nation + Position + Club + FM Age`.

Exact duplicate rows collapse to one record. If two non-identical rows share that same provisional identity tuple, the converter fails closed rather than guessing.

## Convert

```bash
python backend/scripts/convert_fm23_founding_universe.py \
  --input <path>/GTEX_Founding_Universe_v0_basic.csv \
  --output <path>/GTEX_FM23_Founding_Universe_v0.staging.jsonl \
  --report <path>/GTEX_FM23_Founding_Universe_v0.report.json
```

The resulting JSONL can then enter the existing staged bulk path:

```bash
python backend/scripts/import_real_players_bulk.py \
  --file <path>/GTEX_FM23_Founding_Universe_v0.staging.jsonl \
  --provider football_manager \
  --batch-size 1000 \
  --database-url $GTE_DATABASE_URL
```

Staging must be inspected before publication. FM game values must never be treated as authoritative transfer-market values.

## Supplied snapshot audit

The supplied `GTEX_Founding_Universe_v0_basic.csv` was converted locally during engineering validation:

- 31,461 source rows
- 28,158 emitted unique rows
- 3,303 exact duplicate rows collapsed
- SHA-256: `5a27e8d221b17e589c60b1ecb444baa2db70db8aa45394155d5c60f1ce8e1032`

The source CSV itself is intentionally not committed to the public repository by this change.
