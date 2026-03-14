from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.admin_godmode.service import AdminGodModeService
from backend.app.auth.dependencies import get_current_admin, get_current_user, get_session
from backend.app.models.dispute import Dispute, DisputeMessage
from backend.app.models.treasury import (
    DepositRequest,
    DepositStatus,
    KycProfile,
    TreasuryBankAccount,
    TreasurySettings,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalStatus,
)
from backend.app.models.user import KycStatus, User
from backend.app.models.withdrawal_review import WithdrawalReview
from backend.app.treasury.schemas import (
    AdminDepositView,
    AdminDisputeMessageView,
    AdminDisputeView,
    AdminKycView,
    AdminQueueView,
    AdminWithdrawalView,
    DepositRequestView,
    DisputeCreateRequest,
    DisputeMessageRequest,
    KycProfileView,
    KycReviewRequest,
    KycSubmitRequest,
    TreasuryBankAccountCreate,
    TreasuryBankAccountUpdate,
    TreasuryBankAccountView,
    TreasuryDashboardView,
    TreasurySettingsUpdate,
    TreasurySettingsView,
    UserBankAccountCreate,
    UserBankAccountUpdate,
    UserBankAccountView,
    WithdrawalReviewView,
    WithdrawalRequestView,
)
from backend.app.treasury.service import TreasuryConflictError, TreasuryNotFoundError, TreasuryService
from backend.app.wallets.service import WalletService

router = APIRouter(tags=["treasury"])
admin_router = APIRouter(prefix="/api/admin/treasury", tags=["admin-treasury"])
api_router = APIRouter(prefix="/api", tags=["treasury"])


def _service(request: Request | None) -> TreasuryService:
    wallet_service = None
    if request is not None and hasattr(request.app.state, "event_publisher"):
        wallet_service = WalletService(event_publisher=request.app.state.event_publisher)
    return TreasuryService(wallet_service=wallet_service)


def _require_permission(request: Request, actor: User, permission: str) -> None:
    service = AdminGodModeService(wallet_service=WalletService())
    state = service._load_state(request.app)
    profile = service.resolve_profile(actor, state)
    service._assert_has_permission(profile, permission)


@api_router.get("/kyc", response_model=KycProfileView)
def get_kyc_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> KycProfileView:
    service = _service(request)
    profile = service.get_or_create_kyc_profile(session, current_user)
    service.track_event(session, "kyc_started", user=current_user, metadata={})
    return KycProfileView.model_validate(profile)


