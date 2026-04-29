# Zenith AI Cloud Deployment Script
$PROJECT_ID = "multi-agentproductivity"
$REGION = "asia-south1"
$SERVICE_NAME = "zenith-ai"
$IMAGE_TAG = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "🚀 Starting Cloud Build for Zenith AI..." -ForegroundColor Cyan

# Run Cloud Build
gcloud builds submit --tag $IMAGE_TAG --project $PROJECT_ID

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cloud Build failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✅ Cloud Build successful. Deploying to Cloud Run..." -ForegroundColor Cyan

# Deploy to Cloud Run
# We'll set the most important env vars here. 
# Others should be managed via the Cloud Console for security if they are sensitive.
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_TAG `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --project $PROJECT_ID `
    --set-env-vars "ENVIRONMENT=production,GCP_PROJECT_ID=$PROJECT_ID,JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY,GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET,VERTEX_AI_MODEL=gemini-2.5-flash,VERTEX_AI_LOCATION=us-central1,OAUTH_REDIRECT_URI=https://zenith-ai-156148005661.asia-south1.run.app/auth/callback,FRONTEND_REDIRECT_URLS=https://zenith-ai-156148005661.asia-south1.run.app"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cloud Run deployment failed!" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "🎉 Deployment complete!" -ForegroundColor Green
