"""Admin tooling for the Talent Exchange: verification, moderation, correction.

Two rules shape this module.

**Verification is earned, never assumed.** `resolve_effective_tier` derives a
profile's tier purely from its audited decision records: the highest tier that
has a live `GRANTED` record which has not since been revoked, rejected or
expired. A profile simply existing, or being well-filled-in, grants nothing.

**Admins correct facts, not scores.** There is no endpoint that writes a
composite score. Corrections change the underlying facts and then re-run the
deterministic pipeline, so every published number remains reproducible from its
inputs. Every action writes an append-only `TalentModerationAction` row
capturing before/after state and the acting admin.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.talent import privacy
from app.talent.constants import (
    ModerationAction,
    ModerationState,
    VERIFICATION_TIER_RANK,
    VerificationDecision,
    VerificationTier,
    ViewerScope,
    VisibilityState,
)
from app.talent.inputs import normalise_attributes
from app.talent.models import (
    TalentModerationAction,
    TalentProfile,
    TalentVerificationRecord,
)
from app.talent.service import (
    TalentExchangeService,
    TalentNotFoundError,
    TalentValidationError,
)

# Profile fields an admin correction may set, mapped to the payload key.
CORRECTABLE_SCALAR_FIELDS: Mapping[str, str] = {
    "display_name": "display_name",
    "headline": "headline",
    "summary": "summary",
    "position_code": "position_code",
    "preferred_foot": "preferred_foot",
    "date_of_birth": "date_of_birth",
    "nationality_code": "nationality_code",
    "nationality_name": "nationality_name",
    "location_country_code": "location_country_code",
    "location_region": "location_region",
    "location_city": "location_city",
    "height_cm": "height_cm",
    "weight_kg": "weight_kg",
    "availability_note": "availability_note",
    "available_from": "available_from",
    "experience_years": "experience_years",
}

AUDIT_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "display_name",
    "position_code",
    "verification_tier",
    "visibility_state",
    "moderation_state",
    "is_featured",
    "featured_rank",
    "availability_status",
    "composite_score",
    "suspension_reason",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def resolve_effective_tier(records: list[TalentVerificationRecord], *, now: datetime | None = None) -> str:
    """Highest tier backed by a live, unrevoked, unexpired grant."""

    reference = now or _utcnow()
    latest_by_tier: dict[str, TalentVerificationRecord] = {}
    for record in sorted(
        records,
        key=lambda item: (_as_utc(item.decided_at) or _as_utc(item.created_at) or reference, item.id),
    ):
        latest_by_tier[record.tier] = record

    best_rank = VERIFICATION_TIER_RANK[VerificationTier.UNVERIFIED.value]
    best_tier = VerificationTier.UNVERIFIED.value
    for tier, record in latest_by_tier.items():
        if record.decision != VerificationDecision.GRANTED.value:
            continue
        expires_at = _as_utc(record.expires_at)
        if expires_at is not None and expires_at <= reference:
            continue
        rank = VERIFICATION_TIER_RANK.get(tier, 0)
        if rank > best_rank:
            best_rank = rank
            best_tier = tier
    return best_tier


class TalentAdminService:
    def __init__(self, session: Session, *, today: date | None = None) -> None:
        self.session = session
        self.exchange = TalentExchangeService(session, today=today)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _profile(self, player_id: str) -> TalentProfile:
        return self.exchange.get_profile_row(player_id)

    @staticmethod
    def _snapshot(profile: TalentProfile) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        for field_name in AUDIT_SNAPSHOT_FIELDS:
            value = getattr(profile, field_name, None)
            snapshot[field_name] = value.isoformat() if isinstance(value, (date, datetime)) else value
        return snapshot

    def _record_action(
        self,
        profile: TalentProfile,
        *,
        actor: User | None,
        action: ModerationAction,
        reason: str | None,
        before: dict[str, Any],
    ) -> TalentModerationAction:
        entry = TalentModerationAction(
            profile_id=profile.id,
            player_id=profile.player_id,
            actor_user_id=getattr(actor, "id", None),
            action=action.value,
            reason=reason,
            before_json=before,
            after_json=self._snapshot(profile),
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def admin_view(self, player_id: str) -> dict[str, Any]:
        profile = self._profile(player_id)
        return privacy.project_profile(
            profile,
            scope=ViewerScope.ADMIN,
            signal_payloads=self.exchange.latest_signal_payloads(player_id),
        )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def record_verification(
        self,
        player_id: str,
        *,
        actor: User,
        tier: VerificationTier,
        decision: VerificationDecision = VerificationDecision.GRANTED,
        evidence_kind: str | None = None,
        evidence_reference: str | None = None,
        expires_at: date | None = None,
        reviewer_notes: str | None = None,
    ) -> TalentProfile:
        profile = self._profile(player_id)
        before = self._snapshot(profile)

        record = TalentVerificationRecord(
            profile_id=profile.id,
            player_id=profile.player_id,
            tier=tier.value,
            decision=decision.value,
            evidence_kind=evidence_kind,
            evidence_reference=evidence_reference,
            decided_by_user_id=actor.id,
            decided_at=_utcnow(),
            expires_at=(
                datetime.combine(expires_at, datetime.min.time(), tzinfo=timezone.utc)
                if expires_at is not None
                else None
            ),
            reviewer_notes=reviewer_notes,
        )
        self.session.add(record)
        self.session.flush()

        history = list(
            self.session.execute(
                select(TalentVerificationRecord).where(TalentVerificationRecord.player_id == profile.player_id)
            ).scalars()
        )
        profile.verification_tier = resolve_effective_tier(history)
        profile.verification_reviewed_at = record.decided_at
        profile.verification_expires_at = record.expires_at if decision is VerificationDecision.GRANTED else None
        self.session.flush()

        # The credentials component feeds the composite score, so a verification
        # change must be reflected in the ranking immediately rather than
        # waiting for the next scheduled recompute.
        self.exchange.recompute_ranking(profile.player_id)

        action = (
            ModerationAction.VERIFY
            if decision is VerificationDecision.GRANTED
            else ModerationAction.REVOKE_VERIFICATION
        )
        self._record_action(profile, actor=actor, action=action, reason=reviewer_notes, before=before)
        return profile

    def verification_history(self, player_id: str) -> dict[str, Any]:
        profile = self._profile(player_id)
        records = list(
            self.session.execute(
                select(TalentVerificationRecord)
                .where(TalentVerificationRecord.player_id == player_id)
                .order_by(TalentVerificationRecord.created_at.desc())
            ).scalars()
        )
        return {
            "player_id": player_id,
            "current_tier": profile.verification_tier,
            "records": [
                {
                    "id": record.id,
                    "tier": record.tier,
                    "decision": record.decision,
                    "evidence_kind": record.evidence_kind,
                    "evidence_reference": record.evidence_reference,
                    "decided_by_user_id": record.decided_by_user_id,
                    "decided_at": record.decided_at.isoformat() if record.decided_at else None,
                    "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                    "reviewer_notes": record.reviewer_notes,
                }
                for record in records
            ],
        }

    # ------------------------------------------------------------------
    # Visibility / moderation
    # ------------------------------------------------------------------

    def set_visibility(
        self,
        player_id: str,
        *,
        actor: User,
        visibility_state: VisibilityState,
        reason: str | None = None,
    ) -> TalentProfile:
        profile = self._profile(player_id)
        before = self._snapshot(profile)
        profile.visibility_state = visibility_state.value
        if visibility_state is VisibilityState.SUSPENDED:
            if not reason:
                raise TalentValidationError("A suspension requires a reason.")
            profile.suspension_reason = reason
        elif visibility_state is VisibilityState.PUBLISHED:
            profile.suspension_reason = None
        self.session.flush()

        action = {
            VisibilityState.PUBLISHED: ModerationAction.PUBLISH,
            VisibilityState.HIDDEN: ModerationAction.HIDE,
            VisibilityState.SUSPENDED: ModerationAction.SUSPEND,
            VisibilityState.DRAFT: ModerationAction.HIDE,
        }[visibility_state]
        self._record_action(profile, actor=actor, action=action, reason=reason, before=before)
        return profile

    def moderate(
        self,
        player_id: str,
        *,
        actor: User,
        action: ModerationAction,
        moderation_state: ModerationState | None = None,
        reason: str | None = None,
        internal_notes: str | None = None,
    ) -> TalentProfile:
        profile = self._profile(player_id)
        before = self._snapshot(profile)

        if action is ModerationAction.FLAG:
            profile.moderation_state = (moderation_state or ModerationState.FLAGGED).value
        elif action is ModerationAction.CLEAR_FLAG:
            profile.moderation_state = ModerationState.CLEAR.value
        elif action is ModerationAction.SUSPEND:
            if not reason:
                raise TalentValidationError("A suspension requires a reason.")
            profile.visibility_state = VisibilityState.SUSPENDED.value
            profile.moderation_state = (moderation_state or ModerationState.RESTRICTED).value
            profile.suspension_reason = reason
        elif action is ModerationAction.RESTORE:
            profile.visibility_state = VisibilityState.PUBLISHED.value
            profile.moderation_state = (moderation_state or ModerationState.CLEAR).value
            profile.suspension_reason = None
        elif moderation_state is not None:
            profile.moderation_state = moderation_state.value
        else:
            raise TalentValidationError(f"Action '{action.value}' requires a moderation_state.")

        if internal_notes is not None:
            profile.internal_notes = internal_notes
        self.session.flush()
        self._record_action(profile, actor=actor, action=action, reason=reason, before=before)
        return profile

    def set_featured(
        self,
        player_id: str,
        *,
        actor: User,
        is_featured: bool,
        featured_rank: int | None = None,
        reason: str | None = None,
    ) -> TalentProfile:
        profile = self._profile(player_id)
        before = self._snapshot(profile)
        if is_featured and profile.visibility_state != VisibilityState.PUBLISHED.value:
            raise TalentValidationError("Only a published profile can be featured.")
        profile.is_featured = is_featured
        profile.featured_rank = featured_rank if is_featured else None
        self.session.flush()
        self._record_action(
            profile,
            actor=actor,
            action=ModerationAction.FEATURE if is_featured else ModerationAction.UNFEATURE,
            reason=reason,
            before=before,
        )
        return profile

    # ------------------------------------------------------------------
    # Correction
    # ------------------------------------------------------------------

    def correct(
        self,
        player_id: str,
        *,
        actor: User,
        corrections: Mapping[str, Any],
        reason: str | None = None,
    ) -> TalentProfile:
        """Apply a factual correction and re-derive the ranking from it.

        Corrected fields are recorded in `metadata_json['manual_fields']` so a
        later ingestion sync does not silently overwrite a human decision.
        """

        profile = self._profile(player_id)
        before = self._snapshot(profile)
        metadata = dict(profile.metadata_json or {})
        manual_fields = set(str(item) for item in metadata.get("manual_fields", []))
        touched = False

        for field_name, payload_key in CORRECTABLE_SCALAR_FIELDS.items():
            if payload_key not in corrections:
                continue
            setattr(profile, field_name, corrections[payload_key])
            manual_fields.add(field_name)
            touched = True

        if "secondary_positions" in corrections:
            profile.secondary_positions_json = list(corrections["secondary_positions"] or [])
            manual_fields.add("secondary_positions_json")
            touched = True
        if "tactical_roles" in corrections:
            profile.tactical_roles_json = list(corrections["tactical_roles"] or [])
            manual_fields.add("tactical_roles_json")
            touched = True
        if "availability_status" in corrections and corrections["availability_status"] is not None:
            value = corrections["availability_status"]
            profile.availability_status = getattr(value, "value", value)
            manual_fields.add("availability_status")
            touched = True

        for attribute_field, payload_key in (
            ("technical_attributes_json", "technical_attributes"),
            ("tactical_attributes_json", "tactical_attributes"),
            ("physical_attributes_json", "physical_attributes"),
        ):
            if payload_key not in corrections or corrections[payload_key] is None:
                continue
            cleaned = normalise_attributes(corrections[payload_key])
            if not cleaned and corrections[payload_key]:
                raise TalentValidationError(f"No recognised attribute keys supplied for '{payload_key}'.")
            setattr(profile, attribute_field, cleaned)
            manual_fields.add(attribute_field)
            touched = True

        if not touched:
            raise TalentValidationError("No correctable fields were supplied.")

        if "date_of_birth" in corrections and corrections["date_of_birth"] is not None:
            birth_date = corrections["date_of_birth"]
            reference = self.exchange.today
            years = reference.year - birth_date.year
            if (reference.month, reference.day) < (birth_date.month, birth_date.day):
                years -= 1
            profile.age_years = max(0, years)
            manual_fields.add("age_years")

        metadata["manual_fields"] = sorted(manual_fields)
        profile.metadata_json = metadata
        self.exchange.refresh_indexes(profile)
        self.session.flush()

        self.exchange.recompute_ranking(profile.player_id)
        self._record_action(profile, actor=actor, action=ModerationAction.CORRECT, reason=reason, before=before)
        return profile

    # ------------------------------------------------------------------
    # Pipeline + audit
    # ------------------------------------------------------------------

    def recompute(self, player_id: str, *, as_of: date | None = None) -> dict[str, Any]:
        result = self.exchange.recompute_ranking(player_id, as_of=as_of)
        return result.as_payload()

    def moderation_log(self, player_id: str, *, limit: int = 100) -> dict[str, Any]:
        bounded = max(1, min(int(limit), 500))
        entries = list(
            self.session.execute(
                select(TalentModerationAction)
                .where(TalentModerationAction.player_id == player_id)
                .order_by(TalentModerationAction.created_at.desc())
                .limit(bounded)
            ).scalars()
        )
        return {
            "player_id": player_id,
            "entries": [
                {
                    "id": entry.id,
                    "action": entry.action,
                    "reason": entry.reason,
                    "actor_user_id": entry.actor_user_id,
                    "created_at": entry.created_at.isoformat(),
                    "before": dict(entry.before_json or {}),
                    "after": dict(entry.after_json or {}),
                }
                for entry in entries
            ],
        }

    def sync_from_player(self, player_id: str, *, owner_user_id: str | None = None) -> TalentProfile:
        try:
            return self.exchange.sync_profile_from_player(player_id, owner_user_id=owner_user_id)
        except TalentNotFoundError:
            raise


__all__ = [
    "AUDIT_SNAPSHOT_FIELDS",
    "CORRECTABLE_SCALAR_FIELDS",
    "TalentAdminService",
    "resolve_effective_tier",
]
