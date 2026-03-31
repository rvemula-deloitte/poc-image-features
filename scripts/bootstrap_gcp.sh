#!/usr/bin/env bash
# Bootstrap GCP for deploying an ADK app to GCP Agent Engine via GitLab CI
# - Creates runtime and deployer service accounts
# - Grants least-privileged IAM for runtime (BigQuery + Discovery Engine)
# - Configures Workload Identity Federation (WIF) for GitLab CI (keyless)
# - Enables required APIs (idempotent)
#
# Notes:
# - This script purposely avoids Cloud Run/Artifact Registry roles. Agent Engine deployment uses `adk engine deploy`.
# - If you previously used Cloud Run, you can remove those roles separately.
#
# Requirements:
# - gcloud, bq CLIs authenticated with sufficient permissions on the target project
# - You have Owner or the following aggregate permissions:
#     serviceusage.services.enable
#     iam.serviceAccounts.create
#     iam.serviceAccounts.setIamPolicy
#     resourcemanager.projects.getIamPolicy / setIamPolicy
#     bigquery.datasets.create / update
# - For dataset-level bindings, bq CLI is used.

set -euo pipefail

# =========================
# Configurable parameters
# =========================
PROJECT_ID="${PROJECT_ID:-changeme-project}"
REGION="${REGION:-us-central1}"

# Agent Engine logical name (used by CI/CD deploy); creation is handled by `adk engine deploy`
ENGINE_NAME="${ENGINE_NAME:-product-validation-engine}"

# Service accounts
RUNTIME_SA_ID="${RUNTIME_SA_ID:-ae-product-validation-runtime}"
DEPLOYER_SA_ID="${DEPLOYER_SA_ID:-gitlab-deployer}"

# BigQuery (dataset-level, least privilege)
BQ_DATASET="${BQ_DATASET:-poc_product_intake}"
CREATE_BQ_DATASET="${CREATE_BQ_DATASET:-true}"  # set to false to skip dataset creation

# Workload Identity Federation (optional but recommended)
ENABLE_WIF="${ENABLE_WIF:-true}"
WIF_POOL_ID="${WIF_POOL_ID:-gitlab-pool}"
WIF_PROVIDER_ID="${WIF_PROVIDER_ID:-gitlab}"
# GitLab repository path for binding (group/project). Example: mygroup/myrepo
GITLAB_REPO="${GITLAB_REPO:-mygroup/myrepo}"
GITLAB_ISSUER="${GITLAB_ISSUER:-https://gitlab.com}"

# Optional: grant Service Usage Admin to Deployer SA so CI can enable services (broader permission)
GRANT_SERVICE_USAGE_ADMIN="${GRANT_SERVICE_USAGE_ADMIN:-false}"

# =========================
# Derived values
# =========================
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA_EMAIL="${RUNTIME_SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
DEPLOYER_SA_EMAIL="${DEPLOYER_SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Project: $PROJECT_ID ($PROJECT_NUMBER)"
echo "Region: $REGION"
echo "Engine Name: $ENGINE_NAME"
echo "Runtime SA:  $RUNTIME_SA_EMAIL"
echo "Deployer SA: $DEPLOYER_SA_EMAIL"
echo "BQ Dataset:  $BQ_DATASET"
echo "WIF: pool=$WIF_POOL_ID provider=$WIF_PROVIDER_ID repo=$GITLAB_REPO (enabled=$ENABLE_WIF)"

# =========================
# Enable required services
# =========================
echo "==> Enabling required APIs (idempotent)"
gcloud services enable \
  serviceusage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  bigquery.googleapis.com \
  discoveryengine.googleapis.com \
  --project "$PROJECT_ID" || true

# Try to enable Agent Engine API if available in your environment (ignore if unknown)
gcloud services enable adkengine.googleapis.com --project "$PROJECT_ID" || true

# =========================
# Service accounts
# =========================
echo "==> Creating service accounts (idempotent)"
gcloud iam service-accounts describe "$RUNTIME_SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$RUNTIME_SA_ID" --display-name="Agent Engine runtime SA for $ENGINE_NAME" --project "$PROJECT_ID"

gcloud iam service-accounts describe "$DEPLOYER_SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1 || \
  gcloud iam service-accounts create "$DEPLOYER_SA_ID" --display-name="GitLab deployer SA for $ENGINE_NAME" --project "$PROJECT_ID"

# =========================
# BigQuery: dataset + dataset-level IAM (least privilege)
# =========================
if [[ "$CREATE_BQ_DATASET" == "true" ]]; then
  echo "==> Ensuring BigQuery dataset exists: $BQ_DATASET"
  bq --project_id="$PROJECT_ID" --location=US ls -d "$BQ_DATASET" >/dev/null 2>&1 || \
    bq --project_id="$PROJECT_ID" --location=US mk -d "$BQ_DATASET"
