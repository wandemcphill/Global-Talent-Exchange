from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_MARKET_ENDPOINTS = (
    "/api/market/players?limit=20",
    "/api/market/movers?limit=5",
    "/api/transfer-market/filters/meta",
    "/api/transfer-market/listings?status=open",
    "/api/player-cards/marketplace/listings?limit=20",
)


@dataclass(frozen=True)
class ProbeTarget:
    name: str
    path: str
    required: bool


def build_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def request_once(
    *,
    base_url: str,
    target: ProbeTarget,
    timeout_seconds: float,
    bearer_token: str | None,
) -> dict:
    url = build_url(base_url, target.path)
    headers = {"User-Agent": "gtex-load-probe/1.0"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    started = time.perf_counter()
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            latency_ms = (time.perf_counter() - started) * 1000
            status_code = int(response.status)
            ok = 200 <= status_code < 300
            return {
                "target": target.name,
                "path": target.path,
                "url": url,
                "required": target.required,
                "ok": ok,
                "status_code": status_code,
                "latency_ms": round(latency_ms, 2),
                "bytes": len(body),
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "target": target.name,
            "path": target.path,
            "url": url,
            "required": target.required,
            "ok": False,
            "status_code": int(exc.code),
            "latency_ms": round(latency_ms, 2),
            "bytes": 0,
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 - probe must serialize failures.
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "target": target.name,
            "path": target.path,
            "url": url,
            "required": target.required,
            "ok": False,
            "status_code": 0,
            "latency_ms": round(latency_ms, 2),
            "bytes": 0,
            "error": str(exc),
        }


def summarize_target(samples: list[dict], *, max_p95_ms: float, max_error_rate: float) -> dict:
    latencies = [sample["latency_ms"] for sample in samples if sample["ok"]]
    failures = [sample for sample in samples if not sample["ok"]]
    error_rate = len(failures) / len(samples) if samples else 1.0
    p95 = percentile(latencies, 0.95)
    passed = bool(samples) and error_rate <= max_error_rate and p95 <= max_p95_ms
    return {
        "request_count": len(samples),
        "success_count": len(samples) - len(failures),
        "failure_count": len(failures),
        "error_rate": round(error_rate, 4),
        "min_ms": round(min(latencies), 2) if latencies else 0,
        "avg_ms": round(statistics.fmean(latencies), 2) if latencies else 0,
        "p50_ms": round(percentile(latencies, 0.50), 2),
        "p95_ms": round(p95, 2),
        "max_ms": round(max(latencies), 2) if latencies else 0,
        "passed": passed,
        "sample_errors": failures[:5],
    }


def build_targets(args: argparse.Namespace) -> list[ProbeTarget]:
    targets: list[ProbeTarget] = []

    for index, path in enumerate(args.market_endpoint):
        targets.append(ProbeTarget(name=f"market_{index + 1}", path=path, required=True))

    if args.match_id:
        encoded_match_id = urllib.parse.quote(args.match_id, safe="")
        targets.extend(
            [
                ProbeTarget(
                    name="match_center_live_active",
                    path="/api/matches/live/active",
                    required=args.require_match,
                ),
                ProbeTarget(
                    name="match_center_viewer",
                    path=f"/api/match-viewer/{encoded_match_id}",
                    required=args.require_match,
                ),
                ProbeTarget(
                    name="match_center_viewer_session",
                    path=f"/api/match-viewer/{encoded_match_id}/session",
                    required=args.require_match,
                ),
                ProbeTarget(
                    name="match_engine_live_feed",
                    path=f"/api/match-engine/live-feed/{encoded_match_id}",
                    required=False,
                ),
                ProbeTarget(
                    name="match_engine_highlights",
                    path=f"/api/match-engine/highlights/{encoded_match_id}",
                    required=False,
                ),
                ProbeTarget(
                    name="match_viewer_replay",
                    path=f"/api/matches/{encoded_match_id}/replay",
                    required=False,
                ),
            ]
        )
    elif args.require_match:
        raise SystemExit("--require-match was set but --match-id was not provided.")

    return targets


def run_http_probe(args: argparse.Namespace, targets: list[ProbeTarget]) -> tuple[list[dict], dict]:
    scheduled: list[ProbeTarget] = []
    for target in targets:
        scheduled.extend([target] * args.requests_per_endpoint)

    samples: list[dict] = []
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                request_once,
                base_url=args.base_url,
                target=target,
                timeout_seconds=args.timeout_seconds,
                bearer_token=args.bearer_token,
            )
            for target in scheduled
        ]
        for future in concurrent.futures.as_completed(futures):
            samples.append(future.result())

    elapsed = time.perf_counter() - started
    by_target: dict[str, list[dict]] = {}
    for sample in samples:
        by_target.setdefault(sample["target"], []).append(sample)

    target_summaries = {
        name: summarize_target(
            target_samples,
            max_p95_ms=args.max_p95_ms,
            max_error_rate=args.max_error_rate,
        )
        for name, target_samples in sorted(by_target.items())
    }

    required_target_names = {target.name for target in targets if target.required}
    required_failures = [
        name
        for name, summary in target_summaries.items()
        if name in required_target_names and not summary["passed"]
    ]

    summary = {
        "elapsed_seconds": round(elapsed, 2),
        "total_requests": len(samples),
        "requests_per_second": round(len(samples) / elapsed, 2) if elapsed > 0 else 0,
        "required_failure_count": len(required_failures),
        "required_failures": required_failures,
        "targets": target_summaries,
    }
    return samples, summary


