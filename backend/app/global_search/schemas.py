from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GlobalSearchResultView(BaseModel):
    type: str
    id: str
    title: str
    subtitle: str = ""
    image_url: str | None = None
    route: str
    score: float = 0.0
    permission_required: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GlobalSearchSuggestionView(BaseModel):
    label: str
    type: str
    route: str
    score: float = 0.0
