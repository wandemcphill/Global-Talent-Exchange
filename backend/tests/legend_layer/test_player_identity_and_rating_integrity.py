from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.ingestion.models import Player
from app.market.service import derive_player_attributes
from app.models.base import Base
from app.models.user import User, UserRole
from app.schemas.legendary_player import LegendaryPlayerProfileCreate
from app.services.legendary_player_launch_service import (
    LegendaryPlayerLaunchError,
    LegendaryPlayerLaunchService,
)


def _admin(session, user_id: str = "identity-guard-admin") -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hash",  # pragma: allowlist secret
        role=UserRole.ADMIN,
    )
    session.add(user)
    session.flush()
    return user


def test_current_gsi_rating_is_independent_of_potential() -> None:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        # Real player with current rating 91 and potential 95
        player = Player(
            id="mbappe-real",
            source_provider="sportmonks",
            provider_external_id="mbappe-91",
            full_name="Kylian Mbappé",
            canonical_display_name="Kylian Mbappé",
            date_of_birth=date(1998, 12, 20),
            is_real_player=True,
            is_tradable=True,
            dna_profile={"overall": 91, "current_rating": 91, "potential": 95},
        )
        session.add(player)
        session.commit()

        attributes = derive_player_attributes(player, overall=91)

        # Current rating overall must be 91, NOT potential 95
        assert attributes.overall == 91
        assert attributes.potential == 95
        assert attributes.overall != attributes.potential


def test_historical_dob_preserved_while_in_game_age_is_independent() -> None:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        # Michael Laudrup: historical DOB June 15, 1964; in-game representation: peak Barcelona/Real Madrid era (age 28)
        laudrup = Player(
            id="legend-michael-laudrup",
            source_provider="gtex_legend",
            provider_external_id="michael-laudrup-peak",
            full_name="Michael Laudrup",
            canonical_display_name="Michael Laudrup",
            date_of_birth=date(1964, 6, 15),  # Factual historical DOB
            is_real_player=False,
            is_tradable=True,
            dna_profile={
                "overall": 91,
                "current_rating": 91,
                "potential": 91,
                "in_game_football_age": 28,  # Peak representation age
                "peak_career_period": "1991-1994",
            },
        )
        session.add(laudrup)
        session.commit()

        # Historical DOB must remain factually 1964
        assert laudrup.date_of_birth == date(1964, 6, 15)
        # In-game football age is preserved in DNA profile
        assert laudrup.dna_profile["in_game_football_age"] == 28
        assert laudrup.dna_profile["peak_career_period"] == "1991-1994"


def test_active_under_31_and_accent_insensitive_matching_protects_active_players() -> None:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        admin = _admin(session)

        # Active player: Kylian Mbappé (accented)
        active_mbappe = Player(
            id="active-mbappe-001",
            source_provider="sportmonks",
            provider_external_id="mbappe-active",
            full_name="Kylian Mbappé",
            canonical_display_name="Kylian Mbappé",
            date_of_birth=date(1998, 12, 20),
            is_real_player=True,
            is_tradable=True,
            dna_profile={"overall": 91, "current_rating": 91, "potential": 95},
        )
        # Active player under 31: Gift Orban
        active_orban = Player(
            id="active-orban-001",
            source_provider="sportmonks",
            provider_external_id="orban-active",
            full_name="Gift Orban",
            canonical_display_name="Gift Orban",
            date_of_birth=date(2002, 7, 17),
            is_real_player=True,
            is_tradable=True,
            dna_profile={"overall": 76, "current_rating": 76, "potential": 83},
        )
        session.add(active_mbappe)
        session.add(active_orban)
        session.commit()

        service = LegendaryPlayerLaunchService(session)

        # 1. Attempting to launch "Kylian Mbappe" without accents must be rejected
        profile_unaccented = LegendaryPlayerProfileCreate(
            slug="legend-mbappe-unaccented",
            full_name="Kylian Mbappe",  # Unaccented
            country_code="FRA",
            date_of_birth=date(1998, 12, 20),
            primary_position="ST",
            preferred_foot="right",
            historical_height_cm=178,
            signature_traits=[],
            signature_role=None,
            technical_profile={},
            physical_profile={},
            mental_profile={},
            era="2017-present",
            legendary_classification="icon",
            is_active=True,
            is_searchable=True,
            is_tradable=True,
            is_rentable=True,
            is_national_team_eligible=True,
            portrait_metadata={"is_fictional_non_replicative": True},
            editorial_status="approved",
            rights_status="approved",
            catalogue_status="approved",
        )

        with pytest.raises(LegendaryPlayerLaunchError, match="active real-player identity"):
            service.materialize(profile_unaccented, actor=admin)

        # 2. Attempting to launch "Gift Orban" (under 31) must be rejected
        profile_orban = LegendaryPlayerProfileCreate(
            slug="legend-gift-orban",
            full_name="Gift Orban",
            country_code="NGA",
            date_of_birth=date(2002, 7, 17),
            primary_position="ST",
            preferred_foot="right",
            historical_height_cm=178,
            signature_traits=[],
            signature_role=None,
            technical_profile={},
            physical_profile={},
            mental_profile={},
            era="2022-present",
            legendary_classification="icon",
            is_active=True,
            is_searchable=True,
            is_tradable=True,
            is_rentable=True,
            is_national_team_eligible=True,
            portrait_metadata={"is_fictional_non_replicative": True},
            editorial_status="approved",
            rights_status="approved",
            catalogue_status="approved",
        )

        with pytest.raises(LegendaryPlayerLaunchError, match="active real-player identity"):
            service.materialize(profile_orban, actor=admin)
