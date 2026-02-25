# POC Image Features - Product Validation Pipeline

AI Agent using Google ADK for product validation and BigQuery integration.

## Project Structure

```
poc-image-features/
├── root_agent.py              # Main sequential agent orchestrating the pipeline
├── models.py                  # Pydantic models for validation records
├── tools/                     # Tool implementations
│   ├── __init__.py
│   └── bigquery_tool.py      # Tool 4: BigQuery write functionality
├── sub_agents/                # Individual agent modules
│   ├── extract_product/      # Tool 1: Fetch from external API
│   ├── validate_image/       # Tool 2: Image dimension validation
│   ├── validate_attribute/   # Tool 3: Attribute validation by product type
│   ├── summarize_product/    # Summarization agent
│   └── tools.py              # Shared tools for sub-agents
├── pyproject.toml            # Project configuration
├── .env.example              # Environment variables template
└── README.md
```

## Pipeline Workflow

```
1. Extract Product (Tool 1)
   ↓ product_details
2. Validate Image (Tool 2) → Check dimensions ≥1920×1080
   ↓ image_validation_json
3. Validate Attributes (Tool 3) → Check required fields by product_type
   ↓ attribute_validation_json
4. Summarize Results
   ↓ summary
5. Write to BigQuery (Tool 4) → Store raw_data + validated_data
   ↓ bigquery_result
```

## Setup

### 1. Authenticate with GCP

```powershell
gcloud auth application-default login
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
BQ_DATASET=product_validation
BQ_TABLE=validation_results
GOOGLE_API_KEY=your-google-api-key
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Create BigQuery Table

```sql
CREATE TABLE `your-project.product_validation.validation_results` (
  raw_data STRING,
  validated_data STRING
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

Prompt the agent with:
```
Validate product with ID 1
```

The agent will:
1. Fetch product from DummyJSON API
2. Validate the image dimensions
3. Check required attributes
4. Store results in BigQuery
