"""Tell a holder when football moved the valuation of a player he owns.

This is the last link of the chain that had no producer. Everything before it
existed -- performances are persisted at settlement, form is derived, the bounded
overlay reaches the published valuation on the daily snapshot run -- but nothing
ever told the owner. He had to go and look, which means in practice he never
found out.

Deliberately narrow, because a notification is a claim:

* **Only when matchday is actually responsible.** A snapshot fires here only if
  the overlay was applied with a non-zero adjustment. A valuation that moved for
  some other reason is somebody else's event to raise, not this one's.
* **Only what the audit knows.** The figure reported is the overlay's own
  ``applied_adjustment_pct`` -- matchday's contribution -- never the total
  valuation movement, which has other causes mixed into it. Attributing the whole
  move to football would be exactly the causal overreach the matchday contract
  forbids.
* **Never a price claim.** The message says valuation, and says share price is
  untouched, because it is: matchday cannot write ``share_price_coin``.
* **Idempotent.** The snapshot job is idempotent and its cron can be re-run for
  the same instant. Re-running it must not notify the same holder twice for the
  same ``as_of``.

This writes ``NotificationRecord`` rows, which is the existing store that
``GET /api/notifications`` already reads. It is not a new notification pipeline
and does not introduce delivery, push or websockets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_record import NotificationRecord
from app.models.player_token_market import PlayerShareHolding
from app.value_engine.models import ValueSnapshot

#: The topic these rows carry, so a client can filter them from trade and wallet
#: traffic without parsing messages.
TOPIC = "player_valuation"

TEMPLATE_KEY = "value.matchday.valuation_moved"

RESOURCE_TYPE = "player"

#: Below this, matchday's contribution is not worth interrupting someone for.
#: The overlay's effective bound is 2.4%, so this is a real fraction of the
#: available range rather than an arbitrarily small number.
DEFAULT_MINIMUM_ADJUSTMENT_PCT = 0.005


def _applied_adjustment(audit: dict[str, Any] | None) -> float | None:
    """Matchday's own contribution, or None when it made none.

    Prefers ``applied_adjustment_pct``, which is what the overlay actually put
    into the number after its own clamp, over ``adjustment_pct``, which is what
    the signal asked for. When they differ the applied one is the truth.
    """
    if not audit or audit.get("applied") is not True:
        return None
    raw = audit.get("applied_adjustment_pct", audit.get("adjustment_pct"))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value or None


@dataclass(slots=True)
class MatchdayValueNotificationProducer:
    """Raises one notification per holder per player per snapshot instant."""

    session: Session
    minimum_adjustment_pct: float = DEFAULT_MINIMUM_ADJUSTMENT_PCT

    def publish(self, snapshots: Sequence[ValueSnapshot]) -> int:
        """Notify holders of every player matchday actually moved.

        Returns the number of rows written, which is what the cron logs.
        """
        movements = self._movements(snapshots)
        if not movements:
            return 0

        holdings_by_player = self._holders(movements.keys())
        if not holdings_by_player:
            return 0

        already_sent = self._already_notified(holdings_by_player)

        written = 0
        for player_id, (snapshot, adjustment_pct) in movements.items():
            as_of = snapshot.as_of.isoformat()
            for user_id, share_count in holdings_by_player.get(player_id, ()):
                if (user_id, player_id, as_of) in already_sent:
                    continue
                self.session.add(
                    NotificationRecord(
                        user_id=user_id,
                        topic=TOPIC,
                        template_key=TEMPLATE_KEY,
                        resource_type=RESOURCE_TYPE,
                        resource_id=player_id,
                        message=self._message(snapshot.player_name, adjustment_pct),
                        metadata_json={
                            "player_id": player_id,
                            "player_name": snapshot.player_name,
                            "as_of": as_of,
                            "matchday_adjustment_pct": round(adjustment_pct, 6),
                            "previous_credits": snapshot.previous_credits,
                            "target_credits": snapshot.target_credits,
                            "share_count": share_count,
                            "reason_code": (snapshot.matchday_signal_audit or {}).get("reason_code"),
                            "matches_counted": (snapshot.matchday_signal_audit or {}).get("matches_counted"),
                            "confidence": (snapshot.matchday_signal_audit or {}).get("confidence"),
                            # Stated in the payload as well as the copy, so a
                            # client cannot render this as a price event.
                            "moves_share_price": False,
                        },
                    )
                )
                written += 1

        self.session.flush()
        return written

    @staticmethod
    def _message(player_name: str, adjustment_pct: float) -> str:
        direction = "raised" if adjustment_pct > 0 else "lowered"
        pct = abs(adjustment_pct) * 100
        return (
            f"Matchday form {direction} {player_name}'s valuation by "
            f"{pct:.2f}%. This is a valuation change, not a share price change."
        )[:255]

    def _movements(self, snapshots: Sequence[ValueSnapshot]) -> dict[str, tuple[ValueSnapshot, float]]:
        movements: dict[str, tuple[ValueSnapshot, float]] = {}
        for snapshot in snapshots:
            adjustment = _applied_adjustment(snapshot.matchday_signal_audit)
            if adjustment is None or abs(adjustment) < self.minimum_adjustment_pct:
                continue
            movements[snapshot.player_id] = (snapshot, adjustment)
        return movements

    def _holders(self, player_ids: Iterable[str]) -> dict[str, list[tuple[str, int]]]:
        """Every holder of every moved player, in one read rather than per player."""
        ids = list(player_ids)
        if not ids:
            return {}
        rows = self.session.execute(
            select(
                PlayerShareHolding.player_id,
                PlayerShareHolding.user_id,
                PlayerShareHolding.share_count,
            ).where(
                PlayerShareHolding.player_id.in_(ids),
                PlayerShareHolding.share_count > 0,
            )
        ).all()
        holders: dict[str, list[tuple[str, int]]] = {}
        for player_id, user_id, share_count in rows:
            holders.setdefault(player_id, []).append((user_id, int(share_count)))
        return holders

    def _already_notified(self, holdings_by_player: dict[str, list[tuple[str, int]]]) -> set[tuple[str, str, str]]:
        """(user, player, as_of) triples this producer has already raised.

        Read back rather than enforced by a constraint because the natural key
        lives inside the metadata payload, and adding a unique index to a shared
        notification table for one producer's benefit would be the wrong trade.

        Scoped to exactly the players and users about to be notified. That keeps
        the read selective on a table that grows forever, and avoids bounding it
        by ``created_at``: this table's timestamps are written by the database's
        own ``now()``, which is naive under SQLite and aware under Postgres, so a
        datetime comparison here would behave differently per dialect.
        """
        if not holdings_by_player:
            return set()
        player_ids = list(holdings_by_player)
        user_ids = {user_id for holders in holdings_by_player.values() for user_id, _share_count in holders}
        if not user_ids:
            return set()
        rows = self.session.scalars(
            select(NotificationRecord).where(
                NotificationRecord.topic == TOPIC,
                NotificationRecord.resource_id.in_(player_ids),
                NotificationRecord.user_id.in_(user_ids),
            )
        ).all()
        sent: set[tuple[str, str, str]] = set()
        for row in rows:
            metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            as_of = metadata.get("as_of")
            if row.user_id and row.resource_id and isinstance(as_of, str):
                sent.add((row.user_id, row.resource_id, as_of))
        return sent


__all__ = [
    "DEFAULT_MINIMUM_ADJUSTMENT_PCT",
    "MatchdayValueNotificationProducer",
    "TEMPLATE_KEY",
    "TOPIC",
]
