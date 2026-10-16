from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.commentary.rendering import (
    CommentaryProfileSnapshot,
    DEFAULT_COMMENTATOR_PROFILES,
    fallback_commentary_profiles,
    render_commentary_variant,
)
from app.commentary.schemas import (
    CommentaryAudioPacketView,
    CommentarySelectionRequest,
    CommentarySelectionView,
    CommentaryStreamEventView,
    CommentaryStreamResponse,
    CommentaryVariantView,
    CommentatorProfileView,
)
from app.core.cache import CacheBackend, JsonCacheNamespace, NullCacheBackend
from app.global_memory.models import PlayerHistory
from app.live_matches.schemas import LiveMatchStreamEventView
from app.models.club_ownership import ClubGovernanceState, ClubToken
from app.models.club_profile import ClubProfile
from app.models.club_social import RivalryMatchHistory, RivalryProfile
from app.models.commentator_profile import CommentaryProfileSelection, CommentatorProfile
from app.models.player_rivalry import PlayerRivalry
from app.models.player_story import PlayerStory
from app.models.user import User
from services.tts.tts_provider import (
    CompositeStreamingTtsProvider,
    ElevenLabsStreamingProvider,
    HttpFallbackStreamingProvider,
    ToneFallbackProvider,
)
from services.tts.voice_manager import VoiceManager


class CommentaryServiceError(ValueError):
    pass


@dataclass(slots=True)
class CommentaryAudioService:
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    ttl_seconds: int = 43_200
    audio_chunk_size: int = 2_048
    _cache: JsonCacheNamespace = field(init=False)
    voice_manager: VoiceManager = field(init=False)
    provider: CompositeStreamingTtsProvider = field(init=False)

    def __post_init__(self) -> None:
        self._cache = JsonCacheNamespace(self.cache_backend)
        env = os.environ
        chunk_size = max(int(env.get("GTE_TTS_AUDIO_CHUNK_SIZE", str(self.audio_chunk_size))), 256)
        self.voice_manager = VoiceManager(env)
        self.provider = CompositeStreamingTtsProvider(
            primary=ElevenLabsStreamingProvider(
                api_key=env.get("GTE_TTS_ELEVENLABS_API_KEY") or env.get("ELEVEN_API_KEY"),
                model_id=env.get("GTE_TTS_MODEL_ID", "eleven_multilingual_v2"),
                output_format=env.get("GTE_TTS_OUTPUT_FORMAT", "pcm_16000"),
                timeout_seconds=max(int(env.get("GTE_TTS_TIMEOUT_SECONDS", "10")), 1),
                chunk_size=chunk_size,
                latency_mode=max(int(env.get("GTE_TTS_LATENCY_MODE", "3")), 0),
            ),
            fallbacks=(
                HttpFallbackStreamingProvider(
                    endpoint_url=env.get("GTE_TTS_FALLBACK_STREAM_URL"),
                    output_format=env.get("GTE_TTS_OUTPUT_FORMAT", "pcm_16000"),
                    timeout_seconds=max(int(env.get("GTE_TTS_TIMEOUT_SECONDS", "10")), 1),
                    chunk_size=chunk_size,
                ),
                ToneFallbackProvider(chunk_size=chunk_size),
            ),
        )
        self.audio_chunk_size = chunk_size

    def render_audio(
        self,
        *,
        match_id: str,
        event_id: str,
        variant: CommentaryVariantView,
        language: str,
    ) -> CommentaryAudioPacketView | None:
        line = str(variant.line or "").strip()
        if not line:
            return None
        cache_key = f"match:{match_id}:commentary_audio:{event_id}"
        cached_payload = self._load_cached_payload(cache_key)
        cached_variant = dict(cached_payload.get("variants") or {}).get(variant.profile_id)
        if isinstance(cached_variant, dict):
            return CommentaryAudioPacketView.model_validate(cached_variant)

        preset = str(variant.voice_config.get("preset") or variant.style or "default")
        voice = self.voice_manager.resolve(
            preset,
            tone=variant.tone,
            commentator=variant.commentator,
        )
        audio_bytes = bytearray()
        for chunk in self.provider.stream(line, voice):
            payload = bytes(chunk)
            if payload:
                audio_bytes.extend(payload)
        if not audio_bytes:
            return None

        packet = CommentaryAudioPacketView(
            key=cache_key,
            provider=getattr(self.provider, "provider_name", "tts"),
            model_id=getattr(self.provider, "model_id", "unknown"),
            output_format=getattr(self.provider, "output_format", "pcm_16000"),
            codec=str(self.provider.audio_format.get("codec", "pcm_s16le")),
            sample_rate_hz=int(self.provider.audio_format.get("sample_rate_hz", 16_000) or 16_000),
            channels=int(self.provider.audio_format.get("channels", 1) or 1),
            voice_id=voice.voice_id,
            chunk_size=self.audio_chunk_size,
            chunks_base64=[
                base64.b64encode(bytes(audio_bytes[index : index + self.audio_chunk_size])).decode("ascii")
                for index in range(0, len(audio_bytes), self.audio_chunk_size)
            ],
        )
        variants = dict(cached_payload.get("variants") or {})
        variants[variant.profile_id] = packet.model_dump(mode="json")
        cached_payload["variants"] = variants
        cached_payload["language"] = language
        self._cache.set_json(cache_key, cached_payload, ttl_seconds=max(self.ttl_seconds, 60))
        return packet

    def _load_cached_payload(self, cache_key: str) -> dict[str, Any]:
        envelope = self._cache.get_json(cache_key)
        payload = envelope.get("payload") if isinstance(envelope, dict) else None
        if isinstance(payload, dict):
            return dict(payload)
        return {"variants": {}}


