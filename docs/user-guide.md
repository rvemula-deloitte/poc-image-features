# User Guide — Product Validation Pipeline (POC Image Features)

This guide explains how to set up, run, operate, and extend the Product Validation Pipeline built with Google ADK. It is intended for developers, operators, and CI/CD engineers.

- Repository: poc-image-features
- Core capabilities: compliance rules lookup, parallel image and attribute validation, confidence scoring, BigQuery write-back
- Runtime: Google ADK agents orchestrated by a SequentialAgent with a parallel step

What’s new in this structure
- Optional VGC duplicate insights branch (VGCDuplicateCheckAgent) present in code and disabled by default
- ConfidenceScoreAgent injects a session_id for traceability
- BigQuery rows support additional optional fields for analytics (variant_group_code, brand, title, description, size, colour, seller, session_id)

--------------------------------------------------------------------------------
1) What the pipeline does
--------------------------------------------------------------------------------

High-level flow:
1. Fetch compliance rules via Vertex AI Search (Discovery Engine)
2. Validate images (dimensions + visual checks via get_image_dimensions_tool)
3. Validate textual attributes and category/variant logic
4. Combine results into a per-product confidence score and final decision
5. Write results to BigQuery

Session state keys (written in sequence):
- compliance_search_result → image_validation_json, attribute_validation_json → validation_and_score_json → bigquery_result
- Optional (if enabled): vgc_validation_json (from VGC duplicate insights branch)

--------------------------------------------------------------------------------
2) Architecture at a glance
--------------------------------------------------------------------------------

Agent hierarchy:
- product_validation_pipeline (SequentialAgent — root)
  - ComplianceSearchAgent (LlmAgent — Step 1)
  - validation_parallel_agent (ParallelAgent — Step 2)
    - ImageValidatorAgent (LlmAgent — branch A; uses get_image_dimensions_tool)
    - ValidateAttributeAgent (LlmAgent — branch B)
    - VGCDuplicateCheckAgent (LlmAgent — optional, disabled by default; uses vgc_fetch_tool)
  - ConfidenceScoreAgent (LlmAgent — Step 3)
  - BigQueryWriteAgent (LlmAgent — Step 4; uses bigquery_write_tool)

