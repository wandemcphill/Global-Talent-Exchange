from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.economy.service import EconomyConfigService
from backend.app.models.club_infra import ClubFacility, ClubStadium, ClubSupporterHolding, ClubSupporterToken, SupporterTokenStatus
from backend.app.models.club_profile import ClubProfile
from backend.app.models.user import User


class ClubInfraError(ValueError):
    pass


@dataclass(slots=True)
class ClubInfraService:
    session: Session

    def _club_for_user(self, user: User) -> ClubProfile:
        club = self.session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == user.id).order_by(ClubProfile.created_at.asc()))
        if club is None:
            raise ClubInfraError('No club profile exists for this user yet.')
        return club

    def ensure_defaults_for_club(self, club: ClubProfile) -> tuple[ClubStadium, ClubFacility, ClubSupporterToken]:
        stadium = self.session.scalar(select(ClubStadium).where(ClubStadium.club_id == club.id))
        if stadium is None:
            stadium = ClubStadium(club_id=club.id, name=club.home_venue_name or f'{club.club_name} Arena')
            self.session.add(stadium)
        facilities = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club.id))
        if facilities is None:
            facilities = ClubFacility(club_id=club.id, upkeep_cost_fancoin=Decimal('100.0000'))
            self.session.add(facilities)
        token = self.session.scalar(select(ClubSupporterToken).where(ClubSupporterToken.club_id == club.id))
        if token is None:
            symbol = ''.join(ch for ch in (club.short_name or club.club_name).upper() if ch.isalpha())[:4] or 'CLUB'
            token = ClubSupporterToken(
                club_id=club.id,
                token_name=f'{club.club_name} Supporter Share',
                token_symbol=symbol,
                description='Non-financial supporter participation token for polls, club pride, and cosmetic unlocks.',
                metadata_json={'non_financial': True},
            )
            self.session.add(token)
        self.session.flush()
        return stadium, facilities, token

    def bootstrap_existing_clubs(self) -> int:
        clubs = list(self.session.scalars(select(ClubProfile)).all())
        for club in clubs:
            self.ensure_defaults_for_club(club)
        self.session.flush()
        return len(clubs)

    def my_dashboard(self, user: User):
        club = self._club_for_user(user)
        return self.dashboard_for_club(club_id=club.id, viewer=user)

    def dashboard_for_club(self, *, club_id: str, viewer: User | None = None) -> dict[str, object]:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ClubInfraError('Club was not found.')
        stadium, facilities, token = self.ensure_defaults_for_club(club)
        holding = None
        if viewer is not None:
            holding = self.session.scalar(select(ClubSupporterHolding).where(ClubSupporterHolding.club_id == club.id, ClubSupporterHolding.user_id == viewer.id))
        projected_matchday_revenue_coin = self._project_matchday_revenue(stadium=stadium, facilities=facilities)
        projected_gift_ratio = Decimal(stadium.gift_retention_bonus_bps + 10000) / Decimal(10000)
        prestige_index = int(stadium.level * 20 + facilities.branding_level * 10 + facilities.academy_level * 8 + stadium.prestige_bonus_bps / 100)
        insights = [
            f'Stadium capacity sits at {stadium.capacity:,} with level {stadium.level}.',
            f'Projected matchday revenue is about {projected_matchday_revenue_coin} coin before competition-specific multipliers.',
            'Supporter shares are participation-only and do not represent financial securities.',
        ]
        if token.holder_count >= 25:
            insights.append('Supporter token traction is building. Story feed and gifting surfaces should feel stickier.')
        return {
            'club_id': club.id,
            'club_name': club.club_name,
            'stadium': stadium,
            'facilities': facilities,
            'supporter_token': token,
            'my_holding': holding,
            'projected_matchday_revenue_coin': projected_matchday_revenue_coin,
            'projected_gift_retention_ratio': projected_gift_ratio.quantize(Decimal('0.0001')),
            'prestige_index': prestige_index,
            'insights': insights,
        }

    def upgrade_stadium(self, *, actor: User, target_level: int):
        club = self._club_for_user(actor)
        stadium, facilities, _ = self.ensure_defaults_for_club(club)
        if target_level <= stadium.level:
            raise ClubInfraError('Target stadium level must be greater than the current level.')
        pricing = {item.service_key: item for item in EconomyConfigService(self.session).list_service_pricing(active_only=False)}
        price_rule = pricing.get(f'stadium-upgrade-level-{target_level}') or pricing.get('stadium-upgrade-level-1')
        stadium.level = target_level
        stadium.capacity = 5000 + target_level * 2500
        stadium.revenue_multiplier_bps = 10000 + target_level * 450
        stadium.gift_retention_bonus_bps = target_level * 150
        stadium.prestige_bonus_bps = target_level * 200
        if price_rule is not None:
            facilities.upkeep_cost_fancoin = Decimal(facilities.upkeep_cost_fancoin) + Decimal(price_rule.price_fancoin_equivalent) / Decimal('10')
        self.session.flush()
        return self.dashboard_for_club(club_id=club.id, viewer=actor)

    def upgrade_facility(self, *, actor: User, facility_key: str, increment: int):
        club = self._club_for_user(actor)
        _, facilities, _ = self.ensure_defaults_for_club(club)
        field_map = {
            'training': 'training_level',
            'academy': 'academy_level',
            'medical': 'medical_level',
            'branding': 'branding_level',
        }
        attr = field_map.get(facility_key.strip().lower())
        if attr is None:
            raise ClubInfraError('Facility key must be one of training, academy, medical, branding.')
        current = int(getattr(facilities, attr))
        setattr(facilities, attr, min(10, current + increment))
        facilities.upkeep_cost_fancoin = Decimal(facilities.upkeep_cost_fancoin) + Decimal('50.0000') * Decimal(increment)
        self.session.flush()
        return self.dashboard_for_club(club_id=club.id, viewer=actor)

    def support_club(self, *, actor: User, club_id: str, quantity: int):
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ClubInfraError('Club was not found.')
        _, _, token = self.ensure_defaults_for_club(club)
        holding = self.session.scalar(select(ClubSupporterHolding).where(ClubSupporterHolding.club_id == club.id, ClubSupporterHolding.user_id == actor.id))
        created = False
        if holding is None:
            created = True
            holding = ClubSupporterHolding(club_id=club.id, user_id=actor.id, token_balance=0, influence_points=0, is_founding_supporter=token.holder_count < 25)
            self.session.add(holding)
        holding.token_balance += int(quantity)
        holding.influence_points += int(quantity) * 10
        token.circulating_supply += int(quantity)
        token.influence_points += int(quantity) * 10
        if created:
            token.holder_count += 1
        self.session.flush()
        return self.dashboard_for_club(club_id=club.id, viewer=actor)

    def _project_matchday_revenue(self, *, stadium: ClubStadium, facilities: ClubFacility) -> Decimal:
        base = Decimal(stadium.capacity) * Decimal('0.0025')
        multiplier = Decimal(stadium.revenue_multiplier_bps) / Decimal('10000')
        facility_bonus = Decimal(1 + ((facilities.branding_level + facilities.training_level) / 20))
        return (base * multiplier * facility_bonus).quantize(Decimal('0.0001'))
