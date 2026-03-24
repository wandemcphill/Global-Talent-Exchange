from __future__ import annotations

from datetime import UTC, date, datetime

from app.ingestion.real_player_import_models import RealPlayerImportStagingRecord
from app.ingestion.second_zip_publish_readiness import (
    DEFAULT_SECOND_ZIP_FALLBACK_MARKET_VALUE_EUR,
    SECOND_ZIP_FREE_AGENT_CLUB_KEY,
    SECOND_ZIP_FREE_AGENT_CLUB_NAME,
    SecondZipClubAssignmentType,
    SecondZipPublishReadinessService,
    SecondZipPublishTier,
    SecondZipValuationSource,
)
from app.ingestion.transfermarkt_second_zip import SECOND_ZIP_SOURCE_NAME


REFERENCE_DATE = date(2026, 3, 23)


def _record(
    *,
    player_id: str,
    name: str,
    provider_last_updated_at: datetime | None = None,
    market_value_in_eur: str = "250000",
    provider_club_id: str | None = "100",
    provider_club_name: str | None = "Test FC",
    provider_competition_id: str | None = "NG1",
    provider_competition_name: str | None = "Nigeria Premier League",
    position: str = "Attack",
    sub_position: str = "Centre-Forward",
    metadata_json: dict[str, object] | None = None,
) -> RealPlayerImportStagingRecord:
    refreshed_at = provider_last_updated_at or datetime(2026, 3, 23, 12, 0, tzinfo=UTC)
    return RealPlayerImportStagingRecord(
        provider_name=SECOND_ZIP_SOURCE_NAME,
        provider_player_id=player_id,
        provider_club_id=provider_club_id,
        provider_club_name=provider_club_name,
        provider_competition_id=provider_competition_id,
        provider_competition_name=provider_competition_name,
        provider_season_id="2024",
        full_name=name,
        first_name=name.split(" ")[0] if name else None,
        last_name=name.split(" ")[-1] if name else None,
        short_name=None,
        display_position=sub_position or position,
        nationality_name="Nigeria",
        nationality_code="NG",
        date_of_birth=date(2000, 1, 2),
        provider_last_updated_at=refreshed_at,
        source_version="2ndzip-20260323",
        import_state="staged",
        last_import_cursor=None,
        source_payload_hash=f"hash-{player_id}",
        first_seen_at=refreshed_at,
        last_seen_at=refreshed_at,
        last_import_run_id=None,
        latest_payload_json={
            "player_id": player_id,
            "name": name,
            "position": position,
            "sub_position": sub_position,
            "date_of_birth": "2000-01-02 00:00:00",
            "last_season": "2024",
            "current_club_id": provider_club_id,
            "current_club_name": provider_club_name,
            "current_club_domestic_competition_id": provider_competition_id,
            "current_club_domestic_competition_name": provider_competition_name,
            "market_value_in_eur": market_value_in_eur,
        },
        metadata_json=metadata_json or {},
    )


def test_publish_readiness_assigns_conservative_fallback_value_when_market_value_is_missing() -> None:
    service = SecondZipPublishReadinessService(reference_date=REFERENCE_DATE)
    record = _record(
        player_id="10",
        name="Fallback Prospect",
        market_value_in_eur="",
        metadata_json={
            "dedupe": {"status": "passed"},
            "canonical_mapping": {
                "club": {"status": "resolved", "canonical_club_id": "club-100"},
                "competition": {"status": "resolved", "canonical_competition_id": "comp-ng1"},
            },
        },
    )

    result = service.evaluate_record(record)

    assert result.publish_ready is True
    assert result.publish_tier == SecondZipPublishTier.TIER_2
    assert result.publish_blockers == ()
    assert result.valuation.market_value_eur == DEFAULT_SECOND_ZIP_FALLBACK_MARKET_VALUE_EUR
    assert result.valuation.source == SecondZipValuationSource.FALLBACK_MARKET_VALUE
    assert result.valuation.is_fallback is True
    assert result.valuation.reason_code == "missing_market_value_in_eur"
    assert result.club_assignment.assignment_type == SecondZipClubAssignmentType.RESOLVED_CLUB
    assert result.club_assignment.is_fallback is False


