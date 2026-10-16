from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.models.player_match_learning import MatchWeight, PlayerFeatureSnapshot, PlayerMatchEventType, UserPlayerEvent
from app.models.real_player_profile import RealPlayerProfile

DEFAULT_MATCH_WEIGHTS: dict[str, float] = {
    "history_position_bonus": 0.10,
    "history_country_bonus": 0.05,
    "history_foot_bonus": 0.03,
    "history_free_agent_bonus": 0.02,
    "max_adaptive_bonus": 0.20,
}
MATCH_WEIGHT_LIMITS: dict[str, tuple[float, float]] = {
    "history_position_bonus": (0.05, 0.15),
    "history_country_bonus": (0.02, 0.10),
    "history_foot_bonus": (0.01, 0.06),
    "history_free_agent_bonus": (0.00, 0.05),
}
MATCH_WEIGHT_TUNING_FACTORS: dict[str, str] = {
    "position": "history_position_bonus",
    "country": "history_country_bonus",
    "dominant_foot": "history_foot_bonus",
    "availability": "history_free_agent_bonus",
}
MATCH_WEIGHT_TUNING_MULTIPLIER = 0.05
MATCH_WEIGHT_MINIMUM_SAMPLE = 5
MATCH_PROFILE_MATURITY_SIGNAL = 12.0
TRACKED_PLAYER_MATCH_EVENT_TYPES = (
    PlayerMatchEventType.VIEWED,
    PlayerMatchEventType.SHORTLISTED,
    PlayerMatchEventType.SCOUTED,
    PlayerMatchEventType.CONTACTED,
)
PLAYER_MATCH_EVENT_WEIGHTS: dict[PlayerMatchEventType, int] = {
    PlayerMatchEventType.VIEWED: 1,
    PlayerMatchEventType.SHORTLISTED: 3,
    PlayerMatchEventType.SCOUTED: 5,
    PlayerMatchEventType.CONTACTED: 8,
}


class PlayerMatchLearningError(ValueError):
    pass


class PlayerMatchLearningNotFoundError(PlayerMatchLearningError):
    pass


class PlayerMatchLearningValidationError(PlayerMatchLearningError):
    pass


@dataclass(frozen=True, slots=True)
class PlayerLearningSnapshot:
    player_id: str
    position: str | None
    country: str | None
    age: int | None
    height_cm: int | None
    dominant_foot: str | None
    is_free_agent: bool
    current_club_name: str | None
    secondary_positions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlayerMatchPreferenceProfile:
    total_signal: float
    event_count: int
    position_preferences: dict[str, float]
    country_preferences: dict[str, float]
    foot_preferences: dict[str, float]
    availability_preferences: dict[str, float]
    average_age: float | None
    average_height_cm: float | None

    @property
    def signal_maturity(self) -> float:
        if self.total_signal <= 0:
            return 0.0
        return min(self.total_signal / MATCH_PROFILE_MATURITY_SIGNAL, 1.0)

    @property
    def has_history(self) -> bool:
        return self.total_signal > 0 and self.event_count > 0


