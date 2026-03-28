from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from typing import Any

import requests


def _render_description(caption: str, hashtags: Sequence[str]) -> str:
    tag_block = " ".join(tag.strip() for tag in hashtags if str(tag).strip())
    return "\n\n".join(part for part in (caption.strip(), tag_block.strip()) if part).strip()


def _dry_run_post_id(platform: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"{platform}-dry-{digest}"


@dataclass(slots=True)
class YouTubePublisher:
    endpoint_url: str | None = None
    access_token: str | None = None
    timeout_seconds: int = 20
    dry_run: bool = True
    platform_name: str = "youtube"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "YouTubePublisher":
        env = environ or os.environ
        return cls(
            endpoint_url=env.get("GTE_PUBLISHER_YOUTUBE_API_URL"),
            access_token=env.get("GTE_PUBLISHER_YOUTUBE_ACCESS_TOKEN"),
            timeout_seconds=max(int(env.get("GTE_PUBLISHER_YOUTUBE_TIMEOUT_SECONDS", "20")), 1),
            dry_run=(env.get("GTE_PUBLISHER_DRY_RUN", "1").strip().lower() not in {"0", "false", "no", "off"}),
        )

    def publish(
        self,
        *,
        video_path: str,
        caption: str,
        hashtags: Sequence[str],
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_metadata = dict(metadata or {})
        payload = {
            "video_path": video_path,
            "title": str(resolved_metadata.get("title") or resolved_metadata.get("clip_title") or "GTEX Short"),
            "description": _render_description(caption, hashtags),
            "privacy_status": str(resolved_metadata.get("privacy_status") or "public"),
            "shorts": True,
        }
        if self.dry_run or not self.endpoint_url:
            return {
                "platform": self.platform_name,
                "status": "dry_run",
                "post_id": _dry_run_post_id(self.platform_name, payload),
                "payload": payload,
            }
        if not self.access_token:
            raise RuntimeError("YouTube publisher access token is not configured.")
        response = requests.post(
            self.endpoint_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
        post_id = data.get("post_id") or data.get("videoId") or data.get("id") or _dry_run_post_id(
            self.platform_name,
            payload,
        )
        return {
            "platform": self.platform_name,
            "status": "posted",
            "post_id": str(post_id),
            "response": data,
        }


__all__ = ["YouTubePublisher"]
