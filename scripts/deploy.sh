#!/usr/bin/env bash
# Deploy the ADK app container to Cloud Run
# Requires: gcloud authenticated with permissions to deploy (via WIF or SA key)
set -euo pipefail

# Required environment variables (provided by GitLab CI/CD variables or local env)
: "${PROJECT_ID:?PROJECT_ID is required}"
: "${REGION:?REGION is required}"
: "${SERVICE_NAME:?SERVICE_NAME is required}"
: "${IMAGE:?IMAGE (full Artifact Registry path) is required}"
: "${RUNTIME_SA_EMAIL:?RUNTIME_SA_EMAIL is required}"
: "${BQ_DATASET:?BQ_DATASET is required}"
: "${BQ_TABLE:?BQ_TABLE is required}"
: "${GOOGLE_CLOUD_LOCATION:=us}"   # default to us
: "${GOOGLE_API_KEY:?GOOGLE_API_KEY is required (GenAI API key)}"

# Optional tuning
: "${MAX_INSTANCES:=10}"
: "${CPU:=1}"
: "${MEMORY:=1Gi}"
: "${CONCURRENCY:=80}"
: "${ALLOW_UNAUTH:=false}"

ALLOW_FLAG="--no-allow-unauthenticated"
if [[ "${ALLOW_UNAUTH}" == "true" ]]; then
  ALLOW_FLAG="--allow-unauthenticated"
fi

echo "Deploying ${SERVICE_NAME} to Cloud Run in project ${PROJECT_ID}, region ${REGION}"
echo "Using image: ${IMAGE}"
echo "Runtime SA: ${RUNTIME_SA_EMAIL}"

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --service-account="${RUNTIME_SA_EMAIL}" \
  --platform=managed \
  ${ALLOW_FLAG} \
  --min-instances=0 \
  --max-instances="${MAX_INSTANCES}" \
  --cpu="${CPU}" \
  --memory="${MEMORY}" \
  --concurrency="${CONCURRENCY}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},BQ_DATASET=${BQ_DATASET},BQ_TABLE=${BQ_TABLE},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_API_KEY=${GOOGLE_API_KEY}"

echo "Deployment complete."
