"""
Zenith AI - Main FastAPI Application
Personal Assistant with Google Workspace Integration
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import structlog

from config import settings
from auth.google_oauth import GoogleOAuthManager, get_oauth_manager
from auth.dependencies import (
    get_current_user, 
    require_auth, 
    create_access_token,
    check_rate_limit
)
from memory.user_store import UserStore
from memory.conversation import ConversationMemory
from agents.zenith_core import ZenithCore
from tools.calendar import CalendarTools
from tools.gmail import GmailTools
from tools.tasks import TasksTools
from tools.notes import NotesTools

from models.requests import (
    ChatRequest,
    CreateEventRequest,
    QuickAddEventRequest,
    SendEmailRequest,
    SearchEmailRequest,
    AddTaskRequest,
    SetReminderRequest,
    SaveNoteRequest,
    SearchNotesRequest,
    UpdateSettingsRequest
)
from models.responses import (
    ChatResponse,
    EventResponse,
    EventListResponse,
    EmailResponse,
    EmailListResponse,
    InboxSummaryResponse,
    TaskResponse,
    TaskListResponse,
    NoteResponse,
    NoteListResponse,
    UserResponse,
    SessionResponse,
    HealthResponse,
    AuthUrlResponse,
    TokenResponse,
    ErrorResponse
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting Zenith AI", version=settings.app_version)
    yield
    logger.info("Shutting down Zenith AI")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Elite Personal Assistant AI with Google Workspace Integration",
    version=settings.app_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Dependency instances
def get_user_store() -> UserStore:
    return UserStore()

def get_conversation_memory() -> ConversationMemory:
    return ConversationMemory()

def get_zenith_core() -> ZenithCore:
    return ZenithCore()


# ==================== Health & Info ====================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/", tags=["System"])
async def root():
    """Serve the main UI."""
    return FileResponse("static/index.html")


# ==================== Authentication ====================

@app.get("/auth/login", response_model=AuthUrlResponse, tags=["Authentication"])
async def login(
    oauth: GoogleOAuthManager = Depends(get_oauth_manager)
):
    """
    Get Google OAuth authorization URL.
    Redirect the user to this URL to begin authentication.
    """
    state = str(uuid4())
    authorization_url, state = oauth.create_authorization_url(state=state)
    
    return AuthUrlResponse(
        authorization_url=authorization_url,
        state=state
    )


@app.get("/auth/callback", tags=["Authentication"])
async def auth_callback(
    code: str,
    state: Optional[str] = None,
    oauth: GoogleOAuthManager = Depends(get_oauth_manager),
    user_store: UserStore = Depends(get_user_store)
):
    """
    OAuth callback endpoint.
    Exchange authorization code for tokens and redirect to frontend.
    """
    from fastapi.responses import RedirectResponse
    import urllib.parse
    import json
    
    try:
        # Exchange code for tokens (pass state for PKCE)
        result = await oauth.exchange_code_for_tokens(code, state=state)
        credentials = result["credentials"]
        user_info = result["user_info"]
        
        email = user_info.get("email")
        
        # Get or create user
        user, is_new = await user_store.get_or_create_user(
            email=email,
            google_user_info=user_info,
            credentials=credentials
        )
        
        # Create JWT token
        access_token = create_access_token(
            user_id=user["user_id"],
            email=email
        )
        
        logger.info("User authenticated", 
                   user_id=user["user_id"], 
                   email=email,
                   is_new_user=is_new)
        
        # Prepare user data for redirect
        user_data = {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user.get("name"),
            "picture": user.get("picture"),
            "settings": user.get("settings", {}),
        }
        
        # Redirect to frontend with auth data in URL fragment (not visible to server)
        # Using fragment (#) keeps tokens out of server logs
        auth_data = urllib.parse.urlencode({
            "access_token": access_token,
            "user": json.dumps(user_data),
            "is_new_user": str(is_new).lower()
        })
        
        return RedirectResponse(url=f"/?auth_success=true#{auth_data}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Authentication failed", error=error_msg)
        # Redirect to frontend with error
        encoded_error = urllib.parse.quote(error_msg)
        return RedirectResponse(url=f"/?auth_error={encoded_error}")


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Get current authenticated user info."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user.get("name"),
        picture=user.get("picture"),
        settings=user.get("settings", {}),
        created_at=user.get("created_at"),
        last_login=user.get("last_login")
    )


# ==================== Chat (Main Interface) ====================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(check_rate_limit),
    zenith: ZenithCore = Depends(get_zenith_core),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """
    Main chat endpoint - interact with Zenith AI.
    
    Send natural language messages and Zenith will:
    - Understand your intent
    - Execute appropriate actions (calendar, email, tasks, notes)
    - Respond in natural language
    """
    user_id = current_user["user_id"]
    
    # Get or create session
    session_id = request.session_id
    if not session_id:
        session_id = await memory.create_session(user_id)
    
    # Process message through Zenith
    result = await zenith.process_message(
        user_id=user_id,
        session_id=session_id,
        message=request.message
    )
    
    return ChatResponse(
        response=result.get("response", ""),
        session_id=session_id,
        suggestions=result.get("suggestions", []),
        intent=result.get("intent"),
        execution_success=result.get("execution_success"),
        error=result.get("error")
    )


@app.post("/chat/stream", tags=["Chat"])
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(check_rate_limit),
    zenith: ZenithCore = Depends(get_zenith_core),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """
    Streaming chat endpoint.
    Returns Server-Sent Events for real-time responses.
    """
    user_id = current_user["user_id"]
    
    session_id = request.session_id
    if not session_id:
        session_id = await memory.create_session(user_id)
    
    async def generate():
        async for chunk in zenith.process_message_stream(
            user_id=user_id,
            session_id=session_id,
            message=request.message
        ):
            import json
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# ==================== Calendar ====================

@app.get("/calendar/events", response_model=EventListResponse, tags=["Calendar"])
async def list_events(
    max_results: int = Query(default=10, ge=1, le=50),
    query: Optional[str] = None,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """List upcoming calendar events."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    calendar = CalendarTools()
    events = await calendar.list_events(
        credentials=credentials,
        max_results=max_results,
        query=query
    )
    
    return EventListResponse(
        events=[EventResponse(**e) for e in events],
        count=len(events)
    )


