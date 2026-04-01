# POC Image Features — Product Validation Pipeline

AI agent built with Google ADK that validates marketplace products using:
- Compliance rule retrieval via Vertex AI Search (Discovery Engine)
- Image validation (vision + dimensions)
- Attribute validation (textual/structural, PR/Legal wording, brand/category/variants)
- Confidence scoring
- BigQuery write-back

The pipeline is orchestrated by a root SequentialAgent with a parallel step to validate images and attributes concurrently.

--------------------------------------------------------------------------------
Project Structure
--------------------------------------------------------------------------------

```
poc-image-features/
├── docs/
│   ├── deployment-guide.md               # CI/CD to Agent Engine, IAM, WIF
│   ├── technical_design_document.md      # Detailed architecture and data flow
│   └── user-guide.md                     # End-to-end setup/run/operate playbook
├── root_agent/
│   ├── agent.py                          # Orchestrates the full pipeline
│   ├── models.py                         # Optional pydantic model(s)
│   ├── sub_agents/
│   │   ├── compliance_search_agent.py    # Step 1: Vertex AI Search → compliance_search_result
│   │   ├── validate_image_agent.py       # Step 2A: Image checks → image_validation_json
│   │   ├── validate_attribute_agent.py   # Step 2B: Attribute checks → attribute_validation_json
│   │   ├── confidence_score_agent.py     # Step 3: Merge/score → validation_and_score_json
│   │   └── bigquery_write_agent.py       # Step 4: Write BQ → bigquery_result
│   └── tools/
│       ├── bigquery_tool.py              # FunctionTool: write_to_bigquery(...)
│       └── tools.py                      # FunctionTool: get_image_dimensions(...)
├── scripts/
│   ├── bootstrap_gcp.sh
│   ├── deploy_agent_engine.sh
│   └── deploy.sh
├── pyproject.toml                        # Registers ADK app
├── requirements.txt
├── .env.example
├── .gitlab-ci.yml
├── Dockerfile
└── README.md
```

--------------------------------------------------------------------------------
Pipeline Workflow (Active)
--------------------------------------------------------------------------------

Inputs: Caller provides `products_data` in session state (JSON list or JSON-stringified list).

1) ComplianceSearchAgent (gemini-2.5-flash)
- Reads: none (uses Vertex Ai Search)
- Writes: `compliance_search_result`

2) validation_parallel_agent (ParallelAgent)
- 2A) ImageValidatorAgent
  - Reads: `products_data`, `compliance_search_result`
  - Tool: `get_image_dimensions_tool`
  - Writes: `image_validation_json`
- 2B) ValidateAttributeAgent
  - Reads: `products_data`, `compliance_search_result`
  - Writes: `attribute_validation_json`

3) ConfidenceScoreAgent
- Reads: `image_validation_json`, `attribute_validation_json`
- Writes: `validation_and_score_json`  
  - Enum constraints:
    - `status`: must be "validated"
    - `validation_decision`: "Approve" | "Reject"

4) BigQueryWriteAgent
- Reads: `validation_and_score_json`
- Tool: `write_to_bigquery`
- Writes: `bigquery_result`

--------------------------------------------------------------------------------
Setup
--------------------------------------------------------------------------------

1) Authenticate with GCP (ADC)
```
gcloud auth application-default login
```

2) Configure environment
- Copy `.env.example` → `.env` and set:
```
GOOGLE_CLOUD_PROJECT=your-project-id
BQ_DATASET=your_dataset                 # e.g., poc_product_intake
BQ_TABLE=your_table                     # e.g., validated_product_details
GOOGLE_API_KEY=your-google-api-key
# Optional:
# GOOGLE_APPLICATION_CREDENTIALS=path/to/sa.json
# GOOGLE_CLOUD_LOCATION=us
```

3) Install dependencies
- Editable install:
```
pip install -e .
```
- Or:
```
pip install -r requirements.txt
```

