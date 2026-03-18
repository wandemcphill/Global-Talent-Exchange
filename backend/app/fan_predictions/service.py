from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.admin_engine.service import AdminEngineService
from backend.app.models.club_profile import ClubProfile
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_match_event import CompetitionMatchEvent
from backend.app.models.creator_fan_engagement import CreatorClubFollow, CreatorFanGroup, CreatorFanGroupMembership
from backend.app.models.creator_league import CreatorLeagueSeason, CreatorLeagueSeasonTier
from backend.app.models.creator_monetization import CreatorSeasonPass
from backend.app.models.fan_prediction import (
    FanPredictionFixture,
    FanPredictionFixtureStatus,
    FanPredictionLeaderboardScope,
    FanPredictionOutcome,
    FanPredictionRewardGrant,
    FanPredictionRewardType,
    FanPredictionSubmission,
    FanPredictionSubmissionStatus,
    FanPredictionTokenLedger,
    FanPredictionTokenReason,
)
from backend.app.models.reward_settlement import RewardSettlement
from backend.app.models.user import User, UserRole
from backend.app.reward_engine.service import RewardEngineService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_OPEN_BEFORE = timedelta(hours=24)
DEFAULT_LOCK_BEFORE = timedelta(minutes=5)
DAILY_REFILL_TOKENS = 5
SEASON_PASS_BONUS_TOKENS_PER_PASS = 1
SCORING_RULES = (
    ("winner", "Match Winner", 3, "Correctly predict the winning club."),
    ("first_goal_scorer", "First Goal Scorer", 5, "Correctly predict the first goal scorer."),
    ("total_goals", "Total Goals", 3, "Correctly predict the exact total goals."),
    ("mvp", "MVP Player", 4, "Correctly predict the awarded MVP player."),
)
PERFECT_CARD_BONUS = 5


