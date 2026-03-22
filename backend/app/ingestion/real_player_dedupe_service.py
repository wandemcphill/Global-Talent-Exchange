from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Player
from app.models.real_player_import_batch import RealPlayerImportRow
from app.models.real_player_source_link import RealPlayerSourceLink
from app.schemas.real_player_ingestion import RealPlayerSeedInput

from .real_player_identity_normalizer import (
    NormalizedRealPlayerIdentity,
    canonical_position_key,
    names_equivalent,
    normalize_identity_name,
    normalize_preferred_foot,
    normalize_real_player_identity,
    position_family,
)


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
class RealPlayerDedupeService:
    confident_match_threshold: float = 0.82
    ambiguous_match_threshold: float = 0.68
    ambiguity_margin: float = 0.12

    def match(
        self,
        session: Session,
        payload: RealPlayerSeedInput,
        *,
        normalized_identity: NormalizedRealPlayerIdentity | None = None,
    ) -> RealPlayerMatchResult:
        identity = normalized_identity or normalize_real_player_identity(
            payload,
            as_of=(payload.source_last_refreshed_at.date() if payload.source_last_refreshed_at is not None else date.today()),
        )

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

        import_row_result = self._match_existing_import_row(session, identity)
        if import_row_result is not None:
            return import_row_result

        strong_result = self._match_strong_player_identity(session, identity)
        if strong_result is not None:
            return strong_result

        candidates = self._load_candidates(session, identity)
        ranked = tuple(
            sorted(
                (
                    self._score_candidate(player, identity)
                    for player in candidates
                ),
                key=lambda item: (-item.score, item.player_id),
            )
        )
        if not ranked:
            return RealPlayerMatchResult(
                action="create_new",
                player_id=None,
                confidence_score=self._create_score(identity),
            )

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
            raise AmbiguousRealPlayerMatchError(identity.canonical_name, ranked)
        return RealPlayerMatchResult(
            action="create_new",
            player_id=None,
            confidence_score=self._create_score(identity),
            candidates=ranked,
        )

    def _match_existing_import_row(
        self,
        session: Session,
        identity: NormalizedRealPlayerIdentity,
    ) -> RealPlayerMatchResult | None:
        rows = list(
            session.scalars(
                select(RealPlayerImportRow)
                .where(
                    RealPlayerImportRow.source_name == identity.source_name,
                    RealPlayerImportRow.source_player_key == identity.source_player_key,
                    RealPlayerImportRow.review_status == "resolved",
                    RealPlayerImportRow.gtex_player_id.is_not(None),
                )
                .order_by(RealPlayerImportRow.processed_at.desc(), RealPlayerImportRow.updated_at.desc())
            )
        )
        player_ids = tuple(dict.fromkeys(row.gtex_player_id for row in rows if row.gtex_player_id))
        if not player_ids:
            return None
        if len(player_ids) == 1:
            return RealPlayerMatchResult(
                action="matched_existing",
                player_id=player_ids[0],
                confidence_score=0.99,
            )
        raise AmbiguousRealPlayerMatchError(
            identity.canonical_name,
            self._rank_candidates(session, player_ids, identity, base_reason="historical_source_key", base_score=0.99),
            reason="historical_source_key_collision",
        )

    def _match_strong_player_identity(
        self,
        session: Session,
        identity: NormalizedRealPlayerIdentity,
    ) -> RealPlayerMatchResult | None:
        for reason, score, player_ids in (
            ("exact_identity_key", 0.98, self._player_ids_for_import_row_key(session, RealPlayerImportRow.exact_identity_key, identity.exact_identity_key)),
            ("name_birthyear_club_key", 0.94, self._player_ids_for_import_row_key(session, RealPlayerImportRow.name_birthyear_club_key, identity.name_birthyear_club_key)),
            ("name_birthyear_nationality_key", 0.90, self._player_ids_for_import_row_key(session, RealPlayerImportRow.name_birthyear_nationality_key, identity.name_birthyear_nationality_key)),
            ("exact_name_dob", 0.96, self._player_ids_for_exact_name_dob(session, identity)),
            ("name_birthyear_club_anchor", 0.92, self._player_ids_for_birthyear_anchor(session, identity, require_club=True)),
            ("name_birthyear_nationality_anchor", 0.88, self._player_ids_for_birthyear_anchor(session, identity, require_club=False)),
        ):
            if not player_ids:
                continue
            if len(player_ids) == 1:
                return RealPlayerMatchResult(
                    action="matched_existing",
                    player_id=player_ids[0],
                    confidence_score=score,
                    candidates=self._rank_candidates(session, player_ids, identity, base_reason=reason, base_score=score),
                )
            raise AmbiguousRealPlayerMatchError(
                identity.canonical_name,
                self._rank_candidates(session, player_ids, identity, base_reason=reason, base_score=score),
                reason=f"{reason}_collision",
            )
        return None

    def _player_ids_for_import_row_key(self, session: Session, column, key: str | None) -> tuple[str, ...]:
        if not key:
            return ()
        rows = list(
            session.scalars(
                select(RealPlayerImportRow)
                .where(
                    column == key,
                    RealPlayerImportRow.review_status == "resolved",
                    RealPlayerImportRow.gtex_player_id.is_not(None),
                )
                .order_by(RealPlayerImportRow.processed_at.desc(), RealPlayerImportRow.updated_at.desc())
            )
        )
        return tuple(dict.fromkeys(row.gtex_player_id for row in rows if row.gtex_player_id))

    def _player_ids_for_exact_name_dob(self, session: Session, identity: NormalizedRealPlayerIdentity) -> tuple[str, ...]:
        if identity.date_of_birth is None:
            return ()
        search_terms = self._search_terms(identity)
        if not search_terms:
            return ()
        lowered_terms = {term.lower() for term in search_terms}
        players = list(
            session.scalars(
                self._candidate_statement().where(
                    Player.date_of_birth == identity.date_of_birth,
                    or_(
                        func.lower(Player.full_name).in_(lowered_terms),
                        func.lower(func.coalesce(Player.short_name, "")).in_(lowered_terms),
                        func.lower(func.coalesce(Player.canonical_display_name, "")).in_(lowered_terms),
                    ),
                )
            )
        )
        return tuple(dict.fromkeys(player.id for player in players))

    def _player_ids_for_birthyear_anchor(
        self,
        session: Session,
        identity: NormalizedRealPlayerIdentity,
        *,
        require_club: bool,
    ) -> tuple[str, ...]:
        if identity.birth_year is None:
            return ()
        if require_club and not identity.club_reference_key:
            return ()
        if not require_club and not (identity.club_reference_key or identity.normalized_nationality or identity.nationality_code):
            return ()
        statement = self._candidate_statement().where(
            Player.date_of_birth.is_not(None),
            extract("year", Player.date_of_birth) == identity.birth_year,
        )
        players = [
            player
            for player in session.scalars(statement)
            if self._candidate_matches_name(player, identity)
            and (
                self._club_matches(player, identity)
                if require_club
                else self._country_matches(player, identity)
            )
        ]
        return tuple(dict.fromkeys(player.id for player in players))

    def _load_candidates(self, session: Session, identity: NormalizedRealPlayerIdentity) -> list[Player]:
        players_by_id: dict[str, Player] = {}
        for player in self._load_exact_name_candidates(session, identity):
            players_by_id[player.id] = player
        for player in self._load_date_of_birth_candidates(session, identity, exclude_ids=set(players_by_id)):
            players_by_id[player.id] = player
        for player in self._load_birthyear_anchor_candidates(session, identity, exclude_ids=set(players_by_id)):
            players_by_id[player.id] = player
        return list(players_by_id.values())

    def _load_exact_name_candidates(self, session: Session, identity: NormalizedRealPlayerIdentity) -> list[Player]:
        search_terms = self._search_terms(identity)
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

    def _load_date_of_birth_candidates(
        self,
        session: Session,
        identity: NormalizedRealPlayerIdentity,
        *,
        exclude_ids: set[str],
    ) -> list[Player]:
        if identity.date_of_birth is None:
            return []
        return [
            player
            for player in session.scalars(self._candidate_statement().where(Player.date_of_birth == identity.date_of_birth))
            if player.id not in exclude_ids
        ]

    def _load_birthyear_anchor_candidates(
        self,
        session: Session,
        identity: NormalizedRealPlayerIdentity,
        *,
        exclude_ids: set[str],
    ) -> list[Player]:
        if identity.birth_year is None or not (identity.club_reference_key or identity.normalized_nationality or identity.nationality_code):
            return []
        statement = self._candidate_statement().where(
            Player.date_of_birth.is_not(None),
            extract("year", Player.date_of_birth) == identity.birth_year,
        )
        return [
            player
            for player in session.scalars(statement)
            if player.id not in exclude_ids
            and (self._club_matches(player, identity) or self._country_matches(player, identity))
        ]

    def _score_candidate(
        self,
        player: Player,
        identity: NormalizedRealPlayerIdentity,
        *,
        base_reason: str | None = None,
        base_score: float = 0.0,
    ) -> RealPlayerMatchCandidate:
        score = base_score
        reasons: list[str] = [base_reason] if base_reason else []

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

        if any(names_equivalent(identity.normalized_full_name, candidate_name.normalized) for candidate_name in candidate_primary_names):
            score += 0.54
            reasons.append("exact_normalized_name")
        elif identity.normalized_display_name and any(
            names_equivalent(identity.normalized_display_name, candidate_name.normalized)
            for candidate_name in (*candidate_primary_names, *candidate_aliases)
        ):
            score += 0.48
            reasons.append("display_name")
        elif any(
            names_equivalent(payload_alias, candidate_name.normalized)
            for payload_alias in identity.normalized_aliases
            for candidate_name in (*candidate_primary_names, *candidate_aliases)
        ):
            score += 0.46
            reasons.append("alias_name")
        elif any(
            candidate_name.token_signature
            and candidate_name.token_signature == identity.name_token_signature
            and candidate_name.first_token == normalize_identity_name(identity.canonical_name).first_token
            for candidate_name in (*candidate_primary_names, *candidate_aliases)
        ):
            score += 0.34
            reasons.append("token_signature")

        if identity.date_of_birth is not None and player.date_of_birth == identity.date_of_birth:
            score += 0.24
            reasons.append("date_of_birth")
        elif identity.birth_year is not None and player.date_of_birth is not None and player.date_of_birth.year == identity.birth_year:
            score += 0.14
            reasons.append("birth_year")

        if self._country_matches(player, identity):
            score += 0.08
            reasons.append("nationality")

        if self._club_matches(player, identity):
            score += 0.08
            reasons.append("club")

        if self._position_matches(player, identity):
            score += 0.08
            reasons.append("position")
        elif position_family(player.normalized_position or player.position) == identity.position_family:
            score += 0.05
            reasons.append("position_family")

        if identity.dominant_foot and normalize_preferred_foot(player.preferred_foot) == identity.dominant_foot:
            score += 0.03
            reasons.append("preferred_foot")

        if identity.height_cm is not None and player.height_cm is not None:
            difference = abs(player.height_cm - identity.height_cm)
            if difference <= 2:
                score += 0.03
                reasons.append("height_close")
            elif difference <= 5:
                score += 0.02
                reasons.append("height_near")

        if bool(player.is_real_player):
            score += 0.04
            reasons.append("existing_real_player")

        return RealPlayerMatchCandidate(
            player_id=player.id,
            score=round(min(score, 0.99), 4),
            reasons=tuple(reasons),
        )

    def _rank_candidates(
        self,
        session: Session,
        player_ids: tuple[str, ...],
        identity: NormalizedRealPlayerIdentity,
        *,
        base_reason: str,
        base_score: float,
    ) -> tuple[RealPlayerMatchCandidate, ...]:
        players = list(
            session.scalars(
                self._candidate_statement().where(Player.id.in_(player_ids))
            )
        )
        return tuple(
            sorted(
                (
                    self._score_candidate(player, identity, base_reason=base_reason, base_score=base_score)
                    for player in players
                ),
                key=lambda item: (-item.score, item.player_id),
            )
        )

    def _candidate_statement(self):
        return select(Player).options(
            selectinload(Player.country),
            selectinload(Player.current_club),
        )

    def _candidate_matches_name(self, player: Player, identity: NormalizedRealPlayerIdentity) -> bool:
        candidate_names = (
            normalize_identity_name(player.full_name),
            normalize_identity_name(player.canonical_display_name),
            normalize_identity_name(player.short_name),
        )
        if any(names_equivalent(identity.normalized_full_name, candidate.normalized) for candidate in candidate_names if candidate.tokens):
            return True
        if identity.normalized_display_name and any(
            names_equivalent(identity.normalized_display_name, candidate.normalized)
            for candidate in candidate_names
            if candidate.tokens
        ):
            return True
        return any(
            names_equivalent(payload_alias, candidate.normalized)
            for payload_alias in identity.normalized_aliases
            for candidate in candidate_names
            if candidate.tokens
        )

    def _country_matches(self, player: Player, identity: NormalizedRealPlayerIdentity) -> bool:
        candidate_values = {
            normalize_identity_name(getattr(player.country, "name", None)).normalized,
            str(getattr(player.country, "alpha2_code", "") or "").strip().lower(),
            str(getattr(player.country, "alpha3_code", "") or "").strip().lower(),
            str(getattr(player.country, "fifa_code", "") or "").strip().lower(),
        }
        payload_values = {
            (identity.normalized_nationality or ""),
            str(identity.nationality_code or "").strip().lower(),
        }
        candidate_values.discard("")
        payload_values.discard("")
        return bool(candidate_values and payload_values and candidate_values.intersection(payload_values))

    def _club_matches(self, player: Player, identity: NormalizedRealPlayerIdentity) -> bool:
        if not identity.club_reference_key:
            return False
        candidate_values = {
            self._reference_key(player.real_world_club_name),
            self._reference_key(getattr(player.current_club, "name", None)),
        }
        candidate_values.discard("")
        return identity.club_reference_key in candidate_values

    def _position_matches(self, player: Player, identity: NormalizedRealPlayerIdentity) -> bool:
        return canonical_position_key(player.position) == identity.primary_position_key

    def _search_terms(self, identity: NormalizedRealPlayerIdentity) -> tuple[str, ...]:
        return identity.name_variants()

    @staticmethod
    def _reference_key(value: str | None) -> str:
        normalized = normalize_identity_name(value).normalized
        if normalized:
            return normalized.replace(" ", "-")
        return ""

    def _create_score(self, identity: NormalizedRealPlayerIdentity) -> float:
        base_score = 0.88
        if identity.date_of_birth is not None:
            base_score += 0.04
        elif identity.birth_year is not None:
            base_score += 0.02
        if identity.club_reference_key:
            base_score += 0.01
        return round(min(base_score, 0.96), 4)


__all__ = [
    "AmbiguousRealPlayerMatchError",
    "RealPlayerDedupeService",
    "RealPlayerMatchCandidate",
    "RealPlayerMatchResult",
]
