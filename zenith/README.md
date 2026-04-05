# Zenith AI - Personal Assistant

Elite, highly intelligent Personal Assistant AI with Google Workspace integration. Built on Google Cloud Platform with Vertex AI.

## Features

- 🗓️ **Google Calendar** - List, create, schedule, and manage events
- 📧 **Gmail** - Search, read, summarize inbox, send emails
- ✅ **Google Tasks** - Add, list, complete tasks, set reminders
- 📝 **Notes** - Save, search, and query personal knowledge base
- 🤖 **Natural Language** - Chat naturally, Zenith understands intent
- 🔄 **Context Memory** - Remembers conversation for follow-up questions
- 👥 **Multi-tenant** - Supports multiple users with isolated data

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     ZENITH AI CORE                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Context     │  │ Decomposer  │  │ Synthesizer         │  │
│  │ Agent       │→ │ Agent       │→ │ Agent               │  │
│  │ (Phase 1)   │  │ (Phase 2)   │  │ (Phase 3)           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         ↓                ↓                   ↓              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Vertex AI (Gemini 1.5 Pro)               │   │
│  └──────────────────────────────────────────────────────┘   │
│         ↓                ↓                   ↓              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Calendar    │  │ Gmail       │  │ Tasks    │  Notes   │  │
│  │ Tools       │  │ Tools       │  │ Tools    │  Tools   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Firestore (User Data & Memory)              │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

1. **GCP Account** with billing enabled
2. **GCP Project** with these APIs enabled:
   - Calendar API
   - Gmail API
   - Tasks API
   - Cloud Firestore API
   - Vertex AI API
   - Cloud Run Admin API
3. **OAuth 2.0 Credentials** (Web application type)

### Local Development

1. **Clone and setup:**
   ```bash
   cd zenith
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows
   # source .venv/bin/activate   # Linux/Mac
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your GCP project ID and OAuth credentials
   ```

3. **Run locally:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. **Test:**
   - Open http://localhost:8000/docs for Swagger UI
   - Start with `/auth/login` to authenticate

### Deploy to Cloud Run

1. **Setup secrets:**
   ```powershell
   cd infrastructure
   .\setup-secrets.ps1 -ProjectId "your-project-id" `
       -GoogleClientId "your-client-id" `
       -GoogleClientSecret "your-client-secret"
   ```

2. **Deploy:**
   ```powershell
   $env:GCP_PROJECT_ID = "your-project-id"
   .\deploy.ps1
   ```

3. **Update OAuth redirect URI** in GCP Console to include Cloud Run URL

## API Endpoints

### Chat (Main Interface)
- `POST /chat` - Chat with Zenith AI
- `POST /chat/stream` - Streaming chat (SSE)

### Authentication
- `GET /auth/login` - Get OAuth login URL
- `GET /auth/callback` - OAuth callback
- `GET /auth/me` - Get current user

### Calendar
- `GET /calendar/events` - List events
- `POST /calendar/events` - Create event
- `POST /calendar/quick-add` - Quick add (natural language)

### Gmail
- `GET /gmail/messages` - Search messages
- `GET /gmail/inbox/summary` - Inbox summary
- `POST /gmail/send` - Send email

### Tasks
- `GET /tasks` - List tasks
- `POST /tasks` - Add task
- `POST /tasks/reminder` - Set reminder

### Notes
- `GET /notes` - List notes
- `POST /notes` - Save note
- `POST /notes/search` - Search knowledge base

## Example Usage

### Chat Naturally
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Do I have any meetings tomorrow?"}'
```

### Create a Meeting
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule a meeting with john@example.com tomorrow at 3pm for 1 hour to discuss the project"}'
```

### Check Email
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize my inbox from the last 24 hours"}'
```

## Project Structure

```
zenith/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration & environment variables
├── requirements.txt        # Python dependencies
├── Dockerfile              # Cloud Run container
├── .env.example            # Environment template
│
├── auth/
│   ├── google_oauth.py     # Google OAuth 2.0 flow
│   └── dependencies.py     # Auth middleware & JWT
│
├── tools/
│   ├── calendar.py         # Google Calendar API
│   ├── gmail.py            # Gmail API
│   ├── tasks.py            # Google Tasks API
│   └── notes.py            # Firestore notes system
│
├── agents/
│   ├── vertex_ai.py        # Vertex AI LLM client
│   ├── context_agent.py    # Phase 1: Context gathering
│   ├── decomposer.py       # Phase 2: Task decomposition
│   ├── synthesizer.py      # Phase 3: Response synthesis
│   └── zenith_core.py      # Main orchestrator
│
├── memory/
│   ├── firestore_client.py # Firestore wrapper
│   ├── conversation.py     # Chat history management
│   └── user_store.py       # User data management
│
└── models/
    ├── requests.py         # API request models
    └── responses.py        # API response models
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GCP_PROJECT_ID` | GCP Project ID | Yes |
| `GOOGLE_CLIENT_ID` | OAuth Client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | OAuth Client Secret | Yes |
| `JWT_SECRET_KEY` | Secret for JWT tokens | Yes |
| `GCP_REGION` | GCP Region (default: us-central1) | No |
| `VERTEX_AI_MODEL` | Vertex AI model (default: gemini-2.5-flash) | No |
| `DEBUG` | Debug mode (default: false) | No |

## License

MIT
