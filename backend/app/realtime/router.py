from __future__ import annotations

import asyncio
import time

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
from app.realtime.websocket_gateway import get_match_stream_websocket_gateway
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
        websocket_path=f"/ws/match/{match_id}",
        snapshot=snapshot,
    )


@realtime_router.websocket("/wallet/stream")
async def stream_wallet_updates(websocket: WebSocket) -> None:
    user_id = _resolve_websocket_user_id(websocket)
    if user_id is None:
        await websocket.close(code=4401)
        return

    app = websocket.scope["app"]
    realtime = app.state.realtime
    channel = realtime.wallet_channel(user_id)
    await websocket.accept()
    realtime.register_wallet_connection()
    cursor = realtime.wallet_latest_cursor(user_id)
    snapshot = _build_wallet_gateway_snapshot(app, user_id)
    await websocket.send_json(
        {
            "channel": channel,
            "kind": "snapshot",
            "payload": snapshot.model_dump(mode="json"),
        }
    )
    realtime.record_wallet_delivery()
    last_heartbeat = time.monotonic()
    try:
        while True:
            events, cursor = realtime.wallet_events_since(user_id, cursor)
            if events:
                await websocket.send_json(
                    {
                        "channel": channel,
                        "kind": "events",
                        "payload": events,
                    }
                )
                realtime.record_wallet_delivery()
                snapshot = _build_wallet_gateway_snapshot(app, user_id)
                await websocket.send_json(
                    {
                        "channel": channel,
                        "kind": "snapshot",
                        "payload": snapshot.model_dump(mode="json"),
                    }
                )
                realtime.record_wallet_delivery()
                last_heartbeat = time.monotonic()
            elif time.monotonic() - last_heartbeat >= 15:
                await websocket.send_json(
                    {
                        "channel": channel,
                        "kind": "heartbeat",
                        "payload": {"user_id": user_id},
                    }
                )
                realtime.record_wallet_delivery()
                last_heartbeat = time.monotonic()
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
    finally:
        realtime.unregister_wallet_connection()
    await websocket.close()


@realtime_router.websocket("/matches/{match_id}/stream")
async def stream_match_updates(websocket: WebSocket, match_id: str) -> None:
    user_id = _resolve_websocket_user_id(websocket)
    if user_id is None:
        await websocket.close(code=4401)
        return
    del user_id

    app = websocket.scope["app"]
    realtime = app.state.realtime
    channel = realtime.match_channel(match_id)
    await websocket.accept()
    realtime.register_match_connection()
    cursor = realtime.match_latest_cursor(match_id)
    snapshot = _build_match_gateway_snapshot(app, match_id)
    await websocket.send_json(
        {
            "channel": channel,
            "kind": "snapshot",
            "payload": snapshot.model_dump(mode="json"),
        }
    )
    realtime.record_match_delivery()
    last_heartbeat = time.monotonic()
    try:
        while True:
            events, cursor = realtime.match_events_since(match_id, cursor)
            if events:
                await websocket.send_json(
                    {
                        "channel": channel,
                        "kind": "events",
                        "payload": events,
                    }
                )
                realtime.record_match_delivery()
                snapshot = _build_match_gateway_snapshot(app, match_id)
                await websocket.send_json(
                    {
                        "channel": channel,
                        "kind": "snapshot",
                        "payload": snapshot.model_dump(mode="json"),
                    }
                )
                realtime.record_match_delivery()
                last_heartbeat = time.monotonic()
            elif time.monotonic() - last_heartbeat >= 15:
                await websocket.send_json(
                    {
                        "channel": channel,
                        "kind": "heartbeat",
                        "payload": {"match_id": match_id},
                    }
                )
                realtime.record_match_delivery()
                last_heartbeat = time.monotonic()
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
    finally:
        realtime.unregister_match_connection()
    await websocket.close()


@router.websocket("/ws/match/{match_id}")
async def stream_live_match_events(websocket: WebSocket, match_id: str) -> None:
    app = websocket.scope["app"]
    realtime = app.state.realtime
    gateway = get_match_stream_websocket_gateway(app)

    subscription = await gateway.connect(websocket, match_id)
    realtime.register_match_connection()
    try:
        await websocket.send_json(subscription)
        realtime.record_match_delivery()
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            text = (message.get("text") or "").strip().lower()
            if text == "ping":
                await websocket.send_json({"type": "pong", "match_id": match_id})
                realtime.record_match_delivery()
    except WebSocketDisconnect:
        return
    finally:
        await gateway.disconnect(websocket, match_id)
        realtime.unregister_match_connection()


def _resolve_websocket_user_id(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", maxsplit=1)[1].strip()
    if token is None or not token.strip():
        return None
    try:
        payload = decode_access_token(token.strip())
    except TokenError:
        return None
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        return None
    session_factory = getattr(websocket.scope["app"].state, "session_factory", None)
    if session_factory is None:
        return None
    with session_factory() as session:
        user = session.get(User, subject)
        if user is None or not user.is_active:
            return None
        return user.id


def _build_wallet_gateway_snapshot(app, user_id: str) -> WalletGatewaySnapshotView:
    session_factory = getattr(app.state, "session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Wallet gateway is unavailable.")

    realtime = app.state.realtime
    wallet_service = WalletService()
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
        latest_cursor=realtime.match_latest_cursor(match_id),
        websocket_connections=metrics.active_match_connections,
        delivered_messages=metrics.delivered_messages,
    )


router.include_router(realtime_router)

__all__ = ["router"]
