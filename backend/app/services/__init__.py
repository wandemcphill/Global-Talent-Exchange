"""Shared service packages for cross-domain infrastructure."""

# Install the Phase 6 regen-career lifecycle adapter whenever the service
# package is imported. The adapter only changes retirement gating; all existing
# lifecycle side effects remain owned by PlayerLifecycleService.
from app.services import regen_career_lifecycle_adapter as _regen_career_lifecycle_adapter

__all__ = ["_regen_career_lifecycle_adapter"]
