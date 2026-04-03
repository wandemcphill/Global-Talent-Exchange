from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
NULL_SHA = "0" * 40
SECRET_BASELINE_PATH = REPO_ROOT / ".secrets.baseline"
PYTHON_EXTENSIONS = {".py"}
JAVASCRIPT_EXTENSIONS = {".js", ".mjs", ".cjs"}
SECRET_SCAN_EXTENSIONS = {
    ".bat",
    ".cjs",
    ".cmd",
    ".conf",
    ".css",
    ".dart",
    ".env",
    ".go",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".md",
    ".mjs",
    ".php",
    ".properties",
    ".ps1",
    ".py",
    ".rb",
    ".scala",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_SCAN_FILENAMES = {
    "dockerfile",
    "docker-compose.yml",
}
UNTRACKED_SKIP_PREFIXES = (
    ".tmp",
    "tmp/",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repo quality gates against changed files.",
    )
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Base git ref or SHA. Defaults to HEAD for local working tree checks.",
    )
    parser.add_argument(
        "--head",
        default=None,
        help="Optional head git ref or SHA. When omitted, compares the working tree to --base.",
    )
    return parser.parse_args()


def git_stdout(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def changed_files(base: str, head: str | None) -> list[str]:
    files: set[str] = set()
    if head:
        if base == NULL_SHA:
            files.update(git_stdout("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", head))
        else:
            files.update(git_stdout("diff", "--name-only", "--diff-filter=ACMRT", f"{base}..{head}"))
        return sorted(files)

    files.update(git_stdout("diff", "--name-only", "--diff-filter=ACMRT", base, "--"))
    files.update(
        path for path in git_stdout("ls-files", "--others", "--exclude-standard") if include_untracked_file(path)
    )
    return sorted(files)


def existing_files(paths: list[str]) -> list[str]:
    return [path for path in paths if (REPO_ROOT / path).is_file()]


def include_untracked_file(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return not normalized.startswith(UNTRACKED_SKIP_PREFIXES)


def select_files(paths: list[str], extensions: set[str]) -> list[str]:
    return [path for path in paths if Path(path).suffix.lower() in extensions]


def is_secret_scan_file(path: str) -> bool:
    file_path = Path(path)
    name = file_path.name.lower()
    if name in SECRET_SCAN_FILENAMES or name.startswith(".env"):
        return True
    return any(suffix.lower() in SECRET_SCAN_EXTENSIONS for suffix in file_path.suffixes)


def run_check(label: str, command: list[str], files: list[str]) -> None:
    if not files:
        print(f"[quality] Skipping {label}: no matching files changed.")
        return

    full_command = [*command, *files]
    print(f"[quality] Running {label}")
    print(f"[quality] $ {shlex.join(full_command)}")
    subprocess.run(full_command, cwd=REPO_ROOT, check=True)


def main() -> int:
    args = parse_args()
    files = existing_files(changed_files(args.base, args.head))

    if not files:
        print("[quality] No changed tracked files detected.")
        return 0

    python_files = select_files(files, PYTHON_EXTENSIONS)
    javascript_files = select_files(files, JAVASCRIPT_EXTENSIONS)
    secret_scan_files = [path for path in files if is_secret_scan_file(path)]

    run_check(
        "Python format check",
        [sys.executable, "-m", "black", "--check"],
        python_files,
    )
    run_check(
        "Python lint",
        [sys.executable, "-m", "ruff", "check"],
        python_files,
    )
    run_check(
        "JavaScript format check",
        ["npm", "exec", "--", "prettier", "--check"],
        javascript_files,
    )
    run_check(
        "JavaScript lint",
        ["npm", "exec", "--", "eslint", "--max-warnings=0"],
        javascript_files,
    )
    secret_scan_command = [sys.executable, "-m", "detect_secrets.pre_commit_hook", "--no-verify"]
    if SECRET_BASELINE_PATH.is_file():
        secret_scan_command.extend(["--baseline", str(SECRET_BASELINE_PATH)])
    run_check(
        "Secret scan",
        secret_scan_command,
        secret_scan_files,
    )

    print("[quality] All configured quality gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
