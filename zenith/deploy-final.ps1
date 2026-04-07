# Zenith AI - Cloud Run Deployment Script
# Requirements: gcloud CLI configured, Docker installed
# Environment variables should be set before running this script

# Get project ID from environment or prompt for it
$PROJECT_ID = $env:GCP_PROJECT_ID
if (-not $PROJECT_ID) {
    $PROJECT_ID = Read-Host "Enter GCP Project ID"
}

$REGION = $env:GCP_REGION
if (-not $REGION) {
    $REGION = "us-central1"
}

Write-Host "Using Project ID: $PROJECT_ID" -ForegroundColor Cyan
Write-Host "Using Region: $REGION" -ForegroundColor Cyan

# Step 1: Build Docker image
Write-Host "Building Docker image..." -ForegroundColor Green
docker build -t gcr.io/$PROJECT_ID/zenith-ai .

# Step 2: Push to Container Registry
Write-Host "Pushing to Google Container Registry..." -ForegroundColor Green
docker push gcr.io/$PROJECT_ID/zenith-ai

# Step 3: Deploy to Cloud Run
Write-Host "Deploying to Cloud Run..." -ForegroundColor Green
# IMPORTANT: Configure these environment variables securely:
#   - GOOGLE_CLIENT_ID
#   - GOOGLE_CLIENT_SECRET  
#   - JWT_SECRET_KEY
#   - VERTEX_AI_MODEL
#   - VERTEX_AI_LOCATION
#
# Option 1: Use Google Cloud Secret Manager
# Option 2: Set --set-env-vars with secure values
# Option 3: Configure via GCP Console after deployment

gcloud run deploy zenith-ai `
  --image=gcr.io/$PROJECT_ID/zenith-ai `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --min-instances 0 `
  --max-instances 10 `
  --timeout 300 `
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,ALLOWED_ORIGINS=https://dev-adhithiya.github.io

Write-Host "Deployment complete!" -ForegroundColor Cyan
Write-Host "Your app is available at: https://zenith-ai-$PROJECT_ID.$REGION.run.app" -ForegroundColor Cyan
Write-Host "IMPORTANT: Configure GOOGLE_CLIENT_* and JWT_SECRET_KEY via Secret Manager!" -ForegroundColor Yellow
