from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar
import argparse
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = ("lib", "test")
EXCLUDED_PREFIXES = (
    ".dart_tool/",
    "build/",
    "lib/data/generated/",
)

LOCAL_DIRECTIVE_PATTERN = re.compile(
    r"^\s*(?:import|export)\s+['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)
PACKAGE_NAME_PATTERN = re.compile(r"^\s*name:\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)
FINAL_DECL_PATTERN = re.compile(r"\bfinal\b")
PROVIDER_NAME_BEFORE_EQUALS_PATTERN = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*Provider)\s*=$",
)
PROVIDER_ACCESS_PATTERN = re.compile(
    r"\b(?:ref|container|activeContainer)\.(?:watch|read|listen)" r"(?:<[^>()]+>)?\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
T = TypeVar("T")


@dataclass(frozen=True)
class ProviderBlock:
    name: str
    path: Path
    body: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit local Dart import cycles and Riverpod provider recursion "
            "before running the slower Flutter analyzer."
        ),
    )
    parser.add_argument(
        "roots",
        nargs="*",
        default=list(DEFAULT_SCAN_ROOTS),
        help="Dart source roots to scan, relative to the frontend folder.",
    )
    return parser.parse_args()


def package_name() -> str:
    pubspec = ROOT / "pubspec.yaml"
    if not pubspec.is_file():
        return ""
    match = PACKAGE_NAME_PATTERN.search(pubspec.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def normalized(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def is_excluded(path: Path) -> bool:
    relative = normalized(path)
    return any(relative.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def dart_files(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        root_path = ROOT / root
        if root_path.is_file() and root_path.suffix == ".dart":
            if not is_excluded(root_path):
                files.append(root_path)
            continue
        if not root_path.is_dir():
            continue
        for path in root_path.rglob("*.dart"):
            if not is_excluded(path):
                files.append(path)
    return sorted(set(files))


def resolve_directive(source: Path, uri: str, project_package: str) -> Path | None:
    if uri.startswith("dart:"):
        return None
    if uri.startswith("package:"):
        package_prefix = f"package:{project_package}/"
        if not project_package or not uri.startswith(package_prefix):
            return None
        return ROOT / "lib" / uri.removeprefix(package_prefix)
    if uri.endswith(".dart"):
        return source.parent / uri
    return None


def build_import_graph(files: list[Path], project_package: str) -> dict[str, set[str]]:
    file_keys = {path_key(path): normalized(path) for path in files}
    graph: dict[str, set[str]] = {normalized(path): set() for path in files}
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in LOCAL_DIRECTIVE_PATTERN.finditer(text):
            resolved = resolve_directive(path, match.group(1), project_package)
            if resolved is None:
                continue
            resolved_key = path_key(resolved)
            if resolved_key in file_keys:
                graph[normalized(path)].add(file_keys[resolved_key])
    return graph


def find_provider_blocks(files: list[Path]) -> list[ProviderBlock]:
    blocks: list[ProviderBlock] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, initializer_start in provider_declarations(text):
            body = initializer_body(text, initializer_start)
            if body is not None:
                blocks.append(
                    ProviderBlock(name=name, path=path, body=body),
                )
    return blocks


def provider_declarations(text: str) -> list[tuple[str, int]]:
    declarations: list[tuple[str, int]] = []
    for match in FINAL_DECL_PATTERN.finditer(text):
        window_end = min(len(text), match.start() + 320)
        equals_index = text.find("=", match.end(), window_end)
        if equals_index < 0:
            continue
        semicolon_index = text.find(";", match.end(), equals_index)
        if semicolon_index >= 0:
            continue
        declaration = text[match.start() : equals_index + 1]
        name_match = PROVIDER_NAME_BEFORE_EQUALS_PATTERN.search(declaration)
        if name_match is None:
            continue
        declarations.append((name_match.group(1), equals_index + 1))
    return declarations


def initializer_body(text: str, start: int) -> str | None:
    depth_paren = 0
    depth_brace = 0
    depth_bracket = 0
    quote: str | None = None
    escaped = False
    in_line_comment = False
    in_block_comment = False
    for index in range(start, len(text)):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
            continue
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "/" and next_char == "/":
            in_line_comment = True
            continue
        if char == "/" and next_char == "*":
            in_block_comment = True
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "(":
            depth_paren += 1
        elif char == ")":
            depth_paren = max(0, depth_paren - 1)
        elif char == "{":
            depth_brace += 1
        elif char == "}":
            depth_brace = max(0, depth_brace - 1)
        elif char == "[":
            depth_bracket += 1
        elif char == "]":
            depth_bracket = max(0, depth_bracket - 1)
        elif char == ";" and depth_paren == 0 and depth_brace == 0 and depth_bracket == 0:
            return text[start:index]
    return None


def build_provider_graph(blocks: list[ProviderBlock]) -> dict[str, set[str]]:
    provider_names = {block.name for block in blocks}
    graph: dict[str, set[str]] = {name: set() for name in provider_names}
    for block in blocks:
        for match in PROVIDER_ACCESS_PATTERN.finditer(block.body):
            dependency = match.group(1)
            if dependency in provider_names:
                graph[block.name].add(dependency)
    return graph


def strongly_connected_components(graph: dict[T, set[T]]) -> list[list[T]]:
    index = 0
    indices: dict[T, int] = {}
    lowlinks: dict[T, int] = {}
    stack: list[T] = []
    on_stack: set[T] = set()
    components: list[list[T]] = []

    def visit(node: T) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for dependency in graph.get(node, set()):
            if dependency not in indices:
                visit(dependency)
                lowlinks[node] = min(lowlinks[node], lowlinks[dependency])
            elif dependency in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[dependency])
        if lowlinks[node] != indices[node]:
            return
        component: list[T] = []
        while stack:
            dependency = stack.pop()
            on_stack.remove(dependency)
            component.append(dependency)
            if dependency == node:
                break
        components.append(component)

    for node in graph:
        if node not in indices:
            visit(node)
    return components


def cycles(graph: dict[T, set[T]]) -> list[list[T]]:
    found: list[list[T]] = []
    for component in strongly_connected_components(graph):
        if len(component) > 1:
            found.append(sorted(component, key=str))
            continue
        node = component[0]
        if node in graph.get(node, set()):
            found.append(component)
    return sorted(found, key=lambda items: ",".join(str(item) for item in items))


def print_import_cycle(cycle: list[str]) -> None:
    print("[dependency-audit] import cycle:")
    for path in cycle:
        print(f"  - {path}")


def print_provider_cycle(cycle: list[str], provider_paths: dict[str, Path]) -> None:
    print("[dependency-audit] provider recursion:")
    for provider in cycle:
        print(f"  - {provider} ({normalized(provider_paths[provider])})")


def main() -> int:
    args = parse_args()
    files = dart_files(args.roots)
    project_package = package_name()

    import_graph = build_import_graph(files, project_package)
    provider_blocks = find_provider_blocks(files)
    provider_paths = {block.name: block.path for block in provider_blocks}
    provider_graph = build_provider_graph(provider_blocks)

    import_cycles = cycles(import_graph)
    provider_cycles = cycles(provider_graph)

    for cycle in import_cycles:
        print_import_cycle(cycle)
    for cycle in provider_cycles:
        print_provider_cycle(cycle, provider_paths)

    print(
        "[dependency-audit] "
        f"dart_files={len(files)} import_cycles={len(import_cycles)} "
        f"providers={len(provider_blocks)} provider_cycles={len(provider_cycles)}"
    )

    return 1 if import_cycles or provider_cycles else 0


if __name__ == "__main__":
    raise SystemExit(main())
