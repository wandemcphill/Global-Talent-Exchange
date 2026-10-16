from __future__ import annotations

from pathlib import Path
import sys

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
SCRIPT_DIR_STR = str(SCRIPT_DIR)
if SCRIPT_DIR_STR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR_STR)

from real_player_import_from_2nd_zip import main


if __name__ == "__main__":
    raise SystemExit(main(["report", *sys.argv[1:]]))
