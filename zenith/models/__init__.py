"""Models module for Zenith AI - Pydantic models for API requests/responses."""
from .requests import (
    ChatRequest,
    CreateEventRequest,
    SendEmailRequest,
    AddTaskRequest,
    SaveNoteRequest
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
    "ChatResponse",
    "EventResponse",
    "EmailResponse",
    "TaskResponse",
    "NoteResponse",
    "UserResponse",
]
