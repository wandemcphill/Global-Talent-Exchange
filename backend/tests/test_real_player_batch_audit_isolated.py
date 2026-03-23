from __future__ import annotations

from contextlib import redirect_stdout
from datetime import UTC, date, datetime
from decimal import Decimal
from io import StringIO
import os
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.core.database import load_model_modules
from app.core.config import load_settings
from app.ingestion.audit_regen_cohort import AuditRegenCohortSeeder, AuditRegenSpec
from app.ingestion.models import Player
from app.ingestion.real_player_batch_audit import FAIL_VERDICT, PASS_VERDICT, RealPlayerBatchAuditService
from app.market.service import MarketPlayerQueryService, MarketValidationError
from app.models.base import Base
from app.models.player_cards import PlayerCardTier, PlayerMarketValueSnapshot
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.player_cards.marketplace_service import PlayerCardMarketplaceService
from app.player_cards.service import PlayerCardValidationError
from app.players.read_models import PlayerSummaryReadModel
from app.pricing.service import MarketPricingService
from app.value_engine.read_models import PlayerValueSnapshotRecord
from backend.scripts.audit_real_player_batch import render_report


def _session_factory():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
            {"version_num": "20260322_0029_regen_universe_layer"},
        )
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _make_player(
    session,
    *,
    provider_external_id: str,
    full_name: str,
    normalized_position: str,
    date_of_birth: date,
    market_value_eur: float,
    is_real_player: bool = False,
    real_player_tier: str | None = None,
) -> Player:
    player = Player(
        source_provider="audit-test",
        provider_external_id=provider_external_id,
        full_name=full_name,
        short_name=full_name.split()[-1][:8],
        position=normalized_position,
        normalized_position=normalized_position,
        date_of_birth=date_of_birth,
        market_value_eur=market_value_eur,
        is_tradable=True,
        is_real_player=is_real_player,
        real_player_tier=real_player_tier,
        canonical_display_name=full_name,
    )
    session.add(player)
    session.flush()
    return player


