# Zenith AI - Personal Assistant

> **Elite Personal Assistant AI with Google Workspace Integration**

A powerful, intelligent AI assistant that seamlessly integrates with your Google Workspace to manage emails, calendar events, tasks, and personal notes. Built with FastAPI, Vertex AI (Gemini), and Google Cloud Platform.

**🚀 [Quick Start Guide](STARTUP.md)** | **📚 [Integration Guide](INTEGRATION_GUIDE.md)** | **🏗️ [Architecture Overview](PROJECT_SUMMARY.md)**

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## ✨ Features

### 🤖 AI-Powered Conversational Interface
- **Natural Language Processing** with Google's Gemini (1.5 Pro / 2.0 Flash)
- **3-Phase Execution Pipeline**: Context gathering → Task decomposition → Response synthesis
- **Conversational Memory** with context awareness
- **Intent Classification** for smart action routing
- **Vertex AI Integration** for state-of-the-art language understanding

### 📧 Google Workspace Integration
- **Gmail**: Search, read, send emails, inbox summaries
- **Google Calendar**: View events, create meetings, quick-add with natural language
- **Google Tasks**: Add tasks, set reminders, manage to-dos
- **Notes System**: Personal knowledge base with search capabilities

### 🎨 Modern React Frontend
- Beautiful glassmorphism UI design with smooth animations
- Dark/Light theme support with persistent preferences
- Responsive and mobile-friendly layout
- Real-time chat interface with typing indicators
- Voice input support for hands-free interaction
- Session history and conversation management

### 🔐 Security & Authentication
- Google OAuth 2.0 authentication
- JWT-based session management
- Secure credential storage in Firestore
- Rate limiting and request validation

---

## 🚀 Quick Start

**⚡ For detailed startup instructions, see [STARTUP.md](STARTUP.md)**

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- **Google Cloud Project** with APIs enabled:
  - ✅ Vertex AI API (Required for AI chat)
  - ✅ Cloud Resource Manager API (Required for billing)
  - ✅ Firestore API
  - ✅ Gmail API
  - ✅ Google Calendar API
  - ✅ Google Tasks API
- **OAuth 2.0 Credentials** from Google Cloud Console
- **Billing Enabled** in GCP (Required for Vertex AI)
- **Vertex AI Model Quota** approved (100+ requests/minute recommended)

### Quick Installation

```bash
# 1. Navigate to project
cd "f:\projec main final\AI AGENT\zenith"

# 2. Backend setup
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# 3. Frontend setup
cd frontend
npm install
cd ..

# 4. Configure .env file
cp .env.example .env
# Edit .env with your GCP credentials
```

### Required `.env` Configuration

```env
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1

# OAuth 2.0
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Vertex AI (CRITICAL - Must match enabled models)
VERTEX_AI_MODEL=gemini-1.5-pro
VERTEX_AI_LOCATION=us-central1

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-super-secret-jwt-key
```

### Starting the Application

**Terminal 1 - Backend:**
```bash
cd zenith
.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd zenith/frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

📘 **For complete startup instructions, troubleshooting, and verification checklist, see [STARTUP.md](STARTUP.md)**

---

## 📚 Documentation

- **[🚀 Startup Guide](STARTUP.md)** - Complete startup instructions and troubleshooting
- **[📖 Integration Guide](INTEGRATION_GUIDE.md)** - Detailed setup and integration instructions
- **[🏗️ Project Summary](PROJECT_SUMMARY.md)** - Architecture and technical overview
- **[⚡ Quick Start](QUICKSTART.md)** - Fast setup guide
- **[📊 Setup Status Report](SETUP_STATUS_REPORT.md)** - Current configuration status
- **[🔧 Firestore Setup](zenith/setup-firestore-indexes.md)** - Database index configuration

---

## 🏗️ Architecture

### Backend (FastAPI)
```
zenith/
├── agents/           # AI agents (context, decomposer, synthesizer)
├── auth/             # Google OAuth & JWT authentication
├── memory/           # Firestore client, conversation memory, user store
├── models/           # Pydantic request/response models
├── tools/            # Google API integrations (Gmail, Calendar, Tasks, Notes)
├── static/           # Frontend assets
├── config.py         # Configuration management
└── main.py          # FastAPI application entry point
```

### AI Pipeline
1. **Context Agent** - Resolves context from chat history and knowledge base
2. **Decomposer Agent** - Breaks requests into executable steps
3. **Synthesizer Agent** - Generates natural language responses

### Frontend (React + TypeScript)
```
zenith/frontend/
├── src/
│   ├── components/       # React components (Chat, Sidebar, Notes, etc.)
│   ├── contexts/         # React contexts (Auth, Chat, Voice, Theme)
│   ├── styles/           # Global styles and themes
│   ├── utils/            # Utility functions and API client
│   ├── App.tsx          # Main React application
│   └── main.tsx         # Entry point
└── package.json         # npm dependencies
```

- React 18 with TypeScript for type safety
- Glassmorphism design with smooth animations
- Context-based state management
- Responsive layout with theme switching
- Voice input support with Web Speech API

---

## 🔧 Configuration

### Model Configuration
The system supports multiple Gemini models via Vertex AI:

```env
# In .env file
VERTEX_AI_MODEL=gemini-1.5-pro          # Recommended (most stable)
# VERTEX_AI_MODEL=gemini-2.0-flash      # Alternative (faster, newer)

