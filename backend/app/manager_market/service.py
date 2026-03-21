from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.base import generate_uuid, utcnow
from app.models.manager_market import (
    ManagerAuditLog,
    ManagerCatalogEntry,
    ManagerCompetitionSetting,
    ManagerHolding,
    ManagerSettlementRecord,
    ManagerTeamAssignment,
    ManagerTradeListing,
    ManagerTradeRecord,
)
from app.admin_engine.service import AdminEngineService
from app.models.user import User
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

from .schemas import (
    CompetitionAdminUpdateRequest,
    CompetitionAdminView,
    CompetitionOrchestrationView,
    CompetitionRuntimeView,
    CompetitionScheduleMatchView,
    ManagerAssetView,
    ManagerAuditEventView,
    ManagerCatalogItem,
    ManagerCatalogPage,
    ManagerComparisonView,
    ManagerFilterMetadataView,
    ManagerHistoryEntryView,
    ManagerListingView,
    ManagerRecommendationView,
    ManagerSupplyUpdateRequest,
    ManagerTradeResultView,
    TeamManagersView,
)
from .seed_catalog import build_seed_catalog

LEGACY_STATE_FILE = "manager_market_state.json"


class ManagerMarketError(ValueError):
    pass


class CapacityError(ManagerMarketError):
    pass


