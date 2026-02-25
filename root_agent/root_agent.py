"""Root Sequential Agent for Product Validation Pipeline."""

from google.adk.agents import SequentialAgent

# Import all sub-agents
from sub_agents.extract_product_agent import extract_product
from sub_agents.validate_image_agent import validate_image_agent
from sub_agents.validate_attribute_agent import validate_attribute
from sub_agents.summarize_product_agent import summarize_product_agent
from sub_agents.bigquery_write_agent import bigquery_write_agent


# Root Sequential Agent
root_agent = SequentialAgent(
    name="product_validation_pipeline",
    description="Sequential agent pipeline for product extraction, validation, and storage",
    sub_agents=[
        extract_product,           # Tool 1: API fetch
        validate_image_agent,      # Tool 2: Image validation
        validate_attribute,        # Tool 3: Attribute validation
        bigquery_write_agent,      # Tool 4: BigQuery write
    ],
)
