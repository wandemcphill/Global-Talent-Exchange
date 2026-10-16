from __future__ import annotations

import asyncio
import logging
import os
import uuid

logger = logging.getLogger(__name__)

MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-5-20250929"

SYSTEM_PROMPT = (
    "You write short in-world messages for GTEX, a football club-ownership simulator. "
    "You speak as the named sender (a club manager, player, agent, sponsor or league official) to the club owner. "
    "Stay in character using the personality traits given. 2-3 sentences, max 60 words. "
    "No emojis, no hashtags, no markdown. Never invent numbers beyond those provided."
)


async def _write_one(prompt: str) -> str | None:
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return None
    chat = LlmChat(api_key=key, session_id=f"gtex-inbox-{uuid.uuid4().hex}", system_message=SYSTEM_PROMPT).with_model(
        MODEL_PROVIDER, MODEL_NAME
    )
    text = await chat.send_message(UserMessage(text=prompt))
    return (text or "").strip() or None


async def _write_many(prompts: list[str], timeout: float) -> list[str | None]:
    async def guarded(prompt: str) -> str | None:
        try:
            return await asyncio.wait_for(_write_one(prompt), timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            logger.warning("owner_console.ai.fallback reason=%s", exc)
            return None

    return await asyncio.gather(*(guarded(p) for p in prompts))


def write_messages(prompts: list[str], timeout: float = 20.0) -> list[str | None]:
    if not prompts:
        return []
    try:
        return asyncio.run(_write_many(prompts, timeout))
    except RuntimeError:
        return [None for _ in prompts]
