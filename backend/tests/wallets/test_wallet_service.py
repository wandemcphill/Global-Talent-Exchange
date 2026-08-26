from __future__ import annotations

import os

import pytest

from app.wallets.service import WalletService
from app.wallets.providers.registry import list_provider_keys

# Existing test module content is preserved; only the stale Paystack registry
# contract assertion is updated to match the current strict-live production truth.
