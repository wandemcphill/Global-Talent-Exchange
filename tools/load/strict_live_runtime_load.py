from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import os
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

FORBIDDEN_SOURCE_MARKERS = {"demo", "fixture", "mock", "synthetic"}
DEFAULT_ENDPOINTS = {
    "profile": ("/api/session/bootstrap", "/api/profile", "/api/wallet/summary"),
    "admin": ("/api/admin/readiness", "/api/admin/payment-rails", "/api/admin/queues"),
    "national": (
        "/api/national/competitions",
        "/api/national/countries",
        "/api/national/eligible-players",
    ),
    "competition": (
        "/api/world-super-cup/qualification",
        "/api/world-super-cup/bracket",
        "/api/world-super-cup/standings",
        "/api/world-super-cup/countdown",
    ),
}


@dataclass(frozen=True)
class ProbeResult:
    endpoint: str
    status_code: int
    duration_ms: float
    ok: bool
    reason: str = ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run strict-live HTTP load probes against a deployed GTEX API.")
    parser.add_argument("--base-url", default=os.environ.get("GTE_API_BASE_URL", ""))
    parser.add_argument("--token", default=os.environ.get("GTE_ACCESS_TOKEN", ""))
    parser.add_argument("--scenario", choices=(*DEFAULT_ENDPOINTS.keys(), "all"), default="all")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    base_url = args.base_url.strip()
    if not base_url:
        parser.error("--base-url or GTE_API_BASE_URL is required")
    if "fixture" in base_url or "mock" in base_url or "demo" in base_url:
        parser.error("strict-live load probes refuse fixture/mock/demo base URLs")

    endpoints = _scenario_endpoints(args.scenario)
    requests_per_endpoint = max(args.requests, 1)
    work = [endpoint for endpoint in endpoints for _ in range(requests_per_endpoint)]

    started = perf_counter()
    results: list[ProbeResult] = []
    with ThreadPoolExecutor(max_workers=max(args.concurrency, 1)) as executor:
        futures = [
            executor.submit(
                probe_endpoint,
                base_url=base_url,
                endpoint=endpoint,
                token=args.token,
                timeout=max(args.timeout, 1.0),
            )
            for endpoint in work
        ]
        for future in as_completed(futures):
            results.append(future.result())

    summary = summarize_results(results, duration_seconds=perf_counter() - started)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["failed"] == 0 else 1


def _scenario_endpoints(scenario: str) -> tuple[str, ...]:
    if scenario == "all":
        endpoints: list[str] = []
        for group in DEFAULT_ENDPOINTS.values():
            endpoints.extend(group)
        return tuple(endpoints)
    return DEFAULT_ENDPOINTS[scenario]


def probe_endpoint(*, base_url: str, endpoint: str, token: str, timeout: float) -> ProbeResult:
    url = urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))
    request = Request(url, method="GET")
    request.add_header("Accept", "application/json")
    request.add_header("X-GTEX-Strict-Live-Probe", "1")
    if token.strip():
        request.add_header("Authorization", f"Bearer {token.strip()}")
    started = perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            duration_ms = (perf_counter() - started) * 1000
            status_code = int(response.status)
    except HTTPError as exc:
        duration_ms = (perf_counter() - started) * 1000
        return ProbeResult(
            endpoint=endpoint, status_code=exc.code, duration_ms=duration_ms, ok=False, reason="http_error"
        )
    except URLError as exc:
        duration_ms = (perf_counter() - started) * 1000
        return ProbeResult(
            endpoint=endpoint,
            status_code=0,
            duration_ms=duration_ms,
            ok=False,
            reason=f"network_error:{exc.reason}",
        )

    synthetic_reason = _synthetic_reason(body)
    if synthetic_reason:
        return ProbeResult(
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            ok=False,
            reason=synthetic_reason,
        )
    return ProbeResult(endpoint=endpoint, status_code=status_code, duration_ms=duration_ms, ok=200 <= status_code < 300)


def summarize_results(results: list[ProbeResult], *, duration_seconds: float) -> dict[str, Any]:
    by_endpoint: dict[str, dict[str, Any]] = {}
    for result in results:
        row = by_endpoint.setdefault(
            result.endpoint,
            {
                "requests": 0,
                "failed": 0,
                "min_ms": None,
                "max_ms": 0.0,
                "total_ms": 0.0,
                "failures": {},
            },
        )
        row["requests"] += 1
        row["total_ms"] += result.duration_ms
        row["max_ms"] = max(float(row["max_ms"]), result.duration_ms)
        row["min_ms"] = result.duration_ms if row["min_ms"] is None else min(float(row["min_ms"]), result.duration_ms)
        if not result.ok:
            row["failed"] += 1
            failures = row["failures"]
            failures[result.reason] = int(failures.get(result.reason, 0)) + 1

    for row in by_endpoint.values():
        requests = max(int(row["requests"]), 1)
        row["avg_ms"] = round(float(row["total_ms"]) / requests, 2)
        row["min_ms"] = round(float(row["min_ms"] or 0.0), 2)
        row["max_ms"] = round(float(row["max_ms"]), 2)
        del row["total_ms"]

    failed = sum(1 for result in results if not result.ok)
    return {
        "strict_live": True,
        "duration_seconds": round(duration_seconds, 3),
        "requests": len(results),
        "failed": failed,
        "endpoints": by_endpoint,
    }


def _synthetic_reason(body: bytes) -> str:
    text = body.decode("utf-8", errors="ignore")
    if not text.strip():
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ""
    return _walk_forbidden_payload(payload)


def _walk_forbidden_payload(value: Any, *, path: str = "$") -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in {"fixture", "demo", "mock", "synthetic"} and item:
                return f"synthetic_field:{path}.{normalized_key}"
            if normalized_key in {"source", "runtime_source", "source_of_truth", "mode"}:
                marker = str(item).strip().lower()
                if any(forbidden in marker for forbidden in FORBIDDEN_SOURCE_MARKERS):
                    return f"synthetic_source:{path}.{normalized_key}"
            reason = _walk_forbidden_payload(item, path=f"{path}.{normalized_key}")
            if reason:
                return reason
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reason = _walk_forbidden_payload(item, path=f"{path}[{index}]")
            if reason:
                return reason
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
