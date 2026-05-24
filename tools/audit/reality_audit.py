from __future__ import annotations

import re
import shutil
import subprocess
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_LIB_ROOT = REPO_ROOT / "frontend" / "lib"
KORAPAY_SECRET_ENV_KEYS = (
    "GTE_KORAPAY_PUBLIC_KEY",
    "GTE_KORAPAY_SECRET_KEY",
    "GTE_KORAPAY_ENCRYPTION_KEY",
    "GTE_KORAPAY_WEBHOOK_SECRET",
)
TREASURY_SECRET_ENV_KEYS = (
    "TREASURY_BANK_NAME",
    "TREASURY_ACCOUNT_NAME",
    "TREASURY_ACCOUNT_NUMBER",
)

_KORAPAY_PUBLIC_LIVE_PREFIX = "pk_" + "live_"
_KORAPAY_SECRET_LIVE_PREFIX = "sk_" + "live_"
LIVE_SECRET_PATTERNS = (
    re.compile(rf"\b{re.escape(_KORAPAY_PUBLIC_LIVE_PREFIX)}[A-Za-z0-9]{{12,}}\b"),
    re.compile(rf"\b{re.escape(_KORAPAY_SECRET_LIVE_PREFIX)}[A-Za-z0-9]{{12,}}\b"),
    re.compile(r"https://checkout\.korapay\.com/pay/[A-Za-z0-9]+"),
)
LIVE_SECRET_GIT_REGEX = (
    rf"{re.escape(_KORAPAY_PUBLIC_LIVE_PREFIX)}[A-Za-z0-9]{{12,}}|"
    rf"{re.escape(_KORAPAY_SECRET_LIVE_PREFIX)}[A-Za-z0-9]{{12,}}|"
    r"checkout\.korapay\.com/pay/[A-Za-z0-9]+"
)
DART_IMPORT_PATTERN = re.compile(r"^\s*import\s+['\"]([^'\"]+)['\"]")

