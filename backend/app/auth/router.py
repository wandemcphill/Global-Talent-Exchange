from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.auth.dependencies import get_current_user, get_session
from app.auth.schemas import (
    AccountRecoveryRequest,
    AccountRecoveryResetRequest,
    ActionStatusResponse,
    ChangePasswordRequest,
    ConfirmEmailRequest,
    CreatorSignupRequest,
    CurrentUserResponse,
    CurrentUserUpdateRequest,
    LoginRequest,
    RefreshTokenRequest,
    SessionBootstrapCoinTraderState,
    SessionBootstrapCreatorState,
    SessionBootstrapOnboardingState,
    SessionBootstrapPaymentsRuntimeState,
    RegisterRequest,
    SessionBootstrapRuntimeState,
    SessionBootstrapSecurityState,
    SessionBootstrapResponse,
    SessionBootstrapSessionView,
    TokenResponse,
    TraderSignupRequest,
    UserClubSignupRequest,
)
from app.auth.service import (
    AuthError,
    AuthService,
    DuplicateUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidSessionError,
    IssuedAuthSession,
)
from app.core.request_security import extract_client_ip
from app.common.enums.creator_profile_status import CreatorProfileStatus
from app.models.coin_trader import CoinTraderProfile
from app.models.auth_session import AuthSession
from app.models.creator_profile import CreatorProfile
from app.models.user import PublicAccountType, User
from app.policies.schemas import PolicyRequirementSummary, UserComplianceStatus
from app.policies.service import PolicyService
from app.schemas.club_identity_core import ClubProfileCore
from app.trader.service import TraderAccessError, TraderService
from app.treasury.service import TreasuryService
from app.wallets.funding_service import WalletFundingService
from app.wallets.providers.registry import provider_live_deposit_ready
from app.wallets.schemas import WalletAdaptiveOverviewView
from app.wallets.service import WalletService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
legacy_router = APIRouter(prefix="/auth")
api_router = APIRouter(prefix="/api/auth")
api_v2_router = APIRouter(prefix="/api/v2/auth")


class _AuthRouteTelemetry:
    def __init__(self, flow: str) -> None:
        self.flow = flow
        self.started_at = perf_counter()
        self.steps: dict[str, float] = {}

    def capture(self, step: str, duration_ms: float) -> None:
        self.steps[step] = round(duration_ms, 2)

    def mark(self, step: str, started_at: float) -> None:
        self.capture(step, (perf_counter() - started_at) * 1000)

    def log_entry(self, *, method: str, path: str, modules_hydrated: bool | None) -> None:
        logger.info(
            "auth.request.route_entry flow=%s method=%s path=%s modules_hydrated=%s",
            self.flow,
            method,
            path,
            modules_hydrated,
        )

    def log_success(self, *, status_code: int, user_id: str | None) -> None:
        logger.info(
            "auth.request.completed flow=%s status_code=%s user_id=%s duration_ms=%.2f steps=%s",
            self.flow,
            status_code,
            user_id,
            (perf_counter() - self.started_at) * 1000,
            self.steps,
        )

    def log_failure(self, *, status_code: int, user_id: str | None, error: str) -> None:
        logger.warning(
            "auth.request.failed flow=%s status_code=%s user_id=%s duration_ms=%.2f error=%s steps=%s",
            self.flow,
            status_code,
            user_id,
            (perf_counter() - self.started_at) * 1000,
            error,
            self.steps,
        )


def _build_auth_service(request: Request | None) -> AuthService:
    wallet_service = None
    email_service = None
    if request is not None:
        wallet_service = WalletService(
            event_publisher=getattr(request.app.state, "event_publisher", None),
            cache_backend=getattr(request.app.state, "cache_backend", None),
        )
    if request is not None and hasattr(request.app.state, "email_service"):
        email_service = request.app.state.email_service
    return AuthService(wallet_service=wallet_service, email_service=email_service)


def _log_email_dispatch_exception(*, flow: str, recipient: str | None, exc: Exception) -> None:
    logger.warning(
        "auth.email.dispatch_exception flow=%s recipient=%s error_type=%s error=%s",
        flow,
        recipient or "unknown",
        exc.__class__.__name__,
        str(exc),
    )


