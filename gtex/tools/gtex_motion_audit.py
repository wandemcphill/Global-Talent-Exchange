from __future__ import annotations

"""Static/runtime-independent guardrails for the authoritative spatial layer."""

from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend" / "app" / "services" / "authoritative_spatial_simulation.py"


def main() -> None:
    tree = ast.parse(TARGET.read_text(encoding="utf-8"))
    source = TARGET.read_text(encoding="utf-8")
    forbidden = (
        "sin((time_seconds * 0.55)",
        "cos((time_seconds * 0.47)",
    )
    for token in forbidden:
        if token in source:
            raise SystemExit(f"artificial always-on player motion remains: {token}")
    if not any(isinstance(node, ast.FunctionDef) and node.name == "_player_position" for node in tree.body):
        raise SystemExit("authoritative player position function missing")
    print("GTEX motion audit: PASS")


if __name__ == "__main__":
    main()
