from __future__ import annotations

from pathlib import Path
import argparse
import os
import re
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SEVERITY_PATTERN = re.compile(r"^\s*(error|warning|info)\s+[-\u2022]\s+", re.IGNORECASE)
SUCCESS_MARKERS = ("No issues found!", "issues found.")
DEFAULT_ANALYZER_TIMEOUT_SECONDS = 600
DEFAULT_STATIC_TARGETS = (
    "lib/main.dart",
    "lib/app",
    "lib/controllers",
    "lib/core",
    "lib/domain",
    "lib/legacy",
    "lib/models",
    "lib/navigation",
    "lib/providers",
    "lib/router",
    "lib/services",
    "lib/shared",
    "lib/theme",
    "lib/ui_gtex",
    "lib/widgets",
)
DEFAULT_SPLIT_DIRS = (
    "lib/data",
    "lib/features",
    "lib/screens",
    "test",
)
DEFAULT_CHILD_CHUNK_SIZE = 6


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Dart/Flutter analysis with hard-error counting and a process-tree timeout.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional files or directories to pass to flutter analyze.",
    )
    return parser.parse_args()


def analyzer_command(targets: list[str]) -> tuple[list[str] | str, bool]:
    dart_executable = shutil.which("dart") or shutil.which("dart.bat")
    if dart_executable is not None:
        return [dart_executable, "analyze", *targets], False
    flutter_executable = shutil.which("flutter") or shutil.which("flutter.bat")
    if flutter_executable is not None:
        return [flutter_executable, "analyze", "--no-pub", *targets], False
    if os.name == "nt":
        return subprocess.list2cmdline(["flutter", "analyze", "--no-pub", *targets]), True
    return ["flutter", "analyze", "--no-pub", *targets], False


def analyzer_timeout_seconds() -> int:
    raw_value = os.getenv("ANALYZER_TIMEOUT_SECONDS", str(DEFAULT_ANALYZER_TIMEOUT_SECONDS))
    try:
        return int(raw_value)
    except ValueError:
        sys.stderr.write("[analyzer-gate] ANALYZER_TIMEOUT_SECONDS must be an integer, " f"got {raw_value!r}.\n")
        return DEFAULT_ANALYZER_TIMEOUT_SECONDS


def default_target_chunks() -> list[list[str]]:
    chunks: list[list[str]] = [[target] for target in DEFAULT_STATIC_TARGETS if (ROOT / target).exists()]
    for directory in DEFAULT_SPLIT_DIRS:
        path = ROOT / directory
        if not path.exists():
            continue
        root_files = sorted(child.relative_to(ROOT).as_posix() for child in path.glob("*.dart"))
        if root_files:
            chunks.append(root_files)
        children = sorted(
            child.relative_to(ROOT).as_posix()
            for child in path.iterdir()
            if child.is_dir() and child.name != "generated"
        )
        if children:
            chunks.extend(
                children[index : index + DEFAULT_CHILD_CHUNK_SIZE]
                for index in range(0, len(children), DEFAULT_CHILD_CHUNK_SIZE)
            )
        else:
            chunks.append([directory])
    return [chunk for chunk in chunks if chunk]


def kill_process_tree(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        process.kill()


def run_analyzer(
    command: list[str] | str,
    *,
    shell: bool,
    timeout_seconds: int,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    kwargs: dict[str, object] = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=shell,
        **kwargs,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

    return (
        subprocess.CompletedProcess(
            args=command,
            returncode=124 if timed_out else process.returncode,
            stdout=stdout or "",
            stderr=stderr or "",
        ),
        timed_out,
    )


def main() -> int:
    configure_output_encoding()
    args = parse_args()
    timeout_seconds = analyzer_timeout_seconds()
    target_chunks = [args.targets] if args.targets else default_target_chunks()

    total_counts = {"error": 0, "warning": 0, "info": 0}
    for index, targets in enumerate(target_chunks, start=1):
        command, shell = analyzer_command(targets)
        if not args.targets:
            sys.stdout.write("[analyzer-gate] " f"chunk {index}/{len(target_chunks)}: {', '.join(targets)}\n")
            sys.stdout.flush()
        for attempt in range(1, 3):
            completed, timed_out = run_analyzer(command, shell=shell, timeout_seconds=timeout_seconds)
            if timed_out:
                sys.stdout.write(f"{completed.stdout}{completed.stderr}")
                sys.stdout.write(
                    "\n[analyzer-gate] timed out after "
                    f"{timeout_seconds}s while analyzing {', '.join(targets)}; "
                    "killed analyzer process tree and treated the instability "
                    "as a hard failure.\n"
                )
                return 124

            output = f"{completed.stdout}{completed.stderr}"
            if output:
                sys.stdout.write(output)

            chunk_counts = {"error": 0, "warning": 0, "info": 0}
            for line in output.splitlines():
                match = SEVERITY_PATTERN.match(line)
                if match is not None:
                    severity = match.group(1).lower()
                    chunk_counts[severity] += 1

            analyzer_completed = any(marker in output for marker in SUCCESS_MARKERS)
            if chunk_counts["error"] > 0:
                for severity, count in chunk_counts.items():
                    total_counts[severity] += count
                sys.stdout.write(
                    "\n[analyzer-gate] "
                    f"errors={total_counts['error']} warnings={total_counts['warning']} "
                    f"info={total_counts['info']}\n"
                )
                return 1
            if completed.returncode == 0 or (completed.returncode == 1 and analyzer_completed):
                for severity, count in chunk_counts.items():
                    total_counts[severity] += count
                break
            if attempt == 1 and not analyzer_completed:
                sys.stdout.write(
                    "[analyzer-gate] analyzer returned "
                    f"{completed.returncode} without a completion marker; retrying "
                    f"{', '.join(targets)} once.\n"
                )
                sys.stdout.flush()
                continue
            sys.stdout.write(
                "[analyzer-gate] analyzer exited with "
                f"{completed.returncode} while analyzing {', '.join(targets)}.\n"
            )
            return completed.returncode or 1

    sys.stdout.write(
        "\n[analyzer-gate] "
        f"errors={total_counts['error']} warnings={total_counts['warning']} "
        f"info={total_counts['info']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
