# Quick Start Checklist

**📘 For complete startup instructions, see [STARTUP.md](STARTUP.md)**

Copy this checklist and check off each step:

## ✅ Phase 0: Prerequisites (Before starting)

- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] GCP Project created
- [ ] Vertex AI API enabled in GCP
- [ ] Cloud Resource Manager API enabled
- [ ] Billing enabled in GCP
- [ ] Vertex AI quota approved (100+ requests/min)
- [ ] OAuth 2.0 credentials created

## ✅ Phase 1: Configuration (5 minutes)

- [ ] Have GCP Project ID ready
- [ ] Have OAuth Client ID ready
- [ ] Have OAuth Client Secret ready
- [ ] Copy `.env.example` to `.env`
- [ ] Fill in `.env` with credentials
- [ ] Generate JWT_SECRET_KEY

## ✅ Phase 2: Backend Setup (5 minutes)

- [ ] Open PowerShell in `zenith/` folder
- [ ] Create virtual environment: `python -m venv .venv`
- [ ] Activate venv: `.\.venv\Scripts\Activate.ps1`
- [ ] Install dependencies: `pip install -r requirements.txt`

## ✅ Phase 3: Frontend Setup (3 minutes)

- [ ] Navigate to `zenith/frontend/`
- [ ] Install npm dependencies: `npm install`
- [ ] Return to `zenith/` directory

## ✅ Phase 4: Start Application (2 minutes)

**Terminal 1 - Backend:**
- [ ] Navigate to `zenith/`
- [ ] Activate venv: `.\.venv\Scripts\Activate.ps1`
- [ ] Start backend: `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- [ ] Verify backend started (check for "Application startup complete")

**Terminal 2 - Frontend:**
- [ ] Navigate to `zenith/frontend/`
- [ ] Start frontend: `npm run dev`
- [ ] Note the frontend URL (e.g., http://localhost:3000)

## ✅ Phase 5: Test Application (10 minutes)

## ✅ Phase 5: Test Application (10 minutes)

- [ ] Open browser to frontend URL (e.g., http://localhost:3000)
- [ ] Click "Sign in with Google"
- [ ] Complete Google authentication
- [ ] Grant required permissions
- [ ] Send a test message: "Hello, what can you do?"
- [ ] Verify AI response appears
- [ ] Try calendar query: "What's on my calendar today?"
- [ ] Try email query: "Summarize my recent emails"

## ✅ Phase 6: Verify APIs (5 minutes)

- [ ] Open backend API docs: `http://localhost:8000/docs`
- [ ] Explore endpoint list
- [ ] Check browser console for errors (F12)
- [ ] Verify all integrations working

## ✅ Troubleshooting (If needed)

**If chat returns error "Response candidate has no content parts":**
- [ ] Verify Vertex AI API is enabled
- [ ] Verify billing is enabled
- [ ] Verify quota is approved
- [ ] Check `.env` has `VERTEX_AI_MODEL=gemini-1.5-pro`
- [ ] Check `.env` has `VERTEX_AI_LOCATION=us-central1`
- [ ] Restart backend server

**📘 For detailed troubleshooting, see [STARTUP.md](STARTUP.md#troubleshooting)**

---

## Next Steps

After successful setup:

- [ ] Read [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for advanced features
- [ ] Customize UI theme and colors
- [ ] Set up Firestore indexes (when needed)
- [ ] Explore all API endpoints
- [ ] Add custom tools and integrations

---

**⏱️ Total Time: ~30 minutes** (excluding GCP setup and quota approval)
- [ ] Monitor usage

---

**Total Time: ~35 minutes**

**Questions?** Check the INTEGRATION_GUIDE.md file for detailed steps.
