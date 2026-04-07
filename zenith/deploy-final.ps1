# Zenith AI - Cloud Run Deployment with Actual Credentials

$PROJECT_ID = "multi-agentproductivity"
$REGION = "asia-south1"

# Step 1: Build Docker image
Write-Host "Building Docker image..." -ForegroundColor Green
docker build -t gcr.io/$PROJECT_ID/zenith-ai .

# Step 2: Push to Container Registry
Write-Host "Pushing to Google Container Registry..." -ForegroundColor Green
docker push gcr.io/$PROJECT_ID/zenith-ai

# Step 3: Deploy to Cloud Run
Write-Host "Deploying to Cloud Run..." -ForegroundColor Green
# Configure environment variables in Secret Manager or .env before running
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
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID

Write-Host "Deployment complete!" -ForegroundColor Cyan
Write-Host "Your app is available at the URL shown above" -ForegroundColor Cyan
