"""Root Sequential Agent for Product Validation Pipeline."""

from google.adk.agents import SequentialAgent, ParallelAgent

from .sub_agents.compliance_search_agent import compliance_search_agent
from .sub_agents.validate_image_agent import validate_image_agent
from .sub_agents.validate_attribute_agent import validate_attribute_agent
from .sub_agents.confidence_score_agent import confidence_score_agent
from .sub_agents.bigquery_write_agent import bigquery_write_agent

# Parallel agent: image validation + attribute validation run concurrently
validation_parallel_agent = ParallelAgent(
    name="validation_parallel_agent",
    description="Runs image validation and attribute validation in parallel",
    sub_agents=[
        validate_image_agent,      # -> image_validation_json
        validate_attribute_agent,  # -> attribute_validation_json
    ],
)

# Root Sequential Agent - validates and scores products
try:
    root_agent = SequentialAgent(
        name="product_validation_pipeline",
        description="Sequential agent pipeline for product extraction, validation, and storage",
        sub_agents=[
            compliance_search_agent,    # Step 1: Fetch image compliance rules -> compliance_search_result
            validation_parallel_agent,  # Step 2: Image + Attribute validation in parallel
            confidence_score_agent,     # Step 3: Combine both -> validation_and_score_json
            bigquery_write_agent,          # Step 5: Write confidence score results to BigQuery
        ],
    )
except Exception as e:
    print(f"Error initializing root agent: {e}")
