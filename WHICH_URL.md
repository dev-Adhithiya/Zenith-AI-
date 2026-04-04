# 🚨 IMPORTANT - Which URL to Use?

## ✅ Use This URL
```
http://localhost:3000
```
**This is the React frontend - your user interface!**

## ❌ Don't Use This URL
```
http://localhost:8000
```
**This is the FastAPI backend - API server only!**

---

## Why Two Servers?

This is **modern web architecture**:

### Port 3000 - Frontend (React)
- Beautiful glassmorphism UI
- What you see and interact with
- Automatically talks to the backend

### Port 8000 - Backend (FastAPI)
- API server for data and AI processing
- Runs in the background
- Not meant for direct browser access

---

## How to Start Both

### Terminal 1: Backend
```bash
cd zenith
python -m zenith.main
```
**Should see:** `Uvicorn running on http://0.0.0.0:8000`

### Terminal 2: Frontend
```bash
cd zenith/frontend
npm run dev
```
**Should see:** `Local: http://localhost:3000`

---

## Then Open Your Browser

Go to: **http://localhost:3000**

You'll see:
1. Beautiful animated gradient background
2. Glassmorphism sidebar
3. "Sign in with Google" button
4. Modern React interface

---

## Troubleshooting

### If you see the old UI (purple gradient)
❌ You're on port 8000 - **switch to port 3000!**

### If you see redirect page
✅ Good! You're on port 8000 but now know where to go
→ Click the button or manually go to port 3000

### If frontend won't start
```bash
cd zenith/frontend
npm install  # Install dependencies first
npm run dev
```

### If backend gives MAX_TOKENS error
✅ **Already fixed!** Just restart the backend:
```bash
cd zenith
python -m zenith.main
```

---

## Summary

| Port | What | Use? |
|------|------|------|
| 3000 | React Frontend (UI) | ✅ YES |
| 8000 | FastAPI Backend (API) | ❌ NO |

**Always use port 3000 in your browser!**
