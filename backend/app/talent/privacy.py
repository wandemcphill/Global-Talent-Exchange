"""Viewer-scoped projection of talent data.

Every talent payload leaving this service is built by *allowlist*: a projection
function names the fields it emits for a given `ViewerScope`. Nothing is
emitted by serialising an ORM row wholesale, because that is how private
columns leak the day someone adds one.

Three separate concerns are handled here:

* **Visibility** — may this viewer see the profile at all (draft, hidden and
  suspended profiles are not public).
* **Field scope** — which fields this viewer gets. Birth dates, cities,
  moderation state, suspension reasons and reviewer notes each sit at a
  different tier.
* **Signal scope** — negative scouting signals (discipline, availability risk,
  regression, volatility) are withheld from anonymous traffic. They are real
  and scouts need them; broadcasting them publicly about a named person is a
  different act from surfacing them to an accountable, signed-in scout.

KYC status, contact details, credentials and payment data are not merely
filtered here — they are never loaded into this layer at all. `assert_no_private_fields`
exists so a regression that starts loading them fails loudly in tests.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from app.models.user import User, UserRole
from app.talent.constants import (
    RESTRICTED_SIGNAL_CODES,
    ViewerScope,
    VisibilityState,
)
from app.talent.models import TalentProfile

SCOUT_ROLES: frozenset[UserRole] = frozenset({UserRole.SCOUT, UserRole.CLUB, UserRole.AGENT})
ADMIN_ROLES: frozenset[UserRole] = frozenset({UserRole.ADMIN, UserRole.SUPER_ADMIN})

# Key fragments that must never appear anywhere in a talent payload, at any
# scope. These belong to identity, compliance and money domains that the talent
# exchange has no business republishing.
PRIVATE_FIELD_FRAGMENTS: frozenset[str] = frozenset(
    {
        "kyc",
        "password",
        "email",
        "phone",
        "ssn",
        "national_id",
        "passport",
        "document",
        "bank",
        "card",
        "iban",
        "wallet",
        "ledger",
        "payout",
        "payment",
        "balance",
        "credential_file",
    }
)

_SCOPES_WITH_RESTRICTED_SIGNALS: frozenset[str] = frozenset(
    {ViewerScope.SCOUT.value, ViewerScope.OWNER.value, ViewerScope.ADMIN.value}
)


def resolve_viewer_scope(profile: TalentProfile | None, viewer: User | None) -> ViewerScope:
    if viewer is None:
        return ViewerScope.PUBLIC
    if viewer.role in ADMIN_ROLES:
        return ViewerScope.ADMIN
    if profile is not None and profile.owner_user_id and profile.owner_user_id == viewer.id:
        return ViewerScope.OWNER
    if viewer.role in SCOUT_ROLES:
        return ViewerScope.SCOUT
    return ViewerScope.PUBLIC


def is_scout_scope(scope: ViewerScope) -> bool:
    return scope in {ViewerScope.SCOUT, ViewerScope.OWNER, ViewerScope.ADMIN}


def can_view_profile(profile: TalentProfile, scope: ViewerScope) -> bool:
    if scope in {ViewerScope.ADMIN, ViewerScope.OWNER}:
        return True
    return profile.visibility_state == VisibilityState.PUBLISHED.value


def visible_signals(signal_payloads: Sequence[Mapping[str, Any]], scope: ViewerScope) -> list[dict[str, Any]]:
    allow_restricted = scope.value in _SCOPES_WITH_RESTRICTED_SIGNALS
    visible: list[dict[str, Any]] = []
    for payload in signal_payloads:
        code = str(payload.get("code", ""))
        if not allow_restricted and code in RESTRICTED_SIGNAL_CODES:
            continue
        visible.append(dict(payload))
    return sorted(visible, key=lambda item: str(item.get("code", "")))


def visible_portfolio(profile: TalentProfile, scope: ViewerScope) -> list[dict[str, Any]]:
    """Only moderator-approved media is shown outside owner/admin views."""

    entries: list[dict[str, Any]] = []
    for raw in profile.portfolio_json or []:
        if not isinstance(raw, Mapping):
            continue
        approved = bool(raw.get("approved", False))
        if not approved and scope not in {ViewerScope.OWNER, ViewerScope.ADMIN}:
            continue
        entry = {
            "kind": str(raw.get("kind", "link")),
            "url": str(raw.get("url", "")),
            "title": str(raw.get("title", "")),
            "approved": approved,
        }
        entries.append(entry)
    return entries


def project_profile(
    profile: TalentProfile,
    *,
    scope: ViewerScope,
    signal_payloads: Sequence[Mapping[str, Any]] = (),
    ranking_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the talent payload for one viewer scope, by allowlist."""

    payload: dict[str, Any] = {
        "player_id": profile.player_id,
        "profile_id": profile.id,
        "display_name": profile.display_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "position_code": profile.position_code,
        "secondary_positions": list(profile.secondary_positions_json or []),
        "tactical_roles": list(profile.tactical_roles_json or []),
        "preferred_foot": profile.preferred_foot,
        "age_years": profile.age_years,
        "nationality_code": profile.nationality_code,
        "nationality_name": profile.nationality_name,
        "location_country_code": profile.location_country_code,
        "location_region": profile.location_region,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "current_club_name": profile.current_club_name,
        "current_competition_name": profile.current_competition_name,
        "availability_status": profile.availability_status,
        "availability_note": profile.availability_note,
        "available_from": profile.available_from.isoformat() if profile.available_from else None,
        "experience_years": round(float(profile.experience_years or 0.0), 2),
        "verification_tier": profile.verification_tier,
        "verification_reviewed_at": (
            profile.verification_reviewed_at.isoformat() if profile.verification_reviewed_at else None
        ),
        "visibility_state": profile.visibility_state,
        "is_featured": bool(profile.is_featured),
        "technical_attributes": dict(profile.technical_attributes_json or {}),
        "tactical_attributes": dict(profile.tactical_attributes_json or {}),
        "physical_attributes": dict(profile.physical_attributes_json or {}),
        "composite_score": round(float(profile.composite_score or 0.0), 2),
        "form_score": round(float(profile.form_score or 0.0), 2),
        "consistency_score": round(float(profile.consistency_score or 0.0), 2),
        "competition_level_score": round(float(profile.competition_level_score or 0.0), 2),
        "ranking_confidence": round(float(profile.ranking_confidence or 0.0), 4),
        "ranking_sample_size": int(profile.ranking_sample_size or 0),
        "ranking_computed_at": (profile.ranking_computed_at.isoformat() if profile.ranking_computed_at else None),
        "ranking_config_version": profile.ranking_config_version,
        "portfolio": visible_portfolio(profile, scope),
        "signals": visible_signals(signal_payloads, scope),
        "viewer_scope": scope.value,
    }

    if is_scout_scope(scope):
        payload["location_city"] = profile.location_city
        payload["ranking_inputs_digest"] = profile.ranking_inputs_digest

    if scope in {ViewerScope.OWNER, ViewerScope.ADMIN}:
        payload["owner_user_id"] = profile.owner_user_id
        payload["date_of_birth"] = profile.date_of_birth.isoformat() if profile.date_of_birth else None
        payload["moderation_state"] = profile.moderation_state
        payload["verification_expires_at"] = (
            profile.verification_expires_at.isoformat() if profile.verification_expires_at else None
        )

    if scope is ViewerScope.ADMIN:
        payload["internal_notes"] = profile.internal_notes
        payload["suspension_reason"] = profile.suspension_reason
        payload["featured_rank"] = profile.featured_rank
        payload["metadata"] = dict(profile.metadata_json or {})

    if ranking_payload is not None:
        payload["ranking"] = dict(ranking_payload)

    return payload


