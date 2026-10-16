from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.match_engine.schemas import (
    MatchHighlightAccessView,
    MatchHighlightItemView,
    MatchHighlightListView,
    MatchHighlightPipelineView,
    MatchHighlightReelView,
    MatchReplayPayloadView,
)
from app.match_engine.simulation.models import MatchEventType, MatchHighlightProfile
from app.replay_archive.schemas import ReplayArchiveRecord

_GOAL_CATEGORIES = {"goals", "penalties"}
_KEY_MOMENT_CATEGORIES = {"goals", "penalties", "red_cards", "saves"}

_EVENT_TYPE_TO_CATEGORY: dict[str, str] = {
    "goal": "goals",
    "penalty_goal": "penalties",
    "penalty_scored": "penalties",
    "penalty_missed": "penalties",
    "penalty_miss": "penalties",
    "goalkeeper_save": "saves",
    "double_save": "saves",
    "save": "saves",
    "shot_on_target": "missed_chances",
    "missed_chance": "missed_chances",
    "missed_big_chance": "missed_chances",
    "woodwork": "missed_chances",
    "yellow_card": "yellow_cards",
    "red_card": "red_cards",
    "substitution": "substitutions",
    "substitution_impact": "substitutions",
    "injury": "injuries",
    "tactical_change": "tactical_swings",
    "tactical_swing": "tactical_swings",
}

