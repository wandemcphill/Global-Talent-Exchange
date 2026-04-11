from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from urllib import error, parse, request

_UNITY_OPENAPI_PATHS: tuple[tuple[str, str], ...] = (
    ("/api/matches/{match_id}/unity-access", "post"),
    ("/api/matches/{match_id}/unity-access/refresh", "post"),
)
_PROBE_MATCH_ID = "gtex-render-route-probe"
_ALLOWED_RUNTIME_PROBE_STATUSES = frozenset({200, 201, 202, 204, 400, 401, 403, 409, 422})


class RenderUnityRouteVerificationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResponseSnapshot:
    status_code: int
    body: str


def derive_api_base_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise RenderUnityRouteVerificationError("The Render API URL is required.")

    parsed = parse.urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        raise RenderUnityRouteVerificationError(f"Expected an absolute URL for Render verification, got: {candidate!r}")

    path = parsed.path.rstrip("/")
    for suffix in ("/health", "/ready", "/version", "/metrics", "/docs", "/openapi.json"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break

    return parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")


def _request_snapshot(
    *,
    method: str,
    url: str,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> ResponseSnapshot:
    body = None
    request_headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)

    req = request.Request(url=url, data=body, method=method, headers=request_headers)
    try:
        with request.urlopen(req, timeout=30) as response:
            return ResponseSnapshot(
                status_code=response.getcode(),
                body=response.read().decode("utf-8", errors="replace"),
            )
    except error.HTTPError as exc:
        return ResponseSnapshot(
            status_code=exc.code,
            body=exc.read().decode("utf-8", errors="replace"),
        )
    except error.URLError as exc:
        raise RenderUnityRouteVerificationError(f"Request failed for {method} {url}: {exc}") from exc


def _load_openapi(base_url: str) -> dict[str, object]:
    snapshot = _request_snapshot(method="GET", url=f"{base_url}/openapi.json")
    if snapshot.status_code != 200:
        raise RenderUnityRouteVerificationError(
            f"OpenAPI probe failed with HTTP {snapshot.status_code} at {base_url}/openapi.json."
        )
    try:
        payload = json.loads(snapshot.body)
    except json.JSONDecodeError as exc:
        raise RenderUnityRouteVerificationError("OpenAPI probe returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise RenderUnityRouteVerificationError("OpenAPI probe returned an unexpected payload type.")
    return payload


def _verify_openapi_contract(base_url: str) -> None:
    openapi_payload = _load_openapi(base_url)
    paths = openapi_payload.get("paths")
    if not isinstance(paths, dict):
        raise RenderUnityRouteVerificationError("OpenAPI payload did not include a paths map.")

    for path, method in _UNITY_OPENAPI_PATHS:
        route_payload = paths.get(path)
        if not isinstance(route_payload, dict):
            raise RenderUnityRouteVerificationError(f"OpenAPI is missing the Unity route '{path}'.")
        if method not in route_payload:
            raise RenderUnityRouteVerificationError(f"OpenAPI route '{path}' is missing the '{method}' operation.")


def _verify_runtime_probe(*, base_url: str, probe_match_id: str) -> None:
    access_snapshot = _request_snapshot(
        method="POST",
        url=f"{base_url}/api/matches/{probe_match_id}/unity-access?pay_to_view=false",
    )
    if access_snapshot.status_code not in _ALLOWED_RUNTIME_PROBE_STATUSES:
        raise RenderUnityRouteVerificationError(
            "Unity access route probe failed: "
            f"expected one of {sorted(_ALLOWED_RUNTIME_PROBE_STATUSES)}, got HTTP {access_snapshot.status_code}."
        )

    refresh_snapshot = _request_snapshot(
        method="POST",
        url=f"{base_url}/api/matches/{probe_match_id}/unity-access/refresh",
        payload={"refresh_token": "gtex-render-route-probe"},
    )
    if refresh_snapshot.status_code not in _ALLOWED_RUNTIME_PROBE_STATUSES:
        raise RenderUnityRouteVerificationError(
            "Unity refresh route probe failed: "
            f"expected one of {sorted(_ALLOWED_RUNTIME_PROBE_STATUSES)}, got HTTP {refresh_snapshot.status_code}."
        )


def verify_unity_live_routes(
    api_url: str,
    *,
    probe_match_id: str = _PROBE_MATCH_ID,
    skip_runtime_probe: bool = False,
) -> str:
    base_url = derive_api_base_url(api_url)
    _verify_openapi_contract(base_url)
    if not skip_runtime_probe:
        _verify_runtime_probe(base_url=base_url, probe_match_id=probe_match_id.strip() or _PROBE_MATCH_ID)
    return base_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify hosted GTEX Unity live routes after deploy.")
    parser.add_argument("--url", required=True, help="Render API base URL or health URL.")
    parser.add_argument(
        "--probe-match-id",
        default=_PROBE_MATCH_ID,
        help="Synthetic match id used for route probing.",
    )
    parser.add_argument(
        "--skip-runtime-probe",
        action="store_true",
        help="Only verify the OpenAPI contract and skip runtime HTTP probes.",
    )
    args = parser.parse_args()

    try:
        base_url = verify_unity_live_routes(
            args.url,
            probe_match_id=args.probe_match_id,
            skip_runtime_probe=args.skip_runtime_probe,
        )
    except RenderUnityRouteVerificationError as exc:
        print(f"[unity-routes] verification failed: {exc}", flush=True)
        return 1

    print(f"[unity-routes] {base_url} passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
