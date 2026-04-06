# POC Image Features - Product Validation Pipeline

AI-powered multi-agent product validation pipeline built on Google Agent Development Kit (ADK). The pipeline validates Mirakl product listings against Kohl's compliance rules, produces a confidence score with an Approve/Reject decision, and writes results to BigQuery.

## Project Structure

```
poc-image-features/
├── root_agent/
│   ├── agent.py               # Root SequentialAgent and ParallelAgent orchestration
│   ├── models.py              # Pydantic models: ConfidenceScoreRecord, ValidationRecord
│   ├── sub_agents/
│   │   ├── compliance_search_agent.py   # Step 1: Fetch compliance rules via Vertex AI Search
│   │   ├── validate_image_agent.py      # Step 2A: Gemini vision image validation
│   │   ├── validate_attribute_agent.py  # Step 2B: Attribute, PR/Legal, spelling validation
│   │   ├── validate_vgc_agent.py        # Optional: VGC duplicate detection (currently disabled)
│   │   ├── confidence_score_agent.py    # Step 3: Confidence scoring + Approve/Reject decision
│   │   └── bigquery_write_agent.py      # Step 4: Write validation record to BigQuery
│   └── tools/
│       ├── tools.py           # get_image_dimensions_tool (PIL-based)
│       └── bigquery_tool.py   # bigquery_write_tool + vgc_fetch_tool
├── docs/
│   ├── technical_design_document.md
│   └── product_validation_compliance.txt
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Pipeline Workflow

```
User message (JSON product list)
  │
  ▼  before_agent_callback: stores message → state[products_data]
  │
Step 1 — ComplianceSearchAgent
  │  Reads product_category, resolves P1/P2/P3
  │  Calls VertexAiSearchTool (parallel queries for image rules, attributes,
  │         PR/Legal, variants, brands, vendor restrictions)
  ▼  → compliance_search_result
  │
Step 2 — validation_parallel_agent (runs A and B concurrently)
  ├─ A: ImageValidatorAgent
  │     Injects images as Part.from_uri via before_model_callback
  │     Calls get_image_dimensions_tool for all images in parallel
  │     Visual compliance check: dimensions, backgrounds, watermarks,
  │       brand consistency, spelling in images, PR/Legal text in images
  │     → image_validation_json
  │
  └─ B: ValidateAttributeAgent
        Validates: required attributes, category hierarchy (P1/P2/P3),
          variants, brand consistency, vendor agreements,
          PR/Legal requirements, spelling correctness
        → attribute_validation_json
  │
  # C: VGCDuplicateCheckAgent (implemented, currently disabled)
  #    Calls fetch_vgc_comparison_data → cross-VGC and intra-VGC checks
  #    → vgc_validation_json
  │
Step 3 — ConfidenceScoreAgent
  │  before_agent_callback captures ADK session_id → state[session_id]
  │  Holistic scoring (0-100) — no fixed formula
  │  Three-tier decision:
  │    Accepted        → Approve
  │    Temp Rejection  → Reject  (correctable, seller resubmits)
  │    Perm Rejection  → Reject  (uncorrectable, delete & re-upload)
  ▼  → validation_and_score_json (includes session_id)
  │
Step 4 — BigQueryWriteAgent
  │  Assembles full record: score + decision + identity fields
  │  (variant_group_code, brand, title, description, size, colour, seller)
  │  Calls bigquery_write_tool
  ▼  → bigquery_result
```

## Setup

### 1. Authenticate with GCP

```powershell
gcloud auth application-default login
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
BQ_DATASET=product_validation
BQ_TABLE=validation_results
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Create BigQuery Table

The table must include all columns written by the pipeline:

```sql
CREATE TABLE `your-project.product_validation.validation_results` (
  mirakl_product_id    STRING,
  status               STRING,
  confidence_score     FLOAT64,
  validation_decision  STRING,
  ai_comment           STRING,
  variant_group_code   STRING,
  brand                STRING,
  title                STRING,
  description          STRING,
  size                 STRING,
  colour               STRING,
  seller               STRING,
  session_id           STRING
);
```

## Running the Agent

### Using ADK CLI

```bash
adk run root_agent
```

### Using ADK Web UI

```bash
adk web
```

Navigate to `http://localhost:8000` and select `product_validation_pipeline`.

## Sample Usage

Send a JSON product list as the message (the pipeline reads it automatically from the user message):

```json
[
  {
    "mirakl_product_id": "PROD-001",
    "data": {
      "title": "Men's Classic Fit Shirt",
      "brand": "Arrow",
      "style_number": "VGC-12345",
      "product_category": "25_151_13",
      "meta_description": "...",
      "nrf_size": "M",
      "display_color": "Blue",
      "main_image": { "source": "https://...", "original_url": "https://..." },
      "alt_image_1": { "source": "https://..." }
    },
    "sources": [{ "provider_code": "SELLER123" }]
  }
]
```

The pipeline will:
1. Resolve the product category to its P1/P2/P3 hierarchy and retrieve all applicable compliance rules
2. Validate all images visually (dimensions, background, watermarks, brand, spelling) in parallel with attribute validation
3. Assign a confidence score (0–100) and an Approve/Reject decision with point-by-point reasoning
4. Write the full validation record to BigQuery

## VGC Duplicate Detection

A VGC (Variant Group Code) duplicate check agent is fully implemented and can be enabled to run alongside image and attribute validation. It detects:

- **Cross-VGC duplicates**: Same seller has submitted the same product (brand + title) under a different style number
- **Intra-VGC duplicates**: Same size + colour combination already exists in the VGC group (semantic colour comparison, e.g. "Grey" == "Gray")
- **VGC inconsistencies**: Variants in the same group with mismatched brand or title

To enable, uncomment `validate_vgc_agent` in `root_agent/agent.py` and update the ConfidenceScoreAgent prompt to incorporate `{vgc_validation_json}`.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | Yes | — | GCP project used for all services |
| `BQ_DATASET` | Yes | `product_validation` | BigQuery dataset |
| `BQ_TABLE` | Yes | `validation_results` | BigQuery table |
| `GOOGLE_APPLICATION_CREDENTIALS` | Outside GCP | — | Service account JSON path |
