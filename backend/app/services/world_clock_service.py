from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.base import utcnow
from app.models.world_clock import WorldClockState
from app.regen_universe.models import RegenSeason

logger = logging.getLogger(__name__)

DEFAULT_CLOCK_ID = "default"


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
            settings = self._get_settings()
            rate = float(getattr(settings, "world_clock_progression_rate", 1.0) or 1.0)
            start_date_str = str(getattr(settings, "world_clock_virtual_start_date", "2026-01-01") or "2026-01-01")
            months_per_season = int(getattr(settings, "world_clock_virtual_months_per_season", 12) or 12)
            try:
                parsed_start = date.fromisoformat(start_date_str)
                virtual_start = datetime(
                    parsed_start.year, parsed_start.month, parsed_start.day, 0, 0, 0, tzinfo=timezone.utc
                )
            except Exception:
                virtual_start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

            now_real = utcnow()
            state = WorldClockState(
                id=DEFAULT_CLOCK_ID,
                epoch_real_utc=now_real,
                virtual_start_time=virtual_start,
                progression_rate=rate,
                is_paused=False,
                paused_at_virtual_time=None,
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
        if state.is_paused and state.paused_at_virtual_time is not None:
            return _as_utc(state.paused_at_virtual_time)
        now_real = utcnow()
        epoch = _as_utc(state.epoch_real_utc)
        start = _as_utc(state.virtual_start_time)
        rate = float(state.progression_rate or 1.0)
        elapsed_seconds = (now_real - epoch).total_seconds()
        virtual_seconds = elapsed_seconds * rate
        return start + timedelta(seconds=virtual_seconds)

    def now_virtual_date(self) -> date:
        return self.now_virtual().date()

    def to_virtual_time(self, real_utc: datetime) -> datetime:
        state = self.get_or_create_state()
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

    def pause(self) -> WorldClockState:
        state = self.get_or_create_state()
        if not state.is_paused:
            current_virtual = self.now_virtual()
            state.is_paused = True
            state.paused_at_virtual_time = current_virtual
            self.session.flush()
        return state

    def resume(self) -> WorldClockState:
        state = self.get_or_create_state()
        if state.is_paused:
            now_real = utcnow()
            state.epoch_real_utc = now_real
            state.virtual_start_time = _as_utc(state.paused_at_virtual_time or state.virtual_start_time)
            state.is_paused = False
            state.paused_at_virtual_time = None
            self.session.flush()
        return state

    def set_rate(self, new_rate: float) -> WorldClockState:
        if new_rate <= 0:
            raise ValueError("World clock progression rate must be strictly positive.")
        state = self.get_or_create_state()
        current_virtual = self.now_virtual()
        now_real = utcnow()
        state.epoch_real_utc = now_real
        state.virtual_start_time = current_virtual
        state.progression_rate = float(new_rate)
        if state.is_paused:
            state.paused_at_virtual_time = current_virtual
        self.session.flush()
        return state

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


__all__ = ["DEFAULT_CLOCK_ID", "WorldClockService"]
