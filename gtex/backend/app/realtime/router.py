from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.auth.dependencies import get_current_user
from app.auth.security import TokenError, decode_access_token
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.realtime.schemas import (
    MatchGatewaySnapshotView,
    MatchGatewayView,
    RealtimeStatusView,
    WalletGatewaySnapshotView,
    WalletGatewayView,
    WalletRealtimeBalanceView,
    WalletRealtimeFraudCaseView,
    WalletRealtimeLedgerEntryView,
)
from app.realtime.service import commentary_topic, match_topic
from app.risk_ops_engine.service import RiskOpsService
from app.wallets.service import WalletService

router = APIRouter(tags=["realtime"])
realtime_router = APIRouter(prefix="/realtime", tags=["realtime"])


@realtime_router.get("/status", response_model=RealtimeStatusView)
def get_realtime_status(request: Request) -> RealtimeStatusView:
    return RealtimeStatusView.model_validate(request.app.state.realtime.snapshot())


@realtime_router.get("/wallet/gateway", response_model=WalletGatewayView)
def get_wallet_gateway(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> WalletGatewayView:
    snapshot = _build_wallet_gateway_snapshot(request.app, current_user.id)
    return WalletGatewayView(
        channel=snapshot.channel,
        websocket_path="/realtime/wallet/stream",
        snapshot=snapshot,
    )


@realtime_router.get("/matches/{match_id}/gateway", response_model=MatchGatewayView)
def get_match_gateway(
    match_id: str,
    request: Request,
    _current_user: User = Depends(get_current_user),
) -> MatchGatewayView:
    snapshot = _build_match_gateway_snapshot(request.app, match_id)
    return MatchGatewayView(
        channel=snapshot.channel,
        websocket_path=f"/realtime/matches/{match_id}/stream",
        snapshot=snapshot,
    )


@realtime_router.websocket("/stream")
async def realtime_stream(websocket: WebSocket) -> None:
    user_id, token_provided = _resolve_websocket_user_id(websocket)
    requested_topics = _requested_topics(websocket)
    if token_provided and user_id is None:
        await websocket.close(code=4401)
        return
    if user_id is None and _requires_authenticated_scope(requested_topics):
        await websocket.close(code=4401)
        return
    await _run_realtime_stream(
        websocket,
        user_id=user_id,
        topics=requested_topics,
    )


@realtime_router.websocket("/wallet/stream")
async def stream_wallet_updates(websocket: WebSocket) -> None:
    user_id, _token_provided = _resolve_websocket_user_id(websocket)
    if user_id is None:
        await websocket.close(code=4401)
        return
    await _run_realtime_stream(websocket, user_id=user_id, topics=("wallet",))


@realtime_router.websocket("/matches/{match_id}/stream")
async def stream_match_updates(websocket: WebSocket, match_id: str) -> None:
    user_id, token_provided = _resolve_websocket_user_id(websocket)
    if token_provided and user_id is None:
        await websocket.close(code=4401)
        return
    await _run_realtime_stream(
        websocket,
        user_id=user_id,
        topics=(match_topic(match_id), commentary_topic(match_id)),
    )


@router.websocket("/ws/match/{match_id}")
async def stream_live_match_events(websocket: WebSocket, match_id: str) -> None:
    user_id, token_provided = _resolve_websocket_user_id(websocket)
    if token_provided and user_id is None:
        await websocket.close(code=4401)
        return
    await _run_realtime_stream(
        websocket,
        user_id=user_id,
        topics=(match_topic(match_id), commentary_topic(match_id)),
    )


@router.websocket("/ws/matches/{match_id}")
async def stream_live_match_events_plural_alias(websocket: WebSocket, match_id: str) -> None:
    await stream_live_match_events(websocket, match_id)


async def _run_realtime_stream(
    websocket: WebSocket,
    *,
    user_id: str | None,
    topics: tuple[str, ...],
    send_initial_ack: bool = True,
) -> None:
    hub = websocket.scope["app"].state.realtime
    client_id = await hub.connect(websocket, user_id=user_id, topics=topics)
    try:
        active_topics = await hub.subscribe(client_id, topics=())
        if topics and send_initial_ack:
            await websocket.send_json(
                {
                    "type": "subscription_ack",
                    "data": {"topics": list(active_topics)},
                }
            )
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            text = message.get("text")
            if text is None:
                continue
            command = _decode_command(text)
            command_type = str(command.get("type") or "").strip().lower()
            if command_type == "ping" or text.strip().lower() == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
                continue
            if command_type == "subscribe":
                active_topics = await hub.subscribe(client_id, topics=_topics_from_command(command))
                await websocket.send_json({"type": "subscription_ack", "data": {"topics": list(active_topics)}})
                continue
            if command_type == "unsubscribe":
                active_topics = await hub.unsubscribe(client_id, topics=_topics_from_command(command))
                await websocket.send_json({"type": "subscription_ack", "data": {"topics": list(active_topics)}})
    except WebSocketDisconnect:
        return
    finally:
        await hub.disconnect(client_id)


def _decode_command(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        return {}
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return {"type": text.lower()}
    return decoded if isinstance(decoded, dict) else {}


def _topics_from_command(command: dict[str, Any]) -> tuple[str, ...]:
    topics = command.get("topics")
    if isinstance(topics, list):
        return tuple(str(item).strip() for item in topics if str(item).strip())
    data = command.get("data")
    if isinstance(data, dict):
        nested_topics = data.get("topics")
        if isinstance(nested_topics, list):
            return tuple(str(item).strip() for item in nested_topics if str(item).strip())
    return ()


def _requested_topics(websocket: WebSocket) -> tuple[str, ...]:
    raw_topics: list[str] = []
    raw_topics.extend(websocket.query_params.getlist("topic"))
    csv_topics = websocket.query_params.get("topics")
    if csv_topics:
        raw_topics.extend(item.strip() for item in csv_topics.split(","))
    return tuple(dict.fromkeys(item for item in raw_topics if item))


def _requires_authenticated_scope(topics: tuple[str, ...]) -> bool:
    return any(topic == "wallet" or topic.startswith("wallet:") for topic in topics)


def _resolve_websocket_user_id(websocket: WebSocket) -> tuple[str | None, bool]:
    token = websocket.query_params.get("token")
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", maxsplit=1)[1].strip()
    if token is None or not token.strip():
        return None, False
    try:
        payload = decode_access_token(token.strip())
    except TokenError:
        return None, True
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        return None, True
    session_factory = getattr(websocket.scope["app"].state, "session_factory", None)
    if session_factory is None:
        return None, True
    with session_factory() as session:
        user = session.get(User, subject)
        if user is None or not user.is_active:
            return None, True
        return user.id, True


def _build_wallet_gateway_snapshot(app, user_id: str) -> WalletGatewaySnapshotView:
    session_factory = getattr(app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Wallet gateway is unavailable.")

    realtime = app.state.realtime
    wallet_service = WalletService(event_publisher=getattr(app.state, "event_publisher", None))
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found.")

        balances: list[WalletRealtimeBalanceView] = []
        for unit in (LedgerUnit.CREDIT, LedgerUnit.COIN):
            summary = wallet_service.get_wallet_summary(session, user, currency=unit)
            balances.append(
                WalletRealtimeBalanceView(
                    unit=unit.value,
                    available_balance=summary.available_balance,
                    reserved_balance=summary.reserved_balance,
                    total_balance=summary.total_balance,
                )
            )

        ledger_page = wallet_service.list_ledger_entries_for_user(session, user, page=1, page_size=8)
        recent_ledger = [
            WalletRealtimeLedgerEntryView(
                entry_id=entry.id,
                transaction_id=entry.transaction_id,
                account_code=entry.account.code if entry.account is not None else entry.account_id,
                amount=entry.amount,
                unit=entry.unit.value if hasattr(entry.unit, "value") else str(entry.unit),
                reason=entry.reason.value if hasattr(entry.reason, "value") else str(entry.reason),
                source_tag=entry.source_tag.value if hasattr(entry.source_tag, "value") else str(entry.source_tag),
                reference=entry.reference,
                created_at=entry.created_at,
            )
            for entry in ledger_page.items
        ]

        risk_service = RiskOpsService(session)
        fraud_cases = [
            WalletRealtimeFraudCaseView(
                id=item.id,
                case_key=item.case_key,
                fraud_type=item.fraud_type,
                severity=item.severity.value if hasattr(item.severity, "value") else str(item.severity),
                status=item.status.value if hasattr(item.status, "value") else str(item.status),
                confidence_score=item.confidence_score,
                created_at=item.created_at,
            )
            for item in risk_service.list_fraud_cases(user_id=user.id, limit=5)
        ]
        metrics = realtime.snapshot()
        return WalletGatewaySnapshotView(
            user_id=user.id,
            channel=realtime.wallet_channel(user.id),
            balances=balances,
            recent_ledger=recent_ledger,
            risk_overview=risk_service.get_user_overview(user),
            recent_fraud_cases=fraud_cases,
            websocket_connections=metrics.active_wallet_connections,
            delivered_messages=metrics.delivered_messages,
        )


def _build_match_gateway_snapshot(app, match_id: str) -> MatchGatewaySnapshotView:
    realtime = app.state.realtime
    metrics = realtime.snapshot()
    return MatchGatewaySnapshotView(
        match_id=match_id,
        channel=realtime.match_channel(match_id),
        latest_cursor=0,
        websocket_connections=metrics.active_match_connections,
        delivered_messages=metrics.delivered_messages,
    )


router.include_router(realtime_router)

__all__ = ["router"]
