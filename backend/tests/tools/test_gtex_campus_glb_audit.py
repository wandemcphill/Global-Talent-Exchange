"""Regression tests for the dependency-free GTEX campus GLB audit."""
from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.audit_gtex_campus_glb import audit_library


def make_glb(path: Path, positions: bytes | None = None) -> None:
    """Write a minimal one-triangle GLB fixture."""
    positions = positions or struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    doc = {
        "asset": {"version": "2.0", "generator": "test-fixture"},
        "buffers": [{"byteLength": len(positions)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(positions)}],
        "accessors": [{
            "bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3",
            "min": [0, 0, 0], "max": [1, 1, 0],
        }],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "mode": 4}]}],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    json_chunk = json.dumps(doc, separators=(",", ":")).encode()
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    bin_chunk = positions + b"\0" * ((4 - len(positions) % 4) % 4)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    raw = struct.pack("<4sII", b"glTF", 2, total)
    raw += struct.pack("<II", len(json_chunk), 0x4E4F534A) + json_chunk
    raw += struct.pack("<II", len(bin_chunk), 0x004E4942) + bin_chunk
    path.write_bytes(raw)


class CampusGlbAuditTests(unittest.TestCase):
    def test_valid_glb_reports_geometry_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_glb(root / "stadium.glb")
            report = audit_library(root)
            model = report["models"][0]
            self.assertTrue(model["valid_glb"])
            self.assertEqual(model["asset_version"], "2.0")
            self.assertEqual(model["vertices"], 3)
            self.assertEqual(model["triangles"], 1)
            self.assertEqual(report["summary"]["invalid_files"], 0)

    def test_exact_binary_and_geometry_duplicates_are_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_glb(root / "stadium_main.glb")
            (root / "stadium_bowl_core.glb").write_bytes(
                (root / "stadium_main.glb").read_bytes()
            )
            report = audit_library(root)
            self.assertEqual(len(report["summary"]["exact_binary_duplicates"]), 1)
            self.assertEqual(len(report["summary"]["matching_geometry"]), 1)

    def test_matching_counts_alone_are_not_called_geometry_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_glb(root / "model_a.glb")
            make_glb(
                root / "model_b.glb",
                struct.pack("<9f", 0, 0, 0, 2, 0, 0, 0, 1, 0),
            )
            report = audit_library(root)
            self.assertEqual(len(report["summary"]["matching_geometry"]), 0)
            self.assertEqual(len(report["summary"]["same_metrics_only"]), 1)

    def test_invalid_glb_header_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken.glb").write_bytes(b"not-a-glb")
            report = audit_library(root)
            self.assertEqual(report["summary"]["invalid_files"], 1)
            self.assertIn("too short", report["models"][0]["errors"][0])

    def test_mismatched_header_length_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_glb(root / "good.glb")
            raw = bytearray((root / "good.glb").read_bytes())
            struct.pack_into("<I", raw, 8, len(raw) - 4)
            (root / "bad.glb").write_bytes(raw)
            report = audit_library(root)
            bad = next(model for model in report["models"] if model["path"] == "bad.glb")
            self.assertFalse(bad["valid_glb"])
            self.assertIn("!=", bad["errors"][0])


if __name__ == "__main__":
    unittest.main()
