from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request

DEFAULT_SERVICE_ORDER = ("API", "OUTBOX", "SIMULATION", "PROJECTIONS", "WEB")
SUCCESS_STATUSES = {"active", "deployed", "live", "success", "succeeded"}
FAILURE_STATUSES = {
    "build_failed",
    "canceled",
    "cancelled",
    "deactivated",
    "error",
    "failed",
    "rollback_failed",
    "timed_out",
    "update_failed",
}
IN_PROGRESS_MARKERS = (
    "build",
    "created",
    "deploy",
    "in_progress",
    "pending",
    "pre_deploy",
    "queue",
    "start",
    "update",
)


@dataclass(frozen=True, slots=True)
class ServiceTarget:
    name: str
    env_key: str
    service_id: str


class RenderDeployError(RuntimeError):
    pass


def _log(message: str) -> None:
    print(message, flush=True)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RenderDeployError(f"{name} must be configured for deployment automation.")
    return value


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RenderDeployError(f"{name} must be an integer.") from exc


def _load_service_targets() -> list[ServiceTarget]:
    configured: dict[str, ServiceTarget] = {}
    for key, value in os.environ.items():
        if not key.startswith("RENDER_SERVICE_"):
            continue
        suffix = key[len("RENDER_SERVICE_") :].strip().upper()
        if suffix == "ORDER":
            continue
        service_id = value.strip()
        if not service_id:
            continue
        configured[suffix] = ServiceTarget(
            name=suffix.lower().replace("_", "-"),
            env_key=suffix,
            service_id=service_id,
        )

    if not configured:
        raise RenderDeployError(
            "No Render services were configured. Set one or more RENDER_SERVICE_<NAME> environment variables."
        )

    configured_order = [
        item.strip().upper().replace("-", "_")
        for item in os.getenv("RENDER_SERVICE_ORDER", ",".join(DEFAULT_SERVICE_ORDER)).split(",")
        if item.strip()
    ]

    def sort_key(item: ServiceTarget) -> tuple[int, str]:
        try:
            position = configured_order.index(item.env_key)
        except ValueError:
            position = len(configured_order)
        return (position, item.env_key)

    return sorted(configured.values(), key=sort_key)


def _normalize_status(payload: dict[str, Any]) -> str:
    raw_status = payload.get("status") or payload.get("deployStatus") or payload.get("state") or ""
    return str(raw_status).strip().lower().replace("-", "_").replace(" ", "_")


