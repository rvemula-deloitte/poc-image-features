# User Guide Playbook — POC Image Features (Product Validation Pipeline)

This playbook explains how to set up, run, operate, and extend the Product Validation Pipeline built with Google ADK. It is intended for developers, operators, and CI/CD engineers.

- Source repo: poc-image-features
- Core domains: Image validation (vision + dimensions), attribute validation (textual/structural), compliance rule retrieval, confidence scoring, BigQuery write-back
- Runtime: Google ADK Agents orchestrated by a SequentialAgent with a parallel step

--------------------------------------------------------------------------------
1) What the pipeline does
--------------------------------------------------------------------------------

High-level flow:
1. Fetch compliance rules via Vertex AI Search (Discovery Engine)
2. Validate images (vision + dimension metadata via HTTP fetch)
3. Validate textual attributes and category/variant logic
4. Combine results into a per-product confidence score and final decision
5. Write results to BigQuery

Session state keys (written in sequence):
- compliance_search_result → image_validation_json, attribute_validation_json → validation_and_score_json → bigquery_result

--------------------------------------------------------------------------------
2) Architecture at a glance
--------------------------------------------------------------------------------

Agent hierarchy:
- product_validation_pipeline (SequentialAgent — root)
  - ComplianceSearchAgent (LlmAgent — Step 1)
  - validation_parallel_agent (ParallelAgent — Step 2)
    - ImageValidatorAgent (LlmAgent — branch A; uses get_image_dimensions_tool)
    - ValidateAttributeAgent (LlmAgent — branch B)
  - ConfidenceScoreAgent (LlmAgent — Step 3)
  - BigQueryWriteAgent (LlmAgent — Step 4; uses bigquery_write_tool)

