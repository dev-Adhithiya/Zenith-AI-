# Zenith AI - Personal Assistant

> **Elite Personal Assistant AI with Google Workspace Integration**

A powerful, intelligent AI assistant that seamlessly integrates with your Google Workspace to manage emails, calendar events, tasks, and personal notes. Built with FastAPI, Vertex AI (Gemini 2.5 Flash), and Google Cloud Platform.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## ✨ Features

### 🤖 AI-Powered Conversational Interface
- **Natural Language Processing** with Google's Gemini 2.5 Flash
- **3-Phase Execution Pipeline**: Context gathering → Task decomposition → Response synthesis
- **Conversational Memory** with context awareness
- **Intent Classification** for smart action routing

### 📧 Google Workspace Integration
- **Gmail**: Search, read, send emails, inbox summaries
- **Google Calendar**: View events, create meetings, quick-add with natural language
- **Google Tasks**: Add tasks, set reminders, manage to-dos
- **Notes System**: Personal knowledge base with search capabilities

### 🎨 Modern Frontend
- Beautiful glassmorphism UI design
- Dark/Light theme support
- Responsive and mobile-friendly
- Real-time chat interface

### 🔐 Security & Authentication
- Google OAuth 2.0 authentication
- JWT-based session management
- Secure credential storage in Firestore
- Rate limiting and request validation

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Google Cloud Project** with APIs enabled:
  - Vertex AI API
  - Firestore API
  - Gmail API
  - Google Calendar API
  - Google Tasks API
- **OAuth 2.0 Credentials** from Google Cloud Console

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd AI-AGENT/zenith
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

   Required variables:
   ```env
   # GCP Configuration
   GCP_PROJECT_ID=your-project-id
   GCP_REGION=us-central1
   
   # OAuth 2.0
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   
   # Vertex AI
   VERTEX_AI_MODEL=gemini-2.5-flash
   VERTEX_AI_LOCATION=us-central1
   
   # JWT Secret (generate with: openssl rand -hex 32)
   JWT_SECRET_KEY=your-super-secret-jwt-key
   ```

5. **Setup Firestore Indexes** (Important!)
   
   See [`setup-firestore-indexes.md`](zenith/setup-firestore-indexes.md) for instructions.
   The quickest method is to click the auto-generated link when you first run the app.

6. **Run the application**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Open in browser**
   ```
   http://localhost:8000
   ```

---

## 📚 Documentation

- **[Integration Guide](INTEGRATION_GUIDE.md)** - Detailed setup and integration instructions
- **[Project Summary](PROJECT_SUMMARY.md)** - Architecture and technical overview
- **[Quick Start](QUICKSTART.md)** - Fast setup guide
- **[Setup Status Report](SETUP_STATUS_REPORT.md)** - Current configuration status

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

### Frontend
- Vanilla JavaScript with glassmorphism design
- WebSocket-ready for streaming responses
- Responsive layout with theme switching

---

## 🔧 Configuration

### Model Configuration
The system uses **Gemini 2.5 Flash** by default. To change models:

```python
# In .env file
VERTEX_AI_MODEL=gemini-2.5-flash  # or gemini-1.5-pro, etc.
```

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

### Notes System Not Working
**Error**: `400 The query requires an index`

**Solution**: Create the required Firestore composite index. See [`SETUP_STATUS_REPORT.md`](SETUP_STATUS_REPORT.md) for detailed instructions.

### Authentication Issues
1. Verify OAuth credentials in Google Cloud Console
2. Ensure redirect URI is correctly configured: `http://localhost:8000/auth/callback`
3. Check that required scopes are enabled

### Model Errors
1. Verify Vertex AI API is enabled in GCP
2. Check `VERTEX_AI_MODEL` is set to a valid model name
3. Ensure GCP credentials have proper permissions

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Cloud Platform** - Vertex AI, Firestore, OAuth
- **FastAPI** - High-performance web framework
- **Gemini 2.5 Flash** - Advanced language model
- **Pydantic** - Data validation and settings management

---

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Built with ❤️ using Google Cloud Platform and Gemini AI**