fi

echo "==> Granting dataset-level roles/bigquery.dataEditor to runtime SA"
bq --project_id="$PROJECT_ID" \
  add-iam-policy-binding "${PROJECT_ID}:${BQ_DATASET}" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/bigquery.dataEditor"

# =========================
# Discovery Engine (Vertex AI Search) runtime permission
# =========================
echo "==> Granting roles/discoveryengine.searchUser to runtime SA"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/discoveryengine.searchUser" \
  --project "$PROJECT_ID"

# Optional if enabling embeddings later
# gcloud projects add-iam-policy-binding "$PROJECT_ID" \
#   --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
#   --role="roles/aiplatform.user" \
#   --project "$PROJECT_ID"

# =========================
# Deployer permissions for CI (WIF + SA usage)
# =========================
echo "==> Allow Deployer SA to assign/use the Runtime SA (serviceAccountUser)"
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA_EMAIL" \
  --member="serviceAccount:${DEPLOYER_SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser" \
  --project "$PROJECT_ID"

if [[ "$GRANT_SERVICE_USAGE_ADMIN" == "true" ]]; then
  echo "==> Granting roles/serviceusage.serviceUsageAdmin to Deployer SA (optional)"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${DEPLOYER_SA_EMAIL}" \
    --role="roles/serviceusage.serviceUsageAdmin" \
    --project "$PROJECT_ID"
fi

# =========================
# Workload Identity Federation (GitLab OIDC) - optional
# =========================
if [[ "$ENABLE_WIF" == "true" ]]; then
  echo "==> Setting up Workload Identity Federation pool and provider (issuer: $GITLAB_ISSUER)"

  # Create pool (idempotent)
  gcloud iam workload-identity-pools describe "$WIF_POOL_ID" \
    --location="global" \
    --project="$PROJECT_ID" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create "$WIF_POOL_ID" \
    --location="global" \
    --project="$PROJECT_ID" \
    --display-name="GitLab CI Pool"

  # Create provider with GitLab OIDC claims mapping (idempotent)
  gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER_ID" \
    --workload-identity-pool="$WIF_POOL_ID" \
    --location="global" \
    --project="$PROJECT_ID" >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER_ID" \
    --workload-identity-pool="$WIF_POOL_ID" \
    --location="global" \
    --project="$PROJECT_ID" \
    --issuer-uri="$GITLAB_ISSUER" \
    --display-name="GitLab OIDC" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.project_path,attribute.ref=assertion.ref,attribute.namespace_id=assertion.namespace_id"

  echo "==> Binding Workload Identity User on Deployer SA for repo: $GITLAB_REPO"
  gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA_EMAIL" \
    --project="$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL_ID}/attribute.repository/${GITLAB_REPO}"
fi

cat <<EOF

Bootstrap complete.

Summary:
- Runtime SA:  $RUNTIME_SA_EMAIL
  - roles/bigquery.dataEditor (dataset: $BQ_DATASET)
  - roles/discoveryengine.searchUser (project)
  - [optional] roles/aiplatform.user (if enabling embeddings)

- Deployer SA: $DEPLOYER_SA_EMAIL
  - roles/iam.serviceAccountUser on runtime SA
  - [optional] roles/serviceusage.serviceUsageAdmin (if pipeline should enable services)
  - roles/iam.workloadIdentityUser bound to GitLab OIDC principalSet (for WIF)

- Required APIs (enabled):
  - bigquery.googleapis.com
  - discoveryengine.googleapis.com
  - iam.googleapis.com
  - iamcredentials.googleapis.com
  - serviceusage.googleapis.com
  - [optional] adkengine.googleapis.com (if available in your env)

Next steps:
1) In GitLab CI/CD Variables, set:
   - PROJECT_ID, REGION, ENGINE_NAME, RUNTIME_SA_EMAIL=${RUNTIME_SA_EMAIL}, GOOGLE_API_KEY
   - For WIF: GOOGLE_WORKLOAD_IDENTITY_PROVIDER=projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL_ID}/providers/${WIF_PROVIDER_ID}
             GOOGLE_SERVICE_ACCOUNT_EMAIL=${DEPLOYER_SA_EMAIL}
             PROJECT_NUMBER=${PROJECT_NUMBER}
   - Or for key-based auth: GOOGLE_APPLICATION_CREDENTIALS_JSON (masked JSON)

2) Create BigQuery table to match code expectations (if not created already):
   bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "
     CREATE TABLE IF NOT EXISTS \`${PROJECT_ID}.${BQ_DATASET}.validated_product_details\` (
       mirakl_product_id STRING,
       status STRING,
       confidence_score FLOAT64,
       validation_decision STRING,
       ai_comment STRING
     );"

3) Push to your repo; pipeline target is Agent Engine via 'adk engine deploy'.
EOF
