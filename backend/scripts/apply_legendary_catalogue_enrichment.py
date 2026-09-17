from __future__ import annotations

import argparse
from pathlib import Path

from app.legend_catalogue.enrichment import EnrichmentBundle, apply_enrichment
from app.legend_catalogue.schema import CatalogueBundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply explicit editorial/football enrichment to a GTEX legendary staging bundle."
    )
    parser.add_argument("bundle")
    parser.add_argument("patches")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    bundle = CatalogueBundle.model_validate_json(Path(args.bundle).read_text(encoding="utf-8"))
    patches = EnrichmentBundle.model_validate_json(Path(args.patches).read_text(encoding="utf-8"))
    enriched = apply_enrichment(bundle, patches)
    Path(args.output).write_text(enriched.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"Applied {len(patches.patches)} enrichment patches to {len(enriched.records)} catalogue records; output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
