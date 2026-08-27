from __future__ import annotations

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


provisioning.build_websocket_url = build_windows_websocket_url


if __name__ == "__main__":
    sys.argv[0] = provisioning.__file__
    provisioning.main()