def run_websocket_probe(args: argparse.Namespace) -> dict:
    if not args.websocket_url:
        return {"status": "skipped", "reason": "No --websocket-url provided."}

    try:
        import websocket  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - optional dependency.
        status = "failed" if args.require_websocket else "skipped"
        return {
            "status": status,
            "reason": f"Optional websocket-client package is unavailable: {exc}",
        }

    headers = []
    if args.bearer_token:
        headers.append(f"Authorization: Bearer {args.bearer_token}")

    started = time.perf_counter()
    try:
        ws = websocket.create_connection(
            args.websocket_url,
            timeout=args.timeout_seconds,
            header=headers,
        )
        try:
            first_message = ws.recv()
        finally:
            ws.close()
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "status": "pass",
            "latency_ms": round(elapsed_ms, 2),
            "first_message_bytes": len(first_message or ""),
        }
    except Exception as exc:  # noqa: BLE001 - probe must serialize failures.
        return {
            "status": "failed",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "reason": str(exc),
        }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GTEX market and match-center load probe.")
    parser.add_argument("--base-url", required=True, help="Backend base URL, for example https://gtex-api.onrender.com")
    parser.add_argument("--bearer-token", default="", help="Optional bearer token for authenticated endpoints.")
    parser.add_argument(
        "--market-endpoint",
        action="append",
        default=list(DEFAULT_MARKET_ENDPOINTS),
        help="Market endpoint path to probe. Can be repeated.",
    )
    parser.add_argument("--match-id", default="", help="Existing backend-authored match id for match-center endpoints.")
    parser.add_argument("--require-match", action="store_true", help="Fail when match-center endpoints are unavailable.")
    parser.add_argument("--websocket-url", default="", help="Optional realtime websocket URL to probe once.")
    parser.add_argument("--require-websocket", action="store_true", help="Fail if websocket probe is skipped or failed.")
    parser.add_argument("--requests-per-endpoint", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=10)
    parser.add_argument("--max-p95-ms", type=float, default=1500)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--output", default="tmp/gtex_load_probe_summary.json")
    parser.add_argument("--samples-output", default="", help="Optional path for raw samples JSON.")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.requests_per_endpoint < 1:
        raise SystemExit("--requests-per-endpoint must be >= 1.")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1.")
    if args.concurrency > 32:
        raise SystemExit("--concurrency is capped at 32 for staging safety.")

    targets = build_targets(args)
    samples, http_summary = run_http_probe(args, targets)
    websocket_summary = run_websocket_probe(args)

    websocket_passed = websocket_summary["status"] == "pass" or (
        websocket_summary["status"] == "skipped" and not args.require_websocket
    )
    passed = http_summary["required_failure_count"] == 0 and websocket_passed

    payload = {
        "tool": "gtex_load_probe",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "limits": {
            "requests_per_endpoint": args.requests_per_endpoint,
            "concurrency": args.concurrency,
            "timeout_seconds": args.timeout_seconds,
            "max_p95_ms": args.max_p95_ms,
            "max_error_rate": args.max_error_rate,
        },
        "match_id": args.match_id or None,
        "passed": passed,
        "http": http_summary,
        "websocket": websocket_summary,
    }

    output_path = Path(args.output)
    write_json(output_path, payload)
    if args.samples_output:
        write_json(Path(args.samples_output), {"samples": samples})

    print(f"LOAD_PROBE_SUMMARY={output_path}")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
