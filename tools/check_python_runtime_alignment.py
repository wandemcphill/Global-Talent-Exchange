from __future__ import annotations

from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PYTHON = "3.14"
WORKFLOW_FILES = (
    Path(".github/workflows/ci-staging.yml"),
    Path(".github/workflows/deploy-production.yml"),
    Path(".github/workflows/dependency-scan.yml"),
    Path(".github/workflows/quality-gates.yml"),
)
DOCKERFILES = (
    Path("Dockerfile"),
    Path("infra/api/Dockerfile"),
    Path("infra/workers/Dockerfile"),
)
DOC_REQUIREMENTS = {
    Path("README.md"): "Python 3.14",
    Path("docs/RUNBOOK_LOCAL_DEV.md"): "Supported Python runtime: `Python 3.14`",
    Path("DEPLOYMENT_GUIDE.md"): "Supported GTEX application runtime: Python 3.14",
}


def _read(path: Path) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _check_python_version_file(errors: list[str]) -> None:
    configured = _read(Path(".python-version")).strip()
    if configured != SUPPORTED_PYTHON:
        errors.append(f".python-version must be {SUPPORTED_PYTHON}, found {configured!r}.")


def _check_workflows(errors: list[str]) -> None:
    pattern = re.compile(r'python-version:\s*"([^"]+)"')
    for relative_path in WORKFLOW_FILES:
        versions = pattern.findall(_read(relative_path))
        if not versions:
            errors.append(f"{relative_path} does not declare any python-version entries.")
            continue
        if any(version != SUPPORTED_PYTHON for version in versions):
            errors.append(f"{relative_path} must use python-version {SUPPORTED_PYTHON} everywhere, found {versions!r}.")


def _check_dockerfiles(errors: list[str]) -> None:
    pattern = re.compile(r"^FROM\s+python:([0-9.]+)-slim\s*$", re.MULTILINE)
    for relative_path in DOCKERFILES:
        versions = pattern.findall(_read(relative_path))
        if not versions:
            errors.append(f"{relative_path} does not declare a python slim base image.")
            continue
        if any(version != SUPPORTED_PYTHON for version in versions):
            errors.append(f"{relative_path} must use python:{SUPPORTED_PYTHON}-slim, found {versions!r}.")


def _check_docs(errors: list[str]) -> None:
    for relative_path, required_text in DOC_REQUIREMENTS.items():
        if required_text not in _read(relative_path):
            errors.append(f"{relative_path} must mention {required_text!r}.")


def main() -> int:
    errors: list[str] = []
    _check_python_version_file(errors)
    _check_workflows(errors)
    _check_dockerfiles(errors)
    _check_docs(errors)

    if errors:
        for error in errors:
            print(f"[python-runtime] {error}")
        return 1

    print(f"[python-runtime] All checked runtime surfaces are pinned to Python {SUPPORTED_PYTHON}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
