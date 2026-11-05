"""
GTEX Club Dynasty Phase 2.1 — High-Detail Modular 3D glTF 2.0 (.glb) Asset Pipeline
Generates 28 architecturally distinct, multi-material PBR .glb production models and
28 high-segment master models with strict footprint conformance, mullioned glass facades,
cable-stayed stadium roof trusses, hydrotherapy pools, arched indoor arenas, and 5 rich
construction progression stages.
"""

import json
import math
import struct
from pathlib import Path

PUBLIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "react-shell" / "public"
CAMPUS_DIR = PUBLIC_DIR / "models" / "campus"
MASTERS_DIR = CAMPUS_DIR / "masters"


# ---------------------------------------------------------------------------
# PBR Material Palette (GTEX Matchday Luxury)
# ---------------------------------------------------------------------------
MATERIALS = [
    {
        "name": "ArchitecturalConcrete",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.80, 0.82, 0.85, 1.0],
            "metallicFactor": 0.08,
            "roughnessFactor": 0.68,
        },
    },
    {
        "name": "DarkSlateStone",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.15, 0.19, 0.25, 1.0],
            "metallicFactor": 0.14,
            "roughnessFactor": 0.62,
        },
    },
    {
        "name": "CurtainWallGlass",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.12, 0.42, 0.62, 0.78],
            "metallicFactor": 0.88,
            "roughnessFactor": 0.10,
        },
        "alphaMode": "BLEND",
    },
    {
        "name": "BrushedSteel",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.68, 0.73, 0.79, 1.0],
            "metallicFactor": 0.90,
            "roughnessFactor": 0.25,
        },
    },
    {
        "name": "GtexEmeraldAccent",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.02, 0.78, 0.54, 1.0],
            "metallicFactor": 0.35,
            "roughnessFactor": 0.30,
        },
        "emissiveFactor": [0.0, 0.16, 0.10],
    },
    {
        "name": "ChampionshipGold",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.92, 0.73, 0.24, 1.0],
            "metallicFactor": 0.92,
            "roughnessFactor": 0.20,
        },
        "emissiveFactor": [0.14, 0.10, 0.02],
    },
    {
        "name": "HybridPitchTurf",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.10, 0.46, 0.22, 1.0],
            "metallicFactor": 0.02,
            "roughnessFactor": 0.88,
        },
    },
    {
        "name": "PitchStripeLight",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.15, 0.56, 0.28, 1.0],
            "metallicFactor": 0.02,
            "roughnessFactor": 0.85,
        },
    },
    {
        "name": "CrispWhiteLine",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.96, 0.98, 0.99, 1.0],
            "metallicFactor": 0.05,
            "roughnessFactor": 0.42,
        },
    },
    {
        "name": "HydroPoolWater",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.06, 0.65, 0.90, 0.86],
            "metallicFactor": 0.22,
            "roughnessFactor": 0.06,
        },
        "alphaMode": "BLEND",
    },
    {
        "name": "SolarPanelBlue",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.06, 0.18, 0.40, 1.0],
            "metallicFactor": 0.78,
            "roughnessFactor": 0.16,
        },
    },
    {
        "name": "FloodlightEmissive",
        "pbrMetallicRoughness": {
            "baseColorFactor": [1.0, 0.98, 0.90, 1.0],
            "metallicFactor": 0.10,
            "roughnessFactor": 0.10,
        },
        "emissiveFactor": [1.0, 0.96, 0.84],
    },
    {
        "name": "ConstructionSafetyAmber",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.95, 0.62, 0.08, 1.0],
            "metallicFactor": 0.42,
            "roughnessFactor": 0.38,
        },
    },
    {
        "name": "ExcavatedEarth",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.44, 0.32, 0.20, 1.0],
            "metallicFactor": 0.02,
            "roughnessFactor": 0.94,
        },
    },
    {
        "name": "FoliageCanopy",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.12, 0.42, 0.18, 1.0],
            "metallicFactor": 0.02,
            "roughnessFactor": 0.88,
        },
    },
    {
        "name": "TerracottaTimber",
        "pbrMetallicRoughness": {
            "baseColorFactor": [0.78, 0.38, 0.20, 1.0],
            "metallicFactor": 0.08,
            "roughnessFactor": 0.72,
        },
    },
]

MAT = {m["name"]: idx for idx, m in enumerate(MATERIALS)}


