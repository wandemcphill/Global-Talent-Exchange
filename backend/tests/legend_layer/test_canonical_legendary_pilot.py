from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.market.service import MarketPlayerQueryService
from app.models.base import Base
from app.models.legendary_player import LegendaryPlayerProfile
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.players.token_service import PlayerTokenMarketService
from app.schemas.legendary_player import LegendaryPlayerProfileCreate
from app.services.legendary_player_launch_service import LegendaryPlayerLaunchError, LegendaryPlayerLaunchService
from app.wallets.service import LedgerPosting, WalletService
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit

PILOT_PROFILES = [
    ("Edson Arantes do Nascimento", "BRA", "ST", "right", 173, "1950s/1960s/1970s"),
    ("Diego Armando Maradona", "ARG", "AM", "left", 165, "1980s/1990s"),
    ("Hendrik Johannes Cruijff", "NLD", "AM", "right", 178, "1970s"),
    ("Franz Anton Beckenbauer", "DEU", "CB", "right", 181, "1960s/1970s"),
    ("Lev Ivanovich Yashin", "RUS", "GK", "right", 189, "1950s/1960s"),
    ("Zinedine Yazid Zidane", "FRA", "AM", "right", 185, "1990s/2000s"),
    ("Paolo Cesare Maldini", "ITA", "LB", "left", 186, "1980s/1990s/2000s"),
    ("Ferenc Puskás", "HUN", "ST", "left", 172, "1950s/1960s"),
    ("Samuel Eto'o Fils", "CMR", "ST", "right", 179, "2000s/2010s"),
    ("George Tawlon Manneh Oppong Ousman Weah", "LBR", "ST", "right", 185, "1990s"),
    ("Abedi Ayew", "GHA", "AM", "left", 174, "1980s/1990s"),
    ("Augustine Azuka Okocha", "NGA", "AM", "right", 175, "1990s/2000s"),
    ("Mohamed Mohamed Mohamed Abou Trika", "EGY", "AM", "right", 182, "2000s"),
    ("Cha Bum-kun", "KOR", "ST", "right", 179, "1970s/1980s"),
    ("Hidetoshi Nakata", "JPN", "AM", "right", 175, "1990s/2000s"),
    ("Park Ji-sung", "KOR", "CM", "right", 178, "2000s/2010s"),
    ("Paulino Alcántara Riestra", "PHL", "ST", "left", 170, "1910s/1920s"),
    ("Manuel Francisco dos Santos", "BRA", "RW", "right", 169, "1950s/1960s"),
    ("Arthur Antunes Coimbra", "BRA", "AM", "right", 172, "1970s/1980s"),
    ("Mario Alberto Kempes", "ARG", "ST", "left", 182, "1970s/1980s"),
    ("Elías Ricardo Figueroa Brander", "CHL", "CB", "right", 180, "1970s"),
    ("Hugo Sánchez Márquez", "MEX", "ST", "left", 175, "1980s/1990s"),
    ("Sir Robert Charlton", "ENG", "AM", "right", 173, "1950s/1960s/1970s"),
    ("Gheorghe Hagi", "ROU", "AM", "left", 172, "1980s/1990s"),
    ("Lothar Herbert Matthäus", "DEU", "CM", "right", 174, "1980s/1990s/2000s"),
]


def _user(session, *, user_id: str, role: UserRole) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hash",
        role=role,
    )
    session.add(user)
    session.flush()
    WalletService().ensure_default_accounts(session, user)
    return user


