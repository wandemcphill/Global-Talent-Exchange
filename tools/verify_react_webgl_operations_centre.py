"""Automated browser-level verification for GTEX Club Operations Centre WebGL & GLB assets.

Verifies:
1. Destination GLB URLs correctly resolve under /console.
2. All six GLB assets load successfully in the React Three.js environment.
3. Loaded-asset count reaches '6/6 GLB Assets Loaded'.
4. A failed asset triggers the warning state (data-testid="glb-asset-warning").
5. Procedural wireframe fallback remains visible and interactive when an asset fails.
6. 2D architectural floorplan fallback remains accessible and interactive.
7. The Living World timeline drawer, filters and close action work after the WebGL scene is fully restored.
"""

from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
BUILD_DIR = REPO_ROOT / "frontend" / "react-shell" / "build"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm.attributes import flag_modified  # noqa: E402
from app.owner_console import daily_operations_hub, ledger, living_club_world, service, storytelling  # noqa: E402
from tests.world_clock.test_gtex_club_prestige_campus_comms import _seed_club, _session  # noqa: E402

EXPECTED_DESTINATIONS = [
    "executive_office",
    "managers_office",
    "general_managers_office",
    "academy_department",
    "medical_department",
    "finance_commercial_office",
]

EXPECTED_GLBS = {
    "executive_office": "/models/campus/club_hq.glb",
    "managers_office": "/models/campus/stadium_main.glb",
    "general_managers_office": "/models/campus/vip_skybox_concourse.glb",
    "academy_department": "/models/campus/elite_academy_complex.glb",
    "medical_department": "/models/campus/recovery_hydro_hub.glb",
    "finance_commercial_office": "/models/campus/high_performance_centre.glb",
}


