"""Read-only, public-safe club and owner dossiers for GTEX.

Public surfaces are deliberately separate from the authenticated Club HQ
snapshot. They expose football identity and the owner's explicitly requested
public portfolio summary without returning wallet balances, staff wages,
internal notes, or private club records.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_legacy.models import (
    ClubLegacyAsset,
    ClubLegacyCatalogueItem,
    ClubLegacyExecutive,
)
from app.models.club_growth import (
    AcademyProfile,
    AcademyProspect,
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffProfile,
)
from app.models.club_infra import ClubFacility, ClubStadium
from app.models.club_profile import ClubLifecycleStatus, ClubProfile
from app.models.club_trophy import ClubTrophy
from app.models.user import User
from app.owner_console.models import OwnerClubState, OwnerSquadPlayer


class ClubPublicProfileNotFound(LookupError):
    """Raised when a club/owner has no public-facing profile."""


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _preview(category: str | None) -> str | None:
    from app.club_legacy.operations import _preview_file

    if not category:
        return None
    return _preview_file(category)


def _portrait(
    session: Session, player_id: str, player_name: str
) -> str | None:
    try:
        from app.owner_console.storytelling import resolve_player_portrait_url

        return resolve_player_portrait_url(session, player_id, player_name)
    except Exception:
        # Image delivery must not take the public club profile down.
        return None


def _canonical_player_rating(player: Player) -> int | None:
    dna = player.dna_profile if isinstance(player.dna_profile, dict) else {}
    for key in ("current_rating", "overall", "sofifa_overall", "club_rating"):
        value = dna.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return int(round(value))
    return None


def _canonical_player_potential(player: Player) -> int | None:
    if player.potential is not None and player.potential > 0:
        return int(player.potential)
    dna = player.dna_profile if isinstance(player.dna_profile, dict) else {}
    for key in ("potential", "potential_rating", "sofifa_potential"):
        value = dna.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return int(round(value))
    return None


def _player_age(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def _public_player_card(
    session: Session, player: dict[str, Any] | None
) -> dict[str, Any] | None:
    if player is None:
        return None
    return {
        "id": player["id"],
        "name": player["name"],
        "position": player["position"],
        "age": player["age"],
        "rating": player["rating"],
        "potential": player["potential"],
        "is_regen": player["is_regen"],
        "portrait_url": _portrait(
            session, player["portrait_source_id"], player["name"]
        ),
    }


def _asset_summary(session: Session, asset: ClubLegacyAsset) -> dict[str, Any] | None:
    item = session.get(ClubLegacyCatalogueItem, asset.catalogue_id)
    if item is None:
        return None
    return {
        "name": item.name,
        "category": item.category,
        "value": str(item.price),
        "edition_number": asset.edition_number,
        "preview_file": _preview(item.category),
        "fallback_label": item.fallback_label,
        "supply_cap": item.supply_cap,
    }


def _person_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        for key in ("display_name", "displayName", "name", "full_name", "manager_name"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _owner_summary(session: Session, owner_id: str) -> dict[str, Any]:
    owner = session.get(User, owner_id)
    clubs = session.scalars(
        select(ClubProfile)
        .where(ClubProfile.owner_user_id == owner_id)
        .where(ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED)
        .order_by(ClubProfile.created_at.asc())
    ).all()
    owned_assets = session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.owner_class == "owner",
            ClubLegacyAsset.owner_ref == owner_id,
            ClubLegacyAsset.status == "owned",
        )
    ).all()
    net_worth: str | None = None
    try:
        # Return only the aggregate requested for the public owner persona page;
        # do not expose component wallet/cash balances.
        from app.club_legacy.full.phase3 import owner_net_worth

        net_worth = owner_net_worth(session, owner_id).get("net_worth")
    except Exception:
        # Partial public identity remains usable if the optional legacy economy
        # has not been initialized for this user.
        net_worth = None

    return {
        "id": owner_id,
        "display_name": (
            getattr(owner, "display_name", None)
            or getattr(owner, "username", None)
            or "GTEX Club Owner"
            if owner is not None
            else "GTEX Club Owner"
        ),
        "club_count": len(clubs),
        "public_clubs": [
            {
                "id": club.id,
                "name": club.club_name,
                "short_name": club.short_name,
                "slug": club.slug,
                "city": club.city_name,
                "country_code": club.country_code,
                "crest_url": club.crest_asset_ref,
                "primary_color": club.primary_color,
                "secondary_color": club.secondary_color,
            }
            for club in clubs
            if club.visibility == "public"
        ],
        "net_worth": net_worth,
        "net_worth_currency": "GTX",
        "luxury_asset_count": len(owned_assets),
        "profile_path": f"/owner/public/profile/{owner_id}",
    }


def public_club_profile(session: Session, club_id: str) -> dict[str, Any]:
    """Return a rich public club dossier, never the owner-only v2 snapshot."""
    club = session.get(ClubProfile, club_id)
    if (
        club is None
        or club.visibility != "public"
        or _value(club.lifecycle_status) == ClubLifecycleStatus.ARCHIVED_GENERATED.value
    ):
        raise ClubPublicProfileNotFound("public_club_profile_not_found")

    stadium = session.scalar(select(ClubStadium).where(ClubStadium.club_id == club.id))
    facilities = session.scalar(
        select(ClubFacility).where(ClubFacility.club_id == club.id)
    )
    academy = session.scalar(
        select(AcademyProfile).where(AcademyProfile.club_id == club.id)
    )
    active_prospect_filter = (
        AcademyProspect.club_id == club.id,
        AcademyProspect.status.notin_(("released", "poached")),
    )
    prospect_count = int(
        session.scalar(
            select(func.count(AcademyProspect.id)).where(*active_prospect_filter)
        )
        or 0
    )
    prospects = session.scalars(
        select(AcademyProspect)
        .where(*active_prospect_filter)
        .order_by(AcademyProspect.potential.desc(), AcademyProspect.age.asc())
        .limit(3)
    ).all()
    academy_facility_level = None
    if facilities is not None:
        academy_facility_level = int(facilities.academy_level)
    elif academy is not None:
        academy_facility_level = int(academy.level)

    canonical_players = session.scalars(
        select(Player)
        .where(Player.current_club_profile_id == club.id)
        .order_by(Player.normalized_position.asc(), Player.full_name.asc())
        .limit(60)
    ).all()
    squad_by_id: dict[str, dict[str, Any]] = {}
    for player in canonical_players:
        squad_by_id[player.id] = {
            "id": player.id,
            "name": player.canonical_display_name or player.full_name,
            "position": player.normalized_position or player.position,
            "age": _player_age(player.date_of_birth),
            "rating": _canonical_player_rating(player),
            "potential": _canonical_player_potential(player),
            "is_regen": not bool(player.is_real_player),
            "portrait_source_id": player.id,
        }

    legacy_squad = session.scalars(
        select(OwnerSquadPlayer)
        .where(OwnerSquadPlayer.club_id == club.id)
        .where(OwnerSquadPlayer.status.in_(("active", "listed")))
        .order_by(OwnerSquadPlayer.rating.desc(), OwnerSquadPlayer.potential.desc())
        .limit(60)
    ).all()
    for player in legacy_squad:
        linked_player_id = (player.player_ref or "").strip()
        linked = squad_by_id.get(linked_player_id) if linked_player_id else None
        if linked is not None:
            if linked["rating"] is None and player.rating is not None:
                linked["rating"] = int(round(player.rating))
            if linked["potential"] is None and player.potential is not None:
                linked["potential"] = int(round(player.potential))
            linked["portrait_source_id"] = player.id
            continue
        squad_by_id[player.id] = {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": int(player.age) if player.age is not None else None,
            "rating": int(round(player.rating)) if player.rating is not None else None,
            "potential": (
                int(round(player.potential))
                if player.potential is not None
                else None
            ),
            "is_regen": bool(player.is_regen),
            "portrait_source_id": player.id,
        }

    squad_players = sorted(
        squad_by_id.values(),
        key=lambda player: (
            player["rating"] is not None,
            player["rating"] or 0,
            player["potential"] or 0,
        ),
        reverse=True,
    )[:60]
    best_player = max(
        squad_players,
        key=lambda player: (
            player["rating"] or 0,
            player["potential"] or 0,
        ),
        default=None,
    )
    promising_player = max(
        squad_players,
        key=lambda player: (
            player["potential"] or 0,
            -(player["age"] or 100),
            (player["potential"] or 0) - (player["rating"] or 0),
        ),
        default=None,
    )

    people: dict[str, dict[str, Any]] = {}
    assignments = session.execute(
        select(ClubStaffAssignment, ClubStaffContract, ClubStaffProfile)
        .join(
            ClubStaffContract,
            ClubStaffContract.id == ClubStaffAssignment.staff_contract_id,
        )
        .join(
            ClubStaffProfile,
            ClubStaffProfile.id == ClubStaffContract.staff_profile_id,
        )
        .where(
            ClubStaffAssignment.club_id == club.id,
            ClubStaffAssignment.active.is_(True),
            ClubStaffContract.status == "active",
        )
    ).all()
    for assignment, _contract, staff_profile in assignments:
        role_key = assignment.role_key.lower()
        kind = staff_profile.staff_type.lower()
        if (
            "manager" in role_key
            or role_key in {"head_coach", "first_team_manager"}
            or kind == "manager"
        ):
            role = "manager"
        elif "youth" in role_key or "hoyd" in role_key:
            role = "head_of_youth_development"
        elif "general" in role_key or role_key == "gm":
            role = "general_manager"
        elif "coach" in role_key or kind == "coach":
            role = "coach"
        else:
            continue
        people[role] = {
            "role": role,
            "name": staff_profile.display_name,
            "rating": (
                int(staff_profile.rating)
                if staff_profile.rating is not None
                else None
            ),
        }

    # The legacy executive roster is the canonical source for the GM and HOYD
    # roles in clubs that use that feature. Never expose contracts or wages.
    executives = session.scalars(
        select(ClubLegacyExecutive).where(
            ClubLegacyExecutive.club_id == club.id,
            ClubLegacyExecutive.status == "hired",
        )
    ).all()
    for executive in executives:
        role_key = str(executive.role).lower()
        if role_key in {"gm", "general_manager"}:
            role = "general_manager"
        elif role_key in {"hoyd", "head_of_youth_development"}:
            role = "head_of_youth_development"
        elif role_key in {"manager", "first_team_manager"}:
            role = "manager"
        else:
            continue
        people.setdefault(role, {"role": role, "name": executive.name, "rating": None})

    state = session.scalar(
        select(OwnerClubState).where(OwnerClubState.club_id == club.id)
    )
    if "manager" not in people and state is not None:
        name = _person_name(state.manager_json)
        if name:
            people["manager"] = {"role": "manager", "name": name, "rating": None}

    staff_roles = (
        ("manager", "Manager"),
        ("general_manager", "General Manager"),
        ("head_of_youth_development", "Head of Youth Development"),
        ("coach", "First-Team Coach"),
    )
    staff = [
        {
            "role": key,
            "title": title,
            "name": people.get(key, {}).get("name"),
            "rating": people.get(key, {}).get("rating"),
            "appointed": bool(people.get(key, {}).get("name")),
        }
        for key, title in staff_roles
    ]

    # Only assets owned by the club itself are shown in its public fleet.
    club_assets = session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.club_id == club.id,
            ClubLegacyAsset.owner_class == "club",
            ClubLegacyAsset.status == "owned",
        )
    ).all()
    buses = []
    for asset in club_assets:
        row = _asset_summary(session, asset)
        if row is not None and (
            str(row["category"]).lower() in {"coach", "team_transport", "bus"}
            or "coach" in str(row["name"]).lower()
            or "bus" in str(row["name"]).lower()
        ):
            buses.append(row)

    trophies = session.scalars(
        select(ClubTrophy)
        .where(ClubTrophy.club_id == club.id)
        .order_by(ClubTrophy.awarded_at.desc())
        .limit(8)
    ).all()

    owner = _owner_summary(session, club.owner_user_id)
    return {
        "club": {
            "id": club.id,
            "name": club.club_name,
            "short_name": club.short_name,
            "slug": club.slug,
            "description": club.description,
            "crest_url": club.crest_asset_ref,
            "primary_color": club.primary_color,
            "secondary_color": club.secondary_color,
            "accent_color": club.accent_color,
            "country_code": club.country_code,
            "region_name": club.region_name,
            "city_name": club.city_name,
            "founded_year": club.founded_at.year if club.founded_at else None,
            "home_venue_name": club.home_venue_name,
        },
        "owner": owner,
        "stadium": {
            "name": (
                stadium.name
                if stadium is not None
                else (club.home_venue_name or "Stadium details unavailable")
            ),
            "level": int(stadium.level) if stadium is not None else None,
            "capacity": int(stadium.capacity) if stadium is not None else None,
            "theme_key": stadium.theme_key if stadium is not None else None,
            "image_asset": "assets/showroom/arena_imperiale_stadium.webp",
        },
        "facilities": {
            "training_level": (
                int(facilities.training_level) if facilities is not None else None
            ),
            "academy_level": academy_facility_level,
            "medical_level": (
                int(facilities.medical_level) if facilities is not None else None
            ),
            "branding_level": (
                int(facilities.branding_level) if facilities is not None else None
            ),
            "youth_recruitment_level": (
                int(facilities.youth_recruitment_level)
                if facilities is not None
                else None
            ),
            "academy_image_asset": "assets/showroom/apex_performance_campus.webp",
        },
        "academy": {
            "level": int(academy.level) if academy is not None else None,
            "capacity": int(academy.capacity_limit) if academy is not None else None,
            "prospect_count": prospect_count,
            "prospects": [
                {
                    "id": prospect.id,
                    "name": prospect.display_name,
                    "position": prospect.position,
                    "age": int(prospect.age),
                    "potential": int(prospect.potential),
                    "portrait_url": prospect.portrait_asset_ref,
                }
                for prospect in prospects
            ],
        },
        "squad": {
            "player_count": len(squad_players),
            "players": [
                {
                    "id": player["id"],
                    "name": player["name"],
                    "position": player["position"],
                    "age": player["age"],
                    "rating": player["rating"],
                    "potential": player["potential"],
                    "is_regen": player["is_regen"],
                }
                for player in squad_players
            ],
            "best_player": _public_player_card(session, best_player),
            "most_promising_player": _public_player_card(session, promising_player),
        },
        "staff": staff,
        "coach_buses": buses,
        "trophies": [
            {
                "id": trophy.id,
                "name": trophy.trophy_name,
                "competition": trophy.competition_source,
                "season": trophy.season_label,
            }
            for trophy in trophies
        ],
    }


def public_owner_profile(session: Session, owner_user_id: str) -> dict[str, Any]:
    """Public owner persona: clubs, aggregated net worth, and personal assets."""
    owner = session.get(User, owner_user_id)
    if owner is None:
        raise ClubPublicProfileNotFound("public_owner_profile_not_found")
    public_clubs = session.scalars(
        select(ClubProfile)
        .where(
            ClubProfile.owner_user_id == owner_user_id,
            ClubProfile.visibility == "public",
            ClubProfile.lifecycle_status != ClubLifecycleStatus.ARCHIVED_GENERATED,
        )
        .order_by(ClubProfile.created_at.asc())
    ).all()
    if not public_clubs:
        raise ClubPublicProfileNotFound("public_owner_profile_not_found")

    assets = session.scalars(
        select(ClubLegacyAsset).where(
            ClubLegacyAsset.owner_class == "owner",
            ClubLegacyAsset.owner_ref == owner_user_id,
            ClubLegacyAsset.status == "owned",
        )
    ).all()
    public_assets = [
        {
            "name": row["name"],
            "category": row["category"],
            "value": row["value"],
            "edition_number": row["edition_number"],
            "preview_file": row["preview_file"],
            "supply_cap": row["supply_cap"],
        }
        for asset in assets
        if (row := _asset_summary(session, asset)) is not None
    ]
    owner_summary = _owner_summary(session, owner_user_id)
    return {
        **owner_summary,
        "public_clubs": owner_summary["public_clubs"],
        "assets": public_assets,
    }
