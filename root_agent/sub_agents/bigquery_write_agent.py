"""BigQuery Write Agent - Tool 4."""

from google.adk.agents import LlmAgent
from ..tools import bigquery_write_tool


bigquery_write_agent = LlmAgent(
    name="BigQueryWriteAgent",
    model="gemini-2.5-flash",
    description="Write product validation results to BigQuery",
    include_contents='none',
    instruction="""
You are the BigQuery Write Agent. Your only job is to call write_to_bigquery once per product.
product_data : {products_data}
For each product in the confidence score results ({validation_and_score_json}), call write_to_bigquery
with a confidence_score_json dict containing ALL of the following fields — every field is required:

- mirakl_product_id   → product's mirakl_product_id
- status              → always "validated"
- confidence_score    → the numeric score (0–100) from the confidence score agent
- validation_decision → "Approve" or "Reject" from the confidence score agent
- ai_comment          → the full reasoning text from the confidence score agent
- variant_group_code  → data.style_number
- brand               → data.brand
- title               → data.title
- description         → data.meta_description
- size                → data.nrf_size  (the nrf_size field from product data)
- colour              → data.display_color
- seller              → sources[0].provider_code  ← this is the seller identifier

Return the tool's response as-is.
""",
    tools=[bigquery_write_tool],
    output_key="bigquery_result",
)
