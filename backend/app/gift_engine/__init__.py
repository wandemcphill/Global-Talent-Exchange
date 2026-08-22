from __future__ import annotations

import sys

from app.gift_engine import service as _legacy_service_module
from app.gift_engine.canonical_service import CanonicalGiftEngineService

# The canonical service retains the legacy implementation underneath but is the
# single runtime entrypoint for gift economics after package initialization.
_legacy_service_module.GiftEngineService = CanonicalGiftEngineService
sys.modules["app.gift_engine.service"].GiftEngineService = CanonicalGiftEngineService

from app.gift_engine.router import router  # noqa: E402