def project_search_result(profile: TalentProfile, *, scope: ViewerScope) -> dict[str, Any]:
    """Compact card for result lists. Strictly a subset of the full profile."""

    card: dict[str, Any] = {
        "player_id": profile.player_id,
        "profile_id": profile.id,
        "display_name": profile.display_name,
        "headline": profile.headline,
        "position_code": profile.position_code,
        "secondary_positions": list(profile.secondary_positions_json or []),
        "tactical_roles": list(profile.tactical_roles_json or []),
        "preferred_foot": profile.preferred_foot,
        "age_years": profile.age_years,
        "nationality_code": profile.nationality_code,
        "nationality_name": profile.nationality_name,
        "location_country_code": profile.location_country_code,
        "location_region": profile.location_region,
        "current_club_name": profile.current_club_name,
        "availability_status": profile.availability_status,
        "verification_tier": profile.verification_tier,
        "experience_years": round(float(profile.experience_years or 0.0), 2),
        "composite_score": round(float(profile.composite_score or 0.0), 2),
        "form_score": round(float(profile.form_score or 0.0), 2),
        "competition_level_score": round(float(profile.competition_level_score or 0.0), 2),
        "ranking_confidence": round(float(profile.ranking_confidence or 0.0), 4),
        "is_featured": bool(profile.is_featured),
        "signal_codes": visible_signal_codes(profile.active_signal_codes_json or [], scope),
    }
    if is_scout_scope(scope):
        card["location_city"] = profile.location_city
    return card


def visible_signal_codes(codes: Iterable[str], scope: ViewerScope) -> list[str]:
    allow_restricted = scope.value in _SCOPES_WITH_RESTRICTED_SIGNALS
    return sorted({str(code) for code in codes if allow_restricted or str(code) not in RESTRICTED_SIGNAL_CODES})


def assert_no_private_fields(payload: Any, *, path: str = "$") -> None:
    """Raise if a payload contains a key from a private domain.

    Used by the privacy tests and cheap enough to call from a service in a
    debug build. Matching is on key-name fragments, so `kyc_status`,
    `user_email` and `payout_account_id` are all caught.
    """

    if isinstance(payload, Mapping):
        for key, value in payload.items():
            lowered = str(key).lower()
            for fragment in PRIVATE_FIELD_FRAGMENTS:
                if fragment in lowered:
                    raise AssertionError(f"Talent payload exposes private field '{key}' at {path}.")
            assert_no_private_fields(value, path=f"{path}.{key}")
        return
    if isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            assert_no_private_fields(item, path=f"{path}[{index}]")


__all__ = [
    "ADMIN_ROLES",
    "PRIVATE_FIELD_FRAGMENTS",
    "SCOUT_ROLES",
    "assert_no_private_fields",
    "can_view_profile",
    "is_scout_scope",
    "project_profile",
    "project_search_result",
    "resolve_viewer_scope",
    "visible_portfolio",
    "visible_signal_codes",
    "visible_signals",
]
