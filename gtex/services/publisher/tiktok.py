from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from typing import Any

import requests


def _render_caption(caption: str, hashtags: Sequence[str]) -> str:
    tag_block = " ".join(tag.strip() for tag in hashtags if str(tag).strip())
    return " ".join(part for part in (caption.strip(), tag_block.strip()) if part).strip()


def _dry_run_post_id(platform: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha1(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"{platform}-dry-{digest}"


@dataclass(slots=True)
class TikTokPublisher:
    endpoint_url: str | None = None
    access_token: str | None = None
    timeout_seconds: int = 20
    dry_run: bool = True
    platform_name: str = "tiktok"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "TikTokPublisher":
        env = environ or os.environ
        return cls(
            endpoint_url=env.get("GTE_PUBLISHER_TIKTOK_API_URL"),
            access_token=env.get("GTE_PUBLISHER_TIKTOK_ACCESS_TOKEN"),
            timeout_seconds=max(int(env.get("GTE_PUBLISHER_TIKTOK_TIMEOUT_SECONDS", "20")), 1),
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
        payload = {
            "video_path": video_path,
            "caption": _render_caption(caption, hashtags),
            "privacy_level": str((metadata or {}).get("privacy_level") or "PUBLIC_TO_EVERYONE"),
            "disable_comment": bool((metadata or {}).get("disable_comment", False)),
            "brand_content": bool((metadata or {}).get("brand_content", False)),
        }
        if self.dry_run or not self.endpoint_url:
            return {
                "platform": self.platform_name,
                "status": "dry_run",
                "post_id": _dry_run_post_id(self.platform_name, payload),
                "payload": payload,
            }
        if not self.access_token:
            raise RuntimeError("TikTok publisher access token is not configured.")
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
        post_id = (
            data.get("post_id")
            or data.get("publish_id")
            or data.get("id")
            or _dry_run_post_id(self.platform_name, payload)
        )
        return {
            "platform": self.platform_name,
            "status": "posted",
            "post_id": str(post_id),
            "response": data,
        }


__all__ = ["TikTokPublisher"]
