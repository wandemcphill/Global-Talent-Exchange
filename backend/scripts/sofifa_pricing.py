from __future__ import annotations

"""Thin re-export shim. The canonical banded-pricing logic lives in
``app.value_engine.banded_pricing`` so both the app (admin editor, value engine)
and these scripts share one implementation. Kept for backwards-compatible imports
(`from scripts.sofifa_pricing import ...`)."""

from pathlib import Path
import sys

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.value_engine.banded_pricing import (  # noqa: F401,E402
    NAIRA_PER_CREDIT,
    PEAK_AGE,
    PRICE_TIERS,
    SOFIFA_SNAPSHOT_DATE,
    W_AGE,
    W_GSI,
    W_TEAM,
    PriceTier,
    age_from_dob,
    compute_price_credits,
    credits_to_naira,
    effective_gsi,
    projected_price_credits,
    resolve_price_tier,
)
