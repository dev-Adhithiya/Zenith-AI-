# Troubleshooting Guide - Failed to Fetch / Image Upload Issues

## Diagnostics

### 1. Check Backend Connection
Open browser console (F12) and run:
```javascript
fetch('http://localhost:8000/debug/test').then(r => r.json()).then(console.log)
```

Expected response: `{ status: "ok", message: "Backend is working" }`

If this fails:
- Backend is not running, or
- Using wrong port/URL, or
- CORS is blocked

### 2. Check API URL
In browser console:
```javascript
// Should see the API URL
console.log(import.meta.env.VITE_API_URL || 'http://localhost:8000')
```

### 3. Check Authentication Token
```javascript
localStorage.getItem('access_token')
```
Should return a JWT token if you're logged in.

## Common Issues & Solutions

### Issue: "Failed to fetch" on chat message
**Possible causes:**
1. Backend not running
2. Wrong API URL (check .env VITE_API_URL)
3. Authentication token missing or expired
4. Rate limiting (too many requests)
5. Network timeout

**Solutions:**
```bash
# 1. Make sure backend is running
cd zenith
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 2. Check frontend is using correct API URL
# In frontend/.env or vite.config.ts
VITE_API_URL=http://localhost:8000

# 3. Clear cache and re-login
# Clear localStorage and cookies, log back in

# 4. Check backend logs for errors
# Look at terminal running uvicorn
```

### Issue: Image upload not working
**Possible causes:**
1. File validation failing (not an image or too large)
2. FormData not being sent correctly
3. Backend not processing files
4. Browser paste functionality not working

**Solutions:**
```javascript
// 1. Check browser console for messages like:
[Chat] Sending message with 2 image(s)
[Chat] Sending to: http://localhost:8000/chat

// 2. Check if paste is working - try dragging an image instead
// 3. Check file size - max 5MB per image
// 4. Try uploading via the image button instead of paste
```

### Issue: Profile picture not loading
Already fixed - should show fallback avatar if image fails to load.

Check browser console for any 403/CORS errors related to image loading.

## Backend Logs to Check

When running the backend, look for:
```
[ERROR] Chat endpoint error - indicates what went wrong
[WARNING] Failed to process image - image validation failed
[WARNING] Non-image file rejected - wrong file type
[WARNING] Image too large - exceeds 5MB limit
```

## Test Commands

### Test chat endpoint with curl (no images):
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=Hello" \
  -d "session_id=test-session"
```

### Test chat endpoint with curl (with image):
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "message=What's in this image?" \
  -F "session_id=test-session" \
  -F "images=@/path/to/image.jpg"
```

### Test health endpoint:
```bash
curl http://localhost:8000/health
```

## Frontend Debug Info

If you open the browser console (F12), you should see messages like:
```
[Chat] Sending text-only message
[Chat] Sending to: http://localhost:8000/chat
[Chat] Sending message with 2 image(s)
```

If you see API errors, they'll be logged with full details:
```
API Error 401: Unauthorized
API Error 400: Message is required
API Error 500: Internal server error details...
```

## Environment Variables

### Frontend (.env or .env.local)
```
VITE_API_URL=http://localhost:8000
```

### Backend (.env)
```
GCP_PROJECT_ID=your-project
VERTEX_AI_MODEL=gemini-2.5-flash
VERTEX_AI_LOCATION=us-central1
DEBUG=true
```

## Restart Steps

If nothing works, do a full restart:

```bash
# 1. Kill both frontend and backend processes

# 2. Clear caches
rm -rf node_modules .vite __pycache__

# 3. Reinstall dependencies
cd frontend && npm install && cd ..
pip install -r requirements.txt

# 4. Restart in a fresh terminal
# Terminal 1: Backend
cd zenith
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd zenith/frontend
npm run dev
```

## Still Having Issues?

Please check:
1. Backend terminal for error messages
2. Browser console (F12) for network errors
3. Browser Network tab to see the actual request/response
4. Confirm you're logged in (should see profile picture in sidebar)
5. Make sure both backend and frontend are running

## File Size Limits

Current limits:
- **Max image size**: 5MB per image
- **Max message length**: 4000 characters
- **Rate limit**: Check auth/dependencies.py for limits

To change these, edit:
- `models/requests.py` for message length
- `frontend/src/components/chat/InputArea.tsx` for UI validation
- `main.py` chat endpoint for backend validation
