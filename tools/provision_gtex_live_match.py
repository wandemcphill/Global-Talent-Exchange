from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import httpx
import websockets

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_RUNTIME_CONFIG = PROJECT_ROOT / "tmp" / "gtex-match-center-config.json"
DEFAULT_BOOTSTRAP_PATH = PROJECT_ROOT / "tmp" / "gtex-match-center-bootstrap.json"
DEFAULT_USER_EMAIL = "match-center@gtex.local"
DEFAULT_USER_PASSWORD = "MatchCenterPass123!"  # pragma: allowlist secret
DEFAULT_USER_FULL_NAME = "GTEX Match Center"
DEFAULT_USER_PHONE = "08000000000"
DEFAULT_USER_REGION = "NG"
DEFAULT_USER_USERNAME = "matchcenter"
AUTH_LOGIN_PATHS: Final[tuple[str, ...]] = ("/api/auth/login", "/auth/login", "/api/v2/auth/login")
AUTH_REGISTER_PATHS: Final[tuple[str, ...]] = ("/api/auth/register", "/auth/register", "/api/v2/auth/register")
LOCAL_PROFILE: Final[str] = "local"
STAGING_PROFILE: Final[str] = "staging"
PRODUCTION_PROFILE: Final[str] = "production"
PROFILE_CHOICES: Final[tuple[str, str, str]] = (LOCAL_PROFILE, STAGING_PROFILE, PRODUCTION_PROFILE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a real backend-driven GTEX live match center session.")
    parser.add_argument(
        "--profile",
        choices=PROFILE_CHOICES,
        default=LOCAL_PROFILE,
        help="Provisioning profile. Local keeps the current lightweight defaults; staging/production require explicit auth inputs.",
    )
    parser.add_argument("--base-url", default="", help="Backend base URL.")
    parser.add_argument(
        "--runtime-config",
        default=str(DEFAULT_RUNTIME_CONFIG),
        help="Path to an optional match center verification config JSON.",
    )
    parser.add_argument(
        "--bootstrap-path",
        default=str(DEFAULT_BOOTSTRAP_PATH),
        help="Path to the match center verification bootstrap JSON.",
    )
    parser.add_argument(
        "--bootstrap-ttl-seconds",
        type=int,
        default=900,
        help="How long the verification bootstrap file remains valid.",
    )
    parser.add_argument(
        "--keep-bootstrap-file",
        action="store_true",
        help="Keep the bootstrap file after verification. Local uses this by default.",
    )
    parser.add_argument(
        "--match-id",
        default="",
        help="Explicit match id to verify through the 2D match center.",
    )
    parser.add_argument("--tick-count", type=int, default=1, help="How many infinite-league matches to generate.")
    parser.add_argument(
        "--allow-match-generation",
        action="store_true",
        help="Allow the tool to generate/select a match automatically. Local enables this automatically.",
    )
    parser.add_argument(
        "--user-access-token",
        default="",
        help="Existing backend bearer token for protected match center checks.",
    )
    parser.add_argument("--user-email", default="", help="Backend user email for provisioning.")
    parser.add_argument("--user-password", default="", help="Backend user password for provisioning.")
    parser.add_argument("--user-full-name", default="", help="Backend user full name for registration.")
    parser.add_argument("--user-phone", default="", help="Backend user phone number for registration.")
    parser.add_argument("--user-region", default="", help="Backend user region code for registration.")
    parser.add_argument("--user-username", default="", help="Backend username for registration.")
    parser.add_argument(
        "--allow-register",
        action="store_true",
        help="Allow the tool to register the provisioning user if login fails. Local enables this automatically.",
    )
    parser.add_argument(
        "--pay-to-view",
        action="store_true",
        help="Deprecated compatibility flag; match center verification never purchases viewing access.",
    )
    parser.add_argument(
        "--skip-websocket-verify",
        action="store_true",
        help="Skip match realtime websocket verification.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write verification config/bootstrap files.",
    )
    parser.add_argument(
        "--persist-access-token",
        action="store_true",
        help="Deprecated compatibility flag; no short-lived runtime access token is written.",
    )
    return parser.parse_args()


def normalize_base_url(base_url: str, *, profile: str) -> str:
    if profile == LOCAL_PROFILE and not str(base_url or "").strip():
        base_url = DEFAULT_BASE_URL

    normalized = str(base_url or "").strip().rstrip("/")
    if not normalized:
        raise RuntimeError(f"A backend base URL is required for the '{profile}' profile.")
    return normalized


def build_backend_unreachable_message(base_url: str, profile: str) -> str:
    normalized = str(base_url or "").strip() or DEFAULT_BASE_URL
    if profile == LOCAL_PROFILE:
        return (
            f"Could not connect to the local GTEX backend at '{normalized}'. "
            "Start it first with `python tools/run_gtex_live_backend.py`, wait for it to bind to port 8000, then rerun "
            "`python tools/provision_gtex_live_match.py`."
        )

    return (
        f"Could not connect to the GTEX backend at '{normalized}' for the '{profile}' profile. "
        "Verify --base-url, confirm the backend is running, and confirm the host/port are reachable from this machine."
    )


def resolve_user_identity(args: argparse.Namespace) -> dict[str, str]:
    if args.profile == LOCAL_PROFILE:
        return {
            "email": str(args.user_email or "").strip() or DEFAULT_USER_EMAIL,
            "password": str(args.user_password or "").strip() or DEFAULT_USER_PASSWORD,
            "full_name": str(args.user_full_name or "").strip() or DEFAULT_USER_FULL_NAME,
            "phone_number": str(args.user_phone or "").strip() or DEFAULT_USER_PHONE,
            "region_code": str(args.user_region or "").strip() or DEFAULT_USER_REGION,
            "username": str(args.user_username or "").strip() or DEFAULT_USER_USERNAME,
        }

    user_access_token = str(args.user_access_token or "").strip()
    if user_access_token:
        return {
            "email": "",
            "password": "",
            "full_name": str(args.user_full_name or "").strip(),
            "phone_number": str(args.user_phone or "").strip(),
            "region_code": str(args.user_region or "").strip(),
            "username": str(args.user_username or "").strip(),
        }

    email = str(args.user_email or "").strip()
    password = str(args.user_password or "").strip()
    if not email or not password:
        raise RuntimeError(
            f"Non-local provisioning requires --user-access-token or explicit --user-email and --user-password for the '{args.profile}' profile."
        )

    full_name = str(args.user_full_name or "").strip()
    phone_number = str(args.user_phone or "").strip()
    region_code = str(args.user_region or "").strip()
    username = str(args.user_username or "").strip()
    if args.allow_register and (not full_name or not phone_number or not region_code or not username):
        raise RuntimeError(
            f"Non-local provisioning with --allow-register also requires --user-full-name, --user-phone, --user-region, and --user-username for the '{args.profile}' profile."
        )

    return {
        "email": email,
        "password": password,
        "full_name": full_name,
        "phone_number": phone_number,
        "region_code": region_code,
        "username": username,
    }


def should_allow_register(args: argparse.Namespace) -> bool:
    return args.allow_register or args.profile == LOCAL_PROFILE


def unwrap_api_response(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "data" in payload and payload.get("success") is True:
        return dict(payload["data"] or {})
    if isinstance(payload, dict):
        return payload
    raise RuntimeError("Backend returned an unexpected JSON payload.")


def post_first_available(
    client: httpx.Client,
    paths: tuple[str, ...],
    *,
    json_payload: dict[str, Any],
) -> httpx.Response:
    last_response: httpx.Response | None = None
    for path in paths:
        response = client.post(path, json=json_payload)
        if response.status_code in {404, 405}:
            last_response = response
            continue
        return response

    if last_response is not None:
        return last_response

    raise RuntimeError("No auth route candidates were configured.")


def ensure_user_access_token(
    client: httpx.Client,
    *,
    existing_access_token: str,
    email: str,
    password: str,
    full_name: str,
    phone_number: str,
    region_code: str,
    username: str,
    allow_register: bool,
) -> str:
    candidate = str(existing_access_token or "").strip()
    if candidate:
        return candidate

    if not str(email or "").strip() or not str(password or "").strip():
        raise RuntimeError("Backend login credentials are required when no provisioning access token is supplied.")

    login_response = post_first_available(
        client,
        AUTH_LOGIN_PATHS,
        json_payload={"email": email, "password": password},
    )
    if login_response.status_code < 300:
        return str(unwrap_api_response(login_response).get("access_token") or "").strip()

    if login_response.status_code not in {400, 401, 404, 409, 422}:
        login_response.raise_for_status()

    if not allow_register:
        raise RuntimeError(
            "Backend login failed and automatic registration is disabled. Re-run with explicit credentials that can log in, "
            "provide --user-access-token, or pass --allow-register."
        )

    register_response = post_first_available(
        client,
        AUTH_REGISTER_PATHS,
        json_payload={
            "email": email,
            "full_name": full_name,
            "phone_number": phone_number,
            "is_over_18": True,
            "region_code": region_code,
            "username": username,
            "password": password,
        },
    )
    if register_response.status_code < 300:
        return str(unwrap_api_response(register_response).get("access_token") or "").strip()
    if register_response.status_code != 409:
        register_response.raise_for_status()

    retry_login_response = post_first_available(
        client,
        AUTH_LOGIN_PATHS,
        json_payload={"email": email, "password": password},
    )
    retry_payload = unwrap_api_response(retry_login_response)
    access_token = str(retry_payload.get("access_token") or "").strip()
    if not access_token:
        raise RuntimeError("Backend auth flow did not return an access token.")
    return access_token


def select_match(client: httpx.Client, *, tick_count: int) -> dict[str, Any]:
    tick_response = client.post("/infinite-league/tick", params={"count": max(tick_count, 1)})
    tick_response.raise_for_status()
    matches = tick_response.json().get("matches") or []
    if not matches:
        raise RuntimeError("Backend returned no infinite-league matches.")
    match = matches[0]

    match_id = str(match.get("match_id") or "").strip()
    if not match_id:
        raise RuntimeError("Backend returned an invalid match_id.")

    return {"match_id": match_id}


def resolve_match_selection(client: httpx.Client, args: argparse.Namespace) -> dict[str, Any]:
    match_id = str(args.match_id or "").strip()
    if match_id:
        return {"match_id": match_id, "selection_mode": "explicit_match_id"}

    allow_generation = args.profile == LOCAL_PROFILE or args.allow_match_generation
    if not allow_generation:
        raise RuntimeError(
            f"Non-local provisioning requires --match-id for the '{args.profile}' profile unless --allow-match-generation is explicitly set."
        )

    selection = select_match(client, tick_count=args.tick_count)
    selection["selection_mode"] = "generated_match"
    return selection


def fetch_match_viewer_session(
    client: httpx.Client,
    *,
    match_id: str,
    user_access_token: str,
) -> dict[str, Any]:
    response = client.get(
        f"/api/match-viewer/{match_id}/session",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    if response.status_code == 404:
        raise RuntimeError(
            "The target backend does not expose the canonical match viewer session route "
            f"'/api/match-viewer/{match_id}/session'. Deploy the current backend to the target environment "
            "or use the local backend flow instead."
        )
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("match_id") or "").strip() != match_id:
        raise RuntimeError("Match viewer session returned an unexpected match_id.")
    if not payload.get("frames"):
        raise RuntimeError("Match viewer session did not include backend-authored frames.")
    return payload


def fetch_match_viewer_state(
    client: httpx.Client,
    *,
    match_id: str,
    user_access_token: str,
) -> dict[str, Any]:
    response = client.get(
        f"/api/match-viewer/{match_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    response.raise_for_status()
    live_payload = response.json()
    if live_payload.get("match_id") != match_id:
        raise RuntimeError("Match viewer state returned an unexpected match_id.")
    return live_payload


def build_websocket_url(base_url: str, match_id: str) -> str:
    websocket_url = str(base_url or "").strip().rstrip("/")
    if websocket_url.startswith("https://"):
        websocket_url = "wss://" + websocket_url[len("https://") :]
    elif websocket_url.startswith("http://"):
        websocket_url = "ws://" + websocket_url[len("http://") :]
    return websocket_url.rstrip("/") + f"/api/matches/{match_id}/stream"


async def verify_websocket(base_url: str, match_id: str, user_access_token: str) -> dict[str, Any]:
    websocket_url = build_websocket_url(base_url, match_id)

    async with websockets.connect(
        websocket_url,
        open_timeout=30,
        close_timeout=10,
        max_size=None,
        additional_headers={"Authorization": f"Bearer {user_access_token}"},
    ) as websocket:
        ack_payload = json.loads(await websocket.recv())
        if ack_payload.get("type") != "subscription_ack":
            raise RuntimeError("Match realtime stream did not acknowledge the subscription.")
        await websocket.send(json.dumps({"type": "ping"}))
        pong_payload = json.loads(await websocket.recv())
        if pong_payload.get("type") != "pong":
            raise RuntimeError("Match realtime stream did not respond to ping.")

        return {
            "ack_topics": ack_payload.get("data", {}).get("topics"),
            "pong": True,
            "websocket_url": websocket_url,
        }


def write_runtime_config(
    config_path: Path,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if not config_path.exists():
        return {"enabled": True, "runtimeMode": "match_center", "autoStartOnBoot": False}

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["enabled"] = True
    payload["autoStartOnBoot"] = False
    payload["runtimeMode"] = "match_center"
    payload["environment"] = "local"
    payload["matchId"] = ""

    if not dry_run:
        config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return payload


def write_bootstrap_file(
    bootstrap_paths: list[Path],
    *,
    profile: str,
    base_url: str,
    match_id: str,
    bootstrap_ttl_seconds: int,
    consume_on_load: bool,
    dry_run: bool,
) -> dict[str, Any]:
    ttl_seconds = max(60, int(bootstrap_ttl_seconds))
    payload = {
        "profile": str(profile or "").strip() or LOCAL_PROFILE,
        "runtimeMode": "live",
        "environment": "custom",
        "matchId": match_id,
        "baseUrl": base_url,
        "matchViewerSessionPath": f"/api/match-viewer/{match_id}/session",
        "matchViewerStatePath": f"/api/match-viewer/{match_id}",
        "matchSpectatePath": f"/api/matches/{match_id}/spectate",
        "matchWebsocketPath": f"/api/matches/{match_id}/stream",
        "realtimeGatewayPath": f"/api/matches/{match_id}/spectate",
        "realtimeWebsocketPath": f"/api/matches/{match_id}/stream",
        "issuedAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "bootstrapTtlSeconds": ttl_seconds,
        "consumeOnLoad": bool(consume_on_load),
    }

    if not dry_run:
        serialized_payload = json.dumps(payload, indent=2) + "\n"
        for bootstrap_path in bootstrap_paths:
            bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
            bootstrap_path.write_text(serialized_payload, encoding="utf-8")

    return payload


def main() -> None:
    args = parse_args()
    base_url = normalize_base_url(args.base_url, profile=args.profile)
    user_identity = resolve_user_identity(args)
    allow_register = should_allow_register(args)
    config_path = Path(args.runtime_config).resolve()
    bootstrap_path = Path(args.bootstrap_path).resolve()
    bootstrap_paths = [bootstrap_path]
    bootstrap_ttl_seconds = max(60, int(args.bootstrap_ttl_seconds))
    consume_bootstrap_on_load = not (args.keep_bootstrap_file or args.profile == LOCAL_PROFILE)
    try:
        with httpx.Client(base_url=base_url, timeout=60.0) as client:
            user_access_token = ensure_user_access_token(
                client,
                existing_access_token=args.user_access_token,
                email=user_identity["email"],
                password=user_identity["password"],
                full_name=user_identity["full_name"],
                phone_number=user_identity["phone_number"],
                region_code=user_identity["region_code"],
                username=user_identity["username"],
                allow_register=allow_register,
            )
            selection = resolve_match_selection(client, args)
            match_id = selection["match_id"]
            viewer_session = fetch_match_viewer_session(
                client,
                match_id=match_id,
                user_access_token=user_access_token,
            )
            live_payload = fetch_match_viewer_state(
                client,
                match_id=match_id,
                user_access_token=user_access_token,
            )
    except httpx.ConnectError as exception:
        raise RuntimeError(build_backend_unreachable_message(base_url, args.profile)) from exception

    websocket_result = None
    if not args.skip_websocket_verify:
        try:
            websocket_result = asyncio.run(verify_websocket(base_url, match_id, user_access_token))
        except (httpx.ConnectError, OSError) as exception:
            raise RuntimeError(build_backend_unreachable_message(base_url, args.profile)) from exception

    config_payload = write_runtime_config(
        config_path,
        dry_run=args.dry_run,
    )
    bootstrap_payload = write_bootstrap_file(
        bootstrap_paths,
        profile=args.profile,
        base_url=base_url,
        match_id=match_id,
        bootstrap_ttl_seconds=bootstrap_ttl_seconds,
        consume_on_load=consume_bootstrap_on_load,
        dry_run=args.dry_run,
    )

    summary = {
        "profile": args.profile,
        "match_id": match_id,
        "match_selection_mode": selection.get("selection_mode"),
        "base_url": base_url,
        "runtime_config": str(config_path),
        "bootstrap_path": str(bootstrap_path),
        "bootstrap_paths": [str(path) for path in bootstrap_paths],
        "bootstrap_mirror_count": max(0, len(bootstrap_paths) - 1),
        "config_written": not args.dry_run,
        "bootstrap_written": not args.dry_run,
        "bootstrap_profile": bootstrap_payload.get("profile"),
        "auth_mode": (
            "access_token"
            if str(args.user_access_token or "").strip()
            else ("login_or_register" if allow_register else "login_only")
        ),
        "bootstrap_ttl_seconds": bootstrap_ttl_seconds,
        "bootstrap_consume_on_load": consume_bootstrap_on_load,
        "session_frame_count": len(viewer_session.get("frames") or []),
        "session_event_count": len(viewer_session.get("events") or []),
        "score_reveal_locked": viewer_session.get("score_reveal_locked"),
        "timeline_proof_status": (viewer_session.get("timeline_proof") or {}).get("status"),
        "http_frame_count": len(live_payload.get("frames") or []),
        "http_event_count": len(live_payload.get("events") or []),
        "match_viewer_state_url": f"{base_url}/api/match-viewer/{match_id}",
        "websocket_url": build_websocket_url(base_url, match_id),
        "websocket": websocket_result,
        "runtime_mode": config_payload.get("runtimeMode"),
        "auto_start_on_boot": config_payload.get("autoStartOnBoot"),
        "enabled": config_payload.get("enabled"),
        "bootstrap_mode": "match_center_session",
        "config_match_id_present": bool(str(config_payload.get("matchId") or "").strip()),
        "bootstrap_match_id_present": bool(str(bootstrap_payload.get("matchId") or "").strip()),
        "bootstrap_has_match_viewer_session_path": bool(bootstrap_payload.get("matchViewerSessionPath")),
        "bootstrap_has_realtime_websocket_path": bool(bootstrap_payload.get("realtimeWebsocketPath")),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("[GTEX] Provisioning cancelled.")
    except (FileNotFoundError, RuntimeError, httpx.HTTPError, websockets.WebSocketException) as exception:
        raise SystemExit(f"[GTEX] {exception}")
