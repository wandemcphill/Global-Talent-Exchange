"""Clear stale Flutter native-asset test output before test/analyze runs."""

from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
    frontend_root = Path(__file__).resolve().parents[1]
    for relative_path in (
        Path("build") / "unit_test_assets",
        Path("build") / "native_assets",
    ):
        target = frontend_root / relative_path
        shutil.rmtree(target, ignore_errors=True)
        print(f"cleared {relative_path.as_posix()}")


if __name__ == "__main__":
    main()
