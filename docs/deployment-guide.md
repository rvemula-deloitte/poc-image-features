# Deployment Guide: GitLab CI/CD to GCP Agent Engine (ADK)

This repository contains an AI agent built with Google ADK that:
- Searches compliance rules using Vertex AI Search (Discovery Engine)
- Validates product images (via Gemini Vision with inline URIs)
- Computes confidence scores
- Writes results to BigQuery

This guide defines:
- ADK Agent Engine deployment using the ADK CLI (no container build)
- GitLab CI/CD to authenticate (WIF or SA key), install ADK CLI, and run `adk engine deploy`
- Service Accounts and granular IAM for runtime and CI deploy
- Environment/configuration and required GCP APIs
- Bootstrap commands to provision infra (scripts/bootstrap_gcp.sh)

------------------------------------------------------------------------------
1) Codebase analysis → runtime requirements
------------------------------------------------------------------------------

Entrypoint and registration:
- ADK app is declared in `pyproject.toml`:
  [tool.adk]
  apps = [{ module = "root_agent", name = "root_agent" }]

- You deploy this app to Agent Engine with: `adk engine deploy --app root_agent ...`

Services used by code:
- BigQuery: `root_agent/tools/bigquery_tool.py`
  - Expects env vars: GOOGLE_CLOUD_PROJECT, BQ_DATASET, BQ_TABLE
  - Performs JSON row inserts via `client.insert_rows_json(table_id, rows)`

- Vertex AI Search (Discovery Engine): `root_agent/sub_agents/compliance_search_agent.py`
  - Uses `VertexAiSearchTool` with a fixed `DATASTORE_ID` under location us
  - Requires discoveryengine.googleapis.com and IAM role `roles/discoveryengine.searchUser` for runtime SA

- Google Generative AI API (API key based) used by LLM agents (model="gemini-2.5-flash")
  - Requires `GOOGLE_API_KEY` (passed as env var to the Engine)
  - Not gated by GCP IAM (separate API key usage)

- HTTP egress: Image downloads via requests (`root_agent/tools/tools.py`)
  - Ensure your runtime environment allows outbound internet access

Environment variables (set on Engine):
- GOOGLE_CLOUD_PROJECT (required)
- BQ_DATASET, BQ_TABLE (required; see BigQuery DDL below)
- GOOGLE_CLOUD_LOCATION (default us; used for region alignment)
- GOOGLE_API_KEY (required; Generative AI API key)

Note on BigQuery schema:
- Use this schema to match inserts from `write_to_bigquery()`:

  CREATE TABLE `PROJECT_ID.poc_product_intake.validated_product_details` (
    mirakl_product_id STRING,
    status STRING,
    confidence_score FLOAT64,
    validation_decision STRING,
    ai_comment STRING
  );

Replace dataset/table names if you use different BQ_DATASET/BQ_TABLE.

------------------------------------------------------------------------------
2) ADK Agent Engine deployment (no container build)
------------------------------------------------------------------------------

- ADK CLI packages and deploys the app registered in `pyproject.toml`
- The pipeline invokes: `adk engine deploy --project --region --name --app root_agent`
- Files added:
  - `scripts/deploy_agent_engine.sh` (wraps the ADK CLI call)
  - `.gitlab-ci.yml` (auth + install ADK CLI + run deploy)
  - `scripts/bootstrap_gcp.sh` (infra provisioning helper for SA/IAM/APIs/WIF)

------------------------------------------------------------------------------
3) CI/CD Pipeline (GitLab → ADK CLI → Agent Engine)
------------------------------------------------------------------------------

High-level flow:
1. Authenticate to Google Cloud:
   - Preferred: Workload Identity Federation (OIDC from GitLab → impersonate deployer SA)
   - Fallback: Service account JSON key (masked/protected variable)

2. Enable required APIs (idempotent)
   - bigquery, discoveryengine, iam, iamcredentials, serviceusage
   - Agent Engine API (if available): adkengine.googleapis.com (ignored if not found)

3. Install ADK CLI in the runner:
   - `pip3 install google-adk>=0.3.0`

4. Deploy to Agent Engine:
   - `scripts/deploy_agent_engine.sh` runs `adk engine deploy --app root_agent ...`
   - Pass env vars required by the app: GOOGLE_CLOUD_PROJECT, BQ_DATASET, BQ_TABLE, GOOGLE_CLOUD_LOCATION, GOOGLE_API_KEY

File changed/added:
- `.gitlab-ci.yml`
- `scripts/deploy_agent_engine.sh`

GitLab CI/CD variables to set (masked/protected as applicable):
- PROJECT_ID: your GCP project ID
- REGION: e.g., us-central1
- ENGINE_NAME: e.g., product-validation-engine
- RUNTIME_SA_EMAIL: runtime service account email used by Engine
- GOOGLE_API_KEY: Generative AI API key
- Optional (override defaults):
  - BQ_DATASET (default poc_product_intake), BQ_TABLE (default validated_product_details), GOOGLE_CLOUD_LOCATION (default us)

Authentication options:
- Workload Identity Federation (recommended)
  - GOOGLE_WORKLOAD_IDENTITY_PROVIDER: resource name of provider
  - GOOGLE_SERVICE_ACCOUNT_EMAIL: deployer SA email to impersonate
  - PROJECT_NUMBER: your project number
- Key-based fallback:
  - GOOGLE_APPLICATION_CREDENTIALS_JSON: entire SA JSON key as masked variable

------------------------------------------------------------------------------
4) Service Accounts and IAM (least privilege)
------------------------------------------------------------------------------