VERTEX_AI_LOCATION=us-central1          # Recommended (best availability)
```

**Supported Models:**
- `gemini-1.5-pro` - Most stable, production-ready
- `gemini-2.0-flash` - Newer, faster, experimental
- `gemini-1.5-flash` - Lightweight, fast responses

**Important:** Model must be available in your selected region and approved for quota.

### Firestore Collections
- `users` - User profiles and OAuth credentials
- `conversations` - Chat session metadata
- `notes` - Personal knowledge base entries

---

## 🎯 API Endpoints

### Authentication
- `GET /auth/login` - Get Google OAuth URL
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/me` - Get current user info

### Chat
- `POST /chat` - Send message (non-streaming)
- `POST /chat/stream` - Send message (streaming)

### Calendar
- `GET /calendar/events` - List upcoming events
- `POST /calendar/events` - Create new event
- `POST /calendar/quick-add` - Quick add with natural language

### Gmail
- `GET /gmail/messages` - Search messages
- `GET /gmail/inbox/summary` - Get inbox summary
- `POST /gmail/send` - Send email

### Tasks
- `GET /tasks` - List tasks
- `POST /tasks` - Add new task
- `POST /tasks/reminder` - Set reminder

### Notes
- `GET /notes` - List notes
- `POST /notes` - Save note
- `POST /notes/search` - Search knowledge base

---

## 🐛 Troubleshooting

### "Response candidate has no content parts" Error
**Error**: `Response candidate has no content parts. Finish reason: 2`

**Causes:**
1. Vertex AI API not enabled in GCP
2. Model quota not approved
3. Wrong model name or location
4. Billing not enabled

**Solution:**
1. Go to GCP Console → APIs & Services → Library
2. Search for "Vertex AI API" and enable it
3. Enable "Cloud Resource Manager API"
4. Go to IAM & Admin → Quotas → Request quota for `generative_ai`
5. Verify billing is enabled
6. Check `.env` has correct model: `gemini-1.5-pro`
7. Check location: `us-central1`
8. Restart backend server

**📘 For complete troubleshooting guide, see [STARTUP.md](STARTUP.md#troubleshooting)**

### Notes System Not Working
**Error**: `400 The query requires an index`

**Solution**: Click the error link to create Firestore index automatically, or see [`zenith/setup-firestore-indexes.md`](zenith/setup-firestore-indexes.md)

### Authentication Issues
1. Verify OAuth credentials in Google Cloud Console
2. Ensure redirect URI: `http://localhost:8000/auth/callback`
3. Check required scopes are enabled
4. Verify `.env` has correct CLIENT_ID and CLIENT_SECRET

### Frontend Not Loading
1. Ensure frontend dev server is running (`npm run dev` in `zenith/frontend/`)
2. Check terminal output for the correct port (default: 3000)
3. Verify npm dependencies installed (`npm install`)
4. Check browser console (F12) for errors

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Cloud Platform** - Vertex AI, Firestore, OAuth
- **FastAPI** - High-performance Python web framework
- **Gemini AI Models** - Advanced language understanding (1.5 Pro / 2.0 Flash)
- **React** - Modern UI library
- **Vite** - Fast frontend build tool
- **Pydantic** - Data validation and settings management

---

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Built with ❤️ using Google Cloud Platform and Gemini AI**