class FanPredictionError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class FanPredictionService:
    session: Session
    reward_engine: RewardEngineService | None = None

    def __post_init__(self) -> None:
        if self.reward_engine is None:
            self.reward_engine = RewardEngineService(self.session)

    def scoring_payload(self) -> dict[str, object]:
        return {
            "rules": [
                {"key": key, "label": label, "points": points, "description": description}
                for key, label, points, description in SCORING_RULES
            ],
            "perfect_card_bonus": PERFECT_CARD_BONUS,
            "daily_refill_tokens": DAILY_REFILL_TOKENS,
            "season_pass_bonus_tokens_per_pass": SEASON_PASS_BONUS_TOKENS_PER_PASS,
        }

    def ensure_fixture(
        self,
        *,
        match_id: str,
        actor: User | None = None,
        title: str | None = None,
        description: str | None = None,
        opens_at: datetime | None = None,
        locks_at: datetime | None = None,
        token_cost: int | None = None,
        promo_pool_fancoin: Decimal | None = None,
        badge_code: str | None = None,
        max_reward_winners: int | None = None,
        allow_creator_club_segmentation: bool | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> FanPredictionFixture:
        match = self.session.get(CompetitionMatch, match_id)
        if match is None:
            raise FanPredictionError("Prediction match was not found.", reason="match_not_found")
        fixture = self.session.scalar(select(FanPredictionFixture).where(FanPredictionFixture.match_id == match_id))
        season_id = self._resolve_season_id(match)
        default_open, default_lock = self._default_window(match)
        merged_metadata = dict(fixture.metadata_json if fixture is not None else {})
        merged_metadata.update(metadata_json or {})
        if fixture is None:
            fixture = FanPredictionFixture(
                match_id=match.id,
                competition_id=match.competition_id,
                season_id=season_id,
                home_club_id=match.home_club_id,
                away_club_id=match.away_club_id,
                created_by_user_id=actor.id if actor is not None else None,
                title=title or self._default_title(match),
                description=description,
                opens_at=self._coerce_datetime(opens_at) or default_open,
                locks_at=self._coerce_datetime(locks_at) or default_lock,
                token_cost=token_cost or 1,
                promo_pool_fancoin=self._normalize_decimal(promo_pool_fancoin or Decimal("0.0000")),
                badge_code=badge_code,
                max_reward_winners=max_reward_winners or 3,
                allow_creator_club_segmentation=(
                    True if allow_creator_club_segmentation is None else bool(allow_creator_club_segmentation)
                ),
                metadata_json=merged_metadata,
            )
            self.session.add(fixture)
        else:
            if fixture.settled_at is not None:
                raise FanPredictionError(
                    "Settled prediction fixtures cannot be reconfigured.",
                    reason="fixture_already_settled",
                )
            fixture.competition_id = match.competition_id
            fixture.season_id = season_id
            fixture.home_club_id = match.home_club_id
            fixture.away_club_id = match.away_club_id
            fixture.title = title or fixture.title
            fixture.description = description if description is not None else fixture.description
            fixture.opens_at = self._coerce_datetime(opens_at) or fixture.opens_at or default_open
            fixture.locks_at = self._coerce_datetime(locks_at) or fixture.locks_at or default_lock
            if token_cost is not None:
                fixture.token_cost = token_cost
            if promo_pool_fancoin is not None:
                fixture.promo_pool_fancoin = self._normalize_decimal(promo_pool_fancoin)
            if badge_code is not None:
                fixture.badge_code = badge_code
            if max_reward_winners is not None:
                fixture.max_reward_winners = max_reward_winners
            if allow_creator_club_segmentation is not None:
                fixture.allow_creator_club_segmentation = allow_creator_club_segmentation
            fixture.metadata_json = merged_metadata
        if fixture.locks_at <= fixture.opens_at:
            raise FanPredictionError("Prediction lock time must be after the open time.", reason="invalid_window")
        self.session.flush()
        self._refresh_fixture_status(fixture)
        return fixture

    def get_fixture(self, *, match_id: str, actor: User | None = None) -> FanPredictionFixture:
        fixture = self.session.scalar(select(FanPredictionFixture).where(FanPredictionFixture.match_id == match_id))
        if fixture is None:
            fixture = self.ensure_fixture(match_id=match_id)
        self._refresh_fixture_status(fixture)
        if actor is not None:
            self.ensure_token_refill(actor=actor)
        return fixture

    def get_outcome(self, *, fixture_id: str) -> FanPredictionOutcome | None:
        return self.session.scalar(select(FanPredictionOutcome).where(FanPredictionOutcome.fixture_id == fixture_id))

    def list_reward_grants(self, *, fixture_id: str) -> list[FanPredictionRewardGrant]:
        return list(
            self.session.scalars(
                select(FanPredictionRewardGrant)
                .where(FanPredictionRewardGrant.fixture_id == fixture_id)
                .order_by(FanPredictionRewardGrant.created_at.asc(), FanPredictionRewardGrant.id.asc())
            ).all()
        )

    def get_submission_for_user(self, *, fixture_id: str, user_id: str) -> FanPredictionSubmission | None:
        return self.session.scalar(
            select(FanPredictionSubmission).where(
                FanPredictionSubmission.fixture_id == fixture_id,
                FanPredictionSubmission.user_id == user_id,
            )
        )

    def list_submissions_for_user(self, *, actor: User, limit: int = 50) -> list[FanPredictionSubmission]:
        return list(
            self.session.scalars(
                select(FanPredictionSubmission)
                .where(FanPredictionSubmission.user_id == actor.id)
                .order_by(FanPredictionSubmission.updated_at.desc(), FanPredictionSubmission.id.desc())
                .limit(limit)
            ).all()
        )

    def ensure_token_refill(self, *, actor: User, today: date | None = None) -> None:
        effective_date = today or datetime.now(UTC).date()
        refill_key = f"daily-refill:{actor.id}:{effective_date.isoformat()}"
        existing_refill = self.session.scalar(
            select(FanPredictionTokenLedger).where(FanPredictionTokenLedger.unique_key == refill_key)
        )
        if existing_refill is None:
            self.session.add(
                FanPredictionTokenLedger(
                    user_id=actor.id,
                    created_by_user_id=actor.id,
                    reason=FanPredictionTokenReason.DAILY_REFILL,
                    amount=DAILY_REFILL_TOKENS,
                    effective_date=effective_date,
                    unique_key=refill_key,
                    reference=refill_key,
                    note="Daily free prediction token refill",
                    metadata_json={"system_funded": True, "real_money_wagering": False},
                )
            )
        for season_pass in self._active_season_passes(actor=actor, effective_date=effective_date):
            bonus_key = f"season-pass-bonus:{season_pass.id}:{effective_date.isoformat()}"
            existing_bonus = self.session.scalar(
                select(FanPredictionTokenLedger).where(FanPredictionTokenLedger.unique_key == bonus_key)
            )
            if existing_bonus is not None:
                continue
            self.session.add(
                FanPredictionTokenLedger(
                    user_id=actor.id,
                    season_pass_id=season_pass.id,
                    created_by_user_id=actor.id,
                    reason=FanPredictionTokenReason.SEASON_PASS_BONUS,
                    amount=SEASON_PASS_BONUS_TOKENS_PER_PASS,
                    effective_date=effective_date,
                    unique_key=bonus_key,
                    reference=bonus_key,
                    note="Creator season pass daily bonus token",
                    metadata_json={
                        "season_id": season_pass.season_id,
                        "club_id": season_pass.club_id,
                        "real_money_wagering": False,
                    },
                )
            )
        self.session.flush()

    def token_summary(self, *, actor: User, today: date | None = None, ledger_limit: int = 20) -> dict[str, object]:
        effective_date = today or datetime.now(UTC).date()
        self.ensure_token_refill(actor=actor, today=effective_date)
        ledger = list(
            self.session.scalars(
                select(FanPredictionTokenLedger)
                .where(FanPredictionTokenLedger.user_id == actor.id)
                .order_by(FanPredictionTokenLedger.created_at.desc(), FanPredictionTokenLedger.id.desc())
                .limit(ledger_limit)
            ).all()
        )
        available_tokens = int(
            self.session.scalar(
                select(func.coalesce(func.sum(FanPredictionTokenLedger.amount), 0)).where(
                    FanPredictionTokenLedger.user_id == actor.id
                )
            )
            or 0
        )
        today_entries = [
            item
            for item in ledger
            if item.effective_date == effective_date
            and item.reason in {FanPredictionTokenReason.DAILY_REFILL, FanPredictionTokenReason.SEASON_PASS_BONUS}
        ]
        return {
            "available_tokens": available_tokens,
            "daily_refill_tokens": DAILY_REFILL_TOKENS,
            "season_pass_bonus_tokens": sum(
                item.amount for item in today_entries if item.reason == FanPredictionTokenReason.SEASON_PASS_BONUS
            ),
            "today_token_grants": sum(item.amount for item in today_entries),
            "latest_effective_date": ledger[0].effective_date if ledger else None,
            "ledger": ledger,
        }

    def submit_prediction(
        self,
        *,
        actor: User,
        match_id: str,
        winner_club_id: str,
        first_goal_scorer_player_id: str,
        total_goals: int,
        mvp_player_id: str,
        fan_segment_club_id: str | None = None,
        fan_group_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> FanPredictionSubmission:
        fixture = self.get_fixture(match_id=match_id, actor=actor)
        current_time = self._coerce_datetime(now) or datetime.now(UTC)
        self._refresh_fixture_status(fixture, now=current_time)
        if fixture.status != FanPredictionFixtureStatus.OPEN:
            raise FanPredictionError("Prediction window is closed for this match.", reason="prediction_window_closed")
        valid_club_ids = {fixture.home_club_id, fixture.away_club_id}
        if winner_club_id not in valid_club_ids:
            raise FanPredictionError("Winner prediction must target one of the match clubs.", reason="winner_invalid")
        if fan_segment_club_id is not None and fan_segment_club_id not in valid_club_ids:
            raise FanPredictionError(
                "Fan segment club must be one of the creator clubs in the selected match.",
                reason="fan_segment_invalid",
            )
        self._validate_fan_segment(
            actor=actor,
            fixture=fixture,
            fan_segment_club_id=fan_segment_club_id,
            fan_group_id=fan_group_id,
        )
        submission = self.get_submission_for_user(fixture_id=fixture.id, user_id=actor.id)
        if submission is None:
            summary = self.token_summary(actor=actor, today=current_time.date(), ledger_limit=5)
            if int(summary["available_tokens"]) < fixture.token_cost:
                raise FanPredictionError(
                    "Free prediction tokens are exhausted for now. Wait for the next refill or use season pass bonuses.",
                    reason="insufficient_prediction_tokens",
                )
            submission = FanPredictionSubmission(
                fixture_id=fixture.id,
                user_id=actor.id,
                fan_segment_club_id=fan_segment_club_id,
                fan_group_id=fan_group_id,
                leaderboard_week_start=self._week_start_for_datetime(fixture.locks_at),
                winner_club_id=winner_club_id,
                first_goal_scorer_player_id=first_goal_scorer_player_id,
                total_goals=total_goals,
                mvp_player_id=mvp_player_id,
                tokens_spent=fixture.token_cost,
                metadata_json=dict(metadata_json or {}),
            )
            self.session.add(submission)
            self.session.flush()
            self.session.add(
                FanPredictionTokenLedger(
                    user_id=actor.id,
                    submission_id=submission.id,
                    created_by_user_id=actor.id,
                    reason=FanPredictionTokenReason.PREDICTION_SUBMISSION,
                    amount=-fixture.token_cost,
                    effective_date=current_time.date(),
                    unique_key=f"prediction-submission:{submission.id}",
                    reference=f"prediction-submission:{submission.id}",
                    note=f"Prediction submission for fixture {fixture.id}",
                    metadata_json={
                        "fixture_id": fixture.id,
                        "match_id": fixture.match_id,
                        "real_money_wagering": False,
                    },
                )
            )
        else:
            if submission.status == FanPredictionSubmissionStatus.SETTLED:
                raise FanPredictionError("Settled predictions cannot be edited.", reason="prediction_already_settled")
            submission.fan_segment_club_id = fan_segment_club_id
            submission.fan_group_id = fan_group_id
            submission.winner_club_id = winner_club_id
            submission.first_goal_scorer_player_id = first_goal_scorer_player_id
            submission.total_goals = total_goals
            submission.mvp_player_id = mvp_player_id
            submission.metadata_json = dict(metadata_json or submission.metadata_json)
        self.session.flush()
        return submission

    def attempt_match_settlement(
        self,
        *,
        match_id: str,
        actor: User | None = None,
        winner_club_id: str | None = None,
        first_goal_scorer_player_id: str | None = None,
        total_goals: int | None = None,
        mvp_player_id: str | None = None,
        note: str | None = None,
        metadata_json: dict[str, object] | None = None,
        disburse_rewards: bool = True,
        create_if_missing: bool = False,
    ) -> FanPredictionFixture | None:
        fixture = self.session.scalar(select(FanPredictionFixture).where(FanPredictionFixture.match_id == match_id))
        if fixture is None:
            if not create_if_missing:
                return None
            fixture = self.ensure_fixture(match_id=match_id, actor=actor)
        match = self.session.get(CompetitionMatch, match_id)
        if match is None:
            raise FanPredictionError("Prediction match was not found.", reason="match_not_found")
        if match.status != "completed":
            self._refresh_fixture_status(fixture)
            return fixture
        outcome = self._derive_outcome(
            fixture=fixture,
            match=match,
            winner_club_id=winner_club_id,
            first_goal_scorer_player_id=first_goal_scorer_player_id,
            total_goals=total_goals,
            mvp_player_id=mvp_player_id,
            note=note,
            metadata_json=metadata_json or {},
            actor=actor,
        )
        if outcome.mvp_player_id is None:
            fixture.status = FanPredictionFixtureStatus.PENDING_SETTLEMENT
            self.session.flush()
            return fixture
        fixture.status = FanPredictionFixtureStatus.SETTLED
        fixture.settled_at = fixture.settled_at or datetime.now(UTC)
        submissions = list(
            self.session.scalars(
                select(FanPredictionSubmission)
                .where(FanPredictionSubmission.fixture_id == fixture.id)
                .order_by(FanPredictionSubmission.created_at.asc(), FanPredictionSubmission.id.asc())
            ).all()
        )
        for submission in submissions:
            self._score_submission(submission=submission, outcome=outcome)
        if disburse_rewards:
            self._disburse_fixture_rewards(fixture=fixture, actor=actor)
        self.session.flush()
        return fixture

    def fixture_leaderboard(self, *, match_id: str, limit: int = 20) -> dict[str, object]:
        fixture = self.get_fixture(match_id=match_id)
        entries: list[dict[str, object]] = []
        if fixture.status == FanPredictionFixtureStatus.SETTLED:
            submissions = self._ordered_submissions(fixture_id=fixture.id)
            for index, submission in enumerate(submissions[:limit], start=1):
                user = self.session.get(User, submission.user_id)
                entries.append(
                    {
                        "rank": index,
                        "user_id": submission.user_id,
                        "username": user.username if user is not None else submission.user_id,
                        "display_name": user.display_name if user is not None else None,
                        "fan_segment_club_id": submission.fan_segment_club_id,
                        "total_points": submission.points_awarded,
                        "settled_predictions": 1,
                        "correct_pick_count": submission.correct_pick_count,
                        "perfect_cards": 1 if submission.perfect_card else 0,
                    }
                )
        return {
            "scope": "match",
            "week_start": self._week_start_for_datetime(fixture.locks_at),
            "fixture_id": fixture.id,
            "club_id": None,
            "entries": entries,
        }

    def weekly_leaderboard(self, *, week_start: date | None = None, limit: int = 25) -> dict[str, object]:
        resolved_week = week_start or self._week_start_for_datetime(datetime.now(UTC))
        return {
            "scope": "weekly",
            "week_start": resolved_week,
            "fixture_id": None,
            "club_id": None,
            "entries": self._aggregate_leaderboard(week_start=resolved_week, club_id=None, limit=limit),
        }

    def creator_club_weekly_leaderboard(
        self,
        *,
        club_id: str,
        week_start: date | None = None,
        limit: int = 25,
    ) -> dict[str, object]:
        self._require_club(club_id)
        resolved_week = week_start or self._week_start_for_datetime(datetime.now(UTC))
        return {
            "scope": "creator_club_weekly",
            "week_start": resolved_week,
            "fixture_id": None,
            "club_id": club_id,
            "entries": self._aggregate_leaderboard(week_start=resolved_week, club_id=club_id, limit=limit),
        }

    def _aggregate_leaderboard(self, *, week_start: date, club_id: str | None, limit: int) -> list[dict[str, object]]:
        stmt = select(FanPredictionSubmission).where(
            FanPredictionSubmission.leaderboard_week_start == week_start,
            FanPredictionSubmission.status == FanPredictionSubmissionStatus.SETTLED,
        )
        if club_id is not None:
            stmt = stmt.where(FanPredictionSubmission.fan_segment_club_id == club_id)
        submissions = list(self.session.scalars(stmt).all())
        grouped: dict[str, dict[str, object]] = {}
        for submission in submissions:
            entry = grouped.get(submission.user_id)
            if entry is None:
                user = self.session.get(User, submission.user_id)
                entry = {
                    "user_id": submission.user_id,
                    "username": user.username if user is not None else submission.user_id,
                    "display_name": user.display_name if user is not None else None,
                    "fan_segment_club_id": club_id,
                    "total_points": 0,
                    "settled_predictions": 0,
                    "correct_pick_count": 0,
                    "perfect_cards": 0,
                }
                grouped[submission.user_id] = entry
            entry["total_points"] = int(entry["total_points"]) + submission.points_awarded
            entry["settled_predictions"] = int(entry["settled_predictions"]) + 1
            entry["correct_pick_count"] = int(entry["correct_pick_count"]) + submission.correct_pick_count
            entry["perfect_cards"] = int(entry["perfect_cards"]) + (1 if submission.perfect_card else 0)
        ordered = sorted(
            grouped.values(),
            key=lambda item: (
                -int(item["total_points"]),
                -int(item["perfect_cards"]),
                -int(item["correct_pick_count"]),
                -int(item["settled_predictions"]),
                str(item["username"]),
            ),
        )
        result: list[dict[str, object]] = []
        for index, item in enumerate(ordered[:limit], start=1):
            result.append({"rank": index, **item})
        return result

    def _disburse_fixture_rewards(self, *, fixture: FanPredictionFixture, actor: User | None) -> None:
        if fixture.rewards_disbursed_at is not None:
            return
        fairness_controls = self._fan_prediction_fairness_controls()
        configured_reward_amount = self._normalize_decimal(fixture.promo_pool_fancoin)
        participant_count = self._distinct_participant_count(fixture_id=fixture.id)
        reward_amount = self._effective_fancoin_reward_pool(
            configured_amount=configured_reward_amount,
            participant_count=participant_count,
        )
        badge_code = fixture.badge_code
        payout_status = "eligible"
        if participant_count < int(fairness_controls.min_distinct_participants_for_fancoin):
            payout_status = "fancoin_withheld_low_participation"
        elif reward_amount < configured_reward_amount:
            payout_status = "fancoin_capped"
        fixture.metadata_json = {
            **(fixture.metadata_json or {}),
            "fan_prediction_fairness": {
                "distinct_participants": participant_count,
                "winner_cap": self._reward_winner_cap(fixture),
                "configured_promo_pool_fancoin": str(configured_reward_amount),
                "effective_promo_pool_fancoin": str(reward_amount),
                "min_distinct_participants_for_fancoin": int(fairness_controls.min_distinct_participants_for_fancoin),
                "max_fixture_promo_pool_fancoin": str(
                    self._normalize_decimal(fairness_controls.max_fixture_promo_pool_fancoin)
                ),
                "max_fancoin_pool_per_participant": str(
                    self._normalize_decimal(fairness_controls.max_fancoin_pool_per_participant)
                ),
                "reward_payout_status": payout_status,
            },
        }
        if reward_amount <= Decimal("0.0000") and not badge_code:
            fixture.rewards_disbursed_at = fixture.rewards_disbursed_at or datetime.now(UTC)
            return
        winners = self._ranked_reward_winners(fixture=fixture)
        if not winners:
            fixture.rewards_disbursed_at = fixture.rewards_disbursed_at or datetime.now(UTC)
            return
        reward_actor = actor or self._default_reward_actor()
        if reward_actor is None:
            fixture.metadata_json = {
                **(fixture.metadata_json or {}),
                "reward_payout_status": "awaiting_admin_actor",
            }
            return
        allocations = self._reward_allocations(total_amount=reward_amount, winner_count=len(winners))
        competition_key = f"fan_prediction:{fixture.match_id}"
        for rank, submission in enumerate(winners, start=1):
            allocation = allocations[rank - 1] if allocations else Decimal("0.0000")
            reward_reference = f"{competition_key}:{submission.id}:{rank}"
            settlement: RewardSettlement | None = None
            if allocation > Decimal("0.0000"):
                settlement = self.reward_engine.settle_reward(
                    actor=reward_actor,
                    user_id=submission.user_id,
                    competition_key=competition_key,
                    title=f"Fan prediction reward for {fixture.title}",
                    gross_amount=allocation,
                    reward_source=fixture.reward_funding_source,
                    note=f"GTEX promotional reward for fan prediction fixture {fixture.id}",
                )
                self.session.flush()
                self.session.add(
                    FanPredictionRewardGrant(
                        user_id=submission.user_id,
                        fixture_id=fixture.id,
                        submission_id=submission.id,
                        club_id=submission.fan_segment_club_id,
                        reward_settlement_id=settlement.id if settlement is not None else None,
                        awarded_by_user_id=reward_actor.id,
                        leaderboard_scope=FanPredictionLeaderboardScope.MATCH,
                        reward_type=FanPredictionRewardType.FANCOIN,
                        rank=rank,
                        week_start=submission.leaderboard_week_start,
                        fancoin_amount=allocation,
                        promo_pool_reference=reward_reference,
                        unique_key=f"prediction-fancoin-reward:{submission.id}",
                        metadata_json={
                            "fixture_id": fixture.id,
                            "real_money_wagering": False,
                            "promo_funded": True,
                        },
                    )
                )
            if badge_code:
                self.session.add(
                    FanPredictionRewardGrant(
                        user_id=submission.user_id,
                        fixture_id=fixture.id,
                        submission_id=submission.id,
                        club_id=submission.fan_segment_club_id,
                        awarded_by_user_id=reward_actor.id,
                        leaderboard_scope=FanPredictionLeaderboardScope.MATCH,
                        reward_type=FanPredictionRewardType.BADGE,
                        rank=rank,
                        week_start=submission.leaderboard_week_start,
                        badge_code=badge_code,
                        fancoin_amount=Decimal("0.0000"),
                        promo_pool_reference=reward_reference,
                        unique_key=f"prediction-badge-reward:{submission.id}",
                        metadata_json={
                            "fixture_id": fixture.id,
                            "badge_code": badge_code,
                            "cosmetic_only": True,
                        },
                    )
                )
            submission.reward_rank = rank
        fixture.rewards_disbursed_at = datetime.now(UTC)

    def _score_submission(self, *, submission: FanPredictionSubmission, outcome: FanPredictionOutcome) -> None:
        winner_correct = outcome.winner_club_id is not None and submission.winner_club_id == outcome.winner_club_id
        first_goal_correct = (
            outcome.first_goal_scorer_player_id is not None
            and submission.first_goal_scorer_player_id == outcome.first_goal_scorer_player_id
        )
        total_goals_correct = submission.total_goals == outcome.total_goals
        mvp_correct = outcome.mvp_player_id is not None and submission.mvp_player_id == outcome.mvp_player_id
        points = 0
        correct_pick_count = 0
        for key, _label, score, _description in SCORING_RULES:
            is_correct = {
                "winner": winner_correct,
                "first_goal_scorer": first_goal_correct,
                "total_goals": total_goals_correct,
                "mvp": mvp_correct,
            }[key]
            if is_correct:
                points += score
                correct_pick_count += 1
        perfect_card = correct_pick_count == 4
        if perfect_card:
            points += PERFECT_CARD_BONUS
        submission.status = FanPredictionSubmissionStatus.SETTLED
        submission.points_awarded = points
        submission.correct_pick_count = correct_pick_count
        submission.perfect_card = perfect_card
        submission.settled_at = datetime.now(UTC)

    def _derive_outcome(
        self,
        *,
        fixture: FanPredictionFixture,
        match: CompetitionMatch,
        winner_club_id: str | None,
        first_goal_scorer_player_id: str | None,
        total_goals: int | None,
        mvp_player_id: str | None,
        note: str | None,
        metadata_json: dict[str, object],
        actor: User | None,
    ) -> FanPredictionOutcome:
        existing = self.session.scalar(select(FanPredictionOutcome).where(FanPredictionOutcome.fixture_id == fixture.id))
        first_goal_event = self._first_goal_event(match_id=match.id)
        resolved_mvp = mvp_player_id or self._match_metadata_player(match, "mvp_player_id") or self._mvp_event_player(match.id)
        outcome = existing or FanPredictionOutcome(fixture_id=fixture.id, match_id=match.id)
        outcome.winner_club_id = winner_club_id or match.winner_club_id
        outcome.first_goal_scorer_player_id = (
            first_goal_scorer_player_id
            or (first_goal_event.player_id if first_goal_event is not None else None)
        )
        outcome.total_goals = total_goals if total_goals is not None else int(match.home_score + match.away_score)
        outcome.mvp_player_id = resolved_mvp
        outcome.source = "admin_override" if actor is not None and any(
            value is not None for value in (winner_club_id, first_goal_scorer_player_id, total_goals, mvp_player_id)
        ) else "match_completion"
        outcome.settled_by_user_id = actor.id if actor is not None else outcome.settled_by_user_id
        outcome.note = note
        outcome.metadata_json = {
            "match_completed_at": match.completed_at.isoformat() if match.completed_at is not None else None,
            "match_status": match.status,
            "first_goal_event_id": first_goal_event.id if first_goal_event is not None else None,
            **metadata_json,
        }
        if existing is None:
            self.session.add(outcome)
        self.session.flush()
        return outcome

    def _ordered_submissions(self, *, fixture_id: str) -> list[FanPredictionSubmission]:
        submissions = list(
            self.session.scalars(
                select(FanPredictionSubmission)
                .where(FanPredictionSubmission.fixture_id == fixture_id)
                .order_by(FanPredictionSubmission.created_at.asc(), FanPredictionSubmission.id.asc())
            ).all()
        )
        return sorted(
            submissions,
            key=lambda item: (
                -item.points_awarded,
                -item.correct_pick_count,
                -(1 if item.perfect_card else 0),
                item.created_at,
                item.user_id,
            ),
        )

    def _ranked_reward_winners(self, *, fixture: FanPredictionFixture) -> list[FanPredictionSubmission]:
        ordered = self._ordered_submissions(fixture_id=fixture.id)
        if not ordered or ordered[0].points_awarded <= 0:
            return []
        top_score = ordered[0].points_awarded
        candidates = [item for item in ordered if item.points_awarded == top_score]
        return candidates[: self._reward_winner_cap(fixture)]

    def _reward_allocations(self, *, total_amount: Decimal, winner_count: int) -> list[Decimal]:
        if winner_count <= 0 or total_amount <= Decimal("0.0000"):
            return []
        share = (total_amount / Decimal(winner_count)).quantize(AMOUNT_QUANTUM)
        allocations = [share for _ in range(winner_count)]
        remainder = total_amount - sum(allocations, Decimal("0.0000"))
        if allocations:
            allocations[0] = (allocations[0] + remainder).quantize(AMOUNT_QUANTUM)
        return allocations

    def _refresh_fixture_status(self, fixture: FanPredictionFixture, *, now: datetime | None = None) -> None:
        current_time = self._coerce_datetime(now) or datetime.now(UTC)
        opens_at = self._coerce_datetime(fixture.opens_at) or datetime.now(UTC)
        locks_at = self._coerce_datetime(fixture.locks_at) or opens_at
        if fixture.status == FanPredictionFixtureStatus.CANCELLED:
            return
        if fixture.settled_at is not None:
            fixture.status = FanPredictionFixtureStatus.SETTLED
            return
        match = self.session.get(CompetitionMatch, fixture.match_id)
        if match is not None and match.status == "completed":
            fixture.status = FanPredictionFixtureStatus.PENDING_SETTLEMENT
        elif current_time < opens_at:
            fixture.status = FanPredictionFixtureStatus.SCHEDULED
        elif current_time < locks_at:
            fixture.status = FanPredictionFixtureStatus.OPEN
        else:
            fixture.status = FanPredictionFixtureStatus.LOCKED

    def _validate_fan_segment(
        self,
        *,
        actor: User,
        fixture: FanPredictionFixture,
        fan_segment_club_id: str | None,
        fan_group_id: str | None,
    ) -> None:
        if fan_segment_club_id is None and fan_group_id is None:
            return
        if not fixture.allow_creator_club_segmentation:
            raise FanPredictionError(
                "Creator club segmentation is disabled for this prediction fixture.",
                reason="creator_segmentation_disabled",
            )
        if fan_segment_club_id is None:
            raise FanPredictionError(
                "A creator club must be selected when attaching fan group segmentation.",
                reason="fan_segment_required",
            )
        if fan_group_id is not None:
            membership = self.session.scalar(
                select(CreatorFanGroupMembership)
                .where(
                    CreatorFanGroupMembership.group_id == fan_group_id,
                    CreatorFanGroupMembership.user_id == actor.id,
                    CreatorFanGroupMembership.club_id == fan_segment_club_id,
                )
            )
            if membership is None:
                raise FanPredictionError(
                    "Selected fan group does not belong to the user for this creator club.",
                    reason="fan_group_membership_missing",
                )
            group = self.session.get(CreatorFanGroup, fan_group_id)
            if group is None or group.club_id != fan_segment_club_id:
                raise FanPredictionError("Fan group does not match the selected creator club.", reason="fan_group_invalid")
            return
        has_follow = self.session.scalar(
            select(CreatorClubFollow.id).where(
                CreatorClubFollow.club_id == fan_segment_club_id,
                CreatorClubFollow.user_id == actor.id,
            )
        )
        has_season_pass = self.session.scalar(
            select(CreatorSeasonPass.id).where(
                CreatorSeasonPass.user_id == actor.id,
                CreatorSeasonPass.club_id == fan_segment_club_id,
                CreatorSeasonPass.season_id == fixture.season_id,
            )
        )
        if has_follow is None and has_season_pass is None:
            raise FanPredictionError(
                "Creator club leaderboard segmentation requires an existing follow, fan group, or season pass for that club.",
                reason="creator_club_affinity_required",
            )

    def _active_season_passes(self, *, actor: User, effective_date: date) -> list[CreatorSeasonPass]:
        stmt = (
            select(CreatorSeasonPass)
            .join(CreatorLeagueSeason, CreatorLeagueSeason.id == CreatorSeasonPass.season_id)
            .where(
                CreatorSeasonPass.user_id == actor.id,
                CreatorLeagueSeason.start_date <= effective_date,
                CreatorLeagueSeason.end_date >= effective_date,
            )
            .order_by(CreatorSeasonPass.created_at.asc(), CreatorSeasonPass.id.asc())
        )
        return list(self.session.scalars(stmt).all())

    def _default_reward_actor(self) -> User | None:
        admins = list(
            self.session.scalars(
                select(User)
                .where(User.is_active.is_(True), User.role.in_((UserRole.SUPER_ADMIN, UserRole.ADMIN)))
                .order_by(User.created_at.asc(), User.id.asc())
            ).all()
        )
        if not admins:
            return None
        super_admin = next((item for item in admins if item.role == UserRole.SUPER_ADMIN), None)
        return super_admin or admins[0]

    def _default_window(self, match: CompetitionMatch) -> tuple[datetime, datetime]:
        scheduled_at = self._coerce_datetime(match.scheduled_at)
        if scheduled_at is None:
            now = datetime.now(UTC)
            return now - timedelta(minutes=1), now + timedelta(hours=1)
        return scheduled_at - DEFAULT_OPEN_BEFORE, scheduled_at - DEFAULT_LOCK_BEFORE

    def _default_title(self, match: CompetitionMatch) -> str:
        return f"Prediction Challenge {match.home_club_id} vs {match.away_club_id}"

    def _resolve_season_id(self, match: CompetitionMatch) -> str | None:
        competition = self.session.get(Competition, match.competition_id)
        if competition is None:
            return None
        season_tier = None
        if competition.source_id:
            season_tier = self.session.get(CreatorLeagueSeasonTier, competition.source_id)
        if season_tier is None:
            season_tier = self.session.scalar(
                select(CreatorLeagueSeasonTier).where(CreatorLeagueSeasonTier.competition_id == competition.id)
            )
        return season_tier.season_id if season_tier is not None else None

    def _first_goal_event(self, *, match_id: str) -> CompetitionMatchEvent | None:
        return self.session.scalar(
            select(CompetitionMatchEvent)
            .where(
                CompetitionMatchEvent.match_id == match_id,
                CompetitionMatchEvent.event_type == "goal",
            )
            .order_by(
                CompetitionMatchEvent.minute.asc().nulls_last(),
                CompetitionMatchEvent.added_time.asc().nulls_last(),
                CompetitionMatchEvent.created_at.asc(),
                CompetitionMatchEvent.id.asc(),
            )
        )

    def _mvp_event_player(self, match_id: str) -> str | None:
        event = self.session.scalar(
            select(CompetitionMatchEvent)
            .where(
                CompetitionMatchEvent.match_id == match_id,
                CompetitionMatchEvent.event_type == "mvp",
            )
            .order_by(CompetitionMatchEvent.created_at.desc(), CompetitionMatchEvent.id.desc())
        )
        return event.player_id if event is not None else None

    def _match_metadata_player(self, match: CompetitionMatch, key: str) -> str | None:
        value = (match.metadata_json or {}).get(key)
        return str(value) if isinstance(value, str) and value else None

    def _week_start_for_datetime(self, value: datetime) -> date:
        utc_value = self._coerce_datetime(value) or datetime.now(UTC)
        resolved_date = utc_value.date()
        return resolved_date - timedelta(days=resolved_date.weekday())

    def _fan_prediction_fairness_controls(self):
        return AdminEngineService(self.session).get_active_stability_controls().fan_prediction

    def _reward_winner_cap(self, fixture: FanPredictionFixture) -> int:
        fairness_controls = self._fan_prediction_fairness_controls()
        return max(1, min(int(fixture.max_reward_winners), int(fairness_controls.max_reward_winners)))

    def _distinct_participant_count(self, *, fixture_id: str) -> int:
        user_ids = self.session.scalars(
            select(FanPredictionSubmission.user_id).where(
                FanPredictionSubmission.fixture_id == fixture_id,
                FanPredictionSubmission.status != FanPredictionSubmissionStatus.CANCELLED,
            )
        ).all()
        return len({user_id for user_id in user_ids if user_id})

    def _effective_fancoin_reward_pool(self, *, configured_amount: Decimal, participant_count: int) -> Decimal:
        fairness_controls = self._fan_prediction_fairness_controls()
        if participant_count < int(fairness_controls.min_distinct_participants_for_fancoin):
            return Decimal("0.0000")
        fixture_cap = self._normalize_decimal(fairness_controls.max_fixture_promo_pool_fancoin)
        participant_cap = self._normalize_decimal(
            Decimal(participant_count) * self._normalize_decimal(fairness_controls.max_fancoin_pool_per_participant)
        )
        return self._normalize_decimal(min(configured_amount, fixture_cap, participant_cap))

    def _normalize_decimal(self, value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    def _coerce_datetime(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise FanPredictionError("Creator club was not found.", reason="club_not_found")
        return club
