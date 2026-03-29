from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.auth.dependencies import get_current_user
from app.broadcast_network.schemas import BroadcastChannelView, BroadcastHomeView, ChannelSessionView
from app.broadcast_network.service import (
    BroadcastNetworkError,
    ensure_broadcast_network_runtime,
)
from app.models.user import User

router = APIRouter(prefix="/api/broadcast", tags=["broadcast-network"])


def _raise_not_found(exc: BroadcastNetworkError) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/channels", response_model=list[BroadcastChannelView])
def list_channels(request: Request, _: User = Depends(get_current_user)) -> list[BroadcastChannelView]:
    return ensure_broadcast_network_runtime(request.app).list_channels()


@router.post("/channels/{channel_id}/join", response_model=ChannelSessionView)
def join_channel(channel_id: str, request: Request, current_user: User = Depends(get_current_user)) -> ChannelSessionView:
    runtime = ensure_broadcast_network_runtime(request.app)
    try:
        return runtime.join_channel(channel_id=channel_id, user_id=current_user.id)
    except BroadcastNetworkError as exc:
        _raise_not_found(exc)


@router.get("/home", response_model=BroadcastHomeView)
def read_broadcast_home(request: Request, _: User = Depends(get_current_user)) -> BroadcastHomeView:
    return ensure_broadcast_network_runtime(request.app).home()


@router.websocket("/channels/{channel_id}/stream")
async def stream_channel(channel_id: str, websocket: WebSocket, session_id: str) -> None:
    app = websocket.scope["app"]
    runtime = ensure_broadcast_network_runtime(app)
    try:
        initial = runtime.refresh_channel_session(channel_id=channel_id, session_id=session_id, hydrate_match_session=True)
    except BroadcastNetworkError:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    await websocket.send_json({"kind": "channel_snapshot", "payload": initial.model_dump(mode="json")})
    previous_slot_id = initial.current_program.slot_id if initial.current_program is not None else None
    previous_match_id = initial.current_program.match_id if initial.current_program is not None else None
    previous_focus = initial.director_focus.model_dump(mode="json") if initial.director_focus is not None else None
    disconnected = False
    try:
        while True:
            update = runtime.refresh_channel_session(channel_id=channel_id, session_id=session_id)
            current_slot_id = update.current_program.slot_id if update.current_program is not None else None
            current_match_id = update.current_program.match_id if update.current_program is not None else None
            current_focus = update.director_focus.model_dump(mode="json") if update.director_focus is not None else None
            if current_slot_id != previous_slot_id:
                await websocket.send_json({"kind": "program_update", "payload": update.model_dump(mode="json")})
                previous_slot_id = current_slot_id
            if current_match_id != previous_match_id:
                switched = runtime.refresh_channel_session(channel_id=channel_id, session_id=session_id, hydrate_match_session=True)
                await websocket.send_json({"kind": "auto_switch", "payload": switched.model_dump(mode="json")})
                await websocket.send_json(
                    {
                        "kind": "audio_manifest_update",
                        "payload": runtime.audio_manifest(channel_id=channel_id, session_id=session_id).model_dump(mode="json"),
                    }
                )
                previous_match_id = current_match_id
            if current_focus != previous_focus and update.director_focus is not None:
                await websocket.send_json({"kind": "director_focus", "payload": update.director_focus.model_dump(mode="json")})
                previous_focus = current_focus
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        disconnected = True
    finally:
        runtime.finalize_watch_session(session_id=session_id, channel_id=channel_id)
        if not disconnected:
            await websocket.close()


@router.websocket("/channels/{channel_id}/audio/stems/stream")
async def stream_channel_audio(channel_id: str, websocket: WebSocket, session_id: str) -> None:
    app = websocket.scope["app"]
    runtime = ensure_broadcast_network_runtime(app)
    try:
        initial = runtime.refresh_channel_session(channel_id=channel_id, session_id=session_id)
    except BroadcastNetworkError:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    cursor = 0
    current_match_id = initial.current_program.match_id if initial.current_program is not None else None
    await websocket.send_json(
        {
            "kind": "audio_manifest_update",
            "payload": runtime.audio_manifest(channel_id=channel_id, session_id=session_id).model_dump(mode="json"),
        }
    )
    try:
        while True:
            update = runtime.refresh_channel_session(channel_id=channel_id, session_id=session_id)
            next_match_id = update.current_program.match_id if update.current_program is not None else None
            if next_match_id != current_match_id:
                cursor = 0
                current_match_id = next_match_id
                await websocket.send_json(
                    {
                        "kind": "audio_manifest_update",
                        "payload": runtime.audio_manifest(channel_id=channel_id, session_id=session_id).model_dump(mode="json"),
                    }
                )
            frames, cursor = runtime.audio_frames(channel_id=channel_id, session_id=session_id, cursor=cursor)
            if frames:
                await websocket.send_json({"kind": "audio_stems", "payload": frames})
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        return
    await websocket.close()


__all__ = ["router"]