def _fund_coin(session, *, user: User, amount: Decimal) -> None:
    wallet = WalletService()
    wallet.append_transaction(
        session,
        postings=[
            LedgerPosting(account=wallet.get_user_account(session, user, LedgerUnit.COIN), amount=amount),
            LedgerPosting(account=wallet.ensure_platform_account(session, LedgerUnit.COIN), amount=-amount),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
        reference=f"canonical-legendary-pilot-funding:{user.id}",
        actor=user,
    )


def _profile(name: str, country: str, position: str, foot: str, height: int, era: str) -> LegendaryPlayerProfileCreate:
    return LegendaryPlayerProfileCreate(
        slug="legend-" + name.lower().replace(" ", "-").replace("'", "").replace(".", ""),
        full_name=name,
        country_code=country,
        primary_position=position,
        preferred_foot=foot,
        historical_height_cm=height,
        era=era,
        signature_traits=[],
        signature_role=None,
        technical_profile={},
        physical_profile={},
        mental_profile={},
        legendary_classification="icon",
        is_active=True,
        is_searchable=True,
        is_tradable=True,
        is_rentable=True,
        is_national_team_eligible=True,
        portrait_metadata={
            "avatar_system": "gtex_fictional_avatar_v1",
            "is_fictional_non_replicative": True,
            "test_fixture_only": True,
        },
        source_evidence=[
            {
                "provider": "pilot_test",
                "uri": "https://example.invalid/gtex-legendary-pilot",
                "claim_types": ["technical_fixture"],
            }
        ],
        football_evidence=[
            {
                "provider": "pilot_test",
                "uri": "https://example.invalid/gtex-legendary-pilot",
                "claim_types": ["technical_fixture"],
            }
        ],
        editorial_status="approved",
        rights_status="approved",
        catalogue_status="approved",
        source_notes="Canonical technical pilot fixture only. This test record is not production factual data.",
        metadata={"pilot_only": True, "test_fixture_only": True},
    )


def _build_session():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, Session


def test_canonical_25_player_pilot_is_active_searchable_and_tradeable() -> None:
    assert len(PILOT_PROFILES) == 25
    _, Session = _build_session()

    with Session() as session:
        admin = _user(session, user_id="canonical-pilot-admin", role=UserRole.ADMIN)
        buyer = _user(session, user_id="canonical-pilot-buyer", role=UserRole.USER)
        _fund_coin(session, user=buyer, amount=Decimal("5000.0000"))

        launch = LegendaryPlayerLaunchService(session)
        request = [_profile(*record) for record in PILOT_PROFILES]
        materialized = [launch.materialize(item, actor=admin) for item in request]
        session.commit()

        assert len(materialized) == 25
        assert len({item[0].id for item in materialized}) == 25
        assert len({item[1].id for item in materialized}) == 25
        assert len({item[2].id for item in materialized}) == 25
        assert all(player.is_tradable for _, player, _ in materialized)
        assert all(market.status == "active" for _, _, market in materialized)

        market_count = (
            session.scalar(select(PlayerShareMarket).count()) if False else session.query(PlayerShareMarket).count()
        )
        assert market_count == 25

        # The ordinary search surface resolves the canonical player, not a pilot-only registry row.
        ok = MarketPlayerQueryService(session).list_players(search="Edson Arantes do Nascimento")
        assert [item.player_id for item in ok.items] == [materialized[0][1].id]

        # Standard buy/sell works immediately after launch.
        player = materialized[11][1]
        trading = PlayerTokenMarketService(session)
        purchase = trading.buy_shares(actor=buyer, player_id=player.id, share_count=3)
        assert purchase["holding"].share_count == 3
        resale = trading.sell_shares(actor=buyer, player_id=player.id, share_count=1)
        assert resale["holding"].share_count == 2

        # Replaying the same 25 seeds produces no duplicate players or markets.
        replayed = [launch.materialize(item, actor=admin) for item in request]
        session.commit()
        assert [entry[1].id for entry in replayed] == [entry[1].id for entry in materialized]
        assert [entry[2].id for entry in replayed] == [entry[2].id for entry in materialized]
        assert session.query(PlayerShareMarket).count() == 25


def test_launch_boundary_rejects_unapproved_catalogue_profile_before_write() -> None:
    _, Session = _build_session()

    with Session() as session:
        admin = _user(session, user_id="canonical-pilot-approval-admin", role=UserRole.ADMIN)
        profile = _profile(*PILOT_PROFILES[0]).model_copy(update={"editorial_status": "editorial_review"})
        launch = LegendaryPlayerLaunchService(session)

        with pytest.raises(LegendaryPlayerLaunchError, match="not editorially approved"):
            launch.materialize(profile, actor=admin)

        assert session.query(LegendaryPlayerProfile).count() == 0
        assert session.query(PlayerShareMarket).count() == 0
