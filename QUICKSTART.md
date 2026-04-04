# Quick Start Checklist

Copy this checklist and check off each step:

## ✅ Phase 1: Configuration (5 minutes)

- [ ] Have GCP Project ID ready
- [ ] Have OAuth Client ID ready
- [ ] Have OAuth Client Secret ready
- [ ] Copy `.env.example` to `.env`
- [ ] Fill in `.env` with credentials
- [ ] Generate JWT_SECRET_KEY

## ✅ Phase 2: Setup (5 minutes)

- [ ] Open PowerShell in `zenith/` folder
- [ ] Create virtual environment: `python -m venv .venv`
- [ ] Activate venv: `.\.venv\Scripts\Activate.ps1`
- [ ] Install dependencies: `pip install -r requirements.txt`

## ✅ Phase 3: Test Locally (10 minutes)

- [ ] Run server: `uvicorn main:app --reload --port 8000`
- [ ] Open browser: `http://localhost:8000`
- [ ] Click "Sign in with Google"
- [ ] Complete Google authentication
- [ ] Send a test message: "Show me my schedule"
- [ ] Check response appears

## ✅ Phase 4: Verify APIs (5 minutes)

- [ ] Open `http://localhost:8000/docs`
- [ ] Explore endpoint list
- [ ] Try different endpoints
- [ ] Check Console for errors (F12)

## ✅ Phase 5: Deploy (10 minutes)

- [ ] Setup secrets: `.\setup-secrets.ps1`
- [ ] Run deployment: `.\deploy.ps1`
- [ ] Wait for Cloud Run deployment
- [ ] Get service URL
- [ ] Update OAuth redirect URI in GCP
- [ ] Test deployed app

## ✅ Phase 6: Integration (ongoing)

- [ ] Embed in your project
- [ ] Customize UI colors
- [ ] Add custom endpoints
- [ ] Monitor usage

---

**Total Time: ~35 minutes**

**Questions?** Check the INTEGRATION_GUIDE.md file for detailed steps.