class MultiMaterialMeshBuilder:
    """Builds multi-primitive glTF 2.0 binary (.glb) models with exact normals and PBR materials."""

    def __init__(self):
        self.primitives: dict[int, dict] = {}

    def _bucket(self, mat_idx: int) -> dict:
        if mat_idx not in self.primitives:
            self.primitives[mat_idx] = {"positions": [], "normals": [], "indices": []}
        return self.primitives[mat_idx]

    def add_quad(self, mat_idx: int, p0, p1, p2, p3):
        b = self._bucket(mat_idx)
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        n = (nx / length, ny / length, nz / length)
        base = len(b["positions"])
        b["positions"].extend([p0, p1, p2, p3])
        b["normals"].extend([n, n, n, n])
        b["indices"].append((base, base + 1, base + 2))
        b["indices"].append((base, base + 2, base + 3))

    def add_tri(self, mat_idx: int, p0, p1, p2):
        b = self._bucket(mat_idx)
        ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        n = (nx / length, ny / length, nz / length)
        base = len(b["positions"])
        b["positions"].extend([p0, p1, p2])
        b["normals"].extend([n, n, n])
        b["indices"].append((base, base + 1, base + 2))

    def add_box(self, mat_idx: int, cx: float, cy: float, cz: float, sx: float, sy: float, sz: float):
        x0, x1 = cx - sx / 2.0, cx + sx / 2.0
        y0, y1 = cy - sy / 2.0, cy + sy / 2.0
        z0, z1 = cz - sz / 2.0, cz + sz / 2.0
        self.add_quad(mat_idx, (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
        self.add_quad(mat_idx, (x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0))
        self.add_quad(mat_idx, (x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1))
        self.add_quad(mat_idx, (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))
        self.add_quad(mat_idx, (x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0))
        self.add_quad(mat_idx, (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))

    def add_beam(
        self, mat_idx: int, p0: tuple[float, float, float], p1: tuple[float, float, float], thickness: float = 0.04
    ):
        """Adds a 3D structural strut/cable/beam between two arbitrary 3D points."""
        dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length < 1e-4:
            return
        r = thickness / 2.0
        # Construct two perpendicular axes
        if abs(dy) < 0.9 * length:
            ux, uy, uz = -dz, 0.0, dx
        else:
            ux, uy, uz = 1.0, 0.0, 0.0
        ul = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
        ux, uy, uz = (ux / ul) * r, (uy / ul) * r, (uz / ul) * r
        vx = (dy * uz - dz * uy) / length
        vy = (dz * ux - dx * uz) / length
        vz = (dx * uy - dy * ux) / length
        vl = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
        vx, vy, vz = (vx / vl) * r, (vy / vl) * r, (vz / vl) * r

        c00 = (p0[0] - ux - vx, p0[1] - uy - vy, p0[2] - uz - vz)
        c10 = (p0[0] + ux - vx, p0[1] + uy - vy, p0[2] + uz - vz)
        c11 = (p0[0] + ux + vx, p0[1] + uy + vy, p0[2] + uz + vz)
        c01 = (p0[0] - ux + vx, p0[1] - uy + vy, p0[2] - uz + vz)

        d00 = (p1[0] - ux - vx, p1[1] - uy - vy, p1[2] - uz - vz)
        d10 = (p1[0] + ux - vx, p1[1] + uy - vy, p1[2] + uz - vz)
        d11 = (p1[0] + ux + vx, p1[1] + uy + vy, p1[2] + uz + vz)
        d01 = (p1[0] - ux + vx, p1[1] - uy + vy, p1[2] - uz + vz)

        self.add_quad(mat_idx, c00, c10, d10, d00)
        self.add_quad(mat_idx, c10, c11, d11, d10)
        self.add_quad(mat_idx, c11, c01, d01, d11)
        self.add_quad(mat_idx, c01, c00, d00, d01)

    def add_cylinder(
        self,
        mat_idx: int,
        cx: float,
        y0: float,
        cz: float,
        r_bottom: float,
        r_top: float,
        height: float,
        segments: int = 16,
        scale_z: float = 1.0,
    ):
        y1 = y0 + height
        for i in range(segments):
            a0 = (2.0 * math.pi * i) / segments
            a1 = (2.0 * math.pi * (i + 1)) / segments
            c0, s0 = math.cos(a0), math.sin(a0)
            c1, s1 = math.cos(a1), math.sin(a1)
            p00 = (cx + c0 * r_bottom, y0, cz + s0 * r_bottom * scale_z)
            p10 = (cx + c1 * r_bottom, y0, cz + s1 * r_bottom * scale_z)
            p11 = (cx + c1 * r_top, y1, cz + s1 * r_top * scale_z)
            p01 = (cx + c0 * r_top, y1, cz + s0 * r_top * scale_z)
            self.add_quad(mat_idx, p00, p10, p11, p01)
            if r_top > 0.001:
                self.add_tri(mat_idx, (cx, y1, cz), p01, p11)

    def add_ring_wall(
        self,
        mat_idx: int,
        cx: float,
        y0: float,
        cz: float,
        rx_inner: float,
        rz_inner: float,
        rx_outer: float,
        rz_outer: float,
        h_inner: float,
        h_outer: float,
        segments: int = 28,
    ):
        yi = y0 + h_inner
        yo = y0 + h_outer
        for i in range(segments):
            a0 = (2.0 * math.pi * i) / segments
            a1 = (2.0 * math.pi * (i + 1)) / segments
            c0, s0 = math.cos(a0), math.sin(a0)
            c1, s1 = math.cos(a1), math.sin(a1)

            bi0 = (cx + c0 * rx_inner, y0, cz + s0 * rz_inner)
            bi1 = (cx + c1 * rx_inner, y0, cz + s1 * rz_inner)
            bo0 = (cx + c0 * rx_outer, y0, cz + s0 * rz_outer)
            bo1 = (cx + c1 * rx_outer, y0, cz + s1 * rz_outer)

            ti0 = (cx + c0 * rx_inner, yi, cz + s0 * rz_inner)
            ti1 = (cx + c1 * rx_inner, yi, cz + s1 * rz_inner)
            to0 = (cx + c0 * rx_outer, yo, cz + s0 * rz_outer)
            to1 = (cx + c1 * rx_outer, yo, cz + s1 * rz_outer)

            self.add_quad(mat_idx, bo0, bo1, to1, to0)
            self.add_quad(mat_idx, ti0, ti1, bi1, bi0)
            self.add_quad(mat_idx, ti0, to0, to1, ti1)

    def add_mullioned_glass_wing(
        self,
        cx: float,
        y0: float,
        cz: float,
        sx: float,
        sy: float,
        sz: float,
        storeys: int = 2,
        mullion_cols: int = 5,
        accent_mat: int = MAT["GtexEmeraldAccent"],
    ):
        """Creates a multi-storey architectural wing with concrete floor plates, glass curtain walls, and vertical steel mullions."""
        # Core structural concrete frame
        self.add_box(MAT["ArchitecturalConcrete"], cx, y0 + sy / 2.0, cz, sx - 0.06, sy, sz - 0.06)
        # Curtain wall glazing shell
        self.add_box(MAT["CurtainWallGlass"], cx, y0 + sy / 2.0, cz, sx, sy - 0.06, sz)
        # Floor slabs & spandrel bands
        for s in range(storeys + 1):
            fy = y0 + (sy * s) / storeys
            self.add_box(MAT["ArchitecturalConcrete"], cx, fy, cz, sx + 0.03, 0.04, sz + 0.03)
        # Top roof parapet accent
        self.add_box(accent_mat, cx, y0 + sy + 0.025, cz, sx + 0.05, 0.035, sz + 0.05)
        # Vertical facade mullions along front (+Z) and back (-Z)
        for i in range(mullion_cols + 1):
            mx = cx - sx / 2.0 + (sx * i) / mullion_cols
            for side in (-1, 1):
                mz = cz + side * (sz / 2.0 + 0.01)
                self.add_box(MAT["BrushedSteel"], mx, y0 + sy / 2.0, mz, 0.025, sy, 0.025)

    def add_pitch_surface(
        self, cx: float, y0: float, cz: float, pw: float, pd: float, stripes: int = 10, circle_segments: int = 12
    ):
        # Outer dark slate apron
        self.add_box(MAT["DarkSlateStone"], cx, y0 + 0.02, cz, pw + 0.24, 0.04, pd + 0.24)
        # Alternating turf stripes
        sw = pw / stripes
        x_start = cx - pw / 2.0
        for i in range(stripes):
            mat = MAT["HybridPitchTurf"] if i % 2 == 0 else MAT["PitchStripeLight"]
            scx = x_start + (i + 0.5) * sw
            self.add_box(mat, scx, y0 + 0.045, cz, sw, 0.035, pd)
        # White touchlines, goal lines & halfway line
        lw = 0.035
        ly = y0 + 0.068
        self.add_box(MAT["CrispWhiteLine"], cx, ly, cz - pd / 2.0 + lw, pw - 0.08, 0.012, lw)
        self.add_box(MAT["CrispWhiteLine"], cx, ly, cz + pd / 2.0 - lw, pw - 0.08, 0.012, lw)
        self.add_box(MAT["CrispWhiteLine"], cx - pw / 2.0 + lw, ly, cz, lw, 0.012, pd - 0.08)
        self.add_box(MAT["CrispWhiteLine"], cx + pw / 2.0 - lw, ly, cz, lw, 0.012, pd - 0.08)
        self.add_box(MAT["CrispWhiteLine"], cx, ly, cz, lw, 0.012, pd - 0.08)
        # Center circle
        cr = min(pw, pd) * 0.14
        for i in range(circle_segments):
            a0 = (2.0 * math.pi * i) / circle_segments
            a1 = (2.0 * math.pi * (i + 1)) / circle_segments
            p0 = (cx + math.cos(a0) * cr, ly, cz + math.sin(a0) * cr)
            p1 = (cx + math.cos(a1) * cr, ly, cz + math.sin(a1) * cr)
            self.add_beam(MAT["CrispWhiteLine"], p0, p1, thickness=0.025)
        # Penalty boxes & 3D goalframes with net depth
        for side in (-1, 1):
            gx = cx + side * (pw / 2.0 - 0.05)
            bx = cx + side * (pw / 2.0 - 0.28)
            self.add_box(MAT["CrispWhiteLine"], bx, ly, cz, 0.46, 0.011, pd * 0.44)
            # Goalposts, crossbar & rear net frame
            self.add_box(MAT["CrispWhiteLine"], gx, y0 + 0.15, cz - 0.20, 0.025, 0.17, 0.025)
            self.add_box(MAT["CrispWhiteLine"], gx, y0 + 0.15, cz + 0.20, 0.025, 0.17, 0.025)
            self.add_box(MAT["CrispWhiteLine"], gx, y0 + 0.23, cz, 0.025, 0.025, 0.42)
            self.add_box(MAT["BrushedSteel"], gx + side * 0.06, y0 + 0.14, cz, 0.10, 0.15, 0.40)

    def bounds_and_stats(self) -> tuple[int, int, int, tuple[float, float, float], tuple[float, float, float]]:
        verts = sum(len(b["positions"]) for b in self.primitives.values())
        tris = sum(len(b["indices"]) for b in self.primitives.values())
        mats = len(self.primitives)
        min_v = [float("inf"), float("inf"), float("inf")]
        max_v = [float("-inf"), float("-inf"), float("-inf")]
        for b in self.primitives.values():
            for x, y, z in b["positions"]:
                min_v[0], min_v[1], min_v[2] = min(min_v[0], x), min(min_v[1], y), min(min_v[2], z)
                max_v[0], max_v[1], max_v[2] = max(max_v[0], x), max(max_v[1], y), max(max_v[2], z)
        return verts, tris, mats, tuple(min_v), tuple(max_v)

    def to_glb_bytes(self, name: str) -> bytes:
        bin_chunks = bytearray()
        buffer_views = []
        accessors = []
        gltf_primitives = []
        used_materials = []
        mat_remap: dict[int, int] = {}

        for mat_idx, b in sorted(self.primitives.items()):
            positions = b["positions"]
            normals = b["normals"]
            indices = b["indices"]
            if not positions or not indices:
                continue

            if mat_idx not in mat_remap:
                mat_remap[mat_idx] = len(used_materials)
                used_materials.append(MATERIALS[mat_idx])
            local_mat_idx = mat_remap[mat_idx]

            pos_bytes = bytearray()
            min_v = [float("inf"), float("inf"), float("inf")]
            max_v = [float("-inf"), float("-inf"), float("-inf")]
            for x, y, z in positions:
                pos_bytes.extend(struct.pack("<3f", x, y, z))
                min_v[0], min_v[1], min_v[2] = min(min_v[0], x), min(min_v[1], y), min(min_v[2], z)
                max_v[0], max_v[1], max_v[2] = max(max_v[0], x), max(max_v[1], y), max(max_v[2], z)

            norm_bytes = bytearray()
            for nx, ny, nz in normals:
                norm_bytes.extend(struct.pack("<3f", nx, ny, nz))

            idx_bytes = bytearray()
            for i0, i1, i2 in indices:
                idx_bytes.extend(struct.pack("<3H", i0, i1, i2))
            while len(idx_bytes) % 4 != 0:
                idx_bytes.append(0)

            pos_offset = len(bin_chunks)
            bin_chunks.extend(pos_bytes)
            norm_offset = len(bin_chunks)
            bin_chunks.extend(norm_bytes)
            idx_offset = len(bin_chunks)
            bin_chunks.extend(idx_bytes)

            bv_base = len(buffer_views)
            buffer_views.extend(
                [
                    {"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes), "target": 34962},
                    {"buffer": 0, "byteOffset": norm_offset, "byteLength": len(norm_bytes), "target": 34962},
                    {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963},
                ]
            )

            acc_base = len(accessors)
            accessors.extend(
                [
                    {
                        "bufferView": bv_base,
                        "byteOffset": 0,
                        "componentType": 5126,
                        "count": len(positions),
                        "type": "VEC3",
                        "min": [round(v, 5) for v in min_v],
                        "max": [round(v, 5) for v in max_v],
                    },
                    {
                        "bufferView": bv_base + 1,
                        "byteOffset": 0,
                        "componentType": 5126,
                        "count": len(normals),
                        "type": "VEC3",
                    },
                    {
                        "bufferView": bv_base + 2,
                        "byteOffset": 0,
                        "componentType": 5123,
                        "count": len(indices) * 3,
                        "type": "SCALAR",
                    },
                ]
            )

            gltf_primitives.append(
                {
                    "attributes": {"POSITION": acc_base, "NORMAL": acc_base + 1},
                    "indices": acc_base + 2,
                    "material": local_mat_idx,
                    "mode": 4,
                }
            )

        gltf = {
            "asset": {"version": "2.0", "generator": "GTEX-ClubDynasty-Phase2.1-WebGL-Pipeline"},
            "scene": 0,
            "scenes": [{"name": name, "nodes": [0]}],
            "nodes": [{"name": name, "mesh": 0}],
            "meshes": [{"name": f"{name}_Mesh", "primitives": gltf_primitives}],
            "materials": used_materials,
            "buffers": [{"byteLength": len(bin_chunks)}],
            "bufferViews": buffer_views,
            "accessors": accessors,
        }

        json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        while len(json_bytes) % 4 != 0:
            json_bytes += b" "

        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_chunks)
        header = struct.pack("<III", 0x46546C67, 2, total_len)
        chunk0 = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
        chunk1 = struct.pack("<II", len(bin_chunks), 0x004E4942) + bytes(bin_chunks)
        return header + chunk0 + chunk1


# ---------------------------------------------------------------------------
# TIER 1: STADIUM INFRASTRUCTURE (6x5, 4x2, 2x2)
# ---------------------------------------------------------------------------
def build_stadium_bowl_core(
    segments: int = 36,
    include_west_portico: bool = True,
    include_media_superstructure: bool = False,
) -> MultiMaterialMeshBuilder:
    """Footprint: 6 x 5 tiles (-2.85..+2.85 x -2.35..+2.35)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(12, segments // 2)
    # Monumental Stadium Concourse Plinth
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 5.68, 0.08, 4.68)
    m.add_box(MAT["ArchitecturalConcrete"], 0, 0.09, 0, 5.42, 0.04, 4.42)
    # Sunken Matchday Pitch inside Bowl
    m.add_pitch_surface(0, 0.08, 0, 2.75, 1.85, stripes=10, circle_segments=c_seg)
    # Tier 1: Lower Supporter Seating Bowl (Emerald & Concrete)
    m.add_ring_wall(MAT["GtexEmeraldAccent"], 0, 0.10, 0, 1.50, 1.05, 1.88, 1.32, 0.08, 0.34, segments=segments)
    m.add_ring_wall(MAT["ArchitecturalConcrete"], 0, 0.10, 0, 1.85, 1.30, 2.15, 1.52, 0.32, 0.56, segments=segments)
    # Tier 2: Panoramic VIP Skybox Glass Hospitality Ring
    m.add_ring_wall(MAT["CurtainWallGlass"], 0, 0.58, 0, 2.05, 1.46, 2.38, 1.70, 0.22, 0.28, segments=segments)
    # Tier 3: Upper Steep Grandstand & Diagrid Facade
    m.add_ring_wall(MAT["ArchitecturalConcrete"], 0, 0.82, 0, 2.10, 1.50, 2.62, 1.94, 0.18, 0.66, segments=segments)
    # Championship Gold & Emerald Exterior Crown Bands
    m.add_ring_wall(MAT["GtexEmeraldAccent"], 0, 1.16, 0, 2.60, 1.92, 2.67, 1.98, 0.07, 0.07, segments=segments)
    m.add_ring_wall(MAT["ChampionshipGold"], 0, 1.34, 0, 2.61, 1.93, 2.68, 1.99, 0.06, 0.06, segments=segments)
    # Cantilevered Acoustic Roof Canopy + Inner Skylight Lip
    m.add_ring_wall(MAT["BrushedSteel"], 0, 1.46, 0, 1.62, 1.15, 2.70, 2.02, 0.07, 0.13, segments=segments)
    m.add_ring_wall(MAT["CurtainWallGlass"], 0, 1.48, 0, 1.42, 0.98, 1.64, 1.16, 0.04, 0.06, segments=segments)

    # 16 Iconic Cable-Stayed Exterior Roof Masts & Tension Cables (Manchester Reference Style)
    mast_count = 16
    for i in range(mast_count):
        ang = (2.0 * math.pi * i) / mast_count
        ca, sa = math.cos(ang), math.sin(ang)
        outer_x, outer_z = ca * 2.68, sa * 1.98
        mast_top = (ca * 2.56, 2.05, sa * 1.88)
        inner_roof = (ca * 1.52, 1.52, sa * 1.08)
        ground_anchor = (ca * 2.76, 0.10, sa * 2.06)
        # Vertical/Inclined Steel Mast
        m.add_beam(MAT["BrushedSteel"], (outer_x, 0.10, outer_z), mast_top, thickness=0.065)
        # Forward suspension tension cable to inner roof ring
        m.add_beam(MAT["BrushedSteel"], mast_top, inner_roof, thickness=0.03)
        # Rear tie-down cable to concourse plinth
        m.add_beam(MAT["ChampionshipGold"], mast_top, ground_anchor, thickness=0.025)
        # LED Under-Roof Floodlight Pod
        m.add_box(MAT["FloodlightEmissive"], inner_roof[0], 1.49, inner_roof[2], 0.14, 0.04, 0.14)

    # 4 Corner Spiral Access Rotundas
    for sx in (-2.22, 2.22):
        for sz in (-1.62, 1.62):
            m.add_cylinder(MAT["ArchitecturalConcrete"], sx, 0.08, sz, 0.25, 0.25, 1.36, segments=c_seg)
            m.add_cylinder(MAT["CurtainWallGlass"], sx, 0.24, sz, 0.27, 0.27, 0.98, segments=c_seg)
            m.add_cylinder(MAT["ChampionshipGold"], sx, 1.44, sz, 0.28, 0.28, 0.05, segments=c_seg)

    # West VIP Directors Entrance Portico
    if include_west_portico:
        m.add_box(MAT["CurtainWallGlass"], 0, 0.45, 2.12, 1.45, 0.72, 0.28)
        m.add_box(MAT["ChampionshipGold"], 0, 0.84, 2.16, 1.56, 0.06, 0.34)
        for px in (-0.62, -0.22, 0.22, 0.62):
            m.add_box(MAT["ChampionshipGold"], px, 0.44, 2.26, 0.06, 0.74, 0.06)

    # Flagship Main Stadium Additions: East Broadcast Media Gantry, Twin Giant Scoreboards & Rooftop Solar Crown
    if include_media_superstructure:
        m.add_mullioned_glass_wing(
            0, 0.10, -2.10, 1.68, 0.86, 0.28, storeys=2, mullion_cols=5, accent_mat=MAT["GtexEmeraldAccent"]
        )
        for sx in (-1.38, 1.38):
            m.add_box(MAT["DarkSlateStone"], sx, 1.68, 0.0, 0.10, 0.28, 0.64)
            m.add_box(MAT["FloodlightEmissive"], sx - (0.06 if sx > 0 else -0.06), 1.68, 0.0, 0.02, 0.22, 0.56)
            m.add_box(MAT["ChampionshipGold"], sx, 1.83, 0.0, 0.12, 0.03, 0.68)
        for sx in (-1.10, -0.38, 0.38, 1.10):
            m.add_box(MAT["SolarPanelBlue"], sx, 1.60, -1.62, 0.48, 0.025, 0.28)
            m.add_box(MAT["SolarPanelBlue"], sx, 1.60, 1.62, 0.48, 0.025, 0.28)
    return m


def build_stadium_stand_expansion(segments: int = 20, twin_towers: bool = False) -> MultiMaterialMeshBuilder:
    """Footprint: 4 x 2 tiles (-1.88..+1.88 x -0.92..+0.92)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(10, segments // 2)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 3.76, 0.08, 1.84)
    # 3-Tier Raked Supporter Grandstand Steps
    for step in range(6):
        sy = 0.14 + step * 0.12
        sz = 0.48 - step * 0.14
        mat = MAT["GtexEmeraldAccent"] if step % 2 == 1 else MAT["ArchitecturalConcrete"]
        m.add_box(mat, 0, sy, sz, 3.46, 0.12, 0.22)
    # Rear Concourse & Executive Glass Box Gallery
    m.add_mullioned_glass_wing(
        0, 0.08, -0.42, 3.48, 0.88, 0.56, storeys=2, mullion_cols=8, accent_mat=MAT["ChampionshipGold"]
    )
    # Central Cylindrical Concourse Rotunda Drum (uses segments for LOD differentiation)
    m.add_cylinder(MAT["CurtainWallGlass"], 0, 0.08, -0.58, 0.28, 0.28, 1.06, segments=c_seg)
    m.add_cylinder(MAT["GtexEmeraldAccent"], 0, 1.14, -0.58, 0.30, 0.30, 0.04, segments=c_seg)
    # Cantilevered Steel Truss Roof Canopy
    m.add_box(MAT["BrushedSteel"], 0, 1.18, 0.02, 3.60, 0.07, 1.52)
    m.add_box(MAT["ChampionshipGold"], 0, 1.22, 0.74, 3.64, 0.04, 0.08)
    # 6 Overhead Cable-Stayed Roof Gantry Masts
    for tx in (-1.50, -0.90, -0.30, 0.30, 0.90, 1.50):
        m.add_beam(MAT["BrushedSteel"], (tx, 0.08, -0.74), (tx, 1.52, -0.62), thickness=0.06)
        m.add_beam(MAT["BrushedSteel"], (tx, 1.48, -0.62), (tx, 1.20, 0.70), thickness=0.03)
        m.add_box(MAT["FloodlightEmissive"], tx, 1.13, 0.68, 0.22, 0.04, 0.08)
    if twin_towers:
        for sx in (-1.62, 1.62):
            m.add_cylinder(MAT["CurtainWallGlass"], sx, 0.08, -0.52, 0.20, 0.20, 1.22, segments=c_seg)
            m.add_cylinder(MAT["ChampionshipGold"], sx, 1.30, -0.52, 0.22, 0.22, 0.05, segments=c_seg)
    return m


def build_floodlight_pylon_array(segments: int = 16, dual_array: bool = True) -> MultiMaterialMeshBuilder:
    """Footprint: 2 x 2 tiles (-0.92..+0.92 x -0.92..+0.92)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(10, segments // 2)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 1.84, 0.08, 1.84)
    # OB Broadcast Uplink Compound & Control Cabin
    m.add_mullioned_glass_wing(
        -0.32, 0.08, 0.36, 0.88, 0.38, 0.62, storeys=1, mullion_cols=3, accent_mat=MAT["GtexEmeraldAccent"]
    )
    m.add_cylinder(MAT["BrushedSteel"], -0.52, 0.48, 0.36, 0.04, 0.16, 0.14, segments=c_seg)
    m.add_cylinder(MAT["BrushedSteel"], -0.14, 0.48, 0.36, 0.04, 0.14, 0.12, segments=c_seg)

    mast_positions = (-0.46, 0.46) if dual_array else (0.28,)
    for px in mast_positions:
        m.add_box(MAT["ArchitecturalConcrete"], px, 0.16, -0.34, 0.34, 0.20, 0.34)
        # 4-Legged Tapered Lattice Mast + Cross Braces
        for lx in (-0.11, 0.11):
            for lz in (-0.11, 0.11):
                m.add_beam(
                    MAT["BrushedSteel"],
                    (px + lx, 0.24, -0.34 + lz),
                    (px + lx * 0.45, 2.38, -0.34 + lz * 0.45),
                    thickness=0.032,
                )
        for h in (0.65, 1.10, 1.55, 2.00):
            m.add_box(MAT["BrushedSteel"], px, h, -0.34, 0.18, 0.025, 0.18)
        # Cantilevered High-Output LED Broadcast Headframe
        m.add_box(MAT["BrushedSteel"], px, 2.46, -0.28, 0.66, 0.32, 0.10)
        for r in range(3):
            for c in range(4):
                lx = px - 0.22 + c * 0.145
                ly = 2.36 + r * 0.095
                m.add_box(MAT["FloodlightEmissive"], lx, ly, -0.22, 0.11, 0.07, 0.03)
        m.add_box(MAT["ChampionshipGold"], px, 2.64, -0.28, 0.68, 0.04, 0.12)
    return m


# ---------------------------------------------------------------------------
# TIER 2: TRAINING PITCHES, HIGH-PERFORMANCE & INDOOR ARENA
# ---------------------------------------------------------------------------
def build_first_team_pitch_alpha(segments: int = 16, include_gantry: bool = False) -> MultiMaterialMeshBuilder:
    """Footprint: 4 x 3 tiles (-1.88..+1.88 x -1.38..+1.38)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(12, segments // 2)
    m_seg = max(8, segments // 3)
    m.add_pitch_surface(0, 0.0, 0, 3.52, 2.42, stripes=10, circle_segments=c_seg)
    # Recessed Glass Technical Dugouts on North Touchline
    for dx in (-0.82, 0.82):
        m.add_box(MAT["DarkSlateStone"], dx, 0.15, -1.30, 0.66, 0.22, 0.20)
        m.add_box(MAT["CurtainWallGlass"], dx, 0.17, -1.28, 0.62, 0.18, 0.16)
        m.add_box(MAT["GtexEmeraldAccent"], dx, 0.27, -1.30, 0.68, 0.03, 0.22)
    # 4 Perimeter Training Floodlight Masts
    for px in (-1.78, 1.78):
        for pz in (-1.24, 1.24):
            m.add_cylinder(MAT["BrushedSteel"], px, 0.04, pz, 0.04, 0.025, 1.12, segments=m_seg)
            m.add_box(MAT["FloodlightEmissive"], px, 1.18, pz, 0.20, 0.08, 0.06)
    if include_gantry:
        m.add_box(MAT["ChampionshipGold"], 0, 0.24, 1.30, 1.25, 0.14, 0.06)
    return m


def build_first_team_pitch_beta(segments: int = 16) -> MultiMaterialMeshBuilder:
    """Footprint: 4 x 3 tiles (-1.88..+1.88 x -1.38..+1.38)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(12, segments // 2)
    m_seg = max(8, segments // 3)
    m.add_pitch_surface(0, 0.0, -0.14, 3.48, 2.14, stripes=8, circle_segments=c_seg)
    # 4-Lane High-Intensity Terracotta Sprint Track on South Touchline
    m.add_box(MAT["TerracottaTimber"], 0, 0.045, 1.16, 3.52, 0.03, 0.34)
    for lane in (-0.12, 0.0, 0.12):
        m.add_box(MAT["CrispWhiteLine"], 0, 0.062, 1.16 + lane, 3.48, 0.008, 0.015)
    # 2-Storey Tactical Video & Drone Telemetry Control Tower at North Midfield
    m.add_mullioned_glass_wing(
        0, 0.04, -1.28, 0.72, 0.68, 0.26, storeys=2, mullion_cols=3, accent_mat=MAT["ChampionshipGold"]
    )
    # 4 Telemetry Camera Masts
    for px in (-1.76, 1.76):
        for pz in (-1.26, 1.02):
            m.add_cylinder(MAT["BrushedSteel"], px, 0.04, pz, 0.035, 0.02, 0.95, segments=m_seg)
            m.add_box(MAT["FloodlightEmissive"], px, 1.00, pz, 0.16, 0.06, 0.05)
    return m


def build_high_performance_centre(segments: int = 20) -> MultiMaterialMeshBuilder:
    """
    Footprint: 3 x 3 tiles (-1.42..+1.42 x -1.42..+1.42).
    Inspired by the twin-curved glass & solar pavilion in the Manchester reference image.
    """
    m = MultiMaterialMeshBuilder()
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 2.82, 0.08, 2.82)
    # West & East Curved-Front Glass Biomechanics Wings
    for side in (-0.74, 0.74):
        m.add_mullioned_glass_wing(
            side, 0.08, -0.10, 1.02, 0.76, 1.92, storeys=2, mullion_cols=4, accent_mat=MAT["GtexEmeraldAccent"]
        )
        # Rounded Glass Rotunda Front on each wing
        m.add_cylinder(MAT["CurtainWallGlass"], side, 0.08, 0.82, 0.48, 0.48, 0.74, segments=segments)
        m.add_cylinder(MAT["ArchitecturalConcrete"], side, 0.82, 0.82, 0.50, 0.50, 0.05, segments=segments)
        # Rooftop Photovoltaic Solar Array on each wing
        for sz in (-0.65, -0.15, 0.35):
            m.add_box(MAT["SolarPanelBlue"], side, 0.88, sz, 0.68, 0.03, 0.36)
    # Central Dark-Slate & Gold Spine Atrium connecting the twin wings
    m.add_box(MAT["DarkSlateStone"], 0, 0.58, -0.05, 0.52, 1.02, 2.18)
    m.add_box(MAT["ChampionshipGold"], 0, 1.11, -0.05, 0.56, 0.05, 2.22)
    m.add_box(MAT["ChampionshipGold"], 0, 0.42, 1.06, 0.24, 0.52, 0.06)
    # Outdoor 3-Lane Biomechanics Sprint Strip along North Edge
    m.add_box(MAT["TerracottaTimber"], 0, 0.055, -1.24, 2.62, 0.03, 0.26)
    return m


def build_indoor_training_arena(segments: int = 20) -> MultiMaterialMeshBuilder:
    """
    Footprint: 4 x 3 tiles (-1.88..+1.88 x -1.38..+1.38).
    Arched clear-span barrel-vaulted indoor arena with diagonal buttress ribs, glass curtain walls, and rooftop solar array.
    """
    m = MultiMaterialMeshBuilder()
    c_seg = max(12, segments // 2)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 3.76, 0.08, 2.76)
    # Interior Hybrid Pitch visible through glass facades
    m.add_pitch_surface(0, 0.05, 0, 3.12, 2.02, stripes=8, circle_segments=c_seg)
    # Mullioned Curtain-Wall Glass Perimeter Walls
    m.add_mullioned_glass_wing(
        0, 0.08, 0, 3.44, 0.62, 2.38, storeys=2, mullion_cols=8, accent_mat=MAT["GtexEmeraldAccent"]
    )
    # Arched Barrel-Vault Roof Shell + Skylight Strip + Solar Panels
    steps = max(14, segments // 2)
    mid_lo = int(steps * 0.35)
    mid_hi = int(steps * 0.60)
    for i in range(steps):
        z0 = -1.22 + (2.44 * i) / steps
        z1 = -1.22 + (2.44 * (i + 1)) / steps
        a0 = math.pi * (i / steps)
        a1 = math.pi * ((i + 1) / steps)
        y0 = 0.70 + math.sin(a0) * 0.48
        y1 = 0.70 + math.sin(a1) * 0.48
        mat = MAT["CurtainWallGlass"] if mid_lo <= i <= mid_hi else MAT["DarkSlateStone"]
        m.add_quad(mat, (-1.74, y0, z0), (1.74, y0, z0), (1.74, y1, z1), (-1.74, y1, z1))
    # 7 Exterior Steel Structural Arch Ribs & Sloped Buttress Struts
    for rx in (-1.56, -1.04, -0.52, 0.0, 0.52, 1.04, 1.56):
        m.add_box(MAT["BrushedSteel"], rx, 1.19, 0, 0.06, 0.05, 2.46)
        m.add_beam(MAT["BrushedSteel"], (rx, 0.08, -1.34), (rx, 0.72, -1.18), thickness=0.055)
        m.add_beam(MAT["BrushedSteel"], (rx, 0.08, 1.34), (rx, 0.72, 1.18), thickness=0.055)
    # Rooftop Solar Panels along Crown
    for sx in (-1.10, -0.38, 0.38, 1.10):
        m.add_box(MAT["SolarPanelBlue"], sx, 1.21, 0, 0.54, 0.03, 0.72)
    m.add_box(MAT["ChampionshipGold"], 0, 0.72, 1.22, 3.52, 0.04, 0.06)
    return m


# ---------------------------------------------------------------------------
# TIER 3: MEDICAL & HYDROTHERAPY RECOVERY HUB (3x3)
# ---------------------------------------------------------------------------
def build_recovery_hydro_hub(segments: int = 18) -> MultiMaterialMeshBuilder:
    """
    Footprint: 3 x 3 tiles (-1.42..+1.42 x -1.42..+1.42).
    Inspired by the outdoor hydrotherapy pool deck + glass wellness atrium + warm timber spa wing in the reference art.
    """
    m = MultiMaterialMeshBuilder()
    c_seg = max(12, segments // 2)
    m.add_box(MAT["ArchitecturalConcrete"], 0, 0.04, 0, 2.82, 0.08, 2.82)
    # North Glass-Roofed Medical & MRI Diagnostics Hall
    m.add_mullioned_glass_wing(
        -0.22, 0.08, -0.78, 2.24, 0.72, 0.96, storeys=2, mullion_cols=6, accent_mat=MAT["GtexEmeraldAccent"]
    )
    for sx in (-0.95, -0.45, 0.05, 0.55):
        m.add_box(MAT["SolarPanelBlue"], sx, 0.84, -0.78, 0.38, 0.03, 0.72)
    # East Warm Timber/Terracotta Cryotherapy & Sauna Pavilion
    m.add_box(MAT["TerracottaTimber"], 0.96, 0.40, 0.28, 0.68, 0.64, 1.82)
    m.add_box(MAT["CurtainWallGlass"], 0.96, 0.42, 0.28, 0.72, 0.44, 1.56)
    m.add_box(MAT["ChampionshipGold"], 0.96, 0.74, 0.28, 0.74, 0.04, 1.86)
    # West & Central Heated Outdoor Hydrotherapy Lap Pool + Contrast Plunge Pools
    m.add_box(MAT["DarkSlateStone"], -0.36, 0.09, 0.42, 1.76, 0.06, 1.62)
    # Main 25m Lap Pool Water + Lane Lines
    m.add_box(MAT["HydroPoolWater"], -0.22, 0.13, 0.48, 1.18, 0.04, 1.24)
    for lx in (-0.48, -0.22, 0.04):
        m.add_box(MAT["CrispWhiteLine"], lx, 0.152, 0.48, 0.02, 0.008, 1.16)
    # Circular Cold/Hot Hydro Plunge Pool
    m.add_cylinder(MAT["HydroPoolWater"], -0.98, 0.10, 0.05, 0.24, 0.24, 0.05, segments=c_seg)
    # Poolside Loungers
    for lz in (0.15, 0.45, 0.75, 1.02):
        m.add_box(MAT["CrispWhiteLine"], -1.06, 0.15, lz, 0.22, 0.04, 0.12)
    return m


# ---------------------------------------------------------------------------
# TIER 4: ELITE ACADEMY & YOUTH PRECINCT (4x3)
# ---------------------------------------------------------------------------
def build_elite_academy_complex(segments: int = 18, variant_crest: bool = False) -> MultiMaterialMeshBuilder:
    """Footprint: 4 x 3 tiles (-1.88..+1.88 x -1.38..+1.38)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(12, segments // 2)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 3.76, 0.08, 2.76)
    # West 4-Storey Scholar Boarding Residence Tower
    m.add_mullioned_glass_wing(
        -1.26, 0.08, 0.0, 0.96, 1.12, 2.32, storeys=4, mullion_cols=4, accent_mat=MAT["GtexEmeraldAccent"]
    )
    # East 3-Storey Tactical Classrooms & Lecture Theatre Wing
    m.add_mullioned_glass_wing(
        1.26, 0.08, 0.0, 0.96, 0.88, 2.32, storeys=3, mullion_cols=4, accent_mat=MAT["ChampionshipGold"]
    )
    # North Elevated Glass Skybridge & Rotunda Atrium
    m.add_mullioned_glass_wing(
        0, 0.56, -0.78, 1.64, 0.42, 0.62, storeys=1, mullion_cols=5, accent_mat=MAT["ChampionshipGold"]
    )
    m.add_cylinder(MAT["CurtainWallGlass"], 0, 0.08, -0.78, 0.42, 0.42, 0.96, segments=segments)
    m.add_cylinder(MAT["ChampionshipGold"], 0, 1.04, -0.78, 0.46, 0.46, 0.05, segments=segments)
    # Rooftop Solar Panels on Boarding & Classroom Wings
    for sz in (-0.75, 0.0, 0.75):
        m.add_box(MAT["SolarPanelBlue"], -1.26, 1.24, sz, 0.68, 0.03, 0.52)
        m.add_box(MAT["SolarPanelBlue"], 1.26, 1.00, sz, 0.68, 0.03, 0.52)
    # South-Central Technical Futsal / Rondo Courtyard Pitch
    m.add_pitch_surface(0, 0.05, 0.34, 1.32, 1.38, stripes=6, circle_segments=c_seg)
    if variant_crest:
        m.add_cylinder(MAT["GtexEmeraldAccent"], 0, 1.09, -0.78, 0.24, 0.24, 0.06, segments=c_seg)
    return m


def build_academy_youth_pitch(segments: int = 16) -> MultiMaterialMeshBuilder:
    """Footprint: 4 x 3 tiles (-1.88..+1.88 x -1.38..+1.38)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(12, segments // 2)
    m_seg = max(8, segments // 3)
    m.add_pitch_surface(0, 0.0, 0.14, 3.48, 2.16, stripes=8, circle_segments=c_seg)
    # Covered Scout & Family Cantilevered Viewing Tribune on North Touchline
    for step in range(3):
        m.add_box(MAT["ArchitecturalConcrete"], 0, 0.12 + step * 0.10, -1.14 - step * 0.08, 2.36, 0.10, 0.16)
    m.add_box(MAT["CurtainWallGlass"], 0, 0.44, -1.30, 2.36, 0.20, 0.12)
    m.add_box(MAT["GtexEmeraldAccent"], 0, 0.56, -1.18, 2.44, 0.05, 0.44)
    m.add_box(MAT["ChampionshipGold"], 0, 0.60, -1.00, 2.46, 0.03, 0.08)
    # 4 Youth Floodlight Masts
    for px in (-1.76, 1.76):
        for pz in (-1.26, 1.26):
            m.add_cylinder(MAT["BrushedSteel"], px, 0.04, pz, 0.035, 0.02, 0.98, segments=m_seg)
            m.add_box(MAT["FloodlightEmissive"], px, 1.04, pz, 0.18, 0.07, 0.05)
    return m


# ---------------------------------------------------------------------------
# TIER 5: CLUB HEADQUARTERS, VIP HOSPITALITY & FLEET TERMINAL (3x2)
# ---------------------------------------------------------------------------
def build_club_hq_operations(segments: int = 20, twin_flagpoles: bool = True) -> MultiMaterialMeshBuilder:
    """Footprint: 3 x 2 tiles (-1.42..+1.42 x -0.92..+0.92)."""
    m = MultiMaterialMeshBuilder()
    m_seg = max(8, segments // 3)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 2.82, 0.08, 1.84)
    # Podium Reception & Global Scouting War Room
    m.add_mullioned_glass_wing(
        0, 0.08, 0, 2.46, 0.48, 1.52, storeys=1, mullion_cols=6, accent_mat=MAT["GtexEmeraldAccent"]
    )
    # Flagship 4-Storey Executive Boardroom Glass Tower
    m.add_mullioned_glass_wing(
        0, 0.56, -0.06, 1.68, 0.92, 1.18, storeys=3, mullion_cols=5, accent_mat=MAT["ChampionshipGold"]
    )
    # Front VIP Rotunda Entrance Canopy & Reflecting Pool
    m.add_cylinder(MAT["CurtainWallGlass"], 0, 0.08, 0.68, 0.34, 0.34, 0.52, segments=segments)
    m.add_cylinder(MAT["ChampionshipGold"], 0, 0.60, 0.68, 0.38, 0.38, 0.04, segments=segments)
    m.add_box(MAT["HydroPoolWater"], -0.82, 0.085, 0.72, 0.64, 0.02, 0.22)
    m.add_box(MAT["HydroPoolWater"], 0.82, 0.085, 0.72, 0.64, 0.02, 0.22)
    # Rooftop Executive Helipad ('H' Pad)
    m.add_cylinder(MAT["DarkSlateStone"], 0, 1.52, -0.06, 0.48, 0.48, 0.04, segments=segments)
    m.add_cylinder(MAT["ChampionshipGold"], 0, 1.56, -0.06, 0.42, 0.42, 0.015, segments=segments)
    m.add_box(MAT["CrispWhiteLine"], -0.12, 1.58, -0.06, 0.04, 0.012, 0.28)
    m.add_box(MAT["CrispWhiteLine"], 0.12, 1.58, -0.06, 0.04, 0.012, 0.28)
    m.add_box(MAT["CrispWhiteLine"], 0, 1.58, -0.06, 0.24, 0.012, 0.04)
    if twin_flagpoles:
        for fx in (-1.18, 1.18):
            m.add_cylinder(MAT["ChampionshipGold"], fx, 0.08, 0.76, 0.02, 0.015, 0.85, segments=m_seg)
    return m


def build_vip_hospitality_pavilion(segments: int = 20) -> MultiMaterialMeshBuilder:
    """Footprint: 3 x 2 tiles (-1.42..+1.42 x -0.92..+0.92)."""
    m = MultiMaterialMeshBuilder()
    m_seg = max(8, segments // 3)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 2.82, 0.08, 1.84)
    # Double-Height Panoramic Glass Hospitality Pavilion
    m.add_mullioned_glass_wing(
        0, 0.08, -0.04, 2.38, 0.76, 1.42, storeys=2, mullion_cols=6, accent_mat=MAT["ChampionshipGold"]
    )
    # Rooftop Champagne & Sponsor Viewing Rotunda
    m.add_cylinder(MAT["CurtainWallGlass"], 0, 0.86, -0.04, 0.56, 0.56, 0.30, segments=segments)
    m.add_cylinder(MAT["ChampionshipGold"], 0, 1.16, -0.04, 0.62, 0.62, 0.05, segments=segments)
    # VIP Red/Gold Arrival Carpet & Portico Columns
    m.add_box(MAT["ChampionshipGold"], 0, 0.085, 0.76, 0.68, 0.02, 0.24)
    for cx in (-0.85, -0.32, 0.32, 0.85):
        m.add_cylinder(MAT["BrushedSteel"], cx, 0.08, 0.72, 0.03, 0.03, 0.76, segments=m_seg)
    return m


def build_vip_skybox_concourse(segments: int = 20) -> MultiMaterialMeshBuilder:
    """
    Footprint: 3 x 2 tiles (-1.42..+1.42 x -0.92..+0.92).
    Elevated Twin-Rotunda Skybox Concourse Gallery with Cantilevered Viewing Terraces & Rooftop Solar Pergola Fins.
    """
    m = MultiMaterialMeshBuilder()
    c_seg = max(10, segments // 2)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 2.82, 0.08, 1.84)
    # Ground-Floor VIP Arrival Colonnade
    m.add_mullioned_glass_wing(
        0, 0.08, -0.10, 2.18, 0.42, 1.18, storeys=1, mullion_cols=5, accent_mat=MAT["GtexEmeraldAccent"]
    )
    # Upper Cantilevered Skybox Gallery Wing
    m.add_mullioned_glass_wing(
        0, 0.50, 0.02, 2.52, 0.56, 1.38, storeys=2, mullion_cols=7, accent_mat=MAT["ChampionshipGold"]
    )
    # Twin Helical Glass Stair Rotundas at West & East Ends
    for sx in (-1.08, 1.08):
        m.add_cylinder(MAT["CurtainWallGlass"], sx, 0.08, 0.42, 0.26, 0.26, 1.12, segments=c_seg)
        m.add_cylinder(MAT["ChampionshipGold"], sx, 1.20, 0.42, 0.28, 0.28, 0.04, segments=c_seg)
    # Rooftop Solar Pergola Louvers & Terrace Deck
    for lx in (-0.64, -0.22, 0.22, 0.64):
        m.add_box(MAT["SolarPanelBlue"], lx, 1.16, 0.02, 0.28, 0.03, 0.96)
        m.add_box(MAT["BrushedSteel"], lx, 1.12, 0.02, 0.04, 0.08, 1.04)
    return m


def build_executive_fleet_terminal(segments: int = 16) -> MultiMaterialMeshBuilder:
    """Footprint: 3 x 2 tiles (-1.42..+1.42 x -0.92..+0.92)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(10, segments // 2)
    m.add_box(MAT["DarkSlateStone"], 0, 0.04, 0, 2.82, 0.08, 1.84)
    # VIP Departure Lounge at North Edge + Rounded Glass Control Rotunda
    m.add_mullioned_glass_wing(
        0, 0.08, -0.58, 2.42, 0.46, 0.48, storeys=1, mullion_cols=6, accent_mat=MAT["GtexEmeraldAccent"]
    )
    m.add_cylinder(MAT["CurtainWallGlass"], 0, 0.08, -0.36, 0.24, 0.24, 0.52, segments=c_seg)
    # Cantilevered Gull-Wing Solar Transit Canopy + V-Columns
    for cx in (-0.92, 0.0, 0.92):
        m.add_beam(MAT["BrushedSteel"], (cx, 0.08, -0.32), (cx - 0.14, 0.78, 0.05), thickness=0.05)
        m.add_beam(MAT["BrushedSteel"], (cx, 0.08, -0.32), (cx + 0.14, 0.78, 0.05), thickness=0.05)
    m.add_box(MAT["ArchitecturalConcrete"], 0, 0.80, -0.10, 2.48, 0.06, 1.24)
    m.add_box(MAT["SolarPanelBlue"], 0, 0.84, -0.10, 2.32, 0.03, 1.08)
    m.add_box(MAT["ChampionshipGold"], 0, 0.81, -0.10, 2.52, 0.04, 1.28)
    # 2 Detailed GTEX Vanguard XII First-Team Luxury Coaches
    for bx in (-0.64, 0.64):
        m.add_box(MAT["DarkSlateStone"], bx, 0.26, 0.24, 0.46, 0.32, 1.16)
        m.add_box(MAT["CurtainWallGlass"], bx, 0.31, 0.24, 0.48, 0.15, 1.10)
        m.add_box(MAT["ChampionshipGold"], bx, 0.20, 0.24, 0.49, 0.035, 1.18)
        m.add_box(MAT["GtexEmeraldAccent"], bx, 0.43, 0.24, 0.40, 0.03, 1.04)
        m.add_box(MAT["FloodlightEmissive"], bx - 0.14, 0.18, 0.83, 0.08, 0.04, 0.02)
        m.add_box(MAT["FloodlightEmissive"], bx + 0.14, 0.18, 0.83, 0.08, 0.04, 0.02)
    return m


# ---------------------------------------------------------------------------
# TIER 6: 5 DISTINCT CONSTRUCTION STAGES + CRANE COMPOUND + LANDSCAPING & ROADS
# ---------------------------------------------------------------------------
def build_construction_crane_compound(segments: int = 16) -> MultiMaterialMeshBuilder:
    """
    Footprint: 3 x 3 tiles (-1.42..+1.42 x -1.42..+1.42).
    Dedicated Heavy Dual-Tower Crane & Engineering Logistics Compound (distinct from Stage 4 Structural).
    """
    m = MultiMaterialMeshBuilder()
    c_seg = max(10, segments // 2)
    m.add_box(MAT["ExcavatedEarth"], 0, 0.03, 0, 2.74, 0.06, 2.74)
    m.add_box(MAT["DarkSlateStone"], 0, 0.07, 0, 2.36, 0.04, 2.36)
    # Twin Engineering & Site Command Portacabins
    for pz in (0.78, 0.32):
        m.add_box(MAT["ArchitecturalConcrete"], -0.78, 0.20, pz, 0.72, 0.24, 0.32)
        m.add_box(MAT["CurtainWallGlass"], -0.78, 0.22, pz, 0.74, 0.10, 0.24)
        m.add_box(MAT["GtexEmeraldAccent"], -0.78, 0.33, pz, 0.74, 0.03, 0.34)
    # Cylindrical Water/Concrete Silo Tanks
    for sx in (0.52, 0.94):
        m.add_cylinder(MAT["BrushedSteel"], sx, 0.08, 0.76, 0.16, 0.16, 0.62, segments=c_seg)
        m.add_cylinder(MAT["ChampionshipGold"], sx, 0.70, 0.76, 0.17, 0.17, 0.04, segments=c_seg)
    # Primary Heavy Tower Crane (NE Quadrant) + Secondary Auxiliary Derrick Crane (SW Quadrant)
    for cx, cz, h, jib_len, jib_cx in [(0.78, -0.74, 2.32, 1.88, 0.14), (-0.74, -0.68, 1.64, 1.32, -0.34)]:
        m.add_box(MAT["DarkSlateStone"], cx, 0.14, cz, 0.38, 0.14, 0.38)
        m.add_cylinder(MAT["BrushedSteel"], cx, 0.20, cz, 0.14, 0.14, 0.08, segments=c_seg)
        m.add_box(MAT["ConstructionSafetyAmber"], cx, 0.20 + h / 2.0, cz, 0.16, h, 0.16)
        m.add_box(MAT["ConstructionSafetyAmber"], jib_cx, 0.24 + h, cz, jib_len, 0.11, 0.11)
        m.add_beam(MAT["BrushedSteel"], (cx, 0.48 + h, cz), (jib_cx - jib_len * 0.35, 0.26 + h, cz), thickness=0.025)
    return m


def build_construction_stage_model(stage_num: int, segments: int = 16) -> MultiMaterialMeshBuilder:
    """
    Footprint: 3 x 3 tiles (-1.42..+1.42 x -1.42..+1.42), uniformly scaled to target footprint in Three.js.
    Self-contained stage geometry so each stage visually transforms an empty plot into a completed facility
    without overlapping the completed mesh.
    """
    m = MultiMaterialMeshBuilder()
    c_seg = max(10, segments // 2)
    # Base cleared construction pad & perimeter safety fencing
    m.add_box(MAT["ExcavatedEarth"], 0, 0.03, 0, 2.72, 0.06, 2.72)
    for s in (-1.30, 1.30):
        m.add_box(MAT["ConstructionSafetyAmber"], 0, 0.12, s, 2.60, 0.10, 0.04)
        m.add_box(MAT["ConstructionSafetyAmber"], s, 0.12, 0, 0.04, 0.10, 2.60)
    for px in (-1.30, -0.65, 0.0, 0.65, 1.30):
        for pz in (-1.30, 1.30):
            m.add_box(MAT["DarkSlateStone"], px, 0.13, pz, 0.06, 0.16, 0.06)
    # Site Engineering Portacabin Office (SW Corner)
    m.add_box(MAT["ArchitecturalConcrete"], -0.92, 0.18, 0.94, 0.56, 0.24, 0.34)
    m.add_box(MAT["CurtainWallGlass"], -0.92, 0.20, 0.94, 0.58, 0.10, 0.26)
    m.add_box(MAT["GtexEmeraldAccent"], -0.92, 0.31, 0.94, 0.58, 0.03, 0.36)

    if stage_num == 1:
        # Stage 1 (Site Prep): Surveyor stakes, water tank cylinder, stacked timber/steel pallets, bulldozer vehicle
        for sx in (-0.75, 0.75):
            for sz in (-0.75, 0.45):
                m.add_box(MAT["ChampionshipGold"], sx, 0.14, sz, 0.04, 0.18, 0.04)
        m.add_cylinder(MAT["BrushedSteel"], -0.92, 0.06, 0.42, 0.16, 0.16, 0.28, segments=c_seg)
        m.add_box(MAT["TerracottaTimber"], 0.78, 0.12, 0.86, 0.42, 0.12, 0.32)
        m.add_box(MAT["BrushedSteel"], 0.25, 0.11, 0.92, 0.48, 0.10, 0.24)
        # Yellow Site Bulldozer
        m.add_box(MAT["ConstructionSafetyAmber"], -0.15, 0.16, -0.15, 0.44, 0.20, 0.30)
        m.add_box(MAT["DarkSlateStone"], -0.15, 0.09, -0.15, 0.48, 0.08, 0.36)
        m.add_box(MAT["BrushedSteel"], 0.16, 0.14, -0.15, 0.08, 0.16, 0.42)

    elif stage_num == 2:
        # Stage 2 (Groundworks): Deep stepped excavation pit, trench pipes, soil mounds, excavator arm
        m.add_box(MAT["DarkSlateStone"], 0, 0.06, -0.12, 1.92, 0.08, 1.68)
        m.add_box(MAT["ExcavatedEarth"], 0, 0.08, -0.12, 1.72, 0.06, 1.48)
        # Conical Excavated Soil Mounds
        m.add_cylinder(MAT["ExcavatedEarth"], 0.88, 0.06, 0.86, 0.38, 0.10, 0.30, segments=c_seg)
        m.add_cylinder(MAT["ExcavatedEarth"], 0.42, 0.06, 0.94, 0.28, 0.08, 0.22, segments=c_seg)
        # Articulated Excavator on Pit Rim
        m.add_box(MAT["ConstructionSafetyAmber"], -0.82, 0.18, -0.20, 0.38, 0.22, 0.32)
        m.add_beam(MAT["ConstructionSafetyAmber"], (-0.65, 0.24, -0.20), (-0.20, 0.52, -0.20), thickness=0.06)
        m.add_beam(MAT["ConstructionSafetyAmber"], (-0.20, 0.52, -0.20), (0.05, 0.14, -0.20), thickness=0.05)

    elif stage_num == 3:
        # Stage 3 (Foundations): Poured concrete mat, 3x3 footing piers, vertical rebar cages, concrete mixer drum & pump boom
        m.add_box(MAT["ArchitecturalConcrete"], 0, 0.12, -0.12, 1.96, 0.16, 1.72)
        for cx in (-0.72, 0.0, 0.72):
            for cz in (-0.72, -0.12, 0.48):
                m.add_box(MAT["DarkSlateStone"], cx, 0.24, cz, 0.24, 0.10, 0.24)
                m.add_box(MAT["BrushedSteel"], cx, 0.42, cz, 0.10, 0.32, 0.10)
        # Concrete Mixer / Pump Truck, Cylindrical Batch Silo & Pouring Boom
        m.add_box(MAT["ConstructionSafetyAmber"], 0.82, 0.18, 0.92, 0.52, 0.22, 0.28)
        m.add_cylinder(MAT["ArchitecturalConcrete"], 0.32, 0.06, 0.92, 0.16, 0.16, 0.38, segments=c_seg)
        m.add_beam(MAT["GtexEmeraldAccent"], (0.75, 0.28, 0.92), (0.10, 0.68, 0.05), thickness=0.05)

    elif stage_num == 4:
        # Stage 4 (Structural): Multi-bay steel/concrete frame, raked ribs, shoring struts, and tall lattice tower crane
        m.add_box(MAT["ArchitecturalConcrete"], 0, 0.12, -0.12, 1.98, 0.16, 1.74)
        # Concrete Elevator/Stair Core + 2 Floor Plates
        m.add_box(MAT["ArchitecturalConcrete"], -0.45, 0.62, -0.12, 0.48, 0.96, 0.48)
        m.add_box(MAT["ArchitecturalConcrete"], 0, 0.54, -0.12, 1.88, 0.07, 1.64)
        m.add_box(MAT["ArchitecturalConcrete"], 0, 0.96, -0.12, 1.88, 0.07, 1.64)
        # Structural Steel Columns & Raked Grandstand/Roof Ribs
        for cx in (-0.76, -0.25, 0.25, 0.76):
            for cz in (-0.76, 0.52):
                m.add_box(MAT["BrushedSteel"], cx, 0.62, cz, 0.09, 0.98, 0.09)
            m.add_beam(MAT["BrushedSteel"], (cx, 0.98, -0.76), (cx, 1.24, 0.52), thickness=0.045)
        # Exterior Diagonal Timber/Steel Shoring Props (matching reference image 2)
        for sx in (-0.76, 0.0, 0.76):
            m.add_beam(MAT["TerracottaTimber"], (sx, 0.06, 0.92), (sx, 0.56, 0.70), thickness=0.04)
        # Tall Lattice Tower Crane (Mast, Slewing Ring Cylinder, Cab, Counter-Jib, Jib, Hoist Cable & Suspended Load)
        m.add_box(MAT["DarkSlateStone"], 0.94, 0.14, -0.88, 0.36, 0.16, 0.36)
        m.add_cylinder(MAT["BrushedSteel"], 0.94, 0.22, -0.88, 0.14, 0.14, 0.08, segments=c_seg)
        m.add_box(MAT["ConstructionSafetyAmber"], 0.94, 1.22, -0.88, 0.16, 2.16, 0.16)
        m.add_box(MAT["ConstructionSafetyAmber"], 0.22, 2.26, -0.88, 1.96, 0.12, 0.12)
        m.add_box(MAT["DarkSlateStone"], 1.28, 2.22, -0.88, 0.28, 0.18, 0.22)
        m.add_beam(MAT["BrushedSteel"], (0.94, 2.52, -0.88), (-0.42, 2.28, -0.88), thickness=0.025)
        m.add_beam(MAT["BrushedSteel"], (0.94, 2.52, -0.88), (1.32, 2.28, -0.88), thickness=0.025)
        m.add_box(MAT["BrushedSteel"], -0.38, 1.82, -0.88, 0.025, 0.82, 0.025)
        m.add_box(MAT["ChampionshipGold"], -0.38, 1.38, -0.88, 0.42, 0.14, 0.22)

    else:
        # Stage 5 (Finishing): Enclosed shell, 80% curtain-wall glazing, exterior scaffolding grid, rooftop solar & hoist
        m.add_mullioned_glass_wing(
            0, 0.08, -0.10, 1.94, 1.02, 1.68, storeys=3, mullion_cols=5, accent_mat=MAT["GtexEmeraldAccent"]
        )
        # Exterior Multi-Tier Tubular Scaffolding Frame around Front & Side Facades
        for sy in (0.36, 0.68, 1.00):
            m.add_box(MAT["BrushedSteel"], 0, sy, 0.80, 2.04, 0.025, 0.025)
            m.add_box(MAT["BrushedSteel"], 0, sy, -1.00, 2.04, 0.025, 0.025)
        for sx in (-0.98, -0.48, 0.0, 0.48, 0.98):
            m.add_box(MAT["BrushedSteel"], sx, 0.58, 0.80, 0.025, 1.04, 0.025)
        # Rooftop Solar Panels, HVAC Cylinder & Finishing Derrick Hoist
        m.add_box(MAT["SolarPanelBlue"], -0.45, 1.14, -0.10, 0.64, 0.03, 0.82)
        m.add_cylinder(MAT["BrushedSteel"], 0.28, 1.12, -0.25, 0.18, 0.18, 0.16, segments=c_seg)
        m.add_box(MAT["ConstructionSafetyAmber"], 0.68, 1.32, 0.45, 0.10, 0.42, 0.10)
        m.add_beam(MAT["ConstructionSafetyAmber"], (0.68, 1.50, 0.45), (0.68, 1.62, 0.92), thickness=0.04)

    return m


def build_campus_tree_cluster(segments: int = 12) -> MultiMaterialMeshBuilder:
    """Footprint: 1 x 1 tile (-0.46..+0.46 x -0.46..+0.46)."""
    m = MultiMaterialMeshBuilder()
    m.add_cylinder(MAT["DarkSlateStone"], 0, 0.01, 0, 0.42, 0.40, 0.03, segments=segments)
    for tx, tz, r, h in [(-0.18, -0.14, 0.22, 0.64), (0.18, 0.14, 0.19, 0.54), (0.04, -0.18, 0.16, 0.48)]:
        m.add_cylinder(MAT["ExcavatedEarth"], tx, 0.02, tz, 0.045, 0.035, 0.22, segments=max(8, segments // 3))
        m.add_cylinder(MAT["FoliageCanopy"], tx, 0.18, tz, r, r * 0.42, h * 0.52, segments=segments)
        m.add_cylinder(MAT["PitchStripeLight"], tx, 0.38, tz, r * 0.76, 0.02, h * 0.48, segments=segments)
    return m


def build_campus_road_plaza_segment(segments: int = 16) -> MultiMaterialMeshBuilder:
    """Footprint: 1 x 1 tile (-0.48..+0.48 x -0.48..+0.48)."""
    m = MultiMaterialMeshBuilder()
    c_seg = max(8, segments // 3)
    m.add_box(MAT["DarkSlateStone"], 0, 0.015, 0, 0.96, 0.03, 0.96)
    m.add_box(MAT["ArchitecturalConcrete"], -0.42, 0.03, 0, 0.12, 0.04, 0.96)
    m.add_box(MAT["ArchitecturalConcrete"], 0.42, 0.03, 0, 0.12, 0.04, 0.96)
    m.add_box(MAT["ChampionshipGold"], 0, 0.034, 0, 0.04, 0.012, 0.44)
    m.add_box(MAT["GtexEmeraldAccent"], -0.36, 0.048, 0, 0.02, 0.012, 0.96)
    m.add_box(MAT["GtexEmeraldAccent"], 0.36, 0.048, 0, 0.02, 0.012, 0.96)
    # Illuminated Boulevard Bollard on East Curb
    m.add_cylinder(MAT["BrushedSteel"], 0.42, 0.05, 0.0, 0.025, 0.025, 0.16, segments=c_seg)
    m.add_cylinder(MAT["FloodlightEmissive"], 0.42, 0.21, 0.0, 0.03, 0.03, 0.04, segments=c_seg)
    return m


MODEL_SPECS = [
    (
        "stadium_bowl_core",
        "stadium_structures",
        (6, 5),
        lambda seg=28: build_stadium_bowl_core(seg, include_west_portico=False, include_media_superstructure=False),
    ),
    (
        "stadium_main",
        "stadium_structures",
        (6, 5),
        lambda seg=28: build_stadium_bowl_core(seg, include_west_portico=True, include_media_superstructure=True),
    ),
    (
        "stadium_stand_expansion",
        "stadium_structures",
        (4, 2),
        lambda seg=20: build_stadium_stand_expansion(seg, twin_towers=False),
    ),
    (
        "north_stand_expansion",
        "stadium_structures",
        (4, 2),
        lambda seg=20: build_stadium_stand_expansion(seg, twin_towers=True),
    ),
    (
        "floodlight_pylon_array",
        "stadium_structures",
        (2, 2),
        lambda seg=16: build_floodlight_pylon_array(seg, dual_array=True),
    ),
    (
        "floodlight_tower",
        "stadium_structures",
        (2, 2),
        lambda seg=16: build_floodlight_pylon_array(seg, dual_array=False),
    ),
    ("vip_hospitality", "club_headquarters", (3, 2), build_vip_hospitality_pavilion),
    ("vip_skybox_concourse", "club_headquarters", (3, 2), build_vip_skybox_concourse),
    (
        "first_team_pitch_alpha",
        "training_facilities",
        (4, 3),
        lambda seg=16: build_first_team_pitch_alpha(seg, include_gantry=False),
    ),
    (
        "training_pitch",
        "training_facilities",
        (4, 3),
        lambda seg=16: build_first_team_pitch_alpha(seg, include_gantry=True),
    ),
    ("first_team_pitch_beta", "training_facilities", (4, 3), build_first_team_pitch_beta),
    ("high_performance_centre", "training_facilities", (3, 3), build_high_performance_centre),
    ("indoor_training_arena", "training_facilities", (4, 3), build_indoor_training_arena),
    ("recovery_hydro_hub", "medical_facilities", (3, 3), build_recovery_hydro_hub),
    (
        "elite_academy_complex",
        "academy_buildings",
        (4, 3),
        lambda seg=18: build_elite_academy_complex(seg, variant_crest=False),
    ),
    (
        "academy_complex",
        "academy_buildings",
        (4, 3),
        lambda seg=18: build_elite_academy_complex(seg, variant_crest=True),
    ),
    ("academy_youth_pitch", "academy_buildings", (4, 3), build_academy_youth_pitch),
    (
        "club_hq_operations",
        "club_headquarters",
        (3, 2),
        lambda seg=20: build_club_hq_operations(seg, twin_flagpoles=True),
    ),
    ("club_hq", "club_headquarters", (3, 2), lambda seg=20: build_club_hq_operations(seg, twin_flagpoles=False)),
    ("executive_fleet_terminal", "club_headquarters", (3, 2), build_executive_fleet_terminal),
    ("construction_crane_site", "construction_equipment", (3, 3), build_construction_crane_compound),
    ("stage_1_site_prep", "construction_equipment", (3, 3), lambda seg=16: build_construction_stage_model(1, seg)),
    ("stage_2_groundworks", "construction_equipment", (3, 3), lambda seg=16: build_construction_stage_model(2, seg)),
    ("stage_3_foundations", "construction_equipment", (3, 3), lambda seg=16: build_construction_stage_model(3, seg)),
    ("stage_4_structural", "construction_equipment", (3, 3), lambda seg=16: build_construction_stage_model(4, seg)),
    ("stage_5_finishing", "construction_equipment", (3, 3), lambda seg=16: build_construction_stage_model(5, seg)),
    ("campus_tree_cluster", "landscaping", (1, 1), build_campus_tree_cluster),
    ("campus_road_plaza_segment", "roads_infrastructure", (1, 1), build_campus_road_plaza_segment),
]


def main():
    CAMPUS_DIR.mkdir(parents=True, exist_ok=True)
    MASTERS_DIR.mkdir(parents=True, exist_ok=True)

    manifest_entries = []
    for key, category, (fw, fh), builder_fn in MODEL_SPECS:
        # 1. Master high-detail export
        master_mesh = builder_fn(48)
        m_verts, m_tris, m_mats, _, _ = master_mesh.bounds_and_stats()
        master_bytes = master_mesh.to_glb_bytes(f"{key}_master")
        master_path = MASTERS_DIR / f"{key}.master.glb"
        master_path.write_bytes(master_bytes)

        # 2. Optimized production export
        prod_mesh = builder_fn(28)
        p_verts, p_tris, p_mats, min_b, max_b = prod_mesh.bounds_and_stats()
        prod_bytes = prod_mesh.to_glb_bytes(key)
        prod_path = CAMPUS_DIR / f"{key}.glb"
        prod_path.write_bytes(prod_bytes)

        span_x = round(max_b[0] - min_b[0], 3)
        span_y = round(max_b[1] - min_b[1], 3)
        span_z = round(max_b[2] - min_b[2], 3)
        within_footprint = (span_x <= fw + 0.05) and (span_z <= fh + 0.05)
        assert within_footprint, f"Model {key} span ({span_x}x{span_z}) exceeds footprint ({fw}x{fh})!"

        manifest_entries.append(
            {
                "model_key": key,
                "category": category,
                "production_glb": f"/models/campus/{key}.glb",
                "master_glb": f"/models/campus/masters/{key}.master.glb",
                "footprint_tiles": {"width": fw, "depth": fh},
                "bounding_box_units": {
                    "min": [round(v, 3) for v in min_b],
                    "max": [round(v, 3) for v in max_b],
                    "span_x": span_x,
                    "span_y": span_y,
                    "span_z": span_z,
                    "conforms_to_grid_footprint": within_footprint,
                },
                "origin": "center-bottom (0.0, 0.0, 0.0)",
                "unit_scale": "1.0 scene unit = 1 campus grid tile (12m x 12m)",
                "production_stats": {
                    "vertices": p_verts,
                    "triangles": p_tris,
                    "pbr_materials": p_mats,
                    "size_bytes": len(prod_bytes),
                },
                "master_stats": {
                    "vertices": m_verts,
                    "triangles": m_tris,
                    "pbr_materials": m_mats,
                    "size_bytes": len(master_bytes),
                },
            }
        )
        print(
            f"[OK] {key:26s} | Footprint {fw}x{fh} (Span {span_x:4.2f}x{span_z:4.2f}, H {span_y:4.2f}) | Prod: {p_verts:4d}v / {p_tris:4d}t / {p_mats} mats ({len(prod_bytes):6d} B)"
        )

    manifest_json = {
        "schema_version": "2.1.0",
        "pipeline": "GTEX Club Dynasty Phase 2.1 Three.js WebGL Asset Library",
        "coordinate_system": "Right-handed Y-up, origin at center-bottom (0,0,0), 1 unit = 1 grid tile",
        "models": manifest_entries,
    }
    (CAMPUS_DIR / "manifest.json").write_text(json.dumps(manifest_json, indent=2), encoding="utf-8")

    md_lines = [
        "# GTEX 3D Campus Model Library Manifest (Phase 2.1 WebGL)",
        "",
        "- **Coordinate System:** Right-handed `Y`-up (`+Y` vertical, `X`/`Z` horizontal campus grid).",
        "- **Origin Point:** `center-bottom (0.0, 0.0, 0.0)` aligned to ground elevation `Y = 0`.",
        "- **Scale Contract:** `1.0` scene unit = `1` authoritative backend grid tile (`24 × 18` campus grid).",
        "- **Footprint Conformance:** All 28 models are strictly bounded within their `(W × D)` grid tile footprint with zero adjacent-tile overhang.",
        "- **Master vs. Production Exports:** High-segment master files reside in `public/models/campus/masters/*.master.glb`; optimized runtime exports reside in `public/models/campus/*.glb`.",
        "",
        "| Model Key | Category | Grid Footprint | BBox Span (X×Z×H) | Prod Vertices | Prod Triangles | PBR Materials | Prod Size |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for e in manifest_entries:
        ps = e["production_stats"]
        bb = e["bounding_box_units"]
        fw, fh = e["footprint_tiles"]["width"], e["footprint_tiles"]["depth"]
        md_lines.append(
            f"| `{e['model_key']}` | `{e['category']}` | `{fw}×{fh}` | `{bb['span_x']}×{bb['span_z']}×{bb['span_y']}` | {ps['vertices']} | {ps['triangles']} | {ps['pbr_materials']} | {ps['size_bytes']:,} B |"
        )
    (CAMPUS_DIR / "MODEL_LIBRARY_MANIFEST.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"\nGenerated {len(manifest_entries)} production + master GLB models and MODEL_LIBRARY_MANIFEST.md")


if __name__ == "__main__":
    main()
