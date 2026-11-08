from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import generate_uuid
from app.models.club_dna import (
    ClubDNAPolicy,
    ClubGovernanceException,
    DNAPhilosophy,
    ExceptionStatus,
    FinancialPhilosophy,
    PolicyAgeMode,
    PolicyNationalityMode,
    TransferStrategy,
)
from app.models.club_profile import ClubProfile

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Mapping

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
    policy["max_holder_bps"] = _bounded_int(
        policy.get("max_holder_bps"), lower=1, upper=4900, default=DEFAULT_ANTI_TAKEOVER_MAX_HOLDER_BPS
    )
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
    policy["shareholder_rights_preserved_on_sale"] = bool(policy.get("shareholder_rights_preserved_on_sale", True))
    return policy


def owner_approval_required(policy: Mapping[str, Any], *, ownership_bps: int) -> bool:
    return ownership_bps >= int(policy.get("owner_approval_threshold_bps") or 0)


def fully_diluted_governance_shares(*, creator_controlled_shares: int, fan_share_supply: int) -> int:
    return max(0, int(creator_controlled_shares)) + max(0, int(fan_share_supply))


def holder_cap_share_count(*, total_governance_shares: int, max_holder_bps: int) -> int:
    if total_governance_shares <= 0 or max_holder_bps <= 0:
        return 0
    cap = (Decimal(total_governance_shares) * Decimal(int(max_holder_bps)) / Decimal("10000")).to_integral_value(
        rounding=ROUND_DOWN
    )
    return max(1, int(cap))


def quorum_share_count(*, total_governance_shares: int, quorum_share_bps: int) -> int:
    if total_governance_shares <= 0 or quorum_share_bps <= 0:
        return 0
    shares = (Decimal(total_governance_shares) * Decimal(int(quorum_share_bps)) / Decimal("10000")).to_integral_value(
        rounding=ROUND_HALF_UP
    )
    return max(1, int(shares))


def ownership_bps(*, share_count: int, total_share_count: int) -> int:
    if total_share_count <= 0 or share_count <= 0:
        return 0
    return int(
        (Decimal(int(share_count)) * Decimal("10000") / Decimal(int(total_share_count))).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )


