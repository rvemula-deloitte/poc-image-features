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
│   ├── validate_image_embedding/ # Tool 2b: Embedding-based image validation
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
2. Parallel Validation
   ├─ Validate Image (Tool 2) → Embedding-based validation
   │  ↓ embedding_validation_json
   └─ Validate Attributes (Tool 3) → Check required fields by product_type
      ↓ attribute_validation_json
3. Calculate Confidence Scores
   ↓ scored_products
4. Write to BigQuery (Tool 4) → Store validation results
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
2. Run image and attribute validation **in parallel** for better performance
3. Calculate confidence scores based on validation results
4. Store results in BigQuery

## Embedding-Based Image Validation (New)

An alternative to dimension-based image validation is the **embedding-based validation agent** that uses Vertex AI's MultiModalEmbedding model to verify if product images actually match their titles and descriptions.

### How It Works

1. **Downloads** the product image from the URL
2. **Embeds** both the image and the product text (title + description) using Vertex AI
3. **Calculates** cosine similarity between image and text embeddings
4. **Validates** if similarity score meets the threshold (default: 0.70)

### Usage

The new agent is located in:
- Agent: `sub_agents/validate_image_embedding_agent.py`
- Tool: `tools/embedding_validation_tool.py`

To use it, replace or complement the existing `validate_image_agent` in your pipeline.

### Environment Variables

Ensure these are set:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1  # or your preferred region
```

### Example Response

```json
{
  "results": [
    {
      "product_id": "12345",
      "image_url": "https://...",
      "embedding_validation": {
        "valid": true,
        "message": "Image matches product description"
      }
    }
  ],
  "summary": {
    "total": 1,
    "valid": 1,
    "failed": 0,
    "similarity_threshold": 0.70
  }
}
```

### Benefits Over Dimension-Only Validation

- **Content verification**: Ensures image actually shows the product
- **Detects wrong products**: Catches cases where wrong images are used
- **Semantic matching**: Uses AI to understand image-text relationships
- **Complements dimension checks**: Can be used alongside size validation

