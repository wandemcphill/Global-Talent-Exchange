from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean, median, pstdev
from typing import Any, Sequence

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.core.database import build_alembic_config
from app.ingestion.models import Player
from app.market.repositories import SqlAlchemyMarketPlayerRepository
from app.market.service import MarketPlayerQueryService
from app.models.player_cards import PlayerMarketValueSnapshot
from app.models.regen import RegenProfile
from app.models.real_player_profile import RealPlayerProfile
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.authority import authoritative_reference_credits
from app.value_engine.read_models import PlayerValueSnapshotRecord

MINIMUM_SCHEMA_REVISION = "20260322_0028_real_player_ingestion_layer"
PASS_VERDICT = "pass"
FAIL_VERDICT = "fail"
IDENTICAL_VALUE_CLUSTER_THRESHOLD = 3
IDENTICAL_VALUE_CLUSTER_RATIO = 0.25
MAX_FINDINGS_PER_RULE = 5
NEARBY_COMPARATOR_LIMIT = 3
AGE_DECLINE_MIN_OLDER_AGE = 27
AGE_DECLINE_AUTHORITATIVE_SUPPORT_MARGIN = 0.09


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _format_bool(value: bool) -> str:
    return "yes" if value else "no"


def _render_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    widths = [len(header) for header in headers]
    rendered_rows = [[str(value) for value in row] for row in rows]
    for row in rendered_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    header_line = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    divider_line = "-+-".join("-" * width for width in widths)
    if not rendered_rows:
        return "\n".join([header_line, divider_line, "(none)"])
    body_lines = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rendered_rows
    ]
    return "\n".join([header_line, divider_line, *body_lines])


def _age_on(reference_date: date, date_of_birth: date | None) -> int | None:
    if date_of_birth is None:
        return None
    return (
        reference_date.year
        - date_of_birth.year
        - ((reference_date.month, reference_date.day) < (date_of_birth.month, date_of_birth.day))
    )


def _summary_payload(summary: PlayerSummaryReadModel | None) -> dict[str, Any]:
    if summary is None or not isinstance(summary.summary_json, dict):
        return {}
    return summary.summary_json


def _breakdown_payload(snapshot: PlayerValueSnapshotRecord | None) -> dict[str, Any]:
    if snapshot is None or not isinstance(snapshot.breakdown_json, dict):
        return {}
    return snapshot.breakdown_json


def _global_scouting_index(summary: PlayerSummaryReadModel | None, snapshot: PlayerValueSnapshotRecord | None) -> float | None:
    value = _coerce_float(_summary_payload(summary).get("global_scouting_index"))
    if value is not None:
        return value
    return _coerce_float(_breakdown_payload(snapshot).get("global_scouting_index"))


