from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import CompetitionContext, NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent, PlayerEventWindow
    from .service import IngestionService

__all__ = [
    "CompetitionContext",
    "IngestionService",
    "NormalizedAwardEvent",
    "NormalizedMatchEvent",
    "NormalizedTransferEvent",
    "PlayerEventWindow",
]


def __getattr__(name: str):
    if name in {
        "CompetitionContext",
        "NormalizedAwardEvent",
        "NormalizedMatchEvent",
        "NormalizedTransferEvent",
        "PlayerEventWindow",
    }:
        from app.ingestion import models

        return getattr(models, name)
    if name == "IngestionService":
        from app.ingestion import service

        return getattr(service, name)
    raise AttributeError(f"module 'app.ingestion' has no attribute {name!r}")
