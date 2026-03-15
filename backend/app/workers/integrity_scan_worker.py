from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.integrity_engine.service import IntegrityEngineService
from backend.app.market.service import MarketEngine
from backend.app.risk_ops_engine.service import RiskOpsService
from backend.app.surveillance.service import SurveillanceService


@dataclass(slots=True)
class IntegrityScanWorker:
    session: Session
    settings: Settings
    market_engine: MarketEngine | None = None

    def run_integrity_scan(self) -> dict[str, Any]:
        results = IntegrityEngineService(self.session).run_scan()
        created = results.get("created_incidents") or []
        RiskOpsService(self.session).log_audit(
            actor_user_id=None,
            action_key="integrity.scan.completed",
            resource_type="integrity_scan",
            resource_id=None,
            detail="Integrity scan completed.",
            metadata_json={
                "created_incidents": len(created),
                "scanned_gifts": results.get("scanned_gifts"),
                "scanned_rewards": results.get("scanned_rewards"),
            },
        )
        return {
            "created_incidents": len(created),
            "scanned_gifts": results.get("scanned_gifts"),
            "scanned_rewards": results.get("scanned_rewards"),
        }

    def run_suspicious_cluster_scan(self) -> dict[str, Any]:
        if self.market_engine is None:
            return {"alerts": 0, "note": "market_engine_unavailable"}
        alerts = SurveillanceService(self.settings).list_suspicious_clusters(self.market_engine)
        for alert in alerts:
            RiskOpsService(self.session).log_audit(
                actor_user_id=None,
                action_key="surveillance.cluster.alert",
                resource_type="suspicious_cluster",
                resource_id=alert.cluster_id,
                detail="Suspicious trading cluster detected.",
                metadata_json={
                    "member_user_ids": list(alert.member_user_ids),
                    "asset_ids": list(alert.asset_ids),
                    "interaction_count": alert.interaction_count,
                    "repeated_pair_count": alert.repeated_pair_count,
                    "has_cycle": alert.has_cycle,
                    "reasons": list(alert.reasons),
                },
            )
        return {"alerts": len(alerts)}


__all__ = ["IntegrityScanWorker"]
