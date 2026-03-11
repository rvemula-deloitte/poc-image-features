"""Root Sequential Agent for Product Validation Pipeline."""

from google.adk.agents import SequentialAgent, ParallelAgent

# Import all sub-agents
from sub_agents.extract_product_agent import extract_product
from sub_agents.validate_image_agent import validate_image_agent
# from sub_agents.validate_image_embedding_agent import validate_image_embedding_agent
from sub_agents.validate_attribute_agent import validate_and_score_agent
# from sub_agents.summarize_product_agent import summarize_product_agent
# from sub_agents.bigquery_write_agent import bigquery_write_agent


# Root Sequential Agent - validates and scores products
try:
    root_agent = SequentialAgent(
        name="product_validation_pipeline",
        description="Sequential agent pipeline for product extraction, validation, and storage",
        sub_agents=[
            # extract_product,                 # Step 1: Fetch products from API -> products_data
            validate_image_agent,  # Step 2: Image validation -> image_validation_json
            validate_and_score_agent,        # Step 3: Attribute validation + confidence scoring -> validation_and_score_json
            # bigquery_write_agent,          # Step 4: Batch write to BigQuery
        ],
    )
except Exception as e:
    print(f"Error initializing root agent: {e}")
