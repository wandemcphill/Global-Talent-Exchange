from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import generate_uuid, utcnow
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerSourceTag, LedgerUnit, PaymentEvent, PaymentStatus, PayoutRequest, PayoutStatus
from app.players.read_models import PlayerSummaryReadModel
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService
from app.observability.audit_service import AuditTrailService

from .schemas import (
    AdminRoleCatalogUpdate,
    AdminRoleCatalogView,
    AuditEventView,
    AuditQueryView,
    CommissionSettingsUpdate,
    CommissionSettingsView,
    CompetitionControlUpdate,
    CompetitionControlView,
    GodModeBootstrapView,
    GodModeProfileView,
    HighRiskActionView,
    LiquidityInterventionRequest,
    LiquidityInterventionView,
    LiquidityInventoryView,
    PaymentRailHealthView,
    PaymentRailsUpdate,
    PaymentRailsPayload,
    PaymentRailView,
    TreasuryDashboardView,
    TreasurySummaryView,
    WithdrawalControlUpdate,
    WithdrawalControlView,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalView,
    TreasuryBalanceView,
    WithdrawalAdminView,
    WithdrawalStatusUpdate,
    WithdrawalSummaryView,
)

ADMIN_GODMODE_FILE = "admin_god_mode.json"
AUDIT_LOG_FILE = "admin_god_mode.audit.jsonl"

DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "god_mode": [
        "manage_admin_roles",
        "manage_commissions",
        "manage_payment_rails",
        "manage_withdrawals",
        "manage_treasury_withdrawals",
        "manage_liquidity_desk",
        "view_audit_log",
        "pause_payments",
        "view_integrity_controls",
    ],
    "finance_admin": [
        "manage_commissions",
        "manage_payment_rails",
        "manage_withdrawals",
        "manage_treasury_withdrawals",
        "view_audit_log",
    ],
    "market_ops_admin": [
        "manage_liquidity_desk",
        "view_audit_log",
        "view_integrity_controls",
    ],
    "support_admin": [
        "manage_withdrawals",
        "view_audit_log",
    ],
}

DEFAULT_PAYMENT_RAILS: list[dict[str, Any]] = [
    {
        "provider": "bank_transfer_manual",
        "deposits_enabled": True,
        "withdrawals_enabled": True,
        "is_live": True,
        "maintenance_message": "Manual bank-transfer desk is enabled.",
    },
    {
        "provider": "paystack",
        "deposits_enabled": True,
        "withdrawals_enabled": True,
        "is_live": True,
        "maintenance_message": None,
    },
    {
        "provider": "flutterwave",
        "deposits_enabled": True,
        "withdrawals_enabled": True,
        "is_live": True,
        "maintenance_message": None,
    },
    {
        "provider": "monnify",
        "deposits_enabled": True,
        "withdrawals_enabled": True,
        "is_live": True,
        "maintenance_message": None,
    },
]

DEFAULT_COMMISSION_SETTINGS: dict[str, Any] = {
    "buy_commission_bps": 150,
    "sell_commission_bps": 150,
    "instant_sell_fee_bps": 75,
    "withdrawal_fee_bps": 1000,
    "minimum_withdrawal_fee_credits": "5.0000",
    "updated_at": None,
    "updated_by": None,
    "reason": "Initial bounded admin policy.",
}

DEFAULT_WITHDRAWAL_CONTROLS: dict[str, Any] = {
    "egame_withdrawals_enabled": False,
    "trade_withdrawals_enabled": True,
    "processor_mode": "manual_bank_transfer",
    "deposits_via_bank_transfer": True,
    "payouts_via_bank_transfer": True,
    "updated_at": None,
    "updated_by": None,
    "reason": "Manual bank-transfer-first control baseline.",
}

DEFAULT_COMPETITION_CONTROLS: dict[str, Any] = {
    "prize_pool_topup_pct": "0.00",
    "updated_at": None,
    "updated_by": None,
    "reason": "No extra prize-pool top-up yet.",
}


class GodModeError(ValueError):
    pass


class PermissionDeniedError(GodModeError):
    pass


class IntegrityBoundError(GodModeError):
    pass


