from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.competitive_integrity.validation_service import CompetitiveIntegrityValidationService
from app.models.competitive_integrity import Match, CompetitiveMatchStatus
from app.models.player_cards import PlayerCardMomentum
from app.models.risk_ops import SystemEvent, SystemEventSeverity
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerEntry
from app.players.match_learning_service import PlayerMatchLearningService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(slots=True)
class AnalyticsInsightService:
    session: Session

    def agent_learning_summary(self, *, since_days: int = 30) -> dict[str, object]:
        payload = PlayerMatchLearningService(session=self.session).build_admin_summary(since_days=since_days)
        return {
            "mode": "adaptive_heuristics",
            "status": "active",
            "since": payload["since"],
            "analytics": payload,
        }

    def price_predictions(self, *, limit: int = 10) -> list[dict[str, object]]:
        rows = list(
            self.session.scalars(
                select(PlayerCardMomentum)
                .order_by(func.abs(PlayerCardMomentum.momentum_7d_pct).desc(), PlayerCardMomentum.updated_at.desc())
                .limit(limit)
            ).all()
        )
        predictions: list[dict[str, object]] = []
        for row in rows:
            current_price = Decimal(str(row.last_trade_price_credits or Decimal("0.0000")))
            short_term = Decimal(str(row.momentum_7d_pct or Decimal("0.0000")))
            medium_term = Decimal(str(row.momentum_30d_pct or Decimal("0.0000")))
            weighted_move_pct = (short_term * Decimal("0.65")) + (medium_term * Decimal("0.35"))
            predicted_move = (weighted_move_pct / Decimal("100")) * Decimal("0.40")
            predicted_price = (
                current_price * (Decimal("1.0000") + predicted_move)
                if current_price > Decimal("0.0000")
                else None
            )
            confidence = min(0.97, float((abs(short_term) * Decimal("0.02")) + (abs(medium_term) * Decimal("0.01"))))
            rationale: list[str] = []
            if short_term.copy_abs() >= Decimal("10.0000"):
                rationale.append("7d momentum is materially elevated.")
            if medium_term.copy_abs() >= Decimal("15.0000"):
                rationale.append("30d trend confirms sustained movement.")
            if short_term > 0 and medium_term > 0:
                rationale.append("Short and medium trend are aligned upward.")
            elif short_term < 0 and medium_term < 0:
                rationale.append("Short and medium trend are aligned downward.")
            else:
                rationale.append("Signal direction is mixed and should be treated cautiously.")
            predictions.append(
                {
                    "player_id": row.player_id,
                    "current_price": current_price,
                    "predicted_price": None if predicted_price is None else predicted_price.quantize(Decimal("0.0001")),
                    "predicted_direction": "up" if weighted_move_pct >= 0 else "down",
                    "confidence": round(max(confidence, 0.05), 4),
                    "rationale": rationale,
                }
            )
        return predictions

    def user_segments(self) -> dict[str, object]:
        users = list(self.session.scalars(select(User)).all())
        segment_counts: Counter[str] = Counter()
        now = _utcnow()
        for user in users:
            spend_amount = self.session.scalar(
                select(func.coalesce(func.sum(func.abs(LedgerEntry.amount)), 0))
                .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
                .where(
                    LedgerAccount.owner_user_id == user.id,
                    LedgerAccount.kind == LedgerAccountKind.USER,
                    LedgerEntry.amount < 0,
                )
            ) or Decimal("0.0000")
            spend_total = Decimal(str(spend_amount))
            days_since_login = None
            last_login_at = _as_utc(user.last_login_at)
            if last_login_at is not None:
                days_since_login = max(0, (now - last_login_at).days)
            if spend_total >= Decimal("1000.0000"):
                segment = "whales"
            elif spend_total <= Decimal("50.0000"):
                segment = "casuals"
            elif days_since_login is not None and days_since_login >= 14:
                segment = "at_risk"
            else:
                segment = "engaged"
            segment_counts[segment] += 1
        total = max(sum(segment_counts.values()), 1)
        return {
            "generated_at": now,
            "segments": [
                {
                    "segment": segment,
                    "user_count": count,
                    "share": round(count / total, 4),
                }
                for segment, count in sorted(segment_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
        }

    def match_outcome_analytics(self, *, since_days: int = 30) -> dict[str, object]:
        since = _utcnow() - timedelta(days=since_days)
        rows = list(
            self.session.scalars(
                select(Match)
                .where(
                    Match.status == CompetitiveMatchStatus.COMPLETED,
                    Match.completed_at.is_not(None),
                    Match.completed_at >= since,
                )
                .order_by(Match.completed_at.desc())
            ).all()
        )
        match_count = len(rows)
        if not rows:
            return {
                "generated_at": _utcnow(),
                "since": since,
                "matches": 0,
                "avg_total_goals": 0.0,
                "home_win_rate": 0.0,
                "away_win_rate": 0.0,
                "draw_rate": 0.0,
                "upset_rate": 0.0,
            }
        home_wins = 0
        away_wins = 0
        draws = 0
        upsets = 0
        total_goals = 0
        for row in rows:
            payload = dict(row.result_payload or {})
            summary = dict(payload.get("summary") or {})
            home_score = int(summary.get("home_score") or 0)
            away_score = int(summary.get("away_score") or 0)
            total_goals += home_score + away_score
            if home_score > away_score:
                home_wins += 1
            elif away_score > home_score:
                away_wins += 1
            else:
                draws += 1
            if bool(summary.get("upset")):
                upsets += 1
        return {
            "generated_at": _utcnow(),
            "since": since,
            "matches": match_count,
            "avg_total_goals": round(total_goals / match_count, 4),
            "home_win_rate": round(home_wins / match_count, 4),
            "away_win_rate": round(away_wins / match_count, 4),
            "draw_rate": round(draws / match_count, 4),
            "upset_rate": round(upsets / match_count, 4),
        }

    def anomaly_summary(self, *, since_days: int = 30) -> dict[str, object]:
        since = _utcnow() - timedelta(days=since_days)
        rows = list(
            self.session.scalars(
                select(SystemEvent)
                .where(SystemEvent.created_at >= since)
                .order_by(SystemEvent.created_at.desc())
            ).all()
        )
        buckets: Counter[str] = Counter()
        critical_count = 0
        for row in rows:
            event_type = str(row.event_type or "unknown").strip().lower()
            if "anomaly" in event_type:
                buckets["anomaly"] += 1
            elif "fraud" in event_type:
                buckets["fraud"] += 1
            elif "integrity" in event_type or "tamper" in event_type:
                buckets["integrity"] += 1
            else:
                buckets[event_type or "other"] += 1
            if row.severity == SystemEventSeverity.CRITICAL:
                critical_count += 1
        return {
            "generated_at": _utcnow(),
            "since": since,
            "critical_count": critical_count,
            "buckets": [
                {"key": key, "count": value}
                for key, value in sorted(buckets.items(), key=lambda item: (-item[1], item[0]))
            ],
        }

    def integrity_anomaly_scan(self, *, since_days: int = 30) -> dict[str, object]:
        since = _utcnow() - timedelta(days=since_days)
        rows = list(
            self.session.scalars(
                select(Match)
                .where(
                    Match.status == CompetitiveMatchStatus.COMPLETED,
                    Match.completed_at.is_not(None),
                    Match.completed_at >= since,
                )
            ).all()
        )
        service = CompetitiveIntegrityValidationService(self.session)
        flagged = [service.build_match_validation(match.id) for match in rows]
        suspicious = [item for item in flagged if item["tampering_risk"] in {"medium", "high"}]
        return {
            "generated_at": _utcnow(),
            "since": since,
            "matches_scanned": len(rows),
            "flagged_matches": len(suspicious),
            "top_findings": suspicious[:10],
        }


__all__ = ["AnalyticsInsightService"]
