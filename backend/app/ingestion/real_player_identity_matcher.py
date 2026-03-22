from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Player
from app.models.real_player_source_link import RealPlayerSourceLink
from app.schemas.real_player_ingestion import RealPlayerSeedInput


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


class AmbiguousRealPlayerMatchError(ValueError):
    def __init__(self, canonical_name: str, candidates: tuple["RealPlayerMatchCandidate", ...]) -> None:
        self.canonical_name = canonical_name
        self.candidates = candidates
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

        search_terms = {term for term in self._name_variants(payload) if term}
        if not search_terms:
            return RealPlayerMatchResult(action="create_new", player_id=None, confidence_score=self._create_score(payload))

        lowered_terms = {term.lower() for term in search_terms}
        statement = (
            select(Player)
            .options(
                selectinload(Player.country),
                selectinload(Player.current_club),
            )
            .where(
                or_(
                    func.lower(Player.full_name).in_(lowered_terms),
                    func.lower(func.coalesce(Player.short_name, "")).in_(lowered_terms),
                    func.lower(func.coalesce(Player.canonical_display_name, "")).in_(lowered_terms),
                )
            )
        )
        candidates = list(session.scalars(statement))
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

        payload_names = {self._normalize_name(value) for value in self._name_variants(payload)}
        candidate_names = {
            self._normalize_name(player.full_name),
            self._normalize_name(player.short_name),
            self._normalize_name(player.canonical_display_name),
        }
        candidate_names.discard("")
        if payload_names.intersection(candidate_names):
            score += 0.62
            reasons.append("name")
        elif self._token_signature(payload.canonical_name) == self._token_signature(player.full_name):
            score += 0.40
            reasons.append("token_signature")

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
        if value is None:
            return ""
        folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        return _NON_ALNUM_RE.sub(" ", folded.lower()).strip()

    def _token_signature(self, value: str | None) -> str:
        normalized = self._normalize_name(value)
        if not normalized:
            return ""
        return "|".join(sorted(normalized.split()))

    @staticmethod
    def _canonical_position(value: str | None) -> str:
        normalized = _NON_ALNUM_RE.sub("_", (value or "").lower()).strip("_")
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
