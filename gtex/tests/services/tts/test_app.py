from __future__ import annotations

import json

from fastapi.testclient import TestClient

from services.tts.app import create_app
from services.tts.cache import AudioCache
from services.tts.streamer import LiveTextToSpeechStreamer, TextChunker
from services.tts.voice_manager import VoiceManager, VoiceProfile


class FakeStreamingProvider:
    provider_name = "fake"
    model_id = "fake-model"
    output_format = "pcm_16000"
    audio_format = {
        "codec": "pcm_s16le",
        "sample_rate_hz": 16_000,
        "channels": 1,
    }

    def stream(self, text: str, voice: VoiceProfile):
        payload = f"{voice.voice_id}|{text}".encode("utf-8")
        for start in range(0, len(payload), 5):
            yield payload[start : start + 5]


def _build_client() -> TestClient:
    streamer = LiveTextToSpeechStreamer(
        provider=FakeStreamingProvider(),
        voice_manager=VoiceManager({}),
        cache=AudioCache(redis_url=None),
        audio_chunk_size=5,
    )
    return TestClient(create_app(streamer=streamer))


def test_text_chunker_flushes_on_soft_word_limit() -> None:
    chunker = TextChunker(min_words=3, soft_word_limit=6)

    emitted = chunker.push("Lagos City break quickly through the middle with support arriving")

    assert emitted == ["Lagos City break quickly through the"]
    assert chunker.flush() == ["middle with support arriving"]


def test_tts_websocket_streams_bytes_for_one_shot_text() -> None:
    with _build_client() as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        with client.websocket_connect("/live?voice=hype") as websocket:
            ready = websocket.receive_json()
            assert ready["kind"] == "ready"
            assert ready["payload"]["codec"] == "pcm_s16le"
            assert "hype" in ready["payload"]["available_voices"]

            websocket.send_json({"text": "Goal for Lagos City and the crowd loses its mind."})

            audio = bytearray()
            complete = False
            while not complete:
                message = websocket.receive()
                if message.get("bytes") is not None:
                    audio.extend(message["bytes"])
                    continue
                payload = json.loads(message["text"])
                if payload["kind"] == "complete":
                    complete = True

    assert b"excited-commentator" in audio
    assert b"Goal for Lagos City" in audio


def test_tts_websocket_accepts_incremental_text_messages() -> None:
    with _build_client() as client:
        with client.websocket_connect("/live") as websocket:
            ready = websocket.receive_json()
            assert ready["payload"]["voice"] == "default"

            websocket.send_json({"op": "text", "text": "Omo this move is building nicely for the home side"})
            websocket.send_json({"op": "finish"})

            audio = bytearray()
            complete = False
            while not complete:
                message = websocket.receive()
                if message.get("bytes") is not None:
                    audio.extend(message["bytes"])
                    continue
                payload = json.loads(message["text"])
                if payload["kind"] == "complete":
                    complete = True

    assert b"football-commentator" in audio
    assert b"the home" in audio
    assert b"side" in audio
