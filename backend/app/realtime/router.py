from __future__ import annotations

from fastapi import APIRouter, Request

from app.realtime.schemas import RealtimeStatusView

router = APIRouter(prefix="/realtime", tags=["realtime"])


@router.get("/status", response_model=RealtimeStatusView)
def get_realtime_status(request: Request) -> RealtimeStatusView:
    return RealtimeStatusView.model_validate(request.app.state.realtime.snapshot())