def _rollback_with_telemetry(session: Session, telemetry: _AuthRouteTelemetry) -> None:
    rollback_started_at = perf_counter()
    session.rollback()
    telemetry.mark("db.rollback_ms", rollback_started_at)


def _build_token_response(
    *,
    service: AuthService,
    session: Session,
    request: Request | None,
    telemetry: _AuthRouteTelemetry,
    user: User,
    issued_session: IssuedAuthSession,
) -> TokenResponse:
    user_public_started_at = perf_counter()
    user_public = service.build_user_public(session, user)
    telemetry.mark("service.build_user_public_ms", user_public_started_at)
    permissions_started_at = perf_counter()
    permissions = service.resolve_user_permissions(request.app, user, session=session) if request is not None else []
    telemetry.mark("service.resolve_permissions_ms", permissions_started_at)
    landing_route_started_at = perf_counter()
    landing_route = service.resolve_landing_route(
        user,
        permissions=permissions,
        session=session,
    )
    telemetry.mark("service.resolve_landing_route_ms", landing_route_started_at)
    return TokenResponse(
        access_token=issued_session.access_token,
        refresh_token=issued_session.refresh_token,
        session_id=issued_session.session_id,
        expires_in=issued_session.expires_in,
        refresh_expires_in=issued_session.refresh_expires_in,
        user=user_public,
        permissions=permissions,
        landing_route=landing_route,
    )


def _request_client_context(request: Request | None, *, device_id: str | None = None) -> dict[str, str | None]:
    user_agent = None
    ip_address = None
    if request is not None:
        user_agent = request.headers.get("user-agent")
        ip_address = extract_client_ip(request)
    return {
        "device_id": device_id,
        "user_agent": user_agent,
        "ip_address": ip_address,
    }


def _record_login_attempt(
    request: Request | None,
    *,
    email: str,
    success: bool,
    user_id: str | None,
    device_id: str | None,
    failure_reason: str | None = None,
) -> None:
    if request is None:
        return
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        return
    from app.risk.security_monitoring_service import SecurityMonitoringService

    client_context = _request_client_context(request, device_id=device_id)
    try:
        SecurityMonitoringService(session_factory=session_factory).record_login_attempt(
            email=email,
            success=success,
            user_id=user_id,
            ip_address=client_context["ip_address"],
            user_agent=client_context["user_agent"],
            device_id=client_context["device_id"],
            path=str(request.url.path),
            failure_reason=failure_reason,
        )
    except Exception as exc:
        logger.warning(
            "auth.login.audit_failed email=%s success=%s error_type=%s error=%s",
            email,
            success,
            exc.__class__.__name__,
            str(exc),
        )


def _build_compliance_status(session: Session, user: User) -> UserComplianceStatus:
    policy_service = PolicyService(session)
    country_policy = policy_service.get_country_policy_for_user(user=user)
    missing = policy_service.list_missing_acceptances(user_id=user.id)
    wallet = WalletFundingService().ensure_wallet(session, user)
    is_verified = str(wallet.compliance_status or "").strip().lower() == "verified"
    return UserComplianceStatus(
        country_code=country_policy.country_code,
        country_policy_bucket=country_policy.bucket_type,
        deposits_enabled=country_policy.deposits_enabled,
        market_trading_enabled=country_policy.market_trading_enabled,
        platform_reward_withdrawals_enabled=country_policy.platform_reward_withdrawals_enabled,
        compliance_status=wallet.compliance_status,
        required_policy_acceptances_missing=len(missing),
        missing_policy_acceptances=[
            PolicyRequirementSummary(
                document_key=version.document.document_key,
                title=version.document.title,
                version_label=version.version_label,
                is_mandatory=version.document.is_mandatory,
                effective_at=version.effective_at,
            )
            for version in missing
        ],
        can_deposit=country_policy.deposits_enabled,
        can_withdraw_platform_rewards=country_policy.platform_reward_withdrawals_enabled,
        can_trade_market=country_policy.market_trading_enabled and is_verified,
    )


