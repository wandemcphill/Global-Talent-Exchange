from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.ingestion.models import Club, Player, PlayerImageMetadata
from app.models.player_token_market import PlayerShareMarket
from app.market.lifecycle_status import sync_player_lifecycle_and_market_status
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.banded_pricing import (
    SOFIFA_SNAPSHOT_DATE,
    credits_to_naira,
    projected_price_credits,
    resolve_price_tier,
)

from .schemas import PlayerAdminEditRequest, PlayerAdminEditResult, PlayerAdminView

REGEN_SOURCE = "gtex_regen"
LEGEND_GSI_FLOOR = 80


class AdminPlayerError(ValueError):
    pass


class PlayerNotFoundError(AdminPlayerError):
    pass


def calendar_age(dob: date | None, today: date) -> int | None:
    if dob is None:
        return None
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years if years >= 0 else None


def dob_for_game_age(age: int, *, today: date, existing: date | None = None) -> date:
    """Store a game date of birth that shows as `age` on `today`."""
    month = existing.month if existing is not None else today.month
    day = existing.day if existing is not None else today.day
    year = today.year - int(age)
    day = min(day, monthrange(year, month)[1])
    born = date(year, month, day)
    if (born.month, born.day) > (today.month, today.day):
        year -= 1
        day = min(existing.day if existing is not None else day, monthrange(year, month)[1])
        born = date(year, month, day)
    return born


