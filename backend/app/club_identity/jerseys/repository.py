from __future__ import annotations

from dataclasses import dataclass, field

from app.club_identity.models.jersey_models import ClubIdentityProfile


@dataclass(slots=True)
class InMemoryClubIdentityRepository:
    _profiles: dict[str, ClubIdentityProfile] = field(default_factory=dict)

    def get(self, club_id: str) -> ClubIdentityProfile | None:
        return self._profiles.get(club_id)

    def save(self, profile: ClubIdentityProfile) -> ClubIdentityProfile:
        self._profiles[profile.club_id] = profile
        return profile

    def clear(self) -> None:
        self._profiles.clear()
