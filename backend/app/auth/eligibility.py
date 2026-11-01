from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubLifecycleStatus, ClubProfile
from app.models.coin_trader import CoinTraderProfile, CoinTraderProfileStatus
from app.models.user import PublicAccountType, User


class AccountEligibilityError(ValueError):
    pass


class AccountTypeConflictError(AccountEligibilityError):
    pass


class TradingEligibilityError(AccountEligibilityError):
    pass


class AccountEligibilityService:
    @staticmethod
    def assert_can_trade_player_shares(user: User) -> None:
        """Football player share trading is exclusive to normal USER and CREATOR accounts."""
        if user.account_type == PublicAccountType.COIN_TRADER:
            raise AccountTypeConflictError("Coin trader accounts cannot participate in player share trading.")
        if not user.is_active:
            raise TradingEligibilityError("Account is inactive.")

    @staticmethod
    def assert_can_operate_coin_trader(user: User, session: Session) -> None:
        profile = session.scalar(select(CoinTraderProfile).where(CoinTraderProfile.user_id == user.id))
        AccountEligibilityService.assert_can_trade_coin_marketplace(user, profile)

    @staticmethod
    def assert_can_trade_coin_marketplace(user: User, profile: CoinTraderProfile | None) -> None:
        """Coin trader operations require an approved, fully verified, active CoinTraderProfile."""
        if user.account_type != PublicAccountType.COIN_TRADER:
            raise AccountTypeConflictError("Coin trader account access is required.")
        if profile is None:
            raise TradingEligibilityError("Coin trader desk profile not found. Complete trader verification to activate your desk.")
        if profile.status == CoinTraderProfileStatus.FROZEN.value:
            raise TradingEligibilityError("Coin trader desk is frozen by platform compliance.")
        if profile.status == CoinTraderProfileStatus.SUSPENDED.value:
            raise TradingEligibilityError("Coin trader desk is suspended by platform administration.")
        if profile.status == CoinTraderProfileStatus.REJECTED.value:
            raise TradingEligibilityError("Coin trader desk verification was rejected.")
        if profile.status != CoinTraderProfileStatus.APPROVED.value:
            raise TradingEligibilityError("Coin trader desk is pending identity verification.")
        if profile.verification_level not in {"fully_verified", "verified", "standard"} and not profile.verified_at:
            raise TradingEligibilityError("Coin trader desk must complete authoritative identity verification before trading.")

    @staticmethod
    def assert_can_own_club(user: User) -> None:
        """Coin traders cannot become club owners."""
        if user.account_type == PublicAccountType.COIN_TRADER:
            raise AccountTypeConflictError("Coin trader accounts cannot own football clubs.")

    @staticmethod
    def assert_can_apply_for_creator(user: User, session: Session) -> None:
        """Only ordinary USER accounts without active clubs may apply for Creator status."""
        if user.account_type == PublicAccountType.COIN_TRADER:
            raise AccountTypeConflictError("Coin trader accounts cannot be promoted to Creator.")
        if user.account_type == PublicAccountType.CREATOR or user.account_type != PublicAccountType.USER:
            raise AccountTypeConflictError("creator_promotion_requires_normal_account")

        owned_active_club = session.scalar(
            select(ClubProfile.id)
            .where(
                ClubProfile.owner_user_id == user.id,
                ClubProfile.lifecycle_status == ClubLifecycleStatus.ACTIVE,
            )
            .limit(1)
        )
        if owned_active_club is not None:
            raise AccountTypeConflictError("club_ownership_prevents_creator_promotion")

    @staticmethod
    def assert_can_withdraw(user: User, session: Session, amount: Decimal) -> None:
        """Distinguish withdrawal verification requirements by account lane.

        Ordinary USER accounts are not blocked by routine identity verification.
        Coin Traders must be accredited (verified and active).
        """
        del amount
        if user.account_type == PublicAccountType.COIN_TRADER:
            profile = session.scalar(
                select(CoinTraderProfile).where(CoinTraderProfile.user_id == user.id)
            )
            if profile is None or profile.status != CoinTraderProfileStatus.APPROVED.value:
                raise TradingEligibilityError("Coin trader identity verification must be completed before requesting withdrawals.")
