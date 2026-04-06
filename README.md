# POC Image Features — Product Validation Pipeline (Google ADK)

AI-powered multi-agent pipeline for validating product listings (images + attributes), assigning a confidence score, and writing structured results to BigQuery. Built with Google Agent Development Kit (ADK).

Key capabilities
- Compliance-aware validation: Looks up rules via Vertex AI Search and applies them to products.
- Parallel checks: Image validation and attribute validation run concurrently for speed.
- Confidence scoring: Aggregates findings into a single score (0–100) and a final decision (Approve/Reject).
- Analytics-ready output: Writes normalized rows to BigQuery with product identifiers and traceability metadata.
- Optional VGC duplicate insights: A VGC (Variant Group Code) duplicate check agent is available to detect cross-VGC submissions and intra-VGC size/colour duplicates using historical BigQuery data.

Repository structure
```
poc-image-features/
├── .env.example
├── pyproject.toml
├── requirements.txt
├── README.md
├── docs/
│   ├── business-user-guide.md
│   ├── product_validation_compliance.txt
│   └── technical_design_document.md
└── root_agent/
    ├── __init__.py
    ├── agent.py                          # Root Sequential + Parallel agent wiring
    ├── models.py                         # Pydantic models for BQ writes
    ├── sub_agents/
    │   ├── bigquery_write_agent.py       # Step 4: writes results to BigQuery
    │   ├── compliance_search_agent.py    # Step 1: fetches applicable rules via Vertex AI Search
    │   ├── confidence_score_agent.py     # Step 3: creates final score and decision
    │   ├── validate_attribute_agent.py   # Step 2B: attribute validation
    │   ├── validate_image_agent.py       # Step 2A: image validation + dimensions tool
    │   └── validate_vgc_agent.py         # Optional: VGC duplicate check (disabled by default)
    └── tools/
        ├── __init__.py
        ├── bigquery_tool.py              # BigQuery write + VGC fetch FunctionTools
        └── tools.py                      # get_image_dimensions tool
```

Pipeline workflow (as wired by default)
1) ComplianceSearchAgent
- Reads: none (uses Vertex AI Search)
- Writes: compliance_search_result

2) validation_parallel_agent
- Branch A: ImageValidatorAgent
  - Reads: products_data, compliance_search_result
  - Calls: get_image_dimensions_tool
  - Writes: image_validation_json
- Branch B: ValidateAttributeAgent
  - Reads: products_data, compliance_search_result
  - Writes: attribute_validation_json
- Optional Branch C (disabled by default): VGCDuplicateCheckAgent
  - Reads: products_data
  - Calls: vgc_fetch_tool (BigQuery comparison fetch)
  - Writes: vgc_validation_json

3) ConfidenceScoreAgent
- Reads: image_validation_json, attribute_validation_json
- Also injects: session_id (captured from the ADK session)
- Writes: validation_and_score_json

4) BigQueryWriteAgent
- Reads: validation_and_score_json
- Calls: bigquery_write_tool
- Writes: bigquery_result

What’s new vs earlier drafts
- Refined repository layout under root_agent/.
- BigQuery write path uses a typed ConfidenceScoreRecord with additional optional fields:
  - variant_group_code, brand, title, description, size, colour, seller, session_id
- Added vgc_fetch_tool for duplicate/variant comparisons and a VGCDuplicateCheckAgent (present but disabled by default).
- ConfidenceScoreAgent automatically stores the current session_id into state for traceability.

Setup

1) Authenticate with GCP
Use Application Default Credentials for local dev:
```
gcloud auth application-default login
```

2) Configure environment
Copy .env.example to .env and provide values:
```
GOOGLE_CLOUD_PROJECT=your-project-id
BQ_DATASET=product_validation
BQ_TABLE=validation_results
```
Optional but recommended:
- Ensure Vertex AI Search datastore is configured as referenced by ComplianceSearchAgent.

3) Install dependencies
Use editable install for local development:
```
pip install -e .
```

4) Create the BigQuery table
Suggested schema to match ConfidenceScoreRecord.to_bq_row():
```
CREATE TABLE `your-project.product_validation.validation_results` (
  mirakl_product_id   STRING,
  status              STRING,
  confidence_score    FLOAT64,
  validation_decision STRING,
  ai_comment          STRING,
  variant_group_code  STRING,
  brand               STRING,
  title               STRING,
  description         STRING,
  size                STRING,
  colour              STRING,
  seller              STRING,
  session_id          STRING
);
```
Notes:
- Additional columns are optional in code (nullable in schema), but recommended for analytics and VGC insights.

Running the agent

ADK CLI
```
adk run root_agent
```

ADK Web UI
```
adk web
```
Open http://localhost:8000 and select product_validation_pipeline.

Providing input (products_data)
- Paste a JSON list (or JSON string of a list) of product objects into the prompt.
- The pipeline’s before_agent_callback captures your last message as products_data.
- Example files in the repo (e.g., session_payload_min.json) can help you format input.

Result
- The pipeline produces:
  - image_validation_json
  - attribute_validation_json
  - validation_and_score_json
  - bigquery_result (status of the BigQuery insert)
- BigQuery will contain one row per product with confidence_score, decision, and traceability fields.

Enabling optional VGC duplicate check
By default, VGCDuplicateCheckAgent is present but not wired into the parallel step.
To enable:
1) In root_agent/agent.py, uncomment validate_vgc_agent in validation_parallel_agent.sub_agents.
2) (Optional) Update ConfidenceScoreAgent prompt to read vgc_validation_json if you want the score/decision to consider VGC findings.
3) Ensure your BigQuery table is populated with historical rows; vgc_fetch_tool queries your validation_results table to compare the incoming product against past entries.

Environment variables
- GOOGLE_CLOUD_PROJECT: GCP project for Vertex AI and BigQuery
- BQ_DATASET: BigQuery dataset (default recommended: product_validation)
- BQ_TABLE: BigQuery table (default recommended: validation_results)

Troubleshooting
- BigQuery insert failed: Verify GOOGLE_CLOUD_PROJECT/BQ_DATASET/BQ_TABLE and ADC credentials; confirm table exists with expected columns.
- Vertex AI Search errors: Ensure the datastore id in compliance_search_agent.py matches your environment.
- Empty results: Check that products_data was captured (the last message must be JSON or a JSON string).
- Local images/timeouts: get_image_dimensions_tool downloads images; ensure URLs are reachable from your environment.

License
This POC is intended for internal evaluation.
