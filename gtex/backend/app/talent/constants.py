"""Shared vocabulary for the GTEX Talent Exchange discovery layer.

Everything in this module is data, not behaviour, so that the ranking pipeline
(`app.talent.ranking`), the signal pipeline (`app.talent.signals`) and the
persistence layer (`app.talent.models`) all agree on the same bounded
vocabularies. Bounded vocabularies matter here because search filters are built
directly from them: an unbounded filter surface is an unbounded query surface.
"""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType
from typing import Final, Mapping

TALENT_RANKING_CONFIG_VERSION: Final[str] = "talent_rank_v1"
TALENT_SIGNAL_CONFIG_VERSION: Final[str] = "talent_signal_v1"


class VerificationTier(StrEnum):
    """Verification ladder.

    A profile existing is *not* verification. `UNVERIFIED` is the default and
    the only tier that may be inferred; every other tier requires an explicit,
    audited admin decision recorded in `talent_verification_records`.
    """

    UNVERIFIED = "unverified"
    IDENTITY_VERIFIED = "identity_verified"
    PROFILE_VERIFIED = "profile_verified"
    CREDENTIALS_VERIFIED = "credentials_verified"
    STAFF_VERIFIED = "staff_verified"


VERIFICATION_TIER_RANK: Final[Mapping[str, int]] = MappingProxyType(
    {
        VerificationTier.UNVERIFIED.value: 0,
        VerificationTier.IDENTITY_VERIFIED.value: 1,
        VerificationTier.PROFILE_VERIFIED.value: 2,
        VerificationTier.CREDENTIALS_VERIFIED.value: 3,
        VerificationTier.STAFF_VERIFIED.value: 4,
    }
)

VERIFICATION_TIER_SCORE: Final[Mapping[str, float]] = MappingProxyType(
    {
        VerificationTier.UNVERIFIED.value: 0.0,
        VerificationTier.IDENTITY_VERIFIED.value: 40.0,
        VerificationTier.PROFILE_VERIFIED.value: 65.0,
        VerificationTier.CREDENTIALS_VERIFIED.value: 85.0,
        VerificationTier.STAFF_VERIFIED.value: 100.0,
    }
)


