from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Iterable, Protocol

import requests

from services.tts.voice_manager import VoiceProfile


class TtsProviderError(RuntimeError):
    pass


class StreamingTtsProvider(Protocol):
    provider_name: str
    model_id: str
    output_format: str
    audio_format: dict[str, object]

    def stream(self, text: str, voice: VoiceProfile) -> Iterable[bytes]:
        ...


@dataclass(slots=True)
class ElevenLabsStreamingProvider:
    api_key: str | None = None
    model_id: str = "eleven_multilingual_v2"
    output_format: str = "pcm_16000"
    timeout_seconds: int = 10
    chunk_size: int = 2048
    latency_mode: int = 3
    base_url: str = "https://api.elevenlabs.io/v1"
    provider_name: str = "elevenlabs"

    @property
    def audio_format(self) -> dict[str, object]:
        return {
            "codec": "pcm_s16le",
            "sample_rate_hz": _pcm_sample_rate(self.output_format),
            "channels": 1,
        }

    def stream(self, text: str, voice: VoiceProfile) -> Iterable[bytes]:
        if not self.api_key:
            raise TtsProviderError("ElevenLabs API key is not configured.")
        normalized = text.strip()
        if not normalized:
            return
        url = f"{self.base_url}/text-to-speech/{voice.voice_id}/stream"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        params = {
            "output_format": self.output_format,
            "optimize_streaming_latency": self.latency_mode,
        }
        payload = {
            "text": normalized,
            "model_id": self.model_id,
            "voice_settings": voice.as_settings(),
        }
        try:
            with requests.post(
                url,
                params=params,
                json=payload,
                headers=headers,
                stream=True,
                timeout=(3.05, max(self.timeout_seconds, 1)),
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        yield chunk
        except requests.RequestException as exc:
            raise TtsProviderError(f"ElevenLabs streaming failed: {exc}") from exc


@dataclass(slots=True)
class HttpFallbackStreamingProvider:
    endpoint_url: str | None = None
    model_id: str = "fallback-http"
    output_format: str = "pcm_16000"
    timeout_seconds: int = 10
    chunk_size: int = 2048
    provider_name: str = "fallback-http"

    @property
    def audio_format(self) -> dict[str, object]:
        return {
            "codec": "pcm_s16le",
            "sample_rate_hz": _pcm_sample_rate(self.output_format),
            "channels": 1,
        }

    def stream(self, text: str, voice: VoiceProfile) -> Iterable[bytes]:
        if not self.endpoint_url:
            raise TtsProviderError("Fallback TTS endpoint is not configured.")
        payload = {
            "text": text.strip(),
            "voice_id": voice.voice_id,
            "voice_settings": voice.as_settings(),
            "output_format": self.output_format,
        }
        try:
            with requests.post(
                self.endpoint_url,
                json=payload,
                stream=True,
                timeout=(3.05, max(self.timeout_seconds, 1)),
            ) as response:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        yield chunk
        except requests.RequestException as exc:
            raise TtsProviderError(f"Fallback TTS streaming failed: {exc}") from exc


@dataclass(slots=True)
class ToneFallbackProvider:
    chunk_size: int = 2048
    sample_rate_hz: int = 16_000
    output_format: str = "pcm_16000"
    model_id: str = "diagnostic-tone"
    provider_name: str = "diagnostic-tone"

    @property
    def audio_format(self) -> dict[str, object]:
        return {
            "codec": "pcm_s16le",
            "sample_rate_hz": self.sample_rate_hz,
            "channels": 1,
        }

    def stream(self, text: str, voice: VoiceProfile) -> Iterable[bytes]:
        pcm = self._render_pcm(text=text, voice=voice)
        for start in range(0, len(pcm), self.chunk_size):
            yield pcm[start : start + self.chunk_size]

    def _render_pcm(self, *, text: str, voice: VoiceProfile) -> bytes:
        words = [item for item in text.split() if item]
        if not words:
            return b""
        frames = bytearray()
        for index, word in enumerate(words):
            frequency = 175 + ((sum(ord(char) for char in word) + index * 13) % 220)
            duration_seconds = min(max(len(word) * 0.028, 0.09), 0.18)
            frames.extend(
                _tone_pcm(
                    frequency=frequency,
                    sample_rate_hz=self.sample_rate_hz,
                    duration_seconds=duration_seconds,
                    emphasis=1.15 if voice.preset == "hype" else 1.0,
                )
            )
            frames.extend(_silence_pcm(sample_rate_hz=self.sample_rate_hz, duration_seconds=0.028))
        return bytes(frames)


@dataclass(slots=True)
class CompositeStreamingTtsProvider:
    primary: StreamingTtsProvider
    fallbacks: tuple[StreamingTtsProvider, ...] = ()
    provider_name: str = "composite"

    @property
    def model_id(self) -> str:
        return getattr(self.primary, "model_id", "composite")

    @property
    def output_format(self) -> str:
        return getattr(self.primary, "output_format", "pcm_16000")

    @property
    def audio_format(self) -> dict[str, object]:
        return getattr(self.primary, "audio_format", {"codec": "pcm_s16le", "sample_rate_hz": 16_000, "channels": 1})

    def provider_chain(self) -> tuple[str, ...]:
        return tuple(provider.provider_name for provider in (self.primary, *self.fallbacks))

    def stream(self, text: str, voice: VoiceProfile) -> Iterable[bytes]:
        last_error: Exception | None = None
        for provider in (self.primary, *self.fallbacks):
            try:
                yielded = False
                for chunk in provider.stream(text, voice):
                    if chunk:
                        yielded = True
                        yield chunk
                if yielded:
                    return
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise TtsProviderError(str(last_error)) from last_error
        raise TtsProviderError("No TTS provider produced audio.")


def _pcm_sample_rate(output_format: str) -> int:
    parts = str(output_format).split("_")
    if len(parts) >= 2 and parts[-1].isdigit():
        return int(parts[-1])
    return 16_000


def _silence_pcm(*, sample_rate_hz: int, duration_seconds: float) -> bytes:
    sample_count = max(int(sample_rate_hz * duration_seconds), 1)
    return b"\x00\x00" * sample_count


def _tone_pcm(*, frequency: float, sample_rate_hz: int, duration_seconds: float, emphasis: float) -> bytes:
    sample_count = max(int(sample_rate_hz * duration_seconds), 1)
    attack = max(int(sample_rate_hz * 0.01), 1)
    release = max(int(sample_rate_hz * 0.02), 1)
    payload = bytearray()
    for index in range(sample_count):
        envelope = 1.0
        if index < attack:
            envelope = index / attack
        elif index > sample_count - release:
            envelope = max((sample_count - index) / release, 0.0)
        phase = (2.0 * math.pi * frequency * index) / sample_rate_hz
        harmonic = (
            math.sin(phase)
            + (0.42 * math.sin(phase * 2.02))
            + (0.18 * math.sin(phase * 3.01))
        )
        sample = int(max(min(harmonic * envelope * 7_400 * emphasis, 32_767), -32_768))
        payload.extend(struct.pack("<h", sample))
    return bytes(payload)
