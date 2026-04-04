# Zenith AI - Complete Integration Guide

## 🎯 Overview

Zenith AI is a complete personal assistant system. Here's how to connect it to your project:

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR PROJECT                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: Configure GCP ───→ Step 2: Setup Environment      │
│          Credentials              Variables                  │
│              ↓                        ↓                      │
│  Step 3: Install Dependencies ─→ Step 4: Run Locally        │
│              ↓                        ↓                      │
│  Step 5: Test APIs ────────────→ Step 6: Deploy to Cloud    │
│              ↓                        ↓                      │
│                    ✨ Live Application ✨                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites Checklist

Before starting, verify you have completed:

- ✅ **GCP Project Created** with billing enabled
- ✅ **APIs Enabled:**
  - Google Calendar API
  - Gmail API
  - Google Tasks API
  - Cloud Firestore API
  - Vertex AI API
  - Cloud Run Admin API
- ✅ **OAuth 2.0 Credentials** downloaded as JSON
- ✅ **Firestore Database** created in Native mode
- ✅ **Project ID** and **Region** noted

---

## 🔧 Step 1: Configure GCP Credentials

### 1.1 Locate Your OAuth Credentials

From GCP Console:
1. Go to **APIs & Services** → **Credentials**
2. Find your OAuth 2.0 Client ID (Web application)
3. Download the JSON file (or copy the values)

You'll need:
- `client_id` (looks like: `xxx.apps.googleusercontent.com`)
- `client_secret` (long random string)

### 1.2 Get Your Project ID & Region

```powershell
# In GCP Cloud Shell or local gcloud:
gcloud config list
# Look for "project" value

# Or find it in GCP Console:
# Dashboard → Project Info → Project ID
```

---

## 💾 Step 2: Setup Environment Variables

### 2.1 Create `.env` File

```powershell
cd "f:\projec main final\AI AGENT\zenith"
Copy-Item .env.example .env
```

### 2.2 Edit `.env` with Your Values

Open `f:\projec main final\AI AGENT\zenith\.env` in a text editor and fill in:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-actual-project-id
GCP_REGION=us-central1

# OAuth 2.0 Credentials (from OAuth JSON)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here

# OAuth Redirect URI (for local testing)
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# Optional
VERTEX_AI_MODEL=gemini-1.5-pro-001
VERTEX_AI_LOCATION=us-central1
DEBUG=true
```

**How to generate JWT_SECRET_KEY:**
```powershell
# Option 1: Use Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Use OpenSSL (if installed)
openssl rand -hex 32

# Option 3: Just create a random string (32+ characters)
```

---

## 📦 Step 3: Install Dependencies

### 3.1 Create Virtual Environment

```powershell
cd "f:\projec main final\AI AGENT\zenith"

# Create venv
python -m venv .venv

# Activate venv
.\.venv\Scripts\Activate.ps1

# On Windows, if you get execution policy error:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3.2 Install Packages

```powershell
# Make sure .venv is activated
pip install --upgrade pip
pip install -r requirements.txt

# This will install:
# - FastAPI, Uvicorn
# - Google Cloud SDK
# - Vertex AI SDK
# - Auth libraries
# - And all dependencies
```

---

## 🏃 Step 4: Run Locally

### 4.1 Start the Server

```powershell
# From zenith/ directory with .venv activated
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
Uvicorn running on http://0.0.0.0:8000
Press CTRL+C to quit
```

### 4.2 Open in Browser

```
http://localhost:8000
```

You should see:
- 🎨 Beautiful glassmorphism UI
- ☀️ Light/Dark mode toggle (top-right)
- 📝 Chat interface
- 🔐 "Sign in with Google" button

---

## 🔑 Step 5: Test Authentication

### 5.1 Sign In

1. Click **"Sign in with Google"** button
2. You'll be redirected to Google login
3. Authenticate with your Google account
4. You'll be redirected back to the app with a token

### 5.2 Test Chat

Try these messages:
- "Show me my schedule for today"
- "What's in my inbox?"
- "Create a reminder for tomorrow at 3pm"
- "Save a note about this meeting"

