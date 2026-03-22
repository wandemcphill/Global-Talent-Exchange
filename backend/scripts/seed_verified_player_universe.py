from __future__ import annotations

from pathlib import Path
import runpy
import sys


if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.append(str(backend_root))
    entrypoint = backend_root / "app" / "scripts" / "seed_players.py"
    namespace = runpy.run_path(str(entrypoint))
    namespace["main"]()