def _extract_deploy_id(payload: dict[str, Any]) -> str | None:
    for candidate in (payload.get("id"), payload.get("deployId")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    nested = payload.get("deploy")
    if isinstance(nested, dict):
        nested_id = nested.get("id")
        if isinstance(nested_id, str) and nested_id.strip():
            return nested_id.strip()
    return None


def _is_success_status(status: str) -> bool:
    return status in SUCCESS_STATUSES


def _is_failure_status(status: str) -> bool:
    return status in FAILURE_STATUSES or "fail" in status or status.endswith("_error")


def _is_in_progress_status(status: str) -> bool:
    return any(marker in status for marker in IN_PROGRESS_MARKERS)


def _validate_health_payload(payload: dict[str, Any]) -> None:
    if payload.get("status") != "ok":
        raise RenderDeployError(f"Health check returned non-ok status: {payload!r}")
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        raise RenderDeployError("Health check response did not include a checks object.")

    required_checks = [
        item.strip()
        for item in os.getenv("RENDER_HEALTH_REQUIRED_CHECKS", "api,database,redis").split(",")
        if item.strip()
    ]
    for name in required_checks:
        check = checks.get(name)
        if not isinstance(check, dict):
            raise RenderDeployError(f"Health check is missing the '{name}' dependency result.")
        status = str(check.get("status", "")).strip().lower()
        if status != "ok":
            detail = check.get("detail")
            raise RenderDeployError(f"Health check for '{name}' failed: {detail or status}.")


class RenderClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def trigger_deploy(self, service_id: str) -> dict[str, Any]:
        return self._request("POST", f"/services/{service_id}/deploys", payload={})

    def retrieve_deploy(self, service_id: str, deploy_id: str) -> dict[str, Any]:
        return self._request("GET", f"/services/{service_id}/deploys/{deploy_id}")

    def rollback(self, service_id: str) -> dict[str, Any]:
        return self._request("POST", f"/services/{service_id}/rollback", payload={})

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"https://api.render.com/v1{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                content = response.read().decode("utf-8", errors="replace").strip()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RenderDeployError(f"Render API {method} {path} failed with HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RenderDeployError(f"Render API {method} {path} failed: {exc}") from exc
        if not content:
            return {}
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RenderDeployError(f"Render API {method} {path} returned non-JSON content: {content}") from exc
        if not isinstance(parsed, dict):
            raise RenderDeployError(f"Render API {method} {path} returned an unexpected payload: {parsed!r}")
        return parsed


def _wait_for_deploy(
    client: RenderClient,
    *,
    target: ServiceTarget,
    deploy_id: str,
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = ""
    while time.monotonic() < deadline:
        deploy = client.retrieve_deploy(target.service_id, deploy_id)
        status = _normalize_status(deploy)
        if status != last_status:
            _log(f"[{target.name}] deploy {deploy_id} status={status or 'unknown'}")
            last_status = status
        if _is_success_status(status):
            return deploy
        if _is_failure_status(status):
            raise RenderDeployError(f"Deploy failed for {target.name} with status '{status}'.")
        if not status and deploy.get("finishedAt"):
            raise RenderDeployError(f"Deploy for {target.name} finished without a recognized success status.")
        time.sleep(poll_interval_seconds)
    raise RenderDeployError(f"Timed out waiting for deploy {deploy_id} on {target.name}.")


def _run_health_check(*, url: str, timeout_seconds: int, poll_interval_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            req = request.Request(
                url=url,
                method="GET",
                headers={"Accept": "application/json"},
            )
            with request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            if not isinstance(payload, dict):
                raise RenderDeployError(f"Health endpoint returned an unexpected payload: {payload!r}")
            _validate_health_payload(payload)
            _log(f"[health] {url} passed")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            _log(f"[health] waiting for {url}: {exc}")
            time.sleep(poll_interval_seconds)
    raise RenderDeployError(f"Health check failed for {url}: {last_error}")


def _rollback_targets(
    client: RenderClient,
    *,
    targets: list[ServiceTarget],
    deploy_timeout_seconds: int,
    poll_interval_seconds: int,
) -> None:
    if not targets:
        return
    _log("Deployment failed. Starting automatic rollback.")
    rollback_errors: list[str] = []
    for target in reversed(targets):
        try:
            _log(f"[{target.name}] triggering rollback")
            payload = client.rollback(target.service_id)
            rollback_deploy_id = _extract_deploy_id(payload)
            if rollback_deploy_id:
                _wait_for_deploy(
                    client,
                    target=target,
                    deploy_id=rollback_deploy_id,
                    timeout_seconds=deploy_timeout_seconds,
                    poll_interval_seconds=poll_interval_seconds,
                )
        except Exception as exc:  # noqa: BLE001
            rollback_errors.append(f"{target.name}: {exc}")
    if rollback_errors:
        joined = "; ".join(rollback_errors)
        raise RenderDeployError(f"Rollback completed with errors: {joined}")


def main() -> int:
    api_key = _required_env("RENDER_API_KEY")
    targets = _load_service_targets()
    health_url = os.getenv("RENDER_HEALTH_URL", "").strip()
    deploy_timeout_seconds = _get_int_env("RENDER_DEPLOY_TIMEOUT_SECONDS", 1800)
    health_timeout_seconds = _get_int_env("RENDER_HEALTH_TIMEOUT_SECONDS", 180)
    poll_interval_seconds = _get_int_env("RENDER_POLL_INTERVAL_SECONDS", 10)
    client = RenderClient(api_key=api_key)
    deployed_targets: list[ServiceTarget] = []

    if any(target.env_key == "API" for target in targets) and not health_url:
        raise RenderDeployError("RENDER_HEALTH_URL must be set when deploying the API service.")

    try:
        for target in targets:
            _log(f"[{target.name}] triggering deploy")
            deploy = client.trigger_deploy(target.service_id)
            deploy_id = _extract_deploy_id(deploy)
            if not deploy_id:
                raise RenderDeployError(f"Render did not return a deploy id for {target.name}: {deploy!r}")
            _wait_for_deploy(
                client,
                target=target,
                deploy_id=deploy_id,
                timeout_seconds=deploy_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
            deployed_targets.append(target)
            if target.env_key == "API" and health_url:
                _run_health_check(
                    url=health_url,
                    timeout_seconds=health_timeout_seconds,
                    poll_interval_seconds=poll_interval_seconds,
                )

        if health_url:
            _run_health_check(
                url=health_url,
                timeout_seconds=health_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
    except Exception as exc:  # noqa: BLE001
        rollback_error: Exception | None = None
        try:
            _rollback_targets(
                client,
                targets=deployed_targets,
                deploy_timeout_seconds=deploy_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
        except Exception as rollback_exc:  # noqa: BLE001
            rollback_error = rollback_exc
        _log(f"Deployment failed: {exc}")
        if rollback_error is not None:
            _log(f"Rollback encountered errors: {rollback_error}")
        return 1

    _log("Deployment completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
