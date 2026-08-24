from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "issue_player_share_markets_strict.py"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source(), filename=str(SCRIPT))


def _call_names(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.append(node.func.attr)
    return names


def test_strict_issuer_is_valid_python() -> None:
    ast.parse(_source(), filename=str(SCRIPT))


def test_strict_issuer_uses_explicit_issue_market_path() -> None:
    names = _call_names(_tree())
    assert "issue_market" in names
    assert "ensure_market" not in names


def test_strict_issuer_requires_an_attributable_actor_for_activation() -> None:
    source = _source()
    assert '"--actor-user-id"' in source
    assert '"--activate"' in source
    assert 'if args.activate and not args.actor_user_id:' in source


def test_strict_issuer_is_dry_run_by_default() -> None:
    source = _source()
    assert '"dry_run": not args.activate or args.dry_run' in source
    assert 'session.rollback()' in source


def test_strict_issuer_records_runner_provenance() -> None:
    source = _source()
    assert '"issuance_runner": Path(__file__).name' in source
    assert '"bulk_issuance_policy": Path(args.policy_path).name' in source
