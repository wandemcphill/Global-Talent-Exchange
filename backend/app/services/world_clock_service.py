from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.base import utcnow
from app.models.world_clock import WorldClockState
from app.regen_universe.models import RegenSeason
from app.services.world_clock_pace import DEFAULT_PROGRESSION_RATE, GAME_SEASON_VIRTUAL_DAYS

logger = logging.getLogger(__name__)

DEFAULT_CLOCK_ID = "default"


class WorldClockLocked(RuntimeError):
    """The clock can be started once. After that its pace cannot be changed."""


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return utcnow()
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(slots=True)
class WorldClockService:
    session: Session
    settings: Settings | None = None

    def _get_settings(self) -> Settings | None:
        if self.settings is not None:
            return self.settings
        try:
            return get_settings()
        except Exception:
            return None

    def get_or_create_state(self) -> WorldClockState:
        state = self.session.get(WorldClockState, DEFAULT_CLOCK_ID)
        if state is None:
            now_real = utcnow()
            settings = self._get_settings()
            rate = float(
                getattr(settings, "world_clock_progression_rate", DEFAULT_PROGRESSION_RATE) or DEFAULT_PROGRESSION_RATE
            )
            start_date_str = str(getattr(settings, "world_clock_virtual_start_date", "") or "").strip()
            months_per_season = int(getattr(settings, "world_clock_virtual_months_per_season", 12) or 12)
            if start_date_str:
                try:
                    parsed_start = date.fromisoformat(start_date_str)
                    virtual_start = datetime(
                        parsed_start.year, parsed_start.month, parsed_start.day, 0, 0, 0, tzinfo=timezone.utc
                    )
                except ValueError:
                    logger.warning(
                        "world_clock.invalid_virtual_start_date value=%r; anchoring new clock to current UTC",
                        start_date_str,
                    )
                    virtual_start = now_real
            else:
                # Default to a coherent calendar: newly scheduled wall-date fixtures
                # are comparable to virtual time from the very first worker tick.
                virtual_start = now_real

            state = WorldClockState(
                id=DEFAULT_CLOCK_ID,
                epoch_real_utc=now_real,
                virtual_start_time=virtual_start,
                progression_rate=rate,
                is_paused=True,
                officially_started=False,
                paused_at_virtual_time=virtual_start,
                virtual_months_per_season=months_per_season,
                metadata_json={
                    "canonical": True,
                    "unresolved_rules": [
                        "Cadence: progression_rate configurable via GTE_WORLD_CLOCK_PROGRESSION_RATE",
                        "Virtual months per season: configurable via GTE_WORLD_CLOCK_VIRTUAL_MONTHS_PER_SEASON",
                    ],
                },
            )
            self.session.add(state)
            self.session.flush()
        return state

    def now_virtual(self) -> datetime:
        state = self.get_or_create_state()
        if not state.officially_started:
            return _as_utc(state.paused_at_virtual_time or state.virtual_start_time)
        if state.is_paused and state.paused_at_virtual_time is not None:
            return _as_utc(state.paused_at_virtual_time)
        now_real = utcnow()
        epoch = _as_utc(state.epoch_real_utc)
        start = _as_utc(state.virtual_start_time)
        rate = float(state.progression_rate or 1.0)
        elapsed_seconds = (now_real - epoch).total_seconds()
        virtual_seconds = elapsed_seconds * rate
        return start + timedelta(seconds=virtual_seconds)

    def gtex_years_running(self) -> int:
        state = self.get_or_create_state()
        v_now = self.now_virtual()
        v_start = _as_utc(state.virtual_start_time)
        return max(1, (v_now.year - v_start.year) + 1)

    def current_season_number(self) -> int:
        state = self.get_or_create_state()
        v_now = self.now_virtual()
        v_start = _as_utc(state.virtual_start_time)
        return max(1, int((v_now - v_start).days // GAME_SEASON_VIRTUAL_DAYS) + 1)

    def current_season_label(self) -> str:
        return f"GTEX Year {self.gtex_years_running()} · Season {self.current_season_number()}"

    def now_virtual_date(self) -> date:
        return self.now_virtual().date()

    def to_virtual_time(self, real_utc: datetime) -> datetime:
        state = self.get_or_create_state()
        if not state.officially_started:
            return _as_utc(state.paused_at_virtual_time or state.virtual_start_time)
        real_utc = _as_utc(real_utc)
        epoch = _as_utc(state.epoch_real_utc)
        start = _as_utc(state.virtual_start_time)
        rate = float(state.progression_rate or 1.0)
        elapsed = (real_utc - epoch).total_seconds()
        return start + timedelta(seconds=elapsed * rate)

    def to_real_utc(self, virtual_time: datetime) -> datetime:
        state = self.get_or_create_state()
        virtual_time = _as_utc(virtual_time)
        epoch = _as_utc(state.epoch_real_utc)
        start = _as_utc(state.virtual_start_time)
        rate = float(state.progression_rate or 1.0)
        if rate <= 0:
            return epoch
        virtual_delta = (virtual_time - start).total_seconds()
        real_seconds = virtual_delta / rate
        return epoch + timedelta(seconds=real_seconds)

    def season_virtual_month_index(self, season_number: int) -> int:
        state = self.get_or_create_state()
        months_per_season = state.virtual_months_per_season or 12
        return max(0, (int(season_number) - 1) * months_per_season)

    def start(self) -> WorldClockState:
        """Start the clock once, at the fixed season pace. It cannot be stopped after this."""
        state = self.get_or_create_state()
        if state.officially_started:
            raise WorldClockLocked("The game clock is already running. It cannot be paused or sped up.")
        frozen = self.now_virtual()
        now_real = utcnow()
        state.epoch_real_utc = now_real
        state.virtual_start_time = frozen
        state.progression_rate = float(DEFAULT_PROGRESSION_RATE)
        state.is_paused = False
        state.paused_at_virtual_time = None
        state.officially_started = True
        self.session.flush()
        return state

    def pause(self) -> WorldClockState:
        """Pause is not available. The clock runs until an admin starts it, then it keeps going."""
        raise WorldClockLocked("The game clock cannot be paused.")

    def resume(self) -> WorldClockState:
        """Resume is not available. Start the clock once; after that it keeps its own pace."""
        raise WorldClockLocked("The game clock cannot be paused or restarted.")

    def set_rate(self, new_rate: float) -> WorldClockState:
        """Speed is fixed. One season is 365 game days and passes in 11 human weeks."""
        raise WorldClockLocked("The game clock speed is fixed. One season is about 11 weeks.")

    def backfill_existing_seasons(self) -> int:
        """Ensure all existing RegenSeason records contain the required virtual_age_month_index."""
        seasons = list(self.session.scalars(select(RegenSeason).order_by(RegenSeason.season_number.asc())).all())
        updated_count = 0
        for season in seasons:
            meta = dict(season.metadata_json or {})
            if "virtual_age_month_index" not in meta:
                meta["virtual_age_month_index"] = self.season_virtual_month_index(season.season_number)
                season.metadata_json = meta
                updated_count += 1
        if updated_count > 0:
            self.session.flush()
        return updated_count


__all__ = ["DEFAULT_CLOCK_ID", "WorldClockLocked", "WorldClockService"]
