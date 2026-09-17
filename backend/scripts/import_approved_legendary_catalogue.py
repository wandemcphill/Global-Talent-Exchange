from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory
from app.ingestion.models import Country
from app.legend_catalogue.schema import CatalogueBundle
from app.legend_catalogue.validation import evaluate_release
from app.models.user import User, UserRole
from app.schemas.legendary_player import LegendaryPlayerProfileCreate
from app.services.legendary_player_launch_service import LegendaryPlayerLaunchService


ADMIN_ROLES = frozenset({UserRole.ADMIN, UserRole.SUPER_ADMIN})


def _canonical_country_exists(session, code: str) -> bool:
    normalized = code.strip().upper()
    return session.scalar(
        select(Country.id).where(
            (Country.alpha2_code == normalized)
            | (Country.alpha3_code == normalized)
            | (Country.fifa_code == normalized)
        )
    ) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="Import only an approved GTEX legendary catalogue.")
    parser.add_argument("path")
    parser.add_argument("--target-count", type=int, default=2000)
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--actor-user-id")
    parser.add_argument("--database-url")
    args = parser.parse_args()

    bundle = CatalogueBundle.model_validate_json(Path(args.path).read_text(encoding="utf-8"))
    gate = evaluate_release(bundle, target_count=args.target_count)
    if not gate.ready:
        print(gate.model_dump_json(indent=2))
        raise SystemExit("Catalogue release gate failed; no records imported.")
    if args.activate and not args.actor_user_id:
        raise SystemExit("--actor-user-id is required with --activate")

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    report = {"dry_run": not args.activate, "target_count": args.target_count, "processed": 0, "errors": []}

    with session_factory() as session:
        actor = None
        if args.activate:
            actor = session.scalar(select(User).where(User.id == args.actor_user_id))
            if actor is None:
                raise SystemExit(f"Admin actor {args.actor_user_id!r} was not found")
            if actor.role not in ADMIN_ROLES:
                raise SystemExit(
                    f"Actor {args.actor_user_id!r} has role {actor.role!r}; activation requires ADMIN or SUPER_ADMIN."
                )

        service = LegendaryPlayerLaunchService(session)
        for record in bundle.records:
            try:
                country_code = record.country_code or ""
                if args.activate and not _canonical_country_exists(session, country_code):
                    raise ValueError(f"Canonical country {country_code!r} is not seeded; refusing to fabricate it.")

                profile = LegendaryPlayerProfileCreate(
                    slug=record.source_id.replace("wikidata:", "legend-").lower(),
                    full_name=record.full_name,
                    country_code=country_code,
                    date_of_birth=record.date_of_birth,
                    primary_position=record.primary_position or "",
                    secondary_positions=record.secondary_positions,
                    preferred_foot=record.preferred_foot or "right",
                    historical_height_cm=record.historical_height_cm or 0,
                    signature_traits=record.signature_traits,
                    signature_role=record.signature_role,
                    technical_profile=record.technical_profile,
                    physical_profile=record.physical_profile,
                    mental_profile=record.mental_profile,
                    era=record.era or "",
                    legendary_classification=record.legendary_classification or "icon",
                    is_active=True,
                    is_searchable=True,
                    is_tradable=True,
                    is_rentable=True,
                    is_national_team_eligible=True,
                    portrait_metadata=record.portrait_metadata,
                    source_evidence=[item.model_dump(mode="json") for item in record.source_evidence],
                    football_evidence=[item.model_dump(mode="json") for item in record.football_evidence],
                    editorial_status=record.editorial_status,
                    rights_status=record.rights_status,
                    catalogue_status="approved",
                    source_notes=record.source_notes,
                    metadata={**record.metadata, "catalogue_source_id": record.source_id},
                )
                if args.activate:
                    stored, player, market = service.materialize(profile, actor=actor)
                    stored.catalogue_status = "imported"
                    report.setdefault("imported", []).append(
                        {"source_id": record.source_id, "player_id": player.id, "market_id": market.id}
                    )
                else:
                    report.setdefault("planned", []).append({"source_id": record.source_id, "full_name": record.full_name})
                report["processed"] += 1
            except Exception as exc:  # noqa: BLE001
                report["errors"].append({"source_id": record.source_id, "error": str(exc)})

        if args.activate and not report["errors"]:
            session.commit()
        else:
            session.rollback()

    print(json.dumps(report, indent=2, default=str))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
