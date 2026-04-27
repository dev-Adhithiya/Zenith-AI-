"""Response models for Zenith AI API."""
from datetime import datetime
from typing import Optional, Any, Literal, Union
from pydantic import BaseModel, Field, model_validator


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    session_id: str
    suggestions: list[str] = Field(default_factory=list)
    intent: Optional[dict] = None
    execution_success: Optional[bool] = None
    error: Optional[str] = None
    requires_confirmation: Optional[bool] = None
    pending_plan: Optional[dict] = None
    debug: Optional[dict] = None


class EventResponse(BaseModel):
    """Response model for calendar events."""
    id: str
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start: str
    end: str
    timezone: Optional[str] = None
    is_all_day: bool = False
    html_link: Optional[str] = None
    meet_link: Optional[str] = None
    organizer: Optional[str] = None
    attendees: list[dict] = Field(default_factory=list)
    status: Optional[str] = None


class EventListResponse(BaseModel):
    """Response model for list of events."""
    events: list[EventResponse]
    count: int


class EmailResponse(BaseModel):
    """Response model for email messages."""
    id: str
    thread_id: str
    subject: Optional[str] = None
    sender: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None
    date: Optional[str] = None
    snippet: Optional[str] = None
    body_text: Optional[str] = None
    is_unread: bool = False
    is_important: bool = False
    labels: list[str] = Field(default_factory=list)


class EmailListResponse(BaseModel):
    """Response model for list of emails."""
    emails: list[EmailResponse]
    count: int


class InboxSummaryResponse(BaseModel):
    """Response model for inbox summary."""
    total_count: int
    unread_count: int
    important_count: int
    senders: dict[str, int] = Field(default_factory=dict)
    time_range: dict[str, str] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """Response model for tasks."""
    id: str
    title: str
    notes: Optional[str] = None
    status: str
    due: Optional[str] = None
    completed: Optional[str] = None
    is_completed: bool = False


class TaskListResponse(BaseModel):
    """Response model for list of tasks."""
    tasks: list[TaskResponse]
    count: int


class NoteResponse(BaseModel):
    """Response model for notes."""
    note_id: str
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    source: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    relevance_score: Optional[float] = None


class NoteListResponse(BaseModel):
    """Response model for list of notes."""
    notes: list[NoteResponse]
    count: int


class UserResponse(BaseModel):
    """Response model for user data."""
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    settings: dict = Field(default_factory=dict)
    created_at: str
    last_login: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for conversation sessions."""
    session_id: str
    started_at: str
    last_activity: str
    message_count: int


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = "healthy"
    version: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class AuthUrlResponse(BaseModel):
    """Response model for OAuth authorization URL."""
    authorization_url: str
    state: str


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False


class BriefingResponse(BaseModel):
    """Response model for login briefing."""
    status: str
    title: str
    content: str
    error: Optional[str] = None
    metadata: Optional[dict] = None


# ==================== New Models for Agent Upgrade ====================


class InsightItem(BaseModel):
    """A single proactive insight."""
    type: str = Field(description="warning | suggestion | reminder")
    title: str
    message: str
    priority: str = Field(default="medium", description="high | medium | low")
    related_to: str = Field(default="general", description="calendar | email | tasks")


class DailyBriefingResponse(BaseModel):
    """Response model for the daily briefing / insights endpoint."""
    status: str
    meetings: list[dict] = Field(default_factory=list)
    emails: list[dict] = Field(default_factory=list)
    tasks: list[dict] = Field(default_factory=list)
    insights: list[InsightItem] = Field(default_factory=list)
    summary: str = ""
    metadata: Optional[dict] = None


class PreferencesResponse(BaseModel):
    """Response model for user preferences."""
    preferences: dict = Field(default_factory=dict)
    updated_at: Optional[str] = None


class DebugResponse(BaseModel):
    """Debug information returned when ?debug=true."""
    plan: Optional[dict] = None
    steps_executed: list[dict] = Field(default_factory=list)
    latency_ms: float = 0.0
    tools_used: list[str] = Field(default_factory=list)
    risk_level: Optional[str] = None
    planner_reasoning: Optional[str] = None


class TaskPayload(BaseModel):
    """Payload for task action UI buttons (Add Task / Edit & Add Task)."""

    title: str
    description: Optional[str] = None
    due: Optional[str] = None


class MeetingPayload(BaseModel):
    """Payload for meeting action UI buttons (Schedule Meeting / Edit Details / Autoprep)."""

    title: str
    description: Optional[str] = None
    attendees: list[str] = Field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class EmailActionItem(BaseModel):
    """Strict one-action-per-email item for priority feed."""

    id: str
    type: Literal["email_action"] = "email_action"
    action_type: Literal["reply", "task", "meeting", "ignore"]
    ui_actions: list[str] = Field(default_factory=list)
    title: str
    sender: str = Field(alias="from", serialization_alias="from")
    summary: str
    reason: str
    draft_reply: Optional[str] = None
    task_payload: Optional[TaskPayload] = None
    meeting_payload: Optional[MeetingPayload] = None

    @model_validator(mode="after")
    def validate_payload_mapping(self) -> "EmailActionItem":
        expected_actions = {
            "reply": ["Send Reply", "Edit Reply", "Ignore"],
            "task": ["Add Task", "Edit & Add Task", "Ignore"],
            "meeting": ["Schedule Meeting", "Edit Details", "Autoprep", "Ignore"],
            "ignore": ["Ignore only"],
        }
        if self.ui_actions != expected_actions[self.action_type]:
            raise ValueError("ui_actions do not match action_type contract")

        payload_count = sum(
            bool(v) for v in (self.draft_reply, self.task_payload, self.meeting_payload)
        )
        if self.action_type == "ignore" and payload_count != 0:
            raise ValueError("ignore must not include payloads")
        if self.action_type in {"reply", "task", "meeting"} and payload_count != 1:
            raise ValueError("non-ignore must include exactly one payload")
        return self


class MeetingPrepDetails(BaseModel):
    """AutoPrep payload for meeting prep cards."""

    risks: list[str] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)


class MeetingPrepItem(BaseModel):
    """AutoPrep output. Does not include task actions."""

    id: str
    type: Literal["meeting_prep"] = "meeting_prep"
    status: Literal["ready", "needs_clarification"]
    title: str
    summary: str
    reason: str
    prep: MeetingPrepDetails


class PriorityFeedResponse(BaseModel):
    """Merged priority feed with strict action mapping contracts."""

    status: str
    items: list[Union[EmailActionItem, MeetingPrepItem]] = Field(default_factory=list)
    metadata: Optional[dict] = None


class TaskEditPreviewResponse(BaseModel):
    """Preview response for edit-and-add task UX."""

    status: str = "ok"
    task_payload: TaskPayload
