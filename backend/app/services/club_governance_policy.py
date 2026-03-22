from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any, Mapping

DEFAULT_GOVERNANCE_MODE = "shareholder_weighted"
DEFAULT_VOTE_WEIGHT_MODEL = "creator_control_plus_fan_shares"
DEFAULT_ANTI_TAKEOVER_MAX_HOLDER_BPS = 2400
DEFAULT_OWNER_APPROVAL_THRESHOLD_BPS = 1500
DEFAULT_PROPOSAL_SHARE_THRESHOLD = 5
DEFAULT_QUORUM_SHARE_BPS = 1200


def default_governance_policy(*, max_shares_per_fan: int | None = None) -> dict[str, object]:
    fan_cap = max(1, int(max_shares_per_fan or DEFAULT_PROPOSAL_SHARE_THRESHOLD))
    proposal_threshold = min(DEFAULT_PROPOSAL_SHARE_THRESHOLD, fan_cap)
    return {
        "governance_mode": DEFAULT_GOVERNANCE_MODE,
        "vote_weight_model": DEFAULT_VOTE_WEIGHT_MODEL,
        "anti_takeover_enabled": True,
        "max_holder_bps": DEFAULT_ANTI_TAKEOVER_MAX_HOLDER_BPS,
        "owner_approval_threshold_bps": DEFAULT_OWNER_APPROVAL_THRESHOLD_BPS,
        "proposal_share_threshold": max(1, proposal_threshold),
        "quorum_share_bps": DEFAULT_QUORUM_SHARE_BPS,
        "shareholder_rights_preserved_on_sale": True,
    }


def governance_policy_from_metadata(
    metadata_json: Mapping[str, Any] | None,
    *,
    max_shares_per_fan: int | None = None,
) -> dict[str, object]:
    defaults = default_governance_policy(max_shares_per_fan=max_shares_per_fan)
    policy = dict(defaults)
    if metadata_json:
        candidate = metadata_json.get("governance_policy")
        if isinstance(candidate, Mapping):
            policy.update(candidate)

    fan_cap = max(1, int(max_shares_per_fan or 1))
    policy["governance_mode"] = str(policy.get("governance_mode") or DEFAULT_GOVERNANCE_MODE)
    policy["vote_weight_model"] = str(policy.get("vote_weight_model") or DEFAULT_VOTE_WEIGHT_MODEL)
    policy["anti_takeover_enabled"] = bool(policy.get("anti_takeover_enabled", True))
    policy["max_holder_bps"] = _bounded_int(policy.get("max_holder_bps"), lower=1, upper=4900, default=DEFAULT_ANTI_TAKEOVER_MAX_HOLDER_BPS)
    policy["owner_approval_threshold_bps"] = _bounded_int(
        policy.get("owner_approval_threshold_bps"),
        lower=0,
        upper=10000,
        default=DEFAULT_OWNER_APPROVAL_THRESHOLD_BPS,
    )
    policy["proposal_share_threshold"] = _bounded_int(
        policy.get("proposal_share_threshold"),
        lower=1,
        upper=fan_cap,
        default=min(DEFAULT_PROPOSAL_SHARE_THRESHOLD, fan_cap),
    )
    policy["quorum_share_bps"] = _bounded_int(
        policy.get("quorum_share_bps"),
        lower=0,
        upper=10000,
        default=DEFAULT_QUORUM_SHARE_BPS,
    )
    policy["shareholder_rights_preserved_on_sale"] = bool(
        policy.get("shareholder_rights_preserved_on_sale", True)
    )
    return policy


def owner_approval_required(policy: Mapping[str, Any], *, ownership_bps: int) -> bool:
    return ownership_bps >= int(policy.get("owner_approval_threshold_bps") or 0)


def fully_diluted_governance_shares(*, creator_controlled_shares: int, fan_share_supply: int) -> int:
    return max(0, int(creator_controlled_shares)) + max(0, int(fan_share_supply))


def holder_cap_share_count(*, total_governance_shares: int, max_holder_bps: int) -> int:
    if total_governance_shares <= 0 or max_holder_bps <= 0:
        return 0
    cap = (
        Decimal(total_governance_shares) * Decimal(int(max_holder_bps)) / Decimal("10000")
    ).to_integral_value(rounding=ROUND_DOWN)
    return max(1, int(cap))


def quorum_share_count(*, total_governance_shares: int, quorum_share_bps: int) -> int:
    if total_governance_shares <= 0 or quorum_share_bps <= 0:
        return 0
    shares = (
        Decimal(total_governance_shares) * Decimal(int(quorum_share_bps)) / Decimal("10000")
    ).to_integral_value(rounding=ROUND_HALF_UP)
    return max(1, int(shares))


def ownership_bps(*, share_count: int, total_share_count: int) -> int:
    if total_share_count <= 0 or share_count <= 0:
        return 0
    return int(
        (
            Decimal(int(share_count)) * Decimal("10000") / Decimal(int(total_share_count))
        ).to_integral_value(rounding=ROUND_HALF_UP)
    )


def _bounded_int(value: Any, *, lower: int, upper: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(lower, min(upper, parsed))


__all__ = [
    "DEFAULT_ANTI_TAKEOVER_MAX_HOLDER_BPS",
    "DEFAULT_OWNER_APPROVAL_THRESHOLD_BPS",
    "DEFAULT_PROPOSAL_SHARE_THRESHOLD",
    "DEFAULT_QUORUM_SHARE_BPS",
    "default_governance_policy",
    "fully_diluted_governance_shares",
    "governance_policy_from_metadata",
    "holder_cap_share_count",
    "owner_approval_required",
    "ownership_bps",
    "quorum_share_count",
]
