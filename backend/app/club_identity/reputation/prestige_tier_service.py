from __future__ import annotations

from dataclasses import dataclass

from backend.app.club_identity.models.reputation import PrestigeTier


@dataclass(frozen=True, slots=True)
class PrestigeProgress:
    current_tier: PrestigeTier
    next_tier: PrestigeTier | None
    points_to_next_tier: int | None


class PrestigeTierService:
    _thresholds: tuple[tuple[PrestigeTier, int], ...] = (
        (PrestigeTier.LOCAL, 0),
        (PrestigeTier.RISING, 150),
        (PrestigeTier.ESTABLISHED, 350),
        (PrestigeTier.ELITE, 650),
        (PrestigeTier.LEGENDARY, 1050),
        (PrestigeTier.DYNASTY, 1600),
    )

    def determine_tier(self, score: int) -> PrestigeTier:
        normalized_score = max(score, 0)
        current_tier = PrestigeTier.LOCAL
        for tier, minimum_score in self._thresholds:
            if normalized_score >= minimum_score:
                current_tier = tier
        return current_tier

    def get_progress(self, score: int) -> PrestigeProgress:
        current_tier = self.determine_tier(score)
        for index, (tier, _) in enumerate(self._thresholds):
            if tier != current_tier:
                continue
            if index == len(self._thresholds) - 1:
                return PrestigeProgress(current_tier=current_tier, next_tier=None, points_to_next_tier=None)
            next_tier, next_threshold = self._thresholds[index + 1]
            return PrestigeProgress(
                current_tier=current_tier,
                next_tier=next_tier,
                points_to_next_tier=max(next_threshold - max(score, 0), 0),
            )
        return PrestigeProgress(current_tier=PrestigeTier.LOCAL, next_tier=PrestigeTier.RISING, points_to_next_tier=150)
