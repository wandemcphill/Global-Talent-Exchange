from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Sample:
    ok: bool
    latency_ms: float
    status: int | None
    error: str | None = None


async def probe(client: httpx.AsyncClient, url: str) -> Sample:
    started = time.perf_counter()
    try:
        response = await client.get(url)
        return Sample(
            ok=200 <= response.status_code < 400,
            latency_ms=(time.perf_counter() - started) * 1000,
            status=response.status_code,
        )
    except Exception as exc:  # pragma: no cover - operator harness
        return Sample(
            ok=False,
            latency_ms=(time.perf_counter() - started) * 1000,
            status=None,
            error=str(exc),
        )


async def run(
    base_url: str, path: str, concurrency: int, requests: int
) -> dict[str, object]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    limits = httpx.Limits(
        max_connections=concurrency,
        max_keepalive_connections=concurrency,
    )
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        samples = await asyncio.gather(
            *(probe(client, url) for _ in range(requests))
        )

    latencies = [sample.latency_ms for sample in samples]
    successes = sum(sample.ok for sample in samples)
    ordered = sorted(latencies)
    p95_index = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
    return {
        "url": url,
        "requests": requests,
        "concurrency": concurrency,
        "successes": successes,
        "failures": requests - successes,
        "success_rate": successes / requests if requests else 0.0,
        "latency_ms": {
            "min": min(latencies) if latencies else None,
            "mean": statistics.fmean(latencies) if latencies else None,
            "p95": ordered[p95_index] if ordered else None,
            "max": max(latencies) if latencies else None,
        },
        "errors": [sample.error for sample in samples if sample.error][:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a bounded GTEX HTTP production/staging soak probe."
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--path", default="/health")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=300)
    args = parser.parse_args()
    if args.concurrency < 1 or args.requests < 1:
        parser.error("concurrency and requests must be positive")
    report = asyncio.run(run(args.base_url, args.path, args.concurrency, args.requests))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["success_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
