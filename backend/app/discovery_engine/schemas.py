from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DiscoveryItemView(BaseModel):
    item_type: str
    item_id: str
    title: str
    subtitle: str = ""
    rail_key: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeaturedRailView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rail_key: str
    title: str
    rail_type: str
    audience: str
    query_hint: str | None = None
    subtitle: str = ""
    display_order: int
    active: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class FeaturedRailUpsertRequest(BaseModel):
    rail_key: str
    title: str
    rail_type: str = "story"
    audience: str = "public"
    query_hint: str | None = None
    subtitle: str = ""
    display_order: int = 0
    active: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SavedSearchView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    entity_scope: str
    alerts_enabled: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SavedSearchCreate(BaseModel):
    query: str
    entity_scope: str = "all"
    alerts_enabled: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class DiscoveryHomeView(BaseModel):
    featured_rails: list[FeaturedRailView]
    featured_items: list[DiscoveryItemView]
    recommended_items: list[DiscoveryItemView]
    live_now_items: list[DiscoveryItemView]
    saved_searches: list[SavedSearchView]