@app.post("/calendar/events", response_model=EventResponse, tags=["Calendar"])
async def create_event(
    request: CreateEventRequest,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Create a new calendar event."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    calendar = CalendarTools()
    event = await calendar.create_event(
        credentials=credentials,
        summary=request.summary,
        start_time=request.start_time,
        end_time=request.end_time,
        description=request.description,
        location=request.location,
        attendees=request.attendees,
        timezone=request.timezone,
        conference_data=request.add_google_meet
    )
    
    return EventResponse(**event)


@app.post("/calendar/quick-add", response_model=EventResponse, tags=["Calendar"])
async def quick_add_event(
    request: QuickAddEventRequest,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Quick-add an event using natural language."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    calendar = CalendarTools()
    event = await calendar.quick_add(
        credentials=credentials,
        text=request.text
    )
    
    return EventResponse(**event)


# ==================== Gmail ====================

@app.get("/gmail/messages", response_model=EmailListResponse, tags=["Gmail"])
async def search_emails(
    query: Optional[str] = None,
    max_results: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Search Gmail messages."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    gmail = GmailTools()
    messages = await gmail.search_messages(
        credentials=credentials,
        query=query,
        max_results=max_results
    )
    
    return EmailListResponse(
        emails=[EmailResponse(**m) for m in messages],
        count=len(messages)
    )


@app.get("/gmail/inbox/summary", response_model=InboxSummaryResponse, tags=["Gmail"])
async def summarize_inbox(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Get inbox summary for the past N hours."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    gmail = GmailTools()
    summary = await gmail.summarize_inbox(
        credentials=credentials,
        hours=hours
    )
    
    return InboxSummaryResponse(**summary)


@app.post("/gmail/send", tags=["Gmail"])
async def send_email(
    request: SendEmailRequest,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Send an email."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    gmail = GmailTools()
    result = await gmail.send_email(
        credentials=credentials,
        to=request.to,
        subject=request.subject,
        body=request.body,
        cc=request.cc,
        bcc=request.bcc,
        html_body=request.html_body,
        thread_id=request.reply_to_thread_id
    )
    
    return result


# ==================== Tasks ====================

@app.get("/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def list_tasks(
    show_completed: bool = False,
    task_list_id: str = "@default",
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """List tasks."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    tasks_tool = TasksTools()
    tasks = await tasks_tool.list_tasks(
        credentials=credentials,
        task_list_id=task_list_id,
        show_completed=show_completed
    )
    
    return TaskListResponse(
        tasks=[TaskResponse(**t) for t in tasks],
        count=len(tasks)
    )


@app.post("/tasks", response_model=TaskResponse, tags=["Tasks"])
async def add_task(
    request: AddTaskRequest,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Add a new task."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    tasks_tool = TasksTools()
    task = await tasks_tool.add_task(
        credentials=credentials,
        title=request.title,
        notes=request.notes,
        due_date=request.due_date,
        task_list_id=request.task_list_id
    )
    
    return TaskResponse(**task)


@app.post("/tasks/reminder", response_model=TaskResponse, tags=["Tasks"])
async def set_reminder(
    request: SetReminderRequest,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Set a reminder."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    tasks_tool = TasksTools()
    task = await tasks_tool.set_reminder(
        credentials=credentials,
        title=request.title,
        remind_at=request.remind_at,
        notes=request.notes
    )
    
    return TaskResponse(**task)


# ==================== Notes ====================

@app.get("/notes", response_model=NoteListResponse, tags=["Notes"])
async def list_notes(
    limit: int = Query(default=20, ge=1, le=100),
    source: Optional[str] = None,
    current_user: dict = Depends(require_auth)
):
    """List user's notes."""
    notes_tool = NotesTools()
    notes = await notes_tool.list_notes(
        user_id=current_user["user_id"],
        limit=limit,
        source=source
    )
    
    return NoteListResponse(
        notes=[NoteResponse(**n) for n in notes],
        count=len(notes)
    )


@app.post("/notes", response_model=NoteResponse, tags=["Notes"])
async def save_note(
    request: SaveNoteRequest,
    current_user: dict = Depends(require_auth)
):
    """Save a new note."""
    notes_tool = NotesTools()
    note = await notes_tool.save_note(
        user_id=current_user["user_id"],
        title=request.title,
        content=request.content,
        tags=request.tags,
        source=request.source
    )
    
    return NoteResponse(**note)


@app.post("/notes/search", response_model=NoteListResponse, tags=["Notes"])
async def search_notes(
    request: SearchNotesRequest,
    current_user: dict = Depends(require_auth)
):
    """Search notes in knowledge base."""
    notes_tool = NotesTools()
    notes = await notes_tool.query_knowledge_base(
        user_id=current_user["user_id"],
        query=request.query,
        limit=request.limit
    )
    
    return NoteListResponse(
        notes=[NoteResponse(**n) for n in notes],
        count=len(notes)
    )


# ==================== Sessions ====================

@app.get("/sessions", tags=["Sessions"])
async def list_sessions(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_auth),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """List user's conversation sessions."""
    sessions = await memory.get_user_sessions(
        user_id=current_user["user_id"],
        limit=limit
    )
    
    return {"sessions": sessions, "count": len(sessions)}


@app.post("/sessions", tags=["Sessions"])
async def create_session(
    current_user: dict = Depends(require_auth),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """Create a new conversation session."""
    session_id = await memory.create_session(
        user_id=current_user["user_id"]
    )
    
    return {"session_id": session_id}


# ==================== User Settings ====================

@app.patch("/settings", response_model=dict, tags=["Settings"])
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Update user settings."""
    updates = request.model_dump(exclude_none=True)
    
    settings = await user_store.update_settings(
        user_id=current_user["user_id"],
        settings_updates=updates
    )
    
    return {"settings": settings}


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": str(exc.status_code)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
