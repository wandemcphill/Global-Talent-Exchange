from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
import re
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from services.tts.cache import AudioCache
from services.tts.tts_provider import StreamingTtsProvider
from services.tts.voice_manager import VoiceManager

_PUNCTUATION_BOUNDARY_RE = re.compile(r"[,.;!?]\s+")


@dataclass(frozen=True, slots=True)
class QueuedPhrase:
    text: str
    voice: str | None = None
    tone: str | None = None
    commentator: str | None = None
    language: str = "en"


@dataclass(slots=True)
class TextChunker:
    min_words: int = 4
    soft_word_limit: int = 9
    buffer: str = ""

    def push(self, text: str) -> list[str]:
        fragment = _normalize_fragment(text)
        if not fragment:
            return []
        self.buffer = f"{self.buffer} {fragment}".strip() if self.buffer else fragment
        return self._drain(final=False)

    def flush(self) -> list[str]:
        return self._drain(final=True)

    def _drain(self, *, final: bool) -> list[str]:
        emitted: list[str] = []
        while self.buffer:
            chunk, remainder = self._next_chunk(final=final)
            if not chunk:
                break
            emitted.append(chunk)
            self.buffer = remainder
        if final and self.buffer.strip():
            emitted.append(self.buffer.strip())
            self.buffer = ""
        return emitted

    def _next_chunk(self, *, final: bool) -> tuple[str | None, str]:
        candidate = self.buffer.strip()
        if not candidate:
            return None, ""
        for match in _PUNCTUATION_BOUNDARY_RE.finditer(candidate):
            leading = candidate[: match.end()].strip()
            if len(leading.split()) >= self.min_words:
                return leading, candidate[match.end() :].strip()
        words = candidate.split()
        if not final and len(words) < self.soft_word_limit:
            return None, candidate
        if len(words) <= self.soft_word_limit:
            return candidate if final else None, ""
        leading = " ".join(words[: self.soft_word_limit]).strip()
        trailing = " ".join(words[self.soft_word_limit :]).strip()
        return leading, trailing


