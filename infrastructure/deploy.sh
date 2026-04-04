#!/bin/bash
# Zenith AI - Cloud Run Deployment Script
# Run this from the zenith/ directory

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="zenith-ai"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "========================================"
echo "Zenith AI - Cloud Run Deployment"
echo "========================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "========================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check authentication
echo "Checking GCP authentication..."
gcloud auth print-identity-token > /dev/null 2>&1 || {
    echo "Not authenticated. Running 'gcloud auth login'..."
    gcloud auth login
}

# Set project
echo "Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Enable required services
echo "Enabling required GCP services..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com

# Build the container image
echo "Building container image..."
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 60 \
    --concurrency 80 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCP_REGION=${REGION}" \
    --update-secrets "GOOGLE_CLIENT_ID=google-client-id:latest" \
    --update-secrets "GOOGLE_CLIENT_SECRET=google-client-secret:latest" \
    --update-secrets "JWT_SECRET_KEY=jwt-secret-key:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "1. Update OAuth redirect URI in GCP Console:"
echo "   ${SERVICE_URL}/auth/callback"
echo ""
echo "2. Create secrets in Secret Manager:"
echo "   gcloud secrets create google-client-id --data-file=- <<< 'your-client-id'"
echo "   gcloud secrets create google-client-secret --data-file=- <<< 'your-client-secret'"
echo "   gcloud secrets create jwt-secret-key --data-file=- <<< 'your-jwt-secret'"
echo ""
echo "3. Test the API:"
echo "   curl ${SERVICE_URL}/health"
echo "========================================"
