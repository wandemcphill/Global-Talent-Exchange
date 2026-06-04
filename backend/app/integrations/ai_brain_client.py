from __future__ import annotations

import json
import os
from dataclasses import dataclass
from threading import Thread
from typing import Any
from urllib import error, parse, request

from app.core.events import DomainEvent
from app.core.serialization import make_json_safe


@dataclass(frozen=True, slots=True)
class AiBrainConfig:
    enabled: bool
    base_url: str
    api_key: str
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "AiBrainConfig":
        base_url = (os.getenv("AI_BRAIN_BASE_URL") or "").strip().rstrip("/")
        api_key = (os.getenv("AI_BRAIN_API_KEY") or "").strip()
        return cls(
            enabled=_truthy(os.getenv("AI_BRAIN_ENABLED")) and bool(base_url) and bool(api_key),
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=_timeout_seconds(os.getenv("AI_BRAIN_TIMEOUT_SECONDS")),
        )


class AiBrainEventBridge:
    def __init__(self, config: AiBrainConfig | None = None) -> None:
        self.config = config or AiBrainConfig.from_env()

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def handle_event(self, event: DomainEvent) -> None:
        if not self.enabled:
            return
        payload = domain_event_to_ai_payload(event)
        if payload is None:
            return
        Thread(target=self._emit_payload, args=(payload,), daemon=True).start()

    def emit_event(self, event: DomainEvent) -> bool:
        if not self.enabled:
            return False
        payload = domain_event_to_ai_payload(event)
        if payload is None:
            return False
        return self._emit_payload(payload)

    def _emit_payload(self, payload: dict[str, Any]) -> bool:
        trace_id = str(payload["metadata"].get("trace_id") or payload["idempotency_key"])
        return self._request_json("POST", "/events", payload, trace_id=trace_id) is not None

    def get_trust_score(self, actor_id: str, trace_id: str | None = None) -> dict[str, Any] | None:
        if not self.enabled or not actor_id.strip():
            return None
        query = parse.urlencode({"app": "gtex", "user_id": actor_id.strip()})
        return self._request_json("GET", f"/ai/trust/score?{query}", None, trace_id=trace_id)

    def semantic_search(
        self,
        query: str,
        documents: list[dict[str, Any]],
        *,
        user_id: str | None = None,
        limit: int = 10,
        trace_id: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled or not query.strip():
            return None
        payload = {
            "app": "gtex",
            "query": query,
            "user_id": user_id,
            "limit": limit,
            "documents": documents,
        }
        return self._request_json("POST", "/ai/search/semantic", payload, trace_id=trace_id)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        *,
        trace_id: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            body = (
                json.dumps(make_json_safe(payload), separators=(",", ":")).encode("utf-8")
                if payload is not None
                else None
            )
            req = request.Request(
                f"{self.config.base_url}{path}",
                data=body,
                method=method,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.config.api_key,
                    "X-Trace-Id": trace_id or "gtex-ai-brain",
                },
            )
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                if not 200 <= int(response.status) < 300:
                    return None
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except (OSError, error.URLError, error.HTTPError, TimeoutError, ValueError):
            return None


def create_ai_brain_event_bridge_from_env() -> AiBrainEventBridge | None:
    bridge = AiBrainEventBridge()
    return bridge if bridge.enabled else None


def domain_event_to_ai_payload(event: DomainEvent) -> dict[str, Any] | None:
    actor_id = _actor_id(event)
    if not actor_id:
        return None
    normalized_event = _normalize_event_name(event.name)
    entity_id = _entity_id(event)
    entity_type = _entity_type(event)
    trace_id = _header_text(event.headers, "trace_id") or _header_text(event.headers, "x-trace-id")
    projection_metadata = _projection_metadata(event, actor_id=actor_id, entity_id=entity_id, entity_type=entity_type)

    return {
        "app": "gtex",
        "actor_id": actor_id,
        "actor_type": _actor_type(event),
        "event": normalized_event,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "timestamp": event.occurred_at.isoformat(),
        "metadata": {
            "source": "gtex_event_publisher",
            "domain_event_id": event.event_id,
            "domain_event_name": event.name,
            "producer": event.producer,
            "partition_key": event.partition_key,
            "trace_id": trace_id,
            **projection_metadata,
            "payload": make_json_safe(event.payload),
            "headers": make_json_safe(event.headers),
        },
        "schema_version": 1,
        "idempotency_key": f"gtex:event:{event.event_id}",
    }


def _actor_id(event: DomainEvent) -> str:
    for key in (
        "actor_id",
        "actor_user_id",
        "user_id",
        "fan_id",
        "payer_user_id",
        "recipient_user_id",
        "club_id",
        "owner_club_id",
        "buyer_club_id",
        "seller_club_id",
        "manager_id",
        "scout_id",
        "creator_id",
        "collector_id",
        "buyer_user_id",
        "seller_user_id",
        "bidder_club_id",
        "selling_club_id",
        "from_club_id",
        "to_club_id",
        "player_id",
        "buyer_id",
        "seller_id",
    ):
        value = _payload_text(event.payload, key)
        if value:
            return value
    return str(event.aggregate_id or "").strip()


def _actor_type(event: DomainEvent) -> str | None:
    explicit = _payload_text(event.payload, "actor_type") or _payload_text(event.payload, "role")
    if explicit:
        return explicit[:40]
    aggregate_type = str(event.aggregate_type or "").strip().lower()
    if aggregate_type in {"club", "player", "fan", "manager", "system"}:
        return aggregate_type
    return None