def _seed_authoritative_player(
    session,
    *,
    provider_external_id: str,
    full_name: str,
    normalized_position: str,
    date_of_birth: date,
    current_value_credits: float,
    global_scouting_index: float,
    market_value_eur: float,
    is_real_player: bool = False,
    real_player_tier: str | None = None,
    batch_id: str | None = None,
    source_player_key: str | None = None,
    nationality: str | None = None,
    create_snapshot: bool = True,
    create_summary: bool = True,
    create_market_snapshot: bool = True,
    profile_pricing_snapshot_id: str | None = None,
) -> dict[str, object]:
    as_of = datetime(2026, 3, 22, 15, 0, tzinfo=UTC)
    player = _make_player(
        session,
        provider_external_id=provider_external_id,
        full_name=full_name,
        normalized_position=normalized_position,
        date_of_birth=date_of_birth,
        market_value_eur=market_value_eur,
        is_real_player=is_real_player,
        real_player_tier=real_player_tier,
    )
    snapshot_id = profile_pricing_snapshot_id or f"snap-{provider_external_id}"
    snapshot = None
    if create_snapshot:
        snapshot = PlayerValueSnapshotRecord(
            id=snapshot_id,
            player_id=player.id,
            player_name=full_name,
            as_of=as_of,
            snapshot_type="intraday",
            previous_credits=max(current_value_credits - 12.0, 1.0),
            target_credits=current_value_credits,
            movement_pct=4.5,
            football_truth_value_credits=max(current_value_credits - 5.0, 1.0),
            market_signal_value_credits=max(current_value_credits - 3.0, 1.0),
            scouting_signal_value_credits=current_value_credits,
            egame_signal_value_credits=max(current_value_credits - 6.0, 1.0),
            confidence_score=0.92,
            confidence_tier="high",
            liquidity_tier="default",
            market_integrity_score=0.91,
            signal_trust_score=0.95,
            trend_7d_pct=3.0,
            trend_30d_pct=8.0,
            trend_direction="up",
            trend_confidence=0.81,
            config_version="baseline-v1",
            breakdown_json={
                "published_card_value_credits": current_value_credits,
                "global_scouting_index": global_scouting_index,
                "previous_global_scouting_index": max(global_scouting_index - 2.0, 0.0),
                "global_scouting_index_movement_pct": 2.1,
            },
            drivers_json=["authoritative_value_engine"],
            reason_codes_json=["authoritative_snapshot"],
        )
        session.add(snapshot)
    summary = None
    if create_summary:
        summary_payload = {
            "published_card_value_credits": current_value_credits,
            "global_scouting_index": global_scouting_index,
        }
        if is_real_player:
            summary_payload["real_player_profile"] = {
                "is_real_player": True,
                "real_player_tier": real_player_tier,
                "pricing_snapshot_id": snapshot_id,
            }
            summary_payload["ingestion_metadata"] = {
                "ingestion_batch_id": batch_id,
                "authoritative_snapshot_id": snapshot_id,
            }
        summary = PlayerSummaryReadModel(
            player_id=player.id,
            player_name=full_name,
            current_club_name=None,
            current_competition_name=None,
            last_snapshot_id=snapshot_id if create_snapshot else None,
            last_snapshot_at=as_of,
            current_value_credits=current_value_credits,
            previous_value_credits=max(current_value_credits - 12.0, 1.0),
            movement_pct=4.5,
            average_rating=7.2,
            market_interest_score=44,
            summary_json=summary_payload,
        )
        session.add(summary)
    market_snapshot = None
    if create_market_snapshot and create_snapshot:
        market_snapshot = PlayerMarketValueSnapshot(
            player_id=player.id,
            as_of=as_of,
            last_trade_price_credits=None,
            avg_trade_price_credits=current_value_credits,
            volume_24h=0,
            listing_floor_price_credits=current_value_credits,
            listing_count=0,
            high_24h_price_credits=current_value_credits,
            low_24h_price_credits=current_value_credits,
            metadata_json={
                "source": "authoritative_value_engine",
                "authoritative_snapshot_id": snapshot_id,
                "real_player_ingestion": is_real_player,
            },
        )
        session.add(market_snapshot)
    profile = None
    if is_real_player:
        source_link = RealPlayerSourceLink(
            gtex_player_id=player.id,
            source_name="curated-feed",
            source_player_key=source_player_key or provider_external_id,
            canonical_name=full_name,
            nationality=nationality,
            date_of_birth=date_of_birth,
            birth_year=date_of_birth.year,
            primary_position=normalized_position,
            current_real_world_club="Audit Club",
            identity_confidence_score=0.96,
        )
        session.add(source_link)
        session.flush()
        profile = RealPlayerProfile(
            gtex_player_id=player.id,
            source_link_id=source_link.id,
            source_name="curated-feed",
            source_player_key=source_player_key or provider_external_id,
            canonical_name=full_name,
            nationality=nationality,
            birth_year=date_of_birth.year,
            date_of_birth=date_of_birth,
            primary_position=normalized_position,
            current_club_name="Audit Club",
            current_league_name="Audit League",
            competition_level=real_player_tier,
            current_market_reference_value=market_value_eur,
            market_reference_currency="EUR",
            normalized_signals_json={"seed": "test"},
            metadata_json={},
            ingestion_batch_id=batch_id,
            pricing_snapshot_id=snapshot_id if profile_pricing_snapshot_id is not None or create_snapshot else None,
        )
        session.add(profile)
    session.flush()
    return {
        "player": player,
        "snapshot": snapshot,
        "summary": summary,
        "market_snapshot": market_snapshot,
        "profile": profile,
        "as_of": as_of,
    }


def _seed_market_tier(session) -> PlayerCardTier:
    tier = PlayerCardTier(
        code="common",
        name="Common",
        rarity_rank=1,
        base_mint_price_credits=Decimal("12.0000"),
    )
    session.add(tier)
    session.flush()
    return tier


def _seed_regens(session, *specs: AuditRegenSpec, cohort_key: str = "audit-test-regens") -> None:
    AuditRegenCohortSeeder(
        session,
        cohort_key=cohort_key,
    ).seed(specs or ())


