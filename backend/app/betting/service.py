from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.betting.schemas import (
    BetHistoryResponse,
    BetIntegrityAlertView,
    BetMarketLineView,
    BetOddsResponse,
    BetPlaceRequest,
    BetPlaceResponse,
    BetPreferenceRequest,
    BetTicketView,
    BettingProfileView,
)
from app.models.betting import BetAuditLog, BetIntegrityAlert, BetTicket, BettingProfile
from app.models.competition_match import CompetitionMatch
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService

_AMOUNT_STEP = Decimal("0.0001")
_REGION_POLICIES: dict[str, dict[str, object]] = {
    "GLOBAL": {"enabled": True, "mode": "regulated", "max_bet": Decimal("50.0000"), "daily_loss_cap": Decimal("250.0000"), "cooldown_seconds": 20, "notes": ["Opt-in is required.", "Loss caps and cooldowns are enforced.", "Markets may freeze on integrity alerts."]},
    "NG": {"enabled": True, "mode": "regulated", "max_bet": Decimal("25.0000"), "daily_loss_cap": Decimal("100.0000"), "cooldown_seconds": 30, "notes": ["Stricter exposure limits apply in this region.", "Frequent betting patterns trigger extra review."]},
    "GB": {"enabled": True, "mode": "regulated", "max_bet": Decimal("100.0000"), "daily_loss_cap": Decimal("400.0000"), "cooldown_seconds": 15, "notes": ["Opt-in is required.", "Exposure limits are still applied in-app."]},
    "EU": {"enabled": True, "mode": "regulated", "max_bet": Decimal("100.0000"), "daily_loss_cap": Decimal("400.0000"), "cooldown_seconds": 15, "notes": ["Opt-in is required.", "Exposure limits are still applied in-app."]},
    "US": {"enabled": False, "mode": "restricted", "max_bet": Decimal("0.0000"), "daily_loss_cap": Decimal("0.0000"), "cooldown_seconds": 0, "notes": ["Bet placement is disabled pending local licensing checks."]},
}


def _normalize_probabilities(home: float, draw: float, away: float) -> tuple[int, int, int]:
    total = max(home + draw + away, 0.0001)
    raw = [int(round((home / total) * 100)), int(round((draw / total) * 100)), int(round((away / total) * 100))]
    raw[0] += 100 - sum(raw)
    return max(0, raw[0]), max(0, raw[1]), max(0, raw[2])


class BettingError(ValueError):
    pass