@dataclass(slots=True)
class ManagerMarketService:
    wallet_service: WalletService

    def list_catalog(self, app: FastAPI, session: Session, *, search: str | None = None, tactic: str | None = None, trait: str | None = None, mentality: str | None = None, rarity: str | None = None, limit: int = 250) -> ManagerCatalogPage:
        self._bootstrap_db(app, session)
        stmt = select(ManagerCatalogEntry)
        if search:
            stmt = stmt.where(ManagerCatalogEntry.display_name.ilike(f"%{search.strip()}%"))
        if tactic:
            stmt = stmt.where(ManagerCatalogEntry.tactics.contains([tactic]))
        if trait:
            stmt = stmt.where(ManagerCatalogEntry.traits.contains([trait]))
        if mentality:
            stmt = stmt.where(ManagerCatalogEntry.mentality == mentality)
        if rarity:
            stmt = stmt.where(ManagerCatalogEntry.rarity == rarity)
        items = session.scalars(stmt.order_by(ManagerCatalogEntry.display_name.asc()).limit(limit)).all()
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        return ManagerCatalogPage(items=[self._catalog_item(row) for row in items], total=int(total))

    def _active_trading_fee_bps(self, session: Session) -> int:
        rule = next(iter(AdminEngineService(session).list_reward_rules(active_only=True)), None)
        return int(rule.trading_fee_bps if rule is not None else 2000)

    def filter_metadata(self, app: FastAPI, session: Session) -> ManagerFilterMetadataView:
        self._bootstrap_db(app, session)
        catalog = session.scalars(select(ManagerCatalogEntry)).all()
        return ManagerFilterMetadataView(
            tactics=sorted({t for item in catalog for t in (item.tactics or [])}),
            traits=sorted({t for item in catalog for t in (item.traits or [])}),
            mentalities=sorted({item.mentality for item in catalog if item.mentality}),
            rarities=sorted({item.rarity for item in catalog if item.rarity}),
        )

    def get_team(self, app: FastAPI, session: Session, user: User) -> TeamManagersView:
        self._bootstrap_db(app, session)
        holdings = session.scalars(
            select(ManagerHolding)
            .where(ManagerHolding.owner_user_id == user.id, ManagerHolding.status == "owned")
            .order_by(ManagerHolding.updated_at.desc())
        ).all()
        assignment = self._assignment(session, user.id)
        assets = [self._asset_view(session, holding) for holding in holdings]
        main = next((asset for asset in assets if asset.asset_id == (assignment.main_manager_asset_id if assignment else None)), None)
        academy = next((asset for asset in assets if asset.asset_id == (assignment.academy_manager_asset_id if assignment else None)), None)
        bench = [asset for asset in assets if asset.asset_id not in {(main.asset_id if main else None), (academy.asset_id if academy else None)}]
        return TeamManagersView(main_manager=main, academy_manager=academy, bench=bench, total_owned=len(assets))

    def recruit_manager(self, app: FastAPI, session: Session, user: User, manager_id: str, slot: str) -> TeamManagersView:
        self._bootstrap_db(app, session)
        self._assert_capacity(session, user.id)
        manager = self._manager_by_id(session, manager_id)
        if manager.supply_available <= 0:
            raise ManagerMarketError("No circulating copies are currently available for recruitment.")
        asset = ManagerHolding(
            asset_id=generate_uuid(),
            manager_id=manager_id,
            owner_user_id=user.id,
            acquired_at=utcnow().isoformat(),
            status="owned",
        )
        session.add(asset)
        manager.supply_available -= 1
        session.flush()
        if slot in {"main", "academy"}:
            self._assign_slot(session, user.id, asset.asset_id, slot)
        self._append_audit(session, "manager.recruited", user, {"manager_id": manager_id, "asset_id": asset.asset_id, "slot": slot})
        session.flush()
        return self.get_team(app, session, user)

    def assign_manager(self, app: FastAPI, session: Session, user: User, asset_id: str, slot: str) -> TeamManagersView:
        self._bootstrap_db(app, session)
        self._owned_asset(session, user.id, asset_id)
        open_listing = session.scalar(select(ManagerTradeListing).where(ManagerTradeListing.asset_id == asset_id, ManagerTradeListing.status == "open"))
        if open_listing is not None:
            raise ManagerMarketError("Cancel the trade listing before assigning this manager.")
        self._assign_slot(session, user.id, asset_id, slot)
        self._append_audit(session, "manager.assigned", user, {"asset_id": asset_id, "slot": slot})
        session.flush()
        return self.get_team(app, session, user)

    def release_manager(self, app: FastAPI, session: Session, user: User, asset_id: str) -> TeamManagersView:
        self._bootstrap_db(app, session)
        asset = self._owned_asset(session, user.id, asset_id)
        self._unassign_asset(session, user.id, asset_id)
        asset.status = "released"
        manager = self._manager_by_id(session, asset.manager_id)
        manager.supply_available += 1
        self._append_audit(session, "manager.released", user, {"asset_id": asset_id})
        session.flush()
        return self.get_team(app, session, user)

    def list_trade_listings(self, app: FastAPI, session: Session, seller_user_id: str | None = None) -> list[ManagerListingView]:
        self._bootstrap_db(app, session)
        stmt = select(ManagerTradeListing).where(ManagerTradeListing.status == "open").order_by(ManagerTradeListing.created_at.desc())
        if seller_user_id is not None:
            stmt = stmt.where(ManagerTradeListing.seller_user_id == seller_user_id)
        listings = session.scalars(stmt).all()
        return [self._listing_view(session, row) for row in listings]

    def create_listing(self, app: FastAPI, session: Session, user: User, asset_id: str, asking_price_credits: Decimal) -> ManagerListingView:
        self._bootstrap_db(app, session)
        asset = self._owned_asset(session, user.id, asset_id)
        existing = session.scalar(select(ManagerTradeListing).where(ManagerTradeListing.asset_id == asset_id, ManagerTradeListing.status == "open"))
        if existing is not None:
            raise ManagerMarketError("This manager already has an open trade listing.")
        self._unassign_asset(session, user.id, asset_id)
        listing = ManagerTradeListing(
            listing_id=generate_uuid(),
            asset_id=asset_id,
            seller_user_id=user.id,
            seller_name=user.display_name or user.username,
            asking_price_credits=str(asking_price_credits),
            status="open",
        )
        asset.status = "listed"
        session.add(listing)
        self._append_audit(session, "manager.listed", user, {"asset_id": asset_id, "price": str(asking_price_credits)})
        session.flush()
        return self._listing_view(session, listing)

    def cancel_listing(self, app: FastAPI, session: Session, user: User, listing_id: str) -> TeamManagersView:
        self._bootstrap_db(app, session)
        listing = session.scalar(select(ManagerTradeListing).where(ManagerTradeListing.listing_id == listing_id, ManagerTradeListing.status == "open"))
        if listing is None:
            raise ManagerMarketError("Trade listing was not found.")
        if listing.seller_user_id != user.id:
            raise ManagerMarketError("Only the listing owner can cancel this listing.")
        listing.status = "cancelled"
        asset = self._holding_by_asset_id(session, listing.asset_id)
        asset.status = "owned"
        self._append_audit(session, "manager.listing.cancelled", user, {"listing_id": listing_id, "asset_id": asset.asset_id})
        session.flush()
        return self.get_team(app, session, user)

    def buy_listing(self, app: FastAPI, session: Session, buyer: User, listing_id: str) -> ManagerTradeResultView:
        self._bootstrap_db(app, session)
        listing = session.scalar(select(ManagerTradeListing).where(ManagerTradeListing.listing_id == listing_id, ManagerTradeListing.status == "open"))
        if listing is None:
            raise ManagerMarketError("Trade listing was not found.")
        if listing.seller_user_id == buyer.id:
            raise ManagerMarketError("You cannot buy your own manager listing.")
        self._assert_capacity(session, buyer.id)
        asset = self._holding_by_asset_id(session, listing.asset_id)
        seller = session.get(User, listing.seller_user_id)
        if seller is None:
            raise ManagerMarketError("Seller account no longer exists.")

        gross = Decimal(listing.asking_price_credits)
        fee_bps = self._active_trading_fee_bps(session)
        fee = (gross * Decimal(fee_bps) / Decimal(10_000)).quantize(Decimal("0.0001"))
        seller_net = gross - fee
        settlement_reference = f"manager-trade:{listing_id}"
        self._ensure_trade_not_already_settled(session, settlement_reference)

        buyer_account = self.wallet_service.get_user_account(session, buyer, LedgerUnit.COIN)
        seller_account = self.wallet_service.get_user_account(session, seller, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        self.wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=buyer_account, amount=-gross, source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE),
                LedgerPosting(account=seller_account, amount=seller_net, source_tag=LedgerSourceTag.PLAYER_CARD_SALE),
                LedgerPosting(account=platform_account, amount=fee, source_tag=LedgerSourceTag.TRADING_FEE_BURN),
            ],
            reason=self.wallet_service.trade_settlement_reason,
            reference=settlement_reference,
            description="Manager marketplace trade settlement",
            actor=buyer,
        )

        self._unassign_asset(session, seller.id, asset.asset_id)
        asset.status = "owned"
        asset.owner_user_id = buyer.id
        asset.acquired_at = utcnow().isoformat()
        listing.status = "sold"
        trade_id = generate_uuid()
        trade = ManagerTradeRecord(
            trade_id=trade_id,
            mode="cash",
            listing_id=listing_id,
            gross_credits=str(gross),
            fee_credits=str(fee),
            seller_net_credits=str(seller_net),
            settlement_reference=settlement_reference,
            settlement_status="settled",
            immediate_withdrawal_eligible=True,
        )
        settlement = ManagerSettlementRecord(
            reference=settlement_reference,
            trade_id=trade_id,
            listing_id=listing_id,
            mode="cash",
            status="settled",
            gross_credits=str(gross),
            fee_credits=str(fee),
            seller_net_credits=str(seller_net),
            eligible_immediately=True,
            settled_by_user_id=buyer.id,
        )
        session.add_all([trade, settlement])
        self._append_audit(session, "manager.trade.completed", buyer, {"trade_id": trade_id, "listing_id": listing_id, "gross": str(gross), "fee": str(fee), "settlement_reference": settlement_reference})
        session.flush()
        return self._trade_result(trade)

    def swap_trade(self, app: FastAPI, session: Session, user: User, proposer_asset_id: str, requested_asset_id: str, cash_adjustment_credits: Decimal) -> ManagerTradeResultView:
        self._bootstrap_db(app, session)
        proposer_asset = self._owned_asset(session, user.id, proposer_asset_id)
        requested_asset = self._holding_by_asset_id(session, requested_asset_id)
        if requested_asset.owner_user_id == user.id:
            raise ManagerMarketError("Swap target must belong to another user.")
        requested_owner = session.get(User, requested_asset.owner_user_id)
        if requested_owner is None:
            raise ManagerMarketError("Requested manager owner was not found.")
        settlement_reference = f"manager-swap:{proposer_asset_id}:{requested_asset_id}"
        self._ensure_trade_not_already_settled(session, settlement_reference)

        if cash_adjustment_credits > 0:
            buyer_account = self.wallet_service.get_user_account(session, user, LedgerUnit.COIN)
            seller_account = self.wallet_service.get_user_account(session, requested_owner, LedgerUnit.COIN)
            platform_account = self.wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
            fee_bps = self._active_trading_fee_bps(session)
            fee = (cash_adjustment_credits * Decimal(fee_bps) / Decimal(10_000)).quantize(Decimal("0.0001"))
            seller_net = cash_adjustment_credits - fee
            self.wallet_service.append_transaction(
                session,
                postings=[
                    LedgerPosting(account=buyer_account, amount=-cash_adjustment_credits, source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE),
                    LedgerPosting(account=seller_account, amount=seller_net, source_tag=LedgerSourceTag.PLAYER_CARD_SALE),
                    LedgerPosting(account=platform_account, amount=fee, source_tag=LedgerSourceTag.TRADING_FEE_BURN),
                ],
                reason=self.wallet_service.trade_settlement_reason,
                reference=settlement_reference,
                description="Manager swap with cash adjustment",
                actor=user,
            )
        else:
            fee = Decimal("0.0000")
            seller_net = Decimal("0.0000")

        self._unassign_asset(session, user.id, proposer_asset_id)
        self._unassign_asset(session, requested_owner.id, requested_asset_id)
        proposer_asset.owner_user_id, requested_asset.owner_user_id = requested_owner.id, user.id
        proposer_asset.status = "owned"
        requested_asset.status = "owned"
        now_iso = utcnow().isoformat()
        proposer_asset.acquired_at = now_iso
        requested_asset.acquired_at = now_iso

        trade_id = generate_uuid()
        trade = ManagerTradeRecord(
            trade_id=trade_id,
            mode="swap",
            proposer_asset_id=proposer_asset_id,
            requested_asset_id=requested_asset_id,
            gross_credits=str(cash_adjustment_credits),
            fee_credits=str(fee),
            seller_net_credits=str(seller_net),
            settlement_reference=settlement_reference,
            settlement_status="settled",
            immediate_withdrawal_eligible=True,
        )
        settlement = ManagerSettlementRecord(
            reference=settlement_reference,
            trade_id=trade_id,
            mode="swap",
            status="settled",
            gross_credits=str(cash_adjustment_credits),
            fee_credits=str(fee),
            seller_net_credits=str(seller_net),
            eligible_immediately=True,
            settled_by_user_id=user.id,
        )
        session.add_all([trade, settlement])
        self._append_audit(session, "manager.swap.completed", user, {"trade_id": trade_id, "proposer_asset_id": proposer_asset_id, "requested_asset_id": requested_asset_id, "cash_adjustment": str(cash_adjustment_credits), "fee": str(fee), "settlement_reference": settlement_reference})
        session.flush()
        return self._trade_result(trade)

    def recommend(self, app: FastAPI, session: Session, user: User) -> ManagerRecommendationView:
        team = self.get_team(app, session, user)
        manager = team.main_manager or team.academy_manager
        if manager is None:
            return ManagerRecommendationView(
                manager=None,
                summary="No hired manager is active. Manage manually or recruit a coach to unlock tactical recommendations.",
                recommended_positions=["CB", "CM", "ST"],
                suggested_actions=["Recruit a manager whose tactics match your club identity."],
                selected_tactic=None,
                style_fit_score=42,
                squad_strength_score=45,
                depth_score=max(30, min(80, len(team.bench) * 10)),
                rationale=["Manual control remains active until a manager takes the dugout."],
                risk_flags=["No tactical automation bonus is currently active."],
            )
        selected_tactic = self._pick_primary_tactic(manager)
        style_fit_score = self._style_fit_score(manager)
        depth_score = max(35, min(95, 40 + (len(team.bench) * 14)))
        squad_strength_score = max(35, min(96, int((style_fit_score * 0.6) + (depth_score * 0.4))))
        recommendations = [
            "Upgrade full-backs if your manager leans into width.",
            "Keep one high-energy midfielder for late-game control.",
        ]
        rationale = [
            f"{manager.display_name} naturally leans toward {manager.mentality} football.",
            f"Primary tactic slot favors {selected_tactic}.",
            f"Current bench depth score sits at {depth_score}/100.",
        ]
        risk_flags: list[str] = []
        positions = ["RB", "CM", "RW"]
        if "develops_young_players" in manager.traits:
            recommendations.append("Promote at least one academy prospect into the first-team rotation.")
            rationale.append("Youth-development bias boosts squads that rotate prospects early.")
            positions = ["CM", "LW", "CB"]
        if "manages_elite_stars" in manager.traits:
            recommendations.append("Carry at least one decisive final-third star around this coach.")
            rationale.append("This manager converts elite talent into stronger big-game sequences.")
        if "late_substitution" in manager.traits:
            risk_flags.append("Late substitutions can leave tired legs exposed in frantic finishes.")
        if depth_score < 55:
            risk_flags.append("Squad depth is thin. Injury or fixture congestion could blunt this setup.")
        if selected_tactic in {"counter_attack", "low_block_counter"}:
            recommendations.append("Prioritize pace and ball-winning in wide and central transition zones.")
        elif selected_tactic in {"tiki_taka", "possession_control", "technical_build_up"}:
            recommendations.append("Prioritize press resistance, passing angles, and ball security in midfield.")
        summary = f"{manager.display_name} is a realistic fit for your current squad shape, with style fit {style_fit_score}/100 and depth support {depth_score}/100."
        return ManagerRecommendationView(
            manager=manager.display_name,
            summary=summary,
            recommended_positions=positions,
            suggested_actions=recommendations,
            selected_tactic=selected_tactic,
            style_fit_score=style_fit_score,
            squad_strength_score=squad_strength_score,
            depth_score=depth_score,
            rationale=rationale,
            risk_flags=risk_flags,
        )

    def compare_managers(self, app: FastAPI, session: Session, left_manager_id: str, right_manager_id: str) -> ManagerComparisonView:
        self._bootstrap_db(app, session)
        left = self._manager_by_id(session, left_manager_id)
        right = self._manager_by_id(session, right_manager_id)
        tactic_overlap = sorted(set(left.tactics or []).intersection(right.tactics or []))
        trait_overlap = sorted(set(left.traits or []).intersection(right.traits or []))
        left_fit = self._style_fit_score(left)
        right_fit = self._style_fit_score(right)
        if left_fit == right_fit:
            verdict = f"{left.display_name} and {right.display_name} are neck and neck. Choose based on your preferred tactical flavor."
        elif left_fit > right_fit:
            verdict = f"{left.display_name} has the stronger current squad-style fit edge."
        else:
            verdict = f"{right.display_name} has the stronger current squad-style fit edge."
        return ManagerComparisonView(
            left_manager_id=left.manager_id,
            right_manager_id=right.manager_id,
            left_name=left.display_name,
            right_name=right.display_name,
            tactic_overlap=tactic_overlap,
            trait_overlap=trait_overlap,
            style_fit_left=left_fit,
            style_fit_right=right_fit,
            verdict=verdict,
        )

    def trade_history(self, app: FastAPI, session: Session, user: User | None = None, manager_id: str | None = None, limit: int = 50) -> list[ManagerHistoryEntryView]:
        self._bootstrap_db(app, session)
        stmt = select(ManagerTradeRecord).order_by(ManagerTradeRecord.created_at.desc()).limit(limit)
        rows = session.scalars(stmt).all()
        history: list[ManagerHistoryEntryView] = []
        for row in rows:
            display_name = "Unknown manager"
            history_manager_id = manager_id or "unknown"
            candidate_asset_id = row.requested_asset_id or row.proposer_asset_id
            if row.listing_id:
                listing = session.scalar(select(ManagerTradeListing).where(ManagerTradeListing.listing_id == row.listing_id))
                if listing is not None:
                    holding = self._holding_by_asset_id(session, listing.asset_id)
                    manager = self._manager_by_id(session, holding.manager_id)
                    history_manager_id = manager.manager_id
                    display_name = manager.display_name
            elif candidate_asset_id:
                holding = session.scalar(select(ManagerHolding).where(ManagerHolding.asset_id == candidate_asset_id))
                if holding is not None:
                    manager = self._manager_by_id(session, holding.manager_id)
                    history_manager_id = manager.manager_id
                    display_name = manager.display_name
            if manager_id is not None and history_manager_id != manager_id:
                continue
            if user is not None:
                participant_ids = {r for r in [row.proposer_asset_id, row.requested_asset_id] if r}
                if row.listing_id:
                    listing = session.scalar(select(ManagerTradeListing).where(ManagerTradeListing.listing_id == row.listing_id))
                    if listing is not None and listing.seller_user_id != user.id:
                        holding = self._holding_by_asset_id(session, listing.asset_id)
                        if holding.owner_user_id != user.id:
                            continue
                elif participant_ids:
                    owners = {session.scalar(select(ManagerHolding.owner_user_id).where(ManagerHolding.asset_id == pid)) for pid in participant_ids}
                    if user.id not in owners:
                        continue
            history.append(ManagerHistoryEntryView(
                trade_id=row.trade_id,
                manager_id=history_manager_id,
                display_name=display_name,
                mode=row.mode,
                gross_credits=Decimal(row.gross_credits),
                fee_credits=Decimal(row.fee_credits),
                seller_net_credits=Decimal(row.seller_net_credits),
                settlement_status=row.settlement_status,
                created_at=row.created_at,
            ))
        return history

    def list_audit_log(self, app: FastAPI, session: Session, limit: int = 50) -> list[ManagerAuditEventView]:
        self._bootstrap_db(app, session)
        rows = session.scalars(select(ManagerAuditLog).order_by(ManagerAuditLog.created_at.desc()).limit(limit)).all()
        return [ManagerAuditEventView(event_id=row.event_id, event_type=row.event_type, actor_user_id=row.actor_user_id, actor_email=row.actor_email, created_at=row.created_at, payload=row.payload or {}) for row in rows]

    def preview_competition_runtime(self, app: FastAPI, session: Session, code: str, participants: int, region: str = "africa") -> CompetitionRuntimeView:
        self._bootstrap_db(app, session)
        config = session.scalar(select(ManagerCompetitionSetting).where(ManagerCompetitionSetting.code == code))
        if config is None:
            raise ManagerMarketError("Competition configuration not found.")
        minimum = max(2, int(config.minimum_viable_participants))
        qualified_regions = list(config.geo_locked_regions or [])
        fallback_regions = list(config.fallback_source_regions or [])
        adaptive_pool = max(0, int(participants))
        fallback_used = False

        if code == "fast_league":
            can_run = bool(config.enabled) and adaptive_pool >= 2
            bracket_size, byes = self._adaptive_bracket(adaptive_pool)
            reason = "Fast League is live once two users are ready." if can_run else "Fast League is waiting for at least two participants or has been disabled."
            return CompetitionRuntimeView(
                code=code,
                participants=participants,
                can_run=can_run,
                minimum_viable_participants=2,
                reason=reason,
                fallback_used=False,
                qualified_regions=qualified_regions,
                adaptive_pool_size=adaptive_pool,
                bracket_size=bracket_size,
                byes=byes,
                schedule_preview=self._build_schedule_preview(adaptive_pool),
            )

        region_allowed = not qualified_regions or region in qualified_regions
        if not region_allowed and config.allow_fallback_fill and (not fallback_regions or region in fallback_regions or region == 'africa') and adaptive_pool >= 2:
            fallback_used = True
            region_allowed = True

        if adaptive_pool < minimum and config.allow_fallback_fill and adaptive_pool >= 2:
            fallback_used = True
            minimum = 2

        can_run = bool(config.enabled) and region_allowed and adaptive_pool >= minimum
        bracket_size, byes = self._adaptive_bracket(adaptive_pool if can_run else max(0, adaptive_pool))
        if can_run and fallback_used:
            reason = "Adaptive fallback fill relaxed qualifier or region rules so the competition stays playable."
        elif can_run:
            reason = "Competition meets its active region and viability rules."
        elif not region_allowed:
            reason = "Competition is geo-locked for this region right now."
        else:
            reason = "Competition does not yet have enough qualified entrants."
        return CompetitionRuntimeView(
            code=code,
            participants=participants,
            can_run=can_run,
            minimum_viable_participants=minimum,
            reason=reason,
            fallback_used=fallback_used,
            qualified_regions=qualified_regions,
            adaptive_pool_size=adaptive_pool,
            bracket_size=bracket_size,
            byes=byes,
            schedule_preview=self._build_schedule_preview(adaptive_pool if can_run else min(adaptive_pool, bracket_size or adaptive_pool)),
        )

    def orchestrate_competition(self, app: FastAPI, session: Session, code: str, participants: int, region: str = "africa") -> CompetitionOrchestrationView:
        runtime = self.preview_competition_runtime(app, session, code, participants, region)
        notes = [runtime.reason]
        if code == "world_super_cup" and runtime.can_run and region == "africa":
            notes.append("African qualifiers can auto-fill GTEX World Super Cup slots while other continental pools remain gated.")
        if runtime.byes:
            notes.append(f"Adaptive bracketing introduced {runtime.byes} bye slot(s) to keep the schedule clean.")
        if runtime.fallback_used:
            notes.append("Fallback orchestration was invoked and should appear in admin audit trails.")
        return CompetitionOrchestrationView(
            code=code,
            can_run=runtime.can_run,
            entrants=runtime.adaptive_pool_size,
            minimum_viable_participants=runtime.minimum_viable_participants,
            qualified_regions=runtime.qualified_regions,
            fallback_used=runtime.fallback_used,
            fallback_reason=runtime.reason if runtime.fallback_used else None,
            bracket_size=runtime.bracket_size,
            byes=runtime.byes,
            auto_seeded=True,
            schedule=runtime.schedule_preview,
            notes=notes,
        )

    def list_competitions(self, app: FastAPI, session: Session) -> list[CompetitionAdminView]:
        self._bootstrap_db(app, session)
        rows = session.scalars(select(ManagerCompetitionSetting).order_by(ManagerCompetitionSetting.code.asc())).all()
        return [CompetitionAdminView(code=row.code, label=row.label, enabled=row.enabled, minimum_viable_participants=row.minimum_viable_participants, geo_locked_regions=row.geo_locked_regions or [], allow_fallback_fill=row.allow_fallback_fill, fallback_source_regions=row.fallback_source_regions or [], schedule_mode="adaptive", auto_seed_enabled=True) for row in rows]

    def update_competition(self, app: FastAPI, session: Session, actor: User, code: str, payload: CompetitionAdminUpdateRequest) -> CompetitionAdminView:
        self._bootstrap_db(app, session)
        row = session.scalar(select(ManagerCompetitionSetting).where(ManagerCompetitionSetting.code == code))
        if row is None:
            raise ManagerMarketError("Competition configuration not found.")
        updates = payload.model_dump(exclude_none=True)
        if updates.get("minimum_viable_participants") is not None:
            updates["minimum_viable_participants"] = max(2, int(updates["minimum_viable_participants"]))
        for key, value in updates.items():
            setattr(row, key, value)
        self._append_audit(session, "competition.updated", actor, {"code": code, **updates})
        session.flush()
        return CompetitionAdminView(code=row.code, label=row.label, enabled=row.enabled, minimum_viable_participants=row.minimum_viable_participants, geo_locked_regions=row.geo_locked_regions or [], allow_fallback_fill=row.allow_fallback_fill, fallback_source_regions=row.fallback_source_regions or [], schedule_mode="adaptive", auto_seed_enabled=True)

    def update_manager_supply(self, app: FastAPI, session: Session, actor: User, manager_id: str, payload: ManagerSupplyUpdateRequest) -> ManagerCatalogItem:
        self._bootstrap_db(app, session)
        manager = self._manager_by_id(session, manager_id)
        active_owned = session.scalar(select(func.count()).select_from(ManagerHolding).where(ManagerHolding.manager_id == manager_id, ManagerHolding.status.in_(["owned", "listed"]))) or 0
        if payload.supply_total < int(active_owned):
            raise ManagerMarketError("New total supply cannot be lower than copies already held by users.")
        manager.supply_available += payload.supply_total - manager.supply_total
        manager.supply_total = payload.supply_total
        self._append_audit(session, "manager.supply.updated", actor, {"manager_id": manager_id, "supply_total": payload.supply_total, "reason": payload.reason})
        session.flush()
        return self._catalog_item(manager)

    def run_fast_league(self, app: FastAPI, session: Session, participants: int) -> dict[str, Any]:
        runtime = self.preview_competition_runtime(app, session, code="fast_league", participants=participants)
        return runtime.model_dump()

    def _build_schedule_preview(self, participants: int) -> list[CompetitionScheduleMatchView]:
        if participants < 2:
            return []
        bracket_size, _ = self._adaptive_bracket(participants)
        entrants = [f"Seed {index}" for index in range(1, participants + 1)]
        while len(entrants) < bracket_size:
            entrants.append("BYE")
        schedule: list[CompetitionScheduleMatchView] = []
        slot = 1
        left = 0
        right = len(entrants) - 1
        while left < right:
            schedule.append(CompetitionScheduleMatchView(seed=left + 1, slot=slot, home_label=entrants[left], away_label=entrants[right]))
            slot += 1
            left += 1
            right -= 1
        return schedule

    def _adaptive_bracket(self, participants: int) -> tuple[int, int]:
        if participants < 2:
            return (0, 0)
        bracket = 2
        while bracket < participants:
            bracket *= 2
        return bracket, max(0, bracket - participants)

    def _pick_primary_tactic(self, manager: ManagerAssetView) -> str | None:
        tactics = list(manager.tactics or [])
        if not tactics:
            return None
        preferred = ["tiki_taka", "gegenpress", "counter_attack", "possession_control", "compact_midblock"]
        for tactic in preferred:
            if tactic in tactics:
                return tactic
        return tactics[0]

    def _style_fit_score(self, manager: ManagerAssetView | ManagerCatalogEntry) -> int:
        tactics = set(manager.tactics or [])
        traits = set(manager.traits or [])
        score = 48
        mentality = getattr(manager, "mentality", "")
        mentality_boosts = {
            "technical": 8,
            "possession": 9,
            "pressing": 7,
            "attacking": 6,
            "balanced": 4,
            "pragmatic": 3,
            "defensive": 5,
            "physical": 4,
        }
        score += mentality_boosts.get(mentality, 0)
        for trait, boost in {
            "develops_young_players": 9,
            "manages_elite_stars": 8,
            "quick_substitution": 4,
            "late_substitution": -2,
            "tactical_flexibility": 6,
            "defensive_organization": 5,
            "technical_coaching": 7,
            "boosts_physicality_focus": 4,
        }.items():
            if trait in traits:
                score += boost
        for tactic, boost in {
            "tiki_taka": 8,
            "possession_control": 8,
            "technical_build_up": 6,
            "counter_attack": 6,
            "low_block_counter": 5,
            "high_press_attack": 7,
            "wing_play": 4,
            "youth_development_system": 4,
        }.items():
            if tactic in tactics:
                score += boost
        if {"tiki_taka", "technical_build_up"}.issubset(tactics):
            score += 3
        if {"counter_attack", "compact_midblock"}.issubset(tactics):
            score += 3
        return max(1, min(score, 99))

    def _catalog_item(self, row: ManagerCatalogEntry) -> ManagerCatalogItem:
        return ManagerCatalogItem(
            manager_id=row.manager_id,
            display_name=row.display_name,
            rarity=row.rarity,
            mentality=row.mentality,
            tactics=list(row.tactics or []),
            traits=list(row.traits or []),
            substitution_tendency=row.substitution_tendency,
            philosophy_summary=row.philosophy_summary,
            club_associations=list(row.club_associations or []),
            supply_total=row.supply_total,
            supply_available=row.supply_available,
        )

    def _listing_view(self, session: Session, listing: ManagerTradeListing) -> ManagerListingView:
        asset = self._holding_by_asset_id(session, listing.asset_id)
        manager = self._manager_by_id(session, asset.manager_id)
        return ManagerListingView(
            listing_id=listing.listing_id,
            asset_id=asset.asset_id,
            manager_id=manager.manager_id,
            display_name=manager.display_name,
            seller_user_id=listing.seller_user_id,
            seller_name=listing.seller_name,
            asking_price_credits=Decimal(listing.asking_price_credits),
            created_at=listing.created_at,
        )

    def _trade_result(self, trade: ManagerTradeRecord) -> ManagerTradeResultView:
        return ManagerTradeResultView(
            trade_id=trade.trade_id,
            mode=trade.mode,
            fee_credits=Decimal(trade.fee_credits),
            seller_net_credits=Decimal(trade.seller_net_credits),
            gross_credits=Decimal(trade.gross_credits),
            created_at=trade.created_at,
            settlement_reference=trade.settlement_reference,
            immediate_withdrawal_eligible=trade.immediate_withdrawal_eligible,
            settlement_status=trade.settlement_status,
        )

    def _asset_view(self, session: Session, asset: ManagerHolding) -> ManagerAssetView:
        manager = self._manager_by_id(session, asset.manager_id)
        slot = None
        assignment = session.scalar(select(ManagerTeamAssignment).where(or_(ManagerTeamAssignment.main_manager_asset_id == asset.asset_id, ManagerTeamAssignment.academy_manager_asset_id == asset.asset_id)))
        if assignment is not None:
            if assignment.main_manager_asset_id == asset.asset_id:
                slot = "main"
            elif assignment.academy_manager_asset_id == asset.asset_id:
                slot = "academy"
        return ManagerAssetView(asset_id=asset.asset_id, manager_id=manager.manager_id, display_name=manager.display_name, rarity=manager.rarity, tactics=list(manager.tactics or []), traits=list(manager.traits or []), mentality=manager.mentality, slot=slot, acquired_at=datetime.fromisoformat(asset.acquired_at))

    def _assert_capacity(self, session: Session, user_id: str) -> None:
        owned = session.scalar(select(func.count()).select_from(ManagerHolding).where(ManagerHolding.owner_user_id == user_id, ManagerHolding.status == "owned")) or 0
        if int(owned) >= 2:
            raise CapacityError("Each team can only hold two managers at a time.")

    def _assignment(self, session: Session, user_id: str) -> ManagerTeamAssignment | None:
        return session.scalar(select(ManagerTeamAssignment).where(ManagerTeamAssignment.user_id == user_id))

    def _assign_slot(self, session: Session, user_id: str, asset_id: str, slot: str) -> None:
        self._owned_asset(session, user_id, asset_id)
        assignment = self._assignment(session, user_id)
        if assignment is None:
            assignment = ManagerTeamAssignment(user_id=user_id)
            session.add(assignment)
            session.flush()
        key = "main_manager_asset_id" if slot == "main" else "academy_manager_asset_id"
        setattr(assignment, key, asset_id)

    def _unassign_asset(self, session: Session, user_id: str, asset_id: str) -> None:
        assignment = self._assignment(session, user_id)
        if assignment is None:
            return
        if assignment.main_manager_asset_id == asset_id:
            assignment.main_manager_asset_id = None
        if assignment.academy_manager_asset_id == asset_id:
            assignment.academy_manager_asset_id = None

    def _owned_asset(self, session: Session, user_id: str, asset_id: str) -> ManagerHolding:
        asset = self._holding_by_asset_id(session, asset_id)
        if asset.owner_user_id != user_id or asset.status != "owned":
            raise ManagerMarketError("Manager asset is not owned by the current user.")
        return asset

    def _holding_by_asset_id(self, session: Session, asset_id: str) -> ManagerHolding:
        asset = session.scalar(select(ManagerHolding).where(ManagerHolding.asset_id == asset_id))
        if asset is None:
            raise ManagerMarketError("Manager asset was not found.")
        return asset

    def _manager_by_id(self, session: Session, manager_id: str) -> ManagerCatalogEntry:
        manager = session.scalar(select(ManagerCatalogEntry).where(ManagerCatalogEntry.manager_id == manager_id))
        if manager is None:
            raise ManagerMarketError("Manager was not found.")
        return manager

    def _append_audit(self, session: Session, event_type: str, actor: User, payload: dict[str, Any]) -> None:
        session.add(ManagerAuditLog(event_id=generate_uuid(), event_type=event_type, actor_user_id=actor.id, actor_email=actor.email, payload=payload))

    def _ensure_trade_not_already_settled(self, session: Session, settlement_reference: str) -> None:
        existing = session.scalar(select(ManagerSettlementRecord).where(ManagerSettlementRecord.reference == settlement_reference, ManagerSettlementRecord.status == "settled"))
        if existing is not None:
            raise ManagerMarketError("This manager trade has already been settled and cannot be processed again.")

    def _bootstrap_db(self, app: FastAPI, session: Session) -> None:
        existing = session.scalar(select(func.count()).select_from(ManagerCatalogEntry)) or 0
        if int(existing) > 0:
            return

        legacy_path = self._legacy_state_path(app)
        if legacy_path.exists():
            legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
            for row in legacy.get("catalog", []):
                session.add(ManagerCatalogEntry(
                    manager_id=row["manager_id"],
                    display_name=row["display_name"],
                    rarity=row["rarity"],
                    mentality=row["mentality"],
                    tactics=row.get("tactics", []),
                    traits=row.get("traits", []),
                    substitution_tendency=row.get("substitution_tendency", "balanced_substitution"),
                    philosophy_summary=row.get("philosophy_summary", ""),
                    club_associations=row.get("club_associations", []),
                    supply_total=int(row.get("supply_total", 0)),
                    supply_available=int(row.get("supply_available", 0)),
                ))
            for row in legacy.get("holdings", []):
                session.add(ManagerHolding(asset_id=row["asset_id"], manager_id=row["manager_id"], owner_user_id=row["owner_user_id"], acquired_at=row["acquired_at"], status=row["status"]))
            for row in legacy.get("listings", []):
                session.add(ManagerTradeListing(listing_id=row["listing_id"], asset_id=row["asset_id"], seller_user_id=row["seller_user_id"], seller_name=row.get("seller_name") or row["seller_user_id"], asking_price_credits=row["asking_price_credits"], status=row["status"]))
            for user_id, assignment in (legacy.get("team_assignments") or {}).items():
                session.add(ManagerTeamAssignment(user_id=user_id, main_manager_asset_id=assignment.get("main_manager_asset_id"), academy_manager_asset_id=assignment.get("academy_manager_asset_id")))
            for row in legacy.get("trade_history", []):
                session.add(ManagerTradeRecord(trade_id=row["trade_id"], mode=row["mode"], listing_id=row.get("listing_id"), proposer_asset_id=row.get("proposer_asset_id"), requested_asset_id=row.get("requested_asset_id"), gross_credits=row.get("gross_credits", "0"), fee_credits=row.get("fee_credits", "0"), seller_net_credits=row.get("seller_net_credits", "0"), settlement_reference=row.get("settlement_reference") or f"legacy:{row['trade_id']}", settlement_status=row.get("settlement_status", "settled"), immediate_withdrawal_eligible=bool(row.get("immediate_withdrawal_eligible", True)), created_at=datetime.fromisoformat(row["created_at"])))
            for row in legacy.get("settlement_records", []):
                session.add(ManagerSettlementRecord(reference=row["reference"], trade_id=row["trade_id"], listing_id=row.get("listing_id"), mode=row.get("mode", "cash"), status=row.get("status", "settled"), gross_credits=row.get("gross_credits", "0"), fee_credits=row.get("fee_credits", "0"), seller_net_credits=row.get("seller_net_credits", "0"), eligible_immediately=bool(row.get("eligible_immediately", True)), settled_by_user_id=row.get("settled_by_user_id"), created_at=datetime.fromisoformat(row["created_at"])))
            for row in legacy.get("competition_settings", []):
                session.add(ManagerCompetitionSetting(code=row["code"], label=row["label"], enabled=bool(row.get("enabled", True)), minimum_viable_participants=int(row.get("minimum_viable_participants", 2)), geo_locked_regions=row.get("geo_locked_regions", []), allow_fallback_fill=bool(row.get("allow_fallback_fill", False)), fallback_source_regions=row.get("fallback_source_regions", [])))
            for row in legacy.get("audit_log", []):
                session.add(ManagerAuditLog(event_id=row["event_id"], event_type=row["event_type"], actor_user_id=row["actor_user_id"], actor_email=row["actor_email"], payload=row.get("payload", {}), created_at=datetime.fromisoformat(row["created_at"])))
            session.flush()
            return

        for raw in build_seed_catalog():
            manager_id = raw["name"].lower().replace("'", "").replace(" ", "-")
            substitution = next((trait for trait in raw["traits"] if "substitution" in trait), "balanced_substitution")
            session.add(ManagerCatalogEntry(
                manager_id=manager_id,
                display_name=raw["name"],
                rarity=raw["rarity"],
                mentality=raw["mentality"],
                tactics=raw["tactics"][:4],
                traits=raw["traits"][:4],
                substitution_tendency=substitution,
                philosophy_summary=raw["philosophy"],
                club_associations=raw.get("club_associations", []),
                supply_total=raw["supply_total"],
                supply_available=raw["supply_total"],
            ))
        for row in self._default_competitions():
            session.add(ManagerCompetitionSetting(**row))
        session.flush()

    def _default_competitions(self) -> list[dict[str, Any]]:
        return [
            {"code": "african_championship", "label": "African Championship", "enabled": True, "minimum_viable_participants": 2, "geo_locked_regions": ["africa"], "allow_fallback_fill": True, "fallback_source_regions": ["africa"]},
            {"code": "world_super_cup", "label": "GTEX World Super Cup", "enabled": True, "minimum_viable_participants": 4, "geo_locked_regions": ["africa"], "allow_fallback_fill": True, "fallback_source_regions": ["africa"]},
            {"code": "uefa_cup", "label": "UEFA Cup", "enabled": False, "minimum_viable_participants": 4, "geo_locked_regions": ["europe"], "allow_fallback_fill": False, "fallback_source_regions": []},
            {"code": "asia_cup", "label": "Asia Cup", "enabled": False, "minimum_viable_participants": 4, "geo_locked_regions": ["asia"], "allow_fallback_fill": False, "fallback_source_regions": []},
            {"code": "north_america_cup", "label": "North America Cup", "enabled": False, "minimum_viable_participants": 4, "geo_locked_regions": ["north_america"], "allow_fallback_fill": False, "fallback_source_regions": []},
            {"code": "fast_league", "label": "Fast League", "enabled": True, "minimum_viable_participants": 2, "geo_locked_regions": ["africa"], "allow_fallback_fill": True, "fallback_source_regions": ["africa"]},
        ]

    def _legacy_state_path(self, app: FastAPI) -> Path:
        return app.state.settings.config_root / LEGACY_STATE_FILE
