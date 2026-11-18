from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from urllib.parse import urlparse

from app.ai_gateway.config import central_api_key

logger = logging.getLogger(__name__)

LEGACY_NOT_ROUTED = object()
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def staff_dialogue_should_run() -> bool:
    if not central_api_key():
        return False
    raw = os.getenv("OPENAI_ENABLED", "").strip().lower()
    if raw in _FALSE:
        return False
    if os.getenv("GTEX_ENABLE_LIVE_LLM_COMMS", "0").strip() == "1":
        return True
    if raw not in _TRUE:
        return False
    try:
        from app.ai_gateway.repository import load_effective_config

        feature = load_effective_config().feature("staff_dialogue")
    except Exception:
        logger.warning("ai_gateway.staff_feature_lookup_failed")
        return False
    return bool(feature and feature.enabled)


def route_legacy_openai_text(
    *,
    endpoint_url: str | None,
    model: str | None,
    feature: str,
    instructions: str,
    payload: dict[str, object],
    max_output_tokens: int,
    temperature: float,
) -> str | None | object:
    if os.getenv("OPENAI_ROUTE_LEGACY_CLIENTS", "").strip().lower() not in _TRUE:
        return LEGACY_NOT_ROUTED
    host = (urlparse(endpoint_url or "").hostname or "").lower()
    if host != "api.openai.com":
        return LEGACY_NOT_ROUTED
    if not central_api_key():
        return LEGACY_NOT_ROUTED
    if os.getenv("OPENAI_ENABLED", "").strip().lower() in _FALSE:
        return LEGACY_NOT_ROUTED
    try:
        from app.ai_gateway.service import GtexAiService

        result = GtexAiService().generate_text(
            feature=feature,
            user_content="Use only the supplied facts.",
            facts=payload,
            extra_instructions=instructions,
            model_override=model,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    except Exception:
        logger.warning("ai_gateway.legacy_route_failed feature=%s", feature)
        return None
    if result.ok and result.text:
        return result.text.strip() or None
    if result.error_code in {"missing_api_key", "disabled", "configuration_invalid"}:
        return LEGACY_NOT_ROUTED
    return None


def iter_announcement(
    service: object,
    *,
    club_name: str,
    purpose: str,
    facts: str,
    user_id: str | None,
) -> Iterator[str]:
    yield from service.stream_text(  # type: ignore[attr-defined]
        feature="club_announcement",
        user_content=facts,
        facts={"club_name": club_name, "purpose": purpose},
        user_id=user_id,
        extra_instructions="Draft a short club announcement. Do not invent a signing or a fee.",
        temperature=0.4,
    )
