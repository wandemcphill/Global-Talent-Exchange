from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.ingestion.models import (
    Club,
    Competition,
    Country,
    ImageModerationStatus,
    InjuryStatus,
    MarketSignal,
    Player,
    PlayerClubTenure,
    PlayerImageMetadata,
    PlayerSeasonStat,
    PlayerVerification,
    VerificationStatus,
)
from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService, RealPlayerNormalizedProfile
from app.ingestion.real_player_signal_adapter import RealPlayerSignalAdapter
from app.models.player_agency_state import PlayerAgencyState
from app.models.player_cards import PlayerMarketValueSnapshot, PlayerStatsSnapshot
from app.models.player_contract import PlayerContract
from app.models.real_player_import_batch import (
    RealPlayerImportBatch,
    RealPlayerImportBatchStatus,
    RealPlayerImportRow,
    RealPlayerImportRowStatus,
)
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.players.service import PlayerSummaryProjector
from app.schemas.real_player_ingestion import (
    RealPlayerBatchIssue,
    RealPlayerBatchIssueCandidate,
    RealPlayerDryRunReport,
    RealPlayerIngestionItemResult,
    RealPlayerIngestionMode,
    RealPlayerIngestionRequest,
    RealPlayerIngestionResult,
    RealPlayerPostWriteAuditResult,
    RealPlayerSeedInput,
    RealPlayerWriteReport,
)
from app.services.avatar_service import AvatarService
from app.services.squad_assignment_service import SquadAssignmentService
from app.value_engine.models import ValueSnapshot
from app.value_engine.read_models import PlayerValueSnapshotRecord
from app.value_engine.service import IngestionValueEngineBridge, IngestionValueSnapshotRepository

from .canonical_countries import seed_canonical_countries
from .mapping_resolver import ClubResolutionContext, MappingResolver, MappingResolution
from .real_player_canonical_mapping_service import (
    CanonicalReferenceInput,
    CanonicalReferenceResolution,
    RealPlayerCanonicalMappingService,
)
from .real_player_identity_matcher import (
    AmbiguousRealPlayerMatchError,
    RealPlayerIdentityMatcher,
)
from .unresolved_logger import UnresolvedMappingLogger


class RealPlayerIngestionError(ValueError):
    pass


class RealPlayerPricingError(RealPlayerIngestionError):
    pass


class RealPlayerBatchBlockedError(RealPlayerIngestionError):
    def __init__(self, report: RealPlayerDryRunReport) -> None:
        self.report = report
        super().__init__(
            "Real-player batch write aborted: "
            f"{report.ambiguous_match_count} ambiguous, "
            f"{report.missing_pricing_snapshot_count} missing authoritative pricing snapshots, "
            f"{report.hard_failure_count} hard failures."
        )