def _build_wallet_bootstrap(service: AuthService, session: Session, user: User) -> WalletAdaptiveOverviewView:
    wallet_payload = service.wallet_service.get_adaptive_overview(session, user)
    wallet_payload["competition_reward_balance"] = service.wallet_service.competition_reward_balance(session, user)
    wallet_payload["competition_reward_withdrawable_balance"] = (
        service.wallet_service.competition_reward_withdrawable_balance(
            session,
            user,
        )
    )
    return WalletAdaptiveOverviewView(**wallet_payload)


def _build_creator_bootstrap(session: Session, user: User) -> SessionBootstrapCreatorState | None:
    if user.account_type != PublicAccountType.CREATOR:
        return None
    profile = session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user.id))
    if profile is None:
        return None
    status_value = getattr(profile.status, "value", profile.status)
    return SessionBootstrapCreatorState(
        profile_id=profile.id,
        handle=profile.handle,
        display_name=profile.display_name,
        status=str(status_value),
        tier=profile.tier,
        is_active=status_value == CreatorProfileStatus.ACTIVE.value,
    )


def _build_coin_trader_bootstrap(session: Session, user: User) -> SessionBootstrapCoinTraderState | None:
    if user.account_type != PublicAccountType.COIN_TRADER:
        return None
    profile = session.scalar(select(CoinTraderProfile).where(CoinTraderProfile.user_id == user.id))
    if profile is None:
        return None
    status_value = str(profile.status)
    is_approved = status_value == "approved"
    return SessionBootstrapCoinTraderState(
        profile_id=profile.id,
        display_name=profile.display_name,
        status=status_value,
        tier=profile.tier,
        verification_level=profile.verification_level,
        is_approved=is_approved,
        can_trade=is_approved and user.is_active,
    )


def _build_onboarding_bootstrap(
    *,
    user: User,
    club_present: bool,
    creator: SessionBootstrapCreatorState | None,
    coin_trader: SessionBootstrapCoinTraderState | None,
) -> SessionBootstrapOnboardingState:
    if user.account_type == PublicAccountType.CREATOR:
        return SessionBootstrapOnboardingState(
            has_club=False,
            requires_club=False,
            suggested_route="/app/hub",
            available_actions=["creator_dashboard", "community"],
        )
    if user.account_type == PublicAccountType.COIN_TRADER:
        trader_route = (
            "/app/trader-dashboard" if coin_trader is not None and coin_trader.is_approved else "/app/coin-traders"
        )
        return SessionBootstrapOnboardingState(
            has_club=False,
            requires_club=False,
            suggested_route=trader_route,
            available_actions=["coin_trader_dashboard", "wallet", "coin_trader_marketplace"],
        )
    if club_present:
        return SessionBootstrapOnboardingState(
            has_club=True,
            requires_club=False,
            suggested_route="/app/club",
            available_actions=["club_workspace", "market", "competitions", "community"],
        )
    return SessionBootstrapOnboardingState(
        has_club=False,
        requires_club=True,
        suggested_route="/app/club",
        available_actions=["create_club", "join_club", "continue_as_fan"],
    )


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_auth_session_active(record: AuthSession, *, now: datetime) -> bool:
    return record.revoked_at is None and _as_aware_utc(record.expires_at) > now


def _current_auth_session(request: Request) -> AuthSession | None:
    current_session = getattr(request.state, "auth_session", None)
    return current_session if isinstance(current_session, AuthSession) else None


def _build_session_roles(
    *,
    user: User,
    club_present: bool,
    creator: SessionBootstrapCreatorState | None,
    coin_trader: SessionBootstrapCoinTraderState | None,
) -> list[str]:
    role_values = {
        str(getattr(user.role, "value", user.role)),
        str(getattr(user.account_type, "value", user.account_type)),
    }
    if club_present:
        role_values.add("club_owner")
    if creator is not None:
        role_values.add("creator")
    if coin_trader is not None:
        role_values.add("coin_trader")
    return sorted(value for value in role_values if value)


def _build_session_runtime_state() -> SessionBootstrapRuntimeState:
    return SessionBootstrapRuntimeState(
        strict_live=True,
        payments=SessionBootstrapPaymentsRuntimeState(
            paystack_enabled=False,
            korapay_enabled=provider_live_deposit_ready("korapay"),
            manual_payment_enabled=True,
        ),
    )