_CATEGORY_TITLES: dict[str, str] = {
    "goals": "Goal",
    "penalties": "Penalty",
    "saves": "Big Save",
    "missed_chances": "Big Chance",
    "yellow_cards": "Yellow Card",
    "red_cards": "Red Card",
    "substitutions": "Substitution",
    "injuries": "Injury",
    "tactical_swings": "Tactical Swing",
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class MatchHighlightManifestBuilder:
    settings: Settings | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()

    def build_from_replay_payload(self, payload: MatchReplayPayloadView) -> MatchHighlightListView:
        event_by_id = {event.event_id: event for event in payload.timeline.events}
        clip_by_id = {
            clip.event_id: clip
            for clip in payload.summary.highlight_package
            if clip.event_id is not None
        }
        key_moment_by_id = {moment.event_id: moment for moment in payload.key_moments}

        ordered_ids: list[str] = []
        for clip in payload.summary.highlight_package:
            if clip.event_id and clip.event_id in event_by_id and clip.event_id not in ordered_ids:
                ordered_ids.append(clip.event_id)
        for moment in payload.key_moments:
            if moment.event_id in event_by_id and moment.event_id not in ordered_ids:
                ordered_ids.append(moment.event_id)
        if not ordered_ids:
            candidates = sorted(
                (
                    event
                    for event in payload.timeline.events
                    if self._category_for_event_type(event.event_type) in _CATEGORY_TITLES
                ),
                key=lambda event: (-self._importance_for_metadata(event.metadata), event.minute, event.sequence),
            )
            ordered_ids = [event.event_id for event in candidates[:8]]

        access = payload.summary.highlight_access or MatchHighlightAccessView(
            expires_after_seconds=600,
            archive_mode=False,
            watermark_required=True,
            signed_url_required=True,
            audit_log_required=True,
            rate_limit_per_minute=6,
            policy_checks=["entitlement", "download_policy"],
        )
        download_available = bool(payload.replay_download is not None and access.archive_mode)
        commentary_languages = list(payload.broadcast_presentation.commentary_languages) if payload.broadcast_presentation is not None else ["en"]
        commentary_modes = list(payload.broadcast_presentation.commentator_roles) if payload.broadcast_presentation is not None else ["lead", "analyst"]
        clip_items = [
            self._build_payload_item(
                match_id=payload.match_id,
                event=event_by_id[event_id],
                clip=clip_by_id.get(event_id),
                key_moment=key_moment_by_id.get(event_id),
                archive_mode=access.archive_mode,
                download_available=download_available,
                commentary_language=commentary_languages[0] if commentary_languages else "en",
            )
            for event_id in ordered_ids
            if event_id in event_by_id
        ]
        clip_items.sort(
            key=lambda item: (
                item.reel_start_second is None,
                item.reel_start_second if item.reel_start_second is not None else item.minute * 60,
                item.minute,
                item.highlight_id,
            )
        )
        reel_storage_key = self._storage_key(
            match_id=payload.match_id,
            archive_mode=access.archive_mode,
            filename="match_recap.mp4",
        )
        return MatchHighlightListView(
            match_id=payload.match_id,
            highlights=clip_items,
            replay_available=True,
            archive_available=access.archive_mode,
            download_available=download_available,
            highlight_profile=payload.summary.highlight_profile,
            access=access,
            pipeline=MatchHighlightPipelineView(
                object_storage_prefix=self.settings.highlight_temp_prefix,
                object_archive_prefix=self.settings.highlight_archive_prefix,
                cdn_base_url=self.settings.cdn_base_url,
                commentary_languages=commentary_languages,
                commentary_modes=commentary_modes,
            ),
            reel=MatchHighlightReelView(
                title=self._reel_title(
                    payload.summary.highlight_profile,
                    payload.summary.home_stats.team_name,
                    payload.summary.away_stats.team_name,
                ),
                clip_count=len(clip_items),
                runtime_seconds=payload.summary.highlight_runtime_seconds,
                storage_key=reel_storage_key,
                cdn_path=self._cdn_path(reel_storage_key),
                render_status="manifest_ready",
            ),
            generated_at=_utcnow(),
        )

    def build_from_archive_record(self, match_id: str, record: ReplayArchiveRecord) -> MatchHighlightListView:
        archive_mode = bool(record.final_whistle_at is not None and not record.live)
        default_access = MatchHighlightAccessView(
            expires_after_seconds=None if archive_mode else 600,
            archive_mode=archive_mode,
            watermark_required=True,
            signed_url_required=True,
            audit_log_required=True,
            rate_limit_per_minute=6,
            policy_checks=["entitlement", "download_policy"],
        )
        items: list[MatchHighlightItemView] = []
        cursor = 0
        for entry in record.timeline:
            category = self._category_for_event_type(entry.event_type)
            if category not in _CATEGORY_TITLES:
                continue
            importance = self._importance_for_archive_category(category)
            pre_roll, post_roll = self._window_seconds(category=category, xg=0.0, importance=importance)
            event_second = max(0, entry.minute * 60)
            duration_seconds = max(1, pre_roll + post_roll)
            reel_start_second = cursor
            reel_end_second = cursor + duration_seconds
            cursor = reel_end_second + 2
            storage_key = self._storage_key(
                match_id=match_id,
                archive_mode=archive_mode,
                filename=f"{category}_{entry.minute:02d}.mp4",
            )
            scoreline_label = f"{entry.home_score}-{entry.away_score}"
            crowd_spike = category in _KEY_MOMENT_CATEGORIES
            items.append(
                MatchHighlightItemView(
                    highlight_id=entry.event_id,
                    title=self._display_title(category=category, player_name=entry.player_name, team_name=entry.club_name),
                    label=self._label(entry.club_name, entry.player_name),
                    minute=entry.minute,
                    event_type=category,
                    team_name=entry.club_name,
                    player_name=entry.player_name,
                    access_state="available",
                    archive_available=archive_mode,
                    download_available=False,
                    reel_start_second=reel_start_second,
                    reel_end_second=reel_end_second,
                    match_clock_start_second=max(0, event_second - pre_roll),
                    match_clock_end_second=event_second + post_roll,
                    match_clock_start_label=self._clock_label(max(0, event_second - pre_roll)),
                    match_clock_end_label=self._clock_label(event_second + post_roll),
                    duration_seconds=duration_seconds,
                    importance=importance,
                    camera_sequence=self._camera_sequence(category=category, render_camera_mode=None, slow_motion=crowd_spike, crowd_spike=crowd_spike),
                    slow_motion=crowd_spike,
                    replay_speed=0.5 if crowd_spike else 0.75,
                    overlay_title=f"{_CATEGORY_TITLES[category].upper()} - {entry.minute}'",
                    overlay_subtitle=self._overlay_subtitle(
                        player_name=entry.player_name,
                        team_name=entry.club_name,
                        scoreline_label=scoreline_label,
                    ),
                    scoreline_label=scoreline_label,
                    crowd_profile="archive",
                    crowd_spike=crowd_spike,
                    commentary_language="en",
                    storage_key=storage_key,
                    cdn_path=self._cdn_path(storage_key),
                    render_status="manifest_ready",
                    metadata={
                        "source": "archive_record",
                        "queue_hint": "clip_builder_queue",
                    },
                )
            )
        reel_storage_key = self._storage_key(
            match_id=match_id,
            archive_mode=archive_mode,
            filename="match_recap.mp4",
        )
        return MatchHighlightListView(
            match_id=match_id,
            highlights=items,
            replay_available=True,
            archive_available=archive_mode,
            download_available=False,
            highlight_profile=MatchHighlightProfile.ELITE_FINAL if record.competition_context.is_final else MatchHighlightProfile.NORMAL,
            access=default_access,
            pipeline=MatchHighlightPipelineView(
                object_storage_prefix=self.settings.highlight_temp_prefix,
                object_archive_prefix=self.settings.highlight_archive_prefix,
                cdn_base_url=self.settings.cdn_base_url,
                commentary_languages=["en"],
                commentary_modes=["lead", "analyst"],
            ),
            reel=MatchHighlightReelView(
                title=self._reel_title(
                    MatchHighlightProfile.ELITE_FINAL if record.competition_context.is_final else MatchHighlightProfile.NORMAL,
                    record.home_club.club_name,
                    record.away_club.club_name,
                ),
                clip_count=len(items),
                runtime_seconds=max(0, cursor - 2) if items else 0,
                storage_key=reel_storage_key,
                cdn_path=self._cdn_path(reel_storage_key),
                render_status="manifest_ready",
            ),
            generated_at=_utcnow(),
        )

    def _build_payload_item(
        self,
        *,
        match_id: str,
        event,
        clip,
        key_moment,
        archive_mode: bool,
        download_available: bool,
        commentary_language: str,
    ) -> MatchHighlightItemView:
        category = self._category_for_event_type(event.event_type)
        importance = self._importance_for_metadata(event.metadata)
        xg = self._float_value(event.metadata.get("xg", event.metadata.get("chance_quality", 0.0)))
        pre_roll, post_roll = self._window_seconds(category=category, xg=xg, importance=importance)
        event_second = max(0, event.minute * 60)
        render = event.metadata.get("render") if isinstance(event.metadata.get("render"), dict) else {}
        render_camera = render.get("camera") if isinstance(render.get("camera"), dict) else {}
        render_replay = render.get("replay") if isinstance(render.get("replay"), dict) else {}
        slow_motion = bool(render_camera.get("slow_motion")) or (category in _KEY_MOMENT_CATEGORIES and importance >= 4)
        crowd_spike = bool(event.metadata.get("crowd_spike")) or category in _KEY_MOMENT_CATEGORIES or importance >= 4
        reel_start_second = (
            clip.start_second
            if clip is not None
            else key_moment.start_second
            if key_moment is not None
            else None
        )
        reel_end_second = (
            clip.end_second
            if clip is not None
            else key_moment.end_second
            if key_moment is not None
            else None
        )
        duration_seconds = (
            max(1, reel_end_second - reel_start_second)
            if reel_start_second is not None and reel_end_second is not None
            else max(1, pre_roll + post_roll)
        )
        storage_key = self._storage_key(
            match_id=match_id,
            archive_mode=archive_mode,
            filename=f"{category}_{event.minute:02d}_{event.sequence:03d}.mp4",
        )
        scoreline_label = f"{event.home_score}-{event.away_score}"
        player_name = event.primary_player.player_name if event.primary_player is not None else None
        team_name = event.team_name
        clock_label = event.clock_label or f"{event.minute}'"
        return MatchHighlightItemView(
            highlight_id=event.event_id,
            title=clip.title if clip is not None else self._display_title(category=category, player_name=player_name, team_name=team_name),
            label=self._label(team_name, player_name),
            minute=event.minute,
            event_type=category,
            team_name=team_name,
            player_name=player_name,
            access_state="available",
            archive_available=archive_mode,
            download_available=download_available,
            reel_start_second=reel_start_second,
            reel_end_second=reel_end_second,
            match_clock_start_second=max(0, event_second - pre_roll),
            match_clock_end_second=event_second + post_roll,
            match_clock_start_label=self._clock_label(max(0, event_second - pre_roll)),
            match_clock_end_label=self._clock_label(event_second + post_roll),
            duration_seconds=duration_seconds,
            importance=importance,
            camera_sequence=self._camera_sequence(
                category=category,
                render_camera_mode=self._string_value(render_camera.get("mode")),
                slow_motion=slow_motion,
                crowd_spike=crowd_spike,
            ),
            slow_motion=slow_motion,
            replay_speed=self._float_value(render_replay.get("speed", 0.5 if slow_motion else 0.75)),
            overlay_title=f"{_CATEGORY_TITLES.get(category, 'HIGHLIGHT').upper()} - {clock_label}",
            overlay_subtitle=self._overlay_subtitle(
                player_name=player_name,
                team_name=team_name,
                scoreline_label=scoreline_label,
            ),
            scoreline_label=scoreline_label,
            crowd_profile=self._string_value(event.metadata.get("crowd_profile")),
            crowd_spike=crowd_spike,
            commentary_language=commentary_language,
            storage_key=storage_key,
            cdn_path=self._cdn_path(storage_key),
            render_status="manifest_ready",
            metadata={
                "source": "replay_payload",
                "raw_event_type": event.event_type.value,
                "render_type": render.get("type"),
                "queue_hint": "clip_builder_queue",
                "xg": xg,
                "importance": importance,
                "team_id": event.team_id,
                "secondary_player_name": event.secondary_player.player_name if event.secondary_player is not None else None,
            },
        )

    def _reel_title(self, profile: MatchHighlightProfile, home_team: str, away_team: str) -> str:
        if profile is MatchHighlightProfile.ELITE_FINAL:
            return f"{home_team} vs {away_team} Final Recap"
        return f"{home_team} vs {away_team} Match Recap"

    def _category_for_event_type(self, event_type: MatchEventType | str) -> str:
        raw = event_type.value if isinstance(event_type, MatchEventType) else str(event_type)
        normalized = raw.strip().lower()
        return _EVENT_TYPE_TO_CATEGORY.get(normalized, normalized)

    def _importance_for_metadata(self, metadata: dict[str, Any] | None) -> int:
        if not metadata:
            return 3
        try:
            return max(1, min(5, int(metadata.get("importance", 3) or 3)))
        except (TypeError, ValueError):
            return 3

    def _importance_for_archive_category(self, category: str) -> int:
        if category in _GOAL_CATEGORIES or category == "red_cards":
            return 5
        if category == "saves":
            return 4
        return 3

    def _window_seconds(self, *, category: str, xg: float, importance: int) -> tuple[int, int]:
        if category in _GOAL_CATEGORIES:
            return 10, 5 + (1 if importance >= 5 else 0)
        if category == "red_cards":
            return 6, 6
        if xg > 0.5:
            return 8, 3
        if category == "saves":
            return 8, 4
        if category == "missed_chances":
            return 7, 4
        if category in {"substitutions", "injuries"}:
            return 5, 4
        return 6, 4

    def _camera_sequence(
        self,
        *,
        category: str,
        render_camera_mode: str | None,
        slow_motion: bool,
        crowd_spike: bool,
    ) -> list[str]:
        sequence = {
            "goals": ["broadcast_wide", "player_follow", "goal_zoom"],
            "penalties": ["broadcast_wide", "player_follow", "goal_zoom"],
            "saves": ["broadcast_wide", "goal_zoom"],
            "red_cards": ["broadcast_wide", "player_follow"],
            "missed_chances": ["broadcast_wide", "goal_zoom"],
            "substitutions": ["broadcast_wide", "player_follow"],
            "injuries": ["broadcast_wide", "player_follow"],
            "tactical_swings": ["broadcast_wide", "player_follow"],
        }.get(category, ["broadcast_wide", "player_follow"])
        normalized_mode = {
            "goal_camera": "goal_zoom",
            "attack_zoom": "player_follow",
            "broadcast": "broadcast_wide",
            "assistant_flag": "broadcast_wide",
        }.get((render_camera_mode or "").strip().lower())
        if normalized_mode is not None and normalized_mode not in sequence:
            sequence.insert(1, normalized_mode)
        if slow_motion:
            sequence.append("slow_motion")
        if crowd_spike or category in _GOAL_CATEGORIES:
            sequence.append("crowd_reaction")
        deduped: list[str] = []
        for item in sequence:
            if item not in deduped:
                deduped.append(item)
        return deduped

    def _storage_key(self, *, match_id: str, archive_mode: bool, filename: str) -> str:
        prefix = self.settings.highlight_archive_prefix if archive_mode else self.settings.highlight_temp_prefix
        return f"{prefix.rstrip('/')}/{match_id}/{filename}"

    def _cdn_path(self, storage_key: str | None) -> str | None:
        if not storage_key or not self.settings.cdn_base_url:
            return None
        return f"{self.settings.cdn_base_url.rstrip('/')}/{storage_key.lstrip('/')}"

    def _display_title(self, *, category: str, player_name: str | None, team_name: str | None) -> str:
        base = _CATEGORY_TITLES.get(category, "Highlight")
        if player_name:
            return f"{base}: {player_name}"
        if team_name:
            return f"{base}: {team_name}"
        return base

    def _overlay_subtitle(self, *, player_name: str | None, team_name: str | None, scoreline_label: str) -> str:
        parts = [part for part in (player_name, team_name, scoreline_label) if part]
        return " | ".join(parts)

    def _label(self, team_name: str | None, player_name: str | None) -> str | None:
        if team_name and player_name:
            return f"{team_name} - {player_name}"
        return team_name or player_name

    def _clock_label(self, total_seconds: int) -> str:
        minutes, seconds = divmod(max(0, total_seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _float_value(self, value: object) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _string_value(self, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
