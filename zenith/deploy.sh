#!/bin/bash
# Deploy Zenith AI to Google Cloud Run

set -e

# Configuration
PROJECT_ID="your-project-id"  # Replace with your GCP project ID
REGION="asia-south1"
SERVICE_NAME="zenith-ai"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Zenith AI to Cloud Run..."

# Change to zenith directory
cd "$(dirname "$0")"

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t "${IMAGE_NAME}:latest" .

# Push to Google Container Registry
echo "⬆️  Pushing image to GCR..."
docker push "${IMAGE_NAME}:latest"

# Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_NAME}:latest" \
  --platform=managed \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="ENVIRONMENT=production"

echo "✅ Deployment complete!"
echo "🌐 Your app is available at the URL shown above"
