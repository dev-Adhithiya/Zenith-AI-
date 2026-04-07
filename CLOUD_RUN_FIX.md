# Cloud Run Deployment Fix

## Problem
The frontend wasn't showing in Cloud Run - instead, backend errors were displayed because:
1. The frontend build output (`frontend/dist/`) wasn't being copied to the `static/` directory where the backend expects it
2. The Vite config had `base: '/Zenith-AI-/'` which is for GitHub Pages, not Cloud Run

## Solution Applied

### 1. Updated `Dockerfile`
Modified the Dockerfile to:
- Install Node.js and npm during the build phase
- Build the frontend inside the Docker container
- Copy the frontend build output to `/app/static/`
- Clean up Node.js and build artifacts to keep the image small

### 2. Updated `frontend/vite.config.ts`
Changed the base path from `/Zenith-AI-/` to `/` for proper Cloud Run deployment.

### 3. Created `.dockerignore`
Added a `.dockerignore` file to optimize the Docker build by excluding:
- Node modules (will be installed fresh)
- Python cache files
- Development files
- Existing dist and static folders

## How to Deploy

### Option 1: Using gcloud CLI

```bash
# Navigate to the zenith directory
cd zenith

# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="asia-south1"

# Build and submit the container
gcloud builds submit --tag gcr.io/${PROJECT_ID}/zenith-ai

# Deploy to Cloud Run
gcloud run deploy zenith-ai \
  --image gcr.io/${PROJECT_ID}/zenith-ai \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars "ENVIRONMENT=production,GCP_PROJECT_ID=${PROJECT_ID}"
```

### Option 2: Using the deploy script

```bash
# Make the script executable (Linux/Mac)
chmod +x deploy.sh

# Edit deploy.sh and set your PROJECT_ID

# Run the deployment
./deploy.sh
```

### Option 3: Via Cloud Console

1. Go to Cloud Run in Google Cloud Console
2. Click "Create Service"
3. Choose "Continuously deploy from a repository" or "Deploy one revision from an existing container image"
4. If building from source:
   - Connect your GitHub repository
   - Set build type to Dockerfile
   - Set source location to `/zenith/Dockerfile`
5. Configure:
   - Port: 8080
   - Memory: 2Gi
   - CPU: 2
   - Min instances: 0
   - Max instances: 10
6. Add environment variables as needed
7. Click "Create"

## Environment Variables to Set in Cloud Run

Make sure to configure these in Cloud Run:
- `GCP_PROJECT_ID` - Your Google Cloud Project ID
- `GOOGLE_CLIENT_ID` - OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - OAuth Client Secret
- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `ENVIRONMENT` - Set to "production"
- Any other variables from your `.env` file

## Verification

After deployment:
1. Visit your Cloud Run URL
2. You should see the Zenith AI frontend (not a backend error)
3. Check `/health` endpoint: `https://your-service-url/health`
4. Check `/debug/test` endpoint: `https://your-service-url/debug/test`

## Troubleshooting

### If you still see backend errors:
1. Check Cloud Run logs: `gcloud run services logs read zenith-ai --region=asia-south1`
2. Verify the frontend was built: Check if `/app/static/index.html` exists in the container
3. Test locally first:
   ```bash
   docker build -t zenith-test .
   docker run -p 8080:8080 zenith-test
   # Visit http://localhost:8080
   ```

### If the build fails:
1. Check that Node.js version in Dockerfile is compatible with your frontend
2. Verify all frontend dependencies are listed in `package.json`
3. Check frontend build logs in Cloud Build

## Differences from Local Development

| Aspect | Local Dev | Cloud Run |
|--------|-----------|-----------|
| Frontend Serving | Vite dev server (port 3000) | Built static files served by FastAPI |
| Base URL | `/Zenith-AI-/` (for GitHub Pages) | `/` |
| API Proxy | Vite proxy to backend | Direct to backend |
| Hot Reload | Yes | No (production build) |

## Future Improvements

Consider these optimizations:
1. Multi-stage Docker build to separate build and runtime
2. CDN for static assets
3. Separate frontend deployment to Cloud Storage + Cloud CDN
4. Use Cloud Build triggers for automated deployments from GitHub