def test_publish_ready_selector_prioritizes_cleaner_tiers_then_freshness() -> None:
    service = SecondZipPublishReadinessService(reference_date=REFERENCE_DATE)
    records = [
        _record(
            player_id="tier2",
            name="Tier Two Player",
            market_value_in_eur="",
            provider_last_updated_at=datetime(2026, 3, 23, 13, 0, tzinfo=UTC),
            metadata_json={"dedupe_passed": True, "canonical_mapping": {"club": {"status": "resolved"}}},
        ),
        _record(
            player_id="tier1-old",
            name="Tier One Old",
            market_value_in_eur="400000",
            provider_last_updated_at=datetime(2026, 3, 21, 10, 0, tzinfo=UTC),
            metadata_json={"dedupe_passed": True, "canonical_mapping": {"club": {"status": "resolved"}}},
        ),
        _record(
            player_id="tier1-new",
            name="Tier One New",
            market_value_in_eur="450000",
            provider_last_updated_at=datetime(2026, 3, 22, 10, 0, tzinfo=UTC),
            metadata_json={"dedupe_passed": True, "canonical_mapping": {"club": {"status": "resolved"}}},
        ),
        _record(
            player_id="invalid",
            name="Invalid Partial",
            sub_position="",
            provider_last_updated_at=datetime(2026, 3, 24, 10, 0, tzinfo=UTC),
            metadata_json={"dedupe_passed": True, "canonical_mapping": {"club": {"status": "resolved"}}},
        ),
    ]

    selected = service.select_publish_ready(records)

    assert [item.provider_player_id for item in selected] == [
        "tier1-new",
        "tier1-old",
        "tier2",
    ]
    assert [item.publish_tier for item in selected] == [
        SecondZipPublishTier.TIER_1,
        SecondZipPublishTier.TIER_1,
        SecondZipPublishTier.TIER_2,
    ]


def test_publish_tiers_capture_resolved_placeholder_and_free_agent_paths() -> None:
    service = SecondZipPublishReadinessService(reference_date=REFERENCE_DATE)
    resolved = service.evaluate_record(
        _record(
            player_id="resolved",
            name="Resolved Club",
            metadata_json={"dedupe": {"status": "passed"}, "canonical_mapping": {"club": {"status": "resolved"}}},
        )
    )
    free_agent = service.evaluate_record(
        _record(
            player_id="free-agent",
            name="Free Agent",
            provider_club_id=None,
            provider_club_name=None,
            provider_competition_id=None,
            provider_competition_name=None,
            metadata_json={"dedupe": {"status": "passed"}},
        )
    )
    placeholder = service.evaluate_record(
        _record(
            player_id="placeholder",
            name="Placeholder Club",
            provider_club_id="999",
            provider_club_name="Unmapped FC",
            metadata_json={"dedupe": {"status": "passed"}, "canonical_mapping": {"club": {"status": "open"}}},
        )
    )

    assert resolved.publish_tier == SecondZipPublishTier.TIER_1
    assert resolved.club_assignment.assignment_type == SecondZipClubAssignmentType.RESOLVED_CLUB

    assert free_agent.publish_ready is True
    assert free_agent.publish_tier == SecondZipPublishTier.TIER_2
    assert free_agent.club_assignment.assignment_type == SecondZipClubAssignmentType.FREE_AGENT_FALLBACK
    assert free_agent.club_assignment.club_name == SECOND_ZIP_FREE_AGENT_CLUB_NAME
    assert free_agent.club_assignment.club_key == SECOND_ZIP_FREE_AGENT_CLUB_KEY

    assert placeholder.publish_ready is True
    assert placeholder.publish_tier == SecondZipPublishTier.TIER_2
    assert placeholder.club_assignment.assignment_type == SecondZipClubAssignmentType.CLUB_PLACEHOLDER
    assert placeholder.club_assignment.club_key == "placeholder:999"
    assert placeholder.club_assignment.reason_code == "unresolved_club_mapping"


def test_publish_readiness_excludes_rows_with_base_filter_dedupe_or_hard_validation_blockers() -> None:
    service = SecondZipPublishReadinessService(reference_date=REFERENCE_DATE)
    result = service.evaluate_record(
        _record(
            player_id="blocked",
            name="Blocked Player",
            position="",
            sub_position="",
            metadata_json={
                "dedupe": {"status": "duplicate"},
                "validation": {"hard_blockers": ["Missing Nationality"]},
            },
        )
    )

    assert result.publish_ready is False
    assert result.publish_tier == SecondZipPublishTier.TIER_3
    assert result.dedupe_passed is False
    assert result.hard_validation_blockers == ("missing_nationality",)
    assert "base_import_filter:missing_position" in result.publish_blockers
    assert "base_import_filter:missing_sub_position" in result.publish_blockers
    assert "dedupe_failed" in result.publish_blockers
    assert "hard_validation_blocker:missing_nationality" in result.publish_blockers
