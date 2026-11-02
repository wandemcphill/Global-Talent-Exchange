from __future__ import annotations

from dataclasses import replace
import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.live_matches.service import LiveMatchHub
from app.match_engine.commentary.live_engine import (
    LiveCommentaryEngine,
    RemoteCommentaryLLMClient,
    _extract_llm_text as extract_commentary_text,
)
from app.match_engine.simulation.models import MatchEvent, MatchEventType
from app.pundits.debate import (
    DebateGenerator,
    RemoteDebateLLMClient,
    _extract_llm_text as extract_debate_text,
)
from app.viral.analytics import (
    RemoteViralityInsightLLMClient,
    ViralFeedbackLoopService,
    _extract_llm_text as extract_analytics_text,
)
from app.viral.captions import (
    RemoteCaptionLLMClient,
    ViralCaptionService,
    _extract_llm_text as extract_caption_text,
)


def _sample_match_event() -> MatchEvent:
    return MatchEvent(
        event_id="evt-1",
        sequence=1,
        event_type=MatchEventType.GOAL,
        minute=89,
        added_time=0,
        home_score=1,
        away_score=0,
        team_id="t-1",
        team_name="Manchester City",
        primary_player_id="p-1",
        primary_player_name="Erling Haaland",
        metadata={"shot_type": "volley", "distance_meters": 12.5},
    )


