from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.community_engine import LiveThreadStatus, MessageVisibility, PrivateMessageThreadStatus


class CompetitionWatchlistCreate(BaseModel):
    competition_key: str = Field(min_length=2, max_length=120)
    competition_title: str = Field(min_length=2, max_length=180)
    competition_type: str = Field(default="general", max_length=80)
    notify_on_story: bool = True
    notify_on_launch: bool = True
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CompetitionWatchlistView(BaseModel):
    id: str
    competition_key: str
    competition_title: str
    competition_type: str
    notify_on_story: bool
    notify_on_launch: bool
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LiveThreadCreate(BaseModel):
    thread_key: str = Field(min_length=2, max_length=140)
    competition_key: str | None = Field(default=None, max_length=120)
    title: str = Field(min_length=2, max_length=180)
    pinned: bool = False
    metadata_json: dict[str, object] = Field(default_factory=dict)


class LiveThreadMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class LiveThreadView(BaseModel):
    id: str
    thread_key: str
    thread_type: str = "live_thread"
    category: str = "general"
    competition_key: str | None
    title: str
    body: str = ""
    created_by_user_id: str | None
    status: LiveThreadStatus
    pinned: bool
    visibility: str = "public"
    moderation_status: str = "visible"
    trend_score: int = 0
    locked_by_user_id: str | None = None
    locked_at: datetime | None = None
    last_message_at: datetime | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LiveThreadMessageView(BaseModel):
    id: str
    thread_id: str
    author_user_id: str
    parent_message_id: str | None = None
    message_type: str = "reply"
    body: str
    visibility: MessageVisibility
    moderation_status: str = "visible"
    like_count: int
    reply_count: int
    created_at: datetime
    metadata_json: dict[str, object]

    model_config = {"from_attributes": True}


class PrivateMessageThreadCreate(BaseModel):
    participant_user_ids: list[str] = Field(min_length=1, max_length=20)
    subject: str = Field(default="", max_length=180)
    initial_message: str = Field(min_length=1, max_length=4000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class PrivateMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class PrivateMessageParticipantView(BaseModel):
    id: str
    thread_id: str
    user_id: str
    is_muted: bool
    last_read_at: datetime | None
    joined_at: datetime
    metadata_json: dict[str, object]

    model_config = {"from_attributes": True}


class PrivateMessageView(BaseModel):
    id: str
    thread_id: str
    sender_user_id: str
    body: str
    visibility: MessageVisibility = MessageVisibility.PUBLIC
    created_at: datetime
    metadata_json: dict[str, object]

    model_config = {"from_attributes": True}


class PrivateMessageThreadView(BaseModel):
    id: str
    thread_key: str
    created_by_user_id: str
    status: PrivateMessageThreadStatus
    subject: str
    last_message_at: datetime | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
    participants: list[PrivateMessageParticipantView] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CommunityDigestView(BaseModel):
    watchlist_count: int
    live_thread_count: int
    private_thread_count: int
    unread_hint_count: int


class ChatBlockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=160)


class ChatMuteRequest(BaseModel):
    muted: bool = True


class ModerationReportCreate(BaseModel):
    reason_code: str = Field(min_length=2, max_length=48)
    description: str = Field(min_length=2, max_length=2000)


class ModerationReportView(BaseModel):
    id: str
    reporter_user_id: str
    subject_user_id: str | None
    target_type: str
    target_id: str
    reason_code: str
    description: str
    status: str
    priority: str
    report_count_for_target: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscussionCategoryView(BaseModel):
    code: str
    label: str


class DiscussionThreadCreate(BaseModel):
    category: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    body: str = Field(min_length=1, max_length=8000)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class DiscussionReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    parent_reply_id: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class DiscussionReactionCreate(BaseModel):
    reaction_type: str = Field(default="like", min_length=1, max_length=32)


class DiscussionReactionView(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    user_id: str
    reaction_type: str
    created_at: datetime
    metadata_json: dict[str, object]

    model_config = {"from_attributes": True}