@api_router.post("/kyc", response_model=KycProfileView)
def submit_kyc_profile(
    payload: KycSubmitRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> KycProfileView:
    service = _service(request)
    try:
        profile = service.submit_kyc(
            session,
            user=current_user,
            nin=payload.nin,
            bvn=payload.bvn,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            id_document_attachment_id=payload.id_document_attachment_id,
        )
        session.commit()
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return KycProfileView.model_validate(profile)


@api_router.get("/bank-accounts", response_model=list[UserBankAccountView])
def list_user_bank_accounts(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> list[UserBankAccountView]:
    service = _service(request)
    accounts = service.list_user_bank_accounts(session, current_user)
    return [UserBankAccountView.model_validate(account) for account in accounts]


@api_router.post("/bank-accounts", response_model=UserBankAccountView, status_code=status.HTTP_201_CREATED)
def create_user_bank_account(
    payload: UserBankAccountCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> UserBankAccountView:
    service = _service(request)
    account = service.create_user_bank_account(
        session,
        user=current_user,
        bank_name=payload.bank_name.strip(),
        account_number=payload.account_number.strip(),
        account_name=payload.account_name.strip(),
        bank_code=payload.bank_code.strip() if payload.bank_code else None,
        currency_code=payload.currency_code,
        set_active=payload.set_active,
    )
    session.commit()
    session.refresh(account)
    return UserBankAccountView.model_validate(account)


@api_router.put("/bank-accounts/{bank_account_id}", response_model=UserBankAccountView)
def update_user_bank_account(
    bank_account_id: str,
    payload: UserBankAccountUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> UserBankAccountView:
    service = _service(request)
    try:
        account = service.update_user_bank_account(
            session,
            user=current_user,
            bank_account_id=bank_account_id,
            updates=payload.model_dump(exclude_unset=True),
        )
        session.commit()
        session.refresh(account)
    except TreasuryNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserBankAccountView.model_validate(account)


@api_router.get("/disputes", response_model=list[AdminDisputeView])
def list_user_disputes(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[AdminDisputeView]:
    disputes = session.scalars(
        select(Dispute).where(Dispute.user_id == current_user.id).order_by(Dispute.updated_at.desc())
    ).all()
    result: list[AdminDisputeView] = []
    for dispute in disputes:
        result.append(
            AdminDisputeView(
                id=dispute.id,
                status=dispute.status.value,
                reference=dispute.reference,
                resource_type=dispute.resource_type,
                resource_id=dispute.resource_id,
                subject=dispute.subject,
                created_at=dispute.created_at,
                updated_at=dispute.updated_at,
                last_message_at=dispute.last_message_at,
                user_id=dispute.user_id,
                user_email=current_user.email,
                user_full_name=current_user.full_name,
                user_phone_number=current_user.phone_number,
                messages=[],
            )
        )
    return result


@api_router.post("/disputes", response_model=AdminDisputeView, status_code=status.HTTP_201_CREATED)
def open_dispute(
    payload: DisputeCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> AdminDisputeView:
    service = _service(request)
    try:
        dispute = service.open_dispute(
            session,
            user=current_user,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            reference=payload.reference,
            subject=payload.subject,
            message=payload.message,
            attachment_id=payload.attachment_id,
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AdminDisputeView(
        id=dispute.id,
        status=dispute.status.value,
        reference=dispute.reference,
        resource_type=dispute.resource_type,
        resource_id=dispute.resource_id,
        subject=dispute.subject,
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
        last_message_at=dispute.last_message_at,
        user_id=current_user.id,
        user_email=current_user.email,
        user_full_name=current_user.full_name,
        user_phone_number=current_user.phone_number,
        messages=[],
    )


@api_router.get("/disputes/{dispute_id}", response_model=AdminDisputeView)
def get_dispute_detail(
    dispute_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AdminDisputeView:
    dispute = session.get(Dispute, dispute_id)
    if dispute is None or dispute.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")
    messages = session.scalars(
        select(DisputeMessage)
        .where(DisputeMessage.dispute_id == dispute.id)
        .order_by(DisputeMessage.created_at.asc())
    ).all()
    return AdminDisputeView(
        id=dispute.id,
        status=dispute.status.value,
        reference=dispute.reference,
        resource_type=dispute.resource_type,
        resource_id=dispute.resource_id,
        subject=dispute.subject,
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
        last_message_at=dispute.last_message_at,
        user_id=current_user.id,
        user_email=current_user.email,
        user_full_name=current_user.full_name,
        user_phone_number=current_user.phone_number,
        messages=[
            AdminDisputeMessageView(
                id=msg.id,
                sender_user_id=msg.sender_user_id,
                sender_role=msg.sender_role,
                message=msg.message,
                attachment_id=msg.attachment_id,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


@api_router.post("/disputes/{dispute_id}/messages", response_model=AdminDisputeMessageView, status_code=status.HTTP_201_CREATED)
def add_dispute_message(
    dispute_id: str,
    payload: DisputeMessageRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    request: Request = None,
) -> AdminDisputeMessageView:
    service = _service(request)
    dispute = session.get(Dispute, dispute_id)
    if dispute is None or dispute.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")
    message_text = payload.message.strip()
    if not message_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is required.")
    record = service.add_dispute_message(
        session,
        dispute=dispute,
        sender=current_user,
        sender_role="user",
        message=message_text,
        attachment_id=payload.attachment_id,
    )
    session.commit()
    session.refresh(record)
    return AdminDisputeMessageView(
        id=record.id,
        sender_user_id=record.sender_user_id,
        sender_role=record.sender_role,
        message=record.message,
        attachment_id=record.attachment_id,
        created_at=record.created_at,
    )


@admin_router.get("/settings", response_model=TreasurySettingsView)
def get_treasury_settings(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> TreasurySettingsView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    service = _service(request)
    settings = service.ensure_settings(session)
    bank_account = service.get_active_bank_account(session, settings)
    return TreasurySettingsView.model_validate(settings).model_copy(update={"active_bank_account": bank_account})


@admin_router.put("/settings", response_model=TreasurySettingsView)
def update_treasury_settings(
    request: Request,
    payload: TreasurySettingsUpdate,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> TreasurySettingsView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    service = _service(request)
    settings = service.ensure_settings(session)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(settings, key, value)
    settings.updated_by_user_id = actor.id
    session.flush()
    service._audit(
        session,
        actor=actor,
        event_type="treasury.settings.updated",
        resource_type="treasury_settings",
        resource_id=settings.id,
        summary="Treasury settings updated.",
        payload=data,
    )
    if "deposit_rate_value" in data or "withdrawal_rate_value" in data:
        service.track_event(session, "admin_rate_changed", user_id=actor.id, metadata=data)
    if "deposit_mode" in data or "withdrawal_mode" in data:
        service.track_event(session, "admin_payment_mode_changed", user_id=actor.id, metadata=data)
    session.commit()
    session.refresh(settings)
    bank_account = service.get_active_bank_account(session, settings)
    return TreasurySettingsView.model_validate(settings).model_copy(update={"active_bank_account": bank_account})


@admin_router.get("/bank-accounts", response_model=list[TreasuryBankAccountView])
def list_treasury_bank_accounts(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> list[TreasuryBankAccountView]:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    accounts = session.scalars(select(TreasuryBankAccount).order_by(TreasuryBankAccount.created_at.desc())).all()
    return [TreasuryBankAccountView.model_validate(account) for account in accounts]


@admin_router.post("/bank-accounts", response_model=TreasuryBankAccountView, status_code=status.HTTP_201_CREATED)
def create_treasury_bank_account(
    request: Request,
    payload: TreasuryBankAccountCreate,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> TreasuryBankAccountView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    account = TreasuryBankAccount(
        currency_code=payload.currency_code,
        bank_name=payload.bank_name,
        account_number=payload.account_number,
        account_name=payload.account_name,
        bank_code=payload.bank_code,
        is_active=payload.is_active,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return TreasuryBankAccountView.model_validate(account)


@admin_router.put("/bank-accounts/{account_id}", response_model=TreasuryBankAccountView)
def update_treasury_bank_account(
    request: Request,
    account_id: str,
    payload: TreasuryBankAccountUpdate,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> TreasuryBankAccountView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    account = session.get(TreasuryBankAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank account not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    session.commit()
    session.refresh(account)
    return TreasuryBankAccountView.model_validate(account)


@admin_router.get("/dashboard", response_model=TreasuryDashboardView)
def treasury_dashboard(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> TreasuryDashboardView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    now = datetime.now(timezone.utc)
    active_since = now - timedelta(days=7)
    total_users = session.scalar(select(func.count(User.id)))
    active_users = session.scalar(select(func.count(User.id)).where(User.last_login_at >= active_since))
    pending_deposits = session.scalar(
        select(func.count(DepositRequest.id)).where(
            DepositRequest.status.in_([DepositStatus.PAYMENT_SUBMITTED, DepositStatus.UNDER_REVIEW])
        )
    )
    pending_withdrawals = session.scalar(
        select(func.count(TreasuryWithdrawalRequest.id)).where(
            TreasuryWithdrawalRequest.status.in_([
                TreasuryWithdrawalStatus.PENDING_REVIEW,
                TreasuryWithdrawalStatus.APPROVED,
                TreasuryWithdrawalStatus.PROCESSING,
            ])
        )
    )
    pending_kyc = session.scalar(
        select(func.count(KycProfile.id)).where(KycProfile.status == KycStatus.PENDING)
    )
    open_disputes = session.scalar(
        select(func.count(Dispute.id)).where(
            Dispute.status.in_(["open", "awaiting_admin", "awaiting_user"])
        )
    )
    deposits_confirmed_today = session.scalar(
        select(func.count(DepositRequest.id)).where(DepositRequest.confirmed_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    )
    withdrawals_paid_today = session.scalar(
        select(func.count(TreasuryWithdrawalRequest.id)).where(TreasuryWithdrawalRequest.paid_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))
    )
    wallet_liability = session.scalar(
        select(func.coalesce(func.sum(DepositRequest.amount_coin), 0))
    )
    pending_treasury_exposure = session.scalar(
        select(func.coalesce(func.sum(TreasuryWithdrawalRequest.amount_coin), 0))
        .where(
            TreasuryWithdrawalRequest.status.in_([
                TreasuryWithdrawalStatus.PENDING_REVIEW,
                TreasuryWithdrawalStatus.APPROVED,
                TreasuryWithdrawalStatus.PROCESSING,
            ])
        )
    )
    return TreasuryDashboardView(
        total_users=int(total_users or 0),
        active_users=int(active_users or 0),
        pending_deposits=int(pending_deposits or 0),
        pending_withdrawals=int(pending_withdrawals or 0),
        pending_kyc=int(pending_kyc or 0),
        open_disputes=int(open_disputes or 0),
        deposits_confirmed_today=int(deposits_confirmed_today or 0),
        withdrawals_paid_today=int(withdrawals_paid_today or 0),
        wallet_liability=Decimal(wallet_liability or 0),
        pending_treasury_exposure=Decimal(pending_treasury_exposure or 0),
    )


@admin_router.get("/deposits", response_model=AdminQueueView)
def list_admin_deposits(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    status_filter: DepositStatus | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminQueueView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    query = select(DepositRequest, User).join(User, DepositRequest.user_id == User.id)
    if status_filter is not None:
        query = query.where(DepositRequest.status == status_filter)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(
                func.lower(DepositRequest.reference).ilike(like),
                func.lower(User.email).ilike(like),
                func.lower(User.full_name).ilike(like),
                func.lower(User.phone_number).ilike(like),
                func.lower(DepositRequest.payer_name).ilike(like),
                func.lower(DepositRequest.sender_bank).ilike(like),
                func.lower(DepositRequest.transfer_reference).ilike(like),
            )
        )
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.execute(query.order_by(DepositRequest.created_at.desc()).limit(limit).offset(offset)).all()
    items = [
        AdminDepositView(
            id=deposit.id,
            reference=deposit.reference,
            status=deposit.status,
            amount_fiat=deposit.amount_fiat,
            amount_coin=deposit.amount_coin,
            currency_code=deposit.currency_code,
            payer_name=deposit.payer_name,
            sender_bank=deposit.sender_bank,
            transfer_reference=deposit.transfer_reference,
            created_at=deposit.created_at,
            submitted_at=deposit.submitted_at,
            reviewed_at=deposit.reviewed_at,
            confirmed_at=deposit.confirmed_at,
            rejected_at=deposit.rejected_at,
            admin_notes=deposit.admin_notes,
            user_id=user.id,
            user_email=user.email,
            user_full_name=user.full_name,
            user_phone_number=user.phone_number,
        )
        for deposit, user in rows
    ]
    return AdminQueueView(items=items, total=int(total or 0), limit=limit, offset=offset)


@admin_router.post("/deposits/{deposit_id}/confirm", response_model=DepositRequestView)
def admin_confirm_deposit(
    request: Request,
    deposit_id: str,
    payload: dict | None = None,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> DepositRequestView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    service = _service(request)
    try:
        deposit = service.confirm_deposit(session, actor=actor, deposit_request_id=deposit_id, admin_notes=(payload or {}).get("admin_notes"))
        session.commit()
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DepositRequestView.model_validate(deposit)


@admin_router.post("/deposits/{deposit_id}/reject", response_model=DepositRequestView)
def admin_reject_deposit(
    request: Request,
    deposit_id: str,
    payload: dict | None = None,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> DepositRequestView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    service = _service(request)
    deposit = service.reject_deposit(session, actor=actor, deposit_request_id=deposit_id, admin_notes=(payload or {}).get("admin_notes"))
    session.commit()
    return DepositRequestView.model_validate(deposit)


@admin_router.post("/deposits/{deposit_id}/review", response_model=DepositRequestView)
def admin_review_deposit(
    request: Request,
    deposit_id: str,
    payload: dict | None = None,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> DepositRequestView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    service = _service(request)
    deposit = service.mark_deposit_under_review(session, actor=actor, deposit_request_id=deposit_id, admin_notes=(payload or {}).get("admin_notes"))
    session.commit()
    return DepositRequestView.model_validate(deposit)


@admin_router.get("/withdrawals", response_model=AdminQueueView)
def list_admin_withdrawals(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    status_filter: TreasuryWithdrawalStatus | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminQueueView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    query = select(TreasuryWithdrawalRequest, User).join(User, TreasuryWithdrawalRequest.user_id == User.id)
    if status_filter is not None:
        query = query.where(TreasuryWithdrawalRequest.status == status_filter)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(
                func.lower(TreasuryWithdrawalRequest.reference).ilike(like),
                func.lower(User.email).ilike(like),
                func.lower(User.full_name).ilike(like),
                func.lower(User.phone_number).ilike(like),
                func.lower(TreasuryWithdrawalRequest.bank_name).ilike(like),
                func.lower(TreasuryWithdrawalRequest.bank_account_number).ilike(like),
                func.lower(TreasuryWithdrawalRequest.bank_account_name).ilike(like),
            )
        )
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.execute(query.order_by(TreasuryWithdrawalRequest.created_at.desc()).limit(limit).offset(offset)).all()
    items = [
        AdminWithdrawalView(
            id=withdrawal.id,
            reference=withdrawal.reference,
            status=withdrawal.status,
            amount_coin=withdrawal.amount_coin,
            amount_fiat=withdrawal.amount_fiat,
            currency_code=withdrawal.currency_code,
            bank_name=withdrawal.bank_name,
            bank_account_number=withdrawal.bank_account_number,
            bank_account_name=withdrawal.bank_account_name,
            created_at=withdrawal.created_at,
            reviewed_at=withdrawal.reviewed_at,
            approved_at=withdrawal.approved_at,
            processed_at=withdrawal.processed_at,
            paid_at=withdrawal.paid_at,
            rejected_at=withdrawal.rejected_at,
            cancelled_at=withdrawal.cancelled_at,
            user_id=user.id,
            user_email=user.email,
            user_full_name=user.full_name,
            user_phone_number=user.phone_number,
        )
        for withdrawal, user in rows
    ]
    return AdminQueueView(items=items, total=int(total or 0), limit=limit, offset=offset)


@admin_router.post("/withdrawals/{withdrawal_id}/status", response_model=WithdrawalRequestView)
def update_withdrawal_status(
    request: Request,
    withdrawal_id: str,
    payload: dict,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> WithdrawalRequestView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    if "status" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required.")
    service = _service(request)
    try:
        status_value = TreasuryWithdrawalStatus(payload["status"])
        withdrawal = service.review_withdrawal_status(
            session,
            actor=actor,
            withdrawal_id=withdrawal_id,
            status=status_value,
            admin_notes=payload.get("admin_notes"),
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except TreasuryConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return WithdrawalRequestView.model_validate(withdrawal)


@admin_router.get("/withdrawals/{withdrawal_id}/reviews", response_model=list[WithdrawalReviewView])
def list_withdrawal_reviews(
    request: Request,
    withdrawal_id: str,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> list[WithdrawalReviewView]:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    reviews = session.scalars(
        select(WithdrawalReview)
        .where(WithdrawalReview.withdrawal_request_id == withdrawal_id)
        .order_by(WithdrawalReview.created_at.desc())
    ).all()
    return [WithdrawalReviewView.model_validate(item) for item in reviews]


@admin_router.get("/kyc", response_model=AdminQueueView)
def list_admin_kyc(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    status_filter: KycStatus | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminQueueView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    query = select(KycProfile, User).join(User, KycProfile.user_id == User.id)
    if status_filter is not None:
        query = query.where(KycProfile.status == status_filter)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(
                func.lower(User.email).ilike(like),
                func.lower(User.full_name).ilike(like),
                func.lower(User.phone_number).ilike(like),
                func.lower(KycProfile.nin).ilike(like),
                func.lower(KycProfile.bvn).ilike(like),
            )
        )
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.execute(query.order_by(KycProfile.updated_at.desc()).limit(limit).offset(offset)).all()
    items = [
        AdminKycView(
            id=profile.id,
            user_id=profile.user_id,
            status=profile.status,
            nin=profile.nin,
            bvn=profile.bvn,
            address_line1=profile.address_line1,
            city=profile.city,
            state=profile.state,
            country=profile.country,
            submitted_at=profile.submitted_at,
            reviewed_at=profile.reviewed_at,
            rejection_reason=profile.rejection_reason,
            user_email=user.email,
            user_full_name=user.full_name,
            user_phone_number=user.phone_number,
        )
        for profile, user in rows
    ]
    return AdminQueueView(items=items, total=int(total or 0), limit=limit, offset=offset)


@admin_router.post("/kyc/{profile_id}/review", response_model=KycProfileView)
def review_kyc(
    request: Request,
    profile_id: str,
    payload: KycReviewRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> KycProfileView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    service = _service(request)
    try:
        profile = service.review_kyc(
            session,
            actor=actor,
            profile_id=profile_id,
            status=payload.status,
            rejection_reason=payload.rejection_reason,
        )
        session.commit()
    except TreasuryNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return KycProfileView.model_validate(profile)


@admin_router.get("/disputes", response_model=AdminQueueView)
def list_admin_disputes(
    request: Request,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminQueueView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    query = select(Dispute, User).join(User, Dispute.user_id == User.id)
    if status_filter:
        query = query.where(Dispute.status == status_filter)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            or_(
                func.lower(Dispute.reference).ilike(like),
                func.lower(User.email).ilike(like),
                func.lower(User.full_name).ilike(like),
                func.lower(User.phone_number).ilike(like),
            )
        )
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.execute(query.order_by(Dispute.updated_at.desc()).limit(limit).offset(offset)).all()
    items = [
        AdminDisputeView(
            id=dispute.id,
            status=dispute.status.value,
            reference=dispute.reference,
            resource_type=dispute.resource_type,
            resource_id=dispute.resource_id,
            subject=dispute.subject,
            created_at=dispute.created_at,
            updated_at=dispute.updated_at,
            last_message_at=dispute.last_message_at,
            user_id=user.id,
            user_email=user.email,
            user_full_name=user.full_name,
            user_phone_number=user.phone_number,
            messages=[],
        )
        for dispute, user in rows
    ]
    return AdminQueueView(items=items, total=int(total or 0), limit=limit, offset=offset)


@admin_router.get("/disputes/{dispute_id}", response_model=AdminDisputeView)
def get_admin_dispute(
    request: Request,
    dispute_id: str,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> AdminDisputeView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    dispute = session.get(Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")
    user = session.get(User, dispute.user_id)
    messages = session.scalars(
        select(DisputeMessage).where(DisputeMessage.dispute_id == dispute.id).order_by(DisputeMessage.created_at.asc())
    ).all()
    return AdminDisputeView(
        id=dispute.id,
        status=dispute.status.value,
        reference=dispute.reference,
        resource_type=dispute.resource_type,
        resource_id=dispute.resource_id,
        subject=dispute.subject,
        created_at=dispute.created_at,
        updated_at=dispute.updated_at,
        last_message_at=dispute.last_message_at,
        user_id=dispute.user_id,
        user_email=user.email if user else "",
        user_full_name=user.full_name if user else None,
        user_phone_number=user.phone_number if user else None,
        messages=[
            AdminDisputeMessageView(
                id=msg.id,
                sender_user_id=msg.sender_user_id,
                sender_role=msg.sender_role,
                message=msg.message,
                attachment_id=msg.attachment_id,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
    )


@admin_router.post("/disputes/{dispute_id}/messages", response_model=AdminDisputeMessageView, status_code=status.HTTP_201_CREATED)
def add_admin_dispute_message(
    request: Request,
    dispute_id: str,
    payload: DisputeMessageRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(get_current_admin),
) -> AdminDisputeMessageView:
    _require_permission(request, actor, "manage_treasury_withdrawals")
    service = _service(request)
    dispute = session.get(Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")
    message_text = payload.message.strip()
    if not message_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is required.")
    record = service.add_dispute_message(
        session,
        dispute=dispute,
        sender=actor,
        sender_role="admin",
        message=message_text,
        attachment_id=payload.attachment_id,
    )
    session.commit()
    session.refresh(record)
    return AdminDisputeMessageView(
        id=record.id,
        sender_user_id=record.sender_user_id,
        sender_role=record.sender_role,
        message=record.message,
        attachment_id=record.attachment_id,
        created_at=record.created_at,
    )


router.include_router(api_router)
router.include_router(admin_router)
