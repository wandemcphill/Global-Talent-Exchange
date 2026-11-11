"""Build lifecycle squads from active rentals.

Name-only squads are not a valid entry. Tests that used to send a fabricated
name and rating now rent a real player and let the engine read that rating.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import uuid

from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.national_team_tournament import RentalContract, RentalContractStatus
from app.national_team_engine.schemas import NationalTeamCompetitionEntrySubmitRequest


def reference_date(competition) -> date:
    kickoff = getattr(competition, "kickoff_at", None)
    if kickoff is not None:
        return kickoff.date()
    closes = getattr(competition, "entry_closes_at", None)
    if closes is not None:
        return closes.date()
    return utcnow().date()


def birth_date_for_age(age: int, on: date) -> date:
    return date(on.year - int(age), on.month, min(on.day, 28))


def rent_players_for_squad(
    session,
    *,
    actor,
    competition,
    country_name: str,
    ages: tuple[int, ...],
    ratings: tuple[int, ...],
    positions: tuple[str, ...] | None = None,
) -> list[dict]:
    on = reference_date(competition)
    now = utcnow()
    members: list[dict] = []
    for index, (age, rating) in enumerate(zip(ages, ratings, strict=True)):
        position = positions[index] if positions is not None else "ST"
        player = Player(
            source_provider="test",
            provider_external_id=f"rent-{uuid.uuid4().hex}",
            full_name=f"{country_name} {index + 1}",
            canonical_display_name=f"{country_name} {index + 1}",
            date_of_birth=birth_date_for_age(age, on),
            position=position,
            normalized_position=position,
            is_tradable=True,
            is_real_player=False,
            dna_profile={"gsi": int(rating)},
        )
        session.add(player)
        session.flush()
        session.add(
            RentalContract(
                player_id=player.id,
                user_id=actor.id,
                tournament_id=competition.id,
                start_date=now - timedelta(hours=1),
                end_date=now + timedelta(days=30),
                loan_price_coin=Decimal("10.0000"),
                status=RentalContractStatus.ACTIVE,
            )
        )
        members.append(
            {
                "player_id": player.id,
                "player_name": player.full_name,
                "age": int(age),
                "overall_rating": 99,
                "position": position,
            }
        )
    session.flush()
    return members


def submit_request(
    session,
    *,
    actor,
    competition,
    country_code: str,
    country_name: str,
    ages: tuple[int, ...],
    ratings: tuple[int, ...],
    positions: tuple[str, ...] | None = None,
) -> NationalTeamCompetitionEntrySubmitRequest:
    return NationalTeamCompetitionEntrySubmitRequest(
        country_code=country_code,
        country_name=country_name,
        squad=rent_players_for_squad(
            session,
            actor=actor,
            competition=competition,
            country_name=country_name,
            ages=ages,
            ratings=ratings,
            positions=positions,
        ),
    )
