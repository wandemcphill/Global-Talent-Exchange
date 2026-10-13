"""Convert a read-only FM23 Genie Scout CSV into the GTEX bulk-import manifest."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from app.ingestion.fm23_genie_scout import (
    DEFAULT_SNAPSHOT_AT,
    FM23_GENIE_SCOUT_PROVIDER,
    write_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="Semicolon-delimited Genie Scout CSV.")
    parser.add_argument("--output", required=True, help="Output JSON manifest path.")
    parser.add_argument("--snapshot-at", default=DEFAULT_SNAPSHOT_AT.isoformat(), help="ISO-8601 snapshot timestamp.")
    parser.add_argument("--provider", default=FM23_GENIE_SCOUT_PROVIDER, help="Stable GTEX source provider key.")
    args = parser.parse_args(argv)
    snapshot_at = datetime.fromisoformat(args.snapshot_at.replace("Z", "+00:00"))
    manifest = write_manifest(args.file, args.output, snapshot_at=snapshot_at, provider_name=args.provider)
    print({"output": str(Path(args.output).resolve()), "source_row_count": manifest["source_row_count"], "source_sha256": manifest["source_sha256"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
