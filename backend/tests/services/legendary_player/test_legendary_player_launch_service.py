from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import load_model_modules
from app.models.base import Base
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User, UserRole
from app.players.token_service import PlayerTokenMarketService
from app.schemas.legendary_player import LegendaryPlayerProfileCreate
from app.services.legendary_player_launch_service import LegendaryPlayerLaunchService
from app.wallets.service import LedgerPosting, WalletService
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit


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
        reference=f"legendary-launch-test-funding:{user.id}",
        actor=user,
    )


def test_legendary_launch_materializes_active_market_and_uses_normal_share_trading() -> None:
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        admin = _user(session, user_id="legend-launch-admin", role=UserRole.ADMIN)
        buyer = _user(session, user_id="legend-launch-buyer", role=UserRole.USER)
        _fund_coin(session, user=buyer, amount=Decimal("1000.0000"))

        profile = LegendaryPlayerProfileCreate(
            slug="legend-kanu-nwankwo",
            full_name="Kanu Nwankwo",
            country_code="NGA",
            primary_position="ST",
            secondary_positions=["CF"],
            preferred_foot="right",
            historical_height_cm=197,
            signature_traits=["Close Control", "Composure", "Link-Up Play"],
            signature_role="Super-Sub Forward",
            technical_profile={"first_touch": 93, "finishing": 91, "dribbling": 88},
            physical_profile={"height": 97, "strength": 82, "stamina": 72},
            mental_profile={"composure": 96, "vision": 90, "flair": 89},
            era="1996-2011",
            legendary_classification="icon",
            is_active=True,
            is_searchable=True,
            is_tradable=True,
            is_rentable=True,
            is_national_team_eligible=True,
        )

        service = LegendaryPlayerLaunchService(session)
        stored_profile, player, market = service.materialize(profile, actor=admin)
        session.commit()

        assert stored_profile.full_name == "Kanu Nwankwo"
        assert player.legendary_profile_id == stored_profile.id
        assert player.is_tradable is True
        assert market.status == "active"
        assert market.player_id == player.id
        assert session.scalar(
            select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id)
        ).id == market.id

        # Re-running the launch path is idempotent and does not create a second market.
        stored_again, player_again, market_again = service.materialize(profile, actor=admin)
        session.commit()
        assert stored_again.id == stored_profile.id
        assert player_again.id == player.id
        assert market_again.id == market.id
        assert session.query(PlayerShareMarket).filter_by(player_id=player.id).count() == 1

        # Normal GTEX share trading is the only market path used after launch.
        trading = PlayerTokenMarketService(session)
        purchase = trading.buy_shares(actor=buyer, player_id=player.id, share_count=5)
        assert purchase["holding"].share_count == 5
        resale = trading.sell_shares(actor=buyer, player_id=player.id, share_count=2)
        assert resale["holding"].share_count == 3
