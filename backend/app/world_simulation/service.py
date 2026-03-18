from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.app.club_identity.models.reputation import ClubReputationProfile
from backend.app.models.club_profile import ClubProfile
from backend.app.models.competition import UserCompetition
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.football_world import ClubWorldProfile, FootballCultureProfile, WorldNarrativeArc

_KEY_RE = re.compile(r"[^a-z0-9]+")
_RIVALRY_TAGS = {"derby", "rivalry", "grudge", "regional", "cross-town"}


class FootballWorldError(ValueError):
    pass


@dataclass(slots=True)
class FootballWorldService:
    session: Session

    def seed_defaults(self) -> None:
        defaults = (
            {
                "culture_key": "academy-heartland",
                "display_name": "Academy Heartland",
                "scope_type": "archetype",
                "play_style_summary": "Youth pipelines, repeatable structure, and patient squad-building define the identity.",
                "supporter_traits_json": ["patient", "development-proud", "local-first"],
                "rivalry_themes_json": ["next generation bragging rights", "local pathway supremacy"],
                "talent_archetypes_json": ["technical midfielder", "pressing forward", "composed centre-back"],
                "climate_notes": "Long-horizon planning shapes every big result.",
                "metadata_json": {"seeded_default": True},
            },
            {
                "culture_key": "port-city-circuit",
                "display_name": "Port City Circuit",
                "scope_type": "archetype",
                "play_style_summary": "Fast transitions, swagger, and crowd momentum turn home fixtures into event nights.",
                "supporter_traits_json": ["loud", "performative", "traveling"],
                "rivalry_themes_json": ["coastal bragging rights", "headline fixtures"],
                "talent_archetypes_json": ["explosive winger", "creative dribbler", "counter-punching full-back"],
                "climate_notes": "Momentum swings matter as much as tactics.",
                "metadata_json": {"seeded_default": True},
            },
            {
                "culture_key": "fortress-revivalists",
                "display_name": "Fortress Revivalists",
                "scope_type": "archetype",
                "play_style_summary": "Defensive steel, comeback mythology, and stubborn home form anchor the club story.",
                "supporter_traits_json": ["defiant", "ritual-heavy", "memory-driven"],
                "rivalry_themes_json": ["old wounds", "fallen giant resentment"],
                "talent_archetypes_json": ["ball-winning midfielder", "set-piece defender", "late-game finisher"],
                "climate_notes": "Every season is framed as a return to relevance.",
                "metadata_json": {"seeded_default": True},
            },
        )
        for item in defaults:
            existing = self.session.scalar(
                select(FootballCultureProfile).where(FootballCultureProfile.culture_key == item["culture_key"])
            )
            if existing is None:
                self.session.add(FootballCultureProfile(**item))
        self.session.flush()

    def list_cultures(
        self,
        *,
        country_code: str | None = None,
        scope_type: str | None = None,
        active_only: bool = True,
        limit: int = 20,
    ) -> list[FootballCultureProfile]:
        stmt = select(FootballCultureProfile)
        if active_only:
            stmt = stmt.where(FootballCultureProfile.active.is_(True))
        if country_code:
            stmt = stmt.where(FootballCultureProfile.country_code == country_code.strip().upper())
        if scope_type:
            stmt = stmt.where(FootballCultureProfile.scope_type == self._normalize_label(scope_type, default="archetype"))
        stmt = stmt.order_by(
            FootballCultureProfile.scope_type.asc(),
            FootballCultureProfile.display_name.asc(),
            FootballCultureProfile.created_at.asc(),
        ).limit(limit)
        return list(self.session.scalars(stmt).all())

    def upsert_culture(self, *, culture_key: str, payload) -> FootballCultureProfile:
        normalized_key = self._normalize_key(culture_key, default="culture")
        culture = self.session.scalar(
            select(FootballCultureProfile).where(FootballCultureProfile.culture_key == normalized_key)
        )
        if culture is None:
            culture = FootballCultureProfile(culture_key=normalized_key)
            self.session.add(culture)
        culture.display_name = payload.display_name.strip()
        culture.scope_type = self._normalize_label(payload.scope_type, default="archetype")
        culture.country_code = self._normalize_country(payload.country_code)
        culture.region_name = self._clean(payload.region_name)
        culture.city_name = self._clean(payload.city_name)
        culture.play_style_summary = payload.play_style_summary.strip()
        culture.supporter_traits_json = self._clean_list(payload.supporter_traits_json)
        culture.rivalry_themes_json = self._clean_list(payload.rivalry_themes_json)
        culture.talent_archetypes_json = self._clean_list(payload.talent_archetypes_json)
        culture.climate_notes = payload.climate_notes.strip()
        culture.active = payload.active
        culture.metadata_json = dict(payload.metadata_json)
        self.session.flush()
        return culture

    def upsert_club_world_profile(self, *, club_id: str, payload) -> dict[str, Any]:
        club = self._require_club(club_id)
        profile = self.session.scalar(select(ClubWorldProfile).where(ClubWorldProfile.club_id == club.id))
        if profile is None:
            profile = ClubWorldProfile(club_id=club.id)
            self.session.add(profile)
        culture = self._culture_from_key(payload.culture_key) if payload.culture_key is not None else None
        profile.culture_profile_id = culture.id if culture is not None else None
        profile.narrative_phase = self._normalize_label(payload.narrative_phase, default="establishing_identity")
        profile.supporter_mood = self._normalize_label(payload.supporter_mood, default="hopeful")
        profile.derby_heat_score = self._clamp(payload.derby_heat_score)
        profile.global_appeal_score = self._clamp(payload.global_appeal_score)
        profile.identity_keywords_json = self._clean_list(payload.identity_keywords_json)
        profile.transfer_identity_tags_json = self._clean_list(payload.transfer_identity_tags_json)
        profile.fan_culture_tags_json = self._clean_list(payload.fan_culture_tags_json)
        profile.world_flags_json = self._clean_list(payload.world_flags_json)
        profile.metadata_json = dict(payload.metadata_json)
        self.session.flush()
        return self.club_context(club.id)

    def upsert_narrative_arc(self, *, narrative_slug: str, payload) -> WorldNarrativeArc:
        normalized_slug = self._normalize_key(narrative_slug, default="narrative")
        club_id = self._require_club(payload.club_id).id if payload.club_id else None
        competition_id = self._require_competition(payload.competition_id).id if payload.competition_id else None
        narrative = self.session.scalar(select(WorldNarrativeArc).where(WorldNarrativeArc.slug == normalized_slug))
        if narrative is None:
            narrative = WorldNarrativeArc(slug=normalized_slug)
            self.session.add(narrative)
        narrative.slug = normalized_slug
        narrative.scope_type = self._derive_scope_type(club_id=club_id, competition_id=competition_id)
        narrative.club_id = club_id
        narrative.competition_id = competition_id
        narrative.arc_type = self._normalize_label(payload.arc_type, default="story")
        narrative.status = self._normalize_label(payload.status, default="active")
        narrative.visibility = self._normalize_label(payload.visibility, default="public")
        narrative.headline = payload.headline.strip()
        narrative.summary = payload.summary.strip()
        narrative.importance_score = self._clamp(payload.importance_score)
        narrative.simulation_horizon = self._normalize_label(payload.simulation_horizon, default="seasonal")
        narrative.start_at = payload.start_at
        narrative.end_at = payload.end_at
        narrative.tags_json = self._clean_list(payload.tags_json)
        narrative.impact_vectors_json = self._clean_list(payload.impact_vectors_json)
        narrative.metadata_json = dict(payload.metadata_json)
        self.session.flush()
        return narrative

    def list_narratives(
        self,
        *,
        club_id: str | None = None,
        competition_id: str | None = None,
        active_only: bool = True,
        public_only: bool = True,
        limit: int = 20,
    ) -> list[WorldNarrativeArc]:
        now = self._now()
        stmt = select(WorldNarrativeArc)
        if club_id:
            stmt = stmt.where(WorldNarrativeArc.club_id == club_id)
        if competition_id:
            stmt = stmt.where(WorldNarrativeArc.competition_id == competition_id)
        if public_only:
            stmt = stmt.where(WorldNarrativeArc.visibility == "public")
        if active_only:
            stmt = stmt.where(
                WorldNarrativeArc.status == "active",
                or_(WorldNarrativeArc.start_at.is_(None), WorldNarrativeArc.start_at <= now),
                or_(WorldNarrativeArc.end_at.is_(None), WorldNarrativeArc.end_at >= now),
            )
        stmt = stmt.order_by(WorldNarrativeArc.importance_score.desc(), WorldNarrativeArc.updated_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def club_context(self, club_id: str) -> dict[str, Any]:
        club = self._require_club(club_id)
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club.id))
        profile = self.session.scalar(select(ClubWorldProfile).where(ClubWorldProfile.club_id == club.id))
        culture = self._resolve_culture_for_club(club=club, profile=profile)
        narratives = self.list_narratives(club_id=club.id, limit=8)
        world_profile = self._build_club_profile_snapshot(
            club=club,
            profile=profile,
            reputation=reputation,
            culture=culture,
            narratives=narratives,
        )
        return {
            "club_id": club.id,
            "club_name": club.club_name,
            "short_name": club.short_name,
            "country_code": club.country_code,
            "region_name": club.region_name,
            "city_name": club.city_name,
            "reputation_score": reputation.current_score if reputation is not None else 0,
            "prestige_tier": reputation.prestige_tier if reputation is not None else None,
            "culture": culture,
            "world_profile": world_profile,
            "active_narratives": narratives,
            "simulation_hooks": self._build_club_hooks(
                club=club,
                reputation=reputation,
                culture=culture,
                world_profile=world_profile,
                narratives=narratives,
            ),
        }

    def competition_context(self, competition_id: str) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        participant_count = int(
            self.session.scalar(
                select(func.count()).select_from(CompetitionParticipant).where(
                    CompetitionParticipant.competition_id == competition.id
                )
            )
            or 0
        )
        narratives = self.list_narratives(competition_id=competition.id, limit=8)
        return {
            "competition_id": competition.id,
            "name": competition.name,
            "status": competition.status,
            "format": competition.format,
            "stage": competition.stage,
            "participant_count": participant_count,
            "active_narratives": narratives,
            "simulation_hooks": self._build_competition_hooks(
                competition=competition,
                participant_count=participant_count,
                narratives=narratives,
            ),
        }

    def _build_club_profile_snapshot(
        self,
        *,
        club: ClubProfile,
        profile: ClubWorldProfile | None,
        reputation: ClubReputationProfile | None,
        culture: FootballCultureProfile | None,
        narratives: list[WorldNarrativeArc],
    ) -> dict[str, Any]:
        identity_keywords = self._merge_unique(
            (profile.identity_keywords_json if profile is not None else []),
            self._default_identity_keywords(club=club, reputation=reputation),
        )
        transfer_tags = self._merge_unique(
            (profile.transfer_identity_tags_json if profile is not None else []),
            (culture.talent_archetypes_json if culture is not None else []),
            [self._phase_to_transfer_tag(profile.narrative_phase if profile is not None else None, reputation)],
        )
        fan_tags = self._merge_unique(
            (profile.fan_culture_tags_json if profile is not None else []),
            (culture.supporter_traits_json if culture is not None else []),
        )
        derived_phase = self._derive_phase(profile=profile, reputation=reputation, narratives=narratives)
        derived_mood = self._derive_supporter_mood(profile=profile, narratives=narratives, reputation=reputation)
        derived_heat = self._derive_derby_heat(profile=profile, narratives=narratives)
        derived_appeal = self._derive_global_appeal(profile=profile, reputation=reputation, narratives=narratives)
        world_flags = self._merge_unique(
            (profile.world_flags_json if profile is not None else []),
            [derived_phase, derived_mood],
            [f"{narrative.arc_type}:{narrative.simulation_horizon}" for narrative in narratives[:3]],
        )
        return {
            "source": "curated" if profile is not None else "derived",
            "culture_key": culture.culture_key if culture is not None else None,
            "narrative_phase": derived_phase,
            "supporter_mood": derived_mood,
            "derby_heat_score": derived_heat,
            "global_appeal_score": derived_appeal,
            "identity_keywords": identity_keywords,
            "transfer_identity_tags": transfer_tags,
            "fan_culture_tags": fan_tags,
            "world_flags": world_flags,
            "metadata_json": dict(profile.metadata_json) if profile is not None else {},
            "updated_at": profile.updated_at if profile is not None else None,
        }

    def _build_club_hooks(
        self,
        *,
        club: ClubProfile,
        reputation: ClubReputationProfile | None,
        culture: FootballCultureProfile | None,
        world_profile: dict[str, Any],
        narratives: list[WorldNarrativeArc],
    ) -> list[dict[str, Any]]:
        hooks: list[dict[str, Any]] = []
        if culture is not None:
            hooks.append(
                {
                    "hook_key": "culture-resonance",
                    "title": "Culture resonance",
                    "target_scope": "club",
                    "horizon": "multi-season",
                    "weight": self._clamp(45 + (len(culture.supporter_traits_json) * 8)),
                    "inputs": {
                        "culture_key": culture.culture_key,
                        "supporter_traits": culture.supporter_traits_json,
                        "talent_archetypes": culture.talent_archetypes_json,
                    },
                    "metadata_json": {"source": "culture_profile"},
                }
            )
        if reputation is not None and reputation.current_score >= 250:
            hooks.append(
                {
                    "hook_key": "legacy-pressure",
                    "title": "Legacy pressure",
                    "target_scope": "club",
                    "horizon": "seasonal",
                    "weight": self._clamp((reputation.current_score // 5) + 10),
                    "inputs": {
                        "prestige_tier": reputation.prestige_tier,
                        "reputation_score": reputation.current_score,
                    },
                    "metadata_json": {"source": "club_reputation"},
                }
            )
        if world_profile["derby_heat_score"] >= 60:
            hooks.append(
                {
                    "hook_key": "derby-volatility",
                    "title": "Derby volatility",
                    "target_scope": "club",
                    "horizon": "match-window",
                    "weight": world_profile["derby_heat_score"],
                    "inputs": {"club_id": club.id, "fan_culture_tags": world_profile["fan_culture_tags"]},
                    "metadata_json": {"source": "world_profile"},
                }
            )
        if world_profile["supporter_mood"] in {"electric", "expectant", "defiant"}:
            hooks.append(
                {
                    "hook_key": "fan-engagement-lift",
                    "title": "Fan engagement lift",
                    "target_scope": "club",
                    "horizon": "seasonal",
                    "weight": self._clamp(55 + len(world_profile["fan_culture_tags"]) * 5),
                    "inputs": {"supporter_mood": world_profile["supporter_mood"]},
                    "metadata_json": {"source": "world_profile"},
                }
            )
        hooks.extend(self._narrative_hooks(target_scope="club", narratives=narratives))
        return self._deduplicate_hooks(hooks)

    def _build_competition_hooks(
        self,
        *,
        competition: UserCompetition,
        participant_count: int,
        narratives: list[WorldNarrativeArc],
    ) -> list[dict[str, Any]]:
        hooks: list[dict[str, Any]] = []
        if competition.visibility == "public":
            hooks.append(
                {
                    "hook_key": "discovery-lift",
                    "title": "Discovery lift",
                    "target_scope": "competition",
                    "horizon": "seasonal",
                    "weight": 40,
                    "inputs": {"visibility": competition.visibility},
                    "metadata_json": {"source": "competition"},
                }
            )
        if competition.status in {"open", "live", "in_progress"}:
            hooks.append(
                {
                    "hook_key": "fan-attention-window",
                    "title": "Fan attention window",
                    "target_scope": "competition",
                    "horizon": "seasonal",
                    "weight": 60,
                    "inputs": {"status": competition.status, "stage": competition.stage},
                    "metadata_json": {"source": "competition"},
                }
            )
        if participant_count >= 8:
            hooks.append(
                {
                    "hook_key": "upset-potential",
                    "title": "Upset potential",
                    "target_scope": "competition",
                    "horizon": "match-window",
                    "weight": self._clamp(45 + participant_count),
                    "inputs": {"participant_count": participant_count},
                    "metadata_json": {"source": "competition"},
                }
            )
        hooks.extend(self._narrative_hooks(target_scope="competition", narratives=narratives))
        return self._deduplicate_hooks(hooks)

    def _narrative_hooks(self, *, target_scope: str, narratives: list[WorldNarrativeArc]) -> list[dict[str, Any]]:
        hooks: list[dict[str, Any]] = []
        for narrative in narratives:
            impact_vectors = narrative.impact_vectors_json or [narrative.arc_type]
            for vector in impact_vectors:
                hook_key = self._normalize_key(vector, default=narrative.arc_type)
                hooks.append(
                    {
                        "hook_key": hook_key,
                        "title": narrative.headline,
                        "target_scope": target_scope,
                        "horizon": narrative.simulation_horizon.replace("_", "-"),
                        "weight": self._clamp(narrative.importance_score),
                        "inputs": {
                            "slug": narrative.slug,
                            "arc_type": narrative.arc_type,
                            "vector": vector,
                        },
                        "metadata_json": {
                            "source": "narrative_arc",
                            "scope_type": narrative.scope_type,
                        },
                    }
                )
        return hooks

    def _resolve_culture_for_club(
        self,
        *,
        club: ClubProfile,
        profile: ClubWorldProfile | None,
    ) -> FootballCultureProfile | None:
        if profile is not None and profile.culture_profile_id:
            culture = self.session.get(FootballCultureProfile, profile.culture_profile_id)
            if culture is not None:
                return culture
        if club.country_code:
            exact_stmt = (
                select(FootballCultureProfile)
                .where(
                    FootballCultureProfile.active.is_(True),
                    FootballCultureProfile.country_code == self._normalize_country(club.country_code),
                    FootballCultureProfile.region_name == self._clean(club.region_name),
                    FootballCultureProfile.city_name == self._clean(club.city_name),
                )
                .limit(1)
            )
            culture = self.session.scalar(exact_stmt)
            if culture is not None:
                return culture
            country_stmt = (
                select(FootballCultureProfile)
                .where(
                    FootballCultureProfile.active.is_(True),
                    FootballCultureProfile.country_code == self._normalize_country(club.country_code),
                    FootballCultureProfile.region_name.is_(None),
                    FootballCultureProfile.city_name.is_(None),
                )
                .limit(1)
            )
            culture = self.session.scalar(country_stmt)
            if culture is not None:
                return culture
        return None

    def _culture_from_key(self, culture_key: str | None) -> FootballCultureProfile | None:
        if culture_key is None:
            return None
        normalized_key = self._normalize_key(culture_key, default="")
        if not normalized_key:
            return None
        culture = self.session.scalar(
            select(FootballCultureProfile).where(FootballCultureProfile.culture_key == normalized_key)
        )
        if culture is None:
            raise FootballWorldError("culture_profile_not_found")
        return culture

    def _derive_phase(
        self,
        *,
        profile: ClubWorldProfile | None,
        reputation: ClubReputationProfile | None,
        narratives: list[WorldNarrativeArc],
    ) -> str:
        if profile is not None and profile.narrative_phase:
            return profile.narrative_phase
        if narratives:
            return self._normalize_label(narratives[0].arc_type, default="storyline")
        if reputation is None:
            return "establishing_identity"
        if reputation.current_score >= 400:
            return "dynasty_pressure"
        if reputation.current_score >= 200:
            return "continental_push"
        if reputation.current_score <= 80:
            return "underdog_rebuild"
        return "establishing_identity"

    def _derive_supporter_mood(
        self,
        *,
        profile: ClubWorldProfile | None,
        narratives: list[WorldNarrativeArc],
        reputation: ClubReputationProfile | None,
    ) -> str:
        if profile is not None and profile.supporter_mood:
            return profile.supporter_mood
        if narratives and narratives[0].importance_score >= 75:
            return "electric"
        if reputation is not None and reputation.current_score >= 300:
            return "expectant"
        if reputation is not None and reputation.current_score <= 60:
            return "defiant"
        return "hopeful"

    def _derive_derby_heat(self, *, profile: ClubWorldProfile | None, narratives: list[WorldNarrativeArc]) -> int:
        base = profile.derby_heat_score if profile is not None else 0
        narrative_boost = 0
        for narrative in narratives:
            if any(tag in _RIVALRY_TAGS for tag in narrative.tags_json):
                narrative_boost = max(narrative_boost, min(35, narrative.importance_score // 2))
        return self._clamp(base + narrative_boost)

    def _derive_global_appeal(
        self,
        *,
        profile: ClubWorldProfile | None,
        reputation: ClubReputationProfile | None,
        narratives: list[WorldNarrativeArc],
    ) -> int:
        if profile is not None and profile.global_appeal_score:
            return self._clamp(profile.global_appeal_score)
        score = 15
        if reputation is not None:
            score += min(55, reputation.current_score // 6)
        if narratives:
            score += min(20, narratives[0].importance_score // 5)
        return self._clamp(score)

    def _default_identity_keywords(
        self,
        *,
        club: ClubProfile,
        reputation: ClubReputationProfile | None,
    ) -> list[str]:
        defaults = [
            self._clean(club.city_name),
            self._clean(club.region_name),
            self._normalize_country(club.country_code),
            self._normalize_label(reputation.prestige_tier, default="") if reputation is not None else "",
        ]
        return self._clean_list(defaults)

    def _phase_to_transfer_tag(
        self,
        phase: str | None,
        reputation: ClubReputationProfile | None,
    ) -> str:
        resolved_phase = self._normalize_label(phase, default="")
        if resolved_phase in {"dynasty_pressure", "continental_push"}:
            return "win-now"
        if resolved_phase == "underdog_rebuild":
            return "development-value"
        if reputation is not None and reputation.current_score >= 250:
            return "brand-amplifier"
        return "system-fit"

    def _deduplicate_hooks(self, hooks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for hook in hooks:
            key = hook["hook_key"]
            current = deduped.get(key)
            if current is None or hook["weight"] > current["weight"]:
                deduped[key] = hook
        return sorted(deduped.values(), key=lambda item: (-item["weight"], item["hook_key"]))

    def _require_club(self, club_id: str | None) -> ClubProfile:
        if not club_id:
            raise FootballWorldError("club_not_found")
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise FootballWorldError("club_not_found")
        return club

    def _require_competition(self, competition_id: str | None) -> UserCompetition:
        if not competition_id:
            raise FootballWorldError("competition_not_found")
        competition = self.session.get(UserCompetition, competition_id)
        if competition is None:
            raise FootballWorldError("competition_not_found")
        return competition

    def _derive_scope_type(self, *, club_id: str | None, competition_id: str | None) -> str:
        if club_id and competition_id:
            return "club_competition"
        if club_id:
            return "club"
        if competition_id:
            return "competition"
        return "global"

    def _normalize_key(self, value: str | None, *, default: str) -> str:
        cleaned = _KEY_RE.sub("-", (value or "").strip().lower()).strip("-")
        return cleaned or default

    def _normalize_label(self, value: str | None, *, default: str) -> str:
        cleaned = _KEY_RE.sub("_", (value or "").strip().lower()).strip("_")
        return cleaned or default

    def _normalize_country(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned or None

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    def _clean_list(self, values: list[str] | tuple[str, ...] | list[Any]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            item = value.strip()
            if item:
                cleaned.append(item)
        return cleaned

    def _merge_unique(self, *groups: list[str]) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for item in group:
                if item and item not in merged:
                    merged.append(item)
        return merged

    def _clamp(self, value: int) -> int:
        return max(0, min(100, int(value)))

    def _now(self) -> datetime:
        return datetime.now(UTC)
