from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.gift_transaction import GiftTransaction
from backend.app.models.integrity import IntegrityIncident, IntegrityScore
from backend.app.models.reward_settlement import RewardSettlement
from backend.app.models.user import User


@dataclass(slots=True)
class IntegrityEngineService:
    session: Session

    def _ensure_score(self, user_id: str) -> IntegrityScore:
        score = self.session.scalar(select(IntegrityScore).where(IntegrityScore.user_id == user_id))
        if score is None:
            score = IntegrityScore(user_id=user_id)
            self.session.add(score)
            self.session.flush()
        return score

    def _risk_level_for(self, score_value: Decimal) -> str:
        if score_value < Decimal("40"):
            return "critical"
        if score_value < Decimal("60"):
            return "high"
        if score_value < Decimal("80"):
            return "medium"
        return "low"

    def _register_incident(self, *, user_id: str, incident_type: str, severity: str, title: str, description: str, score_delta: Decimal, metadata_json: dict | None = None) -> IntegrityIncident:
        incident = IntegrityIncident(
            user_id=user_id,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            score_delta=score_delta,
            metadata_json=metadata_json or {},
        )
        self.session.add(incident)
        score = self._ensure_score(user_id)
        score.score = Decimal(score.score) + Decimal(score_delta)
        if score.score < Decimal("0"):
            score.score = Decimal("0")
        score.incident_count = int(score.incident_count) + 1
        score.risk_level = self._risk_level_for(Decimal(score.score))
        score.metadata_json = {**(score.metadata_json or {}), "last_incident_type": incident_type}
        self.session.flush()
        return incident

    def register_incident_once(
        self,
        *,
        user_id: str,
        incident_type: str,
        subject: str,
        severity: str,
        title: str,
        description: str,
        score_delta: Decimal,
        metadata_json: dict | None = None,
    ) -> IntegrityIncident | None:
        if self._incident_exists(user_id=user_id, incident_type=incident_type, subject=subject):
            return None
        payload = metadata_json or {}
        payload = {**payload, "subject": subject}
        return self._register_incident(
            user_id=user_id,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            score_delta=score_delta,
            metadata_json=payload,
        )

    def run_scan(self, *, repeated_gift_threshold: int = 3, reward_cluster_threshold: int = 3, lookback_limit: int = 200) -> dict[str, list[IntegrityIncident] | int]:
        created: list[IntegrityIncident] = []
        gifts = list(self.session.scalars(select(GiftTransaction).order_by(GiftTransaction.created_at.desc()).limit(lookback_limit)).all())
        gift_pairs = Counter((item.sender_user_id, item.recipient_user_id) for item in gifts)
        for (sender_id, recipient_id), count in gift_pairs.items():
            if count >= repeated_gift_threshold:
                if not self._incident_exists(user_id=sender_id, incident_type="repeated_gift_pair", subject=f"{sender_id}:{recipient_id}"):
                    created.append(self._register_incident(
                        user_id=sender_id,
                        incident_type="repeated_gift_pair",
                        severity="high" if count >= repeated_gift_threshold + 2 else "medium",
                        title="Repeated gifting pair detected",
                        description=f"User sent {count} recent gifts to the same recipient, which may suggest coordinated farming.",
                        score_delta=Decimal("-12.50"),
                        metadata_json={"pair": [sender_id, recipient_id], "count": count, "subject": f"{sender_id}:{recipient_id}"},
                    ))
        rewards = list(self.session.scalars(select(RewardSettlement).order_by(RewardSettlement.created_at.desc()).limit(lookback_limit)).all())
        reward_users = Counter(item.user_id for item in rewards)
        for user_id, count in reward_users.items():
            if count >= reward_cluster_threshold:
                if not self._incident_exists(user_id=user_id, incident_type="dense_reward_cluster", subject=user_id):
                    created.append(self._register_incident(
                        user_id=user_id,
                        incident_type="dense_reward_cluster",
                        severity="high" if count >= reward_cluster_threshold + 2 else "medium",
                        title="Dense reward cluster detected",
                        description=f"User received {count} recent reward settlements, which requires review for abuse or duplicate payouts.",
                        score_delta=Decimal("-10.00"),
                        metadata_json={"count": count, "subject": user_id},
                    ))
        return {"created_incidents": created, "scanned_gifts": len(gifts), "scanned_rewards": len(rewards)}

    def _incident_exists(self, *, user_id: str, incident_type: str, subject: str) -> bool:
        stmt = select(IntegrityIncident).where(
            IntegrityIncident.user_id == user_id,
            IntegrityIncident.incident_type == incident_type,
            IntegrityIncident.status == "open",
        )
        for item in self.session.scalars(stmt).all():
            if (item.metadata_json or {}).get("subject") == subject:
                return True
        return False

    def get_score_for_user(self, *, user: User) -> IntegrityScore:
        return self._ensure_score(user.id)

    def list_incidents_for_user(self, *, user: User, limit: int = 50) -> list[IntegrityIncident]:
        return list(self.session.scalars(select(IntegrityIncident).where(IntegrityIncident.user_id == user.id).order_by(IntegrityIncident.created_at.desc()).limit(limit)).all())

    def resolve_incident(self, *, incident_id: str, actor: User, resolution_note: str) -> IntegrityIncident:
        incident = self.session.get(IntegrityIncident, incident_id)
        if incident is None:
            raise ValueError("Integrity incident was not found.")
        incident.status = "resolved"
        incident.resolved_by_user_id = actor.id
        incident.resolution_note = resolution_note.strip()
        self.session.flush()
        return incident