def _bounded_int(value: Any, *, lower: int, upper: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(lower, min(upper, parsed))


@dataclass(slots=True, frozen=True)
class PolicyEvaluationResult:
    is_eligible: bool
    policy_violated: str | None
    violation_reason: str | None
    exception_permitted: bool
    has_approved_exception: bool
    exception_id: str | None = None


def _normalize_code(code: str | None) -> str:
    return (code or "").strip().upper()


def _matches_nationality(
    target_codes: list[str],
    player_nationality: str | None,
    dual_nationalities: list[str] | None = None,
    allow_dual: bool = True,
) -> bool:
    if not target_codes:
        return True
    normalized_targets = {_normalize_code(c) for c in target_codes if c}
    if not normalized_targets:
        return True

    candidates = [_normalize_code(player_nationality)]
    if allow_dual and dual_nationalities:
        candidates.extend(_normalize_code(d) for d in dual_nationalities if d)

    for cand in candidates:
        if not cand:
            continue
        if cand in normalized_targets:
            return True
        # Match ISO substrings or country names (e.g. FRA vs FRANCE, NGA vs NIGERIA, BRA vs BRAZIL)
        for target in normalized_targets:
            if target == cand:
                return True
            if len(target) == 3 and len(cand) > 3 and cand.startswith(target):
                return True
            if len(cand) == 3 and len(target) > 3 and target.startswith(cand):
                return True
    return False


@dataclass(slots=True)
class ClubGovernancePolicyService:
    session: Session

    def get_or_create_policy(self, club_id: str) -> ClubDNAPolicy:
        policy = self.session.scalar(select(ClubDNAPolicy).where(ClubDNAPolicy.club_id == club_id))
        if policy is not None:
            return policy

        club = self.session.get(ClubProfile, club_id)
        if club is None:
            # Ephemeral default policy for unpersisted or test contexts
            return ClubDNAPolicy(
                id=generate_uuid(),
                club_id=club_id,
                primary_philosophy=DNAPhilosophy.BALANCED.value,
                secondary_philosophies=[],
                nationality_mode=PolicyNationalityMode.NONE.value,
                target_nationalities=[],
                allow_dual_nationality=True,
                age_mode=PolicyAgeMode.NONE.value,
                preferred_max_age=None,
                allow_age_exceptions=True,
                transfer_strategy=TransferStrategy.BALANCED.value,
                financial_philosophy=FinancialPhilosophy.BALANCED.value,
                club_vision_narrative=None,
                metadata_json={},
            )

        policy = ClubDNAPolicy(
            id=generate_uuid(),
            club_id=club.id,
            primary_philosophy=DNAPhilosophy.BALANCED.value,
            secondary_philosophies=[],
            nationality_mode=PolicyNationalityMode.NONE.value,
            target_nationalities=[club.country_code] if club.country_code else [],
            allow_dual_nationality=True,
            age_mode=PolicyAgeMode.NONE.value,
            preferred_max_age=None,
            allow_age_exceptions=True,
            transfer_strategy=TransferStrategy.BALANCED.value,
            financial_philosophy=FinancialPhilosophy.BALANCED.value,
            club_vision_narrative=f"Balanced football philosophy rooted in {club.city_name or club.country_code or 'club tradition'}.",
            metadata_json={"auto_seeded": True},
        )
        self.session.add(policy)
        self.session.flush()
        return policy

    def update_policy(self, club_id: str, updates: dict[str, Any]) -> ClubDNAPolicy:
        policy = self.get_or_create_policy(club_id)

        if "primary_philosophy" in updates:
            policy.primary_philosophy = str(updates["primary_philosophy"])
        if "secondary_philosophies" in updates:
            policy.secondary_philosophies = [str(item) for item in (updates["secondary_philosophies"] or [])]
        if "nationality_mode" in updates:
            mode_val = str(updates["nationality_mode"]).lower()
            if mode_val not in {m.value for m in PolicyNationalityMode}:
                raise ValueError(f"Invalid nationality_mode: {mode_val}")
            policy.nationality_mode = mode_val
        if "target_nationalities" in updates:
            policy.target_nationalities = [_normalize_code(c) for c in (updates["target_nationalities"] or []) if c]
        if "allow_dual_nationality" in updates:
            policy.allow_dual_nationality = bool(updates["allow_dual_nationality"])
        if "age_mode" in updates:
            age_mode_val = str(updates["age_mode"]).lower()
            if age_mode_val not in {m.value for m in PolicyAgeMode}:
                raise ValueError(f"Invalid age_mode: {age_mode_val}")
            policy.age_mode = age_mode_val
        if "preferred_max_age" in updates:
            val = updates["preferred_max_age"]
            policy.preferred_max_age = int(val) if val is not None else None
        if "allow_age_exceptions" in updates:
            policy.allow_age_exceptions = bool(updates["allow_age_exceptions"])
        if "transfer_strategy" in updates:
            policy.transfer_strategy = str(updates["transfer_strategy"])
        if "financial_philosophy" in updates:
            policy.financial_philosophy = str(updates["financial_philosophy"])
        if "club_vision_narrative" in updates:
            policy.club_vision_narrative = (
                str(updates["club_vision_narrative"]) if updates["club_vision_narrative"] else None
            )
        if "metadata_json" in updates and isinstance(updates["metadata_json"], dict):
            policy.metadata_json = {**(policy.metadata_json or {}), **updates["metadata_json"]}

        self.session.flush()
        return policy

    def evaluate_player_recruitment_eligibility(
        self,
        club_id: str,
        *,
        player_id: str | None = None,
        player_name: str | None = None,
        nationality: str | None = None,
        age: int | None = None,
        dual_nationalities: list[str] | None = None,
    ) -> PolicyEvaluationResult:
        policy = self.get_or_create_policy(club_id)

        # 1. Check for pre-existing approved governance exception
        if player_id:
            exception = self.session.scalar(
                select(ClubGovernanceException).where(
                    ClubGovernanceException.club_id == club_id,
                    ClubGovernanceException.player_id == player_id,
                    ClubGovernanceException.status == ExceptionStatus.APPROVED.value,
                )
            )
            if exception is not None:
                return PolicyEvaluationResult(
                    is_eligible=True,
                    policy_violated=None,
                    violation_reason=None,
                    exception_permitted=True,
                    has_approved_exception=True,
                    exception_id=exception.id,
                )

        # 2. Evaluate Nationality Restrictions
        if policy.nationality_mode == PolicyNationalityMode.EXCLUSIVE.value and policy.target_nationalities:
            is_match = _matches_nationality(
                policy.target_nationalities,
                nationality,
                dual_nationalities=dual_nationalities,
                allow_dual=policy.allow_dual_nationality,
            )
            if not is_match:
                targets_str = ", ".join(policy.target_nationalities)
                reason = (
                    f"Recruitment rejected: Club operates a strict exclusive nationality policy ({targets_str}). "
                    f"Player nationality is '{nationality or 'Unknown'}', which does not satisfy club eligibility rules."
                )
                return PolicyEvaluationResult(
                    is_eligible=False,
                    policy_violated="nationality",
                    violation_reason=reason,
                    exception_permitted=False,
                    has_approved_exception=False,
                )

        # 3. Evaluate Age Restrictions
        if policy.age_mode == PolicyAgeMode.STRICT.value and policy.preferred_max_age is not None and age is not None:
            if age > policy.preferred_max_age:
                targets_max = policy.preferred_max_age
                if policy.allow_age_exceptions:
                    reason = (
                        f"Recruitment restriction: Club age policy restricts signings to U{targets_max} (player is {age}). "
                        f"Owner exception approval is permitted and required before completing this signing."
                    )
                    return PolicyEvaluationResult(
                        is_eligible=False,
                        policy_violated="age",
                        violation_reason=reason,
                        exception_permitted=True,
                        has_approved_exception=False,
                    )
                else:
                    reason = (
                        f"Recruitment rejected: Club age policy strictly prohibits signings over age {targets_max}. "
                        f"Player is {age} and no exceptions are permitted."
                    )
                    return PolicyEvaluationResult(
                        is_eligible=False,
                        policy_violated="age",
                        violation_reason=reason,
                        exception_permitted=False,
                        has_approved_exception=False,
                    )

        # 4. If nationality or age mode is "preferred", recruitment is permitted with preference alignment notes
        violation_reason = None
        if policy.nationality_mode == PolicyNationalityMode.PREFERRED.value and policy.target_nationalities:
            if not _matches_nationality(
                policy.target_nationalities,
                nationality,
                dual_nationalities=dual_nationalities,
                allow_dual=policy.allow_dual_nationality,
            ):
                violation_reason = f"Recruitment notice: Player does not match club preferred nationality ({', '.join(policy.target_nationalities)})."

        if (
            policy.age_mode == PolicyAgeMode.PREFERRED.value
            and policy.preferred_max_age is not None
            and age is not None
            and age > policy.preferred_max_age
        ):
            age_note = f"Recruitment notice: Player age {age} exceeds preferred target U{policy.preferred_max_age}."
            violation_reason = f"{violation_reason} {age_note}" if violation_reason else age_note

        return PolicyEvaluationResult(
            is_eligible=True,
            policy_violated=None,
            violation_reason=violation_reason,
            exception_permitted=True,
            has_approved_exception=False,
        )

    def evaluate_player_entity(
        self,
        club_id: str,
        player_or_id: Any,
    ) -> PolicyEvaluationResult:
        player_id = None
        player_name = None
        nationality = None
        age = None

        if isinstance(player_or_id, str):
            player_id = player_or_id
            from app.ingestion.models import Player

            player = self.session.get(Player, player_id)
        else:
            player = player_or_id
            player_id = getattr(player, "id", None)

        if player is not None:
            player_name = (
                getattr(player, "canonical_display_name", None) or getattr(player, "full_name", None) or "Target Player"
            )
            country = getattr(player, "country", None)
            if country is not None:
                nationality = getattr(country, "code", None) or getattr(country, "name", None)
            if not nationality and getattr(player, "country_id", None):
                nationality = getattr(player, "country_id")

            if not nationality:
                try:
                    from app.models.real_player_profile import RealPlayerProfile

                    rpp = self.session.scalar(
                        select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id == player_id)
                    )
                    if rpp and rpp.nationality:
                        nationality = rpp.nationality
                except Exception:
                    pass

            dob = getattr(player, "date_of_birth", None)
            if dob:
                from datetime import date

                today = date.today()
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        return self.evaluate_player_recruitment_eligibility(
            club_id,
            player_id=player_id,
            player_name=player_name,
            nationality=nationality,
            age=age,
        )

    def approve_exception(
        self,
        club_id: str,
        *,
        player_id: str,
        player_name: str,
        policy_type: str,
        reason: str,
        user_id: str,
        player_nationality: str | None = None,
        player_age: int | None = None,
    ) -> ClubGovernanceException:
        if not reason or len(reason.strip()) < 5:
            raise ValueError("A formal governance justification reason of at least 5 characters is required.")

        existing = self.session.scalar(
            select(ClubGovernanceException).where(
                ClubGovernanceException.club_id == club_id,
                ClubGovernanceException.player_id == player_id,
                ClubGovernanceException.status == ExceptionStatus.APPROVED.value,
            )
        )
        if existing is not None:
            existing.reason = reason.strip()
            existing.approved_at = datetime.now(timezone.utc)
            self.session.flush()
            return existing

        exception = ClubGovernanceException(
            id=generate_uuid(),
            club_id=club_id,
            policy_type=policy_type,
            player_id=player_id,
            player_name=player_name,
            player_nationality=player_nationality,
            player_age=player_age,
            reason=reason.strip(),
            approved_by_user_id=user_id,
            status=ExceptionStatus.APPROVED.value,
            approved_at=datetime.now(timezone.utc),
            metadata_json={"approved_by_governance": True},
        )
        self.session.add(exception)
        self.session.flush()
        return exception

    def list_exceptions(self, club_id: str) -> list[ClubGovernanceException]:
        return list(
            self.session.scalars(
                select(ClubGovernanceException)
                .where(ClubGovernanceException.club_id == club_id)
                .order_by(ClubGovernanceException.approved_at.desc())
            ).all()
        )

    def generate_squad_dna_recommendations(self, club_id: str) -> dict[str, Any]:
        """Generate AI roster, academy promotion, and tactical alignment recommendations from Club DNA."""
        policy = self.get_or_create_policy(club_id)
        primary = (policy.primary_philosophy or "balanced").lower()
        secondaries = [s.lower() for s in (policy.secondary_philosophies or [])]
        all_phil = {primary, *secondaries}

        if "youth_development" in all_phil or "academy_first" in all_phil:
            formation = "4-3-3"
            mentality = "High-Energy Positional Development"
            u21_share = 45 if "academy_first" in all_phil else 38
            academy_quota = 4 if "academy_first" in all_phil else 3
        elif "superstar" in all_phil or "big_spending" in all_phil:
            formation = "4-2-4"
            mentality = "Galactico Attacking Dominance"
            u21_share = 15
            academy_quota = 1
        elif "selling_club" in all_phil or "financially_sustainable" in all_phil:
            formation = "3-4-3"
            mentality = "High-Value Showcase Transition"
            u21_share = 32
            academy_quota = 2
        else:
            formation = "4-3-3"
            mentality = "Balanced Tactical Control"
            u21_share = 25
            academy_quota = 2

        scouting_directives: list[str] = []
        if policy.nationality_mode == "exclusive" and policy.target_nationalities:
            nats = ", ".join(policy.target_nationalities)
            dual_str = (
                " (dual-nationality eligible)" if policy.allow_dual_nationality else " (single nationality strict)"
            )
            scouting_directives.append(f"Enforce strict domestic recruitment restricted to {nats}{dual_str}.")
        elif policy.nationality_mode == "preferred" and policy.target_nationalities:
            nats = ", ".join(policy.target_nationalities)
            scouting_directives.append(f"Prioritize scouting networks in {nats} (+25% recommendation weight).")
        else:
            scouting_directives.append("Maintain global scouting network across all FIFA confederations.")

        if policy.age_mode != "none" and policy.preferred_max_age:
            mode_label = "Strict hard ceiling" if policy.age_mode == "strict" else "Preferred target ceiling"
            scouting_directives.append(
                f"{mode_label} at U{policy.preferred_max_age}; focus transfer bids on high-upside prospects aged 17-{policy.preferred_max_age}."
            )

        tactical_directives: list[str] = [
            f"Deploy {formation} ({mentality}) to maximize squad profile synergy.",
            f"Target {u21_share}% matchday minutes allocation for U21 and academy-developed players.",
            f"Promote at least {academy_quota} academy graduates into the first-team matchday rotation this season.",
        ]
        if "selling_club" in all_phil:
            tactical_directives.append(
                "Feature high-potential transfer-listed talents in continental showcase fixtures to maximize market valuation."
            )

        exceptions_count = len(self.list_exceptions(club_id))
        compliance_score = max(70, 98 - exceptions_count * 4)

        return {
            "club_id": club_id,
            "primary_philosophy": policy.primary_philosophy,
            "secondary_philosophies": list(policy.secondary_philosophies or []),
            "recommended_formation": formation,
            "recommended_mentality": mentality,
            "target_u21_minutes_share_pct": u21_share,
            "academy_promotion_quota": academy_quota,
            "dna_compliance_score": compliance_score,
            "scouting_directives": scouting_directives,
            "tactical_directives": tactical_directives,
            "transfer_strategy": policy.transfer_strategy,
            "financial_philosophy": policy.financial_philosophy,
        }
