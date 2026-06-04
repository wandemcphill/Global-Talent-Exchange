from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

PRODUCTION_MATCH_CODE = (
    "backend/app/live_matches",
    "backend/app/broadcast_network",
)

QUARANTINE_POLICY_MODULE = "backend/app/live_matches/generated_stream_policy.py"
SYNTHETIC_BOOTSTRAP_CALL = "start_synthetic_stream"
APPROVED_SYNTHETIC_BOOTSTRAP_HELPERS = {
    "_bootstrap_infinite_league_stream",
}
QUARANTINE_POLICY_HELPERS = {
    "generated_live_match_streams_enabled",
    "synthetic_match_presentation_enabled",
}
GENERATED_STREAM_FLAG_NAME_FRAGMENTS = (
    "ENABLE_GENERATED",
    "ENABLE_SYNTHETIC",
)
PUBLIC_ROUTE_DECORATOR_METHODS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "websocket",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path.relative_to(REPO_ROOT).as_posix()}:{self.line}: {self.message}"


def _python_files(paths: tuple[str, ...]) -> tuple[Path, ...]:
    files: list[Path] = []
    for raw_path in paths:
        path = REPO_ROOT / raw_path
        candidates = (path,) if path.is_file() else path.rglob("*.py")
        files.extend(candidate for candidate in candidates if candidate.is_file())
    return tuple(sorted(files))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _function_calls(function: ast.AST) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name is not None:
                calls.add(name)
    return calls


def _has_public_route_decorator(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in function.decorator_list:
        call_name = _call_name(decorator)
        if call_name in PUBLIC_ROUTE_DECORATOR_METHODS:
            return True
    return False


def _enclosing_function_name(tree: ast.Module, target: ast.AST) -> str | None:
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(node is target for node in ast.walk(function)):
            return function.name
    return None


def test_generated_match_streams_are_quarantined_by_named_policy_flags() -> None:
    policy_text = (REPO_ROOT / QUARANTINE_POLICY_MODULE).read_text(encoding="utf-8")
    missing_flags = [
        fragment for fragment in GENERATED_STREAM_FLAG_NAME_FRAGMENTS if fragment not in policy_text
    ]

    assert not missing_flags, (
        f"{QUARANTINE_POLICY_MODULE} must expose a clearly named generated/synthetic "
        f"policy flag. Missing fragments: {', '.join(missing_flags)}"
    )

    findings: list[Finding] = []
    for path in _python_files(PRODUCTION_MATCH_CODE):
        tree = _parse(path)
        function_calls = {
            node.name: _function_calls(node)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node.func) != SYNTHETIC_BOOTSTRAP_CALL:
                continue
            helper_name = _enclosing_function_name(tree, node)
            if helper_name in APPROVED_SYNTHETIC_BOOTSTRAP_HELPERS:
                helper_calls = function_calls.get(helper_name, set())
                if helper_calls & QUARANTINE_POLICY_HELPERS:
                    continue
                findings.append(
                    Finding(
                        path=path,
                        line=node.lineno,
                        message=(
                            f"{helper_name} starts synthetic streams without a generated/synthetic "
                            "quarantine policy helper"
                        ),
                    )
                )
                continue
            findings.append(
                Finding(
                    path=path,
                    line=node.lineno,
                    message=(
                        "start_synthetic_stream must be reached only through an approved "
                        "quarantine/internal bootstrap helper"
                    ),
                )
            )

    assert not findings, "\n".join(finding.format() for finding in findings)


def test_public_match_routes_do_not_start_synthetic_streams_directly() -> None:
    findings: list[Finding] = []
    for path in _python_files(PRODUCTION_MATCH_CODE):
        tree = _parse(path)
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not _has_public_route_decorator(function):
                continue
            calls = _function_calls(function)
            if SYNTHETIC_BOOTSTRAP_CALL in calls:
                findings.append(
                    Finding(
                        path=path,
                        line=function.lineno,
                        message=(
                            f"public route {function.name} calls start_synthetic_stream directly; "
                            "use the quarantine/internal bootstrap helper"
                        ),
                    )
                )

    assert not findings, "\n".join(finding.format() for finding in findings)
