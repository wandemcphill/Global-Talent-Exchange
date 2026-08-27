from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import provision_gtex_live_match as provisioning


def build_windows_websocket_url(base_url: str, match_id: str) -> str:
    websocket_url = str(base_url or "").strip().rstrip("/")
    if websocket_url.startswith("https://"):
        websocket_url = "wss://" + websocket_url[len("https://") :]
    elif websocket_url.startswith("http://"):
        websocket_url = "ws://" + websocket_url[len("http://") :]
    return websocket_url + f"/api/v2/ws/match/{match_id}?format=unity"


def force_windows_live_playback_config() -> None:
    """Make the Windows evidence player consume GTEX live render-sync playback."""
    config_path = PROJECT_ROOT / "Gtex_Test_Migration" / "Assets" / "Resources" / "GTEX" / "match-config.json"
    bootstrap_path = PROJECT_ROOT / "Gtex_Test_Migration" / "tmp" / "gtex-live-bootstrap.json"

    if not config_path.exists():
        raise RuntimeError(f"Unity match config not found: {config_path}")

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Unity match config must contain a JSON object.")

    payload.update(
        {
            "runtimeMode": "live",
            "autoStartOnBoot": True,
            "enabled": True,
            "preserveOriginalScenePresentation": False,
            "enableStadiumUpgrade": True,
            "showBroadcastScaffolding": False,
            "showCrowd": True,
            "stadiumVariant": "broadcast",
            "useOriginalMatchCamera": False,
            "verboseLogging": False,
            "enableRuntimeComparisonLogging": False,
            "showRuntimeDebugOverlay": False,
            "continueClockWhenTransportStalls": False,
            "stalledClockAdvanceMinutesPerSecond": 0.0,
            "use3DPlaybackForLocalSimulation": True,
        }
    )
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if bootstrap_path.exists():
        bootstrap = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        if not isinstance(bootstrap, dict):
            raise RuntimeError("GTEX live bootstrap must contain a JSON object.")
        bootstrap["runtimeMode"] = "live"
        bootstrap["environment"] = payload.get("environment", "local")
        bootstrap["baseUrl"] = payload.get("localBaseUrl", "http://127.0.0.1:8000")
        bootstrap_path.write_text(json.dumps(bootstrap, indent=2) + "\n", encoding="utf-8")


provisioning.build_websocket_url = build_windows_websocket_url


if __name__ == "__main__":
    sys.argv[0] = provisioning.__file__
    provisioning.main()
    force_windows_live_playback_config()
    print("[GTEX] Windows evidence config forced to authoritative live playback mode.")
