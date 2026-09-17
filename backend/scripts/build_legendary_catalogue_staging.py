from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.legend_catalogue.schema import CatalogueBundle
from app.legend_catalogue.wikidata_source import fetch_rows, rows_to_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a source-linked GTEX legendary candidate catalogue.")
    parser.add_argument("--output", default="backend/data/legendary_catalogue/legendary_catalogue_staging_v2.json")
    parser.add_argument("--target-count", type=int, default=2000)
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    args = parser.parse_args()

    rows = fetch_rows(page_size=args.page_size, max_pages=args.max_pages, pause_seconds=args.pause_seconds)
    candidates = rows_to_candidates(rows)
    if len(candidates) < args.target_count:
        raise SystemExit(
            f"Only {len(candidates)} unique Wikidata candidates were found; refusing to invent records for target {args.target_count}."
        )
    candidates = candidates[: args.target_count]
    bundle = CatalogueBundle(
        generated_at=datetime.now(timezone.utc),
        source="wikidata",
        target_count=args.target_count,
        records=candidates,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "records": len(bundle.records), "source_rows": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
