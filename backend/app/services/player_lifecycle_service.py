from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_injury_case import PlayerInjuryCase
from backend.app.models.transfer_bid import TransferBid
from backend.app.models.transfer_window import TransferWindow
from backend.app.schemas.player_lifecycle import TransferBidCreateRequest


@dataclass(slots=True)
class PlayerLifecycleService:
    session: Session

    def get_career(self, player_id: str) -> list[PlayerCareerEntry]:
        statement = select(PlayerCareerEntry).where(PlayerCareerEntry.player_id == player_id).order_by(PlayerCareerEntry.season_label.desc(), PlayerCareerEntry.created_at.desc())
        return list(self.session.scalars(statement))

    def get_contracts(self, player_id: str) -> list[PlayerContract]:
        statement = select(PlayerContract).where(PlayerContract.player_id == player_id).order_by(PlayerContract.ends_on.asc(), PlayerContract.created_at.desc())
        return list(self.session.scalars(statement))

    def get_injuries(self, player_id: str) -> list[PlayerInjuryCase]:
        statement = select(PlayerInjuryCase).where(PlayerInjuryCase.player_id == player_id).order_by(PlayerInjuryCase.occurred_on.desc(), PlayerInjuryCase.created_at.desc())
        return list(self.session.scalars(statement))

    def list_transfer_windows(self, *, territory_code: str | None = None, active_on: date | None = None) -> list[TransferWindow]:
        statement = select(TransferWindow).order_by(TransferWindow.opens_on.desc(), TransferWindow.created_at.desc())
        if territory_code:
            statement = statement.where(TransferWindow.territory_code == territory_code)
        if active_on:
            statement = statement.where(TransferWindow.opens_on <= active_on, TransferWindow.closes_on >= active_on)
        return list(self.session.scalars(statement))

    def list_window_bids(self, window_id: str) -> list[TransferBid]:
        statement = select(TransferBid).where(TransferBid.window_id == window_id).order_by(TransferBid.created_at.desc())
        return list(self.session.scalars(statement))

    def create_bid(self, window_id: str, payload: TransferBidCreateRequest) -> TransferBid | None:
        window = self.session.get(TransferWindow, window_id)
        if window is None:
            return None
        bid = TransferBid(
            window_id=window_id,
            player_id=payload.player_id,
            selling_club_id=payload.selling_club_id,
            buying_club_id=payload.buying_club_id,
            status="submitted" if window.status == "open" else "draft",
            bid_amount=payload.bid_amount,
            wage_offer_amount=payload.wage_offer_amount,
            sell_on_clause_pct=payload.sell_on_clause_pct,
            notes=payload.notes,
            structured_terms_json={},
        )
        self.session.add(bid)
        self.session.commit()
        self.session.refresh(bid)
        return bid