@dataclass(slots=True)
class PlayerMatchLearningService:
    session: Session
    today: date | None = None

    def __post_init__(self) -> None:
        if self.today is None:
            self.today = date.today()

    def track_event(
        self,
        *,
        user_id: str,
        player_id: str,
        event_type: PlayerMatchEventType,
        filters: dict[str, Any] | None = None,
        match_score: float | None = None,
        reasons: list[str] | tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UserPlayerEvent:
        if event_type not in PLAYER_MATCH_EVENT_WEIGHTS:
            raise PlayerMatchLearningValidationError("Unsupported player match event.")
        if match_score is not None and match_score < 0:
            raise PlayerMatchLearningValidationError("match_score cannot be negative.")

        player = self.session.get(Player, player_id)
        if player is None:
            raise PlayerMatchLearningNotFoundError(f"player {player_id} was not found")

        profile = self._load_latest_profile(player_id)
        country = self.session.get(Country, player.country_id) if player.country_id else None
        snapshot = self.build_player_learning_snapshot(
            player,
            profile,
            country,
            today=self.today,
        )
        self._upsert_player_snapshot(snapshot)

        event = UserPlayerEvent(
            user_id=user_id,
            player_id=player_id,
            event_type=event_type.value,
            weight=PLAYER_MATCH_EVENT_WEIGHTS[event_type],
            filters_json=dict(filters or {}),
            match_score=match_score,
            reasons_json=list(reasons or ()),
            metadata_json=dict(metadata or {}),
        )
        self.session.add(event)
        self.session.flush()
        return event

    def build_user_profile(self, *, user_id: str) -> PlayerMatchPreferenceProfile:
        rows = self.session.execute(
            select(UserPlayerEvent, PlayerFeatureSnapshot)
            .join(PlayerFeatureSnapshot, PlayerFeatureSnapshot.player_id == UserPlayerEvent.player_id)
            .where(UserPlayerEvent.user_id == user_id)
            .order_by(UserPlayerEvent.created_at.desc())
        ).all()

        position_preferences: defaultdict[str, float] = defaultdict(float)
        country_preferences: defaultdict[str, float] = defaultdict(float)
        foot_preferences: defaultdict[str, float] = defaultdict(float)
        availability_preferences: defaultdict[str, float] = defaultdict(float)
        total_signal = 0.0
        age_weight = 0.0
        age_total = 0.0
        height_weight = 0.0
        height_total = 0.0

        for event, snapshot in rows:
            signal_weight = float(event.weight or 0)
            if signal_weight <= 0:
                continue
            total_signal += signal_weight
            if snapshot.position:
                position_preferences[snapshot.position] += signal_weight
            if snapshot.country:
                country_preferences[snapshot.country] += signal_weight
            if snapshot.dominant_foot:
                foot_preferences[snapshot.dominant_foot] += signal_weight
            if snapshot.is_free_agent:
                availability_preferences["free_agent"] += signal_weight
            if snapshot.age is not None:
                age_total += snapshot.age * signal_weight
                age_weight += signal_weight
            if snapshot.height_cm is not None:
                height_total += snapshot.height_cm * signal_weight
                height_weight += signal_weight

        return PlayerMatchPreferenceProfile(
            total_signal=round(total_signal, 2),
            event_count=len(rows),
            position_preferences=dict(sorted(position_preferences.items(), key=lambda item: (-item[1], item[0]))),
            country_preferences=dict(sorted(country_preferences.items(), key=lambda item: (-item[1], item[0]))),
            foot_preferences=dict(sorted(foot_preferences.items(), key=lambda item: (-item[1], item[0]))),
            availability_preferences=dict(sorted(availability_preferences.items(), key=lambda item: (-item[1], item[0]))),
            average_age=round(age_total / age_weight, 2) if age_weight > 0 else None,
            average_height_cm=round(height_total / height_weight, 2) if height_weight > 0 else None,
        )

    def get_weight_map(self) -> dict[str, float]:
        weights = dict(DEFAULT_MATCH_WEIGHTS)
        rows = self.session.scalars(select(MatchWeight).order_by(MatchWeight.factor.asc())).all()
        for row in rows:
            weights[row.factor] = float(row.weight)
        return weights

    def build_profile_payload(self, *, user_id: str) -> dict[str, Any]:
        profile = self.build_user_profile(user_id=user_id)
        weight_map = self.get_weight_map()
        return {
            "total_signal": profile.total_signal,
            "signal_maturity": round(profile.signal_maturity, 4),
            "event_count": profile.event_count,
            "position_preferences": profile.position_preferences,
            "country_preferences": profile.country_preferences,
            "foot_preferences": profile.foot_preferences,
            "availability_preferences": profile.availability_preferences,
            "average_age": profile.average_age,
            "average_height_cm": profile.average_height_cm,
            "weights": self._serialize_weight_map(weight_map),
        }

    def build_admin_summary(self, *, since_days: int = 30) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        rows = self.session.execute(
            select(UserPlayerEvent, PlayerFeatureSnapshot)
            .outerjoin(PlayerFeatureSnapshot, PlayerFeatureSnapshot.player_id == UserPlayerEvent.player_id)
            .where(UserPlayerEvent.created_at >= since)
            .order_by(UserPlayerEvent.created_at.desc())
        ).all()

        funnel_counter: Counter[str] = Counter()
        score_totals: defaultdict[str, list[float]] = defaultdict(list)
        contacted_positions: Counter[str] = Counter()
        contacted_countries: Counter[str] = Counter()
        contacted_ages: list[int] = []

        for event, snapshot in rows:
            funnel_counter[event.event_type] += 1
            if event.match_score is not None:
                score_totals[event.event_type].append(float(event.match_score))
            if event.event_type != PlayerMatchEventType.CONTACTED.value or snapshot is None:
                continue
            if snapshot.position:
                contacted_positions[snapshot.position] += 1
            if snapshot.country:
                contacted_countries[snapshot.country] += 1
            if snapshot.age is not None:
                contacted_ages.append(snapshot.age)

        return {
            "since": since,
            "funnel": [
                {"event": event_type.value, "count": int(funnel_counter.get(event_type.value, 0))}
                for event_type in TRACKED_PLAYER_MATCH_EVENT_TYPES
            ],
            "score_effectiveness": [
                {
                    "event": event_type.value,
                    "average_score": round(sum(values) / len(values), 4) if values else None,
                }
                for event_type, values in (
                    (PlayerMatchEventType.VIEWED, score_totals.get(PlayerMatchEventType.VIEWED.value, [])),
                    (PlayerMatchEventType.SHORTLISTED, score_totals.get(PlayerMatchEventType.SHORTLISTED.value, [])),
                    (PlayerMatchEventType.SCOUTED, score_totals.get(PlayerMatchEventType.SCOUTED.value, [])),
                    (PlayerMatchEventType.CONTACTED, score_totals.get(PlayerMatchEventType.CONTACTED.value, [])),
                )
            ],
            "top_positions": self._serialize_counter(contacted_positions),
            "top_countries": self._serialize_counter(contacted_countries),
            "age_buckets": self._serialize_counter(Counter(self._age_bucket(age) for age in contacted_ages if age is not None)),
            "weights": self._serialize_weight_map(self.get_weight_map()),
        }

    def refresh_weights(self) -> dict[str, Any]:
        rows = self.session.execute(
            select(UserPlayerEvent, PlayerFeatureSnapshot)
            .join(PlayerFeatureSnapshot, PlayerFeatureSnapshot.player_id == UserPlayerEvent.player_id)
            .where(UserPlayerEvent.event_type.in_([event_type.value for event_type in TRACKED_PLAYER_MATCH_EVENT_TYPES]))
        ).all()

        updated_weights = dict(DEFAULT_MATCH_WEIGHTS)
        for attribute, weight_factor in MATCH_WEIGHT_TUNING_FACTORS.items():
            viewed_values = self._extract_trait_values(rows, event_type=PlayerMatchEventType.VIEWED, attribute=attribute)
            contacted_values = self._extract_trait_values(rows, event_type=PlayerMatchEventType.CONTACTED, attribute=attribute)
            minimum, maximum = MATCH_WEIGHT_LIMITS[weight_factor]
            default_weight = DEFAULT_MATCH_WEIGHTS[weight_factor]
            if len(viewed_values) < MATCH_WEIGHT_MINIMUM_SAMPLE or len(contacted_values) < MATCH_WEIGHT_MINIMUM_SAMPLE:
                updated_weights[weight_factor] = default_weight
                continue
            delta = self._distribution_concentration(contacted_values) - self._distribution_concentration(viewed_values)
            updated_weights[weight_factor] = round(self._clamp(default_weight + (delta * MATCH_WEIGHT_TUNING_MULTIPLIER), minimum, maximum), 4)

        for factor, weight in updated_weights.items():
            row = self.session.scalar(select(MatchWeight).where(MatchWeight.factor == factor))
            if row is None:
                row = MatchWeight(factor=factor, weight=weight, metadata_json={"source": "adaptive_player_matching_v1"})
                self.session.add(row)
            else:
                row.weight = weight
                row.metadata_json = {"source": "adaptive_player_matching_v1"}
        self.session.flush()
        return {"weights": self._serialize_weight_map(self.get_weight_map())}

    @staticmethod
    def build_player_learning_snapshot(
        player: Player,
        profile: RealPlayerProfile | None,
        country: Country | None,
        *,
        today: date | None,
    ) -> PlayerLearningSnapshot:
        position = PlayerMatchLearningService._normalize_value(
            (profile.primary_position if profile is not None else None)
            or player.normalized_position
            or player.position
        )
        country_token = PlayerMatchLearningService._normalize_value(
            (country.name if country is not None else None)
            or (profile.nationality if profile is not None else None)
        )
        date_of_birth = player.date_of_birth or (profile.date_of_birth if profile is not None else None)
        current_club_name = (profile.current_club_name if profile is not None else None) or player.real_world_club_name
        secondary_positions = tuple(
            token
            for token in (
                PlayerMatchLearningService._normalize_value(item)
                for item in (profile.secondary_positions_json if profile is not None else ())
            )
            if token is not None
        )
        return PlayerLearningSnapshot(
            player_id=player.id,
            position=position,
            country=country_token,
            age=PlayerMatchLearningService._player_age(date_of_birth, today=today),
            height_cm=(profile.height_cm if profile is not None else None) or player.height_cm,
            dominant_foot=PlayerMatchLearningService._normalize_value(
                (profile.dominant_foot if profile is not None else None) or player.preferred_foot
            ),
            is_free_agent=PlayerMatchLearningService._is_free_agent_club(current_club_name),
            current_club_name=current_club_name,
            secondary_positions=secondary_positions,
        )

    @staticmethod
    def calculate_adaptive_bonus(
        *,
        snapshot: PlayerLearningSnapshot,
        profile: PlayerMatchPreferenceProfile | None,
        weight_map: dict[str, float] | None,
    ) -> tuple[float, list[str]]:
        if profile is None or not profile.has_history:
            return 0.0, []

        resolved_weights = dict(DEFAULT_MATCH_WEIGHTS)
        resolved_weights.update(weight_map or {})
        bonus = 0.0
        reasons: list[str] = []

        position_bonus = PlayerMatchLearningService._profile_bonus(
            preferences=profile.position_preferences,
            trait=snapshot.position,
            total_signal=profile.total_signal,
            maturity=profile.signal_maturity,
            max_bonus=resolved_weights["history_position_bonus"],
        )
        if position_bonus >= 0.01:
            bonus += position_bonus
            reasons.append("Matches your scouting history")

        country_bonus = PlayerMatchLearningService._profile_bonus(
            preferences=profile.country_preferences,
            trait=snapshot.country,
            total_signal=profile.total_signal,
            maturity=profile.signal_maturity,
            max_bonus=resolved_weights["history_country_bonus"],
        )
        if country_bonus >= 0.01:
            bonus += country_bonus
            reasons.append("Preferred scouting region")

        foot_bonus = PlayerMatchLearningService._profile_bonus(
            preferences=profile.foot_preferences,
            trait=snapshot.dominant_foot,
            total_signal=profile.total_signal,
            maturity=profile.signal_maturity,
            max_bonus=resolved_weights["history_foot_bonus"],
        )
        if foot_bonus >= 0.01:
            bonus += foot_bonus
            reasons.append("Fits your tracked foot preference")

        availability_bonus = 0.0
        if snapshot.is_free_agent:
            availability_bonus = PlayerMatchLearningService._profile_bonus(
                preferences=profile.availability_preferences,
                trait="free_agent",
                total_signal=profile.total_signal,
                maturity=profile.signal_maturity,
                max_bonus=resolved_weights["history_free_agent_bonus"],
            )
        if availability_bonus >= 0.01:
            bonus += availability_bonus
            reasons.append("Aligned with your availability pattern")

        bonus = min(bonus, resolved_weights["max_adaptive_bonus"])
        return round(bonus, 4), reasons

    def _load_latest_profile(self, player_id: str) -> RealPlayerProfile | None:
        return self.session.scalar(
            select(RealPlayerProfile)
            .where(RealPlayerProfile.gtex_player_id == player_id)
            .order_by(
                RealPlayerProfile.source_last_refreshed_at.is_(None),
                RealPlayerProfile.source_last_refreshed_at.desc(),
                RealPlayerProfile.updated_at.desc(),
                RealPlayerProfile.id.desc(),
            )
        )

    def _upsert_player_snapshot(self, snapshot: PlayerLearningSnapshot) -> PlayerFeatureSnapshot:
        existing = self.session.get(PlayerFeatureSnapshot, snapshot.player_id)
        if existing is None:
            existing = PlayerFeatureSnapshot(player_id=snapshot.player_id)
            self.session.add(existing)
        existing.position = snapshot.position
        existing.country = snapshot.country
        existing.age = snapshot.age
        existing.height_cm = snapshot.height_cm
        existing.dominant_foot = snapshot.dominant_foot
        existing.is_free_agent = snapshot.is_free_agent
        existing.current_club_name = snapshot.current_club_name
        existing.secondary_positions_json = list(snapshot.secondary_positions)
        self.session.flush()
        return existing

    def _extract_trait_values(
        self,
        rows: list[tuple[UserPlayerEvent, PlayerFeatureSnapshot]],
        *,
        event_type: PlayerMatchEventType,
        attribute: str,
    ) -> list[str]:
        values: list[str] = []
        for event, snapshot in rows:
            if event.event_type != event_type.value:
                continue
            value = self._snapshot_trait_value(snapshot, attribute=attribute)
            if value is None:
                continue
            values.append(value)
        return values

    def _snapshot_trait_value(self, snapshot: PlayerFeatureSnapshot, *, attribute: str) -> str | None:
        if attribute == "availability":
            return "free_agent" if snapshot.is_free_agent else "signed"
        raw_value = getattr(snapshot, attribute, None)
        if raw_value is None:
            return None
        normalized = self._normalize_value(str(raw_value))
        return normalized

    @staticmethod
    def _distribution_concentration(values: list[str]) -> float:
        if not values:
            return 0.0
        counts = Counter(values)
        total = float(sum(counts.values()))
        return sum((count / total) ** 2 for count in counts.values())

    @staticmethod
    def _serialize_counter(counter: Counter[str], *, limit: int = 5) -> list[dict[str, Any]]:
        return [
            {"label": label, "count": int(count)}
            for label, count in counter.most_common(limit)
        ]

    @staticmethod
    def _serialize_weight_map(weight_map: dict[str, float]) -> list[dict[str, Any]]:
        return [
            {"factor": factor, "weight": round(float(weight), 4)}
            for factor, weight in sorted(weight_map.items())
        ]

    @staticmethod
    def _profile_bonus(
        *,
        preferences: dict[str, float],
        trait: str | None,
        total_signal: float,
        maturity: float,
        max_bonus: float,
    ) -> float:
        if trait is None or total_signal <= 0 or maturity <= 0:
            return 0.0
        trait_weight = float(preferences.get(trait, 0.0))
        if trait_weight <= 0:
            return 0.0
        return max_bonus * (trait_weight / total_signal) * maturity

    @staticmethod
    def _age_bucket(age: int) -> str:
        if age < 20:
            return "under_20"
        if age < 24:
            return "20_23"
        if age < 28:
            return "24_27"
        if age < 32:
            return "28_31"
        return "32_plus"

    @staticmethod
    def _normalize_value(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        return cleaned or None

    @staticmethod
    def _is_free_agent_club(club_name: str | None) -> bool:
        normalized = PlayerMatchLearningService._normalize_value(club_name)
        return normalized in {"", "free agent", "free-agent", "unattached"}

    @staticmethod
    def _player_age(date_of_birth: date | None, *, today: date | None) -> int | None:
        if date_of_birth is None or today is None:
            return None
        age = today.year - date_of_birth.year
        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1
        return age

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
