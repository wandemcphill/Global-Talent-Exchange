from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.admin_engine.service import AdminEngineService
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
from app.models.hosted_competition import (
    HostedCompetitionSettlement,
    HostedCompetitionSettlementStatus,
    HostedCompetitionStanding,
    HostedCompetitionStatus,
    UserHostedCompetition,
)
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.wallets.service import InsufficientBalanceError


class CoinAwareHostedCompetitionService(HostedCompetitionService):
    """Hosted competition service with the Phase A funding constitution enforced."""

    def _active_platform_fee_bps(self) -> int:
        rule = next(iter(AdminEngineService(self.session).list_reward_rules(active_only=True)), None)
        if rule is None:
            raise HostedCompetitionError("No active competition platform fee policy is configured.")
        fee_bps = int(rule.competition_platform_fee_bps)
        if fee_bps < 0 or fee_bps > 3000:
            raise HostedCompetitionError("Configured competition platform fee is outside the allowed policy range.")
        return fee_bps

    def _frozen_platform_fee_bps(self, competition: UserHostedCompetition) -> int:
        raw = str((competition.metadata_json or {}).get("platform_fee_bps") or "").strip()
        if not raw:
            raise HostedCompetitionError("Hosted competition is missing its frozen platform fee policy.")
        try:
            fee_bps = int(raw)
        except ValueError as exc:
            raise HostedCompetitionError("Hosted competition has an invalid frozen platform fee policy.") from exc
        if fee_bps < 0 or fee_bps > 3000:
            raise HostedCompetitionError("Hosted competition frozen platform fee is outside the allowed policy range.")
        return fee_bps

    def _funding_mode(self, payload) -> CompetitionFundingMode:
        requested = getattr(payload, "funding_mode", None)
        if requested:
            try:
                return funding_mode_from_prize_mode(str(requested))
            except CompetitionFundingPolicyError as exc:
                raise HostedCompetitionError(str(exc)) from exc
        return CompetitionFundingMode.FANCOIN_ENTRY_POOL

    def _competition_mode(self, competition: UserHostedCompetition) -> CompetitionFundingMode:
        try:
            value = (
                competition.funding_mode.value
                if hasattr(competition.funding_mode, "value")
                else competition.funding_mode
            )
            return CompetitionFundingMode(str(value))
        except ValueError as exc:
            raise HostedCompetitionError("Hosted competition has an unsupported funding mode.") from exc

    def create_competition(self, *, host, payload, created_by_admin=None, gtex_hosted: bool = False):
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

        participants = self.participants_for_competition(competition_id)
        escrow_service = HostedCompetitionCoinEscrowService(self.session, self.wallet_service)
        settled_prizes = self._normalize_amount(
            self.session.scalar(
                select(func.coalesce(func.sum(HostedCompetitionSettlement.net_amount), 0)).where(
                    HostedCompetitionSettlement.competition_id == competition_id,
                    HostedCompetitionSettlement.settlement_type == "prize",
                    HostedCompetitionSettlement.currency == LedgerUnit.COIN.value,
                )
            )
            or 0
        )
        settled_platform_fee = self._normalize_amount(
            self.session.scalar(
                select(func.coalesce(func.sum(HostedCompetitionSettlement.net_amount), 0)).where(
                    HostedCompetitionSettlement.competition_id == competition_id,
                    HostedCompetitionSettlement.settlement_type == "platform_fee",
                    HostedCompetitionSettlement.currency == LedgerUnit.COIN.value,
                )
            )
            or 0
        )
        return {
            "currency": "coin",
            "participant_count": len(participants),
            "entry_fee_fancoin": Decimal("0.0000"),
            "gross_collected": self._normalize_amount(competition.reward_pool_coin),
            "projected_reward_pool": self._normalize_amount(
                competition.reward_pool_coin - competition.platform_fee_amount
            ),
            "projected_platform_fee": self._normalize_amount(competition.platform_fee_amount),
            "escrow_balance": escrow_service.available_balance(competition),
            "settled_prizes": settled_prizes,
            "settled_platform_fee": settled_platform_fee,
            "status": competition.status.value if hasattr(competition.status, "value") else str(competition.status),
        }

    def finalize_competition(self, *, actor: User, competition_id: str, placements, note: str | None = None):
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError("Hosted competition was not found.")
        if self._competition_mode(competition) is CompetitionFundingMode.FANCOIN_ENTRY_POOL:
            return super().finalize_competition(
                actor=actor,
                competition_id=competition_id,
                placements=placements,
                note=note,
            )
        if competition.status == HostedCompetitionStatus.COMPLETED:
            raise HostedCompetitionError("Hosted competition has already been completed.")

        participants = {item.user_id for item in self.participants_for_competition(competition_id)}
        if not participants:
            raise HostedCompetitionError("Hosted competition has no participants.")
        placements = list(placements)
        if not placements:
            raise HostedCompetitionError("At least one placement is required to settle a hosted competition.")
        placement_user_ids = [str(item.get("user_id")) for item in placements]
        if len(set(placement_user_ids)) != len(placement_user_ids):
            raise HostedCompetitionError("Each placement must reference a distinct participant.")
        if any(user_id not in participants for user_id in placement_user_ids):
            raise HostedCompetitionError("A placement referenced a user that is not part of this competition.")
        ranks = [int(item.get("rank", 0) or 0) for item in placements]
        if len(set(ranks)) != len(ranks) or set(ranks) != set(range(1, len(ranks) + 1)):
            raise HostedCompetitionError("Placement ranks must be unique and contiguous starting at 1.")
        total_percent = sum(Decimal(str(item.get("payout_percent", 0))) for item in placements)
        if total_percent != Decimal("100.0000"):
            raise HostedCompetitionError("Total payout percent must equal 100 for a Coin-prize competition.")
        if any(Decimal(str(item.get("payout_percent", 0))) < Decimal("0.0000") for item in placements):
            raise HostedCompetitionError("Payout percent cannot be negative.")

        gross_prize = self._normalize_amount(competition.reward_pool_coin)
        platform_fee_bps = self._frozen_platform_fee_bps(competition)
        platform_fee = self._normalize_amount(gross_prize * Decimal(platform_fee_bps) / Decimal("10000"))
        net_prize = self._normalize_amount(gross_prize - platform_fee)
        payout_rows: list[tuple[User, Decimal]] = []
        total_payout = Decimal("0.0000")
        standings_by_user = {row.user_id: row for row in self.standings_for_competition(competition_id)}
        if not standings_by_user:
            for participant in self.participants_for_competition(competition_id):
                row = HostedCompetitionStanding(
                    competition_id=competition.id, user_id=participant.user_id, metadata_json={}
                )
                self.session.add(row)
                self.session.flush()
                standings_by_user[participant.user_id] = row

        for item in placements:
            user = self.session.get(User, str(item["user_id"]))
            if user is None:
                raise HostedCompetitionError("A placement referenced a missing user.")
            payout_percent = Decimal(str(item.get("payout_percent", 0)))
            payout = self._normalize_amount(net_prize * payout_percent / Decimal("100"))
            payout_rows.append((user, payout))
            total_payout += payout
            standing = standings_by_user[user.id]
            standing.final_rank = int(item.get("rank", 0))
            standing.payout_amount = payout
            standing.metadata_json = {**(standing.metadata_json or {}), "payout_percent": str(payout_percent)}

        rounding_residual = self._normalize_amount(net_prize - total_payout)
        if rounding_residual != Decimal("0.0000"):
            first_user, first_payout = payout_rows[0]
            adjusted = self._normalize_amount(first_payout + rounding_residual)
            if adjusted <= Decimal("0.0000"):
                raise HostedCompetitionError("Coin prize rounding produced an invalid payout.")
            payout_rows[0] = (first_user, adjusted)
            standings_by_user[first_user.id].payout_amount = adjusted

        escrow_service = HostedCompetitionCoinEscrowService(self.session, self.wallet_service)
        try:
            transaction_id = escrow_service.settle_distribution(
                competition=competition,
                payouts=[(user, payout) for user, payout in payout_rows if payout > Decimal("0.0000")],
                platform_fee=platform_fee,
                actor=actor,
            )
        except (HostedCompetitionCoinEscrowError, InsufficientBalanceError) as exc:
            raise HostedCompetitionError(str(exc)) from exc

        settlements: list[HostedCompetitionSettlement] = []
        for user, payout in payout_rows:
            if payout <= Decimal("0.0000"):
                continue
            settlement = HostedCompetitionSettlement(
                competition_id=competition.id,
                recipient_user_id=user.id,
                settlement_type="prize",
                status=HostedCompetitionSettlementStatus.SETTLED,
                currency=LedgerUnit.COIN.value,
                gross_amount=payout,
                platform_fee_amount=Decimal("0.0000"),
                net_amount=payout,
                ledger_transaction_id=transaction_id,
                note=note or "",
                settled_by_user_id=actor.id,
            )
            self.session.add(settlement)
            settlements.append(settlement)
        fee_settlement = HostedCompetitionSettlement(
            competition_id=competition.id,
            recipient_user_id=None,
            settlement_type="platform_fee",
            status=HostedCompetitionSettlementStatus.SETTLED,
            currency=LedgerUnit.COIN.value,
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
        self.session.flush()
        return competition, list(standings_by_user.values()), settlements


__all__ = ["CoinAwareHostedCompetitionService"]