@dataclass(slots=True)
class LiveTextToSpeechStreamer:
    provider: StreamingTtsProvider
    voice_manager: VoiceManager
    cache: AudioCache
    audio_chunk_size: int = 2048

    async def stream_websocket(
        self,
        websocket: WebSocket,
        *,
        voice: str | None = None,
        tone: str | None = None,
        commentator: str | None = None,
        language: str = "en",
    ) -> None:
        await websocket.accept()
        await websocket.send_json(
            {
                "kind": "ready",
                "payload": {
                    "codec": self.provider.audio_format.get("codec", "pcm_s16le"),
                    "sample_rate_hz": self.provider.audio_format.get("sample_rate_hz", 16_000),
                    "channels": self.provider.audio_format.get("channels", 1),
                    "voice": voice or "default",
                    "available_voices": list(self.voice_manager.available_presets()),
                },
            }
        )

        state = {
            "voice": voice,
            "tone": tone,
            "commentator": commentator,
            "language": language,
            "auto_close": False,
        }
        chunker = TextChunker()
        phrase_queue: asyncio.Queue[QueuedPhrase | None] = asyncio.Queue()
        audio_queue: asyncio.Queue[bytes | dict[str, Any] | None] = asyncio.Queue()
        sentinel_sent = False

        async def close_phrase_queue() -> None:
            nonlocal sentinel_sent
            if sentinel_sent:
                return
            sentinel_sent = True
            await phrase_queue.put(None)

        async def receiver() -> None:
            try:
                while True:
                    payload = await websocket.receive_json()
                    if not isinstance(payload, dict):
                        continue
                    op = str(payload.get("op") or "").strip().lower()
                    state["voice"] = str(payload.get("voice") or state["voice"] or "").strip() or state["voice"]
                    state["tone"] = str(payload.get("tone") or state["tone"] or "").strip() or state["tone"]
                    state["commentator"] = (
                        str(payload.get("commentator") or state["commentator"] or "").strip() or state["commentator"]
                    )
                    state["language"] = str(payload.get("language") or state["language"] or "en").strip() or "en"

                    if not op and "text" in payload:
                        await self._enqueue_text(
                            phrase_queue=phrase_queue,
                            chunker=chunker,
                            text=str(payload.get("text") or ""),
                            voice=state["voice"],
                            tone=state["tone"],
                            commentator=state["commentator"],
                            language=state["language"],
                            final=True,
                        )
                        state["auto_close"] = True
                        await close_phrase_queue()
                        return

                    if op in {"start", "configure"}:
                        continue
                    if op in {"text", "append"}:
                        is_final = bool(payload.get("final", False))
                        await self._enqueue_text(
                            phrase_queue=phrase_queue,
                            chunker=chunker,
                            text=str(payload.get("text") or ""),
                            voice=state["voice"],
                            tone=state["tone"],
                            commentator=state["commentator"],
                            language=state["language"],
                            final=is_final,
                        )
                        if is_final:
                            state["auto_close"] = True
                            await close_phrase_queue()
                            return
                        continue
                    if op == "flush":
                        await self._enqueue_text(
                            phrase_queue=phrase_queue,
                            chunker=chunker,
                            text="",
                            voice=state["voice"],
                            tone=state["tone"],
                            commentator=state["commentator"],
                            language=state["language"],
                            final=True,
                        )
                        continue
                    if op in {"finish", "close"}:
                        await self._enqueue_text(
                            phrase_queue=phrase_queue,
                            chunker=chunker,
                            text="",
                            voice=state["voice"],
                            tone=state["tone"],
                            commentator=state["commentator"],
                            language=state["language"],
                            final=True,
                        )
                        state["auto_close"] = True
                        await close_phrase_queue()
                        return
            except WebSocketDisconnect:
                return
            finally:
                await close_phrase_queue()

        async def synthesizer() -> None:
            while True:
                phrase = await phrase_queue.get()
                if phrase is None:
                    break
                if not phrase.text.strip():
                    continue
                try:
                    await self._stream_phrase(phrase=phrase, audio_queue=audio_queue)
                except Exception as exc:
                    await audio_queue.put({"kind": "error", "payload": {"detail": str(exc)}})
                    break
            await audio_queue.put({"kind": "complete"})

        async def sender() -> None:
            try:
                while True:
                    item = await audio_queue.get()
                    if item is None:
                        return
                    if isinstance(item, bytes):
                        await websocket.send_bytes(item)
                        continue
                    await websocket.send_json(item)
                    if item.get("kind") in {"complete", "error"}:
                        return
            except WebSocketDisconnect:
                return

        tasks = [
            asyncio.create_task(receiver()),
            asyncio.create_task(synthesizer()),
            asyncio.create_task(sender()),
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
            with suppress(Exception):
                await asyncio.gather(*tasks)
            if state["auto_close"]:
                with suppress(RuntimeError, WebSocketDisconnect):
                    await websocket.close()

    async def _enqueue_text(
        self,
        *,
        phrase_queue: asyncio.Queue[QueuedPhrase | None],
        chunker: TextChunker,
        text: str,
        voice: str | None,
        tone: str | None,
        commentator: str | None,
        language: str,
        final: bool,
    ) -> None:
        pieces = chunker.push(text) if text else []
        if final:
            pieces.extend(chunker.flush())
        for piece in pieces:
            normalized = piece.strip()
            if not normalized:
                continue
            await phrase_queue.put(
                QueuedPhrase(
                    text=normalized,
                    voice=voice,
                    tone=tone,
                    commentator=commentator,
                    language=language,
                )
            )

    async def _stream_phrase(
        self,
        *,
        phrase: QueuedPhrase,
        audio_queue: asyncio.Queue[bytes | dict[str, Any] | None],
    ) -> None:
        voice = self.voice_manager.resolve(
            phrase.voice,
            tone=phrase.tone,
            commentator=phrase.commentator,
        )
        cached = self.cache.get_audio(
            text=phrase.text,
            voice_id=voice.voice_id,
            model_id=self.provider.model_id,
            output_format=self.provider.output_format,
        )
        if cached is not None:
            for chunk in self._iter_audio_chunks(cached):
                await audio_queue.put(chunk)
            return

        produced = bytearray()
        loop = asyncio.get_running_loop()

        def synthesize_in_thread() -> None:
            for chunk in self.provider.stream(phrase.text, voice):
                payload = bytes(chunk)
                if not payload:
                    continue
                produced.extend(payload)
                future = asyncio.run_coroutine_threadsafe(audio_queue.put(payload), loop)
                future.result()

        await asyncio.to_thread(synthesize_in_thread)
        if produced:
            self.cache.save_audio(
                text=phrase.text,
                voice_id=voice.voice_id,
                model_id=self.provider.model_id,
                output_format=self.provider.output_format,
                audio=bytes(produced),
            )

    def _iter_audio_chunks(self, payload: bytes):
        for start in range(0, len(payload), self.audio_chunk_size):
            yield payload[start : start + self.audio_chunk_size]


def _normalize_fragment(text: str) -> str:
    normalized = str(text or "")
    return re.sub(r"\s+", " ", normalized).strip()
