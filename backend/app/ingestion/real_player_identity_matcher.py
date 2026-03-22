from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Player
from app.models.real_player_source_link import RealPlayerSourceLink
from app.schemas.real_player_ingestion import RealPlayerSeedInput

from .real_player_identity_normalizer import (
    names_equivalent,
    normalize_identity_name,
)


_POSITION_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


class AmbiguousRealPlayerMatchError(ValueError):
    def __init__(
        self,
        canonical_name: str,
        candidates: tuple["RealPlayerMatchCandidate", ...],
        *,
        reason: str = "ambiguous_candidates",
    ) -> None:
        self.canonical_name = canonical_name
        self.candidates = candidates
        self.reason = reason
        super().__init__(f"Ambiguous identity match for '{canonical_name}'.")


@dataclass(frozen=True, slots=True)
class RealPlayerMatchCandidate:
    player_id: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RealPlayerMatchResult:
    action: str
    player_id: str | None
    confidence_score: float
    candidates: tuple[RealPlayerMatchCandidate, ...] = ()


@dataclass(slots=True)
class RealPlayerIdentityMatcher:
    confident_match_threshold: float = 0.82
    ambiguous_match_threshold: float = 0.68
    ambiguity_margin: float = 0.12

    def match(self, session: Session, payload: RealPlayerSeedInput) -> RealPlayerMatchResult:
        source_link = session.scalar(
            select(RealPlayerSourceLink).where(
                RealPlayerSourceLink.source_name == payload.source_name,
                RealPlayerSourceLink.source_player_key == payload.source_player_key,
            )
        )
        if source_link is not None:
            confidence = max(float(source_link.identity_confidence_score or 0.0), 0.99)
            return RealPlayerMatchResult(
                action="source_link",
                player_id=source_link.gtex_player_id,
                confidence_score=round(confidence, 4),
            )

        if not any(self._name_variants(payload)):
            return RealPlayerMatchResult(action="create_new", player_id=None, confidence_score=self._create_score(payload))

        candidates = self._load_candidates(session, payload)
        ranked = tuple(sorted((self._score_candidate(player, payload) for player in candidates), key=lambda item: (-item.score, item.player_id)))
        if not ranked:
            return RealPlayerMatchResult(action="create_new", player_id=None, confidence_score=self._create_score(payload))

        top_candidate = ranked[0]
        second_candidate = ranked[1] if len(ranked) > 1 else None
        if (
            top_candidate.score >= self.confident_match_threshold
            and (second_candidate is None or (top_candidate.score - second_candidate.score) >= self.ambiguity_margin)
        ):
            return RealPlayerMatchResult(
                action="matched_existing",
                player_id=top_candidate.player_id,
                confidence_score=top_candidate.score,
                candidates=ranked,
            )
        if top_candidate.score >= self.ambiguous_match_threshold:
            raise AmbiguousRealPlayerMatchError(payload.canonical_name, ranked)
        return RealPlayerMatchResult(action="create_new", player_id=None, confidence_score=self._create_score(payload), candidates=ranked)

    def _score_candidate(self, player: Player, payload: RealPlayerSeedInput) -> RealPlayerMatchCandidate:
        score = 0.0
        reasons: list[str] = []

        payload_canonical = normalize_identity_name(payload.canonical_name)
        payload_aliases = tuple(
            normalize_identity_name(value)
            for value in payload.known_aliases
            if normalize_identity_name(value).tokens
        )
        candidate_primary_names = tuple(
            normalized
            for normalized in (
                normalize_identity_name(player.full_name),
                normalize_identity_name(player.canonical_display_name),
            )
            if normalized.tokens
        )
        candidate_aliases = tuple(
            normalized
            for normalized in (
                normalize_identity_name(player.short_name),
            )
            if normalized.tokens
        )
        if payload_canonical.tokens and any(
            names_equivalent(payload_canonical.normalized, candidate_name.normalized)
            for candidate_name in candidate_primary_names
        ):
            score += 0.62
            reasons.append("exact_normalized_name")
        elif payload_canonical.tokens and any(
            names_equivalent(payload_canonical.normalized, candidate_alias.normalized)
            for candidate_alias in candidate_aliases
        ):
            score += 0.52
            reasons.append("alias_name")
        elif any(
            names_equivalent(payload_alias.normalized, candidate_name.normalized)
            for payload_alias in payload_aliases
            for candidate_name in (*candidate_primary_names, *candidate_aliases)
        ):
            score += 0.52
            reasons.append("alias_name")

        if payload.date_of_birth is not None and player.date_of_birth == payload.date_of_birth:
            score += 0.20
            reasons.append("date_of_birth")
        elif payload.birth_year is not None and player.date_of_birth is not None and player.date_of_birth.year == payload.birth_year:
            score += 0.12
            reasons.append("birth_year")

        if self._country_matches(player, payload):
            score += 0.08
            reasons.append("nationality")

        if self._club_matches(player, payload):
            score += 0.07
            reasons.append("club")

        if self._position_matches(player, payload):
            score += 0.06
            reasons.append("position")

        if bool(player.is_real_player):
            score += 0.05
            reasons.append("existing_real_player")

        return RealPlayerMatchCandidate(
            player_id=player.id,
            score=round(min(score, 0.99), 4),
            reasons=tuple(reasons),
        )

    def _load_candidates(self, session: Session, payload: RealPlayerSeedInput) -> list[Player]:
        players_by_id: dict[str, Player] = {}
        for player in self._load_exact_name_candidates(session, payload):
            players_by_id[player.id] = player
        for player in self._load_normalized_primary_name_candidates(
            session,
            payload,
            exclude_ids=set(players_by_id),
        ):
            players_by_id[player.id] = player
        if not players_by_id:
            for player in self._load_alias_candidates(
                session,
                payload,
                exclude_ids=set(players_by_id),
            ):
                players_by_id[player.id] = player
        for player in self._load_anchored_candidates(session, payload):
            players_by_id[player.id] = player
        return list(players_by_id.values())

    def _load_exact_name_candidates(self, session: Session, payload: RealPlayerSeedInput) -> list[Player]:
        search_terms = {term for term in self._name_variants(payload) if term}
        if not search_terms:
            return []
        lowered_terms = {term.lower() for term in search_terms}
        statement = self._candidate_statement().where(
            or_(
                func.lower(Player.full_name).in_(lowered_terms),
                func.lower(func.coalesce(Player.short_name, "")).in_(lowered_terms),
                func.lower(func.coalesce(Player.canonical_display_name, "")).in_(lowered_terms),
            )
        )
        return list(session.scalars(statement))

    def _load_normalized_primary_name_candidates(
        self,
        session: Session,
        payload: RealPlayerSeedInput,
        *,
        exclude_ids: set[str],
    ) -> list[Player]:
        payload_name = normalize_identity_name(payload.canonical_name)
        if not payload_name.tokens:
            return []
        return [
            player
            for player in session.scalars(self._candidate_statement())
            if player.id not in exclude_ids
            and any(
                names_equivalent(payload_name.normalized, candidate_name.normalized)
                for candidate_name in (
                    normalize_identity_name(player.full_name),
                    normalize_identity_name(player.canonical_display_name),
                )
                if candidate_name.tokens
            )
        ]

    def _load_alias_candidates(
        self,
        session: Session,
        payload: RealPlayerSeedInput,
        *,
        exclude_ids: set[str],
    ) -> list[Player]:
        payload_canonical = normalize_identity_name(payload.canonical_name)
        payload_aliases = tuple(
            normalize_identity_name(value)
            for value in payload.known_aliases
            if normalize_identity_name(value).tokens
        )
        if not payload_canonical.tokens and not payload_aliases:
            return []
        return [
            player
            for player in session.scalars(self._candidate_statement())
            if player.id not in exclude_ids
            and self._matches_alias(payload_canonical, payload_aliases, player)
        ]

    def _load_anchored_candidates(self, session: Session, payload: RealPlayerSeedInput) -> list[Player]:
        statement = None
        if payload.date_of_birth is not None and (payload.nationality or payload.nationality_code):
            statement = self._candidate_statement().where(Player.date_of_birth == payload.date_of_birth)
        elif payload.birth_year is not None and (payload.nationality or payload.nationality_code) and payload.current_real_world_club:
            statement = self._candidate_statement().where(
                Player.date_of_birth.is_not(None),
                extract("year", Player.date_of_birth) == payload.birth_year,
            )
        if statement is None:
            return []
        return [
            player
            for player in session.scalars(statement)
            if self._candidate_matches_anchor(player, payload)
        ]

    def _candidate_statement(self):
        return select(Player).options(
            selectinload(Player.country),
            selectinload(Player.current_club),
        )

    def _candidate_matches_anchor(self, player: Player, payload: RealPlayerSeedInput) -> bool:
        if payload.date_of_birth is not None:
            return self._country_matches(player, payload)
        return self._country_matches(player, payload) and self._club_matches(player, payload)

    def _matches_alias(
        self,
        payload_canonical,
        payload_aliases,
        player: Player,
    ) -> bool:
        candidate_primary_names = tuple(
            normalized
            for normalized in (
                normalize_identity_name(player.full_name),
                normalize_identity_name(player.canonical_display_name),
            )
            if normalized.tokens
        )
        candidate_aliases = tuple(
            normalized
            for normalized in (
                normalize_identity_name(player.short_name),
            )
            if normalized.tokens
        )
        if payload_canonical.tokens and any(
            names_equivalent(payload_canonical.normalized, candidate_alias.normalized)
            for candidate_alias in candidate_aliases
        ):
            return True
        return any(
            names_equivalent(payload_alias.normalized, candidate_name.normalized)
            for payload_alias in payload_aliases
            for candidate_name in (*candidate_primary_names, *candidate_aliases)
        )

    def _country_matches(self, player: Player, payload: RealPlayerSeedInput) -> bool:
        candidate_values = {
            self._normalize_name(getattr(player.country, "name", None)),
            self._normalize_name(getattr(player.country, "alpha2_code", None)),
            self._normalize_name(getattr(player.country, "alpha3_code", None)),
            self._normalize_name(getattr(player.country, "fifa_code", None)),
        }
        payload_values = {
            self._normalize_name(payload.nationality),
            self._normalize_name(payload.nationality_code),
        }
        candidate_values.discard("")
        payload_values.discard("")
        return bool(candidate_values and payload_values and candidate_values.intersection(payload_values))

    def _club_matches(self, player: Player, payload: RealPlayerSeedInput) -> bool:
        candidate_values = {
            self._normalize_name(player.real_world_club_name),
            self._normalize_name(getattr(player.current_club, "name", None)),
        }
        candidate_values.discard("")
        payload_club = self._normalize_name(payload.current_real_world_club)
        return bool(payload_club and payload_club in candidate_values)

    def _position_matches(self, player: Player, payload: RealPlayerSeedInput) -> bool:
        input_position = self._canonical_position(payload.primary_position)
        player_position = self._canonical_position(player.position)
        if input_position and player_position and input_position == player_position:
            return True
        return self._position_family(payload.primary_position) == self._position_family(player.normalized_position or player.position)

    def _name_variants(self, payload: RealPlayerSeedInput) -> tuple[str, ...]:
        variants = [payload.canonical_name, *payload.known_aliases]
        return tuple(value for value in variants if value)

    def _create_score(self, payload: RealPlayerSeedInput) -> float:
        base_score = float(payload.identity_confidence_score or 0.88)
        if payload.date_of_birth is not None:
            base_score += 0.04
        elif payload.birth_year is not None:
            base_score += 0.02
        return round(min(base_score, 0.96), 4)

    @staticmethod
    def _normalize_name(value: str | None) -> str:
        return normalize_identity_name(value).normalized

    def _token_signature(self, value: str | None) -> str:
        return normalize_identity_name(value).token_signature

    @staticmethod
    def _canonical_position(value: str | None) -> str:
        normalized = _POSITION_NON_ALNUM_RE.sub("_", (value or "").lower()).strip("_")
        if normalized in {"gk", "goalkeeper"}:
            return "goalkeeper"
        if normalized in {"dm", "cdm", "defensive_midfielder"}:
            return "defensive_midfielder"
        if normalized in {"cm", "midfielder", "central_midfielder"}:
            return "central_midfielder"
        if normalized in {"am", "cam", "attacking_midfielder"}:
            return "attacking_midfielder"
        if normalized in {"cb", "centre_back", "center_back"} or "back" in normalized or "def" in normalized:
            return "defender"
        if normalized in {"winger", "lw", "rw"} or "wing" in normalized:
            return "winger"
        if normalized in {"st", "cf", "striker", "forward"}:
            return "striker"
        return normalized

    def _position_family(self, value: str | None) -> str:
        canonical = self._canonical_position(value)
        if canonical == "goalkeeper":
            return "goalkeeper"
        if canonical in {"defender", "full_back"}:
            return "defender"
        if canonical in {"winger", "striker"}:
            return "forward"
        return "midfielder"


__all__ = [
    "AmbiguousRealPlayerMatchError",
    "RealPlayerIdentityMatcher",
    "RealPlayerMatchCandidate",
    "RealPlayerMatchResult",
]
