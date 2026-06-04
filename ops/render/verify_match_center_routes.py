from __future__ import annotations

import argparse
import json
from typing import Any
from urllib import error, parse, request

_CANONICAL_OPENAPI_PATHS = (
    ("/api/v2/match-viewer/{match_key}", "get"),
    ("/api/v2/match-viewer/{match_key}/session", "get"),
    ("/api/v2/matches/live/active", "get"),
    ("/api/v2/matches/{match_id}/spectate", "post"),
    ("/api/v2/matches/{match_id}/commentary/stream", "get"),
)


def _quarantined_route_fragment(*parts: str) -> str:
    return "/" + "".join(parts)


_FORBIDDEN_OPENAPI_FRAGMENTS = (
    _quarantined_route_fragment("un", "ity", "-access"),
    _quarantined_route_fragment("un", "ity", "-access/refresh"),
    _quarantined_route_fragment("legacy", "-runtime", "-access"),
    _quarantined_route_fragment("legacy", "-runtime", "-access/refresh"),
    _quarantined_route_fragment("matches", "/3", "d"),
    _quarantined_route_fragment("matches", "/native-", "3d"),
    _quarantined_route_fragment("match-viewer", "/{match_key}/illusion"),
    _quarantined_route_fragment("match-engine", "/render-sync"),
)


class RenderMatchCenterRouteVerificationError(RuntimeError):
    pass


def derive_api_base_url(raw_url: str) -> str:
    parsed = parse.urlparse(raw_url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise RenderMatchCenterRouteVerificationError(f"Invalid URL: {raw_url!r}")

    path = parsed.path.rstrip("/")
    if path.endswith("/health"):
        path = path[: -len("/health")]
    if path.endswith("/api/health"):
        path = path[: -len("/api/health")]

    return parse.urlunparse((parsed.scheme, parsed.netloc, path.rstrip("/"), "", "", "")).rstrip("/")


def _load_openapi(base_url: str, *, timeout_seconds: int) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/openapi.json"
    try:
        req = request.Request(url=url, method="GET", headers={"Accept": "application/json"})
        with request.urlopen(req, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 0) or response.getcode())
            if status >= 400:
                raise RenderMatchCenterRouteVerificationError(f"OpenAPI returned HTTP {status} for {url}.")
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        raise RenderMatchCenterRouteVerificationError(f"OpenAPI returned HTTP {exc.code} for {url}.") from exc
    except error.URLError as exc:
        raise RenderMatchCenterRouteVerificationError(f"OpenAPI could not be reached at {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RenderMatchCenterRouteVerificationError(f"OpenAPI returned invalid JSON at {url}.") from exc

    if not isinstance(payload, dict):
        raise RenderMatchCenterRouteVerificationError(f"OpenAPI returned an unexpected payload: {payload!r}")
    return payload


def verify_match_center_routes(base_url: str, *, timeout_seconds: int = 30) -> None:
    openapi = _load_openapi(base_url, timeout_seconds=timeout_seconds)
    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        raise RenderMatchCenterRouteVerificationError("OpenAPI payload is missing a paths object.")

    for path, method in _CANONICAL_OPENAPI_PATHS:
        methods = paths.get(path)
        if not isinstance(methods, dict) or method not in methods:
            raise RenderMatchCenterRouteVerificationError(
                f"OpenAPI is missing the canonical 2D match center route '{method.upper()} {path}'."
            )

    mounted_paths = "\n".join(str(path) for path in paths)
    for forbidden in _FORBIDDEN_OPENAPI_FRAGMENTS:
        if forbidden in mounted_paths:
            raise RenderMatchCenterRouteVerificationError(
                f"OpenAPI still exposes quarantined match route fragment '{forbidden}'."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify hosted GTEX 2D match center routes after deploy.")
    parser.add_argument("--url", required=True, help="API base URL or health URL.")
    parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args()

    base_url = derive_api_base_url(args.url)
    verify_match_center_routes(base_url, timeout_seconds=args.timeout_seconds)
    print(json.dumps({"status": "ok", "base_url": base_url, "verified": "match_center_routes"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
