from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.public_pulse.schemas import LiveWorldPulseView
from app.public_pulse.service import PublicPulseService

router = APIRouter(prefix="/public", tags=["public-pulse"])


@router.get("/live-stats", response_model=LiveWorldPulseView)
def get_live_world_pulse(session: Session = Depends(get_session)) -> LiveWorldPulseView:
    """Lagos-Life-style social proof: clubs, users online, managers in live matches."""
    return PublicPulseService(session).live_world_pulse()


__all__ = ["router"]
