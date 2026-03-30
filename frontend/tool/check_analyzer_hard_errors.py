from __future__ import annotations

from pathlib import Path
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SEVERITY_PATTERN = re.compile(r"^\s*(error|warning|info)\s+[-•]\s+", re.IGNORECASE)
SUCCESS_MARKERS = ("No issues found!", "issues found.")


def main() -> int:
    flutter_executable = shutil.which("flutter") or shutil.which("flutter.bat")
    command: list[str] | str
    shell = False
    if flutter_executable is not None:
        command = [flutter_executable, "analyze", "--no-pub"]
    elif os.name == "nt":
        command = "flutter analyze --no-pub"
        shell = True
    else:
        command = ["flutter", "analyze", "--no-pub"]

    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=shell,
    )
    output = f"{completed.stdout}{completed.stderr}"
    if output:
        sys.stdout.write(output)

    counts = {"error": 0, "warning": 0, "info": 0}
    for line in output.splitlines():
        match = SEVERITY_PATTERN.match(line)
        if match is not None:
            counts[match.group(1).lower()] += 1

    analyzer_completed = any(marker in output for marker in SUCCESS_MARKERS)
    sys.stdout.write(
        "\n[analyzer-gate] "
        f"errors={counts['error']} warnings={counts['warning']} info={counts['info']}\n"
    )

    if counts["error"] > 0:
        return 1
    if completed.returncode == 0:
        return 0
    if completed.returncode == 1 and analyzer_completed:
        return 0
    return completed.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
