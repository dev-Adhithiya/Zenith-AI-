# Zenith AI - Cloud Run Deployment Script (PowerShell)
# Run this from the zenith/ directory

param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$Region = "us-central1",
    [string]$ServiceName = "zenith-ai"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "Zenith AI - Cloud Run Deployment"
Write-Host "========================================"
Write-Host "Project: $ProjectId"
Write-Host "Region: $Region"
Write-Host "Service: $ServiceName"
Write-Host "========================================"

if (-not $ProjectId) {
    Write-Host "Error: GCP_PROJECT_ID not set"
    Write-Host "Set it with: `$env:GCP_PROJECT_ID = 'your-project-id'"
    exit 1
}

$ImageName = "gcr.io/$ProjectId/$ServiceName"

# Check if gcloud is installed
try {
    gcloud --version | Out-Null
} catch {
    Write-Host "Error: gcloud CLI is not installed"
    Write-Host "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Set project
Write-Host "Setting project to $ProjectId..."
gcloud config set project $ProjectId

# Enable required services
Write-Host "Enabling required GCP services..."
gcloud services enable `
    cloudbuild.googleapis.com `
    run.googleapis.com `
    containerregistry.googleapis.com `
    secretmanager.googleapis.com

# Build the container image
Write-Host "Building container image..."
Set-Location -Path "..\zenith"
gcloud builds submit --tag $ImageName

# Deploy to Cloud Run
Write-Host "Deploying to Cloud Run..."
gcloud run deploy $ServiceName `
    --image $ImageName `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --memory 1Gi `
    --cpu 1 `
    --timeout 60 `
    --concurrency 80 `
    --min-instances 0 `
    --max-instances 10 `
    --set-env-vars "GCP_PROJECT_ID=$ProjectId" `
    --set-env-vars "GCP_REGION=$Region" `
    --update-secrets "GOOGLE_CLIENT_ID=google-client-id:latest" `
    --update-secrets "GOOGLE_CLIENT_SECRET=google-client-secret:latest" `
    --update-secrets "JWT_SECRET_KEY=jwt-secret-key:latest"

# Get the service URL
$ServiceUrl = gcloud run services describe $ServiceName --region $Region --format 'value(status.url)'

Write-Host "========================================"
Write-Host "Deployment Complete!"
Write-Host "========================================"
Write-Host "Service URL: $ServiceUrl"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Update OAuth redirect URI in GCP Console:"
Write-Host "   $ServiceUrl/auth/callback"
Write-Host ""
Write-Host "2. Create secrets in Secret Manager (if not done):"
Write-Host "   See setup-secrets.ps1"
Write-Host ""
Write-Host "3. Test the API:"
Write-Host "   Invoke-RestMethod -Uri '$ServiceUrl/health'"
Write-Host "========================================"
