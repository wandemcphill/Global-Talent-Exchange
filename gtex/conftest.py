from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

for candidate in (PROJECT_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

collect_ignore_glob = [
    ".pytest*",
    ".tmp*",
    "backend/.pytest*",
    "backend/.tmp*",
    "backend/.tmp_testdirs/*",
    "tmp/*",
]