def test_audit_service_passes_for_authoritative_first_batch() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            batch_id = "batch-first"
            _seed_authoritative_player(
                session,
                provider_external_id="real-elite",
                full_name="Victor Osimhen",
                normalized_position="ST",
                date_of_birth=date(1998, 12, 29),
                current_value_credits=620.0,
                global_scouting_index=92.0,
                market_value_eur=60_000_000,
                is_real_player=True,
                real_player_tier="elite",
                batch_id=batch_id,
                nationality="Nigeria",
            )
            _seed_authoritative_player(
                session,
                provider_external_id="real-core",
                full_name="Alex Iwobi",
                normalized_position="CM",
                date_of_birth=date(1996, 5, 3),
                current_value_credits=340.0,
                global_scouting_index=74.0,
                market_value_eur=18_000_000,
                is_real_player=True,
                real_player_tier="featured",
                batch_id=batch_id,
                nationality="Nigeria",
            )
            _seed_authoritative_player(
                session,
                provider_external_id="real-prospect",
                full_name="Sam Prospect",
                normalized_position="ST",
                date_of_birth=date(2006, 2, 15),
                current_value_credits=220.0,
                global_scouting_index=71.0,
                market_value_eur=9_000_000,
                is_real_player=True,
                real_player_tier="watchlist",
                batch_id=batch_id,
                nationality="Ghana",
            )
            _seed_authoritative_player(
                session,
                provider_external_id="real-filler",
                full_name="Luka Depth",
                normalized_position="CB",
                date_of_birth=date(1997, 7, 8),
                current_value_credits=180.0,
                global_scouting_index=68.0,
                market_value_eur=7_500_000,
                is_real_player=True,
                real_player_tier="core",
                batch_id=batch_id,
                nationality="Croatia",
            )
            _seed_regens(
                session,
                AuditRegenSpec(
                    key="regen-1",
                    full_name="Regen Striker",
                    country_code="NG",
                    country_name="Nigeria",
                    position="ST",
                    normalized_position="ST",
                    date_of_birth=date(1999, 1, 10),
                    current_value_credits=590.0,
                    global_scouting_index=90.0,
                ),
                AuditRegenSpec(
                    key="regen-2",
                    full_name="Regen Midfielder",
                    country_code="GH",
                    country_name="Ghana",
                    position="CM",
                    normalized_position="CM",
                    date_of_birth=date(1996, 5, 11),
                    current_value_credits=330.0,
                    global_scouting_index=72.0,
                ),
                AuditRegenSpec(
                    key="regen-3",
                    full_name="Regen Prospect",
                    country_code="GH",
                    country_name="Ghana",
                    position="ST",
                    normalized_position="ST",
                    date_of_birth=date(2005, 9, 1),
                    current_value_credits=210.0,
                    global_scouting_index=69.0,
                ),
                AuditRegenSpec(
                    key="regen-4",
                    full_name="Regen Defender",
                    country_code="HR",
                    country_name="Croatia",
                    position="CB",
                    normalized_position="CB",
                    date_of_birth=date(1998, 8, 1),
                    current_value_credits=170.0,
                    global_scouting_index=66.0,
                ),
                cohort_key="batch-first-regens",
            )
            session.commit()

        report = RealPlayerBatchAuditService(session_factory=session_factory).run(first_batch=True)

        assert report.verdict == PASS_VERDICT
        assert report.selected_batch_id == "batch-first"
        assert all(row.status == PASS_VERDICT for row in report.pricing_integrity_rows)
        assert any("[mixed_sort_order]" in finding and "sorts correctly" in finding for finding in report.market_coherence_findings)
    finally:
        engine.dispose()


def test_audit_service_fails_when_snapshot_or_summary_is_missing() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_authoritative_player(
                session,
                provider_external_id="broken-real",
                full_name="Broken Snapshot",
                normalized_position="ST",
                date_of_birth=date(2000, 1, 1),
                current_value_credits=400.0,
                global_scouting_index=80.0,
                market_value_eur=10_000_000,
                is_real_player=True,
                real_player_tier="elite",
                batch_id="batch-broken",
                nationality="Nigeria",
                create_snapshot=False,
                create_summary=False,
                profile_pricing_snapshot_id="missing-snapshot-id",
            )
            _seed_regens(
                session,
                AuditRegenSpec(
                    key="regen-safe",
                    full_name="Regen Safe",
                    country_code="NG",
                    country_name="Nigeria",
                    position="ST",
                    normalized_position="ST",
                    date_of_birth=date(1999, 5, 1),
                    current_value_credits=350.0,
                    global_scouting_index=75.0,
                ),
                cohort_key="batch-broken-regens",
            )
            session.commit()

        report = RealPlayerBatchAuditService(session_factory=session_factory).run(ingestion_batch_id="batch-broken")

        assert report.verdict == FAIL_VERDICT
        assert any(row.status == FAIL_VERDICT for row in report.pricing_integrity_rows)
        assert any("Pricing integrity failed for Broken Snapshot" in risk for risk in report.residual_risks)
    finally:
        engine.dispose()


