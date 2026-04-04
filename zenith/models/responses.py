"""Response models for Zenith AI API."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    session_id: str
    suggestions: list[str] = Field(default_factory=list)
    intent: Optional[dict] = None
    execution_success: Optional[bool] = None
    error: Optional[str] = None


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