4) Create the BigQuery table (match your dataset/table)
```
CREATE TABLE IF NOT EXISTS `PROJECT_ID.DATASET.TABLE` (
  mirakl_product_id STRING,
  status STRING,                -- must be "validated"
  confidence_score FLOAT64,
  validation_decision STRING,   -- "Approve" | "Reject"
  ai_comment STRING
);
```
Note: If you do not set `BQ_DATASET`/`BQ_TABLE`, `root_agent/tools/bigquery_tool.py` defaults to `product_validation.validation_results`.

--------------------------------------------------------------------------------
Running the Agent
--------------------------------------------------------------------------------

ADK CLI
```
adk run root_agent
```
- The ADK app is registered in `pyproject.toml`:
```
[tool.adk]
apps = [{ module = "root_agent", name = "root_agent" }]
```
- Provide an instruction and ensure `products_data` is present in session state (paste in UI or prompt).

ADK Web UI
```
adk web
```
- Open http://localhost:8000
- Select `product_validation_pipeline`
- Add `products_data` to the session and run

Minimal `products_data` example:
```json
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
    "attributes": { "prop_65": "No", "choking_hazard": "No" },
    "data": {
      "main_image": { "source": "https://example.com/images/sku-12345-main.jpg" },
      "alt_image_1": { "source": "https://example.com/images/sku-12345-1.jpg" }
    }
  }
]
```

--------------------------------------------------------------------------------
Outputs
--------------------------------------------------------------------------------

- `compliance_search_result` — rules from Vertex AI Search
- `image_validation_json` — per-image width/height/format, rule checks, issues
- `attribute_validation_json` — invalid attributes, category/variant/brand/vendor checks
- `validation_and_score_json` — per-product:
  ```
  {
    "mirakl_product_id": "<id>",
    "status": "validated",
    "confidence_score": <0-100>,
    "validation_decision": "Approve" | "Reject",
    "ai_comment": "<reasoned explanation>"
  }
  ```
- `bigquery_result` — BigQuery insert outcome
  ```
  { "status": "success", "message": "...", "table": "PROJECT.DATASET.TABLE", "rows_inserted": 1 }
  ```

--------------------------------------------------------------------------------
Troubleshooting
--------------------------------------------------------------------------------

- BigQuery permission errors
  - Ensure runtime identity has dataset-level `roles/bigquery.dataEditor`
  - Verify `GOOGLE_CLOUD_PROJECT`, `BQ_DATASET`, `BQ_TABLE`
- BigQuery insert fails
  - Confirm table exists and schema matches expected columns
  - Validate ADC or service account credentials
- Image download fails
  - Ensure URLs are public/reachable from your runtime (egress/firewall)
- Enum mismatches
  - `status` must be "validated"; `validation_decision` must be "Approve" or "Reject"

--------------------------------------------------------------------------------
CI/CD and Agent Engine (Summary)
--------------------------------------------------------------------------------

- Use `docs/deployment-guide.md`:
  - GitLab CI variables: `PROJECT_ID`, `REGION`, `ENGINE_NAME`, `RUNTIME_SA_EMAIL`, `GOOGLE_API_KEY`
  - Optional: `BQ_DATASET`, `BQ_TABLE`, `GOOGLE_CLOUD_LOCATION`
  - Deploy via ADK CLI:
    ```
    adk engine deploy --project ... --region ... --name ... \
      --app root_agent --service-account=... \
      --set-env-vars=GOOGLE_CLOUD_PROJECT=...,BQ_DATASET=...,BQ_TABLE=...,GOOGLE_API_KEY=...
    ```

--------------------------------------------------------------------------------
Roadmap
--------------------------------------------------------------------------------

- Embedding-based image validation (Vertex AI MultiModal Embedding)
  - Mentioned in docs as a potential enhancement
  - Not currently implemented in this repo (no `validate_image_embedding_agent.py` nor `embedding_validation_tool.py`)

--------------------------------------------------------------------------------
References
--------------------------------------------------------------------------------

- User Guide (full playbook): `docs/user-guide.md`
- Technical Design: `docs/technical_design_document.md`
- Deployment Guide: `docs/deployment-guide.md`