@dataclass(frozen=True, slots=True)
class StagedRealPlayer:
    source_name: str
    source_player_key: str
    canonical_name: str
    gtex_player_id: str
    import_row_id: str
    action: str
    match_action: str
    identity_confidence_score: float
    profile_id: str
    normalized: RealPlayerNormalizedProfile
    mapping_issues: tuple[RealPlayerBatchIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class PreparedRealPlayerBatch:
    report: RealPlayerDryRunReport
    staged_players: tuple[StagedRealPlayer, ...]
    preview_snapshots: dict[str, ValueSnapshot]
    import_batch_id: str | None = None


@dataclass(frozen=True, slots=True)
class StagePlayerOutcome:
    staged_player: StagedRealPlayer | None
    mapping_issues: tuple[RealPlayerBatchIssue, ...] = ()


@dataclass(slots=True)
class RealPlayerIngestionService:
    session_factory: sessionmaker[Session]
    value_engine_bridge: IngestionValueEngineBridge | None = None
    settings: Settings = field(default_factory=get_settings)
    identity_matcher: RealPlayerIdentityMatcher = field(default_factory=RealPlayerIdentityMatcher)
    normalization_service: RealPlayerNormalizationService = field(default_factory=RealPlayerNormalizationService)
    signal_adapter: RealPlayerSignalAdapter = field(default_factory=RealPlayerSignalAdapter)
    canonical_mapping_service: RealPlayerCanonicalMappingService | None = None
    strict_canonical_mapping_service: RealPlayerCanonicalMappingService | None = None
    mapping_resolver: MappingResolver | None = None
    summary_projector: PlayerSummaryProjector = field(default_factory=PlayerSummaryProjector)
    squad_assignment_service: SquadAssignmentService = field(default_factory=SquadAssignmentService)
    avatar_service: AvatarService = field(default_factory=AvatarService)

    def __post_init__(self) -> None:
        if self.value_engine_bridge is None:
            self.value_engine_bridge = IngestionValueEngineBridge(
                session_factory=self.session_factory,
                settings=self.settings,
                summary_projector=self.summary_projector,
                default_lookback_days=self.settings.value_snapshot_lookback_days,
            )
        if self.canonical_mapping_service is None:
            self.canonical_mapping_service = RealPlayerCanonicalMappingService(settings=self.settings)
        if self.strict_canonical_mapping_service is None:
            self.strict_canonical_mapping_service = RealPlayerCanonicalMappingService(
                settings=self.settings,
                auto_create_missing_entities=False,
            )
        if self.mapping_resolver is None:
            self.mapping_resolver = MappingResolver()

    def ingest(self, request: RealPlayerIngestionRequest) -> RealPlayerIngestionResult:
        write_report: RealPlayerWriteReport
        try:
            write_report = self.write_batch(request)
        except RealPlayerBatchBlockedError as exc:
            self._raise_blocked_ingestion_error(exc.report)
            raise AssertionError("unreachable")
        return RealPlayerIngestionResult(
            mode=write_report.mode,
            ingestion_batch_id=write_report.ingestion_batch_id,
            ingestion_source_version=write_report.ingestion_source_version,
            as_of=write_report.as_of,
            players_processed=write_report.players_processed,
            players_created=write_report.players_created,
            players_updated=write_report.players_updated,
            authoritative_snapshots_seeded=write_report.pricing_snapshots_resolved,
            player_ids=list(write_report.player_ids),
            results=list(write_report.results),
        )

    def validate(self, request: RealPlayerIngestionRequest) -> RealPlayerDryRunReport:
        if self.value_engine_bridge is None:
            raise RealPlayerIngestionError("Authoritative value engine bridge is not configured.")
        if not request.players:
            raise RealPlayerIngestionError("At least one real player payload is required.")
        as_of = request.as_of or datetime.now(UTC)
        ingestion_batch_id = request.ingestion_batch_id or f"real-player-{uuid4().hex[:12]}"
        with self.session_factory() as session:
            transaction = self._begin_session_transaction(session)
            try:
                prepared = self._prepare_batch(
                    session=session,
                    request=request,
                    ingestion_batch_id=ingestion_batch_id,
                    as_of=as_of,
                )
                return prepared.report
            finally:
                if transaction.is_active:
                    transaction.rollback()

    def write_batch(self, request: RealPlayerIngestionRequest) -> RealPlayerWriteReport:
        if self.value_engine_bridge is None:
            raise RealPlayerIngestionError("Authoritative value engine bridge is not configured.")
        if not request.players:
            raise RealPlayerIngestionError("At least one real player payload is required.")
        as_of = request.as_of or datetime.now(UTC)
        ingestion_batch_id = request.ingestion_batch_id or f"real-player-{uuid4().hex[:12]}"
        with self.session_factory() as session:
            transaction = self._begin_session_transaction(session)
            try:
                prepared = self._prepare_batch(
                    session=session,
                    request=request,
                    ingestion_batch_id=ingestion_batch_id,
                    as_of=as_of,
                )
                if self._is_blocked(prepared.report):
                    transaction.rollback()
                    self._persist_blocked_import_batch(
                        request=request,
                        report=prepared.report,
                        as_of=as_of,
                    )
                    raise RealPlayerBatchBlockedError(prepared.report)

                ordered_snapshots = [
                    prepared.preview_snapshots[item.gtex_player_id] for item in prepared.staged_players
                ]
                self._persist_authoritative_snapshots(session, snapshots=ordered_snapshots)
                item_results = self._finalize_batch(
                    session=session,
                    staged_players=list(prepared.staged_players),
                    request=request,
                    ingestion_batch_id=ingestion_batch_id,
                    as_of=as_of,
                )
                player_ids = [item.gtex_player_id for item in prepared.staged_players]
                self._complete_import_batch(
                    session=session,
                    import_batch_id=prepared.import_batch_id,
                    report=prepared.report,
                    item_results=item_results,
                    error_message=None,
                )
                transaction.commit()
            except Exception:
                if transaction.is_active:
                    transaction.rollback()
                raise

        try:
            audit = self._audit_batch(player_ids=player_ids, as_of=as_of)
        except Exception as _audit_exc:  # noqa: BLE001
            import logging as _logging

            _logging.getLogger(__name__).warning("_audit_batch skipped due to error: %s", _audit_exc)
            audit = RealPlayerPostWriteAuditResult(
                duplicate_canonical_identity_count=0,
                players_missing_authoritative_price_count=0,
                players_missing_market_snapshot_count=0,
                players_missing_avatar_seed_count=0,
                agency_linkage_required_count=0,
                agency_linkage_present_count=0,
                agency_linkage_missing_count=0,
                all_checks_passed=False,
            )
        return RealPlayerWriteReport(
            mode=request.mode,
            ingestion_batch_id=ingestion_batch_id,
            ingestion_source_version=request.ingestion_source_version,
            as_of=as_of,
            players_processed=len(item_results),
            players_created=sum(1 for item in item_results if item.action == "created"),
            players_updated=sum(1 for item in item_results if item.action == "updated"),
            identities_linked=len(item_results),
            duplicates_prevented=prepared.report.matched_existing_count,
            pricing_snapshots_resolved=len(item_results),
            avatars_assigned=max(len(item_results) - audit.players_missing_avatar_seed_count, 0),
            agency_profiles_created_or_attached=audit.agency_linkage_present_count,
            player_ids=player_ids,
            results=item_results,
            audit=audit,
        )

    def _prepare_batch(
        self,
        *,
        session: Session,
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
    ) -> PreparedRealPlayerBatch:
        staged_players: list[StagedRealPlayer] = []
        preview_snapshots: dict[str, ValueSnapshot] = {}
        issues: list[RealPlayerBatchIssue] = []
        unresolved_logger = UnresolvedMappingLogger()
        row_numbers = {
            (player.source_name, player.source_player_key): index
            for index, player in enumerate(request.players, start=1)
        }
        import_batch = self._upsert_import_batch(
            session=session,
            request=request,
            ingestion_batch_id=ingestion_batch_id,
            as_of=as_of,
        )
        seed_result = seed_canonical_countries(session)
        if seed_result.changed and self.mapping_resolver is not None:
            self.mapping_resolver.invalidate_country_index()
        normalized_row_count = 0
        matched_existing_count = 0
        new_identity_count = 0
        ambiguous_match_count = 0
        missing_pricing_snapshot_count = 0
        hard_failure_count = 0
        ordered_payloads = sorted(request.players, key=lambda item: (item.source_name, item.source_player_key))
        for payload in ordered_payloads:
            row_number = row_numbers[(payload.source_name, payload.source_player_key)]
            try:
                normalized = self.normalization_service.normalize(payload, as_of=as_of)
                normalized_row_count += 1
            except Exception as exc:
                hard_failure_count += 1
                issues.append(
                    self._issue(
                        payload=payload,
                        issue_type="normalization_error",
                        message=f"Normalization failed: {exc}",
                    )
                )
                self._upsert_import_row(
                    session=session,
                    import_batch=import_batch,
                    row_number=row_number,
                    payload=payload,
                    normalized=None,
                    status=RealPlayerImportRowStatus.FAILED.value,
                    match_action=None,
                    import_action="blocked",
                    confidence_score=None,
                    review_status="open",
                    review_reason="normalization_error",
                    validation_errors=[f"Normalization failed: {exc}"],
                )
                continue

            try:
                match = self.identity_matcher.match(session, payload, normalized_identity=normalized.identity)
            except AmbiguousRealPlayerMatchError as exc:
                ambiguous_match_count += 1
                issues.append(
                    self._issue(
                        payload=payload,
                        issue_type="ambiguous_match",
                        message=f"Ambiguous identity match for '{payload.canonical_name}'.",
                        candidates=[
                            RealPlayerBatchIssueCandidate(
                                player_id=candidate.player_id,
                                score=candidate.score,
                                reasons=list(candidate.reasons),
                            )
                            for candidate in exc.candidates
                        ],
                    )
                )
                self._upsert_import_row(
                    session=session,
                    import_batch=import_batch,
                    row_number=row_number,
                    payload=payload,
                    normalized=normalized,
                    status=RealPlayerImportRowStatus.SKIPPED.value,
                    match_action="ambiguous",
                    import_action="review_required",
                    confidence_score=max((candidate.score for candidate in exc.candidates), default=None),
                    review_status="open",
                    review_reason=exc.reason,
                    candidate_players=[
                        {
                            "player_id": candidate.player_id,
                            "score": candidate.score,
                            "reasons": list(candidate.reasons),
                        }
                        for candidate in exc.candidates
                    ],
                    audit_findings=[
                        {
                            "finding_type": "ambiguous_match",
                            "reason": exc.reason,
                        }
                    ],
                )
                continue
            except SQLAlchemyError:
                raise
            except Exception as exc:
                hard_failure_count += 1
                issues.append(
                    self._issue(
                        payload=payload,
                        issue_type="match_error",
                        message=f"Identity match failed: {exc}",
                    )
                )
                self._upsert_import_row(
                    session=session,
                    import_batch=import_batch,
                    row_number=row_number,
                    payload=payload,
                    normalized=normalized,
                    status=RealPlayerImportRowStatus.FAILED.value,
                    match_action=None,
                    import_action="blocked",
                    confidence_score=None,
                    review_status="open",
                    review_reason="match_error",
                    validation_errors=[f"Identity match failed: {exc}"],
                )
                continue

            if match.action in {"source_link", "matched_existing"}:
                matched_existing_count += 1
            else:
                new_identity_count += 1

            if request.mode == RealPlayerIngestionMode.REFRESH_EXISTING.value and match.action != "source_link":
                hard_failure_count += 1
                issues.append(
                    self._issue(
                        payload=payload,
                        issue_type="mode_error",
                        message=f"refresh_existing requires an existing source link for '{payload.canonical_name}'.",
                        gtex_player_id=match.player_id,
                    )
                )
                self._upsert_import_row(
                    session=session,
                    import_batch=import_batch,
                    row_number=row_number,
                    payload=payload,
                    normalized=normalized,
                    status=RealPlayerImportRowStatus.SKIPPED.value,
                    match_action=match.action,
                    import_action="blocked",
                    confidence_score=match.confidence_score,
                    review_status="open",
                    review_reason="mode_error",
                    validation_errors=[
                        f"refresh_existing requires an existing source link for '{payload.canonical_name}'.",
                    ],
                    gtex_player_id=match.player_id,
                    candidate_players=self._candidate_payloads(match.candidates),
                )
                continue

            try:
                with session.begin_nested():
                    outcome = self._stage_player(
                        session=session,
                        import_batch=import_batch,
                        row_number=row_number,
                        payload=payload,
                        normalized=normalized,
                        match=match,
                        request=request,
                        ingestion_batch_id=ingestion_batch_id,
                        as_of=as_of,
                        unresolved_logger=unresolved_logger,
                    )
                if outcome.staged_player is not None:
                    staged_players.append(outcome.staged_player)
                issues.extend(outcome.mapping_issues)
            except SQLAlchemyError:
                raise
            except Exception as exc:
                hard_failure_count += 1
                issues.append(
                    self._issue(
                        payload=payload,
                        issue_type="stage_error",
                        message=f"Stage failed: {exc}",
                        gtex_player_id=match.player_id,
                    )
                )
                self._upsert_import_row(
                    session=session,
                    import_batch=import_batch,
                    row_number=row_number,
                    payload=payload,
                    normalized=normalized,
                    status=RealPlayerImportRowStatus.FAILED.value,
                    match_action=match.action,
                    import_action="blocked",
                    confidence_score=match.confidence_score,
                    review_status="open",
                    review_reason="stage_error",
                    validation_errors=[f"Stage failed: {exc}"],
                    gtex_player_id=match.player_id,
                    candidate_players=self._candidate_payloads(match.candidates),
                )

        for staged in staged_players:
            try:
                snapshot = self._preview_authoritative_snapshot(
                    session=session,
                    player_id=staged.gtex_player_id,
                    as_of=as_of,
                    lookback_days=request.lookback_days,
                )
                preview_snapshots[staged.gtex_player_id] = snapshot
            except SQLAlchemyError:
                raise
            except Exception as exc:
                missing_pricing_snapshot_count += 1
                issues.append(
                    self._issue(
                        source_name=staged.source_name,
                        source_player_key=staged.source_player_key,
                        canonical_name=staged.canonical_name,
                        issue_type="missing_pricing_snapshot",
                        message=f"Authoritative pricing preview failed: {exc}. No fallback pricing path was used.",
                        gtex_player_id=staged.gtex_player_id,
                    )
                )

        report = RealPlayerDryRunReport(
            mode=request.mode,
            ingestion_batch_id=ingestion_batch_id,
            ingestion_source_version=request.ingestion_source_version,
            as_of=as_of,
            source_row_count=len(request.players),
            normalized_row_count=normalized_row_count,
            matched_existing_count=matched_existing_count,
            new_identity_count=new_identity_count,
            ambiguous_match_count=ambiguous_match_count,
            missing_pricing_snapshot_count=missing_pricing_snapshot_count,
            hard_failure_count=hard_failure_count,
            staged_player_ids=[item.gtex_player_id for item in staged_players],
            issues=issues,
        )
        return PreparedRealPlayerBatch(
            report=report,
            staged_players=tuple(staged_players),
            preview_snapshots=preview_snapshots,
            import_batch_id=import_batch.id,
        )

    def _stage_player(
        self,
        *,
        session: Session,
        import_batch: RealPlayerImportBatch,
        row_number: int,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        match,
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
        unresolved_logger: UnresolvedMappingLogger,
    ) -> StagePlayerOutcome:
        if self.canonical_mapping_service is None or self.strict_canonical_mapping_service is None:
            raise RealPlayerIngestionError("Canonical mapping service is not configured.")
        if self.mapping_resolver is None:
            raise RealPlayerIngestionError("Mapping resolver is not configured.")

        sample_payload = self._canonical_reference_sample_payload(payload)
        country_resolution = self._resolve_country_reference(
            session=session,
            payload=payload,
            as_of=as_of,
            sample_payload=sample_payload,
        )
        country = country_resolution.entity if isinstance(country_resolution.entity, Country) else None

        competition_resolution = self.canonical_mapping_service.resolve_competition(
            session,
            source_name=payload.source_name,
            provider_external_id=payload.current_real_world_league_key,
            name=payload.current_real_world_league,
            country=country,
            country_code=payload.nationality_code,
            country_name=payload.nationality,
            as_of=as_of,
            sample_payload=sample_payload,
            auto_create_values={
                "competition_type": "league",
                "format_type": "real_world",
                "is_major": normalized.competition_level in {"elite", "major", "continental"},
                "is_tradable": True,
                "competition_strength": normalized.competition_strength_multiplier,
                "last_synced_at": as_of,
            },
        )
        competition = competition_resolution.entity if isinstance(competition_resolution.entity, Competition) else None

        club_resolution = self._resolve_club_reference(
            session=session,
            payload=payload,
            as_of=as_of,
            sample_payload=sample_payload,
            competition=competition,
            normalized=normalized,
        )
        club = club_resolution.entity if isinstance(club_resolution.entity, Club) else None
        if competition is None and club is not None and club.current_competition_id:
            competition = session.get(Competition, club.current_competition_id)

        mapping_issues = tuple(
            issue
            for issue in (
                self._mapping_issue(payload=payload, entity_label="country", resolution=country_resolution),
                self._mapping_issue(payload=payload, entity_label="competition", resolution=competition_resolution),
                self._mapping_issue(payload=payload, entity_label="club", resolution=club_resolution),
            )
            if issue is not None
        )
        mapping_summary = {
            "country": country_resolution.metadata(),
            "competition": competition_resolution.metadata(),
            "club": club_resolution.metadata(),
        }

        country_blocked = not self._resolution_persists_canonical_data(country_resolution)
        club_blocked = not self._resolution_persists_canonical_data(club_resolution)
        if country_resolution.status == "unresolved" or club_resolution.status == "unresolved":
            unresolved_logger.record(
                raw_club_name=payload.current_real_world_club,
                raw_country_name=payload.nationality,
                competition_name=payload.current_real_world_league,
                player_name=payload.canonical_name,
            )
        if country_blocked or club_blocked:
            review_reason = (
                "unresolved_mapping"
                if country_resolution.status == "unresolved" or club_resolution.status == "unresolved"
                else "mapped_partial"
            )
            validation_errors = [issue.message for issue in mapping_issues]
            audit_findings = [
                {
                    "finding_type": issue.issue_type,
                    "message": issue.message,
                    "details": mapping_summary.get(
                        issue.issue_type.removeprefix("unresolved_").removeprefix("skipped_").removesuffix("_mapping"),
                        {},
                    ),
                }
                for issue in mapping_issues
            ]
            self._upsert_import_row(
                session=session,
                import_batch=import_batch,
                row_number=row_number,
                payload=payload,
                normalized=normalized,
                status=RealPlayerImportRowStatus.SKIPPED.value,
                match_action=match.action,
                import_action="skipped_mapping",
                confidence_score=match.confidence_score,
                review_status="needs_review",
                review_reason=review_reason,
                validation_errors=validation_errors,
                audit_findings=audit_findings,
                candidate_players=self._candidate_payloads(match.candidates),
                gtex_player_id=match.player_id,
                import_metadata={"mapping_summary": mapping_summary},
            )
            return StagePlayerOutcome(
                staged_player=None,
                mapping_issues=mapping_issues,
            )

        player, action, was_real_player = self._upsert_player(
            session,
            payload=payload,
            normalized=normalized,
            country=country,
            competition=competition,
            club=club,
            match=match,
            as_of=as_of,
        )
        if action == "updated" and not was_real_player:
            self._purge_seeded_supporting_records(session, player=player, source_name=payload.source_name)
        self._upsert_verification(
            session,
            player=player,
            source_name=payload.source_name,
            confidence_score=match.confidence_score,
            is_verified_real_player=payload.is_verified_real_player,
            as_of=as_of,
        )
        source_link = self._upsert_source_link(
            session,
            player=player,
            payload=payload,
            normalized=normalized,
            confidence_score=match.confidence_score,
        )
        profile = self._upsert_profile(
            session,
            player=player,
            source_link=source_link,
            payload=payload,
            normalized=normalized,
            ingestion_batch_id=ingestion_batch_id,
            ingestion_source_version=request.ingestion_source_version,
            mapping_summary=mapping_summary,
            as_of=as_of,
        )
        self._upsert_player_image(
            session,
            player=player,
            payload=payload,
            as_of=as_of,
        )
        self._upsert_tenure(session, player=player, payload=payload, club=club, as_of=as_of)
        self._upsert_season_stat(
            session,
            player=player,
            payload=payload,
            normalized=normalized,
            club=club,
            competition=competition,
            as_of=as_of,
        )
        self._upsert_injury_status(session, player=player, payload=payload)
        self._upsert_market_signals(session, player=player, normalized=normalized, as_of=as_of)
        import_row = self._upsert_import_row(
            session=session,
            import_batch=import_batch,
            row_number=row_number,
            payload=payload,
            normalized=normalized,
            status=RealPlayerImportRowStatus.MATCHED.value,
            match_action=match.action,
            import_action=action,
            confidence_score=match.confidence_score,
            review_status="resolved",
            review_reason=None,
            gtex_player_id=player.id,
            source_link_id=source_link.id,
            real_player_profile_id=profile.id,
            candidate_players=self._candidate_payloads(match.candidates),
            import_metadata={"mapping_summary": mapping_summary},
        )
        return StagePlayerOutcome(
            staged_player=StagedRealPlayer(
                source_name=payload.source_name,
                source_player_key=payload.source_player_key,
                canonical_name=normalized.canonical_name,
                gtex_player_id=player.id,
                import_row_id=import_row.id,
                action=action,
                match_action=match.action,
                identity_confidence_score=match.confidence_score,
                profile_id=profile.id,
                normalized=normalized,
                mapping_issues=mapping_issues,
            ),
            mapping_issues=mapping_issues,
        )

    def _finalize_batch(
        self,
        *,
        session: Session,
        staged_players: list[StagedRealPlayer],
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
    ) -> list[RealPlayerIngestionItemResult]:
        player_ids = [item.gtex_player_id for item in staged_players]
        player_records = {
            record.player_id: record
            for record in session.scalars(
                select(PlayerValueSnapshotRecord).where(
                    PlayerValueSnapshotRecord.player_id.in_(tuple(player_ids)),
                    PlayerValueSnapshotRecord.as_of == as_of,
                    PlayerValueSnapshotRecord.snapshot_type == "intraday",
                )
            )
        }
        summaries = {
            summary.player_id: summary
            for summary in session.scalars(
                select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(tuple(player_ids)))
            )
        }

        item_results: list[RealPlayerIngestionItemResult] = []
        for staged in staged_players:
            player = session.get(Player, staged.gtex_player_id)
            if player is None:
                raise RealPlayerIngestionError(f"Player '{staged.gtex_player_id}' disappeared before projection.")
            snapshot_record = player_records.get(staged.gtex_player_id)
            if snapshot_record is None:
                raise RealPlayerPricingError(
                    f"Authoritative value snapshot record was not found for player '{staged.gtex_player_id}'."
                )
            summary = summaries.get(staged.gtex_player_id)
            if summary is None:
                raise RealPlayerPricingError(
                    f"Player summary projection was not produced for player '{staged.gtex_player_id}'."
                )
            profile = session.get(RealPlayerProfile, staged.profile_id)
            if profile is None:
                raise RealPlayerIngestionError(f"Real player profile '{staged.profile_id}' was not found.")

            assignment_profile = self.squad_assignment_service.build_profile(
                player_id=player.id,
                primary_position=player.position,
                normalized_position=player.normalized_position,
                preferred_foot=player.preferred_foot,
                age=staged.normalized.age_years or 24,
                current_club_id=player.current_club_id,
            )
            avatar_seed_token, avatar_dna_seed = self._avatar_seed(
                source_name=staged.source_name,
                source_player_key=staged.source_player_key,
                canonical_name=staged.normalized.canonical_name,
            )
            self._upsert_stats_snapshot(
                session,
                player=player,
                staged=staged,
                assignment_profile=assignment_profile,
                as_of=as_of,
            )
            self._upsert_market_value_snapshot(
                session,
                player_id=player.id,
                snapshot_record=snapshot_record,
                as_of=as_of,
            )
            self._enrich_summary(
                player=player,
                profile=profile,
                summary=summary,
                staged=staged,
                assignment_profile=assignment_profile,
                avatar_seed_token=avatar_seed_token,
                avatar_dna_seed=avatar_dna_seed,
                snapshot_record=snapshot_record,
                request=request,
                ingestion_batch_id=ingestion_batch_id,
                as_of=as_of,
            )
            profile.pricing_snapshot_id = snapshot_record.id
            self._mark_import_row_imported(
                session=session,
                ingestion_batch_id=ingestion_batch_id,
                staged=staged,
                player_id=player.id,
                profile_id=profile.id,
                snapshot_id=snapshot_record.id,
                confidence_score=staged.identity_confidence_score,
                as_of=as_of,
            )

            item_results.append(
                RealPlayerIngestionItemResult(
                    source_name=staged.source_name,
                    source_player_key=staged.source_player_key,
                    gtex_player_id=player.id,
                    action=staged.action,
                    pricing_snapshot_id=snapshot_record.id,
                    authoritative_price_credits=float(snapshot_record.target_credits),
                    identity_confidence_score=staged.identity_confidence_score,
                )
            )
        session.flush()
        return item_results

    def _persist_authoritative_snapshots(self, session: Session, *, snapshots: list[ValueSnapshot]) -> None:
        repository = IngestionValueSnapshotRepository(
            session=session,
            summary_projector=self.summary_projector,
            settings=self.settings,
        )
        for snapshot in snapshots:
            repository.save_snapshot(snapshot)

    def _preview_authoritative_snapshot(
        self,
        *,
        session: Session,
        player_id: str,
        as_of: datetime,
        lookback_days: int | None,
    ) -> ValueSnapshot:
        if self.value_engine_bridge is None:
            raise RealPlayerIngestionError("Authoritative value engine bridge is not configured.")
        if not hasattr(self.value_engine_bridge, "preview_player"):
            raise RealPlayerPricingError("Authoritative value engine bridge does not support preview_player.")
        snapshot = self.value_engine_bridge.preview_player(
            session,
            player_id=player_id,
            as_of=as_of,
            lookback_days=lookback_days,
            snapshot_type="intraday",
        )
        if snapshot is None:
            raise RealPlayerPricingError("Authoritative value engine preview produced no snapshot.")
        return snapshot

    def _audit_batch(self, *, player_ids: list[str], as_of: datetime) -> RealPlayerPostWriteAuditResult:
        if not player_ids:
            return RealPlayerPostWriteAuditResult(
                duplicate_canonical_identity_count=0,
                players_missing_authoritative_price_count=0,
                players_missing_market_snapshot_count=0,
                players_missing_avatar_seed_count=0,
                agency_linkage_required_count=0,
                agency_linkage_present_count=0,
                agency_linkage_missing_count=0,
                all_checks_passed=True,
            )

        with self.session_factory() as session:
            player_id_tuple = tuple(player_ids)
            players = {
                player.id: player for player in session.scalars(select(Player).where(Player.id.in_(player_id_tuple)))
            }
            summaries = {
                summary.player_id: summary
                for summary in session.scalars(
                    select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(player_id_tuple))
                )
            }
            authoritative_snapshots = {
                record.player_id
                for record in session.scalars(
                    select(PlayerValueSnapshotRecord).where(
                        PlayerValueSnapshotRecord.player_id.in_(player_id_tuple),
                        PlayerValueSnapshotRecord.as_of == as_of,
                        PlayerValueSnapshotRecord.snapshot_type == "intraday",
                    )
                )
            }
            market_snapshots = {
                snapshot.player_id
                for snapshot in session.scalars(
                    select(PlayerMarketValueSnapshot).where(
                        PlayerMarketValueSnapshot.player_id.in_(player_id_tuple),
                        PlayerMarketValueSnapshot.as_of == as_of,
                    )
                )
            }
            agency_states = {
                state.player_id
                for state in session.scalars(
                    select(PlayerAgencyState).where(PlayerAgencyState.player_id.in_(player_id_tuple))
                )
            }
            contracted_players = {
                contract.player_id
                for contract in session.scalars(
                    select(PlayerContract).where(
                        PlayerContract.player_id.in_(player_id_tuple),
                        PlayerContract.status.in_(("active", "expiring")),
                    )
                )
            }

            duplicate_groups: dict[str, set[str]] = {}
            players_missing_avatar_seed_count = 0
            agency_required_ids: set[str] = set()

            for player_id in player_ids:
                player = players.get(player_id)
                summary = summaries.get(player_id)
                canonical_name = (
                    (player.canonical_display_name or player.full_name).strip().casefold()
                    if player is not None and (player.canonical_display_name or player.full_name)
                    else ""
                )
                if canonical_name:
                    duplicate_groups.setdefault(canonical_name, set()).add(player_id)

                if player is not None and (
                    player.current_club_profile_id is not None or player_id in contracted_players
                ):
                    agency_required_ids.add(player_id)

                summary_payload = (
                    dict(summary.summary_json) if summary is not None and isinstance(summary.summary_json, dict) else {}
                )
                avatar_seed_token = str(summary_payload.get("avatar_seed_token") or "").strip()
                avatar_dna_seed = str(summary_payload.get("avatar_dna_seed") or "").strip()
                if player is None or not avatar_seed_token or not avatar_dna_seed:
                    players_missing_avatar_seed_count += 1
                    continue
                avatar = self.avatar_service.build_from_player(player, summary_payload=summary_payload)
                if not avatar.seed_token or avatar.seed_token != avatar_seed_token:
                    players_missing_avatar_seed_count += 1

            duplicate_canonical_identity_count = sum(
                max(len(group_player_ids) - 1, 0)
                for group_player_ids in duplicate_groups.values()
                if len(group_player_ids) > 1
            )
            players_missing_authoritative_price_count = sum(
                1 for player_id in player_ids if player_id not in authoritative_snapshots
            )
            players_missing_market_snapshot_count = sum(
                1 for player_id in player_ids if player_id not in market_snapshots
            )
            agency_linkage_present_count = sum(1 for player_id in agency_required_ids if player_id in agency_states)
            agency_linkage_missing_count = max(len(agency_required_ids) - agency_linkage_present_count, 0)

            return RealPlayerPostWriteAuditResult(
                duplicate_canonical_identity_count=duplicate_canonical_identity_count,
                players_missing_authoritative_price_count=players_missing_authoritative_price_count,
                players_missing_market_snapshot_count=players_missing_market_snapshot_count,
                players_missing_avatar_seed_count=players_missing_avatar_seed_count,
                agency_linkage_required_count=len(agency_required_ids),
                agency_linkage_present_count=agency_linkage_present_count,
                agency_linkage_missing_count=agency_linkage_missing_count,
                all_checks_passed=(
                    duplicate_canonical_identity_count == 0
                    and players_missing_authoritative_price_count == 0
                    and players_missing_market_snapshot_count == 0
                    and players_missing_avatar_seed_count == 0
                    and agency_linkage_missing_count == 0
                ),
            )

    def _raise_blocked_ingestion_error(self, report: RealPlayerDryRunReport) -> None:
        if report.missing_pricing_snapshot_count:
            blocked_players = [
                issue.gtex_player_id or issue.source_player_key
                for issue in report.issues
                if issue.issue_type == "missing_pricing_snapshot"
            ]
            raise RealPlayerPricingError(
                "Authoritative value engine produced no snapshots for "
                f"{blocked_players}. No fallback pricing path was used."
            )
        if report.ambiguous_match_count:
            blocked_players = [issue.canonical_name for issue in report.issues if issue.issue_type == "ambiguous_match"]
            raise RealPlayerIngestionError(f"Ambiguous identity matches detected for {blocked_players}.")
        blocked_messages = [issue.message for issue in report.issues]
        raise RealPlayerIngestionError(
            f"Real-player ingestion preflight failed with {report.hard_failure_count} hard failures: {blocked_messages}"
        )

    @staticmethod
    def _is_blocked(report: RealPlayerDryRunReport) -> bool:
        return any(
            (
                report.ambiguous_match_count,
                report.missing_pricing_snapshot_count,
                report.hard_failure_count,
            )
        )

    @staticmethod
    def _begin_session_transaction(session: Session):
        bind = session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            in_transaction = False
            if hasattr(bind, "in_transaction"):
                in_transaction = bool(bind.in_transaction())
            if in_transaction:
                return session.begin_nested()
            session.execute(text("BEGIN"))
            transaction = session.get_transaction()
            if transaction is None:
                raise RealPlayerIngestionError("Failed to begin outer transaction for real-player ingestion.")
            return transaction
        return session.begin()

    def _issue(
        self,
        *,
        payload: RealPlayerSeedInput | None = None,
        source_name: str | None = None,
        source_player_key: str | None = None,
        canonical_name: str | None = None,
        issue_type: str,
        message: str,
        gtex_player_id: str | None = None,
        candidates: list[RealPlayerBatchIssueCandidate] | None = None,
    ) -> RealPlayerBatchIssue:
        resolved_source_name = source_name or (payload.source_name if payload is not None else "")
        resolved_source_player_key = source_player_key or (payload.source_player_key if payload is not None else "")
        resolved_canonical_name = canonical_name or (payload.canonical_name if payload is not None else "")
        return RealPlayerBatchIssue(
            source_name=resolved_source_name,
            source_player_key=resolved_source_player_key,
            canonical_name=resolved_canonical_name,
            issue_type=issue_type,
            message=message,
            gtex_player_id=gtex_player_id,
            candidates=candidates or [],
        )

    @staticmethod
    def _canonical_reference_sample_payload(payload: RealPlayerSeedInput) -> dict[str, object]:
        return {
            "canonical_name": payload.canonical_name,
            "nationality": payload.nationality,
            "nationality_code": payload.nationality_code,
            "current_real_world_club": payload.current_real_world_club,
            "current_real_world_club_key": payload.current_real_world_club_key,
            "current_real_world_league": payload.current_real_world_league,
            "current_real_world_league_key": payload.current_real_world_league_key,
        }

    @staticmethod
    def _resolution_persists_canonical_data(
        resolution: CanonicalReferenceResolution | MappingResolution,
    ) -> bool:
        return resolution.status in {"resolved", "auto_created"}

    def _mapping_issue(
        self,
        *,
        payload: RealPlayerSeedInput,
        entity_label: str,
        resolution: CanonicalReferenceResolution | MappingResolution,
    ) -> RealPlayerBatchIssue | None:
        if self._resolution_persists_canonical_data(resolution) or (
            entity_label == "competition" and resolution.status == "skipped"
        ):
            return None
        reference_label = (
            getattr(resolution, "provider_label", None)
            or getattr(resolution, "provider_external_id", None)
            or getattr(resolution, "provider_reference_key", None)
            or getattr(resolution, "raw_name", None)
            or entity_label
        )
        reason = f" reason={resolution.reason_code}." if resolution.reason_code else ""
        issue_prefix = "skipped" if resolution.status == "skipped" else "unresolved"
        status_verb = "was skipped" if resolution.status == "skipped" else "was not resolved"
        return self._issue(
            payload=payload,
            issue_type=f"{issue_prefix}_{entity_label}_mapping",
            message=(
                f"Canonical {entity_label} mapping for '{reference_label}' {status_verb}. "
                f"GTEX did not persist canonical {entity_label} data for this row.{reason}"
            ),
        )

    def _resolve_country_reference(
        self,
        *,
        session: Session,
        payload: RealPlayerSeedInput,
        as_of: datetime,
        sample_payload: dict[str, object],
    ) -> CanonicalReferenceResolution:
        if (
            self.mapping_resolver is None
            or self.strict_canonical_mapping_service is None
            or self.canonical_mapping_service is None
        ):
            raise RealPlayerIngestionError("Mapping resolver is not configured.")
        resolver_resolution = self.mapping_resolver.resolve_country(
            session,
            raw_name=payload.nationality,
            raw_code=payload.nationality_code,
        )
        reference = CanonicalReferenceInput(
            source_name=payload.source_name,
            entity_type="country",
            provider_external_id=payload.nationality_code,
            display_name=payload.nationality,
            country_code=payload.nationality_code,
            country_name=payload.nationality,
            metadata_json={
                "resolver_method": resolver_resolution.resolution_method,
                "resolver_confidence": resolver_resolution.confidence_score,
            },
        )
        if (
            resolver_resolution.status == "unresolved"
            and self.settings.real_player_mapping_auto_create_missing_entities
        ):
            # The deterministic resolver only binds to pre-seeded canonical countries.
            # Fall back to the permissive canonical service so player nationalities that
            # are not yet seeded auto-create a canonical country instead of silently
            # skipping the whole player (country_blocked). Mirrors the club fallback below.
            fallback_resolution = self.canonical_mapping_service.resolve_country(
                session,
                source_name=payload.source_name,
                provider_external_id=payload.nationality_code,
                name=payload.nationality,
                as_of=as_of,
                sample_payload=sample_payload,
            )
            if fallback_resolution.status != "unresolved":
                return fallback_resolution
        return self._persist_mapping_resolution(
            session=session,
            reference=reference,
            sample_payload=sample_payload,
            resolved_entity=resolver_resolution.entity,
            resolution=resolver_resolution,
            as_of=as_of,
        )

    def _resolve_competition(
        self,
        session: Session,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        *,
        as_of: datetime,
    ) -> Competition | None:
        if self.canonical_mapping_service is None or not payload.current_real_world_league:
            return None
        resolution = self.canonical_mapping_service.resolve_competition(
            session,
            source_name=payload.source_name,
            provider_external_id=payload.current_real_world_league_key,
            name=payload.current_real_world_league,
            country=None,
            country_code=None,
            country_name=None,
            as_of=as_of,
            auto_create_values={
                "competition_type": "league",
                "format_type": "real_world",
                "is_major": normalized.competition_level in {"elite", "major", "continental"},
                "is_tradable": True,
                "competition_strength": normalized.competition_strength_multiplier,
                "last_synced_at": as_of,
            },
        )
        return resolution.entity if isinstance(resolution.entity, Competition) else None

    def _resolve_club(
        self,
        session: Session,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        *,
        country: Country | None,
        competition: Competition | None,
        as_of: datetime,
    ) -> Club | None:
        if self.canonical_mapping_service is None or not payload.current_real_world_club:
            return None
        resolution = self.canonical_mapping_service.resolve_club(
            session,
            source_name=payload.source_name,
            provider_external_id=payload.current_real_world_club_key,
            name=payload.current_real_world_club,
            country=competition.country if competition is not None else country,
            country_code=None,
            country_name=None,
            competition=competition,
            competition_external_id=payload.current_real_world_league_key,
            competition_name=payload.current_real_world_league,
            as_of=as_of,
            auto_create_values={
                "short_name": (payload.current_real_world_club or "")[:80] or None,
                "popularity_score": normalized.club_strength_score,
                "is_tradable": True,
                "last_synced_at": as_of,
            },
        )
        return resolution.entity if isinstance(resolution.entity, Club) else None

    def _resolve_club_reference(
        self,
        *,
        session: Session,
        payload: RealPlayerSeedInput,
        as_of: datetime,
        sample_payload: dict[str, object],
        competition: Competition | None,
        normalized: RealPlayerNormalizedProfile,
    ) -> CanonicalReferenceResolution:
        if (
            self.mapping_resolver is None
            or self.strict_canonical_mapping_service is None
            or self.canonical_mapping_service is None
        ):
            raise RealPlayerIngestionError("Mapping resolver is not configured.")
        resolver_resolution = self.mapping_resolver.resolve_club(
            session,
            raw_name=payload.current_real_world_club,
            context=ClubResolutionContext(
                competition_name=payload.current_real_world_league,
                competition_id=payload.current_real_world_league_key,
                country_name=payload.nationality,
                country_id=competition.country_id if competition is not None else None,
            ),
        )
        reference = CanonicalReferenceInput(
            source_name=payload.source_name,
            entity_type="club",
            provider_external_id=payload.current_real_world_club_key,
            display_name=payload.current_real_world_club,
            country_code=payload.nationality_code,
            country_name=payload.nationality,
            competition_external_id=payload.current_real_world_league_key,
            competition_display_name=payload.current_real_world_league,
            metadata_json={
                "resolver_method": resolver_resolution.resolution_method,
                "resolver_confidence": resolver_resolution.confidence_score,
            },
        )
        if (
            resolver_resolution.status == "skipped"
            and resolver_resolution.reason_code == "missing_reference"
            and payload.current_real_world_club_key
        ):
            provider_match = session.scalar(
                select(Club).where(
                    Club.source_provider == payload.source_name,
                    Club.provider_external_id == payload.current_real_world_club_key,
                )
            )
            if provider_match is not None:
                return self.strict_canonical_mapping_service._persist_mapping(
                    session,
                    reference,
                    entity=provider_match,
                    mapping_status="resolved",
                    resolution_method="provider_exact_fallback",
                    confidence_score=1.0,
                    as_of=as_of,
                )
        if (
            resolver_resolution.status == "unresolved"
            and self.settings.real_player_mapping_auto_create_missing_entities
        ):
            fallback_resolution = self.canonical_mapping_service.resolve_club(
                session,
                source_name=payload.source_name,
                provider_external_id=payload.current_real_world_club_key,
                name=payload.current_real_world_club,
                country=competition.country if competition is not None else None,
                country_code=None,
                country_name=None,
                competition=competition,
                competition_external_id=payload.current_real_world_league_key,
                competition_name=payload.current_real_world_league,
                as_of=as_of,
                sample_payload=sample_payload,
                auto_create_values={
                    "short_name": (payload.current_real_world_club or "")[:80] or None,
                    "popularity_score": normalized.club_strength_score,
                    "is_tradable": True,
                    "last_synced_at": as_of,
                },
            )
            if fallback_resolution.status != "unresolved":
                return fallback_resolution
        return self._persist_mapping_resolution(
            session=session,
            reference=reference,
            sample_payload=sample_payload,
            resolved_entity=resolver_resolution.entity,
            resolution=resolver_resolution,
            as_of=as_of,
        )

    def _persist_mapping_resolution(
        self,
        *,
        session: Session,
        reference: CanonicalReferenceInput,
        sample_payload: dict[str, object],
        resolved_entity,
        resolution: MappingResolution,
        as_of: datetime,
    ) -> CanonicalReferenceResolution:
        if self.strict_canonical_mapping_service is None:
            raise RealPlayerIngestionError("Strict canonical mapping service is not configured.")
        if resolution.status == "resolved":
            return self.strict_canonical_mapping_service._persist_mapping(
                session,
                reference,
                entity=resolved_entity,
                mapping_status="resolved",
                resolution_method=f"resolver:{resolution.resolution_method}",
                confidence_score=resolution.confidence_score,
                as_of=as_of,
            )
        if resolution.status == "unresolved":
            return self.strict_canonical_mapping_service._record_unresolved(
                session,
                reference,
                reason_code=resolution.reason_code or f"{reference.entity_type}_not_found",
                as_of=as_of,
                sample_payload=sample_payload,
                notes="Deterministic mapping resolver could not bind the reference to an existing canonical entity.",
                metadata_json={
                    "resolver_method": resolution.resolution_method,
                    "resolver_confidence": resolution.confidence_score,
                    "resolver_status": resolution.status,
                },
            )
        return self.strict_canonical_mapping_service._skipped_resolution(
            reference,
            reason_code=resolution.reason_code or "skipped",
        )

    def _upsert_player(
        self,
        session: Session,
        *,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        country: Country | None,
        competition: Competition | None,
        club: Club | None,
        match,
        as_of: datetime,
    ) -> tuple[Player, str, bool]:
        player: Player | None = session.get(Player, match.player_id) if match.player_id is not None else None
        if player is None:
            # Identity matcher missed an already-ingested row; fall back to the unique
            # provider key so re-runs UPDATE instead of re-INSERTing (which violates
            # uq_ingestion_players_provider_external_id and crashes the whole run).
            player = session.scalars(
                select(Player).where(
                    Player.source_provider == payload.source_name,
                    Player.provider_external_id == payload.source_player_key,
                )
            ).one_or_none()
        was_real_player = bool(player.is_real_player) if player is not None else False
        if player is None:
            player = Player(
                source_provider=payload.source_name,
                provider_external_id=payload.source_player_key,
            )
            session.add(player)
            action = "created"
        else:
            action = "updated"

        first_name, last_name = self._split_name(normalized.canonical_name)
        player.full_name = normalized.canonical_name
        player.first_name = first_name
        player.last_name = last_name
        player.short_name = self._short_name(normalized.display_name)
        player.country_id = country.id if country is not None else None
        player.current_club_id = club.id if club is not None else None
        player.current_competition_id = competition.id if competition is not None else None
        player.position = normalized.primary_position
        player.normalized_position = normalized.normalized_position
        player.secondary_positions_json = list(normalized.secondary_positions)
        player.date_of_birth = normalized.date_of_birth
        player.height_cm = normalized.identity.height_cm
        player.weight_kg = payload.weight_kg
        player.preferred_foot = normalized.dominant_foot
        player.potential = payload.potential
        # Stash pricing inputs so the appreciation scheduler can recompute the
        # banded price over time (GSI + potential + team factor).
        if payload.overall_rating is not None or payload.club_rating is not None:
            dna = dict(player.dna_profile) if isinstance(player.dna_profile, dict) else {}
            if payload.overall_rating is not None:
                dna["sofifa_overall"] = payload.overall_rating
            if payload.potential is not None:
                dna["sofifa_potential"] = payload.potential
            if payload.club_rating is not None:
                dna["sofifa_club_rating"] = payload.club_rating
            player.dna_profile = dna
        player.market_value_eur = normalized.reference_market_value_eur
        player.profile_completeness_score = normalized.profile_completeness_score
        player.is_tradable = True
        player.is_real_player = True
        player.real_player_tier = normalized.real_player_tier
        player.canonical_display_name = normalized.display_name
        player.identity_confidence_score = match.confidence_score
        player.source_last_refreshed_at = payload.source_last_refreshed_at or as_of
        player.real_world_club_name = normalized.current_real_world_club
        player.real_world_league_name = normalized.current_real_world_league
        player.current_market_reference_value = payload.current_market_reference_value
        player.market_reference_currency = payload.market_reference_currency
        player.normalization_profile_version = normalized.normalization_profile_version
        player.last_synced_at = as_of
        session.flush()
        return player, action, was_real_player

    def _upsert_verification(
        self,
        session: Session,
        *,
        player: Player,
        source_name: str,
        confidence_score: float,
        is_verified_real_player: bool,
        as_of: datetime,
    ) -> None:
        verification = session.scalar(select(PlayerVerification).where(PlayerVerification.player_id == player.id))
        if verification is None:
            verification = PlayerVerification(player_id=player.id)
            session.add(verification)
        verification.status = (
            VerificationStatus.VERIFIED.value if is_verified_real_player else VerificationStatus.PENDING.value
        )
        verification.verification_source = source_name
        verification.verified_at = as_of if is_verified_real_player else None
        verification.expires_at = None
        verification.confidence_score = confidence_score
        verification.rights_confirmed = is_verified_real_player
        verification.reviewer_notes = f"Real-player ingestion via {source_name}. Avatar-safe stylized profile only."

    def _upsert_source_link(
        self,
        session: Session,
        *,
        player: Player,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        confidence_score: float,
    ) -> RealPlayerSourceLink:
        source_link = session.scalar(
            select(RealPlayerSourceLink).where(
                RealPlayerSourceLink.source_name == payload.source_name,
                RealPlayerSourceLink.source_player_key == payload.source_player_key,
            )
        )
        if source_link is None:
            source_link = RealPlayerSourceLink(
                gtex_player_id=player.id,
                source_name=payload.source_name,
                source_player_key=payload.source_player_key,
                canonical_name=normalized.canonical_name,
            )
            session.add(source_link)
        source_link.gtex_player_id = player.id
        source_link.canonical_name = normalized.canonical_name
        source_link.known_aliases_json = list(normalized.known_aliases)
        source_link.nationality = normalized.nationality
        source_link.date_of_birth = normalized.date_of_birth
        source_link.birth_year = normalized.birth_year
        source_link.primary_position = normalized.primary_position
        source_link.secondary_positions_json = list(normalized.secondary_positions)
        source_link.current_real_world_club = normalized.current_real_world_club
        source_link.identity_confidence_score = confidence_score
        source_link.is_verified_real_player = payload.is_verified_real_player
        source_link.verification_state = "verified" if payload.is_verified_real_player else "pending"
        session.flush()
        return source_link

    def _upsert_profile(
        self,
        session: Session,
        *,
        player: Player,
        source_link: RealPlayerSourceLink,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        ingestion_batch_id: str,
        ingestion_source_version: str | None,
        mapping_summary: dict[str, dict[str, object]],
        as_of: datetime,
    ) -> RealPlayerProfile:
        profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.source_link_id == source_link.id))
        if profile is None:
            profile = RealPlayerProfile(
                gtex_player_id=player.id,
                source_link_id=source_link.id,
                source_name=payload.source_name,
                source_player_key=payload.source_player_key,
                canonical_name=normalized.canonical_name,
            )
            session.add(profile)
        profile.gtex_player_id = player.id
        profile.source_name = payload.source_name
        profile.source_player_key = payload.source_player_key
        profile.canonical_name = normalized.canonical_name
        profile.known_aliases_json = list(normalized.known_aliases)
        profile.nationality = normalized.nationality
        profile.birth_year = normalized.birth_year
        profile.date_of_birth = normalized.date_of_birth
        profile.dominant_foot = normalized.dominant_foot
        profile.primary_position = normalized.primary_position
        profile.secondary_positions_json = list(normalized.secondary_positions)
        profile.height_cm = normalized.identity.height_cm
        profile.weight_kg = payload.weight_kg
        profile.current_club_name = normalized.current_real_world_club
        profile.current_league_name = normalized.current_real_world_league
        profile.competition_level = normalized.competition_level
        profile.appearances = normalized.appearances
        profile.minutes_played = normalized.minutes_played
        profile.goals = normalized.goals
        profile.assists = normalized.assists
        profile.clean_sheets = normalized.clean_sheets
        profile.injury_status = payload.injury_status
        profile.current_market_reference_value = payload.current_market_reference_value
        profile.market_reference_currency = payload.market_reference_currency
        profile.source_last_refreshed_at = payload.source_last_refreshed_at or as_of
        profile.normalization_profile_version = normalized.normalization_profile_version
        profile.normalized_signals_json = normalized.normalized_signals()
        profile.ingestion_batch_id = ingestion_batch_id
        profile.ingestion_source_version = ingestion_source_version
        photo_url = self._normalized_photo_url(payload.photo_url)
        national_team = self._national_team_payload(payload)
        profile.metadata_json = {
            "avatar_safe": True,
            "no_real_photos": photo_url is None,
            "has_real_photo": photo_url is not None,
            "photo_url": photo_url,
            "real_player_tier": normalized.real_player_tier,
            "source_name": payload.source_name,
            "source_player_key": payload.source_player_key,
            "display_name": normalized.display_name,
            "identity_keys": {
                "exact_identity_key": normalized.identity.exact_identity_key,
                "name_birthyear_club_key": normalized.identity.name_birthyear_club_key,
                "name_birthyear_nationality_key": normalized.identity.name_birthyear_nationality_key,
                "club_reference_key": normalized.identity.club_reference_key,
                "league_reference_key": normalized.identity.league_reference_key,
            },
            "canonical_mapping": mapping_summary,
        }
        if national_team is not None:
            profile.metadata_json["national_team"] = national_team
        if photo_url is not None:
            profile.metadata_json["image"] = {
                "source_url": photo_url,
                "source_provider": payload.source_name,
                "provider_external_id": payload.source_player_key,
                "is_primary": True,
                "moderation_status": self._trusted_photo_moderation_status(payload),
                "rights_cleared": self._photo_rights_cleared(payload),
            }
        profile.notes = "Normalized real-player profile. External reference value is an input signal only."
        session.flush()
        return profile

    def _upsert_player_image(
        self,
        session: Session,
        *,
        player: Player,
        payload: RealPlayerSeedInput,
        as_of: datetime,
    ) -> None:
        photo_url = self._normalized_photo_url(payload.photo_url)
        if photo_url is None:
            return

        provider_image = session.scalar(
            select(PlayerImageMetadata).where(
                PlayerImageMetadata.source_provider == payload.source_name,
                PlayerImageMetadata.provider_external_id == payload.source_player_key,
            )
        )
        portrait_image = session.scalar(
            select(PlayerImageMetadata).where(
                PlayerImageMetadata.player_id == player.id,
                PlayerImageMetadata.image_role == "portrait",
            )
        )
        image = provider_image or portrait_image
        if image is None:
            image = PlayerImageMetadata(
                source_provider=payload.source_name,
                provider_external_id=payload.source_player_key,
                player_id=player.id,
                image_role="portrait",
            )
            session.add(image)

        image.source_provider = payload.source_name
        image.provider_external_id = payload.source_player_key
        image.player_id = player.id
        image.image_role = "portrait"
        image.source_url = photo_url
        image.storage_key = None
        image.width = None
        image.height = None
        image.mime_type = None
        image.file_size_bytes = None
        image.checksum_sha256 = None
        image.moderation_status = self._trusted_photo_moderation_status(payload)
        image.rights_cleared = self._photo_rights_cleared(payload)
        image.is_primary = True
        image.last_processed_at = as_of

    def _upsert_tenure(
        self,
        session: Session,
        *,
        player: Player,
        payload: RealPlayerSeedInput,
        club: Club | None,
        as_of: datetime,
    ) -> None:
        provider_external_id = f"{payload.source_player_key}:current_tenure"
        tenure = session.scalar(
            select(PlayerClubTenure).where(
                PlayerClubTenure.source_provider == payload.source_name,
                PlayerClubTenure.provider_external_id == provider_external_id,
            )
        )
        if club is None:
            if tenure is not None:
                session.delete(tenure)
            return
        if tenure is None:
            tenure = PlayerClubTenure(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                player_id=player.id,
                club_id=club.id,
            )
            session.add(tenure)
        tenure.player_id = player.id
        tenure.club_id = club.id
        tenure.season_id = None
        tenure.start_date = None
        tenure.end_date = None
        tenure.squad_number = None
        tenure.is_current = True
        tenure.updated_at = as_of

    def _upsert_season_stat(
        self,
        session: Session,
        *,
        player: Player,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile,
        club: Club | None,
        competition: Competition | None,
        as_of: datetime,
    ) -> None:
        provider_external_id = f"{payload.source_player_key}:current_profile"
        stat = session.scalar(
            select(PlayerSeasonStat).where(
                PlayerSeasonStat.source_provider == payload.source_name,
                PlayerSeasonStat.provider_external_id == provider_external_id,
            )
        )
        if stat is None:
            stat = PlayerSeasonStat(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                player_id=player.id,
            )
            session.add(stat)
        stat.player_id = player.id
        stat.club_id = club.id if club is not None else None
        stat.competition_id = competition.id if competition is not None else None
        stat.season_id = None
        stat.appearances = normalized.appearances
        stat.starts = max(min(normalized.appearances, normalized.appearances - 2), 0)
        stat.minutes = normalized.minutes_played
        stat.goals = normalized.goals
        stat.assists = normalized.assists
        stat.clean_sheets = normalized.clean_sheets
        stat.saves = 0 if normalized.primary_position == "Goalkeeper" else None
        stat.average_rating = round(6.0 + (normalized.form_signal / 35.0), 2)
        stat.updated_at = as_of

    def _upsert_injury_status(self, session: Session, *, player: Player, payload: RealPlayerSeedInput) -> None:
        provider_external_id = f"{payload.source_player_key}:injury"
        injury = session.scalar(
            select(InjuryStatus).where(
                InjuryStatus.source_provider == payload.source_name,
                InjuryStatus.provider_external_id == provider_external_id,
            )
        )
        normalized_status = (payload.injury_status or "").strip().lower()
        if normalized_status in {"", "fit", "available", "none"}:
            if injury is not None:
                session.delete(injury)
            return
        if injury is None:
            injury = InjuryStatus(
                source_provider=payload.source_name,
                provider_external_id=provider_external_id,
                player_id=player.id,
            )
            session.add(injury)
        injury.player_id = player.id
        injury.club_id = player.current_club_id
        injury.status = payload.injury_status or "injured"
        injury.detail = payload.injury_status
        injury.expected_return_at = None

    def _upsert_market_signals(
        self,
        session: Session,
        *,
        player: Player,
        normalized: RealPlayerNormalizedProfile,
        as_of: datetime,
    ) -> None:
        bundle = self.signal_adapter.build_signal_bundle(normalized)
        for signal_type, score in bundle.market_signals.items():
            provider_external_id = f"{normalized.source_player_key}:signal:{signal_type}"
            signal = session.scalar(
                select(MarketSignal).where(
                    MarketSignal.source_provider == normalized.source_name,
                    MarketSignal.provider_external_id == provider_external_id,
                )
            )
            if signal is None:
                signal = MarketSignal(
                    source_provider=normalized.source_name,
                    provider_external_id=provider_external_id,
                    player_id=player.id,
                    signal_type=signal_type,
                    score=score,
                    as_of=as_of,
                )
                session.add(signal)
            signal.player_id = player.id
            signal.signal_type = signal_type
            signal.score = score
            signal.as_of = as_of
            signal.notes = json.dumps({**bundle.notes, "signal_type": signal_type}, sort_keys=True)

    def _purge_seeded_supporting_records(self, session: Session, *, player: Player, source_name: str) -> None:
        session.execute(
            delete(MarketSignal).where(
                MarketSignal.player_id == player.id,
                MarketSignal.source_provider != source_name,
                MarketSignal.notes.like('%"seeded": true%'),
            )
        )
        session.execute(
            delete(PlayerSeasonStat).where(
                PlayerSeasonStat.player_id == player.id,
                PlayerSeasonStat.source_provider != source_name,
                PlayerSeasonStat.provider_external_id.like("%:season%"),
            )
        )
        session.execute(
            delete(PlayerStatsSnapshot).where(
                PlayerStatsSnapshot.player_id == player.id,
                PlayerStatsSnapshot.source_type == "seed_snapshot",
            )
        )

    def _upsert_stats_snapshot(
        self,
        session: Session,
        *,
        player: Player,
        staged: StagedRealPlayer,
        assignment_profile,
        as_of: datetime,
    ) -> None:
        session.execute(
            delete(PlayerStatsSnapshot).where(
                PlayerStatsSnapshot.player_id == player.id,
                PlayerStatsSnapshot.as_of == as_of,
                PlayerStatsSnapshot.source_type == "real_player_ingestion",
            )
        )
        session.add(
            PlayerStatsSnapshot(
                player_id=player.id,
                as_of=as_of,
                competition_id=player.current_competition_id,
                season_id=None,
                source_type="real_player_ingestion",
                stats_json={
                    "appearances": staged.normalized.appearances,
                    "starts": max(min(staged.normalized.appearances, staged.normalized.appearances - 2), 0),
                    "minutes": staged.normalized.minutes_played,
                    "goals": staged.normalized.goals,
                    "assists": staged.normalized.assists,
                    "clean_sheets": staged.normalized.clean_sheets,
                    "average_rating": round(6.0 + (staged.normalized.form_signal / 35.0), 2),
                    "primary_position": staged.normalized.primary_position,
                    "secondary_positions": list(staged.normalized.secondary_positions),
                    "formation_slots": list(assignment_profile.formation_slots),
                    "role_archetype": assignment_profile.role_archetype,
                    "source_type": "real_player_ingestion",
                },
            )
        )

    def _upsert_market_value_snapshot(
        self,
        session: Session,
        *,
        player_id: str,
        snapshot_record: PlayerValueSnapshotRecord,
        as_of: datetime,
    ) -> None:
        session.execute(
            delete(PlayerMarketValueSnapshot).where(
                PlayerMarketValueSnapshot.player_id == player_id,
                PlayerMarketValueSnapshot.as_of == as_of,
            )
        )
        session.add(
            PlayerMarketValueSnapshot(
                player_id=player_id,
                as_of=as_of,
                last_trade_price_credits=None,
                avg_trade_price_credits=snapshot_record.target_credits,
                volume_24h=0,
                listing_floor_price_credits=snapshot_record.target_credits,
                listing_count=0,
                high_24h_price_credits=snapshot_record.target_credits,
                low_24h_price_credits=snapshot_record.target_credits,
                metadata_json={
                    "source": "authoritative_value_engine",
                    "authoritative_snapshot_id": snapshot_record.id,
                    "snapshot_type": snapshot_record.snapshot_type,
                    "real_player_ingestion": True,
                },
            )
        )

    def _enrich_summary(
        self,
        *,
        player: Player,
        profile: RealPlayerProfile,
        summary: PlayerSummaryReadModel,
        staged: StagedRealPlayer,
        assignment_profile,
        avatar_seed_token: str,
        avatar_dna_seed: str,
        snapshot_record: PlayerValueSnapshotRecord,
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
    ) -> None:
        summary.current_club_name = summary.current_club_name or player.real_world_club_name
        summary.current_competition_name = summary.current_competition_name or player.real_world_league_name
        summary_payload = dict(summary.summary_json) if isinstance(summary.summary_json, dict) else {}
        photo_url = self._profile_photo_url(profile)
        national_team = self._profile_national_team(profile)
        summary_payload.update(
            {
                "source_type": "real_player",
                "ingestion_mode": request.mode,
                "primary_position": staged.normalized.primary_position,
                "secondary_positions": list(staged.normalized.secondary_positions),
                "dominant_foot": player.preferred_foot,
                "role_archetype": assignment_profile.role_archetype,
                "formation_slots": list(assignment_profile.formation_slots),
                "formation_ready": assignment_profile.formation_ready,
                "squad_eligibility": assignment_profile.squad_eligibility,
                "avatar_seed_token": avatar_seed_token,
                "avatar_dna_seed": avatar_dna_seed,
                "club_assignment": {
                    "status": "free_agent" if player.current_club_id is None else "club_assigned",
                    "current_club_id": player.current_club_id,
                    "current_club_name": summary.current_club_name,
                    "current_competition_id": player.current_competition_id,
                    "current_competition_name": summary.current_competition_name,
                },
                "nationality": {
                    "name": getattr(player.country, "name", None) or staged.normalized.nationality,
                    "alpha2_code": getattr(player.country, "alpha2_code", None) or staged.normalized.nationality_code,
                    "alpha3_code": getattr(player.country, "alpha3_code", None),
                    "fifa_code": getattr(player.country, "fifa_code", None),
                },
                "national_team": national_team,
                "market_visibility": {
                    "eligible": bool(player.is_tradable and snapshot_record.target_credits > 0),
                    "status": "visible" if player.is_tradable and snapshot_record.target_credits > 0 else "hidden",
                    "surface_flags": [
                        "player_summary",
                        "market_listing",
                        "player_card",
                        "club_squad",
                        "lineup_builder",
                        "match_viewer",
                    ],
                },
                "real_player_profile": {
                    "is_real_player": True,
                    "is_verified_real_player": True,
                    "real_player_tier": player.real_player_tier,
                    "canonical_display_name": player.canonical_display_name or player.full_name,
                    "identity_confidence_score": player.identity_confidence_score,
                    "source_name": staged.source_name,
                    "source_player_key": staged.source_player_key,
                    "source_last_refreshed_at": (
                        player.source_last_refreshed_at.isoformat()
                        if player.source_last_refreshed_at is not None
                        else None
                    ),
                    "real_world_club_name": player.real_world_club_name,
                    "real_world_league_name": player.real_world_league_name,
                    "current_market_reference_value": player.current_market_reference_value,
                    "market_reference_currency": player.market_reference_currency,
                    "normalization_profile_version": player.normalization_profile_version,
                    "normalized_signals": staged.normalized.normalized_signals(),
                    "pricing_snapshot_id": snapshot_record.id,
                    "photo_url": photo_url,
                    "no_real_photos": photo_url is None,
                    "national_team": national_team,
                    "valuation_lineage_id": (
                        (snapshot_record.breakdown_json.get("real_player_valuation") or {}).get("lineage_id")
                        if isinstance(snapshot_record.breakdown_json, dict)
                        else None
                    ),
                },
                "ingestion_metadata": {
                    "ingestion_batch_id": ingestion_batch_id,
                    "ingestion_source_version": request.ingestion_source_version,
                    "authoritative_snapshot_id": snapshot_record.id,
                    "as_of": as_of.isoformat(),
                },
            }
        )
        summary.summary_json = summary_payload

    def _upsert_import_batch(
        self,
        *,
        session: Session,
        request: RealPlayerIngestionRequest,
        ingestion_batch_id: str,
        as_of: datetime,
    ) -> RealPlayerImportBatch:
        provider_names = tuple(sorted({player.source_name for player in request.players}))
        provider_name = provider_names[0] if len(provider_names) == 1 else "multi-source"
        batch = session.scalar(
            select(RealPlayerImportBatch).where(RealPlayerImportBatch.batch_key == ingestion_batch_id)
        )
        if batch is None and request.ingestion_source_version:
            batch = session.scalar(
                select(RealPlayerImportBatch).where(
                    RealPlayerImportBatch.provider_name == provider_name,
                    RealPlayerImportBatch.provider_job_key == request.ingestion_source_version,
                )
            )
        if batch is None:
            batch = RealPlayerImportBatch(
                batch_key=ingestion_batch_id,
                provider_name=provider_name,
                provider_job_key=request.ingestion_source_version,
                source_type="real_player_ingestion",
                mode=request.mode,
                requested_at=as_of,
            )
            session.add(batch)
        else:
            batch.batch_key = batch.batch_key or ingestion_batch_id
        batch.provider_name = provider_name
        batch.provider_job_key = request.ingestion_source_version
        batch.source_type = "real_player_ingestion"
        batch.mode = request.mode
        batch.status = RealPlayerImportBatchStatus.RUNNING.value
        batch.started_at = as_of
        batch.submitted_row_count = len(request.players)
        batch.error_message = None
        session.flush()
        return batch

    def _upsert_import_row(
        self,
        *,
        session: Session,
        import_batch: RealPlayerImportBatch,
        row_number: int,
        payload: RealPlayerSeedInput,
        normalized: RealPlayerNormalizedProfile | None,
        status: str,
        match_action: str | None,
        import_action: str | None,
        confidence_score: float | None,
        review_status: str,
        review_reason: str | None,
        validation_errors: list[str] | None = None,
        audit_findings: list[dict[str, object]] | None = None,
        candidate_players: list[dict[str, object]] | None = None,
        gtex_player_id: str | None = None,
        source_link_id: str | None = None,
        real_player_profile_id: str | None = None,
        authoritative_snapshot_id: str | None = None,
        processed_at: datetime | None = None,
        import_metadata: dict[str, object] | None = None,
    ) -> RealPlayerImportRow:
        row = session.scalar(
            select(RealPlayerImportRow).where(
                RealPlayerImportRow.batch_id == import_batch.id,
                RealPlayerImportRow.source_name == payload.source_name,
                RealPlayerImportRow.source_player_key == payload.source_player_key,
            )
        )
        if row is None:
            row = RealPlayerImportRow(
                batch_id=import_batch.id,
                row_number=row_number,
                source_name=payload.source_name,
                source_player_key=payload.source_player_key,
                canonical_name=(normalized.canonical_name if normalized is not None else payload.canonical_name),
            )
            session.add(row)
        row.row_number = row_number
        row.canonical_name = normalized.canonical_name if normalized is not None else payload.canonical_name
        row.status = status
        row.match_action = match_action
        row.import_action = import_action
        row.identity_confidence_score = confidence_score
        row.gtex_player_id = gtex_player_id
        row.source_link_id = source_link_id
        row.real_player_profile_id = real_player_profile_id
        row.authoritative_snapshot_id = authoritative_snapshot_id
        row.player_import_item_id = payload.player_import_item_id
        row.raw_payload_json = payload.model_dump(mode="json")
        row.normalized_payload_json = (
            {
                "identity": normalized.identity.to_dict(),
                "signals": normalized.normalized_signals(),
                "real_player_tier": normalized.real_player_tier,
                "competition_level": normalized.competition_level,
            }
            if normalized is not None
            else {}
        )
        row.import_metadata_json = {
            "player_import_item_id": payload.player_import_item_id,
            "review_status": review_status,
            "review_reason": review_reason,
            **(import_metadata or {}),
        }
        row.validation_errors_json = list(validation_errors or [])
        row.audit_findings_json = list(audit_findings or [])
        row.candidate_players_json = list(candidate_players or [])
        row.review_status = review_status
        row.review_reason = review_reason
        if normalized is not None:
            row.normalized_full_name = normalized.identity.normalized_full_name
            row.normalized_display_name = normalized.identity.normalized_display_name
            row.name_token_signature = normalized.identity.name_token_signature
            row.exact_identity_key = normalized.identity.exact_identity_key
            row.name_birthyear_club_key = normalized.identity.name_birthyear_club_key
            row.name_birthyear_nationality_key = normalized.identity.name_birthyear_nationality_key
            row.normalized_nationality = normalized.identity.normalized_nationality
            row.nationality_code = normalized.identity.nationality_code
            row.primary_position_key = normalized.identity.primary_position_key
            row.secondary_position_keys_json = list(normalized.identity.secondary_position_keys)
            row.position_family = normalized.identity.position_family
            row.dominant_foot = normalized.identity.dominant_foot
            row.height_cm = normalized.identity.height_cm
            row.club_reference_key = normalized.identity.club_reference_key
            row.league_reference_key = normalized.identity.league_reference_key
        row.processed_at = processed_at or row.processed_at
        session.flush()
        return row

    def _mark_import_row_imported(
        self,
        *,
        session: Session,
        ingestion_batch_id: str,
        staged: StagedRealPlayer,
        player_id: str,
        profile_id: str,
        snapshot_id: str,
        confidence_score: float,
        as_of: datetime,
    ) -> None:
        row = session.get(RealPlayerImportRow, staged.import_row_id)
        if row is None:
            return
        row.status = RealPlayerImportRowStatus.IMPORTED.value
        row.import_action = staged.action
        row.identity_confidence_score = confidence_score
        row.gtex_player_id = player_id
        row.real_player_profile_id = profile_id
        row.authoritative_snapshot_id = snapshot_id
        row.review_status = "resolved"
        row.review_reason = None
        row.processed_at = as_of

    def _complete_import_batch(
        self,
        *,
        session: Session,
        import_batch_id: str | None,
        report: RealPlayerDryRunReport,
        item_results: list[RealPlayerIngestionItemResult],
        error_message: str | None,
    ) -> None:
        if import_batch_id is None:
            return
        batch = session.get(RealPlayerImportBatch, import_batch_id)
        if batch is None:
            return
        batch.normalized_row_count = report.normalized_row_count
        batch.matched_existing_count = report.matched_existing_count
        batch.created_player_count = sum(1 for item in item_results if item.action == "created")
        batch.updated_player_count = sum(1 for item in item_results if item.action == "updated")
        batch.skipped_row_count = max(report.source_row_count - len(item_results), 0)
        batch.failed_row_count = (
            report.hard_failure_count + report.ambiguous_match_count + report.missing_pricing_snapshot_count
        )
        batch.authoritative_snapshot_count = len(item_results)
        batch.completed_at = report.as_of
        batch.status = (
            RealPlayerImportBatchStatus.COMPLETED.value
            if batch.failed_row_count == 0
            else RealPlayerImportBatchStatus.COMPLETED_WITH_ERRORS.value
        )
        batch.summary_json = {
            "source_row_count": report.source_row_count,
            "normalized_row_count": report.normalized_row_count,
            "matched_existing_count": report.matched_existing_count,
            "new_identity_count": report.new_identity_count,
            "ambiguous_match_count": report.ambiguous_match_count,
            "missing_pricing_snapshot_count": report.missing_pricing_snapshot_count,
            "hard_failure_count": report.hard_failure_count,
        }
        batch.error_message = error_message

    def _persist_blocked_import_batch(
        self,
        *,
        request: RealPlayerIngestionRequest,
        report: RealPlayerDryRunReport,
        as_of: datetime,
    ) -> None:
        issue_by_key = {(issue.source_name, issue.source_player_key): issue for issue in report.issues}
        row_numbers = {
            (player.source_name, player.source_player_key): index
            for index, player in enumerate(request.players, start=1)
        }
        with self.session_factory() as session:
            transaction = self._begin_session_transaction(session)
            try:
                batch = self._upsert_import_batch(
                    session=session,
                    request=request,
                    ingestion_batch_id=report.ingestion_batch_id,
                    as_of=as_of,
                )
                for payload in request.players:
                    key = (payload.source_name, payload.source_player_key)
                    issue = issue_by_key.get(key)
                    try:
                        normalized = self.normalization_service.normalize(payload, as_of=as_of)
                    except Exception:
                        normalized = None
                    status = (
                        RealPlayerImportRowStatus.MATCHED.value
                        if issue is None
                        else (
                            RealPlayerImportRowStatus.SKIPPED.value
                            if issue.issue_type == "ambiguous_match"
                            else RealPlayerImportRowStatus.FAILED.value
                        )
                    )
                    review_status = "open" if issue is not None else "resolved"
                    review_reason = issue.issue_type if issue is not None else None
                    candidate_players = (
                        [
                            {
                                "player_id": candidate.player_id,
                                "score": candidate.score,
                                "reasons": list(candidate.reasons),
                            }
                            for candidate in issue.candidates
                        ]
                        if issue is not None
                        else []
                    )
                    self._upsert_import_row(
                        session=session,
                        import_batch=batch,
                        row_number=row_numbers[key],
                        payload=payload,
                        normalized=normalized,
                        status=status,
                        match_action=(
                            "ambiguous" if issue is not None and issue.issue_type == "ambiguous_match" else None
                        ),
                        import_action="blocked",
                        confidence_score=max((candidate["score"] for candidate in candidate_players), default=None),
                        review_status=review_status,
                        review_reason=review_reason,
                        validation_errors=[issue.message] if issue is not None else [],
                        audit_findings=(
                            [{"finding_type": issue.issue_type, "message": issue.message}] if issue is not None else []
                        ),
                        candidate_players=candidate_players,
                        gtex_player_id=issue.gtex_player_id if issue is not None else None,
                        processed_at=as_of,
                    )
                self._complete_import_batch(
                    session=session,
                    import_batch_id=batch.id,
                    report=report,
                    item_results=[],
                    error_message=(
                        "Real-player batch blocked before commit."
                        if report.hard_failure_count
                        or report.missing_pricing_snapshot_count
                        or report.ambiguous_match_count
                        else None
                    ),
                )
                if report.hard_failure_count or report.missing_pricing_snapshot_count:
                    batch.status = RealPlayerImportBatchStatus.FAILED.value
                else:
                    batch.status = RealPlayerImportBatchStatus.COMPLETED_WITH_ERRORS.value
                transaction.commit()
            except Exception:
                if transaction.is_active:
                    transaction.rollback()
                raise

    @staticmethod
    def _candidate_payloads(candidates: tuple[RealPlayerBatchIssueCandidate, ...] | tuple) -> list[dict[str, object]]:
        return [
            {
                "player_id": candidate.player_id,
                "score": candidate.score,
                "reasons": list(candidate.reasons),
            }
            for candidate in candidates
        ]

    def _split_name(self, canonical_name: str) -> tuple[str | None, str | None]:
        parts = canonical_name.split()
        if not parts:
            return None, None
        if len(parts) == 1:
            return parts[0], None
        return parts[0], " ".join(parts[1:])

    def _short_name(self, canonical_name: str) -> str:
        parts = canonical_name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}. {' '.join(parts[1:])}"[:80]
        return canonical_name[:80]

    @staticmethod
    def _normalized_photo_url(value: str | None) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    #: Sources whose player photography the operator holds distribution rights for.
    _RIGHTS_CLEARED_SOURCES = frozenset({"sportmonks", "sofifa_fc25"})

    @classmethod
    def _photo_rights_cleared(cls, payload: RealPlayerSeedInput) -> bool:
        return str(payload.source_name or "").strip().lower() in cls._RIGHTS_CLEARED_SOURCES

    def _trusted_photo_moderation_status(self, payload: RealPlayerSeedInput) -> str:
        if self._photo_rights_cleared(payload):
            return ImageModerationStatus.APPROVED.value
        return ImageModerationStatus.PENDING.value

    @staticmethod
    def _profile_photo_url(profile: RealPlayerProfile) -> str | None:
        metadata = dict(profile.metadata_json or {})
        photo_url = metadata.get("photo_url")
        if isinstance(photo_url, str) and photo_url.strip():
            return photo_url.strip()
        image_payload = metadata.get("image")
        if isinstance(image_payload, dict):
            source_url = image_payload.get("source_url")
            if isinstance(source_url, str) and source_url.strip():
                return source_url.strip()
        return None

    @staticmethod
    def _national_team_payload(payload: RealPlayerSeedInput) -> dict[str, object] | None:
        name = str(payload.national_team_name or "").strip() or None
        code = str(payload.national_team_code or "").strip().upper() or None
        age_group = str(payload.national_team_age_group or "").strip().upper() or None
        if name is None and code is None and age_group is None:
            return None
        label_parts = [part for part in (name, age_group) if part]
        return {
            "name": name,
            "code": code,
            "age_group": age_group,
            "label": " ".join(label_parts) if label_parts else code,
            "kind": "youth" if age_group is not None else "senior",
        }

    @staticmethod
    def _profile_national_team(profile: RealPlayerProfile) -> dict[str, object] | None:
        metadata = dict(profile.metadata_json or {})
        national_team = metadata.get("national_team")
        if isinstance(national_team, dict):
            return national_team
        return None

    def _avatar_seed(self, *, source_name: str, source_player_key: str, canonical_name: str) -> tuple[str, str]:
        digest = hashlib.sha256(
            f"{source_name}|{source_player_key}|{canonical_name}|avatar".encode("utf-8")
        ).hexdigest()
        return digest[:16], "-".join(digest[offset : offset + 8] for offset in range(0, 32, 8))


__all__ = [
    "RealPlayerIngestionError",
    "RealPlayerIngestionService",
    "RealPlayerPricingError",
]
