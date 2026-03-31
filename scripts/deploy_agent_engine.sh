#!/usr/bin/env bash
# Deploy the ADK app to GCP Agent Engine using the ADK CLI
# Requires: gcloud authenticated (WIF or SA key) and ADK CLI installed in the runner
set -euo pipefail

# Required environment variables (provided by GitLab CI/CD variables or local env)
: "${PROJECT_ID:?PROJECT_ID is required}"
: "${REGION:?REGION is required}"
: "${ENGINE_NAME:?ENGINE_NAME is required}"              # e.g. product-validation-engine
: "${RUNTIME_SA_EMAIL:?RUNTIME_SA_EMAIL is required}"    # SA used at runtime by the Agent Engine instance

# App/env configuration expected by code
: "${BQ_DATASET:?BQ_DATASET is required}"
: "${BQ_TABLE:?BQ_TABLE is required}"
: "${GOOGLE_CLOUD_LOCATION:=us}"   # default to us
: "${GOOGLE_API_KEY:?GOOGLE_API_KEY is required (GenAI API key)}"

# Optional: When using WIF cred file we can export ADC to ensure the ADK CLI uses it
if [[ -f "/tmp/wif-cred.json" ]]; then
  export GOOGLE_APPLICATION_CREDENTIALS="/tmp/wif-cred.json"
fi

echo "Deploying ADK app to Agent Engine"
echo "Project: ${PROJECT_ID}, Region: ${REGION}, Engine Name: ${ENGINE_NAME}"
echo "Runtime SA: ${RUNTIME_SA_EMAIL}"

# Print ADK version for diagnostics
adk --version || true

# adk engine deploy arguments:
# --app is taken from pyproject [tool.adk] apps (we use module=name root_agent)
# NOTE: If your ADK CLI differs (e.g., subcommand flags), adjust accordingly.
adk engine deploy \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --name "${ENGINE_NAME}" \
  --app root_agent \
  --service-account "${RUNTIME_SA_EMAIL}" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},BQ_DATASET=${BQ_DATASET},BQ_TABLE=${BQ_TABLE},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_API_KEY=${GOOGLE_API_KEY}"

echo "Agent Engine deployment command completed."