TEXT_SUFFIXES = {
    ".dart",
    ".env",
    ".json",
    ".md",
    ".py",
    ".ps1",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
LOCAL_SECRET_SCAN_ROOTS = (
    ".dart_tool",
    "frontend/.dart_tool",
    ".runtime",
    "backend/generated_media",
    "backend/media_dropzones",
)
CURRENT_SECRET_SCAN_ROOTS = (
    ".github",
    "backend/app",
    "backend/tests",
    "docs",
    "frontend/lib",
    "frontend/test",
    "frontend/tool",
    "render.yaml",
    "shared",
    "tools",
)
ROOT_SECRET_SCAN_FILES = (
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    "package.json",
    "pyproject.toml",
)
SECRET_SCAN_PATHS = (
    "*.dart",
    "*.env",
    "*.json",
    "*.md",
    "*.py",
    "*.ps1",
    "*.sh",
    "*.toml",
    "*.txt",
    "*.yaml",
    "*.yml",
)
STRICT_LIVE_PHASE2_SMOKE_MARKERS = (
    ("profile/bootstrap", "/api/session/bootstrap"),
    ("admin rejection", "/api/admin/operations-readiness"),
    ("club snapshot/no-club", "/api/club/current"),
    ("national rental", "/api/national/competitions/{competition_id}/rental-pool"),
    ("competition runtime", "/api/competitions/runtime/world-super-cup"),
    ("world-super-cup bracket", "/api/world-super-cup/knockout/bracket"),
    ("realtime auth/provenance", "/realtime/stream"),
    ("treasury invalid-claim", "/api/admin/treasury/withdrawals/{withdrawal_id}/status"),
)


def main() -> int:
    failures: list[str] = []
    failures.extend(_secret_failures())
    failures.extend(_git_history_secret_failures())
    failures.extend(_local_generated_secret_failures())
    failures.extend(_strict_live_failures())
    failures.extend(_strict_live_phase2_smoke_failures())
    failures.extend(_render_config_failures())
    failures.extend(_frontend_dependency_failures())
    failures.extend(_production_operability_failures())
    if failures:
        print("[reality-audit] FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[reality-audit] strict-live production checks passed.")
    return 0


def _git_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [REPO_ROOT / line.strip() for line in result.stdout.splitlines() if line.strip()]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")


def _secret_failures() -> list[str]:
    python_matches = _python_secret_scan(_current_secret_scan_files())
    if python_matches:
        return ["live secret-like value found in current worktree: " + "; ".join(python_matches[:5])]
    matches, error = _run_rg_secret_scan(
        CURRENT_SECRET_SCAN_ROOTS,
        timeout=_scan_timeout("GTE_REALITY_AUDIT_CURRENT_TIMEOUT_SECONDS", 30),
    )
    if error:
        return [f"could not scan current worktree for live secrets: {error}"]
    if not matches:
        return []
    return ["live secret-like value found in current worktree: " + "; ".join(matches[:5])]


def _git_history_secret_failures() -> list[str]:
    depth = _history_depth()
    rev_list_command = ["git", "rev-list", "--all"]
    if depth > 0:
        rev_list_command.append(f"--max-count={depth}")
    rev_list = subprocess.run(
        rev_list_command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if rev_list.returncode != 0:
        return [f"could not enumerate git history for live KoraPay secret scan: {rev_list.stderr.strip()}"]
    commits = [line.strip() for line in rev_list.stdout.splitlines() if line.strip()]
    if not commits:
        return []
    try:
        result = subprocess.run(
            [
                "git",
                "grep",
                "-I",
                "-n",
                "-E",
                LIVE_SECRET_GIT_REGEX,
                *commits,
                "--",
                *CURRENT_SECRET_SCAN_ROOTS,
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=_history_scan_timeout(),
        )
    except subprocess.TimeoutExpired:
        scan_scope = "all reachable commits" if depth == 0 else f"latest {depth} reachable commit(s)"
        return [
            "git history secret scan timed out for "
            f"{scan_scope}; rerun with GTE_REALITY_AUDIT_HISTORY_DEPTH set lower locally, "
            "or run the full scan in CI before production release."
        ]
    if result.returncode == 1:
        return []
    if result.returncode != 0:
        return [f"could not scan git history for live KoraPay secrets: {result.stderr.strip()}"]
    matches = [line for line in result.stdout.splitlines() if line.strip()]
    if not matches:
        return []
    unique_commits = {line.split(":", 1)[0] for line in matches if ":" in line and line.split(":", 1)[0]}
    scan_scope = "all reachable commits" if depth == 0 else f"latest {depth} reachable commit(s)"
    return [
        "live secret-like value appears in git history "
        f"({scan_scope}); rotate exposed credentials and purge affected commits "
        f"before production ({len(unique_commits)} commit(s))."
    ]


def _current_secret_scan_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=_scan_timeout("GTE_REALITY_AUDIT_CURRENT_TIMEOUT_SECONDS", 90),
    )
    if result.returncode != 0:
        return _git_files()
    files: list[Path] = []
    for line in result.stdout.splitlines():
        relative_path = line.strip()
        if not relative_path:
            continue
        path = REPO_ROOT / relative_path
        if _is_secret_scan_candidate(path):
            files.append(path)
    return files


def _is_secret_scan_candidate(path: Path) -> bool:
    try:
        relative = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return False
    if relative not in ROOT_SECRET_SCAN_FILES and not any(
        relative == root or relative.startswith(f"{root}/") for root in CURRENT_SECRET_SCAN_ROOTS
    ):
        return False
    ignored_parts = {
        ".dart_tool",
        ".pytest_tmp",
        ".runtime",
        ".codex_tmp_gtex_player_data_repair_loop",
        "_zip_review",
        "build",
        "generated_media",
        "media_dropzones",
        "generated",
    }
    if any(part in ignored_parts for part in path.parts):
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    try:
        return path.is_file() and path.stat().st_size <= 2_000_000
    except OSError:
        return False


def _python_secret_scan(files: list[Path]) -> list[str]:
    matches: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in LIVE_SECRET_PATTERNS):
                matches.append(f"{path.relative_to(REPO_ROOT).as_posix()}:{line_number}")
                break
    return matches


def _history_depth() -> int:
    raw_depth = os.environ.get("GTE_REALITY_AUDIT_HISTORY_DEPTH", "20")
    try:
        return max(0, int(raw_depth))
    except ValueError:
        return 20


def _history_scan_timeout() -> int:
    return _scan_timeout("GTE_REALITY_AUDIT_HISTORY_TIMEOUT_SECONDS", 60)


def _scan_timeout(env_name: str, default: int) -> int:
    raw_timeout = os.environ.get(env_name, str(default))
    try:
        return max(10, int(raw_timeout))
    except ValueError:
        return default


def _production_operability_failures() -> list[str]:
    failures: list[str] = []
    metrics = _read("backend/app/observability/metrics.py")
    for metric_name in (
        "gtex_strict_live_blocked_states_total",
        "gtex_strict_live_payload_rejections_total",
        "gtex_auth_rejections_total",
        "gtex_realtime_reconnects_total",
        "gtex_settlement_failures_total",
        "gtex_queue_backlog_depth",
    ):
        if metric_name not in metrics:
            failures.append(f"Production observability missing {metric_name}.")
    middleware = _read("backend/app/observability/middleware.py")
    if "X-Correlation-ID" not in middleware or "request.state.correlation_id" not in middleware:
        failures.append("Observability middleware does not propagate request correlation IDs.")
    load_harness_path = REPO_ROOT / "tools" / "load" / "strict_live_runtime_load.py"
    if not load_harness_path.exists():
        failures.append("Strict-live load harness is missing.")
    else:
        load_harness = load_harness_path.read_text(encoding="utf-8", errors="ignore")
        if "strict_live" not in load_harness or "fixture/mock/demo base URLs" not in load_harness:
            failures.append("Strict-live load harness does not enforce live-only probe targets.")
        for endpoint in (
            "/api/session/bootstrap",
            "/api/admin/readiness",
            "/api/national/eligible-players",
            "/api/world-super-cup/bracket",
        ):
            if endpoint not in load_harness:
                failures.append(f"Strict-live load harness does not probe {endpoint}.")
    if not (REPO_ROOT / "tests" / "smoke" / "live" / "test_strict_live_load_harness.py").exists():
        failures.append("Strict-live load harness smoke tests are missing.")
    return failures


def _strict_live_phase2_smoke_failures() -> list[str]:
    smoke_path = REPO_ROOT / "tests" / "smoke" / "live" / "test_strict_live_phase2_payload_contracts.py"
    if not smoke_path.exists():
        return ["Strict-live Phase 2 payload smoke tests are missing."]
    smoke_source = smoke_path.read_text(encoding="utf-8", errors="ignore")
    failures: list[str] = []
    for label, marker in STRICT_LIVE_PHASE2_SMOKE_MARKERS:
        if marker not in smoke_source:
            failures.append(f"Strict-live Phase 2 smoke coverage is missing {label}: {marker}.")
    for marker in ("demo", "fixture", "mock", "synthetic"):
        if marker not in smoke_source:
            failures.append(f"Strict-live Phase 2 smoke coverage does not assert {marker} rejection.")
    return failures


def _local_generated_secret_failures() -> list[str]:
    roots = [relative_root for relative_root in LOCAL_SECRET_SCAN_ROOTS if (REPO_ROOT / relative_root).exists()]
    if not roots:
        return []
    matches, error = _run_rg_secret_scan(roots, timeout=45)
    if error:
        return [f"could not scan local generated/cache files for live secrets: {error}"]
    if not matches:
        return []
    return ["live secret-like value found in local generated/cache files: " + "; ".join(matches[:5])]


def _run_rg_secret_scan(roots: tuple[str, ...] | list[str], *, timeout: int) -> tuple[list[str], str | None]:
    if shutil.which("rg") is None:
        return [], "ripgrep is required for bounded secret scans."
    command = [
        "rg",
        "-I",
        "--hidden",
        "--no-messages",
        "--max-filesize",
        "2M",
        "-n",
        LIVE_SECRET_GIT_REGEX,
        *roots,
    ]
    for pathspec in SECRET_SCAN_PATHS:
        command.extend(["--glob", pathspec])
    for pathspec in (
        "!**/.dart_tool/**",
        "!**/.pytest_tmp/**",
        "!**/.runtime/**",
        "!**/.codex_tmp_gtex_player_data_repair_loop/**",
        "!**/_zip_review/**",
        "!**/build/**",
        "!backend/generated_media/**",
        "!backend/media_dropzones/**",
        "!frontend/lib/data/generated/**",
    ):
        command.extend(["--glob", pathspec])
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [], f"ripgrep timed out after {timeout}s"
    if result.returncode == 1:
        return [], None
    if result.returncode != 0:
        return [], result.stderr.strip()
    return [line for line in result.stdout.splitlines() if line.strip()], None


def _strict_live_failures() -> list[str]:
    failures: list[str] = []
    main_dart = _read("frontend/lib/main.dart")
    if "final GteAppConfig appConfig = GteAppConfig.fromEnvironment();" not in main_dart:
        failures.append("Frontend bootstrap does not resolve GteAppConfig before creating production clients.")
    if "validateGtexStrictLiveStartup(appConfig);" not in main_dart:
        failures.append("Frontend bootstrap does not validate strict-live startup before runApp.")
    if "GteExchangeApiClient.standard(" not in main_dart:
        failures.append("Frontend bootstrap does not use the standard live exchange client.")
    if "GteExchangeApiClient.fixture(" in main_dart or "GteMockApi(" in main_dart:
        failures.append("Frontend bootstrap references fixture/mock clients.")

    legacy_app_controller = _read("frontend/lib/legacy/gte_app_controller.dart")
    if "GteMockApi(" in legacy_app_controller:
        failures.append("Legacy app controller still defaults to GteMockApi.")

    creator_social_controller = _read(
        "frontend/lib/features/creator_social_redesign/presentation/gtex_creator_social_controller.dart"
    )
    if "snapshot ?? GtexCreatorSocialSnapshot.demo()" in creator_social_controller:
        failures.append("Creator social controller still defaults to demo snapshot data.")
    if "bool get hasLiveSnapshot" not in creator_social_controller:
        failures.append("Creator social controller does not expose live snapshot readiness.")
    creator_dashboard_screen = _read("frontend/lib/screens/creators/gtex_creator_dashboard_screen_v2.dart")
    referral_hub_screen = _read("frontend/lib/screens/referrals/gtex_referral_hub_screen_v2.dart")
    fan_hub_screen = _read("frontend/lib/features/social/gtex_social_fan_hub_screen_v2.dart")
    for label, source, blocked_title in (
        ("Creator Dashboard V2", creator_dashboard_screen, "Live creator workspace unavailable"),
        ("Referral Hub V2", referral_hub_screen, "Live referral data unavailable"),
        ("Fan Hub V2", fan_hub_screen, "Live fan hub unavailable"),
    ):
        if "allowFixtureData" not in source:
            failures.append(f"{label} does not require explicit fixture opt-in for creator/social demo data.")
        if blocked_title not in source:
            failures.append(f"{label} does not render a truthful blocked state when live data is missing.")

    onboarding_controller = _read("frontend/lib/features/onboarding_redesign/onboarding_redesign_controller.dart")
    onboarding_screen = _read("frontend/lib/features/onboarding_redesign/gtex_onboarding_flow_screen_v2.dart")
    if "initialState ?? GtexOnboardingFixtures.state" in onboarding_controller:
        failures.append("Onboarding controller still defaults to fixture onboarding state.")
    if "bool get hasLiveState" not in onboarding_controller:
        failures.append("Onboarding controller does not expose live onboarding readiness.")
    if "Live onboarding unavailable" not in onboarding_screen:
        failures.append("Onboarding flow does not block when live onboarding state is missing.")

    admin_notification_matrix = _read("frontend/lib/screens/admin/gtex_admin_notification_matrix_screen.dart")
    if "fixture-admin-target" in admin_notification_matrix:
        failures.append("Admin notification matrix still pre-fills a fixture target user.")

    shared_club_provider = _read("frontend/lib/shared/providers/club_provider.dart")
    club_screen = _read("frontend/lib/features/club/club_screen.dart")
    if "Lagos Atlas FC" in shared_club_provider or "Provider<Club>(" in shared_club_provider:
        failures.append("Shared club provider still serves a hard-coded registered club.")
    if "Live club workspace unavailable" not in club_screen or "allowFixtureData" not in club_screen:
        failures.append("Legacy Club HQ does not fail closed unless fixture data is explicitly allowed.")

    shared_match_provider = _read("frontend/lib/shared/providers/match_provider.dart")
    for synthetic_match_text in ("atlas-v-phoenix", "Nairobi Phoenix", "Kigali Wave"):
        if synthetic_match_text in shared_match_provider:
            failures.append("Shared match provider still serves hard-coded live match rows.")
            break

    exchange_hub_provider = _read("frontend/lib/shared/providers/exchange_hub_provider.dart")
    if "liveAuthorityAvailable: false" not in exchange_hub_provider:
        failures.append("Exchange hub provider does not expose a blocked live-authority state.")
    if "PaymentMethod { paystack" in exchange_hub_provider or "PaymentMethod.paystack" in exchange_hub_provider:
        failures.append("Exchange hub payment methods still expose Paystack.")
    for synthetic_exchange_text in (
        "market-mbappe",
        "Kylian Mbappe",
        "walletBalanceGtex: 12.5",
        "KoraPay deposit",
        "Ayo Manager",
    ):
        if synthetic_exchange_text in exchange_hub_provider:
            failures.append("Exchange hub provider still seeds synthetic wallet/player market state.")
            break

    transfer_provider = _read("frontend/lib/shared/providers/transfer_provider.dart")
    if "_fallbackUserClubName" in transfer_provider or "GTEX United" in transfer_provider:
        failures.append("Transfer provider still invents a fallback user club name.")
    for synthetic_transfer_text in (
        "fallback: 'Transfer Target'",
        "fallback: 'Open Market'",
        "fallback: 'player-$listingId'",
        "fallback: 'transfer-listing-",
    ):
        if synthetic_transfer_text in transfer_provider:
            failures.append("Transfer provider still synthesizes missing live listing/player identity.")
            break
    transfer_build = _slice_between(
        transfer_provider,
        "TransferMarketState build()",
        "TransferMarketState _buildEmptyState()",
    )
    if "_buildFixtureState()" in transfer_build and "_backendMode == GteBackendMode.fixture" not in transfer_build:
        failures.append("Transfer provider fixture state is not gated to explicit fixture backend mode.")

    tournaments_screen = _read("frontend/lib/features/tournaments/tournaments_screen.dart")
    tournament_screen = _read("frontend/lib/features/tournaments/tournament_screen.dart")
    if "Live tournaments unavailable" not in tournaments_screen or "allowFixtureData" not in tournaments_screen:
        failures.append("Legacy tournaments screen does not block generated tournament fixtures by default.")
    for direct_tournament_fallback in (
        "widget.fixtures ?? buildTournamentFixtures",
        "widget.standings ?? buildTournamentStandings",
        "squad.isEmpty ? buildTournamentSquad",
    ):
        if direct_tournament_fallback in tournament_screen:
            failures.append(
                "Tournament screen still builds client-generated fixtures/standings without fixture opt-in."
            )
            break

    funding_flow_screen = _read("frontend/lib/screens/wallet/gte_funding_flow_screen.dart")
    for forbidden_mock_payment_text in (
        "_simulateMockFailure",
        "Mark test payment",
        "Verify test payment",
        "Test payment mode",
        "test payment mode",
    ):
        if forbidden_mock_payment_text in funding_flow_screen:
            failures.append("Wallet funding flow still exposes mock payment controls.")
            break
    if "Live payment provider returned a mock session" not in funding_flow_screen:
        failures.append("Wallet funding flow does not fail closed when a mock payment session is returned.")

    exchange_client = _read("frontend/lib/data/gte_exchange_api_client.dart")
    standard_factory = _slice_between(
        exchange_client,
        "factory GteExchangeApiClient.standard",
        "factory GteExchangeApiClient.fixture",
    )
    if "GteMockApi" in standard_factory:
        failures.append("GteExchangeApiClient.standard still registers GteMockApi.")
    if "fixtures: const GteFixtureRepositoryUnavailable()" not in standard_factory:
        failures.append("GteExchangeApiClient.standard does not install the unavailable fixture repository.")
    exchange_fixture_factory = _slice_between(
        exchange_client,
        "factory GteExchangeApiClient.fixture",
        "Future<GteAuthSession> login",
    )
    if "assertFixtureFactoryAllowed('GteExchangeApiClient.fixture')" not in exchange_fixture_factory:
        failures.append("GteExchangeApiClient.fixture is not guarded to Flutter test runtime.")
    public_fallback_gate = _slice_between(exchange_client, "Future<T> _loadPublicWithFallback", "Map<String, Object?>")
    if (
        "if (config.mode == GteBackendMode.fixture)" not in public_fallback_gate
        or "return liveCall();" not in public_fallback_gate
    ):
        failures.append("Public exchange fallback helper is not explicitly gated to fixture mode.")

    api_repository = _read("frontend/lib/data/gte_api_repository.dart")
    repository_fallback_gate = _slice_between(api_repository, "Future<T> _withFallback", "Future<T?> _safeFixture")
    if (
        "if (config.mode == GteBackendMode.fixture)" not in repository_fallback_gate
        or "return liveCall();" not in repository_fallback_gate
    ):
        failures.append("Mode-aware repository fallback helper is not explicitly gated to fixture mode.")

    trader_api = _read("frontend/lib/data/trader_api.dart")
    trader_standard_factory = _slice_between(
        trader_api,
        "factory TraderApi.standard",
        "factory TraderApi.fixture",
    )
    if (
        "resolvedMode == GteBackendMode.fixture" in trader_standard_factory
        and "assertFixtureFactoryAllowed('TraderApi.standard fixture mode')" not in trader_standard_factory
    ):
        failures.append("TraderApi.standard fixture mode is not guarded to Flutter test runtime.")
    trader_fixture_factory = _slice_between(
        trader_api,
        "factory TraderApi.fixture",
        "Future<TraderOverview> overview",
    )
    if "assertFixtureFactoryAllowed('TraderApi.fixture')" not in trader_fixture_factory:
        failures.append("TraderApi.fixture is not guarded to Flutter test runtime.")

    for dart_path in FRONTEND_LIB_ROOT.rglob("*.dart"):
        source = dart_path.read_text(encoding="utf-8")
        if ".fixture" not in source:
            continue
        relative_path = str(dart_path.relative_to(REPO_ROOT)).replace("\\", "/")
        for match in re.finditer(r"(?:factory|const)\s+([A-Za-z0-9_]+)\.fixture\b", source):
            factory_name = match.group(1)
            factory_window = source[match.start() : match.start() + 800]
            guard = f"assertFixtureFactoryAllowed('{factory_name}.fixture')"
            if guard not in factory_window:
                failures.append(f"{relative_path} exposes {factory_name}.fixture without a test-runtime guard.")
            if "package:gte_frontend/app/test_runtime_detector.dart" not in source:
                failures.append(f"{relative_path} exposes fixture factories without importing the runtime guard.")

    national_api = _read("frontend/lib/data/national_team_api.dart")
    standard_start = national_api.find("factory NationalTeamApi.standard")
    fixture_start = national_api.find("factory NationalTeamApi.fixture")
    standard_body = (
        national_api[standard_start:fixture_start] if standard_start >= 0 and fixture_start > standard_start else ""
    )
    if "_NationalTeamFixtures.seed()" in standard_body:
        failures.append("NationalTeamApi.standard still registers seeded fixtures.")

    national_screen = _read(
        "frontend/lib/features/national_team_rental_redesign/presentation/gtex_national_team_rental_screen.dart"
    )
    if "this.competitions = GtexNationalTeamRentalDemoData.competitions" in national_screen:
        failures.append("National Rental V2 base widget still defaults to demo competitions.")

    national_wrapper = _read("frontend/lib/screens/gtex_national_team_rental_screen_v2.dart")
    if "_marketFallbackRentalPlayerView" in national_wrapper:
        failures.append("National Rental V2 still synthesizes players from market fallback data.")
    if "fetchMarketNationalTeams" in national_wrapper:
        failures.append("National Rental V2 still reads market nationality fallback data for rental countries.")
    if "_countryViewsFromPool" not in national_wrapper:
        failures.append("National Rental V2 does not derive country options from backend rental-pool authority.")

    profile_adapter = _read("frontend/lib/features/system_profile_redesign/data/profile_runtime_adapter.dart")
    profile_controller = _read(
        "frontend/lib/features/system_profile_redesign/presentation/gtex_profile_controller.dart"
    )
    profile_models = _read("frontend/lib/features/system_profile_redesign/models/gtex_profile_models.dart")
    for endpoint in (
        "'/api/session/bootstrap'",
        "'/api/profile'",
        "'/api/profile/security'",
        "'/api/profile/sessions'",
        "'/api/wallet/summary'",
        "'/api/club/current'",
    ):
        if endpoint not in profile_adapter:
            failures.append(f"Profile runtime adapter does not consume {endpoint}.")
    if "GteApiErrorType.notFound" not in profile_adapter:
        failures.append("Profile runtime adapter does not treat no-club 404 as an explicit no-club state.")
    if "allowDemo" in profile_controller or "GtexProfileSummary.demo" in profile_models:
        failures.append("Profile redesign production code still exposes demo profile data.")
    admin_command_screen = _read("frontend/lib/screens/admin/gtex_admin_command_center_screen_v2.dart")
    admin_command_models = _read("frontend/lib/features/admin_command_redesign/models/gtex_admin_command_models.dart")
    if "allowDemo" in admin_command_screen or "GtexAdminCommandSnapshot.demo" in admin_command_models:
        failures.append("Admin command redesign production code still exposes demo command data.")
    admin_newsroom_screen = _read("frontend/lib/screens/admin/gtex_admin_newsroom_screen_v2.dart")
    if "loadDemoNewsroomQueue" in admin_newsroom_screen:
        failures.append("Admin Newsroom V2 still loads a demo newsroom queue in production code.")

    notifications_screen = _read("frontend/lib/screens/notifications/gte_notifications_screen_v2.dart")
    notifications_init = _slice_between(notifications_screen, "void initState()", "Future<void> _loadLiveNotifications")
    if "allowFixtureData" not in notifications_screen:
        failures.append("Notifications V2 does not require explicit fixture opt-in for demo notification data.")
    if "loadDemoNotifications" in notifications_init and "_canUseFixtureData" not in notifications_init:
        failures.append("Notifications V2 loads demo notifications without explicit fixture gating.")

    chat_screen = _read("frontend/lib/screens/chat/gtex_chat_screen_v2.dart")
    chat_init = _slice_between(chat_screen, "void initState()", "@override\n  Widget build")
    chat_build = _slice_between(chat_screen, "Widget build(BuildContext context)", "class _ConversationList")
    if "allowFixtureData" not in chat_screen:
        failures.append("Chat V2 does not require explicit fixture opt-in for demo conversations.")
    if "loadDemoConversations" in chat_init and "widget.allowFixtureData" not in chat_init:
        failures.append("Chat V2 loads demo conversations without explicit fixture gating.")
    if "loadDemoMessages" in chat_build and "widget.allowFixtureData" not in chat_build:
        failures.append("Chat V2 loads demo messages without explicit fixture gating.")
    if "Live chat unavailable" not in chat_screen:
        failures.append("Chat V2 does not render a truthful blocked state when no live chat API is injected.")

    news_agency_screen = _read("frontend/lib/features/news_agency/gtex_news_agency_screen_v2.dart")
    news_load_articles = _slice_between(
        news_agency_screen, "Future<List<GtexNewsArticle>> _loadArticles", "void _refresh()"
    )
    if "allowFixtureData" not in news_agency_screen:
        failures.append("News Agency V2 does not require explicit fixture opt-in for demo articles.")
    if "loadDemoArticles" in news_load_articles and "widget.allowFixtureData" not in news_load_articles:
        failures.append("News Agency V2 loads demo articles without explicit fixture gating.")
    if "Live story feed API is required" not in news_agency_screen:
        failures.append("News Agency V2 does not fail closed when the live story feed API is missing.")

    trust_ops_api = _read("frontend/lib/features/trust_ops_redesign/data/gtex_trust_ops_api_repository.dart")
    trust_ops_standard = _slice_between(
        trust_ops_api,
        "factory GtexTrustOpsApiRepository.standard",
        "factory GtexTrustOpsApiRepository.fixture",
    )
    if "GtexTrustOpsDemoRepository" in trust_ops_standard:
        failures.append("Trust Ops standard repository still registers demo repository data.")

    match_screen = _read("frontend/lib/features/match_redesign/presentation/gtex_match_center_screen_v2.dart")
    match_controller = _read("frontend/lib/features/match_redesign/presentation/gtex_match_center_controller.dart")
    match_api_repository = _read("frontend/lib/features/match_redesign/data/gtex_match_api_repository.dart")
    for label, source in (
        ("Match V2 screen", match_screen),
        ("Match V2 controller", match_controller),
        ("Match V2 API repository", match_api_repository),
    ):
        if "gtex_match_demo_repository.dart" in source:
            failures.append(f"{label} imports the demo match repository.")

    app_config = _read("frontend/lib/app/gte_app_config.dart")
    if "GTE_BACKEND_MODE=liveThenFixture is forbidden" not in app_config:
        failures.append("Frontend config does not hard-fail liveThenFixture.")
    if "GTE_BACKEND_MODE=fixture is not allowed" not in app_config:
        failures.append("Frontend config does not hard-fail fixture mode outside tests.")
    if "GTE_API_BASE_URL must be set when GTE_BACKEND_MODE is strict_live" not in app_config:
        failures.append("Frontend config does not require a live API base URL for strict_live.")
    if "gteFlutterTestApiBaseUrl" not in app_config or "isFlutterTestRuntime" not in app_config:
        failures.append("Frontend config does not isolate test-only runtime base URL fallback.")

    runtime = "\n".join(
        (
            _read("frontend/lib/core/runtime/gtex_runtime.dart"),
            _read("frontend/lib/core/runtime/gtex_runtime_graph.dart"),
            _read("frontend/lib/core/runtime/gtex_runtime_models.dart"),
            _read("frontend/lib/core/runtime/gtex_realtime_client.dart"),
        )
    )
    if "validateGtexStrictLiveStartup(config);" not in runtime:
        failures.append("Runtime provider does not validate strict-live startup.")
    if "validateGtexRuntimeAdapterGraph(runtime);" not in runtime:
        failures.append("Runtime provider does not validate strict-live repository/controller registrations.")
    for graph_check in (
        "synthetic_match_repository_registered",
        "synthetic_club_repository_registered",
        "synthetic_exchange_repository_registered",
        "synthetic_national_repository_registered",
        "paystack_enabled_in_strict_live",
    ):
        if graph_check not in runtime:
            failures.append(f"Runtime adapter graph gate missing {graph_check}.")
    if "baseUrl.contains('fixture.invalid')" not in runtime:
        failures.append("Frontend strict-live startup gate does not reject fixture API base URLs.")
    if "baseUrl.contains('mock.')" not in runtime or "baseUrl.contains('demo.')" not in runtime:
        failures.append("Frontend strict-live startup gate does not reject mock/demo API base URLs.")
    if "Synthetic realtime payload rejected" not in runtime and "Synthetic websocket payload rejected" not in runtime:
        failures.append("Runtime websocket client does not reject synthetic payloads.")
    if "Stale realtime payload rejected" not in runtime and "Stale websocket payload rejected" not in runtime:
        failures.append("Runtime websocket client does not reject stale payloads.")
    if "GTE_ENABLE_DEMO_CAPABILITIES" not in runtime:
        failures.append("Frontend strict-live startup gate does not check demo capability flags.")
    if "event['runtime_source']" not in runtime or "data['runtime_source']" not in runtime:
        failures.append("Runtime websocket client does not trace payload source/runtime_source.")
    for fixture_like_source in ("'demo'", "'fixture'", "'synthetic'", "contains('mock')"):
        if fixture_like_source not in runtime:
            failures.append(f"Runtime websocket synthetic-source rejection is missing {fixture_like_source}.")
    if "scheme: scheme" not in runtime or "path: '/realtime/stream'" not in runtime:
        failures.append("Runtime websocket client does not derive live ws/wss endpoints from the API base URL.")
    for provenance in (
        "'session': '/api/session/bootstrap'",
        "'match_v2': '/api/matches/{match_id}/state'",
        "'national_v2': '/api/national-team-engine/competitions'",
        "'admin_v2': '/api/admin/operations-readiness'",
    ):
        if provenance not in runtime:
            failures.append(f"Runtime live endpoint provenance missing {provenance}.")
    for websocket_trace in ("'matches': '/ws/matches/{match_id}'", "'notifications': '/realtime/stream'"):
        if websocket_trace not in runtime:
            failures.append(f"Runtime websocket source trace missing {websocket_trace}.")
    if "sourceOfTruthTag: 'persisted_backend_authority'" not in runtime:
        failures.append("Runtime observability does not tag the persisted backend as source of truth.")
    if "stalePayloadThreshold: const Duration(seconds: 45)" not in runtime:
        failures.append("Runtime observability does not expose the 45s stale websocket threshold.")
    if "paystack: false" not in runtime:
        failures.append("Runtime capabilities do not explicitly disable Paystack.")
    if "korapay: !fixtureMode" not in runtime:
        failures.append("Runtime capabilities do not gate KoraPay to live mode.")

    competition_api = _read("frontend/lib/data/competition_api.dart")
    competition_standard = _slice_between(
        competition_api,
        "factory CompetitionApi.standard",
        "factory CompetitionApi.fixture",
    )
    if "_CompetitionFixtureStore.seed" in competition_standard:
        failures.append("CompetitionApi.standard still seeds fixture competition data.")
    if "bool get hasRegisteredFixtures" not in competition_api:
        failures.append("CompetitionApi does not expose fixture registration status to the runtime gate.")

    competition_v2_screen = _read(
        "frontend/lib/features/competition_redesign/presentation/gtex_competitions_hub_screen_v2.dart"
    )
    competition_hub_constructor = _slice_between(
        competition_v2_screen,
        "const GtexCompetitionsHubScreenV2({",
        "class _GtexCompetitionsHubScreenV2State",
    )
    competition_create_constructor = _slice_between(
        competition_v2_screen,
        "const GtexCompetitionCreateScreenV2({",
        "class _GtexCompetitionCreateScreenV2State",
    )
    if "this.repository = const DemoGtexCompetitionRepository()" in competition_hub_constructor:
        failures.append("Competition V2 hub constructor still defaults to demo repository data.")
    if "this.repository = const DemoGtexCompetitionRepository()" in competition_create_constructor:
        failures.append("Competition V2 create constructor still defaults to demo repository data.")
    if "Live competitions unavailable" not in competition_v2_screen:
        failures.append(
            "Competition V2 hub does not render a strict-live blocked state when no repository is injected."
        )

    create_son_screen = _read("frontend/lib/features/regen_redesign/presentation/gtex_create_son_screen_v2.dart")
    admin_create_son_screen = _read(
        "frontend/lib/features/regen_redesign/presentation/gtex_admin_create_son_screen_v2.dart"
    )
    create_son_constructor = _slice_between(
        create_son_screen,
        "const GtexCreateSonScreenV2({",
        "class _GtexCreateSonScreenV2State",
    )
    admin_create_son_constructor = _slice_between(
        admin_create_son_screen,
        "const GtexAdminCreateSonScreenV2({",
        "class _GtexAdminCreateSonScreenV2State",
    )
    if "this.repository = const DemoGtexRegenRepository()" in create_son_constructor:
        failures.append("Create-a-Son V2 constructor still defaults to demo regen repository data.")
    if "this.repository = const DemoGtexRegenRepository()" in admin_create_son_constructor:
        failures.append("Admin Create-a-Son V2 constructor still defaults to demo regen repository data.")
    if "Live Create-a-Son repository is required" not in create_son_screen:
        failures.append("Create-a-Son V2 does not fail closed when the live repository is missing.")
    if "Admin Create-a-Son queue unavailable" not in admin_create_son_screen:
        failures.append("Admin Create-a-Son V2 does not block synthetic order queues by default.")

    hosted_competition_api = _read("frontend/lib/data/hosted_competition_api.dart")
    hosted_standard = _slice_between(
        hosted_competition_api,
        "factory HostedCompetitionApi.standard",
        "factory HostedCompetitionApi.fixture",
    )
    if "_HostedCompetitionFixtures.seed" in hosted_standard:
        failures.append("HostedCompetitionApi.standard still seeds fixture hosted competition data.")

    for path, factory_name, fixture_seed, label in (
        (
            "frontend/lib/data/admin_engine_api.dart",
            "AdminEngineApi",
            "AdminEngineFixtures.seed",
            "admin engine",
        ),
        (
            "frontend/lib/data/admin_finance_api.dart",
            "AdminFinanceApi",
            "AdminFinanceFixtures.seed",
            "admin finance",
        ),
        (
            "frontend/lib/data/community_api.dart",
            "CommunityApi",
            "_CommunityFixtures.seed",
            "community",
        ),
        (
            "frontend/lib/data/regen_universe_api.dart",
            "RegenUniverseApi",
            "_RegenUniverseFixtures.seed",
            "regen universe",
        ),
        (
            "frontend/lib/data/trader_api.dart",
            "TraderApi",
            "_TraderFixtures.seed",
            "legacy trader",
        ),
        (
            "frontend/lib/data/story_feed_api.dart",
            "StoryFeedApi",
            "_StoryFeedFixtures.seed",
            "story feed",
        ),
        (
            "frontend/lib/data/notification_settings_api.dart",
            "NotificationSettingsApi",
            "_NotificationFixtures.seed",
            "notification settings",
        ),
        (
            "frontend/lib/features/launch_control_redesign/launch_control_api.dart",
            "GtexLaunchControlApi",
            "GtexLaunchControlFixtures.seed",
            "launch control",
        ),
        (
            "frontend/lib/features/club_lifecycle_redesign/club_lifecycle_api.dart",
            "GtexClubLifecycleApi",
            "GtexClubLifecycleFixtures.seed",
            "club lifecycle",
        ),
        (
            "frontend/lib/features/club_growth_redesign/club_growth_api.dart",
            "GtexClubGrowthApi",
            "GtexClubGrowthFixtures.seed",
            "club growth",
        ),
        (
            "frontend/lib/features/global_search_redesign/global_search_api.dart",
            "GtexGlobalSearchApi",
            "GtexGlobalSearchFixtures.seed",
            "global search",
        ),
        (
            "frontend/lib/features/matchday_economy_redesign/matchday_economy_api.dart",
            "GtexMatchdayEconomyApi",
            "GtexMatchdayEconomyFixtures.seed",
            "matchday economy",
        ),
        (
            "frontend/lib/data/sponsorship_admin_api.dart",
            "SponsorshipAdminApi",
            "_SponsorshipFixtures.seed",
            "sponsorship admin",
        ),
        (
            "frontend/lib/data/risk_ops_api.dart",
            "RiskOpsApi",
            "_RiskOpsFixtures.seed",
            "risk ops",
        ),
        (
            "frontend/lib/data/policy_admin_api.dart",
            "PolicyAdminApi",
            "_PolicyAdminFixtures.seed",
            "policy admin",
        ),
        (
            "frontend/lib/data/moderation_api.dart",
            "ModerationApi",
            "_ModerationFixtures.seed",
            "moderation",
        ),
        (
            "frontend/lib/data/governance_api.dart",
            "GovernanceApi",
            "_GovernanceFixtures.seed",
            "governance",
        ),
        (
            "frontend/lib/data/dispute_engine_api.dart",
            "DisputeEngineApi",
            "_DisputeEngineFixtures.seed",
            "dispute engine",
        ),
        (
            "frontend/lib/data/discovery_api.dart",
            "DiscoveryApi",
            "_DiscoveryFixtures.seed",
            "discovery",
        ),
        (
            "frontend/lib/data/creator_api.dart",
            "CreatorApi",
            "_CreatorFixtures.seed",
            "creator",
        ),
    ):
        source = _read(path)
        standard = _slice_between(
            source,
            f"factory {factory_name}.standard",
            f"factory {factory_name}.fixture",
        )
        if fixture_seed in standard:
            failures.append(f"{factory_name}.standard still seeds fixture {label} data.")

    creator_api = _read("frontend/lib/data/creator_api.dart")
    creator_leaderboard = _slice_between(
        creator_api,
        "Future<CreatorLeaderboardSnapshot> fetchCreatorLeaderboard",
        "Future<CreatorCopilotAnalysis> analyzeCopilotDraft",
    )
    if "fixtures.leaderboard()" in creator_leaderboard:
        failures.append("Creator leaderboard still reads seeded fixture data outside explicit fixture mode.")

    creator_application_api = _read("frontend/lib/data/creator_application_api.dart")
    creator_application_constructor = _slice_between(
        creator_application_api,
        "CreatorApplicationApi({",
        "factory CreatorApplicationApi.standard",
    )
    creator_application_standard = _slice_between(
        creator_application_api,
        "factory CreatorApplicationApi.standard",
        "factory CreatorApplicationApi.fixture",
    )
    if "fixtureState ?? _CreatorApplicationFixtureState()" in creator_application_constructor:
        failures.append("CreatorApplicationApi constructor still registers fixture state by default.")
    if "_CreatorApplicationFixtureState()" in creator_application_standard:
        failures.append("CreatorApplicationApi.standard still registers fixture state.")

    launch_control_api = _read("frontend/lib/features/launch_control_redesign/launch_control_api.dart")
    if "/demo" in launch_control_api:
        failures.append("Launch Control fixtures still expose demo route targets.")

    football_pulse_provider = _read("frontend/lib/features/world/football_world_pulse_provider.dart")
    football_pulse_widgets = _read("frontend/lib/features/world/widgets/football_world_pulse_widgets.dart")
    if "onError:" in football_pulse_provider or "catch (_)" in football_pulse_provider:
        failures.append("Football world pulse provider still swallows live provider errors.")
    if "FootballWorldPulseData.empty.transferTicker" in football_pulse_provider + football_pulse_widgets:
        failures.append("Football world pulse still renders synthetic transfer ticker fallback rows.")
    if "Discovery route" in football_pulse_widgets:
        failures.append("Football world pulse route overlay still renders synthetic discovery routes.")

    club_api = _read("frontend/lib/data/club_api.dart")
    club_standard = _slice_between(
        club_api,
        "factory ClubApi.standard",
        "factory ClubApi.fixture",
    )
    if "bool get hasRegisteredFixtures" not in club_api:
        failures.append("ClubApi does not expose fixture registration status to the runtime gate.")
    for fixture_constructor, label in (
        ("_ClubFixtureStore.seeded()", "club dashboard fixtures"),
        ("MockClubIdentityRepository()", "club identity fixtures"),
        ("StubTrophyCabinetRepository()", "club trophy fixtures"),
    ):
        if fixture_constructor in club_standard and "resolvedMode == GteBackendMode.fixture" not in club_standard:
            failures.append(f"ClubApi.standard registers {label} outside explicit fixture mode.")

    club_identity_api = _read("frontend/lib/features/club_identity/jerseys/data/club_identity_repository.dart")
    club_identity_constructor = _slice_between(
        club_identity_api,
        "ClubIdentityApiRepository({",
        "factory ClubIdentityApiRepository.standard",
    )
    if "MockClubIdentityRepository" in club_identity_constructor:
        failures.append("ClubIdentityApiRepository constructor still defaults to mock identity fixtures.")

    trophy_api = _read("frontend/lib/features/club_identity/trophies/data/trophy_cabinet_api_repository.dart")
    trophy_repository = _read("frontend/lib/features/club_identity/trophies/data/trophy_cabinet_repository.dart")
    if "fixtures = fixtures ?? StubTrophyCabinetRepository()" in trophy_api:
        failures.append("TrophyCabinetApiRepository constructor still defaults to stub trophy data.")
    if "UnavailableTrophyCabinetRepository" not in trophy_repository:
        failures.append("Trophy cabinet repositories do not have a fail-closed unavailable adapter.")
    for path, label in (
        (
            "frontend/lib/features/club_identity/trophies/presentation/trophy_cabinet_screen.dart",
            "Trophy cabinet screen",
        ),
        (
            "frontend/lib/features/club_identity/trophies/presentation/honors_timeline_screen.dart",
            "Honors timeline screen",
        ),
        (
            "frontend/lib/features/club_identity/trophies/presentation/trophy_leaderboard_screen.dart",
            "Trophy leaderboard screen",
        ),
    ):
        source = _read(path)
        if "widget.repository ?? StubTrophyCabinetRepository()" in source:
            failures.append(f"{label} still defaults to stub trophy data.")

    club_sale_api = _read("frontend/lib/features/club_sale_market/data/club_sale_market_repository.dart")
    club_sale_constructor = _slice_between(
        club_sale_api,
        "ClubSaleMarketApiRepository({",
        "factory ClubSaleMarketApiRepository.standard",
    )
    club_sale_standard = _slice_between(
        club_sale_api,
        "factory ClubSaleMarketApiRepository.standard",
        "final GteAuthedApi _client;",
    )
    if "ClubSaleMarketFixtureRepository" in club_sale_constructor:
        failures.append("ClubSaleMarketApiRepository constructor still defaults to fixture sale-market data.")
    if (
        "ClubSaleMarketFixtureRepository()" in club_sale_standard
        and "resolvedMode == GteBackendMode.fixture" not in club_sale_standard
    ):
        failures.append("ClubSaleMarketApiRepository.standard registers fixture data outside explicit fixture mode.")

    match_viewer_mapper = _read("frontend/lib/services/match_viewer_mapper.dart")
    pre_fallback_branch = _slice_between(
        match_viewer_mapper,
        "final GteExchangeApiClient resolvedApi",
        "if (allowFixtureFallback)",
    )
    if "LiveMatchFixtures.buildSnapshot" in pre_fallback_branch:
        failures.append("Match viewer mapper builds fixture snapshots before the explicit fallback branch.")
    if "preferFallback || effectiveMode == GteBackendMode.fixture" in match_viewer_mapper:
        failures.append("Match viewer mapper still allows preferFallback outside a runtime gate.")
    if (
        "(preferFallback && isFlutterTestRuntime)" not in match_viewer_mapper
        or "Match viewer fixture fallback is available only in Flutter tests or explicit fixture mode."
        not in match_viewer_mapper
    ):
        failures.append("Match viewer mapper does not fail closed for production preferFallback requests.")

    match_timeline_service = _read("backend/app/services/match_timeline_service.py")
    if "allow_synthetic_visuals: bool = False" not in match_timeline_service:
        failures.append("Match timeline live-stream builder does not default synthetic visuals off.")
    if "Live stream viewer state requires persisted visual identity data." not in match_timeline_service:
        failures.append("Match timeline live-stream builder does not fail closed without persisted visual identity.")

    match_viewer_route = _read("backend/app/routes/match_viewer.py")
    if (
        "_protected_runtime_enabled(request.app)" not in match_viewer_route
        or "allow_synthetic_visuals=allow_synthetic_visuals" not in match_viewer_route
    ):
        failures.append("Match viewer route does not block synthetic live-stream visuals in protected runtimes.")

    backend_main = _read("backend/app/main.py")
    for flag in (
        "GTE_ENABLE_API_V1_DEMO_FIXTURES",
        "GTE_DEMO_SIMULATION_ENABLED",
        "GTE_DEMO_SIMULATION_BOOTSTRAP",
        "GTE_DEMO_SIMULATION_SEED_ON_BOOT",
        "GTE_ENABLE_LEGACY_MATCH_SIMULATION",
        "GTE_ENABLE_INFINITE_LEAGUE_LIVE_BRIDGE",
        "GTE_ENABLE_INFINITE_LEAGUE_DEMO_RUNTIME",
        "GTE_ENABLE_BROADCAST_GENERATED_PROGRAMS",
        "GTE_ENABLE_REGEN_FALLBACK_PROSPECTS",
        "GTE_ENABLE_SYNTHETIC_YOUTH_TOURNAMENT_SQUADS",
        "GTE_ENABLE_FULL_EXPERIENCE_SIMULATION",
        "GTE_ENABLE_WORLD_SUPER_CUP_DEMO",
        "GTE_ENABLE_MOCK_INGESTION_PROVIDER",
        "GTE_ENABLE_MOCK_KORAPAY",
        "GTE_ENABLE_PAYSTACK",
    ):
        if flag not in backend_main:
            failures.append(f"Backend strict-live startup gate does not check {flag}.")

    simulation_app_factory = _read("backend/app/simulation/app_factory.py")
    if "Demo simulation app cannot boot in production or staging runtime." not in simulation_app_factory:
        failures.append("Demo simulation app factory does not fail closed in protected runtimes.")

    provider_registry = _read("backend/app/wallets/providers/registry.py")
    if (
        '"paystack": ProviderRegistration(adapter=PaystackProviderAdapter(), is_live=False, status="blocked")'
        not in provider_registry
    ):
        failures.append("Payment provider registry does not mark Paystack as blocked.")
    paystack_enabled_body = _slice_between(
        provider_registry,
        "def paystack_enabled()",
        "def provider_runtime_status(",
    )
    if "return False" not in paystack_enabled_body:
        failures.append("Paystack availability is not hard-blocked.")
    wallet_constants = _read("backend/app/wallets/constants.py")
    if 'SUPPORTED_TOP_UP_PROVIDER_KEYS: tuple[str, ...] = ("korapay",)' not in wallet_constants:
        failures.append("Wallet top-up provider constants still expose Paystack as a selectable top-up provider.")
    admin_godmode_service = _read("backend/app/admin_godmode/service.py")
    if (
        'SUPPORTED_ADMIN_PAYMENT_RAILS: tuple[str, ...] = ("bank_transfer_manual", *SUPPORTED_TOP_UP_PROVIDER_KEYS)'
        not in admin_godmode_service
    ):
        failures.append("Admin payment rails are not derived from the strict live top-up provider list.")
    if (
        '"korapay": ProviderRegistration(adapter=KoraPayProviderAdapter(), is_live=True, status="live")'
        not in provider_registry
    ):
        failures.append("Payment provider registry does not mark KoraPay as the live provider.")
    for key in ("GTE_KORAPAY_SECRET_KEY", "GTE_KORAPAY_WEBHOOK_SECRET", "GTE_KORAPAY_ENCRYPTION_KEY"):
        if key not in provider_registry:
            failures.append(f"KoraPay provider readiness does not reference {key}.")

    regen_creation_service = _read("backend/app/regen_creation/service.py")
    if "_mock_korapay_enabled" in regen_creation_service or "mock.korapay" in regen_creation_service:
        failures.append("Regen creation service still exposes mock KoraPay checkout behavior.")
    if 'provider_live_deposit_ready("korapay")' not in regen_creation_service:
        failures.append("Regen creation service does not require live KoraPay readiness.")
    if '* Decimal("100")' in regen_creation_service:
        failures.append("Regen creation service still sends KoraPay amounts in minor units.")

    live_matches_router = _read("backend/app/live_matches/router.py")
    if "GTE_ENABLE_INFINITE_LEAGUE_LIVE_BRIDGE" not in live_matches_router:
        failures.append("Generated Infinite League live bridge is not protected by an explicit enable flag.")
    generated_bridge_body = _slice_between(
        live_matches_router,
        "def _generated_live_bridge_enabled",
        "def _bootstrap_infinite_league_stream",
    )
    if (
        "if _protected_runtime_enabled(app):" not in generated_bridge_body
        or "return False" not in generated_bridge_body
    ):
        failures.append("Generated Infinite League live bridge is not hard-blocked in protected runtimes.")
    if "return raw_flag in" not in generated_bridge_body:
        failures.append("Generated Infinite League live bridge is not explicitly opt-in outside protected runtimes.")

    infinite_league_router = _read("backend/app/infinite_league/router.py")
    if "Infinite League generated runtime is disabled in protected environments." not in infinite_league_router:
        failures.append("Infinite League router does not block generated runtime reads in protected runtimes.")

    broadcast_network_service = _read("backend/app/broadcast_network/service.py")
    if "generated_broadcast_programs_disabled" not in broadcast_network_service:
        failures.append("Broadcast Network does not mark generated programs blocked in strict-live runtimes.")
    ai_candidate_body = _slice_between(broadcast_network_service, "def _ai_candidates", "def _build_channel")
    if "if _protected_runtime_enabled(self.app):" not in ai_candidate_body or "return []" not in ai_candidate_body:
        failures.append("Broadcast Network still allows generated AI candidates in protected runtimes.")
    if "elif not _protected_runtime_enabled(self.app):" not in broadcast_network_service:
        failures.append("Broadcast Network fallback replay slots are not gated out of protected runtimes.")

    api_v1_service = _read("backend/app/api_v1/service.py")
    if '"club": club_payload' not in api_v1_service or "club_payload = None" not in api_v1_service:
        failures.append("API v1 runtime dashboard still fabricates a club payload without live club context.")
    if "persisted team context is missing" not in api_v1_service:
        failures.append("API v1 runtime match state still falls back when persisted team context is missing.")

    regen_universe_service = _read("backend/app/regen_universe/service.py")
    if "not prospects and not _protected_runtime_enabled()" not in regen_universe_service:
        failures.append("Regen Universe still generates fallback prospects in protected runtimes.")

    regen_expansion_service = _read("backend/app/regen_universe/expansion_service.py")
    if "youth_tournament_requires_persisted_squads" not in regen_expansion_service:
        failures.append("Regen expansion tournaments still allow synthetic squad fill-ins in protected runtimes.")

    fan_experience_service = _read("backend/app/gtex_universe/fan_experience.py")
    if "full_experience_simulation_disabled_in_protected_runtime" not in fan_experience_service:
        failures.append("Fan experience full simulation is not blocked in protected runtimes.")
    if "sold = real_sold" not in fan_experience_service or "vip_sold = real_vip_sold" not in fan_experience_service:
        failures.append("Fan experience match offers still inflate ticket sales with synthetic demand.")

    pricing_service = _read("backend/app/pricing/service.py")
    if "market.pricing.synthetic" in pricing_service:
        failures.append("Pricing candles still emit synthetic history points.")

    world_super_cup_router = _read("backend/app/world_super_cup/api/router.py")
    if "GTE_ENABLE_WORLD_SUPER_CUP_DEMO" not in world_super_cup_router:
        failures.append("World Super Cup demo routes are not blocked behind explicit demo enablement.")
    world_super_cup_persistence = REPO_ROOT / "backend" / "app" / "world_super_cup" / "services" / "persistence.py"
    if not world_super_cup_persistence.exists():
        failures.append("World Super Cup persisted authority service is missing.")
    else:
        persistence_source = world_super_cup_persistence.read_text(encoding="utf-8", errors="ignore")
        for required_text in (
            "WorldSuperCupTournament",
            "WorldSuperCupFixture",
            "WorldSuperCupStanding",
            "settle_fixture",
            "idempotency_key",
        ):
            if required_text not in persistence_source:
                failures.append(f"World Super Cup persisted authority missing {required_text}.")
    world_super_cup_authority_model = REPO_ROOT / "backend" / "app" / "models" / "world_super_cup_authority.py"
    if not world_super_cup_authority_model.exists():
        failures.append("World Super Cup persisted authority models are missing.")
    world_super_cup_migrations = list(
        (REPO_ROOT / "backend" / "migrations" / "versions").glob("*world_super_cup_persistence.py")
    )
    if not world_super_cup_migrations:
        failures.append("World Super Cup persisted authority migration is missing.")

    team_factory = _read("backend/app/match_engine/services/team_factory.py")
    if "allow_synthetic_fallback: bool = False" not in team_factory:
        failures.append("SyntheticSquadFactory still defaults to synthetic squad fallback.")

    for path in (
        "backend/app/match_engine/services/execution_runtime.py",
        "backend/app/backbone/simulation_worker_main.py",
        "backend/app/services/competition_auto_runner.py",
        "backend/app/workers/simulation_worker.py",
    ):
        source = _read(path)
        if "SyntheticSquadFactory" in source and "allow_synthetic_fallback=False" not in source:
            failures.append(f"{path} registers match execution without strict persisted-squad enforcement.")

    return failures


def _render_config_failures() -> list[str]:
    render = _read("render.yaml")
    failures: list[str] = []
    for key in (*KORAPAY_SECRET_ENV_KEYS, *TREASURY_SECRET_ENV_KEYS):
        block = _render_key_block(render, key)
        if not block:
            failures.append(f"render.yaml is missing secret env declaration for {key}.")
            continue
        if "sync: false" not in block:
            failures.append(f"render.yaml must keep {key} env-only with sync: false.")
        if "value:" in block:
            failures.append(f"render.yaml must not hard-code a value for secret env {key}.")
    notification_block = _render_key_block(render, "GTE_KORAPAY_NOTIFICATION_URL")
    if not notification_block or "https://gtex-api.onrender.com/api/webhooks/korapay" not in notification_block:
        failures.append("render.yaml is missing the production KoraPay notification URL.")
    paystack_block = _render_key_block(render, "GTE_ENABLE_PAYSTACK")
    if not paystack_block or ('value: "false"' not in paystack_block and "value: false" not in paystack_block):
        failures.append("render.yaml does not explicitly disable Paystack.")
    api_base_block = _render_key_block(render, "GTE_API_BASE_URL")
    if not api_base_block or "https://gtex-api.onrender.com" not in api_base_block:
        failures.append("render.yaml gtex-web service does not point at the live API base URL.")
    backend_mode_block = _render_key_block(render, "GTE_BACKEND_MODE")
    if not backend_mode_block or (
        "value: live" not in backend_mode_block and "value: strict_live" not in backend_mode_block
    ):
        failures.append("render.yaml gtex-web service does not force live backend mode.")
    return failures


def _frontend_dependency_failures() -> list[str]:
    failures: list[str] = []
    analysis_options = _read("frontend/analysis_options.yaml")
    if "lib/data/generated/**" not in analysis_options:
        failures.append("analysis_options.yaml does not isolate generated frontend files.")

    analyzer_gate = _read("frontend/tool/check_analyzer_hard_errors.py")
    if "ANALYZER_TIMEOUT_SECONDS" not in analyzer_gate or "timeout=" not in analyzer_gate:
        failures.append("frontend analyzer gate does not enforce a timeout.")

    cycles = _dart_import_cycles()
    if cycles:
        failures.append(
            "frontend Dart import cycle detected: "
            + " -> ".join(path.relative_to(FRONTEND_LIB_ROOT).as_posix() for path in cycles[0])
        )
    return failures


def _dart_import_cycles() -> list[list[Path]]:
    if not FRONTEND_LIB_ROOT.exists():
        return []
    files = [path for path in FRONTEND_LIB_ROOT.rglob("*.dart") if "/generated/" not in path.as_posix()]
    by_relative = {path.relative_to(FRONTEND_LIB_ROOT).as_posix(): path for path in files}
    graph: dict[Path, set[Path]] = {path: set() for path in files}
    for path in files:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = DART_IMPORT_PATTERN.match(line)
            if not match:
                continue
            target = _resolve_dart_import(path, match.group(1), by_relative)
            if target in graph:
                graph[path].add(target)

    cycles: list[list[Path]] = []
    seen: set[Path] = set()
    in_stack: dict[Path, int] = {}
    stack: list[Path] = []

    def visit(path: Path) -> None:
        seen.add(path)
        in_stack[path] = len(stack)
        stack.append(path)
        for target in graph[path]:
            if target not in seen:
                visit(target)
                if cycles:
                    return
            elif target in in_stack:
                cycles.append([*stack[in_stack[target] :], target])
                return
        stack.pop()
        in_stack.pop(path, None)

    for path in files:
        if path not in seen:
            visit(path)
            if cycles:
                break
    return cycles


def _resolve_dart_import(
    source: Path,
    import_uri: str,
    by_relative: dict[str, Path],
) -> Path | None:
    if import_uri.startswith("package:gte_frontend/"):
        return by_relative.get(import_uri.removeprefix("package:gte_frontend/"))
    if import_uri.startswith("."):
        candidate = (source.parent / import_uri).resolve()
        if candidate.exists():
            return candidate
    return None


def _slice_between(text: str, start: str, end: str | None = None) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    if end is None:
        return text[start_index:]
    end_index = text.find(end, start_index + len(start))
    if end_index < 0:
        return text[start_index:]
    return text[start_index:end_index]


def _render_key_block(render: str, key: str) -> str:
    marker = f"- key: {key}"
    start = render.find(marker)
    if start < 0:
        return ""
    next_key = render.find("\n      - key:", start + len(marker))
    next_service = render.find("\n  - name:", start + len(marker))
    candidates = [index for index in (next_key, next_service) if index > start]
    end = min(candidates) if candidates else len(render)
    return render[start:end]


if __name__ == "__main__":
    raise SystemExit(main())
