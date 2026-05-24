from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.models.hosted_competition import (
    CompetitionTemplate,
    HostedCompetitionSettlement,
    HostedCompetitionSettlementStatus,
    HostedCompetitionStanding,
    HostedCompetitionStatus,
    UserHostedCompetition,
    UserHostedCompetitionParticipant,
)
from app.models.user import User, UserRole
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.story_feed_engine.service import StoryFeedService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

DEFAULT_TEMPLATES: tuple[dict[str, object], ...] = (
    {
        "template_key": "user-hosted-cup-8",
        "title": "User Hosted Cup",
        "description": "An 8-team knockout cup for creator leagues and community rivalries.",
        "competition_type": "user_hosted_cup",
        "team_type": "club",
        "age_grade": "senior",
        "cup_or_league": "cup",
        "participants": 8,
        "viewing_mode": "broadcast",
        "gift_rules": {"enabled": True},
        "seeding_method": "random",
        "is_user_hostable": True,
        "entry_fee_fancoin": Decimal("250.0000"),
        "reward_pool_fancoin": Decimal("1600.0000"),
        "platform_fee_bps": 1000,
        "metadata_json": {"family": "creator"},
        "active": True,
    },
    {
        "template_key": "user-hosted-league-10",
        "title": "User Hosted League",
        "description": "A 10-team league format for creator communities and fan-organized ladders.",
        "competition_type": "user_hosted_league",
        "team_type": "club",
        "age_grade": "senior",
        "cup_or_league": "league",
        "participants": 10,
        "viewing_mode": "broadcast",
        "gift_rules": {"enabled": True},
        "seeding_method": "snake",
        "is_user_hostable": True,
        "entry_fee_fancoin": Decimal("300.0000"),
        "reward_pool_fancoin": Decimal("2400.0000"),
        "platform_fee_bps": 1000,
        "metadata_json": {"family": "creator"},
        "active": True,
    },
    {
        "template_key": "queue-cup",
        "title": "Queue Cup",
        "description": "Quick-fill queue cup with smaller entry and fast lock window.",
        "competition_type": "queue_cup",
        "team_type": "club",
        "age_grade": "senior",
        "cup_or_league": "cup",
        "participants": 4,
        "viewing_mode": "quick",
        "gift_rules": {"enabled": True},
        "seeding_method": "random",
        "is_user_hostable": True,
        "entry_fee_fancoin": Decimal("100.0000"),
        "reward_pool_fancoin": Decimal("320.0000"),
        "platform_fee_bps": 2000,
        "metadata_json": {"family": "queue"},
        "active": True,
    },
)

AMOUNT_QUANTUM = Decimal("0.0001")


class HostedCompetitionError(ValueError):
    pass