### 5.3 Check Browser Console

Press `F12` → **Console** tab to see:
- API responses
- Authentication token
- Session ID
- Any errors

---

## 🧪 Step 6: Test APIs Directly

### 6.1 Get Health Check

```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-04-04T10:39:06.574Z"
}
```

### 6.2 View API Documentation

Open: `http://localhost:8000/docs`

This shows all API endpoints with:
- Request/response schemas
- Test buttons
- Authentication

### 6.3 Test Endpoints

#### Get OAuth URL
```powershell
curl http://localhost:8000/auth/login
```

#### Chat (requires token from login)
```powershell
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me my schedule"}'
```

---

## 🚀 Step 7: Deploy to Cloud Run

### 7.1 Create Secrets in Secret Manager

```powershell
cd "f:\projec main final\AI AGENT\infrastructure"

# Set your project
$env:GCP_PROJECT_ID = "your-project-id"

# Run setup script
.\setup-secrets.ps1 -ProjectId $env:GCP_PROJECT_ID `
    -GoogleClientId "your-client-id" `
    -GoogleClientSecret "your-client-secret"
```

This creates secrets in GCP Secret Manager.

### 7.2 Deploy to Cloud Run

```powershell
# From infrastructure directory
.\deploy.ps1

# Or manually:
gcloud builds submit --tag gcr.io/$env:GCP_PROJECT_ID/zenith-ai
gcloud run deploy zenith-ai --image gcr.io/$env:GCP_PROJECT_ID/zenith-ai --region us-central1
```

### 7.3 Update OAuth Redirect URI

After deployment, you'll get a Cloud Run URL. Update it in GCP Console:

1. Go to **APIs & Services** → **Credentials**
2. Edit the OAuth 2.0 Client ID
3. Add to **Authorized redirect URIs:**
   ```
   https://zenith-ai-xyz.run.app/auth/callback
   ```

### 7.4 Test Cloud Run Deployment

```powershell
# Get the service URL
$ServiceUrl = gcloud run services describe zenith-ai --region us-central1 --format 'value(status.url)'

# Test health
curl "$ServiceUrl/health"

# Open in browser
Start-Process "$ServiceUrl"
```

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    BROWSER (UI)                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │   Glassmorphism UI (Dark/Light Mode)                  │ │
│  │   - Chat Interface                                     │ │
│  │   - Sidebar Navigation                                │ │
│  │   - Suggestion Cards                                  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTPS / WebSocket
                   ↓
┌─────────────────────────────────────────────────────────────┐
│            CLOUD RUN (FastAPI Server)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Routes                                      │  │
│  │  - /chat                                             │  │
│  │  - /auth/login, /auth/callback                       │  │
│  │  - /calendar/events                                  │  │
│  │  - /gmail/messages                                   │  │
│  │  - /tasks                                            │  │
│  │  - /notes                                            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Agents (Vertex AI)                                  │  │
│  │  - Context Agent (understand intent)                 │  │
│  │  - Decomposer (break into steps)                     │  │
│  │  - Synthesizer (natural response)                    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Google APIs                                         │  │
│  │  - Calendar, Gmail, Tasks                            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────┬──────────┬──────────┬───────────┬────────────────┘
           │          │          │           │
           ↓          ↓          ↓           ↓
        Vertex AI   Firestore  Secret Mgr  Google APIs
        (LLM)       (Database) (Creds)     (Calendar, Gmail)
```

---

## 🔗 Integration Points

### Connect to Your Existing Project

#### Option 1: As a Microservice
```yaml
# docker-compose.yml
services:
  zenith-ai:
    image: gcr.io/your-project/zenith-ai
    ports:
      - "8000:8000"
    environment:
      GCP_PROJECT_ID: your-project
      GOOGLE_CLIENT_ID: ...
    depends_on:
      - firestore
