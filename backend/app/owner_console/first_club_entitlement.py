from __future__ import annotations

from decimal import Decimal
import logging
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.first_club_entitlement import FirstClubEntitlement
from app.models.user import PublicAccountType, User
from app.owner_console import ledger

logger = logging.getLogger(__name__)

LAUNCH_GRANT_GTEX = Decimal("2500.0000")
LAUNCH_GRANT_OWNER_LIMIT = 500
LAUNCH_GRANT_FAN = Decimal("1000.0000")


class FirstClubEntitlementError(Exception):
    def __init__(self, code: str, status_code: int = 400, detail: str | None = None) -> None:
        super().__init__(detail or code)
        self.code = code
        self.status_code = status_code
        self.detail = detail or code


def get_first_club_entitlement(session: Session, user_id: str) -> FirstClubEntitlement | None:
    return session.scalar(select(FirstClubEntitlement).where(FirstClubEntitlement.user_id == user_id))


def has_received_first_club_grant(session: Session, user_id: str) -> bool:
    return get_first_club_entitlement(session, user_id) is not None


def award_first_club_launch_grant(
    session: Session,
    user_id: str,
    club_id: str,
) -> tuple[FirstClubEntitlement | None, bool]:
    """Award the one-time first-club launch grant to a user's first club.

    Returns (entitlement, awarded_now).
    - If user already claimed their entitlement (or owns existing clubs), returns (entitlement, False).
    - If user is a Trader or Creator account, raises FirstClubEntitlementError(403).
    - Enforces DB uniqueness atomically to prevent race condition double-grants.
    """
    user = session.get(User, user_id)
    if user is None:
        raise FirstClubEntitlementError("user_not_found", 404)
    if user.account_type != PublicAccountType.USER:
        raise FirstClubEntitlementError("club_owner_account_type_required", 403)

    # Serialize campaign claims across workers. User uniqueness prevents a
    # duplicate entitlement; this transaction lock prevents exceeding 500.
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": 620611165001},
        )

    existing = get_first_club_entitlement(session, user_id)
    if existing is not None:
        logger.info(
            "first_club_entitlement.already_awarded user_id=%s club_id=%s original_club_id=%s",
            user_id,
            club_id,
            existing.club_id,
        )
        return existing, False

    campaign_claims = int(
        session.scalar(
            select(func.count(FirstClubEntitlement.id)).where(
                FirstClubEntitlement.gtex_grant_amount == LAUNCH_GRANT_GTEX
            )
        )
        or 0
    )
    eligible_for_campaign = campaign_claims < LAUNCH_GRANT_OWNER_LIMIT
    gtex_grant = LAUNCH_GRANT_GTEX if eligible_for_campaign else Decimal("0.0000")
    fan_grant = LAUNCH_GRANT_FAN if eligible_for_campaign else Decimal("0.0000")

    entitlement = FirstClubEntitlement(
        user_id=user_id,
        club_id=club_id,
        gtex_grant_amount=gtex_grant,
        fan_grant_amount=fan_grant,
    )

    try:
        with session.begin_nested():
            session.add(entitlement)
            session.flush()
    except IntegrityError:
        logger.warning(
            "first_club_entitlement.conflict_detected user_id=%s club_id=%s",
            user_id,
            club_id,
        )
        existing = get_first_club_entitlement(session, user_id)
        return existing, False

    if not eligible_for_campaign:
        logger.info(
            "first_club_entitlement.campaign_full user_id=%s club_id=%s claims=%s",
            user_id,
            club_id,
            campaign_claims,
        )
        return entitlement, False

    # Ring-fenced campaign credit: can only be spent on player signings.
    gtex_event = ledger.record(
        session,
        event_type="launch_grant",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=LAUNCH_GRANT_GTEX,
        balance_class="squad_grant",
        club_id=club_id,
        user_id=user_id,
        related_type="club",
        related_id=club_id,
        memo="GTEX first-500 squad signing grant (restricted, non-withdrawable)",
    )

    # Award welcome Fan Coin to user wallet
    fan_event = ledger.record(
        session,
        event_type="launch_grant",
        source=ledger.PLATFORM_GRANTS,
        destination=ledger.user_account(user_id),
        currency=ledger.FAN,
        gross=LAUNCH_GRANT_FAN,
        balance_class="promotional",
        user_id=user_id,
        memo="Welcome Fan Coin (promotional, non-withdrawable)",
    )

    entitlement.gtex_ledger_event_id = getattr(gtex_event, "id", None)
    entitlement.fan_ledger_event_id = getattr(fan_event, "id", None)
    session.flush()

    logger.info(
        "first_club_entitlement.awarded user_id=%s club_id=%s gtex_event=%s fan_event=%s",
        user_id,
        club_id,
        entitlement.gtex_ledger_event_id,
        entitlement.fan_ledger_event_id,
    )
    return entitlement, True