@dataclass(slots=True)
class HostedCompetitionService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def _normalize_amount(self, amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _is_admin_user(self, user: User) -> bool:
        return user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}

    def _require_host_or_admin(self, *, competition: UserHostedCompetition, actor: User) -> None:
        if competition.host_user_id == actor.id or self._is_admin_user(actor):
            return
        raise HostedCompetitionError("Only the host or an admin can manage hosted competition invites.")

    def _metadata_with_join_rules(self, *, payload, visibility: str, gtex_hosted: bool = False) -> dict[str, object]:
        metadata = dict(getattr(payload, "metadata_json", {}) or {})
        passcode = str(getattr(payload, "join_passcode", "") or "").strip()
        if passcode:
            metadata["join_passcode"] = passcode
            metadata["join_passcode_required"] = True
            if visibility == "public":
                visibility = "passcode"
        else:
            metadata.pop("join_passcode", None)
            metadata.setdefault("join_passcode_required", False)
        if gtex_hosted:
            metadata["host_type"] = "gtex_hosted"
            metadata["gtex_hosted"] = True
        else:
            metadata.setdefault("host_type", "user_hosted")
        return metadata

    def _requires_passcode(self, competition: UserHostedCompetition) -> bool:
        metadata = competition.metadata_json or {}
        if str(metadata.get("join_passcode") or "").strip():
            return True
        if bool(metadata.get("join_passcode_required")):
            return True
        return competition.visibility.strip().lower() in {"passcode", "password"}

    def _assert_passcode_allowed(
        self,
        *,
        competition: UserHostedCompetition,
        user: User,
        passcode: str | None,
        invite_required_bypass: bool,
    ) -> None:
        if not self._requires_passcode(competition):
            return
        if competition.host_user_id == user.id or self._is_admin_user(user) or invite_required_bypass:
            return
        expected = str((competition.metadata_json or {}).get("join_passcode") or "").strip()
        supplied = str(passcode or "").strip()
        if not expected or supplied != expected:
            raise HostedCompetitionError("A valid competition passcode is required to join.")

    def _invite_rows(self, competition: UserHostedCompetition) -> list[dict[str, object]]:
        rows = (competition.metadata_json or {}).get("invites")
        if not isinstance(rows, list):
            return []
        normalized: list[dict[str, object]] = []
        for row in rows:
            if isinstance(row, dict):
                normalized.append(dict(row))
        return normalized

    def _set_invite_rows(self, competition: UserHostedCompetition, rows: list[dict[str, object]]) -> None:
        competition.metadata_json = {**(competition.metadata_json or {}), "invites": rows}
        self.session.flush()

    def _invite_matches_user(self, invite: dict[str, object], user: User) -> bool:
        recipient_user_id = str(invite.get("recipient_user_id") or "").strip()
        if recipient_user_id and recipient_user_id == user.id:
            return True
        recipient_email = str(invite.get("recipient_email") or "").strip().lower()
        return bool(recipient_email and recipient_email == user.email.strip().lower())

    def _participant_for_user(
        self,
        *,
        competition: UserHostedCompetition,
        user: User,
    ) -> UserHostedCompetitionParticipant | None:
        return self.session.scalar(
            select(UserHostedCompetitionParticipant).where(
                UserHostedCompetitionParticipant.competition_id == competition.id,
                UserHostedCompetitionParticipant.user_id == user.id,
            )
        )

    def _find_join_invite(
        self,
        *,
        competition: UserHostedCompetition,
        user: User,
        invite_id: str | None = None,
    ) -> dict[str, object] | None:
        for invite in self._invite_rows(competition):
            if invite_id and str(invite.get("invite_id") or "") != invite_id:
                continue
            if not self._invite_matches_user(invite, user):
                continue
            if str(invite.get("status") or "").lower() in {"pending", "accepted"}:
                return invite
        return None

    def _mark_invite_status(
        self,
        *,
        competition: UserHostedCompetition,
        invite_id: str,
        status: str,
    ) -> dict[str, object]:
        rows = self._invite_rows(competition)
        for index, invite in enumerate(rows):
            if str(invite.get("invite_id") or "") != invite_id:
                continue
            updated = {
                **invite,
                "status": status,
                "responded_at": self._now_iso(),
            }
            rows[index] = updated
            self._set_invite_rows(competition, rows)
            return updated
        raise HostedCompetitionError("Hosted competition invite was not found.")

    def _invite_visible_to_actor(self, invite: dict[str, object], actor: User) -> bool:
        return self._invite_matches_user(invite, actor)

    def _invite_payload(self, competition: UserHostedCompetition, invite: dict[str, object]) -> dict[str, object]:
        return {
            "competition_id": competition.id,
            "invite_id": str(invite.get("invite_id") or ""),
            "invited_by_user_id": str(invite.get("invited_by_user_id") or ""),
            "recipient_user_id": invite.get("recipient_user_id"),
            "recipient_email": invite.get("recipient_email"),
            "status": str(invite.get("status") or "pending"),
            "message": str(invite.get("message") or ""),
            "created_at": invite.get("created_at") or self._now_iso(),
            "responded_at": invite.get("responded_at"),
        }

    def seed_defaults(self) -> None:
        existing = {item.template_key for item in self.session.scalars(select(CompetitionTemplate)).all()}
        for payload in DEFAULT_TEMPLATES:
            if payload["template_key"] in existing:
                continue
            self.session.add(CompetitionTemplate(**payload))
        self.session.flush()

    def list_templates(self) -> list[CompetitionTemplate]:
        stmt = (
            select(CompetitionTemplate)
            .where(CompetitionTemplate.active.is_(True))
            .order_by(CompetitionTemplate.title.asc())
        )
        return list(self.session.scalars(stmt).all())

    def get_template_by_key(self, template_key: str) -> CompetitionTemplate | None:
        return self.session.scalar(
            select(CompetitionTemplate).where(
                CompetitionTemplate.template_key == template_key, CompetitionTemplate.active.is_(True)
            )
        )

    def _active_platform_fee_bps(self) -> int:
        rule = next(iter(AdminEngineService(self.session).list_reward_rules(active_only=True)), None)
        return int(rule.competition_platform_fee_bps if rule is not None else 1000)

    def _competition_escrow_account(self, competition: UserHostedCompetition) -> LedgerAccount:
        code = f"competition:{competition.id}:credit:escrow"
        account = self.session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"{competition.title} Competition Escrow",
                unit=LedgerUnit.CREDIT,
                kind=LedgerAccountKind.ESCROW,
            )
            self.session.add(account)
            self.session.flush()
        return account

    def _available_escrow_balance(self, competition: UserHostedCompetition) -> Decimal:
        return self.wallet_service.get_balance(self.session, self._competition_escrow_account(competition))

    def _create_entry_participant(
        self, *, competition: UserHostedCompetition, user: User, role: str
    ) -> UserHostedCompetitionParticipant:
        participant = UserHostedCompetitionParticipant(
            competition_id=competition.id,
            user_id=user.id,
            entry_fee_fancoin=competition.entry_fee_fancoin,
            metadata_json={"role": role},
        )
        self.session.add(participant)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise HostedCompetitionError("User has already joined this competition.") from exc
        return participant

    def _collect_entry_fee(
        self, *, competition: UserHostedCompetition, participant: UserHostedCompetitionParticipant, user: User
    ) -> None:
        amount = self._normalize_amount(competition.entry_fee_fancoin)
        if amount <= Decimal("0.0000"):
            participant.metadata_json = {**participant.metadata_json, "payment_status": "free"}
            self.session.flush()
            return
        user_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.CREDIT)
        escrow_account = self._competition_escrow_account(competition)
        if self.wallet_service.get_balance(self.session, user_account) < amount:
            raise InsufficientBalanceError("Available FanCoin balance is lower than the hosted competition entry fee.")
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=user_account, amount=-amount, source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND
                ),
                LedgerPosting(
                    account=escrow_account, amount=amount, source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            reference=f"hosted-entry:{competition.id}:{user.id}",
            description=f"Hosted competition entry for {competition.title}",
            external_reference=f"hosted-entry:{competition.id}:{user.id}",
            actor=user,
        )
        participant.metadata_json = {
            **participant.metadata_json,
            "payment_status": "settled",
            "entry_transaction_id": entries[0].transaction_id if entries else None,
        }
        self.session.flush()

    def _fund_gtex_hosted_reward_pool(self, *, competition: UserHostedCompetition, admin: User) -> None:
        amount = self._normalize_amount(competition.reward_pool_fancoin)
        if amount <= Decimal("0.0000"):
            return
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        escrow_account = self._competition_escrow_account(competition)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=platform_account,
                    amount=-amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                ),
                LedgerPosting(
                    account=escrow_account,
                    amount=amount,
                    source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
                ),
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            reference=f"gtex-hosted-reward-pool:{competition.id}",
            description=f"GTEX hosted reward pool funding for {competition.title}",
            external_reference=f"gtex-hosted-reward-pool:{competition.id}",
            actor=admin,
            idempotency_key=f"gtex-hosted-reward-pool:{competition.id}",
            metadata={"hosted_competition_id": competition.id, "reward_source": "gtex_hosted_reward_pool"},
        )
        self.session.flush()

    def create_competition(
        self,
        *,
        host: User,
        payload,
        created_by_admin: User | None = None,
        gtex_hosted: bool = False,
    ) -> tuple[UserHostedCompetition, CompetitionTemplate, bool]:
        template = self.get_template_by_key(payload.template_key)
        if template is None or not template.is_user_hostable:
            raise HostedCompetitionError("Competition template was not found or is not hostable.")
        slug = (payload.slug or payload.title).strip().lower().replace(" ", "-")
        if not slug:
            raise HostedCompetitionError("Competition slug cannot be empty.")
        entry_fee = Decimal(
            str(payload.entry_fee_fancoin if payload.entry_fee_fancoin is not None else template.entry_fee_fancoin)
        ).quantize(Decimal("0.0001"))
        if gtex_hosted:
            entry_fee = Decimal("0.0000")
        if entry_fee < Decimal("0.0000"):
            raise HostedCompetitionError("Entry fee cannot be negative.")
        max_participants = int(payload.max_participants or template.participants)
        platform_fee_bps = self._active_platform_fee_bps()
        capacity_revenue = entry_fee * Decimal(max_participants)
        platform_fee_amount = (capacity_revenue * Decimal(platform_fee_bps) / Decimal(10_000)).quantize(
            Decimal("0.0001")
        )
        default_reward_pool = max(
            Decimal("0.0000"), (capacity_revenue - platform_fee_amount).quantize(Decimal("0.0001"))
        )
        reward_pool = Decimal(
            str(
                payload.reward_pool_fancoin
                if getattr(payload, "reward_pool_fancoin", None) is not None
                else default_reward_pool
            )
        ).quantize(Decimal("0.0001"))
        if reward_pool < Decimal("0.0000"):
            raise HostedCompetitionError("Reward pool cannot be negative.")
        visibility = str(payload.visibility or "public").strip().lower()
        metadata = self._metadata_with_join_rules(payload=payload, visibility=visibility, gtex_hosted=gtex_hosted)
        if metadata.get("join_passcode_required") is True and visibility == "public":
            visibility = "passcode"
        competition = UserHostedCompetition(
            template_id=template.id,
            host_user_id=host.id,
            title=payload.title,
            slug=slug,
            description=payload.description,
            visibility=visibility,
            starts_at=payload.starts_at,
            lock_at=payload.lock_at,
            max_participants=max_participants,
            entry_fee_fancoin=entry_fee,
            reward_pool_fancoin=reward_pool,
            platform_fee_amount=platform_fee_amount,
            metadata_json={
                **metadata,
                "created_by_user_id": created_by_admin.id if created_by_admin is not None else host.id,
            },
            status=HostedCompetitionStatus.OPEN,
        )
        self.session.add(competition)
        self.session.flush()
        if gtex_hosted:
            if created_by_admin is not None:
                self._fund_gtex_hosted_reward_pool(competition=competition, admin=created_by_admin)
            return competition, template, False
        participant = self._create_entry_participant(competition=competition, user=host, role="host")
        try:
            self._collect_entry_fee(competition=competition, participant=participant, user=host)
        except InsufficientBalanceError as exc:
            raise HostedCompetitionError(str(exc)) from exc
        return competition, template, True

    def create_admin_competition(
        self, *, admin: User, payload
    ) -> tuple[UserHostedCompetition, CompetitionTemplate, bool]:
        if not self._is_admin_user(admin):
            raise HostedCompetitionError("Only admins can create GTEX hosted competitions.")
        host = admin
        host_user_id = str(getattr(payload, "host_user_id", "") or "").strip()
        gtex_hosted = bool(getattr(payload, "gtex_hosted", True))
        if host_user_id:
            resolved_host = self.session.get(User, host_user_id)
            if resolved_host is None:
                raise HostedCompetitionError("Host user was not found.")
            host = resolved_host
        return self.create_competition(
            host=host,
            payload=payload,
            created_by_admin=admin,
            gtex_hosted=gtex_hosted,
        )

    def list_public_competitions(self) -> list[UserHostedCompetition]:
        stmt = (
            select(UserHostedCompetition)
            .where(UserHostedCompetition.visibility.in_(("public", "passcode")))
            .order_by(UserHostedCompetition.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_for_host(self, *, user: User) -> list[UserHostedCompetition]:
        stmt = (
            select(UserHostedCompetition)
            .where(UserHostedCompetition.host_user_id == user.id)
            .order_by(UserHostedCompetition.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_competition(self, competition_id: str) -> UserHostedCompetition | None:
        return self.session.get(UserHostedCompetition, competition_id)

    def participants_for_competition(self, competition_id: str) -> list[UserHostedCompetitionParticipant]:
        stmt = (
            select(UserHostedCompetitionParticipant)
            .where(UserHostedCompetitionParticipant.competition_id == competition_id)
            .order_by(UserHostedCompetitionParticipant.joined_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def invites_for_competition(self, *, actor: User, competition_id: str) -> list[dict[str, object]]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        rows = self._invite_rows(competition)
        if competition.host_user_id == actor.id or self._is_admin_user(actor):
            return [self._invite_payload(competition, row) for row in rows]
        return [self._invite_payload(competition, row) for row in rows if self._invite_visible_to_actor(row, actor)]

    def invites_for_user(self, *, user: User) -> list[dict[str, object]]:
        stmt = select(UserHostedCompetition).order_by(UserHostedCompetition.created_at.desc())
        invites: list[dict[str, object]] = []
        for competition in self.session.scalars(stmt).all():
            for invite in self._invite_rows(competition):
                if self._invite_visible_to_actor(invite, user):
                    invites.append(self._invite_payload(competition, invite))
        return invites

    def create_invites(
        self,
        *,
        actor: User,
        competition_id: str,
        recipient_user_ids: Iterable[str],
        recipient_emails: Iterable[str],
        message: str = "",
    ) -> tuple[UserHostedCompetition, list[dict[str, object]]]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        self._require_host_or_admin(competition=competition, actor=actor)
        if competition.status in {HostedCompetitionStatus.COMPLETED, HostedCompetitionStatus.CANCELLED}:
            raise HostedCompetitionError("Hosted competition is not accepting invites.")

        rows = self._invite_rows(competition)
        active_keys = {
            (
                str(row.get("recipient_user_id") or "").strip(),
                str(row.get("recipient_email") or "").strip().lower(),
            )
            for row in rows
            if str(row.get("status") or "").lower() in {"pending", "accepted"}
        }
        created: list[dict[str, object]] = []
        normalized_user_ids = [item.strip() for item in recipient_user_ids if item and item.strip()]
        normalized_emails = [item.strip().lower() for item in recipient_emails if item and item.strip()]
        if not normalized_user_ids and not normalized_emails:
            raise HostedCompetitionError("At least one invite recipient is required.")
        for recipient_user_id in dict.fromkeys(normalized_user_ids):
            key = (recipient_user_id, "")
            if key in active_keys:
                continue
            invite = {
                "invite_id": str(uuid4()),
                "invited_by_user_id": actor.id,
                "recipient_user_id": recipient_user_id,
                "recipient_email": None,
                "status": "pending",
                "message": message,
                "created_at": self._now_iso(),
                "responded_at": None,
            }
            rows.append(invite)
            created.append(invite)
            active_keys.add(key)
        for recipient_email in dict.fromkeys(normalized_emails):
            key = ("", recipient_email)
            if key in active_keys:
                continue
            invite = {
                "invite_id": str(uuid4()),
                "invited_by_user_id": actor.id,
                "recipient_user_id": None,
                "recipient_email": recipient_email,
                "status": "pending",
                "message": message,
                "created_at": self._now_iso(),
                "responded_at": None,
            }
            rows.append(invite)
            created.append(invite)
            active_keys.add(key)
        self._set_invite_rows(competition, rows)
        return competition, [self._invite_payload(competition, row) for row in created]

    def accept_invite(
        self,
        *,
        user: User,
        competition_id: str,
        invite_id: str | None = None,
    ) -> tuple[UserHostedCompetition, UserHostedCompetitionParticipant, dict[str, object]]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        invite = self._find_join_invite(competition=competition, user=user, invite_id=invite_id)
        if invite is None:
            raise HostedCompetitionError("No pending hosted competition invite was found for this user.")
        participant = self._participant_for_user(competition=competition, user=user)
        if participant is None:
            competition, participant = self.join_competition(
                user=user,
                competition_id=competition_id,
                invite_required_bypass=True,
            )
        accepted = self._mark_invite_status(
            competition=competition,
            invite_id=str(invite.get("invite_id") or ""),
            status="accepted",
        )
        return competition, participant, self._invite_payload(competition, accepted)

    def standings_for_competition(self, competition_id: str) -> list[HostedCompetitionStanding]:
        stmt = (
            select(HostedCompetitionStanding)
            .where(HostedCompetitionStanding.competition_id == competition_id)
            .order_by(
                HostedCompetitionStanding.final_rank.asc().nullslast(), HostedCompetitionStanding.created_at.asc()
            )
        )
        return list(self.session.scalars(stmt).all())

    def settlements_for_competition(self, competition_id: str) -> list[HostedCompetitionSettlement]:
        stmt = (
            select(HostedCompetitionSettlement)
            .where(HostedCompetitionSettlement.competition_id == competition_id)
            .order_by(HostedCompetitionSettlement.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def finance_snapshot(self, competition_id: str) -> dict[str, Decimal | int | str]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        participants = self.participants_for_competition(competition_id)
        escrow_balance = self._available_escrow_balance(competition)
        settled_prizes = self._normalize_amount(
            self.session.scalar(
                select(func.coalesce(func.sum(HostedCompetitionSettlement.net_amount), 0)).where(
                    HostedCompetitionSettlement.competition_id == competition_id,
                    HostedCompetitionSettlement.settlement_type == "prize",
                )
            )
            or 0
        )
        platform_fee_settled = self._normalize_amount(
            self.session.scalar(
                select(func.coalesce(func.sum(HostedCompetitionSettlement.net_amount), 0)).where(
                    HostedCompetitionSettlement.competition_id == competition_id,
                    HostedCompetitionSettlement.settlement_type == "platform_fee",
                )
            )
            or 0
        )
        return {
            "currency": "fan_coin",
            "participant_count": len(participants),
            "entry_fee_fancoin": self._normalize_amount(competition.entry_fee_fancoin),
            "gross_collected": self._normalize_amount(competition.entry_fee_fancoin * Decimal(len(participants))),
            "projected_reward_pool": self._normalize_amount(competition.reward_pool_fancoin),
            "projected_platform_fee": self._normalize_amount(competition.platform_fee_amount),
            "escrow_balance": escrow_balance,
            "settled_prizes": settled_prizes,
            "settled_platform_fee": platform_fee_settled,
            "status": competition.status.value if hasattr(competition.status, "value") else str(competition.status),
        }

    def join_competition(
        self,
        *,
        user: User,
        competition_id: str,
        passcode: str | None = None,
        invite_required_bypass: bool = False,
    ) -> tuple[UserHostedCompetition, UserHostedCompetitionParticipant]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        if competition.status not in {HostedCompetitionStatus.OPEN, HostedCompetitionStatus.DRAFT}:
            raise HostedCompetitionError("Hosted competition is not open for joining.")
        invite = self._find_join_invite(competition=competition, user=user)
        self._assert_passcode_allowed(
            competition=competition,
            user=user,
            passcode=passcode,
            invite_required_bypass=invite_required_bypass or invite is not None,
        )
        if (
            competition.visibility in {"private", "invite_only"}
            and competition.host_user_id != user.id
            and invite is None
            and not invite_required_bypass
        ):
            raise HostedCompetitionError("An invite is required to join this hosted competition.")
        current_participants = (
            self.session.scalar(
                select(func.count(UserHostedCompetitionParticipant.id)).where(
                    UserHostedCompetitionParticipant.competition_id == competition.id
                )
            )
            or 0
        )
        if int(current_participants) >= int(competition.max_participants):
            raise HostedCompetitionError("Hosted competition is already full.")
        participant = self._create_entry_participant(competition=competition, user=user, role="participant")
        try:
            self._collect_entry_fee(competition=competition, participant=participant, user=user)
        except InsufficientBalanceError as exc:
            self.session.delete(participant)
            self.session.flush()
            raise HostedCompetitionError(str(exc)) from exc
        updated_count = int(current_participants) + 1
        if updated_count >= int(competition.max_participants):
            competition.status = HostedCompetitionStatus.LOCKED
            self.session.flush()
        if invite is not None:
            self._mark_invite_status(
                competition=competition,
                invite_id=str(invite.get("invite_id") or ""),
                status="accepted",
            )
        return competition, participant

    def launch_competition(self, *, actor: User, competition_id: str) -> UserHostedCompetition:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        participants = self.participants_for_competition(competition_id)
        if len(participants) < 2:
            raise HostedCompetitionError("At least two participants are required before launch.")
        competition.status = HostedCompetitionStatus.LIVE
        existing = {row.user_id for row in self.standings_for_competition(competition_id)}
        for index, item in enumerate(participants, start=1):
            if item.user_id in existing:
                continue
            self.session.add(
                HostedCompetitionStanding(
                    competition_id=competition.id,
                    user_id=item.user_id,
                    final_rank=index,
                    metadata_json={"seed_order": index},
                )
            )
        StoryFeedService(self.session).publish(
            story_type="competition_launch",
            title=f"{competition.title} is live",
            body="Hosted competition moved into live mode and standings have been initialized.",
            audience="public",
            subject_type="hosted_competition",
            subject_id=competition.id,
            metadata_json={"competition_id": competition.id, "slug": competition.slug},
            published_by_user_id=actor.id,
        )
        self.session.flush()
        return competition

    def finalize_competition(
        self, *, actor: User, competition_id: str, placements: Iterable[dict[str, object]], note: str | None = None
    ) -> tuple[UserHostedCompetition, list[HostedCompetitionStanding], list[HostedCompetitionSettlement]]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        if competition.status == HostedCompetitionStatus.COMPLETED:
            raise HostedCompetitionError("Hosted competition has already been completed.")
        participants = {item.user_id for item in self.participants_for_competition(competition_id)}
        if not participants:
            raise HostedCompetitionError("Hosted competition has no participants.")
        escrow_account = self._competition_escrow_account(competition)
        escrow_balance = self.wallet_service.get_balance(self.session, escrow_account)
        if escrow_balance <= Decimal("0.0000"):
            raise HostedCompetitionError("Hosted competition escrow balance is empty.")
        platform_fee = min(self._normalize_amount(competition.platform_fee_amount), escrow_balance)
        prize_pool = self._normalize_amount(escrow_balance - platform_fee)
        placements = list(placements)
        if not placements:
            raise HostedCompetitionError("At least one placement is required to settle a hosted competition.")
        total_percent = sum(Decimal(str(item.get("payout_percent", 0))) for item in placements)
        if total_percent > Decimal("100.0000"):
            raise HostedCompetitionError("Total payout percent cannot exceed 100.")
        if prize_pool > Decimal("0.0000") and total_percent != Decimal("100.0000"):
            raise HostedCompetitionError("Total payout percent must equal 100 for competitions with a prize pool.")
        placement_user_ids = [str(item.get("user_id")) for item in placements]
        if len(set(placement_user_ids)) != len(placement_user_ids):
            raise HostedCompetitionError("Each placement must reference a distinct participant.")
        placement_ranks = [int(item.get("rank", 0) or 0) for item in placements]
        if len(set(placement_ranks)) != len(placement_ranks):
            raise HostedCompetitionError("Each placement rank must be unique.")
        expected_ranks = set(range(1, len(placement_ranks) + 1))
        if set(placement_ranks) != expected_ranks:
            raise HostedCompetitionError("Placement ranks must be contiguous starting at 1.")
        standings_by_user = {row.user_id: row for row in self.standings_for_competition(competition_id)}
        if not standings_by_user:
            for item in self.participants_for_competition(competition_id):
                row = HostedCompetitionStanding(competition_id=competition.id, user_id=item.user_id, metadata_json={})
                self.session.add(row)
                self.session.flush()
                standings_by_user[item.user_id] = row
        postings: list[LedgerPosting] = []
        settlements: list[HostedCompetitionSettlement] = []
        total_prize_paid = Decimal("0.0000")
        for item in placements:
            user_id = str(item["user_id"])
            if user_id not in participants:
                raise HostedCompetitionError("A placement referenced a user that is not part of this competition.")
            payout_percent = Decimal(str(item.get("payout_percent", 0)))
            rank = int(item.get("rank", 0) or 0)
            if payout_percent < Decimal("0.0000"):
                raise HostedCompetitionError("Payout percent cannot be negative.")
            payout_amount = self._normalize_amount(prize_pool * payout_percent / Decimal("100"))
            user = self.session.get(User, user_id)
            if user is None:
                raise HostedCompetitionError("A placement referenced a missing user.")
            recipient_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.CREDIT)
            postings.append(
                LedgerPosting(
                    account=recipient_account,
                    amount=payout_amount,
                    source_tag=LedgerSourceTag.USER_HOSTED_GIFT_INCOME_FANCOIN,
                )
            )
            total_prize_paid += payout_amount
            standing = standings_by_user[user_id]
            standing.final_rank = rank
            standing.payout_amount = payout_amount
            standing.metadata_json = {**(standing.metadata_json or {}), "payout_percent": str(payout_percent)}
            settlements.append(
                HostedCompetitionSettlement(
                    competition_id=competition.id,
                    recipient_user_id=user.id,
                    settlement_type="prize",
                    status=HostedCompetitionSettlementStatus.PENDING,
                    gross_amount=payout_amount,
                    platform_fee_amount=Decimal("0.0000"),
                    net_amount=payout_amount,
                    note=note or "",
                    settled_by_user_id=actor.id,
                )
            )
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        total_outgoing = self._normalize_amount(total_prize_paid + platform_fee)
        residual_amount = self._normalize_amount(escrow_balance - total_outgoing)
        if residual_amount > Decimal("0.0000"):
            platform_fee = self._normalize_amount(platform_fee + residual_amount)
        elif residual_amount < Decimal("0.0000"):
            raise HostedCompetitionError("Settlement exceeds available escrow balance.")
        if platform_fee > Decimal("0.0000"):
            postings.append(
                LedgerPosting(
                    account=platform_account,
                    amount=platform_fee,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                )
            )
        total_outgoing = self._normalize_amount(total_prize_paid + platform_fee)
        if total_outgoing > escrow_balance:
            raise HostedCompetitionError("Settlement exceeds available escrow balance.")
        if total_prize_paid > Decimal("0.0000"):
            postings.append(
                LedgerPosting(
                    account=escrow_account,
                    amount=-total_prize_paid,
                    source_tag=LedgerSourceTag.USER_HOSTED_GIFT_INCOME_FANCOIN,
                )
            )
        if platform_fee > Decimal("0.0000"):
            postings.append(
                LedgerPosting(
                    account=escrow_account,
                    amount=-platform_fee,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                )
            )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.COMPETITION_REWARD,
            reference=f"hosted-settlement:{competition.id}",
            description=f"Hosted competition settlement for {competition.title}",
            external_reference=f"hosted-settlement:{competition.id}",
            actor=actor,
        )
        transaction_id = entries[0].transaction_id if entries else None
        for settlement in settlements:
            settlement.status = HostedCompetitionSettlementStatus.SETTLED
            settlement.ledger_transaction_id = transaction_id
            self.session.add(settlement)
        fee_settlement = HostedCompetitionSettlement(
            competition_id=competition.id,
            recipient_user_id=None,
            settlement_type="platform_fee",
            status=HostedCompetitionSettlementStatus.SETTLED,
            gross_amount=platform_fee,
            platform_fee_amount=platform_fee,
            net_amount=platform_fee,
            ledger_transaction_id=transaction_id,
            note=note or "",
            settled_by_user_id=actor.id,
        )
        self.session.add(fee_settlement)
        settlements.append(fee_settlement)
        competition.status = HostedCompetitionStatus.COMPLETED
        StoryFeedService(self.session).publish(
            story_type="competition_result",
            title=f"{competition.title} completed",
            body="Hosted competition settlements have been posted and final standings are available.",
            audience="public",
            subject_type="hosted_competition",
            subject_id=competition.id,
            metadata_json={
                "competition_id": competition.id,
                "slug": competition.slug,
                "transaction_id": transaction_id,
            },
            published_by_user_id=actor.id,
        )
        self.session.flush()
        return competition, list(standings_by_user.values()), settlements
