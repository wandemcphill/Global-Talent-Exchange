from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib import error, parse, request

from verify_unity_routes import RenderUnityRouteVerificationError, derive_api_base_url, verify_unity_live_routes

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
    deploy_hook_url: str


class RenderDeployError(RuntimeError):
    pass


def _log(message: str) -> None:
    print(message, flush=True)


def _optional_env(name: str) -> str:
    return os.getenv(name, "").strip()


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


def _load_service_targets() -> list[ServiceTarget]:
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

        if not deploy_hook_url:
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
        raise RenderDeployError(f"{request_label} {method} {url} failed with HTTP {exc.code}: {detail}") from exc
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
    def trigger_deploy(self, deploy_hook_url: str) -> dict[str, Any]:
        return _request_json(
            method="POST",
            url=deploy_hook_url,
            payload={},
            request_label="Deploy hook",
        )

    def retrieve_deploy(self, service_id: str, deploy_id: str) -> dict[str, Any]:
        safe_service_id = parse.quote(service_id, safe="")
        safe_deploy_id = parse.quote(deploy_id, safe="")
        return _request_json(
            method="GET",
            url=f"https://api.render.com/deploy/{safe_service_id}/{safe_deploy_id}",
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


def _run_unity_live_playback_check(*, health_url: str) -> None:
    if not _get_bool_env("RENDER_VERIFY_UNITY_LIVE_PLAYBACK", False):
        return

    repo_root = Path(__file__).resolve().parents[2]
    provision_script = repo_root / "tools" / "provision_gtex_live_match.py"
    if not provision_script.exists():
        raise RenderDeployError(f"Unity live playback verification script was not found: {provision_script}")

    verify_profile = _optional_env("RENDER_UNITY_LIVE_VERIFY_PROFILE") or "staging"
    base_url = _optional_env("RENDER_UNITY_LIVE_VERIFY_BASE_URL") or derive_api_base_url(health_url)
    match_id = _optional_env("RENDER_UNITY_LIVE_VERIFY_MATCH_ID")
    user_access_token = _optional_env("RENDER_UNITY_LIVE_VERIFY_USER_ACCESS_TOKEN")
    user_email = _optional_env("RENDER_UNITY_LIVE_VERIFY_USER_EMAIL")
    user_password = _optional_env("RENDER_UNITY_LIVE_VERIFY_USER_PASSWORD")
    allow_match_generation = _get_bool_env("RENDER_UNITY_LIVE_VERIFY_ALLOW_MATCH_GENERATION", True)
    skip_websocket_verify = _get_bool_env("RENDER_UNITY_LIVE_VERIFY_SKIP_WEBSOCKET", False)
    pay_to_view = _get_bool_env("RENDER_UNITY_LIVE_VERIFY_PAY_TO_VIEW", False)
    tick_count = max(1, _get_int_env("RENDER_UNITY_LIVE_VERIFY_TICK_COUNT", 1))
    command_timeout_seconds = max(60, _get_int_env("RENDER_UNITY_LIVE_VERIFY_TIMEOUT_SECONDS", 240))

    if not user_access_token and (not user_email or not user_password):
        raise RenderDeployError(
            "Unity live playback verification is enabled but no credentials were configured. "
            "Set RENDER_UNITY_LIVE_VERIFY_USER_ACCESS_TOKEN or both "
            "RENDER_UNITY_LIVE_VERIFY_USER_EMAIL and RENDER_UNITY_LIVE_VERIFY_USER_PASSWORD."
        )

    command = [
        sys.executable,
        str(provision_script),
        "--profile",
        verify_profile,
        "--base-url",
        base_url,
        "--dry-run",
        "--tick-count",
        str(tick_count),
    ]

    if user_access_token:
        command.extend(["--user-access-token", user_access_token])
    else:
        command.extend(["--user-email", user_email, "--user-password", user_password])

    if match_id:
        command.extend(["--match-id", match_id])
    if allow_match_generation:
        command.append("--allow-match-generation")
    if skip_websocket_verify:
        command.append("--skip-websocket-verify")
    if pay_to_view:
        command.append("--pay-to-view")

    _log(f"[unity-live] verifying hosted playback against {base_url}")
    result = subprocess.run(
        command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=command_timeout_seconds,
        check=False,
    )

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise RenderDeployError(f"Unity live playback verification failed: {detail}")

    try:
        summary = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RenderDeployError(
            "Unity live playback verification did not return valid JSON. "
            f"stdout={stdout!r} stderr={stderr!r}"
        ) from exc

    if not isinstance(summary, dict):
        raise RenderDeployError(f"Unity live playback verification returned an unexpected payload: {summary!r}")

    websocket_summary = summary.get("websocket")
    if not skip_websocket_verify:
        if not isinstance(websocket_summary, dict):
            raise RenderDeployError("Unity live playback verification did not include websocket advancement details.")
        first_frame_id = websocket_summary.get("first_frame_id")
        second_frame_id = websocket_summary.get("second_frame_id")
        first_clock = websocket_summary.get("first_clock_minute")
        second_clock = websocket_summary.get("second_clock_minute")
        if first_frame_id == second_frame_id and first_clock == second_clock:
            raise RenderDeployError("Unity live playback websocket probe did not advance frame or clock state.")

    _log(
        "[unity-live] "
        f"match={summary.get('match_id')} "
        f"http_frame={summary.get('http_frame_id')} "
        f"http_clock={summary.get('http_clock_minute')} "
        f"status={summary.get('http_status')}"
    )


def main() -> int:
    targets = _load_service_targets()
    health_url = _optional_env("RENDER_HEALTH_URL")
    deploy_timeout_seconds = _get_int_env("RENDER_DEPLOY_TIMEOUT_SECONDS", 1800)
    health_timeout_seconds = _get_int_env("RENDER_HEALTH_TIMEOUT_SECONDS", 180)
    poll_interval_seconds = _get_int_env("RENDER_POLL_INTERVAL_SECONDS", 10)
    verify_unity_routes_after_deploy = _get_bool_env("RENDER_VERIFY_UNITY_ROUTES", True)
    unity_route_probe_match_id = _optional_env("RENDER_UNITY_ROUTE_PROBE_MATCH_ID") or "gtex-render-route-probe"

    if any(target.env_key == "API" for target in targets) and not health_url:
        raise RenderDeployError("RENDER_HEALTH_URL must be set when deploying the API service.")

    client = RenderHookClient()

    try:
        for target in targets:
            _log(f"[{target.name}] triggering deploy hook")
            deploy = client.trigger_deploy(target.deploy_hook_url)

            deploy_id = _extract_deploy_id(deploy)
            if not deploy_id:
                raise RenderDeployError(f"Deploy hook did not return a deploy id for {target.name}: {deploy!r}")

            _wait_for_deploy(
                client.retrieve_deploy,
                target=target,
                deploy_id=deploy_id,
                timeout_seconds=deploy_timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )

            if target.env_key == "API" and health_url:
                _run_health_check(
                    url=health_url,
                    timeout_seconds=health_timeout_seconds,
                    poll_interval_seconds=poll_interval_seconds,
                )
                if verify_unity_routes_after_deploy:
                    try:
                        api_base_url = derive_api_base_url(health_url)
                        verify_unity_live_routes(
                            api_base_url,
                            probe_match_id=unity_route_probe_match_id,
                        )
                    except RenderUnityRouteVerificationError as exc:
                        raise RenderDeployError(str(exc)) from exc
                    _log(f"[unity-routes] {api_base_url} passed")
                _run_unity_live_playback_check(health_url=health_url)

    except Exception as exc:  # noqa: BLE001
        _log("Automatic rollback is not available in hook-only mode.")
        _log(f"Deployment failed: {exc}")
        return 1

    _log("Deployment completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