@dataclass(slots=True)
class CommentaryService:
    session: Session
    cache_backend: CacheBackend = field(default_factory=NullCacheBackend)
    audio_service: CommentaryAudioService = field(init=False)

    def __post_init__(self) -> None:
        self.audio_service = CommentaryAudioService(cache_backend=self.cache_backend)

    def seed_defaults(self) -> None:
        existing = {
            item.name: item
            for item in self.session.scalars(select(CommentatorProfile)).all()
        }
        for payload in DEFAULT_COMMENTATOR_PROFILES:
            name = str(payload["name"])
            item = existing.get(name)
            if item is None:
                self.session.add(
                    CommentatorProfile(
                        name=name,
                        style=str(payload["style"]),
                        tone_intensity=float(payload["tone_intensity"]),
                        summary=str(payload.get("summary") or "") or None,
                        catchphrases=list(payload.get("catchphrases") or []),
                        bias_rules=dict(payload.get("bias_rules") or {}),
                        voice_config=dict(payload.get("voice_config") or {}),
                        is_default=bool(payload.get("is_default")),
                        is_active=True,
                        metadata_json={},
                    )
                )
                continue
            item.style = str(payload["style"])
            item.tone_intensity = float(payload["tone_intensity"])
            item.summary = str(payload.get("summary") or "") or None
            item.catchphrases = list(payload.get("catchphrases") or [])
            item.bias_rules = dict(payload.get("bias_rules") or {})
            item.voice_config = dict(payload.get("voice_config") or {})
            item.is_default = bool(payload.get("is_default"))
            item.is_active = True
        self.session.flush()

    def list_profiles(self) -> list[CommentatorProfileView]:
        profiles = list(
            self.session.scalars(
                select(CommentatorProfile)
                .where(CommentatorProfile.is_active.is_(True))
                .order_by(CommentatorProfile.is_default.desc(), CommentatorProfile.name.asc())
            ).all()
        )
        if profiles:
            return [self._profile_view(item) for item in profiles]
        return [self._profile_view(item) for item in fallback_commentary_profiles()]

    def save_selection(self, *, user: User, payload: CommentarySelectionRequest) -> CommentarySelectionView:
        primary = self._require_profile(payload.primary_profile_id)
        secondary = self._optional_profile(payload.secondary_profile_id)
        selection_key = self._selection_key(payload.match_id)
        selection = self.session.scalar(
            select(CommentaryProfileSelection).where(
                CommentaryProfileSelection.user_id == user.id,
                CommentaryProfileSelection.selection_key == selection_key,
            )
        )
        if selection is None:
            selection = CommentaryProfileSelection(
                user_id=user.id,
                selection_key=selection_key,
                match_id=payload.match_id,
                primary_profile_id=primary.id,
            )
            self.session.add(selection)
        selection.match_id = payload.match_id
        selection.primary_profile_id = primary.id
        selection.secondary_profile_id = secondary.id if secondary is not None else None
        selection.dual_mode = bool(payload.dual_mode and secondary is not None)
        selection.voice_enabled = bool(payload.voice_enabled)
        selection.language = str(payload.language or "en").strip() or "en"
        selection.metadata_json = dict(payload.metadata_json or {})
        self.session.flush()
        return self._selection_view(selection, primary=primary, secondary=secondary)

    def resolve_selection_view(self, *, user_id: str, match_id: str | None = None) -> CommentarySelectionView:
        selection = self._selection_record(user_id=user_id, match_id=match_id)
        if selection is None:
            primary = self._default_profile()
            return CommentarySelectionView(
                selection_key=self._selection_key(match_id),
                match_id=match_id,
                primary_profile=self._profile_view(primary),
                secondary_profile=None,
                dual_mode=False,
                voice_enabled=True,
                language="en",
                metadata_json={},
            )
        primary = self._require_profile(selection.primary_profile_id)
        secondary = self._optional_profile(selection.secondary_profile_id)
        return self._selection_view(selection, primary=primary, secondary=secondary)

    def render_stream(
        self,
        *,
        match_id: str,
        status: str,
        user_id: str,
        events: list[LiveMatchStreamEventView],
        cursor: int,
        include_audio: bool = False,
    ) -> CommentaryStreamResponse:
        selection = self.resolve_selection_view(user_id=user_id, match_id=match_id)
        primary_profile = self._profile_snapshot(selection.primary_profile)
        secondary_profile = (
            self._profile_snapshot(selection.secondary_profile)
            if selection.secondary_profile is not None and selection.dual_mode
            else None
        )
        enriched = self._event_enrichment(events)
        rendered_events: list[CommentaryStreamEventView] = []
        for event in events:
            base_line = str(event.commentary or event.metadata.get("description") or "").strip()
            if not base_line:
                continue
            context = self._compose_context(
                match_id=match_id,
                event=event,
                enriched=enriched.get(self._event_key(event), {}),
            )
            primary_variant = self._variant_view(
                match_id=match_id,
                event=event,
                profile=primary_profile,
                context=context,
                base_line=base_line,
                variant_index=0,
                include_audio=include_audio and selection.voice_enabled,
                language=selection.language,
            )
            secondary_variant = None
            if secondary_profile is not None:
                secondary_variant = self._variant_view(
                    match_id=match_id,
                    event=event,
                    profile=secondary_profile,
                    context=context,
                    base_line=base_line,
                    variant_index=1,
                    include_audio=include_audio and selection.voice_enabled,
                    language=selection.language,
                )
            cue = dict(
                event.experience.commentary.model_dump(mode="json")
                if event.experience is not None and event.experience.commentary is not None
                else {}
            )
            cue.update(
                {
                    "line": primary_variant.line,
                    "tone": primary_variant.tone,
                    "commentator": primary_variant.commentator,
                    "language": selection.language,
                    "intensity": primary_variant.intensity,
                    "tts_ready": bool(primary_variant.line) and selection.voice_enabled,
                    "banter_layer": secondary_variant is not None,
                    "audio_channel": primary_variant.audio_channel,
                }
            )
            rendered_events.append(
                CommentaryStreamEventView(
                    match_id=match_id,
                    event_id=event.event_id,
                    minute=event.minute,
                    event_type=str(event.source_event_type or event.metadata.get("raw_event_type") or event.event_type),
                    line=primary_variant.line,
                    base_line=base_line,
                    team=event.team or event.metadata.get("team_name"),
                    player=event.player or event.metadata.get("player_name"),
                    context=context,
                    cue=cue,
                    primary=primary_variant,
                    secondary=secondary_variant,
                )
            )
        return CommentaryStreamResponse(
            match_id=match_id,
            status=status,
            cursor=max(cursor, 0),
            selection=selection,
            events=rendered_events,
        )

    def _variant_view(
        self,
        *,
        match_id: str,
        event: LiveMatchStreamEventView,
        profile: CommentaryProfileSnapshot,
        context: dict[str, Any],
        base_line: str,
        variant_index: int,
        include_audio: bool,
        language: str,
    ) -> CommentaryVariantView:
        rendered = render_commentary_variant(
            profile=profile,
            context=context,
            base_line=base_line,
            variant_index=variant_index,
        )
        variant = CommentaryVariantView(
            profile_id=rendered.profile_id,
            profile_name=rendered.profile_name,
            style=rendered.style,
            line=rendered.line,
            tone=rendered.tone,
            commentator=rendered.commentator,
            intensity=rendered.intensity,
            audio_channel=rendered.audio_channel,
            voice_config=dict(rendered.voice_config),
            audio=None,
        )
        if include_audio and event.event_id is not None:
            variant.audio = self.audio_service.render_audio(
                match_id=match_id,
                event_id=event.event_id,
                variant=variant,
                language=language,
            )
        return variant

    def _compose_context(
        self,
        *,
        match_id: str,
        event: LiveMatchStreamEventView,
        enriched: dict[str, Any],
    ) -> dict[str, Any]:
        context = dict(event.metadata.get("commentary_context") or {})
        context.update(dict(enriched))
        context.setdefault("match_id", match_id)
        context.setdefault("minute", event.minute)
        context.setdefault("event_type", str(event.source_event_type or event.metadata.get("raw_event_type") or event.event_type))
        context.setdefault("event_family", self._event_family(str(event.event_type or "")))
        context.setdefault("team_id", event.team_id)
        context.setdefault("team_name", event.team or event.metadata.get("team_name"))
        context.setdefault("team_side", event.team_side)
        context.setdefault("player_id", event.player_id)
        context.setdefault("player_name", event.player or event.metadata.get("player_name"))
        context.setdefault("secondary_player_id", event.secondary_player_id)
        context.setdefault("secondary_player_name", event.secondary_player or event.metadata.get("secondary_player_name"))
        context.setdefault("home_score", event.home_score)
        context.setdefault("away_score", event.away_score)
        context.setdefault("scoreline", f"{event.home_score or 0}-{event.away_score or 0}")
        context.setdefault("importance", int(event.meta.get("importance", 1) or 1))
        context.setdefault("late_drama", event.minute >= 85 and abs((event.home_score or 0) - (event.away_score or 0)) <= 1)
        context.setdefault("is_major_moment", bool(event.highlight_eligible or self._event_family(str(event.event_type or "")) in {"goal", "card"}))
        if "opponent_team_name" not in context and isinstance(enriched.get("opponent_team_name"), str):
            context["opponent_team_name"] = enriched["opponent_team_name"]
        return context

    def _event_enrichment(self, events: list[LiveMatchStreamEventView]) -> dict[str, dict[str, Any]]:
        player_ids = {item for event in events for item in (event.player_id, event.secondary_player_id) if item}
        team_ids = [team_id for team_id in dict.fromkeys(event.team_id for event in events if event.team_id)]
        opponent_names = {
            str(dict(event.metadata.get("commentary_context") or {}).get("opponent_team_name") or "").strip()
            for event in events
        }
        opponent_names.discard("")
        opponent_lookup = {
            item.club_name: item.id
            for item in self.session.scalars(
                select(ClubProfile).where(ClubProfile.club_name.in_(opponent_names))
            ).all()
        } if opponent_names else {}
        for club_id in opponent_lookup.values():
            if club_id not in team_ids:
                team_ids.append(club_id)
        history_by_player = self._latest_history_by_player(player_ids)
        story_by_player = self._stories_by_player(player_ids)
        rivalry_by_player_pair = self._player_rivalries(player_ids)
        governance_by_club = self._governance_by_club(set(team_ids))
        token_by_club = self._token_by_club(set(team_ids))
        rivalry_by_club_pair = self._club_rivalries(set(team_ids))
        rivalry_history_by_id = self._latest_rivalry_history({item.id for item in rivalry_by_club_pair.values()})
        opponent_by_team = {}
        if len(team_ids) == 2:
            opponent_by_team = {team_ids[0]: team_ids[1], team_ids[1]: team_ids[0]}

        enriched: dict[str, dict[str, Any]] = {}
        for event in events:
            payload: dict[str, Any] = {}
            opponent_id = opponent_by_team.get(event.team_id)
            if opponent_id is None:
                context = dict(event.metadata.get("commentary_context") or {})
                opponent_name = str(context.get("opponent_team_name") or "").strip()
                if opponent_name:
                    opponent_id = opponent_lookup.get(opponent_name)
            if opponent_id is not None:
                payload["opponent_team_name"] = next(
                    (
                        candidate.team
                        for candidate in events
                        if candidate.team_id == opponent_id and candidate.team
                    ),
                    None,
                )
            if event.player_id is not None:
                history = history_by_player.get(event.player_id)
                if history is not None:
                    payload["player_history_hook"] = history.event
                story = story_by_player.get(event.player_id)
                story_hook = self._story_hook(story.chapters if story is not None else None)
                if story_hook:
                    payload["legacy_hook"] = story_hook
            if event.player_id is not None and event.secondary_player_id is not None:
                rivalry = rivalry_by_player_pair.get(frozenset({event.player_id, event.secondary_player_id}))
                if rivalry is not None and float(rivalry.intensity_score or 0.0) > 0:
                    payload["rivalry_intensity"] = round(float(rivalry.intensity_score), 2)
                    payload.setdefault("rivalry_label", "a personal rivalry boiling over")
            if event.team_id is not None and opponent_id is not None:
                rivalry_profile = rivalry_by_club_pair.get(frozenset({event.team_id, opponent_id}))
                if rivalry_profile is not None:
                    payload["rivalry_label"] = rivalry_profile.label
                    payload["rivalry_intensity"] = max(
                        round(float(payload.get("rivalry_intensity") or 0.0), 2),
                        round(float(rivalry_profile.intensity_score or 0), 2),
                    )
                    history = rivalry_history_by_id.get(rivalry_profile.id)
                    if history is not None:
                        payload["legacy_hook"] = self._rivalry_history_hook(history, team_id=event.team_id)
            governance = governance_by_club.get(event.team_id or "")
            if governance is not None:
                payload["governance_formation"] = governance.formation
                payload["governance_playstyle"] = governance.playstyle
                mandate = str(governance.fan_mandate_summary or "").strip()
                if mandate:
                    payload["governance_story_hook"] = mandate
                elif self._event_family(str(event.event_type or "")) == "goal":
                    payload["governance_story_hook"] = f"Fans demanded {governance.formation} and the shape paid off."
            token = token_by_club.get(event.team_id or "")
            if token is not None:
                payload["token_price"] = float(token.price or 0)
                payload["fan_demand_score"] = float(token.fan_demand_score or 0)
                payload["treasury_balance"] = float(token.treasury_balance_snapshot or 0)
                payload["win_rate"] = float(token.win_rate or 0)
                payload["performance_score"] = float(token.performance_score or 0)
                if self._is_board_pressure_event(event=event, token=token):
                    payload["board_pressure_hook"] = "The board is under pressure after that setback."
            enriched[self._event_key(event)] = payload
        return enriched

    def _latest_history_by_player(self, player_ids: set[str]) -> dict[str, PlayerHistory]:
        if not player_ids:
            return {}
        rows = list(
            self.session.scalars(
                select(PlayerHistory)
                .where(PlayerHistory.player_id.in_(player_ids))
                .order_by(PlayerHistory.created_at.desc())
            ).all()
        )
        payload: dict[str, PlayerHistory] = {}
        for row in rows:
            payload.setdefault(row.player_id, row)
        return payload

    def _stories_by_player(self, player_ids: set[str]) -> dict[str, PlayerStory]:
        if not player_ids:
            return {}
        return {
            item.player_id: item
            for item in self.session.scalars(
                select(PlayerStory).where(PlayerStory.player_id.in_(player_ids))
            ).all()
        }

    def _player_rivalries(self, player_ids: set[str]) -> dict[frozenset[str], PlayerRivalry]:
        if len(player_ids) < 2:
            return {}
        rows = self.session.scalars(
            select(PlayerRivalry).where(
                or_(
                    PlayerRivalry.player_a_id.in_(player_ids),
                    PlayerRivalry.player_b_id.in_(player_ids),
                )
            )
        ).all()
        return {
            frozenset({item.player_a_id, item.player_b_id}): item
            for item in rows
        }

    def _governance_by_club(self, club_ids: set[str]) -> dict[str, ClubGovernanceState]:
        if not club_ids:
            return {}
        return {
            item.club_id: item
            for item in self.session.scalars(
                select(ClubGovernanceState).where(ClubGovernanceState.club_id.in_(club_ids))
            ).all()
        }

    def _token_by_club(self, club_ids: set[str]) -> dict[str, ClubToken]:
        if not club_ids:
            return {}
        return {
            item.club_id: item
            for item in self.session.scalars(
                select(ClubToken).where(ClubToken.club_id.in_(club_ids))
            ).all()
        }

    def _club_rivalries(self, club_ids: set[str]) -> dict[frozenset[str], RivalryProfile]:
        if len(club_ids) < 2:
            return {}
        rows = self.session.scalars(
            select(RivalryProfile).where(
                or_(
                    RivalryProfile.club_a_id.in_(club_ids),
                    RivalryProfile.club_b_id.in_(club_ids),
                )
            )
        ).all()
        return {
            frozenset({item.club_a_id, item.club_b_id}): item
            for item in rows
        }

    def _latest_rivalry_history(self, rivalry_ids: set[str]) -> dict[str, RivalryMatchHistory]:
        if not rivalry_ids:
            return {}
        rows = list(
            self.session.scalars(
                select(RivalryMatchHistory)
                .where(RivalryMatchHistory.rivalry_id.in_(rivalry_ids))
                .order_by(RivalryMatchHistory.happened_at.desc())
            ).all()
        )
        payload: dict[str, RivalryMatchHistory] = {}
        for row in rows:
            payload.setdefault(row.rivalry_id, row)
        return payload

    @staticmethod
    def _story_hook(chapters: object | None) -> str | None:
        if isinstance(chapters, str):
            normalized = chapters.strip()
            return normalized or None
        if isinstance(chapters, Mapping):
            for value in chapters.values():
                hook = CommentaryService._story_hook(value)
                if hook:
                    return hook
            return None
        if isinstance(chapters, list):
            for value in chapters:
                hook = CommentaryService._story_hook(value)
                if hook:
                    return hook
        return None

    @staticmethod
    def _rivalry_history_hook(item: RivalryMatchHistory, *, team_id: str | None) -> str:
        scoreline = f"{int(item.home_score)}-{int(item.away_score)}"
        if item.winner_club_id is None:
            return f"The last derby finished {scoreline}, and nobody left satisfied."
        if team_id is not None and item.winner_club_id == team_id:
            return f"They won the last rivalry clash {scoreline}."
        return f"They still carry the scar of the last rivalry clash at {scoreline}."

    @staticmethod
    def _is_board_pressure_event(*, event: LiveMatchStreamEventView, token: ClubToken) -> bool:
        team_score = event.home_score or 0
        opponent_score = event.away_score or 0
        if event.team_side == "away":
            team_score, opponent_score = opponent_score, team_score
        losing = team_score < opponent_score
        return losing and (float(token.price or 0) < 1.0 or float(token.performance_score or 0) < 0.0)

    def _selection_record(self, *, user_id: str, match_id: str | None) -> CommentaryProfileSelection | None:
        keys = [self._selection_key(match_id)]
        if match_id is not None:
            keys.append("default")
        for key in keys:
            item = self.session.scalar(
                select(CommentaryProfileSelection).where(
                    CommentaryProfileSelection.user_id == user_id,
                    CommentaryProfileSelection.selection_key == key,
                )
            )
            if item is not None:
                return item
        return None

    @staticmethod
    def _selection_key(match_id: str | None) -> str:
        return f"match:{match_id}" if match_id else "default"

    def _require_profile(self, profile_id: str) -> CommentatorProfile | CommentaryProfileSnapshot:
        item = self.session.get(CommentatorProfile, profile_id)
        if item is None or not item.is_active:
            raise CommentaryServiceError("Commentator profile was not found.")
        return item

    def _optional_profile(self, profile_id: str | None) -> CommentatorProfile | CommentaryProfileSnapshot | None:
        if not profile_id:
            return None
        return self._require_profile(profile_id)

    def _default_profile(self) -> CommentatorProfile | CommentaryProfileSnapshot:
        item = self.session.scalar(
            select(CommentatorProfile)
            .where(CommentatorProfile.is_active.is_(True), CommentatorProfile.is_default.is_(True))
            .order_by(CommentatorProfile.name.asc())
        )
        if item is not None:
            return item
        item = self.session.scalar(
            select(CommentatorProfile)
            .where(CommentatorProfile.is_active.is_(True))
            .order_by(CommentatorProfile.name.asc())
        )
        if item is not None:
            return item
        return fallback_commentary_profiles()[0]

    def _selection_view(
        self,
        selection: CommentaryProfileSelection,
        *,
        primary: CommentatorProfile | CommentaryProfileSnapshot,
        secondary: CommentatorProfile | CommentaryProfileSnapshot | None,
    ) -> CommentarySelectionView:
        return CommentarySelectionView(
            selection_key=selection.selection_key,
            match_id=selection.match_id,
            primary_profile=self._profile_view(primary),
            secondary_profile=self._profile_view(secondary) if secondary is not None else None,
            dual_mode=bool(selection.dual_mode and secondary is not None),
            voice_enabled=selection.voice_enabled,
            language=selection.language,
            metadata_json=dict(selection.metadata_json or {}),
        )

    @staticmethod
    def _event_family(event_type: str) -> str:
        normalized = str(event_type or "").lower()
        if normalized in {"goal", "penalty_goal", "penalty_scored"}:
            return "goal"
        if normalized in {"shot", "shot_on_target", "missed_chance", "missed_big_chance", "woodwork"}:
            return "shot"
        if normalized in {"yellow_card", "red_card", "card"}:
            return "card"
        if normalized == "substitution":
            return "substitution"
        if normalized in {"foul", "tactical_foul"}:
            return "foul"
        return normalized or "moment"

    @staticmethod
    def _event_key(event: LiveMatchStreamEventView) -> str:
        return str(event.event_id or f"{event.minute}:{event.event_type}:{event.sequence or 0}")

    def _profile_snapshot(
        self,
        item: CommentatorProfileView | CommentatorProfile | CommentaryProfileSnapshot,
    ) -> CommentaryProfileSnapshot:
        if isinstance(item, CommentaryProfileSnapshot):
            return item
        if isinstance(item, CommentatorProfileView):
            return CommentaryProfileSnapshot.from_mapping(item.model_dump(mode="json"))
        return CommentaryProfileSnapshot.from_mapping(
            {
                "id": item.id,
                "name": item.name,
                "style": item.style,
                "tone_intensity": item.tone_intensity,
                "summary": item.summary,
                "catchphrases": list(item.catchphrases or []),
                "bias_rules": dict(item.bias_rules or {}),
                "voice_config": dict(item.voice_config or {}),
                "is_default": item.is_default,
            }
        )

    def _profile_view(
        self,
        item: CommentatorProfile | CommentaryProfileSnapshot | None,
    ) -> CommentatorProfileView:
        if item is None:
            raise CommentaryServiceError("Commentator profile was not found.")
        snapshot = self._profile_snapshot(item)
        return CommentatorProfileView(
            id=snapshot.id,
            name=snapshot.name,
            style=snapshot.style,
            tone_intensity=snapshot.tone_intensity,
            summary=snapshot.summary,
            catchphrases=list(snapshot.catchphrases),
            bias_rules=dict(snapshot.bias_rules),
            voice_config=dict(snapshot.voice_config),
            is_default=snapshot.is_default,
            is_active=True,
        )


__all__ = ["CommentaryService", "CommentaryServiceError"]
