"""
Zenith AI - Main FastAPI Application
Personal Assistant with Google Workspace Integration
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, Query, Form, File, UploadFile
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
    UpdateNoteRequest,
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
    ErrorResponse,
    BriefingResponse
)

# LOGIN BRIEFING PROMPT
LOGIN_BRIEFING_PROMPT = """You are Zenith AI, a proactive Chief of Staff. The user has just logged into their workspace.
Your task is to generate a 'Daily Catch-Up' briefing with a clear, organized structure.

IMPORTANT: Use this exact format with emojis and proper section breaks:

✅ TASKS
  • [Task 1]
  • [Task 2]
  • [etc.]

📅 CALENDAR
  • [Time]: [Event name]
  • [Time]: [Event name]
  • [etc.]

📧 EMAILS
[Just provide a brief summary of email status. For example: "You have 10 unread emails. Important: 1 job offer from LinkedIn, 2 security alerts from Google." Only mention if anything important/urgent is present, otherwise just state the count]

Guidelines:
- Use emojis as shown above (✅ for tasks, 📅 for calendar, 📧 for emails)
- Each section has its own line with emoji and title
- Task and Calendar items as bullet points under each section
- Email section: Just a summary, no bullet point listing
- Keep it clear and scannable
- NO markdown formatting (no **, __, ##)
- NO questions, NO follow-up suggestions. Just facts.
- Keep total under 200 words
- If any urgent/important items, mention them first"""

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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://zenith-156148005661.asia-south1.run.app",
        "https://dev-Adhithiya.github.io",
        "https://dev-Adhithiya.github.io/Zenith-AI-"
    ],
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


@app.get("/debug/test", tags=["System"])
async def debug_test():
    """Simple test endpoint to verify backend is working."""
    return {
        "status": "ok",
        "message": "Backend is working",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/", tags=["System"])
async def root():
    """Serve the frontend application."""
    static_dir = Path("static")
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    # Fallback if index.html doesn't exist during development
    return {"message": "Zenith AI - Backend API Server (Frontend: build frontend or visit http://localhost:3000)"}


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
        
        # Redirect to frontend (port 3000 in development)
        frontend_url = "http://localhost:3000"
        return RedirectResponse(url=f"{frontend_url}/?auth_success=true#{auth_data}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Authentication failed", error=error_msg)
        # Redirect to frontend with error
        frontend_url = "http://localhost:3000"
        encoded_error = urllib.parse.quote(error_msg)
        return RedirectResponse(url=f"{frontend_url}/?auth_error={encoded_error}")


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

# Keep this for backward compatibility with JSON requests
@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    images: list[UploadFile] = File(default=[]),
    current_user: dict = Depends(check_rate_limit),
    zenith: ZenithCore = Depends(get_zenith_core),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """
    Main chat endpoint - interact with Zenith AI.
    Supports both FormData with optional file uploads.
    
    Send natural language messages and Zenith will:
    - Understand your intent
    - Execute appropriate actions (calendar, email, tasks, notes)
    - Respond in natural language
    - Process attached images if provided
    """
    try:
        user_id = current_user["user_id"]
        
        if not message or not message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required"
            )
        
        # Get or create session
        if not session_id:
            session_id = await memory.create_session(user_id)
        
        # Process images if provided
        image_data = []
        if images:
            for image_file in images:
                try:
                    # Validate file type
                    if not image_file.content_type.startswith('image/'):
                        logger.warning(f"Non-image file rejected: {image_file.filename}")
                        continue
                    
                    # Read file content
                    content = await image_file.read()
                    
                    # Validate size (max 5MB)
                    if len(content) > 5 * 1024 * 1024:
                        logger.warning(f"Image too large: {image_file.filename}")
                        continue
                    
                    image_data.append({
                        'filename': image_file.filename,
                        'content_type': image_file.content_type,
                        'content': content
                    })
                except Exception as e:
                    logger.error(f"Failed to process image: {image_file.filename}", error=str(e))
                    continue
        
        # Build context message with image count
        context_message = message
        if image_data:
            context_message = f"[User attached {len(image_data)} image(s)]\n{message}"
        
        # Process message through Zenith
        result = await zenith.process_message(
            user_id=user_id,
            session_id=session_id,
            message=context_message,
            images=image_data
        )
        
        return ChatResponse(
            response=result.get("response", ""),
            session_id=session_id,
            suggestions=result.get("suggestions", []),
            intent=result.get("intent"),
            execution_success=result.get("execution_success"),
            error=result.get("error"),
            requires_confirmation=result.get("requires_confirmation"),
            pending_plan=result.get("pending_plan")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat endpoint error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
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


# ==================== Agent Briefing ====================

@app.get("/agent/briefing", response_model=BriefingResponse, tags=["Agent"])
async def get_login_briefing(
    current_user: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
    zenith: ZenithCore = Depends(get_zenith_core),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """
    Daily Executive Summary with AI Processing.
    
    Fetches real data and generates AI-powered summary:
    - Tasks: All pending tasks (not completed)  
    - Events: Today's calendar events (00:00 - 23:59)
    - Emails: Unread emails from last 24 hours
    
    Returns:
        BriefingResponse with AI-generated summary
    """
    user_id = current_user["user_id"]
    
    try:
        # Get user and credentials from store
        user = await user_store.get_user_by_id(user_id)
        credentials = user.get("credentials") if user else None
        
        if not credentials:
            return BriefingResponse(
                status="error",
                title="Your Executive Summary",
                content="Please re-authenticate to see your briefing.",
                error="no_credentials"
            )
        
        # Get today's date range (00:00 - 23:59)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # FETCH REAL DATA
        
        # 1. Fetch ALL PENDING TASKS (not completed)
        try:
            pending_tasks = await zenith.tasks.list_tasks(
                credentials=credentials,
                show_completed=False,
                max_results=50
            )
        except Exception as e:
            logger.warning("Tasks fetch failed", error=str(e))
            pending_tasks = []
        
        # 2. Fetch TODAY'S CALENDAR EVENTS (00:00 - 23:59)
        try:
            calendar_events = await zenith.calendar.list_events(
                credentials=credentials,
                time_min=today_start,
                time_max=today_end,
                max_results=50
            )
        except Exception as e:
            logger.warning("Calendar fetch failed", error=str(e))
            calendar_events = []
        
        # 3. Fetch UNREAD EMAILS from last 24 hours
        try:
            last_24h_date = last_24h.strftime("%Y/%m/%d")
            unread_emails = await zenith.gmail.search_messages(
                credentials=credentials,
                query=f"is:unread after:{last_24h_date}",
                max_results=20
            )
        except Exception as e:
            logger.warning("Email fetch failed", error=str(e))
            unread_emails = []
        
        # Build execution results with actual data for synthesis
        execution_results = {
            "success": True,
            "step_results": [
                {
                    "action": "tasks.list",
                    "success": True,
                    "data": {
                        "count": len(pending_tasks),
                        "tasks": pending_tasks
                    }
                },
                {
                    "action": "calendar.list_events",
                    "success": True,
                    "data": {
                        "count": len(calendar_events),
                        "events": calendar_events
                    }
                },
                {
                    "action": "gmail.search_unread",
                    "success": True,
                    "data": {
                        "count": len(unread_emails),
                        "emails": unread_emails
                    }
                }
            ]
        }
        
        # Build context for synthesis
        context = {
            "original_message": "Generate executive briefing summary",
            "resolved_message": "Generate executive briefing summary with actual fetched data",
            "chat_history": [],
            "intent": {"category": "B", "intent": "briefing"}
        }
        
        # Format the data for the prompt
        tasks_text = "\n".join([f"- {t.get('title', '(No title)')}" for t in pending_tasks[:10]]) if pending_tasks else "No pending tasks"
        events_text = "\n".join([f"- {e.get('start', '')}: {e.get('summary', '(No title)')}" for e in calendar_events[:10]]) if calendar_events else "No events today"
        emails_text = "\n".join([f"- {e.get('subject', '(No subject)')} from {e.get('from', 'Unknown')}" for e in unread_emails[:10]]) if unread_emails else "No unread emails"
        
        # Create detailed briefing prompt with data
        detailed_prompt = f"""{LOGIN_BRIEFING_PROMPT}

Here is today's data:

TASKS ({len(pending_tasks)} pending):
{tasks_text}

CALENDAR EVENTS ({len(calendar_events)} events):
{events_text}

UNREAD EMAILS ({len(unread_emails)} emails):
{emails_text}

Generate a brief, natural summary of this information for the user."""
        
        # Use synthesizer with custom prompt
        briefing_content = await zenith.synthesizer.synthesize(
            context=context,
            execution_results=execution_results,
            custom_prompt=detailed_prompt
        )
        
        # Clean up any markdown formatting (**, __, ##, etc.)
        briefing_content = (briefing_content
            .replace('**', '')
            .replace('__', '')
            .replace('##', '')
            .replace('- ', '• ')
        )
        
        return BriefingResponse(
            status="success",
            title="Your Executive Summary",
            content=briefing_content,
            error=None,
            metadata={
                "task_count": len(pending_tasks),
                "event_count": len(calendar_events),
                "unread_count": len(unread_emails),
                "last_updated": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error("Failed to generate briefing", 
                    user_id=user_id, 
                    error=str(e))
        
        # Graceful degradation
        return BriefingResponse(
            status="error",
            title="Your Executive Summary",
            content="Welcome back! I'm here to help you with your calendar, emails, and tasks.",
            error=str(e)
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

@app.get("/gmail/messages/{message_id}", response_model=EmailResponse, tags=["Gmail"])
async def get_email(
    message_id: str,
    format: str = Query(default="full"),
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Get a specific Gmail message."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")

    gmail = GmailTools()
    message = await gmail.get_message(
        credentials=credentials,
        message_id=message_id,
        format=format
    )

    return EmailResponse(**message)


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


@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse, tags=["Tasks"])
async def complete_task(
    task_id: str,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Mark a task as completed."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    tasks_tool = TasksTools()
    task = await tasks_tool.complete_task(
        credentials=credentials,
        task_id=task_id
    )
    
    return TaskResponse(**task)


@app.patch("/tasks/{task_id}/uncomplete", response_model=TaskResponse, tags=["Tasks"])
async def uncomplete_task(
    task_id: str,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Mark a task as not completed."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    tasks_tool = TasksTools()
    task = await tasks_tool.uncomplete_task(
        credentials=credentials,
        task_id=task_id
    )
    
    return TaskResponse(**task)


# ==================== Notes ====================

@app.get("/notes", response_model=NoteListResponse, tags=["Notes"])
async def list_notes(
    limit: int = Query(default=20, ge=1, le=100),
    source: Optional[str] = None,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """List user's notes."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
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
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Save a new note and optionally sync to Google Drive."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    notes_tool = NotesTools()
    note = await notes_tool.save_note(
        user_id=current_user["user_id"],
        title=request.title,
        content=request.content,
        tags=request.tags,
        source=request.source,
        credentials=credentials
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


@app.put("/notes/{note_id}", response_model=NoteResponse, tags=["Notes"])
async def update_note(
    note_id: str,
    request: UpdateNoteRequest,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Update an existing note and sync changes to Google Drive."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    notes_tool = NotesTools()
    note = await notes_tool.update_note(
        user_id=current_user["user_id"],
        note_id=note_id,
        title=request.title,
        content=request.content,
        tags=request.tags,
        credentials=credentials
    )
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return NoteResponse(**note)


@app.delete("/notes/{note_id}", tags=["Notes"])
async def delete_note(
    note_id: str,
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Delete a note from both Firestore and Google Drive."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    notes_tool = NotesTools()
    success = await notes_tool.delete_note(
        user_id=current_user["user_id"],
        note_id=note_id,
        credentials=credentials
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return {"message": "Note deleted successfully"}


@app.post("/notes/import-from-drive", tags=["Notes"])
async def import_notes_from_drive(
    current_user: dict = Depends(require_auth),
    user_store: UserStore = Depends(get_user_store)
):
    """Import all notes from Google Drive's Zenith Notes folder."""
    user = await user_store.get_user_by_id(current_user["user_id"])
    credentials = user.get("credentials")
    
    if not credentials:
        raise HTTPException(status_code=400, detail="Google Drive credentials not available")
    
    notes_tool = NotesTools()
    result = await notes_tool.import_notes_from_drive(
        user_id=current_user["user_id"],
        credentials=credentials
    )
    
    return result


@app.get("/notes/{note_id}/sync-status", tags=["Notes"])
async def get_note_sync_status(
    note_id: str,
    current_user: dict = Depends(require_auth)
):
    """Get Google Drive sync status for a note."""
    notes_tool = NotesTools()
    status = await notes_tool.get_sync_status(
        user_id=current_user["user_id"],
        note_id=note_id
    )
    
    if not status:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return status


# ==================== Sessions ====================

@app.get("/sessions", tags=["Sessions"])
async def list_sessions(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(require_auth),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """List user's conversation sessions."""
    try:
        sessions = await memory.get_user_sessions(
            user_id=current_user["user_id"],
            limit=limit
        )
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        # Handle Firestore index not ready error gracefully
        error_msg = str(e)
        if "index" in error_msg.lower():
            logger.warning(f"Firestore index not ready for sessions: {e}")
            return {"sessions": [], "count": 0, "error": "Index building - chat history will be available soon"}
        logger.error(f"Failed to list sessions: {e}")
        return {"sessions": [], "count": 0, "error": str(e)}


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


@app.get("/chat/sessions/{session_id}", tags=["Sessions"])
async def get_session_messages(
    session_id: str,
    current_user: dict = Depends(require_auth),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """Get messages for a specific session."""
    messages = await memory.get_context_window(
        user_id=current_user["user_id"],
        session_id=session_id,
        max_messages=100
    )
    
    return {
        "session_id": session_id,
        "messages": messages,
        "count": len(messages)
    }

@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session(
    session_id: str,
    current_user: dict = Depends(require_auth),
    memory: ConversationMemory = Depends(get_conversation_memory)
):
    """Delete a specific chat session."""
    try:
        success = await memory.delete_session(
            user_id=current_user["user_id"],
            session_id=session_id
        )
        if not success:
             raise HTTPException(status_code=404, detail="Session not found")
        return {"result": "success", "message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete session")


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
