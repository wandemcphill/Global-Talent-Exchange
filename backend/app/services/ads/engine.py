from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5
from typing import TYPE_CHECKING, Any

from app.schemas.match_viewer import MatchViewerEventType, MatchViewerEventView, MatchViewStateView
from app.services.ads.analytics import impression_metadata
from app.services.ads.pricing import estimate_value_usd, resolve_cpm
from app.services.ads.schemas import (
    MatchAdPlacementType,
    MatchAdPlacementView,
    MatchViewerMonetizationView,
)
from app.services.ads.targeting import (
    infer_country_from_match,
    match_user_to_ads,
    profile_from_input,
    targeting_tags,
)

if TYPE_CHECKING:
    from app.match_engine.schemas import MatchHighlightItemView, MatchHighlightListView


@dataclass(slots=True)
class AdDecisionEngine:
    rewarded_coin_floor: int = 50
    rewarded_coin_grant: int = 50

    def select_ad(
        self,
        user: dict[str, Any] | None,
        match: dict[str, Any] | None,
        event: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        profile = profile_from_input(user)
        if profile.is_premium_user:
            return None
        brands = match_user_to_ads(self._effective_profile(profile, match))
        if not brands:
            return None

        event_type = str((event or {}).get("event_type", "")).strip().lower()
        if event_type == "goal":
            brand = self._pick_brand(brands, seed=f"sponsored:{(event or {}).get('event_id', 'goal')}")
            return {
                "type": MatchAdPlacementType.SPONSORED_HIGHLIGHT.value,
                "brand": brand,
                "message": f"Goal of the Match powered by {brand}",
            }
        if profile.coins < self.rewarded_coin_floor:
            brand = self._pick_brand(brands, seed="rewarded")
            return {
                "type": MatchAdPlacementType.REWARDED_AD.value,
                "brand": brand,
                "message": f"Watch {brand} and earn coins",
            }
        return None

    def build_viewer_monetization(
        self,
        *,
        match_id: str,
        view_state: MatchViewStateView,
        ad_profile: dict[str, Any] | None = None,
        match_context: dict[str, Any] | None = None,
    ) -> MatchViewerMonetizationView:
        profile = self._effective_profile(profile_from_input(ad_profile), match_context or self._match_context_from_view_state(view_state))
        if profile.is_premium_user:
            return MatchViewerMonetizationView(
                ads_enabled=False,
                premium_ad_free=True,
                placements=[],
                metadata={"market_country": profile.normalized_country},
            )

        brands = match_user_to_ads(profile)
        if not brands:
            return MatchViewerMonetizationView(ads_enabled=False, premium_ad_free=False)

        tags = targeting_tags(profile, match=match_context or self._match_context_from_view_state(view_state))
        placements: list[MatchAdPlacementView] = []
        sponsored_event = self._first_sponsored_event(view_state.events)
        if sponsored_event is not None:
            sponsored_brand = self._pick_brand(brands, seed=f"{match_id}:sponsored")
            placements.append(
                self._placement(
                    match_id=match_id,
                    ad_type=MatchAdPlacementType.SPONSORED_HIGHLIGHT,
                    brand=sponsored_brand,
                    message=self._sponsored_message(sponsored_event, sponsored_brand),
                    placement="highlight_overlay",
                    event_id=sponsored_event.event_id,
                    active_from_second=max(0, int(sponsored_event.time_seconds) - 1),
                    active_until_second=min(
                        view_state.duration_seconds,
                        max(int(sponsored_event.time_seconds) + 8, int(sponsored_event.time_seconds) + 1),
                    ),
                    cta_label="Watch Highlight",
                    tags=tags,
                    event_type=sponsored_event.event_type.value,
                    is_final=self._is_final(view_state),
                    is_major_match=self._is_major_match(view_state),
                )
            )

        pre_roll_end = max(6, min(14, max(6, view_state.duration_seconds // 18)))
        preroll_brand = self._pick_brand(
            brands,
            seed=f"{match_id}:pre_roll",
            avoid={placements[0].brand} if placements else set(),
        )
        placements.append(
            self._placement(
                match_id=match_id,
                ad_type=MatchAdPlacementType.PRE_ROLL,
                brand=preroll_brand,
                message=self._preroll_message(preroll_brand),
                placement="video_preroll",
                active_from_second=0,
                active_until_second=pre_roll_end,
                cta_label="Continue to Highlight",
                tags=tags,
                is_final=self._is_final(view_state),
                is_major_match=self._is_major_match(view_state),
            )
        )

        if view_state.duration_seconds >= 45:
            banner_brand = self._pick_brand(
                brands,
                seed=f"{match_id}:banner",
                avoid={placement.brand for placement in placements},
            )
            live_start = max(12, int(round(view_state.duration_seconds * 0.18)))
            live_end = min(view_state.duration_seconds, max(live_start + 8, int(round(view_state.duration_seconds * 0.78))))
            placements.append(
                self._placement(
                    match_id=match_id,
                    ad_type=MatchAdPlacementType.LIVE_BANNER,
                    brand=banner_brand,
                    message=self._live_banner_message(banner_brand),
                    placement="live_overlay",
                    active_from_second=live_start,
                    active_until_second=live_end,
                    cta_label="Learn More",
                    tags=tags,
                    is_final=self._is_final(view_state),
                    is_major_match=self._is_major_match(view_state),
                )
            )

        if profile.coins < self.rewarded_coin_floor:
            reward_brand = self._pick_brand(
                brands,
                seed=f"{match_id}:rewarded",
                avoid={placement.brand for placement in placements},
            )
            placements.append(
                self._placement(
                    match_id=match_id,
                    ad_type=MatchAdPlacementType.REWARDED_AD,
                    brand=reward_brand,
                    message=f"Watch {reward_brand} and earn {self.rewarded_coin_grant} coins",
                    placement="rewarded_panel",
                    reward_coins=self.rewarded_coin_grant,
                    cta_label=f"Watch Ad +{self.rewarded_coin_grant}",
                    tags=tags,
                    is_final=self._is_final(view_state),
                    is_major_match=self._is_major_match(view_state),
                )
            )

        return MatchViewerMonetizationView(
            ads_enabled=bool(placements),
            premium_ad_free=False,
            placements=placements,
            metadata={
                "market_country": profile.normalized_country,
                "reward_floor": self.rewarded_coin_floor,
                "placements": len(placements),
            },
        )

    def attach_highlight_ads(
        self,
        manifest: MatchHighlightListView,
        *,
        ad_profile: dict[str, Any] | None = None,
        match_context: dict[str, Any] | None = None,
    ) -> MatchHighlightListView:
        profile = self._effective_profile(profile_from_input(ad_profile), match_context)
        if profile.is_premium_user:
            return manifest.model_copy(
                update={
                    "monetization": MatchViewerMonetizationView(
                        ads_enabled=False,
                        premium_ad_free=True,
                        placements=[],
                        metadata={"market_country": profile.normalized_country},
                    )
                }
            )

        brands = match_user_to_ads(profile)
        if not brands:
            return manifest

        tags = targeting_tags(profile, match=match_context)
        placements: list[MatchAdPlacementView] = []
        sponsored_lookup: dict[str, MatchAdPlacementView] = {}
        for item in manifest.highlights:
            if item.event_type not in {"goals", "penalties"}:
                continue
            highlight_brand = self._pick_brand(
                brands,
                seed=f"{manifest.match_id}:{item.highlight_id}:highlight",
            )
            placement = self._placement(
                match_id=manifest.match_id,
                ad_type=MatchAdPlacementType.SPONSORED_HIGHLIGHT,
                brand=highlight_brand,
                message=f"{item.title} powered by {highlight_brand}",
                placement="highlight_overlay",
                event_id=item.highlight_id,
                active_from_second=item.reel_start_second,
                active_until_second=item.reel_end_second,
                cta_label="Play Sponsored Clip",
                tags=tags,
                event_type=item.event_type,
                is_final=manifest.highlight_profile is not None and manifest.highlight_profile.value == "elite_final",
                is_major_match=item.importance >= 4,
            )
            placements.append(placement)
            sponsored_lookup[item.highlight_id] = placement

        if manifest.highlights:
            first_clip = manifest.highlights[0]
            preroll_brand = self._pick_brand(
                brands,
                seed=f"{manifest.match_id}:highlight_preroll",
                avoid={placement.brand for placement in placements},
            )
            placements.append(
                self._placement(
                    match_id=manifest.match_id,
                    ad_type=MatchAdPlacementType.PRE_ROLL,
                    brand=preroll_brand,
                    message=self._preroll_message(preroll_brand),
                    placement="video_preroll",
                    active_from_second=0,
                    active_until_second=min(12, first_clip.duration_seconds or 12),
                    cta_label="Start Reel",
                    tags=tags,
                    is_final=manifest.highlight_profile is not None and manifest.highlight_profile.value == "elite_final",
                    is_major_match=any(item.importance >= 4 for item in manifest.highlights),
                )
            )

        if profile.coins < self.rewarded_coin_floor:
            reward_brand = self._pick_brand(
                brands,
                seed=f"{manifest.match_id}:highlight_rewarded",
                avoid={placement.brand for placement in placements},
            )
            placements.append(
                self._placement(
                    match_id=manifest.match_id,
                    ad_type=MatchAdPlacementType.REWARDED_AD,
                    brand=reward_brand,
                    message=f"Watch {reward_brand} and earn {self.rewarded_coin_grant} coins",
                    placement="rewarded_panel",
                    reward_coins=self.rewarded_coin_grant,
                    cta_label=f"Watch Ad +{self.rewarded_coin_grant}",
                    tags=tags,
                    is_final=manifest.highlight_profile is not None and manifest.highlight_profile.value == "elite_final",
                    is_major_match=any(item.importance >= 4 for item in manifest.highlights),
                )
            )

        updated_highlights: list[MatchHighlightItemView] = []
        for item in manifest.highlights:
            sponsored = sponsored_lookup.get(item.highlight_id)
            metadata = dict(item.metadata)
            if sponsored is not None:
                metadata["sponsored"] = True
                metadata["sponsor_brand"] = sponsored.brand
            updated_highlights.append(
                item.model_copy(
                    update={
                        "ad_placement": sponsored,
                        "metadata": metadata,
                    }
                )
            )

        return manifest.model_copy(
            update={
                "highlights": updated_highlights,
                "monetization": MatchViewerMonetizationView(
                    ads_enabled=bool(placements),
                    premium_ad_free=False,
                    placements=placements,
                    metadata={
                        "market_country": profile.normalized_country,
                        "placements": len(placements),
                    },
                ),
            }
        )

    def _placement(
        self,
        *,
        match_id: str,
        ad_type: MatchAdPlacementType,
        brand: str,
        message: str,
        placement: str,
        tags: list[str],
        event_type: str | None = None,
        event_id: str | None = None,
        active_from_second: int | None = None,
        active_until_second: int | None = None,
        reward_coins: int | None = None,
        cta_label: str | None = None,
        is_final: bool = False,
        is_major_match: bool = False,
    ) -> MatchAdPlacementView:
        ad_id = self._ad_id(match_id, ad_type=ad_type, brand=brand, event_id=event_id)
        return MatchAdPlacementView(
            ad_id=ad_id,
            ad_type=ad_type,
            placement=placement,
            brand=brand,
            message=message,
            event_id=event_id,
            active_from_second=active_from_second,
            active_until_second=active_until_second,
            reward_coins=reward_coins,
            cta_label=cta_label,
            pricing_cpm_usd=resolve_cpm(
                ad_type.value,
                event_type=event_type,
                is_final=is_final,
                is_major_match=is_major_match,
            ),
            estimated_value_usd=estimate_value_usd(
                ad_type.value,
                event_type=event_type,
                is_final=is_final,
                is_major_match=is_major_match,
            ),
            targeting_tags=list(tags),
            metadata=impression_metadata(
                match_id=match_id,
                ad_id=ad_id,
                placement=placement,
            ),
        )

    def _effective_profile(self, profile, match: dict[str, Any] | None):
        if profile.normalized_country != "GLOBAL":
            return profile
        inferred_country = infer_country_from_match(match, fallback="GLOBAL")
        return profile.__class__(
            country=inferred_country,
            coins=profile.coins,
            is_premium_user=profile.is_premium_user,
            favorite_clubs=profile.favorite_clubs,
            interests=profile.interests,
        )

    def _match_context_from_view_state(self, view_state: MatchViewStateView) -> dict[str, Any]:
        return {
            "home_team_name": view_state.home_team.team_name,
            "away_team_name": view_state.away_team.team_name,
            "competition_name": view_state.source,
        }

    def _first_sponsored_event(self, events: list[MatchViewerEventView]) -> MatchViewerEventView | None:
        for event in events:
            if event.event_type in {MatchViewerEventType.GOAL, MatchViewerEventType.PENALTY}:
                return event
        return None

    def _sponsored_message(self, event: MatchViewerEventView, brand: str) -> str:
        label = "Goal of the Match" if event.event_type is MatchViewerEventType.GOAL else "Spotlight Moment"
        return f"{label} powered by {brand}"

    def _preroll_message(self, brand: str) -> str:
        return f"{brand} presents this highlight start"

    def _live_banner_message(self, brand: str) -> str:
        if brand.lower() in {"betking", "fanduel"}:
            return f"{brand} Live Odds"
        if brand.lower() == "korapay":
            return "KoraPay Matchday Rails"
        return f"{brand} Match Pulse"

    def _pick_brand(self, brands: list[str], *, seed: str, avoid: set[str] | None = None) -> str:
        blocked = avoid or set()
        available = [brand for brand in brands if brand not in blocked]
        pool = available or brands
        if not pool:
            return "GTEX"
        index = self._stable_index(seed, len(pool))
        return pool[index]

    def _ad_id(
        self,
        match_id: str,
        *,
        ad_type: MatchAdPlacementType,
        brand: str,
        event_id: str | None,
    ) -> str:
        return f"{match_id}:{ad_type.value}:{brand.lower().replace(' ', '_')}:{event_id or 'slot'}"

    def _stable_index(self, seed: str, size: int) -> int:
        if size <= 1:
            return 0
        digest = md5(seed.encode("utf-8")).hexdigest()[:8]
        return int(digest, 16) % size

    def _is_final(self, view_state: MatchViewStateView) -> bool:
        return any(event.event_type is MatchViewerEventType.FULLTIME for event in view_state.events)

    def _is_major_match(self, view_state: MatchViewStateView) -> bool:
        return any(event.emphasis_level >= 3 for event in view_state.events)


__all__ = ["AdDecisionEngine"]