@dataclass(slots=True)
class AdminGodModeService:
    wallet_service: WalletService

    def load_bootstrap(self, app: FastAPI, session: Session, actor: User) -> GodModeBootstrapView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "view_audit_log")
        return GodModeBootstrapView(
            profile=profile,
            commissions=CommissionSettingsView.model_validate(state["commissions"]),
            payment_rails=[PaymentRailView.model_validate(item) for item in state["payment_rails"]],
            withdrawal_controls=WithdrawalControlView.model_validate(state.get("withdrawal_controls") or DEFAULT_WITHDRAWAL_CONTROLS),
            competition_controls=CompetitionControlView.model_validate(state.get("competition_controls") or DEFAULT_COMPETITION_CONTROLS),
            treasury=self.get_treasury_summary(app, session),
            withdrawals=self.list_withdrawals(session),
            withdrawal_summary=self.get_withdrawal_summary(app, session),
            payment_rail_health=self.get_payment_rail_health(app),
            treasury_dashboard=self.get_treasury_dashboard(app, session),
            high_risk_actions=self.list_high_risk_actions(app),
            audit_query=AuditQueryView(
                available_event_types=self.available_audit_event_types(app),
                limit=30,
            ),
            audit_events=self.list_audit_events(app),
        )

    def get_role_catalog(self, app: FastAPI) -> AdminRoleCatalogView:
        state = self._load_state(app)
        return AdminRoleCatalogView.model_validate(state["roles"])

    def update_role_catalog(self, app: FastAPI, actor: User, payload: AdminRoleCatalogUpdate) -> AdminRoleCatalogView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_admin_roles")
        state["roles"] = payload.model_dump(mode="json")
        self._save_state(app, state)
        self._append_audit(
            app,
            event_type="admin.roles.updated",
            actor=actor,
            summary="Updated admin role catalog and assignments.",
            payload=payload.model_dump(mode="json"),
        )
        return AdminRoleCatalogView.model_validate(state["roles"])

    def get_commissions(self, app: FastAPI) -> CommissionSettingsView:
        state = self._load_state(app)
        return CommissionSettingsView.model_validate(state["commissions"])

    def update_commissions(self, app: FastAPI, actor: User, payload: CommissionSettingsUpdate) -> CommissionSettingsView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_commissions")
        updated = payload.model_dump(mode="json")
        updated["updated_at"] = utcnow().isoformat()
        updated["updated_by"] = actor.id
        state["commissions"] = updated
        self._save_state(app, state)
        self._append_audit(
            app,
            event_type="admin.commissions.updated",
            actor=actor,
            summary="Updated bounded commission settings.",
            payload=updated,
        )
        with app.state.session_factory() as audit_session:
            self._log_admin_override(
                session=audit_session,
                actor=actor,
                action_key="admin.commissions.updated",
                detail="Commission settings override applied.",
                metadata={"reason": payload.reason},
            )
        return CommissionSettingsView.model_validate(updated)

    def get_payment_rails(self, app: FastAPI) -> PaymentRailsPayload:
        state = self._load_state(app)
        return PaymentRailsPayload(
            rails=[PaymentRailView.model_validate(item) for item in state["payment_rails"]],
        )

    def update_payment_rails(self, app: FastAPI, actor: User, payload: PaymentRailsUpdate) -> PaymentRailsPayload:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_payment_rails")
        now = utcnow().isoformat()
        updated_rails = []
        for item in payload.rails:
            record = item.model_dump(mode="json")
            record["updated_at"] = now
            record["updated_by"] = actor.id
            updated_rails.append(record)
        state["payment_rails"] = updated_rails
        self._save_state(app, state)
        self._append_audit(
            app,
            event_type="admin.payment_rails.updated",
            actor=actor,
            summary="Updated payment rail switches and maintenance messages.",
            payload={"rails": updated_rails, "reason": payload.reason},
        )
        with app.state.session_factory() as audit_session:
            self._log_admin_override(
                session=audit_session,
                actor=actor,
                action_key="admin.payment_rails.updated",
                detail="Payment rail switches updated.",
                metadata={"reason": payload.reason},
            )
        return PaymentRailsPayload(
            rails=[PaymentRailView.model_validate(item) for item in updated_rails],
            reason=payload.reason,
        )

    def get_withdrawal_controls(self, app: FastAPI) -> WithdrawalControlView:
        state = self._load_state(app)
        return WithdrawalControlView.model_validate(state.get("withdrawal_controls") or DEFAULT_WITHDRAWAL_CONTROLS)

    def update_withdrawal_controls(self, app: FastAPI, actor: User, payload: WithdrawalControlUpdate) -> WithdrawalControlView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_payment_rails")
        updated = payload.model_dump(mode="json")
        updated["updated_at"] = utcnow().isoformat()
        updated["updated_by"] = actor.id
        state["withdrawal_controls"] = updated
        self._save_state(app, state)
        self._append_audit(
            app,
            event_type="admin.withdrawal_controls.updated",
            actor=actor,
            summary="Updated withdrawal processor and e-game cash-out controls.",
            payload=updated,
        )
        with app.state.session_factory() as audit_session:
            self._log_admin_override(
                session=audit_session,
                actor=actor,
                action_key="admin.withdrawal_controls.updated",
                detail="Withdrawal controls updated.",
                metadata={"reason": payload.reason},
            )
        return WithdrawalControlView.model_validate(updated)

    def get_competition_controls(self, app: FastAPI) -> CompetitionControlView:
        state = self._load_state(app)
        return CompetitionControlView.model_validate(state.get("competition_controls") or DEFAULT_COMPETITION_CONTROLS)

    def update_competition_controls(self, app: FastAPI, actor: User, payload: CompetitionControlUpdate) -> CompetitionControlView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_commissions")
        updated = payload.model_dump(mode="json")
        updated["updated_at"] = utcnow().isoformat()
        updated["updated_by"] = actor.id
        state["competition_controls"] = updated
        self._save_state(app, state)
        self._append_audit(
            app,
            event_type="admin.competition_controls.updated",
            actor=actor,
            summary="Updated competition prize-pool controls.",
            payload=updated,
        )
        return CompetitionControlView.model_validate(updated)

    def get_treasury_summary(self, app: FastAPI, session: Session) -> TreasurySummaryView:
        platform_accounts = session.scalars(
            select(LedgerAccount)
            .where(LedgerAccount.code.like("platform:%"))
            .order_by(LedgerAccount.code.asc())
        ).all()
        balances = [
            TreasuryBalanceView(
                code=account.code,
                label=account.label,
                unit=account.unit.value,
                balance=self.wallet_service.get_balance(session, account),
            )
            for account in platform_accounts
        ]
        inventory_accounts = [
            account for account in platform_accounts if account.code.startswith("platform:position:")
        ]
        inventory = [
            LiquidityInventoryView(
                player_id=account.code.split(":")[2],
                balance=self.wallet_service.get_balance(session, account),
            )
            for account in inventory_accounts
        ]
        # SQLAlchemy count compatibility without relying on dialect-specific count helpers.
        verified_payment_count = len(
            session.scalars(select(PaymentEvent.id).where(PaymentEvent.status == PaymentStatus.VERIFIED)).all()
        )
        pending_payout_count = len(
            session.scalars(select(PayoutRequest.id).where(PayoutRequest.status.in_((PayoutStatus.REQUESTED, PayoutStatus.REVIEWING, PayoutStatus.HELD)))).all()
        )
        processing_payout_count = len(
            session.scalars(select(PayoutRequest.id).where(PayoutRequest.status == PayoutStatus.PROCESSING)).all()
        )
        return TreasurySummaryView(
            balances=balances,
            liquidity_inventory=inventory,
            pending_payout_count=pending_payout_count,
            processing_payout_count=processing_payout_count,
            verified_payment_count=verified_payment_count,
            recent_interventions=self._recent_interventions(app),
        )

    def get_withdrawal_summary(self, app: FastAPI, session: Session) -> WithdrawalSummaryView:
        requests = session.scalars(select(PayoutRequest)).all()
        counts = {status.value: 0 for status in PayoutStatus}
        queued_amount = Decimal("0.0000")
        for item in requests:
            counts[item.status.value] = counts.get(item.status.value, 0) + 1
            if item.status in {PayoutStatus.REQUESTED, PayoutStatus.REVIEWING, PayoutStatus.HELD, PayoutStatus.PROCESSING}:
                queued_amount += Decimal(item.amount)
        dashboard = self.get_treasury_dashboard(app, session)
        immediate = dashboard.immediate_withdrawable_manager_trade_credits
        return WithdrawalSummaryView(
            total_requests=len(requests),
            requested_count=counts.get("requested", 0),
            reviewing_count=counts.get("reviewing", 0),
            held_count=counts.get("held", 0),
            processing_count=counts.get("processing", 0),
            completed_count=counts.get("completed", 0),
            failed_count=counts.get("failed", 0),
            rejected_count=counts.get("rejected", 0),
            queued_amount=queued_amount.quantize(Decimal("0.0001")),
            immediate_eligible_amount=immediate,
            manager_trade_immediate_eligible_amount=immediate,
        )

    def get_payment_rail_health(self, app: FastAPI) -> PaymentRailHealthView:
        state = self._load_state(app)
        rails = list(state.get("payment_rails") or [])
        return PaymentRailHealthView(
            live_count=sum(1 for rail in rails if rail.get("is_live")),
            deposits_enabled_count=sum(1 for rail in rails if rail.get("deposits_enabled")),
            withdrawals_enabled_count=sum(1 for rail in rails if rail.get("withdrawals_enabled")),
            paused_providers=sorted(str(rail.get("provider")) for rail in rails if not rail.get("is_live")),
            maintenance_providers=sorted(str(rail.get("provider")) for rail in rails if rail.get("maintenance_message")),
        )

    def get_treasury_dashboard(self, app: FastAPI, session: Session) -> TreasuryDashboardView:
        manager_state = self._load_manager_market_state(app)
        platform_credit = self.wallet_service.get_balance(session, self.wallet_service.ensure_platform_account(session, LedgerUnit.CREDIT))
        platform_coin = self.wallet_service.get_balance(session, self.wallet_service.ensure_platform_account(session, LedgerUnit.COIN))
        sink_credit = self.wallet_service.get_balance(session, self._ensure_treasury_sink_account(session, LedgerUnit.CREDIT))
        sink_coin = self.wallet_service.get_balance(session, self._ensure_treasury_sink_account(session, LedgerUnit.COIN))
        trade_history = list(manager_state.get("trade_history") or [])
        gross_total = sum((Decimal(str(item.get("gross_credits") or 0)) for item in trade_history), Decimal("0.0000"))
        fee_total = sum((Decimal(str(item.get("fee_credits") or 0)) for item in trade_history), Decimal("0.0000"))
        immediate_total = sum((Decimal(str(item.get("seller_net_credits") or 0)) for item in trade_history if bool(item.get("immediate_withdrawal_eligible", True))), Decimal("0.0000"))
        return TreasuryDashboardView(
            platform_credit_balance=platform_credit,
            platform_coin_balance=platform_coin,
            treasury_withdrawal_sink_credit_balance=sink_credit,
            treasury_withdrawal_sink_coin_balance=sink_coin,
            manager_trade_volume_credits=gross_total.quantize(Decimal("0.0001")),
            manager_trade_fee_revenue_credits=fee_total.quantize(Decimal("0.0001")),
            immediate_withdrawable_manager_trade_credits=immediate_total.quantize(Decimal("0.0001")),
            open_manager_listing_count=sum(1 for item in manager_state.get("listings", []) if item.get("status") == "open"),
            settled_manager_trade_count=len(trade_history),
        )

    def list_high_risk_actions(self, app: FastAPI) -> list[HighRiskActionView]:
        return [
            HighRiskActionView(action_key="liquidity_intervention", label="Liquidity desk intervention", required_permission="manage_liquidity_desk", integrity_note="Requires bounded reference pricing and an explicit confirmation phrase."),
            HighRiskActionView(action_key="payment_rail_toggle", label="Payment rail toggle", required_permission="manage_payment_rails", integrity_note="Pausing live rails should always carry a maintenance message and an audit reason."),
            HighRiskActionView(action_key="withdrawal_status_change", label="Withdrawal status change", required_permission="manage_withdrawals", integrity_note="Completion must pass through processing to reduce accidental settlement errors."),
            HighRiskActionView(action_key="treasury_withdrawal", label="Treasury withdrawal", required_permission="manage_treasury_withdrawals", integrity_note="Requires a destination reference, clear reason, and a confirmation phrase."),
            HighRiskActionView(action_key="commission_change", label="Commission policy change", required_permission="manage_commissions", integrity_note="Reason is mandatory so fee policy changes remain traceable."),
        ]

    def available_audit_event_types(self, app: FastAPI) -> list[str]:
        path = self._audit_path(app)
        if not path.exists():
            return []
        event_types: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_type = str(payload.get("event_type") or "").strip()
            if event_type:
                event_types.add(event_type)
        return sorted(event_types)

    def _load_manager_market_state(self, app: FastAPI) -> dict[str, Any]:
        path = app.state.settings.config_root / "manager_market_state.json"
        if not path.exists():
            return {"trade_history": [], "listings": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def execute_liquidity_intervention(
        self,
        app: FastAPI,
        session: Session,
        actor: User,
        payload: LiquidityInterventionRequest,
    ) -> LiquidityInterventionView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_liquidity_desk")

        target_user = session.get(User, payload.user_id)
        if target_user is None:
            raise GodModeError("Counterparty user was not found.")

        player_summary = session.get(PlayerSummaryReadModel, payload.player_id)
        if player_summary is None:
            raise GodModeError("Player summary was not found for liquidity operation.")

        reference_price = Decimal(str(player_summary.current_value_credits or 0)).quantize(Decimal("0.0001"))
        liquidity_band = (player_summary.summary_json or {}).get("liquidity_band") or {}
        max_spread_bps = int(liquidity_band.get("max_spread_bps") or 1000)
        lower_bound = (reference_price * Decimal(10000 - max_spread_bps) / Decimal(10000)).quantize(Decimal("0.0001"))
        upper_bound = (reference_price * Decimal(10000 + max_spread_bps) / Decimal(10000)).quantize(Decimal("0.0001"))
        if payload.unit_price_credits < lower_bound or payload.unit_price_credits > upper_bound:
            raise IntegrityBoundError(
                f"Requested desk price is outside the allowed bounded range {lower_bound} - {upper_bound} credits."
            )
        confirmation = str(getattr(payload, "confirmation_text", "") or "").strip().lower()
        if confirmation != "confirm liquidity action":
            raise IntegrityBoundError("Confirmation text must be exactly 'CONFIRM LIQUIDITY ACTION'.")

        total = (payload.quantity * payload.unit_price_credits).quantize(Decimal("0.0001"))
        reference = f"godmode:{payload.action}:{payload.player_id}:{generate_uuid()}"
        if payload.action == "buy_from_user":
            self.wallet_service.settle_available_position_units(
                session,
                user=target_user,
                player_id=payload.player_id,
                quantity=payload.quantity,
                reference=reference,
                description="God mode liquidity buyback.",
                external_reference=reference,
                source_tag=LedgerSourceTag.PLAYER_CARD_SALE,
            )
            self.wallet_service.credit_trade_proceeds(
                session,
                user=target_user,
                amount=total,
                reference=reference,
                description="Liquidity desk credited user for buyback.",
                external_reference=reference,
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.PLAYER_CARD_SALE,
            )
        else:
            self.wallet_service.credit_position_units(
                session,
                user=target_user,
                player_id=payload.player_id,
                quantity=payload.quantity,
                reference=reference,
                description="Liquidity desk inventory sale to user.",
                external_reference=reference,
                source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
            )
            self.wallet_service.settle_available_funds(
                session,
                user=target_user,
                amount=total,
                reference=reference,
                description="Liquidity desk debited user for inventory sale.",
                external_reference=reference,
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
            )

        action = {
            "action_id": generate_uuid(),
            "action": payload.action,
            "user_id": payload.user_id,
            "player_id": payload.player_id,
            "quantity": str(payload.quantity),
            "unit_price_credits": str(payload.unit_price_credits),
            "gross_total_credits": str(total),
            "reference_price_credits": str(reference_price),
            "max_allowed_price_credits": str(upper_bound),
            "min_allowed_price_credits": str(lower_bound),
            "created_at": utcnow().isoformat(),
            "created_by": actor.id,
            "reason": payload.reason,
        }
        state.setdefault("liquidity_interventions", []).insert(0, action)
        state["liquidity_interventions"] = state["liquidity_interventions"][:100]
        self._save_state(app, state)
        self._append_audit(
            app,
            event_type="admin.liquidity.executed",
            actor=actor,
            summary=f"Executed bounded liquidity intervention for player {payload.player_id}.",
            payload=action,
        )
        with app.state.session_factory() as audit_session:
            self._log_admin_override(
                session=audit_session,
                actor=actor,
                action_key="admin.liquidity.executed",
                detail="Liquidity intervention executed.",
                metadata=action,
            )
        return LiquidityInterventionView.model_validate(action)

    def list_withdrawals(self, session: Session) -> list[WithdrawalAdminView]:
        requests = session.scalars(
            select(PayoutRequest).order_by(PayoutRequest.updated_at.desc(), PayoutRequest.created_at.desc())
        ).all()
        result: list[WithdrawalAdminView] = []
        for item in requests:
            user = session.get(User, item.user_id)
            result.append(
                WithdrawalAdminView(
                    payout_request_id=item.id,
                    user_id=item.user_id,
                    username=user.username if user is not None else None,
                    amount=item.amount,
                    unit=item.unit.value,
                    status=item.status,
                    destination_reference=item.destination_reference,
                    notes=item.notes,
                    requested_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )
        return result

    def _payout_meta(self, request: PayoutRequest) -> dict[str, Any]:
        raw = (request.notes or "").strip()
        if raw.startswith("{"):
            try:
                value = json.loads(raw)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                return {"raw_notes": request.notes or ""}
        return {"raw_notes": request.notes or ""}

    def _withdrawal_view(self, request: PayoutRequest, user: User | None) -> WithdrawalAdminView:
        meta = self._payout_meta(request)
        fee_amount = Decimal(str(meta.get("fee_amount", "0.0000")))
        total_debit = Decimal(str(meta.get("total_debit", request.amount)))
        source_scope = str(meta.get("source_scope", "trade"))
        return WithdrawalAdminView(
            payout_request_id=request.id,
            user_id=request.user_id,
            username=user.username if user is not None else None,
            amount=request.amount,
            fee_amount=fee_amount,
            total_debit=total_debit,
            source_scope=source_scope if source_scope in {"trade", "competition"} else "trade",
            unit=request.unit.value,
            status=request.status,
            destination_reference=request.destination_reference,
            notes=request.notes,
            requested_at=request.created_at,
            updated_at=request.updated_at,
        )

    def update_withdrawal_status(
        self,
        app: FastAPI,
        session: Session,
        actor: User,
        payout_request_id: str,
        payload: WithdrawalStatusUpdate,
    ) -> WithdrawalAdminView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_withdrawals")
        request = session.get(PayoutRequest, payout_request_id)
        if request is None:
            raise GodModeError("Withdrawal request was not found.")
        next_status = PayoutStatus(payload.status)
        if request.status == PayoutStatus.COMPLETED:
            raise GodModeError("Completed withdrawals are append-only and cannot be moved again.")
        if next_status == PayoutStatus.COMPLETED and request.status not in {PayoutStatus.PROCESSING, PayoutStatus.REVIEWING}:
            raise GodModeError("Withdrawal must be in processing or reviewing before it can be completed.")
        if next_status == PayoutStatus.PROCESSING and request.status not in {PayoutStatus.REQUESTED, PayoutStatus.REVIEWING, PayoutStatus.HELD}:
            raise GodModeError("Only queued withdrawals can enter processing.")
        previous_status = request.status
        request.status = next_status
        existing_meta = self._payout_meta(request)
        if payload.notes is not None:
            existing_meta["admin_notes"] = payload.notes
            request.notes = json.dumps(existing_meta, sort_keys=True)
        if next_status == PayoutStatus.COMPLETED and request.settlement_transaction_id is None:
            self.wallet_service.complete_payout_request(session, request, actor=actor)
        elif next_status in {PayoutStatus.REJECTED, PayoutStatus.FAILED} and request.settlement_transaction_id is None:
            self.wallet_service.release_payout_request(session, request, actor=actor, failure_reason=payload.status)
        elif previous_status in {PayoutStatus.REJECTED, PayoutStatus.FAILED} and next_status not in {PayoutStatus.REJECTED, PayoutStatus.FAILED}:
            raise GodModeError("Rejected or failed withdrawals are terminal after funds are released.")
        session.flush()
        self._append_audit(
            app,
            event_type="admin.withdrawal.updated",
            actor=actor,
            summary=f"Moved payout request {payout_request_id} to {payload.status}.",
            payload={"payout_request_id": payout_request_id, "status": payload.status, "notes": payload.notes},
        )
        with app.state.session_factory() as audit_session:
            self._log_admin_override(
                session=audit_session,
                actor=actor,
                action_key="admin.withdrawal.updated",
                detail="Withdrawal status updated.",
                metadata={"payout_request_id": payout_request_id, "status": payload.status},
            )
        user = session.get(User, request.user_id)
        return self._withdrawal_view(request, user)

    def create_treasury_withdrawal(
        self,
        app: FastAPI,
        session: Session,
        actor: User,
        payload: TreasuryWithdrawalRequest,
    ) -> TreasuryWithdrawalView:
        state = self._load_state(app)
        profile = self.resolve_profile(actor, state)
        self._assert_has_permission(profile, "manage_treasury_withdrawals")
        confirmation = str(getattr(payload, "confirmation_text", "") or "").strip().lower()
        if confirmation != "confirm treasury withdrawal":
            raise GodModeError("Confirmation text must be exactly 'CONFIRM TREASURY WITHDRAWAL'.")
        unit = LedgerUnit(payload.unit)
        platform_account = self.wallet_service.ensure_platform_account(session, unit)
        treasury_sink = self._ensure_treasury_sink_account(session, unit)
        reference = f"treasury-withdrawal:{generate_uuid()}"
        self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=platform_account, amount=-payload.amount),
                LedgerPosting(account=treasury_sink, amount=payload.amount),
            ],
            reason=self.wallet_service.trade_settlement_reason,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=reference,
            description=f"Treasury withdrawal to {payload.destination_reference}",
            external_reference=reference,
            actor=actor,
        )
        record = {
            "withdrawal_id": generate_uuid(),
            "unit": payload.unit,
            "amount": str(payload.amount),
            "destination_reference": payload.destination_reference,
            "reason": payload.reason,
            "created_at": utcnow().isoformat(),
            "created_by": actor.id,
        }
        state.setdefault("treasury_withdrawals", []).insert(0, record)
        state["treasury_withdrawals"] = state["treasury_withdrawals"][:100]
        self._save_state(app, state)
        self._append_audit(
            app,
            event_type="admin.treasury.withdrawal",
            actor=actor,
            summary="Executed treasury withdrawal.",
            payload=record,
        )
        self._log_admin_override(
            session=session,
            actor=actor,
            action_key="admin.treasury.withdrawal",
            detail="Treasury withdrawal executed.",
            metadata=record,
        )
        return TreasuryWithdrawalView.model_validate(record)

    def list_audit_events(self, app: FastAPI, limit: int = 30, query: str | None = None, event_type: str | None = None) -> list[AuditEventView]:
        path = self._audit_path(app)
        if not path.exists():
            return []
        items: list[AuditEventView] = []
        query_term = (query or "").strip().lower()
        event_type_term = (event_type or "").strip().lower()
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line:
                continue
            payload = AuditEventView.model_validate(json.loads(line))
            if event_type_term and payload.event_type.lower() != event_type_term:
                continue
            haystack = f"{payload.summary} {payload.event_type} {json.dumps(payload.payload, sort_keys=True)}".lower()
            if query_term and query_term not in haystack:
                continue
            items.append(payload)
            if len(items) >= limit:
                break
        return items

    def resolve_profile(self, actor: User, state: dict[str, Any]) -> GodModeProfileView:
        roles_block = state["roles"]
        available_roles = dict(roles_block.get("available_roles") or DEFAULT_ROLE_PERMISSIONS)
        assignments = roles_block.get("assignments") or []
        subject_options = (actor.id, actor.email.lower(), actor.username.lower())
        role_name = roles_block.get("default_admin_role") or "god_mode"
        permissions = list(available_roles.get(role_name, []))
        for assignment in assignments:
            if not assignment.get("is_enabled", True):
                continue
            subject_key = str(assignment.get("subject_key") or "").strip().lower()
            if subject_key and subject_key in {option.lower() for option in subject_options if isinstance(option, str)}:
                role_name = str(assignment.get("role_name") or role_name)
                permissions = list(available_roles.get(role_name, []))
                permissions.extend(str(item) for item in assignment.get("permissions") or [])
                break
        permissions = sorted(set(permissions))
        return GodModeProfileView(
            subject_key=actor.id,
            role_name=role_name,
            permissions=permissions,
            can_directly_set_price=False,
            can_edit_results=False,
        )

    def _assert_has_permission(self, profile: GodModeProfileView, permission: str) -> None:
        if permission not in profile.permissions:
            raise PermissionDeniedError(f"Permission {permission} is required for this action.")

    def _recent_interventions(self, app: FastAPI, limit: int = 10) -> list[LiquidityInterventionView]:
        state = self._load_state(app)
        return [
            LiquidityInterventionView.model_validate(item)
            for item in (state.get("liquidity_interventions") or [])[:limit]
        ]

    def _state_path(self, app: FastAPI) -> Path:
        return app.state.settings.config_root / ADMIN_GODMODE_FILE

    def _audit_path(self, app: FastAPI) -> Path:
        return app.state.settings.config_root / AUDIT_LOG_FILE

    def _log_admin_override(
        self,
        *,
        session: Session,
        actor: User,
        action_key: str,
        detail: str,
        metadata: dict[str, Any],
    ) -> None:
        AuditTrailService(session).log_admin_override(
            actor_user_id=actor.id,
            action_key=action_key,
            detail=detail,
            metadata=metadata,
        )

    def _load_state(self, app: FastAPI) -> dict[str, Any]:
        path = self._state_path(app)
        if not path.exists():
            state = self._default_state()
            self._save_state(app, state)
            return state
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_state(self, app: FastAPI, state: dict[str, Any]) -> None:
        path = self._state_path(app)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def _default_state(self) -> dict[str, Any]:
        return {
            "roles": {
                "default_admin_role": "god_mode",
                "available_roles": DEFAULT_ROLE_PERMISSIONS,
                "assignments": [],
            },
            "commissions": DEFAULT_COMMISSION_SETTINGS,
            "payment_rails": DEFAULT_PAYMENT_RAILS,
            "withdrawal_controls": DEFAULT_WITHDRAWAL_CONTROLS,
            "competition_controls": DEFAULT_COMPETITION_CONTROLS,
            "liquidity_interventions": [],
            "treasury_withdrawals": [],
        }

    def _append_audit(
        self,
        app: FastAPI,
        *,
        event_type: str,
        actor: User,
        summary: str,
        payload: dict[str, Any],
    ) -> None:
        record = {
            "event_id": generate_uuid(),
            "event_type": event_type,
            "actor_user_id": actor.id,
            "actor_email": actor.email,
            "created_at": utcnow().isoformat(),
            "summary": summary,
            "payload": payload,
        }
        path = self._audit_path(app)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _ensure_treasury_sink_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        code = f"platform:{unit.value}:treasury_withdrawals"
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            from app.models.wallet import LedgerAccountKind
            account = LedgerAccount(
                code=code,
                label=f"Treasury {unit.value.capitalize()} Withdrawal Sink",
                unit=unit,
                kind=LedgerAccountKind.SYSTEM,
                allow_negative=False,
            )
            session.add(account)
            session.flush()
        return account