def _entity_id(event: DomainEvent) -> str:
    if event.aggregate_id:
        return str(event.aggregate_id).strip()
    for key in (
        "entity_id",
        "offer_id",
        "bid_id",
        "listing_id",
        "order_id",
        "execution_id",
        "trade_id",
        "payment_id",
        "payout_id",
        "wallet_id",
        "transaction_id",
        "match_id",
        "competition_id",
        "campaign_id",
        "card_id",
        "purchase_id",
        "share_id",
        "contract_id",
        "sponsorship_id",
        "academy_player_id",
        "source_player_id",
        "target_player_id",
        "provider_event_id",
        "reference",
        "player_id",
        "club_id",
    ):
        value = _payload_text(event.payload, key)
        if value:
            return value
    return event.event_id


def _entity_type(event: DomainEvent) -> str | None:
    explicit = event.aggregate_type or _payload_text(event.payload, "entity_type")
    if explicit:
        return str(explicit).strip().lower()[:40]
    name = _normalize_event_name(event.name)
    for prefix, entity_type in (
        ("market_listing", "listing"),
        ("market_offer", "offer"),
        ("market_trade_intent", "listing"),
        ("orders_", "order"),
        ("wallet_", "payment"),
        ("ledger_", "payment"),
        ("payment_", "payment"),
        ("payout_", "payment"),
        ("transfer_", "listing"),
        ("competition_", "competition"),
        ("match_", "match"),
        ("player_", "player"),
        ("club_", "club"),
        ("sponsorship_", "campaign"),
        ("academy_", "player"),
        ("card_", "player_card"),
        ("player_card_", "player_card"),
        ("creator_share_", "share"),
        ("club_sale_", "listing"),
        ("creator_", "creator"),
        ("social_", "social"),
        ("reputation_", "trust"),
        ("referral_", "referral"),
    ):
        if name.startswith(prefix):
            return entity_type
    return None


def _projection_metadata(
    event: DomainEvent,
    *,
    actor_id: str,
    entity_id: str,
    entity_type: str | None,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "actor_id": actor_id,
        "event": _normalize_event_name(event.name),
        "entity_id": entity_id,
    }
    if entity_type:
        output["entity_type"] = entity_type
        output.setdefault(f"{entity_type}_id", entity_id)

    for key in (
        "player_id",
        "club_id",
        "home_club_id",
        "away_club_id",
        "current_club_id",
        "owner_club_id",
        "buyer_club_id",
        "seller_club_id",
        "from_club_id",
        "to_club_id",
        "opponent_club_id",
        "selling_club_id",
        "bidder_club_id",
        "buyer_id",
        "seller_id",
        "buyer_user_id",
        "seller_user_id",
        "payer_user_id",
        "recipient_user_id",
        "user_id",
        "fan_id",
        "manager_id",
        "scout_id",
        "collector_id",
        "creator_id",
        "listing_id",
        "offer_id",
        "bid_id",
        "order_id",
        "execution_id",
        "trade_id",
        "payment_id",
        "payout_id",
        "wallet_id",
        "transaction_id",
        "match_id",
        "competition_id",
        "campaign_id",
        "audience_id",
        "card_id",
        "purchase_id",
        "share_id",
        "contract_id",
        "sponsorship_id",
        "academy_player_id",
        "source_player_id",
        "target_player_id",
        "provider",
        "provider_event_id",
        "rail",
        "reference",
        "currency",
        "amount_minor",
        "price_minor",
        "valuation",
        "valuation_delta",
        "market_value",
        "position",
        "nationality",
        "league",
        "season",
        "match_status",
        "creator_id",
        "asset_id",
        "side",
        "quantity",
        "price",
        "ask_price",
        "cash_amount",
        "amount",
        "notional",
        "status",
        "listing_type",
    ):
        value = event.payload.get(key)
        if value is not None and str(value).strip():
            output.setdefault(key, value)

    if "seller_user_id" in output:
        output.setdefault("seller_id", output["seller_user_id"])
    if "buyer_user_id" in output:
        output.setdefault("buyer_id", output["buyer_user_id"])
    if "asset_id" in output:
        output.setdefault("player_id", output["asset_id"])
    if "bidder_club_id" in output:
        output.setdefault("club_id", output["bidder_club_id"])
    if "selling_club_id" in output:
        output.setdefault("seller_id", output["selling_club_id"])
    if "buyer_club_id" in output:
        output.setdefault("buyer_id", output["buyer_club_id"])
        output.setdefault("club_id", output["buyer_club_id"])
    if "seller_club_id" in output:
        output.setdefault("seller_id", output["seller_club_id"])
    if "from_club_id" in output:
        output.setdefault("seller_id", output["from_club_id"])
    if "to_club_id" in output:
        output.setdefault("buyer_id", output["to_club_id"])
    if "payer_user_id" in output:
        output.setdefault("buyer_id", output["payer_user_id"])
    if "recipient_user_id" in output:
        output.setdefault("seller_id", output["recipient_user_id"])
    if "academy_player_id" in output:
        output.setdefault("player_id", output["academy_player_id"])
    if "source_player_id" in output:
        output.setdefault("player_id", output["source_player_id"])
    return make_json_safe(output)


def _normalize_event_name(name: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "_" for char in str(name or "").strip())
    return "_".join(part for part in normalized.split("_") if part) or "event_recorded"


def _payload_text(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _header_text(headers: dict[str, Any], key: str) -> str | None:
    for candidate in (key, key.lower(), key.upper()):
        value = headers.get(candidate)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _timeout_seconds(value: str | None) -> float:
    try:
        seconds = float(str(value or "").strip())
    except ValueError:
        seconds = 0.8
    return min(10.0, max(0.05, seconds))
