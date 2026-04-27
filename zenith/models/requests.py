"""Request models for Zenith AI API."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, EmailStr


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = Field(None, description="Existing session ID or create new")


class CreateEventRequest(BaseModel):
    """Request model for creating calendar events."""
    summary: str = Field(..., min_length=1, max_length=500)
    start_time: datetime
    end_time: datetime
    description: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=500)
    attendees: Optional[list[EmailStr]] = None
    timezone: str = Field(default="UTC")
    add_google_meet: bool = Field(default=False)


class QuickAddEventRequest(BaseModel):
    """Request model for quick-adding events using natural language."""
    text: str = Field(..., min_length=1, max_length=500,
                     examples=["Meeting with John tomorrow at 3pm",
                              "Lunch at 12:30pm on Friday"])


class SendEmailRequest(BaseModel):
    """Request model for sending emails."""
    to: list[EmailStr] = Field(..., min_items=1)
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=50000)
    cc: Optional[list[EmailStr]] = None
    bcc: Optional[list[EmailStr]] = None
    html_body: Optional[str] = None
    reply_to_thread_id: Optional[str] = None


class SearchEmailRequest(BaseModel):
    """Request model for searching emails."""
    query: Optional[str] = Field(None, max_length=500)
    max_results: int = Field(default=10, ge=1, le=50)
    label_ids: Optional[list[str]] = None


class AddTaskRequest(BaseModel):
    """Request model for adding tasks."""
    title: str = Field(..., min_length=1, max_length=500)
    notes: Optional[str] = Field(None, max_length=5000)
    due_date: Optional[datetime] = None
    task_list_id: str = Field(default="@default")


class SetReminderRequest(BaseModel):
    """Request model for setting reminders."""
    title: str = Field(..., min_length=1, max_length=500)
    remind_at: datetime
    notes: Optional[str] = Field(None, max_length=2000)


class SaveNoteRequest(BaseModel):
    """Request model for saving notes."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=50000)
    tags: Optional[list[str]] = Field(None, max_items=20)
    source: Optional[str] = Field(default="manual")


class UpdateNoteRequest(BaseModel):
    """Request model for updating notes."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1, max_length=50000)
    tags: Optional[list[str]] = Field(None, max_items=20)


class SearchNotesRequest(BaseModel):
    """Request model for searching notes."""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)


class UpdateSettingsRequest(BaseModel):
    """Request model for updating user settings."""
    timezone: Optional[str] = None
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None


# ==================== New Models for Agent Upgrade ====================


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences."""
    preferred_meeting_times: Optional[list[str]] = Field(
        None,
        description="e.g. ['09:00-12:00', '14:00-16:00']"
    )
    frequent_contacts: Optional[list[str]] = Field(
        None,
        description="List of frequently contacted email addresses"
    )
    email_tone: Optional[str] = Field(
        None,
        description="formal | casual | professional"
    )
    custom_rules: Optional[list[str]] = Field(
        None,
        description="List of custom productivity or communication rules"
    )
    working_hours: Optional[dict] = Field(
        None,
        description="{'start': '09:00', 'end': '17:00', 'days': ['Monday', ...]}"
    )
    timezone: Optional[str] = None
    notification_preferences: Optional[dict] = None


class ConfirmActionRequest(BaseModel):
    """Request model for confirming a pending action."""
    session_id: str = Field(..., description="Session with pending action")
    action: str = Field(
        default="approve",
        description="approve | cancel | edit"
    )


class EditTaskRequest(BaseModel):
    """Request model for editing task payload before creation."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    due: Optional[datetime] = None
