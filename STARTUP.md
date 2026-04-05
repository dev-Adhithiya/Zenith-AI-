# Zenith AI - Startup Guide

Complete guide to starting and running Zenith AI Personal Assistant.

---

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [First-Time Setup](#first-time-setup)
- [Starting the Application](#starting-the-application)
- [Accessing the App](#accessing-the-app)
- [Stopping the Application](#stopping-the-application)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting Zenith AI, ensure you have:

### ✅ Required Software
- **Python 3.10+** installed
- **Node.js 18+** and npm installed (for frontend)
- **Git** installed

### ✅ Google Cloud Project Setup
1. **GCP Project Created**
   - Project ID: `multi-agentproductivity` (or your project)
   
2. **APIs Enabled** in GCP Console:
   - ✅ Vertex AI API
   - ✅ Cloud Resource Manager API
   - ✅ Firestore API
   - ✅ Gmail API
   - ✅ Google Calendar API
   - ✅ Google Tasks API

3. **Billing Enabled**
   - Required for Vertex AI API access

4. **Vertex AI Model Quota**
   - Request quota for `gemini-1.5-pro` or `gemini-2.0-flash`
   - Minimum: 100 requests/minute

5. **OAuth 2.0 Credentials**
   - Created in GCP Console → APIs & Services → Credentials
   - Authorized redirect URI: `http://localhost:8000/auth/callback`

### ✅ Environment Configuration
The `.env` file must be properly configured (see [First-Time Setup](#first-time-setup))

---

## First-Time Setup

### 1. Clone and Navigate to Project
```bash
cd "f:\projec main final\AI AGENT"
```

### 2. Backend Setup

#### Create Python Virtual Environment
```bash
cd zenith
python -m venv .venv
```

#### Activate Virtual Environment
**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Configure Environment Variables

Copy the example file and edit with your credentials:

```bash
cd ..  # Back to zenith directory
cp .env.example .env
```

Edit `.env` with your values:

```env
# GCP Configuration
GCP_PROJECT_ID=multi-agentproductivity
GCP_REGION=asia-south1

# OAuth 2.0 Credentials
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# OAuth Redirect URI
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback

# Vertex AI Configuration
VERTEX_AI_MODEL=gemini-1.5-pro
VERTEX_AI_LOCATION=us-central1

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-generated-secret-key

# Debug Mode
DEBUG=true
```

**Important Notes:**
- `VERTEX_AI_MODEL`: Use `gemini-1.5-pro` or `gemini-2.0-flash` (both tested and working)
- `VERTEX_AI_LOCATION`: Use `us-central1` where models are most available
- `JWT_SECRET_KEY`: Generate with `openssl rand -hex 32` or any secure random string

### 5. Setup Firestore Indexes

When you first run the app, if you see errors about missing indexes, Firestore will provide a link to create them automatically. Just click the link and it will create all required indexes.

Alternatively, see `setup-firestore-indexes.md` for manual setup instructions.

---

## Starting the Application

You need to start **TWO** servers: Backend and Frontend.

### Option 1: Using Two Terminal Windows (Recommended)

#### Terminal 1: Start Backend Server

```bash
# Navigate to zenith directory
cd "f:\projec main final\AI AGENT\zenith"

# Activate virtual environment (if not already active)
.venv\Scripts\Activate.ps1

# Start backend server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Will watch for changes in these directories: ['F:\\projec main final\\AI AGENT\\zenith']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [67890]
INFO:     Waiting for application startup.
{"version": "1.0.0", "event": "Starting Zenith AI", "timestamp": "2026-04-04T..."}
INFO:     Application startup complete.
```

✅ Backend is now running on **http://localhost:8000**

---

#### Terminal 2: Start Frontend Server

```bash
# Navigate to frontend directory
cd "f:\projec main final\AI AGENT\zenith\frontend"

# Start frontend dev server
npm run dev
```

**Expected Output:**
```
> zenith-frontend@1.0.0 dev
> vite

  VITE v5.4.21  ready in 342 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

✅ Frontend is now running on **http://localhost:3000** (or 3001, 3002, etc. if 3000 is in use)

---

### Option 2: Using Start Scripts (Automated)

#### Windows PowerShell Script

Create `start-zenith.ps1`:
```powershell
# Start Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'f:\projec main final\AI AGENT\zenith'; .venv\Scripts\Activate.ps1; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

# Wait 5 seconds for backend to start
Start-Sleep -Seconds 5

# Start Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'f:\projec main final\AI AGENT\zenith\frontend'; npm run dev"

Write-Host "✅ Zenith AI servers starting..."
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
```

Run with:
```powershell
.\start-zenith.ps1
```

---

## Accessing the App

### 1. Open Your Browser

Navigate to the frontend URL (shown in Terminal 2):
```
http://localhost:3000
```

If port 3000 is in use, check the terminal output for the actual port (e.g., 3001, 3002, etc.)

### 2. Sign In with Google

1. Click **"Sign in with Google"** button
2. Choose your Google account
3. Grant permissions for:
   - Gmail access
   - Calendar access
   - Tasks access
   - Basic profile info

### 3. Start Chatting!

Once signed in:
- Type a message in the chat input
- Press Enter or click Send
- Zenith AI will respond using Vertex AI

**Example prompts:**
- "What's on my calendar today?"
- "Summarize my recent emails"
- "Add a task to buy groceries"
- "Create a meeting tomorrow at 2pm"

---

## Stopping the Application

### Stop Backend Server
In Terminal 1 (backend):
```
Press Ctrl+C
```

### Stop Frontend Server
In Terminal 2 (frontend):
```
Press Ctrl+C
```

**Or close the terminal windows.**

---

## Troubleshooting

### ❌ Backend Won't Start

**Error: "Port 8000 is already in use"**

**Solution:**
```powershell
# Windows: Find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Error: "ModuleNotFoundError: No module named '...'"**

**Solution:**
```bash
# Ensure virtual environment is activated
.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "404 Publisher Model not found"**

**Solution:**
This means Vertex AI API is not enabled or model quota not approved.
1. Go to GCP Console → APIs & Services → Library
2. Enable "Vertex AI API"
3. Go to Quotas page and request `generative_ai` quota
4. Wait 5-30 minutes for approval
5. Restart backend server

---

### ❌ Frontend Won't Start

**Error: "npm ERR! code ENOENT"**

**Solution:**
```bash
cd frontend
npm install
npm run dev
```

**Error: "Port 3000 is already in use"**

**Solution:**
Vite will automatically try the next available port (3001, 3002, etc.). Check the terminal output for the actual URL.

---

### ❌ Chat Not Working

**Error: "Response candidate has no content parts"**

**Causes:**
1. Vertex AI API not enabled
2. Model quota not approved
3. Wrong model name in .env

**Solution:**
1. Check `.env` has correct model: `gemini-1.5-pro` or `gemini-2.0-flash`
2. Check location: `us-central1` (most reliable)
3. Verify Vertex AI API is enabled in GCP
4. Verify quota is approved (check email or GCP quotas page)

---

### ❌ Authentication Failed

**Error: "Invalid OAuth credentials"**

**Solution:**
1. Go to GCP Console → APIs & Services → Credentials
2. Verify OAuth 2.0 Client ID is correct
3. Verify redirect URI includes: `http://localhost:8000/auth/callback`
4. Copy correct Client ID and Secret to `.env`
5. Restart backend server

---

### ❌ Firestore Errors

**Error: "The query requires an index"**

**Solution:**
1. Click the error link (it will open GCP Console)
2. Click "Create Index"
3. Wait 2-5 minutes for index to build
4. Retry the operation

---

### ❌ Notes Not Working

**Error: "400 Bad Request" when saving notes**

**Solution:**
Same as Firestore errors - create the required composite index.

---

## Verification Checklist

Before using Zenith AI, verify:

- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] Virtual environment created and activated
- [ ] All Python dependencies installed (`pip install -r requirements.txt`)
- [ ] All npm dependencies installed (`npm install` in frontend/)
- [ ] `.env` file configured with correct credentials
- [ ] GCP Project has Vertex AI API enabled
- [ ] GCP Project has billing enabled
- [ ] Vertex AI model quota approved
- [ ] OAuth credentials created and configured
- [ ] Backend server starts without errors
- [ ] Frontend server starts without errors
- [ ] Can access http://localhost:8000 (backend)
- [ ] Can access http://localhost:3000 (frontend)
- [ ] Can sign in with Google
- [ ] Can send a chat message and get AI response

---

## Quick Reference

### File Locations
```
f:\projec main final\AI AGENT\
├── zenith/                    # Backend directory
│   ├── .env                  # Environment configuration
│   ├── .venv/                # Python virtual environment
│   ├── main.py               # Backend entry point
│   ├── requirements.txt      # Python dependencies
│   └── frontend/             # Frontend directory
│       ├── package.json      # npm dependencies
│       └── src/              # Frontend source code
├── README.md                 # Project overview
├── STARTUP.md               # This file
└── INTEGRATION_GUIDE.md     # Detailed setup guide
```

### Important URLs
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **GCP Console:** https://console.cloud.google.com
- **Vertex AI Quotas:** https://console.cloud.google.com/iam-admin/quotas

### Important Commands

**Start Backend:**
```bash
cd zenith
.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Start Frontend:**
```bash
cd zenith/frontend
npm run dev
```

**Stop Servers:**
```
Ctrl+C in each terminal
```

---

## Next Steps

After successfully starting Zenith AI:

1. **Read the README.md** for feature overview
2. **Check INTEGRATION_GUIDE.md** for advanced configuration
3. **Explore the UI** and try different chat prompts
4. **Test integrations** (Gmail, Calendar, Tasks, Notes)
5. **Customize settings** in the app sidebar

---

## Support

If you encounter issues not covered in this guide:

1. Check the backend terminal for error messages
2. Check the frontend terminal for errors
3. Check browser console (F12) for frontend errors
4. Review `.env` file for correct configuration
5. Verify all GCP APIs are enabled
6. Ensure Vertex AI quota is approved

---

**🎉 Enjoy using Zenith AI!**

For detailed technical documentation, see:
- [README.md](README.md) - Project overview
- [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Integration details
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Architecture overview
