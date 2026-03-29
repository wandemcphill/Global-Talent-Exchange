from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.tournament import (
    Tournament,
    TournamentGameType,
    TournamentMatch,
    TournamentMatchStatus,
    TournamentPlayer,
    TournamentPlayerStatus,
    TournamentRound,
    TournamentRoundStatus,
    TournamentStatus,
)
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransactionType,
    LedgerUnit,
)
from app.infrastructure.distributed_lock import DistributedLockService, build_distributed_lock_service
from app.tournaments.schemas import TournamentCreateRequest, TournamentMatchResultRequest
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService


class TournamentError(Exception):
    def __init__(self, detail: str, *, reason: str) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason


class TournamentNotFoundError(TournamentError):
    def __init__(self, detail: str = "Tournament not found.") -> None:
        super().__init__(detail, reason="not_found")


class TournamentValidationError(TournamentError):
    pass


@dataclass(slots=True)
class TournamentService:
    session: Session
    wallet_service: WalletService | None = None
    lock_service: DistributedLockService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.lock_service is None:
            self.lock_service = build_distributed_lock_service()

    def list_tournaments(self) -> list[dict[str, object]]:
        tournament_ids = self.session.scalars(
            select(Tournament.id).order_by(Tournament.created_at.desc())
        ).all()
        views: list[dict[str, object]] = []
        for tournament_id in tournament_ids:
            views.append(self.get_tournament(tournament_id))
        return views

    def create_tournament(self, payload: TournamentCreateRequest) -> dict[str, object]:
        tournament = Tournament(
            name=payload.name,
            game_type=payload.game_type.value,
            entry_fee=payload.entry_fee,
            max_players=payload.max_players,
            status=TournamentStatus.REGISTRATION.value,
            rounds=self._round_count(payload.max_players),
            current_round=1,
            prize_pool=0,
            round_timeout_minutes=payload.round_timeout_minutes,
            metadata_json=dict(payload.metadata_json),
        )
        self.session.add(tournament)
        self.session.flush()
        return self._build_view(tournament)

    def get_tournament(self, tournament_id: str) -> dict[str, object]:
        tournament = self._get_tournament(tournament_id)
        if tournament.status == TournamentStatus.ACTIVE.value:
            with self._state_lock(tournament.id) as acquired:
                if not acquired:
                    raise TournamentValidationError("Tournament state is busy. Retry shortly.", reason="operation_busy")
                tournament = self._get_tournament(tournament_id, for_update=True)
                self._sync_tournament(tournament)
        self._synchronize_prize_pool(tournament)
        return self._build_view(tournament)

    def join_tournament(self, tournament_id: str, *, user_id: str) -> dict[str, object]:
        with self._join_lock(tournament_id) as acquired:
            if not acquired:
                raise TournamentValidationError("Tournament join is already processing.", reason="operation_busy")
            tournament = self._get_tournament(tournament_id, for_update=True)
            if tournament.status != TournamentStatus.REGISTRATION.value:
                existing = self._get_player(tournament.id, user_id)
                if existing is not None:
                    self._synchronize_prize_pool(tournament)
                    return self._build_view(tournament)
                raise TournamentValidationError("Tournament registration is closed.", reason="registration_closed")

            user = self.session.get(User, user_id)
            if user is None:
                raise TournamentValidationError("User not found.", reason="user_not_found")

            existing_player = self._get_player(tournament.id, user_id)
            if existing_player is not None:
                self._synchronize_prize_pool(tournament)
                return self._build_view(tournament)

            players = self._list_players(tournament.id)
            if len(players) >= tournament.max_players:
                raise TournamentValidationError("Tournament is already full.", reason="tournament_full")

            entry_transaction_id = self._charge_entry_fee(tournament=tournament, user=user)
            player = TournamentPlayer(
                tournament_id=tournament.id,
                user_id=user.id,
                bracket_slot=len(players) + 1,
                status=TournamentPlayerStatus.REGISTERED.value,
                entry_transaction_id=entry_transaction_id,
            )
            self.session.add(player)
            self.session.flush()
            self._synchronize_prize_pool(tournament)

            if len(players) + 1 >= tournament.max_players:
                self._start_tournament(tournament)
                self._sync_tournament(tournament)

            return self._build_view(tournament)

    def record_match_result(
        self,
        tournament_id: str,
        match_id: str,
        payload: TournamentMatchResultRequest,
    ) -> dict[str, object]:
        with self._state_lock(tournament_id) as acquired:
            if not acquired:
                raise TournamentValidationError("Tournament state is busy. Retry shortly.", reason="operation_busy")
            tournament = self._get_tournament(tournament_id, for_update=True)
            self._sync_tournament(tournament)
            if tournament.status != TournamentStatus.ACTIVE.value:
                raise TournamentValidationError("Tournament is not active.", reason="tournament_not_active")

            match = self.session.scalar(
                select(TournamentMatch).where(
                    TournamentMatch.id == match_id,
                    TournamentMatch.tournament_id == tournament.id,
                )
            )
            if match is None:
                raise TournamentValidationError("Match not found.", reason="match_not_found")
            if match.round_number != tournament.current_round:
                raise TournamentValidationError("Only the current round can be reported.", reason="round_locked")
            if match.status == TournamentMatchStatus.COMPLETED.value:
                self._synchronize_prize_pool(tournament)
                return self._build_view(tournament)

            participants = {match.player_one_user_id, match.player_two_user_id}
            if payload.winner_user_id not in participants:
                raise TournamentValidationError("Winner must be part of the match.", reason="invalid_winner")

            self._complete_match(
                match,
                winner_user_id=payload.winner_user_id,
                resolution="result",
                player_one_score=payload.player_one_score,
                player_two_score=payload.player_two_score,
            )
            self._sync_tournament(tournament)
            self._synchronize_prize_pool(tournament)
            return self._build_view(tournament)

    def advance_tournament(self, tournament_id: str) -> dict[str, object]:
        with self._state_lock(tournament_id) as acquired:
            if not acquired:
                raise TournamentValidationError("Tournament state is busy. Retry shortly.", reason="operation_busy")
            tournament = self._get_tournament(tournament_id, for_update=True)
            before = (tournament.status, tournament.current_round, tournament.completed_at)
            self._sync_tournament(tournament, fail_if_not_ready=True)
            after = (tournament.status, tournament.current_round, tournament.completed_at)
            if before == after:
                raise TournamentValidationError("Tournament round is not ready to advance.", reason="round_not_ready")
            self._synchronize_prize_pool(tournament)
            return self._build_view(tournament)

    def generate_bracket(self, players: list[str]) -> list[tuple[str | None, str | None]]:
        bracket_size = self._next_power_of_two(len(players))
        seeded: list[str | None] = list(players)
        while len(seeded) < bracket_size:
            seeded.append(None)
        return [(seeded[index], seeded[-(index + 1)]) for index in range(bracket_size // 2)]

    def advance_winners(self, round_results: list[str]) -> list[tuple[str | None, str | None]]:
        winners = list(round_results)
        if len(winners) % 2 == 1:
            winners.append(None)
        return [(winners[index], winners[index + 1]) for index in range(0, len(winners), 2)]

    def _get_tournament(self, tournament_id: str, *, for_update: bool = False) -> Tournament:
        if for_update:
            statement = select(Tournament).where(Tournament.id == tournament_id)
            if self._supports_row_locks():
                statement = statement.with_for_update()
            tournament = self.session.scalar(statement)
        else:
            tournament = self.session.get(Tournament, tournament_id)
        if tournament is None:
            raise TournamentNotFoundError()
        return tournament

    def _get_player(self, tournament_id: str, user_id: str) -> TournamentPlayer | None:
        return self.session.scalar(
            select(TournamentPlayer).where(
                TournamentPlayer.tournament_id == tournament_id,
                TournamentPlayer.user_id == user_id,
            )
        )

    def _list_players(self, tournament_id: str) -> list[TournamentPlayer]:
        return self.session.scalars(
            select(TournamentPlayer)
            .where(TournamentPlayer.tournament_id == tournament_id)
            .order_by(TournamentPlayer.bracket_slot.asc(), TournamentPlayer.created_at.asc())
        ).all()

    def _list_rounds(self, tournament_id: str) -> list[TournamentRound]:
        return self.session.scalars(
            select(TournamentRound)
            .where(TournamentRound.tournament_id == tournament_id)
            .order_by(TournamentRound.round_number.asc(), TournamentRound.created_at.asc())
        ).all()

    def _list_matches(self, tournament_id: str) -> list[TournamentMatch]:
        return self.session.scalars(
            select(TournamentMatch)
            .where(TournamentMatch.tournament_id == tournament_id)
            .order_by(TournamentMatch.round_number.asc(), TournamentMatch.slot_index.asc(), TournamentMatch.created_at.asc())
        ).all()

    def _round_matches(self, tournament_id: str, round_number: int) -> list[TournamentMatch]:
        return self.session.scalars(
            select(TournamentMatch)
            .where(
                TournamentMatch.tournament_id == tournament_id,
                TournamentMatch.round_number == round_number,
            )
            .order_by(TournamentMatch.slot_index.asc(), TournamentMatch.created_at.asc())
        ).all()

    def _active_round(self, tournament_id: str, round_number: int) -> TournamentRound | None:
        return self.session.scalar(
            select(TournamentRound).where(
                TournamentRound.tournament_id == tournament_id,
                TournamentRound.round_number == round_number,
            )
        )

    def _charge_entry_fee(self, *, tournament: Tournament, user: User) -> str | None:
        if tournament.entry_fee <= 0:
            return None
        assert self.wallet_service is not None
        player_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.CREDIT)
        pool_account = self._ensure_tournament_pool_account(tournament)
        reference = f"tournament:{tournament.id}:entry:{user.id}"
        try:
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=player_account,
                        amount=Decimal(str(-tournament.entry_fee)),
                        source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                        transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                    ),
                    LedgerPosting(
                        account=pool_account,
                        amount=Decimal(str(tournament.entry_fee)),
                        source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                        transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                    ),
                ],
                reason=LedgerEntryReason.COMPETITION_ENTRY,
                source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
                transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                reference=reference,
                description=f"Entry fee for tournament {tournament.name}",
                idempotency_key=reference,
                metadata={"tournament_id": tournament.id},
            )
        except InsufficientBalanceError as exc:
            raise TournamentValidationError("Insufficient wallet balance for tournament entry.", reason="insufficient_balance") from exc
        return entries[0].transaction_id if entries else None

    def _synchronize_prize_pool(self, tournament: Tournament) -> None:
        if tournament.entry_fee <= 0:
            tournament.prize_pool = 0
            return
        paid_entries = self.session.scalar(
            select(func.count())
            .select_from(TournamentPlayer)
            .where(
                TournamentPlayer.tournament_id == tournament.id,
                TournamentPlayer.entry_transaction_id.is_not(None),
            )
        )
        tournament.prize_pool = int(paid_entries or 0) * int(tournament.entry_fee)

    def _ensure_tournament_pool_account(self, tournament: Tournament) -> LedgerAccount:
        code = f"tournament:{tournament.id}:pool:credit"
        account = self.session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is not None:
            return account
        account = LedgerAccount(
            owner_user_id=None,
            code=code,
            label=f"{tournament.name} Prize Pool",
            unit=LedgerUnit.CREDIT,
            kind=LedgerAccountKind.SYSTEM,
            allow_negative=False,
        )
        self.session.add(account)
        self.session.flush()
        return account

    def _start_tournament(self, tournament: Tournament) -> None:
        players = self._list_players(tournament.id)
        if len(players) < 2:
            raise TournamentValidationError("At least two players are required to start.", reason="insufficient_players")
        if tournament.status == TournamentStatus.ACTIVE.value:
            return
        tournament.status = TournamentStatus.ACTIVE.value
        tournament.started_at = utcnow()
        tournament.current_round = 1
        for player in players:
            player.status = TournamentPlayerStatus.ACTIVE.value
        self._create_round_matches(
            tournament=tournament,
            round_number=1,
            ordered_user_ids=[player.user_id for player in players],
            bracket_style="seeded",
        )

    def _sync_tournament(self, tournament: Tournament, *, fail_if_not_ready: bool = False) -> None:
        if tournament.status != TournamentStatus.ACTIVE.value:
            return

        progressed = False
        while tournament.status == TournamentStatus.ACTIVE.value:
            current_round = self._active_round(tournament.id, tournament.current_round)
            if current_round is None:
                self._complete_tournament(tournament, winner_user_id=None)
                progressed = True
                break

            matches = self._round_matches(tournament.id, tournament.current_round)
            if not matches:
                self._complete_tournament(tournament, winner_user_id=None)
                progressed = True
                break

            now = utcnow()
            all_completed = all(match.status == TournamentMatchStatus.COMPLETED.value for match in matches)
            timed_out = self._as_utc(current_round.timeout_at) <= now
            if not all_completed and not timed_out:
                if fail_if_not_ready and not progressed:
                    raise TournamentValidationError("Current round has pending matches.", reason="round_not_ready")
                break

            if timed_out:
                for match in matches:
                    if match.status == TournamentMatchStatus.COMPLETED.value:
                        continue
                    winner_user_id = self._timeout_winner(match)
                    if winner_user_id is None:
                        raise TournamentValidationError("Unable to resolve timed out match.", reason="timeout_resolution_failed")
                    self._complete_match(match, winner_user_id=winner_user_id, resolution="timeout")

            current_round.status = TournamentRoundStatus.COMPLETED.value
            current_round.completed_at = now

            winners = [match.winner_user_id for match in matches if match.winner_user_id]
            if len(winners) <= 1:
                self._complete_tournament(tournament, winner_user_id=winners[0] if winners else None)
                progressed = True
                continue

            next_round_number = current_round.round_number + 1
            tournament.current_round = next_round_number
            self._create_round_matches(
                tournament=tournament,
                round_number=next_round_number,
                ordered_user_ids=winners,
                bracket_style="sequential",
            )
            progressed = True

    def _create_round_matches(
        self,
        *,
        tournament: Tournament,
        round_number: int,
        ordered_user_ids: list[str],
        bracket_style: str,
    ) -> None:
        now = utcnow()
        round_entry = TournamentRound(
            tournament_id=tournament.id,
            round_number=round_number,
            status=TournamentRoundStatus.ACTIVE.value,
            starts_at=now,
            timeout_at=now + timedelta(minutes=tournament.round_timeout_minutes),
        )
        self.session.add(round_entry)
        self.session.flush()

        if bracket_style == "seeded":
            pairings = self.generate_bracket(ordered_user_ids)
        else:
            pairings = self.advance_winners(ordered_user_ids)

        for slot_index, (player_one_user_id, player_two_user_id) in enumerate(pairings, start=1):
            match = TournamentMatch(
                tournament_id=tournament.id,
                round_id=round_entry.id,
                round_number=round_number,
                slot_index=slot_index,
                player_one_user_id=player_one_user_id,
                player_two_user_id=player_two_user_id,
                status=TournamentMatchStatus.SCHEDULED.value,
                metadata_json={},
            )
            self.session.add(match)
            self.session.flush()
            if player_one_user_id and not player_two_user_id:
                self._complete_match(match, winner_user_id=player_one_user_id, resolution="bye")
            elif player_two_user_id and not player_one_user_id:
                self._complete_match(match, winner_user_id=player_two_user_id, resolution="bye")

    def _timeout_winner(self, match: TournamentMatch) -> str | None:
        if match.player_one_user_id and not match.player_two_user_id:
            return match.player_one_user_id
        if match.player_two_user_id and not match.player_one_user_id:
            return match.player_two_user_id
        if not match.player_one_user_id or not match.player_two_user_id:
            return None

        players = self.session.scalars(
            select(TournamentPlayer).where(
                TournamentPlayer.tournament_id == match.tournament_id,
                TournamentPlayer.user_id.in_((match.player_one_user_id, match.player_two_user_id)),
            )
        ).all()
        slots = {player.user_id: player.bracket_slot for player in players}
        if slots.get(match.player_one_user_id, math.inf) <= slots.get(match.player_two_user_id, math.inf):
            return match.player_one_user_id
        return match.player_two_user_id

    def _complete_match(
        self,
        match: TournamentMatch,
        *,
        winner_user_id: str,
        resolution: str,
        player_one_score: int | None = None,
        player_two_score: int | None = None,
    ) -> None:
        if winner_user_id not in {match.player_one_user_id, match.player_two_user_id}:
            raise TournamentValidationError("Winner must belong to the match.", reason="invalid_winner")

        match.winner_user_id = winner_user_id
        match.player_one_score = player_one_score
        match.player_two_score = player_two_score
        match.status = TournamentMatchStatus.COMPLETED.value
        match.resolution = resolution
        match.completed_at = utcnow()

        loser_user_id = None
        if match.player_one_user_id == winner_user_id:
            loser_user_id = match.player_two_user_id
        elif match.player_two_user_id == winner_user_id:
            loser_user_id = match.player_one_user_id

        winner = self._get_player(match.tournament_id, winner_user_id)
        if winner is not None and winner.status != TournamentPlayerStatus.WINNER.value:
            winner.status = TournamentPlayerStatus.ACTIVE.value
        if loser_user_id is not None:
            loser = self._get_player(match.tournament_id, loser_user_id)
            if loser is not None:
                loser.status = TournamentPlayerStatus.ELIMINATED.value

    def _complete_tournament(self, tournament: Tournament, *, winner_user_id: str | None) -> None:
        tournament.status = TournamentStatus.COMPLETED.value
        tournament.completed_at = utcnow()
        tournament.winner_user_id = winner_user_id
        if winner_user_id is not None:
            winner = self._get_player(tournament.id, winner_user_id)
            if winner is not None:
                winner.status = TournamentPlayerStatus.WINNER.value

    def _supports_row_locks(self) -> bool:
        bind = self.session.get_bind()
        return bind is not None and bind.dialect.name != "sqlite"

    def _join_lock(self, tournament_id: str):
        assert self.lock_service is not None
        return self.lock_service.tournament_join_lock(tournament_id)

    def _state_lock(self, tournament_id: str):
        assert self.lock_service is not None
        return self.lock_service.tournament_state_lock(tournament_id)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _build_view(self, tournament: Tournament) -> dict[str, object]:
        players = self._list_players(tournament.id)
        rounds = self._list_rounds(tournament.id)
        matches = self._list_matches(tournament.id)
        user_ids = {player.user_id for player in players}
        users = self.session.scalars(select(User).where(User.id.in_(tuple(user_ids)))).all() if user_ids else []
        users_by_id = {user.id: user for user in users}
        return {
            "tournament_id": tournament.id,
            "name": tournament.name,
            "game_type": TournamentGameType(tournament.game_type),
            "entry_fee": tournament.entry_fee,
            "max_players": tournament.max_players,
            "status": TournamentStatus(tournament.status),
            "rounds": tournament.rounds,
            "current_round": tournament.current_round,
            "prize_pool": tournament.prize_pool,
            "round_timeout_minutes": tournament.round_timeout_minutes,
            "player_count": len(players),
            "spots_remaining": max(tournament.max_players - len(players), 0),
            "started_at": tournament.started_at,
            "completed_at": tournament.completed_at,
            "winner_user_id": tournament.winner_user_id,
            "players": [
                {
                    "user_id": player.user_id,
                    "display_name": users_by_id.get(player.user_id).display_name if users_by_id.get(player.user_id) else None,
                    "bracket_slot": player.bracket_slot,
                    "status": player.status,
                    "joined_at": player.joined_at,
                }
                for player in players
            ],
            "rounds_detail": [
                {
                    "round_number": round_entry.round_number,
                    "status": round_entry.status,
                    "starts_at": round_entry.starts_at,
                    "timeout_at": round_entry.timeout_at,
                    "completed_at": round_entry.completed_at,
                }
                for round_entry in rounds
            ],
            "matches": [
                {
                    "match_id": match.id,
                    "round_number": match.round_number,
                    "slot_index": match.slot_index,
                    "player_one_user_id": match.player_one_user_id,
                    "player_two_user_id": match.player_two_user_id,
                    "winner_user_id": match.winner_user_id,
                    "player_one_score": match.player_one_score,
                    "player_two_score": match.player_two_score,
                    "status": match.status,
                    "resolution": match.resolution,
                    "completed_at": match.completed_at,
                }
                for match in matches
            ],
            "metadata_json": dict(tournament.metadata_json or {}),
        }

    @staticmethod
    def _round_count(max_players: int) -> int:
        return int(math.log2(TournamentService._next_power_of_two(max_players)))

    @staticmethod
    def _next_power_of_two(value: int) -> int:
        bracket = 1
        while bracket < value:
            bracket *= 2
        return bracket