@dataclass(slots=True)
class AdminPlayerService:
    """Admin editing of a player's GSI, market value, club, and status.

    GSI edits recompute the banded price; a direct market_value_credits override
    pins the price instead. Reads/writes the same fields the app displays and trades
    on (dna_profile + player_summary_read_models.current_value_credits).
    """

    def _overall_key(self, player: Player) -> str:
        return "overall" if player.source_provider == REGEN_SOURCE else "sofifa_overall"

    def _potential_key(self, player: Player) -> str:
        return "potential" if player.source_provider == REGEN_SOURCE else "sofifa_potential"

    def _dna(self, player: Player) -> dict:
        return dict(player.dna_profile) if isinstance(player.dna_profile, dict) else {}

    def _read_int(self, dna: dict, *keys: str) -> int | None:
        for key in keys:
            value = dna.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
        return None

    def get_player(self, session: Session, player_id: str) -> PlayerAdminView:
        player = session.get(Player, player_id)
        if player is None:
            raise PlayerNotFoundError(f"Player '{player_id}' not found.")
        return self._view(session, player)

    def list_players(
        self,
        session: Session,
        *,
        search: str | None = None,
        tier: str | None = None,
        source: str | None = None,
        limit: int = 24,
    ) -> list[PlayerAdminView]:
        stmt = select(Player)
        if search and search.strip():
            like = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    Player.full_name.ilike(like),
                    Player.canonical_display_name.ilike(like),
                    Player.id == search.strip(),
                )
            )
        if tier:
            if tier == "regen":
                stmt = stmt.where(Player.source_provider == REGEN_SOURCE)
            else:
                stmt = stmt.where(Player.real_player_tier == tier)
        if source:
            stmt = stmt.where(Player.source_provider == source)
        stmt = stmt.order_by(Player.potential.desc().nullslast(), Player.full_name).limit(max(1, min(limit, 100)))
        return [self._view(session, p) for p in session.scalars(stmt).all()]

    def _apply_image(self, session: Session, player: Player, url: str) -> None:
        url = url.strip()
        dna = self._dna(player)
        dna["portraitUrl"] = url or None
        player.dna_profile = dna
        flag_modified(player, "dna_profile")
        existing = session.scalars(
            select(PlayerImageMetadata).where(
                PlayerImageMetadata.player_id == player.id, PlayerImageMetadata.image_role == "portrait"
            )
        ).first()
        if not url:
            if existing is not None:
                session.delete(existing)
        elif existing is not None:
            existing.source_url = url[:1024]
            existing.source_provider = "admin_override"
            existing.moderation_status = "approved"
            existing.rights_cleared = True
        else:
            session.add(
                PlayerImageMetadata(
                    source_provider="admin_override",
                    provider_external_id=f"admin-{player.id}",
                    player_id=player.id,
                    image_role="portrait",
                    source_url=url[:1024],
                    moderation_status="approved",
                    rights_cleared=True,
                    is_primary=True,
                )
            )
        summary = session.get(PlayerSummaryReadModel, player.id)
        if summary is not None:
            data = dict(summary.summary_json or {})
            if url:
                data["image_url"] = url
                data["portrait_url"] = url
            else:
                data.pop("image_url", None)
                data.pop("portrait_url", None)
            summary.summary_json = data
            flag_modified(summary, "summary_json")

    def edit_player(
        self,
        session: Session,
        player_id: str,
        edits: PlayerAdminEditRequest,
    ) -> PlayerAdminEditResult:
        player = session.get(Player, player_id)
        if player is None:
            raise PlayerNotFoundError(f"Player '{player_id}' not found.")

        changed: list[str] = []
        dna = self._dna(player)
        gsi_touched = False

        if edits.overall is not None:
            dna[self._overall_key(player)] = edits.overall
            dna["current_rating"] = edits.overall
            player.governed_gsi = edits.overall
            gsi_touched = True
            changed.append("overall")
        if edits.potential is not None:
            player.potential = edits.potential
            player.governed_potential_gsi = edits.potential
            dna[self._potential_key(player)] = edits.potential
            dna["potential_rating"] = edits.potential
            gsi_touched = True
            changed.append("potential")
        if edits.age is not None:
            player.date_of_birth = dob_for_game_age(
                edits.age,
                today=datetime.now(UTC).date(),
                existing=player.date_of_birth,
            )
            changed.append("age")
        if edits.club_rating is not None:
            dna["sofifa_club_rating"] = edits.club_rating
            gsi_touched = True
            changed.append("club_rating")
        if gsi_touched:
            player.dna_profile = dna
            flag_modified(player, "dna_profile")

        if edits.real_player_tier is not None:
            player.real_player_tier = edits.real_player_tier or None
            changed.append("real_player_tier")
        if (
            edits.overall is not None
            and player.real_player_tier == "legend"
            and edits.overall < LEGEND_GSI_FLOOR
        ):
            raise AdminPlayerError(f"A legend's GSI cannot be set below {LEGEND_GSI_FLOOR}.")
        if edits.real_world_club_name is not None:
            player.real_world_club_name = edits.real_world_club_name or None
            changed.append("real_world_club_name")
        if edits.image_url is not None:
            self._apply_image(session, player, edits.image_url)
            changed.append("image_url")

        # Move club (or clear to free agent).
        if edits.current_club_id is not None:
            self._move_club(session, player, edits.current_club_id or None)
            changed.append("current_club_id")

        if edits.retire:
            sync_player_lifecycle_and_market_status(session, player, is_retired=True)
            self._move_club(session, player, None)
            changed.append("retire")
        elif edits.is_tradable is not None:
            sync_player_lifecycle_and_market_status(session, player, is_tradable=edits.is_tradable)
            changed.append("is_tradable")

        player.last_synced_at = datetime.now(UTC)
        session.flush()

        summary = session.get(PlayerSummaryReadModel, player.id)
        repriced = False
        if edits.market_value_credits is not None:
            # Direct override wins.
            if summary is not None:
                summary.previous_value_credits = summary.current_value_credits
                summary.current_value_credits = round(float(edits.market_value_credits), 4)
                summary.movement_pct = self._movement(summary.previous_value_credits, summary.current_value_credits)
            market = session.scalars(
                select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id)
            ).first()
            if market is not None:
                market.share_price_coin = round(float(edits.market_value_credits), 4)
            changed.append("market_value_credits")
        elif gsi_touched and summary is not None:
            new_price = self._recompute_price(player)
            summary.previous_value_credits = summary.current_value_credits
            summary.current_value_credits = new_price
            summary.movement_pct = self._movement(summary.previous_value_credits, new_price)
            repriced = True

        session.flush()
        return PlayerAdminEditResult(
            player=self._view(session, player),
            changed_fields=changed,
            repriced=repriced,
        )

    def _recompute_price(self, player: Player) -> float:
        dna = self._dna(player)
        overall = self._read_int(dna, "sofifa_overall", "overall")
        potential = self._read_int(dna, "sofifa_potential", "potential") or player.potential
        club_rating = self._read_int(dna, "sofifa_club_rating")
        anchor = (
            player.created_at.date()
            if player.source_provider == REGEN_SOURCE and player.created_at
            else SOFIFA_SNAPSHOT_DATE
        )
        price, _tier, _ = projected_price_credits(
            overall=overall,
            potential=potential,
            club_rating=club_rating,
            dob=player.date_of_birth,
            ingest_date=anchor,
            as_of=datetime.now(UTC).date(),
        )
        return round(price, 4)

    def _move_club(self, session: Session, player: Player, club_id: str | None) -> None:
        if club_id is None:
            player.current_club_id = None
            return
        club = session.get(Club, club_id)
        if club is None:
            raise AdminPlayerError(f"Club '{club_id}' not found.")
        player.current_club_id = club.id
        if club.current_competition_id:
            player.current_competition_id = club.current_competition_id

    @staticmethod
    def _movement(previous: float | None, current: float | None) -> float:
        prev = float(previous or 0.0)
        curr = float(current or 0.0)
        return round((curr - prev) / prev * 100.0, 4) if prev > 0 else 0.0

    def _view(self, session: Session, player: Player) -> PlayerAdminView:
        dna = self._dna(player)
        overall = player.governed_gsi if player.governed_gsi is not None else self._read_int(
            dna, "sofifa_overall", "overall", "current_rating"
        )
        potential = (
            player.governed_potential_gsi
            if player.governed_potential_gsi is not None
            else self._read_int(dna, "sofifa_potential", "potential", "potential_rating") or player.potential
        )
        club_rating = self._read_int(dna, "sofifa_club_rating")
        summary = session.get(PlayerSummaryReadModel, player.id)
        current_value = float(summary.current_value_credits) if summary is not None else None
        club_name = None
        if player.current_club_id:
            club = session.get(Club, player.current_club_id)
            club_name = club.name if club is not None else None
        return PlayerAdminView(
            player_id=player.id,
            full_name=player.full_name,
            source_provider=player.source_provider,
            is_regen=player.source_provider == REGEN_SOURCE,
            is_real_player=bool(player.is_real_player),
            date_of_birth=player.date_of_birth,
            current_club_id=player.current_club_id,
            current_club_name=club_name,
            current_competition_id=player.current_competition_id,
            overall=overall,
            potential=potential,
            age=calendar_age(player.date_of_birth, datetime.now(UTC).date()),
            club_rating=club_rating,
            is_tradable=bool(player.is_tradable),
            current_value_credits=current_value,
            current_value_naira=credits_to_naira(current_value) if current_value is not None else None,
            price_tier=resolve_price_tier(overall).code if overall is not None else None,
            real_player_tier=player.real_player_tier,
            real_world_club_name=player.real_world_club_name,
            position=player.normalized_position or player.position,
            image_url=dna.get("portraitUrl") or None,
        )
