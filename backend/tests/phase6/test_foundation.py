from __future__ import annotations

from datetime import date

import pytest

from app.phase6.foundation import (
    ClubAppointmentRole,
    ClubStaffAppointment,
    FacilityProgressionBoundary,
    FacilityTrack,
    FacilityUpgradeStatus,
    GtexSeasonRef,
    GtexSeasonStatus,
    PersonalManagerIdentity,
    PersonalManagerQualityBand,
    PlayerMarketLifecycleState,
    RegenCareerStage,
    RegenCareerState,
    RegenLegacyStatus,
    StaffPersonContract,
    StaffQualification,
    StaffSpecialisation,
)


def test_real_player_market_states_are_explicit_and_distinct() -> None:
    assert [state.value for state in PlayerMarketLifecycleState] == [
        "searchable_only",
        "market_pending",
        "market_active",
        "trade_only",
        "market_blocked",
    ]


def test_regen_career_clock_does_not_invent_age_conversion() -> None:
    state = RegenCareerState(
        regen_id="regen-1",
        stage=RegenCareerStage.ACADEMY_PROSPECT,
        birth_season_number=2,
        current_season_number=7,
        active_career_seasons=3,
        legacy_status=RegenLegacyStatus.NONE,
    )
    assert state.virtual_age_years is None
    assert state.age_calculation_version is None


def test_virtual_age_requires_an_explicit_calculation_version() -> None:
    with pytest.raises(ValueError, match="age_calculation_version"):
        RegenCareerState(
            regen_id="regen-1",
            stage=RegenCareerStage.SENIOR_PLAYER,
            birth_season_number=1,
            current_season_number=3,
            virtual_age_years=18.2,
        )


def test_retired_regen_requires_retirement_season() -> None:
    with pytest.raises(ValueError, match="retirement_season_number"):
        RegenCareerState(
            regen_id="regen-1",
            stage=RegenCareerStage.RETIRED_LEGACY,
            birth_season_number=1,
            current_season_number=8,
        )


def test_staff_person_is_unique_and_qualifications_are_separate_from_appointment() -> None:
    person = StaffPersonContract(
        staff_person_id="staff-1",
        display_name="Sample Coach",
        specialisations=(StaffSpecialisation.COACH,),
        qualifications=(StaffQualification.FOOTBALL_COACHING,),
    )
    appointment = ClubStaffAppointment(
        staff_person_id=person.staff_person_id,
        club_id="club-1",
        role=ClubAppointmentRole.FIRST_TEAM_MANAGER,
    )
    assert person.unique_share is True
    assert appointment.role is ClubAppointmentRole.FIRST_TEAM_MANAGER
    assert appointment.salary_coin_unit == "FAN"


def test_medical_appointment_requires_medical_specialisation_or_qualification_at_contract_level() -> None:
    person = StaffPersonContract(
        staff_person_id="staff-medical",
        display_name="Qualified Physio",
        specialisations=(StaffSpecialisation.PHYSIOTHERAPY,),
        qualifications=(StaffQualification.PHYSIOTHERAPY,),
    )
    appointment = ClubStaffAppointment(
        staff_person_id=person.staff_person_id,
        club_id="club-1",
        role=ClubAppointmentRole.MEDICAL_STAFF,
    )
    assert StaffQualification.PHYSIOTHERAPY in person.qualifications
    assert appointment.role is ClubAppointmentRole.MEDICAL_STAFF


def test_personal_manager_quality_bands_are_fixed_and_non_transferable_non_salaried() -> None:
    manager = PersonalManagerIdentity(
        gt_profile_id="profile-1",
        manager_id="pm-1",
        quality_band=PersonalManagerQualityBand.BAND_96_99,
        gsi_min=96,
        gsi_max=99,
    )
    assert manager.transferable is False
    assert manager.salaried is False
    assert manager.creation_price_fan_coin is None

    with pytest.raises(ValueError, match="GSI bounds"):
        PersonalManagerIdentity(
            gt_profile_id="profile-2",
            manager_id="pm-2",
            quality_band=PersonalManagerQualityBand.BAND_91_95,
            gsi_min=90,
            gsi_max=95,
        )


def test_facility_progression_uses_fan_coin_without_inventing_a_price_or_timing() -> None:
    baseline = FacilityProgressionBoundary(
        club_id="club-1",
        track=FacilityTrack.MEDICAL_CENTRE,
    )
    assert baseline.level == 1
    assert baseline.status is FacilityUpgradeStatus.NOT_STARTED
    assert baseline.fan_coin_investment is None
    assert baseline.completion_season_number is None

    in_progress = FacilityProgressionBoundary(
        club_id="club-1",
        track=FacilityTrack.TRAINING_CENTRE,
        level=2,
        status=FacilityUpgradeStatus.IN_PROGRESS,
        target_level=3,
    )
    assert in_progress.target_level == 3


def test_season_reference_only_defines_calendar_boundaries() -> None:
    season = GtexSeasonRef(
        season_number=12,
        status=GtexSeasonStatus.ACTIVE,
    )
    assert season.season_number == 12
    assert season.starts_on is None
    assert season.ends_on is None

    with pytest.raises(ValueError, match="ends_on"):
        GtexSeasonRef(
            season_number=12,
            status=GtexSeasonStatus.COMPLETED,
            starts_on=date(2027, 1, 2),
            ends_on=date(2027, 1, 1),
        )
