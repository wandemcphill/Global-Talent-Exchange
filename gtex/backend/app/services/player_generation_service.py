from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import json
import random
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Country, MarketSignal, Player, PlayerSeasonStat, Season
from app.models.player_cards import PlayerMarketValueSnapshot, PlayerStatsSnapshot
from app.players.read_models import PlayerSummaryReadModel
from app.services.squad_assignment_service import SquadAssignmentService
from app.value_engine.read_models import PlayerValueSnapshotRecord


@dataclass(frozen=True, slots=True)
class PlayerSeedGenerationSummary:
    season_stats_created: int
    market_signals_created: int
    stats_snapshots_created: int

    def to_dict(self) -> dict[str, int]:
        return {
            "season_stats_created": self.season_stats_created,
            "market_signals_created": self.market_signals_created,
            "stats_snapshots_created": self.stats_snapshots_created,
        }


@dataclass(frozen=True, slots=True)
class PlayerSeedProjectionSummary:
    player_summaries_ready: int
    market_value_snapshots_created: int
    formation_ready_players: int
    market_visible_players: int
    clubs_with_ready_squads: int
    free_agent_players: int

    def to_dict(self) -> dict[str, int]:
        return {
            "player_summaries_ready": self.player_summaries_ready,
            "market_value_snapshots_created": self.market_value_snapshots_created,
            "formation_ready_players": self.formation_ready_players,
            "market_visible_players": self.market_visible_players,
            "clubs_with_ready_squads": self.clubs_with_ready_squads,
            "free_agent_players": self.free_agent_players,
        }


