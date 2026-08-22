from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.competition_constants import CompetitionFundingMode
from app.economy.competition_funding_policy import CompetitionFundingPolicyError, validate_competition_funding_contract
from app.economy.hosted_competition_coin_escrow import HostedCompetitionCoinEscrowError, HostedCompetitionCoinEscrowService
from app.hosted_competition_engine.schemas import HostedCompetitionCreate
from app.hosted_competition_engine.service import HostedCompetitionError, HostedCompetitionService
from app.models.admin_rules import AdminRewardRule
from app.models.hosted_competition import (
    CompetitionTemplate,
    HostedCompetitionSettlement,
    HostedCompetitionStatus,
    UserHostedCompetition,
)
from app.models.wallet import LedgerUnit
from app.wallets.service import InsufficientBalanceError, WalletService


class CoinAwareHostedCompetitionService(HostedCompetitionService):
    def __init__(self, session: Session, wallet_service: WalletService | None = None) -> None:
        super().__init__(session=session, wallet_service=wallet_service)

    def _active_platform_fee_bps(self) -> int:
        rule = self.session.scalar(
            select(AdminRewardRule)
            .where(AdminRewardRule.active.is_(True))
            .order_by(AdminRewardRule.updated_at.desc())
        )
        return int(rule.competition_platform_fee_bps if rule is not None else 3000)

    def create_competition(self, *, host, payload, created_by_admin=None, gtex_hosted: bool = False):
        mode = self._funding_mode(payload)
        if mode is CompetitionFundingMode.FANCOIN_ENTRY_POOL:
            competition, template, host_participation_created = super().create_competition(
                host=host,
                payload=payload,
                created_by_admin=created_by_admin,
                gtex_hosted=gtex_hosted,
            )
            metadata = dict(competition.metadata_json or {})
            metadata["funding_mode"] = mode.value
            metadata["platform_fee_bps"] = self._active_platform_fee_bps()
            metadata["platform_fee_policy_frozen"] = True
            competition.funding_mode = mode
            competition.metadata_json = metadata
            self.session.flush()
            return competition, template, host_participation_created

        if mode is not CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE:
            raise HostedCompetitionError("Unsupported hosted competition funding mode.")
        if gtex_hosted and created_by_admin is None:
            raise HostedCompetitionError("GTEX-hosted Coin-prize competitions require an admin creator.")

        template = self.get_template_by_key(payload.template_key)
        if template is None or not template.is_user_hostable:
            raise HostedCompetitionError("Competition template was not found or is not hostable.")
        slug = (payload.slug or payload.title).strip().lower().replace(" ", "-")
        if not slug:
            raise HostedCompetitionError("Competition slug cannot be empty.")
        entry_fee = self._normalize_amount(getattr(payload, "entry_fee_fancoin", None) or 0)
        gross_prize = self._normalize_amount(getattr(payload, "reward_pool_coin", None) or 0)
        if entry_fee != Decimal("0.0000"):
            raise HostedCompetitionError(
                "Host-funded GTEX Coin competitions cannot charge participant entry Coin or FanCoin."
            )
        try:
            validate_competition_funding_contract(
                mode=mode,
                currency=LedgerUnit.COIN,
                participant_entry_amount=Decimal("0.0000"),
                host_prize_amount=gross_prize,
            )
        except CompetitionFundingPolicyError as exc:
            raise HostedCompetitionError(str(exc)) from exc

        max_participants = int(payload.max_participants or template.participants)
        platform_fee_bps = self._active_platform_fee_bps()
        platform_fee = self._normalize_amount(gross_prize * Decimal(platform_fee_bps) / Decimal("10000"))
        net_prize = self._normalize_amount(gross_prize - platform_fee)
        if net_prize <= Decimal("0.0000"):
            raise HostedCompetitionError(
                "Host-funded GTEX Coin prize must leave a positive net prize after platform fees."
            )
        metadata = self._metadata_with_join_rules(
            payload=payload,
            visibility=str(payload.visibility or "public").strip().lower(),
            gtex_hosted=gtex_hosted,
        )
        metadata["funding_mode"] = mode.value
        metadata["platform_fee_policy_frozen"] = True
        visibility = str(payload.visibility or "public").strip().lower()
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
            funding_mode=mode,
            entry_fee_fancoin=Decimal("0.0000"),
            reward_pool_fancoin=Decimal("0.0000"),
            reward_pool_coin=gross_prize,
            host_funding_required_coin=gross_prize,
            host_funding_escrowed_coin=Decimal("0.0000"),
            platform_fee_amount=platform_fee,
            metadata_json={
                **metadata,
                "created_by_user_id": created_by_admin.id if created_by_admin is not None else host.id,
                "prize_currency": LedgerUnit.COIN.value,
                "gross_prize_coin": str(gross_prize),
                "net_prize_coin": str(net_prize),
                "platform_fee_bps": platform_fee_bps,
            },
            status=HostedCompetitionStatus.OPEN,
        )
        self.session.add(competition)
        self.session.flush()

        escrow_service = HostedCompetitionCoinEscrowService(self.session, self.wallet_service)
        try:
            escrow_service.fund_from_host(competition=competition, host=host, gross_prize=gross_prize)
        except (InsufficientBalanceError, HostedCompetitionCoinEscrowError) as exc:
            self.session.delete(competition)
            self.session.flush()
            raise HostedCompetitionError(str(exc)) from exc
        participant = self._create_entry_participant(competition=competition, user=host, role="host")
        participant.entry_fee_fancoin = Decimal("0.0000")
        participant.metadata_json = {
            **participant.metadata_json,
            "payment_status": "host_funded",
            "prize_currency": LedgerUnit.COIN.value,
        }
        self.session.flush()
        return competition, template, True

    def finance_snapshot(self, competition_id: str):
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        if self._competition_mode(competition) is CompetitionFundingMode.FANCOIN_ENTRY_POOL:
            return super().finance_snapshot(competition_id)
        escrow_service = HostedCompetitionCoinEscrowService(self.session, self.wallet_service)
        escrow_balance = escrow_service.available_balance(competition)
        gross_prize = self._normalize_amount(competition.reward_pool_coin)
        fee = self._normalize_amount(competition.platform_fee_amount)
        settlements = list(
            self.session.scalars(
                select(HostedCompetitionSettlement).where(HostedCompetitionSettlement.competition_id == competition.id)
            ).all()
        )
        settled_prizes = self._normalize_amount(
            sum((row.net_amount for row in settlements if row.settlement_type == "prize"), Decimal("0.0000"))
        )
        settled_platform_fee = self._normalize_amount(
            sum((row.net_amount for row in settlements if row.settlement_type == "platform_fee"), Decimal("0.0000"))
        )
        return {
            "currency": LedgerUnit.COIN.value,
            "escrow_balance": escrow_balance,
            "gross_prize": gross_prize,
            "projected_reward_pool": self._normalize_amount(gross_prize - fee),
            "projected_platform_fee": fee,
            "settled_prizes": settled_prizes,
            "settled_platform_fee": settled_platform_fee,
            "status": competition.status.value,
        }
