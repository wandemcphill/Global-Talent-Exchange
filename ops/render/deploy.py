from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib import error, parse, request

from verify_match_center_routes import (
    RenderMatchCenterRouteVerificationError,
    derive_api_base_url,
    verify_match_center_routes,
)

DEFAULT_SERVICE_ORDER = ("API", "OUTBOX", "SIMULATION", "PROJECTIONS", "WEB")
RENDER_API_BASE_URL = "https://api.render.com/v1"
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
    deploy_hook_url: str


class RenderDeployError(RuntimeError):
    pass


class RenderDeployHttpError(RenderDeployError):
    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


def _log(message: str) -> None:
    print(message, flush=True)


def _optional_env(name: str) -> str:
    return os.getenv(name, "").strip()


def _required_env(name: str) -> str:
    value = _optional_env(name)
    if not value:
        raise RenderDeployError(f"{name} must be set.")
    return value


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RenderDeployError(f"{name} must be an integer.") from exc


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    lowered = raw_value.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise RenderDeployError(f"{name} must be a boolean.")


def _get_deploy_mode() -> str:
    raw_value = _optional_env("RENDER_DEPLOY_MODE") or "hook-only"
    normalized = raw_value.lower().replace("_", "-").strip()
    if normalized in {"hook", "hook-only"}:
        return "hook-only"
    if normalized in {"api", "full-api"}:
        return "api"
    raise RenderDeployError("RENDER_DEPLOY_MODE must be either 'hook-only' or 'api'.")