def _round2(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _float_eq(left: float | None, right: float | None, *, tolerance: float = 0.01) -> bool:
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tolerance


def _normalized_nationality_codes(player: Player | None, profile: RealPlayerProfile) -> set[str]:
    codes: set[str] = set()
    if player is not None and player.country is not None:
        for candidate in (
            player.country.alpha2_code,
            player.country.alpha3_code,
            player.country.fifa_code,
            player.country.name,
        ):
            if candidate:
                codes.add(str(candidate).strip().upper())
    if profile.nationality:
        codes.add(profile.nationality.strip().upper())
    return codes


@dataclass(frozen=True, slots=True)
class PricingIntegrityRow:
    player_id: str
    player_name: str
    cohort: str
    current_value_credits: float | None
    pricing_snapshot_id: str | None
    summary_snapshot_id: str | None
    snapshot_match: bool
    null_valuation: bool
    fallback_marker: bool
    local_compute_artifact: bool
    market_snapshot_source: str | None
    status: str

    def render_row(self) -> list[object]:
        return [
            self.player_name,
            self.cohort,
            _format_number(self.current_value_credits),
            self.pricing_snapshot_id or "-",
            self.summary_snapshot_id or "-",
            _format_bool(self.snapshot_match),
            _format_bool(self.null_valuation),
            _format_bool(self.fallback_marker),
            _format_bool(self.local_compute_artifact),
            self.market_snapshot_source or "-",
            self.status,
        ]


@dataclass(frozen=True, slots=True)
class CohortDistributionSummary:
    cohort: str
    player_count: int
    median_value_credits: float | None
    mean_value_credits: float | None
    minimum_value_credits: float | None
    maximum_value_credits: float | None
    comparator_median_value_credits: float | None
    comparator_mean_value_credits: float | None

    def render(self) -> str:
        return (
            f"[cohort_distribution] {self.cohort}: count={self.player_count}, "
            f"median={_format_number(self.median_value_credits)}, "
            f"mean={_format_number(self.mean_value_credits)}, "
            f"min={_format_number(self.minimum_value_credits)}, "
            f"max={_format_number(self.maximum_value_credits)}, "
            f"nearby_regen_median={_format_number(self.comparator_median_value_credits)}, "
            f"nearby_regen_mean={_format_number(self.comparator_mean_value_credits)}"
        )


@dataclass(frozen=True, slots=True)
class RealPlayerBatchAuditReport:
    minimum_schema_revision: str
    current_schema_heads: tuple[str, ...]
    selected_batch_id: str | None
    as_of: datetime | None
    summary_lines: tuple[str, ...]
    checks_run: tuple[str, ...]
    pricing_integrity_rows: tuple[PricingIntegrityRow, ...]
    distribution_findings: tuple[str, ...]
    market_coherence_findings: tuple[str, ...]
    narrow_tuning_applied: tuple[str, ...] = ()
    residual_risks: tuple[str, ...] = ()
    verdict: str = FAIL_VERDICT

    def render_text(self) -> str:
        pricing_table = _render_table(
            (
                "player",
                "cohort",
                "value",
                "profile_snapshot_id",
                "summary_snapshot_id",
                "summary_matches_snapshot",
                "null_value",
                "fallback_marker",
                "local_compute_artifact",
                "market_snapshot_source",
                "status",
            ),
            [row.render_row() for row in self.pricing_integrity_rows],
        )
        sections = [
            ("1. Summary", self.summary_lines),
            ("2. Exact files changed", ("None",)),
            ("3. Checks/queries run", self.checks_run),
            ("4. Pricing integrity table", (pricing_table,)),
            ("5. Distribution findings", self.distribution_findings),
            ("6. Market coherence findings", self.market_coherence_findings),
            ("7. Any narrow tuning applied", self.narrow_tuning_applied or ("None",)),
            ("8. Residual risks", self.residual_risks or ("None",)),
            ("9. Verdict: pass/fail for first-batch pricing stability", (self.verdict,)),
        ]
        rendered_sections: list[str] = []
        for title, lines in sections:
            rendered_sections.append(title)
            if len(lines) == 1 and "\n" in lines[0]:
                rendered_sections.append(lines[0])
            else:
                rendered_sections.extend(f"- {line}" for line in lines)
            rendered_sections.append("")
        return "\n".join(rendered_sections).rstrip()


@dataclass(frozen=True, slots=True)
class _ComparablePlayer:
    player_id: str
    player_name: str
    position: str | None
    age: int | None
    current_value_credits: float
    global_scouting_index: float


@dataclass(frozen=True, slots=True)
class _AuditedBatchPlayer:
    profile: RealPlayerProfile
    player: Player | None
    summary: PlayerSummaryReadModel | None
    authoritative_snapshot: PlayerValueSnapshotRecord | None
    summary_snapshot: PlayerValueSnapshotRecord | None
    market_snapshot: PlayerMarketValueSnapshot | None
    current_value_credits: float | None
    global_scouting_index: float | None
    age: int | None
    cohort: str
    comparator_ids: tuple[str, ...] = ()
    comparator_values: tuple[float, ...] = ()


def _audited_metric(item: _AuditedBatchPlayer, key: str) -> float | None:
    snapshot = item.authoritative_snapshot or item.summary_snapshot
    if snapshot is not None and hasattr(snapshot, key):
        value = _coerce_float(getattr(snapshot, key))
        if value is not None:
            return value
    for payload in (
        _breakdown_payload(snapshot),
        _summary_payload(item.summary),
    ):
        value = _coerce_float(payload.get(key))
        if value is not None:
            return value
    return None


def _materially_exceeds(left: float | None, right: float | None, *, margin: float = AGE_DECLINE_AUTHORITATIVE_SUPPORT_MARGIN) -> bool:
    if left is None or right is None or right <= 0:
        return False
    return left > right * (1.0 + margin)


@dataclass(slots=True)
class RealPlayerBatchAuditService:
    session_factory: sessionmaker[Session]
    minimum_schema_revision: str = MINIMUM_SCHEMA_REVISION

    def run(
        self,
        *,
        ingestion_batch_id: str | None = None,
        first_batch: bool = False,
    ) -> RealPlayerBatchAuditReport:
        engine = self._engine()
        schema_ok, current_heads = self._schema_status(engine)
        checks_run = [
            f"schema_revision_check: current_heads={current_heads or ('<none>',)} minimum_required={self.minimum_schema_revision}",
        ]
        if not schema_ok:
            return RealPlayerBatchAuditReport(
                minimum_schema_revision=self.minimum_schema_revision,
                current_schema_heads=current_heads,
                selected_batch_id=None,
                as_of=None,
                summary_lines=(
                    "Audit failed closed before data inspection.",
                    f"Schema head does not reach {self.minimum_schema_revision}.",
                ),
                checks_run=tuple(checks_run),
                pricing_integrity_rows=(),
                distribution_findings=("Audit did not proceed because the database schema is below the required real-player ingestion layer.",),
                market_coherence_findings=("Audit did not proceed because the database schema is below the required real-player ingestion layer.",),
                residual_risks=("Stale schema can hide missing authoritative fields or alternate pricing paths.",),
                verdict=FAIL_VERDICT,
            )

        with self.session_factory() as session:
            batch_id = self._resolve_batch_id(
                session,
                ingestion_batch_id=ingestion_batch_id,
                first_batch=first_batch,
            )
            checks_run.append(
                "batch_selection: "
                + (
                    f"explicit real_player_profiles.ingestion_batch_id={ingestion_batch_id}"
                    if ingestion_batch_id is not None
                    else "earliest non-null real_player_profiles.ingestion_batch_id"
                )
            )
            if batch_id is None:
                return RealPlayerBatchAuditReport(
                    minimum_schema_revision=self.minimum_schema_revision,
                    current_schema_heads=current_heads,
                    selected_batch_id=None,
                    as_of=None,
                    summary_lines=(
                        "Audit failed closed before player inspection.",
                        "No persisted real-player ingestion batch was found.",
                    ),
                    checks_run=tuple(checks_run),
                    pricing_integrity_rows=(),
                    distribution_findings=("No real-player batch rows were available for distribution analysis.",),
                    market_coherence_findings=("No real-player batch rows were available for market coherence analysis.",),
                    residual_risks=("Missing batch data prevents validation of authoritative value propagation.",),
                    verdict=FAIL_VERDICT,
                )

            audited_players = self._load_audited_players(session, batch_id=batch_id)
            checks_run.extend(
                (
                    "integrity_scan: real_player_profiles + ingestion_players + player_summary_read_models + player_value_snapshots + player_market_value_snapshots",
                    "distribution_scan: cohort comparison across global stars, Nigerian core, prospects, fillers, and nearby regen comparators",
                    "market_coherence_scan: MarketPlayerQueryService list/detail/reference behaviors on mixed real + regen data",
                )
            )
            if not audited_players:
                return RealPlayerBatchAuditReport(
                    minimum_schema_revision=self.minimum_schema_revision,
                    current_schema_heads=current_heads,
                    selected_batch_id=batch_id,
                    as_of=None,
                    summary_lines=(
                        f"Audit failed closed for batch {batch_id}.",
                        "No real-player profiles were found for the selected ingestion batch.",
                    ),
                    checks_run=tuple(checks_run),
                    pricing_integrity_rows=(),
                    distribution_findings=("Selected batch has no persisted real-player profiles.",),
                    market_coherence_findings=("Selected batch has no persisted real-player profiles.",),
                    residual_risks=("Empty batch selection prevents pricing validation.",),
                    verdict=FAIL_VERDICT,
                )

            report_as_of = self._resolve_as_of(audited_players)
            regen_player_ids = self._load_regen_player_ids(session)
            regen_pool = self._load_regen_pool(
                session,
                as_of=report_as_of.date() if report_as_of is not None else date.today(),
                regen_player_ids=regen_player_ids,
            )
            audited_players = self._attach_regen_comparators(audited_players, regen_pool=regen_pool)
            pricing_rows, pricing_failures = self._build_pricing_integrity_rows(audited_players)
            distribution_findings, distribution_failures = self._build_distribution_findings(audited_players)
            market_findings, market_failures, residual_risks = self._build_market_coherence_findings(
                session,
                audited_players=audited_players,
                regen_player_ids=regen_player_ids,
                regen_pool=regen_pool,
            )

        verdict = PASS_VERDICT
        if any(row.status == FAIL_VERDICT for row in pricing_rows) or distribution_failures or market_failures:
            verdict = FAIL_VERDICT
        residual_items = list(residual_risks)
        residual_items.extend(pricing_failures)
        summary_lines = (
            f"Batch {batch_id} audited against schema heads {current_heads or ('<none>',)}.",
            f"Players audited={len(audited_players)}, pricing_failures={sum(1 for row in pricing_rows if row.status == FAIL_VERDICT)}, distribution_failures={distribution_failures}, market_failures={market_failures}.",
            f"Verdict={verdict}.",
        )
        return RealPlayerBatchAuditReport(
            minimum_schema_revision=self.minimum_schema_revision,
            current_schema_heads=current_heads,
            selected_batch_id=batch_id,
            as_of=report_as_of,
            summary_lines=summary_lines,
            checks_run=tuple(checks_run),
            pricing_integrity_rows=tuple(pricing_rows),
            distribution_findings=tuple(distribution_findings),
            market_coherence_findings=tuple(market_findings),
            residual_risks=tuple(dict.fromkeys(item for item in residual_items if item)),
            verdict=verdict,
        )

    def _engine(self) -> Engine:
        engine = self.session_factory.kw.get("bind")
        if engine is None:
            with self.session_factory() as session:
                return session.get_bind()
        return engine

    def _schema_status(self, engine: Engine) -> tuple[bool, tuple[str, ...]]:
        config = build_alembic_config(str(engine.url))
        script = ScriptDirectory.from_config(config)
        with engine.connect() as connection:
            current_heads = tuple(sorted(MigrationContext.configure(connection).get_current_heads()))
        if not current_heads:
            return False, current_heads
        return (
            all(self._head_reaches_revision(script, head, self.minimum_schema_revision) for head in current_heads),
            current_heads,
        )

    def _head_reaches_revision(self, script: ScriptDirectory, head: str, target_revision: str) -> bool:
        stack = [head]
        seen: set[str] = set()
        while stack:
            revision_id = stack.pop()
            if revision_id in seen:
                continue
            seen.add(revision_id)
            if revision_id == target_revision:
                return True
            revision = script.get_revision(revision_id)
            if revision is None:
                continue
            down_revision = revision.down_revision
            if isinstance(down_revision, tuple):
                stack.extend(item for item in down_revision if item is not None)
            elif down_revision is not None:
                stack.append(down_revision)
            dependencies = getattr(revision, "dependencies", None)
            if isinstance(dependencies, tuple):
                stack.extend(item for item in dependencies if item is not None)
            elif dependencies is not None:
                stack.append(dependencies)
        return False

    def _resolve_batch_id(
        self,
        session: Session,
        *,
        ingestion_batch_id: str | None,
        first_batch: bool,
    ) -> str | None:
        if ingestion_batch_id:
            return session.scalar(
                select(RealPlayerProfile.ingestion_batch_id).where(
                    RealPlayerProfile.ingestion_batch_id == ingestion_batch_id
                )
            )
        if not first_batch:
            raise ValueError("Either ingestion_batch_id or first_batch=True is required.")
        return session.scalar(
            select(RealPlayerProfile.ingestion_batch_id)
            .where(RealPlayerProfile.ingestion_batch_id.is_not(None))
            .group_by(RealPlayerProfile.ingestion_batch_id)
            .order_by(func.min(RealPlayerProfile.created_at).asc(), RealPlayerProfile.ingestion_batch_id.asc())
        )

    def _load_audited_players(self, session: Session, *, batch_id: str) -> list[_AuditedBatchPlayer]:
        profiles = list(
            session.scalars(
                select(RealPlayerProfile)
                .where(RealPlayerProfile.ingestion_batch_id == batch_id)
                .order_by(RealPlayerProfile.created_at.asc(), RealPlayerProfile.id.asc())
            )
        )
        if not profiles:
            return []

        player_ids = [profile.gtex_player_id for profile in profiles]
        players = {
            player.id: player
            for player in session.scalars(
                select(Player)
                .options(
                    selectinload(Player.country),
                    selectinload(Player.current_club),
                    selectinload(Player.current_competition),
                )
                .where(Player.id.in_(player_ids))
            )
        }
        summaries = {
            summary.player_id: summary
            for summary in session.scalars(
                select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(player_ids))
            )
        }
        snapshot_ids = {
            profile.pricing_snapshot_id
            for profile in profiles
            if profile.pricing_snapshot_id
        }
        snapshot_ids.update(
            summary.last_snapshot_id
            for summary in summaries.values()
            if summary.last_snapshot_id
        )
        snapshots_by_id = (
            {
                snapshot.id: snapshot
                for snapshot in session.scalars(
                    select(PlayerValueSnapshotRecord).where(PlayerValueSnapshotRecord.id.in_(snapshot_ids))
                )
            }
            if snapshot_ids
            else {}
        )
        market_snapshots_by_player: dict[str, list[PlayerMarketValueSnapshot]] = defaultdict(list)
        for snapshot in session.scalars(
            select(PlayerMarketValueSnapshot)
            .where(PlayerMarketValueSnapshot.player_id.in_(player_ids))
            .order_by(
                PlayerMarketValueSnapshot.player_id.asc(),
                PlayerMarketValueSnapshot.as_of.desc(),
                PlayerMarketValueSnapshot.created_at.desc(),
                PlayerMarketValueSnapshot.id.desc(),
            )
        ):
            market_snapshots_by_player[snapshot.player_id].append(snapshot)

        rows: list[_AuditedBatchPlayer] = []
        for profile in profiles:
            player = players.get(profile.gtex_player_id)
            summary = summaries.get(profile.gtex_player_id)
            authoritative_snapshot = snapshots_by_id.get(profile.pricing_snapshot_id) if profile.pricing_snapshot_id else None
            summary_snapshot = snapshots_by_id.get(summary.last_snapshot_id) if summary is not None and summary.last_snapshot_id else None
            summary_payload = _summary_payload(summary)
            breakdown_payload = _breakdown_payload(authoritative_snapshot or summary_snapshot)
            current_value_credits = authoritative_reference_credits(
                summary=summary,
                latest_snapshot=authoritative_snapshot or summary_snapshot,
                summary_payload=summary_payload,
                breakdown_payload=breakdown_payload,
            )
            market_snapshot = self._resolve_market_snapshot(
                market_snapshots_by_player.get(profile.gtex_player_id, []),
                authoritative_snapshot_id=profile.pricing_snapshot_id,
            )
            reference_date = (
                (authoritative_snapshot or summary_snapshot).as_of.date()
                if (authoritative_snapshot or summary_snapshot) is not None
                else date.today()
            )
            age = _age_on(reference_date, player.date_of_birth) if player is not None else None
            rows.append(
                _AuditedBatchPlayer(
                    profile=profile,
                    player=player,
                    summary=summary,
                    authoritative_snapshot=authoritative_snapshot,
                    summary_snapshot=summary_snapshot,
                    market_snapshot=market_snapshot,
                    current_value_credits=current_value_credits,
                    global_scouting_index=_global_scouting_index(summary, authoritative_snapshot or summary_snapshot),
                    age=age,
                    cohort=self._classify_cohort(player=player, profile=profile, age=age),
                )
            )
        return rows

    def _resolve_market_snapshot(
        self,
        snapshots: Sequence[PlayerMarketValueSnapshot],
        *,
        authoritative_snapshot_id: str | None,
    ) -> PlayerMarketValueSnapshot | None:
        if authoritative_snapshot_id:
            for snapshot in snapshots:
                metadata = snapshot.metadata_json if isinstance(snapshot.metadata_json, dict) else {}
                if str(metadata.get("authoritative_snapshot_id") or "") == authoritative_snapshot_id:
                    return snapshot
        return snapshots[0] if snapshots else None

    def _resolve_as_of(self, audited_players: Sequence[_AuditedBatchPlayer]) -> datetime | None:
        timestamps = [
            snapshot.as_of
            for item in audited_players
            for snapshot in (item.authoritative_snapshot, item.summary_snapshot)
            if snapshot is not None
        ]
        return max(timestamps) if timestamps else None

    def _classify_cohort(
        self,
        *,
        player: Player | None,
        profile: RealPlayerProfile,
        age: int | None,
    ) -> str:
        tier = (player.real_player_tier if player is not None else None) or ""
        normalized_tier = tier.strip().casefold()
        if normalized_tier == "elite":
            return "global stars"
        nationality_codes = _normalized_nationality_codes(player, profile)
        if nationality_codes.intersection({"NG", "NGA", "NIGERIA"}) and normalized_tier in {"featured", "core"}:
            return "Nigerian core"
        if age is not None and age <= 21:
            return "prospects"
        if age is not None and age <= 23 and normalized_tier == "watchlist":
            return "prospects"
        return "fillers"

    def _load_regen_player_ids(self, session: Session) -> set[str]:
        return set(session.scalars(select(RegenProfile.player_id)))

    def _load_regen_pool(
        self,
        session: Session,
        *,
        as_of: date,
        regen_player_ids: set[str],
    ) -> list[_ComparablePlayer]:
        if not regen_player_ids:
            return []
        players = list(
            session.scalars(
                select(Player)
                .options(selectinload(Player.country))
                .where(
                    Player.id.in_(regen_player_ids),
                    Player.is_real_player.is_(False),
                    Player.is_tradable.is_(True),
                )
                .order_by(Player.id.asc())
            )
        )
        if not players:
            return []
        summaries = {
            summary.player_id: summary
            for summary in session.scalars(
                select(PlayerSummaryReadModel).where(
                    PlayerSummaryReadModel.player_id.in_([player.id for player in players])
                )
            )
        }
        pool: list[_ComparablePlayer] = []
        for player in players:
            summary = summaries.get(player.id)
            value = authoritative_reference_credits(summary=summary, summary_payload=_summary_payload(summary))
            gsi = _global_scouting_index(summary, None)
            if value is None or gsi is None:
                continue
            pool.append(
                _ComparablePlayer(
                    player_id=player.id,
                    player_name=player.full_name,
                    position=player.normalized_position or player.position,
                    age=_age_on(as_of, player.date_of_birth),
                    current_value_credits=value,
                    global_scouting_index=gsi,
                )
            )
        return pool

    def _attach_regen_comparators(
        self,
        audited_players: Sequence[_AuditedBatchPlayer],
        *,
        regen_pool: Sequence[_ComparablePlayer],
    ) -> list[_AuditedBatchPlayer]:
        updated: list[_AuditedBatchPlayer] = []
        for item in audited_players:
            if item.player is None or item.current_value_credits is None or item.global_scouting_index is None:
                updated.append(item)
                continue
            candidates = [
                candidate
                for candidate in regen_pool
                if candidate.position == (item.player.normalized_position or item.player.position)
            ]
            if item.age is not None:
                nearby_age = [candidate for candidate in candidates if candidate.age is not None and abs(candidate.age - item.age) <= 3]
                if nearby_age:
                    candidates = nearby_age
            candidates = sorted(
                candidates,
                key=lambda candidate: (
                    abs(candidate.current_value_credits - item.current_value_credits),
                    abs(candidate.global_scouting_index - item.global_scouting_index),
                    candidate.player_id,
                ),
            )[:NEARBY_COMPARATOR_LIMIT]
            updated.append(
                _AuditedBatchPlayer(
                    profile=item.profile,
                    player=item.player,
                    summary=item.summary,
                    authoritative_snapshot=item.authoritative_snapshot,
                    summary_snapshot=item.summary_snapshot,
                    market_snapshot=item.market_snapshot,
                    current_value_credits=item.current_value_credits,
                    global_scouting_index=item.global_scouting_index,
                    age=item.age,
                    cohort=item.cohort,
                    comparator_ids=tuple(candidate.player_id for candidate in candidates),
                    comparator_values=tuple(candidate.current_value_credits for candidate in candidates),
                )
            )
        return updated

    def _build_pricing_integrity_rows(
        self,
        audited_players: Sequence[_AuditedBatchPlayer],
    ) -> tuple[list[PricingIntegrityRow], list[str]]:
        rows: list[PricingIntegrityRow] = []
        failures: list[str] = []
        for item in audited_players:
            player = item.player
            summary = item.summary
            profile = item.profile
            summary_payload = _summary_payload(summary)
            real_profile_payload = summary_payload.get("real_player_profile") if isinstance(summary_payload.get("real_player_profile"), dict) else {}
            ingestion_metadata = summary_payload.get("ingestion_metadata") if isinstance(summary_payload.get("ingestion_metadata"), dict) else {}
            market_metadata = item.market_snapshot.metadata_json if item.market_snapshot is not None and isinstance(item.market_snapshot.metadata_json, dict) else {}
            snapshot_exists = item.authoritative_snapshot is not None and item.authoritative_snapshot.player_id == profile.gtex_player_id
            summary_matches_snapshot = (
                summary is not None
                and item.authoritative_snapshot is not None
                and summary.last_snapshot_id == profile.pricing_snapshot_id
                and _float_eq(summary.current_value_credits, item.authoritative_snapshot.target_credits)
            )
            null_valuation = item.current_value_credits is None
            fallback_marker = any(
                (
                    summary_payload.get("fallback_used"),
                    real_profile_payload.get("fallback_used"),
                    ingestion_metadata.get("fallback_used"),
                    market_metadata.get("fallback_used"),
                    market_metadata.get("source") not in {None, "authoritative_value_engine"},
                )
            )
            local_compute_artifact = any(
                (
                    player is None,
                    player is not None and not bool(player.is_real_player),
                    profile.pricing_snapshot_id is None,
                    not snapshot_exists,
                    summary is None,
                    not summary_matches_snapshot,
                    str(real_profile_payload.get("pricing_snapshot_id") or "") not in {"", str(profile.pricing_snapshot_id or "")},
                    str(ingestion_metadata.get("authoritative_snapshot_id") or "") not in {"", str(profile.pricing_snapshot_id or "")},
                    market_metadata.get("authoritative_snapshot_id") not in {None, profile.pricing_snapshot_id},
                )
            )
            status = PASS_VERDICT
            if not snapshot_exists or not summary_matches_snapshot or null_valuation or fallback_marker or local_compute_artifact:
                status = FAIL_VERDICT
                failures.append(
                    f"Pricing integrity failed for {player.full_name if player is not None else profile.canonical_name}."
                )
            rows.append(
                PricingIntegrityRow(
                    player_id=profile.gtex_player_id,
                    player_name=player.full_name if player is not None else profile.canonical_name,
                    cohort=item.cohort,
                    current_value_credits=item.current_value_credits,
                    pricing_snapshot_id=profile.pricing_snapshot_id,
                    summary_snapshot_id=summary.last_snapshot_id if summary is not None else None,
                    snapshot_match=summary_matches_snapshot,
                    null_valuation=null_valuation,
                    fallback_marker=fallback_marker,
                    local_compute_artifact=local_compute_artifact,
                    market_snapshot_source=market_metadata.get("source") if isinstance(market_metadata.get("source"), str) else None,
                    status=status,
                )
            )
        return rows, failures

    def _build_distribution_findings(
        self,
        audited_players: Sequence[_AuditedBatchPlayer],
    ) -> tuple[list[str], int]:
        findings: list[str] = []
        failure_count = 0
        cohort_groups: dict[str, list[_AuditedBatchPlayer]] = defaultdict(list)
        for item in audited_players:
            cohort_groups[item.cohort].append(item)
        for cohort_name in ("global stars", "Nigerian core", "prospects", "fillers"):
            cohort_items = [item for item in cohort_groups.get(cohort_name, []) if item.current_value_credits is not None]
            values = [item.current_value_credits for item in cohort_items if item.current_value_credits is not None]
            comparator_values = [value for item in cohort_items for value in item.comparator_values]
            findings.append(
                CohortDistributionSummary(
                    cohort=cohort_name,
                    player_count=len(cohort_items),
                    median_value_credits=_round2(median(values)) if values else None,
                    mean_value_credits=_round2(mean(values)) if values else None,
                    minimum_value_credits=_round2(min(values)) if values else None,
                    maximum_value_credits=_round2(max(values)) if values else None,
                    comparator_median_value_credits=_round2(median(comparator_values)) if comparator_values else None,
                    comparator_mean_value_credits=_round2(mean(comparator_values)) if comparator_values else None,
                ).render()
            )
        value_counts = Counter(round(item.current_value_credits, 2) for item in audited_players if item.current_value_credits is not None)
        for value, count in sorted(value_counts.items()):
            if count >= IDENTICAL_VALUE_CLUSTER_THRESHOLD and count / max(len(audited_players), 1) >= IDENTICAL_VALUE_CLUSTER_RATIO:
                findings.append(f"[identical_value_cluster] {count} batch players share exactly {_format_number(value)} GTEX Coin.")
                failure_count += 1

        elite_players = [item for item in audited_players if item.cohort == "global stars" and item.current_value_credits is not None]
        lower_tier_players = [item for item in audited_players if item.cohort != "global stars" and item.current_value_credits is not None]
        inversion_count = 0
        for elite in elite_players:
            for lower in lower_tier_players:
                if inversion_count >= MAX_FINDINGS_PER_RULE:
                    break
                if lower.current_value_credits <= elite.current_value_credits:
                    continue
                if (lower.global_scouting_index or 0.0) > (elite.global_scouting_index or 0.0) + 8.0:
                    continue
                findings.append(
                    f"[elite_value_inversion] {lower.player.full_name if lower.player is not None else lower.profile.canonical_name} "
                    f"({_format_number(lower.current_value_credits)}) exceeds elite "
                    f"{elite.player.full_name if elite.player is not None else elite.profile.canonical_name} "
                    f"({_format_number(elite.current_value_credits)}) without a stronger authoritative signal basis."
                )
                inversion_count += 1
                failure_count += 1

        prospect_flags = 0
        prospects = [item for item in audited_players if item.cohort == "prospects" and item.current_value_credits is not None]
        for prospect in prospects:
            for elite in elite_players:
                if prospect_flags >= MAX_FINDINGS_PER_RULE:
                    break
                if prospect.current_value_credits <= elite.current_value_credits * 1.10:
                    continue
                if (prospect.global_scouting_index or 0.0) > (elite.global_scouting_index or 0.0) + 4.0:
                    continue
                findings.append(
                    f"[prospect_superstar_inversion] Prospect {prospect.player.full_name if prospect.player is not None else prospect.profile.canonical_name} "
                    f"({_format_number(prospect.current_value_credits)}) overtakes elite "
                    f"{elite.player.full_name if elite.player is not None else elite.profile.canonical_name} "
                    f"({_format_number(elite.current_value_credits)}) without sufficient signal separation."
                )
                prospect_flags += 1
                failure_count += 1

        age_flags = 0
        comparable_players = [
            item
            for item in audited_players
            if item.player is not None
            and item.current_value_credits is not None
            and item.global_scouting_index is not None
            and item.age is not None
        ]
        for older in comparable_players:
            for younger in comparable_players:
                if age_flags >= MAX_FINDINGS_PER_RULE:
                    break
                if older.profile.gtex_player_id == younger.profile.gtex_player_id:
                    continue
                if older.player.normalized_position != younger.player.normalized_position:
                    continue
                older_primary_position = (older.profile.primary_position or "").strip().casefold()
                younger_primary_position = (younger.profile.primary_position or "").strip().casefold()
                if older_primary_position and younger_primary_position and older_primary_position != younger_primary_position:
                    continue
                if older.age < AGE_DECLINE_MIN_OLDER_AGE:
                    continue
                if older.age < younger.age + 4:
                    continue
                if older.current_value_credits <= younger.current_value_credits * 1.10:
                    continue
                if older.global_scouting_index > younger.global_scouting_index + 2.0:
                    continue
                if _materially_exceeds(
                    _audited_metric(older, "football_truth_value_credits"),
                    _audited_metric(younger, "football_truth_value_credits"),
                ):
                    continue
                if _materially_exceeds(
                    _audited_metric(older, "market_signal_value_credits"),
                    _audited_metric(younger, "market_signal_value_credits"),
                ):
                    continue
                findings.append(
                    f"[age_decline_anomaly] Older player {older.player.full_name} (age {older.age}, {_format_number(older.current_value_credits)}) "
                    f"sits above younger comparable {younger.player.full_name} (age {younger.age}, {_format_number(younger.current_value_credits)}) without stronger authoritative trend support."
                )
                age_flags += 1
                failure_count += 1

        for cohort_name, cohort_items in cohort_groups.items():
            values = [item.current_value_credits for item in cohort_items if item.current_value_credits is not None]
            comparator_values = [value for item in cohort_items for value in item.comparator_values]
            if len(values) < 3 or len(comparator_values) < 3:
                continue
            real_std = pstdev(values)
            comparator_std = pstdev(comparator_values)
            if comparator_std <= 0:
                continue
            if real_std > comparator_std * 0.25:
                continue
            if len({round(value, 2) for value in values}) > max(2, len(values) // 2):
                continue
            findings.append(
                f"[regen_economy_flattening] {cohort_name} imported values cluster too tightly against nearby regen bands "
                f"(real_std={_format_number(real_std)}, regen_std={_format_number(comparator_std)})."
            )
            failure_count += 1
        if failure_count == 0:
            findings.append("No suspicious clustering, inversion, or flattening patterns were detected.")
        return findings, failure_count

    def _build_market_coherence_findings(
        self,
        session: Session,
        *,
        audited_players: Sequence[_AuditedBatchPlayer],
        regen_player_ids: set[str],
        regen_pool: Sequence[_ComparablePlayer],
    ) -> tuple[list[str], int, tuple[str, ...]]:
        findings: list[str] = []
        residual_risks: list[str] = []
        failure_count = 0
        service = MarketPlayerQueryService(session=session)
        repository = SqlAlchemyMarketPlayerRepository(session)
        all_records = repository.list_player_records()
        list_result = service.list_players(limit=max(len(all_records), 1), sort="current_value")
        real_player_ids = {item.profile.gtex_player_id for item in audited_players}
        returned_ids = [item.player_id for item in list_result.items]
        returned_real_ids = [player_id for player_id in returned_ids if player_id in real_player_ids]
        returned_regen_ids = [player_id for player_id in returned_ids if player_id in regen_player_ids]
        if not returned_real_ids:
            findings.append("[market_query_missing_real_players] Market discovery returned no audited real players.")
            failure_count += 1
        else:
            findings.append(f"[market_query_real_players] Market discovery returned {len(returned_real_ids)} audited real players.")
        if not returned_regen_ids:
            findings.append("[market_query_missing_regens] Market discovery returned no regen players alongside the audited batch.")
            failure_count += 1
        else:
            findings.append(f"[market_query_regens] Market discovery returned {len(returned_regen_ids)} regen players alongside the audited batch.")
        ordered_values = [item.current_value_credits for item in list_result.items if item.current_value_credits is not None]
        if ordered_values != sorted(ordered_values, reverse=True):
            findings.append("[mixed_sort_order] Mixed real + regen discovery list is not ordered by current_value_credits descending.")
            failure_count += 1
        else:
            findings.append("[mixed_sort_order] Mixed real + regen discovery list sorts correctly by authoritative current_value_credits.")

        record_by_player_id = {record.player.id: record for record in all_records}
        detail_checked = 0
        sample_ids = list(dict.fromkeys([*(item.profile.gtex_player_id for item in audited_players[:2]), *returned_regen_ids[:1]]))
        for player_id in sample_ids:
            try:
                detail = service.get_player_detail(player_id)
            except Exception as exc:
                findings.append(f"[market_detail_failure] Market detail failed for {player_id}: {exc}")
                failure_count += 1
                continue
            detail_checked += 1
            if detail.value.current_value_credits is None:
                findings.append(f"[market_detail_null_value] Market detail returned null value for {player_id}.")
                failure_count += 1
        if detail_checked:
            findings.append(f"[market_detail_payload] Market detail payloads rendered cleanly for {detail_checked} mixed-cohort players.")

        for item in audited_players:
            record = record_by_player_id.get(item.profile.gtex_player_id)
            if record is None:
                findings.append(f"[market_record_missing] No market record exists for audited player {item.profile.gtex_player_id}.")
                failure_count += 1
                continue
            reference_price = service._reference_price(record)
            expected_reference = authoritative_reference_credits(
                summary=record.summary,
                latest_snapshot=record.latest_snapshot,
                summary_payload=_summary_payload(record.summary),
                breakdown_payload=_breakdown_payload(record.latest_snapshot),
            )
            if reference_price is None:
                findings.append(f"[market_reference_missing] Real player {record.player.full_name} has no authoritative market reference price.")
                failure_count += 1
                continue
            if not _float_eq(reference_price, expected_reference):
                findings.append(
                    f"[market_reference_drift] Real player {record.player.full_name} resolves market reference {_format_number(reference_price)} instead of authoritative {_format_number(expected_reference)}."
                )
                failure_count += 1
        if not regen_pool:
            residual_risks.append("No authoritative regen comparator pool was available; cohort comparison depth is reduced.")
        if failure_count == 0:
            findings.append("No value-field null crashes, payload drift, or special-case real-player valuation branches were observed in market query surfaces.")
        return findings, failure_count, tuple(residual_risks)


__all__ = [
    "FAIL_VERDICT",
    "MINIMUM_SCHEMA_REVISION",
    "PASS_VERDICT",
    "PricingIntegrityRow",
    "RealPlayerBatchAuditReport",
    "RealPlayerBatchAuditService",
]