@dataclass(slots=True)
class BettingService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def update_preferences(self, *, actor: User, payload: BetPreferenceRequest) -> BettingProfileView:
        profile, policy = self._ensure_profile(actor, payload.region_code)
        profile.region_code = payload.region_code.upper()
        profile.is_opted_in = bool(payload.opt_in)
        profile.is_enabled = bool(payload.is_enabled)
        profile.compliance_mode = str(policy["mode"])
        profile.max_bet_amount = self._normalize(payload.max_bet_amount or Decimal(str(policy["max_bet"])))
        profile.daily_loss_cap = self._normalize(payload.daily_loss_cap or Decimal(str(policy["daily_loss_cap"])))
        metadata = dict(profile.metadata_json or {})
        metadata["age_gate_confirmed"] = bool(payload.age_gate_confirmed)
        profile.metadata_json = metadata
        self.session.flush()
        return self._profile_view(profile, actor, policy)

    def get_odds(self, *, actor: User, match_id: str, region_code: str | None = None) -> BetOddsResponse:
        profile, policy = self._ensure_profile(actor, region_code)
        snapshot = self._match_snapshot(match_id)
        market_status = "closed" if snapshot["completed"] else ("open" if bool(policy["enabled"]) and profile.is_enabled else "restricted")
        return BetOddsResponse(
            match_id=match_id,
            market_status=market_status,
            profile=self._profile_view(profile, actor, policy),
            markets=[] if market_status != "open" else self._market_lines(snapshot=snapshot, profile=profile, policy=policy),
            generated_at=datetime.now(timezone.utc),
        )

    def place_bet(self, *, actor: User, payload: BetPlaceRequest) -> BetPlaceResponse:
        profile, policy = self._ensure_profile(actor, payload.region_code)
        self._enforce_profile(actor=actor, profile=profile, policy=policy, payload=payload)
        snapshot = self._match_snapshot(payload.match_id)
        if snapshot["completed"]:
            raise BettingError("Betting is closed for completed matches.")
        line = self._market_line_for(snapshot=snapshot, profile=profile, policy=policy, bet_type=payload.bet_type, selection_key=payload.selection_key)
        stake = self._normalize(payload.stake_amount)
        max_bet = min(self._normalize(profile.max_bet_amount), self._normalize(Decimal(str(policy["max_bet"]))))
        if stake > max_bet:
            raise BettingError("Stake exceeds the region or profile bet limit.")
        if self._current_loss_exposure(profile) + stake > self._normalize(profile.daily_loss_cap):
            raise BettingError("Daily loss cap reached for this betting profile.")
        if profile.available_bet_balance < stake and payload.auto_fund_from_main:
            self._fund_bet_balance(actor=actor, profile=profile, amount=stake - profile.available_bet_balance)
        if profile.available_bet_balance < stake:
            raise BettingError("Bet balance is insufficient for this stake.")
        before_available = self._normalize(profile.available_bet_balance)
        before_locked = self._normalize(profile.locked_bet_balance)
        profile.available_bet_balance = self._normalize(profile.available_bet_balance - stake)
        profile.locked_bet_balance = self._normalize(profile.locked_bet_balance + stake)
        profile.last_bet_at = datetime.now(timezone.utc)
        cooldown_seconds = int(policy["cooldown_seconds"])
        if cooldown_seconds > 0:
            profile.cooldown_until = profile.last_bet_at + timedelta(seconds=cooldown_seconds)
        ticket = BetTicket(
            user_id=actor.id,
            match_id=payload.match_id,
            event_id=None,
            bet_type=payload.bet_type,
            selection_key=payload.selection_key,
            selection_label=line.label,
            region_code=profile.region_code,
            status="placed",
            stake_amount=stake,
            odds_decimal=self._normalize(line.odds_decimal),
            implied_probability=self._normalize(line.implied_probability),
            potential_payout_amount=self._normalize(stake * line.odds_decimal),
            market_demand_factor=self._normalize(line.market_demand_factor),
            risk_adjustment_factor=self._normalize(line.risk_adjustment_factor),
            settled_amount=Decimal("0.0000"),
            placed_at=datetime.now(timezone.utc),
            metadata_json={"teams": [snapshot["home_team_name"], snapshot["away_team_name"]]},
        )
        self.session.add(ticket)
        self.session.flush()
        self._audit(profile=profile, actor=actor, ticket=ticket, event_type="bet_placed", amount=stake, before_available=before_available, after_available=profile.available_bet_balance, before_locked=before_locked, after_locked=profile.locked_bet_balance, reference=f"bet:{ticket.id}:placed")
        alerts = self._market_alerts(match_id=payload.match_id, actor=actor, ticket=ticket)
        self.session.flush()
        return BetPlaceResponse(ticket=self._ticket_view(ticket), profile=self._profile_view(profile, actor, policy), alerts=[BetIntegrityAlertView.model_validate(item, from_attributes=True) for item in alerts])

    def history(self, *, actor: User) -> BetHistoryResponse:
        profile, policy = self._ensure_profile(actor, None)
        self._auto_settle_actor_matches(actor.id)
        items = list(self.session.scalars(select(BetTicket).where(BetTicket.user_id == actor.id).order_by(BetTicket.placed_at.desc())).all())
        alerts = list(self.session.scalars(select(BetIntegrityAlert).where(BetIntegrityAlert.user_id == actor.id).order_by(BetIntegrityAlert.created_at.desc()).limit(10)).all())
        return BetHistoryResponse(
            profile=self._profile_view(profile, actor, policy),
            items=[self._ticket_view(item) for item in items],
            alerts=[BetIntegrityAlertView.model_validate(item, from_attributes=True) for item in alerts],
        )

    def settle_match_bets(self, *, match_id: str) -> list[BetTicket]:
        snapshot = self._match_snapshot(match_id)
        if not snapshot["completed"]:
            return []
        if self._match_requires_review(snapshot):
            for ticket in self.session.scalars(select(BetTicket).where(BetTicket.match_id == match_id, BetTicket.status == "placed")).all():
                ticket.status = "review"
                ticket.result_summary = "Settlement held for integrity review."
                self._record_alert(match_id=match_id, actor_user_id=ticket.user_id, bet_id=ticket.id, issue_type="match_integrity_hold", risk_level="high", summary="Match settlement was held for manual integrity review.")
            self.session.flush()
            return list(self.session.scalars(select(BetTicket).where(BetTicket.match_id == match_id).order_by(BetTicket.placed_at.asc())).all())
        tickets = list(self.session.scalars(select(BetTicket).where(BetTicket.match_id == match_id, BetTicket.status == "placed").order_by(BetTicket.placed_at.asc())).all())
        for ticket in tickets:
            profile = self.session.scalar(select(BettingProfile).where(BettingProfile.user_id == ticket.user_id))
            if profile is None:
                continue
            result = self._resolve_ticket(ticket=ticket, snapshot=snapshot)
            before_available = self._normalize(profile.available_bet_balance)
            before_locked = self._normalize(profile.locked_bet_balance)
            profile.locked_bet_balance = self._normalize(profile.locked_bet_balance - ticket.stake_amount)
            ticket.settled_at = datetime.now(timezone.utc)
            ticket.result_summary = result["summary"]
            if result["status"] in {"won", "refunded"}:
                profile.available_bet_balance = self._normalize(profile.available_bet_balance + Decimal(str(result["credit"])))
            ticket.status = result["status"]
            ticket.settled_amount = self._normalize(Decimal(str(result["credit"])))
            ticket.result_json = dict(result)
            self._audit(profile=profile, actor=None, ticket=ticket, event_type="bet_settled", amount=ticket.settled_amount, before_available=before_available, after_available=profile.available_bet_balance, before_locked=before_locked, after_locked=profile.locked_bet_balance, reference=f"bet:{ticket.id}:settled")
        self.session.flush()
        return tickets

    def _ensure_profile(self, actor: User, region_code: str | None) -> tuple[BettingProfile, dict[str, object]]:
        region = (region_code or "GLOBAL").upper()
        policy = _REGION_POLICIES.get(region, _REGION_POLICIES["GLOBAL"])
        profile = self.session.scalar(select(BettingProfile).where(BettingProfile.user_id == actor.id))
        if profile is None:
            profile = BettingProfile(
                user_id=actor.id,
                region_code=region,
                compliance_mode=str(policy["mode"]),
                is_opted_in=False,
                is_enabled=True,
                available_bet_balance=Decimal("0.0000"),
                locked_bet_balance=Decimal("0.0000"),
                max_bet_amount=self._normalize(Decimal(str(policy["max_bet"]))),
                daily_loss_cap=self._normalize(Decimal(str(policy["daily_loss_cap"]))),
                metadata_json={},
            )
            self.session.add(profile)
            self.session.flush()
        elif region_code:
            profile.region_code = region
            profile.compliance_mode = str(policy["mode"])
        return profile, policy

    def _enforce_profile(self, *, actor: User, profile: BettingProfile, policy: dict[str, object], payload: BetPlaceRequest) -> None:
        if not bool(policy["enabled"]) or not profile.is_enabled:
            raise BettingError("Bet placement is disabled for this region or profile.")
        metadata = dict(profile.metadata_json or {})
        if payload.age_gate_confirmed:
            metadata["age_gate_confirmed"] = True
            profile.metadata_json = metadata
        if payload.opt_in_acknowledged:
            profile.is_opted_in = True
        if not profile.is_opted_in:
            raise BettingError("Betting opt-in is required before placing a stake.")
        if not bool(metadata.get("age_gate_confirmed")):
            raise BettingError("Age gate confirmation is required before placing a stake.")
        now = datetime.now(timezone.utc)
        if profile.self_excluded_until is not None and profile.self_excluded_until > now:
            raise BettingError("This betting profile is temporarily self-excluded.")
        if profile.cooldown_until is not None and profile.cooldown_until > now:
            raise BettingError("A cooldown is active for this betting profile.")

    def _profile_view(self, profile: BettingProfile, actor: User, policy: dict[str, object]) -> BettingProfileView:
        main_balance = self.wallet_service.get_wallet_summary(self.session, actor, currency=LedgerUnit.CREDIT).available_balance
        return BettingProfileView(
            user_id=actor.id,
            region_code=profile.region_code,
            compliance_mode=profile.compliance_mode,
            is_opted_in=profile.is_opted_in,
            is_enabled=profile.is_enabled,
            main_balance=self._normalize(main_balance),
            bet_balance=self._normalize(profile.available_bet_balance),
            locked_bet_balance=self._normalize(profile.locked_bet_balance),
            max_bet_amount=self._normalize(profile.max_bet_amount),
            daily_loss_cap=self._normalize(profile.daily_loss_cap),
            cooldown_until=profile.cooldown_until,
            self_excluded_until=profile.self_excluded_until,
            policy_notes=[str(item) for item in list(policy.get("notes") or [])],
        )

    def _ticket_view(self, ticket: BetTicket) -> BetTicketView:
        return BetTicketView.model_validate(ticket, from_attributes=True)

    def _fund_bet_balance(self, *, actor: User, profile: BettingProfile, amount: Decimal) -> None:
        amount = self._normalize(amount)
        if amount <= Decimal("0.0000"):
            return
        user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.CREDIT)
        betting_pool = self.wallet_service.ensure_betting_pool_account(self.session, LedgerUnit.CREDIT)
        self.wallet_service.append_transaction(
            self.session,
            postings=[LedgerPosting(account=user_account, amount=-amount), LedgerPosting(account=betting_pool, amount=amount)],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
            reference=f"betting-fund:{actor.id}:{datetime.now(timezone.utc).isoformat()}",
            description="Transfer from main wallet to betting balance",
            actor=actor,
            metadata={"channel": "betting_balance_funding"},
        )
        before_available = self._normalize(profile.available_bet_balance)
        profile.available_bet_balance = self._normalize(profile.available_bet_balance + amount)
        self._audit(profile=profile, actor=actor, ticket=None, event_type="bet_balance_funded", amount=amount, before_available=before_available, after_available=profile.available_bet_balance, before_locked=profile.locked_bet_balance, after_locked=profile.locked_bet_balance, reference="bet-balance-fund")

    def _market_lines(self, *, snapshot: dict[str, Any], profile: BettingProfile, policy: dict[str, object]) -> list[BetMarketLineView]:
        players = snapshot["players"]
        max_stake = min(self._normalize(profile.max_bet_amount), self._normalize(Decimal(str(policy["max_bet"]))))
        lines = [
            self._build_line(snapshot["match_id"], "match_winner", "home", snapshot["home_team_name"], Decimal(str(snapshot["probabilities"]["home"])), max_stake),
            self._build_line(snapshot["match_id"], "match_winner", "draw", "Draw", Decimal(str(snapshot["probabilities"]["draw"])), max_stake),
            self._build_line(snapshot["match_id"], "match_winner", "away", snapshot["away_team_name"], Decimal(str(snapshot["probabilities"]["away"])), max_stake),
            self._build_line(snapshot["match_id"], "over_under_goals", "over:2.5", "Over 2.5 Goals", Decimal(str(snapshot["totals"]["over_2_5"])), max_stake),
            self._build_line(snapshot["match_id"], "over_under_goals", "under:2.5", "Under 2.5 Goals", Decimal(str(snapshot["totals"]["under_2_5"])), max_stake),
        ]
        for item in players[:3]:
            lines.append(self._build_line(snapshot["match_id"], "first_goal_scorer", str(item["player_id"]), f"First Goal: {item['player_name']}", Decimal(str(item["first_goal_probability"])), max_stake))
        for item in players[:2]:
            lines.append(self._build_line(snapshot["match_id"], "player_performance", f"{item['player_id']}:rating_over:7.5", f"{item['player_name']} rating over 7.5", Decimal(str(item["rating_over_probability"])), max_stake))
        return lines

    def _market_line_for(self, *, snapshot: dict[str, Any], profile: BettingProfile, policy: dict[str, object], bet_type: str, selection_key: str) -> BetMarketLineView:
        for line in self._market_lines(snapshot=snapshot, profile=profile, policy=policy):
            if line.bet_type == bet_type and line.selection_key == selection_key:
                return line
        raise BettingError("Requested market selection is not available.")

    def _build_line(self, match_id: str, bet_type: str, selection_key: str, label: str, base_probability: Decimal, max_stake: Decimal) -> BetMarketLineView:
        market_stake = self._normalize(self.session.scalar(select(func.coalesce(func.sum(BetTicket.stake_amount), 0)).where(BetTicket.match_id == match_id, BetTicket.bet_type == bet_type)) or 0)
        selection_stake = self._normalize(self.session.scalar(select(func.coalesce(func.sum(BetTicket.stake_amount), 0)).where(BetTicket.match_id == match_id, BetTicket.bet_type == bet_type, BetTicket.selection_key == selection_key)) or 0)
        share = (selection_stake / market_stake) if market_stake > Decimal("0.0000") else Decimal("0.3300")
        demand_factor = self._normalize((share - Decimal("0.3300")) * Decimal("0.1200"))
        risk_factor = Decimal("0.0200") if share > Decimal("0.7000") else Decimal("0.0000")
        adjusted_probability = min(Decimal("0.9200"), max(Decimal("0.0500"), self._normalize(base_probability + demand_factor + risk_factor)))
        odds = self._normalize(Decimal("0.9400") / adjusted_probability)
        return BetMarketLineView(
            bet_type=bet_type,
            selection_key=selection_key,
            label=label,
            odds_decimal=odds,
            implied_probability=adjusted_probability,
            market_demand_factor=demand_factor,
            risk_adjustment_factor=self._normalize(risk_factor),
            max_stake=max_stake,
        )

    def _match_snapshot(self, match_id: str) -> dict[str, Any]:
        match = self.session.get(CompetitionMatch, match_id)
        if match is None:
            raise BettingError("Match not found for betting.")
        metadata = dict(match.metadata_json or {})
        preview = self._parse_preview(metadata.get("preview_request"))
        replay = self._parse_replay(metadata.get("replay_payload"))
        completed = replay is not None or str(match.status).lower() == "completed"
        home_name = str(preview.home_team.team_name) if preview is not None else (str(replay.summary.home_stats.team_name) if replay is not None else match.home_club_id)
        away_name = str(preview.away_team.team_name) if preview is not None else (str(replay.summary.away_stats.team_name) if replay is not None else match.away_club_id)
        players = self._players_from_preview(preview, replay)
        probabilities = self._probabilities(preview, replay)
        return {
            "match_id": match_id,
            "completed": completed,
            "home_team_name": home_name,
            "away_team_name": away_name,
            "preview": preview,
            "replay": replay,
            "players": players,
            "probabilities": probabilities,
            "totals": {"over_2_5": probabilities["over_2_5"], "under_2_5": 1 - probabilities["over_2_5"]},
        }

    def _players_from_preview(self, preview: Any | None, replay: Any | None) -> list[dict[str, Any]]:
        players: list[dict[str, Any]] = []
        if preview is not None:
            for team in (preview.home_team, preview.away_team):
                for player in team.starters:
                    probability = max(0.04, min(0.28, float(player.finishing) / 400))
                    players.append({"player_id": player.player_id, "player_name": player.player_name, "first_goal_probability": probability, "rating_over_probability": max(0.2, min(0.78, float(player.overall) / 120)), "overall": int(player.overall)})
        elif replay is not None:
            for player in replay.summary.player_stats:
                players.append({"player_id": player.player_id, "player_name": player.player_name, "first_goal_probability": max(0.04, min(0.22, (float(player.rating or 6.5) / 50))), "rating_over_probability": max(0.2, min(0.82, (float(player.rating or 6.5) / 10))), "overall": int(round((float(player.rating or 6.5) * 10)))})
        return sorted(players, key=lambda item: item["overall"], reverse=True)

    def _probabilities(self, preview: Any | None, replay: Any | None) -> dict[str, float]:
        if replay is not None:
            return {
                "home": float(replay.win_probability_home) / 100,
                "draw": float(replay.win_probability_draw) / 100,
                "away": float(replay.win_probability_away) / 100,
                "over_2_5": min(0.88, max(0.12, (float(replay.expected_goals_home) + float(replay.expected_goals_away)) / 4.2)),
            }
        home_strength = self._team_strength(getattr(preview, "home_team", None))
        away_strength = self._team_strength(getattr(preview, "away_team", None))
        delta = (home_strength - away_strength) / 100
        home, draw, away = _normalize_probabilities(0.38 + (delta * 0.28), 0.28 - abs(delta) * 0.08, 0.34 - (delta * 0.24))
        return {"home": home / 100, "draw": draw / 100, "away": away / 100, "over_2_5": min(0.88, max(0.12, 0.56 + (abs(delta) * 0.1)))}

    def _resolve_ticket(self, *, ticket: BetTicket, snapshot: dict[str, Any]) -> dict[str, object]:
        replay = snapshot["replay"]
        if replay is None:
            return {"status": "review", "credit": "0.0000", "summary": "Missing replay payload for settlement."}
        if ticket.bet_type == "match_winner":
            winner_key = "draw"
            if replay.summary.home_score > replay.summary.away_score:
                winner_key = "home"
            elif replay.summary.away_score > replay.summary.home_score:
                winner_key = "away"
            won = ticket.selection_key == winner_key
            return {"status": "won" if won else "lost", "credit": str(ticket.potential_payout_amount if won else Decimal("0.0000")), "summary": f"Result market settled on {winner_key}."}
        if ticket.bet_type == "over_under_goals":
            total_goals = replay.summary.home_score + replay.summary.away_score
            threshold = Decimal(ticket.selection_key.split(":")[1])
            won = total_goals > float(threshold) if ticket.selection_key.startswith("over") else total_goals < float(threshold)
            return {"status": "won" if won else "lost", "credit": str(ticket.potential_payout_amount if won else Decimal("0.0000")), "summary": f"Totals market settled at {total_goals} goals."}
        if ticket.bet_type == "first_goal_scorer":
            scorer = None
            for event in replay.timeline.events:
                event_type = str(getattr(event.event_type, "value", event.event_type)).lower()
                if "goal" in event_type:
                    scorer = event.player_id
                    break
            if scorer is None:
                return {"status": "refunded", "credit": str(ticket.stake_amount), "summary": "No goal was scored, so the market was voided."}
            won = ticket.selection_key == scorer
            return {"status": "won" if won else "lost", "credit": str(ticket.potential_payout_amount if won else Decimal("0.0000")), "summary": f"First scorer market settled on {scorer}."}
        if ticket.bet_type == "player_performance":
            player_id, metric, threshold_raw = ticket.selection_key.split(":")
            threshold = float(threshold_raw)
            player = next((item for item in replay.summary.player_stats if item.player_id == player_id), None)
            if player is None:
                return {"status": "refunded", "credit": str(ticket.stake_amount), "summary": "Player data was unavailable, so the market was refunded."}
            value = float(player.rating or 0.0) if metric == "rating_over" else float(player.goals)
            won = value > threshold
            return {"status": "won" if won else "lost", "credit": str(ticket.potential_payout_amount if won else Decimal("0.0000")), "summary": f"Player performance market settled at {value}."}
        return {"status": "review", "credit": "0.0000", "summary": "Unknown bet type requires manual review."}

    def _match_requires_review(self, snapshot: dict[str, Any]) -> bool:
        replay = snapshot["replay"]
        if replay is None:
            return True
        goal_total = replay.summary.home_score + replay.summary.away_score
        if goal_total >= 9:
            return True
        if abs(replay.summary.home_score - replay.summary.away_score) >= 6:
            return True
        return False

    def _market_alerts(self, *, match_id: str, actor: User, ticket: BetTicket) -> list[BetIntegrityAlert]:
        alerts: list[BetIntegrityAlert] = []
        duplicate_count = int(self.session.scalar(select(func.count()).select_from(BetTicket).where(BetTicket.user_id == actor.id, BetTicket.match_id == match_id, BetTicket.selection_key == ticket.selection_key)) or 0)
        if duplicate_count >= 3:
            alerts.append(self._record_alert(match_id=match_id, actor_user_id=actor.id, bet_id=ticket.id, issue_type="repeat_same_side", risk_level="medium", summary="Repeated same-side staking pattern detected for this user."))
        total_stake = self._normalize(self.session.scalar(select(func.coalesce(func.sum(BetTicket.stake_amount), 0)).where(BetTicket.match_id == match_id)) or 0)
        selection_stake = self._normalize(self.session.scalar(select(func.coalesce(func.sum(BetTicket.stake_amount), 0)).where(BetTicket.match_id == match_id, BetTicket.selection_key == ticket.selection_key)) or 0)
        if total_stake > Decimal("0.0000") and (selection_stake / total_stake) > Decimal("0.7500"):
            alerts.append(self._record_alert(match_id=match_id, actor_user_id=None, bet_id=ticket.id, issue_type="selection_concentration", risk_level="high", summary="Market concentration on one selection crossed the safety threshold."))
        return alerts

    def _record_alert(self, *, match_id: str, actor_user_id: str | None, bet_id: str | None, issue_type: str, risk_level: str, summary: str) -> BetIntegrityAlert:
        alert = BetIntegrityAlert(match_id=match_id, bet_id=bet_id, user_id=actor_user_id, issue_type=issue_type, risk_level=risk_level, status="open", summary=summary, metadata_json={})
        self.session.add(alert)
        self.session.flush()
        return alert

    def _audit(self, *, profile: BettingProfile, actor: User | None, ticket: BetTicket | None, event_type: str, amount: Decimal, before_available: Decimal, after_available: Decimal, before_locked: Decimal, after_locked: Decimal, reference: str) -> None:
        self.session.add(BetAuditLog(bet_id=ticket.id if ticket is not None else None, user_id=profile.user_id, event_type=event_type, amount=self._normalize(amount), before_available_balance=self._normalize(before_available), after_available_balance=self._normalize(after_available), before_locked_balance=self._normalize(before_locked), after_locked_balance=self._normalize(after_locked), reference=reference, metadata_json={"actor_user_id": actor.id if actor is not None else None}))

    def _current_loss_exposure(self, profile: BettingProfile) -> Decimal:
        today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        lost = self._normalize(self.session.scalar(select(func.coalesce(func.sum(BetTicket.stake_amount), 0)).where(BetTicket.user_id == profile.user_id, BetTicket.status == "lost", BetTicket.settled_at >= today_start)) or 0)
        open_exposure = self._normalize(self.session.scalar(select(func.coalesce(func.sum(BetTicket.stake_amount), 0)).where(BetTicket.user_id == profile.user_id, BetTicket.status == "placed")) or 0)
        return self._normalize(lost + open_exposure)

    def _auto_settle_actor_matches(self, user_id: str) -> None:
        match_ids = [item for item in self.session.scalars(select(BetTicket.match_id).where(BetTicket.user_id == user_id, BetTicket.status == "placed").distinct()).all()]
        for match_id in match_ids:
            snapshot = self._match_snapshot(match_id)
            if snapshot["completed"]:
                self.settle_match_bets(match_id=match_id)

    def _team_strength(self, team: Any | None) -> float:
        players = list(getattr(team, "starters", []) or [])
        return sum(float(player.overall) for player in players) / len(players) if players else 75.0

    def _parse_preview(self, payload: Any) -> Any | None:
        if not isinstance(payload, dict):
            return None
        try:
            from app.match_engine.schemas import MatchSimulationRequest

            return MatchSimulationRequest.model_validate(payload)
        except Exception:
            return None

    def _parse_replay(self, payload: Any) -> Any | None:
        if not isinstance(payload, dict):
            return None
        try:
            from app.match_engine.schemas import MatchReplayPayloadView

            return MatchReplayPayloadView.model_validate(payload)
        except Exception:
            return None

    def _normalize(self, value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(_AMOUNT_STEP)