def _build_session_security_state(
    *,
    request: Request,
    records: list[AuthSession],
    user: User,
    now: datetime,
) -> SessionBootstrapSecurityState:
    current_session = _current_auth_session(request)
    return SessionBootstrapSecurityState(
        current_session_id=None if current_session is None else current_session.id,
        current_device_id=None if current_session is None else current_session.device_id,
        current_ip_address=None if current_session is None else current_session.ip_address,
        current_user_agent=None if current_session is None else current_session.user_agent,
        session_count=len(records),
        active_session_count=sum(1 for record in records if _is_auth_session_active(record, now=now)),
        last_login_at=user.last_login_at,
    )


def _build_session_views(
    *,
    request: Request,
    records: list[AuthSession],
    now: datetime,
) -> list[SessionBootstrapSessionView]:
    current_session = _current_auth_session(request)
    current_session_id = None if current_session is None else current_session.id
    return [
        SessionBootstrapSessionView(
            id=record.id,
            device_id=record.device_id,
            user_agent=record.user_agent,
            ip_address=record.ip_address,
            created_at=record.created_at,
            last_used_at=record.last_used_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
            is_current=record.id == current_session_id,
            is_active=_is_auth_session_active(record, now=now),
        )
        for record in records
    ]


def _list_user_auth_sessions(session: Session, user: User) -> list[AuthSession]:
    return list(
        session.scalars(
            select(AuthSession).where(AuthSession.user_id == user.id).order_by(AuthSession.created_at.desc()).limit(20)
        )
    )


def _build_session_bootstrap_response(
    *,
    service: AuthService,
    session: Session,
    request: Request,
    user: User,
) -> SessionBootstrapResponse:
    bootstrap = service.build_session_bootstrap_state(session, user, app=request.app)
    wallet = _build_wallet_bootstrap(service, session, user)
    compliance = _build_compliance_status(session, user)
    creator = _build_creator_bootstrap(session, user)
    coin_trader = _build_coin_trader_bootstrap(session, user)
    session_records = _list_user_auth_sessions(session, user)
    now = datetime.now(UTC)
    club_present = bootstrap.club is not None
    return SessionBootstrapResponse(
        user=bootstrap.user,
        roles=_build_session_roles(
            user=user,
            club_present=club_present,
            creator=creator,
            coin_trader=coin_trader,
        ),
        club=None if bootstrap.club is None else ClubProfileCore.model_validate(bootstrap.club),
        wallet=wallet,
        compliance=compliance,
        permissions=bootstrap.permissions,
        effective_role=bootstrap.user.role,
        account_type=bootstrap.user.account_type,
        active_organization_id=bootstrap.user.active_organization_id,
        active_organization_name=bootstrap.user.active_organization_name,
        active_organization_type=bootstrap.user.active_organization_type,
        creator=creator,
        coin_trader=coin_trader,
        onboarding=_build_onboarding_bootstrap(
            user=user,
            club_present=club_present,
            creator=creator,
            coin_trader=coin_trader,
        ),
        security=_build_session_security_state(
            request=request,
            records=session_records,
            user=user,
            now=now,
        ),
        sessions=_build_session_views(
            request=request,
            records=session_records,
            now=now,
        ),
        runtime=_build_session_runtime_state(),
    )


@legacy_router.post("/register", status_code=status.HTTP_410_GONE, include_in_schema=False)
@api_router.post("/register", status_code=status.HTTP_410_GONE, include_in_schema=False)
@api_v2_router.post("/register", status_code=status.HTTP_410_GONE, include_in_schema=False)
def register_user(
    payload: RegisterRequest | None = None,
    session: Session = Depends(get_session),
    request: Request = None,
) -> None:
    del payload, session, request
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Public signup moved to /auth/signup/user, /auth/signup/creator, or /auth/signup/trader.",
    )


def _issue_signup_session(
    *,
    service: AuthService,
    session: Session,
    request: Request,
    user: User,
    telemetry: _AuthRouteTelemetry,
) -> tuple[IssuedAuthSession, str | None]:
    confirmation_code = service.prepare_signup_confirmation(session, user=user)
    issued_session = service.issue_session_tokens(
        user,
        session=session,
        **_request_client_context(request),
        timing_recorder=telemetry.capture,
    )
    return issued_session, confirmation_code


