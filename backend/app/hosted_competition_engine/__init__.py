"""Hosted competition engine.

The canonical service is ``app.hosted_competition_engine.service``. This package
re-exports it so a second implementation cannot charge entry fees.
"""

from app.hosted_competition_engine.service import (
    DEFAULT_TEMPLATES,
    HostedCompetitionError,
    HostedCompetitionService,
)

__all__ = [
    "DEFAULT_TEMPLATES",
    "HostedCompetitionError",
    "HostedCompetitionService",
]