class ConsoleSPARequestHandler(SimpleHTTPRequestHandler):
    """Serves the React Shell build directory with support for /console prefix and SPA routing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BUILD_DIR), **kwargs)

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path).path
        if parsed.startswith("/console/"):
            parsed = parsed[len("/console") :]
        elif parsed == "/console":
            parsed = "/"
        candidate = BUILD_DIR / parsed.lstrip("/")
        if candidate.exists() and candidate.is_file():
            return str(candidate)
        if not Path(parsed).suffix:
            return str(BUILD_DIR / "index.html")
        return str(candidate)

    def guess_type(self, path: str) -> str:
        if path.endswith(".glb"):
            return "model/gltf-binary"
        return super().guess_type(path)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


def seed_test_database():
    session = _session()
    state = _seed_club(session, prestige=82, cash=500_000)
    user_id = state.owner_user_id
    club_id = state.club_id

    regens = service.academy_intake(session, user_id, club_id)
    if regens:
        regens[0].injured_days = 6
        p0 = dict(regens[0].personality_json or {})
        p0["last_injury_type"] = "Quadriceps Strain"
        regens[0].personality_json = p0
        flag_modified(regens[0], "personality_json")
        session.commit()

    # Initialize living world events and directives for timeline verification
    living_club_world.process_world_day_events(session, state, campus_effects={})
    living_club_world.issue_department_directive(
        session,
        user_id,
        club_id,
        department="medical",
        directive_key="accelerate_rehab",
        title="Accelerate Hydrotherapy Protocols",
        instruction="Prioritize hydrotherapy for squad recovery",
        deadline_days=3,
    )
    return session, user_id, club_id


def run_verification(headless: bool = True) -> int:
    from playwright.sync_api import sync_playwright

    if not (BUILD_DIR / "index.html").exists():
        print(f"[ERROR] Build directory not found: {BUILD_DIR}")
        print("Please run 'npm run build' inside frontend/react-shell first.")
        return 1

    session, user_id, club_id = seed_test_database()

    # Start static file server
    server = ThreadingHTTPServer(("127.0.0.1", 0), ConsoleSPARequestHandler)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"
    console_url = f"{base_url}/console"
    print(f"[INFO] React Shell SPA server listening at {console_url}")

    with sync_playwright() as p:
        launch_args = ["--use-gl=angle", "--enable-webgl", "--ignore-gpu-blocklist"]
        browser = None
        for channel in ["msedge", "chrome", None]:
            try:
                browser = (
                    p.chromium.launch(channel=channel, headless=headless, args=launch_args)
                    if channel
                    else p.chromium.launch(headless=headless, args=launch_args)
                )
                break
            except Exception:
                continue

        if not browser:
            print("[ERROR] Could not launch Chromium browser.")
            server.shutdown()
            return 1

        context = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.25)
        page = context.new_page()

        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(f"[page] {err}"))

        # Setup API interception
        CORS_HEADERS = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }

        def handle_api(route, request):
            parsed = urlparse(request.url)
            path = parsed.path
            method = request.method.upper()
            if method == "OPTIONS":
                return route.fulfill(status=204, headers=CORS_HEADERS, body="")

            def ok(data):
                route.fulfill(
                    status=200,
                    headers=CORS_HEADERS,
                    content_type="application/json",
                    body=json.dumps(data, default=str),
                )

            try:
                if path.endswith("/v2/auth/me"):
                    return ok(
                        {
                            "id": user_id,
                            "email": "owner@gtex.test",
                            "username": "prestige_owner",
                            "display_name": "Executive Club Owner",
                            "account_type": "user",
                            "role": "user",
                        }
                    )
                if path.endswith("/owner/control-center"):
                    states = service.user_states(session, user_id)
                    briefing = daily_operations_hub.build_authoritative_daily_briefing(session, user_id, club_id)
                    return ok(
                        {
                            "user": {
                                "id": user_id,
                                "username": "prestige_owner",
                                "display_name": "Executive Club Owner",
                                "role": "user",
                            },
                            "clubs": [service.club_card(session, s) for s in states],
                            "max_clubs": service.MAX_CLUBS,
                            "inbox": [],
                            "inbox_open_count": 0,
                            "inbox_unread_count": 0,
                            "daily_briefing": briefing,
                            "ticker": storytelling.list_ticker_events(session, user_id=user_id, limit=6),
                            "newsroom": storytelling.list_newsroom_articles(session, user_id=user_id, limit=6),
                            "economy": {
                                "wallet": ledger.wallet_classes(session, user_id),
                                "club_cash_total": "490000",
                            },
                        }
                    )
                if path.endswith(f"/owner/clubs/{club_id}/operations-hub"):
                    hub = daily_operations_hub.get_club_operations_hub(session, user_id, club_id)
                    return ok(hub)
                if path.endswith(f"/owner/clubs/{club_id}/daily-briefing"):
                    briefing = daily_operations_hub.build_authoritative_daily_briefing(session, user_id, club_id)
                    return ok(briefing)
                if path.endswith(f"/owner/clubs/{club_id}"):
                    state = service.get_state(session, club_id)
                    return ok(service.club_profile(session, state))
                if "/living-world/timeline" in path:
                    from urllib.parse import parse_qs

                    query = parse_qs(parsed.query)
                    category = query.get("category", [None])[0]
                    severity = query.get("severity", [None])[0]
                    status_param = query.get("status", [None])[0]
                    limit = int(query.get("limit", [20])[0])
                    offset = int(query.get("offset", [0])[0])
                    tl = living_club_world.get_living_world_timeline(
                        session,
                        user_id,
                        club_id,
                        category=category,
                        severity=severity,
                        status=status_param,
                        limit=limit,
                        offset=offset,
                    )
                    return ok(tl)
                if "/living-world/relationships" in path:
                    rels = living_club_world.get_club_relationships(session, club_id)
                    return ok(
                        {
                            "club_id": club_id,
                            "total_count": len(rels),
                            "relationships": rels,
                        }
                    )
                if "/living-world/directives" in path and method == "POST":
                    body = json.loads(request.post_data or "{}")
                    dir_res = living_club_world.issue_department_directive(
                        session,
                        user_id,
                        club_id,
                        department=body.get("department", "medical"),
                        directive_key=body.get("directive_key", "dir_key"),
                        title=body.get("title", "Directive"),
                        instruction=body.get("instruction", "Instruction"),
                    )
                    return ok(dir_res)
                if "/living-world/events/" in path and path.endswith("/resolve") and method == "POST":
                    parts = path.split("/")
                    ev_id = parts[-2]
                    body = json.loads(request.post_data or "{}")
                    res = living_club_world.resolve_club_event(
                        session,
                        user_id,
                        club_id,
                        event_id=ev_id,
                        action=body.get("action", "acknowledge"),
                        resolution_note=body.get("resolution_note"),
                    )
                    return ok(res)
                return ok({"status": "ok"})
            except Exception as exc:
                print(f"  [MOCK API ERROR] {method} {path}: {type(exc).__name__}: {exc}")
                return route.fulfill(
                    status=500,
                    headers=CORS_HEADERS,
                    content_type="application/json",
                    body=json.dumps({"detail": str(exc)}),
                )

        page.route("**/api/**", handle_api)
        page.route("http://localhost:8000/**", handle_api)
        page.route("http://127.0.0.1:8000/**", handle_api)

        # -------------------------------------------------------------
        # TEST 1: Full GLB loading under /console route
        # -------------------------------------------------------------
        print("\n--- Test 1: Full 6/6 GLB Loading Under /console Route ---")
        loaded_glbs = []

        def track_glb_request(response):
            if ".glb" in response.url:
                parsed_url = urlparse(response.url).path
                status = response.status
                print(f"  [GLB FETCH] {parsed_url} -> HTTP {status}")
                if status == 200:
                    loaded_glbs.append(parsed_url)

        page.on("response", track_glb_request)
        page.on(
            "response",
            lambda response: (
                print(f"  [BROWSER HTTP {response.status}] {response.url}") if response.status >= 500 else None
            ),
        )
        page.on("console", lambda msg: print(f"  [BROWSER CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"  [BROWSER PAGE ERROR] {err}"))

        # Seed auth in localStorage
        page.goto(f"{console_url}/", wait_until="domcontentloaded")
        page.evaluate(f"""() => {{
                localStorage.setItem('gtex_access', 'live-phase2-3-owner-token');
                localStorage.setItem('gtex_active_club', '{club_id}');
            }}""")

        # Navigate to /console/app
        print(f"[INFO] Navigating to {console_url}/app ...")
        page.goto(f"{console_url}/app", wait_until="domcontentloaded")

        # Wait for Living Club Management Centre container
        page.wait_for_selector('[data-testid="living-club-management-centre"]', timeout=30000)
        print("[PASS] Living Club Management Centre container rendered.")

        # Verify 3D canvas is present
        page.wait_for_selector('[data-testid="club-operations-3d-canvas"]', timeout=15000)
        print("[PASS] Three.js WebGL canvas rendered.")

        # Wait for all 6 GLBs to load
        t_start = time.perf_counter()
        while time.perf_counter() - t_start < 25.0:
            status_text = page.locator('[data-testid="glb-asset-status"]').inner_text()
            if "6/6 GLB Assets Loaded" in status_text:
                print(f"[PASS] Status indicator reached: '{status_text}'")
                break
            time.sleep(0.5)
        else:
            final_status = page.locator('[data-testid="glb-asset-status"]').inner_text()
            print(f"[FAIL] GLB asset status timed out. Current text: '{final_status}'")
            browser.close()
            server.shutdown()
            return 1

        # Verify all 6 GLBs were resolved under /console
        for dest_key, glb_path in EXPECTED_GLBS.items():
            expected_console_url = f"/console{glb_path}"
            matched = any(expected_console_url in u for u in loaded_glbs)
            if not matched:
                print(f"[FAIL] Missing /console resolution for {dest_key}: {expected_console_url}")
                browser.close()
                server.shutdown()
                return 1
            print(f"[PASS] Confirmed resolution under /console: {expected_console_url}")

        # Verify no warning banner when all assets load
        warning_locator = page.locator('[data-testid="glb-asset-warning"]')
        if warning_locator.count() > 0 and warning_locator.is_visible():
            print("[FAIL] Unexpected glb-asset-warning banner visible during normal load.")
            browser.close()
            server.shutdown()
            return 1
        print("[PASS] No asset warning banner present during complete 6/6 load.")

        # -------------------------------------------------------------
        # TEST 2: Asset Failure Warning & Procedural Wireframe Fallback
        # -------------------------------------------------------------
        print("\n--- Test 2: Asset Failure Warning & Wireframe Fallback Mesh ---")
        context_fail = browser.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.25)
        page_fail = context_fail.new_page()
        page_fail.on("pageerror", lambda err: page_errors.append(f"[page_fail] {err}"))
        page_fail.on(
            "response",
            lambda response: (
                print(f"  [BROWSER HTTP {response.status}] {response.url}") if response.status >= 500 else None
            ),
        )
        page_fail.route("**/api/**", handle_api)
        page_fail.route("http://localhost:8000/**", handle_api)
        page_fail.route("http://127.0.0.1:8000/**", handle_api)

        # Block one specific GLB to simulate missing/corrupt asset
        blocked_glb = "high_performance_centre.glb"
        page_fail.route(
            f"**/{blocked_glb}",
            lambda route: route.abort("failed"),
        )

        page_fail.goto(f"{console_url}/", wait_until="domcontentloaded")
        page_fail.evaluate(f"""() => {{
                localStorage.setItem('gtex_access', 'live-phase2-3-owner-token');
                localStorage.setItem('gtex_active_club', '{club_id}');
            }}""")

        page_fail.goto(f"{console_url}/app", wait_until="domcontentloaded")
        page_fail.wait_for_selector('[data-testid="living-club-management-centre"]', timeout=30000)

        # Wait for asset warning banner to appear
        page_fail.wait_for_selector('[data-testid="glb-asset-warning"]', timeout=20000)
        warning_text = page_fail.locator('[data-testid="glb-asset-warning"]').inner_text()
        print(f"[PASS] Asset warning displayed: '{warning_text}'")
        assert "finance_commercial_office" in warning_text or "1 3D model" in warning_text

        # Verify wireframe fallback destination button remains interactive
        btn_fallback = page_fail.locator('[data-testid="destination-tab-finance_commercial_office"]')
        assert btn_fallback.is_visible()
        btn_fallback.click()
        print("[PASS] Fallback wireframe destination is selectable and interactive.")

        # Reliable assertion for the actual fallback wireframe mesh in the Three.js scene
        fallback_mesh_info = page_fail.evaluate("""() => {
                const api = window.__GTEX_OPERATIONS_3D__;
                if (!api || !api.roomGroups) return null;
                const grp = api.roomGroups.get("finance_commercial_office");
                if (!grp) return null;
                const mesh = grp.children.find(
                    (c) => c.name === "fallback-wireframe-finance_commercial_office" || c.userData?.isFallbackWireframe
                );
                if (!mesh) return null;
                return {
                    name: mesh.name,
                    isMesh: Boolean(mesh.isMesh),
                    isWireframe: Boolean(mesh.material && mesh.material.wireframe),
                    visible: Boolean(mesh.visible),
                    position: [mesh.position.x, mesh.position.y, mesh.position.z],
                    userData: mesh.userData,
                };
            }""")
        print(f"  [SCENE AUDIT] Fallback mesh in Three.js scene: {fallback_mesh_info}")
        assert fallback_mesh_info is not None, "Fallback wireframe mesh was NOT found in Three.js scene group!"
        assert fallback_mesh_info["isMesh"] is True, "Fallback scene object is not a THREE.Mesh"
        assert fallback_mesh_info["isWireframe"] is True, "Fallback mesh material is not wireframe"
        assert fallback_mesh_info["visible"] is True, "Fallback mesh is not visible"
        assert (
            fallback_mesh_info["userData"].get("isFallbackWireframe") is True
        ), "Fallback mesh missing isFallbackWireframe"
        print("[PASS] Confirmed procedural wireframe mesh is added to Three.js scene with wireframe material.")

        # Release the failure-injection browser context before the next
        # WebGL test. Keeping two Three.js scenes alive can contend for GPU
        # resources and starve browser-side React interactions in headless CI.
        context_fail.close()
        print("[INFO] Closed the isolated GLB-failure browser context.")

        # -------------------------------------------------------------
        # TEST 3: 2D Floorplan Fallback Switch & Navigation
        # -------------------------------------------------------------
        print("\n--- Test 3: 2D Floorplan Fallback Switch & Navigation ---")
        toggle_btn = page.locator('[data-testid="toggle-render-mode"]')
        assert toggle_btn.is_visible()
        toggle_btn.click()

        page.wait_for_selector('[data-testid="club-operations-2d-floorplan"]', timeout=5000)
        print("[PASS] 2D Architectural Floorplan rendered successfully.")

        # Check all 6 rooms on floorplan
        for dest_key in EXPECTED_DESTINATIONS:
            room_btn = page.locator(f'[data-testid="floorplan-room-{dest_key}"]')
            assert room_btn.is_visible()
            print(f"  [PASS] 2D Floorplan room present: {dest_key}")

        # Click a room on the floorplan
        page.locator('[data-testid="floorplan-room-medical_department"]').click()
        status_text_2d = page.locator('[data-testid="glb-asset-status"]').inner_text()
        print(f"[PASS] 2D Blueprint status indicator: '{status_text_2d}'")
        assert "2D Blueprint Active" in status_text_2d

        # Switch back to 3D WebGL. Re-mounting the Three.js scene and reloading
        # its six GLB assets is slower than the initial mode toggle in headless CI.
        toggle_btn.click()
        page.wait_for_selector(
            '[data-testid="club-operations-3d-canvas"]',
            state="visible",
            timeout=25000,
        )
        page.wait_for_function(
            """() => {
                const status = document.querySelector('[data-testid="glb-asset-status"]');
                return Boolean(status && status.textContent.includes("WebGL Active"));
            }""",
            timeout=25000,
        )
        # The renderer reports "WebGL Active" as soon as its canvas is ready.
        # That does not mean the asynchronous GLB reloads have completed.
        # Wait for all six models before starting UI interaction tests so
        # heavy GLTF parsing/GPU uploads cannot starve the timeline interaction.
        page.wait_for_function(
            """() => {
                const status = document.querySelector('[data-testid="glb-asset-status"]');
                return Boolean(status && status.textContent.includes("6/6 GLB Assets Loaded"));
            }""",
            timeout=30000,
        )
        page.wait_for_timeout(250)
        print("[PASS] Successfully restored the fully initialized 3D WebGL viewport.")

        # -------------------------------------------------------------
        # TEST 4: Unified Living World Timeline Drawer & Filters
        # -------------------------------------------------------------
        print("\n--- Test 4: Unified Living World Timeline Drawer & Filters ---")
        timeline_btn = page.locator('[data-testid="toggle-living-world-timeline"]')
        timeline_btn.wait_for(state="visible", timeout=15000)
        timeline_btn.scroll_into_view_if_needed()
        timeline_btn.click(timeout=15000)

        # Use a DOM-backed condition rather than a short selector wait. The
        # browser has just restored a heavyweight WebGL scene and may need a
        # frame to commit the React state update.
        page.wait_for_function(
            """() => {
                const drawer = document.querySelector('[data-testid="living-world-timeline-drawer"]');
                if (!drawer) return false;
                const rect = drawer.getBoundingClientRect();
                const style = window.getComputedStyle(drawer);
                return rect.width > 0 && rect.height > 0 &&
                    style.display !== "none" && style.visibility !== "hidden";
            }""",
            timeout=15000,
        )
        print("[PASS] Living World Timeline drawer opened.")

        # Verify the filter controls and one of the valid timeline content
        # states (populated, empty or error) have rendered.
        page.wait_for_selector('[data-testid="timeline-category-filters"]', state="visible", timeout=15000)
        page.wait_for_function(
            """() => [
                '[data-testid="living-timeline-list"]',
                '[data-testid="living-timeline-empty"]',
                '[data-testid="living-timeline-error"]',
                '[data-testid="living-timeline-loading"]'
            ].some((selector) => {
                const node = document.querySelector(selector);
                if (!node) return false;
                const rect = node.getBoundingClientRect();
                const style = window.getComputedStyle(node);
                return rect.width > 0 && rect.height > 0 &&
                    style.display !== "none" && style.visibility !== "hidden";
            })""",
            timeout=15000,
        )
        print("[PASS] Timeline filters and event content state rendered.")

        # Test culture filter and wait for React to apply the selected state.
        culture_filter_btn = page.locator('[data-testid="timeline-filter-category-culture"]')
        culture_filter_btn.click(timeout=15000)
        page.wait_for_function(
            """() => {
                const button = document.querySelector('[data-testid="timeline-filter-category-culture"]');
                return Boolean(button && button.className.includes("bg-purple-600/30"));
            }""",
            timeout=10000,
        )
        print("[PASS] Category filter for 'culture' selected successfully.")

        # Reset to all categories and verify the selected state.
        all_filter_btn = page.locator('[data-testid="timeline-filter-category-all"]')
        all_filter_btn.click(timeout=15000)
        page.wait_for_function(
            """() => {
                const button = document.querySelector('[data-testid="timeline-filter-category-all"]');
                return Boolean(button && button.className.includes("bg-purple-600/30"));
            }""",
            timeout=10000,
        )

        # Close timeline drawer and verify it is removed from the DOM.
        close_btn = page.locator('[data-testid="close-timeline-drawer"]')
        close_btn.wait_for(state="visible", timeout=10000)
        close_btn.click(timeout=15000)
        page.wait_for_function(
            """() => !document.querySelector('[data-testid="living-world-timeline-drawer"]')""",
            timeout=10000,
        )
        print("[PASS] Timeline drawer closed successfully.")

        # Fail verification if unexpected JavaScript page errors occurred on either page context
        if page_errors:
            print(f"\n[FAIL] Unexpected JavaScript page errors encountered ({len(page_errors)}):")
            for pe in page_errors:
                print(f"  - {pe}")
            context_fail.close()
            context.close()
            browser.close()
            server.shutdown()
            return 1
        print("[PASS] Zero unhandled JavaScript page errors detected across all browser contexts.")

        context.close()
        browser.close()
        server.shutdown()

    print("\n=======================================================")
    print("  ALL REACT WEBGL & GLB ASSET VERIFICATIONS PASSED")
    print("=======================================================\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Verify GTEX Living Club Management Centre React WebGL & GLB assets.")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode for visual observation.")
    args = parser.parse_args()
    sys.exit(run_verification(headless=not args.headed))


if __name__ == "__main__":
    main()
