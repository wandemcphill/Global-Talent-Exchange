from __future__ import annotations

import sys

from . import provision_gtex_live_match as provisioning


def _build_websocket_url(base_url: str, match_id: str) -> str:
    websocket_url = str(base_url or "").strip().rstrip("/")
    if websocket_url.startswith("https://"):
        websocket_url = "wss://" + websocket_url[len("https://") :]
    elif websocket_url.startswith("http://"):
        websocket_url = "ws://" + websocket_url[len("http://") :]
    return websocket_url + f"/api/v2/ws/match/{match_id}?format=unity"


provisioning.build_websocket_url = _build_websocket_url


if __name__ == "__main__":
    sys.argv[0] = provisioning.__file__
    provisioning.main()
