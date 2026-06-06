from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SCAN_ROOTS = (
    ".github",
    "ops/render",
    "scripts",
    "tools",
    "frontend/lib",
    "frontend/test",
)

CANONICAL_PRODUCTION_ROOTS = (
    ".github/workflows/ci-staging.yml",
    ".github/workflows/deploy-production.yml",
    "ops/render",
    "scripts/run_gtex_guardrails.ps1",
    "shared/api_contract.json",
    "frontend/lib/data/generated/gte_api_contract.g.dart",
    "frontend/lib/navigation",
    "frontend/lib/router",
    "frontend/lib/features/app_routes",
    "frontend/lib/features/match_center",
    "backend/app/admin_finance",
    "backend/app/api_v1",
    "backend/app/live_matches",
    "backend/app/match_engine",
    "backend/app/modules.py",
    "backend/app/routes",
    "backend/app/services/payment_gateway_service.py",
    "backend/app/treasury",
    "backend/app/wallets",
    "tools/guardrails",
    "tools/quality/run_gtex_canonical_acceptance.py",
)

CHANGED_SOURCE_PREFIXES = (
    ".github/",
    "backend/app/admin_finance/",
    "backend/app/api_v1/",
    "backend/app/live_matches/",
    "backend/app/match_engine/",
    "backend/app/routes/",
    "backend/app/services/payment_gateway_service.py",
    "backend/app/treasury/",
    "backend/app/wallets/",
    "frontend/lib/data/generated/gte_api_contract.g.dart",
    "frontend/lib/features/app_routes/",
    "frontend/lib/features/match_center/",
    "frontend/lib/navigation/",
    "frontend/lib/router/",
    "frontend/test/guardrails/",
    "ops/render/",
    "scripts/",
    "shared/",
    "tools/guardrails/",
    "tools/quality/",
)

CHANGED_SOURCE_FILES = {
    "render.yaml",
}

SCAN_PROFILES = {
    "default": DEFAULT_SCAN_ROOTS,
    "canonical-production": CANONICAL_PRODUCTION_ROOTS,
}

SKIP_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "Library",
    "Temp",
    "Build",
    "Builds",
    "obj",
}

SKIP_PATH_FRAGMENTS = (
    "backend/generated_media/",
    "backend/manual_phase1_checks/",
    "backend/pytesttmp_phase1_admin/",
    "docs/FINAL_API_SCHEMA.json",
    "docs/FRONTEND_API_MAP.json",
    "docs/ROUTE_MAP.json",
    "Gtex_Test_Migration/Packages/",
    "Gtex_Test_Migration/UserSettings/",
)