```

#### Option 2: As an API
Call from your app:
```javascript
// From your app
const response = await fetch('http://zenith-ai:8000/chat', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ message: 'Your message' })
});
```

#### Option 3: Embed in Your App
Use the `APIClient` class:
```javascript
const api = new APIClient('http://zenith-ai:8000', token);
const response = await api.chat('Your message');
```

---

## 🛠️ Common Tasks

### Change Appearance
Edit `zenith/static/css/styles.css`:
```css
:root {
  --accent-primary: #your-brand-color;
  --glass-bg: rgba(255, 255, 255, 0.7);
}
```

### Add Custom Endpoints
Edit `zenith/main.py`:
```python
@app.post("/custom-endpoint", tags=["Custom"])
async def custom_endpoint(request: YourModel):
    # Your logic here
    return {"result": "data"}
```

### Customize Chat Behavior
Edit `zenith/agents/zenith_core.py`:
```python
# Modify the 3-phase pipeline
async def process_message(self, ...):
    # Phase 1: Context
    # Phase 2: Decompose
    # Phase 3: Synthesize
```

### Connect Different Database
Replace Firestore in `zenith/memory/user_store.py`:
```python
# Change from Firestore to your DB
# PostgreSQL, MongoDB, etc.
```

---

## 🧠 How Zenith Works

### The Chat Flow

```
1. User enters message
   ↓
2. Context Agent
   - Resolves pronouns
   - Extracts entities
   - Queries knowledge base
   ↓
3. Decomposer Agent
   - Classifies intent
   - Creates execution plan
   - Selects tools
   ↓
4. Tool Execution
   - Calendar.list_events()
   - Gmail.search_messages()
   - Tasks.add_task()
   - Notes.save_note()
   ↓
5. Synthesizer Agent
   - Formats results
   - Generates natural response
   - Suggests follow-ups
   ↓
6. User sees response + suggestions
```

### Example: "Schedule a meeting with John tomorrow at 3pm"

```
Context Agent Output:
{
  "resolved_message": "Schedule a meeting with John at 3pm tomorrow",
  "entities": {
    "people": ["John"],
    "times": ["15:00"],
    "dates": ["2026-04-05"]
  }
}

Decomposer Output:
{
  "type": "tool_execution",
  "steps": [
    {"action": "calendar.check_availability", "params": {...}},
    {"action": "calendar.create_event", "params": {...}}
  ]
}

Tool Results:
{
  "id": "evt_123",
  "summary": "Meeting with John",
  "start": "2026-04-05T15:00:00",
  "meet_link": "https://meet.google.com/xxx"
}

Synthesizer Output:
"I've scheduled a meeting with John for tomorrow at 3 PM. 
Here's the Google Meet link: https://meet.google.com/xxx"
```

---

## 📞 Support & Troubleshooting

### Issue: "Unauthorized" error
**Solution:** Re-authenticate
```bash
# Delete stored token and re-login
rm .venv/lib/...  # Clear cache
# Then click "Sign in with Google" again
```

### Issue: "Firestore not found"
**Solution:** Ensure Firestore is created
```bash
# Check in GCP Console
# Firestore > Databases > Check status
```

### Issue: "Vertex AI error"
**Solution:** Enable API
```bash
gcloud services enable aiplatform.googleapis.com
```

### Issue: "Static files not found"
**Solution:** Run from correct directory
```bash
cd zenith
uvicorn main:app --reload
```

---

## 📚 Useful Links

- **GCP Console:** https://console.cloud.google.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Vertex AI Docs:** https://cloud.google.com/vertex-ai/docs
- **Google APIs:** https://developers.google.com
- **Cloud Run Docs:** https://cloud.google.com/run/docs

---

## ✅ Next Steps

1. **Configure .env** - Fill in your GCP credentials
2. **Test locally** - Run on `localhost:8000`
3. **Try chat** - Ask Zenith anything
4. **Deploy** - Push to Cloud Run
5. **Monitor** - Check logs in GCP Console
6. **Integrate** - Connect to your project
7. **Customize** - Adjust colors, add features

---

**You're all set! 🎉 Now you have a fully functional personal assistant AI!**
