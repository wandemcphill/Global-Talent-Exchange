from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_UNRESOLVED_REPORT_PATH = Path("/tmp/unresolved_mappings_report.csv")


@dataclass(frozen=True, slots=True)
class UnresolvedMappingRecord:
    club_name: str | None
    country_name: str | None
    competition_name: str | None
    occurrence_count: int
    sample_player_names: tuple[str, ...] = ()

    def csv_row(self) -> dict[str, str]:
        return {
            "club_name": self.club_name or "",
            "country_name": self.country_name or "",
            "count": str(self.occurrence_count),
            "examples": " | ".join(self.sample_player_names),
        }


@dataclass(slots=True)
class _MutableUnresolvedMappingRecord:
    club_name: str | None
    country_name: str | None
    competition_name: str | None
    occurrence_count: int = 0
    sample_player_names: list[str] = field(default_factory=list)

    def to_record(self) -> UnresolvedMappingRecord:
        return UnresolvedMappingRecord(
            club_name=self.club_name,
            country_name=self.country_name,
            competition_name=self.competition_name,
            occurrence_count=self.occurrence_count,
            sample_player_names=tuple(self.sample_player_names),
        )


@dataclass(slots=True)
class UnresolvedMappingLogger:
    csv_path: Path = field(default_factory=lambda: DEFAULT_UNRESOLVED_REPORT_PATH)
    _records: dict[tuple[str, str, str], _MutableUnresolvedMappingRecord] = field(default_factory=dict, init=False)

    def record(
        self,
        *,
        raw_club_name: str | None,
        raw_country_name: str | None,
        competition_name: str | None = None,
        player_name: str | None = None,
    ) -> None:
        club_name = (raw_club_name or "").strip() or None
        country_name = (raw_country_name or "").strip() or None
        competition = (competition_name or "").strip() or None
        key = (club_name or "", country_name or "", competition or "")
        entry = self._records.get(key)
        if entry is None:
            entry = _MutableUnresolvedMappingRecord(
                club_name=club_name,
                country_name=country_name,
                competition_name=competition,
            )
            self._records[key] = entry
        entry.occurrence_count += 1
        if player_name:
            cleaned_name = player_name.strip()
            if cleaned_name and cleaned_name not in entry.sample_player_names and len(entry.sample_player_names) < 3:
                entry.sample_player_names.append(cleaned_name)

    def summary(self) -> list[UnresolvedMappingRecord]:
        return sorted(
            (entry.to_record() for entry in self._records.values()),
            key=lambda item: (
                -item.occurrence_count,
                (item.club_name or "").casefold(),
                (item.country_name or "").casefold(),
                (item.competition_name or "").casefold(),
            ),
        )

    def write_csv(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.csv_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("club_name", "country_name", "count", "examples"))
            writer.writeheader()
            for record in self.summary():
                writer.writerow(record.csv_row())
        return target


__all__ = [
    "DEFAULT_UNRESOLVED_REPORT_PATH",
    "UnresolvedMappingLogger",
    "UnresolvedMappingRecord",
]
