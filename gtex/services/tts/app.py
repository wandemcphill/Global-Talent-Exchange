from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping

from fastapi import FastAPI, WebSocket

from services.tts.cache import AudioCache
from services.tts.streamer import LiveTextToSpeechStreamer
from services.tts.tts_provider import (
    CompositeStreamingTtsProvider,
    ElevenLabsStreamingProvider,
    HttpFallbackStreamingProvider,
    ToneFallbackProvider,
)
from services.tts.voice_manager import VoiceManager


@dataclass(frozen=True, slots=True)
class TtsServiceSettings:
    redis_url: str | None
    elevenlabs_api_key: str | None
    fallback_endpoint_url: str | None
    model_id: str
    output_format: str
    timeout_seconds: int
    cache_ttl_seconds: int
    audio_chunk_size: int
    latency_mode: int


def load_settings(environ: Mapping[str, str] | None = None) -> TtsServiceSettings:
    env = environ or os.environ
    return TtsServiceSettings(
        redis_url=env.get("GTE_TTS_REDIS_URL") or env.get("GTE_REDIS_URL"),
        elevenlabs_api_key=env.get("GTE_TTS_ELEVENLABS_API_KEY") or env.get("ELEVEN_API_KEY"),
        fallback_endpoint_url=env.get("GTE_TTS_FALLBACK_STREAM_URL"),
        model_id=env.get("GTE_TTS_MODEL_ID", "eleven_multilingual_v2"),
        output_format=env.get("GTE_TTS_OUTPUT_FORMAT", "pcm_16000"),
        timeout_seconds=max(int(env.get("GTE_TTS_TIMEOUT_SECONDS", "10")), 1),
        cache_ttl_seconds=max(int(env.get("GTE_TTS_CACHE_TTL_SECONDS", "43200")), 60),
        audio_chunk_size=max(int(env.get("GTE_TTS_AUDIO_CHUNK_SIZE", "2048")), 256),
        latency_mode=max(int(env.get("GTE_TTS_LATENCY_MODE", "3")), 0),
    )


def build_streamer(settings: TtsServiceSettings | None = None) -> LiveTextToSpeechStreamer:
    resolved = settings or load_settings()
    voice_manager = VoiceManager(os.environ)
    provider = CompositeStreamingTtsProvider(
        primary=ElevenLabsStreamingProvider(
            api_key=resolved.elevenlabs_api_key,
            model_id=resolved.model_id,
            output_format=resolved.output_format,
            timeout_seconds=resolved.timeout_seconds,
            chunk_size=resolved.audio_chunk_size,
            latency_mode=resolved.latency_mode,
        ),
        fallbacks=(
            HttpFallbackStreamingProvider(
                endpoint_url=resolved.fallback_endpoint_url,
                output_format=resolved.output_format,
                timeout_seconds=resolved.timeout_seconds,
                chunk_size=resolved.audio_chunk_size,
            ),
            ToneFallbackProvider(
                chunk_size=resolved.audio_chunk_size,
            ),
        ),
    )
    cache = AudioCache(
        redis_url=resolved.redis_url,
        ttl_seconds=resolved.cache_ttl_seconds,
    )
    return LiveTextToSpeechStreamer(
        provider=provider,
        voice_manager=voice_manager,
        cache=cache,
        audio_chunk_size=resolved.audio_chunk_size,
    )


def create_app(streamer: LiveTextToSpeechStreamer | None = None) -> FastAPI:
    app = FastAPI(title="GTEX TTS Service", version="0.1.0")
    app.state.streamer = streamer or build_streamer()

    @app.get("/health")
    def health() -> dict[str, object]:
        runtime = app.state.streamer
        provider_chain = (
            runtime.provider.provider_chain()
            if hasattr(runtime.provider, "provider_chain")
            else (getattr(runtime.provider, "provider_name", "unknown"),)
        )
        return {
            "status": "ok",
            "codec": runtime.provider.audio_format.get("codec", "pcm_s16le"),
            "sample_rate_hz": runtime.provider.audio_format.get("sample_rate_hz", 16_000),
            "voice_presets": list(runtime.voice_manager.available_presets()),
            "provider_chain": list(provider_chain),
        }

    @app.websocket("/live")
    async def tts_live(websocket: WebSocket) -> None:
        await websocket.app.state.streamer.stream_websocket(
            websocket,
            voice=websocket.query_params.get("voice"),
            tone=websocket.query_params.get("tone"),
            commentator=websocket.query_params.get("commentator"),
            language=websocket.query_params.get("language") or "en",
        )

    return app


app = create_app()
