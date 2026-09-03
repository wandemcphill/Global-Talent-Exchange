"""Full generated profiles for national-pool regen seeds.

## Why this exists

`seed_preseeded_national_regens` already builds a complete `RegenProfileView`
for every national seed - personality, origin, ability and potential bands,
scout confidence, story seed - and then **throws almost all of it away**,
persisting only flat scalars onto `national_regen_seeds` plus five personality
fields. The data was generated and discarded.

The consequence reached the product: `GET /regen-universe/players/{id}`
resolves through `RegenProfile`, so every national seed 404s and the whole
regen dossier - lineage, personality, potential band, development - is dark
for what is the bulk of the regen population.

## Why this does not create `regen_profiles` rows

`RegenProfile` carries three mandatory foreign keys:

    player_id             -> ingestion_players.id   (unique, NOT NULL)
    linked_unique_card_id -> player_cards.id        (unique, NOT NULL)
    generated_for_club_id -> club_profiles.id       (NOT NULL)

Materialising a real profile row per seed therefore means creating one
tradable `ingestion_players` row and one mintable `player_cards` row for each
of the ~12k depth seeds, plus clubs to own them. That injects the national
depth pool into the live economy: seeds are deliberately `national_pool_only`
and non-tradable, and this repo has already had to delete 273k orphaned regen
read-model rows once after a non-idempotent generator did something similar.

So the profile is stored **on the seed**, as a snapshot of the same
`RegenProfileView` the engine already produces, and the showcase endpoint
serves it. Seeds gain real profile data and a working dossier; no player, card
or club rows are created, and nothing becomes tradable that was not before.

Making seeds into first-class tradable regens is a separate economic decision
and is deliberately not taken here.
"""

from __future__ import annotations

from random import Random
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.regen_ecosystem import NationalRegenSeed
from app.schemas.regen_core import RegenProfileView
from app.services.regen_service import RegenClubContext, RegenGenerationEngine

#: Where the snapshot lives on the seed row. Kept out of `personality_seed_json`
#: because `regen_universe/service.py` already reads a specific shape there.
PROFILE_SNAPSHOT_KEY = "profile_snapshot"

#: Bumped when the snapshot shape changes so a backfill can be re-run.
PROFILE_SNAPSHOT_VERSION = 1


def build_seed_profile_view(seed: NationalRegenSeed) -> RegenProfileView:
    """Generate the full profile for ``seed``, deterministically.

    The RNG is keyed on the seed's own immutable ``seed_key``, so the same seed
    always produces the same profile no matter when or where this runs. The
    fields the seed already publishes - name, age, position, ratings, growth
    curve, country - are then written back over the generated ones, because the
    seed row is the source of truth for anything already on screen. A dossier
    that disagreed with the card it was opened from would be worse than none.
    """
    settings = get_settings()
    engine = RegenGenerationEngine(settings)
    context = RegenClubContext(
        country_code=seed.country_code,
        region_name=str((seed.metadata_json or {}).get("region_name") or "") or None,
        city_name=str((seed.metadata_json or {}).get("city_name") or "") or None,
        youth_coaching=68.0,
        training_level=66.0,
        academy_level=70.0,
        academy_investment=64.0,
        first_team_gsi=65.0,
        club_reputation=62.0,
        competition_quality=65.0,
        manager_youth_development=67.0,
        urbanicity="urban",
    )
    rng = Random(f"seed-profile:{seed.seed_key}")
    view = engine._build_regen(
        club_id=f"national-pool-{seed.country_code.lower()}",
        generation_source="national_pool",
        club_context=context,
        age=int(seed.age),
        used_names=set(),
        rng=rng,
        current_gsi_override=int(seed.current_rating),
    )

    # Reconcile with what the seed already shows.
    payload: dict[str, Any] = view.model_dump(mode="json")
    payload["display_name"] = seed.display_name
    payload["age"] = int(seed.age)
    payload["primary_position"] = seed.primary_position
    payload["secondary_positions"] = list(seed.secondary_positions_json or [])
    payload["current_rating"] = int(seed.current_rating)
    payload["current_gsi"] = int(seed.current_rating)
    payload["potential"] = int(seed.potential_rating)
    payload["growth_curve"] = float(seed.growth_curve)
    payload["birth_country_code"] = seed.country_code
    payload["status"] = seed.status
    payload["regen_id"] = seed.id
    payload["id"] = seed.id
    # A seed has no player row, and saying so is the point: the dossier renders
    # it, but nothing downstream may treat it as a tradable player id.
    payload["player_id"] = None
    # Nor does it have a minted card. The engine hands back a fresh card id for
    # a card it never created; keeping that would be a dangling reference to a
    # row that does not exist, so it is blanked rather than persisted.
    payload["linked_unique_card_id"] = ""
    payload["club_id"] = f"national-pool-{seed.country_code.lower()}"
    # The engine stamps wall-clock times into the profile and into its own
    # bookkeeping. Persisted, that would make an idempotent backfill rewrite a
    # different snapshot on every run. Anchor to the seed's own creation time
    # and drop the engine's internal log, which is not profile data.
    payload["generated_at"] = (
        seed.created_at.isoformat() if seed.created_at is not None else None
    )
    payload["metadata"] = {
        "source": "national_seed_snapshot",
        "seed_key": seed.seed_key,
        "rarity_tier": seed.rarity_tier,
        "age_band": seed.age_band,
    }

    # The bands must bracket the values the seed publishes, or the dossier
    # would show a potential ceiling below the potential on the card.
    current_band = dict(payload.get("current_ability_range") or {})
    payload["current_ability_range"] = {
        "minimum": min(int(current_band.get("minimum", seed.current_rating)), int(seed.current_rating)),
        "maximum": max(int(current_band.get("maximum", seed.current_rating)), int(seed.current_rating)),
    }
    potential_band = dict(payload.get("potential_range") or {})
    payload["potential_range"] = {
        "minimum": min(int(potential_band.get("minimum", seed.potential_rating)), int(seed.potential_rating)),
        "maximum": max(int(potential_band.get("maximum", seed.potential_rating)), int(seed.potential_rating)),
    }

    # Personality: prefer whatever the original seeding run actually stored, so
    # a backfill never contradicts values that have already been shown.
    original = dict(seed.personality_seed_json or {})
    personality = dict(payload.get("personality") or {})
    for key in ("temperament", "ambition", "resilience", "work_rate", "media_appetite"):
        if isinstance(original.get(key), int):
            personality[key] = int(original[key])
    payload["personality"] = personality

    story_seed = dict(original.get("story_seed") or {})
    if story_seed:
        payload["story_seed"] = story_seed

    return RegenProfileView.model_validate(payload)