A) Runtime Service Account (Agent Engine)
- Example: ae-product-validation-runtime@PROJECT_ID.iam.gserviceaccount.com
- Purpose: Used by Agent Engine runtime to call APIs

Grant:
- BigQuery dataset-level:
  - roles/bigquery.dataEditor on dataset BQ_DATASET
    - Allows streaming inserts used by `insert_rows_json`
- Discovery Engine:
  - roles/discoveryengine.searchUser on the project (or scoped as needed)
- Optional if enabling Vertex AI embeddings later:
  - roles/aiplatform.user on the project/region used
- Optional if storing GOOGLE_API_KEY in Secret Manager (instead of CI vars):
  - roles/secretmanager.secretAccessor on the secret

B) Deployer Service Account (GitLab CI)
- Example: gitlab-deployer@PROJECT_ID.iam.gserviceaccount.com
- Purpose: Impersonated by GitLab pipeline via WIF or used via key to:
  - Execute `adk engine deploy` on your behalf and attach the runtime SA

Grant:
- roles/iam.serviceAccountUser on the runtime SA
  - To assign runtime SA to the Engine
- roles/iam.workloadIdentityUser binding (WIF only)
  - On the Deployer SA with principals from your GitLab repo OIDC provider
- Optional (only if pipeline should enable services):
  - roles/serviceusage.serviceUsageAdmin (or pre-enable services to avoid this broader role)

C) Why no Artifact Registry/Cloud Run roles?
- This workflow deploys directly to Agent Engine using ADK CLI; no container build is required

------------------------------------------------------------------------------
5) Workload Identity Federation (keyless, recommended)
------------------------------------------------------------------------------

Concept:
- GitLab runner obtains an OIDC token
- Google IAM Workload Identity Federation exchanges that token for short-lived credentials to impersonate the deployer SA

Provisioning (see scripts/bootstrap_gcp.sh):
- Create a pool/provider for issuer https://gitlab.com
- Bind roles/iam.workloadIdentityUser on the deployer SA to principals from that pool/provider (scoped to your repo)

Then in CI:
- gcloud iam workload-identity-pools create-cred-config ... --service-account="$GOOGLE_SERVICE_ACCOUNT_EMAIL" --output-file=/tmp/wif-cred.json
- gcloud auth login --cred-file=/tmp/wif-cred.json

------------------------------------------------------------------------------
6) scripts/deploy_agent_engine.sh
------------------------------------------------------------------------------

- Validates required env vars
- Runs `adk engine deploy`:
  - --project, --region, --name
  - --app root_agent
  - --service-account=RUNTIME_SA_EMAIL
  - --set-env-vars (GOOGLE_CLOUD_PROJECT, BQ_DATASET, BQ_TABLE, GOOGLE_CLOUD_LOCATION, GOOGLE_API_KEY)

------------------------------------------------------------------------------
7) Required APIs
------------------------------------------------------------------------------

- bigquery.googleapis.com
- discoveryengine.googleapis.com
- iam.googleapis.com
- iamcredentials.googleapis.com
- serviceusage.googleapis.com
- [optional] adkengine.googleapis.com (if available)

------------------------------------------------------------------------------
8) BigQuery provisioning (DDL)
------------------------------------------------------------------------------

Dataset (if not present):
- BQ_DATASET: poc_product_intake (from `.env.example`)

Table (must match code’s expected fields):
- BQ_TABLE: validated_product_details

SQL (update project/dataset/table as needed):
CREATE TABLE IF NOT EXISTS `PROJECT_ID.poc_product_intake.validated_product_details` (
  mirakl_product_id STRING,
  status STRING,
  confidence_score FLOAT64,
  validation_decision STRING,
  ai_comment STRING
);

------------------------------------------------------------------------------
9) Concepts used and why
------------------------------------------------------------------------------

- ADK Agent Engine: Managed execution for ADK apps; `adk engine deploy` packages and deploys from source (no container)
- Workload Identity Federation: Keyless CI auth (no long-lived keys), least-privileged SA impersonation
- Least-privilege IAM:
  - Separate deployer and runtime SAs
  - Dataset-level BigQuery permissions for runtime
  - Resource-specific roles (Discovery Engine search only)
- Config via environment variables: 12-factor approach; GOOGLE_API_KEY provided via CI variables (or Secret Manager if desired)
- Idempotent API enabling: Safe to re-run on any branch

------------------------------------------------------------------------------
10) How to run
------------------------------------------------------------------------------

1) Bootstrap (once per project):
   - Edit variables and run `scripts/bootstrap_gcp.sh`

2) In GitLab → Settings → CI/CD → Variables:
   - PROJECT_ID, REGION, ENGINE_NAME, RUNTIME_SA_EMAIL, GOOGLE_API_KEY
   - For WIF: GOOGLE_WORKLOAD_IDENTITY_PROVIDER, GOOGLE_SERVICE_ACCOUNT_EMAIL, PROJECT_NUMBER
   - Or for key-based: GOOGLE_APPLICATION_CREDENTIALS_JSON

3) Push to your repo; the pipeline will:
   - Authenticate (WIF or key)
   - Ensure APIs
   - Install ADK CLI
   - Deploy the ADK app to Agent Engine with runtime SA and env vars

4) Operate the Engine using ADK tooling/console as applicable for your environment

------------------------------------------------------------------------------
Appendix: Files added/updated by this guide
------------------------------------------------------------------------------
- .gitlab-ci.yml (Agent Engine deployment)
- scripts/deploy_agent_engine.sh
- scripts/bootstrap_gcp.sh
- pyproject.toml (already registers app for ADK)
