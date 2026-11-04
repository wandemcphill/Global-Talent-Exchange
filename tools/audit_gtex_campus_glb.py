#!/usr/bin/env python3
"""Read-only GLB 2.0 integrity and geometry-duplication audit for GTEX campus assets.

Usage:
  python tools/audit_gtex_campus_glb.py frontend/react-shell/public/models/campus \
      --json /tmp/campus-audit.json --markdown /tmp/campus-audit.md

No Supabase, Blender, Three.js, or third-party Python packages are required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any

_COMPONENT_BYTES = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_TYPE_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}
_JSON_CHUNK, _BIN_CHUNK = 0x4E4F534A, 0x004E4942


def _parse_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("file is too short to be GLB 2.0")
    magic, version, declared_length = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2:
        raise ValueError("invalid GLB magic or container version (expected glTF 2.0)")
    if declared_length != len(raw):
        raise ValueError(f"header length {declared_length} != file length {len(raw)}")
    document, binary, offset = None, b"", 12
    while offset + 8 <= len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        end = offset + length
        if end > len(raw):
            raise ValueError("chunk exceeds GLB length")
        chunk = raw[offset:end]
        offset = end
        if kind == _JSON_CHUNK:
            if document is not None:
                raise ValueError("multiple JSON chunks")
            document = json.loads(chunk.decode("utf-8").rstrip("\x00 \t\r\n"))
        elif kind == _BIN_CHUNK:
            if binary:
                raise ValueError("multiple BIN chunks")
            binary = chunk
    if offset != len(raw) or document is None:
        raise ValueError("malformed chunk alignment or missing JSON chunk")
    return document, binary


def _accessor_bytes(doc: dict[str, Any], binary: bytes, index: int) -> tuple[bytes, int, str]:
    accessors = doc.get("accessors", [])
    if not isinstance(index, int) or not 0 <= index < len(accessors):
        raise ValueError(f"invalid accessor index {index!r}")
    accessor = accessors[index]
    ctype, atype, count = accessor.get("componentType"), accessor.get("type"), accessor.get("count")
    if ctype not in _COMPONENT_BYTES or atype not in _TYPE_COMPONENTS or not isinstance(count, int) or count < 0:
        raise ValueError(f"accessor {index} has unsupported type or count")
    item_size = _COMPONENT_BYTES[ctype] * _TYPE_COMPONENTS[atype]
    payload = bytes(item_size * count)
    view_index = accessor.get("bufferView")
    if view_index is not None:
        views = doc.get("bufferViews", [])
        if not isinstance(view_index, int) or not 0 <= view_index < len(views):
            raise ValueError(f"accessor {index} references missing bufferView {view_index}")
        view = views[view_index]
        if view.get("buffer", 0) != 0:
            raise ValueError(f"accessor {index} references non-GLB buffer")
        start, size = int(view.get("byteOffset", 0)), int(view.get("byteLength", 0))
        raw_view = binary[start : start + size]
        stride = int(view.get("byteStride", item_size))
        first = int(accessor.get("byteOffset", 0))
        if start < 0 or size < 0 or first < 0 or len(raw_view) != size or stride < item_size:
            raise ValueError(f"accessor {index} has invalid bufferView bounds/stride")
        if count and first + (count - 1) * stride + item_size > len(raw_view):
            raise ValueError(f"accessor {index} exceeds bufferView bounds")
        payload = b"".join(raw_view[first + i * stride : first + i * stride + item_size] for i in range(count))
    descriptor = f"{ctype}:{atype}:{count}:{bool(accessor.get('normalized', False))}".encode()
    sparse = accessor.get("sparse")
    if sparse:
        descriptor += json.dumps(sparse, sort_keys=True, separators=(",", ":")).encode()
        for part in (sparse.get("indices", {}), sparse.get("values", {})):
            bv = part.get("bufferView")
            if bv is None:
                continue
            views = doc.get("bufferViews", [])
            if not isinstance(bv, int) or not 0 <= bv < len(views):
                raise ValueError(f"accessor {index} sparse data references missing bufferView {bv}")
            view = views[bv]
            start, size = int(view.get("byteOffset", 0)), int(view.get("byteLength", 0))
            sparse_bytes = binary[start:start + size]
            if start < 0 or size < 0 or len(sparse_bytes) != size:
                raise ValueError(f"accessor {index} sparse data exceeds BIN chunk")
            payload += sparse_bytes
    return descriptor + b"\0" + payload, count, atype


def _audit(path: Path, root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    item: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(raw),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "valid_glb": False,
        "asset_version": None,
        "meshes": 0,
        "primitives": 0,
        "vertices": 0,
        "triangles": 0,
        "materials": 0,
        "pbr_materials": 0,
        "textures": 0,
        "images": 0,
        "external_uris": [],
        "invalid_references": [],
        "warnings": [],
        "errors": [],
        "geometry_sha256": None,
        "bounds_span": None,
    }
    try:
        doc, binary = _parse_glb(path)
        item["valid_glb"] = True
        item["asset_version"] = (doc.get("asset") or {}).get("version")
        if item["asset_version"] != "2.0":
            item["warnings"].append("asset.version is not 2.0")
        buffers = doc.get("buffers", [])
        if buffers and int(buffers[0].get("byteLength", 0)) > len(binary):
            item["errors"].append("declared buffer length exceeds BIN chunk")
        if len(buffers) > 1:
            item["warnings"].append("multiple buffers require manual review")
        item["external_uris"] = [str(x["uri"]) for x in [*buffers, *doc.get("images", [])] if x.get("uri")]
        if item["external_uris"]:
            item["warnings"].append("external resources are referenced")
        meshes, materials = doc.get("meshes", []), doc.get("materials", [])
        item["meshes"], item["materials"] = len(meshes), len(materials)
        item["pbr_materials"] = sum(isinstance(m.get("pbrMetallicRoughness"), dict) for m in materials)
        item["textures"], item["images"] = len(doc.get("textures", [])), len(doc.get("images", []))
        primitive_hashes, pos_bounds = [], []
        for mi, mesh in enumerate(meshes):
            for pi, primitive in enumerate(mesh.get("primitives", [])):
                item["primitives"] += 1
                digest = hashlib.sha256(str(primitive.get("mode", 4)).encode())
                attrs = primitive.get("attributes") or {}
                if "POSITION" not in attrs:
                    item["warnings"].append(f"mesh {mi} primitive {pi} has no POSITION")
                for name, accessor_index in sorted(attrs.items()):
                    try:
                        payload, count, _ = _accessor_bytes(doc, binary, accessor_index)
                        digest.update(name.encode() + b"\0" + payload)
                        if name == "POSITION":
                            item["vertices"] += count
                            acc = doc["accessors"][accessor_index]
                            if len(acc.get("min", [])) >= 3 and len(acc.get("max", [])) >= 3:
                                pos_bounds.append((acc["min"][:3], acc["max"][:3]))
                    except (ValueError, TypeError, KeyError) as exc:
                        item["invalid_references"].append(f"mesh {mi} primitive {pi} attribute {name}: {exc}")
                index = primitive.get("indices")
                try:
                    if index is not None:
                        _, count, _ = _accessor_bytes(doc, binary, index)
                    else:
                        pos_index = attrs.get("POSITION")
                        count = doc["accessors"][pos_index]["count"] if pos_index is not None else 0
                    mode = primitive.get("mode", 4)
                    item["triangles"] += count // 3 if mode == 4 else max(0, count - 2) if mode in (5, 6) else 0
                    if index is not None:
                        digest.update(_accessor_bytes(doc, binary, index)[0])
                except (ValueError, TypeError, KeyError, IndexError) as exc:
                    item["invalid_references"].append(f"mesh {mi} primitive {pi} indices: {exc}")
                material = primitive.get("material")
                if material is not None and not (isinstance(material, int) and 0 <= material < len(materials)):
                    item["invalid_references"].append(
                        f"mesh {mi} primitive {pi} references missing material {material}"
                    )
                primitive_hashes.append(digest.hexdigest())
        if primitive_hashes:
            item["geometry_sha256"] = hashlib.sha256("|".join(sorted(primitive_hashes)).encode()).hexdigest()
        if pos_bounds:
            low = [min(float(x[0][i]) for x in pos_bounds) for i in range(3)]
            high = [max(float(x[1][i]) for x in pos_bounds) for i in range(3)]
            item["bounds_span"] = [round(high[i] - low[i], 6) for i in range(3)]
        for ni, node in enumerate(doc.get("nodes", [])):
            mesh = node.get("mesh")
            if mesh is not None and not (isinstance(mesh, int) and 0 <= mesh < len(meshes)):
                item["invalid_references"].append(f"node {ni} references missing mesh {mesh}")
        if item["invalid_references"]:
            item["errors"].extend(item["invalid_references"])
    except (OSError, ValueError, json.JSONDecodeError, struct.error) as exc:
        item["errors"].append(str(exc))
    return item


def _groups(items: list[dict[str, Any]], field: str) -> list[list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in items:
        value = item.get(field)
        if value:
            grouped[value].append(item["path"])
    return [sorted(paths) for paths in grouped.values() if len(paths) > 1]


def audit_library(root: Path) -> dict[str, Any]:
    items = [_audit(path, root) for path in sorted(root.rglob("*.glb"))]
    metrics: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for item in items:
        if item["valid_glb"]:
            key = (
                item["vertices"],
                item["triangles"],
                item["materials"],
                tuple(item["bounds_span"] or []),
            )
            metrics[key].append(item["path"])
    return {
        "models_root": str(root),
        "summary": {
            "files": len(items),
            "valid_files": sum(x["valid_glb"] and not x["errors"] for x in items),
            "invalid_files": sum(bool(x["errors"]) for x in items),
            "exact_binary_duplicates": _groups(items, "file_sha256"),
            "matching_geometry": _groups(items, "geometry_sha256"),
            "same_metrics_only": [sorted(v) for v in metrics.values() if len(v) > 1],
        },
        "models": items,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# GTEX Campus GLB Audit",
        "",
        f"- Files: **{summary['files']}** | valid: **{summary['valid_files']}** | invalid: **{summary['invalid_files']}**",
        f"- Exact binary duplicate groups: **{len(summary['exact_binary_duplicates'])}**",
        f"- Matching geometry groups: **{len(summary['matching_geometry'])}**",
        f"- Same metrics only (not proof of duplication): **{len(summary['same_metrics_only'])}**",
        "",
        "| Model | Valid | Vertices | Triangles | Materials/PBR | Span (local) | Bytes | Findings |",
        "|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for model in report["models"]:
        span = " × ".join(map(str, model["bounds_span"] or [])) or "—"
        findings = len(model["warnings"]) + len(model["errors"])
        lines.append(
            f"| {model['path']} | {'yes' if model['valid_glb'] and not model['errors'] else 'NO'} | "
            f"{model['vertices']} | {model['triangles']} | "
            f"{model['materials']}/{model['pbr_materials']} | {span} | {model['bytes']:,} | {findings} |"
        )
    for key, title in (
        ("exact_binary_duplicates", "Exact binary duplicates"),
        ("matching_geometry", "Matching geometry fingerprints"),
        ("same_metrics_only", "Same metrics only — manual review required"),
    ):
        lines.extend(["", f"## {title}", ""])
        lines.extend(["- " + ", ".join(group) for group in summary[key]] or ["None found."])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Matching geometry fingerprints compare primitive topology and raw accessor payloads; they do not apply node transforms or compare material assignments.",
            "- Equal vertex/triangle/material counts and dimensions are only a review signal, never proof of duplicate architecture.",
            "- Bounds use accessor-local min/max values; this tool does not apply node transforms.",
            "- The audit is read-only and does not alter any GLB.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models_dir", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--markdown", dest="md_path", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit 1 if any GLB fails validation")
    args = parser.parse_args()
    root = args.models_dir.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    report = audit_library(root)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(encoded, encoding="utf-8")
    if args.md_path:
        args.md_path.parent.mkdir(parents=True, exist_ok=True)
        args.md_path.write_text(markdown(report), encoding="utf-8")
    print(markdown(report))
    return 1 if args.strict and report["summary"]["invalid_files"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
