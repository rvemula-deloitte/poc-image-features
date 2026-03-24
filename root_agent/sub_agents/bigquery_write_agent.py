"""BigQuery Write Agent - Tool 4."""

from google.adk.agents import LlmAgent
from ..tools import bigquery_write_tool


bigquery_write_agent = LlmAgent(
    name="BigQueryWriteAgent",
    model="gemini-2.5-flash",
    description="Write product validation results to BigQuery",
    instruction="""
Call the write_to_bigquery tool with this parameter:
- confidence_score_json: {validation_and_score_json}

Use the confidence score results from the confidence score agent state to write row(s) to BigQuery.
Return the tool's response as-is.
""",
    tools=[bigquery_write_tool],
    output_key="bigquery_result",
)