Files of interest:
- root_agent/agent.py (pipeline orchestration)
- root_agent/sub_agents/*.py (each agent’s prompt + behavior)
- root_agent/tools/tools.py (get_image_dimensions_tool)
- root_agent/tools/bigquery_tool.py (write_to_bigquery as FunctionTool)
- docs/technical_design_document.md (in-depth architecture)
- docs/deployment-guide.md (CI/CD and Agent Engine deployment)

--------------------------------------------------------------------------------
3) Prerequisites
--------------------------------------------------------------------------------

- Python 3.10+
- GCP project with:
  - APIs enabled: BigQuery, Discovery Engine, IAM, IAM Credentials, Service Usage
  - Vertex AI Search datastore configured for compliance content (see ComplianceSearchAgent)
- Credentials:
  - Application Default Credentials: gcloud auth application-default login
  - Or a service account JSON via GOOGLE_APPLICATION_CREDENTIALS
- Environment variables (see .env.example):
  - GOOGLE_CLOUD_PROJECT (required)
  - BQ_DATASET, BQ_TABLE (required to match your target table)
  - GOOGLE_API_KEY (required for LLM calls inside LlmAgents)
  - Optional: GOOGLE_CLOUD_LOCATION (default us)

Note on BigQuery schema:
- The tool writes a flat row:
  - mirakl_product_id (STRING)
  - status (STRING; must be "validated")
  - confidence_score (FLOAT64)
  - validation_decision (STRING; "Approve" or "Reject")
  - ai_comment (STRING)

Example DDL (align with your env vars):
CREATE TABLE IF NOT EXISTS `PROJECT_ID.poc_product_intake.validated_product_details` (
  mirakl_product_id STRING,
  status STRING,
  confidence_score FLOAT64,
  validation_decision STRING,
  ai_comment STRING
);

Defaults in code if BQ_DATASET/BQ_TABLE are not set:
- dataset: product_validation
- table: validation_results
Set env vars to override and match your desired target.

--------------------------------------------------------------------------------
4) Local setup
--------------------------------------------------------------------------------

- Clone and open the repository
- Create a virtual environment (optional but recommended)
- Configure environment
  - Copy .env.example to .env and set:
    - GOOGLE_CLOUD_PROJECT
    - GOOGLE_APPLICATION_CREDENTIALS (if not using ADC)
    - BQ_DATASET, BQ_TABLE
    - GOOGLE_API_KEY
  - Authenticate to GCP:
    gcloud auth application-default login
- Install dependencies
  - Editable install: pip install -e .
  - Or from requirements: pip install -r requirements.txt

--------------------------------------------------------------------------------
5) Running the pipeline
--------------------------------------------------------------------------------

Option A — ADK CLI
- Ensure pyproject.toml registers the app:
  [tool.adk]
  apps = [{ module = "root_agent", name = "root_agent" }]
- Start the app:
  adk run root_agent
- When prompted, supply your instruction and the products_data (see Section 6 for a sample).

Option B — ADK Web UI
- Start:
  adk web
- Navigate to http://localhost:8000
- Select product_validation_pipeline
- Provide products_data in the session (paste JSON into the UI or prompt as instructed)

Expected behavior on run:
1) ComplianceSearchAgent writes compliance_search_result (rules pulled via Vertex Ai Search)
2) Parallel:
   - ImageValidatorAgent reads products_data + compliance_search_result, calls get_image_dimensions_tool for each image, performs visual checks, writes image_validation_json
   - ValidateAttributeAgent reads products_data + compliance_search_result, validates textual attributes, writes attribute_validation_json
3) ConfidenceScoreAgent merges Step 2 outputs, writes validation_and_score_json
4) BigQueryWriteAgent calls write_to_bigquery with validation_and_score_json, writes to BQ, returns bigquery_result

--------------------------------------------------------------------------------
6) Products data format (input to the pipeline)
--------------------------------------------------------------------------------

Provide products_data as either:
- JSON list (preferred), or
- JSON string that parses to a list

Minimum fields used by agents:
- mirakl_product_id: unique product identifier
- data.main_image and data.alt_image_*: image objects with at least source or original_url
- Textual fields to validate: title/description/features/brand/category data helpful for attribute checks

Example minimal products_data:
[
  {
    "mirakl_product_id": "SKU-12345",
    "brand": "Contoso",
    "title": "Men's Cotton Crew T-Shirt",
    "description": "Soft cotton crew neck T-shirt.",
    "category_hierarchy": { "p1": "Apparel", "p2": "Tops", "p3": "T-Shirts" },
    "variants": [
      { "color": "Black", "size": "M", "sku": "SKU-12345-BLK-M" },
      { "color": "Black", "size": "L", "sku": "SKU-12345-BLK-L" }
    ],
    "attributes": {
      "prop_65": "No",
      "choking_hazard": "No"
    },
    "data": {
      "main_image": { "source": "https://example.com/images/sku-12345-main.jpg" },
      "alt_image_1": { "source": "https://example.com/images/sku-12345-1.jpg" }
    }
  }
]

Notes:
- ImageValidatorAgent will read data.main_image and all keys beginning with data.alt_image_
- It prefers the source URL and falls back to original_url
- Attribute validation focuses on textual/structural checks; it does not do image checks

--------------------------------------------------------------------------------
7) Outputs and where to find them
--------------------------------------------------------------------------------

- compliance_search_result: JSON rules from Vertex AI Search (step 1)
- image_validation_json: per-image checks with width/height/format, rule results, issues, compliance score
- attribute_validation_json: invalid attributes, category/variant/brand/vendor verdicts, rule results
- validation_and_score_json: per-product combined confidence_score (0–100), status ("validated"), validation_decision ("Approve" | "Reject"), ai_comment (reasoning)
- bigquery_result: BigQuery insert result; success example:
  {
    "status": "success",
    "message": "Successfully inserted confidence score validation row(s)",
    "table": "PROJECT_ID.DATASET.TABLE",
    "rows_inserted": 1
  }

--------------------------------------------------------------------------------
8) Common troubleshooting
--------------------------------------------------------------------------------

- BigQuery 403 / permission denied
  - Ensure the runtime identity has dataset-level roles/bigquery.dataEditor
  - Confirm GOOGLE_CLOUD_PROJECT, BQ_DATASET, BQ_TABLE are set on the process
- “Failed to write to BigQuery: …”
  - Validate table existence and schema columns match the tool’s expected row fields
  - Ensure Application Default Credentials or service account credentials are in effect
- Image fetch failures (Download failed / Could not read image)
  - Verify image URLs are public and reachable from runtime
  - Check corporate proxy or egress controls
- Missing products_data or bad shape
  - Provide a list (array) of product objects or a string that parses to such a list
  - Include mirakl_product_id and data.main_image/alt_image_* entries with URLs
- Invalid enums in final output (status/decision)
  - The scoring agent enforces exact strings:
    - status: "validated"
    - validation_decision: "Approve" or "Reject"

--------------------------------------------------------------------------------
9) CI/CD and Agent Engine deployment (summary)
--------------------------------------------------------------------------------

- See docs/deployment-guide.md for end-to-end GitLab → ADK Engine deployment
- Key variables:
  - PROJECT_ID, REGION, ENGINE_NAME, RUNTIME_SA_EMAIL, GOOGLE_API_KEY
  - Optional: BQ_DATASET, BQ_TABLE, GOOGLE_CLOUD_LOCATION
- Authentication:
  - Recommended: Workload Identity Federation (OIDC → short-lived credentials)
  - Fallback: Service account key via GOOGLE_APPLICATION_CREDENTIALS_JSON
- Deploy command (wrapped in scripts/deploy_agent_engine.sh):
  - adk engine deploy --project ... --region ... --name ... --app root_agent --service-account=... --set-env-vars=...

--------------------------------------------------------------------------------
10) Extensibility and maintenance
--------------------------------------------------------------------------------

- Add new tools
  - Create FunctionTool wrappers in root_agent/tools and inject into relevant LlmAgents
- Modify prompts/rules
  - Update instructions in sub_agents/*.py; keep JSON output contracts stable
- Update BigQuery schema
  - Adjust root_agent/tools/bigquery_tool.py and redeploy; coordinate DDL changes
- Embedding-based image validation (roadmap)
  - README mentions a potential validate_image_embedding_agent and embedding_validation_tool; these are not present in the current codebase
  - To add: implement a Vertex AI MultiModal Embedding tool + agent branch; write combined results into ConfidenceScoreAgent

--------------------------------------------------------------------------------
11) Quick verification checklist
--------------------------------------------------------------------------------

- Local run sanity:
  - pip install -e .
  - gcloud auth application-default login
  - Prepare .env with GOOGLE_CLOUD_PROJECT, BQ_DATASET, BQ_TABLE, GOOGLE_API_KEY
  - adk run root_agent
  - Provide sample products_data JSON
  - Confirm bigquery_result.status == "success"

- Operational checks:
  - API enablement: BigQuery, Discovery Engine, IAM/IAM Credentials, Service Usage
  - Runtime SA permissions: dataset roles/bigquery.dataEditor; discoveryengine.searchUser
  - Outbound HTTP egress allowed

--------------------------------------------------------------------------------
Appendix A: Useful commands
--------------------------------------------------------------------------------

- Authenticate ADC: gcloud auth application-default login
- Run local: adk run root_agent
- Start web UI: adk web (open http://localhost:8000)
- Editable install: pip install -e .
- Requirements install: pip install -r requirements.txt

--------------------------------------------------------------------------------
Appendix B: Data contracts (concise)
--------------------------------------------------------------------------------

- Input (caller):
  - products_data: JSON list (or JSON string -> list) of product objects
- Outputs:
  - compliance_search_result (JSON rules)
  - image_validation_json (see ImageValidatorAgent)
  - attribute_validation_json (see ValidateAttributeAgent)
  - validation_and_score_json:
    {
      "mirakl_product_id": "<id>",
      "status": "validated",
      "confidence_score": <0-100>,
      "validation_decision": "Approve" | "Reject",
      "ai_comment": "<reasoned explanation>"
    }
  - bigquery_result (tool result: success or error details)

For deep technical details, see docs/technical_design_document.md.
