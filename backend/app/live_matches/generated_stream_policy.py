from __future__ import annotations

import os

GENERATED_LIVE_MATCHES_FLAG = "GTEX_ENABLE_GENERATED_LIVE_MATCHES"
SYNTHETIC_MATCH_PRESENTATION_FLAG = "GTEX_ENABLE_SYNTHETIC_MATCH_PRESENTATION"


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def generated_live_match_streams_enabled() -> bool:
    return _env_enabled(GENERATED_LIVE_MATCHES_FLAG)


def synthetic_match_presentation_enabled() -> bool:
    return _env_enabled(SYNTHETIC_MATCH_PRESENTATION_FLAG)
