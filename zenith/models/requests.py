"""Request models for Zenith AI API."""
from datetime import datetime
from typing import Optional
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


class SearchNotesRequest(BaseModel):
    """Request model for searching notes."""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)


class UpdateSettingsRequest(BaseModel):
    """Request model for updating user settings."""
    timezone: Optional[str] = None
    language: Optional[str] = None
    notifications_enabled: Optional[bool] = None