def _load_service_targets(deploy_mode: str) -> list[ServiceTarget]:
    service_ids: dict[str, str] = {}
    deploy_hooks: dict[str, str] = {}

    for key, value in os.environ.items():
        stripped = value.strip()
        if not stripped:
            continue

        if key.startswith("RENDER_SERVICE_"):
            suffix = key[len("RENDER_SERVICE_") :].strip().upper()
            if suffix != "ORDER":
                service_ids[suffix] = stripped

        if key.startswith("RENDER_DEPLOY_HOOK_"):
            suffix = key[len("RENDER_DEPLOY_HOOK_") :].strip().upper()
            deploy_hooks[suffix] = stripped

    configured_suffixes = sorted(set(service_ids) | set(deploy_hooks))
    if not configured_suffixes:
        raise RenderDeployError(
            "No Render services were configured. "
            "Set one or more RENDER_SERVICE_<NAME> and RENDER_DEPLOY_HOOK_<NAME> environment variables."
        )

    targets: list[ServiceTarget] = []
    for suffix in configured_suffixes:
        service_id = service_ids.get(suffix, "").strip()
        deploy_hook_url = deploy_hooks.get(suffix, "").strip()

        if not service_id:
            raise RenderDeployError(
                f"Missing RENDER_SERVICE_{suffix}. " "Each configured service needs its Render service id."
            )

        if deploy_mode == "hook-only" and not deploy_hook_url:
            raise RenderDeployError(
                f"Missing RENDER_DEPLOY_HOOK_{suffix}. "
                "Hook-only mode requires a deploy hook for every configured service."
            )

        targets.append(
            ServiceTarget(
                name=suffix.lower().replace("_", "-"),
                env_key=suffix,
                service_id=service_id,
                deploy_hook_url=deploy_hook_url,
            )
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

    return sorted(targets, key=sort_key)


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


def _request_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    request_label: str,
) -> dict[str, Any]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(
        url=url,
        data=body,
        method=method,
        headers=headers
        or {
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            content = response.read().decode("utf-8", errors="replace").strip()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RenderDeployHttpError(
            status_code=exc.code,
            message=f"{request_label} {method} {url} failed with HTTP {exc.code}: {detail}",
        ) from exc
    except error.URLError as exc:
        raise RenderDeployError(f"{request_label} {method} {url} failed: {exc}") from exc

    if not content:
        return {}

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RenderDeployError(f"{request_label} {method} {url} returned non-JSON content: {content}") from exc

    if not isinstance(parsed, dict):
        raise RenderDeployError(f"{request_label} {method} {url} returned an unexpected payload: {parsed!r}")

    return parsed


class RenderHookClient:
    def __init__(self, *, api_key: str | None = None) -> None:
        self._api_key = (api_key or _required_env("RENDER_API_KEY")).strip()

    def _render_api_headers(self, *, include_content_type: bool = False) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        if include_content_type:
            headers["Content-Type"] = "application/json"
        return headers

    def trigger_deploy(self, deploy_hook_url: str) -> dict[str, Any]:
        return _request_json(
            method="POST",
            url=deploy_hook_url,
            payload={},
            request_label="Deploy hook",
        )

    def create_deploy(self, service_id: str) -> dict[str, Any]:
        safe_service_id = parse.quote(service_id, safe="")
        return _request_json(
            method="POST",
            url=f"{RENDER_API_BASE_URL}/services/{safe_service_id}/deploys",
            payload={},
            headers=self._render_api_headers(include_content_type=True),
            request_label="Render API",
        )

    def retrieve_deploy(self, service_id: str, deploy_id: str) -> dict[str, Any]:
        safe_service_id = parse.quote(service_id, safe="")
        safe_deploy_id = parse.quote(deploy_id, safe="")
        return _request_json(
            method="GET",
            url=f"{RENDER_API_BASE_URL}/services/{safe_service_id}/deploys/{safe_deploy_id}",
            headers=self._render_api_headers(),
            request_label="Render API",
        )


def _wait_for_deploy(
    retrieve_deploy: Callable[[str, str], dict[str, Any]],
    *,
    target: ServiceTarget,
    deploy_id: str,
    timeout_seconds: int,
    poll_interval_seconds: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status = ""

    while time.monotonic() < deadline:
        deploy = retrieve_deploy(target.service_id, deploy_id)
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


def _health_url_for_target(target: ServiceTarget, default_health_url: str) -> str:
    scoped_health_url = _optional_env(f"RENDER_HEALTH_URL_{target.env_key}")
    if scoped_health_url:
        return scoped_health_url
    if target.env_key == "API":
        return default_health_url
    return ""


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


def _deploy_with_hook_only(
    client: RenderHookClient,
    *,
    target: ServiceTarget,
    health_url: str,
    deploy_timeout_seconds: int,
    health_timeout_seconds: int,
    poll_interval_seconds: int,
) -> None:
    _log(f"[{target.name}] triggering deploy hook")
    deploy = client.trigger_deploy(target.deploy_hook_url)
    deploy_id = _extract_deploy_id(deploy)

    if deploy_id:
        try:
            _wait_for_deploy(
                client.retrieve_deploy,
                target=target,
                deploy_id=deploy_id,
                timeout_seconds=deploy_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
        except RenderDeployHttpError as exc:
            if health_url and exc.status_code == 404:
                _log(f"[{target.name}] deploy status unavailable in hook-only mode; falling back to health check")
            else:
                raise
    elif not health_url:
        raise RenderDeployError(f"Deploy hook did not return a deploy id for {target.name}: {deploy!r}")

    if health_url:
        _run_health_check(
            url=health_url,
            timeout_seconds=health_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        _log(f"[{target.name}] health check passed")


def _deploy_with_render_api(
    client: RenderHookClient,
    *,
    target: ServiceTarget,
    health_url: str,
    deploy_timeout_seconds: int,
    health_timeout_seconds: int,
    poll_interval_seconds: int,
) -> None:
    _log(f"[{target.name}] creating deploy via Render API")
    deploy = client.create_deploy(target.service_id)
    deploy_id = _extract_deploy_id(deploy)
    if not deploy_id:
        raise RenderDeployError(f"Render API did not return a deploy id for {target.name}: {deploy!r}")

    _wait_for_deploy(
        client.retrieve_deploy,
        target=target,
        deploy_id=deploy_id,
        timeout_seconds=deploy_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )

    if health_url:
        _run_health_check(
            url=health_url,
            timeout_seconds=health_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        _log(f"[{target.name}] health check passed")


def main() -> int:
    deploy_mode = _get_deploy_mode()
    targets = _load_service_targets(deploy_mode)
    health_url = _optional_env("RENDER_HEALTH_URL")
    deploy_timeout_seconds = _get_int_env("RENDER_DEPLOY_TIMEOUT_SECONDS", 1800)
    health_timeout_seconds = _get_int_env("RENDER_HEALTH_TIMEOUT_SECONDS", 180)
    poll_interval_seconds = _get_int_env("RENDER_POLL_INTERVAL_SECONDS", 10)
    verify_match_center_routes_after_deploy = _get_bool_env("RENDER_VERIFY_MATCH_CENTER_ROUTES", True)
    api_health_url = _optional_env("RENDER_HEALTH_URL_API") or health_url

    if any(target.env_key == "API" for target in targets) and not api_health_url:
        raise RenderDeployError("RENDER_HEALTH_URL must be set when deploying the API service.")

    client = RenderHookClient()

    try:
        for target in targets:
            target_health_url = _health_url_for_target(target, health_url)

            if deploy_mode == "hook-only":
                _deploy_with_hook_only(
                    client,
                    target=target,
                    health_url=target_health_url,
                    deploy_timeout_seconds=deploy_timeout_seconds,
                    health_timeout_seconds=health_timeout_seconds,
                    poll_interval_seconds=poll_interval_seconds,
                )
            else:
                _deploy_with_render_api(
                    client,
                    target=target,
                    health_url=target_health_url,
                    deploy_timeout_seconds=deploy_timeout_seconds,
                    health_timeout_seconds=health_timeout_seconds,
                    poll_interval_seconds=poll_interval_seconds,
                )

            if target.env_key == "API" and target_health_url:
                if verify_match_center_routes_after_deploy:
                    try:
                        api_base_url = derive_api_base_url(target_health_url)
                        verify_match_center_routes(api_base_url)
                    except RenderMatchCenterRouteVerificationError as exc:
                        raise RenderDeployError(str(exc)) from exc
                    _log(f"[match-center-routes] {api_base_url} passed")

    except Exception as exc:  # noqa: BLE001
        if deploy_mode == "hook-only":
            _log("Automatic rollback is not available in hook-only mode.")
        else:
            _log("Automatic rollback is not configured in this deploy workflow.")
        _log(f"Deployment failed: {exc}")
        return 1

    _log("Deployment verified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
