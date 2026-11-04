# GTEX Club Dynasty Phase 2.1 — Visual & Technical Evidence Directory

This directory contains the canonical visual verification screenshots, Before-and-After comparisons, the 28-Model Production GLB Architectural Contact Sheet, and the PR #378 GLB Integrity Audit output for **GTEX Club Dynasty Phase 2.1** (`gemini/gtex-phase2-1-campus-builder`, incorporating PR #379).

---

## 1. Before-and-After Visual Comparisons

### A. Daylight Campus Overview: Phase 1 (2D Canvas Projection) → Phase 2 (Initial Low-Poly WebGL) → Phase 2.1 (High-Detail Multi-Material PBR WebGL 3D)

| Stage | Screenshot |
| :--- | :--- |
| **Before (Phase 1):** Custom 2D HTML5 Canvas isometric projection (no WebGL renderer or GLB loading) | ![Before Phase 1 Canvas](./before_phase1_canvas_2d_projection.png) |
| **Before (Phase 2 Initial):** First Three.js WebGL pass with low-poly procedural GLB boxes | ![Before Phase 2 Initial WebGL](./before_phase2_initial_lowpoly_webgl.png) |
| **After (Phase 2.1 Final):** High-detail multi-material PBR WebGL 3D Campus with cable-stayed stadium roof trusses, East Broadcast Media Superstructure, mullioned glass facades, and clarified 6-card KPI strip | ![After Phase 2.1 Daylight](./phase2_1_01_daylight_campus_overview.png) |

### B. Night Floodlights Mode: Initial Dim Pass → Phase 2.1 Calibrated 4-Rig Stadium & Precinct Floodlight Illumination

| Stage | Screenshot |
| :--- | :--- |
| **Before (Initial Night Pass):** Low-intensity point lights (`intensity=2.2`) left ground and facades dark under physical light decay | ![Before Night Mode](./before_phase2_initial_night_mode.png) |
| **After (Phase 2.1 Calibrated Night Mode):** 4 high-output physical `PointLight` rigs (`stadiumSpot1`, `stadiumSpot2`, `hqSpot`, `academySpot`) + cool moonlight fill (`0x93c5fd`) illuminating turf stripes, seating bowl, glass facades, and roads | ![After Phase 2.1 Night Mode](./phase2_1_02_night_campus_overview.png) |

---

## 2. 28 Production GLB Models — Architectural Contact Sheet (`4 × 7` Studio Renders)

All 28 production `.glb` assets from `frontend/react-shell/public/models/campus/*.glb` rendered individually via Three.js `WebGLRenderer` + `GLTFLoader` on their exact `(W × D)` grid footprint plinths:

![28 Production GLB Architectural Contact Sheet](./phase2_1_09_28_production_glb_contact_sheet.png)

- **GLB Integrity Audit ([`campus_glb_audit_report.md`](./campus_glb_audit_report.md)):**
  - **Files Audited:** `56` (`28` production `.glb` + `28` high-segment `.master.glb`)
  - **Valid GLB 2.0:** `56 / 56` (`0` invalid, `0` warnings, `0` errors)
  - **Exact Binary Duplicates:** `0`
  - **Matching Geometry Fingerprints:** `0`
  - **Same Metrics Only Groups:** `0`

---

## 3. Complete 8-Screenshot Phase 2.1 Browser Verification Suite

1. **`phase2_1_01_daylight_campus_overview.png` — Daylight 3D Isometric Overview:**
   ![01 Daylight Overview](./phase2_1_01_daylight_campus_overview.png)

2. **`phase2_1_02_night_campus_overview.png` — Night Floodlights Stadium Aerial Overview:**
   ![02 Night Overview](./phase2_1_02_night_campus_overview.png)

3. **`phase2_1_03_ground_level_stadium_inspection.png` — Ground-Level Stadium Inspection:**
   ![03 Ground Level Stadium](./phase2_1_03_ground_level_stadium_inspection.png)

4. **`phase2_1_04_academy_precinct_inspection.png` — Elite Academy & High-Performance Precinct Inspection:**
   ![04 Academy Precinct](./phase2_1_04_academy_precinct_inspection.png)

5. **`phase2_1_05_valid_placement_preview.png` — Raycasted Build Mode Ghost Preview & `90°` Rotation Validation:**
   ![05 Valid Placement Preview](./phase2_1_05_valid_placement_preview.png)

6. **`phase2_1_06_active_construction_stages.png` — Active Construction Lifecycle Progression (Stage 5 Finishing Fit-Out):**
   ![06 Active Construction Stage 5](./phase2_1_06_active_construction_stages.png)

7. **`phase2_1_07_completed_construction_persisted.png` — Completed Operational Facility Persisted After Page Refresh:**
   ![07 Completed Facility Persisted](./phase2_1_07_completed_construction_persisted.png)

8. **`phase2_1_08_individual_facilities_showcase.png` — Full 14-Facility Campus Showcase (All 12 Blueprints Represented):**
   ![08 Full 14-Facility Showcase](./phase2_1_08_individual_facilities_showcase.png)