def test_audit_service_does_not_treat_generic_non_real_players_as_regens() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_authoritative_player(
                session,
                provider_external_id="real-only",
                full_name="Real Only",
                normalized_position="ST",
                date_of_birth=date(1999, 1, 1),
                current_value_credits=420.0,
                global_scouting_index=82.0,
                market_value_eur=18_000_000,
                is_real_player=True,
                real_player_tier="elite",
                batch_id="batch-generic-non-real",
                nationality="Nigeria",
            )
            _seed_authoritative_player(
                session,
                provider_external_id="generic-non-real",
                full_name="Generic Non Real",
                normalized_position="ST",
                date_of_birth=date(1999, 6, 1),
                current_value_credits=300.0,
                global_scouting_index=70.0,
                market_value_eur=0,
            )
            session.commit()

        report = RealPlayerBatchAuditService(session_factory=session_factory).run(
            ingestion_batch_id="batch-generic-non-real"
        )

        assert report.verdict == FAIL_VERDICT
        assert any("[market_query_missing_regens]" in finding for finding in report.market_coherence_findings)
        assert any("No authoritative regen comparator pool was available" in risk for risk in report.residual_risks)
    finally:
        engine.dispose()


def test_audit_service_flags_distribution_anomalies() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            batch_id = "batch-anomaly"
            _seed_authoritative_player(
                session,
                provider_external_id="elite-low",
                full_name="Elite Low",
                normalized_position="ST",
                date_of_birth=date(1998, 1, 1),
                current_value_credits=300.0,
                global_scouting_index=90.0,
                market_value_eur=50_000_000,
                is_real_player=True,
                real_player_tier="elite",
                batch_id=batch_id,
                nationality="Nigeria",
            )
            _seed_authoritative_player(
                session,
                provider_external_id="filler-high",
                full_name="Filler High",
                normalized_position="ST",
                date_of_birth=date(1999, 1, 1),
                current_value_credits=520.0,
                global_scouting_index=78.0,
                market_value_eur=15_000_000,
                is_real_player=True,
                real_player_tier="core",
                batch_id=batch_id,
                nationality="Spain",
            )
            _seed_authoritative_player(
                session,
                provider_external_id="prospect-over",
                full_name="Prospect Over",
                normalized_position="ST",
                date_of_birth=date(2006, 1, 1),
                current_value_credits=610.0,
                global_scouting_index=80.0,
                market_value_eur=12_000_000,
                is_real_player=True,
                real_player_tier="watchlist",
                batch_id=batch_id,
                nationality="Ghana",
            )
            for index in range(3):
                _seed_authoritative_player(
                    session,
                    provider_external_id=f"cluster-{index}",
                    full_name=f"Cluster Player {index}",
                    normalized_position="CM",
                    date_of_birth=date(1997, 6, 1),
                    current_value_credits=250.0,
                    global_scouting_index=60.0 + index,
                    market_value_eur=8_000_000,
                    is_real_player=True,
                    real_player_tier="core",
                    batch_id=batch_id,
                    nationality="Nigeria" if index == 0 else "France",
                )
            _seed_regens(
                session,
                AuditRegenSpec(
                    key="regen-st-1",
                    full_name="Regen ST 1",
                    country_code="NG",
                    country_name="Nigeria",
                    position="ST",
                    normalized_position="ST",
                    date_of_birth=date(1998, 1, 1),
                    current_value_credits=500.0,
                    global_scouting_index=85.0,
                ),
                AuditRegenSpec(
                    key="regen-st-2",
                    full_name="Regen ST 2",
                    country_code="GH",
                    country_name="Ghana",
                    position="ST",
                    normalized_position="ST",
                    date_of_birth=date(2006, 1, 1),
                    current_value_credits=200.0,
                    global_scouting_index=70.0,
                ),
                AuditRegenSpec(
                    key="regen-cm-1",
                    full_name="Regen CM 1",
                    country_code="ES",
                    country_name="Spain",
                    position="CM",
                    normalized_position="CM",
                    date_of_birth=date(1997, 6, 1),
                    current_value_credits=120.0,
                    global_scouting_index=55.0,
                ),
                cohort_key="batch-anomaly-regens",
            )
            session.commit()

        report = RealPlayerBatchAuditService(session_factory=session_factory).run(ingestion_batch_id="batch-anomaly")

        assert report.verdict == FAIL_VERDICT
        assert any("[identical_value_cluster]" in finding for finding in report.distribution_findings)
        assert any("[elite_value_inversion]" in finding for finding in report.distribution_findings)
        assert any("[prospect_superstar_inversion]" in finding for finding in report.distribution_findings)
    finally:
        engine.dispose()


