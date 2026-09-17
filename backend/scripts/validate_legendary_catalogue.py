from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.legend_catalogue.schema import CatalogueBundle
from app.legend_catalogue.validation import evaluate_release


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a GTEX legendary catalogue release bundle.")
    parser.add_argument("path")
    parser.add_argument("--target-count", type=int)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    bundle = CatalogueBundle.model_validate_json(Path(args.path).read_text(encoding="utf-8"))
    result = evaluate_release(bundle, target_count=args.target_count)
    print(result.model_dump_json(indent=2))
    return 0 if result.ready or not args.require_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
