from __future__ import annotations

from decimal import Decimal

from app.economy.competition_funding_policy import (
    CompetitionFundingMode,
    CompetitionFundingPolicyError,
    funding_mode_from_prize_mode,
    validate_competition_funding_contract,
)
from app.economy.hosted_competition_coin_escrow import (
    HostedCompetitionCoinEscrowError,
    HostedCompetitionCoinEscrowService,
)
from app.hosted_competition_engine.service import HostedCompetitionError, HostedCompetitionService
from app.models.hosted_competition import HostedCompetitionStatus
from app.models.wallet import LedgerUnit
from app.wallets.service import InsufficientBalanceError


class CoinAwareHostedCompetitionService(HostedCompetitionService):
    """Hosted competition service with the Phase A funding constitution enforced."""

    def _funding_mode(self, payload) -> CompetitionFundingMode:
        requested = getattr(payload, "funding_mode", None)
        if requested:
            try:
                return funding_mode_from_prize_mode(str(requested))
            except CompetitionFundingPolicyError as exc:
                raise HostedCompetitionError(str(exc)) from exc
        return CompetitionFundingMode.FANCOIN_ENTRY_POOL

    def create_competition(
        self,
        *,
        host,
        payload,
        created_by_admin=None,
        gtex_hosted: bool = False,
    ):
        mode = self._funding_mode(payload)
        if mode is CompetitionFundingMode.FANCOIN_ENTRY_POOL:
            return super().create_competition(
                host=host,
                payload=payload,
                created_by_admin=created_by_admin,
                gtex_hosted=gtex_hosted,
            )

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
            raise HostedCompetitionError("Host-funded GTEX Coin competitions cannot charge participant entry Coin or FanCoin.")
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
            raise HostedCompetitionError("Host-funded GTEX Coin prize must leave a positive net prize after platform fees.")
        metadata = self._metadata_with_join_rules(
            payload=payload,
            visibility=str(payload.visibility or "public").strip().lower(),
            gtex_hosted=gtex_hosted,
        )
        visibility = str(payload.visibility or "public").strip().lower()
        if metadata.get("join_passcode_required") is True and visibility == "public":
            visibility = "passcode"

        competition = self.__class__.__mro__[1].__dict__["__dataclass_fields__"] if False else None
        # Use the canonical SQLAlchemy model directly to avoid invoking legacy FanCoin prepayment.
        from app.models.hosted_competition import UserHostedCompetition

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
            funding_actor = host
            escrow_service.fund_from_host(
                competition=competition,
                host=funding_actor,
                gross_prize=gross_prize,
            )
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


__all__ = ["CoinAwareHostedCompetitionService"]
