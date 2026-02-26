"""Root Sequential Agent for Product Validation Pipeline."""

from google.adk.agents import SequentialAgent, ParallelAgent

# Import all sub-agents
from sub_agents.extract_product_agent import extract_product
from sub_agents.validate_image_agent import validate_image_agent
from sub_agents.validate_image_embedding_agent import validate_image_embedding_agent
from sub_agents.validate_attribute_agent import validate_attribute
from sub_agents.confidence_score_agent import confidence_score_agent
from sub_agents.summarize_product_agent import summarize_product_agent
from sub_agents.bigquery_write_agent import bigquery_write_agent


# Root Sequential Agent - run validations sequentially to ensure output_key propagation
root_agent = SequentialAgent(
    name="product_validation_pipeline",
    description="Sequential agent pipeline for product extraction, validation, and storage",
    sub_agents=[
        extract_product,           # Step 1: Fetch products from API -> products_data
        # validate_image_agent,      # Step 2: Image validation -> image_validation_results
        validate_image_embedding_agent,  # Step 2: Embedding-based image validation -> embedding_validation_results
        validate_attribute,        # Step 3: Attribute validation -> attribute_validation_results
        confidence_score_agent,    # Step 4: Calculate confidence scores -> scored_products
        # bigquery_write_agent,    # Step 5: Batch write to BigQuery
    ],
)
