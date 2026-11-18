from __future__ import annotations

from typing import Any

from app.ai_gateway.guardrails import scrub_context
from app.ai_gateway.schemas import (
    AdvisoryOut,
    AnnouncementRequest,
    CompetitionSummaryRequest,
    FraudReviewOut,
    FraudReviewRequest,
    MarketInsightRequest,
    MatchReportOut,
    MatchReportRequest,
    ModerationRequest,
    OpsSummaryRequest,
    ScoutingBriefRequest,
    ScoutingToolOut,
    YouthDevelopmentRequest,
)
from app.ai_gateway.service import AiCallResult, GtexAiService

_JSON_OBJECT = "Return JSON only. Do not propose a balance change, transfer, or result correction."

MATCH_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "key_moments": {"type": "array", "items": {"type": "string"}},
        "advisory": {"type": "string"},
    },
    "required": ["headline", "summary", "key_moments", "advisory"],
}

ADVISORY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "advisory": {"type": "string"},
    },
    "required": ["summary", "advisory"],
}

FRAUD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "recommended_follow_up": {"type": "string"},
    },
    "required": ["summary", "risk_level", "recommended_follow_up"],
}

SCOUTING_TOOL = {
    "type": "function",
    "name": "suggest_scouting_action",
    "description": "Recommend a scouting action. Do not sign, transfer, price, or buy the player.",
    "strict": True,
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action": {"type": "string", "enum": ["watch", "compare", "develop", "decline"]},
            "summary": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["action", "summary", "reason"],
    },
}


def match_report(service: GtexAiService, payload: MatchReportRequest, user_id: str | None) -> AiCallResult:
    facts = scrub_context(payload.model_dump())
    return service.generate_json(
        feature="match_report",
        user_content="Write a short match report from these facts.",
        facts=facts,
        schema=MATCH_REPORT_SCHEMA,
        schema_name="gtex_match_report",
        validator=MatchReportOut,
        user_id=user_id,
        extra_instructions=_JSON_OBJECT + " The score in the facts is the only score.",
    )


def scouting_brief(service: GtexAiService, payload: ScoutingBriefRequest, user_id: str | None) -> AiCallResult:
    facts = scrub_context(payload.model_dump())
    return service.generate_json(
        feature="scouting_brief",
        user_content="Recommend one scouting action for this player profile.",
        facts=facts,
        schema=SCOUTING_TOOL["parameters"],
        schema_name="gtex_scouting_action",
        validator=ScoutingToolOut,
        user_id=user_id,
        tools=[SCOUTING_TOOL],
        allowlist={"suggest_scouting_action"},
        extra_instructions=_JSON_OBJECT + " Call suggest_scouting_action. Do not invent a fee.",
    )


def competition_summary(
    service: GtexAiService, payload: CompetitionSummaryRequest, user_id: str | None
) -> AiCallResult:
    return service.summarize(
        feature="competition_summary",
        user_content="Summarize this competition snapshot.",
        facts=scrub_context(payload.model_dump()),
        user_id=user_id,
        extra_instructions="Do not change the table order you were given.",
    )


def youth_development(service: GtexAiService, payload: YouthDevelopmentRequest, user_id: str | None) -> AiCallResult:
    return service.generate_json(
        feature="youth_development",
        user_content="Recommend how this academy player should be developed.",
        facts=scrub_context(payload.model_dump()),
        schema=ADVISORY_SCHEMA,
        schema_name="gtex_youth_advice",
        validator=AdvisoryOut,
        user_id=user_id,
        extra_instructions=_JSON_OBJECT + " Do not promote the player or change a contract.",
    )


def announcement(service: GtexAiService, payload: AnnouncementRequest, user_id: str | None) -> AiCallResult:
    return service.generate_text(
        feature="club_announcement",
        user_content=payload.facts,
        facts={"club_name": payload.club_name, "purpose": payload.purpose},
        user_id=user_id,
        extra_instructions="Draft a short club announcement. Do not announce a signing or fee that is not in the facts.",
    )


def moderation_review(service: GtexAiService, payload: ModerationRequest, user_id: str | None) -> AiCallResult:
    moderated = service.moderate(text=payload.text, user_id=user_id)
    if not moderated.ok or (moderated.data or {}).get("flagged"):
        return moderated
    classified = service.classify(
        feature="community_moderation",
        user_content=payload.text,
        labels=["clean", "spam", "abuse", "suspicious"],
        user_id=user_id,
    )
    if not classified.ok:
        return moderated
    label = str((classified.data or {}).get("label") or "clean")
    data = dict(moderated.data or {})
    data["spam_label"] = label
    data["executed"] = False
    if label in {"spam", "abuse", "suspicious"}:
        data["recommendation"] = "review"
    moderated.data = data
    return moderated


def ops_summary(service: GtexAiService, payload: OpsSummaryRequest, user_id: str | None) -> AiCallResult:
    return service.summarize(
        feature="admin_ops_summary",
        user_content="Summarize these operational metrics for an administrator.",
        facts=scrub_context(payload.model_dump()),
        user_id=user_id,
        extra_instructions="Do not recommend moving money.",
    )


def market_insight(service: GtexAiService, payload: MarketInsightRequest, user_id: str | None) -> AiCallResult:
    return service.generate_json(
        feature="market_insight",
        user_content="Explain these marketplace observations.",
        facts=scrub_context(payload.model_dump()),
        schema=ADVISORY_SCHEMA,
        schema_name="gtex_market_insight",
        validator=AdvisoryOut,
        user_id=user_id,
        extra_instructions=_JSON_OBJECT + " Do not place a trade or change a price.",
    )


def fraud_review(service: GtexAiService, payload: FraudReviewRequest, user_id: str | None) -> AiCallResult:
    return service.generate_json(
        feature="fraud_review",
        user_content="Explain these already-computed risk signals. Do not freeze an account.",
        facts=scrub_context(payload.model_dump()),
        schema=FRAUD_SCHEMA,
        schema_name="gtex_fraud_review",
        validator=FraudReviewOut,
        user_id=user_id,
        extra_instructions=_JSON_OBJECT + " recommended_follow_up is advice for a human reviewer.",
    )


def polish_reporter_copy(*, title: str, body: str) -> str | None:
    import os

    raw = os.getenv("OPENAI_ENABLED", "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return None
    service = GtexAiService()
    feature = service.config.feature("reporter_polish")
    if feature is None or not feature.enabled:
        return None
    result = service.generate_text(
        feature="reporter_polish",
        user_content="Rewrite this wire copy without adding facts.",
        facts={"title": title[:160], "body": body[:1200]},
        extra_instructions="Keep every score, name, and number unchanged.",
        max_output_tokens=400,
    )
    if result.ok and result.text:
        return result.text.strip()[:4000]
    return None


def public_payload(result: AiCallResult) -> dict[str, Any]:
    payload = result.as_public()
    payload["authoritative"] = False
    return payload
