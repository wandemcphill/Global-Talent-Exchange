from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.common.enums.competition_visibility import CompetitionVisibility
from backend.app.models.competition import Competition
from backend.app.models.competition_visibility_rule import CompetitionVisibilityRule


@dataclass(slots=True)
class VisibilityDecision:
    allowed: bool
    reason: str | None = None
    requires_invite: bool = False


@dataclass(slots=True)
class CompetitionVisibilityService:
    def evaluate(
        self,
        competition: Competition,
        *,
        club_id: str,
        invite_valid: bool,
        rules: list[CompetitionVisibilityRule],
        context: dict[str, Any] | None = None,
    ) -> VisibilityDecision:
        context = context or {}
        visibility = CompetitionVisibility(competition.visibility)

        if visibility is CompetitionVisibility.INVITE_ONLY and not invite_valid:
            return VisibilityDecision(allowed=False, reason="invite_required", requires_invite=True)

        if visibility is CompetitionVisibility.PUBLIC and not rules:
            return VisibilityDecision(allowed=True)

        if visibility is CompetitionVisibility.PRIVATE and not rules:
            return VisibilityDecision(allowed=False, reason="private_competition", requires_invite=False)

        if visibility is CompetitionVisibility.GATED and not rules:
            return VisibilityDecision(allowed=False, reason="gated_competition", requires_invite=False)

        ordered_rules = sorted((rule for rule in rules if rule.enabled), key=lambda rule: rule.priority)
        for rule in ordered_rules:
            decision = self._evaluate_rule(rule, club_id=club_id, context=context, invite_valid=invite_valid)
            if not decision.allowed:
                return decision

        return VisibilityDecision(allowed=True)

    def _evaluate_rule(
        self,
        rule: CompetitionVisibilityRule,
        *,
        club_id: str,
        context: dict[str, Any],
        invite_valid: bool,
    ) -> VisibilityDecision:
        payload = rule.rule_payload or {}
        if rule.rule_type == "allowlist_clubs":
            allowed = club_id in set(payload.get("club_ids", []))
            return VisibilityDecision(allowed=allowed, reason=None if allowed else "club_not_allowlisted")
        if rule.rule_type == "denylist_clubs":
            denied = club_id in set(payload.get("club_ids", []))
            return VisibilityDecision(allowed=not denied, reason="club_denied" if denied else None)
        if rule.rule_type == "region_allowlist":
            region = context.get("region")
            allowed = region in set(payload.get("regions", []))
            return VisibilityDecision(allowed=allowed, reason=None if allowed else "region_not_allowed")
        if rule.rule_type == "min_rank":
            rank = context.get("rank")
            threshold = payload.get("max_rank")
            if rank is None or threshold is None:
                return VisibilityDecision(allowed=False, reason="rank_required")
            allowed = int(rank) <= int(threshold)
            return VisibilityDecision(allowed=allowed, reason=None if allowed else "rank_too_low")
        if rule.rule_type == "requires_invite":
            return VisibilityDecision(allowed=invite_valid, reason=None if invite_valid else "invite_required", requires_invite=True)

        return VisibilityDecision(allowed=False, reason="visibility_rule_unhandled")


__all__ = ["CompetitionVisibilityService", "VisibilityDecision"]
