#!/bin/bash
set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="market-scout-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Deploying Market Scout FastAPI Backend to Google Cloud Run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if gcloud CLI is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install it: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Authenticate and set project
echo "🔐 Authenticating with Google Cloud..."
gcloud auth configure-docker
gcloud config set project "${PROJECT_ID}"

# Build Docker image
echo "🔨 Building Docker image..."
docker build -t "${IMAGE_NAME}:latest" -t "${IMAGE_NAME}:$(date +%s)" .

# Push to Google Container Registry
echo "📦 Pushing image to Container Registry..."
docker push "${IMAGE_NAME}:latest"

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE_NAME}:latest" \
  --platform=managed \
  --region="${REGION}" \
  --memory=2Gi \
  --cpu=2 \
  --timeout=3600 \
  --max-instances=10 \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=info" \
  --service-account="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform=managed --region="${REGION}" --format='value(status.url)')

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment complete!"
echo "🔗 Service URL: ${SERVICE_URL}"
echo "📊 Health check: ${SERVICE_URL}/health"
echo "📝 API docs: ${SERVICE_URL}/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show logs
echo ""
echo "📋 Recent logs:"
gcloud run logs read "${SERVICE_NAME}" --platform=managed --region="${REGION}" --limit=20

# Test the deployment
echo ""
echo "🧪 Testing health endpoint..."
curl -s "${SERVICE_URL}/health" | jq . || echo "Service not yet ready, check logs in few moments"
