"""Regression tests: X-Forwarded-For must not be attacker-controllable.

extract_client_ip feeds both the anonymous rate-limit bucket key and the
client_ip recorded on every security audit row. Reading the left-most
X-Forwarded-For entry let any caller rotate their apparent address per request
and walk past login throttling while poisoning the audit trail.
"""

from __future__ import annotations

import pytest

from app.core.request_security import extract_client_ip


class _StubClient:
    def __init__(self, host: str | None) -> None:
        self.host = host


class _StubState:
    def __init__(self, settings: object | None) -> None:
        self.settings = settings


class _StubApp:
    def __init__(self, settings: object | None) -> None:
        self.state = _StubState(settings)


class _StubSettings:
    def __init__(self, trusted_proxy_hops: int) -> None:
        self.trusted_proxy_hops = trusted_proxy_hops


class _StubRequest:
    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        peer: str | None = "10.0.0.9",
        trusted_proxy_hops: int | None = 1,
    ) -> None:
        self.headers = dict(headers or {})
        self.client = _StubClient(peer)
        settings = None if trusted_proxy_hops is None else _StubSettings(trusted_proxy_hops)
        self.app = _StubApp(settings)


def test_spoofed_forwarded_for_prefix_is_ignored() -> None:
    request = _StubRequest(headers={"x-forwarded-for": "1.2.3.4, 203.0.113.7"})
    assert extract_client_ip(request) == "203.0.113.7"


def test_attacker_cannot_rotate_bucket_key_with_forwarded_for() -> None:
    resolved = {
        extract_client_ip(_StubRequest(headers={"x-forwarded-for": f"9.9.9.{index}, 203.0.113.7"}))
        for index in range(1, 25)
    }
    assert resolved == {"203.0.113.7"}


def test_single_forwarded_entry_is_honoured() -> None:
    request = _StubRequest(headers={"x-forwarded-for": "203.0.113.7"})
    assert extract_client_ip(request) == "203.0.113.7"


@pytest.mark.parametrize("hops,expected", [(1, "198.51.100.2"), (2, "198.51.100.1"), (5, "203.0.113.7")])
def test_trusted_hop_count_selects_entry_from_the_right(hops: int, expected: str) -> None:
    request = _StubRequest(
        headers={"x-forwarded-for": "203.0.113.7, 198.51.100.1, 198.51.100.2"},
        trusted_proxy_hops=hops,
    )
    assert extract_client_ip(request) == expected


def test_zero_trusted_hops_uses_the_socket_peer() -> None:
    request = _StubRequest(headers={"x-forwarded-for": "1.2.3.4"}, trusted_proxy_hops=0)
    assert extract_client_ip(request) == "10.0.0.9"


def test_falls_back_to_peer_without_forwarding_header() -> None:
    assert extract_client_ip(_StubRequest()) == "10.0.0.9"


def test_unknown_when_no_peer_and_no_trusted_header() -> None:
    request = _StubRequest(peer=None, trusted_proxy_hops=0)
    assert extract_client_ip(request) == "unknown"
