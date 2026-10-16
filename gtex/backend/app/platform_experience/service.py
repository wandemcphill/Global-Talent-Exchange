from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.broadcast_network.service import ensure_broadcast_network_runtime
from app.models.fan_experience import FanExperienceTicket
from app.models.platform_experience_state import PlatformExperienceState
from app.models.user import User
from app.platform_experience.schemas import PlatformSwitchRequest


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PlatformExperienceService:
    def __init__(self, session: Session, *, app: FastAPI | None = None) -> None:
        self.session = session
        self.app = app

    def get_mode(self, *, current_user: User | None, device_id: str | None = None) -> dict[str, Any]:
        if current_user is None:
            return {
                "mode": "mobile",
                "device_id": device_id,
                "device_name": None,
                "available_modes": ["mobile", "web", "tv"],
                "features": self._features_for_mode("mobile"),
                "sync_state": {
                    "source_device_id": None,
                    "source_device_name": None,
                    "resume_match_id": None,
                    "resume_channel_id": None,
                    "resume_position_seconds": 0.0,
                    "commentary_cursor": 0,
                    "watch_history": [],
                    "last_synced_at": None,
                    "metadata": {"authenticated": False},
                },
                "metadata": {"authenticated": False},
            }

        states = self._states_for_user(current_user.id)
        active = self._resolve_active_state(states, device_id=device_id)
        sync_source = self._resolve_sync_source(states, active=active)
        mode = active.mode if active is not None else "mobile"
        features = {
            **self._features_for_mode(mode),
            **self._ticket_feature_flags(current_user.id),
        }
        return {
            "mode": mode,
            "device_id": active.device_id if active is not None else device_id,
            "device_name": active.device_name if active is not None else None,
            "available_modes": ["mobile", "web", "tv"],
            "features": features,
            "sync_state": self._sync_payload(states, sync_source=sync_source),
            "metadata": {
                "authenticated": True,
                "device_count": len(states),
                "tv_ready": True,
            },
        }

    def switch_mode(self, *, current_user: User, payload: PlatformSwitchRequest) -> dict[str, Any]:
        state = self.session.scalar(
            select(PlatformExperienceState).where(
                PlatformExperienceState.user_id == current_user.id,
                PlatformExperienceState.device_id == payload.device_id,
            )
        )
        now = _utcnow()
        title = self._resolve_program_title(
            channel_id=payload.current_channel_id,
            match_id=payload.current_match_id,
        )
        history_entry = {
            "watched_at": now.isoformat(),
            "mode": payload.mode,
            "device_id": payload.device_id,
            "device_name": payload.device_name,
            "match_id": payload.current_match_id,
            "channel_id": payload.current_channel_id,
            "title": title,
            "resume_position_seconds": round(float(payload.resume_position_seconds), 3),
            "commentary_cursor": int(payload.commentary_cursor),
            "metadata": dict(payload.metadata),
        }
        if state is None:
            state = PlatformExperienceState(
                user_id=current_user.id,
                device_id=payload.device_id,
                watch_history_json=[],
                metadata_json={},
            )
            self.session.add(state)
        state.device_name = payload.device_name
        state.mode = payload.mode
        state.current_match_id = payload.current_match_id
        state.current_channel_id = payload.current_channel_id
        state.resume_position_seconds = float(payload.resume_position_seconds)
        state.commentary_cursor = int(payload.commentary_cursor)
        state.last_watch_at = now
        state.metadata_json = {
            **dict(state.metadata_json or {}),
            **dict(payload.metadata),
            "last_program_title": title,
        }
        history = [
            item
            for item in list(state.watch_history_json or [])
            if isinstance(item, dict)
        ]
        if payload.current_match_id or payload.current_channel_id:
            history.insert(0, history_entry)
        state.watch_history_json = history[:12]
        self.session.flush()
        return self.get_mode(current_user=current_user, device_id=payload.device_id)

    def broadcast_guide(self) -> dict[str, Any]:
        if self.app is None:
            return {
                "what_is_live_now": None,
                "featured_channel": None,
                "channels": [],
                "highlight_reels": [],
                "auto_switch_policy": {
                    "enabled": False,
                    "auto_play_matches": True,
                    "highlight_reels_between_matches": True,
                },
                "metadata": {"channel_count": 0},
            }
        runtime = ensure_broadcast_network_runtime(self.app)
        home = runtime.home()
        channels = list(home.channels)
        reels: list[dict[str, Any]] = []
        for channel in channels:
            current_program = channel.current_program
            if current_program is not None and current_program.replay_route:
                reels.append(
                    {
                        "reel_id": f"{channel.channel_id}:{current_program.slot_id}",
                        "title": f"{current_program.title} Highlights",
                        "channel_id": channel.channel_id,
                        "match_id": current_program.match_id,
                        "replay_route": current_program.replay_route,
                        "reason": "between_match_window" if current_program.program_type == "replay_loop" else "post_match_recap",
                        "metadata": {"program_type": current_program.program_type},
                    }
                )
            for upcoming in channel.upcoming_programs[:2]:
                if not upcoming.replay_route:
                    continue
                reels.append(
                    {
                        "reel_id": f"{channel.channel_id}:{upcoming.slot_id}:next",
                        "title": f"{upcoming.title} Preview Reel",
                        "channel_id": channel.channel_id,
                        "match_id": upcoming.match_id,
                        "replay_route": upcoming.replay_route,
                        "reason": "upcoming_match_preview",
                        "metadata": {"program_type": upcoming.program_type},
                    }
                )
        deduped_reels: list[dict[str, Any]] = []
        seen_reel_ids: set[str] = set()
        for reel in reels:
            reel_id = str(reel["reel_id"])
            if reel_id in seen_reel_ids:
                continue
            seen_reel_ids.add(reel_id)
            deduped_reels.append(reel)
        return {
            "what_is_live_now": home.match_of_the_moment,
            "featured_channel": home.featured_channel,
            "channels": channels,
            "highlight_reels": deduped_reels[:8],
            "auto_switch_policy": {
                "enabled": any(channel.auto_switch_enabled for channel in channels),
                "auto_play_matches": True,
                "highlight_reels_between_matches": True,
                "switch_on_match_end": True,
                "remote_friendly": True,
            },
            "metadata": {
                "channel_count": len(channels),
                "generated_at": home.generated_at,
                "featured_channel_id": home.featured_channel.channel_id if home.featured_channel is not None else None,
            },
        }

    def _states_for_user(self, user_id: str) -> list[PlatformExperienceState]:
        return list(
            self.session.scalars(
                select(PlatformExperienceState)
                .where(PlatformExperienceState.user_id == user_id)
                .order_by(PlatformExperienceState.last_watch_at.desc(), PlatformExperienceState.updated_at.desc())
            ).all()
        )

    def _resolve_active_state(
        self,
        states: list[PlatformExperienceState],
        *,
        device_id: str | None,
    ) -> PlatformExperienceState | None:
        if device_id:
            for state in states:
                if state.device_id == device_id:
                    return state
        return states[0] if states else None

    def _resolve_sync_source(
        self,
        states: list[PlatformExperienceState],
        *,
        active: PlatformExperienceState | None,
    ) -> PlatformExperienceState | None:
        if active is None:
            return states[0] if states else None
        for state in states:
            if state.id != active.id and (state.current_match_id or state.current_channel_id):
                return state
        return active

    def _sync_payload(
        self,
        states: list[PlatformExperienceState],
        *,
        sync_source: PlatformExperienceState | None,
    ) -> dict[str, Any]:
        history: list[dict[str, Any]] = []
        for state in states:
            for item in list(state.watch_history_json or []):
                if not isinstance(item, dict):
                    continue
                history.append(
                    {
                        "watched_at": item.get("watched_at") or state.last_watch_at,
                        "mode": item.get("mode") or state.mode,
                        "device_id": item.get("device_id") or state.device_id,
                        "device_name": item.get("device_name") or state.device_name,
                        "match_id": item.get("match_id"),
                        "channel_id": item.get("channel_id"),
                        "title": item.get("title"),
                        "resume_position_seconds": float(item.get("resume_position_seconds") or 0.0),
                        "commentary_cursor": int(item.get("commentary_cursor") or 0),
                        "metadata": dict(item.get("metadata") or {}),
                    }
                )
        history.sort(
            key=lambda item: str(item.get("watched_at") or ""),
            reverse=True,
        )
        return {
            "source_device_id": sync_source.device_id if sync_source is not None else None,
            "source_device_name": sync_source.device_name if sync_source is not None else None,
            "resume_match_id": sync_source.current_match_id if sync_source is not None else None,
            "resume_channel_id": sync_source.current_channel_id if sync_source is not None else None,
            "resume_position_seconds": round(float(sync_source.resume_position_seconds), 3) if sync_source is not None else 0.0,
            "commentary_cursor": int(sync_source.commentary_cursor) if sync_source is not None else 0,
            "watch_history": history[:8],
            "last_synced_at": sync_source.last_watch_at if sync_source is not None else None,
            "metadata": {
                "watch_history_count": min(len(history), 8),
                "commentary_synced": sync_source is not None and int(sync_source.commentary_cursor) > 0,
            },
        }

    def _resolve_program_title(self, *, channel_id: str | None, match_id: str | None) -> str | None:
        if self.app is None or channel_id is None:
            return None
        runtime = ensure_broadcast_network_runtime(self.app)
        for channel in runtime.list_channels():
            if channel.channel_id != channel_id:
                continue
            if channel.current_program is not None and (
                match_id is None or channel.current_program.match_id == match_id
            ):
                return channel.current_program.title
            for program in channel.upcoming_programs:
                if match_id is None or program.match_id == match_id:
                    return program.title
        return None

    def _ticket_feature_flags(self, user_id: str) -> dict[str, bool]:
        tickets = list(
            self.session.scalars(
                select(FanExperienceTicket).where(
                    FanExperienceTicket.user_id == user_id,
                    FanExperienceTicket.status.in_(("purchased", "attended")),
                )
            ).all()
        )
        return {
            "priority_stream_access": any(bool(ticket.priority_stream) for ticket in tickets),
            "exclusive_commentary_lane": any(bool(ticket.exclusive_commentary_lines_json) for ticket in tickets),
            "ceremony_tv_access": any(ticket.event_type == "ceremony" for ticket in tickets),
        }

    @staticmethod
    def _features_for_mode(mode: str) -> dict[str, bool]:
        return {
            "vertical_feed": mode == "mobile",
            "quick_view": mode == "mobile",
            "multi_match_view": mode == "web",
            "advanced_stats": mode == "web",
            "trading_console": mode == "web",
            "full_screen_broadcast": mode == "tv",
            "auto_play_matches": mode == "tv",
            "channel_switching": mode == "tv",
            "remote_friendly_ui": mode == "tv",
        }


__all__ = ["PlatformExperienceService"]
