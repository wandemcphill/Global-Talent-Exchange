"""Bounded, restartable Talent Exchange profile/ranking backfill.

The runner creates only the discovery projection from canonical Player rows and
then invokes the deterministic ranking pipeline. It never fabricates sporting
attributes and never writes to the economic value engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.talent.models import TalentProfile
from app.talent.service import TalentExchangeService

MAX_BATCH_SIZE = 500


@dataclass(slots=True)
class TalentBackfillReport:
    scanned: int = 0
    processed: int = 0
    failed: int = 0
    skipped: int = 0
    created_profiles: int = 0
    recomputed_rankings: int = 0
    failures: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "scanned": self.scanned,
            "processed": self.processed,
            "failed": self.failed,
            "skipped": self.skipped,
            "created_profiles": self.created_profiles,
            "recomputed_rankings": self.recomputed_rankings,
            "failures": list(self.failures),
        }


class TalentBackfillRunner:
    """Restartable cursor-based backfill for the Talent Exchange projection."""

    def __init__(self, session: Session, *, as_of: date | None = None) -> None:
        self.session = session
        self.service = TalentExchangeService(session, today=as_of)
        self.as_of = as_of

    def iter_player_ids(
        self,
        *,
        batch_size: int = MAX_BATCH_SIZE,
        only_missing: bool = True,
        after_player_id: str | None = None,
    ) -> Iterable[tuple[str, ...]]:
        size = max(1, min(MAX_BATCH_SIZE, int(batch_size)))
        cursor = after_player_id
        while True:
            statement = select(Player.id).order_by(Player.id.asc()).limit(size)
            if only_missing:
                statement = statement.outerjoin(TalentProfile, TalentProfile.player_id == Player.id).where(
                    TalentProfile.id.is_(None)
                )
            if cursor is not None:
                statement = statement.where(Player.id > cursor)
            ids = tuple(self.session.execute(statement).scalars().all())
            if not ids:
                return
            yield ids
            cursor = ids[-1]

    def run(
        self,
        *,
        batch_size: int = MAX_BATCH_SIZE,
        only_missing: bool = True,
        after_player_id: str | None = None,
        recompute_rankings: bool = True,
        continue_on_error: bool = True,
    ) -> TalentBackfillReport:
        report = TalentBackfillReport()
        for player_ids in self.iter_player_ids(
            batch_size=batch_size,
            only_missing=only_missing,
            after_player_id=after_player_id,
        ):
            report.scanned += len(player_ids)
            try:
                for player_id in player_ids:
                    self._process_player(player_id, report, recompute_rankings=recompute_rankings)
                self.session.commit()
            except Exception as exc:
                self.session.rollback()
                if not continue_on_error:
                    raise
                for player_id in player_ids:
                    try:
                        self._process_player(player_id, report, recompute_rankings=recompute_rankings)
                        self.session.commit()
                    except Exception as item_exc:
                        self.session.rollback()
                        report.failed += 1
                        report.failures.append(
                            {"player_id": player_id, "error": f"{type(item_exc).__name__}: {item_exc}"}
                        )
        return report

    def _process_player(self, player_id: str, report: TalentBackfillReport, *, recompute_rankings: bool) -> None:
        existing = self.session.scalar(select(TalentProfile).where(TalentProfile.player_id == player_id))
        profile = self.service.sync_profile_from_player(player_id, as_of=self.as_of)
        report.processed += 1
        if existing is None:
            report.created_profiles += 1
        if recompute_rankings:
            self.service.recompute_ranking(player_id, as_of=self.as_of)
            report.recomputed_rankings += 1
