"""Models module for Zenith AI - Pydantic models for API requests/responses."""
from .requests import (
    ChatRequest,
    CreateEventRequest,
    SendEmailRequest,
    AddTaskRequest,
    SaveNoteRequest,
    UpdateNoteRequest
)
from .responses import (
    ChatResponse,
    EventResponse,
    EmailResponse,
    TaskResponse,
    NoteResponse,
    UserResponse
)

__all__ = [
    "ChatRequest",
    "CreateEventRequest", 
    "SendEmailRequest",
    "AddTaskRequest",
    "SaveNoteRequest",
    "UpdateNoteRequest",
    "ChatResponse",
    "EventResponse",
    "EmailResponse",
    "TaskResponse",
    "NoteResponse",
    "UserResponse",
]