TEXT_SUFFIXES = {
    ".cs",
    ".dart",
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


@dataclass(frozen=True)
class GuardrailRule:
    key: str
    pattern: re.Pattern[str]
    summary: str


@dataclass(frozen=True)
class GuardrailHit:
    path: str
    line: int
    column: int
    rule: str
    match: str
    classification: str
    lane: str
    note: str


RULES = (
    GuardrailRule(
        key="paystack-canonical-exposure",
        pattern=re.compile(r"\bpaystack\b", re.IGNORECASE),
        summary="Paystack must not be exposed as canonical money authority.",
    ),
    GuardrailRule(
        key="noncanonical-payment-rail",
        pattern=re.compile(
            r"\b(?:flutterwave|paypal|monnify|opay|coinbase|"
            r"mobile\s+money|m-?pesa)\b|"
            r"\b(?:payment|provider|checkout|gateway|rail)s?\b[^\n]{0,48}\b"
            r"(?:stripe|crypto(?:currency)?)\b|"
            r"\b(?:stripe|crypto(?:currency)?)\b[^\n]{0,48}\b"
            r"(?:payment|provider|checkout|gateway|rail)s?\b",
            re.IGNORECASE,
        ),
        summary="Payment rails must stay limited to KoraPay and manual bank transfer.",
    ),
    GuardrailRule(
        key="unity-access-route",
        pattern=re.compile(r"(?:unity[_-]access|/unity-access\b)", re.IGNORECASE),
        summary="Unity access routes must not be promoted as production routes.",
    ),
    GuardrailRule(
        key="verify-unity-routes",
        pattern=re.compile(
            r"\b(?:verify[_-]unity[_-]routes(?:\.py)?|"
            r"render[_-]verify[_-]unity[_-]routes|"
            r"render[_-]unity[_-]live[_-]verify)\b",
            re.IGNORECASE,
        ),
        summary="The legacy Unity route verifier must not be reintroduced.",
    ),
    GuardrailRule(
        key="production-3d-route-promotion",
        pattern=re.compile(
            r"(?:/matches/3d\b|/matches/native-3d\b|match_3d_route_truth|"
            r"match_3d_route_hardening|native_match_3d_surface_test)",
            re.IGNORECASE,
        ),
        summary="3D routes/tests must not be used as production route gates.",
    ),
    GuardrailRule(
        key="promoted-3d-cta",
        pattern=re.compile(
            r"\b(?:open|launch|watch|view|start|play|enter)\s+" r"(?:the\s+)?(?:native\s+|flutter\s+)?3d\b",
            re.IGNORECASE,
        ),
        summary="Production CTAs should direct users to the 2D match viewer.",
    ),
    GuardrailRule(
        key="pseudo-3d-label",
        pattern=re.compile(r"\bpseudo[- ]?3d\b", re.IGNORECASE),
        summary="Pseudo-3D wording must stay deprecated/internal.",
    ),
    GuardrailRule(
        key="fake-production-authority-data",
        pattern=re.compile(
            r"\b(?:fake|mock|dummy|sample|hardcoded|synthetic|"
            r"client[- ]generated|client[- ]side|local[- ]only|fallback)\s+"
            r"(?:balances?|scores?|bids?|rankings?|fixtures?)\b|"
            r"\b(?:balances?|scores?|bids?|rankings?|fixtures?)\s+"
            r"(?:fake|mock|dummy|sample|hardcoded|synthetic|"
            r"client[- ]generated|client[- ]side|local[- ]only|fallback)\b",
            re.IGNORECASE,
        ),
        summary=(
            "Production balances, scores, bids, rankings, and fixtures must "
            "come from backend authority, not fake or fallback data."
        ),
    ),
    GuardrailRule(
        key="fixture-mode-production-enabled",
        pattern=re.compile(
            r"\b(?:kFixtureMode|GtexFixtureMode|fixtureMode|"
            r"enableFixtureMode|enableCapitalFixtures)\b\s*[:=]\s*true\b|"
            r"\b(?:mode|backendMode)\s*:\s*GteBackendMode\.fixture\b|"
            r"\ballowFixtureMode\s*\?\s*GteBackendMode\.fixture\b|"
            r"\bbool\.fromEnvironment\([^\n)]*(?:fixtureMode|FixtureMode|"
            r"GtexFixtureMode|kFixtureMode)[^\n)]*defaultValue\s*:\s*true",
            re.IGNORECASE,
        ),
        summary="Fixture mode must be impossible to enable in production builds.",
    ),
)

ARCHITECTURE_RULES = (
    GuardrailRule(
        key="renderer-ref-outside-authorized-zone",
        pattern=re.compile(
            r"(?:\bUnity\b|unity_match_3d|match_3d/unity_activity|"
            r"\bSceneKit\b|\bBabylon\b|\bAndroidView\b|\bUiKitView\b|"
            r"\bPlatformViewHitTestBehavior\b|native\s+renderer|experimental\s+bridge)",
            re.IGNORECASE,
        ),
        summary=(
            "Renderer/native bridge references are only authorized under "
            "frontend/lib/features/3d/** or frontend/lib/native/**."
        ),
    ),
    GuardrailRule(
        key="legacy-capital-import",
        pattern=re.compile(
            r"package:gte_frontend/(?:"
            r"screens/(?:wallet|trader)(?:/|\.dart|')|"
            r"screens/support/gte_support_dispute_screens\.dart|"
            r"data/(?:trader_api|dispute_engine_api|admin_finance_api)\.dart|"
            r"widgets/gte_wallet_summary_card\.dart|"
            r"features/(?:creator_share_market|club_sale_market|"
            r"creator_league_admin|creator_stadium_monetization)(?:/|\.dart|')"
            r")",
            re.IGNORECASE,
        ),
        summary="Financial domain imports must resolve through frontend/lib/features/capital/**.",
    ),
    GuardrailRule(
        key="legacy-competition-import",
        pattern=re.compile(
            r"package:gte_frontend/(?:"
            r"screens/competitions(?:/|\.dart|')|"
            r"widgets/competitions(?:/|\.dart|')|"
            r"controllers/competition_controller\.dart|"
            r"features/competitions(?:/|\.dart|')"
            r")",
            re.IGNORECASE,
        ),
        summary="Competition domain imports must resolve through frontend/lib/features/compete/**.",
    ),
    GuardrailRule(
        key="live-match-outside-match-center-import",
        pattern=re.compile(
            r"package:gte_frontend/(?:"
            r"screens/match(?:/|\.dart|')|"
            r"widgets/match(?:/|\.dart|')|"
            r"services/match_|"
            r"features/match(?:/|\.dart|')"
            r")",
            re.IGNORECASE,
        ),
        summary="Live match domain imports should resolve through frontend/lib/features/match_center/**.",
    ),
    GuardrailRule(
        key="wallet-summary-read-outside-capital",
        pattern=re.compile(
            r"(?:fetchWalletSummary\s*\(|/api/wallets/summary|/wallets/summary)",
            re.IGNORECASE,
        ),
        summary=("Consumer wallet availability reads must go through " "frontend/lib/features/capital/wallet/**."),
    ),
    GuardrailRule(
        key="ui-wallet-summary-read-outside-capital",
        pattern=re.compile(
            r"\b(?:widget\.)?controller\.walletSummary\b",
            re.IGNORECASE,
        ),
        summary=(
            "Consumer UI must render capital wallet display snapshots instead " "of raw wallet summary transport state."
        ),
    ),
    GuardrailRule(
        key="mock-wallet-fixture-state-outside-capital",
        pattern=re.compile(
            r"\b(?:_walletSummary|_fanWalletSummary|_walletLedger|"
            r"_walletTransactions|_topUpSessions|_ledgerSequence|"
            r"_walletTransactionSequence|_seedWalletSummary|"
            r"_seedFanWalletSummary|_seedWalletLedger)\b",
            re.IGNORECASE,
        ),
        summary=("Mock wallet fixture state must stay in " "frontend/lib/features/capital/wallet/**."),
    ),
    GuardrailRule(
        key="mock-wallet-fixture-mutation-outside-capital",
        pattern=re.compile(
            r"(?:_capitalWallet\.(?:coinSummary|fanSummary)\s*=|"
            r"_capitalWallet\.(?:ledger|transactions)\.insert\s*\(|"
            r"_capitalWallet\.topUpSessions\[|"
            r"_capitalWallet\.(?:ledgerSequence|transactionSequence))",
            re.IGNORECASE,
        ),
        summary=("Mock wallet fixture mutations must be routed through " "capital-owned fixture methods."),
    ),
    GuardrailRule(
        key="extracted-capital-fixture-state-outside-capital",
        pattern=re.compile(
            r"\b(?:_depositRequests|_depositSequence|_seedDeposits|"
            r"_withdrawalRequests|_withdrawalSequence|_seedWithdrawals|"
            r"_treasuryBankAccounts|_treasuryBankSequence|"
            r"_seedTreasurySettings|_seedTreasuryBankAccount|"
            r"_userBankAccounts|_userBankSequence|_seedUserBankAccounts|"
            r"_kycProfile|_seedKycProfile|"
            r"_disputes|_disputeSequence|_seedDisputes|"
            r"_policyDocuments|_policyAcceptances|"
            r"_seedPolicyDocuments|_seedPolicyAcceptances|"
            r"_baseTickers|_baseOrderBooks|_sessionOrderIds|"
            r"_orderSequence|_seedTickers|_seedOrderBooks|_seedOrders|"
            r"_portfolioSummary|_seedPortfolioHoldings|"
            r"_seedPortfolioSummary|_liquidityBandForPrice|"
            r"_payoutBandForPrice|_adminBuybackPayoutRatio)\b",
            re.IGNORECASE,
        ),
        summary=(
            "Extracted capital fixture state must stay in capital-owned "
            "wallet, settlement, payouts, disputes, or trader stores."
        ),
    ),
)

PATH_SCOPED_ARCHITECTURE_RULES = (
    (
        ("frontend/lib/features/capital/",),
        GuardrailRule(
            key="capital-feature-direct-controller-api",
            pattern=re.compile(
                r"\b(?:widget\.)?controller\.api\.",
                re.IGNORECASE,
            ),
            summary=(
                "Capital feature surfaces must call capital-owned facades " "instead of shared exchange API transport."
            ),
        ),
    ),
    (
        ("frontend/lib/data/",),
        GuardrailRule(
            key="capital-fixture-direct-mock-construction",
            pattern=re.compile(
                r"\bGteMockApi\.capitalFixtures\s*\(",
                re.IGNORECASE,
            ),
            summary=(
                "Capital-enabled fixture construction must go through "
                "frontend/lib/features/capital/capital_fixture_repository.dart."
            ),
        ),
    ),
)

ARCHITECTURE_PATH_RULES = (
    (
        "legacy-capital-path",
        (
            "frontend/lib/screens/wallet/",
            "frontend/lib/screens/trader/",
            "frontend/lib/screens/support/gte_support_dispute_screens.dart",
            "frontend/lib/data/trader_api.dart",
            "frontend/lib/data/dispute_engine_api.dart",
            "frontend/lib/data/admin_finance_api.dart",
            "frontend/lib/widgets/gte_wallet_summary_card.dart",
            "frontend/lib/features/club_sale_market/",
            "frontend/lib/features/creator_share_market/",
            "frontend/lib/features/creator_league_admin/",
            "frontend/lib/features/creator_stadium_monetization/",
        ),
        "Financial domain implementation must live under frontend/lib/features/capital/**.",
    ),
    (
        "legacy-competition-path",
        (
            "frontend/lib/screens/competitions/",
            "frontend/lib/widgets/competitions/",
            "frontend/lib/controllers/competition_controller.dart",
            "frontend/lib/features/competitions/",
        ),
        "Competition implementation must live under frontend/lib/features/compete/**.",
    ),
    (
        "live-match-outside-match-center-path",
        (
            "frontend/lib/screens/match/",
            "frontend/lib/widgets/match/",
            "frontend/lib/services/match_",
            "frontend/lib/features/match/",
        ),
        "Live match implementation should live under frontend/lib/features/match_center/**.",
    ),
)

AUTHORIZED_RENDERER_PREFIXES = (
    "frontend/lib/features/3d/",
    "frontend/lib/native/",
)

GUARDRAIL_TEST_PREFIXES = (
    "backend/tests/ops/",
    "frontend/test/guardrails/",
)

GUARDRAIL_TEST_PATTERN_MARKERS = (
    "regexp",
    "re.compile",
    "pattern",
    "forbidden",
    "guardrail",
    "reject",
    "quarantine",
    "assert ",
    "expect(",
    "hasmatch",
    "allmatches",
    "findsnothing",
    "_scan",
    "token",
    "route",
)

RULE_PREFILTER_TOKENS = {
    "paystack-canonical-exposure": ("paystack",),
    "noncanonical-payment-rail": (
        "flutterwave",
        "paypal",
        "monnify",
        "opay",
        "coinbase",
        "mobile",
        "m-pesa",
        "mpesa",
        "pesa",
        "payment",
        "provider",
        "checkout",
        "gateway",
        "rail",
        "stripe",
        "crypto",
    ),
    "unity-access-route": ("unity",),
    "verify-unity-routes": ("unity", "verify", "render"),
    "production-3d-route-promotion": ("3d", "match_3d", "native_match"),
    "promoted-3d-cta": ("3d",),
    "pseudo-3d-label": ("pseudo", "3d"),
    "fake-production-authority-data": (
        "fake",
        "mock",
        "dummy",
        "sample",
        "hardcoded",
        "synthetic",
        "client-generated",
        "client generated",
        "client-side",
        "client side",
        "local-only",
        "local only",
        "fallback",
        "balance",
        "score",
        "bid",
        "ranking",
        "fixture",
    ),
    "fixture-mode-production-enabled": (
        "fixture",
        "kfixturemode",
        "gtexfixturemode",
        "fixturemode",
        "enablefixturemode",
        "enablecapitalfixtures",
        "gtebackendmode.fixture",
        "allowfixturemode",
        "bool.fromenvironment",
    ),
    "renderer-ref-outside-authorized-zone": (
        "unity",
        "match_3d",
        "scenekit",
        "babylon",
        "androidview",
        "uikitview",
        "platformviewhittestbehavior",
        "native renderer",
        "experimental bridge",
    ),
    "legacy-capital-import": ("package:gte_frontend/",),
    "legacy-competition-import": ("package:gte_frontend/",),
    "live-match-outside-match-center-import": ("package:gte_frontend/",),
    "wallet-summary-read-outside-capital": ("walletsummary", "/wallets/summary"),
    "ui-wallet-summary-read-outside-capital": ("walletsummary",),
    "mock-wallet-fixture-state-outside-capital": ("_wallet", "_fanwallet", "_ledger", "_seed", "_topup"),
    "mock-wallet-fixture-mutation-outside-capital": ("_capitalwallet",),
    "extracted-capital-fixture-state-outside-capital": (
        "_deposit",
        "_withdrawal",
        "_treasury",
        "_userbank",
        "_kyc",
        "_dispute",
        "_policy",
        "_base",
        "_session",
        "_order",
        "_portfolio",
        "_seed",
        "_liquidity",
        "_payout",
        "_adminbuyback",
    ),
    "capital-feature-direct-controller-api": ("controller.api.",),
    "capital-fixture-direct-mock-construction": ("gtemockapi.capitalfixtures",),
}


def _is_guardrail_test_pattern_line(line: str) -> bool:
    normalized = line.strip().lower()
    if any(marker in normalized for marker in GUARDRAIL_TEST_PATTERN_MARKERS):
        return True
    return normalized.startswith(("r'", 'r"', "r'''", 'r"""', "('", '("', "f'", 'f"', "'", '"'))


@lru_cache(maxsize=None)
def _to_repo_path(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def _line_may_match(rule: GuardrailRule, lower_line: str) -> bool:
    tokens = RULE_PREFILTER_TOKENS.get(rule.key)
    if tokens is None:
        return True
    return any(token in lower_line for token in tokens)


def _should_skip(path: Path) -> bool:
    repo_path = _to_repo_path(path) if path.is_absolute() else path.as_posix()
    normalized = repo_path.replace("\\", "/")
    if any(fragment in normalized for fragment in SKIP_PATH_FRAGMENTS):
        return True
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def _normalize_repo_path(path: str) -> str:
    return path.strip().replace("\\", "/")


def _is_changed_source_path(path: str) -> bool:
    normalized = _normalize_repo_path(path)
    if normalized in CHANGED_SOURCE_FILES:
        return True
    return any(normalized.startswith(prefix) for prefix in CHANGED_SOURCE_PREFIXES)


def _is_text_file(path: Path) -> bool:
    if path.suffix in TEXT_SUFFIXES:
        return True
    return path.name in {"AGENTS.md", "Dockerfile"}


def _iter_files(roots: Sequence[str]) -> Iterable[Path]:
    seen: set[str] = set()
    for raw_root in roots:
        root = (REPO_ROOT / raw_root).resolve()
        if not root.exists():
            continue
        if root.is_file():
            key = str(root).lower()
            if key not in seen and _is_text_file(root) and not _should_skip(root):
                seen.add(key)
                yield root
            continue
        for path in root.rglob("*"):
            if path.is_dir() or _should_skip(path) or not _is_text_file(path):
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path


def _classify(path: str, line: str, rule: GuardrailRule) -> tuple[str, str, str]:
    lower_path = path.lower()
    lower_line = line.lower()

    if rule.key == "fake-production-authority-data" and _is_disabled_authority_reference(lower_line):
        return (
            "fixed",
            "production authority guard",
            "The line rejects or disables fake/fixture fallback authority.",
        )

    if rule.key == "fixture-mode-production-enabled" and _is_allowed_fixture_mode_reference(
        lower_path,
        lower_line,
    ):
        return (
            "fixed",
            "fixture mode production clamp",
            "Fixture mode is defined only for test/local fixture factories or is clamped away from production runtime.",
        )

    if lower_path.startswith(GUARDRAIL_TEST_PREFIXES):
        if _is_guardrail_test_pattern_line(line):
            return (
                "quarantined",
                "guardrail scan pattern",
                "The test hit names forbidden wording only as a scan/assertion pattern.",
            )
        return (
            "violation",
            "guardrail test literal",
            "Guardrail tests may name forbidden wording only inside scan/assertion patterns.",
        )

    if lower_path.startswith("tools/guardrails/") or lower_path == "scripts/run_gtex_guardrails.ps1":
        return (
            "quarantined",
            "guardrail negative assertion",
            "The hit is part of the scanner or a test that rejects this wording.",
        )

    if lower_path == "ops/render/verify_match_center_routes.py":
        return (
            "fixed",
            "canonical route verifier",
            "The only legacy route fragment here is rejected by the 2D match center verifier.",
        )

    if lower_path.startswith(".github/"):
        if rule.key in {
            "paystack-canonical-exposure",
            "noncanonical-payment-rail",
            "production-3d-route-promotion",
            "fake-production-authority-data",
            "fixture-mode-production-enabled",
        }:
            return (
                "violation",
                "ci production gate",
                "CI must enforce canonical payments, backend-owned data, fixture-mode blocking, and 2D routes.",
            )
        return (
            "quarantined",
            "Unity build safety",
            "Unity wording is allowed only for optional batchmode build safety, not route promotion.",
        )

    if lower_path.startswith("tools/quality/run_gtex_canonical_acceptance.py"):
        return (
            "quarantined",
            "acceptance command harness",
            "The acceptance harness names forbidden tokens only to reject canonical exposure.",
        )

    if lower_path.startswith("gtex_test_migration/") or lower_path.startswith("unity/"):
        return (
            "quarantined",
            "Unity project/runtime",
            "Unity references remain internal build/runtime integration details.",
        )

    if lower_path.startswith("tools/") and (
        "gtex_live" in lower_path
        or "run_gtex" in lower_path
        or "provision_gtex_live_match" in lower_path
        or "capture_gtex_player_session" in lower_path
    ):
        return (
            "quarantined",
            "Unity ops tooling",
            "Legacy live match-center tooling remains internal and is not a product route gate.",
        )

    if lower_path.startswith("docs/guardrails/") or lower_path.startswith("docs/guardrails/"):
        return (
            "quarantined",
            "guardrail documentation",
            "Guardrail docs name forbidden terms only to define the quarantine policy.",
        )

    if lower_path.startswith("docs/") or lower_path.startswith("docs/"):
        if "prototype_mapping/" in lower_path:
            lane = "prototype mapping docs"
        elif "gtex_p6" in lower_path or lower_path in {"gtex_tasks.md", "gtex_phased_prompts.md"}:
            lane = "P6/P6V evidence docs"
        elif "architecture/" in lower_path:
            lane = "architecture docs"
        else:
            lane = "historical/report docs"
        return (
            "quarantined",
            lane,
            "Documentation hit is allowed only as evidence/mapping, not canonical product authority.",
        )

    if lower_path.startswith("backend/app/"):
        if rule.key in {
            "paystack-canonical-exposure",
            "noncanonical-payment-rail",
        }:
            return (
                "violation",
                "canonical payment source",
                "Canonical payment source must stay on KoraPay/manual rails and not expose retired providers.",
            )
        if rule.key in {
            "fake-production-authority-data",
            "fixture-mode-production-enabled",
        }:
            return (
                "violation",
                "backend production authority",
                "Backend production code must not enable fixtures or emit fake authority data.",
            )
        if "live_matches/" in lower_path or "match_engine/" in lower_path:
            return (
                "owned-by-thread",
                "backend match/realtime implementation",
                "Backend runtime implementation is owned by match/realtime lanes.",
            )

    if lower_path.startswith("backend/tests/"):
        return (
            "owned-by-thread",
            "backend guard/test owner",
            "Existing backend tests may mention providers or legacy runtime internals for regression coverage.",
        )

    if lower_path.startswith("frontend/test/"):
        if "wallet/" in lower_path or rule.key == "paystack-canonical-exposure":
            return (
                "owned-by-thread",
                "wallet/payment frontend tests",
                "Provider mentions in frontend tests belong to the wallet/payment owner.",
            )
        return (
            "owned-by-thread",
            "frontend match guard/test owner",
            "Existing frontend tests may mention blocked legacy surfaces while product owners finish quarantine.",
        )

    if lower_path.startswith("frontend/lib/widgets/match_3d/native_match_3d_surface.dart") and (
        "@deprecated" in lower_line
        or "quarantined" in lower_line
        or "legacy" in lower_line
        or "kgtexlegacy3druntimeenabled" in lower_line
    ):
        return (
            "quarantined",
            "match viewer disclosure",
            "The legacy runtime surface is explicitly deprecated/quarantined.",
        )

    if lower_path.startswith("frontend/lib/") and (
        "match_3d" in lower_path or "pseudo3d" in lower_path or "match/" in lower_path
    ):
        return (
            "owned-by-thread",
            "match viewer/native route owner",
            "Frontend match runtime product code is owned by the match viewer/native lanes.",
        )

    return (
        "violation",
        "production surface",
        (
            f"{rule.summary} Keep production data backend-owned, payment rails "
            "limited to KoraPay/manual transfer, and match surfaces on 2D broadcast paths."
        ),
    )


def _is_disabled_authority_reference(lower_line: str) -> bool:
    if not any(token in lower_line for token in ("fake", "mock", "fixture", "fallback")):
        return False
    return any(
        marker in lower_line
        for marker in (
            " disabled",
            " is disabled",
            "disabled.",
            "blocked",
            "reject",
            "never ",
            " no ",
            " not ",
            "without ",
            "removed",
        )
    )


def _is_allowed_fixture_mode_reference(lower_path: str, lower_line: str) -> bool:
    if lower_path == "frontend/lib/app/gte_app_config.dart":
        return "allowfixturemode" in lower_line or "gtebackendmode.fixture" in lower_line
    if lower_path == "frontend/lib/data/gte_mock_api.dart":
        return "enablecapitalfixtures" in lower_line or "gtebackendmode.fixture" in lower_line
    if lower_path.endswith("_test.dart"):
        return True
    return False


def _classify_architecture(path: str, line: str, rule: GuardrailRule) -> tuple[str, str, str]:
    lower_path = path.lower()

    if lower_path.startswith(GUARDRAIL_TEST_PREFIXES):
        if _is_guardrail_test_pattern_line(line):
            return (
                "quarantined",
                "guardrail scan pattern",
                "The test hit names forbidden architecture only as a scan/assertion pattern.",
            )
        return (
            "violation",
            "guardrail test literal",
            "Guardrail tests may name forbidden architecture only inside scan/assertion patterns.",
        )

    if lower_path.startswith("tools/guardrails/"):
        return (
            "quarantined",
            "guardrail negative assertion",
            "The hit is part of the scanner or a test that rejects this architecture.",
        )

    if not (lower_path.startswith("frontend/lib/") or lower_path.startswith("frontend/test/")):
        return (
            "quarantined",
            "non-frontend source",
            "Architecture import ownership is enforced for Flutter source and tests.",
        )

    if rule.key == "renderer-ref-outside-authorized-zone":
        if lower_path.startswith(AUTHORIZED_RENDERER_PREFIXES):
            return (
                "owned-by-thread",
                "authorized renderer zone",
                "Renderer/native integration is quarantined to the approved frontend zone.",
            )
        if lower_path.startswith("frontend/test/"):
            return (
                "owned-by-thread",
                "renderer guard/test owner",
                "Frontend tests may name renderer bridge tokens while asserting quarantine behavior.",
            )
        return (
            "violation",
            "unauthorized renderer reference",
            rule.summary,
        )

    if rule.key == "live-match-outside-match-center-import":
        return (
            "risk",
            "live match ownership migration",
            (
                "Existing live match surfaces are still being migrated by the match lane; "
                "new imports should point at match_center."
            ),
        )

    if rule.key == "wallet-summary-read-outside-capital":
        if lower_path.startswith("frontend/lib/features/capital/"):
            return (
                "owned-by-thread",
                "capital wallet facade",
                "Capital owns direct backend wallet balance reads.",
            )
        if lower_path.startswith("frontend/lib/data/"):
            return (
                "owned-by-thread",
                "shared backend transport",
                "Shared API clients may define low-level wallet transport methods.",
            )
        if lower_path.startswith("frontend/test/"):
            return (
                "owned-by-thread",
                "wallet guard/test owner",
                "Tests may call low-level wallet transport while asserting capital behavior.",
            )
        return (
            "violation",
            "wallet consumer ownership",
            rule.summary,
        )

    if rule.key == "ui-wallet-summary-read-outside-capital":
        if lower_path.startswith("frontend/test/"):
            return (
                "owned-by-thread",
                "wallet guard/test owner",
                "Tests may inspect controller compatibility state.",
            )
        if lower_path.startswith("frontend/lib/features/capital/"):
            return (
                "owned-by-thread",
                "capital wallet UI",
                "Capital-owned wallet surfaces may adapt wallet transport state.",
            )
        return (
            "violation",
            "wallet UI ownership",
            rule.summary,
        )

    if rule.key == "mock-wallet-fixture-state-outside-capital":
        if lower_path.startswith("frontend/lib/features/capital/wallet/"):
            return (
                "owned-by-thread",
                "capital wallet fixture owner",
                "Capital owns wallet fixture state for tests and local fixtures.",
            )
        if lower_path.startswith("frontend/test/"):
            return (
                "owned-by-thread",
                "wallet guard/test owner",
                "Tests may name legacy fixture state while asserting guardrails.",
            )
        return (
            "violation",
            "mock wallet fixture ownership",
            rule.summary,
        )

    if rule.key == "mock-wallet-fixture-mutation-outside-capital":
        if lower_path.startswith("frontend/lib/features/capital/wallet/"):
            return (
                "owned-by-thread",
                "capital wallet fixture owner",
                "Capital owns wallet fixture mutation helpers.",
            )
        if lower_path.startswith("frontend/test/"):
            return (
                "owned-by-thread",
                "wallet guard/test owner",
                "Tests may name legacy fixture mutation while asserting guardrails.",
            )
        return (
            "violation",
            "mock wallet fixture mutation ownership",
            rule.summary,
        )

    if rule.key == "extracted-capital-fixture-state-outside-capital":
        if lower_path.startswith(
            (
                "frontend/lib/features/capital/wallet/",
                "frontend/lib/features/capital/settlement/",
                "frontend/lib/features/capital/payouts/",
                "frontend/lib/features/capital/disputes/",
                "frontend/lib/features/capital/trader/",
            )
        ):
            return (
                "owned-by-thread",
                "capital fixture owner",
                "Capital-owned fixture stores may own extracted capital state.",
            )
        if lower_path.startswith("frontend/test/"):
            return (
                "owned-by-thread",
                "capital guard/test owner",
                "Tests may name extracted fixture state while asserting guardrails.",
            )
        return (
            "violation",
            "capital fixture state ownership",
            rule.summary,
        )

    if rule.key in {
        "capital-feature-direct-controller-api",
    }:
        return (
            "violation",
            "capital facade boundary",
            rule.summary,
        )

    if rule.key == "capital-fixture-direct-mock-construction":
        if lower_path == "frontend/lib/data/gte_mock_api.dart":
            return (
                "owned-by-thread",
                "compatibility fixture shim",
                "The legacy mock exposes the compatibility constructor; callers must use the capital fixture factory.",
            )
        return (
            "violation",
            "capital fixture factory boundary",
            rule.summary,
        )

    return (
        "violation",
        "domain ownership import",
        rule.summary,
    )


def _architecture_path_hit(path: str) -> GuardrailHit | None:
    lower_path = path.lower()
    for rule_key, prefixes, summary in ARCHITECTURE_PATH_RULES:
        if not lower_path.startswith(prefixes):
            continue
        classification = "risk" if rule_key == "live-match-outside-match-center-path" else "violation"
        lane = "live match ownership migration" if classification == "risk" else "domain ownership path"
        return GuardrailHit(
            path=path,
            line=0,
            column=0,
            rule=rule_key,
            match=path,
            classification=classification,
            lane=lane,
            note=summary,
        )
    return None


def scan(roots: Sequence[str] = DEFAULT_SCAN_ROOTS) -> list[GuardrailHit]:
    hits: list[GuardrailHit] = []
    for path in _iter_files(roots):
        repo_path = _to_repo_path(path)
        architecture_path_hit = _architecture_path_hit(repo_path)
        if architecture_path_hit is not None:
            hits.append(architecture_path_hit)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            hits.append(
                GuardrailHit(
                    path=repo_path,
                    line=0,
                    column=0,
                    rule="scan-error",
                    match=type(exc).__name__,
                    classification="owned-by-thread",
                    lane="filesystem",
                    note=f"Could not read file during scan: {exc}",
                )
            )
            continue
        for line_number, line in enumerate(lines, start=1):
            lower_line = line.lower()
            for rule in RULES:
                if not _line_may_match(rule, lower_line):
                    continue
                for match in rule.pattern.finditer(line):
                    classification, lane, note = _classify(repo_path, line, rule)
                    hits.append(
                        GuardrailHit(
                            path=repo_path,
                            line=line_number,
                            column=match.start() + 1,
                            rule=rule.key,
                            match=match.group(0),
                            classification=classification,
                            lane=lane,
                            note=note,
                        )
                    )
            for rule in ARCHITECTURE_RULES:
                if not _line_may_match(rule, lower_line):
                    continue
                for match in rule.pattern.finditer(line):
                    classification, lane, note = _classify_architecture(repo_path, line, rule)
                    hits.append(
                        GuardrailHit(
                            path=repo_path,
                            line=line_number,
                            column=match.start() + 1,
                            rule=rule.key,
                            match=match.group(0),
                            classification=classification,
                            lane=lane,
                            note=note,
                        )
                    )
            for prefixes, rule in PATH_SCOPED_ARCHITECTURE_RULES:
                if not repo_path.lower().startswith(prefixes):
                    continue
                if not _line_may_match(rule, lower_line):
                    continue
                for match in rule.pattern.finditer(line):
                    classification, lane, note = _classify_architecture(repo_path, line, rule)
                    hits.append(
                        GuardrailHit(
                            path=repo_path,
                            line=line_number,
                            column=match.start() + 1,
                            rule=rule.key,
                            match=match.group(0),
                            classification=classification,
                            lane=lane,
                            note=note,
                        )
                    )
    return sorted(hits, key=lambda hit: (hit.classification, hit.path, hit.line, hit.column, hit.rule))


def changed_scan_roots(base: str, head: str | None = None) -> tuple[str, ...]:
    changed: set[str] = set()
    pathspec = [*CHANGED_SOURCE_PREFIXES, *CHANGED_SOURCE_FILES]
    if head:
        diff_command = ["git", "diff", "--name-only", "--diff-filter=ACMRT", f"{base}..{head}", "--", *pathspec]
    else:
        diff_command = ["git", "diff", "--name-only", "--diff-filter=ACMRT", base, "--", *pathspec]
    diff = subprocess.run(diff_command, cwd=REPO_ROOT, capture_output=True, check=True, text=True)
    changed.update(_normalize_repo_path(line) for line in diff.stdout.splitlines() if line.strip())

    if head is None:
        untracked = subprocess.run(
            [
                "git",
                "ls-files",
                "--others",
                "--exclude-standard",
                "--",
                *pathspec,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            text=True,
        )
        changed.update(_normalize_repo_path(line) for line in untracked.stdout.splitlines() if line.strip())

    return tuple(
        sorted(
            path
            for path in changed
            if _is_changed_source_path(path)
            and (REPO_ROOT / path).is_file()
            and _is_text_file(REPO_ROOT / path)
            and not _should_skip(REPO_ROOT / path)
        )
    )


def _summarize(hits: Sequence[GuardrailHit]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for hit in hits:
        summary[hit.classification] = summary.get(hit.classification, 0) + 1
    return dict(sorted(summary.items()))


def _print_summary(hits: Sequence[GuardrailHit]) -> None:
    print("GTEX production guardrail scan")
    print("Summary: " + json.dumps(_summarize(hits), sort_keys=True))


def _print_text(hits: Sequence[GuardrailHit]) -> None:
    summary = _summarize(hits)
    print("GTEX production guardrail scan")
    print("Summary: " + json.dumps(summary, sort_keys=True))
    for hit in hits:
        print(
            f"{hit.classification.upper()} {hit.path}:{hit.line}:{hit.column} "
            f"{hit.rule} matched {hit.match!r} [{hit.lane}] {hit.note}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan GTEX production guardrail forbidden references.")
    parser.add_argument(
        "--profile",
        choices=tuple(SCAN_PROFILES),
        default="canonical-production",
        help="Named scan root set. --root replaces the profile roots when supplied.",
    )
    parser.add_argument("--root", action="append", dest="roots", help="Replacement scan root.")
    parser.add_argument(
        "--include-changed",
        action="store_true",
        help="Add changed canonical source files while excluding audit docs and generated media.",
    )
    parser.add_argument("--diff-base", default="HEAD", help="Base ref for --include-changed.")
    parser.add_argument("--diff-head", default="", help="Optional head ref for --include-changed.")
    parser.add_argument("--format", choices=("text", "summary", "json"), default="text")
    parser.add_argument(
        "--fail-on",
        choices=("none", "violation"),
        default="violation",
        help="Exit non-zero when hits with this severity are present.",
    )
    args = parser.parse_args(argv)

    roots = list(args.roots) if args.roots else list(SCAN_PROFILES[args.profile])
    if args.include_changed:
        roots.extend(changed_scan_roots(args.diff_base, args.diff_head.strip() or None))

    hits = scan(tuple(roots))
    if args.format == "json":
        print(json.dumps({"summary": _summarize(hits), "hits": [asdict(hit) for hit in hits]}, indent=2))
    elif args.format == "summary":
        _print_summary(hits)
    else:
        _print_text(hits)

    if args.fail_on == "violation" and any(hit.classification == "violation" for hit in hits):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
