"""Root Sequential Agent for Product Validation Pipeline."""

from google.adk.agents import SequentialAgent, ParallelAgent

# Import all sub-agents
from .sub_agents.extract_product_agent import extract_product
from .sub_agents.compliance_search_agent import compliance_search_agent
from .sub_agents.validate_image_agent import validate_image_agent
# from .sub_agents.validate_image_embedding_agent import validate_image_embedding_agent
from .sub_agents.validate_attribute_agent import validate_attribute_agent
from .sub_agents.confidence_score_agent import confidence_score_agent
# from .sub_agents.summarize_product_agent import summarize_product_agent
# from .sub_agents.bigquery_write_agent import bigquery_write_agent


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
            # extract_product,            # Step 1: Fetch products from API -> products_data
            compliance_search_agent,      # Step 2: Fetch image compliance rules -> compliance_search_result
            validation_parallel_agent,    # Step 3: Image + Attribute validation in parallel
                                          #           -> image_validation_json
                                          #           -> attribute_validation_json
            confidence_score_agent,       # Step 4: Combine both -> validation_and_score_json
            # bigquery_write_agent,       # Step 5: Batch write to BigQuery
        ],
    )
except Exception as e:
    print(f"Error initializing root agent: {e}")