class RegenSeedProfileService:
    """Persists and reads the profile snapshot on national regen seeds."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def snapshot_for(seed: NationalRegenSeed) -> dict[str, Any] | None:
        """The stored profile snapshot, or None when the seed has none yet."""
        metadata = dict(seed.metadata_json or {})
        snapshot = metadata.get(PROFILE_SNAPSHOT_KEY)
        if not isinstance(snapshot, dict):
            return None
        profile = snapshot.get("profile")
        return profile if isinstance(profile, dict) else None

    @staticmethod
    def attach_snapshot(seed: NationalRegenSeed, view: RegenProfileView) -> None:
        """Write ``view`` onto ``seed`` as its profile snapshot.

        Reassigns ``metadata_json`` rather than mutating it in place: it is a
        plain JSON column, so an in-place mutation is not seen as dirty by the
        session and would silently not persist.
        """
        metadata = dict(seed.metadata_json or {})
        metadata[PROFILE_SNAPSHOT_KEY] = {
            "version": PROFILE_SNAPSHOT_VERSION,
            "profile": view.model_dump(mode="json"),
        }
        seed.metadata_json = metadata

    def ensure_profile(self, seed: NationalRegenSeed) -> RegenProfileView:
        """Return the seed's profile, generating and storing it if absent."""
        stored = self.snapshot_for(seed)
        if stored is not None:
            try:
                return RegenProfileView.model_validate(stored)
            except Exception:
                # A snapshot written by an older shape is regenerated rather
                # than served half-parsed.
                pass
        view = build_seed_profile_view(seed)
        self.attach_snapshot(seed, view)
        return view

    def backfill(self, *, limit: int | None = None, regenerate: bool = False) -> dict[str, int]:
        """Give every seed without a profile snapshot one.

        Idempotent by default: a seed that already carries a current snapshot
        is skipped, so the job can be re-run safely. Pass ``regenerate`` to
        rewrite existing snapshots after a version bump.
        """
        stmt = select(NationalRegenSeed).order_by(NationalRegenSeed.id.asc())
        if limit is not None:
            stmt = stmt.limit(limit)
        summary = {"scanned": 0, "written": 0, "skipped_existing": 0, "failed": 0}
        for seed in self.session.scalars(stmt):
            summary["scanned"] += 1
            if not regenerate and self.snapshot_for(seed) is not None:
                summary["skipped_existing"] += 1
                continue
            try:
                view = build_seed_profile_view(seed)
                self.attach_snapshot(seed, view)
                summary["written"] += 1
            except Exception:
                summary["failed"] += 1
        return summary