def test_runtime_guards_fail_closed_for_real_players_without_authoritative_value() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            player = _make_player(
                session,
                provider_external_id="real-no-value",
                full_name="No Value Real",
                normalized_position="ST",
                date_of_birth=date(2001, 1, 1),
                market_value_eur=25_000_000,
                is_real_player=True,
                real_player_tier="elite",
            )
            tier = _seed_market_tier(session)
            session.commit()

        with session_factory() as session:
            market_service = MarketPlayerQueryService(session=session)
            with pytest.raises(MarketValidationError):
                market_service.get_player_ticker(player.id)

            pricing_service = MarketPricingService(session_factory=session_factory)
            assert pricing_service._load_reference_context(player.id) == (None, player.short_name)

            marketplace_service = PlayerCardMarketplaceService(
                session=session,
                settings=load_settings(environ={**os.environ, "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:"}),
            )
            with pytest.raises(PlayerCardValidationError):
                marketplace_service._base_value_credits({"player": player, "tier": tier})
    finally:
        engine.dispose()


def test_market_sort_uses_authoritative_current_values_for_mixed_cohorts() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            real = _seed_authoritative_player(
                session,
                provider_external_id="real-mid",
                full_name="Real Mid",
                normalized_position="CM",
                date_of_birth=date(1998, 1, 1),
                current_value_credits=400.0,
                global_scouting_index=80.0,
                market_value_eur=22_000_000,
                is_real_player=True,
                real_player_tier="elite",
                batch_id="batch-sort",
                nationality="Nigeria",
            )
            regen_high = _seed_authoritative_player(
                session,
                provider_external_id="regen-high",
                full_name="Regen High",
                normalized_position="CM",
                date_of_birth=date(1998, 1, 1),
                current_value_credits=500.0,
                global_scouting_index=88.0,
                market_value_eur=0,
            )
            regen_low = _seed_authoritative_player(
                session,
                provider_external_id="regen-low",
                full_name="Regen Low",
                normalized_position="CM",
                date_of_birth=date(1998, 1, 1),
                current_value_credits=300.0,
                global_scouting_index=70.0,
                market_value_eur=0,
            )
            session.commit()

        with session_factory() as session:
            service = MarketPlayerQueryService(session=session)
            result = service.list_players(limit=10, sort="current_value")
            ordered_ids = [item.player_id for item in result.items[:3]]
            assert ordered_ids == [
                regen_high["player"].id,
                real["player"].id,
                regen_low["player"].id,
            ]
            assert service.get_player_detail(real["player"].id).value.current_value_credits == 400.0
    finally:
        engine.dispose()


def test_cli_render_uses_exact_section_order() -> None:
    engine, session_factory = _session_factory()
    try:
        with session_factory() as session:
            _seed_authoritative_player(
                session,
                provider_external_id="render-real",
                full_name="Render Real",
                normalized_position="ST",
                date_of_birth=date(1998, 1, 1),
                current_value_credits=410.0,
                global_scouting_index=81.0,
                market_value_eur=20_000_000,
                is_real_player=True,
                real_player_tier="elite",
                batch_id="batch-render",
                nationality="Nigeria",
            )
            _seed_regens(
                session,
                AuditRegenSpec(
                    key="render-regen",
                    full_name="Render Regen",
                    country_code="NG",
                    country_name="Nigeria",
                    position="ST",
                    normalized_position="ST",
                    date_of_birth=date(1998, 1, 1),
                    current_value_credits=390.0,
                    global_scouting_index=78.0,
                ),
                cohort_key="batch-render-regens",
            )
            session.commit()

        report = RealPlayerBatchAuditService(session_factory=session_factory).run(ingestion_batch_id="batch-render")
        rendered = render_report(report)

        expected_sections = [
            "1. Summary",
            "2. Exact files changed",
            "3. Checks/queries run",
            "4. Pricing integrity table",
            "5. Distribution findings",
            "6. Market coherence findings",
            "7. Any narrow tuning applied",
            "8. Residual risks",
            "9. Verdict: pass/fail for first-batch pricing stability",
        ]
        positions = [rendered.index(section) for section in expected_sections]
        assert positions == sorted(positions)
        assert rendered.rstrip().endswith(report.verdict)

        buffer = StringIO()
        with redirect_stdout(buffer):
            print(rendered)
        assert "1. Summary" in buffer.getvalue()
    finally:
        engine.dispose()
