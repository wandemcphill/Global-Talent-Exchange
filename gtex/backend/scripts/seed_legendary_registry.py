"""Validate and seed the factual Legendary Player launch registry.

Usage: PYTHONPATH=. python scripts/seed_legendary_registry.py registry.json --actor-user-id <admin-id>
"""

from __future__ import annotations

import argparse

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.legend_layer.registry import LegendaryRegistry, seed_legendary_registry
from app.models.user import User


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry")
    parser.add_argument("--actor-user-id", required=True)
    args = parser.parse_args()
    registry = LegendaryRegistry.from_file(args.registry)
    load_model_modules()
    session_factory = create_session_factory(create_database_engine())
    with session_factory() as session:
        actor = session.get(User, args.actor_user_id)
        if actor is None:
            raise SystemExit("actor user not found")
        summary = seed_legendary_registry(session, registry=registry, actor=actor)
        session.commit()
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
