from tools.provision_gtex_live_match_windows import build_windows_websocket_url


def test_windows_websocket_uses_canonical_api_v2_route() -> None:
    assert (
        build_windows_websocket_url("http://127.0.0.1:8000/", "match_demo")
        == "ws://127.0.0.1:8000/api/v2/ws/match/match_demo?format=unity"
    )


def test_windows_websocket_converts_https_to_wss() -> None:
    assert (
        build_windows_websocket_url("https://example.test", "match_demo")
        == "wss://example.test/api/v2/ws/match/match_demo?format=unity"
    )