@dataclass(slots=True)
class PlayerGenerationService:
    squad_assignment_service: SquadAssignmentService = field(default_factory=SquadAssignmentService)

    def seed_supporting_records(
        self,
        session: Session,
        *,
        provider_name: str,
        mode: str,
        random_seed: int,
        as_of: datetime,
        batch_size: int = 5_000,
    ) -> PlayerSeedGenerationSummary:
        ordered_player_ids = self.list_provider_player_ids(session, provider_name=provider_name)
        if not ordered_player_ids:
            return PlayerSeedGenerationSummary(season_stats_created=0, market_signals_created=0, stats_snapshots_created=0)

        seasons_by_competition = {
            season.competition_id: season.id
            for season in session.scalars(
                select(Season)
                .where(Season.source_provider == provider_name, Season.is_current.is_(True))
                .order_by(Season.competition_id.asc())
            )
        }

        season_stats_created = 0
        market_signals_created = 0
        stats_snapshots_created = 0

        for player_ids in self._chunks(ordered_player_ids, batch_size):
            players = list(
                session.scalars(
                    select(Player)
                    .options(
                        selectinload(Player.country),
                        selectinload(Player.current_club),
                        selectinload(Player.current_competition),
                    )
                    .where(Player.id.in_(tuple(player_ids)))
                )
            )
            players.sort(key=lambda item: item.provider_external_id)

            season_rows: list[dict[str, Any]] = []
            market_signal_rows: list[dict[str, Any]] = []
            stats_snapshot_rows: list[dict[str, Any]] = []
            for player in players:
                season_id = seasons_by_competition.get(player.current_competition_id or "")
                payload = self._seed_payload(
                    player=player,
                    mode=mode,
                    random_seed=random_seed,
                    as_of=as_of,
                )
                profile = payload["profile"]

                if season_id is not None:
                    season_rows.append(
                        {
                            "id": str(uuid4()),
                            "source_provider": provider_name,
                            "provider_external_id": f"{player.provider_external_id}:season",
                            "player_id": player.id,
                            "club_id": player.current_club_id,
                            "competition_id": player.current_competition_id,
                            "season_id": season_id,
                            "appearances": payload["appearances"],
                            "starts": payload["starts"],
                            "minutes": payload["minutes"],
                            "goals": payload["goals"],
                            "assists": payload["assists"],
                            "yellow_cards": payload["yellow_cards"],
                            "red_cards": payload["red_cards"],
                            "clean_sheets": payload["clean_sheets"],
                            "saves": payload["saves"],
                            "average_rating": payload["average_rating"],
                            "created_at": as_of,
                            "updated_at": as_of,
                        }
                    )
                    stats_snapshot_rows.append(
                        {
                            "id": str(uuid4()),
                            "player_id": player.id,
                            "as_of": as_of,
                            "competition_id": player.current_competition_id,
                            "season_id": season_id,
                            "source_type": "seed_snapshot",
                            "stats_json": {
                                "appearances": payload["appearances"],
                                "starts": payload["starts"],
                                "minutes": payload["minutes"],
                                "goals": payload["goals"],
                                "assists": payload["assists"],
                                "clean_sheets": payload["clean_sheets"],
                                "saves": payload["saves"],
                                "average_rating": payload["average_rating"],
                                "primary_position": player.position,
                                "secondary_positions": list(profile.secondary_positions),
                                "formation_slots": list(profile.formation_slots),
                                "role_archetype": profile.role_archetype,
                            },
                            "created_at": as_of,
                        }
                    )

                market_signal_rows.extend(
                    self._market_signal_rows(
                        player=player,
                        payload=payload,
                        provider_name=provider_name,
                        mode=mode,
                        as_of=as_of,
                    )
                )

            if season_rows:
                session.execute(insert(PlayerSeasonStat), season_rows)
                season_stats_created += len(season_rows)
            if market_signal_rows:
                session.execute(insert(MarketSignal), market_signal_rows)
                market_signals_created += len(market_signal_rows)
            if stats_snapshot_rows:
                session.execute(insert(PlayerStatsSnapshot), stats_snapshot_rows)
                stats_snapshots_created += len(stats_snapshot_rows)
            session.flush()

        return PlayerSeedGenerationSummary(
            season_stats_created=season_stats_created,
            market_signals_created=market_signals_created,
            stats_snapshots_created=stats_snapshots_created,
        )

    def finalize_seed_views(
        self,
        session: Session,
        *,
        provider_name: str,
        mode: str,
        random_seed: int,
        as_of: datetime,
        batch_size: int = 5_000,
    ) -> PlayerSeedProjectionSummary:
        ordered_player_ids = self.list_provider_player_ids(session, provider_name=provider_name)
        if not ordered_player_ids:
            return PlayerSeedProjectionSummary(
                player_summaries_ready=0,
                market_value_snapshots_created=0,
                formation_ready_players=0,
                market_visible_players=0,
                clubs_with_ready_squads=0,
                free_agent_players=0,
            )

        player_summaries_ready = 0
        market_value_snapshots_created = 0
        formation_ready_players = 0
        market_visible_players = 0
        clubs_with_ready_squads: set[str] = set()
        free_agent_players = 0

        for player_ids in self._chunks(ordered_player_ids, batch_size):
            players = list(
                session.scalars(
                    select(Player)
                    .options(
                        selectinload(Player.country),
                        selectinload(Player.current_club),
                        selectinload(Player.current_competition),
                    )
                    .where(Player.id.in_(tuple(player_ids)))
                )
            )
            players.sort(key=lambda item: item.provider_external_id)
            players_by_id = {player.id: player for player in players}

            season_stats = {
                stat.player_id: stat
                for stat in session.scalars(
                    select(PlayerSeasonStat)
                    .where(PlayerSeasonStat.player_id.in_(tuple(player_ids)))
                    .order_by(PlayerSeasonStat.player_id.asc(), PlayerSeasonStat.updated_at.desc())
                )
            }
            summaries = {
                summary.player_id: summary
                for summary in session.scalars(
                    select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(tuple(player_ids)))
                )
            }
            value_snapshots = {
                snapshot.player_id: snapshot
                for snapshot in session.scalars(
                    select(PlayerValueSnapshotRecord)
                    .where(
                        PlayerValueSnapshotRecord.player_id.in_(tuple(player_ids)),
                        PlayerValueSnapshotRecord.as_of == as_of,
                    )
                    .order_by(PlayerValueSnapshotRecord.player_id.asc())
                )
            }

            session.execute(
                delete(PlayerMarketValueSnapshot).where(
                    PlayerMarketValueSnapshot.player_id.in_(tuple(player_ids)),
                    PlayerMarketValueSnapshot.as_of == as_of,
                )
            )

            market_snapshot_rows: list[dict[str, Any]] = []
            for player_id in player_ids:
                player = players_by_id.get(player_id)
                summary = summaries.get(player_id)
                snapshot = value_snapshots.get(player_id)
                if player is None or summary is None or snapshot is None:
                    continue

                payload = self._seed_payload(
                    player=player,
                    mode=mode,
                    random_seed=random_seed,
                    as_of=as_of,
                )
                profile = payload["profile"]
                season_stat = season_stats.get(player.id)
                summary_payload = dict(summary.summary_json) if isinstance(summary.summary_json, dict) else {}
                summary_payload.update(
                    {
                        "seed_mode": mode,
                        "primary_position": player.position,
                        "secondary_positions": list(profile.secondary_positions),
                        "dominant_foot": player.preferred_foot,
                        "role_archetype": profile.role_archetype,
                        "formation_slots": list(profile.formation_slots),
                        "formation_ready": profile.formation_ready,
                        "squad_eligibility": profile.squad_eligibility,
                        "avatar_seed_token": payload["avatar_seed_token"],
                        "avatar_dna_seed": payload["avatar_dna_seed"],
                        "club_assignment": {
                            "status": "free_agent" if player.current_club_id is None else "club_assigned",
                            "current_club_id": player.current_club_id,
                            "current_club_name": player.current_club.name if player.current_club is not None else None,
                            "current_competition_id": player.current_competition_id,
                            "current_competition_name": player.current_competition.name if player.current_competition is not None else None,
                        },
                        "nationality": self._country_payload(player.country),
                        "season_seed": {
                            "appearances": season_stat.appearances if season_stat is not None else None,
                            "starts": season_stat.starts if season_stat is not None else None,
                            "minutes": season_stat.minutes if season_stat is not None else None,
                            "goals": season_stat.goals if season_stat is not None else None,
                            "assists": season_stat.assists if season_stat is not None else None,
                            "average_rating": season_stat.average_rating if season_stat is not None else None,
                        },
                        "market_visibility": {
                            "eligible": bool(player.is_tradable and snapshot.target_credits > 0),
                            "status": "visible" if player.is_tradable and snapshot.target_credits > 0 else "hidden",
                            "surface_flags": ["player_summary", "market_listing", "simulation_input", "club_squad"],
                        },
                        "seed_metadata": {
                            "provider_name": provider_name,
                            "provider_external_id": player.provider_external_id,
                            "random_seed": random_seed,
                            "as_of": as_of.isoformat(),
                        },
                    }
                )
                summary.summary_json = summary_payload

                market_snapshot_rows.append(
                    {
                        "id": str(uuid4()),
                        "player_id": player.id,
                        "as_of": as_of,
                        "last_trade_price_credits": None,
                        "avg_trade_price_credits": snapshot.target_credits,
                        "volume_24h": 0,
                        "listing_floor_price_credits": snapshot.target_credits,
                        "listing_count": 0,
                        "high_24h_price_credits": snapshot.target_credits,
                        "low_24h_price_credits": snapshot.target_credits,
                        "metadata_json": {
                            "source": "authoritative_value_engine",
                            "authoritative_snapshot_id": snapshot.id,
                            "snapshot_type": snapshot.snapshot_type,
                            "provider_name": provider_name,
                        },
                        "created_at": as_of,
                    }
                )

                player_summaries_ready += 1
                if profile.formation_ready:
                    formation_ready_players += 1
                if summary_payload["market_visibility"]["eligible"]:
                    market_visible_players += 1
                if player.current_club_id is not None:
                    clubs_with_ready_squads.add(player.current_club_id)
                else:
                    free_agent_players += 1

            if market_snapshot_rows:
                session.execute(insert(PlayerMarketValueSnapshot), market_snapshot_rows)
                market_value_snapshots_created += len(market_snapshot_rows)
            session.flush()

        return PlayerSeedProjectionSummary(
            player_summaries_ready=player_summaries_ready,
            market_value_snapshots_created=market_value_snapshots_created,
            formation_ready_players=formation_ready_players,
            market_visible_players=market_visible_players,
            clubs_with_ready_squads=len(clubs_with_ready_squads),
            free_agent_players=free_agent_players,
        )

    def list_provider_player_ids(self, session: Session, *, provider_name: str) -> list[str]:
        return list(
            session.scalars(
                select(Player.id)
                .where(Player.source_provider == provider_name)
                .order_by(Player.provider_external_id.asc())
            )
        )

    def _seed_payload(
        self,
        *,
        player: Player,
        mode: str,
        random_seed: int,
        as_of: datetime,
    ) -> dict[str, Any]:
        age = self._age_on(as_of.date(), player.date_of_birth)
        player_rng = random.Random(self._seed_int(player.provider_external_id, str(random_seed), mode))
        quality_index = self._quality_index(player)
        profile = self.squad_assignment_service.build_profile(
            player_id=player.id,
            primary_position=player.position,
            normalized_position=player.normalized_position,
            preferred_foot=player.preferred_foot,
            age=age,
            current_club_id=player.current_club_id,
        )
        appearances = min(38, max(8, int(10 + (quality_index * 18) + player_rng.randint(0, 8))))
        starts = min(appearances, max(5, appearances - player_rng.randint(0, 6)))
        minutes = max((starts * player_rng.randint(72, 90)) + ((appearances - starts) * player_rng.randint(8, 26)), 540)

        yellow_cards = player_rng.randint(0, 7)
        red_cards = 1 if player_rng.random() < 0.05 else 0
        clean_sheets = 0
        saves = 0
        goals = 0
        assists = 0
        position = player.position or player.normalized_position or "Central Midfielder"
        if position == "Goalkeeper":
            clean_sheets = min(appearances, int((quality_index * 9) + player_rng.randint(3, 12)))
            saves = int((appearances * 1.8) + (quality_index * 22) + player_rng.randint(4, 18))
        elif position == "Centre-Back":
            goals = int((quality_index * 3) + player_rng.randint(0, 3))
            assists = int((quality_index * 2) + player_rng.randint(0, 2))
            clean_sheets = min(appearances, int((quality_index * 8) + player_rng.randint(2, 10)))
        elif position == "Full-Back":
            goals = int((quality_index * 2) + player_rng.randint(0, 2))
            assists = int((quality_index * 5) + player_rng.randint(1, 5))
            clean_sheets = min(appearances, int((quality_index * 7) + player_rng.randint(1, 8)))
        elif position == "Defensive Midfielder":
            goals = int((quality_index * 2) + player_rng.randint(0, 3))
            assists = int((quality_index * 4) + player_rng.randint(1, 5))
        elif position == "Central Midfielder":
            goals = int((quality_index * 4) + player_rng.randint(1, 5))
            assists = int((quality_index * 6) + player_rng.randint(2, 6))
        elif position == "Attacking Midfielder":
            goals = int((quality_index * 6) + player_rng.randint(2, 7))
            assists = int((quality_index * 8) + player_rng.randint(3, 8))
        elif position == "Winger":
            goals = int((quality_index * 8) + player_rng.randint(2, 8))
            assists = int((quality_index * 8) + player_rng.randint(2, 8))
        else:
            goals = int((quality_index * 11) + player_rng.randint(4, 12))
            assists = int((quality_index * 4) + player_rng.randint(0, 5))

        average_rating = round(min(8.8, 6.15 + (quality_index * 1.9) + (player_rng.random() * 0.35)), 2)
        avatar_digest = self._seed_digest(player.provider_external_id, str(random_seed), mode, "avatar")
        return {
            "profile": profile,
            "age": age,
            "appearances": appearances,
            "starts": starts,
            "minutes": minutes,
            "goals": goals,
            "assists": assists,
            "yellow_cards": yellow_cards,
            "red_cards": red_cards,
            "clean_sheets": clean_sheets,
            "saves": saves,
            "average_rating": average_rating,
            "quality_index": quality_index,
            "avatar_seed_token": avatar_digest[:16],
            "avatar_dna_seed": "-".join(
                avatar_digest[offset:offset + 8]
                for offset in range(0, 32, 8)
            ),
        }

    def _market_signal_rows(
        self,
        *,
        player: Player,
        payload: dict[str, Any],
        provider_name: str,
        mode: str,
        as_of: datetime,
    ) -> list[dict[str, Any]]:
        quality_index = float(payload["quality_index"])
        age = int(payload["age"])
        age_bonus = 8 if age <= 21 else 4 if age <= 25 else 0
        player_rng = random.Random(self._seed_int(player.provider_external_id, "signals", mode))
        reference_market_value = round(float(player.market_value_eur or 0.0), 2)
        signals = {
            "reference_market_value_eur": reference_market_value,
            "watchlist_adds": int(6 + (quality_index * 38) + age_bonus + player_rng.randint(0, 8)),
            "shortlist_adds": int(1 + (quality_index * 15) + player_rng.randint(0, 4)),
            "transfer_room_adds": int((quality_index * 9) + player_rng.randint(0, 3)),
            "scouting_activity": int(3 + (quality_index * 10) + player_rng.randint(0, 5)),
            "competition_selection_count": int(5 + (quality_index * 26) + player_rng.randint(0, 10)),
            "transfer_interest_score": round(28 + (quality_index * 48) + player_rng.randint(0, 11), 2),
        }
        rows: list[dict[str, Any]] = []
        for signal_type, score in signals.items():
            rows.append(
                {
                    "id": str(uuid4()),
                    "source_provider": provider_name,
                    "provider_external_id": f"{player.provider_external_id}:signal:{signal_type}",
                    "player_id": player.id,
                    "signal_type": signal_type,
                    "score": score,
                    "as_of": as_of,
                    "notes": json.dumps(
                        {
                            "seeded": True,
                            "seed_mode": mode,
                            "player_position": player.position,
                        }
                    ),
                    "created_at": as_of,
                    "updated_at": as_of,
                }
            )
        return rows

    def _quality_index(self, player: Player) -> float:
        market_value = max(float(player.market_value_eur or 0.0), 0.0)
        competition_strength = 1.0
        if player.current_competition is not None and player.current_competition.competition_strength is not None:
            competition_strength = float(player.current_competition.competition_strength)
        profile_score = max(float(player.profile_completeness_score or 0.88), 0.55)
        raw_score = (market_value / 24_000_000.0) * 0.72
        raw_score += min(competition_strength / 2.0, 0.2)
        raw_score += (profile_score - 0.55) * 0.3
        return round(min(max(raw_score, 0.18), 0.98), 4)

    @staticmethod
    def _age_on(reference_date: date, birth_date: date | None) -> int:
        if birth_date is None:
            return 18
        years = reference_date.year - birth_date.year
        if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
            years -= 1
        return max(years, 15)

    @staticmethod
    def _country_payload(country: Country | None) -> dict[str, str | None]:
        if country is None:
            return {
                "name": None,
                "alpha2_code": None,
                "alpha3_code": None,
                "fifa_code": None,
            }
        return {
            "name": country.name,
            "alpha2_code": country.alpha2_code,
            "alpha3_code": country.alpha3_code,
            "fifa_code": country.fifa_code,
        }

    @staticmethod
    def _chunks(values: list[str], size: int) -> list[list[str]]:
        return [values[index:index + size] for index in range(0, len(values), size)]

    @staticmethod
    def _seed_digest(*parts: str) -> str:
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _seed_int(self, *parts: str) -> int:
        return int(self._seed_digest(*parts)[:12], 16)


__all__ = [
    "PlayerGenerationService",
    "PlayerSeedGenerationSummary",
    "PlayerSeedProjectionSummary",
]