Files of interest:
- root_agent/agent.py (pipeline orchestration and products_data capture)
- root_agent/sub_agents/*.py (each agent’s prompt + behavior)
  - validate_image_agent.py, validate_attribute_agent.py, confidence_score_agent.py
  - validate_vgc_agent.py (optional VGC duplicate insights)
  - bigquery_write_agent.py (BQ write step)
- root_agent/tools/tools.py (get_image_dimensions_tool)
- root_agent/tools/bigquery_tool.py (write_to_bigquery, fetch_vgc_comparison_data)
- docs/technical_design_document.md (in-depth architecture)
- docs/deployment-guide.md (CI/CD and Agent Engine deployment)

--------------------------------------------------------------------------------
3) Prerequisites
--------------------------------------------------------------------------------

- Python 3.10+
- GCP project with required APIs:
  - BigQuery, Discovery Engine (Vertex AI Search), IAM, IAM Credentials, Service Usage
- Credentials:
  - Recommended for local: Application Default Credentials (ADC)
    - gcloud auth application-default login
  - Or set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON
- Environment variables (required — no code defaults for dataset/table):
  - GOOGLE_CLOUD_PROJECT
  - BQ_DATASET (e.g., product_validation)
  - BQ_TABLE (e.g., validation_results)
  - GOOGLE_API_KEY (required for LlmAgents using Gemini via google-genai)
- BigQuery table
  - Must exist before writing; see example schema in README.md

--------------------------------------------------------------------------------
4) Local setup
--------------------------------------------------------------------------------

- Clone and open the repository
- (Optional) Create and activate a virtual environment
- Configure environment
  - Copy .env.example to .env and set:
    - GOOGLE_CLOUD_PROJECT
    - BQ_DATASET, BQ_TABLE
    - GOOGLE_API_KEY
    - (Optional) GOOGLE_APPLICATION_CREDENTIALS if not using ADC
  - Authenticate to GCP:
    gcloud auth application-default login
- Install dependencies
  - Editable install: pip install -e .
  - Or: pip install -r requirements.txt

--------------------------------------------------------------------------------
5) Running the pipeline
--------------------------------------------------------------------------------

Option A — ADK CLI
- Ensure pyproject.toml registers the app:
  [tool.adk]
  apps = [{ module = "root_agent", name = "root_agent" }]
- Start the app:
  adk run root_agent
- When prompted, supply your instruction and paste products_data (JSON list or a JSON string of a list).

Option B — ADK Web UI
- Start:
  adk web
- Navigate to http://localhost:8000
- Select product_validation_pipeline
- Provide products_data in the session (paste JSON into the UI as the last message)

Expected behavior on run:
1) ComplianceSearchAgent writes compliance_search_result
2) Parallel (Step 2):
   - ImageValidatorAgent reads products_data + compliance_search_result, calls get_image_dimensions_tool for each image, performs visual checks, writes image_validation_json
   - ValidateAttributeAgent reads products_data + compliance_search_result, validates textual attributes, writes attribute_validation_json
   - (Optional, if enabled) VGCDuplicateCheckAgent reads products_data, calls vgc_fetch_tool, writes vgc_validation_json
3) ConfidenceScoreAgent merges Step 2 outputs, injects session_id, writes validation_and_score_json
4) BigQueryWriteAgent calls write_to_bigquery with validation_and_score_json, writes to BQ, returns bigquery_result

Note on products_data capture:
- The root agent stores the last message text into state["products_data"]. Ensure your final message is the JSON list or a string that parses to a list.

--------------------------------------------------------------------------------
6) Products data format (input to the pipeline)
--------------------------------------------------------------------------------

Provide products_data as either:
- JSON list (preferred), or
- JSON string that parses to a list

Recommended fields used by agents:
- mirakl_product_id: unique product identifier
- data.main_image and data.alt_image_*: image objects with at least source or original_url
- Textual fields for attribute checks (title, description, brand, category)
- Useful for VGC insights (if enabled): data.style_number (variant_group_code), data.nrf_size (size), data.display_color (colour), sources[0].provider_code (seller)

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
    "data": {
      "style_number": "VGX-1001",
      "nrf_size": "M",
      "display_color": "Black",
      "main_image": { "source": "https://example.com/images/sku-12345-main.jpg" },
      "alt_image_1": { "source": "https://example.com/images/sku-12345-1.jpg" }
    },
    "sources": [
      { "provider_code": "SELLER-ABC" }
    ]
  }
]

Notes:
- ImageValidatorAgent prefers data.main_image.source and falls back to original_url; it inspects all data.alt_image_* keys.
- The attribute validator focuses on textual/structural checks; it does not perform image analysis.
- If you plan to enable VGC insights, include style_number, nrf_size, display_color, and sources[0].provider_code.

--------------------------------------------------------------------------------
7) Outputs and where to find them
--------------------------------------------------------------------------------

- compliance_search_result: JSON rules (step 1)
- image_validation_json: per-image checks with width/height/format, rule results, issues, compliance score
- attribute_validation_json: invalid attributes, category/variant/brand/vendor verdicts, rule results
- validation_and_score_json: per-product combined output (with session id)
  {
    "mirakl_product_id": "<id>",
    "status": "validated",
    "confidence_score": <0-100>,
    "validation_decision": "Approve" | "Reject",
    "ai_comment": "<reasoned explanation>",
    "session_id": "<uuid>"
  }
- bigquery_result: BigQuery insert status and details
  {
    "status": "success",
    "message": "Successfully inserted confidence score validation row(s)",
    "table": "PROJECT.DATASET.TABLE",
    "rows_inserted": 1
  }
- (Optional) vgc_validation_json: cross/intra-VGC findings if VGC branch is enabled

--------------------------------------------------------------------------------
8) Enabling the optional VGC duplicate insights branch
--------------------------------------------------------------------------------

- In root_agent/agent.py:
  - In validation_parallel_agent, uncomment validate_vgc_agent in sub_agents.
- In root_agent/sub_agents/confidence_score_agent.py:
  - (Optional) Extend the prompt/instruction to read and reason over vgc_validation_json if you want VGC findings to influence scoring/decision.
- Ensure your BigQuery table contains historical rows; vgc_fetch_tool compares incoming products with past entries.

--------------------------------------------------------------------------------
9) Common troubleshooting
--------------------------------------------------------------------------------

- BigQuery insert errors
  - Verify .env has GOOGLE_CLOUD_PROJECT, BQ_DATASET, BQ_TABLE
  - Confirm the table exists and schema matches required fields
  - Ensure ADC is active or GOOGLE_APPLICATION_CREDENTIALS is set
- Vertex AI Search (compliance) issues
  - Check the datastore id configured in ComplianceSearchAgent
  - Verify the service account or ADC identity has appropriate permissions
- Image fetch/parse failures
  - Confirm URLs are reachable from your environment
  - Check for timeouts, proxies, or unsupported image formats
- products_data not captured
  - Ensure the last message is a JSON list (or a JSON string → list)
  - Use provided sample files (e.g., session_payload_min.json) as a reference
- Invalid enums in final output
  - status must be "validated"
  - validation_decision must be "Approve" or "Reject"
- VGC insights empty/slow (if enabled)
  - Validate that historical rows exist in the target BQ table
  - Confirm env vars map to the correct dataset/table queried by vgc_fetch_tool

--------------------------------------------------------------------------------
10) CI/CD and Agent Engine deployment (summary)
--------------------------------------------------------------------------------

- See docs/deployment-guide.md for GitLab → ADK Engine deployment steps
- Key variables:
  - PROJECT_ID, REGION, ENGINE_NAME, RUNTIME_SA_EMAIL, GOOGLE_API_KEY
  - BQ_DATASET, BQ_TABLE, and optionally GOOGLE_CLOUD_LOCATION
- Authentication:
  - Recommended: Workload Identity Federation for CI/CD; otherwise use service account JSON (handle securely)
- Deploy command (example):
  - adk engine deploy --project ... --region ... --name ... --app root_agent --service-account=... --set-env-vars=...

--------------------------------------------------------------------------------
11) Extensibility and maintenance
--------------------------------------------------------------------------------

- Add new tools
  - Implement FunctionTools under root_agent/tools and attach to relevant LlmAgents
- Adjust prompts/rules
  - Update instructions in sub_agents/*.py; keep JSON output contracts stable
- BigQuery schema evolution
  - Prefer additive changes (new nullable columns); update README schema sample accordingly
- Optional features
  - VGC duplicate insights can be enabled per environment needs; consider UI/reporting impacts

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

Input (caller):
- products_data: JSON list (or JSON string -> list) of product objects

Outputs:
- compliance_search_result (JSON rules)
- image_validation_json (see ImageValidatorAgent)
- attribute_validation_json (see ValidateAttributeAgent)
- validation_and_score_json:
  {
    "mirakl_product_id": "<id>",
    "status": "validated",
    "confidence_score": <0-100>,
    "validation_decision": "Approve" | "Reject",
    "ai_comment": "<reasoned explanation>",
    "session_id": "<uuid>"
  }
- bigquery_result (tool result: success or error details)
- (Optional) vgc_validation_json (if optional branch is enabled)

For deeper technical details, see docs/technical_design_document.md.
