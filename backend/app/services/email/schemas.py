from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EmailSendResult:
    success: bool
    provider: str
    message_id: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to_email: str
    subject: str
    text_body: str
    html_body: str | None = None
    reply_to: str | None = None


@dataclass(frozen=True, slots=True)
class EmailTemplatePayload:
    to_email: str
    subject: str
    text_body: str
    html_template_path: Path
    context: Mapping[str, str]
    reply_to: str | None = None
