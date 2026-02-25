"""BigQuery Write Agent - Tool 4."""

from google.adk.agents import LlmAgent
from tools import bigquery_write_tool


bigquery_write_agent = LlmAgent(
    name="BigQueryWriteAgent",
    model="gemini-2.5-flash",
    description="Write product validation results to BigQuery",
    instruction="""
Call the write_to_bigquery tool with these parameters:
- product_details: {prodcut_details}
- image_validation: {image_validation_json}
- attribute_validation: {attribute_validation_json}

IMPORTANT: Pass the data EXACTLY as received. Do NOT modify or interpret it.
Return the tool's response as-is.
""",
    tools=[bigquery_write_tool],
    output_key="bigquery_result",
)