def _submit_signup_compliance(
    session: Session,
    user: User,
    *,
    government_id_attachment_id: str,
    selfie_attachment_id: str,
    proof_of_address_attachment_id: str | None,
    country_confirmation: str,
) -> None:
    TreasuryService().submit_kyc(
        session,
        user=user,
        nin=None,
        bvn=None,
        address_line1="Signup compliance submission",
        address_line2=None,
        city=None,
        state=None,
        country=country_confirmation,
        id_document_attachment_id=None,
        government_id_attachment_id=government_id_attachment_id,
        selfie_attachment_id=selfie_attachment_id,
        proof_of_address_attachment_id=proof_of_address_attachment_id,
        country_confirmation=country_confirmation,
    )


@legacy_router.post("/signup/user", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@api_router.post("/signup/user", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@api_v2_router.post("/signup/user", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_user(
    payload: UserClubSignupRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    issued_session: IssuedAuthSession | None = None
    confirmation_code: str | None = None
    telemetry = _AuthRouteTelemetry("signup_user")
    user: User | None = None
    try:
        analytics.track_event(
            session, name="signup_started", user_id=None, metadata={"email": payload.email, "account_type": "user"}
        )
        user = service.register_user(
            session,
            email=payload.email,
            full_name=payload.full_name,
            phone_number=None,
            is_over_18=True,
            region_code=payload.country[:8],
            username=payload.username,
            password=payload.password,
            display_name=payload.full_name,
            account_type=PublicAccountType.USER,
            timing_recorder=telemetry.capture,
        )
        service.create_explicit_club_profile(
            session,
            user,
            club_name=payload.club_name,
            short_name=payload.club_short_tag,
            club_type=payload.club_type,
            country_code=payload.club_country,
            region_name=payload.club_state,
            city_name=payload.club_locality,
            crest_asset_ref=payload.crest_asset_ref,
            primary_color=payload.primary_color,
            secondary_color=payload.secondary_color,
        )
        user.preferred_position = payload.position
        user.nationality = payload.country
        _submit_signup_compliance(
            session,
            user,
            government_id_attachment_id=payload.compliance.government_id_attachment_id,
            selfie_attachment_id=payload.compliance.selfie_attachment_id,
            proof_of_address_attachment_id=payload.compliance.proof_of_address_attachment_id,
            country_confirmation=payload.compliance.country_confirmation,
        )
        issued_session, confirmation_code = _issue_signup_session(
            service=service,
            session=session,
            request=request,
            user=user,
            telemetry=telemetry,
        )
        analytics.track_event(session, name="signup_completed", user_id=user.id, metadata={"account_type": "user"})
        session.commit()
        session.refresh(user)
    except DuplicateUserError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception:
        _rollback_with_telemetry(session, telemetry)
        raise
    else:
        if confirmation_code is not None:
            try:
                email_started_at = perf_counter()
                service.send_signup_confirmation_email(user=user, confirmation_code=confirmation_code)
                telemetry.mark("email.signup_confirmation_ms", email_started_at)
            except Exception as exc:
                _log_email_dispatch_exception(flow="signup_confirmation", recipient=user.email, exc=exc)
    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@legacy_router.post("/signup/creator", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@api_router.post("/signup/creator", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@api_v2_router.post("/signup/creator", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_creator(
    payload: CreatorSignupRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    telemetry = _AuthRouteTelemetry("signup_creator")
    user: User | None = None
    issued_session: IssuedAuthSession | None = None
    confirmation_code: str | None = None
    try:
        user = service.register_user(
            session,
            email=payload.email,
            full_name=payload.creator_name,
            phone_number=None,
            is_over_18=True,
            region_code=payload.country[:8],
            username=payload.username,
            password=payload.password,
            display_name=payload.creator_name,
            account_type=PublicAccountType.CREATOR,
            timing_recorder=telemetry.capture,
        )
        session.add(
            CreatorProfile(
                user_id=user.id,
                handle=payload.username,
                display_name=payload.creator_name,
                tier="community",
                status=CreatorProfileStatus.ACTIVE,
                payout_config_json={
                    "category": payload.category,
                    "country": payload.country,
                    "main_club_supported": payload.main_club_supported,
                    "primary_language": payload.primary_language,
                    "avatar_asset_ref": payload.avatar_asset_ref,
                    "banner_asset_ref": payload.banner_asset_ref,
                    "monetization": payload.monetization,
                },
            )
        )
        issued_session, confirmation_code = _issue_signup_session(
            service=service,
            session=session,
            request=request,
            user=user,
            telemetry=telemetry,
        )
        session.commit()
        session.refresh(user)
    except DuplicateUserError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        if confirmation_code is not None:
            try:
                service.send_signup_confirmation_email(user=user, confirmation_code=confirmation_code)
            except Exception as exc:
                _log_email_dispatch_exception(flow="signup_confirmation", recipient=user.email, exc=exc)
    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@legacy_router.post("/signup/trader", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@api_router.post("/signup/trader", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@api_v2_router.post("/signup/trader", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_trader(
    payload: TraderSignupRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    telemetry = _AuthRouteTelemetry("signup_trader")
    user: User | None = None
    issued_session: IssuedAuthSession | None = None
    confirmation_code: str | None = None
    try:
        user = service.register_user(
            session,
            email=payload.email,
            full_name=payload.full_name,
            phone_number=payload.phone_number,
            is_over_18=True,
            region_code=payload.country[:8],
            username=payload.trading_alias,
            password=payload.password,
            display_name=payload.trading_alias,
            account_type=PublicAccountType.COIN_TRADER,
            timing_recorder=telemetry.capture,
        )
        trader_service = TraderService(session)
        trader_service.ensure_profile(
            user,
            trading_alias=payload.trading_alias,
            preferred_currency=payload.preferred_currency,
            trading_experience=payload.trading_experience,
            interests=payload.interests,
            wallet_label=payload.wallet_label,
        )
        trader_service.ensure_security(
            user,
            totp_secret=payload.totp_secret,
            totp_code=payload.totp_code,
            recovery_phrase_hash=payload.recovery_phrase_hash,
            security_pin_hash=payload.security_pin_hash,
        )
        _submit_signup_compliance(
            session,
            user,
            government_id_attachment_id=payload.compliance.government_id_attachment_id,
            selfie_attachment_id=payload.compliance.selfie_attachment_id,
            proof_of_address_attachment_id=payload.compliance.proof_of_address_attachment_id,
            country_confirmation=payload.compliance.country_confirmation,
        )
        issued_session, confirmation_code = _issue_signup_session(
            service=service,
            session=session,
            request=request,
            user=user,
            telemetry=telemetry,
        )
        session.commit()
        session.refresh(user)
    except (DuplicateUserError, TraderAccessError) as exc:
        _rollback_with_telemetry(session, telemetry)
        status_code = status.HTTP_409_CONFLICT if isinstance(exc, DuplicateUserError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        if confirmation_code is not None:
            try:
                service.send_signup_confirmation_email(user=user, confirmation_code=confirmation_code)
            except Exception as exc:
                _log_email_dispatch_exception(flow="signup_confirmation", recipient=user.email, exc=exc)
    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@legacy_router.post("/login", response_model=TokenResponse)
@api_router.post("/login", response_model=TokenResponse)
@api_v2_router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    session: Session = Depends(get_session),
    request: Request = None,
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    telemetry = _AuthRouteTelemetry("login")
    issued_session: IssuedAuthSession | None = None
    user: User | None = None
    telemetry.log_entry(
        method=request.method if request is not None else "POST",
        path=str(request.url.path) if request is not None else "/auth/login",
        modules_hydrated=getattr(request.app.state, "modules_hydrated", None) if request is not None else None,
    )
    try:
        login_started_at = perf_counter()
        user = service.authenticate_user(
            session,
            email=payload.email,
            password=payload.password,
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.authenticate_user_ms", login_started_at)
        analytics_success_started_at = perf_counter()
        analytics.track_event(session, name="login_success", user_id=user.id, metadata={})
        telemetry.mark("analytics.login_success_ms", analytics_success_started_at)
        token_started_at = perf_counter()
        issued_session = service.issue_session_tokens(
            user,
            session=session,
            **_request_client_context(request, device_id=x_device_id),
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.issue_access_token_ms", token_started_at)
        commit_started_at = perf_counter()
        session.commit()
        telemetry.mark("db.commit_ms", commit_started_at)
        refresh_started_at = perf_counter()
        session.refresh(user)
        telemetry.mark("db.refresh_user_ms", refresh_started_at)
    except InvalidCredentialsError as exc:
        analytics_failure_started_at = perf_counter()
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        telemetry.mark("analytics.login_failure_ms", analytics_failure_started_at)
        _rollback_with_telemetry(session, telemetry)
        _record_login_attempt(
            request,
            email=payload.email,
            success=False,
            user_id=None,
            device_id=x_device_id,
            failure_reason=str(exc),
        )
        telemetry.log_failure(status_code=status.HTTP_401_UNAUTHORIZED, user_id=None, error=str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        analytics_failure_started_at = perf_counter()
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        telemetry.mark("analytics.login_failure_ms", analytics_failure_started_at)
        _rollback_with_telemetry(session, telemetry)
        _record_login_attempt(
            request,
            email=payload.email,
            success=False,
            user_id=user.id if user is not None else None,
            device_id=x_device_id,
            failure_reason=str(exc),
        )
        telemetry.log_failure(
            status_code=status.HTTP_400_BAD_REQUEST, user_id=user.id if user is not None else None, error=str(exc)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _rollback_with_telemetry(session, telemetry)
        _record_login_attempt(
            request,
            email=payload.email,
            success=False,
            user_id=user.id if user is not None else None,
            device_id=x_device_id,
            failure_reason=str(exc),
        )
        telemetry.log_failure(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise
    _record_login_attempt(
        request,
        email=payload.email,
        success=True,
        user_id=user.id,
        device_id=x_device_id,
    )
    telemetry.log_success(status_code=status.HTTP_200_OK, user_id=user.id)

    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@legacy_router.post("/refresh", response_model=TokenResponse)
@api_router.post("/refresh", response_model=TokenResponse)
def refresh_auth_session(
    payload: RefreshTokenRequest,
    request: Request,
    session: Session = Depends(get_session),
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> TokenResponse:
    service = _build_auth_service(request)
    telemetry = _AuthRouteTelemetry("refresh")
    issued_session: IssuedAuthSession | None = None
    user: User | None = None
    telemetry.log_entry(
        method=request.method,
        path=str(request.url.path),
        modules_hydrated=getattr(request.app.state, "modules_hydrated", None),
    )
    try:
        refresh_started_at = perf_counter()
        user, issued_session = service.refresh_session_tokens(
            session,
            refresh_token=payload.refresh_token,
            **_request_client_context(request, device_id=x_device_id),
            timing_recorder=telemetry.capture,
        )
        telemetry.mark("service.refresh_session_tokens_ms", refresh_started_at)
        commit_started_at = perf_counter()
        session.commit()
        telemetry.mark("db.commit_ms", commit_started_at)
        refresh_user_started_at = perf_counter()
        session.refresh(user)
        telemetry.mark("db.refresh_user_ms", refresh_user_started_at)
    except (InvalidRefreshTokenError, InvalidSessionError) as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(
            status_code=status.HTTP_401_UNAUTHORIZED,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(
            status_code=status.HTTP_400_BAD_REQUEST,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _rollback_with_telemetry(session, telemetry)
        telemetry.log_failure(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            user_id=user.id if user is not None else None,
            error=str(exc),
        )
        raise
    logger.info(
        "auth.token.refresh user_id=%s session_id=%s device_id=%s",
        user.id,
        issued_session.session_id if issued_session is not None else None,
        x_device_id,
    )
    telemetry.log_success(status_code=status.HTTP_200_OK, user_id=user.id)
    return _build_token_response(
        service=service,
        session=session,
        request=request,
        telemetry=telemetry,
        user=user,
        issued_session=issued_session,
    )


@legacy_router.post("/logout", response_model=ActionStatusResponse)
@api_router.post("/logout", response_model=ActionStatusResponse)
def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    auth_session = getattr(request.state, "auth_session", None)
    session_id = getattr(auth_session, "id", None)
    if not isinstance(session_id, str) or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated session is invalid.")
    try:
        service.revoke_session(
            session,
            session_id=session_id,
            user_id=current_user.id,
            reason="logout",
        )
        session.commit()
    except InvalidSessionError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    logger.info("auth.session.logout user_id=%s session_id=%s", current_user.id, session_id)
    return ActionStatusResponse(detail="Logged out successfully.")


@legacy_router.post("/confirm-email", response_model=ActionStatusResponse)
def confirm_email(
    payload: ConfirmEmailRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    try:
        service.confirm_email_address(session, code=payload.code)
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ActionStatusResponse(detail="Email address confirmed.")


@legacy_router.post("/recovery/request", response_model=ActionStatusResponse)
def request_account_recovery(
    payload: AccountRecoveryRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    analytics = AnalyticsService()
    user = None
    recovery_code = None
    try:
        user, recovery_code = service.prepare_account_recovery(session, email=payload.email)
        session.commit()
    except AuthError as exc:
        analytics.track_event(session, name="login_failure", user_id=None, metadata={"email": payload.email})
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if user is not None and recovery_code is not None:
        try:
            service.send_account_recovery_email(user=user, recovery_code=recovery_code)
        except Exception as exc:
            _log_email_dispatch_exception(flow="account_recovery", recipient=user.email, exc=exc)

    return ActionStatusResponse(detail="If an account exists for that email, recovery instructions have been sent.")


@legacy_router.post("/recovery/reset", response_model=ActionStatusResponse)
def reset_account_with_recovery(
    payload: AccountRecoveryResetRequest,
    session: Session = Depends(get_session),
    request: Request = None,
) -> ActionStatusResponse:
    service = _build_auth_service(request)
    try:
        service.reset_password_with_recovery(session, code=payload.code, new_password=payload.new_password)
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ActionStatusResponse(detail="Account recovery completed.")


@router.get("/api/session/bootstrap", response_model=SessionBootstrapResponse)
def get_session_bootstrap(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SessionBootstrapResponse:
    service = _build_auth_service(request)
    try:
        response = _build_session_bootstrap_response(
            service=service,
            session=session,
            request=request,
            user=current_user,
        )
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return response


@router.get("/api/profile", response_model=CurrentUserResponse)
def read_live_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    return AuthService().get_current_user_profile(session, current_user, app=request.app)


@router.patch("/api/profile", response_model=CurrentUserResponse)
def update_live_profile(
    payload: CurrentUserUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    service = AuthService()
    try:
        service.update_current_user_profile(
            session,
            user=current_user,
            payload=payload,
        )
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return service.get_current_user_profile(session, current_user, app=request.app)


@router.get("/api/profile/security", response_model=SessionBootstrapSecurityState)
def read_profile_security(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SessionBootstrapSecurityState:
    records = _list_user_auth_sessions(session, current_user)
    return _build_session_security_state(
        request=request,
        records=records,
        user=current_user,
        now=datetime.now(UTC),
    )


@router.get("/api/profile/sessions", response_model=list[SessionBootstrapSessionView])
def read_profile_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[SessionBootstrapSessionView]:
    return _build_session_views(
        request=request,
        records=_list_user_auth_sessions(session, current_user),
        now=datetime.now(UTC),
    )


@router.get("/api/club/current", response_model=ClubProfileCore)
def read_current_club(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubProfileCore:
    bootstrap = AuthService().build_session_bootstrap_state(session, current_user, app=request.app)
    if bootstrap.club is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The authenticated account does not have an active club.",
        )
    return ClubProfileCore.model_validate(bootstrap.club)


@api_router.get("/me", response_model=CurrentUserResponse)
def read_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    return AuthService().get_current_user_profile(session, current_user, app=request.app)


@api_router.patch("/me", response_model=CurrentUserResponse)
def update_current_user_profile(
    payload: CurrentUserUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    service = AuthService()
    try:
        service.update_current_user_profile(
            session,
            user=current_user,
            payload=payload,
        )
        session.commit()
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return service.get_current_user_profile(session, current_user, app=request.app)


@api_router.post("/change-password", response_model=CurrentUserResponse)
def change_current_user_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CurrentUserResponse:
    service = AuthService()
    try:
        service.change_password(session, user=current_user, payload=payload)
        session.commit()
        session.refresh(current_user)
        return service.get_current_user_profile(session, current_user, app=request.app)
    except InvalidCredentialsError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


router.include_router(legacy_router)
router.include_router(api_router)
router.include_router(api_v2_router)
