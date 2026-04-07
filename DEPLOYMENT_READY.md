# ✅ Cloud Run Deployment - Ready to Deploy

## ✨ What's Fixed

Your Zenith AI application is now **fully ready for Cloud Run deployment**. The Docker image includes:

✅ **Frontend** - Built React app served from `/app/static/`  
✅ **Backend** - FastAPI server on port 8080  
✅ **Health checks** - Configured and working  
✅ **Single container** - Everything in one image  

---

## 🚀 Deploy to Google Cloud Run

### **Step 1: Set Your GCP Project**

```powershell
# Set your project ID
$PROJECT_ID = "your-gcp-project-id"  # Change this!
$REGION = "asia-south1"
```

### **Step 2: Build and Push to Container Registry**

```powershell
cd zenith

# Build the Docker image
docker build -t gcr.io/$PROJECT_ID/zenith-ai .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/zenith-ai
```

### **Step 3: Deploy to Cloud Run**

**Option A: Using gcloud CLI**
```powershell
gcloud run deploy zenith-ai `
  --image gcr.io/$PROJECT_ID/zenith-ai:latest `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --min-instances 0 `
  --max-instances 10 `
  --set-env-vars `
    "GCP_PROJECT_ID=$PROJECT_ID,`
     GOOGLE_CLIENT_ID=your-client-id,`
     GOOGLE_CLIENT_SECRET=your-client-secret,`
     JWT_SECRET_KEY=your-jwt-secret-key"
```

**Option B: Using the provided script**
```powershell
# Edit deploy.sh with your PROJECT_ID
.\deploy.sh
```

**Option C: Via Cloud Console**
1. Go to Cloud Run in Google Cloud Console
2. Click "Create Service"
3. Select "Deploy one revision from an existing container image"
4. Enter: `gcr.io/your-project-id/zenith-ai:latest`
5. Configure:
   - **Service name:** zenith-ai
   - **Region:** asia-south1
   - **Authentication:** Allow unauthenticated invocations
   - **Port:** 8080
   - **Memory:** 2Gi
   - **CPU:** 2
   - **Min instances:** 0
   - **Max instances:** 10
6. Add environment variables:
   - `GCP_PROJECT_ID`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `JWT_SECRET_KEY`
7. Click "Create"

---

## 📝 Required Environment Variables

Set these in Cloud Run environment variables (not in code):

| Variable | Value | Required |
|----------|-------|----------|
| `GCP_PROJECT_ID` | Your GCP project ID | ✅ Yes |
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client ID | ✅ Yes |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret | ✅ Yes |
| `JWT_SECRET_KEY` | Secret key for JWT tokens (random string) | ✅ Yes |
| `ENVIRONMENT` | `production` or `development` | ❌ Optional |

---

## ✅ Verify Deployment

Once deployed, test these endpoints:

```powershell
# Replace with your Cloud Run URL
$URL = "https://zenith-ai-xxxxx.asia-south1.run.app"

# Test health
curl "$URL/health"

# Should return:
# {"status":"healthy","version":"1.0.0","timestamp":"..."}

# Test frontend
curl "$URL/"
# Should return HTML with Zenith AI frontend
```

---

## 🔍 What Happens During Deployment

1. **Cloud Build pulls your image** from Container Registry
2. **Cloud Run starts the container** on port 8080
3. **Container startup:**
   - Loads environment variables
   - Initializes FastAPI app
   - Mounts frontend static files
   - Health check passes ✅
4. **User visits URL:**
   - Request to `/` → Returns `index.html`
   - Request to `/assets/*` → Returns JavaScript/CSS bundles
   - Request to `/api/*` → Routes to backend endpoints
   - Request to `/health` → Backend health check

---

## 📊 Performance & Scaling

| Metric | Configuration |
|--------|---------------|
| **CPU** | 2 vCPU |
| **Memory** | 2 GB |
| **Min instances** | 0 (scale to zero when idle) |
| **Max instances** | 10 (auto-scale) |
| **Timeout** | 300 seconds |
| **Request timeout** | None (uses default) |

---

## 🐛 Troubleshooting

### Frontend not showing (404 errors)
- Check Cloud Run logs: `gcloud run services logs read zenith-ai --region=asia-south1`
- Verify `static/index.html` exists in container
- Check MIME type configuration

### Backend errors
- Check environment variables are set correctly
- Verify OAuth credentials in Cloud Run settings
- Check that Vertex AI API is enabled in your GCP project

### Cold start slow
- Set `min-instances: 1` to keep container warm (costs more)
- Optimize dependencies in `requirements.txt`

### Port already in use locally
```powershell
docker ps -a
docker kill <container-id>
```

---

## 📋 Pre-Deployment Checklist

Before deploying to Cloud Run, ensure:

- [ ] GCP Project created and billed
- [ ] `gcloud` CLI installed and authenticated
- [ ] OAuth 2.0 credentials configured
- [ ] Vertex AI API enabled in GCP
- [ ] Docker image builds locally successfully
- [ ] Environment variables ready
- [ ] Container Registry API enabled

---

## ✨ Next Steps

1. **Set environment variables** with your actual OAuth credentials
2. **Run** `docker build -t gcr.io/YOUR-PROJECT-ID/zenith-ai .`
3. **Push** `docker push gcr.io/YOUR-PROJECT-ID/zenith-ai`
4. **Deploy** using gcloud CLI or Cloud Console
5. **Test** the health endpoint and frontend

Your Zenith AI is ready! 🚀