class TestLLMEngineWiring:
    def test_extract_llm_text_all_formats(self) -> None:
        extractors = [
            extract_commentary_text,
            extract_debate_text,
            extract_caption_text,
            extract_analytics_text,
        ]
        for extract in extractors:
            # 1. OpenAI format (choices[0].message.content string)
            openai_resp = {
                "choices": [{"message": {"role": "assistant", "content": "What an unbelievable volley!"}}]
            }
            assert extract(openai_resp) == "What an unbelievable volley!"

            # 2. OpenAI format (content as list of text chunks)
            openai_chunked = {
                "choices": [{"message": {"role": "assistant", "content": [{"text": "Chunked commentary."}]}}]
            }
            assert extract(openai_chunked) == "Chunked commentary."

            # 3. Gemini format (candidates[0].content.parts[0].text)
            gemini_resp = {
                "candidates": [{"content": {"parts": [{"text": "Gemini generated insight."}]}}]
            }
            assert extract(gemini_resp) == "Gemini generated insight."

            # 4. Bedrock / Anthropic format (output[0].content[0].text)
            bedrock_resp = {
                "output": [{"content": [{"type": "text", "text": "Bedrock generated text."}]}]
            }
            assert extract(bedrock_resp) == "Bedrock generated text."

            # 5. Direct output_text
            output_text_resp = {"output_text": "Direct output text."}
            assert extract(output_text_resp) == "Direct output text."

            # 6. Direct text
            direct_text_resp = {"text": "Simple text field."}
            assert extract(direct_text_resp) == "Simple text field."

            # 7. Empty or malformed payload
            assert extract({}) is None
            assert extract({"choices": []}) is None

    @patch("requests.post")
    def test_commentary_llm_client_openai_payload(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Haaland thunders it into the top corner!"}}]
        }
        mock_post.return_value = mock_response

        client = RemoteCommentaryLLMClient(
            enabled=True,
            endpoint_url="https://api.openai.com/v1/chat/completions",
            model="gpt-4o-mini",
            api_key="sk-test-secret-key",
            timeout_seconds=8,
        )

        result = client.generate({"event": "goal", "player": "Haaland"})
        assert result == "Haaland thunders it into the top corner!"

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-test-secret-key"
        body = call_kwargs["json"]
        assert body["model"] == "gpt-4o-mini"
        assert "messages" in body
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"
        assert body["max_tokens"] == 120

    @patch("requests.post")
    def test_commentary_llm_client_custom_input_payload(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output_text": "Custom input formatted commentary."
        }
        mock_post.return_value = mock_response

        client = RemoteCommentaryLLMClient(
            enabled=True,
            endpoint_url="https://bedrock-runtime.eu-central-1.amazonaws.com/model/custom/invoke",
            model="anthropic.claude-3-haiku",
            api_key="token-123",
            timeout_seconds=5,
        )

        result = client.generate({"event": "goal"})
        assert result == "Custom input formatted commentary."

        call_kwargs = mock_post.call_args[1]
        body = call_kwargs["json"]
        assert "input" in body
        assert body["max_output_tokens"] == 120

    @patch("requests.post")
    def test_live_commentary_engine_generates_llm_commentary(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Sensational strike into the roof of the net!"}}]
        }
        mock_post.return_value = mock_response

        settings = replace(
            get_settings(),
            live_commentary_llm_enabled=True,
            live_commentary_llm_endpoint_url="https://api.openai.com/v1/chat/completions",
            live_commentary_llm_model="gpt-4o-mini",
            live_commentary_llm_api_key="sk-test",
            live_commentary_llm_timeout_seconds=8,
        )

        engine = LiveCommentaryEngine.from_settings(settings)
        event = _sample_match_event()
        commentary = engine.generate(
            match_id="match-123",
            event=event,
            home_team_id="t-1",
            away_team_id="t-2",
            home_team_name="Manchester City",
            away_team_name="Liverpool",
        )

        assert commentary.line == "Sensational strike into the roof of the net!"
        assert commentary.tier == "llm"
        assert commentary.provider == "remote-llm"

    @patch("requests.post")
    def test_live_commentary_engine_fallback_when_llm_fails(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = TimeoutError("Request timed out")

        settings = replace(
            get_settings(),
            live_commentary_llm_enabled=True,
            live_commentary_llm_endpoint_url="https://api.openai.com/v1/chat/completions",
            live_commentary_llm_model="gpt-4o-mini",
            live_commentary_llm_api_key="sk-test",
        )

        engine = LiveCommentaryEngine.from_settings(settings)
        event = _sample_match_event()
        commentary = engine.generate(
            match_id="match-456",
            event=event,
            home_team_id="t-1",
            away_team_id="t-2",
            home_team_name="Manchester City",
            away_team_name="Liverpool",
        )

        # Graceful fallback to local template without crashing
        assert commentary.line
        assert commentary.provider in {"local-dramatic", "template", "raw_event"}
        assert commentary.provider != "remote-llm"

    @patch("requests.post")
    def test_debate_generator_with_openai_response(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "Mara Sterling: The expected goals told the complete story of territorial dominance.\n"
                            "Kofi Blaze: That is absolute rubbish, someone didn't want it enough in the tackle!\n"
                            "Amina Vale: They cooked so hard in transition, total class."
                        )
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        settings = replace(
            get_settings(),
            social_content_llm_enabled=True,
            social_content_llm_endpoint_url="https://api.openai.com/v1/chat/completions",
            social_content_llm_model="gpt-4o-mini",
            social_content_llm_api_key="sk-test",
        )

        generator = DebateGenerator.from_settings(settings)
        lines = generator.generate(
            analysis={"winner_team_name": "City", "score": "2-1", "xg_diff": 1.4},
            hot_takes=["City dominant"],
        )

        assert len(lines) >= 2
        speakers = [line.speaker for line in lines]
        assert "Mara Sterling" in speakers or "Kofi Blaze" in speakers

    @patch("requests.post")
    def test_caption_generator_with_openai_response(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "UNREAL STOP AT THE DEATH!\n"
                            "Drop a comment if you've seen a better reflex save this season! 🧤🔥"
                        )
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        settings = replace(
            get_settings(),
            social_content_llm_enabled=True,
            social_content_llm_endpoint_url="https://api.openai.com/v1/chat/completions",
            social_content_llm_model="gpt-4o-mini",
            social_content_llm_api_key="sk-test",
        )

        service = ViralCaptionService.from_settings(settings)
        result = service.generate_caption({"event_type": "save", "player": "Alisson"})

        assert "UNREAL STOP" in result.hook or "UNREAL STOP" in result.caption
        assert result.source == "remote-llm"

    @patch("requests.post")
    def test_analytics_feedback_with_openai_response(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "The clip went viral because of the instant high-energy audio hook and the 90th-minute bicycle kick drama."
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        settings = replace(
            get_settings(),
            social_content_llm_enabled=True,
            social_content_llm_endpoint_url="https://api.openai.com/v1/chat/completions",
            social_content_llm_model="gpt-4o-mini",
            social_content_llm_api_key="sk-test",
        )

        feedback_service = ViralFeedbackLoopService.from_settings(settings)
        feedback = feedback_service.analyze_clip(
            clip_id="clip-789",
            metrics={"views": 50000, "shares": 1200, "completion_rate": 0.85},
            clip_context={"player": "Haaland", "event": "goal"},
        )

        assert "bicycle kick" in feedback.viral_analysis
        assert feedback.analysis_source == "remote-llm"

    def test_live_match_hub_initialization(self) -> None:
        hub = LiveMatchHub()
        assert hub.commentary_engine is not None
        assert hasattr(hub.commentary_engine, "generate")
