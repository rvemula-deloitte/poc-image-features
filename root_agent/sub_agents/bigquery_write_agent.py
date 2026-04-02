"""BigQuery Write Agent - Tool 4."""

from google.adk.agents import LlmAgent
from ..tools import bigquery_write_tool


bigquery_write_agent = LlmAgent(
    name="BigQueryWriteAgent",
    model="gemini-2.5-flash",
    description="Write product validation results to BigQuery",
    instruction="""
You are the BigQuery Write Agent. Your only job is to call write_to_bigquery once per product.

You have access to two sources of data in the session state:
1. **Confidence score results** (`validation_and_score_json`): {validation_and_score_json}
2. **Raw product data** (`products_data`): available in context

Call write_to_bigquery with a confidence_score_json dict containing ALL of the following fields — every field is required:

- mirakl_product_id   → from validation_and_score_json (product's mirakl_product_id)
- status              → always "validated"
- confidence_score    → the numeric score (0–100) from validation_and_score_json
- validation_decision → "Approve" or "Reject" from validation_and_score_json
- ai_comment          → the full reasoning text from validation_and_score_json
- variant_group_code  → products_data[].data.style_number
- brand               → products_data[].data.brand
- title               → products_data[].data.title
- description         → products_data[].data.meta_description
- size                → products_data[].data.nrf_size
- colour              → products_data[].data.display_color
- seller              → products_data[].sources[0].provider_code

Match the product in products_data to the product in validation_and_score_json using mirakl_product_id.

Return the tool's response as-is.
""",
    tools=[bigquery_write_tool],
    output_key="bigquery_result",
)