class VerificationDecision(StrEnum):
    GRANTED = "granted"
    REVOKED = "revoked"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AvailabilityStatus(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    OPEN_TO_OFFERS = "open_to_offers"
    CONTRACTED = "contracted"
    ON_TRIAL = "on_trial"
    INJURED = "injured"
    UNAVAILABLE = "unavailable"
    RETIRED = "retired"


DISCOVERABLE_AVAILABILITY: Final[frozenset[str]] = frozenset(
    {
        AvailabilityStatus.AVAILABLE.value,
        AvailabilityStatus.OPEN_TO_OFFERS.value,
        AvailabilityStatus.ON_TRIAL.value,
        AvailabilityStatus.CONTRACTED.value,
    }
)


class VisibilityState(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"
    SUSPENDED = "suspended"


class ModerationState(StrEnum):
    CLEAR = "clear"
    UNDER_REVIEW = "under_review"
    FLAGGED = "flagged"
    RESTRICTED = "restricted"


class ViewerScope(StrEnum):
    """Who is looking. Drives the privacy projection in `app.talent.privacy`."""

    PUBLIC = "public"
    SCOUT = "scout"
    OWNER = "owner"
    ADMIN = "admin"


class ShortlistEntryStatus(StrEnum):
    WATCHING = "watching"
    TARGET = "target"
    CONTACTED = "contacted"
    REJECTED = "rejected"


class ModerationAction(StrEnum):
    VERIFY = "verify"
    REVOKE_VERIFICATION = "revoke_verification"
    CORRECT = "correct"
    SUSPEND = "suspend"
    RESTORE = "restore"
    HIDE = "hide"
    PUBLISH = "publish"
    FEATURE = "feature"
    UNFEATURE = "unfeature"
    FLAG = "flag"
    CLEAR_FLAG = "clear_flag"


POSITION_CODES: Final[tuple[str, ...]] = (
    "GK",
    "CB",
    "LB",
    "RB",
    "LWB",
    "RWB",
    "DM",
    "CM",
    "AM",
    "LW",
    "RW",
    "ST",
)

POSITION_CODE_SET: Final[frozenset[str]] = frozenset(POSITION_CODES)

POSITION_FAMILY: Final[Mapping[str, str]] = MappingProxyType(
    {
        "GK": "goalkeeper",
        "CB": "defender",
        "LB": "defender",
        "RB": "defender",
        "LWB": "defender",
        "RWB": "defender",
        "DM": "midfielder",
        "CM": "midfielder",
        "AM": "midfielder",
        "LW": "forward",
        "RW": "forward",
        "ST": "forward",
    }
)

# Expected goal contributions per 90 minutes for an average professional in the
# family. Used only to normalise output so a striker is not rewarded (and a
# centre-back not punished) simply for the position they play.
POSITION_OUTPUT_BASELINE_PER_90: Final[Mapping[str, float]] = MappingProxyType(
    {
        "goalkeeper": 0.02,
        "defender": 0.10,
        "midfielder": 0.25,
        "forward": 0.50,
    }
)

TACTICAL_ROLES: Final[tuple[str, ...]] = (
    "sweeper_keeper",
    "shot_stopper",
    "ball_playing_defender",
    "stopper",
    "wide_centre_back",
    "inverted_fullback",
    "overlapping_fullback",
    "anchor",
    "deep_lying_playmaker",
    "box_to_box",
    "advanced_playmaker",
    "mezzala",
    "shadow_striker",
    "inside_forward",
    "touchline_winger",
    "target_forward",
    "pressing_forward",
    "poacher",
    "false_nine",
)

TACTICAL_ROLE_SET: Final[frozenset[str]] = frozenset(TACTICAL_ROLES)

PREFERRED_FOOT_VALUES: Final[frozenset[str]] = frozenset({"left", "right", "both"})

OUTFIELD_TECHNICAL_ATTRIBUTES: Final[tuple[str, ...]] = (
    "first_touch",
    "ball_control",
    "passing",
    "dribbling",
    "finishing",
    "crossing",
    "heading",
    "long_shots",
    "set_pieces",
    "tackling",
)

GOALKEEPER_TECHNICAL_ATTRIBUTES: Final[tuple[str, ...]] = (
    "handling",
    "reflexes",
    "shot_stopping",
    "distribution",
    "aerial_command",
    "one_on_ones",
    "footwork",
)

TACTICAL_ATTRIBUTES: Final[tuple[str, ...]] = (
    "positioning",
    "decision_making",
    "anticipation",
    "off_the_ball",
    "vision",
    "composure",
    "team_work",
    "concentration",
    "pressing_intelligence",
)

PHYSICAL_ATTRIBUTES: Final[tuple[str, ...]] = (
    "pace",
    "acceleration",
    "stamina",
    "strength",
    "agility",
    "balance",
    "jumping_reach",
    "durability",
)

ALL_ATTRIBUTE_KEYS: Final[frozenset[str]] = frozenset(
    OUTFIELD_TECHNICAL_ATTRIBUTES + GOALKEEPER_TECHNICAL_ATTRIBUTES + TACTICAL_ATTRIBUTES + PHYSICAL_ATTRIBUTES
)


def technical_attribute_keys(position_code: str | None) -> tuple[str, ...]:
    if (position_code or "").upper() == "GK":
        return GOALKEEPER_TECHNICAL_ATTRIBUTES
    return OUTFIELD_TECHNICAL_ATTRIBUTES


class CompetitionLevel(StrEnum):
    ELITE = "elite"
    TIER_1 = "tier1"
    TIER_2 = "tier2"
    TIER_3 = "tier3"
    TIER_4 = "tier4"
    SEMI_PRO = "semi_pro"
    AMATEUR = "amateur"
    YOUTH = "youth"
    UNKNOWN = "unknown"


COMPETITION_LEVEL_SCORE: Final[Mapping[str, float]] = MappingProxyType(
    {
        CompetitionLevel.ELITE.value: 100.0,
        CompetitionLevel.TIER_1.value: 88.0,
        CompetitionLevel.TIER_2.value: 74.0,
        CompetitionLevel.TIER_3.value: 60.0,
        CompetitionLevel.TIER_4.value: 48.0,
        CompetitionLevel.SEMI_PRO.value: 38.0,
        CompetitionLevel.AMATEUR.value: 28.0,
        CompetitionLevel.YOUTH.value: 26.0,
        CompetitionLevel.UNKNOWN.value: 40.0,
    }
)

NEUTRAL_COMPONENT_SCORE: Final[float] = 50.0

DECISIVE_MATCH_STAGES: Final[frozenset[str]] = frozenset(
    {
        "final",
        "grand_final",
        "semi_final",
        "semi-final",
        "quarter_final",
        "quarter-final",
        "round_of_16",
        "knockout",
        "playoff",
        "play-off",
        "play_off",
        "third_place",
        "promotion_playoff",
        "relegation_playoff",
    }
)


class TalentSignalCode(StrEnum):
    SUSTAINED_HIGH_PERFORMANCE = "sustained_high_performance"
    CLUTCH_PERFORMANCE = "clutch_performance"
    CONSISTENT_PERFORMER = "consistent_performer"
    VOLATILE_PERFORMER = "volatile_performer"
    POSITIONAL_EXCELLENCE = "positional_excellence"
    PROGRESSION = "progression"
    REGRESSION = "regression"
    ELITE_COMPETITION_EXPERIENCE = "elite_competition_experience"
    DISCIPLINARY_CONCERN = "disciplinary_concern"
    INJURY_AVAILABILITY_RISK = "injury_availability_risk"


SIGNAL_POLARITY: Final[Mapping[str, str]] = MappingProxyType(
    {
        TalentSignalCode.SUSTAINED_HIGH_PERFORMANCE.value: "positive",
        TalentSignalCode.CLUTCH_PERFORMANCE.value: "positive",
        TalentSignalCode.CONSISTENT_PERFORMER.value: "positive",
        TalentSignalCode.VOLATILE_PERFORMER.value: "negative",
        TalentSignalCode.POSITIONAL_EXCELLENCE.value: "positive",
        TalentSignalCode.PROGRESSION.value: "positive",
        TalentSignalCode.REGRESSION.value: "negative",
        TalentSignalCode.ELITE_COMPETITION_EXPERIENCE.value: "positive",
        TalentSignalCode.DISCIPLINARY_CONCERN.value: "negative",
        TalentSignalCode.INJURY_AVAILABILITY_RISK.value: "negative",
    }
)

# Signals that are legitimate scouting intelligence but are withheld from
# anonymous public traffic: publishing "disciplinary concern" to the open web
# about a named person is a reputational action, not a discovery feature.
RESTRICTED_SIGNAL_CODES: Final[frozenset[str]] = frozenset(
    {
        TalentSignalCode.DISCIPLINARY_CONCERN.value,
        TalentSignalCode.INJURY_AVAILABILITY_RISK.value,
        TalentSignalCode.VOLATILE_PERFORMER.value,
        TalentSignalCode.REGRESSION.value,
    }
)

# Search bounds. These are hard ceilings, not defaults, and are enforced in
# `app.talent.schemas` (request validation) and re-asserted in
# `app.talent.service` (defence in depth for non-HTTP callers).
SEARCH_DEFAULT_PAGE_SIZE: Final[int] = 20
SEARCH_MAX_PAGE_SIZE: Final[int] = 50
SEARCH_MAX_RESULT_WINDOW: Final[int] = 1000
SEARCH_MAX_FILTER_VALUES: Final[int] = 20
SEARCH_MIN_TEXT_LENGTH: Final[int] = 2
SEARCH_MAX_TEXT_LENGTH: Final[int] = 64
COMPARE_MAX_TALENTS: Final[int] = 6
SHORTLIST_MAX_ENTRIES: Final[int] = 500
SHORTLIST_MAX_PER_OWNER: Final[int] = 50

TALENT_SEARCH_SORTS: Final[frozenset[str]] = frozenset(
    {
        "ranking",
        "form",
        "age_asc",
        "age_desc",
        "competition_level",
        "recently_updated",
        "name",
    }
)


__all__ = [
    "ALL_ATTRIBUTE_KEYS",
    "AvailabilityStatus",
    "COMPARE_MAX_TALENTS",
    "COMPETITION_LEVEL_SCORE",
    "CompetitionLevel",
    "DECISIVE_MATCH_STAGES",
    "DISCOVERABLE_AVAILABILITY",
    "GOALKEEPER_TECHNICAL_ATTRIBUTES",
    "ModerationAction",
    "ModerationState",
    "NEUTRAL_COMPONENT_SCORE",
    "OUTFIELD_TECHNICAL_ATTRIBUTES",
    "PHYSICAL_ATTRIBUTES",
    "POSITION_CODES",
    "POSITION_CODE_SET",
    "POSITION_FAMILY",
    "POSITION_OUTPUT_BASELINE_PER_90",
    "PREFERRED_FOOT_VALUES",
    "RESTRICTED_SIGNAL_CODES",
    "SEARCH_DEFAULT_PAGE_SIZE",
    "SEARCH_MAX_FILTER_VALUES",
    "SEARCH_MAX_PAGE_SIZE",
    "SEARCH_MAX_RESULT_WINDOW",
    "SEARCH_MAX_TEXT_LENGTH",
    "SEARCH_MIN_TEXT_LENGTH",
    "SHORTLIST_MAX_ENTRIES",
    "SHORTLIST_MAX_PER_OWNER",
    "SIGNAL_POLARITY",
    "TACTICAL_ATTRIBUTES",
    "TACTICAL_ROLES",
    "TACTICAL_ROLE_SET",
    "TALENT_RANKING_CONFIG_VERSION",
    "TALENT_SEARCH_SORTS",
    "TALENT_SIGNAL_CONFIG_VERSION",
    "TalentSignalCode",
    "VERIFICATION_TIER_RANK",
    "VERIFICATION_TIER_SCORE",
    "VerificationDecision",
    "VerificationTier",
    "ViewerScope",
    "VisibilityState",
    "ShortlistEntryStatus",
    "technical_attribute_keys",
]
